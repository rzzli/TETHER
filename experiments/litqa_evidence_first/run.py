"""Bounded one-shot controller for the separately frozen evidence-first method.

Every native phase has an exclusive permanent worker claim and an owned process
tree. The trusted coordinator verifies sources; each model actor receives only
its sealed member. Unknown failures stop the run and never release its claims.
"""
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import sys
import time

from tether._process import ProcessLimits, validate_success_report
from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import canonical, encode, freeze, parse_json
from experiments.labbench import model as native_model
from experiments.labbench.native_contract import validate_prediction, visible_unsure_index
from experiments.labbench.runtime import contain_process_tree, DeadlineWatchdog, ProcessSamples, process_sample
from experiments.litqa_comparison.pipeline import proof
from experiments.litqa_comparison.run import inventory
from experiments.litqa_refinement import pipeline as previous_pipeline
from experiments.litqa_refinement import run as process_tools
from experiments.litqa_refinement.access import RoleAudit
from experiments.litqa_refinement_recovery import original
from . import cells, contracts as c, model, plan, release, stage

ROOT = c.ROOT
KIND = 'sc05_evidence_first_execution_v1'
FRAME_FIELDS = {'schema_version', 'kind', 'purpose', 'plan', 'authority', 'code_files',
                'protocol', 'engineering', 'qualification', 'release', 'output'}
LAUNCHER = ('import runpy,sys;sys.path[:0]=sys.argv[1:4];'
            'sys.argv=["tether-evidence-first-worker"]+sys.argv[4:];'
            'runpy.run_module("experiments.litqa_evidence_first.run",run_name="__main__")')
MODEL_RECEIPT = process_tools.MODEL_RECEIPT


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    return c.write(path, value)


def _preserve_failure(root, error, *, stage_name, journal=None, **details):
    """Attempt both records independently without hiding the original failure."""
    if journal is not None and not journal._stream.closed:
        try:
            journal.fail(error, stage_name)
        except BaseException as secondary:
            error.add_note('Failure journal persistence: ' + type(secondary).__name__)
    try:
        write(root / 'FAILURE.json', dict(stage=stage_name, error_type=type(error).__name__,
            message=str(error), automatic_retry=False, **details))
    except BaseException as secondary:
        error.add_note('Failure record persistence: ' + type(secondary).__name__)


def _cleanup(actions):
    """Run every cleanup; secondary failures cannot replace an active error."""
    primary = sys.exc_info()[1]; raised = None
    for label, action in actions:
        try:
            action()
        except BaseException as error:
            if primary is not None:
                primary.add_note(label + ': ' + type(error).__name__)
            elif raised is None:
                raised = error
            else:
                raised.add_note(label + ': ' + type(error).__name__)
    if raised is not None:
        raise raised


def protocol(frame, value):
    """The external frame fixes the owner-approved experiment, not a free ID."""
    declared = c.read(frame['protocol'])
    c.need(set(declared) == {'schema_version', 'kind', 'created_at_utc', 'owner_approval', 'original_inspection',
        'method', 'bank', 'budgets', 'endpoints', 'original_inputs', 'code_files', 'automatic_retry'} and
        type(declared['schema_version']) is int and declared['schema_version'] == 1 and
        declared['kind'] == 'sc05_evidence_first_protocol_v1',
        'Complete prospective protocol required')
    created = datetime.fromisoformat(declared['created_at_utc'])
    c.need(created.utcoffset() == timedelta(0) and created <= datetime.now(timezone.utc),
           'Prospective protocol requires an existing aware UTC declaration')
    reference = declared['original_inputs']
    c.need(set(reference) == {'path', 'sha256', 'bytes'} and
        str(c.path(reference['path'])) == reference['path'] and
        isinstance(reference['sha256'], str) and len(reference['sha256']) == 64 and
        all(char in '0123456789abcdef' for char in reference['sha256']) and
        type(reference['bytes']) is int and reference['bytes'] > 0,
        'Original evaluation-input proof required; answer bytes stay closed')
    c.need(declared['automatic_retry'] is False and declared['code_files'] == frame['code_files'] and
        canonical(declared['budgets']) == canonical({purpose: c.budgets(purpose) for purpose in c.PURPOSES}),
        'Protocol source/scope/clock declaration differs')
    c.need(c.fingerprint(c.read(declared['method'])) == value['method_identity'], 'Protocol method differs')
    inspection = value['parent']['inspection'] if frame['purpose'] == 'production' else value['parent']['original_inspection']
    c.need(declared['original_inspection'] == inspection, 'External original-parent binding differs')
    if frame['purpose'] == 'fictional_qualification':
        c.need(declared['bank'] == value['parent']['bank'], 'Only the prospectively sealed control bank is permitted')
    approval = c.read(declared['owner_approval'])
    c.need(all(type(approval[key]) is int for key in ('total_generations_cap', 'production_generations_cap',
        'qualification_generations_cap', 'new_source_http_requests')) and
        type(approval['provider_cost_usd']) in (int, float) and
        approval['kind'] == 'tether_evidence_first_owner_approval_v1' and
        approval['response'] == 'Approve the separate revised-method experiment (Recommended)' and
        approval['total_generations_cap'] == 410 and approval['production_generations_cap'] == 398 and
        approval['qualification_generations_cap'] == 12 and approval['provider_cost_usd'] == 0 and
        approval['new_source_http_requests'] == 0 and approval['automatic_retry'] is False and
        approval['old_failed_run_preserved'] is True, 'Explicit new-method approval/scope required')
    proposal = c.capture(approval['proposal']['path'], maximum=1024 * 1024)[0]
    c.need(proposal['sha256'] == approval['proposal']['sha256'], 'Approved proposal changed')
    c.need(c.read(declared['bank'])['decision'] == proposal,
           'Control bank must bind the exact owner-approved proposal')
    c.read(declared['endpoints'])  # Frozen metrics contract, never a reference-answer file.
    return declared


