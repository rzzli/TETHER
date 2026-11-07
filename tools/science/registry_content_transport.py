"""Local B0 read-only transport for an already source-bound, validated job.

No CLI or cohort authorization lives here. The caller must validate source,
selection, schema and code ancestry before calling this lifecycle. Outcome bytes
are copied and compared, never parsed or classified by this module.
"""
from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import time

from tether_engine.serde import ContractError, read_json, sha256_file, write_json
from tools.science.outcome_extract import check_pins, source_lease

STARTUP_SETTLE_SECONDS = 50
METADATA_SQL = ("SELECT json_build_object('database',current_database(),"
                "'studies',(SELECT count(*) FROM ctgov.studies),"
                "'directory',current_setting('data_directory'),"
                "'port',current_setting('port'),"
                "'read_only',current_setting('transaction_read_only'));")


def startup_command(pg, root, folder, port):
    """Canonical hidden startup arguments, shared with receipt verification."""
    ownership_file = folder / 'owned-postmaster.pid'
    if any(c.isspace() or c in "'\"" for c in ownership_file.as_posix()):
        raise ContractError('Ownership PID path needs a simple local path')
    ctl = str(pg / 'pg_ctl.exe').replace("'", "''")
    options = (f'-p {port} -c listen_addresses=127.0.0.1 '
               '-c default_transaction_read_only=on '
               f'-c external_pid_file={ownership_file.as_posix()}')
    args = ['-D', str(root / 'pgdata'), '-l', str(folder / 'server.log'),
            '-o', options, '-w', '-t', '45', 'start']
    arglist = ','.join("'\"" + arg.replace("'", "''") + "\"'" for arg in args)
    return ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
            f"$b0Process=Start-Process -FilePath '{ctl}' -ArgumentList @({arglist}) "
            '-WindowStyle Hidden -PassThru; $b0Process.WaitForExit(); exit $b0Process.ExitCode']


def _pin(path):
    return {'path': str(path.resolve()), 'sha256': sha256_file(path),
            'bytes': path.stat().st_size}


def _port_open(port):
    with socket.socket() as probe:
        probe.settimeout(1)
        return probe.connect_ex(('127.0.0.1', port)) == 0


def _run_bounded(args, *, env, stdout, stderr, timeout, cap):
    """Monitor retained output; a polling interval can permit a small overshoot."""
    proc = subprocess.Popen(args, env=env, stdout=stdout, stderr=stderr,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    deadline = time.monotonic() + timeout
    try:
        while True:
            code = proc.poll()
            if Path(stdout.name).stat().st_size > cap:
                raise ContractError('B0 result exceeds output byte cap; retained partial read')
            if Path(stderr.name).stat().st_size > 1024 * 1024:
                raise ContractError('B0 command exceeds diagnostic byte cap; retained partial logs')
            if code is not None:
                return subprocess.CompletedProcess(args, code)
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(args, timeout)
            time.sleep(0.05)
    except BaseException:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=10)
        raise


def _owned_pid(root, ownership_file, port):
    """Never infer ownership from a port or a cluster PID file alone."""
    pid_file = root / 'pgdata/postmaster.pid'
    if not pid_file.exists():
        return None
    lines = pid_file.read_text(encoding='utf-8').splitlines()
    if (len(lines) < 4 or not lines[0].isdigit() or int(lines[0]) <= 0 or
            lines[3] != str(port) or not ownership_file.is_file() or
            ownership_file.read_text(encoding='utf-8').strip() != lines[0] or
            Path(lines[1]).resolve() != root / 'pgdata'):
        raise ContractError('Server startup ownership unproven; refusing shutdown')
    return {'pid': lines[0], 'started_epoch': lines[2]}


