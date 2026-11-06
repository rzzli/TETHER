"""Independent BG05 reconstruction using only the Python standard library.

No producer controller, validator, policy helper or Inspect import is permitted.
The frozen oracle supplies normative answers; this reconstructs the independent
joins and arithmetic, not a second implementation of all biomedical policy.
"""
from collections import Counter
from datetime import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import re
import stat
import statistics as stats
import zipfile

NAN = object()
MISSING = object()
MAX_FILE = 512 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pairs(items):
    obj = {}
    for key, value in items:
        require(key not in obj, 'Duplicate JSON property: ' + key)
        obj[key] = value
    return obj


def forbidden_constant(value):
    raise ValueError('Nonfinite JSON value: ' + value)


def parse(raw):
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=forbidden_constant)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprint(value):
    return sha(canonical(value))


def safe(path):
    path = Path(path).absolute()
    for parent in (path, *path.parents):
        if parent.exists() or parent.is_symlink():
            info = parent.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                    'Linked/reparse path is not an independent input: ' + str(parent))
    return path


def inside(root, name):
    require(type(name) is str and name and ':' not in name and not name.startswith(('/', '\\')),
            'Unsafe inventory member')
    require(all(part not in ('', '.', '..') for part in name.replace('\\', '/').split('/')), 'Unsafe inventory component')
    root = safe(root); path = safe(root / name)
    require(path.is_relative_to(root), 'Inventory escapes root')
    return path


def read(path, pin=None, maximum=MAX_FILE):
    path = safe(path)
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, 'Nonregular/oversized independent input')
    identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns)
    with path.open('rb') as stream:
        import os
        require(identity(os.fstat(stream.fileno())) == identity(before), 'Input changed before read')
        raw = stream.read(before.st_size + 1)
        require(identity(os.fstat(stream.fileno())) == identity(before), 'Input changed during read')
    require(len(raw) == before.st_size and identity(path.stat()) == identity(before), 'Input changed after read')
    if pin is not None:
        expected = pin if type(pin) is str else pin['sha256']
        require(sha(raw) == expected, 'External input hash differs: ' + str(path))
        if isinstance(pin, dict) and 'bytes' in pin:
            require(type(pin['bytes']) is int and len(raw) == pin['bytes'], 'External input size differs')
    return raw


def load(path, pin=None):
    return parse(read(path, pin))


def verify_inventory(root, items, *, excluded=()):
    require(isinstance(items, dict), 'Inventory is not a mapping')
    for name, pin in items.items():
        read(inside(root, name), pin)
    actual = {p.relative_to(root).as_posix() for p in Path(root).rglob('*') if p.is_file()}
    require(actual == set(items) | set(excluded), 'Sealed inventory missing/extra files')
    return {'files': len(items), 'bytes': sum(row['bytes'] for row in items.values())}


def chain(raw):
    require(raw.endswith(b'\n'), 'Unterminated sealed journal')
    rows = []; previous = '0' * 64
    for number, line in enumerate(raw.splitlines()):
        row = parse(line)
        require(set(row) == {'sequence', 'previous_sha256', 'at_utc', 'event', 'details', 'sha256'}, 'Journal schema differs')
        require(type(row['sequence']) is int and row['sequence'] == number and row['previous_sha256'] == previous,
                'Journal chain sequence differs')
        require(row['sha256'] == fingerprint({k: v for k, v in row.items() if k != 'sha256'}), 'Journal event hash differs')
        when = datetime.fromisoformat(row['at_utc'].replace('Z', '+00:00'))
        require(when.tzinfo is not None and when.utcoffset() is not None, 'Journal time is not aware')
        previous = row['sha256']; rows.append(row)
    require(bool(rows), 'Empty journal')
    return rows


