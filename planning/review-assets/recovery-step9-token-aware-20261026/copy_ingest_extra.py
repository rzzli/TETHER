"""Copy the existing approved Arrow21 install into the optional verifier environment.

No network, acquisition or dependency change to the default project runtime.
The default installed-wheel checks run first without this optional dependency.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'.venv/Lib/site-packages'
TARGET = ROOT/'data/cache/recovery-step9-token-aware-wheel-20261026/environment-v2/Lib/site-packages'
REPORT = ROOT/'data/cache/r09prep-installed-20261026/optional-ingest-copy.json'
default = json.loads((REPORT.parent/'guarded-installed-verification.json').read_bytes())
assert default['status'] == 'passed'
files = []
for name in ('pyarrow', 'pyarrow.libs', 'pyarrow-21.0.0.dist-info'):
    source, target = SOURCE/name, TARGET/name
    assert source.is_dir() and not source.is_symlink() and not target.exists()
    for path in sorted(source.rglob('*')):
        assert not path.is_symlink()
        if not path.is_file() or '__pycache__' in path.parts:
            continue
        raw = path.read_bytes()
        destination = target/path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(raw)
        digest = hashlib.sha256(raw).hexdigest()
        assert hashlib.sha256(destination.read_bytes()).hexdigest() == digest
        files.append(dict(path=destination.relative_to(TARGET).as_posix(), sha256=digest, bytes=len(raw)))
with REPORT.open('x', encoding='utf-8') as stream:
    json.dump(dict(schema_version=1, status='copied_existing_optional_dependency',
                   dependency='pyarrow==21.0.0', source=str(SOURCE), target=str(TARGET),
                   downloads=0, default_runtime_dependencies_changed=False, files=files), stream, indent=2)
print(json.dumps(dict(status='copied', files=len(files), bytes=sum(f['bytes'] for f in files))))
