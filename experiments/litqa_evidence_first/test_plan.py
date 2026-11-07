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
    decision = c.write(root / 'DECISION.json', {'scope': 'Invented engineering fixture proposal'})
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
            current_source_available_at_utc={}))
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
    return dict(bank=c.write(root / 'BANK.json', dict(schema_version=1, kind='tether_evidence_first_qualification_bank_v1',
        purpose='fictional_qualification', max_native_calls=12, source_http_requests=0, phase_order=c.PHASES,
        schedule=ids, role_files=roles, slots=slots, decision=decision)))


def invented_inspection(root):
    """Metadata-only engineering fixture, never an admitted scientific parent."""
    root.mkdir(); original = root / 'original'; original.mkdir()
    frame = c.write(original / 'FRAME.json', dict(schema_version=1, kind='sc05_refinement_execution_v1',
        purpose='production', output=str(original), schedule=[str(UUID(int=i + 1)) for i in range(199)]))
    inspection = root / 'inspection'; inspection.mkdir()
    result = c.write(inspection / 'RESULT.json', dict(kind='sc05_failed_production_metadata_forensics_v1',
        status='metadata_and_byte_inventory_verified', original_root=str(original),
        freeze_root=str(root / 'freeze'), original_frame=frame))
    (root / 'freeze').mkdir()
    inventory = c.write(inspection / 'ORIGINAL-INVENTORY.json', dict(root=str(original),
        files={'FRAME.json': frame}, directories=[]))
    return c.write(inspection / 'RECEIPT.json', dict(kind='sc05_failed_production_metadata_audit_receipt_v1',
        status='complete', files={'RESULT.json': result, 'ORIGINAL-INVENTORY.json': inventory}))


class PlanTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup); self.root = Path(temp.name).resolve()
        replace = patch.object(c, 'ROOT', self.root); replace.start(); self.addCleanup(replace.stop)
        self.parent = dict(invented_bank(self.root / 'bank'),
                           original_inspection=invented_inspection(self.root / 'parent-metadata'))
        (self.root / 'data').mkdir()
        self.model = dict(model_receipt={}, model_license={}, model_spec={}, model_provenance={
            'weights_sha256': {'invented.gguf': 'a' * 64}, 'runtime_sha256': 'b' * 64},
            interpreter=c.capture(Path(sys.executable).resolve())[0], port=55645, alias='invented')

    def metadata_parent(self):
        return dict(self.parent)

    def test_qualification_identity_must_derive_from_anchored_original_metadata(self):
        self.parent = self.metadata_parent()
        anchor = self.prepare(); value = plan.read(anchor)
        result = c.read(c.read(self.parent['original_inspection'])['files']['RESULT.json'])
        self.assertEqual(value['parent_identity'], plan.previous_contracts.identity(
            result['original_root'], result['original_frame']))
        claim = plan.reserve(anchor)
        bank = invented_bank(self.root / 'replacement-bank')['bank']
        self.parent = dict(self.parent, bank=bank)
        with self.assertRaises(FileExistsError): plan.reserve(self.prepare('replacement-plan'))
        self.assertTrue(Path(claim['path']).is_file())

    def test_free_qualification_identity_is_rejected_without_writes(self):
        self.parent = dict(bank=self.parent['bank'], original_parent_identity='a' * 64)
        with self.assertRaises(ValueError): self.prepare()
        self.assertFalse((self.root / 'data/prepared').exists())

    def test_original_frame_metadata_tampering_cannot_reserve_qualification(self):
        self.parent = self.metadata_parent(); anchor = self.prepare()
        receipt = c.read(self.parent['original_inspection']); report = c.read(receipt['files']['RESULT.json'])
        Path(report['original_frame']['path']).write_bytes(b'{}')
        with self.assertRaises(ValueError): plan.reserve(anchor)
        self.assertFalse(c.authority_registry('fictional_qualification').exists())

    def bank_with_times(self, times):
        bank_path = Path(self.parent['bank']['path']); bank = encode(c.read(self.parent['bank']))
        actor_path = Path(bank['role_files']['contexts']['proof']['path'])
        actors = encode(c.read(bank['role_files']['contexts']['proof']))
        source = dict(source_id='invented:p1', text='Invented result.')
        from hashlib import sha256
        source['sha256'] = sha256(source['text'].encode()).hexdigest()
        actors['cases'][0]['sources'] = [source]
        actor_path.write_bytes(canonical(actors)); bank['role_files']['contexts']['proof'] = encode(c.capture(actor_path)[0])
        ancestry_path = Path(bank['role_files']['ancestry']['proof']['path'])
        ancestry = encode(c.read(bank['role_files']['ancestry']['proof']))
        ancestry['cases'][0]['current_source_available_at_utc'] = times
        ancestry_path.write_bytes(canonical(ancestry)); bank['role_files']['ancestry']['proof'] = encode(c.capture(ancestry_path)[0])
        for phase in c.PHASES:
            slot = bank['slots'][f'actor_cases/{phase}-0000.json']; case = actors['cases'][0]
            raw = dict(case); raw['sources'] = case['sources'] if phase == 'repair' else []
            Path(slot['proof']['path']).write_bytes(canonical(dict(task=phase, **raw)))
            slot['proof'] = encode(c.capture(slot['proof']['path'])[0])
        bank_path.write_bytes(canonical(bank)); self.parent['bank'] = c.capture(bank_path)[0]

    def test_actual_format_source_time_mapping_accepts_complete_per_source_times(self):
        self.bank_with_times({'invented:p1': '2026-11-07T11:00:00+00:00'})
        _, rows, _, _, _ = plan._bank(self.parent)
        self.assertEqual(len(rows[0]['sources']), 1)

    def test_source_time_mapping_rejects_future_missing_extra_and_scalar(self):
        for times in ({'invented:p1': '2026-11-07T13:00:00+00:00'}, {},
                      {'invented:p1': '2026-11-07T11:00:00+00:00', 'other': '2026-11-07T11:00:00+00:00'},
                      {'invented:p1': '2026-11-07T11:00:00'}, '2026-11-07T11:00:00+00:00'):
            self.bank_with_times(times)
            with self.subTest(times=times), self.assertRaises(ValueError): plan._bank(self.parent)

    def prepare(self, name='prepared'):
        return plan.prepare(self.parent, self.root / 'data' / name, qualification_model=self.model)

    def rewrite_plan(self, anchor, value):
        Path(anchor['path']).write_bytes(canonical(value)); changed = c.capture(anchor['path'])[0]
        terminal = Path(anchor['path']).parent / 'COMPLETE.json'
        complete = encode(c.read(c.capture(terminal)[0])); complete['plan'] = changed
        terminal.write_bytes(canonical(complete))
        return changed

    def test_six_complete_pairs_and_no_evaluator_grant(self):
        anchor = self.prepare(); value = plan.read(anchor)
        self.assertEqual(len(value['prepared']), 6)
        closure = c.read(value['source_closure'])
        self.assertFalse(any(Path(p['path']).name == 'EVALUATOR.json' for p in closure['proofs']))
        context = c.read(value['prepared'][0]['context'])
        self.assertEqual(context['control_sha256'], value['prepared'][0]['control_sha256'])
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
        self.parent = dict(self.parent, bank=invented_bank(self.root / 'replacement-bank')['bank'])
        second = self.prepare('replacement-plan')
        with self.assertRaises(FileExistsError): plan.reserve(second)

    def test_resealed_budget_increase_fails_before_reservation(self):
        anchor = self.prepare(); value = encode(c.read(anchor)); value['budgets']['generation_calls'] = 13
        changed = self.rewrite_plan(anchor, value)
        with self.assertRaises(ValueError): plan.reserve(changed)
        self.assertFalse(c.authority_registry('fictional_qualification').exists())

    def test_resealed_omitted_parent_closure_fails_before_reservation(self):
        anchor = self.prepare(); value = encode(c.read(anchor))
        Path(value['source_closure']['path']).write_bytes(canonical(dict(proofs=[], inventories=[])))
        value['source_closure'] = encode(c.capture(value['source_closure']['path'])[0])
        changed = self.rewrite_plan(anchor, value)
        with self.assertRaises(ValueError): plan.reserve(changed)
        self.assertFalse(c.authority_registry('fictional_qualification').exists())

    def test_changed_bank_parent_is_not_authorized_by_old_plan(self):
        anchor = self.prepare()
        (self.root / 'bank/actor_cases/repair-0000.json').write_bytes(b'{}')
        with self.assertRaises(ValueError): plan.reserve(anchor)

    def test_forged_production_cannot_use_six_case_qualification(self):
        anchor = self.prepare(); value = encode(c.read(anchor)); value['purpose'] = 'production'
        changed = self.rewrite_plan(anchor, value)
        with self.assertRaises(ValueError): plan.reserve(changed)

    def test_preparation_failure_is_retained_without_calls_or_authority(self):
        with self.assertRaises(ValueError):
            plan.prepare(self.parent, self.root / 'data/bad', qualification_model={})
        failure = c.read(c.capture(self.root / 'data/bad/FAILURE.json')[0])
        self.assertFalse(failure['model_or_http_execution_performed'])
        self.assertFalse((self.root / 'data/bad/PLAN.json').exists())

    def test_failed_or_missing_preparation_terminal_cannot_reserve_authority(self):
        anchor = self.prepare(); folder = Path(anchor['path']).parent
        terminal = folder / 'COMPLETE.json'; original = terminal.read_bytes()
        terminal.unlink()
        with self.assertRaises((ValueError, FileNotFoundError)): plan.reserve(anchor)
        terminal.write_bytes(original)
        for name in ('FAILURE.json', 'DEADLINE.json', 'FINALIZATION-FAILED.json'):
            marker = folder / name; marker.write_bytes(b'{}')
            with self.subTest(marker=name), self.assertRaises(ValueError): plan.reserve(anchor)
            marker.unlink()
        self.assertFalse(c.authority_registry('fictional_qualification').exists())

    def test_preparation_terminal_must_bind_exact_successful_plan(self):
        anchor = self.prepare(); terminal = Path(anchor['path']).parent / 'COMPLETE.json'
        original = c.read(c.capture(terminal)[0])
        for key, changed in (('status', 'failed'), ('native_calls', 1), ('authority_reserved', True),
                             ('plan', dict(anchor, sha256='f' * 64))):
            value = encode(original); value[key] = changed
            terminal.write_bytes(canonical(value))
            with self.subTest(field=key), self.assertRaises(ValueError): plan.reserve(anchor)
        self.assertFalse(c.authority_registry('fictional_qualification').exists())

    def test_real_finalization_write_failure_leaves_plan_ineligible(self):
        real_write = c.write
        def fail_terminal(path, value):
            if Path(path).name == 'COMPLETE.json': raise OSError('invented terminal publication failure')
            return real_write(path, value)
        with patch.object(c, 'write', side_effect=fail_terminal), self.assertRaises(OSError):
            self.prepare()
        root = self.root / 'data/prepared'
        self.assertTrue((root / 'PLAN.json').is_file())
        self.assertTrue((root / 'FAILURE.json').is_file())
        with self.assertRaises(ValueError): plan.reserve(c.capture(root / 'PLAN.json')[0])
        self.assertFalse(c.authority_registry('fictional_qualification').exists())

    def test_output_outside_data_and_inside_authority_are_rejected(self):
        for output in (self.root / 'outside', c.authority_registry('fictional_qualification') / 'nested'):
            with self.assertRaises(ValueError):
                plan.prepare(self.parent, output, qualification_model=self.model)
            self.assertFalse(output.exists())


if __name__ == '__main__': unittest.main()