def protect_output(frame, value, root, fp):
    """Shared pre-write exclusion for both controller and producer directories."""
    protected = [Path(frame['plan']['path']).parent, Path(frame['authority']['path']).parent]
    parent = value['parent']
    if frame['purpose'] == 'fictional_qualification': protected.append(Path(parent['bank']['path']).parent)
    inspection = parent['inspection'] if frame['purpose'] == 'production' else parent['original_inspection']
    inspected = c.read(inspection); report = c.read(inspected['files']['RESULT.json'])
    protected += [c.path(report['original_root']), c.path(report['freeze_root']), Path(inspection['path']).parent]
    if frame['purpose'] == 'production':
        baseline = parent['baseline_acceptance']
        protected += [c.path(parent['source_archive']['path']).parent, c.path(baseline['replay_root']),
                      c.path(baseline['analyzer_archive']['path']).parent]
    if frame['qualification'] is not None:
        qualification = c.read(frame['qualification'])
        protected += [Path(frame['qualification']['path']).parent,
            c.path(qualification['execution']['root']), c.path(qualification['execution']['controller']['root'])]
    for target in protected:
        c.need(not root.is_relative_to(target) and not target.is_relative_to(root), 'Execution overlaps immutable inputs')
    for item in (fp, frame['protocol'], frame['engineering'], frame['release']):
        c.need(not c.path(item['path']).is_relative_to(root), 'Execution cannot overwrite a gate input')


def preflight(frame_path, expected, output):
    fp, raw = c.capture(c.path(frame_path)); frame = freeze(parse_json(raw))
    c.need(fp['sha256'] == expected and set(frame) == FRAME_FIELDS and
        type(frame['schema_version']) is int and frame['schema_version'] == 1 and frame['kind'] == KIND,
        'Externally anchored evidence-first frame required')
    c.need(frame['purpose'] in c.PURPOSES, 'Explicit execution purpose')
    root = c.path(output)
    c.need(root == c.path(frame['output']) and root != ROOT / 'data' and root.is_relative_to(ROOT / 'data') and
        root.parent.is_dir() and not root.exists(), 'Fresh project data execution directory required')
    value = c.read(frame['plan'])
    c.need(value['kind'] == plan.KIND and value['purpose'] == frame['purpose'] and
        canonical(value['budgets']) == canonical(c.budgets(frame['purpose'])), 'Metadata-only execution caps')
    protect_output(frame, value, root, fp)
    return frame, fp, raw, root, value['budgets']


