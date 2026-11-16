"""Fresh bounded byte verification of a pinned metadata screen; no role grant.

This checks retained hashes, not publisher authenticity, schemas or scientific
semantics. Original files and evaluation-only roles are never modified.
"""
from collections import Counter
import argparse
import hashlib
from pathlib import Path
import re
import time

from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal
from tether_engine.serde import ContractError, canonical, parse_json
from tether_engine.source_access import SourceAccess, local_path, selected_root


def qualify(manifest_path, expected_sha256, output, *, source_roots,
            max_bytes=512*1024**2, seconds=600):
    if (type(max_bytes) is not int or max_bytes <= 0 or
            type(seconds) not in (int, float) or not 0 < seconds <= 3600):
        raise ContractError('Invalid qualification limits')
    if not isinstance(expected_sha256, str) or not re.fullmatch('[0-9a-f]{64}', expected_sha256):
        raise ContractError('Exact metadata-screen SHA-256 required')
    started = time.monotonic()
    deadline = started + seconds
    manifest_path, output = local_path(manifest_path), local_path(output)
    access = SourceAccess(tuple(selected_root(root) for root in source_roots))
    prepared = access.prepare([manifest_path], deadline=deadline)
    raw = prepared.read(manifest_path, 16*1024**2)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ContractError('Metadata screen hash differs from caller anchor')
    manifest = parse_json(raw)
    files, metadata = manifest.get('files'), manifest.get('metadata_pins')
    if not isinstance(files, list) or not files or not isinstance(metadata, list) or len(files)+len(metadata) > 10000:
        raise ContractError('Bounded nonempty source inventory required')
    items, identities = [], {}
    for kind, entries in (('original', files), ('metadata', metadata)):
        local_seen = set()
        for row in entries:
            path = local_path(row['path'])
            if path in local_seen:
                raise ContractError('Duplicate input path within inventory')
            local_seen.add(path)
            digest, size = row.get('sha256'), row.get('bytes')
            if (not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)
                    or type(size) is not int or size < 0):
                raise ContractError('Invalid input fingerprint declaration')
            if path.is_relative_to(output) or output == path:
                raise ContractError('Output overlaps source inventory')
            if path in identities:
                raise ContractError('Duplicate input path across inventory roles')
            identities[path] = (digest, size)
            items.append((kind, path, digest, size))
    if sum(size for _, _, _, size in items) > max_bytes:
        raise ContractError('Qualification exceeds declared byte cap')
    # Preflight every declared path before creating output or reading originals.
    prepared = access.prepare(identities, deadline=deadline)
    if any(prepared.identities[path][2] != size for _, path, _, size in items):
        raise ContractError('Input size differs before bounded hashing')
    from tether_engine.study.proofs import _no_links
    _no_links(output.parent)
    if output.exists() or output.is_symlink():
        _no_links(output)
    journal = RunJournal(output, kind='build')
    done, measured = Counter(), 0
    failure = None
    try:
        journal.append('byte_qualification_started', metadata_screen_sha256=expected_sha256,
                       scheduled_originals=len(files), scheduled_metadata=len(metadata), max_bytes=max_bytes)
        for kind, path, digest, size in items:
            observed_digest, observed_size = prepared.digest_size(path)
            measured += observed_size
            if (observed_digest, observed_size) != (digest, size):
                raise ContractError('Input fingerprint differs from pinned metadata screen')
            done[kind] += 1
            journal.append('source_bytes_verified', kind=kind, path=str(path), sha256=digest, bytes=size)
        report = {'schema_version': 1, 'status': 'byte_integrity_verified',
                  'metadata_screen_sha256': expected_sha256, 'files_verified': done['original'],
                  'metadata_verified': done['metadata'], 'bytes_hashed': measured,
                  'declared_receipt_roles': dict(Counter(str(row.get('receipt_role')) for row in files)),
                  'actor_input_qualification': 'not_established', 'historical_eligibility': 'not_established',
                  'scientific_validation': 'not_established', 'row_values_read': 0,
                  'elapsed_seconds': time.monotonic()-started,
                  'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        payload = canonical(report)+b'\n'
        publish_bytes(output/'report.json', payload)
        report_hash = hashlib.sha256(payload).hexdigest()
        event = journal.append('build_completed', report_sha256=report_hash)
        journal.seal(canonical({'schema_version': 1, 'status': report['status'],
                     'report_sha256': report_hash, 'journal_head': event['sha256']}),
                     deadline=deadline, name='terminal-seal.json')
        return report
    except BaseException as error:
        failure = error
        if not journal.sealed:
            try:
                journal.append('build_failed', error_class=type(error).__name__,
                               files_verified=done['original'], metadata_verified=done['metadata'],
                               bytes_hashed=measured)
            except BaseException as cleanup:
                error.add_note('Failure journal append failed: '+type(cleanup).__name__)
        raise
    finally:
        try:
            journal.close()
        except BaseException as cleanup:
            if failure is None:
                raise
            failure.add_note('Journal close failed: '+type(cleanup).__name__)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, action='append', required=True)
    args = parser.parse_args()
    report = qualify(args.manifest.absolute(), args.sha256, args.output.absolute(), source_roots=args.source_root)
    print(canonical(report).decode())


if __name__ == '__main__':
    main()
