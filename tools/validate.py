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
from tether_engine.maintenance import validate_catalog, write_new_json
from tether_engine.serde import ContractError, read_json
from tools.review.probe_framework import main as probe_main

EXPECTED_CORE_SKIPS = {'install the ingest extra for adapter tests',
    'install the ingest extra for source-audit tests', 'PowerShell 7 required for utility integration',
    'native held-handle test requires Windows'}


def legacy_compatibility_scope():
    """Keep historical integration coverage visible outside the current-policy gate."""
    from tests.test_refinement_recovery import legacy_test_inventory
    ids = legacy_test_inventory()
    return {'status': 'not_executed_by_current_policy_gate', 'tests': len(ids), 'test_ids': ids,
            'required_engine_version': '0.4.0', 'required_wrapper_version': '0.6.0',
            'current_policy_qualified': False,
            'reason': 'Frozen SC04 producer has no registered derivation; current policy must reject it.',
            'validation': 'Run original methods separately with matching source checkpoint and runtime; retain that result.'}


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

# Working records stay local. Public validation must not require or publish them.
PRIVATE_ROOTS = frozenset({
    'memory', 'planning', 'reports', 'paper', 'research_notes', 'tmp', 'temp',
    'cache', 'results', 'scratch', 'logs',
})
PRIVATE_COMPONENTS = frozenset({
    '.venv', '__pycache__', 'build', 'dist', 'runs', 'private', 'cache', 'results',
    'tmp', 'temp', 'scratch', 'logs', 'credentials', 'secrets', 'signed_urls',
    'memory', 'planning', 'reports', 'paper', 'research_notes',
})
PUBLIC_DOC_FILES = frozenset({
    'docs/ARCHIVE.md', 'docs/FRAMEWORK.md', 'docs/MAINTENANCE.md', 'docs/PORTABLE-BUNDLE.md', 'docs/RESULTS.md',
    'docs/TETHER-CATALOG-POLICY.md', 'docs/TETHER-VERIFICATION-SCOPE.md',
})
PUBLIC_DATA_FILES = frozenset({
    'data/.gitignore', 'data/README.md', 'data/catalog/README.md',
    'data/catalog/sources.json', 'data/catalog/policy-v2.json',
})
PRIVATE_CONFIG_SUFFIXES = frozenset({
    '.json', '.jsonl', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
    '.txt', '.csv', '.tsv', '.log',
})
# Construct the retired identifier without reintroducing it into public files.
LEGACY_PROJECT_TOKEN = bytes((97, 115, 111, 102))
PRIVATE_FILES = frozenset({
    'todo.md', 'memory.md', 'data/data_plan.md',
    'packages/tether/migration-validation.json',
    'docs/tether-namespace-migration.md', 'docs/tether-namespace-validation.json',
    'docs/expert review coordinator guide 2026-10-26.md',
    'docs/independent project review 2026-10-26.md',
    'docs/opus_20261026t050236z_review.md',
})


def validate_public_path(name):
    """Reject internal records and generated payloads before opening their bytes."""
    if not name or '\\' in name or name.startswith('/') or '..' in name.split('/'):
        raise ContractError('Noncanonical public repository path: '+name)
    folded = name.casefold()
    parts = folded.split('/')
    if LEGACY_PROJECT_TOKEN in folded.encode('utf-8'):
        raise ContractError('Legacy project identifier in public path: '+name)
    if parts[0] in PRIVATE_ROOTS or folded in PRIVATE_FILES:
        raise ContractError('Internal working record entered public tracking scope: '+name)
    if any(key in parts for key in PRIVATE_COMPONENTS):
        raise ContractError('Private or generated file entered tracking scope: '+name)
    if parts[0] == 'docs' and name not in PUBLIC_DOC_FILES:
        raise ContractError('Unapproved documentation entered tracking scope: '+name)
    if parts[0] == 'data' and name not in PUBLIC_DATA_FILES:
        raise ContractError('Unapproved data artifact entered tracking scope: '+name)
    leaf = parts[-1]
    if leaf in {'memory.md', 'todo.md'}:
        raise ContractError('Internal working record entered public tracking scope: '+name)
    if leaf != '.env.example' and (leaf == '.env' or leaf.startswith('.env.')):
        raise ContractError('Local environment configuration entered tracking scope: '+name)
    if Path(leaf).suffix in PRIVATE_CONFIG_SUFFIXES and any(
            token in leaf for token in ('credentials', 'secrets', 'signed_urls')):
        raise ContractError('Credential artifact entered tracking scope: '+name)


