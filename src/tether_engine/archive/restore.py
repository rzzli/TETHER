"""Materialize externally pinned recovery objects without executing archived code."""
from __future__ import annotations
import hashlib
import json
import os
import re
from pathlib import Path
from .paths import ArchiveResolver, _no_links, _relative, logical_key, join, from_envelope
from tether_engine.serde import ContractError


def need(value, message):
    if not value:
        raise ContractError(message)


def anchored_json(path, expected):
    path = Path(path).absolute()
    _no_links(path)
    raw = path.read_bytes()
    need(isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected) and
         hashlib.sha256(raw).hexdigest() == expected, 'Manifest external anchor mismatch')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, 'Duplicate manifest key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def stable_copy(base, entry, destination):
    """Hash the actual copied stream and reject changing or linked source objects."""
    base = Path(base).absolute()
    source = base.joinpath(*_relative(entry['object']))
    _no_links(source)
    need(source.resolve().is_relative_to(base.resolve()), 'Object escapes manifest directory')
    destination = Path(destination)
    _no_links(destination.absolute())
    destination.parent.mkdir(parents=True, exist_ok=True)
    before = source.stat()
    digest = hashlib.sha256(); total = 0
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    with source.open('rb') as incoming, destination.open('xb') as outgoing:
        need(identity(before) == identity(os.fstat(incoming.fileno())), 'Object changed before copy')
        while chunk := incoming.read(1024 * 1024):
            total += len(chunk)
            need(total <= entry['bytes'], 'Object exceeds pinned size')
            digest.update(chunk); outgoing.write(chunk)
        outgoing.flush(); os.fsync(outgoing.fileno())
        need(identity(before) == identity(os.fstat(incoming.fileno())), 'Object changed during copy')
    _no_links(source)
    need(identity(before) == identity(source.stat()), 'Object replaced during copy')
    need(total == entry['bytes'] and digest.hexdigest() == entry['sha256'], 'Object hash/size mismatch')
    return total


def materialize(checkpoint, checkpoint_sha256, recovery, recovery_sha256,
                supplement, supplement_sha256, output):
    """Create fresh per-run trees from three externally anchored CAS inventories."""
    cp = anchored_json(checkpoint, checkpoint_sha256)
    hist = anchored_json(recovery, recovery_sha256)
    extra = anchored_json(supplement, supplement_sha256)
    need(cp.get('schema_version') == 1 and cp.get('kind') == 'recovery_checkpoint', 'Unknown checkpoint')
    need(hist.get('checkpoint_sha256') == checkpoint_sha256, 'Recovery checkpoint anchor differs')
    need(extra.get('prior_recovery_sha256') == recovery_sha256, 'Supplement recovery anchor differs')
    roots = [{'root_id':'project', 'logical_root':cp['repository_logical_root']},
             {'root_id':'raw', 'logical_root':cp['raw_logical_root']}]
    def location(path):
        key = logical_key(path)
        for root in roots:
            prefix = logical_key(root['logical_root'])
            if key[:len(prefix)] == prefix and len(key) > len(prefix):
                # Preserve spelling; lexical key is only used for identity comparisons.
                relative = path.replace('\\','/')[len(root['logical_root'].replace('\\','/').rstrip('/'))+1:]
                _relative(relative)
                return root['root_id'], relative
        raise ContractError('Checkpoint file outside declared roots: ' + str(path))
    recovered = {e['sha256']:e for e in extra['recovered']}
    output = Path(output).absolute(); _no_links(output)
    output.mkdir(parents=True, exist_ok=False)
    copied = {}; runs = []; physical = {}; total = 0
    try:
        (output/'raw').mkdir()
        for run in cp['runs']:
            rid = run['kind']
            need(re.fullmatch('[A-Za-z0-9_-]+',rid) and rid not in physical, 'Duplicate/unsafe run ID')
            project = output/'runs'/rid/'project'; project.mkdir(parents=True)
            bindings = dict(project=str(project),raw=str(output/'raw'))
            physical[rid] = bindings
            selected = {}
            for e in cp['entries']:
                if e.get('role') == 'repository' or e.get('run') == rid:
                    key = logical_key(e['logical_path'])
                    previous = selected.get(key)
                    # Historical_code explicitly supersedes the current repository version.
                    if previous and previous[0]['sha256'] != e['sha256']:
                        need(e.get('role') == 'historical_code', 'Conflicting checkpoint identity')
                    selected[key] = (e,Path(checkpoint).parent)
            original_pins = []
            for req in hist['requirements']:
                if req['run'] != rid:
                    continue
                obj = req if req.get('status') == 'recovered' else recovered.get(req['sha256'])
                need(obj is not None, 'Historical code object missing: ' + req['logical_path'])
                entry = dict(obj,logical_path=req['logical_path'])
                selected[logical_key(req['logical_path'])] = (entry,Path(recovery).parent if obj is req else Path(supplement).parent)
                original_pins.append({'logical_path':req['logical_path'],'sha256':req['sha256'],'origin':req['origin']})
            files = []
            for entry, base in selected.values():
                root_id, relative = location(entry['logical_path'])
                file = dict(logical_path=entry['logical_path'],root_id=root_id,relative_path=relative,
                            sha256=entry['sha256'],bytes=entry['bytes'])
                destination = Path(bindings[root_id]).joinpath(*_relative(relative))
                key = str(destination).casefold() if os.name == 'nt' else str(destination)
                if key in copied:
                    need(copied[key] == (entry['sha256'],entry['bytes']), 'Shared destination conflict')
                else:
                    total += stable_copy(base,entry,destination)
                    copied[key] = (entry['sha256'],entry['bytes'])
                files.append(file)
            resolver = ArchiveResolver([dict(root,physical_root=bindings[root['root_id']]) for root in roots],files)
            receipt = run.get('receipt_sha256')
            anchor_name = 'receipt.json' if receipt else 'journal.jsonl'
            anchor = hashlib.sha256(resolver.read_bytes(join(run['logical_root'],anchor_name))).hexdigest()
            need(not receipt or receipt == anchor,'Restored receipt anchor differs')
            pins = {logical_key(e['logical_path']) for e in original_pins}
            runs.append(dict(run_id=rid,kind=rid,logical_root=run['logical_root'],receipt_sha256=receipt,
                             journal_sha256=anchor if not receipt else None,files=files,
                             original_code_pins=original_pins,
                             supplemental_checkpoint_sources=[f['logical_path'] for f in files
                                if f['logical_path'].endswith('.py') and logical_key(f['logical_path']) not in pins]))
        envelope = dict(schema_version=1,resolver_version=1,roots=roots,runs=runs,
                        input_anchors=dict(checkpoint=checkpoint_sha256,recovery=recovery_sha256,supplement=supplement_sha256),
                        archived_code_executed=False)
        path = output/'envelope.json'
        raw = (json.dumps(envelope,indent=2,ensure_ascii=False)+'\n').encode()
        with path.open('xb') as stream: stream.write(raw)
        result = dict(envelope=str(path),envelope_sha256=hashlib.sha256(raw).hexdigest(),
                      approved_root_candidates=physical,copied_bytes=total,runs=len(runs))
        with (output/'materialization.json').open('x',encoding='utf-8') as stream: json.dump(result,stream,indent=2)
        return result
    except BaseException as exc:
        with (output/'failure.json').open('x',encoding='utf-8') as stream:
            json.dump(dict(status='materialization_failed',error_class=type(exc).__name__,message=str(exc)),stream)
        raise


