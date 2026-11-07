"""Stream a pinned ALCE TAR into complete, role-separated supplied-document views.

Preparation is a trusted mixed-role operation. Generation readers receive only
their exact projected-file proof; original rows and archive access are evaluator
permissions. No scoring, inference, extraction of arbitrary archive paths, or
claim of hostile-process isolation is provided here. Deadlines are cooperative;
actual preparation also requires an outer process/resource supervisor.
"""
from collections.abc import Mapping
from dataclasses import asdict, dataclass
import hashlib
import math
import os
from pathlib import Path
import re
import stat
import tarfile
import time
import unicodedata

from tether_engine import serde
from tether_engine.serde import ContractError, canonical, freeze, parse_json

FAMILIES = ('asqa', 'qampari', 'eli5')
MEMBERS = dict(asqa='data/asqa_eval_gtr_top100.json',
               qampari='data/qampari_eval_gtr_top100.json',
               eli5='data/eli5_eval_bm25_top100.json')
ID_FIELDS = ('id', 'qid', 'question_id', 'sample_id')
BLOCK = 1024 * 1024


@dataclass(frozen=True)
class Limits:
    archive_bytes: int = 512 * 1024**2
    expanded_bytes: int = 512 * 1024**2
    member_bytes: int = 256 * 1024**2
    output_bytes: int = 1024 * 1024**2
    members: int = 10000
    rows_per_family: int = 10000
    docs_per_row: int = 10000
    seconds: int = 1800

    def __post_init__(self):
        need(all(type(v) is int and v > 0 for v in asdict(self).values()), 'Positive integer preparation limits required')


def need(value, message):
    if not value:
        raise ContractError(message)


def _tick(end):
    if time.monotonic() >= end:
        raise TimeoutError('ALCE preparation deadline expired')


def _logical(value):
    need(isinstance(value, str) and value and '\\' not in value and
         unicodedata.normalize('NFC', value) == value, 'Canonical logical path required')
    parts = value.split('/')
    for part in parts:
        need(part not in ('', '.', '..') and part.rstrip(' .') == part and
             not any(ord(c) < 32 or c in ':<>"|?*' for c in part), 'Unsafe logical path')
        need(part.split('.')[0].upper() not in {'CON', 'PRN', 'AUX', 'NUL'} and
             re.fullmatch(r'(COM|LPT)[1-9\u00b9\u00b2\u00b3]', part.split('.')[0].upper()) is None,
             'Reserved logical path')
    return value


def _path(value):
    need(isinstance(value, (str, Path)), 'Local path required')
    text = str(value)
    need(not text.startswith(('\\\\', '//')) and
         all(x not in ('.', '..') for x in text.replace('\\', '/').split('/')), 'Aliased local path')
    path = Path(value)
    need(path.is_absolute(), 'Absolute local path required')
    _logical('/'.join(path.parts[1:]))
    for parent in (*reversed(path.parents), path):
        try:
            info = parent.lstat()
        except FileNotFoundError:
            continue
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
             'Linked/reparse path')
    return path


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _proof(value):
    need(isinstance(value, Mapping) and set(value) == {'path', 'bytes', 'sha256'}, 'Exact file proof required')
    need(type(value['bytes']) is int and value['bytes'] >= 0 and isinstance(value['sha256'], str)
         and re.fullmatch('[0-9a-f]{64}', value['sha256']), 'Invalid file proof')
    return _path(value['path'])


def _hash(path, end):
    path = _path(path)
    before = path.stat()
    need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'Single regular source file required')
    total, h = 0, hashlib.sha256()
    with path.open('rb') as stream:
        need(_identity(os.fstat(stream.fileno())) == _identity(before), 'Input changed before hashing')
        while True:
            _tick(end)
            chunk = stream.read(BLOCK)
            if not chunk:
                break
            total += len(chunk)
            need(total <= before.st_size, 'Input grew during hashing')
            h.update(chunk)
        need(_identity(os.fstat(stream.fileno())) == _identity(before), 'Input changed during hashing')
    need(total == before.st_size and _identity(_path(path).stat()) == _identity(before), 'Input changed after hashing')
    return dict(path=str(path), bytes=total, sha256=h.hexdigest())