def admit(frame, value):
    c.need(value['code_files'] == frame['code_files'] == plan.code_files(), 'Exact current source closure required')
    c.need(value['model']['interpreter'] == c.capture(Path(sys.executable).resolve())[0], 'Pinned interpreter differs')
    c.need(value['model']['model_receipt']['sha256'] == MODEL_RECEIPT, 'Pinned model receipt differs')
    declared = protocol(frame, value)
    engineering = c.read(frame['engineering'])
    c.need(engineering['kind'] == 'sc05_evidence_first_engineering_qualification_v1' and
        engineering['status'] == 'passed' and engineering['code_files'] == frame['code_files'] and
        engineering['method_identity'] == value['method_identity'] and engineering['model_calls'] == 0 and
        engineering['complete_controller_and_independent_evaluation'] is True,
        'Full model-free controller/evaluator qualification required')
    released = release.verify(frame['release'], frame['code_files'])
    if frame['purpose'] == 'production':
        c.need(frame['qualification'] is not None, 'Production requires the complete twelve-call native gate')
        # This independent boundary must exist and pass; a status-only receipt
        # cannot grant production. No fallback to producer summaries is allowed.
        from .reconstruct import accept_qualification
        reserved = read_chain(c.path(frame['output']) / 'journal.jsonl')[0]
        c.need(reserved['event'] == 'build_reserved', 'Actual production reservation required')
        accept_qualification(frame['qualification'], value, declared,
            production_started_at=reserved['details']['created_at_utc'])
    else:
        c.need(frame['qualification'] is None, 'Fresh native controls cannot inherit a prior qualification')
    return released


def job_budgets(value, phase, *, phase_elapsed, outer_elapsed):
    spent = c.finite(phase_elapsed, 'phase preflight time'); outer = c.finite(outer_elapsed, 'outer elapsed')
    c.need(phase in c.PHASES and spent <= outer, 'Enclosing phase/outer chronology')
    seconds = int(min(value['budgets']['phase_seconds'][phase] - spent,
                      value['budgets']['outer_seconds'] - outer - 60))
    allowance = seconds - 90
    if phase == 'repair': allowance = min(allowance, value['budgets']['repair_stage_seconds'])
    c.need(seconds > 120 and allowance > 0, 'No bounded phase time remains after verification/cleanup')
    return seconds, allowance


def grants(frame, value, phase):
    entries = [frame['plan'], frame['authority'], value['method'], *[
        item for row in value['prepared'] for item in (row[phase], row['context'])]]
    result = {}
    for item in entries:
        c.need(item['path'] not in result, 'Duplicate coordinator grant')
        result[item['path']] = item
    return freeze([result[key] for key in sorted(result)])


def model_assets(settings):
    spec, bindings, provenance = native_model.make_server_spec(settings['model_receipt']['path'],
        settings['model_receipt']['sha256'], port=settings['port'], alias=settings['alias'], startup_seconds=180)
    c.need(canonical(spec) == canonical(settings['model_spec']) and provenance == settings['model_provenance'],
           'Pinned model assets/configuration differ')
    c.capture(settings['model_license']['path'], settings['model_license'])
    return spec, bindings, provenance


def decision(inputs, summary, context):
    c.need(context['control_sha256'] == inputs['control_sha256'], 'Source/control admission binding differs')
    task = inputs['task']; query = inputs['query']
    if summary['status'] != 'completed':
        return None, freeze(dict(id=query['id'], producer_status='parse_failure' if summary['status'] == 'codec_failure'
            else 'input_unavailable', check_status='not_run', prediction=None, reason=summary['status']))
    member = inputs['prepared_member']
    c.need(summary['request_sha256'] == c.fingerprint(member['request']), 'Actual bound request differs')
    model.validate_binding(member['request'], member['payload'])
    pred = validate_prediction(summary['decoded'], query, [row['source_id'] for row in inputs['sources']])
    accepted = pred['answer_index'] == visible_unsure_index(query) or bool(pred['evidence_ids'])
    mechanical = not accepted and task == 'removal'
    reason = None if accepted else ('raw_source_removal_mechanically_rejects_substantive_answer' if mechanical else
                                    'Substantive answer requires current admitted raw evidence')
    checked = freeze(dict(accepted=accepted, reason=reason, prediction=pred, task=task,
        request_sha256=summary['request_sha256'], context_sha256=c.fingerprint(context),
        control_sha256=inputs['control_sha256'], raw_removal_mechanical_rejection=mechanical,
        semantic_support='unevaluated'))
    return checked, freeze(dict(id=query['id'], producer_status='produced',
        check_status='accepted' if accepted else 'rejected', prediction=pred, reason=reason))


