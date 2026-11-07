"""Independent evidence-first execution reader; no producer replay or inference.

The original source context is reconstructed once per operation. New native
answers are never adopted from the failed condition. Expected qualification
answers remain outside this reader until a complete execution is issued.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import math
import os
import sys
import weakref
from uuid import UUID

from tether_engine.serde import encode, freeze
from experiments.litqa_analysis import accepted_primary
from experiments.litqa_analysis.recovered_envelope import _model, _memory
from experiments.litqa_refinement import envelopes as old
from experiments.litqa_refinement import evaluation as joins
from experiments.litqa_refinement import native_evaluation as prior
from experiments.litqa_refinement import source_evaluation as sources
from experiments.litqa_refinement import phase_checks
from experiments.litqa_refinement_recovery import original
from experiments.litqa_refinement_recovery.reconstruct import _closure as preceding_closure
from . import native_evaluation as native

n = native.n
need = n.need
PHASES = ('repair', 'removal')
FIELDS = old.FIELDS
MODEL_FIELDS = {'model_receipt', 'model_license', 'model_spec', 'model_provenance', 'interpreter', 'port', 'alias'}
REPO = Path(__file__).resolve().parents[2]
CELL_LIMITS = dict(generation_calls=1, reserved_input_tokens=16128, reserved_output_tokens=256,
                  source_http_requests=0, safety_accounted_bytes=0, provider_cost_usd=0)
_ISSUED = weakref.WeakValueDictionary()
_STATES = {}


@dataclass(frozen=True)
class VerifiedEvidenceFirst:
    root: str
    receipt_sha256: str
    report: object
    envelope: object


def revalidate(value):
    need(type(value) is VerifiedEvidenceFirst and _ISSUED.get(id(value)) is value,
         'Issued independent evidence-first capability required')
    state = _STATES[id(value)]
    need(state['fingerprint'] == fingerprint(dict(root=value.root, receipt_sha256=value.receipt_sha256,
         report=value.report, envelope=value.envelope)), 'Independent capability changed')
    checked = original.verify_snapshot(state['closure'])
    if state['parent'] is not None: original.revalidate(state['parent'])
    checked.unchanged()
    return value


def same(left, right): return n.canonical(encode(left)) == n.canonical(encode(right))
def fingerprint(value): return n.digest(n.canonical(encode(value)))


def _retain_closure(inputs, closure):
    """Copy verified immutable proof instructions into the consuming operation."""
    closure = encode(closure)
    need(set(closure) == {'proofs', 'inventories'}, 'Complete transitive proof closure')
    for proof in closure['proofs']: inputs.bound(proof)
    for entry in closure['inventories']:
        need(set(entry) == {'root', 'omit', 'recursive', 'files'} and type(entry['recursive']) is bool,
             'Typed transitive inventory closure')
        actual = inputs.inventory(entry['root'], omit=entry['omit'], recursive=entry['recursive'])
        need(same(actual, entry['files']), 'Transitive qualification inventory changed')


def _schedule(ids, purpose):
    need(purpose in ('production', 'fictional_qualification'), 'Explicit method purpose')
    need(isinstance(ids, list) and len(ids) == (199 if purpose == 'production' else 6) and
         len(set(ids)) == len(ids) and all(isinstance(v, str) and str(UUID(v)) == v for v in ids),
         'Complete unique evidence-first schedule')
    return ids


def _budgets(purpose):
    need(purpose in ('production', 'fictional_qualification'), 'Explicit budget purpose')
    production = purpose == 'production'; count = 398 if production else 12
    return dict(generation_calls=count, reserved_input_tokens=count * 16128,
        reserved_output_tokens=count * 256, source_http_requests=0, provider_cost_usd=0,
        phase_seconds=dict(repair=6419 if production else 1200, removal=7200 if production else 1200),
        repair_stage_seconds=6401 if production else 1200, outer_seconds=39018 if production else 3600,
        call_seconds=120, automatic_retry=False)


def _identity(root, frame):
    root = old.path(root)
    need(old.path(frame['path']) == root / 'FRAME.json', 'Original root/frame identity')
    return fingerprint(dict(original_root=os.path.normcase(str(root)), frame_sha256=frame['sha256']))


def _closure(inputs):
    records = {row['path']: row for row in preceding_closure(inputs)}
    for path in Path(__file__).parent.glob('*.py'):
        if not path.name.startswith('test_'):
            proof, _ = inputs.capture(path); records[proof['path']] = proof
    return [records[key] for key in sorted(records)]


def _qualification_origin(anchor, inputs):
    receipt = inputs.json(anchor); base = old.path(anchor['path']).parent
    need(Path(anchor['path']).name == 'RECEIPT.json' and
         receipt['kind'] == 'sc05_failed_production_metadata_audit_receipt_v1' and receipt['status'] == 'complete',
         'Anchored original inspection scope')
    files = receipt['files']
    for name in ('RESULT.json', 'ORIGINAL-INVENTORY.json'):
        need(old.path(files[name]['path']) == base / name, 'Original metadata role location')
    report = inputs.json(files['RESULT.json']); inventory = inputs.json(files['ORIGINAL-INVENTORY.json'])
    need(report['kind'] == 'sc05_failed_production_metadata_forensics_v1' and
         report['status'] == 'metadata_and_byte_inventory_verified', 'Original metadata inspection status')
    root = old.path(report['original_root']); fp = report['original_frame']; frame = inputs.json(fp)
    need(inventory['root'] == str(root) and inventory['files']['FRAME.json'] == fp and
         old.path(frame['output']) == root and type(frame['schema_version']) is int and frame['schema_version'] == 1 and
         frame['kind'] == 'sc05_refinement_execution_v1' and frame['purpose'] == 'production', 'Original production metadata binding')
    _schedule(frame['schedule'], 'production')
    return _identity(root, fp), [anchor, files['RESULT.json'], files['ORIGINAL-INVENTORY.json'], fp]


def _invented_parent(descriptor, inputs):
    need(set(descriptor) == {'bank', 'original_inspection'}, 'Exact invented source authority')
    parent_id, proofs = _qualification_origin(descriptor['original_inspection'], inputs)
    bp = descriptor['bank']; bank = inputs.json(bp); base = old.path(bp['path']).parent
    need(bank['kind'] == 'tether_evidence_first_qualification_bank_v1' and type(bank['schema_version']) is int and
         bank['schema_version'] == 1 and bank['purpose'] == 'fictional_qualification' and
         type(bank['max_native_calls']) is int and bank['max_native_calls'] == 12 and
         type(bank['source_http_requests']) is int and bank['source_http_requests'] == 0 and
         bank['phase_order'] == list(PHASES), 'Six-pair invented source scope')
    ids = _schedule(bank['schedule'], 'fictional_qualification'); roles = bank['role_files']
    need(set(roles) == {'contexts', 'ancestry', 'expectations'}, 'Separate qualification roles')
    for role, filename, label in (('contexts', 'ACTOR.json', 'coordinator_only'),
        ('ancestry', 'ANCESTRY.json', 'coordinator_only'), ('expectations', 'EVALUATOR.json', 'evaluation_only')):
        row = roles[role]
        need(set(row) == {'proof', 'role'} and row['role'] == label and Path(row['proof']['path']) == base / filename,
             'Qualification role location differs')
    # Deliberately do not open roles['expectations']['proof'] here.
    actors = inputs.json(roles['contexts']['proof']); origins = inputs.json(roles['ancestry']['proof'])
    need(actors['kind'] == 'synthetic_refinement_contexts_v1' and actors['scope'] == 'fictional_qualification' and
         origins['kind'] == 'synthetic_refinement_ancestry_v1' and type(origins['actual_prior_model_calls']) is int and
         origins['actual_prior_model_calls'] == 0, 'Invented captures must not claim real prior calls')
    need([row['query']['id'] for row in actors['cases']] == ids and [row['id'] for row in origins['cases']] == ids,
         'Full qualification context membership')
    proofs += [bp, roles['contexts']['proof'], roles['ancestry']['proof']]
    expected_slots = {f'actor_cases/{task}-{i:04d}.json' for i in range(6) for task in PHASES}
    need(set(bank['slots']) == expected_slots, 'Exactly twelve prospective actor slots')
    rows = []; cutoff = None
    for i, (case, origin) in enumerate(zip(actors['cases'], origins['cases'])):
        need(set(case) == {'query', 'candidate_context', 'critique_context', 'sources'} and
             origin['invented'] is True and origin['scope'] == 'fictional_qualification' and
             origin['prior_capture_is_actual_native'] is False and origin['critic_capture_is_actual_native'] is False,
             'Explicit invented source ancestry')
        query, prior_value, critic, raw = (case[k] for k in ('query', 'candidate_context', 'critique_context', 'sources'))
        prior._query(query); prior._sources(raw); prior.candidate(query, prior_value); prior._critic_context(query, prior_value, critic)
        observed = datetime.fromisoformat(origin['cutoff_utc'])
        need(observed.utcoffset() is not None and (cutoff is None or cutoff == origin['cutoff_utc']), 'Fixed aware qualification cutoff')
        cutoff = origin['cutoff_utc']
        times = origin['current_source_available_at_utc']
        need(isinstance(times, dict) and set(times) == {source['source_id'] for source in raw}, 'Exact source availability mapping')
        for timestamp in (origin['critique_created_at_utc'], *times.values()):
            need(isinstance(timestamp, str), 'Aware input availability timestamp')
            dt = datetime.fromisoformat(timestamp); need(dt.utcoffset() is not None and dt <= observed, 'Input after cutoff')
        for task in PHASES:
            key = f'actor_cases/{task}-{i:04d}.json'; slot = bank['slots'][key]
            need(set(slot) == {'proof', 'role', 'phase', 'ordinal', 'id'} and slot['role'] == 'single_slot_actor_input' and
                 slot['phase'] == task and type(slot['ordinal']) is int and slot['ordinal'] == i and slot['id'] == ids[i] and
                 Path(slot['proof']['path']) == base / key, 'Exact single-actor source role')
            need(inputs.json(slot['proof']) == dict(task=task, query=query, candidate_context=prior_value,
                critique_context=critic, sources=raw if task == 'repair' else []), 'Invented source projection differs')
            proofs.append(slot['proof'])
        control = fingerprint(dict(query=query, candidate=prior_value, critique=critic))
        rows.append(dict(query=query, prior=prior_value, critic=critic, sources=raw,
            context=dict(kind='invented_evidence_first_context_v1', cutoff=cutoff, control_sha256=control,
                source_scope='invented', source_ancestry=origin, scientific_support='unevaluated')))
    return dict(rows=rows, ids=ids, cutoff=cutoff, parent_identity=parent_id,
                closure=dict(proofs=proofs, inventories=[]), parent=None, state=None)


def _source_parent(value, inputs):
    """Independent source-derived comparison, never trusting planned actor text."""
    if value['purpose'] == 'fictional_qualification':
        result = _invented_parent(value['parent'], inputs)
    else:
        descriptor = value['parent']
        need(set(descriptor) == {'inspection', 'source_archive', 'baseline_acceptance'}, 'Exact original source descriptor')
        parent = original.reconstruct(descriptor['inspection'], descriptor['source_archive'],
            baseline_acceptance=descriptor['baseline_acceptance'])
        state = original._state(parent); payload = encode(parent.payload)
        need(payload['purpose'] == 'production', 'Genuine production parent required')
        rows = encode(state['semantic']['prepared'])
        result = dict(rows=rows, ids=payload['schedule'], cutoff=rows[0]['context']['cutoff'],
            parent_identity=_identity(payload['original_root'], payload['frame_proof']),
            closure=encode(state['closure']), parent=parent, state=state)
        need(same(value['model'], {k: payload['frame'][k] for k in MODEL_FIELDS}), 'Original pinned model changed')
    need(value['schedule'] == result['ids'] and value['cutoff'] == result['cutoff'] and
         value['parent_identity'] == result['parent_identity'] and
         same(inputs.json(value['source_closure']), result['closure']), 'Original source authority/closure differs')
    expected = []
    need(len(value['prepared']) == len(result['rows']), 'Every original source case required')
    for i, (row, entry) in enumerate(zip(result['rows'], value['prepared'])):
        query, candidate, critic, raw, context = (row[k] for k in ('query', 'prior', 'critic', 'sources', 'context'))
        control = fingerprint(dict(query=query, candidate=candidate, critique=critic))
        need(entry['id'] == query['id'] and type(entry['ordinal']) is int and entry['ordinal'] == i and
             entry['control_sha256'] == control and inputs.json(entry['context']) == context, 'Retained source context/order changed')
        members = {}
        for task in PHASES:
            selected = raw if task == 'repair' else []
            member = native.prepare_member(task, query, candidate, critic, selected, value['model']['model_provenance'], value['method'])
            actor = dict(task=task, query=query, candidate_context=candidate, critique_context=critic, sources=selected,
                model_provenance=value['model']['model_provenance'], prepared_member=member, control_sha256=control)
            need(inputs.json(entry[task]) == actor, 'Independent new-method actor projection differs')
            members[task] = actor
        expected.append(dict(query=query, prior=candidate, critic=critic, context=context, members=members,
                             control_sha256=control, sources=raw))
    result['prepared'] = expected
    return result


def _plan(frame, inputs):
    pp = frame['plan']; value = inputs.json(pp); base = old.path(pp['path']).parent
    fields = {'schema_version', 'kind', 'purpose', 'parent', 'parent_identity', 'method', 'method_identity',
        'schedule', 'prepared', 'cutoff', 'source_closure', 'model', 'budgets', 'authority_registry',
        'code_files', 'automatic_retry', 'reference_keys_available', 'new_source_collection'}
    need(set(value) == fields and type(value['schema_version']) is int and value['schema_version'] == 1 and
         value['kind'] == 'sc05_evidence_first_plan_v1' and value['purpose'] == frame['purpose'], 'Exact method plan')
    _schedule(value['schedule'], value['purpose'])
    need(value['budgets'] == _budgets(value['purpose']) and value['automatic_retry'] is False and
         value['reference_keys_available'] is False and value['new_source_collection'] is False, 'Fixed prospective budgets/roles')
    actual = inputs.inventory(base)
    expected = {'REQUEST.json', 'METHOD.json', 'SOURCE-CLOSURE.json', 'PLAN.json', 'COMPLETE.json'}
    expected |= {f'pairs/{i:04d}/{name}.json' for i in range(len(value['schedule'])) for name in ('CONTEXT', 'REPAIR', 'REMOVAL')}
    need(set(actual) == expected and actual['PLAN.json'] == pp and actual['METHOD.json'] == value['method'] and
         actual['SOURCE-CLOSURE.json'] == value['source_closure'], 'Closed successful preparation package')
    need(inputs.json(actual['COMPLETE.json']) == dict(status='paired_inputs_sealed', plan=pp, native_calls=0,
         source_http_requests=0, authority_reserved=False), 'Successful preparation terminal')
    request = inputs.json(actual['REQUEST.json'])
    need(set(request) == {'parent', 'created_at_utc', 'model_or_http_execution_performed', 'reference_keys_available'} and
         request['parent'] == value['parent'] and request['model_or_http_execution_performed'] is False and
         request['reference_keys_available'] is False, 'Preparation origin/role')
    old.historical.utc(request['created_at_utc'])
    method = inputs.json(value['method']); native.method(value['method'])
    need(value['method_identity'] == fingerprint(method) and same(value['code_files'], frame['code_files']), 'Method/source identity')
    import ast
    model_code = [p for p in frame['code_files'] if Path(p['path']) == REPO / 'experiments/litqa_evidence_first/model.py']
    need(len(model_code) == 1, 'Pinned method implementation required')
    tree = ast.parse(inputs.bound(model_code[0]).decode('utf8'))
    declarations = [node.value for node in tree.body if isinstance(node, ast.Assign) and
                    any(isinstance(target, ast.Name) and target.id == 'INSTRUCTION' for target in node.targets)]
    need(len(declarations) == 1 and ast.literal_eval(declarations[0]) == method['instruction'], 'Frozen method instruction/source binding')
    need(len(value['prepared']) == len(value['schedule']), 'Complete prepared source schedule')
    for i, entry in enumerate(value['prepared']):
        need(set(entry) == {'id', 'ordinal', 'control_sha256', 'context', 'repair', 'removal'} and
             type(entry['ordinal']) is int and entry['ordinal'] == i and entry['id'] == value['schedule'][i], 'Prepared member identity')
        for key in ('context', 'repair', 'removal'):
            need(entry[key] == actual[f'pairs/{i:04d}/{key.upper()}.json'], 'Exact prepared member location')
    return value


def _release(frame, inputs, recorded):
    """Recheck CI identity and exact committed bytes without a network request."""
    import io
    import shutil
    import zipfile
    from tether._process import ProcessLimits, supervise_command, validate_success_report
    value = inputs.json(frame['release']); need(set(value) == {'run', 'jobs'}, 'Captured CI metadata')
    run = value['run']; jobs = value['jobs']['jobs']; commit = run['head_sha']
    import re
    need(isinstance(commit, str) and re.fullmatch('[0-9a-f]{40}', commit) and
         type(run['id']) is int and run['id'] > 0 and run['status'] == 'completed' and run['conclusion'] == 'success' and
         run['url'] == f'https://api.github.com/repos/rzzli/TETHER/actions/runs/{run["id"]}' and
         run['path'] == '.github/workflows/validate.yml' and run['head_branch'] == 'main' and run['event'] == 'push' and
         type(run['run_attempt']) is int and run['run_attempt'] > 0, 'Exact successful release workflow')
    required = {'tether-interface', 'validate (windows-latest, core)', 'validate (ubuntu-latest, core)', 'validate (windows-latest, full)'}
    need(value['jobs']['total_count'] == 4 and len(jobs) == 4 and {r['name'] for r in jobs} == required, 'Four release jobs')
    for job in jobs:
        need(job['head_sha'] == commit and job['run_id'] == run['id'] and type(job['run_attempt']) is int and
             job['run_attempt'] == run['run_attempt'] and job['status'] == 'completed' and job['conclusion'] == 'success', 'Exact successful CI attempt')
    need(set(recorded) == {'kind', 'commit', 'ci', 'matched_runtime_files', 'required_jobs', 'verification_seconds', 'source_http_requests'} and
         recorded['kind'] == 'evidence_first_release_verified_v1' and recorded['commit'] == commit and
         recorded['ci'] == frame['release'] and recorded['matched_runtime_files'] == len(frame['code_files']) and
         recorded['required_jobs'] == sorted(required) and recorded['source_http_requests'] == 0, 'Recorded release identity')
    old.finite(recorded['verification_seconds'], 'Release verification time')
    git = shutil.which('git'); need(git is not None, 'Git required for committed source verification')
    limits = ProcessLimits(60, 64 * 1024**2)
    process = supervise_command([git, '-C', str(REPO), 'archive', '--format=zip', commit], limits=limits)
    need(process.returncode == 0, 'Committed source archive unavailable')
    validate_success_report(process.supervision, limits, len(process.stdout), len(process.stderr))
    with zipfile.ZipFile(io.BytesIO(process.stdout)) as archive:
        need(len(archive.namelist()) == len(set(archive.namelist())), 'Duplicate archive names')
        for proof in frame['code_files']:
            path = old.path(proof['path']); need(path.is_relative_to(REPO), 'Committed project source path')
            name = path.relative_to(REPO).as_posix(); info = archive.getinfo(name)
            need(info.file_size == proof['bytes'] <= 64 * 1024**2 and n.digest(archive.read(info)) == proof['sha256'], 'Current source differs from CI commit')


def _gates(frame, value, inputs, started):
    protocol = inputs.json(frame['protocol'])
    fields = {'schema_version', 'kind', 'created_at_utc', 'owner_approval', 'original_inspection',
              'method', 'bank', 'budgets', 'endpoints', 'original_inputs', 'code_files', 'automatic_retry'}
    need(set(protocol) == fields and type(protocol['schema_version']) is int and protocol['schema_version'] == 1 and
         protocol['kind'] == 'sc05_evidence_first_protocol_v1' and protocol['automatic_retry'] is False and
         same(protocol['code_files'], frame['code_files']) and
         protocol['budgets'] == {purpose: _budgets(purpose) for purpose in ('production', 'fictional_qualification')}, 'Prospective protocol contract')
    declared = datetime.fromisoformat(protocol['created_at_utc'])
    need(declared.utcoffset() == timedelta(0) and declared <= old.historical.utc(started), 'Existing UTC method declaration required')
    inspection = value['parent']['inspection'] if value['purpose'] == 'production' else value['parent']['original_inspection']
    need(protocol['original_inspection'] == inspection and fingerprint(inputs.json(protocol['method'])) == value['method_identity'], 'Protocol source/method identity')
    if value['purpose'] == 'fictional_qualification': need(protocol['bank'] == value['parent']['bank'], 'Prospective bank differs')
    approval = inputs.json(protocol['owner_approval'])
    expected = dict(kind='tether_evidence_first_owner_approval_v1',
        response='Approve the separate revised-method experiment (Recommended)', total_generations_cap=410,
        production_generations_cap=398, qualification_generations_cap=12, provider_cost_usd=0,
        new_source_http_requests=0, automatic_retry=False, old_failed_run_preserved=True)
    need(all(same(approval.get(k), v) for k, v in expected.items()), 'Explicit approved separate method scope')
    proposal = approval['proposal']; raw = n.read(proposal['path'], 1024**2)
    need(n.digest(raw) == proposal['sha256'], 'Owner-approved proposal changed')
    proposed, _ = inputs.capture(proposal['path']); bank = inputs.json(protocol['bank'])
    need(bank['decision'] == proposed, 'Bank decision must equal the externally owner-approved proposal')
    # Endpoints are safe metric metadata. Original reference manifests remain unopened.
    inputs.json(protocol['endpoints'])
    evidence = inputs.json(frame['engineering'])
    need(evidence['kind'] == 'sc05_evidence_first_engineering_qualification_v1' and evidence['status'] == 'passed' and
         same(evidence['code_files'], frame['code_files']) and evidence['method_identity'] == value['method_identity'] and
         type(evidence['model_calls']) is int and evidence['model_calls'] == 0 and
         evidence['complete_controller_and_independent_evaluation'] is True, 'Full engineering gate binding')
    return protocol


def _stage(root, rp, frame, value, job, inputs, worker_seconds, process_seconds):
    receipt = inputs.json(rp); files = inputs.inventory(root, omit=('STAGE-RECEIPT.json',))
    compact = {name: {key: p[key] for key in ('bytes', 'sha256')} for name, p in files.items()}
    need(set(receipt) == {'kind', 'status', 'files', 'seal_elapsed_seconds', 'automatic_retry'} and
         receipt['kind'] == 'sc05_evidence_first_stage_receipt_v1' and receipt['status'] == 'complete' and
         receipt['automatic_retry'] is False and receipt['files'] == compact, 'Closed complete stage receipt')
    config = inputs.json(files['CONFIG.json']); report = inputs.json(files['REPORT.json']); phase = job['phase']
    namespace = config['execution_namespace']; need(str(UUID(namespace)) == namespace, 'New execution namespace')
    ordered = [dict(ordinal=i, id=key, phase=phase, execution_id=f'{namespace}-{phase}-{i:04d}') for i, key in enumerate(value['schedule'])]
    need(set(config) == {'kind', 'phase', 'purpose', 'ids', 'execution_namespace', 'schedule', 'seconds', 'cell_limits'} and
         config['kind'] == 'sc05_evidence_first_stage_v1' and config['phase'] == phase and config['purpose'] == frame['purpose'] and
         config['ids'] == value['schedule'] and config['schedule'] == ordered and config['cell_limits'] == CELL_LIMITS, 'Stage full schedule/configuration')
    seconds = old.finite(config['seconds'], 'Stage cap'); elapsed = old.finite(report['wall_seconds'], 'Stage elapsed')
    seal = old.finite(receipt['seal_elapsed_seconds'], 'Stage seal elapsed')
    need(0 < seconds <= job['stage_seconds'] and elapsed <= seal < seconds and seal <= worker_seconds <= process_seconds, 'Nested stage clocks')
    need(inputs.json(files['INPUTS.json']) == dict(plan=frame['plan'], phase=phase, cutoff=value['cutoff'],
        method_identity=value['method_identity'], reference_keys_available=False, scoring_performed=False), 'Stage input roles')
    rows = report['rows']; need(len(rows) == len(ordered), 'Full stage denominator')
    events = old._events(inputs, files['journal.jsonl']); old._reserved(events[0])
    expected = [('evidence_first_stage_configured', dict(config_sha256=fingerprint(config)))]
    for row, slot in zip(rows, ordered):
        need(set(row) == set(slot) | {'status', 'reason', 'product', 'accounting'} and all(row[k] == v for k, v in slot.items()) and
             row['status'] in ('completed', 'capacity', 'codec_failure') and row['product'] is not None, 'All scheduled terminal rows')
        old._accounting(row['accounting'], phase, row['status']); name = f'slots/{slot["ordinal"]:04d}.json'
        need(inputs.json(files[name]) == row, 'Stage slot bytes')
        expected.extend([('evidence_first_slot_reserved', dict(slot=slot, limits=CELL_LIMITS)),
            ('evidence_first_slot_terminal', dict(ordinal=slot['ordinal'], path=name, slot_sha256=fingerprint(row), status=row['status']))])
    rebuilt = dict(kind='sc05_evidence_first_stage_report_v1', phase=phase, purpose=frame['purpose'], status='complete',
        scheduled=len(rows), entered=len(rows), unexecuted=0, rows=rows, wall_seconds=elapsed,
        accounting=dict(known_totals={key: sum(row['accounting'][key] for row in rows) for key in FIELDS}, provider_cost_usd=0,
            uncertain_cells=[], measurements_complete=True, uncertain_per_cell_ceiling=CELL_LIMITS, historical_work_included=False), automatic_retry=False)
    need(same(report, rebuilt), 'Rebuilt native accounting')
    expected.append(('evidence_first_stage_finalized', dict(status='complete', report_sha256=fingerprint(report))))
    need([(e['event'], e['details']) for e in events[1:]] == expected, 'Exact stage dispatch journal')
    old._membership(root, ('CONFIG.json', 'INPUTS.json', 'REPORT.json', 'STAGE-RECEIPT.json', 'journal.jsonl'), ('slots', 'products'))
    old._membership(root / 'slots', {f'{i:04d}.json' for i in range(len(rows))}, ())
    old._membership(root / 'products', (), {f'{i:04d}' for i in range(len(rows))})
    return dict(root=str(root), rows=rows, report=report, files=files)


LAUNCHER = ('import runpy,sys;sys.path[:0]=sys.argv[1:4];'
    'sys.argv=["tether-evidence-first-worker"]+sys.argv[4:];'
    'runpy.run_module("experiments.litqa_evidence_first.run",run_name="__main__")')


def _process(root, inputs, files, *, frame, fp, jp, mode, output, seconds):
    from tether._process import ProcessLimits, validate_success_report
    command = [frame['interpreter']['path'], '-I', '-B', '-c', LAUNCHER, str(REPO), str(REPO / 'src'),
        str(REPO / 'packages/tether/src'), '--' + mode, '--frame', fp['path'], '--frame-sha256', fp['sha256'],
        '--job', jp['path'], '--job-sha256', jp['sha256'], '--output', str(output)]
    need(inputs.json(files['COMMAND.json']) == command, 'Exact supervised child command')
    process = inputs.json(files['PROCESS.json'])
    need(set(process) == {'returncode', 'supervision'} and type(process['returncode']) is int and process['returncode'] == 0,
         'Successful reaped child required')
    stdout, stderr = inputs.bound(files['stdout.bin']), inputs.bound(files['stderr.bin'])
    validate_success_report(process['supervision'], ProcessLimits(seconds, 4 * 1024**2), len(stdout), len(stderr))
    return process['supervision'], command


def _admission(root, frame, value, job, fp, jp, inputs, worker_owner, worker_wall):
    files = inputs.inventory(root)
    expected_files = {'COMMAND.json', 'PROCESS.json', 'COMPLETE.json', 'stdout.bin', 'stderr.bin',
        'worker/REQUEST.json', 'worker/RELEASE-VERIFICATION.json', 'worker/REPORT.json', 'worker/RECEIPT.json', 'worker/journal.jsonl'}
    need(set(files) == expected_files, 'Closed successful isolated admission')
    observed = inputs.json(files['PROCESS.json'])['supervision']['limits']['timeout_seconds']
    need(0 < old.finite(observed, 'Admission cap') <= min(3600 if frame['purpose'] == 'production' else 600,
         job['seconds'] - 390), 'Admission fits original phase/startup/call reserves')
    process, _ = _process(root, inputs, files, frame=value['model'], fp=fp, jp=jp, mode='admission',
        output=root / 'worker', seconds=observed)
    need(process['total_elapsed_seconds'] <= worker_wall, 'Worker time must contain isolated admission')
    rp = files['worker/RECEIPT.json']; receipt = inputs.json(rp)
    child_files = {name[7:]: proof for name, proof in files.items() if name.startswith('worker/') and name != 'worker/RECEIPT.json'}
    need(receipt == dict(kind='sc05_evidence_first_admission_receipt_v1', status='admitted', files=child_files), 'Admission receipt')
    expected = dict(kind='sc05_evidence_first_worker_admission_v1', status='admitted', frame=fp, job=jp,
        plan=frame['plan'], authority=frame['authority'], protocol=frame['protocol'], engineering=frame['engineering'],
        qualification=frame['qualification'], release=frame['release'], parent_identity=value['parent_identity'],
        method_identity=value['method_identity'], schedule=value['schedule'], budgets=value['budgets'], phase=job['phase'],
        model_or_http_execution_performed=False, scientific_answers_returned=False)
    need(inputs.json(child_files['REPORT.json']) == expected and inputs.json(files['COMPLETE.json']) ==
         dict(status='admitted', receipt=rp, frame=fp, job=jp, model_or_http_execution_performed=False), 'Source-only admission projection')
    need(inputs.json(child_files['REQUEST.json']) == dict(frame=fp, job=jp, role='trusted_parent_admission',
         model_or_http_execution_performed=False, scientific_answers_returned=False), 'Admission request role')
    events = old._events(inputs, child_files['journal.jsonl']); owner = old._reserved(events[0])
    need(owner['owner_pid'] != worker_owner and len(events) == 2 and events[1]['event'] == 'evidence_first_worker_admitted' and
         events[1]['details'] == dict(report_sha256=fingerprint(expected)), 'Independent admission process journal/ownership')
    return dict(supervision=process, report=expected, release=inputs.json(child_files['RELEASE-VERIFICATION.json']))


def _envelope(descriptor):
    need(isinstance(descriptor, dict) and set(descriptor) == {'root', 'receipt_sha256', 'controller'}, 'External supervised execution descriptor')
    inputs = accepted_primary._Inputs(); root = old.path(descriptor['root'])
    rp, receipt = inputs.anchored(root / 'ROOT-RECEIPT.json', descriptor['receipt_sha256'])
    files = inputs.inventory(root, omit=('ROOT-RECEIPT.json',))
    need(set(receipt) == {'kind', 'status', 'frame_sha256', 'files'} and
         receipt['kind'] == 'sc05_evidence_first_root_receipt_v1' and receipt['status'] == 'evidence_first_execution_complete' and
         receipt['files'] == files, 'Closed successful new-method root')
    need(not any(Path(name).name in ('FAILURE.json', 'DEADLINE.json', 'FINALIZATION-FAILED.json',
         'repair-DEADLINE.json', 'removal-DEADLINE.json') for name in files), 'Failure dominates a complete root')
    old._membership(root, {'FRAME.json', 'REQUEST.json', 'ROOT-RECEIPT.json', 'RELEASE-VERIFICATION.json',
        'COMPLETE.json', 'journal.jsonl', 'repair-ANCHOR.json', 'removal-ANCHOR.json'}, PHASES)
    fp = files['FRAME.json']; frame = inputs.json(fp)
    need(set(frame) == {'schema_version', 'kind', 'purpose', 'plan', 'authority', 'code_files', 'protocol',
         'engineering', 'qualification', 'release', 'output'} and type(frame['schema_version']) is int and
         frame['schema_version'] == 1 and frame['kind'] == 'sc05_evidence_first_execution_v1' and
         receipt['frame_sha256'] == fp['sha256'] and old.path(frame['output']) == root, 'New frame identity')
    need(same(frame['code_files'], _closure(inputs)), 'Executing and independent source closure differs')
    request = inputs.json(files['REQUEST.json'])
    need(set(request) == {'frame', 'output', 'automatic_retry'} and request['output'] == str(root) and
         request['automatic_retry'] is False and inputs.bound(request['frame']) == inputs.bound(fp) and
         not old.path(request['frame']['path']).is_relative_to(root), 'External frame reservation')
    value = _plan(frame, inputs); source = _source_parent(value, inputs)
    settings = value['model']; need(set(settings) == MODEL_FIELDS, 'Original model metadata fields')
    inputs.bound(settings['interpreter']); model = _model({k: v for k, v in settings.items() if k != 'interpreter'}, inputs)
    events = old._events(inputs, files['journal.jsonl']); reserved = old._reserved(events[0]); started = reserved['created_at_utc']
    protocol = _gates(frame, value, inputs, started)
    _release(frame, inputs, inputs.json(files['RELEASE-VERIFICATION.json']))
    if value['purpose'] == 'production':
        need(frame['qualification'] is not None, 'Complete native controls required')
        accept_qualification(frame['qualification'], value, protocol, inputs=inputs, production_started_at=started)
    else: need(frame['qualification'] is None, 'Fresh controls cannot inherit qualification')
    registry = REPO / 'data/benchmark/litqa_evidence_first/authority' / frame['purpose']
    key = fingerprint(dict(kind='evidence_first_authority_v1', parent=value['parent_identity'], method=value['method_identity']))
    location = registry / key; ap = frame['authority']; authority = inputs.json(ap)
    need(value['authority_registry'] == str(registry) and old.path(ap['path']) == location / 'AUTHORITY.json' and authority ==
         dict(schema_version=1, kind='sc05_evidence_first_authority_v1', identity=key, parent_identity=value['parent_identity'],
         method_identity=value['method_identity'], plan=frame['plan'], purpose=frame['purpose'], schedule=value['schedule'],
         budgets=value['budgets'], permanent=True, automatic_retry=False), 'Permanent method authority')
    execution = location / 'EXECUTION'; claim, _ = inputs.capture(execution / 'CLAIM.json')
    need(inputs.json(claim) == dict(frame_sha256=fp['sha256'], output=str(root), automatic_retry=False), 'Single permanent execution')
    old._membership(location, ('AUTHORITY.json',), ('EXECUTION',))
    old._membership(execution, {'CLAIM.json'} | {phase + suffix for phase in PHASES for suffix in ('-AUTHORIZED-JOB.json', '-WORKER-CLAIM.json')}, ())
    inputs.inventory(location)
    complete = inputs.json(files['COMPLETE.json']); wall = old.finite(complete['wall_seconds'], 'Execution elapsed')
    expected_terminal = dict(status='evidence_first_execution_complete', purpose=frame['purpose'], phases=complete['phases'],
        plan=frame['plan'], authority=ap, method_identity=value['method_identity'], scheduled=len(value['schedule']),
        new_scheduled=value['budgets']['generation_calls'], wall_seconds=wall, provider_cost_usd=0,
        scientific_scoring_performed=False, automatic_retry=False)
    need(complete == expected_terminal and set(complete['phases']) == set(PHASES) and wall < value['budgets']['outer_seconds'], 'Complete all-case execution')
    expected_events = [('evidence_first_admitted', dict(plan=frame['plan'], authority=ap, execution_claim=claim))]
    phases = {}; contexts = {}; resources = {}; spent = 0; last_phase_end = 0; physical = set()
    for phase in PHASES:
        folder = root / phase; anchor = complete['phases'][phase]; pp = files[phase + '/PACKAGE-RECEIPT.json']
        pf = inputs.inventory(folder, omit=('PACKAGE-RECEIPT.json',)); package = inputs.json(pp)
        need(anchor == dict(root=str(folder), package_sha256=pp['sha256'], stage_receipt_sha256=anchor['stage_receipt_sha256']) and
             inputs.json(files[phase + '-ANCHOR.json']) == anchor and package == dict(kind='sc05_evidence_first_phase_receipt_v1',
             status='complete', phase=phase, frame_sha256=fp['sha256'], files=pf), 'Complete phase anchor')
        old._membership(folder, ('JOB.json', 'COMMAND.json', 'PROCESS.json', 'stdout.bin', 'stderr.bin',
            'PHASE-TIMING.json', 'PACKAGE-RECEIPT.json'), ('worker', 'admission'))
        jp = pf['JOB.json']; job = inputs.json(jp); preflight = old.finite(job['phase_preflight_seconds'], 'Phase preflight')
        outer_preflight = old.finite(job['outer_preflight_seconds'], 'Outer preflight')
        need(preflight <= outer_preflight, 'Nested preflight clocks')
        seconds = int(min(value['budgets']['phase_seconds'][phase] - preflight, value['budgets']['outer_seconds'] - outer_preflight - 60))
        stage_seconds = min(seconds - 90, value['budgets']['repair_stage_seconds']) if phase == 'repair' else seconds - 90
        grants = [frame['plan'], ap, value['method'], *[p for row in value['prepared'] for p in (row[phase], row['context'])]]
        grants = sorted(grants, key=lambda p: p['path'])
        need(seconds > 120 and stage_seconds > 0 and job == dict(phase=phase, frame_sha256=fp['sha256'], input_files=grants,
             model_bindings=model['bindings'], seconds=seconds, stage_seconds=stage_seconds, execution_claim=claim,
             phase_preflight_seconds=preflight, outer_preflight_seconds=outer_preflight), 'Exact narrow grants and carried phase clocks')
        for proof in grants: inputs.bound(proof)
        auth_proof, _ = inputs.capture(execution / (phase + '-AUTHORIZED-JOB.json'))
        need(inputs.json(auth_proof) == dict(frame_sha256=fp['sha256'], job=jp, output=str(folder / 'worker')), 'One authorized child')
        process, command = _process(folder, inputs, pf, frame=settings, fp=fp, jp=jp, mode='worker', output=folder / 'worker', seconds=seconds)
        spent += process['execution_elapsed_seconds']
        expected_events.extend([('evidence_first_phase_reserved', dict(phase=phase, job=jp, command=command,
            limits=dict(timeout_seconds=seconds, max_output_bytes=4 * 1024**2))), ('evidence_first_phase_completed', dict(phase=phase, anchor=anchor))])
        worker = folder / 'worker'; cfg = inputs.json(pf['worker/CONFIG.json']); terminal = inputs.json(pf['worker/COMPLETE.json'])
        owner_events = old._events(inputs, pf['worker/journal.jsonl']); owner = old._reserved(owner_events[0])
        need(old.historical.utc(started) <= old.historical.utc(owner['created_at_utc']), 'Worker reservation predates root')
        wp, _ = inputs.capture(execution / (phase + '-WORKER-CLAIM.json'))
        need(inputs.json(wp) == dict(frame_sha256=fp['sha256'], job_sha256=jp['sha256'], output=str(worker), owner_pid=owner['owner_pid']), 'Permanent worker owner')
        need(cfg == dict(frame_sha256=fp['sha256'], job_sha256=jp['sha256'], phase=phase, purpose=frame['purpose'],
             worker_pid=owner['owner_pid'], python_version=sys.version, coordinator_grants=grants) and inputs.json(pf['worker/MODEL.json']) == model,
             'Worker model/configuration')
        worker_wall = old.finite(terminal['wall_seconds'], 'Worker elapsed')
        need(set(terminal) == {'status', 'phase', 'purpose', 'frame_sha256', 'stage_receipt', 'wall_seconds', 'worker_memory',
             'server_terminal', 'audit_denials', 'provider_cost_usd', 'reference_keys_read', 'scientific_scoring_performed'} and
             terminal['status'] == 'complete' and terminal['phase'] == phase and terminal['purpose'] == frame['purpose'] and
             terminal['frame_sha256'] == fp['sha256'] and type(terminal['audit_denials']) is int and terminal['audit_denials'] == 0 and
             terminal['provider_cost_usd'] == 0 and terminal['reference_keys_read'] is False and
             terminal['scientific_scoring_performed'] is False and worker_wall < seconds, 'Successful worker terminal')
        phase_checks._worker_journal(inputs.bound(pf['worker/journal.jsonl']), terminal, cfg, phase)
        server = terminal['server_terminal']; need(inputs.json(pf['worker/server/server-command.json']) == model['spec'], 'Owned native command')
        sp = pf['worker/phase/STAGE-RECEIPT.json']
        need(terminal['stage_receipt'] == sp and sp['sha256'] == anchor['stage_receipt_sha256'], 'Stage external anchor')
        stage = _stage(worker / 'phase', sp, frame, value, job, inputs, worker_wall, process['execution_elapsed_seconds']); phases[phase] = stage
        for row in stage['rows']:
            need(row['execution_id'] not in physical, 'Repeated physical execution ID'); physical.add(row['execution_id'])
        admission = _admission(folder / 'admission', frame, value, job, fp, jp, inputs, owner['owner_pid'], worker_wall)
        recorded_release = inputs.json(files['RELEASE-VERIFICATION.json'])
        need({k:v for k,v in admission['release'].items() if k != 'verification_seconds'} ==
             {k:v for k,v in recorded_release.items() if k != 'verification_seconds'}, 'Admission release identity')
        old.finite(admission['release']['verification_seconds'], 'Admission release duration')
        io = phase_checks._audit(inputs.bound(pf['worker/io-audit.jsonl']), root=folder,
            frame=dict(settings, code_files=frame['code_files']), job=job, rows=stage['rows'])
        old._membership(worker, ('CONFIG.json', 'COMPLETE.json', 'MODEL.json', 'io-audit.jsonl', 'journal.jsonl', 'SERVER-RESOURCE-SAMPLES.json'), ('phase', 'server'))
        old._membership(worker / 'server', ('server-command.json', 'server.stdout.log', 'server.stderr.log'), ())
        samples = inputs.json(pf['worker/SERVER-RESOURCE-SAMPLES.json']); need(isinstance(samples, list) and 0 < len(samples) <= 100000, 'Bounded resource samples')
        for sample in samples:
            need(set(sample) == {'monotonic', 'value', 'error_class'} and (sample['error_class'] is None or isinstance(sample['error_class'], str)), 'Resource sample fields')
            old.finite(sample['monotonic'], 'Sample clock'); _memory(sample['value'])
        timing = inputs.json(pf['PHASE-TIMING.json']); offset = old.finite(timing['start_offset_seconds'], 'Phase offset')
        charged = old.finite(timing['charged_wall_seconds'], 'Charged phase time')
        need(timing == dict(phase=phase, start_offset_seconds=offset, preflight_seconds=preflight, charged_wall_seconds=charged,
             limit_seconds=value['budgets']['phase_seconds'][phase]) and offset + preflight == outer_preflight and
             charged >= preflight + process['total_elapsed_seconds'] and charged < value['budgets']['phase_seconds'][phase] and
             offset >= last_phase_end and offset + charged <= wall and (phase != 'repair' or offset == 0), 'Full phase resource chronology')
        last_phase_end = offset + charged
        contexts[phase] = dict(model_provenance=model['provenance'], alias=model['alias'], owner_pid=server['pid'], endpoint=f'http://127.0.0.1:{settings["port"]}')
        resources[phase] = dict(supervision=process, admission=admission['supervision'], worker_wall_seconds=worker_wall,
            worker_memory=_memory(terminal['worker_memory']), server_terminal=server, io_audit=io, phase_timing=timing,
            stage_accounting=stage['report']['accounting'], server_resource_samples=samples)
    expected_events.append(('evidence_first_execution_completed', dict(phases=list(PHASES))))
    need([(event['event'], event['details']) for event in events[1:]] == expected_events and spent <= wall, 'Root process/dispatch reconciliation')
    outer = _controller(descriptor, frame, request['frame'], value, inputs, wall, reserved)
    return dict(root=str(root), receipt_sha256=rp['sha256'], frame=frame, value=value, protocol=protocol,
                phases=phases, model_contexts=contexts, source=source, started=started, resources=resources,
                wall_seconds=wall, inputs=inputs, controller=outer, producer=descriptor)


def _controller(descriptor, frame, fp, value, inputs, root_wall, root_owner):
    """Check the externally anchored outer process, not a controller self-report."""
    from tether._process import ProcessLimits, validate_success_report
    outer = descriptor['controller']
    need(isinstance(outer, dict) and set(outer) == {'root', 'receipt_sha256'}, 'External controller anchor')
    root = old.path(outer['root']); producer = root / 'producer'
    need(root.is_relative_to(REPO / 'data') and producer == old.path(descriptor['root']), 'Exact outer/producer containment')
    rp, receipt = inputs.anchored(root / 'RECEIPT.json', outer['receipt_sha256'])
    files = inputs.inventory(root, omit=('RECEIPT.json',))
    need(receipt == dict(kind='sc05_evidence_first_controller_receipt_v1', status='complete', frame_sha256=fp['sha256'], files=files),
         'Complete external controller inventory')
    old._membership(root, ('REQUEST.json', 'CONFIG.json', 'COMMAND.json', 'PROCESS.json', 'stdout.bin', 'stderr.bin',
                          'COMPLETE.json', 'journal.jsonl', 'RECEIPT.json'), ('producer',))
    need(files['producer/ROOT-RECEIPT.json']['sha256'] == descriptor['receipt_sha256'] and
         inputs.json(files['REQUEST.json']) == dict(frame=fp, output=str(root), producer_output=str(producer), automatic_retry=False),
         'Outer request/source anchor')
    config = inputs.json(files['CONFIG.json']); elapsed = old.finite(config['preflight_seconds'], 'Outer preflight')
    seconds = int(value['budgets']['outer_seconds'] - elapsed - 60); need(seconds > 120, 'Remaining outer allowance')
    limits = ProcessLimits(seconds, 4 * 1024**2)
    need(config == dict(kind='sc05_evidence_first_controller_config_v1', frame_sha256=fp['sha256'], purpose=frame['purpose'],
         outer_seconds=value['budgets']['outer_seconds'], preflight_seconds=elapsed, control_reserve_seconds=60, limits=limits.payload()),
         'Fixed inclusive outer clock')
    command = [value['model']['interpreter']['path'], '-I', '-B', '-c', LAUNCHER, str(REPO), str(REPO / 'src'),
        str(REPO / 'packages/tether/src'), '--frame', fp['path'], '--frame-sha256', fp['sha256'], '--output', str(producer)]
    need(inputs.json(files['COMMAND.json']) == command, 'Exact outer controller command')
    process = inputs.json(files['PROCESS.json'])
    need(set(process) == {'returncode', 'supervision'} and type(process['returncode']) is int and process['returncode'] == 0,
         'Controller process must complete successfully')
    validate_success_report(process['supervision'], limits, len(inputs.bound(files['stdout.bin'])), len(inputs.bound(files['stderr.bin'])))
    complete = inputs.json(files['COMPLETE.json']); wall = old.finite(complete['wall_seconds'], 'Outer wall time')
    need(complete == dict(kind='sc05_evidence_first_controller_terminal_v1', status='complete',
         producer={k: descriptor[k] for k in ('root', 'receipt_sha256')}, frame=fp, wall_seconds=wall,
         provider_cost_usd=0, automatic_retry=False, scientific_scoring_performed=False) and
         root_wall <= process['supervision']['execution_elapsed_seconds'] and
         elapsed + process['supervision']['total_elapsed_seconds'] <= wall < value['budgets']['outer_seconds'], 'Entire observed controller lifetime')
    events = old._events(inputs, files['journal.jsonl']); owner = old._reserved(events[0])
    need(owner['owner_pid'] != root_owner['owner_pid'] and
         old.historical.utc(owner['created_at_utc']) <= old.historical.utc(root_owner['created_at_utc']) and
         [(e['event'], e['details']) for e in events[1:]] == [
            ('evidence_first_controller_reserved', dict(frame=fp, command=command, limits=limits.payload())),
            ('evidence_first_controller_completed', dict(terminal_sha256=fingerprint(complete)))], 'Distinct outer owner and dispatch journal')
    return dict(receipt=rp, supervision=process['supervision'], wall_seconds=wall, preflight_seconds=elapsed,
                root_wall_seconds=root_wall, reserved_at_utc=owner['created_at_utc'], status='independently_verified')


def _history(envelope):
    source = envelope['source']; ids = envelope['value']['schedule']
    zero = lambda: dict.fromkeys(FIELDS, 0)
    if source['parent'] is None:
        baseline = [dict(id=key, logical_model_usage=dict.fromkeys((*FIELDS[:5], 'provider_cost_usd'), 0),
            logical_http_usage=dict(requests=0, measured_response_bytes=0, safety_accounted_bytes=0,
                                    unknown_transfer_upper_bytes=0)) for key in ids]
        measured = {phase: zero() for phase in old.PHASES}
        return dict(reused_prerequisites={p: measured[p] for p in old.PHASES[:3]},
            original_failed_exposure=dict(verified_by_phase=measured, physical_totals=zero(), unverified_native=[],
                actual_prior_model_calls=0, scope='Explicitly invented captures; no actual historical work'),
            baseline_resources=baseline, original_resources=None, original_phase_resources=None)
    state = encode(source['state']); payload = encode(source['parent'].payload)
    measured = {phase: state['semantic']['measured'].get(phase, zero()) for phase in old.PHASES}
    for row in measured.values():
        need(set(row) == set(FIELDS) and all(type(v) is int and v >= 0 for v in row.values()), 'Verified historical usage')
    return dict(reused_prerequisites={p: measured[p] for p in old.PHASES[:3]},
        original_failed_exposure=dict(verified_by_phase=measured,
            physical_totals={key: sum(row[key] for row in measured.values()) for key in FIELDS},
            unverified_native=[state['semantic']['failed_call']],
            scope='Whole earlier failed condition; includes reused prerequisites and sunk earlier repair work. '
                  'Raw reported failed-call usage is separate from verified totals.'),
        baseline_resources=payload['resources']['baseline_resources'], original_resources=payload['resources']['original_resources'],
        original_phase_resources=payload['resources']['phases'])


def _join(envelope):
    value = envelope['value']; source = envelope['source']; inputs = envelope['inputs']; ids = value['schedule']
    records = {key: [] for key in ('one_pass', *PHASES)}; evidence = {key: {} for key in records}
    cases = []; critics = []; source_cases = []; qualified_rows = []
    measured = {phase: dict.fromkeys(FIELDS, 0) for phase in PHASES}
    state = None if source['state'] is None else encode(source['state'])
    old_ids = set() if state is None else set(state['semantic']['physical_ids'])
    history = _history(envelope)
    for i, prepared in enumerate(source['prepared']):
        query, candidate, critic, context = (prepared[k] for k in ('query', 'prior', 'critic', 'context'))
        key = query['id']; need(key == ids[i], 'Complete original query order')
        if state is None:
            prior_sources = context['source_ancestry'].get('prior_sources', [])
            original_record = dict(id=key, producer_status=candidate['producer_status'],
                check_status=candidate['original_admission_status'], prediction=candidate['prediction'],
                reason=None if candidate['original_admission_status'] == 'accepted' else 'Invented prior capture: ' + candidate['producer_status'])
            source_case = dict(id=key, retained_dois=[], pool_dois=[], selected_dois=[],
                original_retained_dois=[], original_pool_dois=[], original_selected_dois=[],
                original_selected_sources=prior_sources, selected_sources=prepared['sources'],
                source_context_changed=prepared['sources'] != prior_sources, refinement_available=True,
                source_scope='invented', source_ancestry=context['source_ancestry'], acquisition_cutoff=value['cutoff'])
        else:
            baseline = state['baseline']['cases'][i]
            need(baseline['query'] == query, 'Unchanged original options')
            original_record = baseline['original_disposition']; prior_sources = baseline['original_selected_sources']
            source_case = state['semantic']['source_cases'][i]
        records['one_pass'].append(original_record); evidence['one_pass'][key] = [s['source_id'] for s in prior_sources]
        source_cases.append(source_case); physical = {}; accounting = {}
        critics.append(dict(id=key, native_status=critic['native_status'],
                            decoded=None if critic['decoded'] is None else dict(support=critic['decoded']['support'])))
        for task in PHASES:
            stage = envelope['phases'][task]; row = stage['rows'][i]; product = row['product']
            need(row['id'] == key and row['execution_id'] not in old_ids, 'New condition cannot reuse original native calls')
            cellroot = Path(stage['root']) / 'products' / f'{i:04d}'; actor = prepared['members'][task]
            cell = native.reconstruct_cell(cellroot, actor, execution_id=row['execution_id'],
                method_proof=value['method'], **envelope['model_contexts'][task])
            need(set(product) == {'call', 'native_proof', 'disposition', 'decision', 'paired_member_sha256',
                 'control_sha256', 'source_context_sha256'}, 'Exact independent new-cell products')
            call = product['call']; need(set(call) == {'root', 'summary', 'summary_proof'} and
                old.path(call['root']) == cellroot and call['summary_proof'] == stage['files'][f'products/{i:04d}/SUMMARY.json'] and
                inputs.json(call['summary_proof']) == call['summary'] == cell['summary'], 'Cell summary identity')
            raw_proof = None if cell['native_call_sha256'] is None else stage['files'][f'products/{i:04d}/native/native-response.bin']
            usage = joins._usage(cell)
            need(product['native_proof'] == raw_proof and row['accounting'] == usage and row['status'] == cell['summary']['status'] and
                row['reason'] == (None if row['status'] == 'completed' else row['status']), 'Independent native usage/disposition')
            checked = sources.disposition(query, cell, context)
            need(product['decision'] == stage['files'][f'products/{i:04d}/DECISION.json'] and
                inputs.json(product['decision']) == checked['decision'] and product['disposition'] == checked['disposition'] and
                product['paired_member_sha256'] == fingerprint(actor['prepared_member']) and
                product['control_sha256'] == prepared['control_sha256'] and product['source_context_sha256'] == fingerprint(context),
                'Independent current-source admission/control join')
            records[task].append(checked['disposition']); evidence[task][key] = [s['source_id'] for s in actor['sources']]
            physical[task] = row['execution_id']; accounting[task] = {field: usage[field] for field in FIELDS}
            for field in FIELDS: measured[task][field] += usage[field]
            qualified_rows.append(dict(phase=task, ordinal=i, id=key, status=row['status'],
                producer_status=checked['disposition']['producer_status'], check_status=checked['disposition']['check_status'],
                prediction=checked['disposition']['prediction']))
        cases.append(dict(id=key, original=original_record, repair=records['repair'][-1], removal=records['removal'][-1],
            critic=critic, semantic_selection=joins._selection(query, candidate, critic), physical_execution_ids=physical,
            accounting=accounting, control_sha256=prepared['control_sha256'], source_context_sha256=fingerprint(context)))
    for task in PHASES:
        need(measured[task] == envelope['phases'][task]['report']['accounting']['known_totals'], 'All new physical usage reconciles')
    physical = {field: sum(row[field] for row in measured.values()) for field in FIELDS}
    need(physical['generation_calls'] <= 2 * len(ids) and physical['source_http_requests'] == 0 and
        physical['measured_response_bytes'] == physical['safety_accounted_bytes'] == 0, 'New condition has no acquisition')
    logical_usage = {**history['reused_prerequisites'], **measured}
    logical = joins._logical_resources(dict(frame=dict(schedule=ids), resources=dict(baseline_resources=history['baseline_resources'])), logical_usage)
    logical['warning'] += ' Critic and acquisition are reused prerequisites; earlier repair outputs and costs are excluded.'
    qualified_rows.sort(key=lambda row: (PHASES.index(row['phase']), row['ordinal']))
    return dict(status='independently_reconstructed_evidence_first', purpose=value['purpose'], method_identity=value['method_identity'],
        queries=[row['query'] for row in source['prepared']], records=records, evidence_ids=evidence,
        critics=critics, source_cases=source_cases, case_products=cases, qualification_rows=qualified_rows,
        incremental_resources=dict(by_phase=measured, physical_totals=physical, provider_cost_usd=0, reused_original_work_included=False),
        logical_resources=logical, source_lineage_checked=True, native_calls_checked=True, cross_stage_products_checked=True,
        old_repair_outputs_adopted=False, scientific_support_verified=False), history


def reconstruct(descriptor):
    envelope = _envelope(encode(descriptor)); report, history = _join(envelope)
    source = envelope['source']; value = envelope['value']; inputs = envelope['inputs']; parent = source['parent']
    if parent is not None:
        original.revalidate(parent); payload = encode(parent.payload)
        original_start = payload['original_started_at_utc']; baseline = payload['baseline_acceptance']
        original_descriptor = payload['original_producer_descriptor']
    else:
        original_start = value['cutoff']; baseline = None
        original_descriptor = dict(kind='invented_qualification_ancestry', original_inspection=value['parent']['original_inspection'],
            bank=value['parent']['bank'], actual_prior_model_calls=0)
    # The original reference manifest itself remains unopened until evaluation.
    protocol = envelope['protocol']; declared_inputs = protocol['original_inputs']
    need(set(declared_inputs) == {'path', 'bytes', 'sha256'} and isinstance(declared_inputs['path'], str) and
         Path(declared_inputs['path']).is_absolute() and type(declared_inputs['bytes']) is int and
         declared_inputs['bytes'] > 0 and isinstance(declared_inputs['sha256'], str) and len(declared_inputs['sha256']) == 64 and
         all(c in '0123456789abcdef' for c in declared_inputs['sha256']),
         'Exact evaluation-only original input proof')
    endpoints = inputs.json(protocol['endpoints'])
    expected = joins.endpoint_contract(endpoints['declared_at_utc'], endpoints['implementation_note'], endpoints['endpoint_addendum'])
    need(endpoints == expected and old.historical.utc(endpoints['declared_at_utc']) <= old.historical.utc(original_start),
         'Original endpoints must precede original execution')
    for proof in (endpoints['implementation_note'], endpoints['endpoint_addendum']): inputs.bound(proof)
    summary = dict(frame=envelope['frame'], producer=envelope['producer'], baseline_acceptance=baseline, original_producer_descriptor=original_descriptor,
        original_started_at_utc=original_start, new_started_at_utc=envelope['started'],
        method=dict(proof=value['method'], identity=value['method_identity']), protocol=envelope['frame']['protocol'],
        protocol_declared_at_utc=protocol['created_at_utc'], endpoint_freeze=protocol['endpoints'], original_inputs=declared_inputs,
        resources=dict(phases=envelope['resources'], controller=envelope['controller'], new_work_wall_seconds=envelope['wall_seconds'], history=history,
            historical_work_reexecuted=False, old_repair_outputs_adopted=False),
        root_journal_verified=True, supervised_workers_verified=True, external_controller_supervision_verified=True,
        source_lineage_checked=True, native_calls_checked=True, cross_stage_products_checked=True)
    inputs.unchanged(); report = freeze(report); summary = freeze(summary)
    result = VerifiedEvidenceFirst(envelope['root'], envelope['receipt_sha256'], report, summary)
    _ISSUED[id(result)] = result
    _STATES[id(result)] = dict(fingerprint=fingerprint(dict(root=result.root, receipt_sha256=result.receipt_sha256,
        report=result.report, envelope=result.envelope)), closure=original.snapshot(inputs), parent=parent)
    weakref.finalize(result, _STATES.pop, id(result), None)
    return result


def qualify(value):
    """Compare frozen controls only after this exact execution capability was issued."""
    from . import qualification
    value = revalidate(value); bound = accepted_primary._Inputs()
    need(value.report['purpose'] == 'fictional_qualification' and len(value.report['queries']) == 6,
         'Six-case full independently reconstructed qualification required')
    wanted = bound.json(encode(value.envelope['protocol'])); frame = encode(value.envelope['frame']); prepared = bound.json(frame['plan'])
    bank_proof = wanted['bank']; need(prepared['parent']['bank'] == bank_proof, 'Fixed bank authority differs')
    bank_raw = bound.bound(bank_proof); bank = n.decode(bank_raw)
    approval = bound.json(wanted['owner_approval']); proposal = approval['proposal']
    proposal_proof, _ = bound.capture(proposal['path'])
    need(proposal_proof['sha256'] == proposal['sha256'] and proposal_proof == bank['decision'], 'Independently approved bank decision')
    documents = {}
    for role in bank['role_files'].values():
        proof = role['proof']; documents[Path(proof['path']).name] = bound.bound(proof)
    for name, role in bank['slots'].items(): documents[name] = bound.bound(role['proof'])
    metadata = qualification.validate_bank_bundle(bank_raw, documents, expected_bank_sha256=bank_proof['sha256'],
        expected_decision_sha256=proposal_proof['sha256'])
    qualification._compare_expectations(metadata, value.report['qualification_rows'])
    revalidate(value); bound.unchanged()
    _retain_closure(bound, _STATES[id(value)]['closure'])
    bound.unchanged()
    return freeze(dict(kind='sc05_evidence_first_qualification_acceptance_v1', status='passed', controls=12,
        execution=encode(value.envelope['producer']), protocol=encode(value.envelope['protocol']), method_identity=prepared['method_identity'],
        original_parent_identity=prepared['parent_identity'], native_integrity_verified=True, source_execution_verified=True,
        process_integrity_verified=True, all_frozen_expectations_matched=True, scientific_benchmark_scored=False,
        proof_closure=original.snapshot(bound)))


def _qualification_chronology(created_at, production_started_at, controller):
    created = datetime.fromisoformat(created_at); production = datetime.fromisoformat(production_started_at)
    observed = old.historical.utc(controller['reserved_at_utc']) + timedelta(seconds=controller['wall_seconds'])
    need(created.utcoffset() == production.utcoffset() == timedelta(0) and observed <= created <= production,
         'Recorded qualification acceptance must follow its observed execution and precede production')
    return dict(created_at_utc=created_at, production_started_at_utc=production_started_at,
                observed_terminal_clock_bound_utc=observed.isoformat(),
                scope='Recorded gate-acceptance chronology; not a cryptographic external-time attestation')


def accept_qualification(anchor, production_plan, protocol, *, production_started_at, inputs=None):
    """Reconstruct and join a qualified execution to a separately verified production plan."""
    bound = accepted_primary._Inputs(); record = bound.json(encode(anchor))
    need(set(record) == {'kind', 'status', 'created_at_utc', 'execution', 'protocol'} and
         record['kind'] == 'sc05_evidence_first_native_qualification_v1' and record['status'] == 'passed',
         'External native qualification execution anchor')
    value = reconstruct(record['execution']); declared = bound.json(record['protocol'])
    chronology = _qualification_chronology(record['created_at_utc'], production_started_at,
                                         value.envelope['resources']['controller'])
    wanted, planned = encode(protocol), encode(production_plan)
    need(declared == wanted and encode(value.envelope['protocol']) == record['protocol'], 'Qualification prospective protocol differs')
    prepared = bound.json(encode(value.envelope['frame']['plan']))
    need(planned['purpose'] == 'production' and len(planned['schedule']) == 199 and
         planned['parent_identity'] == prepared['parent_identity'] and planned['method_identity'] == prepared['method_identity'] and
         planned['code_files'] == prepared['code_files'] and planned['model'] == prepared['model'] and
         fingerprint(bound.json(planned['method'])) == value.report['method_identity'], 'Qualification cannot authorize a different method/source/model')
    result = qualify(value)
    _retain_closure(bound, result['proof_closure']); bound.unchanged()
    result = dict(encode(result), proof_closure=encode(original.snapshot(bound)), acceptance_chronology=chronology)
    if inputs is not None: _retain_closure(inputs, result['proof_closure'])
    return freeze(result)