def sealed_record(root, external_receipt_sha256, expected_request):
    root = safe(root)
    receipt = load(root / 'receipt.json', external_receipt_sha256)
    require(set(receipt) == {'schema_version', 'kind', 'request', 'result', 'journal', 'terminal_chain_sha256'}
            and receipt['schema_version'] == 1 and receipt['kind'] == 'inspect_policy_case', 'Case receipt schema differs')
    request = load(root / 'request.json', receipt['request'])
    result = load(root / 'result.json', receipt['result'])
    events = chain(read(root / 'journal.jsonl', receipt['journal']))
    require(canonical(request) == canonical(expected_request), 'Case request differs from frozen schedule')
    require(events[0]['event'] == 'reserved' and events[0]['details'] == {'request_sha256': fingerprint(request)},
            'Initial reservation/request mismatch')
    require(sum(e['event'] == 'terminal' for e in events) == 1 and events[-1]['event'] == 'terminal'
            and events[-1]['details'] == {'result': receipt['result']}
            and events[-1]['sha256'] == receipt['terminal_chain_sha256'], 'Terminal/result binding differs')
    return {'request': request, 'result': result, 'events': events, 'receipt': receipt}


def case_record(root, external_receipt_sha256, expected_request):
    record = sealed_record(root, external_receipt_sha256, expected_request)
    result = record['result']; ident = expected_request['control_id']
    require(result['control_id'] == ident, 'Case result identity differs')
    if result.get('decision') is not None:
        require(result['decision']['control_id'] == ident, 'Nested policy identity differs')
    if 'source_descriptor_proof' in result:
        require(canonical(result['source_descriptor_proof']) == canonical(expected_request['descriptor']), 'Result source descriptor differs')
    return record


def parse_native(raw):
    def native_constant(value):
        require(value == 'NaN', 'Native infinity is not an unscored sentinel')
        return NAN
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=native_constant)
    def walk(item, path=()):
        if item is NAN:
            require(path and path[-1] == 'value' and any(part in ('scores', 'metrics', 'score') for part in path),
                    'Native NaN outside a score/metric value')
        elif isinstance(item, dict):
            for key, child in item.items(): walk(child, path + (key,))
        elif isinstance(item, list):
            for index, child in enumerate(item): walk(child, path + (index,))
        elif type(item) is float:
            require(math.isfinite(item), 'Nonfinite native number')
    walk(value)
    return value


def native_log(path):
    raw = read(path)
    if raw[:2] == b'PK':
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            names = [x.filename for x in entries]
            require(len(names) == len(set(names)), 'Repeated native ZIP members not qualified for this no-retry study')
            require(sum(x.file_size for x in entries) <= MAX_FILE, 'Native log expansion exceeds cap')
            require('header.json' in names, 'Native eval header absent')
            header = parse_native(archive.read('header.json'))
            samples = [parse_native(archive.read(name)) for name in names if re.fullmatch(r'samples/.+_epoch_\d+\.json', name)]
    else:
        header = parse_native(raw)
        samples = header.get('samples', [])
    require(type(samples) is list, 'Native sample array missing')
    identities = [(s['id'], s['epoch']) for s in samples]
    require(len(identities) == len(set(identities)), 'Duplicate native sample/epoch')
    require(all(type(epoch) is int and epoch == 1 for _, epoch in identities), 'Unexpected native repetition')
    return {'header': {k: v for k, v in header.items() if k != 'samples'}, 'samples': [resolve_sample(s) for s in samples]}


def resolve_sample(sample):
    """Resolve native dedup references from the same externally sealed bytes."""
    attachments=sample.get('attachments',{})
    def walk(value,active=()):
        if type(value) is str and value.startswith('attachment://'):
            key=value[len('attachment://'):]
            require(key in attachments and key not in active,'Missing/cyclic native attachment')
            return walk(attachments[key],active+(key,))
        if isinstance(value,list):return [walk(v,active) for v in value]
        if isinstance(value,dict):return {k:walk(v,active) for k,v in value.items()}
        return value
    return {key:(value if key=='attachments' else walk(value)) for key,value in sample.items()}


def is_unscored(score):
    return score.get('value') is NAN or score.get('value') is None


