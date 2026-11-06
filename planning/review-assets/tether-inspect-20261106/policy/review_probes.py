"""Independent fictional boundary probes; never run the frozen 109-case suite.

This module imports the new extension for testing, not as independent numerical
reconstruction. No event loop, provider network, production inputs or model is used.
"""
from pathlib import Path
from types import SimpleNamespace
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experiments/inspect_policy/tests'))

from experiments.inspect_policy.records import CaseRecord, canonical, digest, publish, thaw
from experiments.inspect_policy.accounting import Accounting
from experiments.inspect_policy.archive import execute_archive_case
from experiments.inspect_policy.task import archive_scorer
from experiments.inspect_policy.runtime import ACTIVE, ScriptedProvider, CONFIG
from experiments.inspect_policy.evidence import EvidenceContext
from inspect_ai.model import ChatMessageUser, GenerateConfig, ModelOutput
from fixtures import source


def immediate(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as done:
        return done.value
    raise AssertionError('Probe unexpectedly required event-loop scheduling')


def main():
    base = ROOT / 'data/cache/inspect-policy-independent-probes'
    base.mkdir(parents=True, exist_ok=True)
    findings = {}
    with tempfile.TemporaryDirectory(dir=base) as temporary:
        root = Path(temporary)
        # Both records have the same verdict; only identity makes this invalid.
        observed = {'schema_version': 1, 'control_id': 'fiction-B', 'decision': 'accept',
                    'stage': 'prepare_run', 'violated_obligations': [],
                    'checked_scope': [], 'observables': {}}
        result = {'control_id': 'fiction-B', 'status': 'completed', 'decision': observed}
        record = CaseRecord(root / 'record-B', {'control_id': 'fiction-B'})
        seal = record.finish(result)
        oracle = root / 'oracle.json'
        pin = publish(oracle, {'cases': [{'control_id': 'fiction-A', 'decision': 'accept', 'observables': {}}]})
        state = SimpleNamespace(sample_id='fiction-A',
            metadata={'policy_record': {'path': str(record.path), 'receipt': seal['receipt']}},
            output=ModelOutput.from_content(model='none', content=canonical(result).decode()))
        try:
            verdict = immediate(archive_scorer(str(oracle), pin)(state, None))
            findings['cross_case_record_swap'] = {'rejected': False, 'native_score': verdict.value}
        except (ValueError, KeyError) as exc:
            findings['cross_case_record_swap'] = {'rejected': True, 'reason': str(exc)}

        # A frozen request created for CONFIG must not authorize altered temp.
        record = CaseRecord(root / 'config-change', {'id': 'fiction-config'})
        budget = {'max_calls': 1, 'max_input_tokens': 100, 'max_output_tokens': 100,
                  'max_cost_usd': 0.0, 'max_seconds': 10.0}
        account = Accounting(record, budget)
        request = {'case_id': 'fiction-config', 'offered_observation_ids': []}
        ticket = account.reserve(request, {'input_tokens': 10, 'output_tokens': 10, 'cost_usd': 0.0})
        active = {'record': record, 'ticket': ticket, 'account': account, 'entries': 0,
                  'dispatched': 0, 'step': {'script': {'behavior': 'success',
                    'content': '{"observation_ids":[]}', 'usage': {'input_tokens': 1, 'output_tokens': 1, 'cost_usd': 0.0}}}}
        configured = GenerateConfig(**CONFIG)
        provider = ScriptedProvider(model_name='fictional-no-network', config=configured)
        altered = GenerateConfig(**{**CONFIG, 'temperature': 0.9, 'max_tokens': 10})
        token = ACTIVE.set(active)
        try:
            try:
                immediate(provider.generate([ChatMessageUser(content=canonical(request).decode())], [], 'none', altered))
                findings['altered_temperature'] = {'rejected': False, 'dispatches': active['dispatched']}
            except (ValueError, RuntimeError) as exc:
                findings['altered_temperature'] = {'rejected': True, 'reason': str(exc), 'dispatches': active['dispatched']}
        finally:
            ACTIVE.reset(token)

        row = source(root / 'source', ident='fiction-output')
        nested = Path(row['bundle_root']) / 'new-output'
        nested.mkdir()
        try:
            returned = execute_archive_case(row, nested)
            findings['nested_input_output'] = {'rejected_before_write': False,
                'status': returned['result']['status'], 'decision': thaw(returned['result']['decision']),
                'created_protected_files': sorted(str(p.relative_to(Path(row['bundle_root']))) for p in nested.rglob('*') if p.is_file())}
        except (ValueError, FileExistsError) as exc:
            findings['nested_input_output'] = {'rejected_before_write': not any(nested.rglob('*')), 'reason': str(exc)}

        context = EvidenceContext(row)
        record = CaseRecord(root / 'duplicate-claims', {'id': 'fiction-duplicate'})
        first = context.commit(['obs-1'], 'genetics', record, clock=lambda: 0, deadline=1)
        try:
            second = context.commit(['obs-1'], 'genetics', record, clock=lambda: 0, deadline=1)
            findings['duplicate_cross_step_claim'] = {'rejected': False,
                'same_claim_id': first['claims'][0]['claim_id'] == second['claims'][0]['claim_id']}
        except ValueError as exc:
            findings['duplicate_cross_step_claim'] = {'rejected': True, 'reason': str(exc)}
    print(json.dumps({'scope': 'fictional direct-function probes; no native eval or production corpus',
                      'findings': findings}, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
