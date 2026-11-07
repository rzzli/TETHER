"""Model-free whole-controller fixture with explicitly invented external systems.

The public unit-test bank is unrelated to the prospective native control bank.
Owned processes, child OS observations, Git transport and native HTTP responses
are invented. Plan, authority, role auditing, source projection, native capture,
stage accounting and independent reconstruction execute their real code. Passing
these tests cannot qualify a real model or attest a real GitHub CI run.
"""
from contextlib import contextmanager
import copy
from datetime import datetime, timedelta, timezone
import io
import inspect
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
from uuid import NAMESPACE_URL, uuid5

from tether import _process
from tether_engine.serde import canonical, encode, parse_json
from experiments.labbench.tests import test_model as native_fixtures
from experiments.labbench.evaluate import evaluate_schedule
from experiments.litqa_refinement.evaluation import endpoint_contract
from . import arithmetic, contracts as c, evaluation, model, plan, reconstruct, release, run as r, supervise, transport
from . import test_plan, test_qualification, test_release
from .test_run import InertWatchdog


def materialize_public_bank(output):
    """Write only the unrelated published engineering fixture, never private data."""
    root = Path(output).resolve(); root.mkdir(); (root/'actor_cases').mkdir()
    bank, documents = test_qualification.invented_bundle()
    for name, raw in documents.items():
        (root/name).write_bytes(raw)
    for role in bank['role_files'].values():
        role['proof'] = encode(c.capture(root/Path(role['proof']['path']).name)[0])
    for name, slot in bank['slots'].items():
        slot['proof'] = encode(c.capture(root/name)[0])
    (root/'DECISION.md').write_bytes(b'Unrelated invented authorization')
    bank['decision'] = encode(c.capture(root/'DECISION.md')[0])
    return c.write(root/'BANK.json', bank)


def process_result(returncode, stdout, stderr, limits, elapsed):
    """Invented OS envelope; elapsed measures the in-process test callback only."""
    supervision = dict(schema_version=1, method='tether.process_envelope.v1', limits=limits.payload(),
        termination_reason='exited', process_started=True, process_reaped=True,
        pipe_eof=dict(stdout=True, stderr=True), cleanup_errors=[], observed_counts_are_lower_bounds=False,
        retained_stdout_bytes=len(stdout), observed_stdout_bytes=len(stdout),
        retained_stderr_bytes=len(stderr), observed_stderr_bytes=len(stderr),
        execution_elapsed_seconds=elapsed, total_elapsed_seconds=elapsed)
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr, supervision=supervision)


def archive_transport(command, *, limits, **kwargs):
    """An invented external Git response containing exact current source bytes."""
    if 'archive' not in command:
        raise AssertionError('Only the declared invented Git archive transport is available')
    started = time.monotonic(); stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
        for item in plan.code_files():
            path = Path(item['path'])
            archive.writestr(path.relative_to(c.ROOT).as_posix(), path.read_bytes())
    return process_result(0, stream.getvalue(), b'', limits, time.monotonic()-started)


@contextmanager
def external_release_transport():
    # These are external byte transports, not replacements for release checking.
    with patch.object(release, 'supervise_command', side_effect=archive_transport), \
         patch.object(_process, 'supervise_command', side_effect=archive_transport):
        yield


class InventedHTTPConnection:
    """Two native routes only; synthesize responses from the public toy passages."""
    calls = None
    alias = 'fictional-mcq'

    def __init__(self, *args, **kwargs):
        self.sock = native_fixtures.Socket(); self.response = None

    def connect(self):
        pass

    def request(self, method, path, *, body, headers):
        if method != 'POST' or path not in ('/tokenize', '/completion'):
            raise AssertionError('No acquisition or extra native endpoint is permitted')
        payload = parse_json(body)
        self.calls.append(dict(method=method, path=path, payload_sha256=c.fingerprint(payload)))
        if path == '/tokenize':
            self.response = native_fixtures.Response(canonical(dict(tokens=list(range(50)))))
            return
        section_text = payload['prompt'].split('<|im_start|>user\n', 1)[1].split('<|im_end|>', 1)[0]
        sections = json.loads(section_text)
        options = sections[1]['indexed_options']; sources = sections[2]['raw_passages']
        unsure = next(row['answer_index'] for row in options if 'Insufficient information' in row['text'])
        answer, citations = unsure, []
        if len(sources) == 1:
            text = sources[0]['text'].lower()
            matches = [row['answer_index'] for row in options
                       if row['text'][4:].lower() in ('increased', 'decreased', 'unchanged')
                       and ('was '+row['text'][4:].lower()+'.') in text]
            if len(matches) != 1:
                raise AssertionError('Only the public instrument fixture is supported')
            answer, citations = matches[0], [sources[0]['source_id']]
        native = dict(prompt=payload['prompt'], model=self.alias, generation_settings=payload,
            content=canonical(dict(answer_index=answer, evidence_ids=citations)).decode(),
            tokens_evaluated=50, tokens_predicted=12, truncated=False, stop=True, stop_type='eos',
            stopped_eos=True, stopped_word=False, stopped_limit=False, stopping_word='')
        self.response = native_fixtures.Response(canonical(native))

    def getresponse(self):
        return self.response

    def close(self):
        pass


