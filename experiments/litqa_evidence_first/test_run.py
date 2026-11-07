"""Controller boundaries over public invented plans, without native execution.

GitHub release verification, process containment and child supervision are
explicitly invented boundaries. Successful-child fixtures do not qualify a real
controller/native/evaluator integration. No prospective control bank is read.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tether_engine.journal import read_chain
from tether_engine.serde import canonical, encode, freeze
from experiments.litqa_refinement import source_evaluation, test_contracts as old_fixtures
from . import contracts as c, model, plan, projection, run as r
from . import test_plan as plan_fixtures, test_release as release_fixtures


class InertWatchdog:
    def __init__(self, end, path):
        self.end, self.path = end, Path(path)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = plan_fixtures.PlanTests('runTest')
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        replace = patch.object(r, 'ROOT', self.root); replace.start(); self.addCleanup(replace.stop)
        self.fixture.model.update(
            model_receipt=c.write(self.root/'invented-model.json', {'scope': 'invented model assets'}),
            model_license=c.write(self.root/'invented-terms.json', {'scope': 'invented terms'}))
        replace = patch.object(r, 'MODEL_RECEIPT', self.fixture.model['model_receipt']['sha256'])
        replace.start(); self.addCleanup(replace.stop)
        self.anchor = self.fixture.prepare()
        self.value = plan.read(self.anchor)
        self.authority = plan.reserve(self.anchor)
        self.claim_root = Path(self.authority['path']).parent/'EXECUTION'
        proposal = c.read(self.fixture.parent['bank'])['decision']
        approval = c.write(self.root/'invented-approval.json', dict(
            kind='tether_evidence_first_owner_approval_v1',
            response='Approve the separate revised-method experiment (Recommended)',
            total_generations_cap=410, production_generations_cap=398, qualification_generations_cap=12,
            provider_cost_usd=0, new_source_http_requests=0, automatic_retry=False,
            old_failed_run_preserved=True, proposal=proposal))
        endpoints = c.write(self.root/'invented-endpoints.json', {'scope': 'metadata only; no keys'})
        original_inputs = c.write(self.root/'invented-original-inputs.json', dict(
            kind='invented_reference_manifest_v1', role='evaluation_only',
            scope='engineering metadata fixture', contains_reference_answers=False))
        protocol = c.write(self.root/'invented-protocol.json', dict(
            schema_version=1, kind='sc05_evidence_first_protocol_v1',
            created_at_utc=datetime.now(timezone.utc).isoformat(), owner_approval=approval,
            original_inspection=self.fixture.parent['original_inspection'], method=self.value['method'],
            bank=self.fixture.parent['bank'], budgets={p: c.budgets(p) for p in c.PURPOSES},
            endpoints=endpoints, original_inputs=original_inputs,
            code_files=self.value['code_files'], automatic_retry=False))
        engineering = c.write(self.root/'invented-engineering.json', dict(
            kind='sc05_evidence_first_engineering_qualification_v1', status='passed',
            code_files=self.value['code_files'], method_identity=self.value['method_identity'],
            model_calls=0, complete_controller_and_independent_evaluation=True,
            fixture_scope='Invented admission metadata, not an actual qualification result'))
        release = c.write(self.root/'invented-release.json', release_fixtures.ci())
        self.output = self.root/'data/execution'
        self.frame = dict(schema_version=1, kind=r.KIND, purpose='fictional_qualification',
            plan=self.anchor, authority=self.authority, code_files=self.value['code_files'],
            protocol=protocol, engineering=engineering, qualification=None, release=release, output=str(self.output))
        self.frame_proof = c.write(self.root/'EXECUTION-FRAME.json', self.frame)
        self.children = []
        self.frame_number = 0

    def new_frame(self, *, output=None, **changes):
        self.frame = dict(self.frame, **changes)
        if output is not None:
            self.output = output; self.frame['output'] = str(output)
        self.frame_number += 1
        self.frame_proof = c.write(self.root/f'FRAME-{self.frame_number:04d}.json', self.frame)
        return self.frame_proof

    def fake_release(self, anchor, pins):
        commit = r.release.validate_ci(c.read(anchor))
        self.assertEqual(pins, self.value['code_files'])
        return freeze(dict(kind='invented_external_release_boundary', commit=commit))

    @contextmanager
    def boundaries(self, *, supervise=None, watchdog=InertWatchdog):
        def failed(command, limits, folder):
            self.children.append((command, limits, folder))
            return SimpleNamespace(returncode=7, stdout=b'', stderr=b'invented child failure', supervision={})

        with patch.object(r, 'contain_process_tree', return_value=object()), \
             patch.object(r, 'DeadlineWatchdog', watchdog), \
             patch.object(r.release, 'verify', side_effect=self.fake_release), \
             patch.object(r, 'model_assets', return_value=(None, {}, self.fixture.model['model_provenance'])), \
             patch.object(r.process_tools, 'supervised', side_effect=supervise or failed):
            yield

    def execute(self):
        return r.execute(self.frame_proof['path'], self.frame_proof['sha256'], output=self.output)

    def authorize_worker(self, *, job_changes=None):
        self.output.mkdir()
        (self.output/'FRAME.json').write_bytes(Path(self.frame_proof['path']).read_bytes())
        self.claim_root.mkdir()
        claim = c.write(self.claim_root/'CLAIM.json', dict(
            frame_sha256=self.frame_proof['sha256'], output=str(self.output), automatic_retry=False))
        folder = self.output/'repair'; folder.mkdir()
        seconds, stage_seconds = r.job_budgets(self.value, 'repair', phase_elapsed=5, outer_elapsed=5)
        job = dict(phase='repair', frame_sha256=self.frame_proof['sha256'],
            input_files=r.grants(self.frame, self.value, 'repair'), model_bindings={}, seconds=seconds,
            stage_seconds=stage_seconds, execution_claim=claim, phase_preflight_seconds=5, outer_preflight_seconds=5)
        if job_changes: job.update(job_changes)
        jp = c.write(folder/'JOB.json', job)
        c.write(self.claim_root/'repair-AUTHORIZED-JOB.json', dict(
            frame_sha256=self.frame_proof['sha256'], job=jp, output=str(folder/'worker')))
        return jp, folder/'worker'

    def invented_admission(self, fp, jp, output, *, seconds):
        self.assertGreater(seconds, 0)
        self.assertLessEqual(seconds, 600)
        frame, job = c.read(fp), c.read(jp)
        self.assertEqual(output, self.output/'repair/admission')
        return r.admission_projection(frame, fp, job, jp, self.value)

    def test_real_plan_preflight_and_admit_with_explicit_invented_external_release(self):
        frame, fp, raw, root, bounds = r.preflight(self.frame_proof['path'], self.frame_proof['sha256'], self.output)
        self.assertEqual(fp, self.frame_proof)
        self.assertEqual(raw, Path(self.frame_proof['path']).read_bytes())
        self.assertEqual(root, self.output)
        self.assertEqual(bounds, c.budgets('fictional_qualification'))
        self.assertFalse(self.output.exists())
        with self.boundaries():
            self.assertEqual(r.admit(frame, self.value)['commit'], 'a'*40)
        self.assertFalse(self.children)
        self.assertFalse(self.claim_root.exists())

    def test_wrong_external_frame_anchor_fails_before_output_or_calls(self):
        with self.boundaries(), self.assertRaises(ValueError):
            r.execute(self.frame_proof['path'], '0'*64, output=self.output)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.children)
        self.assertFalse(self.claim_root.exists())

    def test_preflight_protects_original_bank_and_plan_directories(self):
        # Keep inputs inside the otherwise allowed output area, so rejection
        # reaches the overlap guard rather than the earlier project-root gate.
        parent = dict(plan_fixtures.invented_bank(self.root/'data/protected-bank'),
                      original_inspection=plan_fixtures.invented_inspection(self.root/'data/protected-origin'))
        anchor = plan.prepare(parent, self.root/'data/protected-plan', qualification_model=self.fixture.model)
        authority = plan.reserve(anchor)
        self.new_frame(plan=anchor, authority=authority)
        receipt = c.read(parent['original_inspection'])
        inspected = c.read(receipt['files']['RESULT.json'])
        for protected in (Path(inspected['original_root']), Path(inspected['freeze_root']),
                Path(parent['bank']['path']).parent, Path(anchor['path']).parent, Path(authority['path']).parent):
            with self.subTest(path=protected):
                target = protected/'forbidden-output'
                self.new_frame(output=target)
                self.assertTrue(target.is_relative_to(self.root/'data'))
                with self.assertRaisesRegex(ValueError, 'overlaps immutable inputs'):
                    r.preflight(self.frame_proof['path'], self.frame_proof['sha256'], target)
                self.assertFalse(target.exists())

    def test_phase_and_outer_elapsed_are_charged_without_clock_reset(self):
        self.assertEqual(r.job_budgets(self.value, 'repair', phase_elapsed=10, outer_elapsed=20), (1190, 1100))
        self.assertEqual(r.job_budgets(self.value, 'removal', phase_elapsed=20, outer_elapsed=3400), (140, 50))
        for phase, phase_elapsed, outer_elapsed in [('repair', True, 5), ('repair', -1, 5),
                ('repair', float('nan'), 5), ('repair', 6, 5), ('repair', 1100, 1100),
                ('removal', 0, 3500), ('unknown', 0, 0)]:
            with self.subTest(phase=phase, elapsed=phase_elapsed, outer=outer_elapsed), self.assertRaises(ValueError):
                r.job_budgets(self.value, phase, phase_elapsed=phase_elapsed, outer_elapsed=outer_elapsed)

    def test_worker_grants_exclude_other_member_and_evaluator_files(self):
        for phase, other in (('repair', 'removal'), ('removal', 'repair')):
            granted = {row['path'] for row in r.grants(self.frame, self.value, phase)}
            wanted = {self.anchor['path'], self.authority['path'], self.value['method']['path']}
            wanted.update(row[phase]['path'] for row in self.value['prepared'])
            wanted.update(row['context']['path'] for row in self.value['prepared'])
            self.assertEqual(granted, wanted)
            self.assertFalse(granted & {row[other]['path'] for row in self.value['prepared']})
            self.assertFalse(any(Path(path).name in ('BANK.json', 'ACTOR.json', 'EVALUATOR.json') for path in granted))

    def test_permanent_worker_claim_survives_absent_output_and_blocks_repeat(self):
        jp, output = self.authorize_worker()
        args = (self.output/'FRAME.json', self.frame_proof['sha256'], jp['path'], jp['sha256'], output)
        with patch.object(r, '_admit_supervised', side_effect=self.invented_admission) as admission:
            _, checked, _ = r.worker_preflight(*args)
            self.assertEqual(checked['seconds'], 1195)
            claim = self.claim_root/'repair-WORKER-CLAIM.json'
            original = claim.read_bytes()
            self.assertFalse(output.exists())
            with self.assertRaises(FileExistsError):
                r.worker_preflight(*args)
            self.assertEqual(admission.call_count, 2)
        self.assertEqual(claim.read_bytes(), original)
        self.assertFalse(output.exists())

    def test_resealed_worker_clock_increase_fails_before_permanent_claim(self):
        jp, output = self.authorize_worker(job_changes={'seconds': 1200})
        with self.assertRaisesRegex(ValueError, 'clock'):
            r.worker_preflight(self.output/'FRAME.json', self.frame_proof['sha256'], jp['path'], jp['sha256'], output)
        self.assertFalse((self.claim_root/'repair-WORKER-CLAIM.json').exists())
        self.assertFalse(output.exists())

    def test_failed_or_wrong_separate_admission_cannot_claim_worker(self):
        jp, output = self.authorize_worker()
        args = (self.output/'FRAME.json', self.frame_proof['sha256'], jp['path'], jp['sha256'], output)
        with patch.object(r, '_admit_supervised', side_effect=TimeoutError('invented admission timeout')):
            with self.assertRaises(TimeoutError):
                r.worker_preflight(*args)
        self.assertFalse((self.claim_root/'repair-WORKER-CLAIM.json').exists())
        self.assertFalse(output.exists())
        with patch.object(r, '_admit_supervised', return_value=freeze({'status': 'admitted'})):
            with self.assertRaisesRegex(ValueError, 'trusted admission'):
                r.worker_preflight(*args)
        self.assertFalse((self.claim_root/'repair-WORKER-CLAIM.json').exists())

    def test_source_rich_admission_logic_returns_only_metadata_without_model_dispatch(self):
        jp, output = self.authorize_worker()
        destination = output.parent/'admission/worker'
        with self.boundaries(), patch.object(r, 'model_assets', side_effect=AssertionError('Model load forbidden')):
            result = r.admission_worker(self.output/'FRAME.json', self.frame_proof['sha256'],
                                         jp['path'], jp['sha256'], destination)
        receipt_proof = c.capture(destination/'RECEIPT.json')[0]
        self.assertEqual(result['receipt_sha256'], receipt_proof['sha256'])
        receipt = c.read(receipt_proof)
        report = c.read(receipt['files']['REPORT.json'])
        fp = c.capture(self.output/'FRAME.json')[0]
        self.assertEqual(report, r.admission_projection(freeze(self.frame), fp, c.read(jp), jp, self.value))
        self.assertFalse(report['model_or_http_execution_performed'])
        self.assertFalse(report['scientific_answers_returned'])
        self.assertFalse({'query', 'sources', 'prediction', 'expected_answers'} & set(report))
        self.assertFalse((self.claim_root/'repair-WORKER-CLAIM.json').exists())
        self.assertFalse(self.children)

    def test_failed_child_keeps_claim_and_stops_before_second_phase(self):
        with self.boundaries(), self.assertRaisesRegex(ValueError, 'worker failed'):
            self.execute()
        self.assertEqual(len(self.children), 1)
        self.assertTrue((self.claim_root/'CLAIM.json').is_file())
        self.assertTrue((self.claim_root/'repair-AUTHORIZED-JOB.json').is_file())
        self.assertFalse((self.claim_root/'removal-AUTHORIZED-JOB.json').exists())
        self.assertFalse((self.output/'removal').exists())
        self.assertFalse((self.output/'ROOT-RECEIPT.json').exists())
        failed = c.read(c.capture(self.output/'FAILURE.json')[0])
        self.assertEqual(failed['stage'], 'repair')
        self.assertFalse(failed['automatic_retry'])
        self.assertEqual(read_chain(self.output/'journal.jsonl')[-1]['event'], 'build_failed')
        self.new_frame(output=self.root/'data/replacement-output')
        with self.boundaries(), self.assertRaises(FileExistsError):
            self.execute()
        self.assertEqual(len(self.children), 1)

    def test_interrupted_child_keeps_attempt_and_never_starts_second_phase(self):
        def interrupted(command, limits, folder):
            self.children.append((command, limits, folder))
            raise KeyboardInterrupt('invented supervisor interruption')

        with self.boundaries(supervise=interrupted), self.assertRaises(KeyboardInterrupt):
            self.execute()
        self.assertEqual(len(self.children), 1)
        failure = c.read(c.capture(self.output/'FAILURE.json')[0])
        self.assertEqual(failure['error_type'], 'KeyboardInterrupt')
        self.assertFalse((self.output/'removal').exists())
        self.assertEqual(read_chain(self.output/'journal.jsonl')[-1]['event'], 'build_interrupted')

    def test_supervisor_timeout_preserves_claim_and_stops_remaining_phase(self):
        def timeout(command, limits, folder):
            self.children.append((command, limits, folder))
            raise TimeoutError('invented contained child timeout')

        with self.boundaries(supervise=timeout), self.assertRaises(TimeoutError):
            self.execute()
        self.assertEqual(len(self.children), 1)
        self.assertTrue((self.claim_root/'CLAIM.json').is_file())
        failure = c.read(c.capture(self.output/'FAILURE.json')[0])
        self.assertEqual(failure['error_type'], 'TimeoutError')
        self.assertFalse((self.output/'removal').exists())
        self.assertFalse((self.output/'ROOT-RECEIPT.json').exists())

    def test_journal_failure_cannot_replace_primary_or_suppress_failure_document(self):
        def timeout(command, limits, folder):
            self.children.append((command, limits, folder))
            raise TimeoutError('invented primary worker timeout')

        with self.boundaries(supervise=timeout), \
             patch.object(r.RunJournal, 'fail', side_effect=OSError('invented failure-journal write error')):
            with self.assertRaisesRegex(TimeoutError, 'primary worker timeout') as caught:
                self.execute()
        self.assertEqual(len(self.children), 1)
        self.assertTrue((self.output/'FAILURE.json').is_file())
        self.assertEqual(c.read(c.capture(self.output/'FAILURE.json')[0])['error_type'], 'TimeoutError')
        self.assertTrue(any('OSError' in note for note in caught.exception.__notes__))
        self.assertFalse((self.output/'removal').exists())

    def test_failure_document_write_error_cannot_replace_primary_exception(self):
        def timeout(command, limits, folder):
            self.children.append((command, limits, folder))
            raise TimeoutError('invented primary worker timeout')

        write = r.write

        def fail_document(path, value):
            if Path(path).name == 'FAILURE.json':
                raise PermissionError('invented failure-document write error')
            return write(path, value)

        with self.boundaries(supervise=timeout), patch.object(r, 'write', side_effect=fail_document):
            with self.assertRaisesRegex(TimeoutError, 'primary worker timeout') as caught:
                self.execute()
        self.assertEqual(len(self.children), 1)
        self.assertFalse((self.output/'FAILURE.json').exists())
        self.assertEqual(read_chain(self.output/'journal.jsonl')[-1]['event'], 'build_failed')
        self.assertTrue(any('PermissionError' in note for note in caught.exception.__notes__))
        self.assertFalse((self.output/'removal').exists())

    def test_early_write_failure_retains_request_failure_without_claim_or_child(self):
        write = r.write

        def fail_request(path, value):
            if Path(path).name == 'REQUEST.json':
                raise PermissionError('invented request write failure')
            return write(path, value)

        with self.boundaries(), patch.object(r, 'write', side_effect=fail_request), self.assertRaises(PermissionError):
            self.execute()
        self.assertFalse(self.claim_root.exists())
        self.assertFalse(self.children)
        failure = c.read(c.capture(self.output/'FAILURE.json')[0])
        self.assertEqual(failure['stage'], 'admission')
        self.assertFalse((self.output/'COMPLETE.json').exists())

    def test_admission_time_reduces_first_job_allowance(self):
        real_admit = r.admit
        # This clock changes only at the trusted admission boundary. No sleeping
        # or claimed process timing is used to simulate consumed preflight time.
        current = [1000.0]

        def spent_admit(*args):
            result = real_admit(*args)
            current[0] += 17
            return result

        with self.boundaries(), patch.object(r.time, 'monotonic', side_effect=lambda: current[0]), \
             patch.object(r, 'admit', side_effect=spent_admit), self.assertRaises(ValueError):
            self.execute()
        job = c.read(c.capture(self.output/'repair/JOB.json')[0])
        self.assertEqual(job['phase_preflight_seconds'], 17)
        self.assertEqual(job['outer_preflight_seconds'], 17)
        self.assertEqual(job['seconds'], 1183)
        self.assertEqual(job['stage_seconds'], 1093)

    def invented_successful_child(self, marker=None, *, seal_seconds=.05, worker_seconds=.1):
        def child(command, limits, folder):
            self.children.append((command, limits, folder))
            worker = folder/'worker'; worker.mkdir()
            stage_root = worker/'phase'; stage_root.mkdir()
            stage_receipt = c.write(stage_root/'STAGE-RECEIPT.json',
                                    {'invented_stage': True, 'seal_elapsed_seconds': seal_seconds})
            c.write(worker/'COMPLETE.json', dict(status='complete', phase=folder.name,
                frame_sha256=self.frame_proof['sha256'], audit_denials=0,
                server_terminal={'server_stopped': True}, stage_receipt=stage_receipt, wall_seconds=worker_seconds))
            if marker is not None:
                c.write(worker/marker, {'error_type': 'InventedLateFailure'})
            return SimpleNamespace(returncode=0, stdout=b'', stderr=b'',
                                   supervision={'execution_elapsed_seconds': .2})
        return child

    @staticmethod
    def invented_stage(*args, **kwargs):
        return freeze(dict(config={'seconds': 100}, report={'status': 'complete', 'wall_seconds': .01},
                           seal_elapsed_seconds=.05))

    def contradictory_child_case(self, marker):
        with self.boundaries(supervise=self.invented_successful_child(marker)), \
             patch.object(r, 'validate_success_report'), patch.object(r.stage, 'verify', side_effect=self.invented_stage), \
             self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(len(self.children), 1)
        self.assertFalse((self.output/'ROOT-RECEIPT.json').exists())

    def test_worker_failure_marker_cannot_pass_zero_exit(self):
        self.contradictory_child_case('FAILURE.json')

    def test_worker_deadline_marker_cannot_pass_zero_exit(self):
        self.contradictory_child_case('DEADLINE.json')

    def test_worker_finalization_marker_cannot_pass_zero_exit(self):
        self.contradictory_child_case('FINALIZATION-FAILED.json')

    def test_stage_sealing_cannot_exceed_recorded_worker_elapsed(self):
        with self.boundaries(supervise=self.invented_successful_child(seal_seconds=.15)), \
             patch.object(r, 'validate_success_report'), patch.object(r.stage, 'verify', side_effect=self.invented_stage), \
             self.assertRaisesRegex(ValueError, 'elapsed accounting'):
            self.execute()
        self.assertEqual(len(self.children), 1)
        self.assertFalse((self.output/'ROOT-RECEIPT.json').exists())

    def test_worker_elapsed_cannot_exceed_supervised_execution_elapsed(self):
        with self.boundaries(supervise=self.invented_successful_child(worker_seconds=.3)), \
             patch.object(r, 'validate_success_report'), patch.object(r.stage, 'verify', side_effect=self.invented_stage), \
             self.assertRaisesRegex(ValueError, 'elapsed accounting'):
            self.execute()
        self.assertEqual(len(self.children), 1)
        self.assertFalse((self.output/'ROOT-RECEIPT.json').exists())

    def test_phase_package_write_failure_never_authorizes_second_phase(self):
        write = r.write

        def fail_package(path, value):
            if Path(path).name == 'PACKAGE-RECEIPT.json':
                raise PermissionError('invented phase seal failure')
            return write(path, value)

        with self.boundaries(supervise=self.invented_successful_child()), \
             patch.object(r, 'validate_success_report'), patch.object(r.stage, 'verify', side_effect=self.invented_stage), \
             patch.object(r, 'write', side_effect=fail_package), self.assertRaises(PermissionError):
            self.execute()
        self.assertEqual(len(self.children), 1)
        self.assertTrue((self.claim_root/'CLAIM.json').is_file())
        self.assertTrue((self.output/'repair/worker/COMPLETE.json').is_file())
        self.assertFalse((self.output/'repair-ANCHOR.json').exists())
        self.assertFalse((self.output/'removal').exists())
        self.assertFalse((self.output/'ROOT-RECEIPT.json').exists())
        self.assertEqual(c.read(c.capture(self.output/'FAILURE.json')[0])['stage'], 'repair')


class DispositionTests(unittest.TestCase):
    def test_independent_old_reader_parity_for_both_roles_and_all_terminal_statuses(self):
        query, prior, critic, sources = (old_fixtures.query(), old_fixtures.prior(),
                                         old_fixtures.context(), old_fixtures.sources())
        provenance = dict(weights_sha256={'invented.gguf': 'a'*64}, runtime_sha256='b'*64)
        pair = model.make_pair(query, prior, critic, sources, provenance)
        context = dict(control_sha256=pair['control_sha256'], semantic_support='unevaluated')
        for task in c.PHASES:
            raw = sources if task == 'repair' else ()
            inputs = projection.actor_input(task, query, prior, critic, raw, provenance,
                                            pair[task], pair['control_sha256'])
            predictions = [dict(answer_index=2, evidence_ids=[]), dict(answer_index=0, evidence_ids=[])]
            if task == 'repair':
                predictions.append(dict(answer_index=0, evidence_ids=[sources[0]['source_id']]))
            cases = [('completed', prediction) for prediction in predictions] + [('codec_failure', None), ('capacity', None)]
            for status, prediction in cases:
                with self.subTest(task=task, status=status, prediction=prediction):
                    summary = dict(task=task, status=status, decoded=prediction,
                                   request_sha256=c.fingerprint(pair[task]['request']))
                    decision, disposition = r.decision(inputs, summary, context)
                    independent = source_evaluation.disposition(query, {'summary': summary}, context)
                    self.assertEqual(encode(decision), independent['decision'])
                    self.assertEqual(encode(disposition), independent['disposition'])


if __name__ == '__main__':
    unittest.main()
