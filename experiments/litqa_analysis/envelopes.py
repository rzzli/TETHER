"""Independent SC04 envelopes and measured resource accounting (stdlib only).

This verifies externally anchored inventories, schedules, journals and accounting.
It does not establish source eligibility, model semantics, or scientific correctness;
those require the independent collection/native/scoring layers. No dispatch occurs.
"""
import base64
from datetime import datetime, timezone
import hashlib
import math
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import time

from .native_records import canonical, decode, digest, journal, need

REPO = Path(__file__).resolve().parents[2]
PRIMARY_PHASES = ('expand', 'collect', 'rank', 'answer')
ARMS = ('L/O', 'E/O', 'L/R', 'E/R')
MAX_FILE = 128 * 1024 ** 2


def regular(path):
    path = Path(path)
    info = path.lstat()
    need(not path.is_symlink() and not getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT,
         'Linked envelope input')
    need(stat.S_ISREG(info.st_mode), 'Nonregular envelope input')
    need(info.st_size <= MAX_FILE, 'Envelope input too large')
    return info


def raw(path):
    before = regular(path)
    with Path(path).open('rb') as stream:
        value = stream.read(MAX_FILE + 1)
    after = regular(path)
    need(len(value) == before.st_size <= MAX_FILE and
         (before.st_size, before.st_mtime_ns, before.st_ino) ==
         (after.st_size, after.st_mtime_ns, after.st_ino), 'Envelope input changed')
    return value


def load(path):
    return decode(raw(path))


def proof(path):
    path = Path(path).absolute()
    before = regular(path)
    with path.open('rb') as stream:
        hashed = hashlib.file_digest(stream, 'sha256').hexdigest()
    after = regular(path)
    need((before.st_size, before.st_mtime_ns, before.st_ino) ==
         (after.st_size, after.st_mtime_ns, after.st_ino), 'Hash input changed')
    return dict(path=str(path), bytes=after.st_size, sha256=hashed)


def anchored(path, expected):
    value = raw(path)
    need(digest(value) == expected, 'External receipt anchor mismatch')
    return decode(value)


def external(proof_value):
    need(proof(proof_value['path']) == proof_value, 'External input proof mismatch')
    return load(proof_value['path'])


def child(root, name):
    need(isinstance(name, str) and name and '\\' not in name, 'Invalid relative artifact name')
    relative = PurePosixPath(name)
    need(not relative.is_absolute() and all(p not in ('', '.', '..') for p in relative.parts), 'Unsafe artifact path')
    path = Path(root).joinpath(*relative.parts)
    need(path.resolve().is_relative_to(Path(root).resolve()), 'Escaped artifact path')
    return path


def inventory(root, *, omit=(), recursive=True):
    root = Path(root).absolute()
    info = root.lstat()
    need(root.is_dir() and not root.is_symlink() and
         not getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT, 'Linked package root')
    result = {}
    total = 0
    end = time.monotonic() + 300
    for path in root.rglob('*') if recursive else root.iterdir():
        need(time.monotonic() < end, 'Independent inventory deadline')
        info = path.lstat()
        need(not path.is_symlink() and not getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT,
             'Linked package artifact')
        if path.is_dir():
            continue
        name = path.relative_to(root).as_posix()
        if name in omit:
            continue
        total += info.st_size
        need(len(result) < 60000 and total <= 8 * 1024 ** 3, 'Independent inventory bounds')
        result[name] = proof(path)
    return result


def nonnegative(value, label):
    need(type(value) in (int, float) and math.isfinite(value) and value >= 0, label)
    return value


def integer(value, label):
    need(type(value) is int and value >= 0, label)
    return value


def utc(value):
    result = datetime.fromisoformat(value)
    need(result.tzinfo is not None and result.utcoffset().total_seconds() == 0, 'Explicit UTC timestamp required')
    return result.astimezone(timezone.utc)


def producer_spec(spec):
    """Only the owned loopback port may differ between sequential controllers."""
    result = dict(spec)
    args = list(spec['argv'])
    need(args.count('--port') == 1 and str(spec['port']) == args[args.index('--port') + 1] and
         spec['host'] == '127.0.0.1', 'Model port/command mismatch')
    args[args.index('--port') + 1] = '<owned-loopback-port>'
    result.update(argv=args, port='<owned-loopback-port>')
    return result