def _read(proof, maximum, end):
    path = _proof(proof)
    need(proof['bytes'] <= maximum, 'Bound metadata/member exceeds configured limit')
    before = path.stat()
    need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size == proof['bytes'], 'Changed/nonregular bound file')
    with path.open('rb') as stream:
        _tick(end)
        need(_identity(os.fstat(stream.fileno())) == _identity(before), 'Input changed before capture')
        raw = stream.read(before.st_size + 1)
        need(_identity(os.fstat(stream.fileno())) == _identity(before), 'Input changed during capture')
    need(len(raw) == proof['bytes'] and hashlib.sha256(raw).hexdigest() == proof['sha256'] and
         _identity(_path(path).stat()) == _identity(before), 'Bound bytes changed')
    _tick(end)
    return raw


def _acquisition(archive, receipt_proof, asset_id, end):
    """Bind the exact asset through the externally anchored transport receipt."""
    _proof(archive)
    root = parse_json(_read(receipt_proof, 16 * 1024**2, end))
    need(root.get('kind') == 'alce_acquisition_receipt_v1' and root.get('status') == 'verified' and
         type(root.get('automatic_retries')) is int and root['automatic_retries'] == 0 and root.get('range_resume') is False and
         root.get('payload_hashes_rechecked') is True, 'Successful acquisition receipt required')
    for name in ('FAILURE.json', 'DEADLINE.json', 'FINALIZATION-FAILED.json',
                 'FAILED.json', 'SUPERVISOR-FAILED.json', 'STALLED.json'):
        need(not (_path(receipt_proof['path']).parent / name).exists(), 'Acquisition terminal contradiction')
    worker = parse_json(_read(root['worker_receipt'], 16 * 1024**2, end))
    need(worker.get('kind') == 'alce_acquisition_worker_receipt_v1' and worker.get('status') == 'completed'
         and worker.get('manifest') == root['manifest'] and worker.get('hard_parent_supervision') is True,
         'Acquisition worker binding')
    manifest = parse_json(_read(root['manifest'], 16 * 1024**2, end))
    need(manifest.get('kind') == 'alce_acquisition_manifest_v1', 'Acquisition manifest kind')
    process = _acquisition_process(root['process'], _path(receipt_proof['path']).parent,
                                   manifest['limits']['total_seconds'], end)
    entries = worker['files']
    need(isinstance(entries, list) and len({e['id'] for e in entries}) == len(entries), 'Unique acquired asset IDs')
    matches = [e for e in entries if e['id'] == asset_id]
    planned = [e for e in manifest['assets'] if e['id'] == asset_id]
    need(len(matches) == len(planned) == 1, 'Exact planned/acquired archive asset')
    entry, asset = matches[0], planned[0]
    need(entry.get('status') == 'completed' and type(entry.get('attempts')) is int and entry['attempts'] == 1,
         'Single completed archive transfer')
    need({k: entry[k] for k in ('path', 'bytes', 'sha256')} == dict(archive), 'Archive receipt byte binding')
    need(asset['expected_bytes'] == archive['bytes'] and
         asset['digest'] == dict(algorithm='sha256', kind='content', value=archive['sha256']) and
         all(entry[k] == asset[k] for k in ('destination', 'revision', 'digest', 'metadata_proof', 'rights_reference')),
         'Planned archive identity binding')
    return dict(receipt=dict(receipt_proof), worker_receipt=root['worker_receipt'],
                manifest=root['manifest'], process=process, asset_id=asset_id)


