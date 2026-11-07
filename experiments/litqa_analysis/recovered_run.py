"""Independent recovered-source and answer reconstruction, using stdlib readers.

External collection and answer-stage anchors are required. This layer does not
import the recovery producer, its admission code or its replay. Root supervision,
producer equivalence and authorization remain separate envelope gates; no scores,
reference answers, network clients or model execution are present here.
"""
from pathlib import Path
from urllib.parse import urlencode
from uuid import UUID

from . import collection, envelopes, lineage, native_records, source_archive, supplied_collection
from .native_records import canonical, decode, digest, journal, load, need, read, safe_path as _safe_path
from .reconstruct_run import call_descriptor, logical_usage, matching, text_usage
from .sources import selected_passages

PHASE = 'collect/worker/phase'
UNSURE = 'Insufficient information to answer the question'


def _same(left, right):
    """JSON identity distinguishes Boolean declarations from numeric counters."""
    return canonical(left) == canonical(right)


def safe_path(path):
    """Reject remote/traversing aliases before touching the filesystem."""
    return _safe_path(source_archive._absolute(str(path)))


class _Inputs:
    """Retain all observed anchors and recheck them before returning a result."""
    def __init__(self):
        self.proofs = {}
        self.inventories = []

    def proof(self, path):
        path = safe_path(path)
        raw = read(path)
        value = dict(path=str(path), bytes=len(raw), sha256=digest(raw))
        previous = self.proofs.setdefault(str(path), value)
        need(previous == value, 'Independent input changed between reads')
        return value

    def bound(self, proof):
        need(isinstance(proof, dict) and set(proof) == {'path', 'bytes', 'sha256'} and
             type(proof['bytes']) is int and proof['bytes'] >= 0, 'Exact independent input proof required')
        need(self.proof(proof['path']) == proof, 'Independent input proof mismatch')
        raw = read(proof['path'])
        need(len(raw) == proof['bytes'] and digest(raw) == proof['sha256'], 'Independent input changed after proof')
        return raw

    def json(self, proof): return decode(self.bound(proof))

    def inventory(self, root, omit=()):
        root = safe_path(root)
        values = envelopes.inventory(root, omit=omit)
        for value in values.values():
            need(self.proof(value['path']) == value, 'Independent inventory changed')
        self.inventories.append((root, tuple(omit), decode(canonical(values)), _directories(root)))
        return values

    def unchanged(self):
        for value in tuple(self.proofs.values()): self.bound(value)
        for root, omit, files, directories in self.inventories:
            need(_same(envelopes.inventory(root, omit=omit), files) and _directories(root) == directories,
                 'Independent inventory changed during reconstruction')


def _doi_plan(doi, policy):
    value = dict(kind='sc04_supplied_doi_plan_v1', doi=doi, policy=policy,
        metadata_url=collection.BASE+'search?'+urlencode(dict(query='DOI:"'+doi+'"',
            format='json', pageSize=10, resultType='core')),
        role='supplied_source_diagnostic', ordinary_retrieval=False)
    supplied_collection.query_plan(value)
    return value


def _query_inputs(frame, inputs):
    need(frame['kind'] == 'sc04_supplied_execution_v1' and frame['purpose'] in
         ('production', 'fictional_qualification') and frame['ordinary_retrieval'] is False and
         frame['automatic_retry'] is False and frame['provider_cost_usd'] == 0, 'Original source task role')
    need(set(frame['products']) == {'doi_schedule', 'answer_queries', 'hints'}, 'Original input roles')
    dois, queries, hints = (inputs.json(frame['products'][key]) for key in
                            ('doi_schedule', 'answer_queries', 'hints'))
    need(isinstance(dois, list) and 0 < len(dois) <= 190 and len(set(dois)) == len(dois) and
         isinstance(queries, list) and isinstance(hints, list) and 0 < len(queries) == len(hints) <= 199,
         'Bounded complete recovered task schedule')
    flattened, ids = [], []
    for q, h in zip(queries, hints):
        need(set(q) == {'id', 'question', 'choices'} and str(UUID(q['id'])) == q['id'] and
             isinstance(q['question'], str) and q['question'].strip(), 'Visible query identity only')
        need(isinstance(q['choices'], list) and 2 <= len(q['choices']) <= 26 and
             all(isinstance(c, str) and c.startswith(f'({chr(65+i)}) ') and c[4:].strip()
                 for i, c in enumerate(q['choices'])) and
             sum(c[4:] == UNSURE for c in q['choices']) == 1, 'Exact visible options')
        need(set(h) == {'id', 'question', 'dois'} and h['id'] == q['id'] and h['question'] == q['question'] and
             isinstance(h['dois'], list) and 1 <= len(h['dois']) <= 2 and len(set(h['dois'])) == len(h['dois']),
             'Exact source hint identity/role')
        ids.append(q['id']); flattened.extend(h['dois'])
    need(len(ids) == len(set(ids)) and list(dict.fromkeys(flattened)) == dois and
         (frame['unique_dois'], frame['questions'], frame['question_doi_pairs']) ==
         (len(dois), len(queries), len(flattened)), 'Full original question-to-DOI join')
    if frame['purpose'] == 'production':
        need((len(dois), len(queries), len(flattened)) == (190, 199, 205), 'Full production denominator')
    for doi in dois: _doi_plan(doi, frame['policy'])
    return dois, queries, hints


