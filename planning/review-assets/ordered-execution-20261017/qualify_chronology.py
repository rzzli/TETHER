"""Read-only archive/model chronology qualification, without clinical outcome queries.

Copies only the PostgreSQL dump to a new E: cache directory for pg_restore --list.
Does not restore/start a database, download weights, or change transport receipts.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from asof.serde import sha256_file
from tools.feasibility.restore_intermediate_aact import safe_members, dump_date


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    root = Path('E:/projects_data/drug_target_agents_data/cache') / ('aact-20260101-qualification-' + stamp)
    root.mkdir(parents=True, exist_ok=False)
    archive = Path('E:/projects_data/drug_target_agents_data/raw/aact_snapshots/jan2026zip/5tzn1rk7zy0q2xbdspg5iicwh9tt.zip')
    result = {'status': 'running', 'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'archive': str(archive), 'root': str(root), 'provider_spend_usd': 0,
              'clinical_rows_queried': 0, 'database_restored': False}
    def save():
        (root / 'qualification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    save()
    try:
        before = archive.stat()
        result['archive_sha256'] = sha256_file(archive)
        if result['archive_sha256'] != '7fb923dacecae1dfec864c3e21fbed669add8a64b6bd1664ce973c24a514035c':
            raise ValueError('January 2026 archive differs from retained original hash')
        result['archive_bytes'] = before.st_size
        result['members'] = []
        with zipfile.ZipFile(archive) as z:
            safe_members(z.infolist())
            if sum(i.file_size for i in z.infolist()) > 3_000_000_000:
                raise ValueError('Unexpected archive expansion')
            for item in z.infolist():
                digest = hashlib.sha256(); count = 0
                target = (root / 'postgres.dmp').open('xb') if item.filename == 'postgres.dmp' else None
                try:
                    with z.open(item) as source:
                        for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
                            digest.update(block); count += len(block)
                            if target:
                                target.write(block)
                finally:
                    if target:
                        target.close()
                if count != item.file_size:
                    raise ValueError('Member size mismatch')
                result['members'].append({'name': item.filename, 'bytes': count,
                    'sha256': digest.hexdigest(), 'crc32': item.CRC,
                    'crc_check': 'passed_full_read', 'zip_timestamp': list(item.date_time)})
        after = archive.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('Archive changed during qualification')
        command = ['E:/projects_data/drug_target_agents_data/cache/postgresql-17.11-portable/pgsql/bin/pg_restore.exe',
                   '--list', str(root / 'postgres.dmp')]
        completed = subprocess.run(command, capture_output=True, check=True,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        (root / 'dump-toc.txt').write_bytes(completed.stdout)
        result['snapshot_date'] = dump_date(completed.stdout.decode('utf-8'), '2026-01-01')
        result.update(status='archive_crc_hash_and_toc_passed', exact_first_public_availability=None,
            exact_first_public_availability_reason='User-supplied versioned archive; dump and member times have unspecified timezone',
            limitations=['schema.png is empty', 'HTML ancillary definitions are not qualified scientific inputs',
                         'Database has not been restored or scientifically validated'])
    except BaseException as exc:
        result.update(status='failed', error=repr(exc))
        raise
    finally:
        result['finished_at_utc'] = datetime.now(timezone.utc).isoformat(); save()
        pointer = Path('data/derived/active-chronology-qualification.json')
        pointer.write_text(json.dumps({'path': str(root / 'qualification.json'),
            'sha256': sha256_file(root / 'qualification.json')}, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
