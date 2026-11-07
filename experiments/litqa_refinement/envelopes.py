"""Independent SC05 process, role and stage envelopes; no producer replay.

The original baseline is adopted from an externally accepted independent replay
after byte preservation checks. That adoption does not recalculate historical
semantics. New native/source semantics and scientific scoring are separate gates.
No archived source is executed and no model or network operation is dispatched.
"""
import os
from pathlib import Path
import sys
from uuid import UUID
import weakref

from experiments.litqa_analysis import accepted_primary, source_archive
from experiments.litqa_analysis import envelopes as historical
from experiments.litqa_analysis.recovered_envelope import _model, _memory
from experiments.litqa_analysis.native_records import canonical, decode, digest, need

REPO = Path(__file__).resolve().parents[2]
PHASES = ('critic', 'refinement_collect', 'pair_prepare', 'repair', 'removal')
PARENTS = dict(critic=(), refinement_collect=('critic',), pair_prepare=('critic', 'refinement_collect'),
               repair=('pair_prepare',), removal=('pair_prepare',))
MODEL_PHASES = ('critic', 'repair', 'removal')
FIELDS = ('generation_calls', 'measured_input_tokens', 'measured_output_tokens', 'reserved_input_tokens',
          'reserved_output_tokens', 'source_http_requests', 'measured_response_bytes', 'safety_accounted_bytes')
ALLOWED = dict(critic=('completed', 'capacity', 'codec_failure'), refinement_collect=('completed', 'unavailable'),
               pair_prepare=('completed',), repair=('completed', 'capacity', 'codec_failure'),
               removal=('completed', 'capacity', 'codec_failure'))
MODEL_RECEIPT = 'cc95c56ce1f497b36d6b9ed62b22721d8af7eaccc0a8c50da91439c5b076acbf'
CONFIGURATION = dict(seed=20261106, temperature=0.0, n_predict=256, context_tokens=16384, max_prompt_bytes=14000)
LAUNCHER = 'import runpy,sys;sys.path[:0]=sys.argv[1:4];sys.argv=["tether-sc05-worker"]+sys.argv[4:];runpy.run_module("experiments.litqa_refinement.run",run_name="__main__")'


def same(a, b): return canonical(a) == canonical(b)
def path(value): return accepted_primary._path(value)
def finite(value, label): return historical.nonnegative(value, label)
def fingerprint(value): return digest(canonical(value))


def _entry(inputs, root, files, name):
    source_archive._logical(name)
    need(name in files and files[name]['path'] == str(root / name), 'Missing or substituted envelope member')
    return inputs.json(files[name])


def _membership(root, files, directories):
    need({p.name for p in root.iterdir() if p.is_file()} == set(files) and
         {p.name for p in root.iterdir() if p.is_dir()} == set(directories), 'Unexpected envelope artifact membership')


def _reserved(event):
    details = event['details']
    need(event['event'] == 'build_reserved' and set(details) == {'run_id', 'owner_pid', 'created_at_utc'} and
         str(UUID(details['run_id'])) == details['run_id'] and type(details['owner_pid']) is int and
         details['owner_pid'] > 0, 'Invalid exclusive reservation')
    historical.utc(details['created_at_utc'])
    return details


def _events(inputs, proof): return accepted_primary._chain(inputs.bound(proof))


def _chronology(started, entered, phase, job):
    first, worker = historical.utc(started), historical.utc(entered)
    need(first <= worker, 'Worker reservation predates its root reservation')
    if phase == 'pair_prepare':
        need(first <= historical.utc(job['cutoff']) <= worker,
             'Source cutoff must be captured after root reservation and before pair-worker dispatch')


def _closure(inputs):
    names = []
    allowed = {'__init__.py', 'access.py', 'admission.py', 'cells.py', 'collection.py', 'contracts.py', 'model.py',
               'phase_checks.py', 'pipeline.py', 'projection.py', 'run.py', 'schedule.py', 'selection.py', 'transport.py'}
    for folder in ('src/tether_engine', 'packages/tether/src/tether', 'experiments/labbench',
                   'experiments/litqa_comparison', 'experiments/litqa_refinement'):
        for item in (REPO / folder).rglob('*'):
            if not item.is_file() or item.suffix not in ('.py', '.json') or 'tests' in item.parts or item.name.startswith('test_'):
                continue
            if folder.endswith('litqa_refinement') and item.name not in allowed: continue
            names.append(inputs.capture(item)[0])
    return sorted(names, key=lambda p: p['path'])


