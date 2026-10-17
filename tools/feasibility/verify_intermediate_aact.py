"""Read-only verification of completed intermediate restores and their local seals.

Local hashes establish consistency, not publisher authenticity, first-public
availability or scientific validity. Never starts a database or repeats import.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from tools.feasibility.restore_intermediate_aact import sha, technical_checks, dump_date


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify_seal(manifest, expected):
    if sha(manifest) != expected:
        raise ValueError('Evidence manifest anchor changed')
    paths = set()
    for entry in load(manifest)['files']:
        path = (manifest.parent / entry['path']).resolve()
        if not path.is_relative_to(manifest.parent.resolve()) or path in paths:
            raise ValueError('Unsafe or duplicate evidence path')
        paths.add(path)
        if path.stat().st_size != entry['bytes'] or sha(path) != entry['sha256']:
            raise ValueError('Sealed evidence changed: ' + entry['path'])
    if not paths:
        raise ValueError('Empty evidence seal')
    return paths


def verify_journal(path):
    previous = None
    events = []
    for line in path.read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        digest = row.pop('sha256')
        if row['previous_sha256'] != previous or hashlib.sha256(
                json.dumps(row, sort_keys=True, separators=(',', ':')).encode()).hexdigest() != digest:
            raise ValueError('Broken restore journal chain')
        previous = digest
        events.append(row)
    if not events or events[-1]['stage'] != 'batch_terminal' or events[-1]['status'] != 'completed':
        raise ValueError('Restore batch is not complete')
    if any(e.get('status') == 'failed' or e['stage'] == 'batch_failed' for e in events):
        raise ValueError('Restore journal contains failure')
    return events


def verify(batch, rehash_originals=False):
    result, plan = load(batch / 'result.json'), load(batch / 'plan.json')
    if result['status'] != 'completed' or len(result['snapshots']) != len(plan['snapshots']):
        raise ValueError('Incomplete restore batch')
    events = verify_journal(batch / 'journal.jsonl')
    reports = []
    for item, row in zip(plan['snapshots'], result['snapshots']):
        root = Path(row['root'])
        if root.resolve() != (batch / item['requested_date']).resolve() or row['requested_date'] != item['requested_date']:
            raise ValueError('Unexpected snapshot identity/path')
        if row['status'] != 'completed' or not row['server_stopped'] or (root / 'pgdata/postmaster.pid').exists():
            raise ValueError('Snapshot incomplete or server still active')
        paths = verify_seal(root / 'evidence-manifest.json', row['evidence_manifest_sha256'])
        for name in ('archive-inspection.json', 'technical-audit.json', 'dump-toc-pg17.txt',
                     'cohort-query.sql', 'cohort-records.json', 'restore-result.json'):
            if (root / name).resolve() not in paths:
                raise ValueError('Required proof omitted: ' + name)
        actual = dump_date((root / 'dump-toc-pg17.txt').read_text(), item['requested_date'])
        if actual != row['actual_snapshot_date'] or technical_checks(root, actual) != row['technical_checks']:
            raise ValueError('Technical summary differs from audit')
        saved = load(root / 'restore-result.json')
        if any(saved.get(k) != v for k, v in row.items() if k not in ('evidence_manifest_sha256', 'retained_bytes')):
            raise ValueError('Snapshot result differs from batch')
        inspection = load(root / 'archive-inspection.json')
        if inspection['status'] != 'archive_integrity_passed' or Path(inspection['archive']).resolve() != Path(item['archive']).resolve():
            raise ValueError('Archive inspection identity/status differs')
        members = inspection['members']
        if not members or any(m['crc_check'] != 'passed_full_read' for m in members):
            raise ValueError('Incomplete archive CRC evidence')
        for path, size, digest in [(Path(inspection['archive']), inspection['archive_bytes'], inspection['archive_sha256'])] + [
                (root / 'extracted' / m['name'], m['bytes'], m['sha256']) for m in members]:
            if path.stat().st_size != size or (rehash_originals and sha(path) != digest):
                raise ValueError('Original or extracted member changed')
        records = load(root / 'cohort-records.json')
        if len(records) != len(plan['frozen_nct_ids']) or {r['nct_id'] for r in records} != set(plan['frozen_nct_ids']):
            raise ValueError('Frozen trial set differs')
        if sha(root / 'cohort-query.sql') != plan['frozen_cohort_query_sha256']:
            raise ValueError('Frozen extraction query changed')
        for stage in ('archive_check', 'toc', 'setup', 'import', 'analyze', 'audit', 'cohort', 'stop'):
            matching = [e for e in events if e.get('requested_date') == item['requested_date'] and
                        e['stage'] == stage and e.get('status') == 'completed']
            if len(matching) != 1:
                raise ValueError('Missing or duplicate completed stage: ' + stage)
        completion = [e for e in events if e['stage'] == 'snapshot_completed' and e['requested_date'] == item['requested_date']]
        if len(completion) != 1 or completion[0]['evidence_manifest_sha256'] != row['evidence_manifest_sha256'] or completion[0]['actual_snapshot_date'] != actual:
            raise ValueError('Journal snapshot proof differs')
        reports.append({'requested_date': item['requested_date'], 'actual_snapshot_date': actual,
                        'files_verified': len(paths), 'cohort_records': len(records), **row['technical_checks']})
    return {'status': 'retained_evidence_checks_passed', 'snapshots': reports,
            'journal_events_verified': len(events), 'original_bytes_rehashed': rehash_originals,
            'original_check_scope': 'size plus full SHA-256' if rehash_originals else 'size now; full SHA-256 and CRC retained from initial inspection',
            'result_sha256': sha(batch / 'result.json'), 'journal_sha256': sha(batch / 'journal.jsonl'),
            'plan_sha256': sha(batch / 'plan.json'), 'executed_code_sha256': sha(batch / 'executed-code.py'),
            'verifier_sha256': sha(Path(__file__)), 'scientific_validation': 'not_established',
            'publisher_authenticity_and_first_public_availability': 'not_established'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rehash-originals', action='store_true')
    args = parser.parse_args()
    with args.output.open('x', encoding='utf-8') as output:
        try:
            report = verify(args.batch, args.rehash_originals)
        except Exception as exc:
            json.dump({'status': 'failed', 'error': repr(exc)}, output, indent=2)
            raise
        json.dump(report, output, indent=2)
        output.write('\n')
    print(json.dumps(report))