def _account(result):
    value = result['accounting']
    return dict(http_attempts=len(result['manifest']['requests']),
        **{k: value[k] for k in ('measured_response_bytes', 'safety_accounted_bytes', 'unknown_transfer_upper_bytes')},
        wire_bytes=None, provider_cost_usd=0)


def _total(rows):
    return dict(http_attempts=sum(r['accounting']['http_attempts'] for r in rows),
        measured_response_bytes=sum(r['accounting']['measured_response_bytes'] or 0 for r in rows),
        safety_accounted_bytes=sum(r['accounting']['safety_accounted_bytes'] for r in rows),
        unknown_transfer_upper_bytes=sum(r['accounting']['unknown_transfer_upper_bytes'] for r in rows),
        wire_bytes=None, provider_cost_usd=0)


def _reservation(event):
    d = event['details']
    need(event['event'] == 'build_reserved' and set(d) == {'created_at_utc', 'owner_pid', 'run_id'} and
         type(d['owner_pid']) is int and d['owner_pid'] > 0 and str(UUID(d['run_id'])) == d['run_id'],
         'Original reservation identity')
    envelopes.utc(d['created_at_utc'])


def _directories(root):
    return {p.relative_to(root).as_posix() for p in Path(root).rglob('*') if safe_path(p).is_dir()}