def operation(slot, end, *, entry, root, owner, audit, alias):
    deadline = min(end, time.monotonic() + 120)
    phase = slot['phase']; inputs = c.read(entry[phase]); context = c.read(entry['context'])
    c.need(inputs['task'] == phase and inputs['query']['id'] == slot['id'] == entry['id'] and
        slot['ordinal'] == entry['ordinal'], 'Exact scheduled actor binding')
    with audit.actor(phase, root):
        result = cells.call_pair_member(inputs['query'], inputs['candidate_context'], inputs['critique_context'],
            inputs['sources'], inputs['model_provenance'], inputs['prepared_member'], phase,
            control_sha256=inputs['control_sha256'], owner=owner, output=root, deadline=deadline,
            alias=alias, execution_id=slot['execution_id'])
    descriptor = dict(task=phase, query=inputs['query'], prior=inputs['candidate_context'],
        critic=inputs['critique_context'], sources=inputs['sources'], model_provenance=inputs['model_provenance'],
        execution_id=slot['execution_id'], prepared_member=inputs['prepared_member'], control_sha256=inputs['control_sha256'])
    call, usage, native_proof = previous_pipeline._model_result(result, descriptor, root, deadline)
    checked, disposition = decision(inputs, call['summary'], context)
    terminal = write(root / 'DECISION.json', checked)
    c.need(time.monotonic() < deadline, 'Cell admission exceeded its bounded deadline')
    return dict(status=call['summary']['status'], reason=None if call['summary']['status'] == 'completed' else call['summary']['status'],
        accounting=usage, product=dict(call=call, native_proof=native_proof, disposition=disposition, decision=terminal,
        paired_member_sha256=c.fingerprint(inputs['prepared_member']), control_sha256=inputs['control_sha256'],
        source_context_sha256=c.fingerprint(context)))


def worker_preflight(frame_path, frame_sha, job_path, job_sha, output):
    started = time.monotonic()
    fp, raw = c.capture(c.path(frame_path)); jp, body = c.capture(c.path(job_path))
    c.need(fp['sha256'] == frame_sha and jp['sha256'] == job_sha, 'Worker external frame/job anchors')
    frame = freeze(parse_json(raw)); job = freeze(parse_json(body)); value = c.read(frame['plan'])
    c.need(set(frame) == FRAME_FIELDS and frame['kind'] == KIND and frame['schema_version'] == 1,
           'Worker frame identity differs')
    phase = job['phase']; root = c.path(frame['output']); out = c.path(output)
    c.need(phase in c.PHASES and Path(frame_path) == root / 'FRAME.json' and Path(job_path) == root / phase / 'JOB.json'
        and out == root / phase / 'worker' and not out.exists(), 'Exact fresh worker paths')
    c.need(set(job) == {'phase', 'frame_sha256', 'input_files', 'model_bindings', 'seconds', 'stage_seconds',
        'execution_claim', 'phase_preflight_seconds', 'outer_preflight_seconds'}, 'Exact worker job fields')
    c.need(job['frame_sha256'] == frame_sha and value['purpose'] == frame['purpose'] and
        (job['seconds'], job['stage_seconds']) == job_budgets(value, phase,
            phase_elapsed=job['phase_preflight_seconds'], outer_elapsed=job['outer_preflight_seconds']),
        'Worker cannot reset carried phase clocks')
    c.schedule(value['schedule'], value['purpose'])
    c.need(value['code_files'] == frame['code_files'] == plan.code_files() and
        job['input_files'] == grants(frame, value, phase), 'Exact worker code/input grants differ')
    authority = c.read(frame['authority']); claim = c.read(job['execution_claim'])
    key = c.identity(value['parent_identity'], value['method_identity'])
    location = c.authority_registry(frame['purpose']) / key
    c.need(Path(frame['authority']['path']) == location / 'AUTHORITY.json' and authority['plan'] == frame['plan'] and
        authority['identity'] == key and authority['parent_identity'] == value['parent_identity'] and
        authority['method_identity'] == value['method_identity'] and authority['permanent'] is True and
        authority['automatic_retry'] is False and authority['schedule'] == value['schedule'] and
        canonical(authority['budgets']) == canonical(c.budgets(frame['purpose'])), 'Permanent worker authority differs')
    execution = location / 'EXECUTION'
    c.need(Path(job['execution_claim']['path']) == execution / 'CLAIM.json' and
        claim == freeze(dict(frame_sha256=frame_sha, output=str(root), automatic_retry=False)), 'Execution claim differs')
    approval = c.read(c.capture(execution / (phase + '-AUTHORIZED-JOB.json'))[0])
    c.need(approval == freeze(dict(frame_sha256=frame_sha, job=jp, output=str(out))), 'Phase authorization differs')
    c.need(value['model']['interpreter'] == c.capture(Path(sys.executable).resolve())[0], 'Worker interpreter differs')
    remaining = job['seconds'] - (time.monotonic() - started)
    seconds = min(3600 if frame['purpose'] == 'production' else 600, remaining - 390)
    c.need(seconds > 0, 'No admission time after startup/cleanup/minimum-call reserves')
    admitted = _admit_supervised(fp, jp, root / phase / 'admission', seconds=seconds)
    c.need(admitted == admission_projection(frame, fp, job, jp, value), 'Separate trusted admission differs')
    # A moved worker output cannot make this exclusive external claim reusable.
    write(execution / (phase + '-WORKER-CLAIM.json'), dict(frame_sha256=frame_sha,
        job_sha256=job_sha, output=str(out), owner_pid=os.getpid()))
    return frame, job, value