def observable(source, name):
    if name in ('admitted_observation_ids', 'eligible_observation_ids', 'selected_observation_ids', 'scorer_preflight'):
        return source.get(name, MISSING)
    if name.startswith('prediction_'):
        return source.get('prediction', {}).get(name[len('prediction_'):], MISSING)
    if name == 'probability_is_null':
        prediction = source.get('prediction', {})
        return prediction['probability'] is None if 'probability' in prediction else MISSING
    if name in ('feature_values', 'feature_status', 'dependency_groups'):
        values = source.get('features', {}).get('values')
        if not isinstance(values, dict): return MISSING
        field = {'feature_values':'value', 'feature_status':'status', 'dependency_groups':'dependency_groups'}[name]
        return {key: row.get(field, MISSING) for key, row in values.items()}
    if name == 'exclusion_reasons':
        return [row['reason'] for row in source['exclusions']] if 'exclusions' in source else MISSING
    if name == 'dispatches': return source.get('calls', MISSING)
    if name == 'accounting_basis':
        if 'accounting' not in source: return MISSING
        values = sorted(set(row['basis'] for row in source['accounting']))
        return values[0] if len(values) == 1 else values
    if name == 'later_dispatches':
        return len(source['dispatches']) - 1 if source.get('dispatches') else MISSING
    if name == 'unresolved_attempts': return source.get('recovery', {}).get(name, MISSING)
    if name == 'recovery_may_dispatch':
        text = source.get('recovery', {}).get('recovery_action', '')
        return False if text.startswith('inspect only;') and 'never automatically repeat' in text else MISSING
    raise ValueError('Unknown normative observable: ' + name)