def verify_pair(primary, supplied):
    """Cross-bind two verify_run results; must be called after both full checks.

    Retained timestamps establish declared ordering, not a trusted time service.
    The diagnostic frame commits to the already finalized primary receipt.
    """
    need(primary['kind'] == 'primary' and supplied['kind'] == 'supplied', 'Expected primary/diagnostic pair')
    left, right = primary['frame'], supplied['frame']
    need(left['purpose'] == right['purpose'] == 'production', 'Pair comparison requires full production runs')
    descriptor = right['primary_execution']
    need(Path(descriptor['root']) == Path(primary['root']) and
         descriptor['receipt'] == proof(Path(primary['root']) / 'ROOT-RECEIPT.json') and
         descriptor['receipt']['sha256'] == primary['root_sha256'], 'Diagnostic commits to a different primary run')
    need(right['primary_frame']['sha256'] == primary['frame_sha256'] and
         external(right['primary_frame']) == left, 'Diagnostic primary frame mismatch')
    need(external(right['products']['answer_queries']) == external(left['query_products']['answer_queries']),
         'Pair question/option order mismatch')
    need(right['generation_configuration'] == left['generation_configuration'] and
         right['model']['model_provenance'] == left['model_provenance'] and
         producer_spec(right['model']['model_spec']) == producer_spec(left['model_spec']) and
         right['model']['alias'] == left['alias'],
         'Pair answer producer configuration differs')
    need(all(right['code_pins'].get(k) == v for k, v in left['code_pins'].items()), 'Pair primary producer code differs')
    first = journal(Path(supplied['root']) / 'journal.jsonl')[0]['details']['created_at_utc']
    need(utc(primary['complete']['source_cutoff']) <= utc(right['created_at_utc']) <= utc(first) <=
         utc(supplied['complete']['source_cutoff']), 'Declared diagnostic chronology contradicts primary/diagnostic cutoffs')
    return dict(status='verified', primary_root_sha256=primary['root_sha256'], supplied_root_sha256=supplied['root_sha256'],
                scope='Complete primary receipt committed by diagnostic frame; same questions/options and answer producer. '
                      'Timestamp order is declared local-clock evidence, not independent trusted-clock attestation.')


def _stage(root, expected_sha, ids, branches, stage, known_inventory):
    receipt = anchored(root / 'STAGE-RECEIPT.json', expected_sha)
    need(receipt['status'] == 'complete', 'Incomplete stage receipt')
    prefix = 'worker/phase/'
    actual = {name[len(prefix):]: dict(bytes=p['bytes'], sha256=p['sha256'])
              for name, p in known_inventory.items()
              if name.startswith(prefix) and name != prefix + 'STAGE-RECEIPT.json'}
    need(receipt['files'] == actual, 'Stage inventory mismatch')
    config = load(root / 'CONFIG.json')
    planned = [dict(ordinal=n, id=cid, branch=b)
               for n, (cid, b) in enumerate((cid, b) for cid in ids for b in branches)]
    need(config['kind'] == 'sc04_stage_v1' and config['stage'] == stage and config['ids'] == ids and
         config['schedule'] == planned, 'Stage schedule differs from frozen task IDs')
    report = load(root / 'REPORT.json')
    need(report['status'] == 'complete' and report['scheduled'] == report['entered'] == len(planned) and
         report['unexecuted'] == 0, 'Incomplete stage accounting')
    need(nonnegative(report['wall_seconds'], 'Stage elapsed') < nonnegative(config['seconds'], 'Stage limit'),
         'Stage exceeded deadline')
    events = journal(root / 'journal.jsonl')
    need(len(events) == 3 + 2 * len(planned) and events[0]['event'] == 'build_reserved' and
         events[1]['event'] == 'stage_configured' and events[1]['details'] ==
         dict(config_sha256=digest(raw(root / 'CONFIG.json'))), 'Stage setup events')
    rows = []
    for index, identity in enumerate(planned):
        name = f'slots/{index:04d}.json'
        row = load(root / name)
        need(set(row) == set(identity) | {'status', 'reason', 'product'} and
             all(row[k] == v for k, v in identity.items()) and
             row['status'] in ('completed', 'fallback', 'not_applicable'), 'Slot identity or status')
        reserved, terminal = events[2 + 2 * index:4 + 2 * index]
        need(reserved['event'] == 'slot_reserved' and reserved['details'] == identity and
             terminal['event'] == 'slot_terminal' and terminal['details'] ==
             dict(ordinal=index, slot_sha256=digest(raw(root / name)), path=name, status=row['status']),
             'Slot reservation/terminal mismatch')
        rows.append(row)
    need(report['rows'] == rows and events[-1]['event'] == 'stage_finalized' and events[-1]['details'] ==
         dict(status='complete', report_sha256=digest(raw(root / 'REPORT.json'))), 'Stage report/journal mismatch')
    actual_slots = {name for name in actual if name.startswith('slots/')}
    need(actual_slots == {f'slots/{i:04d}.json' for i in range(len(planned))}, 'Unexpected slot artifacts')
    return rows