def validate_public_bytes(name, raw):
    """Scan every public payload, including non-Python fixtures and documents."""
    if LEGACY_PROJECT_TOKEN in raw.lower():
        raise ContractError('Legacy project identifier in public content: '+name)


def validate_public_catalog_template(catalog):
    """Keep the published source inventory separate from local acquisition state."""
    if catalog.get('catalog_mode') != 'requirements_template' or not isinstance(
            catalog.get('status_scope'), str) or not catalog['status_scope'].strip():
        raise ContractError('Public catalog must declare its requirements-template status scope')
    for row in catalog['datasets']:
        if (row.get('collection_status') != 'planned' or row.get('parse_status') != 'not_run'
                or row.get('validation_status') != 'not_run'):
            raise ContractError('Public catalog contains local acquisition status: '+row['dataset_id'])
        proof = row.get('verification', {})
        if (proof.get('level') != 'not_checked' or proof.get('checked_at') is not None
                or proof.get('evidence') != []):
            raise ContractError('Public catalog contains local verification evidence: '+row['dataset_id'])
    private_keys = {'acquisition_snapshot', 'last_maintenance_update', 'metadata_artifact_path',
                    'workspace_path', 'state_path'}
    # The preceding-letter guard avoids confusing the end of https:// with a
    # Windows drive. Provider URLs remain valid public source references.
    local_drive = re.compile(r'(?i)(?<![a-z0-9])[a-z]:[\\/]')
    local_unix = re.compile(r'(?<![\w:/])/(?:home|Users|tmp|var|mnt|media|workspace|'
                            r'workspaces|projects|private|Volumes|scratch)(?:/|$)')
    def check(value):
        if isinstance(value, dict):
            if any(key.casefold() in private_keys for key in value):
                raise ContractError('Public catalog contains local working-state metadata')
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)
        elif isinstance(value, str) and (local_drive.search(value) or local_unix.search(value)
                                        or value.startswith(('/', '\\\\'))):
            raise ContractError('Public catalog contains an absolute local path')
    check(catalog)


def validate_public_policy_template(policy):
    """A published template cannot grant access to deployment-specific artifacts."""
    if policy['artifacts'] or policy['uses']:
        raise ContractError('Public catalog policy must have zero artifact and use grants')


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
        validate_public_path(name)
        raw = (ROOT/name).read_bytes()
        validate_public_bytes(name, raw)
        if name.endswith('.py'):
            if validate_python_artifact(name, raw) == 'archived_invalid_source':
                archived_invalid.append(name)
    for name in ('runs/probe.json','data/derived/probe.json','data/raw/probe.parquet',
                 'data/manifests/private/probe.json','.venv/probe','.env','data/benchmark/labels/probe.json',
                 'memory/probe.md','planning/probe.md','reports/probe.json','paper/probe.pdf',
                 'research_notes/probe.md','tmp/probe.json','TODO.md','results/probe.json',
                 'experiments/probe/cache/receipt.json','experiments/probe/private/receipt.json','tools/tmp/probe.json',
                 'data/catalog/acquisition-report.json','docs/session-notes.md',
                 'config/cloud-credentials.json','config/secrets.yaml','tools/signed_urls.txt',
                 'experiments/memory/session.md','packages/tether/planning/notes.md',
                 'experiments/example/reports/run.json','experiments/paper/results.json',
                 'packages/research_notes/session.md','experiments/TODO.md',
                 'packages/tether/memory.md'):
        if subprocess.run(['git','check-ignore','-q',name],cwd=ROOT).returncode:
            raise ContractError('Required ignore missing: '+name)
    catalog = read_json(ROOT/'data/catalog/sources.json')
    validate_catalog(catalog)
    validate_public_catalog_template(catalog)
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
        validate_public_policy_template(policy)
        validate_source_catalog(policy, (ROOT/'data/catalog/sources.json').read_bytes())
    # Catalog records and the optional source-bound policy are the public input
    # interfaces. A private planning index or historical pilot registry is not a
    # prerequisite for installing or validating a clean source checkout.
    return {'tracked_scope_files':len(files),'providers':len(catalog['providers']),'datasets':len(catalog['datasets']),
            'preserved_invalid_python_archives':archived_invalid}


