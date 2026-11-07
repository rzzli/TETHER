"""Own a pinned loopback llama-server and run the ten exposed T6 development cases.

No provider calls, historical labels, independent scientific review or trained score.
New output only; server shutdown is attempted in finally, never implicit resumption.
"""
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

from tether_engine.serde import fingerprint, sha256_file


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wire-format', default='canonical',
        choices=('canonical', 'tether-shared-scientific-fields-v1'))
    parser.add_argument('--case-id', action='append', default=[])
    parser.add_argument('--protocol', type=Path, default=Path('planning/protocols/evaluation-v0.1.json'))
    args = parser.parse_args()
    pointer = json.loads(Path('data/derived/active-local-model-acquisition.json').read_text(encoding='utf-8'))
    receipt_path = Path(pointer['path'])
    if sha256_file(receipt_path) != pointer['sha256']:
        raise ValueError('Changed model acquisition receipt')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if receipt['status'] != 'downloaded_hash_verified_not_inference_validated':
        raise ValueError('Model acquisition is incomplete')
    model_root = Path(receipt['root'])
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    prefix = 'local-model-pilot-' if args.wire_format == 'canonical' else 'local-wire-pilot-'
    out = Path('runs') / (prefix + stamp); out.mkdir(parents=True, exist_ok=False)
    (out / 'executed-launcher.py').write_bytes(Path(__file__).read_bytes())
    write(Path('data/derived/active-local-model-pilot.json'), {'path': str(out)})
    result = {'status': 'running', 'root': str(out), 'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'cases': [], 'provider_spend_usd': 0, 'scientific_validation': 'not_established',
        'independent_human_reviews': 0, 'weights_receipt': str(receipt_path), 'weights_receipt_sha256': pointer['sha256'],
        'wire_format': args.wire_format, 'protocol': str(args.protocol), 'protocol_sha256': sha256_file(args.protocol)}
    previous = None
    def event(stage, **fields):
        nonlocal previous
        e = {'at_utc': datetime.now(timezone.utc).isoformat(), 'stage': stage, 'previous_sha256': previous, **fields}
        e['sha256'] = fingerprint(e); previous = e['sha256']
        with (out / 'pilot-journal.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(e) + '\n'); stream.flush(); os.fsync(stream.fileno())
        print(json.dumps({'stage': stage, **fields}), flush=True); write(out / 'pilot-report.json', result)
    process = None; started = time.monotonic()
    try:
        protocol = json.loads(args.protocol.read_text(encoding='utf-8'))
        if protocol['development']['selection_limits'].get('wire_format', 'canonical') != args.wire_format:
            raise ValueError('Wire format differs from the frozen development protocol')
        requested_cases = args.case_id or protocol['development'].get('validation_case_ids', [])
        if args.case_id and protocol['development'].get('validation_case_ids') != args.case_id:
            raise ValueError('Focused case IDs differ from the frozen development protocol')
        event('asset_verification_started')
        for item in receipt['items']:
            path = model_root / item['name']
            if path.stat().st_size != item['bytes'] or sha256_file(path) != item['sha256']:
                raise ValueError('Local model/runtime archive changed')
        for item in receipt['runtime_files']:
            if sha256_file(model_root / item['path']) != item['sha256']:
                raise ValueError('Extracted runtime changed')
        server = next((model_root / 'runtime').rglob('llama-server.exe'))
        model = model_root / receipt['items'][0]['name']
        event('asset_verification_passed')
        with socket.socket() as check:
            check.bind(('127.0.0.1', 55580))
        command = [str(server), '--model', str(model), '--host', '127.0.0.1', '--port', '55580',
            '--ctx-size', '16384', '--parallel', '1', '--n-gpu-layers', '99', '--threads', '8',
            '--alias', 'tether-qwen25-14b-q4km-b466e1f', '--no-webui', '--offline']
        write(out / 'server-command.json', {'argv': command, 'runtime_sha256': sha256_file(server)})
        logs = [(out / ('server.' + name + '.log')).open('xb') for name in ('stdout', 'stderr')]
        try:
            process = subprocess.Popen(command, stdout=logs[0], stderr=logs[1],
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        finally:
            for stream in logs: stream.close()
        event('server_started', pid=process.pid)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('Owned local model server exited; retained native logs')
            try:
                with opener.open('http://127.0.0.1:55580/health', timeout=1) as response:
                    if response.status == 200: break
            except OSError:
                time.sleep(1)
        else:
            raise TimeoutError('Owned local model server startup timed out')
        event('server_ready', startup_elapsed_seconds=time.monotonic() - started)
        config = {'schema_version': 1, 'endpoint': 'http://127.0.0.1:55580',
            'model_id': 'Qwen/Qwen2.5-14B-Instruct-GGUF@' + receipt['revision'],
            'model_provenance': {'weights_sha256': {x['name']: x['sha256'] for x in receipt['items'] if x['name'].endswith('.gguf')},
                'runtime_sha256': sha256_file(server), 'acquisition_receipt_sha256': pointer['sha256']},
            'retrieval': {'max_records': 12, 'max_request_bytes': 12000},
            'max_output_tokens': 256, 'timeout_seconds': 120, 'seed': 20261017}
        if args.wire_format != 'canonical':
            config['retrieval']['wire_format'] = args.wire_format
        write(out / 'model-config.json', config)
        registry = json.loads(Path('planning/run-registry.json').read_text(encoding='utf-8'))
        old = next(x for x in registry['entries'] if x['id'] == registry['canonical_pilot_id'])
        build = next(x for x in registry['entries'] if x['id'] == old['build_id'])
        base = Path(build['path'])
        # Verify the exact selected build report rather than discovering the latest tree.
        for item in build['reports']:
            if sha256_file(Path(item['path'])) != item['sha256']:
                raise ValueError('Canonical source build proof changed')
        cases = old['cases']
        if requested_cases:
            if len(set(requested_cases)) != len(requested_cases) or set(requested_cases) - {c['case_id'] for c in cases}:
                raise ValueError('Unknown or duplicate selected development case')
            cases = [next(c for c in cases if c['case_id'] == cid) for cid in requested_cases]
        result['planned_case_ids'] = [c['case_id'] for c in cases]
        for case in cases:
            case_id = case['case_id']; case_started = time.monotonic()
            event('case_started', case_id=case_id)
            run = out / case_id
            argv = [sys.executable, '-m', 'tether_engine', 'run', '--case', str(base / case_id / 'case.json'),
                '--snapshot', str(base / case_id / 'snapshot.json'), '--catalog', 'data/catalog/sources.json',
                '--local-model', str(out / 'model-config.json'), '--output', str(run)]
            with (out / (case_id + '.stdout.log')).open('xb') as stdout, (out / (case_id + '.stderr.log')).open('xb') as stderr:
                completed = subprocess.run(argv, stdout=stdout, stderr=stderr, timeout=600,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if completed.returncode:
                raise RuntimeError('Local development case failed; inspect logs before any retry: ' + case_id)
            # A separate process rereads hashes and recomputes source-inclusive semantics.
            check = subprocess.run([sys.executable, '-m', 'tether_engine', 'verify', '--run-dir', str(run)],
                capture_output=True, timeout=600, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            (out / (case_id + '.verification.stdout.log')).write_bytes(check.stdout)
            (out / (case_id + '.verification.stderr.log')).write_bytes(check.stderr)
            if check.returncode:
                raise RuntimeError('Local development semantic/source verification failed: ' + case_id)
            status = json.loads((run / 'run.json').read_text(encoding='utf-8'))
            prediction = json.loads((run / 'prediction.json').read_text(encoding='utf-8'))
            if prediction['probability'] is not None:
                raise ValueError('Unvalidated clinical probability appeared')
            result['cases'].append({'case_id': case_id, 'status': status['status'],
                'calls': status['calls'], 'usage': status['usage'], 'coverage': status['coverage'],
                'receipt_sha256': sha256_file(run / 'receipt.json'), 'verification': json.loads(check.stdout),
                'elapsed_seconds_including_source_verification': time.monotonic() - case_started})
            event('case_verified', case_id=case_id, calls=status['calls'])
        result['status'] = 'ten_development_cases_verified' if len(cases) == 10 else 'selected_development_cases_verified'
    except BaseException as error:
        result.update(status='failed', error_class=type(error).__name__, error=str(error))
        event('failed', error_class=type(error).__name__)
        raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=10)
        result.update(finished_at_utc=datetime.now(timezone.utc).isoformat(),
            elapsed_seconds=time.monotonic() - started,
            server_stopped=process is None or process.poll() is not None)
        event('terminal', status=result['status'], server_stopped=result['server_stopped'])
        seal = {'files': [{'path': p.relative_to(out).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha256_file(p)}
            for p in sorted(out.rglob('*')) if p.is_file()]}
        write(out / 'evidence-manifest.json', seal)
        write(Path('data/derived/active-local-model-pilot.json'), {'path': str(out),
            'evidence_manifest_sha256': sha256_file(out / 'evidence-manifest.json')})


if __name__ == '__main__':
    main()
