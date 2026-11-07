"""Adopt an externally accepted primary reconstruction after byte preservation checks.

This does not rerun semantic reconstruction, execute archived code, score answers,
or dispatch work. The external replay receipt is the trust anchor for the earlier
independent result. Original outputs, external metadata and both source archives
must still match their historical bindings; working-tree substitutions never apply.
"""
from pathlib import Path

from . import envelopes, source_archive
from .native_records import canonical, decode, digest, need, read, safe_path

STATUS = 'retained_independent_reconstruction_with_byte_recheck'
PHASES = ('expand', 'collect', 'rank', 'answer')
ARMS = ('L/O', 'E/O', 'L/R', 'E/R')
MAX_FILE_BYTES = 128 * 1024 ** 2


def _path(value):
    return safe_path(source_archive._absolute(str(value)))


def _same(left, right):
    return canonical(left) == canonical(right)


def _directories(root, files):
    expected = {str(Path(name).parent).replace('\\', '/') for name in files}
    expected.discard('.')
    expected |= {parent.as_posix() for name in tuple(expected) for parent in Path(name).parents
                 if str(parent) != '.'}
    actual = {path.relative_to(root).as_posix() for path in root.rglob('*') if path.is_dir()}
    need(actual == expected, 'Unbound directories in preserved package')


class _Inputs:
    """Parse only bytes checked against their proof, retaining external bindings."""
    def __init__(self):
        self.proofs = {}
        self.inventories = []

    def bound(self, proof):
        need(isinstance(proof, dict) and set(proof) == {'path', 'bytes', 'sha256'} and
             type(proof['bytes']) is int and 0 <= proof['bytes'] <= MAX_FILE_BYTES,
             'Exact bounded byte proof required')
        source_archive._hash(proof['sha256'])
        path = _path(proof['path'])
        need(str(path) == proof['path'], 'Canonical original proof path required')
        raw = read(path, MAX_FILE_BYTES)
        actual = dict(path=str(path), bytes=len(raw), sha256=digest(raw))
        need(_same(actual, proof), 'Retained input bytes changed')
        previous = self.proofs.setdefault(str(path), actual)
        need(_same(previous, actual), 'Input changed between checks')
        return raw

    def capture(self, path):
        path = _path(path)
        raw = read(path, MAX_FILE_BYTES)
        proof = dict(path=str(path), bytes=len(raw), sha256=digest(raw))
        previous = self.proofs.setdefault(str(path), proof)
        need(_same(previous, proof), 'Input changed between checks')
        return proof, raw

    def json(self, proof):
        return decode(self.bound(proof))

    def anchored(self, path, sha):
        source_archive._hash(sha)
        proof, raw = self.capture(path)
        need(proof['sha256'] == sha, 'External receipt anchor mismatch')
        return proof, decode(raw)

    def inventory(self, root, *, omit=(), recursive=True):
        root = _path(root)
        values = envelopes.inventory(root, omit=omit, recursive=recursive)
        for name, proof in values.items():
            source_archive._logical(name)
            need(proof['path'] == str(root.joinpath(*name.split('/'))), 'Inventory path substitution')
        if recursive:
            _directories(root, values)
        self.inventories.append((root, tuple(omit), recursive, values))
        return values

    def unchanged(self):
        for proof in tuple(self.proofs.values()):
            self.bound(proof)
        for root, omit, recursive, expected in self.inventories:
            need(_same(envelopes.inventory(root, omit=omit, recursive=recursive), expected),
                 'Preserved inventory changed during adoption')
            if recursive:
                _directories(root, expected)


def _chain(raw):
    need(raw.endswith(b'\n'), 'Incomplete retained journal')
    events, previous = [], None
    for ordinal, line in enumerate(raw.splitlines()):
        value = decode(line)
        sha = value.pop('sha256')
        need(set(value) == {'sequence', 'previous_sha256', 'event', 'details'} and
             type(value['sequence']) is int and value['sequence'] == ordinal and
             value['previous_sha256'] == previous and digest(canonical(value)) == sha,
             'Invalid retained journal chain')
        previous = sha
        events.append(value)
    return events