def powershell_check():
    if not shutil.which('pwsh'):
        return False
    code = "$ErrorActionPreference='Stop'; Get-ChildItem -LiteralPath tools -Recurse -Filter *.ps1 | ForEach-Object { $t=$null; $e=$null; [System.Management.Automation.Language.Parser]::ParseFile($_.FullName,[ref]$t,[ref]$e) | Out-Null; if($e.Count){throw ('Syntax error: '+$_.FullName)} }"
    subprocess.run(['pwsh','-NoProfile','-Command',code],cwd=ROOT,check=True)
    return True


def validate_engine_wheel(wheel):
    """Reject stale build payloads and every namespace outside this distribution."""
    from tether_engine import __version__
    metadata_root = 'tether_target_engine-' + __version__ + '.dist-info'
    with zipfile.ZipFile(wheel) as archive:
        names = [info.orig_filename for info in archive.infolist()]
        if len(names) != len(set(names)):
            raise ContractError('Duplicate wheel member')
        for name in names:
            parts = name.rstrip('/').split('/')
            if (not parts or any(part in ('', '.', '..') or ':' in part for part in parts)
                    or '\\' in name or '\x00' in name or parts[0] not in ('tether_engine', metadata_root)
                    or len(parts) < 2):
                raise ContractError('Unexpected wheel namespace/member: '+name)
        required = {'tether_engine/demo/v2/case.json', 'tether_engine/demo/case.json',
                    'tether_engine/schemas/portable-bundle-v1.json',
                    metadata_root+'/METADATA', metadata_root+'/WHEEL', metadata_root+'/RECORD'}
        if not required.issubset(names):
            raise ContractError('Packaged runtime/demo metadata missing')
    return {'members':len(names), 'namespace':'tether_engine', 'metadata_root':metadata_root}


def package_check(directory):
    constraints = ROOT/'tools/build-constraints.txt'
    subprocess.run(['uv','build','--offline','--build-constraints',str(constraints),
                    '--python',sys.executable,'--wheel','--out-dir',str(directory/'dist')],cwd=ROOT,check=True,capture_output=True)
    wheel = next((directory/'dist').glob('*.whl'))
    inventory = validate_engine_wheel(wheel)
    environment = directory/'wheel-environment'
    subprocess.run(['uv','venv','--offline','--python',sys.executable,str(environment)],check=True,capture_output=True)
    python = environment/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    subprocess.run(['uv','pip','install','--offline','--no-index','--python',str(python),'--no-deps',str(wheel)],check=True,capture_output=True)
    run = directory/'wheel-demo'
    subprocess.run([str(python),'-I','-m','tether_engine','demo','--output',str(run)],cwd=directory,check=True,capture_output=True)
    subprocess.run([str(python),'-I','-m','tether_engine','verify','--run-dir',str(run)],cwd=directory,check=True,capture_output=True)
    return {'wheel':wheel.name,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),
            'wheel_inventory':inventory,
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
        report['legacy_compatibility_group'] = legacy_compatibility_scope()
        result = unittest.TextTestRunner(verbosity=2, failfast=args.failfast, resultclass=LiveErrorResult).run(suite)
        report['tests']={'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
                         'skipped':[{'test':t.id(),'reason':reason} for t,reason in result.skipped]}
        success = successful_tests(result,args.mode)
        with tempfile.TemporaryDirectory(prefix='tether-validation-') as temporary:
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