def admission_projection(frame, fp, job, jp, value):
    return freeze(dict(kind='sc05_evidence_first_worker_admission_v1', status='admitted',
        frame=fp, job=jp, plan=frame['plan'], authority=frame['authority'], protocol=frame['protocol'],
        engineering=frame['engineering'], qualification=frame['qualification'], release=frame['release'],
        parent_identity=value['parent_identity'], method_identity=value['method_identity'],
        schedule=value['schedule'], budgets=value['budgets'], phase=job['phase'],
        model_or_http_execution_performed=False, scientific_answers_returned=False))


def admission_worker(frame_path, frame_sha, job_path, job_sha, output):
    """Source-rich isolated child; returns metadata only and never starts a model."""
    fp, raw = c.capture(c.path(frame_path)); jp, body = c.capture(c.path(job_path))
    c.need(fp['sha256'] == frame_sha and jp['sha256'] == job_sha, 'Admission external anchors')
    frame = freeze(parse_json(raw)); job = freeze(parse_json(body))
    c.need(set(frame) == FRAME_FIELDS and frame['kind'] == KIND and frame['schema_version'] == 1 and
        job['phase'] in c.PHASES and job['frame_sha256'] == frame_sha, 'Admission scope/identity')
    destination = c.path(frame['output']); phase = job['phase']
    c.need(Path(frame_path) == destination / 'FRAME.json' and Path(job_path) == destination / phase / 'JOB.json' and
        c.path(output) == destination / phase / 'admission/worker', 'Exact isolated admission paths')
    journal = RunJournal(Path(output), kind='build'); root = journal.output
    try:
        write(root / 'REQUEST.json', dict(frame=fp, job=jp, role='trusted_parent_admission',
            model_or_http_execution_performed=False, scientific_answers_returned=False))
        value, _ = plan.verify_authority(frame['plan'], frame['authority'])
        c.need(job['input_files'] == grants(frame, value, phase) and
            (job['seconds'], job['stage_seconds']) == job_budgets(value, phase,
                phase_elapsed=job['phase_preflight_seconds'], outer_elapsed=job['outer_preflight_seconds']),
            'Admission exact source-only grants and carried clocks')
        released = admit(frame, value)
        write(root / 'RELEASE-VERIFICATION.json', released)
        report = admission_projection(frame, fp, job, jp, value)
        write(root / 'REPORT.json', report)
        c.capture(fp['path'], fp); c.capture(jp['path'], jp)
        c.need(plan.code_files() == frame['code_files'], 'Admission source closure changed')
        journal.append('evidence_first_worker_admitted', report_sha256=c.fingerprint(report)); journal.close()
        receipt = write(root / 'RECEIPT.json', dict(kind='sc05_evidence_first_admission_receipt_v1',
            status='admitted', files=inventory(root, omit=('RECEIPT.json',))))
        return freeze(dict(root=str(root), receipt_sha256=receipt['sha256']))
    except BaseException as error:
        _preserve_failure(root, error, stage_name='trusted_parent_admission', journal=journal,
                          model_or_http_execution_performed=False)
        raise
    finally: _cleanup([('Admission journal close', journal.close)])