def _acquisition_process(process_proof, root, maximum_seconds, end):
    need(_proof(process_proof) == root/'PROCESS.json', 'Acquisition process locator')
    value = parse_json(_read(process_proof, 1024**2, end))
    need(set(value) == {'returncode','supervision'} and type(value['returncode']) is int and
         value['returncode'] == 0, 'Acquisition process successful return required')
    p = value['supervision']
    keys = {'schema_version','method','limits','termination_reason','execution_elapsed_seconds',
            'total_elapsed_seconds','retained_stdout_bytes','retained_stderr_bytes','observed_stdout_bytes',
            'observed_stderr_bytes','observed_counts_are_lower_bounds','pipe_eof','process_started',
            'process_reaped','cleanup_errors'}
    need(isinstance(p,dict) and set(p) == keys and type(p['schema_version']) is int and p['schema_version']==1 and
         p['method']=='tether.process_envelope.v1' and p['termination_reason']=='exited' and
         p['process_started'] is True and p['process_reaped'] is True and p['cleanup_errors']==[] and
         p['observed_counts_are_lower_bounds'] is False and isinstance(p['pipe_eof'],dict) and
         set(p['pipe_eof'])=={'stdout','stderr'} and all(x is True for x in p['pipe_eof'].values()),
         'Acquisition process reaped/closed supervision required')
    limits=p['limits']
    need(isinstance(limits,dict) and set(limits)=={'timeout_seconds','max_output_bytes'} and
         type(maximum_seconds) is int and maximum_seconds>0 and
         type(limits['timeout_seconds']) in (int,float) and math.isfinite(limits['timeout_seconds']) and
         0<limits['timeout_seconds']<=maximum_seconds and type(limits['max_output_bytes']) is int and
         limits['max_output_bytes']==4*BLOCK,'Acquisition process limits')
    for name in ('execution_elapsed_seconds','total_elapsed_seconds'):
        need(type(p[name]) in (int,float) and math.isfinite(p[name]) and p[name]>=0,'Acquisition process time')
    need(p['execution_elapsed_seconds']<limits['timeout_seconds'] and
         p['execution_elapsed_seconds']<=p['total_elapsed_seconds']<=maximum_seconds,'Acquisition process clock bounds')
    streams={}
    for name in ('stdout','stderr'):
        path=_path(root/f'{name}.bin')
        need(path.stat().st_size<=limits['max_output_bytes'],'Acquisition stream byte cap')
        streams[name]=_hash(path,end)
        for prefix in ('retained','observed'):
            count=p[f'{prefix}_{name}_bytes']
            need(type(count) is int and count==streams[name]['bytes'],'Acquisition stream count binding')
    need(sum(x['bytes'] for x in streams.values())<=limits['max_output_bytes'],'Acquisition aggregate streams bound')
    return dict(proof=dict(process_proof),streams=streams)


class _Header(tarfile.TarInfo):
    @classmethod
    def frombuf(cls, buf, encoding, errors):
        value = super().frombuf(buf, encoding, errors)
        # Reject extension records before tarfile can allocate their payload.
        need(value.type in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE),
             'Only regular files/directories allowed; links, sparse and extension records rejected')
        need(not value.linkname and not value.sparse and not value.pax_headers, 'No TAR indirection')
        _logical(value.name)
        # TarInfo strips directory slashes: permit one conventional trailing slash only.
        raw_name = buf[:100].split(b'\0', 1)[0].decode(encoding, errors)
        need(not raw_name.endswith('//'), 'Aliased directory header')
        need(value.size >= 0 and (not value.isdir() or value.size == 0), 'Invalid TAR member size')
        return value