def same(actual, expected):
    if actual is MISSING: return False
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(same(actual.get(k, MISSING), v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(same(a,b) for a,b in zip(actual,expected))
    return canonical(actual) == canonical(expected)


def compare(actual, expected):
    require(actual['control_id'] == expected['control_id'], 'Policy/oracle identity differs')
    verdict = actual['decision'] in ('accept', 'reject', 'inspect_only')
    if not verdict:
        return {'has_verdict':False,'decision_match':False,'observable_match':False,
                'full_match':False,'mismatches':[],'reason':actual['decision']}
    decision_match = verdict and actual['decision'] == expected['decision']
    misses = [key for key, value in expected['observables'].items() if not same(observable(actual['observables'], key), value)]
    return {'has_verdict': verdict, 'decision_match': decision_match,
            'observable_match': verdict and not misses, 'full_match': decision_match and not misses,
            'mismatches': misses, 'reason':None}


def native_archive_join(sample, request, result, expected):
    ident = expected['control_id']
    require(sample['id'] == ident == request['control_id'] == result['control_id'], 'Native case identity differs')
    require(sample['epoch'] == 1 and sample['target'] == '', 'Native epoch/target isolation differs')
    require(sample['input'] == canonical(request).decode(), 'Native input differs from frozen request')
    require(not sample.get('error_retries'), 'Native retries are outside the frozen schedule')
    require(not sample.get('model_usage') and not sample.get('turn_count'), 'Archive task unexpectedly generated model output')
    for event in sample.get('events', []):
        require(event['event'] != 'model', 'Archive sample contains provider/model event')
        if event['event'] == 'sample_init':
            require(event['sample']['id'] == ident and event['sample']['target'] == ''
                    and event['sample']['input'] == sample['input'], 'Native initialization differs')
        if event['event'] == 'score':
            require(event.get('target', '') == '', 'Native scorer target contains oracle data')
    if result['status'] != 'completed':
        return {'native_correct': False, 'native_error': bool(sample.get('error')), 'native_unscored': not sample.get('scores')}
    completion = sample.get('output', {}).get('completion')
    require(completion == canonical(result).decode(), 'Native completion/retained candidate differs')
    choices = sample.get('output', {}).get('choices', [])
    require(len(choices) == 1 and choices[0]['message']['content'] == completion, 'Native message/completion differs')
    comparison = compare(result['decision'], expected)
    scores = sample.get('scores') or {}
    if sample.get('error') or not scores:
        return {'native_correct': False, 'native_error': bool(sample.get('error')), 'native_unscored': True}
    require(len(scores) == 1, 'Multiple native scores not in this task')
    score = next(iter(scores.values()))
    if not comparison['has_verdict']:
        require(is_unscored(score), 'Unsupported/error credited as a scored verdict')
        return {'native_correct': False, 'native_error': False, 'native_unscored': True}
    expected_score = 'C' if comparison['full_match'] else 'I'
    require(score['value'] == expected_score and score.get('answer') == result['decision']['decision'], 'Native score contradicts independent projection')
    return {'native_correct': comparison['full_match'], 'native_error': False, 'native_unscored': False}


def aggregate(expected, rows):
    oracle = {row['control_id']: row for row in expected}
    require(len(oracle) == len(expected) and len(oracle) > 0, 'Unique nonempty expected schedule required')
    actual = {row['control_id']: row for row in rows}
    require(len(actual) == len(rows) and set(actual) <= set(oracle), 'Duplicate or unscheduled result')
    counts = {'scheduled': len(oracle), 'full_match': 0, 'decision_match': 0, 'missing': 0,
              'errors': 0, 'unsupported': 0, 'false_admissions': 0, 'false_rejections': 0,
              'expected_accept': 0, 'expected_reject': 0, 'expected_inspect_only': 0}
    for ident, gold in oracle.items():
        counts['expected_' + gold['decision']] += 1
        row = actual.get(ident)
        if row is None or row['status'] in ('unstarted', 'missing'):
            counts['missing'] += 1; continue
        if row['status'] != 'completed' or row['native_decision'] == 'error': counts['errors'] += 1
        if row['native_decision'] == 'unsupported': counts['unsupported'] += 1
        completed = row['status'] == 'completed'
        counts['full_match'] += int(completed and row['full_match'])
        counts['decision_match'] += int(completed and row['decision_match'])
        counts['false_admissions'] += int(completed and gold['decision'] == 'reject' and row['native_decision'] == 'accept')
        counts['false_rejections'] += int(completed and gold['decision'] == 'accept' and row['native_decision'] == 'reject')
    counts['full_match_rate'] = counts['full_match'] / counts['scheduled']
    counts['decision_match_rate'] = counts['decision_match'] / counts['scheduled']
    return counts


def statistics(values):
    require(all(type(v) in (int,float) and math.isfinite(v) and v >= 0 for v in values), 'Invalid measured time')
    return {'count': len(values), 'sum': sum(values), 'median': stats.median(values) if values else None,
            'minimum': min(values) if values else None, 'maximum': max(values) if values else None}


def successful_supervision(report, limits, stdout_size, stderr_size):
    require(report['schema_version']==1 and report['method']=='tether.process_envelope.v1'
            and report['limits']==limits and report['termination_reason']=='exited','Successful process identity differs')
    require(report['process_started'] is True and report['process_reaped'] is True
            and report['observed_counts_are_lower_bounds'] is False
            and report['pipe_eof']=={'stdout':True,'stderr':True} and report['cleanup_errors']==[],
            'Successful process cleanup/EOF differs')
    statistics([report['execution_elapsed_seconds'],report['total_elapsed_seconds']])
    require(report['execution_elapsed_seconds']<limits['timeout_seconds']
            and report['total_elapsed_seconds']>=report['execution_elapsed_seconds'],'Successful process clock differs')
    require(stdout_size+stderr_size<=limits['max_output_bytes'],'Process output exceeds frozen cap')
    for stream,count in (('stdout',stdout_size),('stderr',stderr_size)):
        for kind in ('observed','retained'):
            value=report[kind+'_'+stream+'_bytes']
            require(type(value) is int and value==count,'Process stream count differs')


def primary_counts(expected, records):
    """Rebuild the producer's published count names independently."""
    gold = {row['control_id']:row for row in expected}
    require(len(records) == len(gold) and {r['control_id'] for r in records} == set(gold), 'Primary schedule differs')
    counts = dict(scheduled=len(records), completed=0, full_conformance=0, decision_match=0,
                  correct_rejection=0, false_admission=0, false_rejection=0, unscored=0)
    cases = []
    for record in records:
        ident = record['control_id']; expected_row = gold[ident]
        finished = record['status'] == 'completed'
        available = finished and record['decision'] is not None
        decision = record['decision']['decision'] if available else None
        matched = compare(record['decision'], expected_row) if available else {
            'has_verdict':False,'decision_match':False,'full_match':False}
        counts['completed'] += int(finished)
        counts['full_conformance'] += int(matched['full_match'])
        counts['decision_match'] += int(matched['decision_match'])
        counts['unscored'] += int(not matched['has_verdict'])
        counts['correct_rejection'] += int(decision == expected_row['decision'] == 'reject')
        counts['false_admission'] += int(expected_row['decision'] == 'reject' and decision == 'accept')
        counts['false_rejection'] += int(expected_row['decision'] == 'accept' and decision == 'reject')
        cases.append({'control_id':ident,'status':record['status'],'expected_decision':expected_row['decision'],
                      'actual_decision':decision,**matched})
    return {**counts, 'full_conformance_per_scheduled':counts['full_conformance']/len(records),
            'status_counts':dict(Counter(r['status'] for r in records)), 'cases':cases}


def check_audit_record(frozen,result,events):
    if 'batch_input_pins' not in frozen:
        require('source_integrity' not in result,'Legacy freeze unexpectedly uses changed audit contract')
        return {'scheme':'legacy_full_per_batch','retained_integrity_passed':None}
    pins=frozen['input_pins'];batch=frozen['batch_input_pins']
    require(all(name in pins and pin==pins[name] for name,pin in batch.items()),'Batch audit pin differs from complete closure')
    integrity=result['source_integrity']
    require(integrity['scope']==frozen['audit_scope'],'Audit scope declaration differs')
    for name in ('global_preflight','global_postflight'):
        value=integrity.get(name)
        matched=[e['details'] for e in events if e['event']=='global_source_'+name.removeprefix('global_')]
        if value is None:require(not matched,'Absent source audit has journal success')
        else:
            require(len(matched)==1 and matched[0]==value,'Source audit differs from journal')
            require(value['files']==len(pins) and value['logical_bytes']==sum(p['bytes'] for p in pins.values()),'Global audit inventory size differs')
    require(integrity['status'] in ('passed','failed'),'Unfinished global source audit')
    if integrity['status']=='passed':
        require(integrity['global_preflight'] is not None and integrity['global_postflight'] is not None,'Passed integrity lacks both boundaries')
    else:
        require(result['status']=='partial','Source-integrity failure mislabeled as completed study')
        if integrity.get('error'):
            failed=[e['details'] for e in events if e['event']=='global_source_postflight_failed']
            require(failed==[{'error':integrity['error']}],'Source failure differs from journal')
    return {'scheme':'full_global_brackets_and_bounded_batch_checks','retained_integrity_passed':integrity['status']=='passed',
            'batch_pin_files':len(batch),'full_pin_files':len(pins),'scope':integrity['scope']}


def verify_source_archive(frozen,freeze_path):
    if 'source_archive' not in frozen:return None
    root=Path(freeze_path).parent/'source-archive'
    index=load(root/'INDEX.json',frozen['input_pins'][str(root/'INDEX.json')])
    require(index=={'schema_version':1,'files':frozen['source_archive']},'Archived source index differs from freeze')
    expected={'INDEX.json'}
    for original,pin in frozen['source_archive'].items():
        plain={key:pin[key] for key in ('sha256','bytes')}
        require(frozen['input_pins'].get(original)==plain,'Archived original source pin differs')
        path=inside(root,pin['path']);read(path,pin);expected.add(pin['path'])
        require(frozen['input_pins'].get(str(path))==plain and frozen['batch_input_pins'].get(str(path))==plain,'Archived source not in audit closure')
    require(set(frozen['code_pins'])<=set(frozen['source_archive']),'Executed source absent from immutable archive')
    require({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}==expected,'Source archive files differ')
    return {'original_source_files':len(frozen['source_archive']),'unique_archived_files':len(expected)-1,
            'index_sha256':sha(read(root/'INDEX.json'))}


def verify_corpus_inventory(frozen):
    root=safe(frozen['corpus_root'])
    original=load(root/'FROZEN.json',frozen['corpus'])
    bundles=root/'bundles'
    files={p.relative_to(bundles).as_posix() for p in bundles.rglob('*') if p.is_file()}
    directories={p.relative_to(bundles).as_posix() for p in bundles.rglob('*') if p.is_dir()}
    require(files==set(original['bundles']) and directories==set(original['bundle_directories']),
            'Exact frozen corpus files/directories differ')
    return {'files':len(files),'directories':len(directories),'original_freeze_sha256':sha(read(root/'FROZEN.json'))}


def reconstruct_stage(root, seal_sha256, freeze_path, freeze_sha256):
    """Read a completed or partial sealed comparison, never start/recover work."""
    root=safe(root); freeze_path=safe(freeze_path)
    frozen=load(freeze_path,freeze_sha256)
    require(frozen['schema_version']==1 and frozen['mode'] in ('benchmark','fictional'), 'Unknown freeze contract')
    arms=('bare_independent','bare_tether','inspect')
    expected_schedule=[{'repetition':r+1,'position':p+1,'arm':arm} for r in range(3)
                       for p,arm in enumerate(arms[r:]+arms[:r])]
    require(frozen['schedule']==expected_schedule, 'Frozen batch rotation differs')
    rows=frozen['rows']; ids=[row['control_id'] for row in rows]
    require(len(ids)==len(set(ids)) and ids, 'Unique frozen case schedule required')
    if frozen['mode']=='benchmark':require(len(rows)==109 and frozen['expected_cells']==981,'Primary denominator differs')
    seal=load(root/'SEALED.json',seal_sha256)
    require(seal['schema_version']==1 and seal['kind']=='inspect_policy_comparison'
            and seal['source_freeze_sha256']==freeze_sha256,'Stage seal/freeze mismatch')
    products=verify_inventory(root,seal['outputs'],excluded=('SEALED.json',))
    require(canonical(load(root/'freeze.json'))==canonical(frozen),'Copied freeze differs')
    current_source_mismatches=[]
    for name,pin in frozen['input_pins'].items():
        try:read(name,pin)
        except (ValueError,OSError) as exc:
            if 'batch_input_pins' not in frozen:raise
            current_source_mismatches.append({'path':name,'error':str(exc)})
    archive_proof=verify_source_archive(frozen,freeze_path)
    corpus_inventory=None
    try:corpus_inventory=verify_corpus_inventory(frozen)
    except (ValueError,OSError) as exc:
        if 'batch_input_pins' not in frozen:raise
        current_source_mismatches.append({'path':frozen['corpus_root'],'error':str(exc)})
    if 'environment_files' in frozen:
        environment=safe(frozen['environment_root'])
        current={p.relative_to(environment).as_posix() for p in environment.rglob('*') if p.is_file()}
        if current!=set(frozen['environment_files']):
            current_source_mismatches.append({'path':str(environment),'error':'Current environment file inventory differs'})
    for name,pin in frozen['code_pins'].items():
        require(frozen['input_pins'].get(name)==pin,'Code not in frozen input closure')
    oracle=load(frozen['oracle']['path'],frozen['oracle'])
    require([row['control_id'] for row in oracle['cases']]==ids,'Oracle/task ordering differs')
    parent=sealed_record(root,seal['outputs']['receipt.json']['sha256'],
                         {'freeze_path':str(freeze_path),'expected_freeze_sha256':freeze_sha256})
    result=parent['result']
    source_audit=check_audit_record(frozen,result,parent['events'])
    require(result['status']==seal['status'] and not result['automatic_retry'] and result['provider_cost_usd']==0,'Parent status/boundaries differ')
    require(result['scheduled_cells']==frozen['expected_cells']==9*len(rows)
            and result['retained_cells']==9*len(rows) and len(result['batches'])==9,'Incomplete all-scheduled denominator')
    dispatches={e['details']['ordinal']:e['details'] for e in parent['events'] if e['event']=='worker_dispatch'}
    returned={e['details']['ordinal']:e['details'] for e in parent['events'] if e['event']=='worker_returned'}
    require(len(dispatches)==sum(e['event']=='worker_dispatch' for e in parent['events'])
            and len(returned)==sum(e['event']=='worker_returned' for e in parent['events']), 'Duplicate batch dispatch/return')
    batches=[]
    for ordinal,condition in enumerate(expected_schedule):
        primary=result['batches'][ordinal]
        require(primary['ordinal']==ordinal and all(primary[k]==v for k,v in condition.items()),'Result batch ordering differs')
        folder=root/('batch-'+str(ordinal+1).zfill(2)+'-'+condition['arm']);worker=folder/'worker'
        require([r['control_id'] for r in primary['rows']]==ids,'Case disposition schedule differs')
        recipe=None;worker_checked=None
        if ordinal in dispatches:
            recipe=load(folder/'recipe.json',dispatches[ordinal]['recipe'])
            require(recipe['arm']==condition['arm'] and canonical(recipe['rows'])==canonical(rows)
                    and recipe['limits']==frozen['limits'] and recipe['code_pins']==frozen['code_pins']
                    and Path(recipe['output'])==worker,'Worker recipe differs from freeze')
            require(('oracle' in recipe)==(condition['arm']=='inspect'),'Worker oracle access differs')
            if 'oracle' in recipe:require(recipe['oracle']==frozen['oracle'],'Inspect oracle proof differs')
            command=dispatches[ordinal]['command']
            require(command[0]==frozen['python']['path'] and '-I' in command and '-B' in command
                    and str(folder/'recipe.json') in command and dispatches[ordinal]['recipe']['sha256'] in command,
                    'Worker command isolation/recipe binding differs')
        if (worker/'receipt.json').exists():
            require(recipe is not None,'Completed worker lacks dispatch')
            worker_pin=seal['outputs'][(worker/'receipt.json').relative_to(root).as_posix()]
            worker_checked=sealed_record(worker,worker_pin['sha256'],recipe)
            require(canonical(worker_checked['result'])==canonical(primary['worker_result']),'Worker/parent result differs')
        recovered=[];case_times=[];operation_times=[];operation_cpu=[]
        native=None;native_by_id={};native_joins=[]
        if condition['arm']=='inspect':
            logs=list((worker/'native-logs').glob('*.json')) if (worker/'native-logs').exists() else []
            require(len(logs)<=1,'Unexpected native log count')
            if logs:
                native=native_log(logs[0]);native_by_id={s['id']:s for s in native['samples']}
                require(set(native_by_id)<=set(ids),'Native unscheduled sample')
                if worker_checked:
                    summary=worker_checked['result'].get('native')
                    if summary:
                        require(summary['status']==native['header']['status'] and Path(summary['location'])==logs[0], 'Worker native summary differs')
                        require([s['id'] for s in summary['samples']]==[s['id'] for s in native['samples']], 'Native summary sample order differs')
        watchdog=load(worker/'WATCHDOG.json') if (worker/'WATCHDOG.json').exists() else None
        for row,declared in zip(rows,primary['rows']):
            ident=row['control_id'];path=worker/'cases'/ident
            recovered_row={'control_id':ident,'status':'unstarted','decision':None,'receipt':None,'error':None}
            record=None
            if (path/'receipt.json').exists():
                pin=seal['outputs'][(path/'receipt.json').relative_to(root).as_posix()]
                record=case_record(path,pin['sha256'],row)
                outcome=record['result']
                recovered_row.update(status=outcome['status'],decision=outcome['decision'],receipt=pin,error=outcome['error'])
                for key,target in (('operation_wall_seconds',operation_times),('operation_cpu_seconds',operation_cpu)):
                    value=outcome.get('resources',{}).get(key)
                    if value is not None:target.append(value)
                if worker_checked:
                    matches=[e['details'] for e in worker_checked['events'] if e['event']=='case_returned' and e['details']['control_id']==ident]
                    require(len(matches)<=1,'Case returned more than once')
                    if matches:
                        require(matches[0]['receipt']==pin,'Worker case receipt differs')
                        case_times.append(matches[0]['case_wall_seconds'])
                if ident in native_by_id:
                    gold=next(g for g in oracle['cases'] if g['control_id']==ident)
                    native_joins.append({'control_id':ident,**native_archive_join(native_by_id[ident],row,outcome,gold)})
            elif path.exists():recovered_row.update(status='unfinished',error='No sealed case receipt')
            if watchdog and watchdog['control_id']==ident:
                recovered_row.update(status='timeout',decision=None,error='Per-case wall bound exceeded')
            require(canonical(recovered_row)==canonical(declared),'Primary disposition differs from independently recovered files: '+ident)
            recovered.append(recovered_row)
        independently_scored=primary_counts(oracle['cases'],recovered)
        if primary.get('score') is not None:
            require(canonical(independently_scored)==canonical(primary['score']),'Primary metric/case projection differs')
        if primary['status']=='completed':
            require(ordinal in returned and worker_checked is not None and worker_checked['result']['status']=='completed', 'Completed batch lacks terminal')
            supervisor=load(folder/'supervision.json')
            require(canonical(supervisor)==canonical(primary['supervision'])==canonical(returned[ordinal]['report']),'Supervision/journal result differs')
            require(supervisor['returncode']==0 and supervisor['error'] is None,'Completed batch has failed supervisor')
            successful_supervision(supervisor['supervision'],dispatches[ordinal]['limits'],
                                   len(read(folder/'stdout.bin')),len(read(folder/'stderr.bin')))
            if condition['arm']=='inspect':
                require(native is not None and len(native_by_id)==len(ids),'Completed Inspect batch lacks full native schedule')
        batches.append({'ordinal':ordinal,**condition,'status':primary['status'],'policy_counts':independently_scored,
            'native_present':len(native_by_id),'native_missing':len(rows)-len(native_by_id) if condition['arm']=='inspect' else None,
            'native_scoring_joins':native_joins,'operation_wall_seconds':statistics(operation_times),
            'operation_cpu_seconds':statistics(operation_cpu),'case_wall_seconds':statistics(case_times),
            'worker_resources':{k:v for k,v in (worker_checked['result'] if worker_checked else {}).items()
                                if k in ('worker_preexecution_wall_seconds','arm_execution_interval_seconds','worker_cpu_seconds','worker_peak_memory_bytes')},
            'supervision':primary.get('supervision')})
    arm_summary={}
    for arm in arms:
        selected=[b for b in batches if b['arm']==arm]
        elapsed=[b['supervision']['supervision']['total_elapsed_seconds'] for b in selected
                 if b.get('supervision') and b['supervision'].get('supervision')]
        arm_summary[arm]={'scheduled':3*len(rows),'completed_batches':sum(b['status']=='completed' for b in selected),
            'full_policy_conformance':sum(b['policy_counts']['full_conformance'] for b in selected),
            'full_policy_conformance_per_scheduled':sum(b['policy_counts']['full_conformance'] for b in selected)/(3*len(rows)),
            'supervised_batch_elapsed_seconds':statistics(elapsed),
            'worker_cpu_seconds':statistics([b['worker_resources']['worker_cpu_seconds'] for b in selected if 'worker_cpu_seconds' in b['worker_resources']]),
            'worker_peak_memory_bytes':[b['worker_resources'].get('worker_peak_memory_bytes') for b in selected],
            'native_samples_present':sum(b['native_present'] for b in selected) if arm=='inspect' else None,
            'native_scored_correct':sum(j['native_correct'] for b in selected for j in b['native_scoring_joins']) if arm=='inspect' else None}
    return {'schema_version':1,'status':'PASS' if not current_source_mismatches else 'PASS_WITH_CURRENT_SOURCE_MISMATCH','mode':frozen['mode'],
            'stage':str(root),'stage_seal_sha256':seal_sha256,'freeze_sha256':freeze_sha256,
            'scheduled_cells':len(rows)*9,'primary_status':result['status'],'products':products,
            'input_files_checked':len(frozen['input_pins']),
            'input_files_verified':len(frozen['input_pins'])-sum(item['path'] in frozen['input_pins'] for item in current_source_mismatches),
            'input_logical_bytes':sum(p['bytes'] for p in frozen['input_pins'].values()),
            'source_audit':source_audit,'source_archive':archive_proof,'corpus_inventory':corpus_inventory,
            'current_source_mismatches':current_source_mismatches,
            'batches':batches,'arm_summary':arm_summary,'provider_cost_usd':0,'automatic_redispatch':False,
            'limitations':['Independent schedule/proof/aggregation/native-log reconstruction; no re-execution of biomedical admission policy.',
                          'Policy-result conformance and native pipeline completion are retained separately.',
                          'Resource measurements are reconstructed from sealed observations, not independently remeasured.',
                          'Runtime witnesses are a separate analysis; no inference of full therapeutic scheduling parity.']}


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage',required=True);parser.add_argument('--seal-sha256',required=True)
    parser.add_argument('--freeze',required=True);parser.add_argument('--freeze-sha256',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    report=reconstruct_stage(args.stage,args.seal_sha256,args.freeze,args.freeze_sha256)
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as stream:stream.write(canonical(report)+b'\n')
    print(json.dumps({'status':report['status'],'scheduled_cells':report['scheduled_cells'],'report_sha256':sha(read(output))}))


if __name__=='__main__':main()