class InventedSamples:
    def __init__(self, pid):
        self.values = [dict(monotonic=time.monotonic(), value=None, error_class=None)]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def author_controller(output):
    """Produce a retained six-pair engineering execution with genuine file gates.

    Permanent claims are explicitly fictional and retained in the normal
    fictional-qualification registry. They are never removed or reused. The
    caller owns the fresh output directory and any later independent checks.
    """
    base = Path(output).resolve(); base.mkdir(parents=True, exist_ok=False)
    bank = materialize_public_bank(base/'public-unit-bank')
    parent = dict(bank=bank, original_inspection=test_plan.invented_inspection(base/'original-metadata'))
    fixture = native_fixtures.ModelTests('runTest')

    class RetainedScratch:
        def __init__(self, *args, **kwargs):
            self.name = str(base/'model-assets'); Path(self.name).mkdir()
        def cleanup(self):
            pass

    with patch.object(tempfile, 'TemporaryDirectory', RetainedScratch):
        fixture.setUp()
    license_proof = c.write(fixture.asset/'LICENSE.fixture.txt', {'invented_model': True})
    settings = dict(model_receipt=c.capture(fixture.receipt)[0], model_license=license_proof,
        model_spec=encode(fixture.spec), model_provenance=fixture.model,
        interpreter=c.capture(Path(sys.executable).resolve())[0], port=fixture.spec.port, alias='fictional-mcq')
    anchor = plan.prepare(parent, base/'prepared', qualification_model=settings)
    value = c.read(anchor); authority = plan.reserve(anchor)
    label_root = c.ROOT/'data/benchmark/litqa_evidence_first/test-claim-provenance'
    label_root.mkdir(parents=True, exist_ok=True)
    c.write(label_root/(Path(authority['path']).parent.name+'.json'), dict(
        kind='tether_evidence_first_public_test_claim_v1', purpose='fictional_qualification', test_generated=True,
        authority=authority, fixture_root=str(base), private_prospective_bank_used=False,
        actual_model_calls=0, actual_source_http_requests=0, actual_os_attestation=False,
        permanent_claim_must_not_be_released=True))
    proposal = c.read(bank)['decision']
    approval = c.write(base/'OWNER-APPROVAL.json', dict(kind='tether_evidence_first_owner_approval_v1',
        response='Approve the separate revised-method experiment (Recommended)', total_generations_cap=410,
        production_generations_cap=398, qualification_generations_cap=12, provider_cost_usd=0,
        new_source_http_requests=0, automatic_retry=False, old_failed_run_preserved=True, proposal=proposal,
        scope='Invented engineering authorization, not a real native release'))
    implementation = c.write(base/'IMPLEMENTATION-NOTE.json', {'scope': 'Invented engineering metadata only'})
    addendum = c.write(base/'ENDPOINT-ADDENDUM.json', {'scope': 'Invented prospectively fixed endpoints'})
    endpoints = c.write(base/'ENDPOINTS.json', endpoint_contract('2019-12-31T00:00:00+00:00', implementation, addendum))
    # Separate arbitrary substantive keys exercise scoring, not control success.
    # They are frozen before dispatch and never granted to any worker/actor.
    contexts = c.read(c.read(bank)['role_files']['contexts']['proof'])['cases']
    queries = [item['query'] for item in contexts]
    references = []
    for query in queries:
        unsure = next(i for i, text in enumerate(query['choices']) if 'Insufficient information' in text)
        references.append(dict(id=query['id'], answer_index=next(i for i in range(len(query['choices'])) if i != unsure),
                               unsure_index=unsure))
    original_inputs = c.write(base/'ORIGINAL-INPUTS.json', dict(kind=evaluation.FICTIONAL_INPUT_KIND,
        role='evaluation_only', queries=queries, references=references,
        groups=[[query['id']] for query in queries], annotations={query['id']: [] for query in queries}))
    protocol = c.write(base/'PROTOCOL.json', dict(schema_version=1, kind='sc05_evidence_first_protocol_v1',
        created_at_utc=datetime.now(timezone.utc).isoformat(), owner_approval=approval, original_inspection=parent['original_inspection'],
        method=value['method'], bank=bank, budgets={purpose: c.budgets(purpose) for purpose in c.PURPOSES},
        endpoints=endpoints, original_inputs=original_inputs, code_files=value['code_files'], automatic_retry=False))
    engineering = c.write(base/'ENGINEERING.json', dict(kind='sc05_evidence_first_engineering_qualification_v1',
        status='passed', code_files=value['code_files'], method_identity=value['method_identity'], model_calls=0,
        complete_controller_and_independent_evaluation=True, scope='Invented prerequisite fixture; no actual qualification claim'))
    ci = c.write(base/'INVENTED-CI.json', test_release.ci())
    wrapper = base/'execution'; root = wrapper/'producer'
    frame = dict(schema_version=1, kind=r.KIND, purpose='fictional_qualification', plan=anchor, authority=authority,
        code_files=value['code_files'], protocol=protocol, engineering=engineering, qualification=None, release=ci, output=str(root))
    fp = c.write(base/'FRAME.json', frame)
    audits, calls = [], []
    real_audit = r.RoleAudit

    def audited(**kwargs):
        audit = real_audit(**kwargs); audits.append(audit); return audit

    @contextmanager
    def owner(spec, bindings, *, output, journal, parent_deadline):
        started = time.monotonic()
        terminal = dict(started=True, server_stopped=False, pid=12345, exit_code=None,
                        secondary_failures=[], elapsed_seconds=0, peak_native_memory_bytes=None,
                        peak_native_memory_reason='Invented process boundary; native memory not measured')
        r.write(output/'server-command.json', encode(spec))
        (output/'server.stdout.log').write_bytes(b''); (output/'server.stderr.log').write_bytes(b'')
        journal.append('server_started', pid=12345); journal.append('server_ready', pid=12345)
        obj = SimpleNamespace(spec=spec, bindings=bindings, terminal_record=terminal, assert_ready=lambda: None)
        try:
            yield obj
        finally:
            terminal.update(server_stopped=True, exit_code=0, elapsed_seconds=time.monotonic()-started)
            journal.append('server_terminal', **terminal)

    def supervised(command, limits, folder):
        started = time.monotonic(); folder = Path(folder); stderr = b''; status = 0
        arg = lambda flag: command[command.index(flag)+1]
        try:
            if '--job' not in command:
                with patch.object(os, 'getpid', return_value=900001):
                    r.execute(arg('--frame'), arg('--frame-sha256'), output=arg('--output'))
            elif '--admission' in command:
                phase = Path(arg('--job')).parent.name; index = c.PHASES.index(phase)
                with patch.object(os, 'getpid', return_value=920001+index):
                    r.admission_worker(arg('--frame'), arg('--frame-sha256'), arg('--job'),
                                       arg('--job-sha256'), arg('--output'))
            else:
                phase = Path(arg('--job')).parent.name; index = c.PHASES.index(phase)
                count = len(audits)
                try:
                    with patch.object(os, 'getpid', return_value=910001+index):
                        r.worker(arg('--frame'), arg('--frame-sha256'), arg('--job'),
                                 arg('--job-sha256'), arg('--output'))
                finally:
                    for audit in audits[count:]:
                        audit.active = False; audit.stream.close()
        except BaseException:
            status = 1; stderr = traceback.format_exc().encode()
        result = process_result(status, b'', stderr, limits, time.monotonic()-started)
        (folder/'stdout.bin').write_bytes(result.stdout); (folder/'stderr.bin').write_bytes(result.stderr)
        r.write(folder/'PROCESS.json', dict(returncode=status, supervision=result.supervision))
        return result

    class FixtureHTTP(InventedHTTPConnection):
        pass
    FixtureHTTP.calls = calls
    with external_release_transport(), patch.object(r, 'MODEL_RECEIPT', settings['model_receipt']['sha256']), \
         patch.object(r, 'contain_process_tree', return_value=None), patch.object(r, 'DeadlineWatchdog', InertWatchdog), \
         patch.object(r, 'RoleAudit', side_effect=audited), patch.object(r, 'ProcessSamples', InventedSamples), \
         patch.object(r, 'process_sample', return_value=None), patch.object(r.native_model, 'owned_server', side_effect=owner), \
         patch.object(r.process_tools, 'supervised', side_effect=supervised), \
         patch.object(transport.native, '_check_owner', return_value=12345), \
         patch.object(transport.native, '_watchdog', return_value=native_fixtures.Timer()), \
         patch.object(transport.native.http.client, 'HTTPConnection', FixtureHTTP):
        try:
            descriptor = supervise.launch(fp['path'], fp['sha256'], output=wrapper)
        except BaseException as error:
            if (wrapper/'stderr.bin').is_file():
                error.add_note(str(wrapper/'stderr.bin')+'\n'+(wrapper/'stderr.bin').read_bytes().decode('utf-8', 'replace')[-8000:])
            for phase in c.PHASES:
                for name in ('stderr.bin', 'admission/stderr.bin', 'worker/FAILURE.json', 'admission/worker/FAILURE.json'):
                    path = root/phase/name
                    if path.is_file():
                        error.add_note(str(path)+'\n'+path.read_bytes().decode('utf-8', 'replace')[-8000:])
            raise
    scope = c.write(base/'TEST-SCOPE.json', dict(kind='tether_evidence_first_model_free_integration_fixture_v1',
        descriptor=descriptor, protocol=protocol, plan=anchor, authority=authority, bank=bank,
        actual_model_calls=0, actual_source_http_requests=0, fake_completion_responses=sum(row['path']=='/completion' for row in calls),
        fake_tokenizer_responses=sum(row['path']=='/tokenize' for row in calls),
        external_systems_invented=['native owner', 'HTTP native responses', 'child OS supervision', 'Git/CI transport'],
        prospective_private_bank_read=False, actual_native_qualification=False, scientific_claims=False))
    return dict(descriptor=encode(descriptor), frame=frame, plan=value, protocol=protocol, bank=bank,
                model=settings, scope=scope, calls=calls, root=str(base))