def _scan(archive, members, limits, end, selected):
    """Stream all regular members; callback receives only an exact selected member."""
    path = _proof(archive)
    need(archive['bytes'] <= limits.archive_bytes and archive['bytes'] % 512 == 0, 'Bounded plain TAR required')
    need(_hash(path, end) == dict(archive), 'Archive strong hash differs')
    before = path.stat()
    inventory, paths, folded, prefixes, expanded, found = [], {}, {}, {}, 0, set()
    family_for = {v: k for k, v in members.items()}
    with path.open('rb') as stream:
        need(_identity(os.fstat(stream.fileno())) == _identity(before), 'Archive replaced before inventory')
        with tarfile.open(fileobj=stream, mode='r|', tarinfo=_Header, encoding='utf-8', errors='strict') as tar:
            for item in tar:
                _tick(end)
                name = _logical(item.name)
                need(len(inventory) < limits.members and name.casefold() not in folded, 'Duplicate/colliding TAR path or member limit')
                parts = name.split('/')
                for length in range(1,len(parts)+1):
                    prefix = '/'.join(parts[:length])
                    need(prefixes.get(prefix.casefold(),prefix) == prefix,'Case-colliding TAR ancestor alias')
                    prefixes[prefix.casefold()] = prefix
                for parent in Path(name).parents:
                    if str(parent) != '.':
                        need(paths.get(parent.as_posix()) != 'file', 'File/directory TAR collision')
                need(not any(p.startswith(name + '/') for p in paths) or item.isdir(), 'File shadows TAR directory')
                folded[name.casefold()] = name
                paths[name] = 'directory' if item.isdir() else 'file'
                record = dict(path=name, kind=paths[name], bytes=item.size, sha256=None)
                if item.isfile():
                    expanded += item.size
                    need(expanded <= limits.expanded_bytes and item.size <= limits.member_bytes, 'Expanded/member TAR limit')
                    h, total = hashlib.sha256(), 0
                    src = tar.extractfile(item)
                    need(src is not None, 'Missing TAR member stream')

                    def chunks():
                        nonlocal total
                        while True:
                            _tick(end)
                            block = src.read(BLOCK)
                            if not block:
                                break
                            total += len(block)
                            need(total <= item.size, 'TAR member grew')
                            h.update(block)
                            yield block

                    if name in family_for:
                        found.add(name)
                        selected(family_for[name], chunks(), item.size)
                    else:
                        for _ in chunks():
                            pass
                    need(total == item.size, 'Incomplete TAR member')
                    record['sha256'] = h.hexdigest()
                inventory.append(record)
            trailing = 0
            while True:
                _tick(end)
                block = tar.fileobj.read(BLOCK)
                if not block:
                    break
                trailing += len(block)
                need(not block.strip(b'\0'), 'Nonzero/concatenated TAR tail')
            need(trailing >= 512, 'Two TAR terminal blocks required')
        need(_identity(os.fstat(stream.fileno())) == _identity(before), 'Archive changed during inventory')
    need(found == set(members.values()), 'Missing exact scheduled family member')
    need(_hash(path, end) == dict(archive), 'Archive changed after inventory')
    return dict(members=inventory, member_count=len(inventory), expanded_file_bytes=expanded)


def _text(value, *, empty=False):
    return isinstance(value, str) and (empty or bool(value.strip()))


def _finite_json(value):
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, float):
            need(math.isfinite(item),'Nonfinite JSON metadata')
        elif isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item,list):
            pending.extend(item)


def _references(row, family):
    """Validate native-required shapes without interpreting reference correctness."""
    if family == 'qampari':
        answers = row.get('answers')
        need(isinstance(answers, list) and answers and all(isinstance(a, list) and a and
             all(_text(x) for x in a) for a in answers), 'Native QAMPARI answer groups required')
        return
    need(_text(row.get('answer')), 'Native family reference answer required')
    if family == 'eli5':
        need(isinstance(row.get('claims'), list) and row['claims'] and
             all(_text(x) for x in row['claims']), 'Native ELI5 claims required')
        return
    pairs, annotations = row.get('qa_pairs'), row.get('annotations')
    need(isinstance(pairs, list) and pairs and all(isinstance(p, dict) and _text(p.get('question')) and
         isinstance(p.get('short_answers'), list) and p['short_answers'] and
         all(_text(x) for x in p['short_answers']) for p in pairs), 'Native ASQA QA pairs required')
    need(isinstance(annotations, list) and len(annotations) >= 2 and
         all(isinstance(a, dict) and _text(a.get('long_answer')) for a in annotations), 'Native ASQA references required')