def _external_proofs(value, inputs):
    """Check declared frame metadata, without opening files referenced inside it."""
    if isinstance(value, dict):
        if set(value) == {'path', 'bytes', 'sha256'}:
            inputs.bound(value)
        else:
            for item in value.values():
                _external_proofs(item, inputs)
    elif isinstance(value, list):
        for item in value:
            _external_proofs(item, inputs)


def _archive(descriptor, pins, original_root, inputs):
    need(isinstance(descriptor, dict) and set(descriptor) == {'path', 'sha256'},
         'Explicit externally anchored source archive required')
    resolver = source_archive.load_archive(descriptor['path'], descriptor['sha256'], pins, original_root)
    inputs.bound(resolver.manifest_proof)
    proofs = {name: resolver.proof(name) for name in resolver.logical_names}
    for value in proofs.values():
        inputs.bound(value)
    return resolver.manifest_proof, proofs


def _primary(frame, report, inputs):
    root = _path(frame['primary_root'])
    proof, receipt = inputs.anchored(root / 'ROOT-RECEIPT.json', frame['primary_root_sha256'])
    files = inputs.inventory(root, omit=('ROOT-RECEIPT.json',), recursive=False)
    names = {'FRAME.json', 'COMPLETE.json', 'journal.jsonl'} | {phase + '-ANCHOR.json' for phase in PHASES}
    need(set(receipt) == {'status', 'frame_sha256', 'files'} and _same(receipt['files'], files) and
         set(files) == names and {p.name for p in root.iterdir() if p.is_dir()} == set(PHASES),
         'Original primary root membership changed')
    original = inputs.json(files['FRAME.json'])
    complete = inputs.json(files['COMPLETE.json'])
    need(original['kind'] == 'sc04_primary_execution_v1' and original['purpose'] in
         ('production', 'fictional_qualification') and original['phases'] == list(PHASES) and
         original['conditions'] == list(ARMS) + ['supplied_source_pending_separate_execution'] and
         receipt['status'] == complete['status'] == 'primary_execution_complete' and
         receipt['frame_sha256'] == files['FRAME.json']['sha256'] == report['frame_sha256'] and
         complete['purpose'] == original['purpose'] == report['purpose'] and
         report['root'] == str(root) and report['root_sha256'] == frame['primary_root_sha256'],
         'Original primary/report identity mismatch')
    need(set(complete['phases']) == set(PHASES) and complete['provider_cost_usd'] == 0 and
         complete['sc04_complete'] is False and complete['scientific_scoring_performed'] is False and
         complete['supplied_source_complete'] is False and original['automatic_retry'] is False and
         original['provider_spend_usd'] == 0, 'Primary completion scope differs')
    _external_proofs(original, inputs)
    queries = inputs.json(original['query_products']['answer_queries'])
    source = inputs.json(original['query_products']['source_queries'])
    ids = [q['id'] for q in queries]
    count = 199 if original['purpose'] == 'production' else 2
    need(len(ids) == len(set(ids)) == count == original['count'] and ids == original['schedule'] and
         _same(queries, report['queries']) and
         _same(source, [dict(id=q['id'], question=q['question']) for q in queries]),
         'Original query ordering or projection differs')
    need(set(report['records']) == set(report['source_cases']) == set(report['evidence_ids']) == set(ARMS),
         'Retained primary arm membership differs')
    for arm in ARMS:
        need([r['id'] for r in report['records'][arm]] == ids and
             [r['id'] for r in report['source_cases'][arm]] == ids and
             set(report['evidence_ids'][arm]) == set(ids), 'Retained primary row ordering differs')
    phases = {}
    for phase in PHASES:
        descriptor = complete['phases'][phase]
        phase_root = root / phase
        need(set(descriptor) == {'root', 'package_sha256', 'stage_receipt_sha256'} and
             descriptor['root'] == str(phase_root) and
             _same(inputs.json(files[phase + '-ANCHOR.json']), descriptor), 'Original phase descriptor differs')
        package_proof, package = inputs.anchored(phase_root / 'PACKAGE-RECEIPT.json', descriptor['package_sha256'])
        package_files = inputs.inventory(phase_root, omit=('PACKAGE-RECEIPT.json',))
        need(set(package) == {'status', 'phase', 'frame_sha256', 'files'} and
             package['status'] == 'complete' and package['phase'] == phase and
             package['frame_sha256'] == report['frame_sha256'] and _same(package['files'], package_files) and
             package_files['worker/phase/STAGE-RECEIPT.json']['sha256'] == descriptor['stage_receipt_sha256'],
             'Original phase bytes or identity changed')
        need(not any(Path(name).name in ('FAILURE.json', 'DEADLINE.json', 'FINALIZATION-FAILED.json')
                     for name in package_files), 'Contradictory original terminal artifact')
        phases[phase] = dict(receipt=package_proof, files=len(package_files),
                             bytes=sum(p['bytes'] for p in package_files.values()))
    return original, proof, phases, count


