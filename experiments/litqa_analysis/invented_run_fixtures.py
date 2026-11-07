"""Current-code, entirely invented envelopes for offline regression tests.

The pipelines write genuine current-format source/native artifacts, but every
HTTP body, token sequence, answer, owner PID and supervision record is invented.
No server is started, model executed or network accessed. These fixtures do not
replace the historical actual-model qualification or establish model conformance.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from unittest.mock import patch

from tether_engine.serde import canonical, encode
from experiments.labbench.retrieval import DEFAULT_POLICY
from experiments.litqa_comparison import acquisition, pipeline, replay, qualification_fixtures
from experiments.litqa_comparison.tests.test_replay import ReplayTests
from experiments.litqa_supplied import pipeline as supplied_pipeline, resolver
from experiments.litqa_supplied import qualification_fixtures as supplied_fixtures
from . import envelopes as e


def write(path, value, *, newline=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value) + (b'\n' if newline else b''))


def chain(path, rows):
    previous = None
    events = []
    for ordinal, (event, details) in enumerate(rows):
        value = dict(sequence=ordinal, previous_sha256=previous, event=event, details=details)
        previous = e.digest(canonical(value))
        events.append(dict(value, sha256=previous))
    Path(path).write_bytes(b''.join(canonical(value) + b'\n' for value in events))


class InventedRuns:
    """Own a disposable two-question, five-condition fixture and fake assets."""

    def __init__(self):
        parent = e.REPO / 'data/cache/sc04-invented-current-tests'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.root = Path(self.temp.name).absolute()
        self.native = ReplayTests('runTest')
        self.native.setUp()
        self.queries = qualification_fixtures.queries()
        self.source_queries = [{key: q[key] for key in ('id', 'question')} for q in self.queries]
        self.cutoff = datetime.now(timezone.utc) + timedelta(minutes=1)
        self.primary_path = self.root / 'primary'
        self.supplied_path = self.root / 'supplied'
        try:
            # A forgotten mocking boundary must fail instead of contacting a
            # provider or launching an executable from invented asset bytes.
            with patch.object(socket, 'create_connection', side_effect=AssertionError('No fixture network')), \
                 patch.object(subprocess, 'Popen', side_effect=AssertionError('No fixture processes')):
                self._build()
        except BaseException:
            self.close()
            raise

    def close(self):
        self.native.doCleanups()
        self.temp.cleanup()

    def call(self, task, query, items, output, deadline):
        # Preserve one deliberately unsure candidate so joins and abstention
        # behavior remain covered, without claiming a measured model response.
        original = self.native.f.native_body
        def body(**updates):
            if task == 'answer' and query['id'] == self.queries[1]['id']:
                updates['content'] = canonical(dict(answer_index=1, evidence_ids=[])).decode()
            return original(**updates)
        with patch.object(self.native.f, 'native_body', side_effect=body):
            return self.native.call(task, query, items, output, deadline)

    def _model(self):
        license_path = self.native.f.asset / 'LICENSE.fixture.txt'
        license_path.write_text('Invented model fixture; no model or original publisher license.\n')
        return dict(model_provenance=self.native.info['provenance'], model_spec=self.native.info['spec'],
                    alias=self.native.alias, model_receipt=e.proof(self.native.f.receipt),
                    model_license=e.proof(license_path))

    def _base_frame(self, phases):
        names = ('experiments/litqa_comparison/codecs.py', 'experiments/labbench/tether_adapter.py')
        return dict(purpose='fictional_qualification', automatic_retry=False,
                    fixture_kind='invented_no_inference_no_network_v1', real_model_calls=0, real_http_requests=0,
                    python=e.proof(sys.executable), generation_configuration=encode(pipeline.codecs.CONFIG),
                    policy=encode(DEFAULT_POLICY), phase_seconds={name: 120 for name in phases}, replay_seconds=120,
                    code_pins={name: e.proof(e.REPO / name)['sha256'] for name in names})

    def _build(self):
        inputs = self.root / 'inputs'
        write(inputs / 'answer.json', self.queries)
        write(inputs / 'source.json', self.source_queries)
        model = self._model()
        frame = self._base_frame(e.PRIMARY_PHASES)
        frame.update(model, kind='sc04_primary_execution_v1', count=2, phases=list(e.PRIMARY_PHASES),
                     conditions=list(e.ARMS) + ['supplied_source_pending_separate_execution'],
                     provider_spend_usd=0, schedule=[q['id'] for q in self.queries],
                     query_products=dict(answer_queries=e.proof(inputs / 'answer.json'), source_queries=e.proof(inputs / 'source.json')))
        self.primary_sha = self._run(self.primary_path, frame, primary=True, cutoff=self.cutoff)
        hints = [dict(q, dois=[supplied_fixtures.DOI]) for q in self.source_queries]
        write(inputs / 'hints.json', hints)
        write(inputs / 'dois.json', [supplied_fixtures.DOI])
        supplied = self._base_frame(('collect', 'answer'))
        supplied.update(kind='sc04_supplied_execution_v1', model=model, provider_cost_usd=0, ordinary_retrieval=False,
                        questions=2, unique_dois=1, question_doi_pairs=2,
                        created_at_utc=(self.cutoff + timedelta(seconds=1)).isoformat(),
                        primary_frame=e.proof(self.primary_path / 'FRAME.json'),
                        primary_execution=dict(root=str(self.primary_path), receipt=e.proof(self.primary_path / 'ROOT-RECEIPT.json')),
                        products=dict(answer_queries=e.proof(inputs / 'answer.json'), hints=e.proof(inputs / 'hints.json'),
                                      doi_schedule=e.proof(inputs / 'dois.json')))
        self.supplied_sha = self._run(self.supplied_path, supplied, primary=False, cutoff=self.cutoff + timedelta(seconds=3))

    def _run(self, root, frame, *, primary, cutoff):
        root.mkdir()
        write(root / 'FRAME.json', frame, newline=True)
        frame_sha = e.proof(root / 'FRAME.json')['sha256']
        phases = e.PRIMARY_PHASES if primary else ('collect', 'answer')
        descriptors, parents = {}, {}
        start = self.cutoff - timedelta(seconds=30) if primary else self.cutoff + timedelta(seconds=2)
        events = [('build_reserved', dict(created_at_utc=start.isoformat()))]
        for phase in phases:
            phase_root = root / phase
            worker = phase_root / 'worker'
            worker.mkdir(parents=True)
            stage_root = worker / 'phase'
            names = dict(expand=(), collect=('expand',), rank=('collect',), answer=('collect', 'rank')).get(phase, ()) if primary else ()
            if primary:
                queries = self.queries if phase == 'answer' else self.source_queries
                with patch.object(acquisition.legacy, 'fetch_http', side_effect=qualification_fixtures.fetch):
                    pipeline.execute(phase, queries, stage_root, seconds=120, parents={n: parents[n] for n in names},
                                     policy=DEFAULT_POLICY, cutoff=cutoff, model_provenance=self.native.info['provenance'], call_model=self.call)
                verified = replay.phase(stage_root, e.proof(stage_root / 'STAGE-RECEIPT.json')['sha256'], phase, queries,
                                        parents={n: parents[n] for n in names}, policy=DEFAULT_POLICY,
                                        model_info=self.native.info, cutoff=cutoff)
                parents[phase] = verified['rows']
            elif phase == 'collect':
                with patch.object(resolver.legacy, 'fetch_http', side_effect=supplied_fixtures.fetch):
                    supplied_pipeline.collect([supplied_fixtures.DOI], stage_root, seconds=120, policy=DEFAULT_POLICY)
                parents['collect'] = supplied_pipeline.collection_rows(stage_root, e.proof(stage_root / 'STAGE-RECEIPT.json')['sha256'], [supplied_fixtures.DOI])
            else:
                hints = e.external(frame['products']['hints'])
                supplied_pipeline.answer(self.queries, hints, parents['collect'], root, stage_root, seconds=120,
                                         cutoff=cutoff, model_provenance=self.native.info['provenance'], call_model=self.call)
                supplied_pipeline.replay_answers(stage_root, e.proof(stage_root / 'STAGE-RECEIPT.json')['sha256'],
                                                 self.queries, hints, parents['collect'], root, cutoff=cutoff, model_info=self.native.info)
            descriptors[phase] = self._wrap_phase(root, phase, frame, frame_sha, descriptors, primary, cutoff)
            write(root / (phase + '-ANCHOR.json'), descriptors[phase])
            prefix = '' if primary else 'diagnostic_'
            events += [(prefix + 'phase_started', dict(phase=phase)), (prefix + 'phase_accepted', dict(phase=phase, **descriptors[phase]))]
        complete = dict(status='primary_execution_complete' if primary else 'diagnostic_execution_complete',
                        purpose=frame['purpose'], phases=descriptors, provider_cost_usd=0, sc04_complete=False,
                        scientific_scoring_performed=False, source_cutoff=cutoff.isoformat())
        complete.update(dict(supplied_source_complete=False) if primary else dict(ordinary_retrieval=False))
        write(root / 'COMPLETE.json', complete)
        if primary:
            events.append(('primary_comparison_executed', dict(scientific_scoring_performed=False, supplied_source_complete=False)))
        events.append(('primary_report_sealed' if primary else 'diagnostic_report_sealed', dict(complete_sha256=e.proof(root / 'COMPLETE.json')['sha256'])))
        chain(root / 'journal.jsonl', events)
        write(root / 'ROOT-RECEIPT.json', dict(status=complete['status'], frame_sha256=frame_sha, files=e.inventory(root, recursive=False)))
        return e.proof(root / 'ROOT-RECEIPT.json')['sha256']

    def _wrap_phase(self, root, phase, frame, frame_sha, descriptors, primary, cutoff):
        phase_root, worker = root / phase, root / phase / 'worker'
        stage_proof = e.proof(worker / 'phase/STAGE-RECEIPT.json')
        cache = (e.REPO / 'data/cache' / (('sc04-' if primary else 'sc04-diagnostic-') + root.name + '-' + phase + '-imports')).resolve()
        job = dict(phase=phase, frame_sha256=frame_sha, cutoff=cutoff.isoformat() if phase == 'answer' else None)
        if primary:
            names = dict(expand=(), collect=('expand',), rank=('collect',), answer=('collect', 'rank'))[phase]
            job.update(parents={name: descriptors[name] for name in names}, worker_import_cache=str(cache))
        else:
            job.update(collection=None if phase == 'collect' else descriptors['collect'], common_root=str(root), import_cache=str(cache))
        write(phase_root / 'JOB.json', job)
        write(worker / 'CONFIG.json', dict(job=job, frame_sha256=frame_sha, purpose=frame['purpose']))
        terminal = None if phase == 'collect' else dict(pid=12345, server_stopped=True)
        complete = dict(status='complete', phase=phase, frame_sha256=frame_sha, purpose=frame['purpose'], audit_denials=0,
                        stage_receipt=stage_proof, server_terminal=terminal, worker_memory=dict(process_peak_working_set_bytes=None))
        complete['wall_seconds' if primary else 'worker_wall_seconds'] = .01
        write(worker / 'COMPLETE.json', complete)
        if terminal:
            write(worker / 'MODEL.json', self.native.info)
            write(worker / 'SERVER-RESOURCE-SAMPLES.json', [])
        worker_events = [('build_reserved', {})]
        if terminal:
            worker_events += [('server_started', dict(pid=12345)), ('server_ready', dict(pid=12345)), ('server_terminal', terminal)]
        worker_events.append(('phase_completed', dict(phase=phase, stage_receipt_sha256=stage_proof['sha256'])) if primary else
                             ('diagnostic_phase_completed', dict(complete_sha256=e.proof(worker / 'COMPLETE.json')['sha256'])))
        chain(worker / 'journal.jsonl', worker_events)
        audit = dict(path=str(root / 'FRAME.json'), mode='r', flags=0, allowed=True, basis='explicit_data_or_runtime')
        (worker / 'io-audit.jsonl').write_bytes(canonical(audit) + b'\n')
        report = dict(status='verified', phase=phase, frame_sha256=frame_sha, stage_receipt_sha256=stage_proof['sha256'])
        write(phase_root / 'REPLAY.json', report)
        write(phase_root / 'review/REPORT.json', report)
        chain(phase_root / 'review/journal.jsonl', [('build_reserved', {}), ('replay_completed' if primary else 'diagnostic_replay_completed',
                                                                                dict(report_sha256=e.proof(phase_root / 'review/REPORT.json')['sha256']))])
        driver = e.REPO / ('experiments/litqa_comparison/run.py' if primary else 'experiments/litqa_supplied/run.py')
        for label, command_file in (('execution', 'COMMAND.json'), ('review', 'REVIEW-COMMAND.json')):
            command = [frame['python']['path'], '-I', '-B', '-X', 'pycache_prefix=' + str(cache) + ('-review' if label == 'review' else ''),
                       str(driver), 'review-worker' if label == 'review' else 'worker', '--frame', str(root / 'FRAME.json'),
                       '--frame-sha256', frame_sha, '--job', str(phase_root / 'JOB.json'), '--job-sha256', e.proof(phase_root / 'JOB.json')['sha256'],
                       '--output', str(phase_root / ('review' if label == 'review' else 'worker'))]
            limits = dict(timeout_seconds=120, max_output_bytes=4194304)
            write(phase_root / command_file, dict(command=command, limits=limits))
            for stream in ('stdout', 'stderr'):
                (phase_root / (label + '-' + stream + '.txt')).write_bytes(b'')
            supervision = dict(limits=limits, termination_reason='exited', process_started=True, process_reaped=True,
                               pipe_eof=dict(stderr=True, stdout=True), cleanup_errors=[], observed_counts_are_lower_bounds=False,
                               retained_stdout_bytes=0, observed_stdout_bytes=0, retained_stderr_bytes=0, observed_stderr_bytes=0,
                               execution_elapsed_seconds=.01, total_elapsed_seconds=.01)
            write(phase_root / (label + '-SUPERVISION.json'), dict(returncode=0, supervision=supervision))
        dispatch = dict(phase=phase)
        end = dict(stage_receipt_sha256=stage_proof['sha256'])
        if primary:
            dispatch['job_sha256'] = e.proof(phase_root / 'JOB.json')['sha256']
            end['phase'] = phase
        names = ('phase_worker_dispatch', 'phase_replay_dispatch', 'phase_package_verified') if primary else ('diagnostic_worker_dispatch', 'diagnostic_replay_dispatch', 'diagnostic_phase_verified')
        chain(phase_root / 'journal.jsonl', [('build_reserved', {}), (names[0], dispatch), (names[1], dict(phase=phase)), (names[2], end)])
        write(phase_root / 'PACKAGE-RECEIPT.json', dict(status='complete', phase=phase, frame_sha256=frame_sha, files=e.inventory(phase_root)))
        return dict(root=str(phase_root), package_sha256=e.proof(phase_root / 'PACKAGE-RECEIPT.json')['sha256'], stage_receipt_sha256=stage_proof['sha256'])