def _admit_supervised(fp, jp, output, *, seconds):
    root = c.path(output); root.mkdir(exist_ok=False)
    command = [str(sys.executable), '-I', '-B', '-c', LAUNCHER, str(ROOT), str(ROOT / 'src'),
        str(ROOT / 'packages/tether/src'), '--admission', '--frame', fp['path'], '--frame-sha256', fp['sha256'],
        '--job', jp['path'], '--job-sha256', jp['sha256'], '--output', str(root / 'worker')]
    limits = ProcessLimits(seconds, 4 * 1024 ** 2); write(root / 'COMMAND.json', command)
    try:
        result = process_tools.supervised(command, limits, root)
        c.need(result.returncode == 0, 'Separate source admission failed; no model dispatch')
        validate_success_report(result.supervision, limits, len(result.stdout), len(result.stderr))
        rp = c.capture(root / 'worker/RECEIPT.json')[0]; receipt = c.read(rp)
        c.need(set(receipt) == {'kind', 'status', 'files'} and receipt['kind'] == 'sc05_evidence_first_admission_receipt_v1'
            and receipt['status'] == 'admitted' and canonical(receipt['files']) ==
            canonical(inventory(root / 'worker', omit=('RECEIPT.json',))), 'Exact separate admission receipt')
        c.need(not any((root / 'worker' / name).exists() for name in ('FAILURE.json', 'DEADLINE.json')),
               'Failed admission cannot authorize a model worker')
        report = c.read(receipt['files']['REPORT.json'])
        c.need(report['frame'] == fp and report['job'] == jp and report['model_or_http_execution_performed'] is False
            and report['scientific_answers_returned'] is False, 'Source admission result role/identity')
        write(root / 'COMPLETE.json', dict(status='admitted', receipt=rp, frame=fp, job=jp,
            model_or_http_execution_performed=False))
        return report
    except BaseException as error:
        _preserve_failure(root, error, stage_name='supervised_admission',
                          model_or_http_execution_performed=False)
        raise


def worker(frame_path, frame_sha, job_path, job_sha, output):
    started = time.monotonic()
    frame, job, value = worker_preflight(frame_path, frame_sha, job_path, job_sha, output)
    journal = RunJournal(Path(output), kind='build'); root = journal.output
    owner = audit = watchdog = current = handle = None
    try:
        end = started + job['seconds']; phase = job['phase']; settings = value['model']
        handle = contain_process_tree(); watchdog = DeadlineWatchdog(end, root / 'DEADLINE.json'); watchdog.__enter__()
        write(root / 'CONFIG.json', dict(frame_sha256=frame_sha, job_sha256=job_sha, phase=phase,
            purpose=frame['purpose'], worker_pid=os.getpid(), python_version=sys.version, coordinator_grants=job['input_files']))
        audit = RoleAudit(inputs=[frame_path, job_path, settings['model_receipt']['path'], settings['model_license']['path'],
            *[p['path'] for p in job['input_files']]], code_files=[p['path'] for p in frame['code_files']],
            runtime_roots=(sys.prefix, sys.base_prefix), model_files=list(job['model_bindings'].values()), output=root)
        audit.activate()
        for item in job['input_files']: c.capture(item['path'], item)
        spec, bindings, provenance = model_assets(settings)
        c.need({key: str(path) for key, path in bindings.items()} == dict(job['model_bindings']), 'Native file bindings differ')
        write(root / 'MODEL.json', dict(spec=encode(spec), bindings={key: str(path) for key, path in bindings.items()},
            provenance=provenance, alias=settings['alias']))
        (root / 'server').mkdir()
        with native_model.owned_server(spec, bindings, output=root / 'server', journal=journal, parent_deadline=end - 40) as owner:
            current = stage.Stage(value['schedule'], phase, root / 'phase', purpose=frame['purpose'],
                seconds=min(job['stage_seconds'], end - time.monotonic() - 90))
            write(current.root / 'INPUTS.json', dict(plan=frame['plan'], phase=phase, cutoff=value['cutoff'],
                method_identity=value['method_identity'], reference_keys_available=False, scoring_performed=False))
            with ProcessSamples(owner.terminal_record['pid']) as samples:
                for entry in value['prepared']:
                    current.call(lambda slot, deadline: operation(slot, deadline, entry=entry,
                        root=current.root / 'products' / f'{slot["ordinal"]:04d}', owner=owner, audit=audit, alias=settings['alias']))
                report = current.finish()
            write(root / 'SERVER-RESOURCE-SAMPLES.json', samples.values)
        audit.flush()
        c.need(owner.terminal_record['server_stopped'] is True and report['status'] == 'complete' and
            audit.denials == 0 and time.monotonic() < end, 'Worker failed cleanup/coverage/time/access')
        c.need(plan.code_files() == frame['code_files'], 'Worker code changed during execution')
        terminal = dict(status='complete', phase=phase, purpose=frame['purpose'], frame_sha256=frame_sha,
            stage_receipt=proof(root / 'phase/STAGE-RECEIPT.json'), wall_seconds=time.monotonic() - started,
            worker_memory=process_sample(os.getpid()), server_terminal=encode(owner.terminal_record), audit_denials=audit.denials,
            provider_cost_usd=0, reference_keys_read=False, scientific_scoring_performed=False)
        write(root / 'COMPLETE.json', terminal)
        journal.append('refinement_worker_completed', terminal_sha256=c.fingerprint(terminal))
        return freeze(terminal)
    except BaseException as error:
        if current is not None and not current.closed:
            try: current.finish()
            except BaseException as secondary: error.add_note('Partial stage persistence: ' + type(secondary).__name__)
        _preserve_failure(root, error, stage_name='evidence_first_worker', journal=journal,
            wall_seconds=time.monotonic() - started, server_terminal=None if owner is None else encode(owner.terminal_record))
        raise
    finally:
        actions = [('Worker journal close', journal.close)]
        if audit is not None: actions.insert(0, ('Worker audit flush', audit.flush))
        if watchdog is not None: actions.append(('Worker watchdog close', lambda: watchdog.__exit__(None, None, None)))
        _cleanup(actions)
        _ = handle