def _frame(value, root, inputs):
    fields = {'schema_version', 'kind', 'purpose', 'schedule', 'baseline', 'interpreter', 'code_files', 'phase_seconds',
              'port', 'alias', 'model_receipt', 'model_license', 'model_spec', 'model_provenance',
              'generation_configuration', 'qualification', 'provider_spend_usd', 'automatic_retry', 'output'}
    need(set(value) == fields and type(value['schema_version']) is int and value['schema_version'] == 1 and
         value['kind'] == 'sc05_refinement_execution_v1' and value['purpose'] in ('production', 'fictional_qualification'),
         'Refinement frame schema/purpose')
    ids = value['schedule']; count = 199 if value['purpose'] == 'production' else 2
    need(isinstance(ids, list) and len(ids) == len(set(ids)) == count and
         all(isinstance(i, str) and str(UUID(i)) == i for i in ids), 'Complete ordered refinement denominator')
    need(path(value['output']) == root and root.is_relative_to(REPO / 'data') and root != REPO / 'data', 'Frozen output root')
    need(same(value['code_files'], _closure(inputs)), 'Executed producer closure differs from current pinned sources')
    need(same(value['interpreter'], inputs.capture(sys.executable)[0]), 'Independent role audit requires exact worker interpreter')
    need(same(value['generation_configuration'], CONFIGURATION) and value['provider_spend_usd'] == 0 and
         value['automatic_retry'] is False, 'Generation, spending or retry policy differs')
    need(set(value['phase_seconds']) == set(PHASES) and all(type(s) is int and 120 <= s <= 43200
         for s in value['phase_seconds'].values()), 'Explicit bounded phase deadlines')
    need(type(value['port']) is int and 49152 <= value['port'] <= 65535 and
         value['alias'] == 'tether-sc05-refinement-qwen14b-v1' and value['model_receipt']['sha256'] == MODEL_RECEIPT,
         'Qualified model identity')
    if value['purpose'] == 'production':
        q = inputs.json(value['qualification'])
        need(q['kind'] == 'sc05_refinement_native_qualification_v1' and q['status'] == 'passed' and
             same(q['code_files'], value['code_files']) and same(q['model_provenance'], value['model_provenance']) and
             q['native_tasks'] == list(MODEL_PHASES) and q['automatic_retry'] is False, 'Production native qualification binding')
    else: need(value['qualification'] is None, 'Fictional qualification cannot inherit production authority')
    return _model({k: value[k] for k in ('model_receipt', 'model_license', 'port', 'alias', 'model_spec', 'model_provenance')}, inputs)


def _adopt(descriptor):
    need(isinstance(descriptor, dict) and set(descriptor) == {'replay_root', 'receipt_sha256', 'analyzer_archive'},
         'Separate externally pinned baseline acceptance required')
    result = accepted_primary.load(descriptor['replay_root'], descriptor['receipt_sha256'], analyzer_archive=descriptor['analyzer_archive'])
    need(result['status'] == accepted_primary.STATUS, 'Baseline acceptance adoption scope')
    return result