def _parent(planning, inputs):
    """Derive completed, uncertain and untouched slots from original raw journals."""
    parent = planning['plan']; audit = inputs.json(parent['interrupted_snapshot'])
    original = inputs.json(parent['original_frame']); root = safe_path(parent['original_root'])
    files = inputs.inventory(root)
    need(audit['schema_version'] == 1 and audit['kind'] == 'sc04_read_only_interrupted_attempt_audit' and
         audit['original_root'] == str(root) and audit['frame_proof'] == parent['original_frame'] and
         audit['externally_retained_anchors']['supplied_frame_sha256'] == parent['original_frame']['sha256'] and
         files == audit['original_inventory'] and inputs.json(files['FRAME.json']) == original,
         'Anchored original interrupted inventory/frame')
    dois, queries, hints = _query_inputs(original, inputs)
    roots = [journal(root/name) for name in ('journal.jsonl', 'collect/journal.jsonl', 'collect/worker/journal.jsonl')]
    for es in roots: _reservation(es[0])
    need([len(es) for es in roots] == [2, 2, 1] and roots[0][1]['event'] == 'diagnostic_phase_started' and
         roots[0][1]['details'] == {'phase': 'collect'} and roots[1][1]['event'] == 'diagnostic_worker_dispatch' and
         roots[1][1]['details'] == {'phase': 'collect'}, 'Original controller stopped during collection')
    config = inputs.json(files[PHASE+'/CONFIG.json']); events = journal(root/PHASE/'journal.jsonl')
    schedule = [dict(ordinal=i, id=d, branch='shared') for i, d in enumerate(dois)]
    need(_same(config, dict(kind='sc04_stage_v1', stage='supplied', ids=dois, schedule=schedule, seconds=config['seconds'])) and
         type(config['seconds']) in (int, float) and 0 < config['seconds'] <= original['phase_seconds']['collect'],
         'Original collection configuration')
    _reservation(events[0])
    need(events[1]['event'] == 'stage_configured' and events[1]['details'] ==
         dict(config_sha256=files[PHASE+'/CONFIG.json']['sha256']), 'Original stage configuration event')
    base = {'FRAME.json', 'journal.jsonl', 'collect/COMMAND.json', 'collect/JOB.json', 'collect/journal.jsonl',
        'collect/worker/CONFIG.json', 'collect/worker/io-audit.jsonl', 'collect/worker/journal.jsonl',
        PHASE+'/CONFIG.json', PHASE+'/journal.jsonl'}
    expected_files = set(base)
    expected_dirs = {'collect', 'collect/worker', PHASE, PHASE+'/products', PHASE+'/slots'}
    states = []; rebuilt = {}; active = None; cursor = 0
    job = inputs.json(files['collect/JOB.json'])
    need(set(job) == {'phase', 'frame_sha256', 'common_root', 'collection', 'cutoff', 'import_cache'} and
         job['phase'] == 'collect' and job['frame_sha256'] == parent['original_frame']['sha256'] and
         job['common_root'] == str(root) and job['collection'] is None and job['cutoff'] is None and
         inputs.json(files['collect/worker/CONFIG.json']) == dict(frame_sha256=job['frame_sha256'], job=job,
             purpose=original['purpose']), 'Original worker identity')
    command = inputs.json(files['collect/COMMAND.json']); argv = command['command']
    need(isinstance(argv, list) and len(argv) == 17, 'Original worker command shape')
    driver = Path(argv[5]); cache = driver.parents[2]/'data/cache'/('sc04-diagnostic-'+root.name+'-collect-imports')
    need(driver.is_absolute() and driver.parts[-3:] == ('experiments', 'litqa_supplied', 'run.py') and
         job['import_cache'] == str(cache) and argv == [original['python']['path'], '-I', '-B', '-X',
            'pycache_prefix='+str(cache), str(driver), 'worker', '--frame', parent['original_frame']['path'],
            '--frame-sha256', parent['original_frame']['sha256'], '--job', str(root/'collect/JOB.json'),
            '--job-sha256', files['collect/JOB.json']['sha256'], '--output', str(root/'collect/worker')] and
         command == dict(command=argv, limits=dict(max_output_bytes=4*1024**2,
             timeout_seconds=original['phase_seconds']['collect'])), 'Original command/frame/job binding')
    io = inputs.bound(files['collect/worker/io-audit.jsonl'])
    need(io and io.endswith(b'\n') and all(isinstance(decode(line), dict) for line in io.splitlines()),
         'Complete original retained I/O prefix')
    for event in events[2:]:
        if event['event'] == 'slot_reserved':
            need(active is None and cursor < len(schedule) and event['details'] == schedule[cursor],
                 'Original sequential one-shot reservation')
            active = cursor; cursor += 1
        else:
            need(event['event'] == 'slot_terminal' and active is not None, 'Original unsupported terminal/retry')
            name = PHASE+f'/slots/{active:04d}.json'; row = inputs.json(files[name]); prefix = PHASE+f'/products/{active:04d}'
            product = row['product']; doi_plan = _doi_plan(dois[active], original['policy'])
            need(_same(row, dict(**schedule[active], status='completed', reason=None, product=product)) and
                 product == dict(root=str(root/prefix), receipt=files[prefix+'/RECEIPT.json'],
                     manifest=files[prefix+'/MANIFEST.json'], plan=doi_plan) and
                 event['details'] == dict(ordinal=active, slot_sha256=files[name]['sha256'],
                     path=f'slots/{active:04d}.json', status='completed'), 'Original completed source slot binding')
            result = supplied_collection.reconstruct(product['root'], product['receipt']['sha256'], doi_plan)
            rebuilt[dois[active]] = result
            expected_files.update(prefix+'/'+n for n in inputs.json(product['receipt'])['files'])
            expected_files.update((name, prefix+'/RECEIPT.json'))
            expected_dirs.update((prefix, prefix+'/responses'))
            states.append(dict(**schedule[active], disposition='adopt_completed', dispatch_allowed=False,
                original_slot=files[name], product=product, coverage=result['coverage'], accounting=result['accounting']))
            active = None
    if active is not None:
        prefix = PHASE+f'/products/{active:04d}'; pp = files[prefix+'/PLAN.json']; jp = files[prefix+'/journal.jsonl']
        value = inputs.json(pp); es = journal(jp['path']); _reservation(es[0])
        reservation = dict(request_id='000', kind='metadata', url=value['metadata_url'],
                           byte_reservation=value['policy']['metadata_bytes'], transport_status='started')
        need(value == _doi_plan(dois[active], original['policy']) and len(es) == 3 and
             es[1]['event'] == 'plan_bound' and es[1]['details'] == dict(plan_sha256=pp['sha256']) and
             es[2]['event'] == 'http_attempt' and es[2]['details'] == reservation, 'Original uncertain request prefix')
        states.append(dict(**schedule[active], disposition='inherited_uncertain_metadata', dispatch_allowed=False,
            plan=pp, journal=jp, reservation=reservation, response_proof=None, terminal_proof=None,
            accounting=dict(measured_response_bytes=None, safety_accounted_bytes=reservation['byte_reservation'],
                            unknown_transfer_upper_bytes=reservation['byte_reservation'])))
        expected_files.update((prefix+'/PLAN.json', prefix+'/journal.jsonl'))
        expected_dirs.update((prefix, prefix+'/responses'))
    states.extend(dict(**s, disposition='untouched', dispatch_allowed=True) for s in schedule[cursor:])
    need(set(files) == expected_files and _directories(root) <= expected_dirs,
         'Unexplained original files or hidden answer/attempt')
    historical = [_account(rebuilt[s['id']]) for s in states if s['disposition'] == 'adopt_completed']
    if active is not None:
        historical.append(dict(http_attempts=1, **states[active]['accounting'], wire_bytes=None, provider_cost_usd=0))
    identity = digest(canonical(dict(original_frame_sha256=parent['original_frame']['sha256'],
                                    original_root_reservation_sha256=roots[0][0]['sha256'])))
    expected = dict(schema_version=2, kind='sc04_interrupted_collection_plan_v2', parent_identity=identity,
        original_root=str(root), interrupted_snapshot=parent['interrupted_snapshot'], original_frame=parent['original_frame'],
        original_root_reservation_sha256=roots[0][0]['sha256'], parent_inventory_sha256=digest(canonical(files)),
        original_journal_proofs={n:p for n,p in files.items() if n.endswith('/journal.jsonl') or n=='journal.jsonl'},
        input_proofs=original['products'], doi_schedule=dois, answer_queries=queries, hints=hints, slots=states,
        scheduled_dois=len(dois), scheduled_answers=len(queries), question_doi_pairs=sum(len(h['dois']) for h in hints),
        prior_answers=0, allowed_dispatch_ordinals=[s['ordinal'] for s in states if s['dispatch_allowed']],
        historical_accounting=_total([dict(accounting=a) for a in historical]),
        model_or_http_execution_performed=False, production_dispatch_qualified=False,
        scope='Read-only interrupted-source reconstruction; process absence, producer equivalence, recovery execution and scientific acceptance remain separate gates.')
    need(_same(parent, expected), 'Independently reconstructed parent plan differs')
    return parent, original, rebuilt