def run_source(job, pg_bin, folder, journal):
    """Return two identical raw result pins plus verified connection metadata.

    ``job`` contains snapshot_date, restore_root, expected_studies, port, pins and
    one query {path, sha256, bytes, request}. It must already be validated by the
    source-inclusive caller. This function does not confer execution permission.
    Fresh output and the shared legacy source lease prevent concurrent reuse.
    """
    folder = Path(folder).resolve()
    root = Path(job['restore_root']).resolve()
    pg = Path(pg_bin).resolve()
    port = job['port']
    query = job['query']
    cap = query['request'].get('max_output_bytes')
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ContractError('Invalid B0 local port')
    if type(cap) is not int or not 1 <= cap <= 128 * 1024 * 1024:
        raise ContractError('Invalid B0 output byte cap')
    folder.mkdir(parents=False, exist_ok=False)
    stage = job['snapshot_date']
    attempted = False
    stopped = False
    port_closed = False
    primary_error = None
    cleanup_error = None
    startup_uncertain = False
    result = None
    ownership_file = folder / 'owned-postmaster.pid'

    def check_query():
        check_pins([query])
        sql = Path(query['path']).read_text(encoding='utf-8')
        if (sql != query['request'].get('sql') or
                not sql.startswith('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;') or
                not sql.rstrip().endswith('ROLLBACK;')):
            raise ContractError('B0 SQL differs from the validated read-only query')

    def command(name, args, *, env=None, allowed=(0,), timeout=90, output_cap=None):
        # No environment or password appears in durable command records.
        journal.append('build_progress', stage=stage, command=name, status='started',
                       arguments=args, timeout_seconds=timeout)
        stdout_path = folder / (name + '.stdout.log')
        stderr_path = folder / (name + '.stderr.log')
        try:
            with stdout_path.open('xb') as stdout, stderr_path.open('xb') as stderr:
                if output_cap is not None:
                    proc = _run_bounded(args, env=env, stdout=stdout, stderr=stderr,
                                        timeout=timeout, cap=output_cap)
                else:
                    proc = subprocess.run(args, env=env, stdout=stdout, stderr=stderr,
                                          timeout=timeout,
                                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except BaseException as exc:
            journal.append('build_progress', stage=stage, command=name, status='interrupted',
                           error_class=type(exc).__name__)
            raise
        journal.append('build_progress', stage=stage, command=name, status='finished',
                       returncode=proc.returncode, stdout_bytes=stdout_path.stat().st_size,
                       stderr_bytes=stderr_path.stat().st_size)
        if output_cap is not None and stdout_path.stat().st_size > output_cap:
            raise ContractError('B0 result exceeds output byte cap; retained oversized read')
        if proc.returncode not in allowed:
            raise RuntimeError(name + ' failed; inspect retained logs')
        return proc.returncode

    try:
        # Shared with legacy extraction: a B0 run cannot race an older runner.
        with source_lease(root):
            try:
                check_pins(job['pins'])
                check_query()
                status = command('status-before', [str(pg / 'pg_ctl.exe'), '-D',
                                                   str(root / 'pgdata'), 'status'], allowed=(0, 3))
                if status == 0:
                    raise ContractError('Existing server running; ownership refused')
                if _port_open(port):
                    raise ContractError('Requested port already occupied')
                start_args = startup_command(pg, root, folder, port)
                attempted = True
                try:
                    command('start', start_args)
                except (subprocess.TimeoutExpired, KeyboardInterrupt):
                    startup_uncertain = True
                    raise
                if _owned_pid(root, ownership_file, port) is None:
                    raise ContractError('Started server lacks external PID ownership proof')
                env = os.environ.copy()
                env.update(PGHOST='127.0.0.1', PGPORT=str(port), PGUSER='aact_restore_admin',
                           PGDATABASE='aact_snapshot', PGCLIENTENCODING='UTF8',
                           PGPASSWORD=(root / '.local-postgres-secrets/password.txt').read_text(encoding='utf-8'),
                           PGOPTIONS='-c default_transaction_read_only=on -c statement_timeout=300000 -c jit=off')
                command('metadata', [str(pg / 'psql.exe'), '-XAtq', '-v', 'ON_ERROR_STOP=1',
                                     '-c', METADATA_SQL], env=env)
                meta = read_json(folder / 'metadata.stdout.log')
                if (meta.get('database') != 'aact_snapshot' or type(meta.get('studies')) is not int or
                        meta['studies'] != job['expected_studies'] or
                        not isinstance(meta.get('directory'), str) or
                        Path(meta['directory']).resolve() != root / 'pgdata' or
                        meta.get('port') != str(port) or meta.get('read_only') != 'on'):
                    raise ContractError('Wrong source database identity/read-only state')
                for name in ('first', 'repeat'):
                    check_query()
                    try:
                        command(name, [str(pg / 'psql.exe'), '-XAtq', '-v', 'ON_ERROR_STOP=1',
                                       '-f', query['path']], env=env, timeout=330, output_cap=cap)
                    finally:
                        check_query()
                first, repeat = folder / 'first.stdout.log', folder / 'repeat.stdout.log'
                first_pin, repeat_pin = _pin(first), _pin(repeat)
                if (first_pin['bytes'], first_pin['sha256']) != (repeat_pin['bytes'], repeat_pin['sha256']):
                    raise ContractError('Repeat B0 source reads differ')
                check_pins(job['pins'])
                check_query()
                result = {'snapshot_date': stage, 'first': first_pin, 'repeat': repeat_pin,
                          'repeat_identical': True, 'metadata': meta,
                          'metadata_file': _pin(folder / 'metadata.stdout.log')}
            except BaseException as exc:
                primary_error = exc
                journal.append('build_progress', stage=stage, status='source_failed',
                               error_class=type(exc).__name__)
                raise
            finally:
                try:
                    if attempted:
                        # A timed-out/interrupted shell may leave pg_ctl finishing
                        # its one startup attempt. Retain the lease while it settles.
                        if startup_uncertain:
                            deadline = time.monotonic() + STARTUP_SETTLE_SECONDS
                            while time.monotonic() < deadline:
                                if ((root / 'pgdata/postmaster.pid').exists() and ownership_file.is_file()):
                                    break
                                time.sleep(0.1)
                        owner = _owned_pid(root, ownership_file, port)
                        if owner is not None:
                            journal.append('build_progress', stage=stage, status='owned_server_cleanup',
                                           server_pid=owner['pid'], server_started_epoch=owner['started_epoch'])
                            command('stop', [str(pg / 'pg_ctl.exe'), '-D', str(root / 'pgdata'),
                                             '-m', 'fast', '-w', '-t', '45', 'stop'])
                        stopped = command('status-after', [str(pg / 'pg_ctl.exe'), '-D',
                                                          str(root / 'pgdata'), 'status'], allowed=(3,)) == 3
                        port_closed = not _port_open(port)
                        if not port_closed:
                            raise ContractError('Owned local port remains open')
                except BaseException as exc:
                    cleanup_error = exc
                    journal.append('build_cleanup_failed', stage=stage, error_class=type(exc).__name__)
                    if primary_error is None:
                        raise
                finally:
                    write_json(folder / 'lifecycle.json', {
                        'startup_attempted': attempted, 'server_stopped': stopped,
                        'port_closed': port_closed, 'port': port, 'automatic_retry': False,
                        'primary_error_class': type(primary_error).__name__ if primary_error else None,
                        'cleanup_error_class': type(cleanup_error).__name__ if cleanup_error else None})
    except BaseException as exc:
        # Covers lease acquisition failures too; never serializes exception text,
        # command environment or credentials into a failure record.
        write_json(folder / 'failure.json', {'error_class': type(exc).__name__, 'automatic_retry': False})
        raise
    journal.append('build_progress', stage=stage, status='source_reads_complete',
                   server_stopped=stopped, port_closed=port_closed)
    result['lifecycle'] = _pin(folder / 'lifecycle.json')
    return result
