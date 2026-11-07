"""Independent-reader engineering controls; no real references or inference."""
from pathlib import Path
import copy
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical, encode
from tether_engine.journal import RunJournal
from tether._process import ProcessLimits
from experiments.litqa_analysis import accepted_primary
from . import plan, reconstruct as r
from . import test_plan as fixtures


class SourceProjectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.PlanTests('runTest'); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def value(self):
        return encode(plan.read(self.fixture.prepare()))

    def test_source_projection_is_independent_and_expectations_remain_closed(self):
        value = self.value(); inputs = accepted_primary._Inputs()
        result = r._source_parent(value, inputs)
        self.assertEqual(len(result['prepared']), 6)
        self.assertIsNone(result['parent'])
        self.assertFalse(any(Path(path).name == 'EVALUATOR.json' for path in inputs.proofs))
        for row in result['prepared']:
            self.assertEqual(row['members']['removal']['sources'], [])
            self.assertEqual(row['members']['repair']['control_sha256'], row['members']['removal']['control_sha256'])
        inputs.unchanged()

    def test_resealed_actor_control_and_payload_substitution_rejected(self):
        value = self.value(); proof = value['prepared'][0]['repair']; path = Path(proof['path'])
        original = path.read_bytes()
        for change in ('control', 'prompt', 'source'):
            actor = r.n.decode(original)
            if change == 'control': actor['control_sha256'] = 'b' * 64
            if change == 'prompt': actor['prepared_member']['payload']['prompt'] = 'Changed prompt'
            if change == 'source': actor['sources'] = [{'source_id': 'injected', 'text': 'invented', 'sha256': r.n.digest(b'invented')}]
            path.write_bytes(canonical(actor))
            altered = copy.deepcopy(value); altered['prepared'][0]['repair'] = encode(plan.c.capture(path)[0])
            with self.subTest(change=change), self.assertRaises(ValueError):
                r._source_parent(altered, accepted_primary._Inputs())
        path.write_bytes(original)

    def test_source_context_and_parent_identity_cannot_be_relabelled(self):
        value = self.value()
        changed = copy.deepcopy(value); changed['parent_identity'] = 'b' * 64
        with self.assertRaises(ValueError): r._source_parent(changed, accepted_primary._Inputs())
        proof = value['prepared'][0]['context']; path = Path(proof['path']); context = r.n.decode(path.read_bytes())
        context['source_scope'] = 'scientifically_validated'
        path.write_bytes(canonical(context)); value['prepared'][0]['context'] = encode(plan.c.capture(path)[0])
        with self.assertRaises(ValueError): r._source_parent(value, accepted_primary._Inputs())

    def test_invented_parent_cannot_authorize_production(self):
        value = self.value(); value['purpose'] = 'production'
        with self.assertRaises(ValueError): r._source_parent(value, accepted_primary._Inputs())


class CapabilityBoundaryTests(unittest.TestCase):
    def test_unissued_or_copied_values_cannot_revalidate_or_open_expectations(self):
        value = r.VerifiedEvidenceFirst('invented', 'a' * 64, {}, {})
        for candidate in (value, copy.copy(value), {}, object()):
            with self.subTest(type=type(candidate).__name__), patch.object(accepted_primary._Inputs, 'json') as read:
                with self.assertRaises(ValueError): r.revalidate(candidate)
                with self.assertRaises(ValueError): r.qualify(candidate)
                read.assert_not_called()

    def test_fictional_history_has_no_actual_prior_usage(self):
        history = r._history(dict(source=dict(parent=None), value=dict(schedule=['invented'])))
        self.assertEqual(history['original_failed_exposure']['actual_prior_model_calls'], 0)
        self.assertEqual(history['original_failed_exposure']['unverified_native'], [])
        self.assertTrue(all(v == 0 for v in history['original_failed_exposure']['physical_totals'].values()))
        self.assertEqual(set(history['reused_prerequisites']), {'critic', 'refinement_collect', 'pair_prepare'})


class TransitiveClosureTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.anchor = self.root / 'anchor.json'; self.anchor.write_bytes(b'{"kind":"invented"}')
        self.authority = self.root / 'authority'; self.authority.mkdir()
        (self.authority / 'CLAIM.json').write_bytes(b'{"retry":false}')
        self.child = accepted_primary._Inputs(); self.child.capture(self.anchor); self.child.inventory(self.authority)
        self.owner = accepted_primary._Inputs()

    def test_consumer_retains_anchor_and_closed_authority_after_child_is_discarded(self):
        r._retain_closure(self.owner, r.original.snapshot(self.child))
        self.owner.unchanged()
        self.anchor.write_bytes(b'{"kind":"changed"}')
        with self.assertRaises(ValueError): self.owner.unchanged()

    def test_added_external_authority_directory_is_detected(self):
        r._retain_closure(self.owner, r.original.snapshot(self.child))
        (self.authority / 'unexpected').mkdir()
        with self.assertRaises(ValueError): self.owner.unchanged()

    def test_changed_child_proof_cannot_be_merged_as_new_authority(self):
        closure = r.original.snapshot(self.child)
        self.anchor.write_bytes(b'{"kind":"changed"}')
        with self.assertRaises(ValueError): r._retain_closure(self.owner, closure)

    def test_qualification_acceptance_must_fall_between_execution_and_production(self):
        controller = dict(reserved_at_utc='2026-11-07T01:00:00+00:00', wall_seconds=10)
        result = r._qualification_chronology('2026-11-07T01:00:11+00:00', '2026-11-07T01:00:12+00:00', controller)
        self.assertIn('not a cryptographic', result['scope'])
        for created, started in (
            ('2026-11-07T01:00:09+00:00', '2026-11-07T01:00:12+00:00'),
            ('2026-11-07T01:00:13+00:00', '2026-11-07T01:00:12+00:00'),
            ('2026-11-07T01:00:11', '2026-11-07T01:00:12+00:00'),
            ('2026-11-07T02:00:11+01:00', '2026-11-07T01:00:12+00:00')):
            with self.subTest(created=created), self.assertRaises(ValueError):
                r._qualification_chronology(created, started, controller)