def _baseline(descriptor, frame, adopted, inputs):
    """Rebuild the role projection from preserved original artifacts, not labels."""
    need(set(descriptor) == {'root', 'receipt_sha256'}, 'Baseline descriptor fields')
    root = path(descriptor['root']); rp, receipt = inputs.anchored(root / 'RECEIPT.json', descriptor['receipt_sha256'])
    inventory = inputs.inventory(root, omit=('RECEIPT.json', 'COORDINATOR.json'))
    need(set(receipt) == {'kind', 'files', 'execution_descriptor', 'coordinator_activation_excluded'} and
         receipt['kind'] == 'tether_baseline_projection_receipt_v1' and receipt['coordinator_activation_excluded'] is True and
         same(receipt['files'], {n: {k: p[k] for k in ('bytes', 'sha256')} for n, p in inventory.items()}), 'Baseline projection receipt')
    _membership(root, ('BASELINE.json', 'RECEIPT.json', 'COORDINATOR.json'), ('cases',))
    manifest = inputs.json(inventory['BASELINE.json']); report = adopted['report']; original = path(report['root'])
    execution = dict(kind='sc05_original_execution_v1', role='original_sc04_execution', root=str(original), root_receipt_sha256=report['root_sha256'])
    need(receipt['execution_descriptor'] == execution and manifest['execution_descriptor'] == execution and
         manifest['schedule'] == frame['schedule'] and manifest['purpose'] == frame['purpose'] == report['purpose'] and
         same(manifest['queries'], report['queries']), 'Original accepted baseline identity/order differs')
    roles = {}
    def read(proof, role='original_execution_control'):
        value = inputs.bound(proof); roles[proof['path']] = dict(role=role, proof=proof)
        return value
    def json(proof, role='original_execution_control'): return decode(read(proof, role))
    original_receipt_proof, original_receipt = inputs.anchored(original / 'ROOT-RECEIPT.json', report['root_sha256'])
    read(original_receipt_proof)
    original_files = original_receipt['files']
    oframe = json(original_files['FRAME.json'])
    queries = json(oframe['query_products']['answer_queries'], 'visible_query')
    complete = json(original_files['COMPLETE.json'])
    need(same(queries, report['queries']) and original_receipt['frame_sha256'] == report['frame_sha256'], 'Accepted query/frame join')
    stages = {}
    for name in ('collect', 'answer'):
        anchor = json(original_files[name + '-ANCHOR.json']); proot = original / name
        pp, _ = inputs.anchored(proot / 'PACKAGE-RECEIPT.json', anchor['package_sha256']); package = json(pp)
        files = package['files']; stage = proot / 'worker/phase'
        stage_receipt = json(files['worker/phase/STAGE-RECEIPT.json'])
        def stage_read(member, role='original_execution_control', files=files):
            return json(files['worker/phase/' + member], role)
        config = stage_read('CONFIG.json')
        need(config['stage'] == name and config['ids'] == frame['schedule'], 'Original stage denominator')
        stages[name] = (stage, stage_receipt, files, stage_read)
    cases = []
    for ordinal, query in enumerate(queries):
        cr, cseal, cf, cread = stages['collect']; ar, aseal, af, aread = stages['answer']
        collected = cread(f'slots/{2 * ordinal:04d}.json'); answered = aread(f'slots/{4 * ordinal:04d}.json')
        for row, branch, index in ((collected, 'L', 2 * ordinal), (answered, 'L/O', 4 * ordinal)):
            need(row['id'] == query['id'] and row['branch'] == branch and row['ordinal'] == index and row['status'] == 'completed', 'Original L/O slot identity')
        source = collected['product']; sr = cr / 'products' / f'{2 * ordinal:04d}'
        need(source['root'] == str(sr), 'Original collection location')
        source_receipt = json(source['receipt'], 'raw_source_receipt'); source_proofs = []
        for name in source_receipt['files']:
            full = cf[f'worker/phase/products/{2 * ordinal:04d}/' + name]
            read(full, 'raw_source_parent'); source_proofs.append(dict(role='raw_source_parent', proof=full))
        # The acquisition MANIFEST was independently reconstructed in the accepted
        # replay, and its unchanged bytes are covered by that adoption.
        acq = inputs.json(cf[f'worker/phase/products/{2 * ordinal:04d}/MANIFEST.json'])
        prefix = f'products/{4 * ordinal:04d}/'
        inp = aread(prefix + 'INPUT.json', 'generated_candidate_control')
        context = aread(prefix + 'CONTEXT.json', 'original_source_context')
        summary = aread(prefix + 'SUMMARY.json', 'generated_candidate_control')
        disposition = answered['product']['disposition']
        need(same(disposition, report['records']['L/O'][ordinal]) and inp['query'] == query and inp['task'] == 'answer' and
             [s['source_id'] for s in inp['items']] == report['evidence_ids']['L/O'][query['id']], 'Accepted baseline disposition/source join')
        native_proofs = []
        for name in aseal['files']:
            if name.startswith(prefix) and (name.endswith('journal.jsonl') or name.startswith(prefix + 'native/')):
                full = af['worker/phase/' + name]; read(full, 'generated_candidate_control')
                native_proofs.append(dict(role='generated_candidate_control', proof=full))
        native_sha = None
        if summary['generation_entered']:
            native_sha = aseal['files'][prefix + 'native/native-response.bin']['sha256']
            for name in ('native/native-response.bin', 'native/request.json', 'native/payload.json'):
                aread(prefix + name, 'generated_candidate_control')
        candidate = dict(kind='model_generated_candidate_context_v1', id=query['id'], query_sha256=fingerprint(query),
            prediction=disposition['prediction'], producer_status=disposition['producer_status'],
            original_admission_status=disposition['check_status'], native_call_sha256=native_sha,
            generated_at_utc=None, is_scientific_evidence=False)
        cases.append(dict(id=query['id'], query=query, candidate=candidate, original_selected_sources=inp['items'],
            original_collection=dict(root=str(sr), receipt_sha256=source['receipt']['sha256'], plan=source['plan'], sources=acq['sources']),
            original_context=context, source_proofs=source_proofs, native_proofs=native_proofs, original_disposition=disposition,
            source_cutoff=complete['source_cutoff'], generation_time_unknown_reason='Archived execution has no exact generation timestamp',
            source_validation='reconstructed from original acquisition bytes', native_validation='coordinator accepted replay prerequisite'))
    expected = dict(kind='tether_baseline_projection_v1', execution_descriptor=execution, purpose=frame['purpose'],
        schedule=frame['schedule'], queries=queries, cases=cases, original_frame_sha256=report['frame_sha256'],
        role_files=list(roles.values()), scientific_correctness='not_read',
        scope='Original L/O role projection; independent accepted execution is a coordinator prerequisite')
    need(same(manifest, expected), 'Baseline projection differs from preserved accepted original artifacts')
    expected_files = {'BASELINE.json': manifest}
    for ordinal, case in enumerate(cases):
        for name, value in (('QUERY', case['query']), ('CANDIDATE', case['candidate']), ('SOURCES', case['original_selected_sources'])):
            expected_files[f'cases/{ordinal:04d}/{name}.json'] = value
    need(set(inventory) == set(expected_files), 'Baseline minimal file membership')
    for name, expected in expected_files.items(): need(same(inputs.json(inventory[name]), expected), 'Baseline projection content differs')
    grants = {p['path']: p for p in inventory.values()}; grants[rp['path']] = rp
    for row in manifest['role_files']:
        p = row['proof']; need(p['path'] not in grants or grants[p['path']] == p, 'Baseline conflicting proof'); grants[p['path']] = p
    return manifest, grants