def _native_resources(stage_root):
    totals = dict(generation_calls=0, tokenizer_calls=0, measured_input_tokens=0, measured_output_tokens=0,
                  reserved_input_tokens=0, reserved_output_tokens=0, provider_cost_usd=0)
    cells = []
    for path in sorted((stage_root / 'products').glob('*/SUMMARY.json')):
        summary = load(path)
        root = path.parent
        usage = summary['usage']
        if summary['generation_entered']:
            need(summary['status'] in ('completed', 'codec_failure'), 'Unexpected completed-stage native status')
            wrapper = load(root / 'native/native-response.bin')
            body = base64.b64decode(wrapper['body_base64'], validate=True)
            response = decode(body)
            need(digest(body) == wrapper['body_sha256'] and wrapper['complete'] is True and
                 wrapper['http_status'] == 200, 'Incomplete native response accounting')
            token_bytes = raw(root / 'native/tokenization/body.bin')
            token_receipt = load(root / 'native/tokenization/result.json')
            tokens = decode(token_bytes)['tokens']
            need(isinstance(tokens, list) and all(type(t) is int and t >= 0 for t in tokens) and
                 token_receipt['body_sha256'] == digest(token_bytes) and
                 base64.b64decode(token_receipt['body_base64'], validate=True) == token_bytes and
                 token_receipt['token_count'] == len(tokens) == response['tokens_evaluated'], 'Native input accounting')
            measured = dict(input_tokens=len(tokens), output_tokens=integer(response['tokens_predicted'], 'Output tokens'), cost_usd=0.0)
            need(usage == measured and measured['output_tokens'] <= 256, 'Measured usage differs from native bytes')
            payload = load(root / 'native/payload.json')
            reserved = max(len(payload['prompt'].encode()) + 32, len(tokens))
            need(summary['reservation_input_tokens'] == reserved and summary['reservation_output_tokens'] == 256,
                 'Native conservative reservation mismatch')
            terminal_path = root / 'native' / ('result.json' if summary['status'] == 'completed' else 'failure.json')
            terminal = load(terminal_path)
            need(terminal['measured_usage'] == measured and terminal['conservative_reserved_input_tokens'] == reserved and
                 terminal['conservative_reserved_output_tokens'] == 256, 'Terminal accounting mismatch')
            totals['generation_calls'] += 1
            totals['tokenizer_calls'] += 1
            totals['measured_input_tokens'] += measured['input_tokens']
            totals['measured_output_tokens'] += measured['output_tokens']
        else:
            need(summary['status'] == 'capacity' and usage is None and
                 not (root / 'native').exists() and summary['reservation_input_tokens'] ==
                 summary['reservation_output_tokens'] == 0, 'Undispatched native accounting')
        totals['reserved_input_tokens'] += integer(summary['reservation_input_tokens'], 'Input reservation')
        totals['reserved_output_tokens'] += integer(summary['reservation_output_tokens'], 'Output reservation')
        need(summary['provider_cost_usd'] == 0, 'Unexpected provider cost')
        cells.append(dict(root=str(root), status=summary['status'], usage=usage,
                          generation_entered=summary['generation_entered']))
    return totals, cells


def _http_resources(stage_root):
    totals = dict(attempted_requests=0, captured_requests=0, failed_requests=0, http_200=0,
                  measured_response_bytes=0, safety_accounted_bytes=0, unknown_transfer_upper_bytes=0,
                  reserved_response_bytes=0, wire_bytes=None, retries=0, provider_cost_usd=0)
    for path in sorted((stage_root / 'products').glob('*/MANIFEST.json')):
        value = load(path)
        measured = accounted = 0
        requests = value['requests']
        need(len(requests) <= 5, 'Acquisition request bound')
        for index, record in enumerate(requests):
            need(record['request_id'] == f'{index:03d}', 'HTTP attempt order')
            reservation = integer(record['byte_reservation'], 'HTTP reservation')
            need(reservation > 0, 'Empty HTTP reservation')
            totals['attempted_requests'] += 1
            totals['reserved_response_bytes'] += reservation
            if record['transport_status'] == 'failed':
                need(record['measured_bytes'] is None and record['accounted_bytes'] == reservation and
                     record['http_status'] is None, 'Failed HTTP uncertainty accounting')
                totals['failed_requests'] += 1
                accounted += reservation
                continue
            need(record['transport_status'] == 'captured', 'Unfinished HTTP attempt')
            body = raw(child(path.parent, record['body_path']))
            receipt_bytes = raw(child(path.parent, record['receipt_path']))
            receipt = decode(receipt_bytes)
            need(digest(receipt_bytes) == record['receipt_sha256'] and receipt['status'] == 'completed' and
                 receipt['url'] == receipt['source_url'] == record['url'] and
                 receipt['http_status'] == record['http_status'], 'HTTP original receipt binding')
            need(digest(body) == record['body_sha256'] == receipt['sha256'] and
                 len(body) == record['body_bytes'] == receipt['bytes'] ==
                 record['measured_bytes'] == record['accounted_bytes'] <= reservation, 'HTTP measured bytes mismatch')
            need(record['body_path'] == receipt['relative_path'], 'HTTP original body identity')
            if value['kind'] == 'sc04_acquisition_v1':
                need(receipt['body_path'] == record['body_path'] and receipt['body_sha256'] == record['body_sha256'] and
                     receipt['body_bytes'] == record['body_bytes'], 'Primary receipt body aliases')
            else:
                need(value['kind'] == 'sc04_supplied_doi_v1' and
                     receipt['selection_role'] == 'supplied_source_diagnostic' and
                     receipt['requested_doi'] == value['plan']['doi'], 'Diagnostic receipt role/DOI')
            totals['captured_requests'] += 1
            totals['http_200'] += int(record['http_status'] == 200)
            measured += len(body)
            accounted += len(body)
        expected = dict(measured_response_bytes=measured, safety_accounted_bytes=accounted,
                        unknown_transfer_upper_bytes=accounted - measured, wire_bytes=None, retries=0, provider_cost_usd=0)
        need(value['accounting'] == expected, 'Aggregate acquisition accounting mismatch')
        for key in ('measured_response_bytes', 'safety_accounted_bytes', 'unknown_transfer_upper_bytes'):
            totals[key] += expected[key]
    return totals


