"""Preserve/test the ordered-execution increment; no raw corpus, weights or credentials.

Uses the previously authorized E: backup root. Upload is a separate explicit command.
"""
import argparse
import json
from pathlib import Path
import subprocess
import zipfile

from asof.serde import read_json, safe_child, sha256_file, write_json

ROOT = Path(__file__).resolve().parents[3]
EXTERNAL = Path('E:/projects_data/drug_target_agents_data')


def reserved(path):
    path = path.resolve()
    if not path.is_relative_to((EXTERNAL / 'backups').resolve()):
        raise ValueError('Use the authorized project backup root')
    path.mkdir(parents=True, exist_ok=False)
    return path


def archive_path(path):
    path = path.resolve()
    if path.is_relative_to(ROOT): return 'project/' + path.relative_to(ROOT).as_posix()
    if path.is_relative_to(EXTERNAL): return 'external/' + path.relative_to(EXTERNAL).as_posix()
    raise ValueError('Source outside authorized project roots')


def prepare(destination):
    destination = reserved(destination); sources = set(); seals = []
    for name in ['2026-10-17-registry-scope.json', '2026-10-17-registry-power.json',
                 '2026-10-17-registry-power-diagnostic.json', '2026-10-17-local-model-canonical-pilot.json',
                 '2026-10-17-local-model-wire-pilot.json', '2026-10-17-full-cis-revision.json']:
        anchor = read_json(ROOT / 'data/manifests/public' / name)
        pin = anchor.get('canonical_manifest')
        if pin:
            seal = Path(pin['path']); seal = seal if seal.is_absolute() else ROOT / seal
            expected = pin['sha256']
        else:
            pin = anchor['evidence_anchor']; seal = Path(pin['root']) / pin['manifest']; expected = pin['sha256']
        if sha256_file(seal) != expected: raise ValueError('Changed product seal')
        sources.add(seal.resolve()); seals.append({'archive_path': archive_path(seal), 'sha256': expected})
        sources.update(safe_child(seal.parent, row['path']) for row in read_json(seal)['files'])
    for name in ['task4-replay-initial-validation.json', 'task4-replay-validation.json']:
        report = read_json(ROOT / 'planning/review-assets/ordered-execution-20261017' / name)
        folder = ROOT / report['output']; sources.update(p.resolve() for p in folder.iterdir() if p.is_file())
    for name in ['active-registry-scope.json', 'active-registry-power-calibrated.json',
                 'active-local-model-acquisition.json', 'active-chronology-qualification.json', 'active-local-model-pilot.json']:
        sources.add((ROOT / 'data/derived' / name).resolve())
    receipt = Path(read_json(ROOT / 'data/derived/active-local-model-acquisition.json')['path'])
    sources.update([receipt, receipt.parent / 'LICENSE-QWEN'])
    qualification = Path(read_json(ROOT / 'data/derived/active-chronology-qualification.json')['path'])
    sources.update([qualification, qualification.parent / 'dump-toc.txt'])
    entries = []
    with zipfile.ZipFile(destination / 'ordered-evidence.zip', 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for source in sorted(sources):
            if any(k in source.parts for k in ('.git', 'pgdata', '.local-postgres-secrets', '__pycache__')) or any(
                    k in source.name.lower() for k in ('password', 'credential', 'signed_url', 'secret')):
                raise ValueError('Sensitive or excluded backup input')
            if source.suffix.lower() in ('.gguf', '.exe', '.dll') or source.name == 'postgres.dmp':
                raise ValueError('Bulk native/model/archive payload excluded')
            before = source.stat(); digest = sha256_file(source); member = archive_path(source)
            z.write(source, member)
            after = source.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError('Changing source during preservation')
            entries.append({'archive_path': member, 'bytes': after.st_size, 'sha256': digest})
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    subprocess.run(['git', 'bundle', 'create', str(destination / 'repository.bundle'), '--all'], cwd=ROOT, check=True, capture_output=True)
    write_json(destination / 'file-manifest.json', {'code_commit': head, 'files': entries, 'seals': seals,
        'dependency': 'Prior registry-sizing-20261017 recovery release for the v0.4 baseline',
        'excluded': 'Original raw datasets, full AACT archives/dumps/databases, model/native binaries and credentials; originals remain in authorized local storage'})
    write_json(destination / 'asset-hashes.json', {'code_commit': head, 'assets': {n: {
        'bytes': (destination / n).stat().st_size, 'sha256': sha256_file(destination / n)}
        for n in ['ordered-evidence.zip', 'repository.bundle', 'file-manifest.json']}})
    print(json.dumps({'files': len(entries), 'payload_bytes': sum(e['bytes'] for e in entries),
        'zip_bytes': (destination / 'ordered-evidence.zip').stat().st_size,
        'asset_index_sha256': sha256_file(destination / 'asset-hashes.json'), 'code_commit': head}))


def restore(download, destination, expected):
    download = download.resolve()
    if sha256_file(download / 'asset-hashes.json') != expected: raise ValueError('Wrong independently retained index')
    assets = read_json(download / 'asset-hashes.json')
    if set(assets['assets']) != {'ordered-evidence.zip', 'repository.bundle', 'file-manifest.json'}:
        raise ValueError('Unexpected recovery assets')
    for name, item in assets['assets'].items():
        if sha256_file(download / name) != item['sha256'] or (download / name).stat().st_size != item['bytes']:
            raise ValueError('Downloaded recovery asset changed')
    destination = reserved(destination); manifest = read_json(download / 'file-manifest.json'); seen = set()
    with zipfile.ZipFile(download / 'ordered-evidence.zip') as z:
        if len(z.infolist()) != len(manifest['files']): raise ValueError('Archive inventory differs')
        for item in manifest['files']:
            path = safe_child(destination, item['archive_path'])
            if path in seen: raise ValueError('Duplicate recovery member')
            seen.add(path); path.parent.mkdir(parents=True, exist_ok=True)
            with z.open(item['archive_path']) as src, path.open('xb') as dst:
                while block := src.read(4 * 1024 * 1024): dst.write(block)
            if sha256_file(path) != item['sha256'] or path.stat().st_size != item['bytes']:
                raise ValueError('Restored file differs')
    for seal in manifest['seals']:
        path = safe_child(destination, seal['archive_path'])
        if sha256_file(path) != seal['sha256']: raise ValueError('Restored product seal differs')
        for item in read_json(path)['files']:
            if sha256_file(safe_child(path.parent, item['path'])) != item['sha256']:
                raise ValueError('Restored sealed product member differs')
    clone = destination / 'repository'
    subprocess.run(['git', 'clone', '--no-hardlinks', str(download / 'repository.bundle'), str(clone)], check=True, capture_output=True)
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=clone, text=True).strip()
    if actual != assets['code_commit']: raise ValueError('Restored source commit differs')
    subprocess.run(['git', 'fsck', '--full'], cwd=clone, check=True, capture_output=True)
    report = {'status': 'downloaded_increment_restored_and_verified', 'files_rehashed': len(seen),
        'sealed_products_verified': len(manifest['seals']), 'code_commit': actual, 'git_fsck': 'passed',
        'asset_index_sha256': expected, 'payload_bytes': sum(x['bytes'] for x in manifest['files']),
        'scope': 'Incremental scientific artifacts and code; not a full original-data/model backup or new scientific validation'}
    write_json(destination / 'restore-report.json', report); print(json.dumps(report))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='mode', required=True)
    a = sub.add_parser('prepare'); a.add_argument('--destination', type=Path, required=True)
    a = sub.add_parser('restore'); a.add_argument('--download', type=Path, required=True)
    a.add_argument('--destination', type=Path, required=True); a.add_argument('--expected-index-sha256', required=True)
    a = p.parse_args()
    if a.mode == 'prepare': prepare(a.destination)
    else: restore(a.download, a.destination, a.expected_index_sha256)