def _limits(phase):
    model = phase in MODEL_PHASES; source = phase == 'refinement_collect'
    return dict(generation_calls=int(model), reserved_input_tokens=16128 if model else 0,
        reserved_output_tokens=256 if model else 0, source_http_requests=5 if source else 0,
        safety_accounted_bytes=8 * 1024 ** 2 if source else 0, provider_cost_usd=0)


def _accounting(value, phase, status):
    need(set(value) == set(FIELDS) | {'provider_cost_usd'} and all(type(value[k]) is int and value[k] >= 0 for k in FIELDS)
         and type(value['provider_cost_usd']) in (int, float) and value['provider_cost_usd'] == 0, 'Exact nonnegative cell accounting')
    caps = _limits(phase)
    need(all(value[k] <= caps[k] for k in caps) and value['measured_input_tokens'] <= value['reserved_input_tokens'] and
         value['measured_output_tokens'] <= value['reserved_output_tokens'] and value['measured_response_bytes'] <= value['safety_accounted_bytes'],
         'Measured/reserved accounting bounds')
    if value['generation_calls'] == 0: need(not any(value[k] for k in FIELDS[1:5]), 'No-generation token accounting')
    if phase in MODEL_PHASES:
        need(value['generation_calls'] == int(status != 'capacity') and (status == 'capacity' or value['reserved_output_tokens'] == 256), 'Native disposition accounting')
    if phase == 'refinement_collect':
        need((not any(value[k] for k in FIELDS)) if status == 'unavailable' else 2 <= value['source_http_requests'] <= 5, 'Collection disposition accounting')