def _authority(frame, inputs):
    planning = inputs.json(frame['planning_frame']); authority = inputs.json(frame['planning_authority'])
    need(planning['kind'] == 'sc04_recovery_planning_authority_v2' and planning['schema_version'] == 2 and
         planning['automatic_retry'] is False and planning['production_dispatch_qualified'] is False, 'Planning authority role')
    parent, original, rebuilt = _parent(planning, inputs)
    policy = inputs.json(planning['registry_policy']); inputs.bound(planning['prospective_contract'])
    need(policy == dict(schema_version=1, kind='sc04_recovery_registry_binding_v1', parent_identity=parent['parent_identity'],
                        registry=planning['registry'], contract=planning['prospective_contract']), 'Canonical authority registry policy')
    authority_root = safe_path(Path(policy['registry'])/parent['parent_identity'])
    need(planning['authority'] == str(authority_root) and frame['planning_authority']['path'] == str(authority_root/'AUTHORITY.json') and
         authority == dict(kind='sc04_parent_continuation_authority_v2', parent_identity=parent['parent_identity'],
            frame=frame['planning_frame'], allowed_dispatch_ordinals=parent['allowed_dispatch_ordinals'],
            interrupted_snapshot=parent['interrupted_snapshot'], registry_policy=planning['registry_policy'],
            automatic_retry=False, production_dispatch_qualified=False), 'Exclusive original parent authority')
    p_root = safe_path(planning['output']); files = inputs.inventory(p_root)
    need(set(files) == {'FRAME.json', 'COMPLETE.json', 'journal.jsonl'} and files['FRAME.json'] == frame['planning_frame'],
         'Sealed planning artifact inventory')
    need(inputs.json(files['COMPLETE.json']) == dict(status='planning_authority_reserved', frame=frame['planning_frame'],
         authority=frame['planning_authority'], model_or_http_execution_performed=False, production_dispatch_qualified=False),
         'Planning completion anchors')
    es = journal(p_root/'journal.jsonl')
    need([e['event'] for e in es] == ['recovery_planning_output_reserved', 'parent_authority_reserved', 'planning_authority_sealed'] and
         es[1]['details'] == dict(authority=str(authority_root), frame_sha256=frame['planning_frame']['sha256']) and
         es[2]['details'] == dict(complete_sha256=files['COMPLETE.json']['sha256']), 'Planning authority journal')
    inputs.bound(planning['planner_source'])
    return parent, original, rebuilt, authority_root