@unittest.skipUnless(os.name == 'nt', 'native held-handle test requires Windows')
class WholeControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cache = (c.ROOT/'data/cache').resolve()
        # Keep successful and failed attempts available for forensic inspection.
        # In particular, their permanent fictional authority must never point at
        # a fixture removed by unittest cleanup.
        retained = Path(tempfile.mkdtemp(prefix='evidence-first-integration-', dir=cache)).resolve()
        cls.fixture = author_controller(retained/'fixture')

    def test_real_controller_and_native_reader_cover_all_twelve_invented_cells(self):
        fixture = self.fixture; root = Path(fixture['descriptor']['root'])
        self.assertEqual(sum(row['path']=='/completion' for row in fixture['calls']), 12)
        self.assertEqual(sum(row['path']=='/tokenize' for row in fixture['calls']), 12)
        self.assertEqual(c.read(c.capture(root/'COMPLETE.json')[0])['new_scheduled'], 12)
        for phase in c.PHASES:
            report = c.read(c.capture(root/phase/'worker/phase/REPORT.json')[0])
            self.assertEqual(report['accounting']['known_totals']['generation_calls'], 6)
            self.assertEqual(report['accounting']['known_totals']['source_http_requests'], 0)
            audit = [parse_json(line) for line in (root/phase/'worker/io-audit.jsonl').read_bytes().splitlines()]
            self.assertFalse(any(row.get('allowed') is False for row in audit))
            actors = [row for row in audit if row.get('event') == 'actor_entered']
            self.assertEqual(len(actors), 6)
            self.assertTrue(all(row['role'] == phase and row['coordinator_inputs_granted'] is False for row in actors))
        with external_release_transport():
            value = reconstruct.reconstruct(fixture['descriptor'])
            self.assertIs(reconstruct.revalidate(value), value)
            qualified = reconstruct.qualify(value)
            self.assertEqual(qualified['status'], 'passed')
            dependencies = {inspect.getsourcefile(evaluate_schedule.__globals__[key]) for key in
                ('freeze', 'evidence_ids', 'validate_prediction', 'validate_query', 'visible_unsure_index')}
            authority = c.write(Path(fixture['root'])/'EVALUATION-AUTHORITY.json', dict(
                kind=evaluation.AUTHORITY_KIND, role='evaluation_only', purpose='fictional_qualification',
                created_at_utc=datetime.now(timezone.utc).isoformat(), producer=fixture['descriptor'],
                native_scorer=c.capture(inspect.getsourcefile(evaluate_schedule))[0],
                native_scorer_dependencies=[c.capture(path)[0] for path in sorted(dependencies)], native_scorer_archive=None,
                **{key: encode(value.envelope[key]) for key in ('baseline_acceptance', 'original_producer_descriptor',
                    'original_inputs', 'endpoint_freeze', 'method', 'protocol')}))
            result = evaluation.evaluate(value, authority, native_scorer=evaluate_schedule)
            self.assertEqual(result['scheduled_count'], 6)
            self.assertEqual(result['publication_component_count'], 6)
            self.assertTrue(result['provenance_validated'])
            self.assertFalse(result['scientific_support_verified'])
            self.assertFalse(result['old_repair_outputs_adopted'])
            self.assertEqual(result['native_agreement']['generated_conditions_checked'], 3)
            self.assertEqual(result['removal_diagnostic']['native']['counts']['correct_and_admitted'], 0)
            evaluator_inputs = c.read(value.envelope['original_inputs'])
            arithmetic.audit_report(result, expected_ids=[q['id'] for q in evaluator_inputs['queries']],
                                    expected_groups=evaluator_inputs['groups'])
            # This comparator exercises only qualification-to-owner binding;
            # it is not a production plan/authority or a scientific execution.
            comparator = dict(fixture['plan'], purpose='production', schedule=[
                str(uuid5(NAMESPACE_URL, 'invented-production-comparator-'+str(i))) for i in range(199)])
            accepted_at = datetime.now(timezone.utc)
            qualification_anchor = c.write(Path(fixture['root'])/'QUALIFICATION-ANCHOR.json', dict(
                kind='sc05_evidence_first_native_qualification_v1', status='passed',
                created_at_utc=accepted_at.isoformat(), execution=fixture['descriptor'], protocol=fixture['protocol']))
            owner_frame = c.write(Path(fixture['root'])/'INVENTED-DERIVED-OWNER.json', dict(
                qualification=qualification_anchor, scope='Metadata-only owner closure; no production authority'))
            owner_inputs = reconstruct.accepted_primary._Inputs()
            owner = owner_inputs.json(encode(owner_frame))
            adopted = reconstruct.accept_qualification(owner['qualification'], comparator, c.read(fixture['protocol']),
                inputs=owner_inputs, production_started_at=(accepted_at+timedelta(seconds=1)).isoformat())
            self.assertEqual(adopted['status'], 'passed')
            owner_closure = reconstruct.original.snapshot(owner_inputs)
            expected_proof = c.read(fixture['bank'])['role_files']['expectations']['proof']
            native_path = root/'repair/worker/phase/products/0000/native/native-response.bin'
            for path in (Path(qualification_anchor['path']), Path(expected_proof['path']), native_path):
                saved = path.read_bytes()
                try:
                    path.write_bytes(saved+b' ')
                    with self.subTest(derived_qualification_path=path.name), self.assertRaises(ValueError):
                        reconstruct.original.verify_snapshot(owner_closure).unchanged()
                finally:
                    path.write_bytes(saved)
            reconstruct.original.verify_snapshot(owner_closure).unchanged()
            with self.assertRaises(ValueError):
                reconstruct.accept_qualification(owner['qualification'], comparator, c.read(fixture['protocol']),
                    inputs=reconstruct.accepted_primary._Inputs(),
                    production_started_at=(accepted_at-timedelta(seconds=1)).isoformat())
            # A copied certificate and changed native bytes must fail before any
            # evaluator reference payload is opened, even after a valid score.
            with patch.object(evaluation, '_inputs') as key_reader:
                with self.assertRaises(ValueError):
                    evaluation.evaluate(copy.copy(value), authority, native_scorer=evaluate_schedule)
                key_reader.assert_not_called()
            raw_path = root/'repair/worker/phase/products/0000/native/native-response.bin'
            original_bytes = raw_path.read_bytes()
            try:
                raw_path.write_bytes(original_bytes+b' ')
                with patch.object(evaluation, '_inputs') as key_reader:
                    with self.assertRaises(ValueError):
                        evaluation.evaluate(value, authority, native_scorer=evaluate_schedule)
                    key_reader.assert_not_called()
            finally:
                raw_path.write_bytes(original_bytes)
            self.assertIs(reconstruct.revalidate(value), value)
            authority_root = Path(fixture['frame']['authority']['path']).parent
            unexpected = authority_root/'UNEXPECTED-TEST-ENTRY'
            try:
                unexpected.mkdir()
                with patch.object(evaluation, '_inputs') as key_reader:
                    with self.assertRaises(ValueError):
                        evaluation.evaluate(value, authority, native_scorer=evaluate_schedule)
                    key_reader.assert_not_called()
            finally:
                unexpected.rmdir()
            self.assertIs(reconstruct.revalidate(value), value)


if __name__ == '__main__':
    unittest.main()
