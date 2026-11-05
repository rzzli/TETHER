"""Run the unchanged facade suite with exact source and dev-metadata brackets."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).parent
ENVIRONMENT = ROOT / 'data/cache/tether-052-dev'
sys.path.insert(0, str(ROOT))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    paths = set()
    for directory in (ROOT / 'src/asof', ROOT / 'packages/tether/src/tether'):
        paths.update(p for p in directory.rglob('*') if p.suffix in ('.py', '.json') and '__pycache__' not in p.parts)
    paths.update((ROOT / 'packages/tether/tests').glob('*.py'))
    paths.update((ROOT / 'tests').glob('*.py'))
    paths.update(ROOT / name for name in ('pyproject.toml', 'uv.lock', 'packages/tether/pyproject.toml',
        'packages/tether/uv.lock') if (ROOT / name).is_file())
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def metadata_pins():
    base = ENVIRONMENT / 'Lib/site-packages'
    paths = set()
    for name in ('asof_target_agents-*.dist-info', 'tether_target_agents-*.dist-info'):
        for directory in base.glob(name):
            paths.update(p for p in directory.rglob('*') if p.is_file())
    paths.update(base.glob('__editable__.*.pth'))
    return {p.relative_to(ENVIRONMENT).as_posix(): sha(p) for p in sorted(paths)}


def save(name, value):
    with (HERE / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    assert Path(sys.executable).resolve() == (ENVIRONMENT / 'Scripts/python.exe').resolve()
    temporary = ROOT / 'data/cache/replay-facade-validation-052-attempt01'
    temporary.mkdir(exist_ok=False)
    os.environ['TEMP'] = os.environ['TMP'] = str(temporary)
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    tempfile.tempdir = str(temporary)
    before, metadata_before = sources(), metadata_pins()
    record = dict(schema_version=1, status='STARTED', started_at_utc=datetime.now(timezone.utc).isoformat(),
        python=sys.executable, python_sha256=sha(Path(sys.executable)),
        versions={name: metadata.version(name) for name in ('asof-target-agents', 'tether-target-agents')},
        source_sha256=before, environment_metadata_sha256=metadata_before,
        temporary=str(temporary), checker_sha256=sha(Path(__file__)),
        scope='Source-tree facade suite in fresh candidate dev environment; not isolated installed-release qualification')
    save('STARTED.json', record)
    try:
        assert record['versions'] == {'asof-target-agents': '0.3.13', 'tether-target-agents': '0.5.2'}
        with (HERE / 'facade-tests.log').open('x', encoding='utf-8') as log, redirect_stdout(log), redirect_stderr(log):
            suite = unittest.defaultTestLoader.discover(str(ROOT / 'packages/tether/tests'), pattern='test_*.py')
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        record['tests'] = dict(run=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped))
        assert result.testsRun > 0 and result.wasSuccessful() and not result.skipped, record['tests']
        record['status'] = 'PASS'
    except BaseException as error:
        record.update(status='FAIL', error=dict(type=type(error).__name__, reason=str(error), traceback=traceback.format_exc()))
    record['source_sha256_after'] = sources()
    record['environment_metadata_sha256_after'] = metadata_pins()
    record['sources_unchanged'] = before == record['source_sha256_after']
    record['metadata_unchanged'] = metadata_before == record['environment_metadata_sha256_after']
    if not record['sources_unchanged'] or not record['metadata_unchanged']:
        record['status'] = 'FAIL'
    log = HERE / 'facade-tests.log'
    record['log_sha256'] = sha(log) if log.exists() else None
    record['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    save('VALIDATION.json', record)
    print(json.dumps({key: record.get(key) for key in ('status', 'tests', 'sources_unchanged', 'metadata_unchanged', 'log_sha256', 'error')}, indent=2))
    return 0 if record['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