def project(raw, *, family, member, archive_sha256, identity_field, limits=Limits(), end=None):
    """Pure full-family projection. Unknown fields remain only in original raw bytes."""
    end = time.monotonic() + limits.seconds if end is None else end
    need(family in FAMILIES and identity_field in (*ID_FIELDS, None), 'Declared native family/identity field')
    _logical(member)
    need(isinstance(archive_sha256,str) and re.fullmatch('[0-9a-f]{64}',archive_sha256),'Archive identity SHA256 required')
    need(len(raw) <= limits.member_bytes, 'Selected member JSON limit')
    rows = parse_json(raw)
    _finite_json(rows)
    need(isinstance(rows, list) and 0 < len(rows) <= limits.rows_per_family, 'Nonempty complete JSON row array required')
    generation, schedule, ids, questions, excluded = [], [], set(), set(), {}
    for ordinal, row in enumerate(rows):
        _tick(end)
        need(isinstance(row, dict) and _text(row.get('question')) and isinstance(row.get('docs'), list), 'Question/docs schema')
        _references(row, family)
        qhash = hashlib.sha256(row['question'].encode('utf-8')).hexdigest()
        need(qhash not in questions, 'Duplicate exact question within family')
        questions.add(qhash)
        available = [key for key in ID_FIELDS if key in row]
        if identity_field is None:
            need(not available, 'Question-hash fallback requires genuinely absent upstream IDs')
            identity = dict(kind='question_sha256_fallback', upstream_field=None, upstream_value=None)
            case_id = f'{family}:question_sha256:{qhash}'
        else:
            need(identity_field in row and type(row[identity_field]) in (str, int) and
                 (type(row[identity_field]) is int or _text(row[identity_field])), 'Valid declared upstream ID required')
            need(all(row[k] == row[identity_field] and type(row[k]) is type(row[identity_field]) for k in available),
                 'Conflicting upstream ID fields')
            identity = dict(kind='upstream', upstream_field=identity_field, upstream_value=row[identity_field])
            case_id = f'{family}:upstream:' + hashlib.sha256(canonical(identity)).hexdigest()
        need(case_id not in ids, 'Duplicate upstream identity')
        ids.add(case_id)
        docs = row['docs']
        need(len(docs) <= limits.docs_per_row, 'Document count limit')
        for doc in docs:
            need(isinstance(doc, dict) and _text(doc.get('title'), empty=True) and _text(doc.get('text')), 'Raw title/text required')
        chosen, source_bindings = [], []
        for index, doc in enumerate(docs[:5], 1):
            locator = dict(archive_sha256=archive_sha256, member=member, row_ordinal=ordinal, doc_position=index)
            source_id = 'alce:' + hashlib.sha256(canonical(locator)).hexdigest()
            chosen.append(dict(source_id=source_id, citation_position=index, title=doc['title'], text=doc['text']))
            source_bindings.append(dict(source_id=source_id, original_doc_position=index,
                                        identity_kind='archive_member_row_document_locator'))
        generation.append(dict(id=case_id, question=row['question'], docs=chosen))
        schedule.append(dict(id=case_id, family=family, row_ordinal=ordinal, member=member,
            question_sha256=qhash, identity=identity, original_document_count=len(docs),
            selected_document_count=len(chosen), sources=source_bindings))
        for key in set(row) - {'question', 'docs'}:
            excluded['row:' + key] = excluded.get('row:' + key, 0) + 1
        for doc in docs:
            for key in set(doc) - {'title', 'text'}:
                excluded['document:' + key] = excluded.get('document:' + key, 0) + 1
    # Strict serialization also rejects nonfinite values hidden in preserved IDs.
    canonical(schedule)
    return dict(generation=generation, schedule=schedule, excluded_field_occurrences=excluded)


def _configuration(members, identity_fields, limits):
    need(isinstance(limits, Limits) and isinstance(members, Mapping) and set(members) == set(FAMILIES)
         and isinstance(identity_fields, Mapping) and set(identity_fields) == set(FAMILIES), 'All three families required')
    for family in FAMILIES:
        _logical(members[family])
        need(Path(members[family]).name == Path(MEMBERS[family]).name, 'Exact original retrieval condition required')
        need(identity_fields[family] in (*ID_FIELDS, None), 'Explicit upstream-ID or absent-ID declaration required')
    need(len(set(members.values())) == 3, 'Distinct explicit family members required')


