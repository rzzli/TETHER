"""Restore a bounded, user-supplied AACT batch; preserve originals and stage evidence.

Uses copies of the audited January 2025 setup/audit recipes. No downloader, global
installation, service, scientific labels, or automatic retry of failed imports.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import zipfile


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    temporary.replace(path)


def safe_members(infos):
    names = [x.filename for x in infos]
    if len(names) != len(set(x.casefold() for x in names)):
        raise ValueError('Duplicate ZIP members')
    for name in names:
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in ('.', '..'):
            raise ValueError('Only flat named archive members are allowed')
    if names.count('postgres.dmp') != 1:
        raise ValueError('Exactly one postgres.dmp required')


def dump_date(toc, requested):
    match = re.search(r'^; Archive created at (\d{4}-\d{2}-\d{2}) ', toc, re.M)
    if not match:
        raise ValueError('Dump creation date unavailable')
    actual = match.group(1)
    # The supplied July 2023 ZIP metadata suggests a one-day release lag.
    # Preserve the actual date; never silently relabel it as the requested date.
    permitted = {requested}
    if requested == '2023-07-01':
        permitted.add('2023-07-02')
    if actual not in permitted:
        raise ValueError('Unexpected dump date: ' + actual)
    return actual


def technical_checks(root, date):
    audit = json.loads((root / 'technical-audit.json').read_text(encoding='utf-8'))
    toc = (root / 'dump-toc-pg17.txt').read_text()
    expected = set(re.findall(r'TABLE ctgov (\w+) ', toc))
    actual = {x['table'] for x in audit['tables'] if x['schema'] == 'ctgov'}
    if audit['status'] != 'completed' or actual != expected:
        raise ValueError('Incomplete table restoration/audit')
    if not all(x['convalidated'] for x in audit['constraints']):
        raise ValueError('Unvalidated constraints')
    if not all(x['indisvalid'] and x['indisready'] for x in audit['indexes']):
        raise ValueError('Invalid indexes')
    ids = audit['study_id_check']
    if ids['rows'] != ids['distinct_nct_ids'] or ids['null_nct_ids']:
        raise ValueError('Invalid study identifiers')
    if any(x['after_candidate_date'] for x in audit['study_date_ranges'] if x['column'] in
           ('study_first_posted_date', 'last_update_posted_date', 'results_first_posted_date')):
        raise ValueError('Posting dates after actual snapshot date')
    return {'snapshot_date': date, 'tables': len(actual), 'studies': ids['rows'],
            'total_rows': sum(x['rows'] for x in audit['tables']),
            'identifier_exceptions': [x for x in audit['tables'] if any(x.get(k, 0) for k in
                ('null_nct_ids', 'malformed_nct_ids', 'orphan_nct_ids'))],
            'constraints': len(audit['constraints']), 'indexes_including_toast': len(audit['indexes']),
            'scientific_validation': 'not_established'}


def execute(plan, out):
    out.mkdir(parents=True, exist_ok=False)
    write(out / 'plan.json', plan)
    shutil.copyfile(__file__, out / 'executed-code.py')
    previous = None
    def event(stage, **fields):
        nonlocal previous
        row = {'at_utc': datetime.now(timezone.utc).isoformat(), 'stage': stage,
               'previous_sha256': previous, **fields}
        digest = hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with (out / 'journal.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps({**row, 'sha256': digest}) + '\n'); f.flush(); os.fsync(f.fileno())
        previous = digest
        print(json.dumps({'stage': stage, **fields}), flush=True)

    pg_bin = Path(plan['pg_bin'])
    template = Path(plan['template_restore'])
    result = {'status': 'running', 'snapshots': [], 'provider_spending_usd': 0}
    start = time.monotonic()
    write(out / 'result.json', result)
    try:
        for index, item in enumerate(plan['snapshots']):
            root = out / item['requested_date']; root.mkdir()
            archive = Path(item['archive'])
            port = str(plan['first_port'] + index)
            row = {'requested_date': item['requested_date'], 'root': str(root), 'status': 'running'}
            result['snapshots'].append(row); write(out / 'result.json', result)
            event('archive_check', requested_date=item['requested_date'], status='started')
            initial_stat = archive.stat()
            inspection = {'archive': str(archive), 'archive_bytes': initial_stat.st_size,
                          'archive_sha256': sha(archive), 'members': [], 'status': 'running'}
            extracted = root / 'extracted'; extracted.mkdir()
            with zipfile.ZipFile(archive) as z:
                safe_members(z.infolist())
                if sum(i.file_size for i in z.infolist()) > plan['max_expanded_archive_bytes']:
                    raise ValueError('Archive expansion exceeds configured bound')
                for info in z.infolist():
                    dest = extracted / info.filename
                    h = hashlib.sha256(); count = 0
                    with z.open(info) as source, dest.open('xb') as target:
                        for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
                            target.write(block); h.update(block); count += len(block)
                    if count != info.file_size:
                        raise ValueError('Archive member size differs')
                    inspection['members'].append({'name': info.filename, 'bytes': count,
                        'sha256': h.hexdigest(), 'zip_timestamp': list(info.date_time),
                        'crc32': info.CRC, 'crc_check': 'passed_full_read'})
            final_stat = archive.stat()
            if (initial_stat.st_size, initial_stat.st_mtime_ns) != (final_stat.st_size, final_stat.st_mtime_ns):
                raise ValueError('Archive changed while reading')
            inspection['status'] = 'archive_integrity_passed'
            write(root / 'archive-inspection.json', inspection)
            event('archive_check', requested_date=item['requested_date'], status='completed')

            def run(name, command, env=None):
                event(name, requested_date=item['requested_date'], status='started')
                with (root / (name + '.stdout.log')).open('xb') as stdout, (root / (name + '.stderr.log')).open('xb') as stderr:
                    proc = subprocess.run(command, stdout=stdout, stderr=stderr, env=env,
                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                event(name, requested_date=item['requested_date'], status='completed' if proc.returncode == 0 else 'failed',
                      returncode=proc.returncode)
                if proc.returncode:
                    raise RuntimeError(name + ' failed; retained logs at ' + str(root))

            run('toc', [str(pg_bin / 'pg_restore.exe'), '-l', str(extracted / 'postgres.dmp')])
            shutil.copyfile(root / 'toc.stdout.log', root / 'dump-toc-pg17.txt')
            actual_date = dump_date((root / 'dump-toc-pg17.txt').read_text(), item['requested_date'])
            row['actual_snapshot_date'] = actual_date
            row['date_basis'] = 'dump_creation_date_timezone_unknown_not_exact_public_availability'
            setup = (template / 'setup.py').read_text()
            if setup.count("PORT='55433'") != 1 or setup.count('port = 55433') != 1:
                raise ValueError('Unexpected setup template')
            setup = setup.replace("PORT='55433'", 'PORT=' + repr(port)).replace('port = 55433', 'port = ' + port)
            audit = (template / 'audit.py').read_text()
            if audit.count("DATE '2025-01-01'") != 1:
                raise ValueError('Unexpected audit template')
            audit = audit.replace("DATE '2025-01-01'", "DATE '" + actual_date + "'")
            (root / 'setup.py').write_text(setup, encoding='utf-8')
            (root / 'audit.py').write_text(audit, encoding='utf-8')
            write(root / 'recipe-provenance.json', {'template_root': str(template),
                'setup_template_sha256': sha(template / 'setup.py'), 'audit_template_sha256': sha(template / 'audit.py'),
                'changes': {'local_port': port, 'audit_candidate_date': actual_date}, 'pg_bin': str(pg_bin)})
            try:
                run('setup', [sys.executable, str(root / 'setup.py')])
                env = os.environ.copy()
                env.update(PGHOST='127.0.0.1', PGPORT=port, PGUSER='aact_restore_admin', PGDATABASE='aact_snapshot',
                           PGPASSWORD=(root / '.local-postgres-secrets/password.txt').read_text())
                restore_start = time.monotonic()
                run('import', [str(pg_bin / 'pg_restore.exe'), '--exit-on-error', '--verbose', '--no-owner',
                              '--no-acl', '--jobs=4', '--dbname=aact_snapshot', str(extracted / 'postgres.dmp')], env)
                row['import_elapsed_seconds'] = time.monotonic() - restore_start
                run('analyze', [str(pg_bin / 'psql.exe'), '-X', '-v', 'ON_ERROR_STOP=1', '-c', 'ANALYZE;'], env)
                run('audit', [sys.executable, str(root / 'audit.py')])
                row['technical_checks'] = technical_checks(root, actual_date)
                query = Path(plan['frozen_cohort_query'])
                if sha(query) != plan['frozen_cohort_query_sha256']:
                    raise ValueError('Frozen extraction query changed')
                shutil.copyfile(query, root / 'cohort-query.sql')
                env['PGOPTIONS'] = '-c default_transaction_read_only=on'
                run('cohort', [str(pg_bin / 'psql.exe'), '-XAtq', '-v', 'ON_ERROR_STOP=1', '-f', str(root / 'cohort-query.sql')], env)
                shutil.copyfile(root / 'cohort.stdout.log', root / 'cohort-records.json')
                records = json.loads((root / 'cohort-records.json').read_text(encoding='utf-8'))
                if len({r['nct_id'] for r in records}) != len(records):
                    raise ValueError('Duplicate extracted trial')
                if set(r['nct_id'] for r in records) != set(plan['frozen_nct_ids']):
                    raise ValueError('Frozen trial set incomplete or differs')
                row['cohort_records'] = len(records); row['status'] = 'completed'
            except BaseException as exc:
                row.update(status='failed', error=repr(exc))
                raise
            finally:
                if (root / 'pgdata/postmaster.pid').exists():
                    run('stop', [str(pg_bin / 'pg_ctl.exe'), '-D', str(root / 'pgdata'), '-m', 'fast', '-w', 'stop'])
                row['server_stopped'] = not (root / 'pgdata/postmaster.pid').exists()
                write(root / 'restore-result.json', row)
            files = []
            for path in sorted(root.rglob('*')):
                if not path.is_file() or any(x in path.relative_to(root).parts for x in
                    ('pgdata', 'extracted', '.local-postgres-secrets', '__pycache__')):
                    continue
                files.append({'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': sha(path)})
            write(root / 'evidence-manifest.json', {'files': files, 'originals_bound_by': 'archive-inspection.json'})
            row['evidence_manifest_sha256'] = sha(root / 'evidence-manifest.json')
            row['retained_bytes'] = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
            write(out / 'result.json', result)
            event('snapshot_completed', requested_date=item['requested_date'], actual_snapshot_date=actual_date,
                  studies=row['technical_checks']['studies'], evidence_manifest_sha256=row['evidence_manifest_sha256'])
        result['status'] = 'completed'
    except BaseException as exc:
        result.update(status='failed', error=repr(exc))
        if result['snapshots'] and result['snapshots'][-1]['status'] == 'running':
            result['snapshots'][-1].update(status='failed', error=repr(exc))
        event('batch_failed', error=repr(exc))
        raise
    finally:
        result['elapsed_seconds'] = time.monotonic() - start
        result['peak_memory_bytes'] = None
        result['peak_memory_reason'] = 'Database subprocess peak not instrumented; no inferred estimate'
        write(out / 'result.json', result)
        event('batch_terminal', status=result['status'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    execute(json.loads(args.plan.read_text()), args.output)
