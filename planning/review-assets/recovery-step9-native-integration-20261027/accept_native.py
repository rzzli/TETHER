"""Accept native integration mechanics only after all frozen retained checks pass."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CACHE=ROOT/'data/cache/recovery-step9-native-validation-20261028'


def load(path):return json.loads(Path(path).read_bytes())


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def pin(path):
    path=Path(path)
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)


full,code=load(CACHE/'full-validation.json'),load(CACHE/'code-validation.json')
assert full['status']==code['status']=='passed'
assert full['tests']==dict(run=1724,failures=0,errors=0,skipped=[])
assert full['required_probes_exit_code']==0 and full['packaging']['dependency_free_demo']=='passed'
assert code['unchanged_code'] and code['protected_unchanged'] and len(code['source_pins'])==324
assert all(sha(ROOT/n)==h for n,h in code['source_pins'].items())
assert len(code['protected_hashes'])==2 and all(sha(ROOT/n)==h for n,h in code['protected_hashes'].items())  # Hash only.
for name,count,seconds in [('FOCUSED-COMPONENT-FINAL.log',53,'12.933'),('INTEGRATION-FAILURES-FINAL.log',29,'257.991'),
        ('LINEAGE-NATIVE-FOCUSED.log',1,'70.535'),('RECORDED-REGRESSIONS.log',8,'92.139')]:
    text=(HERE/name).read_text(encoding='utf-8')
    assert f'Ran {count} test' in text and seconds in text and text.rstrip().endswith('OK')
frozen=load(HERE/'FROZEN-VERIFIER-CHECKS.json')
assert frozen['status']=='passed_all_eight_matching_installed_verifiers' and len(frozen['records'])==8
for row in frozen['records']:
    assert row['exit_code']==row['version_check_exit_code']==0 and sha(row['report'])==row['report_sha256']
environments=load(HERE/'WHEEL-ENVIRONMENTS.json')
assert environments['status']=='offline_wheel_and_two_installed_environments_verified'
assert environments['default_runtime_dependencies']==[] and environments['optional_pyarrow_version']=='21.0.0'
wheel=Path(environments['wheel']);assert sha(wheel)==environments['wheel_sha256']
with ZipFile(wheel) as archive:
    members={n for n in archive.namelist() if n.startswith('asof/') and n.endswith(('.py','.json'))}
    expected={p.relative_to(ROOT/'src').as_posix() for p in (ROOT/'src/asof').rglob('*')
        if p.is_file() and p.suffix in ('.py','.json') and '__pycache__' not in p.parts}
    assert members==expected and all(archive.read(n)==(ROOT/'src'/n).read_bytes() for n in members)
qualified=load(HERE/'SIMULATION-QUALIFICATION.json')
protocol=load(HERE/'SIMULATION-PROTOCOL.json')
assert qualified['status']=='qualified_real_inputs_simulated_native_case' and qualified['execution_seconds']<300
assert qualified['protocol_sha256']==sha(HERE/'SIMULATION-PROTOCOL.json')
assert protocol['helper_sha256']==sha(HERE/'qualify_simulated.py')
assert qualified['actual_model_calls']==qualified['actual_native_servers']==qualified['actual_network_requests']==0
assert qualified['tokenizer_children']==qualified['simulated_posts']==6 and qualified['simulated_servers']==1
assert not qualified['guards']['network'] and not qualified['guards']['unapproved']
assert qualified['result']['input_reserved']<=32000 and qualified['result']['output_reserved']==6144
assert qualified['result']['simulated_transport_usage']==dict(input_tokens=384,output_tokens=384,cost_usd=0.0)
default_path=ROOT/'data/cache/r09-native-installed-20261028/guarded-installed-verification.json'
default=load(default_path)
assert default['status']=='passed' and default['isolated_mode'] and len(default['results'])==7
assert all(row['status']=='passed' for row in default['results'])
assert len(default['installed_interpretation_interface'])==12
assert default['installed_native_wrapper']['positive_cases']==1 and len(default['installed_native_wrapper']['negative_cases'])==3
for key in ('original_root_access_attempts','archived_execution_attempts','repository_tools_import_attempts','network_or_child_attempts'):
    assert default[key]==[]
installed_reports=[]
for name,status in [('INSTALLED-REPLAY.json','installed_native_simulation_replay_verified'),
        ('INSTALLED-RELOCATION.json','installed_native_simulation_relocation_verified')]:
    path=HERE/name;record=load(path)
    assert record['status']==status and record['result']==qualified['result'] and record['isolated']
    assert not any(record['guards'].values()) and record['model_calls']==record['tokenizer_calls']==record['network_calls']==0
    assert record['original_source_input_count']==27 and record['approved_model_inputs']==36
    assert not record['archived_code_executed'] and not record['fixture_callbacks_imported']
    installed_reports.append(path)
preserved=ROOT/'data/reference/recovery-r09-native-verifier-039-20261028'
preserved.mkdir(exist_ok=False)
for path in (wheel,ROOT/'src/asof/archive/semantic_dependencies.json',ROOT/'src/asof/__init__.py'):
    with (preserved/path.name).open('xb') as stream:stream.write(path.read_bytes())
reports=[default_path,*installed_reports]
for name in ('full-validation.json','code-validation.json'):
    with (HERE/name).open('xb') as stream:stream.write((CACHE/name).read_bytes())
    reports.append(HERE/name)
reports += [HERE/name for name in ('CONTRACT.md','compatibility-profile-review.md','DEVELOPMENT-FINDINGS.md',
    'FOCUSED-COMPONENT-FINAL.log','INTEGRATION-FAILURES-FINAL.log','LINEAGE-NATIVE-FOCUSED.log',
    'RECORDED-REGRESSIONS.log','SIMULATION-PROTOCOL.json','SIMULATION-QUALIFICATION.json',
    'WHEEL-ENVIRONMENTS.json','NATIVE-MODEL-MIRROR.json','FROZEN-VERIFIER-CHECKS.json',
    'qualify_simulated.py','verify_native_installed.py','verify_default_installed.py',
    'build_installed.py','CLOSEOUT.md','NEXT-GRAMMAR-GATE.md')]
reports += [Path(row['report']) for row in frozen['records']]
acceptance=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),version='0.3.9',
    status='accepted_native_adapter_controller_integration_engineering_only',interface='source-quote-interpretation-v2',
    full_tests=full['tests'],new_regression_tests=43,source_pins_rechecked=324,protected_hashes_only=2,
    installed_legacy_families=7,matching_frozen_verifiers=8,installed_interface_preparations=12,
    actual_model_calls=0,actual_native_servers=0,actual_network_requests=0,tokenizer_children=6,
    simulated_native_calls=6,simulated_native_servers=1,pure_results=2,
    source_inclusive_simulation_result=qualified['result'],
    native_grammar_conformance='unverified',actual_native_resource_feasibility='unverified',
    new_independent_peer_review=False,model_adapter_implemented=True,controller_integration_implemented=True,
    provider_spend_usd=0,new_downloads=0,scientific_validation='not_established',human_reviews='pending',
    entire_R09_complete=False,native_R07_stop_unchanged=True,
    relocation_scope='Run bundle only; explicit original source/model inputs remain available',
    remaining=['Pinned native schema-to-grammar conformance','Separately declared finite native experiment',
        'Independent source references, fresh-frame/source sufficiency and R10-R16 gates'],
    wheel=pin(wheel),preserved_wheel=pin(preserved/wheel.name),evidence=[pin(path) for path in reports])
with (HERE/'acceptance.json').open('x',encoding='utf-8') as stream:json.dump(acceptance,stream,indent=2)
print(json.dumps(dict(status=acceptance['status'],tests=full['tests']['run'],acceptance_sha256=sha(HERE/'acceptance.json'))))