class _Writer:
    def __init__(self, root, maximum):
        self.root, self.maximum, self.total = root, maximum, 0

    def chunks(self, relative, chunks):
        _logical(relative)
        path = _path(self.root / relative)
        with path.open('xb') as stream:
            for block in chunks:
                self.total += len(block)
                need(self.total <= self.maximum, 'Preparation output byte limit')
                stream.write(block)
            stream.flush()
            os.fsync(stream.fileno())

    def json(self, relative, value):
        self.chunks(relative, [canonical(value) + b'\n'])


def prepare(archive, acquisition_receipt, asset_id, output, *, members=MEMBERS,
            identity_fields, source_proofs, limits=Limits()):
    """Create one fresh preparation; keep incomplete outputs and FAILURE on error."""
    _configuration(members, identity_fields, limits)
    need(isinstance(source_proofs, Mapping) and set(source_proofs) == {'run.py', 'eval.py'}, 'Pinned native source proofs required')
    paths = [_proof(x) for x in (archive, acquisition_receipt, *source_proofs.values())]
    root = _path(output)
    need(root.parent.is_dir() and not root.exists() and
         all(root != p and root not in p.parents and p not in root.parents for p in paths), 'Fresh separate output required')
    start = time.monotonic()
    end = start + limits.seconds
    # Exclusive directory creation is the only ownership claim; never reopen it.
    root.mkdir()
    writer = _Writer(root, limits.output_bytes)
    try:
        request = dict(schema_version=1, kind='alce_data_preparation_request_v1', archive=dict(archive),
            acquisition_receipt=dict(acquisition_receipt), asset_id=asset_id, members=dict(members),
            identity_fields=dict(identity_fields), limits=asdict(limits), source_proofs=dict(source_proofs),
            adapter=_hash(Path(__file__).resolve(), end), serde=_hash(Path(serde.__file__).resolve(), end))
        writer.json('REQUEST.json', request)
        for p in source_proofs.values():
            _read(p, 8 * 1024**2, end)
        binding = _acquisition(archive, acquisition_receipt, asset_id, end)
        (root / 'evaluation').mkdir()
        (root / 'generation').mkdir()
        inventory = _scan(archive, members, limits, end,
                          lambda family, chunks, size: writer.chunks(f'evaluation/{family}.json', chunks))
        writer.json('INVENTORY.json', inventory)
        schedules, generation_files, evaluator_files, excluded = {}, {}, {}, {}
        for family in FAMILIES:
            raw_proof = _hash(root / f'evaluation/{family}.json', end)
            result = project(_read(raw_proof, limits.member_bytes, end), family=family, member=members[family],
                archive_sha256=archive['sha256'], identity_field=identity_fields[family], limits=limits, end=end)
            writer.json(f'generation/{family}.json', result['generation'])
            schedules[family] = result['schedule']
            generation_files[family] = _hash(root / f'generation/{family}.json', end)
            evaluator_files[family] = raw_proof
            excluded[family] = result['excluded_field_occurrences']
        writer.json('SCHEDULE.json', schedules)
        writer.json('GENERATION.json', dict(schema_version=1, kind='alce_generation_files_v1',
            condition='original_retrieved_order_first_five', files=generation_files))
        writer.json('EVALUATION.json', dict(schema_version=1, kind='alce_evaluator_originals_v1',
            role='evaluator_only', archive=dict(archive), acquisition=binding, original_members=evaluator_files,
            schedule=_hash(root / 'SCHEDULE.json', end), unknown_fields_preserved=True,
            excluded_field_occurrences=excluded))
        # No success can be issued after source or archive drift.
        need(_hash(_proof(archive), end) == dict(archive), 'Archive changed before sealing')
        need(_acquisition(archive, acquisition_receipt, asset_id, end) == binding,
             'Acquisition evidence changed before sealing')
        for p in (*source_proofs.values(), request['adapter'], request['serde']):
            _read(p, 8 * 1024**2, end)
        writer.json('COMPLETE.json', dict(status='prepared', families=list(FAMILIES),
            counts={f:len(schedules[f]) for f in FAMILIES}, full_selected_members=True,
            per_case_filtering=False, top_documents=5, wall_seconds=time.monotonic()-start,
            native_execution=False, scientific_correctness_evaluated=False))
        files = {p.relative_to(root).as_posix():_hash(p, end) for p in sorted(root.rglob('*')) if p.is_file()}
        writer.json('RECEIPT.json', dict(kind='alce_data_preparation_receipt_v1', status='prepared', files=files))
        return freeze(dict(root=str(root), receipt_sha256=_hash(root/'RECEIPT.json', end)['sha256']))
    except BaseException as error:
        try:
            # Reserve failure metadata outside the normal payload budget.
            with (_path(root) / 'FAILURE.json').open('xb') as stream:
                stream.write(canonical(dict(status='failed', error_type=type(error).__name__,
                    complete=False, automatic_retry=False, payloads_preserved=True)) + b'\n')
        except BaseException as persistence:
            error.add_note('Failure retention failed: ' + type(persistence).__name__)
        raise


