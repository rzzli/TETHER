"""Fetch pinned public local-inference assets, independently of biomedical workers.

Every invocation reserves a new directory. Partial files and failure records remain;
no automatic retries, existing-file rewrites, global install or provider calls.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import urllib.request
import zipfile

from tether_engine.serde import sha256_file


def main():
    policy = json.loads(Path('planning/protocols/evaluation-v0.1.json').read_text(encoding='utf-8'))
    model = policy['models'][0]
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    root = Path('E:/projects_data/drug_target_agents_data/models') / ('qwen25-14b-q4km-' + stamp)
    root.mkdir(parents=True, exist_ok=False)
    proof = json.loads(Path('planning/review-assets/ordered-execution-20261017/chronology-source-proof.json').read_text(encoding='utf-8'))
    runtime = proof['native_runtime_candidate']['assets'][0]
    items = [{'name': a['path'], 'bytes': a['bytes'], 'sha256': a['sha256'],
        'url': f"https://huggingface.co/{model['id']}/resolve/{model['revision']}/{a['path']}"} for a in model['files']]
    items.append({'name': runtime['name'], 'bytes': runtime['size'],
        'sha256': runtime['digest'].removeprefix('sha256:'), 'url': runtime['browser_download_url']})
    result = {'status': 'running', 'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'model_id': model['id'], 'revision': model['revision'], 'root': str(root),
        'provider_spend_usd': 0, 'items': items, 'runtime_tag': proof['native_runtime_candidate']['tag']}
    def save():
        (root / 'acquisition.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    save()
    try:
        if shutil.disk_usage(root).free < 2 * sum(x['bytes'] for x in items):
            raise ValueError('Insufficient free storage with working reserve')
        for item in items:
            dest = root / item['name']; temporary = dest.with_suffix(dest.suffix + '.partial')
            request = urllib.request.Request(item['url'], headers={'User-Agent': 'TETHER local model qualification'})
            digest = hashlib.sha256(); count = 0
            item['status'] = 'started'; save()
            with urllib.request.urlopen(request, timeout=60) as response, temporary.open('xb') as stream:
                while block := response.read(8 * 1024 * 1024):
                    count += len(block)
                    if count > item['bytes']:
                        raise ValueError('Download exceeds pinned file size')
                    stream.write(block); digest.update(block)
            if count != item['bytes'] or digest.hexdigest() != item['sha256']:
                raise ValueError('Download differs from publisher pin: ' + item['name'])
            temporary.rename(dest); item.update(status='hash_verified', collected_at_utc=datetime.now(timezone.utc).isoformat()); save()
            print(json.dumps({'name': item['name'], 'bytes': count, 'status': item['status']}), flush=True)
        license_url = f"https://huggingface.co/{model['id']}/resolve/{model['revision']}/LICENSE"
        with urllib.request.urlopen(license_url, timeout=30) as response:
            payload = response.read(100_000)
        if b'Apache' not in payload or len(payload) >= 100_000:
            raise ValueError('Expected bounded Apache license text')
        (root / 'LICENSE-QWEN').write_bytes(payload)
        native = root / 'runtime'; native.mkdir()
        with zipfile.ZipFile(root / runtime['name']) as z:
            if sum(x.file_size for x in z.infolist()) > 512 * 1024 * 1024:
                raise ValueError('Unexpected native package expansion')
            for entry in z.infolist():
                if entry.is_dir():
                    continue
                target = native / entry.filename
                if not target.resolve().is_relative_to(native.resolve()):
                    raise ValueError('Unsafe native archive path')
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(entry) as source, target.open('xb') as stream:
                    shutil.copyfileobj(source, stream)
        result['runtime_files'] = [{'path': str(p.relative_to(root)), 'sha256': sha256_file(p), 'bytes': p.stat().st_size}
            for p in sorted(native.rglob('*')) if p.is_file()]
        result.update(status='downloaded_hash_verified_not_inference_validated', license_sha256=sha256_file(root / 'LICENSE-QWEN'))
    except BaseException as error:
        result.update(status='failed', error_class=type(error).__name__)
        raise
    finally:
        result['finished_at_utc'] = datetime.now(timezone.utc).isoformat(); save()
        Path('data/derived/active-local-model-acquisition.json').write_text(json.dumps({
            'path': str(root / 'acquisition.json'), 'sha256': sha256_file(root / 'acquisition.json')}, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'root': str(root), 'status': result['status']}), flush=True)


if __name__ == '__main__':
    main()
