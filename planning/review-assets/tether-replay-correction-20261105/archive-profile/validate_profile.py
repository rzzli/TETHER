"""Fresh archive compatibility checks against unchanged retained old controls."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).parent
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def check_profile():
    prepared = json.loads((HERE / 'PREPARED.json').read_bytes())
    path = ROOT / prepared['active_resource']
    assert path.read_bytes() == (ROOT / prepared['candidate']).read_bytes()
    assert sha(path) == prepared['new_resource_sha256']
    prior = ROOT / prepared['old_copy']
    assert sha(prior) == prepared['old_resource_sha256']
    old, new = json.loads(prior.read_bytes()), json.loads(path.read_bytes())
    assert new['previous_resource_sha256'] == sha(prior) and new['policy'] == old['policy']
    assert set(new['modules']) - set(old['modules']) == {'replay_validation.py'}
    assert set(old['modules']) <= set(new['modules'])
    assert sorted(k for k in old['modules'] if old['modules'][k] != new['modules'][k]) == ['__init__.py', 'agents.py', 'artifacts.py']
    assert {p.name: sha(p) for p in (ROOT / 'src/asof/archive').glob('*.py')} == prepared['archive_python_sha256']
    for name, expected in new['modules'].items():
        assert sha(ROOT / 'src/asof' / name) == expected, name
    return prepared


def main():
    work = ROOT / 'data/cache/replay-archive-profile-0313-attempt01'
    work.mkdir(exist_ok=False)
    temporary = work / 'temp'
    temporary.mkdir()
    os.environ['TEMP'] = os.environ['TMP'] = str(temporary)
    tempfile.tempdir = str(temporary)
    record = dict(schema_version=1, status='FAIL', work=str(work),
        scope='Source-tree archive compatibility qualification; no archived Python or model execution',
        created_at_utc=datetime.now(timezone.utc).isoformat(), checker_sha256=sha(Path(__file__)))
    try:
        prepared = check_profile()
        record['profile_sha256'] = prepared['new_resource_sha256']
        record['executing_module_sha256'] = prepared['approved_current_module_sha256']
        import asof
        from asof.archive.core import ensure_supported_semantics
        from asof.artifacts import verify_run
        assert asof.__version__ == '0.3.13'
        ensure_supported_semantics()
        suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test_archive*.py', top_level_dir=str(ROOT))
        with (work / 'archive-tests.log').open('x', encoding='utf-8') as stream:
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        record['tests'] = dict(run=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped))
        record['tests_log_sha256'] = sha(work / 'archive-tests.log')
        assert result.testsRun >= 52 and result.wasSuccessful() and not result.skipped
        legacy_source = ROOT / 'tests/fixtures/legacy-v1'
        legacy_before = inventory(legacy_source)
        legacy = work / 'preserved-legacy-v1'
        shutil.copytree(legacy_source, legacy)
        anchor = (legacy / 'receipt.sha256').read_text().strip()
        record['preserved_v1_byte_check'] = verify_run(legacy, anchor)
        assert record['preserved_v1_byte_check']['semantic_consistency'] == 'unavailable_legacy_v1'
        assert legacy_before == inventory(legacy_source) == inventory(legacy)
        old_work = ROOT / 'data/cache/ce-archive-profile-v2-attempt01/old'
        old_before = inventory(old_work)
        manifest_path = old_work / 'manifest.json'
        prior_validation_path = ROOT / 'planning/review-assets/tether-ce-fixes-20261102/archive-profile-v2/VALIDATION.json'
        prior_validation = json.loads(prior_validation_path.read_bytes())
        assert sha(manifest_path) == prior_validation['old_manifest_sha256']
        helper = ROOT / 'planning/review-assets/tether-ce-fixes-20261102/archive-profile-v2/run_archive_regressions.py'
        assert sha(helper) == prior_validation['script_sha256']
        spec = importlib.util.spec_from_file_location('retained_archive_relocation_helper', helper)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        manifest = json.loads(manifest_path.read_bytes())
        record['retained_old_controls'] = module.relocated_controls(work, manifest)
        record['old_manifest_sha256'] = sha(manifest_path)
        record['old_controls_unchanged'] = old_before == inventory(old_work)
        record['old_producer_version'] = manifest['engine_version']
        record['previous_validation_sha256'] = sha(prior_validation_path)
        record['relocation_helper_sha256'] = sha(helper)
        assert record['old_controls_unchanged']
        check_profile()
        record['profile_and_archive_python_unchanged_during_validation'] = True
        record['status'] = 'PASS'
    except Exception as error:
        record['error'] = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc())
    record['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
    with (HERE / 'VALIDATION.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    print(json.dumps(record, indent=2))
    return 0 if record['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