def execute(frame_path, expected, *, output):
    started = time.monotonic(); frame, fp, raw, root, bounds = preflight(frame_path, expected, output)
    journal = RunJournal(root, kind='build'); phases = {}; accepted = {}
    watchdog = phase_watchdog = handle = None; current = 'admission'
    try:
        write(root / 'REQUEST.json', dict(frame=fp, output=str(root), automatic_retry=False))
        (root / 'FRAME.json').write_bytes(raw)
        handle = contain_process_tree(); end = started + bounds['outer_seconds']
        watchdog = DeadlineWatchdog(end, root / 'DEADLINE.json'); watchdog.__enter__()
        phase_watchdog = DeadlineWatchdog(started + bounds['phase_seconds']['repair'], root / 'repair-DEADLINE.json')
        phase_watchdog.__enter__()
        value, _ = plan.verify_authority(frame['plan'], frame['authority'])
        released = admit(frame, value)
        write(root / 'RELEASE-VERIFICATION.json', released)
        execution = Path(frame['authority']['path']).parent / 'EXECUTION'; execution.mkdir(exist_ok=False)
        claim = write(execution / 'CLAIM.json', dict(frame_sha256=expected, output=str(root), automatic_retry=False))
        journal.append('evidence_first_admitted', plan=frame['plan'], authority=frame['authority'], execution_claim=claim)
        _, bindings, _ = model_assets(value['model'])
        for phase in c.PHASES:
            current = phase; phase_started = started if phase == 'repair' else time.monotonic()
            if phase == 'removal':
                phase_watchdog = DeadlineWatchdog(phase_started + bounds['phase_seconds'][phase], root / 'removal-DEADLINE.json')
                phase_watchdog.__enter__()
            folder = root / phase; folder.mkdir(); now = time.monotonic()
            phase_elapsed = now - phase_started; outer_elapsed = now - started
            seconds, stage_seconds = job_budgets(value, phase, phase_elapsed=phase_elapsed, outer_elapsed=outer_elapsed)
            job = dict(phase=phase, frame_sha256=expected, input_files=grants(frame, value, phase),
                model_bindings={key: str(path) for key, path in bindings.items()}, seconds=seconds, stage_seconds=stage_seconds,
                execution_claim=claim, phase_preflight_seconds=phase_elapsed, outer_preflight_seconds=outer_elapsed)
            jp = write(folder / 'JOB.json', job)
            write(execution / (phase + '-AUTHORIZED-JOB.json'), dict(frame_sha256=expected, job=jp, output=str(folder / 'worker')))
            command = [str(sys.executable), '-I', '-B', '-c', LAUNCHER, str(ROOT), str(ROOT / 'src'),
                str(ROOT / 'packages/tether/src'), '--worker', '--frame', str(root / 'FRAME.json'), '--frame-sha256', expected,
                '--job', jp['path'], '--job-sha256', jp['sha256'], '--output', str(folder / 'worker')]
            limits = ProcessLimits(seconds, 4 * 1024 ** 2); write(folder / 'COMMAND.json', command)
            journal.append('evidence_first_phase_reserved', phase=phase, job=jp, command=command, limits=limits.payload())
            result = process_tools.supervised(command, limits, folder)
            c.need(result.returncode == 0, 'Phase worker failed; automatic replay is forbidden')
            validate_success_report(result.supervision, limits, len(result.stdout), len(result.stderr))
            terminal = c.read(proof(folder / 'worker/COMPLETE.json'))
            c.need(terminal['status'] == 'complete' and terminal['phase'] == phase and terminal['frame_sha256'] == expected and
                terminal['audit_denials'] == 0 and terminal['server_terminal']['server_stopped'] is True,
                'Child completion/cleanup differs')
            c.need(not any((folder / 'worker' / name).exists() for name in
                ('FAILURE.json', 'DEADLINE.json', 'FINALIZATION-FAILED.json')), 'Worker failure marker dominates completion')
            c.need(Path(terminal['stage_receipt']['path']) == folder / 'worker/phase/STAGE-RECEIPT.json' and
                terminal['stage_receipt'] == proof(folder / 'worker/phase/STAGE-RECEIPT.json'), 'Exact child stage receipt')
            stage_receipt = c.read(terminal['stage_receipt'])
            checked = stage.verify(folder / 'worker/phase', terminal['stage_receipt']['sha256'],
                expected_ids=value['schedule'], expected_phase=phase, purpose=value['purpose'], deadline=end)
            c.need(checked['report']['status'] == 'complete' and checked['config']['seconds'] <= stage_seconds and
                checked['report']['wall_seconds'] <= stage_receipt['seal_elapsed_seconds'] <= terminal['wall_seconds']
                <= result.supervision['execution_elapsed_seconds'] and terminal['wall_seconds'] < seconds,
                'Stage/worker/process elapsed accounting differs')
            c.need(plan.code_files() == frame['code_files'], 'Code changed before phase sealing')
            elapsed = time.monotonic() - phase_started
            c.need(elapsed < bounds['phase_seconds'][phase], 'Entire phase exceeded its approved clock')
            write(folder / 'PHASE-TIMING.json', dict(phase=phase, start_offset_seconds=phase_started - started,
                preflight_seconds=phase_elapsed, charged_wall_seconds=elapsed, limit_seconds=bounds['phase_seconds'][phase]))
            files = inventory(folder, omit=('PACKAGE-RECEIPT.json',))
            pp = write(folder / 'PACKAGE-RECEIPT.json', dict(kind='sc05_evidence_first_phase_receipt_v1',
                status='complete', phase=phase, frame_sha256=expected, files=files))
            accepted[phase] = freeze(dict(files, **{'PACKAGE-RECEIPT.json': pp}))
            phases[phase] = dict(root=str(folder), package_sha256=pp['sha256'], stage_receipt_sha256=terminal['stage_receipt']['sha256'])
            write(root / (phase + '-ANCHOR.json'), phases[phase])
            journal.append('evidence_first_phase_completed', phase=phase, anchor=phases[phase])
            phase_watchdog.__exit__(None, None, None); phase_watchdog = None
        original.verify_snapshot(c.read(value['source_closure']))
        c.need(time.monotonic() < end, 'Outer execution deadline exceeded')
        write(root / 'COMPLETE.json', dict(status='evidence_first_execution_complete', purpose=frame['purpose'],
            phases=phases, plan=frame['plan'], authority=frame['authority'], method_identity=value['method_identity'],
            scheduled=len(value['schedule']), new_scheduled=value['budgets']['generation_calls'],
            wall_seconds=time.monotonic() - started, provider_cost_usd=0, scientific_scoring_performed=False, automatic_retry=False))
        journal.append('evidence_first_execution_completed', phases=list(phases)); journal.close()
        files = inventory(root, omit=('ROOT-RECEIPT.json',), seconds=min(600, max(.001, end - time.monotonic())))
        process_tools.verify_final_packages(files, accepted)
        c.need(time.monotonic() < end, 'Outer final seal deadline exceeded')
        receipt = write(root / 'ROOT-RECEIPT.json', dict(kind='sc05_evidence_first_root_receipt_v1',
            status='evidence_first_execution_complete', frame_sha256=expected, files=files))
        return freeze(dict(root=str(root), receipt_sha256=receipt['sha256']))
    except BaseException as error:
        _preserve_failure(root, error, stage_name=current, journal=journal,
            completed_phases=phases, wall_seconds=time.monotonic() - started)
        raise
    finally:
        actions = [('Execution journal close', journal.close)]
        if phase_watchdog is not None:
            actions.append(('Phase watchdog close', lambda: phase_watchdog.__exit__(None, None, None)))
        if watchdog is not None: actions.append(('Execution watchdog close', lambda: watchdog.__exit__(None, None, None)))
        _cleanup(actions)
        _ = handle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frame', type=Path, required=True); parser.add_argument('--frame-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--worker', action='store_true'); group.add_argument('--admission', action='store_true')
    parser.add_argument('--job', type=Path); parser.add_argument('--job-sha256')
    args = parser.parse_args()
    if args.worker or args.admission:
        c.need(args.job is not None and args.job_sha256, 'Worker requires an externally bound job')
        entry = admission_worker if args.admission else worker
        result = entry(args.frame, args.frame_sha256, args.job, args.job_sha256, args.output)
    else: result = execute(args.frame, args.frame_sha256, output=args.output)
    print(encode(result))


if __name__ == '__main__': main()