def _supervision(root, frame, phase):
    result = {}
    for label, command_file in (('execution', 'COMMAND.json'), ('review', 'REVIEW-COMMAND.json')):
        command = load(root / command_file)
        wrapper = load(root / (label + '-SUPERVISION.json'))
        report = wrapper['supervision']
        expected_seconds = frame['phase_seconds'][phase] if label == 'execution' else frame['replay_seconds']
        need(command['limits'] == report['limits'] == dict(timeout_seconds=expected_seconds, max_output_bytes=4194304),
             'Supervision limits differ from frozen frame')
        need(wrapper['returncode'] == 0 and report['termination_reason'] == 'exited' and
             report['process_started'] is True and report['process_reaped'] is True and
             report['pipe_eof'] == dict(stderr=True, stdout=True) and not report['cleanup_errors'] and
             report['observed_counts_are_lower_bounds'] is False, 'Incomplete process supervision')
        for stream in ('stdout', 'stderr'):
            size = (root / (label + '-' + stream + '.txt')).stat().st_size
            need(size == report['retained_' + stream + '_bytes'] == report['observed_' + stream + '_bytes'],
                 'Supervised stream byte accounting')
        need(report['observed_stdout_bytes'] + report['observed_stderr_bytes'] <= 4194304, 'Supervised stream cap')
        need(nonnegative(report['execution_elapsed_seconds'], 'Execution elapsed') <= expected_seconds and
             nonnegative(report['total_elapsed_seconds'], 'Total elapsed') >= report['execution_elapsed_seconds'],
             'Supervision elapsed limits')
        result[label + '_supervised_seconds'] = report['total_elapsed_seconds']
    return result


