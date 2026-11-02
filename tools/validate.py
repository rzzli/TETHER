"""Clean-checkout validation shared by local development and CI; no biomedical downloads."""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from asof.maintenance import validate_catalog, write_new_json
from asof.serde import ContractError, read_json
from tools.review.probe_framework import main as probe_main

EXPECTED_CORE_SKIPS = {'install the ingest extra for adapter tests',
    'install the ingest extra for source-audit tests', 'PowerShell 7 required for utility integration',
    'native held-handle test requires Windows'}


class LiveErrorResult(unittest.TextTestResult):
    """Retain unittest accounting while printing diagnostic tracebacks promptly."""

    def addError(self, test, error):
        super().addError(test, error)
        self.stream.write('\nCaptured test error: ' + self.getDescription(test) + '\n' + self.errors[-1][1])
        self.stream.flush()

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.stream.write('\nCaptured assertion failure: ' + self.getDescription(test) + '\n' + self.failures[-1][1])
        self.stream.flush()

# Failed originals are retained as audit data, never imported/executed. Only an
# exact path AND byte hash is exempt from the active-source syntax requirement.
ARCHIVED_INVALID_PYTHON = {
    'planning/review-assets/recovery-step9-native-recognition-20261028/check_recognition_module_policy_v1_before_syntax.py':
        '5aa964d861635aaf01c50ec05f83618d5bfb7307f6e591630991f34070d05253',
}


def validate_python_artifact(name, raw):
    """Parse active code while preserving sealed intentionally invalid originals."""
    expected = ARCHIVED_INVALID_PYTHON.get(name)
    if expected is not None:
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ContractError('Preserved invalid-source archive changed: '+name)
        try:
            ast.parse(raw.decode('utf-8-sig'), filename=name)
        except SyntaxError:
            return 'archived_invalid_source'
        raise ContractError('Expected failed-source archive unexpectedly parses: '+name)
    ast.parse(raw.decode('utf-8-sig'), filename=name)
    return 'active_python'


def successful_tests(result, mode):
    return (result.testsRun > 0 and result.wasSuccessful() and
            all(mode == 'core' and reason in EXPECTED_CORE_SKIPS for _,reason in result.skipped))


def structural_checks():
    files = subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).decode().split('\0')
    files = sorted(set(name for name in files if name))
    archived_invalid = []
    for name in files:
        parts = Path(name).parts
        if any(key in parts for key in ('.venv','runs','private')):
            raise ContractError('Private or generated file entered tracking scope: '+name)
        if name.startswith(('data/raw/','data/reference/','data/derived/','data/cache/','data/benchmark/')) and Path(name).name != '.gitkeep':
            raise ContractError('Bulk/benchmark payload entered tracking scope: '+name)
        if name.endswith('.py'):
            if validate_python_artifact(name, (ROOT/name).read_bytes()) == 'archived_invalid_source':
                archived_invalid.append(name)
    for name in ('runs/probe.json','data/derived/probe.json','data/raw/probe.parquet',
                 'data/manifests/private/probe.json','.venv/probe','.env','data/benchmark/labels/probe.json'):
        if subprocess.run(['git','check-ignore','-q',name],cwd=ROOT).returncode:
            raise ContractError('Required ignore missing: '+name)
    catalog = read_json(ROOT/'data/catalog/sources.json')
    validate_catalog(catalog)
    artifact_policy = ROOT/'data/catalog/policy-v2.json'
    if artifact_policy.exists():
        # The frozen engine remains schema-one. Validate the additive canonical
        # policy explicitly; file presence never promotes collection/readiness.
        canonical_source = str(ROOT/'packages/tether/src')
        if canonical_source not in sys.path:
            sys.path.insert(0, canonical_source)
        from tether._catalog_policy import strict_json, validate_policy, validate_source_catalog
        policy = strict_json(artifact_policy.read_bytes())
        validate_policy(policy)
        validate_source_catalog(policy, (ROOT/'data/catalog/sources.json').read_bytes())
    index = set(re.findall(r'^\| `([^`]+)` \|',(ROOT/'data/DATA_PLAN.md').read_text(encoding='utf-8'),re.M))
    if not {row['dataset_id'] for row in catalog['datasets']}.issubset(index):
        raise ContractError('Catalog products missing from documentation index')
    registry = read_json(ROOT/'planning/run-registry.json')
    entries = registry['entries']
    selected = [row for row in entries if row['id']==registry['canonical_pilot_id']]
    if len(selected)!=1 or selected[0]['state']!='canonical' or len(selected[0]['cases'])!=10:
        raise ContractError('Invalid canonical registry')
    # Local production assets may be absent in a clean checkout.
    from asof.serde import safe_child
    for row in entries:
        safe_child(ROOT,row['path'])
    return {'tracked_scope_files':len(files),'providers':len(catalog['providers']),'datasets':len(catalog['datasets']),
            'preserved_invalid_python_archives':archived_invalid}