def _supervision(frame, files, inputs):
    seconds = frame['seconds']
    need(type(seconds) is int and 1 <= seconds <= 21600, 'Bounded original analysis timeout required')
    limits = dict(timeout_seconds=seconds, max_output_bytes=4 * 1024 ** 2)
    command = inputs.json(files['COMMAND.json'])
    expected = [frame['environment']['executable']['path'], '-I', '-B', frame['runner']['path'],
                'worker', files['FRAME.json']['path'], files['FRAME.json']['sha256']]
    need(_same(command, dict(argv=expected, limits=limits)), 'Original replay command binding differs')
    report = inputs.json(files['SUPERVISION.json'])
    need(report['schema_version'] == 1 and report['limits'] == limits and
         report['process_started'] is True and report['process_reaped'] is True and
         report['termination_reason'] == 'exited' and not report['cleanup_errors'] and
         report['observed_counts_are_lower_bounds'] is False and
         report['pipe_eof'] == dict(stdout=True, stderr=True), 'Retained replay supervision incomplete')
    total = 0
    for name in ('stdout', 'stderr'):
        size = len(inputs.bound(files[name + '.log']))
        need(type(report['observed_' + name + '_bytes']) is int and
             size == report['observed_' + name + '_bytes'] == report['retained_' + name + '_bytes'],
             'Retained replay stream accounting differs')
        total += size
    need(total <= limits['max_output_bytes'] and
         envelopes.nonnegative(report['execution_elapsed_seconds'], 'Replay elapsed') <= seconds and
         envelopes.nonnegative(report['total_elapsed_seconds'], 'Replay total elapsed') >= report['execution_elapsed_seconds'],
         'Retained replay supervision bounds differ')


