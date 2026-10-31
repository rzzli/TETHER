"""Accept the source-connected recorded mechanism only after retained validation."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CACHE=ROOT/'data/cache/recovery-step9-collected-validation-20261027'


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def pin(path):
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)


full,code=load(CACHE/'full-validation.json'),load(CACHE/'code-validation.json')
assert full['status']==code['status']=='passed'
assert full['tests']==dict(run=1660,failures=0,errors=0,skipped=[])
assert full['required_probes_exit_code']==0 and code['unchanged_code'] and code['protected_unchanged']
assert len(code['source_pins'])==314 and all(sha(ROOT/n)==h for n,h in code['source_pins'].items())
assert all(sha(ROOT/n)==h for n,h in code['protected_hashes'].items())  # Hash only.
qualified=load(HERE/'QUALIFICATION.json')
assert qualified['status']=='qualified_collected_source_recorded_four_arm'
assert qualified['tokenizer_children']==6 and qualified['replay_children']==0
assert qualified['protocol_sha256']==sha(HERE/'QUALIFICATION-PROTOCOL.json')
assert qualified['model_calls']==qualified['provider_spend_usd']==qualified['new_downloads']==0
assert qualified['source_pins_unchanged']==314 and not any(qualified['guards'].values())
result=qualified['result']
assert result['track']=='authority_bound_collected_source_four_arm_recorded'
assert result['recorded_calls']==6 and result['pure_invocations']==2 and result['actual_model_calls']==0
assert result['sealed_elapsed_seconds']<300 and result['input_reserved']<=32000 and result['output_reserved']==6144
assert result['fixture_declared_usage']==dict(input_tokens=384,output_tokens=384,cost_usd=0.0)
coverage=qualified['coverage']
assert coverage['raw_qualified_candidates']==coverage['declared_candidates']==5 and coverage['selected_count']==1
assert coverage['parent_observations_available']==9 and coverage['missing_input_count']==65
frozen=load(HERE/'FROZEN-VERIFIER-CHECKS.json')
assert len(frozen['records'])==6 and frozen['status']=='passed_all_six_matching_installed_verifiers'
frozen_reports=[]
for row in frozen['records']:
    path=Path(row['report'])
    assert row['exit_code']==row['version_check_exit_code']==0 and sha(path)==row['report_sha256']
    report=load(path)
    assert report['status'].startswith('passed')
    for key,value in report.items():
        if key.endswith('attempts'):
            assert value==[] or (isinstance(value,dict) and all(v==[] for v in value.values())),(path,key,value)
        if key=='guards':
            assert not any(value.values()),(path,value)
    frozen_reports.append(path)
default_path=ROOT/'data/cache/r09-collected-default-installed-20261027/guarded-installed-verification.json'
default=load(default_path)
assert default['status']=='passed' and len(default['results'])==7 and default['isolated_mode']
assert all(row['status']=='passed' for row in default['results'])
for key in ('original_root_access_attempts','archived_execution_attempts','repository_tools_import_attempts','network_or_child_attempts'):
    assert default[key]==[]
installed=load(HERE/'installed-verification.json')
relocated=load(HERE/'relocation-verification.json')
assert installed['status']=='installed_collected_source_replay_verified'
assert relocated['status']=='installed_collected_source_relocation_verified'
for report in (installed,relocated):
    assert report['result']==result and not any(report['guards'].values())
    assert report['original_source_input_count']==27 and report['archived_code_executed'] is False
assert relocated['run_bundle_relocation_only'] and relocated['raw_inputs_restored'] is False
wheel=ROOT/'data/cache/recovery-step9-collected-wheel-20261027/dist/asof_target_agents-0.3.7-py3-none-any.whl'
with ZipFile(wheel) as archive:
    members={n for n in archive.namelist() if n.startswith('asof/') and n.endswith(('.py','.json'))}
    expected={p.relative_to(ROOT/'src').as_posix() for p in (ROOT/'src/asof').rglob('*')
              if p.is_file() and p.suffix in ('.py','.json') and '__pycache__' not in p.parts}
    assert members==expected and all(archive.read(n)==(ROOT/'src'/n).read_bytes() for n in members)
preserved=ROOT/'data/reference/recovery-r09-collected-verifier-037-20261027'
preserved.mkdir(exist_ok=False)
for path in (wheel,ROOT/'src/asof/archive/semantic_dependencies.json',ROOT/'src/asof/__init__.py'):
    with (preserved/path.name).open('xb') as stream:
        stream.write(path.read_bytes())
reports=[]
for name in ('full-validation.json','code-validation.json'):
    with (HERE/name).open('xb') as stream:
        stream.write((CACHE/name).read_bytes())
    reports.append(HERE/name)
reports += [default_path,*frozen_reports,*[HERE/name for name in ('CONTRACT.md','compatibility-profile-review.md',
    'FOCUSED-v2.log','QUALIFICATION-PROTOCOL.json','QUALIFICATION.json','FROZEN-VERIFIER-CHECKS.json',
    'installed-verification.json','relocation-verification.json','ARROW-INSTALL.json','HELPER-REVIEW.md','NEXT-GATE-AUDIT.md')]]
acceptance=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),version='0.3.7',
    status='accepted_collected_source_four_arm_recorded_engineering_only',full_tests=full['tests'],
    new_regression_tests=14,focused_regressions=26,new_independent_peer_review=False,
    source_pins_rechecked=314,protected_hashes_only=2,installed_legacy_families=7,matching_frozen_verifiers=6,
    original_source_inputs=27,case='exposed_IL6R_RA_inhibit_antibody',fresh_case=False,
    retrieval_policy='literal_case_overlap_then_id_v1',declared_candidates=5,selected_count=1,
    parent_observations_available=9,missing_input_count=65,arms=4,recorded_cells=6,pure_results=2,
    tokenizer_children=6,actual_model_calls=0,provider_spend_usd=0,features={},clinical_probability=None,
    input_reserved=result['input_reserved'],output_reserved=result['output_reserved'],
    execution_outer_seconds=qualified['execution_outer_seconds'],sealed_elapsed_seconds=result['sealed_elapsed_seconds'],
    replay_seconds=qualified['replay_seconds'],peak_parent_working_set_bytes=qualified['peak_parent_working_set_bytes'],
    retained_bundle_bytes=qualified['retained_bundle_bytes'],child_peak_memory_bytes=None,
    scientific_validation='not_established',human_reviews='pending',entire_R09_complete=False,
    native_R07_stop_unchanged=True,default_byte_policy_unchanged=True,run_bundle_relocation_only=True,
    raw_inputs_restored=False,source_report_stimuli='whole verbatim statements, evaluator-only fixtures',
    remaining=['Real retrieval and scientific source/question sufficiency',
        'Independent source-only references and domain-matched reviewers',
        'Separately versioned model-backed interpretation design and qualification',
        'R10-R16 scientific and conditional programme'],
    wheel=pin(wheel),preserved_wheel=pin(preserved/wheel.name),evidence=[pin(path) for path in reports])
with (HERE/'acceptance.json').open('x',encoding='utf-8') as stream:
    json.dump(acceptance,stream,indent=2)
print(json.dumps(dict(status=acceptance['status'],tests=full['tests']['run'],acceptance_sha256=sha(HERE/'acceptance.json'))))