def reconstruct_collection(root, expected_sha256, *, common_root, _inputs=None):
    """Independently verify all original/new DOI records, without producer replay."""
    inputs = _Inputs() if _inputs is None else _inputs
    root, common_root = safe_path(root), safe_path(common_root)
    receipt_proof = inputs.proof(root/'RECEIPT.json'); receipt = inputs.json(receipt_proof)
    need(receipt_proof['sha256'] == expected_sha256 and set(receipt) ==
         {'schema_version', 'kind', 'status', 'execution_frame', 'files'} and receipt['schema_version'] == 2 and
         receipt['kind'] == 'sc04_recovered_collection_receipt_v2' and receipt['status'] == 'complete', 'External recovered collection anchor/schema')
    files = inputs.inventory(root, omit=('RECEIPT.json',))
    need(files == receipt['files'], 'Recovered collection exact byte inventory')
    frame_proof = receipt['execution_frame']; frame = inputs.json(frame_proof)
    need(set(frame) == {'schema_version', 'kind', 'purpose', 'created_at_utc', 'planning_frame', 'planning_authority',
         'qualification', 'output', 'code_pins', 'python', 'policy', 'limits', 'automatic_retry', 'provider_cost_usd',
         'model_execution_permitted'} and inputs.bound(files['FRAME.json']) == inputs.bound(frame_proof) and frame['output'] == str(root) and
         frame['schema_version'] == 2 and frame['kind'] == 'sc04_recovered_collection_execution_v2' and
         frame['automatic_retry'] is False and frame['model_execution_permitted'] is False and frame['provider_cost_usd'] == 0,
         'Recovered execution frame policy')
    parent, original, rebuilt, authority = _authority(frame, inputs)
    need(root != common_root and root.is_relative_to(common_root) and
         Path(parent['original_root']) != common_root and Path(parent['original_root']).is_relative_to(common_root) and
         frame['purpose'] == original['purpose'] and frame['policy'] == original['policy'], 'Common roots and unchanged source policy')
    limits = frame['limits']; count = len(parent['allowed_dispatch_ordinals'])
    need(type(limits['phase_seconds']) is int and 0 < limits['phase_seconds'] <= 21600 and limits ==
         dict(phase_seconds=limits['phase_seconds'], doi_seconds=60, request_seconds=frame['policy']['request_seconds'],
              new_slots=count, new_http_attempts=2*count,
              new_response_reservation_bytes=count*(frame['policy']['metadata_bytes']+frame['policy']['article_bytes'])),
         'Recovered acquisition limits')
    qualification = inputs.json(frame['qualification'])
    need(qualification['schema_version'] == 2 and qualification['kind'] == 'sc04_recovery_collection_qualification_v2' and
         qualification['status'] == 'PASS' and qualification['tests'] > 0 and
         all(qualification[k] == 0 for k in ('failures', 'errors', 'skipped')) and
         qualification['code_pins'] == frame['code_pins'], 'Frozen collection qualification identity')
    repo = Path(__file__).resolve().parents[2]
    for name, sha in frame['code_pins'].items():
        need(inputs.proof(envelopes.child(repo, name))['sha256'] == sha, 'Recovered producer source pin differs')
    claim_proof = inputs.proof(authority/'collection-execution/CLAIM.json'); claim = inputs.json(claim_proof)
    need(claim == dict(kind='sc04_collection_execution_claim_v2', frame=frame_proof, output=str(root),
        parent_identity=parent['parent_identity'], allowed_dispatch_ordinals=parent['allowed_dispatch_ordinals'],
        created_at_utc=claim['created_at_utc'], automatic_retry=False), 'Exclusive collection execution claim')
    envelopes.utc(claim['created_at_utc'])
    es = journal(root/'journal.jsonl')
    need(es[0]['event'] == 'collection_output_reserved' and es[1]['event'] == 'collection_frame_verified' and
         es[1]['details'] == dict(frame_sha256=frame_proof['sha256'], parent_identity=parent['parent_identity']) and
         es[2]['event'] == 'collection_execution_claimed' and es[2]['details'] == dict(claim=claim_proof), 'Recovered collection reservation')
    cursor = 3; rows = []; expected_files = {'FRAME.json', 'MANIFEST.json', 'RESOURCES.json', 'COMPLETE.json', 'journal.jsonl'}
    expected_dirs = {'products', 'records'}
    for slot in parent['slots']:
        i, doi = slot['ordinal'], slot['id']; name = f'records/{i:04d}.json'; expected_files.add(name)
        row = inputs.json(files[name]); resolution = None
        if slot['disposition'] == 'inherited_uncertain_metadata':
            expected = dict(ordinal=i, id=doi, branch='shared', disposition=slot['disposition'], resolution=None,
                parent_proofs={k:slot[k] for k in ('plan', 'journal', 'reservation', 'response_proof', 'terminal_proof')},
                coverage=dict(exact_doi_resolved=None, article_retained=None, source_availability='unknown',
                    missingness='interrupted_metadata_transfer_without_retained_response', ordinary_retrieval=False),
                accounting=dict(http_attempts=1, **slot['accounting'], wire_bytes=None, provider_cost_usd=0))
            kind = 'slot_uncertainty_retained'; rebuilt[doi] = None
        else:
            if slot['disposition'] == 'adopt_completed':
                product = slot['product']; kind = 'slot_adopted'; disposition = 'adopt_completed'
                resolution = dict(root=product['root'], receipt_sha256=product['receipt']['sha256'], plan=product['plan'])
                parents = dict(original_slot=slot['original_slot'], receipt=product['receipt'], manifest=product['manifest'])
            else:
                need(slot['disposition'] == 'untouched' and slot['dispatch_allowed'] and
                     es[cursor]['event'] == 'slot_reserved' and es[cursor]['details'] == dict(ordinal=i, id=doi,
                        maximum_response_reservation_bytes=frame['policy']['metadata_bytes']+frame['policy']['article_bytes'], doi_seconds=60),
                     'Only original untouched DOI may receive one new reservation')
                cursor += 1; prefix = f'products/{i:04d}'; kind = 'slot_completed'; disposition = 'newly_completed'
                resolution = dict(root=str(root/prefix), receipt_sha256=files[prefix+'/RECEIPT.json']['sha256'],
                                  plan=_doi_plan(doi, frame['policy']))
                parents = dict(receipt=files[prefix+'/RECEIPT.json'], manifest=files[prefix+'/MANIFEST.json'])
                rebuilt[doi] = supplied_collection.reconstruct(resolution['root'], resolution['receipt_sha256'], resolution['plan'])
                expected_files.add(prefix+'/RECEIPT.json')
                expected_files.update(prefix+'/'+n for n in inputs.json(parents['receipt'])['files'])
                expected_dirs.update((prefix, prefix+'/responses'))
            result = rebuilt[doi]
            expected = dict(ordinal=i, id=doi, branch='shared', disposition=disposition, resolution=resolution,
                            parent_proofs=parents, coverage=result['coverage'], accounting=_account(result))
        need(_same(row, expected) and es[cursor]['event'] == kind and es[cursor]['details'] ==
             dict(ordinal=i, id=doi, record=files[name]), 'Independent recovered source row/journal differs')
        cursor += 1; rows.append(expected)
    manifest = inputs.json(files['MANIFEST.json']); cutoff = envelopes.utc(manifest['availability_cutoff'])
    for row in rows:
        if row['resolution'] is None: continue
        for request in rebuilt[row['id']]['manifest']['requests']:
            if request['transport_status'] == 'captured':
                proof = inputs.proof(Path(row['resolution']['root'])/request['receipt_path'])
                need(proof['sha256'] == request['receipt_sha256'] and
                     lineage.aware(inputs.json(proof)['completed_at_utc']) <= cutoff, 'Future recovered source receipt')
    historical = _total([r for r in rows if r['disposition'] != 'newly_completed'])
    accounting = dict(historical=historical, incremental=_total([r for r in rows if r['disposition'] == 'newly_completed']), total=_total(rows))
    need(historical == parent['historical_accounting'] and accounting['incremental']['http_attempts'] <= limits['new_http_attempts'] and
         accounting['incremental']['safety_accounted_bytes'] <= limits['new_response_reservation_bytes'], 'Recovery cumulative budgets')
    expected = dict(schema_version=2, kind='sc04_recovered_collection_v2', status='complete', execution_frame=frame_proof,
        planning_frame=frame['planning_frame'], parent_identity=parent['parent_identity'], original_root=parent['original_root'],
        doi_schedule=parent['doi_schedule'], answer_queries=parent['answer_queries'], hints=parent['hints'], records=rows,
        accounting=accounting, publication_cutoff=frame['policy']['cutoff_date'], availability_cutoff=cutoff.isoformat(),
        ordinary_retrieval=False, automatic_retry=False, provider_cost_usd=0, scientific_support_verified=False)
    need(_same(manifest, expected), 'Complete independently reconstructed recovered manifest')
    resources = inputs.json(files['RESOURCES.json'])
    need(_same(resources, dict(wall_seconds=resources['wall_seconds'], phase_seconds=limits['phase_seconds'], accounting=accounting,
         interruption_gap_seconds=None, original_stage_deadline_compliance_claimed=False, model_calls=0, provider_cost_usd=0)) and
         type(resources['wall_seconds']) in (int, float) and 0 <= resources['wall_seconds'] < limits['phase_seconds'],
         'Recovered collection physical resources')
    complete = inputs.json(files['COMPLETE.json'])
    need(complete == dict(status='complete', kind='sc04_recovered_collection_v2', manifest=files['MANIFEST.json'],
         resources=files['RESOURCES.json'], execution_claim=claim_proof, scientific_scoring_performed=False) and
         len(es) == cursor+1 and es[cursor]['event'] == 'collection_completed' and
         es[cursor]['details'] == dict(complete=files['COMPLETE.json']) and set(files) == expected_files and
         _directories(root) <= expected_dirs,
         'Recovered collection completion and exact product inventory')
    state = dict(root=str(root), common_root=str(common_root), receipt=receipt_proof, manifest=manifest)
    identity = dict(receipt=receipt_proof, manifest_sha256=digest(canonical(manifest)),
                    parent_identity=parent['parent_identity'], prepared_sha256=digest(canonical(state)))
    if _inputs is None: inputs.unchanged()
    return dict(manifest=manifest, by_doi={r['id']:r for r in rows}, reconstructions=rebuilt,
                identity=identity, purpose=original['purpose'], resources=resources, receipt=receipt_proof,
                frame_sha256=frame_proof['sha256'], source_lineage_checked=True)