def powershell_check():
    if not shutil.which('pwsh'):
        return False
    code = "$ErrorActionPreference='Stop'; Get-ChildItem tools,planning/review-assets -Recurse -Filter *.ps1 | ForEach-Object { $t=$null; $e=$null; [System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$t,[ref]$e) | Out-Null; if($e.Count){throw ('Syntax error: '+$_.FullName)} }"
    subprocess.run(['pwsh','-NoProfile','-Command',code],cwd=ROOT,check=True)
    return True


def package_check(directory):
    constraints = ROOT/'paper/release/build-constraints.txt'
    subprocess.run(['uv','build','--offline','--build-constraints',str(constraints),
                    '--python',sys.executable,'--wheel','--out-dir',str(directory/'dist')],cwd=ROOT,check=True,capture_output=True)
    wheel = next((directory/'dist').glob('*.whl'))
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        if 'asof/demo/v2/case.json' not in names or 'asof/demo/case.json' not in names:
            raise ContractError('Packaged demo fixtures missing')
        if any(n.startswith(('data/','runs/','tests/')) for n in names):
            raise ContractError('Non-runtime payload in wheel')
    environment = directory/'wheel-environment'
    subprocess.run(['uv','venv','--offline','--python',sys.executable,str(environment)],check=True,capture_output=True)
    python = environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    subprocess.run(['uv','pip','install','--offline','--no-index','--python',str(python),'--no-deps',str(wheel)],check=True,capture_output=True)
    run = directory/'wheel-demo'
    subprocess.run([str(python),'-I','-m','asof','demo','--output',str(run)],cwd=directory,check=True,capture_output=True)
    subprocess.run([str(python),'-I','-m','asof','verify','--run-dir',str(run)],cwd=directory,check=True,capture_output=True)
    return {'wheel':wheel.name,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),
            'build_constraints_sha256':hashlib.sha256(constraints.read_bytes()).hexdigest(),
            'package_network_policy':'offline','dependency_free_demo':'passed'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('core','full'),default='full')
    parser.add_argument('--report',type=Path)
    parser.add_argument('--package',action='store_true')
    parser.add_argument('--failfast',action='store_true',help='Stop failed test execution after recording its first traceback')
    args = parser.parse_args(argv)
    # Reject stale destinations before imports, discovery or expensive checks.
    # Atomic final publication still rejects a competing writer; this preflight
    # is not a cross-process reservation or hard-kill recovery guarantee.
    if args.report and (args.report.exists() or args.report.is_symlink()):
        raise FileExistsError(args.report)
    started = time.monotonic()
    report = {'schema_version':1,'mode':args.mode,'status':'running','stage':'prerequisites'}
    exit_code = 1
    try:
        if args.mode=='full':
            import pyarrow
            if pyarrow.__version__!='21.0.0' or not shutil.which('pwsh'):
                raise ContractError('Full validation requires pyarrow 21.0.0 and PowerShell 7')
        report['stage'] = 'structural'
        report['structural'] = structural_checks()
        report['stage'] = 'powershell_syntax'
        report['powershell_syntax'] = powershell_check()
        report['stage'] = 'tests'
        suite = unittest.defaultTestLoader.discover(str(ROOT/'tests'),top_level_dir=str(ROOT))
        result = unittest.TextTestRunner(verbosity=2, failfast=args.failfast, resultclass=LiveErrorResult).run(suite)
        report['tests']={'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
                         'skipped':[{'test':t.id(),'reason':reason} for t,reason in result.skipped]}
        success = successful_tests(result,args.mode)
        with tempfile.TemporaryDirectory(prefix='asof-validation-') as temporary:
            directory=Path(temporary)
            previous=sys.argv
            report['stage'] = 'required_probes'
            try:
                sys.argv=['probe_framework','--output',str(directory/'probes.json')]
                report['required_probes_exit_code']=probe_main()
            finally:
                sys.argv=previous
            success = success and report['required_probes_exit_code']==0
            if args.package:
                report['stage'] = 'packaging'
                report['packaging']=package_check(directory)
        report.update(status='passed' if success else 'failed',stage='complete')
        exit_code = 0 if success else 1
    except BaseException as error:
        report.update(status='interrupted' if isinstance(error, KeyboardInterrupt) else 'failed',
                      error={'type':type(error).__name__,'message':str(error)})
        exit_code = 130 if isinstance(error, KeyboardInterrupt) else 1
        traceback.print_exc()
    report['elapsed_seconds'] = time.monotonic()-started
    print(json.dumps(report,indent=2))
    if args.report:
        write_new_json(args.report,report)
    return exit_code


if __name__=='__main__':
    raise SystemExit(main())