def audit_records(data, *, inputs, output, code_roots):
    """Recompute the captured Python-open audit, including denied/FD events."""
    need(data.endswith(b'\n'), 'Incomplete Python-open audit tail')
    allowed_inputs = {str(Path(p).resolve()).casefold() for p in inputs}
    output = Path(output).resolve()
    code_roots = [Path(p).resolve() for p in code_roots]
    records = [decode(line) for line in data.splitlines()]
    need(records, 'Missing Python-open audit events')
    counts = dict(events=len(records), output_events=0, input_or_runtime_events=0, existing_descriptor_events=0, denied_events=0)
    for record in records:
        need(type(record['flags']) is int and (record['mode'] is None or isinstance(record['mode'], str)), 'Audit open metadata')
        if record['path'] is None:
            need(set(record) == {'path', 'descriptor', 'mode', 'flags', 'allowed', 'basis'} and
                 type(record['descriptor']) is int and record['descriptor'] >= 0 and
                 record['allowed'] is True and record['basis'] == 'existing_descriptor', 'Existing descriptor audit')
            counts['existing_descriptor_events'] += 1
            continue
        need(set(record) == {'path', 'mode', 'flags', 'allowed', 'basis'} and
             isinstance(record['path'], str) and Path(record['path']).is_absolute(), 'Audit path schema')
        path = Path(record['path']).resolve()
        write = bool(record['flags'] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        within_output = path.is_relative_to(output)
        expected = within_output or (not write and (str(path).casefold() in allowed_inputs or
                                                   any(path.is_relative_to(p) for p in code_roots)))
        basis = 'output' if within_output else 'explicit_data_or_runtime' if expected else 'denied'
        need(record['allowed'] is expected and record['basis'] == basis, 'Audit role/allowlist classification mismatch')
        counts['output_events' if within_output else 'input_or_runtime_events' if expected else 'denied_events'] += 1
    need(counts['denied_events'] == 0, 'Denied Python-open event in completed run')
    return counts


def _io_audit(root, frame, phase, primary, job, model_info, complete):
    frame_sha = digest(canonical(frame) + b'\n')
    # Frame files are canonical with a final newline in both frozen controllers.
    need(job['frame_sha256'] == frame_sha, 'Audit frozen frame serialization')
    cache = (REPO / 'data/cache' / (('sc04-' if primary else 'sc04-diagnostic-') +
                                   root.parent.name + '-' + phase + '-imports')).resolve()
    need(Path(job['worker_import_cache' if primary else 'import_cache']) == cache, 'Worker import cache path')
    command = load(root / 'COMMAND.json')['command']
    need(isinstance(command, list) and command.count('--frame') == 1, 'Worker frame command field')
    frame_path = Path(command[command.index('--frame') + 1])
    need(frame_path.is_absolute() and digest(raw(frame_path)) == frame_sha, 'Worker original frame path/hash')
    driver = REPO / ('experiments/litqa_comparison/run.py' if primary else 'experiments/litqa_supplied/run.py')
    expected = [frame['python']['path'], '-I', '-B', '-X', 'pycache_prefix=' + str(cache), str(driver), 'worker',
                '--frame', str(frame_path), '--frame-sha256', frame_sha, '--job', str(root / 'JOB.json'),
                '--job-sha256', proof(root / 'JOB.json')['sha256'], '--output', str(root / 'worker')]
    need(command == expected, 'Exact worker execution command mismatch')
    expected[4] += '-review'
    expected[6] = 'review-worker'
    expected[-1] = str(root / 'review')
    need(load(root / 'REVIEW-COMMAND.json')['command'] == expected, 'Exact replay execution command mismatch')
    inputs = [frame_path, root / 'JOB.json']
    if primary:
        inputs.append(frame['query_products']['answer_queries' if phase == 'answer' else 'source_queries']['path'])
        parents = list(job['parents'].values())
    else:
        inputs += [frame['products'][key]['path'] for key in
                   (('doi_schedule',) if phase == 'collect' else ('doi_schedule', 'answer_queries', 'hints'))]
        parents = [] if phase == 'collect' else [job['collection']]
    for parent in parents:
        inputs += [p for p in Path(parent['root']).rglob('*') if p.is_file()]
    if model_info is not None:
        model_frame = frame if primary else frame['model']
        location = Path(model_frame['model_receipt']['path']).parent
        spec = model_frame['model_spec']
        logical_ids = {p['logical_id'] for p in spec['required_inputs']} | {spec['executable']['logical_id']}
        expected_bindings = {name: str(child(location, name)) for name in logical_ids}
        need(model_info['bindings'] == expected_bindings, 'Exact declared model input bindings')
        inputs += list(expected_bindings.values()) + [model_frame['model_license']['path']]
    need(proof(sys.executable) == frame['python'], 'Audit requires the same pinned interpreter')
    runtime_roots = [Path(sys.prefix), Path(sys.base_prefix)]
    code_roots = [REPO / 'src', REPO / 'packages/tether/src', REPO / 'experiments', *runtime_roots, cache]
    result = audit_records(raw(root / 'worker/io-audit.jsonl'), inputs=inputs, output=root / 'worker', code_roots=code_roots)
    need(complete['audit_denials'] == result['denied_events'], 'Worker/audit denial accounting mismatch')
    result.update(runtime_roots=[str(p) for p in runtime_roots], declared_input_count=len(set(map(str, inputs))),
                  scope='Captured Python-open events only; writes limited to worker output, exact role-specific data inputs, '
                        'read-only code/runtime roots. Existing file descriptors remain opaque. Runtime roots use the current '
                        'matching interpreter; original sys.prefix/base_prefix were not independently sealed. Not an OS sandbox.')
    return result


def _phase_journals(root, primary, phase, worker, stage_sha):
    events = journal(root / 'journal.jsonl')
    expected_names = (['build_reserved', 'phase_worker_dispatch', 'phase_replay_dispatch', 'phase_package_verified']
                      if primary else ['build_reserved', 'diagnostic_worker_dispatch', 'diagnostic_replay_dispatch',
                                       'diagnostic_phase_verified'])
    need([e['event'] for e in events] == expected_names, 'Phase supervisor event bijection')
    dispatch = dict(phase=phase)
    if primary:
        dispatch['job_sha256'] = digest(raw(root / 'JOB.json'))
    terminal = dict(stage_receipt_sha256=stage_sha)
    if primary:
        terminal['phase'] = phase
    need(events[1]['details'] == dispatch and events[2]['details'] == dict(phase=phase) and
         events[3]['details'] == terminal, 'Phase supervisor event binding')
    events = journal(root / 'worker/journal.jsonl')
    names = ['build_reserved']
    if phase != 'collect':
        names += ['server_started', 'server_ready', 'server_terminal']
    names += ['phase_completed' if primary else 'diagnostic_phase_completed']
    need([e['event'] for e in events] == names, 'Worker event bijection')
    if phase != 'collect':
        need(events[1]['details'] == events[2]['details'] == dict(pid=worker['server_terminal']['pid']) and
             events[3]['details'] == worker['server_terminal'], 'Worker server lifecycle binding')
    expected = (dict(phase=phase, stage_receipt_sha256=stage_sha) if primary else
                dict(complete_sha256=digest(raw(root / 'worker/COMPLETE.json'))))
    need(events[-1]['details'] == expected, 'Worker terminal event binding')
    events = journal(root / 'review/journal.jsonl')
    need([e['event'] for e in events] == ['build_reserved', 'replay_completed' if primary else 'diagnostic_replay_completed'] and
         events[-1]['details'] == dict(report_sha256=digest(raw(root / 'review/REPORT.json'))), 'Replay event bijection/binding')


def _product_bijection(stage_root, rows, phase):
    expected = set()
    for row in rows:
        product = row['product']
        root = stage_root / 'products' / f'{row["ordinal"]:04d}'
        if phase == 'collect':
            need(Path(product['root']) == root and product['manifest'] == proof(root / 'MANIFEST.json') and
                 product['receipt'] == proof(root / 'RECEIPT.json'), 'Collection slot/product identity')
            expected.add(root.name)
        elif product['call'] is not None:
            call = product['call']
            need(Path(call['root']) == root and call['summary_proof'] == proof(root / 'SUMMARY.json') and
                 call['summary'] == load(root / 'SUMMARY.json'), 'Native slot/summary identity')
            summary = call['summary']
            if summary['generation_entered']:
                terminal = root / 'native' / ('result.json' if summary['status'] == 'completed' else 'failure.json')
                need(summary['native_result'] == proof(terminal), 'Native terminal proof identity')
            expected.add(root.name)
        else:
            need(phase == 'rank' and row['status'] == 'not_applicable', 'Missing expected model call')
    directory = stage_root / 'products'
    need({p.name for p in directory.iterdir()} == expected and all(p.is_dir() for p in directory.iterdir()),
         'Product directory / scheduled slot bijection')


def verify_run(root, expected_root_sha256, *, kind=None):
    """Verify one completed run. Caller must retain the external root hash.

    Original absolute proof paths are required; relocation is intentionally not
    accepted. Large model assets are not rehashed here: the bound execution
    frame/model receipt and native records are checked, not hardware attestation.
    """
    root = Path(root).absolute()
    receipt = anchored(root / 'ROOT-RECEIPT.json', expected_root_sha256)
    files = inventory(root, omit=('ROOT-RECEIPT.json',), recursive=False)
    need(receipt['files'] == files, 'Root exact file inventory mismatch')
    frame = load(root / 'FRAME.json')
    frame_sha = digest(raw(root / 'FRAME.json'))
    primary = frame['kind'] == 'sc04_primary_execution_v1'
    need(primary or frame['kind'] == 'sc04_supplied_execution_v1', 'Unknown run kind')
    actual_kind = 'primary' if primary else 'supplied'
    need(kind is None or kind == actual_kind, 'Requested run kind differs')
    phases = PRIMARY_PHASES if primary else ('collect', 'answer')
    expected_names = {'COMPLETE.json', 'FRAME.json', 'journal.jsonl'} | {p + '-ANCHOR.json' for p in phases}
    need(set(files) == expected_names and {p.name for p in root.iterdir() if p.is_dir()} == set(phases),
         'Unexpected root artifacts')
    need(receipt['frame_sha256'] == frame_sha and frame['purpose'] in ('production', 'fictional_qualification'),
         'Frame identity or purpose mismatch')
    complete = load(root / 'COMPLETE.json')
    status = 'primary_execution_complete' if primary else 'diagnostic_execution_complete'
    need(receipt['status'] == complete['status'] == status and complete['purpose'] == frame['purpose'] and
         set(complete['phases']) == set(phases) and complete['provider_cost_usd'] == 0 and
         complete['sc04_complete'] is False and complete['scientific_scoring_performed'] is False,
         'Incomplete/contradictory run completion')
    need(frame['automatic_retry'] is False and
         frame['provider_spend_usd' if primary else 'provider_cost_usd'] == 0, 'Spending/retry frame')
    expected_count = 199 if frame['purpose'] == 'production' else 2
    if primary:
        need(frame['count'] == expected_count and frame['phases'] == list(phases) and
             frame['conditions'] == list(ARMS) + ['supplied_source_pending_separate_execution'] and
             complete['supplied_source_complete'] is False, 'Primary declared scope mismatch')
        queries = external(frame['query_products']['answer_queries'])
        source = external(frame['query_products']['source_queries'])
        ids = [q['id'] for q in queries]
        need(ids == frame['schedule'] and source == [dict(id=q['id'], question=q['question']) for q in queries],
             'Question/answer role projection mismatch')
        doi_ids = None
    else:
        need(frame['ordinary_retrieval'] is complete['ordinary_retrieval'] is False and
             frame['questions'] == expected_count, 'Diagnostic declared scope mismatch')
        queries = external(frame['products']['answer_queries'])
        hints = external(frame['products']['hints'])
        doi_ids = external(frame['products']['doi_schedule'])
        ids = [q['id'] for q in queries]
        need(len(hints) == len(queries) and [h['id'] for h in hints] == ids and
             all(set(h) == {'id', 'question', 'dois'} and h['question'] == q['question'] and
                 1 <= len(h['dois']) <= 2 and len(set(h['dois'])) == len(h['dois']) for h, q in zip(hints, queries)),
             'Diagnostic hint projection mismatch')
        need(len(doi_ids) == len(set(doi_ids)) == frame['unique_dois'] == (190 if expected_count == 199 else 1) and
             {d for h in hints for d in h['dois']} == set(doi_ids) and
             sum(len(h['dois']) for h in hints) == frame['question_doi_pairs'] == (205 if expected_count == 199 else 2),
             'Diagnostic complete paper schedule mismatch')
    need(len(ids) == len(set(ids)) == expected_count, 'Missing/duplicate question schedule')
    for name, sha in frame['code_pins'].items():
        need(proof(child(REPO, name))['sha256'] == sha, 'Frozen executed code changed: ' + name)
    need(proof(frame['python']['path']) == frame['python'], 'Frozen interpreter changed')
    model_frame = frame if primary else frame['model']
    external(model_frame['model_receipt'])
    need(proof(model_frame['model_license']['path']) == model_frame['model_license'], 'Model license bytes changed')
    root_events = journal(root / 'journal.jsonl')
    event_names = ['build_reserved']
    prefix = '' if primary else 'diagnostic_'
    for phase in phases:
        event_names += [prefix + 'phase_started', prefix + 'phase_accepted']
    event_names += ['primary_comparison_executed', 'primary_report_sealed'] if primary else ['diagnostic_report_sealed']
    need([e['event'] for e in root_events] == event_names, 'Root journal event bijection')
    need(root_events[-1]['details'] == dict(complete_sha256=files['COMPLETE.json']['sha256']), 'Root sealed completion')
    if primary:
        need(root_events[-2]['details'] == dict(scientific_scoring_performed=False, supplied_source_complete=False),
             'Primary journal scope mismatch')
    result_phases = {}
    resource_phases = {}
    output_bytes = sum(p['bytes'] for p in files.values()) + (root / 'ROOT-RECEIPT.json').stat().st_size
    for ordinal, phase in enumerate(phases):
        descriptor = complete['phases'][phase]
        phase_root = root / phase
        need(Path(descriptor['root']) == phase_root and load(root / (phase + '-ANCHOR.json')) == descriptor,
             'Phase descriptor/anchor identity')
        need(root_events[1 + ordinal * 2]['details'] == dict(phase=phase) and
             root_events[2 + ordinal * 2]['details'] == dict(phase=phase, **descriptor), 'Root phase event binding')
        package = anchored(phase_root / 'PACKAGE-RECEIPT.json', descriptor['package_sha256'])
        known = inventory(phase_root, omit=('PACKAGE-RECEIPT.json',))
        need(package['status'] == 'complete' and package['phase'] == phase and package['frame_sha256'] == frame_sha and
             package['files'] == known, 'Phase package exact inventory/identity mismatch')
        output_bytes += sum(p['bytes'] for p in known.values()) + (phase_root / 'PACKAGE-RECEIPT.json').stat().st_size
        need(not any(Path(n).name in ('FAILURE.json', 'DEADLINE.json', 'FINALIZATION-FAILED.json') for n in known),
             'Failed package cannot be complete')
        job = load(phase_root / 'JOB.json')
        need(job['phase'] == phase and job['frame_sha256'] == frame_sha and
             job['cutoff'] == (complete['source_cutoff'] if phase == 'answer' else None), 'Worker job/frame/cutoff mismatch')
        if primary:
            parent_names = dict(expand=(), collect=('expand',), rank=('collect',), answer=('collect', 'rank'))[phase]
            need(job['parents'] == {p: complete['phases'][p] for p in parent_names}, 'Parent descriptor graph mismatch')
        else:
            need(job['collection'] == (None if phase == 'collect' else complete['phases']['collect']) and
                 Path(job['common_root']) == root, 'Diagnostic parent graph mismatch')
        worker_root = phase_root / 'worker'
        worker = load(worker_root / 'COMPLETE.json')
        config = load(worker_root / 'CONFIG.json')
        stage_root = worker_root / 'phase'
        need(worker['status'] == 'complete' and worker['phase'] == phase and worker['frame_sha256'] == frame_sha and
             worker['purpose'] == frame['purpose'] and worker['audit_denials'] == 0 and config['job'] == job and
             config['frame_sha256'] == frame_sha and config['purpose'] == frame['purpose'], 'Worker/config completion mismatch')
        need(worker['stage_receipt'] == proof(stage_root / 'STAGE-RECEIPT.json') and
             worker['stage_receipt']['sha256'] == descriptor['stage_receipt_sha256'], 'Worker stage receipt mismatch')
        branches = ('L', 'E') if phase in ('collect', 'rank') else ARMS if phase == 'answer' else ('shared',)
        if not primary:
            branches = ('shared',)
        rows = _stage(stage_root, descriptor['stage_receipt_sha256'], doi_ids if not primary and phase == 'collect' else ids,
                      branches, phase if primary else 'supplied', known)
        _product_bijection(stage_root, rows, phase)
        replay = load(phase_root / 'REPLAY.json')
        need(replay == load(phase_root / 'review/REPORT.json') and replay['status'] == 'verified' and
             replay['phase'] == phase and replay['frame_sha256'] == frame_sha and
             replay['stage_receipt_sha256'] == descriptor['stage_receipt_sha256'], 'Maintained replay binding mismatch')
        _phase_journals(phase_root, primary, phase, worker, descriptor['stage_receipt_sha256'])
        resources = _supervision(phase_root, frame, phase)
        resources['worker_wall_seconds'] = nonnegative(worker['wall_seconds' if primary else 'worker_wall_seconds'], 'Worker elapsed')
        need(resources['worker_wall_seconds'] < frame['phase_seconds'][phase], 'Worker overtime')
        resources['worker_memory'] = worker['worker_memory']
        for value in worker['worker_memory'].values():
            if value is not None:
                nonnegative(value, 'Worker resource measurement')
        model_info = None
        if phase != 'collect':
            model_info = load(worker_root / 'MODEL.json')
            need(model_info['provenance'] == model_frame['model_provenance'] and model_info['spec'] == model_frame['model_spec'] and
                 model_info['alias'] == model_frame['alias'] and worker['server_terminal']['server_stopped'] is True,
                 'Native model/cleanup mismatch')
            samples = load(worker_root / 'SERVER-RESOURCE-SAMPLES.json')
            good = [s['value'] for s in samples if s['error_class'] is None]
            for sample in good:
                for value in sample.values():
                    if value is not None:
                        nonnegative(value, 'Server resource sample')
            resources['server_peak_working_set_bytes'] = max((s['process_peak_working_set_bytes'] for s in good), default=None)
            resources['server_cpu_seconds_last_sample'] = good[-1]['cpu_seconds'] if good else None
            resources['server_resource_sample_errors'] = sum(s['error_class'] is not None for s in samples)
            resources['model'], cells = _native_resources(stage_root)
        else:
            need(worker['server_terminal'] is None, 'Collection unexpectedly used a model server')
            resources['http'] = _http_resources(stage_root)
            cells = []
        resources['io_audit'] = _io_audit(phase_root, frame, phase, primary, job, model_info, worker)
        result_phases[phase] = dict(root=str(phase_root), stage_root=str(stage_root), rows=rows,
                                   worker=worker, model_info=model_info, model_cells=cells)
        resource_phases[phase] = resources
    model_totals = {key: sum(p['model'][key] for p in resource_phases.values() if 'model' in p)
                    for key in ('generation_calls', 'tokenizer_calls', 'measured_input_tokens', 'measured_output_tokens',
                                'reserved_input_tokens', 'reserved_output_tokens', 'provider_cost_usd')}
    resources = dict(phases=resource_phases, physical_model=model_totals, physical_http=resource_phases['collect']['http'],
                     output_bytes=output_bytes, worker_wall_seconds_sum=sum(p['worker_wall_seconds'] for p in resource_phases.values()),
                     measured_gpu_memory_bytes=None, measured_energy_joules=None,
                     limits='Server CPU is last retained sample, not full shutdown CPU; process peaks are not aggregate RAM. '
                            'HTTP response bodies exclude wire overhead. Shared physical calls must not be summed once per arm.')
    return dict(root=str(root), root_sha256=expected_root_sha256, kind=actual_kind, frame=frame,
                frame_sha256=frame_sha, complete=complete, phases=result_phases, resources=resources,
                source_eligibility_reconstructed=False, semantic_predictions_reconstructed=False,
                scope='Independent externally anchored envelopes, full schedules and physical accounting; '
                      'requires separate source/native/scientific evaluation. Model weight bytes are not rehashed by this layer.')
