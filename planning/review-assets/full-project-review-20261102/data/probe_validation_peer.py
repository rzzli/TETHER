"""Independent bounded validator stage probes; discovery is always intercepted."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools import validate

HERE = Path(__file__).resolve().parent


def main():
    scratch = ROOT / 'data/cache/full-review-validator-peer'
    scratch.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(scratch)
    checks = []
    for scenario in ('prerequisite', 'discovery_interrupt', 'packaging', 'success'):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'report.json'
            suite = unittest.TestSuite([unittest.FunctionTestCase(lambda: None)])
            with contextlib.ExitStack() as stack:
                structural = stack.enter_context(patch.object(validate, 'structural_checks', return_value={}))
                stack.enter_context(patch.object(validate, 'powershell_check', return_value=True))
                discovery = stack.enter_context(patch.object(validate.unittest.defaultTestLoader, 'discover', return_value=suite))
                probe = stack.enter_context(patch.object(validate, 'probe_main', return_value=0))
                package = stack.enter_context(patch.object(validate, 'package_check', return_value={}))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
                argv = ['--mode', 'core', '--report', str(target)]
                if scenario == 'prerequisite':
                    stack.enter_context(patch.dict(validate.sys.modules, {'pyarrow': None}))
                    argv[1] = 'full'
                elif scenario == 'discovery_interrupt':
                    discovery.side_effect = KeyboardInterrupt
                elif scenario == 'packaging':
                    package.side_effect = OSError('fictional offline build error')
                    argv.append('--package')
                code = validate.main(argv)
                report = json.loads(target.read_text())
                if scenario == 'prerequisite':
                    assert code == 1 and report['stage'] == 'prerequisites' and report['status'] == 'failed'
                    structural.assert_not_called(); discovery.assert_not_called(); probe.assert_not_called()
                elif scenario == 'discovery_interrupt':
                    assert code == 130 and report['stage'] == 'tests' and report['status'] == 'interrupted'
                    probe.assert_not_called(); package.assert_not_called()
                elif scenario == 'packaging':
                    assert code == 1 and report['stage'] == 'packaging' and report['status'] == 'failed'
                    assert report['tests']['run'] == 1 and report['required_probes_exit_code'] == 0
                else:
                    assert code == 0 and report['stage'] == 'complete' and report['status'] == 'passed'
                checks.append({'scenario': scenario, 'status': 'PASS', 'observed_exit': code, 'reported_stage': report['stage']})
    subjects = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                for p in ('tools/validate.py', 'tests/test_validation_failure_report.py')}
    result = {'schema_version': 1, 'method': 'tether.independent_validator_stage_review.v1',
              'status': 'PASS_BOUNDED_VALIDATOR_STAGE_REVIEW', 'role': 'evaluation_only',
              'agent_visible': False, 'subjects': subjects, 'checks': checks,
              'scope': 'Source review and four mocked lifecycle probes. No actual broad discovery, package build or framework probe execution.',
              'unresolved_findings': [],
              'limits': ['No hard-kill recovery or exclusive cross-process reservation',
                         'Final report filesystem publication can still fail; stdout/error remains the fallback',
                         'Root earlier accidentally entered broad discovery; its interrupted transcript is not passing test evidence']}
    (HERE / 'VALIDATOR-PEER.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'independent_scenarios': len(checks)}))


if __name__ == '__main__':
    main()
