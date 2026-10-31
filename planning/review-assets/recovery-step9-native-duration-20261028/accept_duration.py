"""Accept the separate timing correction only after all retained checks pass."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CACHE=ROOT/'data/cache/recovery-step9-duration-validation-20261028'


def load(path):return json.loads(Path(path).read_bytes())


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def pin(path):
    path=Path(path)
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)


full,code=load(CACHE/'full-validation.json'),load(CACHE/'code-validation.json')
assert full['status']==code['status']=='passed'
assert full['tests']==dict(run=1737,failures=0,errors=0,skipped=[])
assert full['required_probes_exit_code']==0 and full['packaging']['dependency_free_demo']=='passed'
assert code['unchanged_code'] and code['protected_unchanged'] and len(code['source_pins'])==324
assert all(sha(ROOT/n)==h for n,h in code['source_pins'].items())
assert len(code['protected_hashes'])==2 and all(sha(ROOT/n)==h for n,h in code['protected_hashes'].items())  # Hash only.
old_phase=HERE.parent/'recovery-step9-native-integration-20261027'
assert sha(old_phase/'acceptance.json')=='8a77c2eaba83dece672330b72c518a8f16f1417c9a14498b54686ac990b7815b'
old_acceptance=load(old_phase/'acceptance.json')
assert all(sha(ROOT/r['path'])==r['sha256'] for r in old_acceptance['evidence'])
assert sha(ROOT/old_acceptance['preserved_wheel']['path'])==old_acceptance['wheel']['sha256']
for name,count,seconds in [('DURATION-COMPONENT-FOCUSED.log',25,'19.451'),
        ('NATIVE-CONTROLLER-FOCUSED.log',75,'289.852'),('RECORDED-REGRESSIONS.log',8,'97.275')]:
    text=(HERE/name).read_text(encoding='utf-8')
    assert f'Ran {count} test' in text and seconds in text and text.rstrip().endswith('OK')
before=(HERE/'DURATION-REGRESSIONS-BEFORE.log').read_text(encoding='utf-8')
assert 'Ran 7 tests' in before and 'FAILED (failures=17)' in before
frozen=load(HERE/'FROZEN-VERIFIER-CHECKS.json')
assert frozen['status']=='passed_all_nine_matching_installed_verifiers' and len(frozen['records'])==9
for row in frozen['records']:
    assert row['exit_code']==row['version_check_exit_code']==0 and sha(row['report'])==row['report_sha256']
envs=load(HERE/'WHEEL-ENVIRONMENTS.json');wheel=Path(envs['wheel'])
assert envs['status']=='offline_wheel_and_two_installed_environments_verified'
assert envs['default_runtime_dependencies']==[] and envs['optional_pyarrow_version']=='21.0.0'
assert sha(wheel)==envs['wheel_sha256']
with ZipFile(wheel) as archive:
    expected={p.relative_to(ROOT/'src').as_posix() for p in (ROOT/'src/asof').rglob('*')
        if p.is_file() and p.suffix in ('.py','.json') and '__pycache__' not in p.parts}
    members={n for n in archive.namelist() if n.startswith('asof/') and n.endswith(('.py','.json'))}
    assert members==expected and all(archive.read(n)==(ROOT/'src'/n).read_bytes() for n in members)
qualified=load(HERE/'SIMULATION-QUALIFICATION.json');protocol=load(HERE/'SIMULATION-PROTOCOL.json')
assert qualified['status']=='qualified_real_inputs_simulated_native_case' and qualified['execution_seconds']<300
assert qualified['protocol_sha256']==sha(HERE/'SIMULATION-PROTOCOL.json') and protocol['helper_sha256']==sha(HERE/'qualify_simulated.py')
assert qualified['actual_model_calls']==qualified['actual_native_servers']==qualified['actual_network_requests']==0
assert qualified['tokenizer_children']==qualified['simulated_posts']==6 and qualified['simulated_servers']==1
assert not qualified['guards']['network'] and not qualified['guards']['unapproved']
assert len(qualified['duration_checks'])==6
for row in qualified['duration_checks']:
    assert 0<=row['native_elapsed_seconds']<row['allocated_seconds']
    assert row['native_elapsed_seconds']<=row['child_report_elapsed_seconds']+1e-6
default_path=ROOT/'data/cache/r09-duration-installed-20261028/guarded-installed-verification.json'
default=load(default_path)
assert default['status']=='passed' and default['isolated_mode'] and len(default['results'])==7
assert all(row['status']=='passed' for row in default['results'])
assert len(default['installed_interpretation_interface'])==12
checks=default['installed_native_wrapper']['duration_cases']
assert len(checks)==8 and all(row['accepted']==row['expected'] for row in checks)
for key in ('original_root_access_attempts','archived_execution_attempts','repository_tools_import_attempts','network_or_child_attempts'):
    assert default[key]==[]
installed_paths=[]
for name,status in [('INSTALLED-REPLAY.json','installed_native_simulation_replay_verified'),
        ('INSTALLED-RELOCATION.json','installed_native_simulation_relocation_verified')]:
    path=HERE/name;record=load(path)
    assert record['status']==status and record['result']==qualified['result'] and record['isolated']
    assert not any(record['guards'].values()) and record['model_calls']==record['tokenizer_calls']==record['network_calls']==0
    assert record['original_source_input_count']==27 and record['approved_model_inputs']==36
    installed_paths.append(path)
preserved=ROOT/'data/reference/recovery-r09-duration-verifier-0310-20261028'
preserved.mkdir(exist_ok=False)
for path in (wheel,ROOT/'src/asof/archive/semantic_dependencies.json',ROOT/'src/asof/__init__.py'):
    with (preserved/path.name).open('xb') as stream:stream.write(path.read_bytes())
reports=[default_path,*installed_paths]
for name in ('full-validation.json','code-validation.json'):
    with (HERE/name).open('xb') as stream:stream.write((CACHE/name).read_bytes())
    reports.append(HERE/name)
reports += [HERE/name for name in ('CONTRACT.md','compatibility-profile-review.md','DEVELOPMENT-FINDINGS.md',
    'DURATION-REGRESSIONS-BEFORE.log','DURATION-COMPONENT-FOCUSED.log','NATIVE-CONTROLLER-FOCUSED.log',
    'RECORDED-REGRESSIONS.log','TARGETED-COMPLETION.json','VERSION-BOUNDARY.json',
    'RESOURCE-RISK-NOTE.md','STAGE-TIMING-AUDIT.json','stage_timing_audit.py',
    'SIMULATION-PROTOCOL.json','SIMULATION-QUALIFICATION.json','WHEEL-ENVIRONMENTS.json',
    'FROZEN-VERIFIER-CHECKS.json','qualify_simulated.py','verify_native_installed.py','verify_default_installed.py','CLOSEOUT.md')]
reports += [Path(row['report']) for row in frozen['records']]
acceptance=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),version='0.3.10',
    status='accepted_native_duration_consistency_engineering_only',full_tests=full['tests'],new_regression_tests=13,
    source_pins_rechecked=324,protected_hashes_only=2,installed_legacy_families=7,matching_frozen_verifiers=9,
    installed_duration_cases=8,real_input_duration_checks=6,actual_model_calls=0,actual_native_servers=0,
    source_inclusive_simulation_result=qualified['result'],provider_spend_usd=0,new_model_downloads=0,
    outer_execution_seconds=qualified['execution_seconds'],case_budget_seconds=300,
    observed_time_margin_seconds=300-qualified['execution_seconds'],actual_native_case_feasibility='not_established',
    grammar_conformance='unverified',scientific_validation='not_established',human_reviews='pending',
    entire_R09_complete=False,native_R07_stop_unchanged=True,old_039_artifacts_modified=False,
    wheel=pin(wheel),preserved_wheel=pin(preserved/wheel.name),evidence=[pin(path) for path in reports],
    remaining=['Typed actual-DLL ABI smoke and native converter qualification under frozen protocol',
        'Native document/EOS or vocabulary/EOG qualification if conversion eligible',
        'Fresh-case/source sufficiency, independent human references and R10-R16 scientific gates'])
with (HERE/'acceptance.json').open('x',encoding='utf-8') as stream:json.dump(acceptance,stream,indent=2)
print(json.dumps(dict(status=acceptance['status'],tests=full['tests']['run'],acceptance_sha256=sha(HERE/'acceptance.json'))))