def _context(query, hint, recovered, cutoff, model_provenance, configuration, code_proof, catalog_proof):
    rows = [recovered['by_doi'][d] for d in hint['dois']]
    sources, proofs, publications, articles, identities, available = [], [], {}, {}, {}, []
    descriptors, operational = {}, []
    for row in rows:
        doi = row['id']
        operational.append(dict(doi=doi, ordinal=row['ordinal'], disposition=row['disposition'],
            parent_proofs=row['parent_proofs'], accounting=row['accounting'], citable=False))
        if row['resolution'] is None:
            available.append(dict(doi=doi, coverage=row['coverage'], decisions=[], inherited_uncertainty=True,
                                  source_availability='unknown', source=None)); continue
        descriptors[doi] = row['resolution']; rebuilt = recovered['reconstructions'][doi]; manifest = rebuilt['manifest']; source = rebuilt['source']
        available.append(dict(doi=doi, coverage=rebuilt['coverage'], decisions=rebuilt['decisions']))
        if source is None: continue
        sid = source['source_id']; signature = digest(canonical(source))
        need(sid not in identities or identities[sid] == signature, 'Conflicting duplicate retained article')
        if sid not in identities: sources.append(source); identities[sid] = signature
        prefix = 'doi:'+digest(doi.encode())[:24]
        pp, reported = lineage.original_proofs(row['resolution']['root'], manifest, cutoff, prefix+':', prefix+':parsed', True)
        proofs.extend(pp); publications[doi] = reported[sid]; articles.update(rebuilt['articles'])
    pool = collection.pool(dict(id=query['id'], question=query['question']), sources); selected = collection.selection(pool['pool'])
    payload = dict(prompt=native_records.prompt(query, selected, native_records.instruction(code_proof)),
        seed=configuration['seed'], temperature=configuration['temperature'], n_predict=configuration['n_predict'],
        stop=['<|im_end|>'], stream=False, cache_prompt=False, grammar=native_records.grammar(query, selected))
    need(len(payload['prompt'].encode()) <= configuration['max_prompt_bytes'], 'Captured context exceeds common request capacity')
    request = dict(schema_version=1, kind='sc04_common_answer_local_v1', task='answer', query=query, sources=selected,
                   configuration=configuration, model_provenance=model_provenance, payload_sha256=digest(canonical(payload)))
    coverage = dict(annotated_dois=len(hint['dois']), retained_articles=len(sources), sources=available,
        selection_role='supplied_source_diagnostic', ordinary_retrieval=False,
        unknown_or_unavailable_inputs=[r['doi'] for r in available if r['coverage']['article_retained'] is not True],
        inherited_uncertain_inputs=[r['id'] for r in rows if r['resolution'] is None])
    context = dict(policy_kind='sc04_recovered_supplied_source_v2', diagnostic_only=True, ordinary_retrieval=False,
        query_sha256=digest(canonical(query)), hint_sha256=digest(canonical(hint)), full_hint=hint,
        selection_uses_reference_paper_identity=True, collection_identity=recovered['identity'], resolved_source_descriptors=descriptors,
        operational_provenance=operational, cutoff=lineage.aware(cutoff).isoformat(),
        catalog_sha256=digest(canonical(lineage.catalog(catalog_proof))), publications=publications, source_proofs=proofs,
        coverage=coverage, pool=pool, sources_sha256=digest(canonical(selected)), request_sha256=digest(canonical(request)),
        uncertainty_answer_policy='single_generation_empty_evidence_with_inherited_uncertainty_coverage', scientific_support_verified=False)
    selected_metrics = selected_passages(selected, pool['bindings'], articles)
    return dict(context=context, sources=selected, raw_sources=sources, request=request, source_metrics=selected_metrics,
        retained_dois=sorted({a['reconciled_doi'] for a in articles.values() if a['reconciled_doi']}),
        pool_dois=selected_passages(pool['pool'], pool['bindings'], articles)['selected_dois'])


