"""Explicit installed-release replay checks; never overwrite or rescore BG02.

Run only with the new qualified environment's Python using -I -B. This script
does not add repository source directories to sys.path or load experiment code.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata, resources
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import traceback
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def inventory(directory):
    return {p.relative_to(directory).as_posix(): sha(p) for p in sorted(directory.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def installed_pins(environment):
    site = environment / 'Lib/site-packages'
    result = {}
    for name in ('asof', 'tether'):
        result[name] = inventory(site / name)
    for pattern in ('asof_target_agents-*.dist-info', 'tether_target_agents-*.dist-info'):
        for directory in site.glob(pattern):
            result[directory.name] = inventory(directory)
    result['python.exe'] = sha(environment / 'Scripts/python.exe')
    return result


def forbid_network(event, arguments):
    if event in ('socket.connect', 'socket.connect_ex', 'socket.bind', 'socket.getaddrinfo'):
        raise PermissionError('Installed replay qualification forbids network operations')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qualification', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    qualification = args.qualification.resolve()
    environment = qualification / 'environment'
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / 'data/cache'):
        parser.error('Use a fresh output directory under project data/cache')
    if (Path(sys.executable).resolve() != (environment / 'Scripts/python.exe').resolve()
            or not sys.flags.isolated or not sys.dont_write_bytecode):
        parser.error('Use the qualified installed environment interpreter with -I -B')
    qualification_path = qualification / 'QUALIFICATION.json'
    qualified = json.loads(qualification_path.read_bytes())
    if qualified.get('status') != 'PASS':
        parser.error('Installed release qualification must finish successfully first')
    output.mkdir(exist_ok=False)
    temporary = output / 'temporary'
    temporary.mkdir()
    os.environ['TEMP'] = os.environ['TMP'] = str(temporary)
    tempfile.tempdir = str(temporary)
    sys.addaudithook(forbid_network)
    before = installed_pins(environment)
    diagnostic = ROOT / 'planning/review-assets/tether-equal-policy-result-review-20261105/ep075-causal-attempt01'
    diagnostic_before = inventory(diagnostic)
    record = dict(schema_version=1, status='STARTED', checked_at_utc=datetime.now(timezone.utc).isoformat(),
        qualification_sha256=sha(qualification_path), python=sys.executable,
        checker_sha256=sha(Path(__file__)), installed_before=before,
        scope='Installed release replay qualification with fictional data and unchanged post-hoc counterexample; not a scored benchmark')
    save(output / 'STARTED.json', record)
    try:
        import asof
        import tether
        from asof.agents import ReplayBackend
        from asof.artifacts import verify_run, write_run
        from asof.chrono import load_snapshot
        from asof.contracts import Case
        from asof.scorer import ScorerArtifact
        from asof.serde import ContractError, decode, read_json
        from asof.workflow import run_workflow
        from tether._presentation import verify_engine
        versions = {name: metadata.version(name) for name in ('asof-target-agents', 'tether-target-agents')}
        assert versions == {'asof-target-agents': '0.3.13', 'tether-target-agents': '0.5.2'}
        assert asof.__version__ == '0.3.13' and tether.__version__ == '0.5.2'
        for module in (asof, tether):
            assert Path(module.__file__).resolve().is_relative_to(environment / 'Lib/site-packages')
        assert not any(Path(path).resolve() in (ROOT / 'src', ROOT / 'packages/tether/src') for path in sys.path if path)
        record['runtime'] = dict(versions=versions, asof_file=asof.__file__, tether_file=tether.__file__, isolated=True)
        fixture = output / 'fictional-inputs'
        shutil.copytree(Path(str(resources.files('asof').joinpath('demo', 'v2'))), fixture)
        case = decode(Case, read_json(fixture / 'case.json'))
        model = decode(ScorerArtifact, read_json(fixture / 'scorer.json'))
        store = load_snapshot(fixture / 'snapshot.json', case)
        result = run_workflow(case, store, ReplayBackend(fixture / 'replay.json'), model)
        positive = output / 'positive-recorded-run'
        anchor = write_run(positive, result, store, model)
        (fixture / 'replay.json').unlink()  # Only this fresh fictional copy.
        with patch.object(ReplayBackend, 'quote', side_effect=AssertionError('Verification cannot quote')), \
             patch.object(ReplayBackend, 'select', side_effect=AssertionError('Verification cannot dispatch')):
            record['positive'] = verify_engine(positive, anchor, True)
            record['positive_archived_only'] = verify_run(positive, anchor, verify_sources=False)
            observations = []
            for name, verifier in (('live_core_source', lambda: verify_run(diagnostic / 'copied-bundle/run')),
                ('live_core_archived_only', lambda: verify_run(diagnostic / 'copied-bundle/run', verify_sources=False)),
                ('facade_engine_source', lambda: verify_engine(diagnostic / 'copied-bundle/run', None, True))):
                try:
                    verifier()
                except ContractError as error:
                    observations.append(dict(surface=name, decision='reject', reason=str(error)))
                else:
                    observations.append(dict(surface=name, decision='accept'))
            record['retained_counterexample'] = observations
        assert record['positive']['semantic_consistency'] == 'verified'
        assert record['positive']['code_matches_current'] is True
        assert record['positive']['replay_binding']['request_binding'] == 'source_reconstructed'
        assert record['positive_archived_only']['replay_binding']['request_binding'] == 'archived_dispatch_fingerprints'
        assert all(row['decision'] == 'reject' and 'request fingerprint' in row['reason'] for row in observations)
        record['positive_calls'] = result.calls
        record['positive_receipt_sha256'] = anchor
        record['status'] = 'PASS'
    except BaseException as error:
        record.update(status='FAIL', error=dict(type=type(error).__name__, reason=str(error), traceback=traceback.format_exc()))
    record['installed_after'] = installed_pins(environment)
    record['installed_unchanged'] = before == record['installed_after']
    record['retained_counterexample_unchanged'] = diagnostic_before == inventory(diagnostic)
    record['qualification_unchanged'] = sha(qualification_path) == record['qualification_sha256']
    if not all(record[k] for k in ('installed_unchanged', 'retained_counterexample_unchanged', 'qualification_unchanged')):
        record['status'] = 'FAIL'
    record['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    save(output / 'RESULT.json', record)
    print(json.dumps({key: record.get(key) for key in ('status', 'runtime', 'positive_calls', 'retained_counterexample', 'installed_unchanged', 'error')}, indent=2))
    return 0 if record['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
