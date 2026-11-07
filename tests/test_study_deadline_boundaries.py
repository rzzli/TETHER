"""Absolute preparation caps remain exact at floating-point clock boundaries."""
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError
from tether_engine.study import authority_four_arm as composition
from tether_engine.study import retrieval_preparation as retrieval
from tether_engine.study import retrieval_smoke as integration
from tether_engine.study import source_preparation as source
from tether_engine.study import tokenization as tokenizer


NOW = 212.007
LIMIT = NOW + 300


class PassedDeadlineGate(Exception):
    """Stop before any original-source access or output reservation."""


class PreparationDeadlineTests(unittest.TestCase):
    def test_tokenizer_accepts_its_exact_absolute_limit(self):
        self.assertGreater(LIMIT - NOW, 300)
        with patch.object(tokenizer.time, 'monotonic', return_value=NOW):
            tokenizer._bounded_deadline(LIMIT)

    def test_default_token_replay_deadline_reaches_source_checks(self):
        with patch.object(tokenizer.time, 'monotonic', return_value=NOW), \
             patch.object(tokenizer, '_no_links', side_effect=PassedDeadlineGate) as sources:
            with self.assertRaises(PassedDeadlineGate):
                tokenizer.verify_tokenization('invented-unused-quote', 'a'*64, 'b'*64, 'c'*64)
        sources.assert_called_once()

    def test_source_accepts_exact_limit_before_any_source_access(self):
        with patch.object(source.time, 'monotonic', return_value=NOW), \
             patch.object(source, '_prepare_parent', side_effect=PassedDeadlineGate) as parent:
            with self.assertRaises(PassedDeadlineGate):
                source.prepare_source_request('unused-authority', 'a'*64, {},
                                              'unused-output', deadline=LIMIT)
        parent.assert_called_once()

    def test_retrieval_accepts_exact_limit_before_any_source_access(self):
        with patch.object(retrieval.time, 'monotonic', return_value=NOW), \
             patch.object(retrieval, '_prepare_parent', side_effect=PassedDeadlineGate) as parent:
            with self.assertRaises(PassedDeadlineGate):
                retrieval.prepare_retrieval({}, 'a'*64, {}, 'unused-output', deadline=LIMIT)
        parent.assert_called_once()

    def test_invalid_token_deadlines_never_reserve_or_read_assets(self):
        cases = ((math.nextafter(LIMIT, math.inf), ContractError),
                 (NOW, TimeoutError), (NOW-1, TimeoutError),
                 (math.nan, ContractError), (math.inf, ContractError),
                 (-math.inf, ContractError), (True, ContractError), (False, ContractError))
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve()/'must-not-exist'
            for deadline, exception in cases:
                with self.subTest(deadline=deadline), \
                     patch.object(tokenizer.time, 'monotonic', return_value=NOW), \
                     patch.object(tokenizer, '_reserve') as reserve, \
                     patch.object(tokenizer, '_validate_spec') as assets:
                    with self.assertRaises(exception):
                        tokenizer.tokenize_prompt('invented prompt', {}, deadline, output)
                    reserve.assert_not_called()
                    assets.assert_not_called()
                    self.assertFalse(output.exists())

    def assert_invalid_preparation(self, module, invoke):
        deadlines = (math.nextafter(LIMIT, math.inf), NOW, NOW-1, math.nan,
                     math.inf, -math.inf, True, False)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary).resolve()/'must-not-exist'
            for deadline in deadlines:
                with self.subTest(deadline=deadline), \
                     patch.object(module.time, 'monotonic', return_value=NOW), \
                     patch.object(module, '_prepare_parent') as parent, \
                     patch.object(module, 'RunJournal') as reserve:
                    with self.assertRaises(ContractError):
                        invoke(output, deadline)
                    parent.assert_not_called()
                    reserve.assert_not_called()
                    self.assertFalse(output.exists())

    def test_invalid_source_deadlines_never_reserve_output(self):
        self.assert_invalid_preparation(source, lambda output, deadline:
            source.prepare_source_request('unused-authority', 'a'*64, {}, output,
                                          deadline=deadline))

    def test_invalid_retrieval_deadlines_never_reserve_output(self):
        self.assert_invalid_preparation(retrieval, lambda output, deadline:
            retrieval.prepare_retrieval({}, 'a'*64, {}, output, deadline=deadline))

    def test_composition_exact_limit_returns_a_bounded_duration(self):
        with patch.object(composition.time, 'monotonic', return_value=NOW):
            self.assertEqual(composition._remaining(LIMIT), 300.0)
            self.assertEqual(composition._remaining(NOW+100), 100.0)

    def test_integration_exact_limit_returns_a_bounded_duration(self):
        with patch.object(integration.time, 'monotonic', return_value=NOW):
            self.assertEqual(integration._remaining(LIMIT), 300.0)
            self.assertEqual(integration._remaining(NOW+100), 100.0)

    def test_remaining_helpers_reject_invalid_endpoints(self):
        for module in (composition, integration):
            for deadline in (math.nextafter(LIMIT, math.inf), NOW, NOW-1,
                             math.nan, math.inf, -math.inf, True, False):
                with self.subTest(module=module.__name__, deadline=deadline), \
                     patch.object(module.time, 'monotonic', return_value=NOW):
                    with self.assertRaises(ContractError):
                        module._remaining(deadline)

    def test_boolean_endpoint_is_not_an_early_uptime_budget(self):
        for module in (composition, integration):
            with self.subTest(module=module.__name__), \
                 patch.object(module.time, 'monotonic', return_value=0.0):
                with self.assertRaises(ContractError):
                    module._remaining(True)


if __name__ == '__main__':
    unittest.main()