def reconstruct(collection_root, collection_receipt_sha256, answer_root, answer_receipt_sha256, *,
                common_root, cutoff, model_provenance, alias, owner_pid, configuration,
                code_proof, catalog_proof, expected_endpoint=None):
    """Return aggregate-compatible records after independent source/native checks.

    The caller must separately qualify the enclosing supervised run and the
    producer arguments. A stage receipt proves bytes, not supervision or science.
    """
    inputs = _Inputs(); recovered = reconstruct_collection(collection_root, collection_receipt_sha256,
                                                          common_root=common_root, _inputs=inputs)
    cutoff = lineage.aware(cutoff).isoformat()
    need(lineage.aware(cutoff) >= lineage.aware(recovered['manifest']['availability_cutoff']), 'Answer before recovered availability')
    inputs.bound(code_proof); inputs.bound(catalog_proof)
    root = safe_path(answer_root); files = inputs.inventory(root); queries = recovered['manifest']['answer_queries']; hints = recovered['manifest']['hints']
    need(root.is_relative_to(safe_path(common_root)) and root != safe_path(common_root), 'Answer stage outside declared common root')
    rows = envelopes._stage(root, answer_receipt_sha256, [q['id'] for q in queries], ('shared',), 'supplied',
                           {'worker/phase/'+k:v for k,v in files.items()})
    config = dict(kind='sc04_recovered_answer_configuration_v2', collection_identity=recovered['identity'], cutoff=cutoff,
        question_ids=[q['id'] for q in queries], hint_sha256=digest(canonical(hints)), automatic_retry=False,
        ordinary_retrieval=False, provider_cost_usd=0, preflight='All source contexts must pass before any answer dispatch')
    need(_same(load(root/'RECOVERY.json'), config), 'Exact recovered answer configuration')
    preflight = journal(root/'preflight/journal.jsonl'); _reservation(preflight[0])
    need(len(preflight) == 2+2*len(queries) and preflight[-1]['event'] == 'all_contexts_checked' and
         preflight[-1]['details'] == dict(questions=len(queries)), 'Complete recovered source preflight')
    records, evidence_ids, cases, natives = [], {}, [], []
    expected_files = {'STAGE-RECEIPT.json', 'CONFIG.json', 'RECOVERY.json', 'REPORT.json', 'journal.jsonl', 'preflight/journal.jsonl'}
    for index, (query, hint, row) in enumerate(zip(queries, hints, rows)):
        cell = root/'products'/f'{index:04d}'; pre = f'preflight/{index:04d}.json'
        checked = _context(query, hint, recovered, cutoff, model_provenance, configuration, code_proof, catalog_proof)
        context = checked['context']
        need(_same(load(root/pre), context) and _same(load(cell/'CONTEXT.json'), context),
             'Independently reconstructed recovered context differs')
        started, completed = preflight[1+2*index:3+2*index]
        need(started['event'] == 'context_check_started' and started['details'] == dict(ordinal=index, id=query['id']) and
             completed['event'] == 'context_checked' and completed['details'] == dict(ordinal=index, context=files[pre]),
             'Preflight context proof/journal binding')
        native = native_records.reconstruct(cell, query, model_provenance=model_provenance, alias=alias,
            owner_pid=owner_pid, configuration=configuration, code_proof=code_proof, expected_endpoint=expected_endpoint)
        need(native['sources'] == checked['sources'] and
             (native['summary']['request_sha256'] is None or native['summary']['request_sha256'] == context['request_sha256']),
             'Native source/request differs from independent admitted context')
        disposition = lineage.disposition(query, native, context)
        matching(row, status='completed', reason=None, product=dict(call=call_descriptor(cell, native), **disposition,
            context=files[f'products/{index:04d}/CONTEXT.json'], hint_sha256=digest(canonical(hint)),
            collection_identity=recovered['identity'], diagnostic_only=True, recovery_contract='sc04_recovered_source_context_v2'))
        records.append(disposition['disposition']); evidence_ids[query['id']] = [s['source_id'] for s in checked['sources']]; natives.append(native)
        logical = _total([recovered['by_doi'][d] for d in hint['dois']])
        http = dict(requests=logical['http_attempts'], **{k:logical[k] for k in
                    ('measured_response_bytes', 'safety_accounted_bytes', 'unknown_transfer_upper_bytes')})
        cases.append(dict(id=query['id'], retained_dois=checked['retained_dois'], pool_dois=checked['pool_dois'],
            selected_dois=checked['source_metrics']['selected_dois'], source_coverage=context['coverage'],
            selected_bytes=checked['source_metrics']['selected_bytes'], selected_passages=len(checked['sources']),
            native_status=native['summary']['status'], logical_model_usage=logical_usage([native]), logical_http_usage=http,
            **text_usage(checked['raw_sources'], context['pool'])))
        expected_files.update((pre, f'slots/{index:04d}.json'))
        expected_files.update(f'products/{index:04d}/'+n for n in envelopes.inventory(cell))
    need(set(files) == expected_files, 'Unexpected recovered answer artifact')
    # Native-cell reconstruction already checks each physical token/response;
    # aggregate resource sums do not conflate unknown transferred bytes with zero.
    model_usage = {k:sum(logical_usage([n])[k] for n in natives) for k in logical_usage([])}
    model_usage['tokenizer_calls'] = sum(n['summary']['generation_entered'] for n in natives)
    resources = dict(collection=recovered['resources'], answer=dict(model=model_usage,
        wall_seconds=load(root/'REPORT.json')['wall_seconds']), provider_cost_usd=0,
        accounting_scope='Physical collection total includes historical captures, failed transfers and inherited uncertainty; logical per-question charges may repeat shared inputs.')
    inputs.unchanged()
    need(inputs.inventory(root) == files, 'Answer inventory changed during independent reconstruction')
    return dict(status='independently_reconstructed', root=str(root), root_sha256=answer_receipt_sha256,
        frame_sha256=recovered['frame_sha256'], purpose=recovered['purpose'], queries=queries,
        records={'supplied':records}, evidence_ids={'supplied':evidence_ids}, source_cases={'supplied':cases}, resources=resources,
        diagnostic_resolutions=[dict(doi=r['id'], coverage=r['coverage'], disposition=r['disposition'],
            decisions=recovered['reconstructions'][r['id']]['decisions'] if recovered['reconstructions'][r['id']] else [])
            for r in recovered['manifest']['records']], collection_identity=recovered['identity'],
        source_lineage_checked=True, native_calls_checked=True, cross_stage_products_checked=True,
        scientific_correctness_scored=False, model_weight_bytes_rehashed=False, supervised_root_verified=False,
        scope='Independent recovered collection, original source ancestry, selection, native answers and admission. Root supervision, producer equivalence, scientific correctness and entailment remain separate gates.')