class OuterProcessTests(unittest.TestCase):
    """Invented process records test the outer reader; no execution is attested."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=r.REPO / 'data/cache'); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve(); self.root = self.base / 'outer'; self.producer = self.root / 'producer'
        self.frame = dict(purpose='fictional_qualification')
        self.fp = self.write(self.base / 'FRAME.json', self.frame)
        self.value = dict(budgets=r._budgets('fictional_qualification'), model=dict(interpreter=dict(path=str(Path(sys.executable).resolve()))))
        self.limits = ProcessLimits(3539, 4 * 1024**2)
        self.command = [self.value['model']['interpreter']['path'], '-I', '-B', '-c', r.LAUNCHER,
            str(r.REPO), str(r.REPO / 'src'), str(r.REPO / 'packages/tether/src'), '--frame', self.fp['path'],
            '--frame-sha256', self.fp['sha256'], '--output', str(self.producer)]
        journal = RunJournal(self.root, kind='build'); self.producer.mkdir()
        pp = self.write(self.producer / 'ROOT-RECEIPT.json', {'invented': True})
        self.descriptor = dict(root=str(self.producer), receipt_sha256=pp['sha256'], controller={})
        self.write(self.root / 'REQUEST.json', dict(frame=self.fp, output=str(self.root), producer_output=str(self.producer), automatic_retry=False))
        self.write(self.root / 'CONFIG.json', dict(kind='sc05_evidence_first_controller_config_v1', frame_sha256=self.fp['sha256'],
            purpose='fictional_qualification', outer_seconds=3600, preflight_seconds=.01, control_reserve_seconds=60, limits=self.limits.payload()))
        self.write(self.root / 'COMMAND.json', self.command)
        supervision = dict(schema_version=1, method='tether.process_envelope.v1', limits=self.limits.payload(), termination_reason='exited',
            process_started=True, process_reaped=True, pipe_eof=dict(stdout=True, stderr=True), cleanup_errors=[],
            observed_counts_are_lower_bounds=False, retained_stdout_bytes=0, observed_stdout_bytes=0,
            retained_stderr_bytes=0, observed_stderr_bytes=0, execution_elapsed_seconds=.3, total_elapsed_seconds=.3)
        self.write(self.root / 'PROCESS.json', dict(returncode=0, supervision=supervision))
        (self.root / 'stdout.bin').write_bytes(b''); (self.root / 'stderr.bin').write_bytes(b'')
        terminal = dict(kind='sc05_evidence_first_controller_terminal_v1', status='complete',
            producer={k:self.descriptor[k] for k in ('root', 'receipt_sha256')}, frame=self.fp, wall_seconds=.5,
            provider_cost_usd=0, automatic_retry=False, scientific_scoring_performed=False)
        self.write(self.root / 'COMPLETE.json', terminal)
        journal.append('evidence_first_controller_reserved', frame=self.fp, command=self.command, limits=self.limits.payload())
        journal.append('evidence_first_controller_completed', terminal_sha256=r.fingerprint(terminal)); journal.close()
        owner = r.n.journal(self.root / 'journal.jsonl')[0]['details']
        self.owner = dict(owner, owner_pid=owner['owner_pid'] + 1)
        self.seal()

    def write(self, path, value):
        path.write_bytes(canonical(value)); return r.native.proof(path)

    def seal(self):
        files = accepted_primary._Inputs().inventory(self.root, omit=('RECEIPT.json',))
        proof = self.write(self.root / 'RECEIPT.json', dict(kind='sc05_evidence_first_controller_receipt_v1', status='complete',
            frame_sha256=self.fp['sha256'], files=files))
        self.descriptor['controller'] = dict(root=str(self.root), receipt_sha256=proof['sha256'])

    def check(self):
        return r._controller(self.descriptor, self.frame, self.fp, self.value, accepted_primary._Inputs(), .2, self.owner)

    def test_complete_invented_outer_process_reconciles(self):
        self.assertEqual(self.check()['status'], 'independently_verified')

    def test_resealed_nonzero_or_unreaped_process_rejected(self):
        original = r.n.load(self.root / 'PROCESS.json')
        for key in ('returncode', 'process_reaped'):
            altered = copy.deepcopy(original)
            if key == 'returncode': altered[key] = 1
            else: altered['supervision'][key] = False
            self.write(self.root / 'PROCESS.json', altered); self.seal()
            with self.subTest(key=key), self.assertRaises(ValueError): self.check()

    def test_outer_failure_extra_directory_and_wrong_command_rejected(self):
        self.write(self.root / 'FAILURE.json', {'failure': True}); self.seal()
        with self.assertRaises(ValueError): self.check()
        (self.root / 'FAILURE.json').unlink(); self.seal(); (self.root / 'extra').mkdir()
        with self.assertRaises(ValueError): self.check()
        (self.root / 'extra').rmdir(); self.write(self.root / 'COMMAND.json', self.command + ['--invented']); self.seal()
        with self.assertRaises(ValueError): self.check()

    def test_controller_lifetime_and_distinct_owner_are_required(self):
        self.owner['owner_pid'] = os.getpid()
        with self.assertRaises(ValueError): self.check()
        self.owner['owner_pid'] += 1
        process = r.n.load(self.root / 'PROCESS.json'); process['supervision']['execution_elapsed_seconds'] = .1
        self.write(self.root / 'PROCESS.json', process); self.seal()
        with self.assertRaises(ValueError): self.check()

    def test_resealed_budget_increase_rejected(self):
        cfg = r.n.load(self.root / 'CONFIG.json'); cfg['limits']['timeout_seconds'] = 3600
        self.write(self.root / 'CONFIG.json', cfg); self.seal()
        with self.assertRaises(ValueError): self.check()


if __name__ == '__main__': unittest.main()