def _stage(root, receipt_proof, phase, frame, job, inputs, *, worker_seconds, process_seconds):
    receipt = inputs.json(receipt_proof); files = inputs.inventory(root, omit=('STAGE-RECEIPT.json',))
    need(set(receipt) == {'kind', 'status', 'files', 'seal_elapsed_seconds', 'automatic_retry'} and
         receipt['kind'] == 'tether_refinement_stage_receipt_v1' and receipt['status'] == 'complete' and
         receipt['automatic_retry'] is False and same(receipt['files'], {n: {k:p[k] for k in ('bytes','sha256')} for n,p in files.items()}), 'Complete stage byte closure')
    config = _entry(inputs, root, files, 'CONFIG.json'); report = _entry(inputs, root, files, 'REPORT.json')
    data = _entry(inputs, root, files, 'INPUTS.json'); namespace = config['execution_namespace']
    need(str(UUID(namespace)) == namespace and config['kind'] == 'tether_refinement_stage_v1' and
         config['phase'] == phase and config['purpose'] == frame['purpose'] and config['ids'] == frame['schedule'] and
         config['cell_limits'] == _limits(phase), 'Stage identity, schedule and cell limits')
    ordered = [dict(ordinal=n, id=i, phase=phase, execution_id=f'{namespace}-{phase}-{n:04d}') for n,i in enumerate(frame['schedule'])]
    need(config['schedule'] == ordered and finite(config['seconds'], 'Stage budget') > 0 and config['seconds'] <= frame['phase_seconds'][phase], 'Fixed stage schedule/deadline')
    expected_inputs = dict(baseline=frame['baseline'], parents={n:dict(root=str(Path(d['root'])/'worker/phase'), receipt_sha256=d['stage_receipt_sha256']) for n,d in job['parents'].items()},
        cutoff=job['cutoff'], model_provenance=frame['model_provenance'], reference_keys_available=False, scoring_performed=False)
    need(same(data, expected_inputs), 'Stage exact role inputs')
    elapsed = finite(report['wall_seconds'], 'Stage elapsed'); seal = finite(receipt['seal_elapsed_seconds'], 'Stage sealing')
    need(elapsed <= seal < config['seconds'], 'Stage time accounting')
    need(seal <= worker_seconds <= process_seconds, 'Nested stage/worker/process elapsed order differs')
    rows = report['rows']; events = _events(inputs, files['journal.jsonl']); _reserved(events[0])
    expected_events = [('refinement_stage_configured', dict(config_sha256=fingerprint(config)))]
    need(len(rows) == len(ordered), 'All scheduled slots required')
    for row, slot in zip(rows, ordered):
        need(set(row) == set(slot) | {'status','reason','product','accounting'} and all(row[k] == v for k,v in slot.items()) and
             row['status'] in ALLOWED[phase] and row['product'] is not None, 'Stage slot disposition/identity')
        _accounting(row['accounting'], phase, row['status']); name = f'slots/{slot["ordinal"]:04d}.json'
        need(same(_entry(inputs, root, files, name), row), 'Stage slot/report binding')
        expected_events += [('refinement_slot_reserved', dict(slot=slot, limits=config['cell_limits'])),
            ('refinement_slot_terminal', dict(ordinal=slot['ordinal'], path=name, slot_sha256=fingerprint(row), status=row['status']))]
    rebuilt = dict(kind='tether_refinement_stage_report_v1', phase=phase, purpose=frame['purpose'], status='complete', scheduled=len(rows),
        entered=len(rows), unexecuted=0, rows=rows, wall_seconds=elapsed,
        accounting=dict(known_totals={k:sum(r['accounting'][k] for r in rows) for k in FIELDS}, provider_cost_usd=0,
            uncertain_cells=[], measurements_complete=True, uncertain_per_cell_ceiling=config['cell_limits'], historical_work_included=False), automatic_retry=False)
    need(same(report, rebuilt), 'Recomputed stage accounting differs')
    expected_events.append(('refinement_stage_finalized', dict(status='complete', report_sha256=fingerprint(report))))
    need([(e['event'],e['details']) for e in events[1:]] == expected_events, 'Stage exclusive reservation/terminal journal')
    return dict(root=str(root), rows=rows, inputs=data, report=report)


def _supervision(root, frame, frame_proof, job_proof, phase, inputs, files):
    command = [frame['interpreter']['path'], '-I', '-B', '-c', LAUNCHER, str(REPO), str(REPO/'src'), str(REPO/'packages/tether/src'),
        '--worker','--frame',frame_proof['path'],'--frame-sha256',frame_proof['sha256'],'--job',job_proof['path'],
        '--job-sha256',job_proof['sha256'],'--output',str(root/'worker')]
    need(_entry(inputs, root, files, 'COMMAND.json') == command, 'Exact phase command')
    wrapper = _entry(inputs, root, files, 'PROCESS.json'); record = wrapper['supervision']
    limits = dict(timeout_seconds=frame['phase_seconds'][phase]+60, max_output_bytes=4*1024**2)
    need(set(wrapper) == {'returncode','supervision'} and type(wrapper['returncode']) is int and wrapper['returncode'] == 0 and
         record['schema_version'] == 1 and record['method'] == 'tether.process_envelope.v1' and same(record['limits'],limits) and
         record['termination_reason'] == 'exited' and record['process_started'] is True and record['process_reaped'] is True and
         record['pipe_eof'] == dict(stdout=True,stderr=True) and record['cleanup_errors'] == [] and record['observed_counts_are_lower_bounds'] is False,
         'Complete successful process supervision')
    for stream in ('stdout','stderr'):
        size = len(inputs.bound(files[stream+'.bin']))
        need(type(record['retained_'+stream+'_bytes']) is int and size == record['retained_'+stream+'_bytes'] == record['observed_'+stream+'_bytes'], 'Captured process stream accounting')
    need(record['retained_stdout_bytes'] + record['retained_stderr_bytes'] <= limits['max_output_bytes'] and
         finite(record['execution_elapsed_seconds'],'Process elapsed') < limits['timeout_seconds'] and
         finite(record['total_elapsed_seconds'],'Total process elapsed') >= record['execution_elapsed_seconds'], 'Process resource bounds')
    return record, command, limits


