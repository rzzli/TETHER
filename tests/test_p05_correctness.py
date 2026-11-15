"""Bounded correctness controls; synthetic values only, no provider calls."""
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.agents import Usage
from tether_engine.features import build_features
from tether_engine.serde import ContractError, parse_json
from tether_engine.workflow import Budget, BudgetMeter


class CorrectnessTests(unittest.TestCase):
    def test_recovery_inspection_sums_unresolved_reservations_exactly(self):
        from tether_engine.journal import inspect_run
        events = [{'event': 'run_reserved', 'details': {}}]
        for index in range(3):
            events.append({'event': 'dispatch', 'details': {
                'attempt_id': str(index), 'reserved': {
                    'input_tokens': 1, 'output_tokens': 1, 'cost_usd': .1}}})
        with tempfile.TemporaryDirectory() as temporary:
            with patch('tether_engine.journal.read_chain', return_value=events):
                result = inspect_run(Path(temporary))
        self.assertEqual(result['estimated_upper_usage']['cost_usd'], .3)
        self.assertEqual(len(result['unresolved_attempts']), 3)

    def test_exact_decimal_budget_accepts_three_ten_cent_calls(self):
        meter = BudgetMeter(Budget(max_cost_usd=.30))
        quote = Usage(1, 1, .10)
        for _ in range(3):
            self.assertTrue(meter.can_reserve(quote))
            meter.account(quote)
        self.assertFalse(meter.can_reserve(Usage(0, 0, .000001)))
        self.assertEqual(meter.used.cost_usd, .30)

    def test_tiny_decimal_overrun_is_not_hidden_by_float_rounding(self):
        meter = BudgetMeter(Budget(max_cost_usd=.1))
        meter.account(Usage(0, 0, .1))
        self.assertFalse(meter.can_reserve(Usage(0, 0, 1e-20)))

    def test_money_rejects_boolean_and_nonfinite_values(self):
        for value in (True, False, float('inf'), float('nan'), -1, 10**400):
            with self.subTest(value=value), self.assertRaises(ContractError):
                Usage(0, 0, value).validate()
            with self.subTest(cap=value), self.assertRaises(ContractError):
                Budget(max_cost_usd=value).validate()

    def test_overflow_json_rejected_before_decoding_contract(self):
        for value in ('1e400', '-1e400', '{"x": [1e400]}'):
            with self.subTest(value=value), self.assertRaisesRegex(ContractError, 'finite'):
                parse_json(value)
        self.assertEqual(parse_json('1.25e2'), 125)

    def test_extreme_json_integer_has_stable_contract_error(self):
        with self.assertRaises(ContractError):
            parse_json('1' * 5000)

    def test_decimal_costs_reconcile_through_sealed_execution(self):
        import tether_engine
        from tether_engine.agents import ExtractiveBackend, Selection
        from tether_engine.artifacts import verify_run, write_run
        from tether_engine.chrono import load_snapshot
        from tether_engine.contracts import Case
        from tether_engine.serde import decode, read_json
        from tether_engine.workflow import run_workflow
        class FictionalCharges(ExtractiveBackend):
            def quote(self, request):
                return Usage(1, 1, .1)
            def select(self, request):
                selection = super().select(request)
                return Selection(selection.observation_ids, Usage(1, 1, .1))
        fixture = Path(tether_engine.__file__).parent / 'demo' / 'v2'
        case = decode(Case, read_json(fixture / 'case.json'))
        store = load_snapshot(fixture / 'snapshot.json', case)
        result = run_workflow(case, store, FictionalCharges(), budget=Budget(max_cost_usd=.3))
        self.assertEqual(result.calls, 3)
        self.assertEqual(result.usage.cost_usd, .3)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'run'
            receipt = write_run(output, result, store, None)
            self.assertEqual(verify_run(output, receipt)['semantic_consistency'], 'verified')

    def test_invalid_unicode_is_a_parser_error(self):
        for value in ('"\\ud800"', '{"\\udfff": 1}', '"\ud800"'):
            with self.subTest(value=repr(value)), self.assertRaisesRegex(ContractError, 'Unicode|JSON'):
                parse_json(value)
        self.assertEqual(parse_json('"\\ud83d\\ude00"'), '\U0001f600')

    def test_json_nesting_is_bounded_with_a_stable_reason(self):
        with self.assertRaisesRegex(ContractError, 'nesting|depth'):
            parse_json('[' * 2000 + '0' + ']' * 2000)
        self.assertEqual(parse_json('{"text":"[{}]", "list":[[]]}')['list'], [[]])

    def test_generated_group_label_cannot_merge_unrelated_components(self):
        case = SimpleNamespace(hypothesis=SimpleNamespace(key='scope'))
        def claim(identifier, group, value):
            observation = SimpleNamespace(observation_id=identifier, dependency_group=group,
                study_id=None, context=SimpleNamespace(cohort_ids=()), feature_scope='scope',
                features={'genetic_support': value})
            return SimpleNamespace(evidence=SimpleNamespace(observation=observation))
        claims = (claim('a', None, .2), claim('b', 'unknown-dependence:a', .8))
        feature = build_features(claims, case).values['genetic_support']
        self.assertEqual(feature.dependency_groups, 2)
        self.assertAlmostEqual(feature.value, .5)
        self.assertEqual(feature.status, 'observed')

    def test_malformed_pointer_validation_is_bounded(self):
        code = "from tether_engine.study.source_fact_adapters import _POINTER; assert _POINTER.fullmatch('/'*8192+'~') is None; assert _POINTER.fullmatch('/a~1b/~0/') is not None"
        try:
            result = subprocess.run([sys.executable, '-c', code], capture_output=True, timeout=5)
        except subprocess.TimeoutExpired:
            self.fail('Malformed pointer exceeded five-second validation bound')
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))


if __name__ == '__main__':
    unittest.main()
