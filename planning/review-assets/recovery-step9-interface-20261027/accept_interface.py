"""Accept the pure interface only after complete retained engineering checks."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CACHE=ROOT/'data/cache/recovery-step9-interface-validation-20261027'


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def pin(path):
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)


full,code=load(CACHE/'full-validation.json'),load(CACHE/'code-validation.json')
assert full['status']==code['status']=='passed'
assert full['tests']==dict(run=1681,failures=0,errors=0,skipped=[])
assert full['required_probes_exit_code']==0 and code['unchanged_code'] and code['protected_unchanged']
assert len(code['source_pins'])==316 and all(sha(ROOT/n)==h for n,h in code['source_pins'].items())
assert all(sha(ROOT/n)==h for n,h in code['protected_hashes'].items())  # Hash only.
oracle=load(HERE/'SCHEMA-QUALIFICATION-v3.json')
assert oracle['status']=='passed' and oracle['cases']==105 and oracle['powershell_version']=='7.6.5'
assert oracle['interface_module_sha256']==sha(ROOT/'src/asof/study/interpretation_interface.py')
assert oracle['oracle_helper_sha256']==sha(HERE/'qualify_schema_v3.py')
assert oracle['oracle_script_sha256']==sha(HERE/'schema_oracle.ps1')
assert len(oracle['differences'])==1 and oracle['differences'][0]['id']=='duplicate_claim_texts'
assert oracle['differences'][0]['expected_schema_exception']
assert oracle['model_calls']==oracle['provider_spend_usd']==oracle['new_downloads']==0
dependencies=load(HERE/'ORACLE-DEPENDENCIES.json')
assert dependencies['powershell_version']=='7.6.5' and dependencies['model_calls']==0
assert any(row['name']=='JsonSchema.Net' for row in dependencies['assemblies'])
assert all(sha(Path(row['path']))==row['sha256'] for row in dependencies['assemblies'])
frozen=load(HERE/'FROZEN-VERIFIER-CHECKS.json')
assert frozen['status']=='passed_all_seven_matching_installed_verifiers' and len(frozen['records'])==7
for row in frozen['records']:
    assert row['exit_code']==row['version_check_exit_code']==0 and sha(Path(row['report']))==row['report_sha256']
installed_path=ROOT/'data/cache/r09-interface-installed-20261027/guarded-installed-verification.json'
installed=load(installed_path)
assert installed['status']=='passed' and len(installed['results'])==7 and installed['isolated_mode']
assert all(row['status']=='passed' for row in installed['results'])
assert len(installed['installed_interpretation_interface'])==12
assert all(row['states_checked']==3 for row in installed['installed_interpretation_interface'])
for key in ('original_root_access_attempts','archived_execution_attempts','repository_tools_import_attempts','network_or_child_attempts'):
    assert installed[key]==[]
wheel=ROOT/'data/cache/recovery-step9-interface-wheel-20261027/dist/asof_target_agents-0.3.8-py3-none-any.whl'
with ZipFile(wheel) as archive:
    members={n for n in archive.namelist() if n.startswith('asof/') and n.endswith(('.py','.json'))}
    expected={p.relative_to(ROOT/'src').as_posix() for p in (ROOT/'src/asof').rglob('*')
              if p.is_file() and p.suffix in ('.py','.json') and '__pycache__' not in p.parts}
    assert members==expected and all(archive.read(n)==(ROOT/'src'/n).read_bytes() for n in members)
preserved=ROOT/'data/reference/recovery-r09-interface-verifier-038-20261027'
preserved.mkdir(exist_ok=False)
for path in (wheel,ROOT/'src/asof/archive/semantic_dependencies.json',ROOT/'src/asof/__init__.py'):
    with (preserved/path.name).open('xb') as stream:
        stream.write(path.read_bytes())
reports=[installed_path]
for name in ('full-validation.json','code-validation.json'):
    with (HERE/name).open('xb') as stream:
        stream.write((CACHE/name).read_bytes())
    reports.append(HERE/name)
reports += [HERE/name for name in ('CONTRACT.md','compatibility-profile-review.md',
    'FOCUSED-CODEC-FINAL.log','DEVELOPMENT-FINDINGS.md','SCHEMA-QUALIFICATION-v3.json','ORACLE-DEPENDENCIES.json',
    'FROZEN-VERIFIER-CHECKS.json','NEXT-ADAPTER-DESIGN.md')]
reports += [Path(row['report']) for row in frozen['records']]
acceptance=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),version='0.3.8',
    status='accepted_pure_original_quote_interface_engineering_only',interface='source-quote-interpretation-v2',
    full_tests=full['tests'],new_regression_tests=21,focused_codec_tests=33,
    source_pins_rechecked=316,protected_hashes_only=2,installed_legacy_families=7,
    installed_interface_preparations=12,installed_states_per_preparation=3,
    matching_frozen_verifiers=7,schema_oracle_cases=105,schema_oracle='PowerShell7.6.5 Test-Json / JsonSchema.NET',
    schema_post_validation_difference='Cross-claim unique texts intentionally checked only after generation',
    native_grammar_conformance='unverified',new_independent_peer_review=False,model_adapter_implemented=False,
    model_calls=0,provider_spend_usd=0,new_downloads=0,scientific_validation='not_established',
    human_reviews='pending',entire_R09_complete=False,native_R07_stop_unchanged=True,
    remaining=['Concrete model-backed adapter and source/history/capacity integration',
        'Pinned native schema-to-grammar conformance', 'Separately declared finite native experiment',
        'Independent source references, fresh-frame/source sufficiency and R10-R16 gates'],
    wheel=pin(wheel),preserved_wheel=pin(preserved/wheel.name),evidence=[pin(path) for path in reports])
with (HERE/'acceptance.json').open('x',encoding='utf-8') as stream:
    json.dump(acceptance,stream,indent=2)
print(json.dumps(dict(status=acceptance['status'],tests=full['tests']['run'],acceptance_sha256=sha(HERE/'acceptance.json'))))