def _audit(root, phase, frame, job, frame_proof, job_proof, model, rows, inputs, proof):
    raw = inputs.bound(proof); need(raw.endswith(b'\n'), 'Complete role audit required')
    records = [decode(line) for line in raw.splitlines()]; need(records, 'Nonempty role audit required')
    explicit = {frame_proof['path'],job_proof['path'],frame['model_receipt']['path'],frame['model_license']['path']} | {p['path'] for p in job['input_files']}
    shared = {p['path'] for p in frame['code_files']} | set(model['bindings'].values())
    runtime = (Path(sys.prefix).resolve(),Path(sys.base_prefix).resolve()); role = 'coordinator'; active = None; entered = []
    for item in records:
        if 'event' in item:
            if item['event'] == 'actor_entered':
                need(set(item) == {'event','role','output','coordinator_inputs_granted'} and role == 'coordinator' and
                     phase in MODEL_PHASES and item['role'] == phase and item['coordinator_inputs_granted'] is False, 'Exclusive model actor entry')
                ordinal = len(entered); need(ordinal < len(rows), 'Repeated model actor entry')
                active = root/'phase/products'/f'{ordinal:04d}'
                need(path(item['output']) == active, 'Actor may only own its scheduled cell')
                role=phase; entered.append(str(active))
            else:
                need(set(item) == {'event','role','output'} and item['event'] == 'actor_exited' and role == phase and
                     item['role'] == phase and item['output'] == str(active), 'Matched model actor exit')
                role='coordinator'; active=None
            continue
        need(item['role'] == role and item['allowed'] is True and type(item['flags']) is int, 'Recorded role/denial contradiction')
        if item['path'] is None:
            need(set(item) == {'path','descriptor','mode','flags','allowed','basis','role'} and type(item['descriptor']) is int and
                 item['descriptor'] >= 0 and item['basis'] == 'existing_descriptor', 'Existing descriptor audit schema')
            continue
        need(set(item) == {'path','mode','flags','allowed','basis','role'}, 'File audit schema')
        p = source_archive._absolute(item['path'])
        # Audit rows can include unsuccessful optional opens, so existence is not
        # required. Every existing ancestor is still checked for reparse aliases.
        current=p
        while not current.exists():
            need(current.parent != current, 'Audit path has no existing local ancestor')
            current=current.parent
        path(current)
        writing=bool(item['flags'] & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        own=p.is_relative_to(root if role=='coordinator' else active)
        common=str(p) in shared or any(p.is_relative_to(r) for r in runtime)
        granted=role=='coordinator' and str(p) in explicit
        basis='role_output' if own else 'code_model_runtime' if common and not writing else 'coordinator_input' if granted and not writing else 'denied'
        need(basis != 'denied' and item['basis'] == basis, 'Independent actor/coordinator path reclassification failed')
    need(role == 'coordinator' and len(entered) == (len(rows) if phase in MODEL_PHASES else 0), 'All actor scopes closed exactly once')
    return dict(recorded_operations=len(records), actor_cells=len(entered), denied_operations=0,
        scope='Recorded Python opens reclassified; no hostile native-code OS sandbox attestation')


class VerifiedEnvelope(dict):
    """Operation-scoped result; revalidation rejects copied or altered dictionaries."""


_ISSUED = {}


def _issue(result, inputs, adopted):
    identity = id(result)
    reference = weakref.ref(result, lambda ref: _ISSUED.pop(identity, None))
    _ISSUED[identity] = (reference, inputs, fingerprint(dict(result)), fingerprint(adopted))
    return result


def revalidate(envelope):
    issued = _ISSUED.get(id(envelope))
    need(type(envelope) is VerifiedEnvelope and issued is not None and issued[0]() is envelope and
         fingerprint(dict(envelope)) == issued[2], 'Envelope capability absent or mutated')
    issued[1].unchanged()
    adopted = _adopt(envelope['baseline_acceptance'])
    need(fingerprint(adopted) == issued[3], 'Original accepted reconstruction changed')
    return True


def reconstruct(descriptor, *, baseline_acceptance):
    need(isinstance(descriptor,dict) and set(descriptor)=={'root','receipt_sha256'}, 'Exact refinement root descriptor')
    inputs=accepted_primary._Inputs(); root=path(descriptor['root'])
    rp,receipt=inputs.anchored(root/'ROOT-RECEIPT.json',descriptor['receipt_sha256'])
    files=inputs.inventory(root,omit=('ROOT-RECEIPT.json',))
    need(set(receipt)=={'kind','status','frame_sha256','files'} and receipt['kind']=='sc05_refinement_root_receipt_v1' and
         receipt['status']=='refinement_execution_complete' and same(receipt['files'],files), 'Full recursive root receipt')
    need(not any(Path(n).name in ('FAILURE.json','DEADLINE.json','FINALIZATION-FAILED.json') for n in files), 'Completed envelope contains terminal failure')
    _membership(root, {'ROOT-RECEIPT.json','FRAME.json','COMPLETE.json','journal.jsonl'}|{p+'-ANCHOR.json' for p in PHASES}, PHASES)
    fp=files['FRAME.json']; frame=inputs.json(fp); need(receipt['frame_sha256']==fp['sha256'],'Root/frame receipt binding')
    model=_frame(frame,root,inputs); adopted=_adopt(baseline_acceptance)
    baseline,base_grants=_baseline(frame['baseline'],frame,adopted,inputs)
    complete=inputs.json(files['COMPLETE.json']); events=_events(inputs,files['journal.jsonl']); reservation=_reserved(events[0])
    need(set(complete)=={'status','purpose','phases','scheduled','wall_seconds','provider_cost_usd','scientific_scoring_performed','automatic_retry'} and
         complete['status']=='refinement_execution_complete' and complete['purpose']==frame['purpose'] and
         set(complete['phases'])==set(PHASES) and complete['scheduled']==len(frame['schedule']) and complete['provider_cost_usd']==0 and
         complete['scientific_scoring_performed'] is False and complete['automatic_retry'] is False,'Root terminal scope')
    phases={}; resources={}; contexts={}; expected_events=[]; prior_grants={}; physical=set(); process_seconds=0
    for phase in PHASES:
        pr=root/phase; anchor=complete['phases'][phase]
        need(set(anchor)=={'root','package_sha256','stage_receipt_sha256'} and anchor['root']==str(pr) and
             same(inputs.json(files[phase+'-ANCHOR.json']),anchor),'Exact phase anchor')
        pp=files[phase+'/PACKAGE-RECEIPT.json']; package=inputs.json(pp); pf=inputs.inventory(pr,omit=('PACKAGE-RECEIPT.json',))
        need(pp['sha256']==anchor['package_sha256'] and same(package,dict(kind='sc05_refinement_phase_receipt_v1',status='complete',
             phase=phase,frame_sha256=fp['sha256'],files=pf)),'Recursive phase receipt binding')
        _membership(pr,('JOB.json','COMMAND.json','PROCESS.json','stdout.bin','stderr.bin','PACKAGE-RECEIPT.json'),('worker',))
        jp=pf['JOB.json']; job=inputs.json(jp); expected_grants=dict(base_grants)
        for name in PARENTS[phase]:
            for key,p in prior_grants[name].items():
                need(key not in expected_grants or expected_grants[key]==p,'Conflicting predecessor proof'); expected_grants[key]=p
        expected_job=dict(phase=phase,frame_sha256=fp['sha256'],parents={n:complete['phases'][n] for n in PARENTS[phase]},
            input_files=[expected_grants[k] for k in sorted(expected_grants)],model_bindings=model['bindings'],cutoff=job['cutoff'] if phase=='pair_prepare' else None)
        need(same(job,expected_job),'Exact coordinator grants and required phase ancestry')
        if phase=='pair_prepare':historical.utc(job['cutoff'])
        for p in job['input_files']: inputs.bound(p)
        prior_grants[phase]=dict(expected_grants)
        prior_grants[phase].update({p['path']:p for p in pf.values()}); prior_grants[phase][pp['path']]=pp
        supervision,command,limits=_supervision(pr,frame,fp,jp,phase,inputs,pf); process_seconds+=supervision['execution_elapsed_seconds']
        expected_events += [('refinement_phase_reserved',dict(phase=phase,job=jp,command=command,limits=limits)),('refinement_phase_completed',dict(phase=phase,anchor=anchor))]
        wr=pr/'worker'; cfg=inputs.json(pf['worker/CONFIG.json']); terminal=inputs.json(pf['worker/COMPLETE.json'])
        we=_events(inputs,pf['worker/journal.jsonl']); worker_res=_reserved(we[0]); is_model=phase in MODEL_PHASES
        _chronology(reservation['created_at_utc'],worker_res['created_at_utc'],phase,job)
        _membership(wr,{'CONFIG.json','COMPLETE.json','MODEL.json','io-audit.jsonl','journal.jsonl'}|({'SERVER-RESOURCE-SAMPLES.json'} if is_model else set()),{'phase'}|({'server'} if is_model else set()))
        need(same(cfg,dict(frame_sha256=fp['sha256'],job_sha256=jp['sha256'],phase=phase,purpose=frame['purpose'],worker_pid=worker_res['owner_pid'],
             python_version=sys.version,coordinator_grants=job['input_files'])) and same(inputs.json(pf['worker/MODEL.json']),model),'Worker configuration/model binding')
        need(set(terminal)=={'status','phase','purpose','frame_sha256','stage_receipt','wall_seconds','worker_memory','server_terminal','audit_denials','provider_cost_usd','reference_keys_read','scientific_scoring_performed'} and
             terminal['status']=='complete' and terminal['phase']==phase and terminal['purpose']==frame['purpose'] and terminal['frame_sha256']==fp['sha256'] and
             type(terminal['audit_denials']) is int and terminal['audit_denials']==0 and terminal['provider_cost_usd']==0 and terminal['reference_keys_read'] is False and
             terminal['scientific_scoring_performed'] is False and finite(terminal['wall_seconds'],'Worker elapsed')<frame['phase_seconds'][phase], 'Worker terminal constraints')
        sp=pf['worker/phase/STAGE-RECEIPT.json']; need(sp==terminal['stage_receipt'] and sp['sha256']==anchor['stage_receipt_sha256'],'Worker/stage anchor')
        stage=_stage(wr/'phase',sp,phase,frame,job,inputs,worker_seconds=terminal['wall_seconds'],
            process_seconds=supervision['execution_elapsed_seconds']); phases[phase]=stage
        for row in stage['rows']:
            need(row['execution_id'] not in physical,'Repeated physical execution identifier'); physical.add(row['execution_id'])
        worker_events=[]; server=terminal['server_terminal']
        if is_model:
            _membership(wr/'server',('server-command.json','server.stdout.log','server.stderr.log'),())
            need(server['started'] is True and server['server_stopped'] is True and type(server['pid']) is int and server['pid']>0 and
                 type(server['exit_code']) is int and server['secondary_failures']==[] and 'error_class' not in server and
                 finite(server['elapsed_seconds'],'Server elapsed')<=terminal['wall_seconds'] and
                 same(inputs.json(pf['worker/server/server-command.json']),model['spec']),'Owned native lifecycle')
            worker_events=[('server_started',dict(pid=server['pid'])),('server_ready',dict(pid=server['pid'])),('server_terminal',server)]
            contexts[phase]=dict(model_provenance=model['provenance'],alias=model['alias'],owner_pid=server['pid'],endpoint=f'http://127.0.0.1:{frame["port"]}')
            samples=inputs.json(pf['worker/SERVER-RESOURCE-SAMPLES.json']); need(isinstance(samples,list) and 0<len(samples)<=100000,'Bounded native resource samples')
            for sample in samples:
                need(set(sample)=={'monotonic','value','error_class'} and (sample['error_class'] is None or isinstance(sample['error_class'],str)),'Resource sample schema')
                finite(sample['monotonic'],'Sample clock'); _memory(sample['value'])
        else: need(server is None,'Nonmodel phase has native lifecycle')
        worker_events.append(('refinement_worker_completed',dict(terminal_sha256=fingerprint(terminal))))
        need([(e['event'],e['details']) for e in we[1:]]==worker_events,'Worker/server journal reconciliation')
        audit=_audit(wr,phase,frame,job,fp,jp,model,stage['rows'],inputs,pf['worker/io-audit.jsonl'])
        resources[phase]=dict(supervision=supervision,worker_wall_seconds=terminal['wall_seconds'],worker_memory=_memory(terminal['worker_memory']),
            stage_accounting=stage['report']['accounting'],io_audit=audit,server_terminal=server)
    expected_events.append(('refinement_execution_completed',dict(phases=list(PHASES))))
    need([(e['event'],e['details']) for e in events[1:]]==expected_events,'Root phase dispatch/terminal reconciliation')
    wall=finite(complete['wall_seconds'],'Root wall time')
    need(process_seconds<=wall<=sum(s+60 for s in frame['phase_seconds'].values())+600,'Root wall/process accounting')
    inputs.unchanged()
    result=VerifiedEnvelope(root=str(root),root_receipt_sha256=rp['sha256'],frame=frame,phases=phases,baseline=baseline,
        model_contexts=contexts,started_at_utc=reservation['created_at_utc'],baseline_acceptance=decode(canonical(baseline_acceptance)),
        baseline_adoption=adopted['adoption'],supervised_root_verified=True,actor_roles_verified=True,baseline_verified=True,
        model_weight_bytes_rehashed=False,archived_code_executed=False,scientific_correctness_scored=False,
        resources=dict(phases=resources,new_work_wall_seconds=wall,original_resources=adopted['report']['resources'],
            baseline_resources=[dict(id=r['id'],logical_model_usage=r['logical_model_usage'],logical_http_usage=r['logical_http_usage']) for r in adopted['report']['source_cases']['L/O']],
            historical_work_reexecuted=False,physical_calls_shared_across_baselines=True),
        proofs=dict(root_receipt=rp,frame=fp,inputs=list(inputs.proofs.values())),
        scope='Independent byte/process/recorded-role/stage verification; historical baseline is retained independent reconstruction with byte recheck. New native/source semantics and scientific correctness require separate readers.')
    return _issue(result, inputs, adopted)
