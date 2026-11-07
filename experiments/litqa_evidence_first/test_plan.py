"""Public invented bank and exclusive authority tests, with no inference."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID

from tether_engine.serde import canonical, encode
from experiments.litqa_refinement import contracts as old
from experiments.litqa_refinement import test_contracts as fixtures
from . import contracts as c, model, plan


def invented_bank(root):
    """Engineering schema fixture, distinct from the prospective control bank."""
    root.mkdir(); (root / 'actor_cases').mkdir()
    cases = []; ancestry = []; slots = {}; ids = []
    for index in range(6):
        q = fixtures.query(); q['id'] = str(UUID(int=index + 1)); ids.append(q['id'])
        prior = old.candidate(q, None, producer_status='input_unavailable', original_admission_status='not_run',
                              native_call_sha256=None, generated_at_utc=None, offered_ids=[])
        critic = old.critique(q, prior, [], None, native_status='capacity', native_call_sha256=None)
        case = dict(query=q, candidate_context=prior, critique_context=critic, sources=[]); cases.append(case)
        ancestry.append(dict(id=q['id'], invented=True, scope='fictional_qualification',
            prior_capture_is_actual_native=False, critic_capture_is_actual_native=False,
            cutoff_utc='2026-11-07T12:10:31+00:00', critique_created_at_utc='2026-11-07T10:00:00+00:00',
            current_source_available_at_utc='2026-11-07T11:00:00+00:00'))
        for phase in c.PHASES:
            name = f'actor_cases/{phase}-{index:04d}.json'
            slots[name] = dict(proof=c.write(root / name, dict(task=phase, **case)),
                               role='single_slot_actor_input', phase=phase, ordinal=index, id=q['id'])
    roles = {
        'contexts': dict(role='coordinator_only', proof=c.write(root / 'ACTOR.json',
            dict(kind='synthetic_refinement_contexts_v1', scope='fictional_qualification', cases=cases))),
        'ancestry': dict(role='coordinator_only', proof=c.write(root / 'ANCESTRY.json',
            dict(kind='synthetic_refinement_ancestry_v1', actual_prior_model_calls=0, cases=ancestry))),
        'expectations': dict(role='evaluation_only', proof=c.write(root / 'EVALUATOR.json', {'never_grant': 'gold'})),
    }
    return dict(original_parent_identity='a' * 64, bank=c.write(root / 'BANK.json', dict(schema_version=1, kind='tether_evidence_first_qualification_bank_v1',
        purpose='fictional_qualification', max_native_calls=12, source_http_requests=0, phase_order=c.PHASES,
        schedule=ids, role_files=roles, slots=slots)))


class PlanTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup); self.root = Path(temp.name).resolve()
        replace = patch.object(c, 'ROOT', self.root); replace.start(); self.addCleanup(replace.stop)
        self.parent = invented_bank(self.root / 'bank')
        (self.root / 'data').mkdir()
        self.model = dict(model_receipt={}, model_license={}, model_spec={}, model_provenance={
            'weights_sha256': {'invented.gguf': 'a' * 64}, 'runtime_sha256': 'b' * 64},
            interpreter=c.capture(Path(sys.executable).resolve())[0], port=55645, alias='invented')

    def prepare(self, name='prepared'):
        return plan.prepare(self.parent, self.root / 'data' / name, qualification_model=self.model)

    def test_six_complete_pairs_and_no_evaluator_grant(self):
        anchor = self.prepare(); value = plan.read(anchor)
        self.assertEqual(len(value['prepared']), 6)
        closure = c.read(value['source_closure'])
        self.assertFalse(any(Path(p['path']).name == 'EVALUATOR.json' for p in closure['proofs']))
        claim = plan.reserve(anchor)
        checked, authority = plan.verify_authority(anchor, claim)
        self.assertEqual(checked, value); self.assertEqual(authority['budgets']['generation_calls'], 12)
        self.assertTrue(authority['permanent'])

    def test_moving_to_second_output_does_not_duplicate_authority(self):
        first = self.prepare(); second = self.prepare('elsewhere')
        authority = plan.reserve(first); original = Path(authority['path']).read_bytes()
        with self.assertRaises(FileExistsError): plan.reserve(second)
        self.assertEqual(Path(authority['path']).read_bytes(), original)

    def test_concurrent_registry_claim_has_one_winner(self):
        anchor = self.prepare()
        def reserve(_):
            try: return plan.reserve(anchor)
            except FileExistsError: return None
        with ThreadPoolExecutor(max_workers=2) as pool: values = list(pool.map(reserve, range(2)))
        self.assertEqual(sum(v is not None for v in values), 1)

    def test_replacement_bank_does_not_create_another_twelve_call_allowance(self):
        first = self.prepare(); plan.reserve(first)
        self.parent = invented_bank(self.root / 'replacement-bank')
        second = self.prepare('replacement-plan')
        with self.assertRaises(FileExistsError): plan.reserve(second)

    def test_resealed_budget_increase_fails_before_reservation(self):
        anchor = self.prepare(); value = encode(c.read(anchor)); value['budgets']['generation_calls'] = 13
        Path(anchor['path']).write_bytes(canonical(value)); changed = c.capture(anchor['path'])[0]
        with self.assertRaises(ValueError): plan.reserve(changed)
        self.assertFalse(c.authority_registry('fictional_qualification').exists())

    def test_resealed_omitted_parent_closure_fails_before_reservation(self):
        anchor = self.prepare(); value = encode(c.read(anchor))
        Path(value['source_closure']['path']).write_bytes(canonical(dict(proofs=[], inventories=[])))
        value['source_closure'] = encode(c.capture(value['source_closure']['path'])[0])
        Path(anchor['path']).write_bytes(canonical(value)); changed = c.capture(anchor['path'])[0]
        with self.assertRaises(ValueError): plan.reserve(changed)
        self.assertFalse(c.authority_registry('fictional_qualification').exists())

    def test_changed_bank_parent_is_not_authorized_by_old_plan(self):
        anchor = self.prepare()
        (self.root / 'bank/actor_cases/repair-0000.json').write_bytes(b'{}')
        with self.assertRaises(ValueError): plan.reserve(anchor)

    def test_forged_production_cannot_use_six_case_qualification(self):
        anchor = self.prepare(); value = encode(c.read(anchor)); value['purpose'] = 'production'
        Path(anchor['path']).write_bytes(canonical(value)); changed = c.capture(anchor['path'])[0]
        with self.assertRaises(ValueError): plan.reserve(changed)

    def test_preparation_failure_is_retained_without_calls_or_authority(self):
        with self.assertRaises(ValueError):
            plan.prepare(self.parent, self.root / 'data/bad', qualification_model={})
        failure = c.read(c.capture(self.root / 'data/bad/FAILURE.json')[0])
        self.assertFalse(failure['model_or_http_execution_performed'])
        self.assertFalse((self.root / 'data/bad/PLAN.json').exists())

    def test_output_outside_data_and_inside_authority_are_rejected(self):
        for output in (self.root / 'outside', c.authority_registry('fictional_qualification') / 'nested'):
            with self.assertRaises(ValueError):
                plan.prepare(self.parent, output, qualification_model=self.model)
            self.assertFalse(output.exists())


if __name__ == '__main__': unittest.main()