def load_generation(proof, *, maximum=256 * 1024**2):
    """Read only a directly authorized generation file, never a coordinator package."""
    need(type(maximum) is int and maximum > 0, 'Generation byte ceiling required')
    rows = parse_json(_read(proof, maximum, time.monotonic()+60))
    need(isinstance(rows, list) and rows, 'Generation rows required')
    ids = set()
    for row in rows:
        need(isinstance(row, dict) and set(row) == {'id','question','docs'} and _text(row['id']) and
             row['id'] not in ids and _text(row['question']) and isinstance(row['docs'], list) and
             len(row['docs']) <= 5, 'Strict generation row allowlist')
        ids.add(row['id'])
        doc_ids = set()
        for position, doc in enumerate(row['docs'], 1):
            need(isinstance(doc, dict) and set(doc) == {'title','text','source_id','citation_position'} and
                 _text(doc['title'], empty=True) and _text(doc['text']) and
                 isinstance(doc['source_id'], str) and re.fullmatch('alce:[0-9a-f]{64}',doc['source_id']) and
                 doc['source_id'] not in doc_ids and type(doc['citation_position']) is int and
                 doc['citation_position'] == position, 'Strict generation document allowlist')
            doc_ids.add(doc['source_id'])
    return freeze(rows)


def verify_preparation(root, receipt_sha256):
    """Rebuild every projection from the anchored original TAR once, without writes."""
    root = _path(root)
    started = time.monotonic()
    end = started+1800
    receipt_proof = _hash(root/'RECEIPT.json', end)
    need(receipt_proof['sha256'] == receipt_sha256, 'External preparation receipt anchor')
    receipt = parse_json(_read(receipt_proof, 16*1024**2, end))
    need(receipt.get('kind') == 'alce_data_preparation_receipt_v1' and receipt.get('status') == 'prepared', 'Prepared receipt required')
    expected = {'REQUEST.json','INVENTORY.json','SCHEDULE.json','GENERATION.json','EVALUATION.json','COMPLETE.json',
                *(f'{role}/{f}.json' for role in ('generation','evaluation') for f in FAMILIES)}
    need(set(receipt['files']) == expected, 'Exact preparation files')
    def membership():
        files,dirs=set(),set()
        for path in root.rglob('*'):
            _path(path)
            info=path.lstat()
            need(stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode),'Regular preparation membership')
            (files if stat.S_ISREG(info.st_mode) else dirs).add(path.relative_to(root).as_posix())
        need(files == expected | {'RECEIPT.json'} and dirs == {'generation','evaluation'},
             'Closed preparation membership/failure precedence')
    membership()
    for name,p in receipt['files'].items():
        need(Path(p['path']) == root/name and _hash(root/name,end) == p, 'Preparation member binding')
    request = parse_json(_read(receipt['files']['REQUEST.json'], 16*1024**2,end))
    need(set(request)=={'schema_version','kind','archive','acquisition_receipt','asset_id','members',
                       'identity_fields','limits','source_proofs','adapter','serde'} and
         request['schema_version']==1 and request['kind']=='alce_data_preparation_request_v1' and
         set(request['source_proofs'])=={'run.py','eval.py'},'Exact preparation request/source schema')
    limits = Limits(**request['limits'])
    _configuration(request['members'],request['identity_fields'],limits)
    end = started+limits.seconds
    _tick(end)
    for p in (*request['source_proofs'].values(),request['adapter'],request['serde']):
        _read(p,8*1024**2,end)
    need(Path(request['adapter']['path']) == Path(__file__).resolve() and
         Path(request['serde']['path']) == Path(serde.__file__).resolve(), 'Current projector implementation binding')
    binding = _acquisition(request['archive'],request['acquisition_receipt'],request['asset_id'],end)
    schedules, excluded, generation_files, evaluator_files = {}, {}, {}, {}

    def selected(family,chunks,size):
        raw = b''.join(chunks)  # One selected, size-checked member; never the whole archive.
        expected_raw = receipt['files'][f'evaluation/{family}.json']
        need(len(raw) == expected_raw['bytes'] and hashlib.sha256(raw).hexdigest() == expected_raw['sha256'], 'Evaluator original copy differs')
        view = project(raw,family=family,member=request['members'][family],archive_sha256=request['archive']['sha256'],
                       identity_field=request['identity_fields'][family],limits=limits,end=end)
        gp = receipt['files'][f'generation/{family}.json']
        need(canonical(view['generation'])+b'\n' == _read(gp,limits.output_bytes,end), 'Exact original projection differs')
        schedules[family],excluded[family] = view['schedule'],view['excluded_field_occurrences']
        generation_files[family],evaluator_files[family] = gp,expected_raw

    inventory = _scan(request['archive'],request['members'],limits,end,selected)
    rebuilt = {'INVENTORY.json':inventory,'SCHEDULE.json':schedules,
        'GENERATION.json':dict(schema_version=1,kind='alce_generation_files_v1',
            condition='original_retrieved_order_first_five',files=generation_files),
        'EVALUATION.json':dict(schema_version=1,kind='alce_evaluator_originals_v1',role='evaluator_only',
            archive=request['archive'],acquisition=binding,original_members=evaluator_files,
            schedule=receipt['files']['SCHEDULE.json'],unknown_fields_preserved=True,excluded_field_occurrences=excluded)}
    for name,obj in rebuilt.items():
        need(canonical(obj)+b'\n' == _read(receipt['files'][name],limits.output_bytes,end), 'Preparation projection metadata differs')
    complete = parse_json(_read(receipt['files']['COMPLETE.json'],1024**2,end))
    need(complete['status']=='prepared' and complete['counts']=={f:len(schedules[f]) for f in FAMILIES} and
         complete['families']==list(FAMILIES) and complete['full_selected_members'] is True and
         complete['per_case_filtering'] is False and complete['top_documents']==5 and
         complete['native_execution'] is False and complete['scientific_correctness_evaluated'] is False and
         type(complete['wall_seconds']) in (int,float) and math.isfinite(complete['wall_seconds']) and
         0 <= complete['wall_seconds'] <= limits.seconds, 'Preparation terminal counts/scope')
    for name,p in receipt['files'].items():
        need(_hash(root/name,end)==p,'Late preparation mutation')
    need(_acquisition(request['archive'],request['acquisition_receipt'],request['asset_id'],end)==binding,
         'Late acquisition evidence mutation')
    for p in (*request['source_proofs'].values(),request['adapter'],request['serde']):
        _read(p,8*1024**2,end)
    need(_hash(_proof(request['archive']),end)==request['archive'],'Late archive mutation')
    need(_hash(root/'RECEIPT.json',end)==receipt_proof,'Late preparation receipt mutation')
    membership()
    return freeze(dict(status='source_projection_verified',counts=complete['counts'],
                       generation_files=generation_files,receipt=receipt_proof))