def load(replay_root, external_receipt_sha, *, analyzer_archive):
    """Return the original report and explicit evidence for byte-only adoption.

    The caller supplies the previously accepted replay receipt and the archive
    anchor for the analyzer that ran then. This never substitutes current source
    or interpreter identity for historical proofs, nor refreshes semantic claims.
    """
    inputs = _Inputs()
    root = _path(replay_root)
    replay_proof, receipt = inputs.anchored(root / 'RECEIPT.json', external_receipt_sha)
    files = inputs.inventory(root, omit=('RECEIPT.json',))
    names = {'FRAME.json', 'COMMAND.json', 'SUPERVISION.json', 'stdout.log', 'stderr.log', 'journal.jsonl',
             'worker/RECEIPT.json', 'worker/RECONSTRUCTION.json', 'worker/RESOURCES.json', 'worker/journal.jsonl'}
    need(set(receipt) == {'status', 'files'} and receipt['status'] == 'complete' and
         _same(receipt['files'], files) and set(files) == names, 'Accepted replay exact inventory differs')
    frame = inputs.json(files['FRAME.json'])
    need(set(frame) == {'kind', 'primary_root', 'primary_root_sha256', 'archive', 'runner', 'code_proofs',
        'environment', 'seconds', 'automatic_retry', 'scientific_scoring', 'new_http_calls', 'new_model_calls'} and
         frame['kind'] == 'sc04_primary_independent_replay_v1' and frame['automatic_retry'] is False and
         frame['scientific_scoring'] is False and type(frame['new_http_calls']) is int and frame['new_http_calls'] == 0 and
         type(frame['new_model_calls']) is int and frame['new_model_calls'] == 0, 'Retained replay frame scope differs')
    worker_receipt = inputs.json(files['worker/RECEIPT.json'])
    worker_files = {name.removeprefix('worker/'): value for name, value in files.items()
                    if name.startswith('worker/') and name != 'worker/RECEIPT.json'}
    need(_same(worker_receipt, dict(status='complete', frame_sha256=files['FRAME.json']['sha256'], files=worker_files)) and
         _same(inputs.json(files['stdout.log']), dict(status='complete', receipt=files['worker/RECEIPT.json'])),
         'Retained replay worker binding differs')
    report = inputs.json(files['worker/RECONSTRUCTION.json'])
    need(report['status'] == 'independently_reconstructed' and report['source_lineage_checked'] is True and
         report['native_calls_checked'] is True and report['cross_stage_products_checked'] is True and
         report['scientific_correctness_scored'] is False and report['model_weight_bytes_rehashed'] is False,
         'Retained report is not the required unscored reconstruction')
    original, primary_proof, phases, count = _primary(frame, report, inputs)
    producer_record = report['executed_source_archive']
    need(isinstance(producer_record, dict) and set(producer_record) == {'path', 'bytes', 'sha256', 'original_repository_root'} and
         _same(frame['archive'], {k: producer_record[k] for k in ('path', 'sha256')}), 'Original producer archive binding differs')
    original_root = producer_record['original_repository_root']
    producer_manifest, producer_proofs = _archive(frame['archive'], original['code_pins'], original_root, inputs)
    need(_same(producer_record, dict(producer_manifest, original_repository_root=original_root)) and
         _same(producer_proofs, report['executed_source_proofs']), 'Executed producer proof membership differs')
    code = frame['code_proofs']
    need(isinstance(code, dict) and code and
         {'experiments/litqa_analysis/reconstruct_run.py', 'experiments/litqa_analysis/envelopes.py',
          'experiments/litqa_analysis/native_records.py', 'experiments/litqa_analysis/source_archive.py'} <= set(code),
         'Missing original analyzer closure')
    for name, proof in code.items():
        source_archive._logical(name)
        need(set(proof) == {'path', 'bytes', 'sha256'} and
             proof['path'] == str(Path(original_root).joinpath(*name.split('/'))), 'Original analyzer source locator differs')
    analyzer_manifest, analyzer_proofs = _archive(analyzer_archive, {n: p['sha256'] for n, p in code.items()}, original_root, inputs)
    need(all(analyzer_proofs[n]['bytes'] == code[n]['bytes'] for n in code), 'Archived analyzer size differs')
    inputs.bound(frame['runner'])
    _external_proofs(frame['environment'], inputs)
    _supervision(frame, files, inputs)
    events = _chain(inputs.bound(files['journal.jsonl']))
    worker_events = _chain(inputs.bound(files['worker/journal.jsonl']))
    need([e['event'] for e in events] == ['analysis_reserved', 'worker_dispatch', 'worker_accepted'] and
         events[1]['details'] == dict(frame_sha256=files['FRAME.json']['sha256']) and
         _same(events[2]['details'], dict(receipt=files['worker/RECEIPT.json'])) and
         [e['event'] for e in worker_events] == ['analysis_reserved', 'source_inclusive_reconstruction_started',
                                              'source_inclusive_reconstruction_complete'] and
         worker_events[1]['details'] == dict(primary_root_sha256=frame['primary_root_sha256']) and
         worker_events[2]['details'] == dict(questions=count, records=4 * count), 'Retained replay journal claims differ')
    resources = inputs.json(files['worker/RESOURCES.json'])
    need(resources['new_model_calls'] == resources['new_http_calls'] == 0 and resources['scientific_scoring'] is False and
         envelopes.nonnegative(resources['wall_seconds'], 'Original analysis elapsed') <= frame['seconds'],
         'Retained replay resource scope differs')
    inputs.unchanged()
    return dict(status=STATUS, report=report, adoption=dict(status=STATUS, replay_receipt=replay_proof,
        reconstruction=files['worker/RECONSTRUCTION.json'], primary_receipt=primary_proof,
        primary_frame_sha256=report['frame_sha256'], phase_preservation=phases,
        analyzer_archive=analyzer_manifest, analyzer_files=len(analyzer_proofs),
        producer_archive=producer_manifest, producer_files=len(producer_proofs),
        questions=count, answer_records=4 * count, semantic_reconstruction_recomputed=False,
        archived_code_executed=False, model_weight_bytes_rehashed=False, scientific_correctness_scored=False,
        new_model_calls=0, new_http_calls=0,
        scope='Original independent report adopted by externally anchored byte preservation; semantics and scientific correctness are not newly evaluated.'))
