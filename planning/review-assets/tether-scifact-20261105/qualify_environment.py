"""Check actual installed payloads against RECORD and retained wheel hashes."""
import base64
import csv
import hashlib
import importlib.metadata as md
import io
import json
import platform
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def main():
    wheel_root = Path('data/cache/tether-scifact-wheels-attempt01')
    manifest = json.loads((wheel_root/'WHEELS.json').read_text(encoding='utf-8'))
    expected = {x['package']: x['version'] for x in manifest['wheels']}
    expected.update({'asof-target-agents': '0.3.13', 'tether-target-agents': '0.5.2'})
    installed, wheels = {}, []
    for name, version in expected.items():
        dist = md.distribution(name)
        assert dist.version == version, name
        count = 0
        for file in dist.files or []:
            if file.hash is None:
                continue
            assert file.hash.mode == 'sha256', file
            path = Path(dist.locate_file(file))
            content = path.read_bytes()
            digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b'=').decode()
            assert digest == file.hash.value and len(content) == file.size, str(path)
            count += 1
        installed[name] = {'version': version, 'record_payloads_verified': count,
                           'metadata_sha256': hashlib.sha256(dist.read_text('METADATA').encode()).hexdigest()}
    paths = sorted(wheel_root.glob('*.whl')) + sorted(Path('data/cache/tether-052-installed-qualification-attempt01/wheels').glob('*.whl'))
    for path in paths:
        raw = path.read_bytes()
        if path.parent == wheel_root:
            item = next(x for x in manifest['wheels'] if x['filename'] == path.name)
            assert hashlib.sha256(raw).hexdigest() == item['sha256'] and len(raw) == item['bytes']
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            licenses = [{'member': x, 'sha256': hashlib.sha256(archive.read(x)).hexdigest()}
                        for x in archive.namelist() if any(k in x.upper() for k in ('LICENSE','COPYING','NOTICE')) and not x.endswith('/')]
        wheels.append({'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'license_members': licenses})
    result = {'schema_version': 1, 'status': 'PASS', 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'python': {'version': platform.python_version(), 'executable': sys.executable,
                         'executable_sha256': hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
                         'base_executable': sys._base_executable,
                         'base_executable_sha256': hashlib.sha256(Path(sys._base_executable).read_bytes()).hexdigest()},
              'installed': installed, 'wheels': wheels, 'scope': 'installed versions/RECORD and acquired wheel bytes; solver tests separate'}
    out = Path(sys.argv[1])
    with out.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(result,f,indent=2); f.write('\n')
    print(json.dumps({'status': 'PASS', 'packages': len(installed), 'payloads': sum(x['record_payloads_verified'] for x in installed.values()), 'wheels': len(wheels)}))


if __name__ == '__main__':
    main()