def verify(envelope, envelope_sha256, run_id, approved_roots, *, receipt_sha256=None, journal_sha256=None):
    """Dispatch only trusted installed verification code, never archived modules."""
    doc = anchored_json(envelope,envelope_sha256)
    need(doc.get('schema_version') == 1 and doc.get('resolver_version') == 1,'Unknown envelope version')
    ids = [r['run_id'] for r in doc['runs']]
    need(len(set(ids)) == len(ids) and run_id in ids,'Unknown/duplicate run')
    run = doc['runs'][ids.index(run_id)]
    if run['kind'] == 'question_latest_failed':
        need(receipt_sha256 is None and run.get('receipt_sha256') is None,'Failed run cannot have receipt')
        need(journal_sha256 is not None and journal_sha256 == run['journal_sha256'],'External journal anchor mismatch')
        need(set(approved_roots) == {r['root_id'] for r in doc['roots']},'Approved root map differs')
        need(all(set(r) == {'root_id','logical_root'} for r in doc['roots']),'Archive cannot authorize roots')
        resolver = ArchiveResolver([dict(r,physical_root=approved_roots[r['root_id']]) for r in doc['roots']],run['files'])
        need(hashlib.sha256(resolver.read_bytes(join(run['logical_root'],'journal.jsonl'))).hexdigest() == journal_sha256,'Journal changed')
        from .interpretation import inspect_failed_interpretation_archive
        return inspect_failed_interpretation_archive(run['logical_root'],resolver)
    need(receipt_sha256 is not None and receipt_sha256 == run['receipt_sha256'],'External receipt anchor mismatch')
    resolver = from_envelope(envelope,envelope_sha256,approved_roots,run_id)
    if run['kind'] in {'bounded_interpretation_recorded','question_interpretation_recorded'}:
        from .interpretation import verify_interpretation_archive
        return verify_interpretation_archive(run['logical_root'],resolver,receipt_sha256)
    need(run['kind'] in {'legacy_v1','core_v2','local_selection_recorded','local_selection_native'},'Unsupported archive run kind')
    from .core import verify_core_archive
    project = next(r['logical_root'] for r in doc['roots'] if r['root_id'] == 'project')
    return verify_core_archive(run['logical_root'],resolver,receipt_sha256,code_root=join(project,'src/tether_engine'))
