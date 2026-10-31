"""Accept only the verified bounded engineering slice, never all of R09 or science."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CACHE=ROOT/'data/cache/recovery-step9-four-arm-validation-20261026'


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def pin(path):
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)


full,code=load(CACHE/'full-validation.json'),load(CACHE/'code-validation.json')
assert full['status']==code['status']=='passed'
assert full['tests']==dict(run=1646,failures=0,errors=0,skipped=[])
assert full['required_probes_exit_code']==0 and code['unchanged_code'] and code['protected_unchanged']
assert all(sha(ROOT/n)==h for n,h in code['source_pins'].items())
assert all(sha(ROOT/n)==h for n,h in code['protected_hashes'].items())  # Hash only.
peer=load(HERE/'INDEPENDENT-ENGINEERING-REVIEW.json')
assert peer['peer_test_results']['capacity']['passed']==9
assert peer['peer_test_results']['composition']['passed']==4
assert all(sha(ROOT/p['path'])==p['sha256'] for p in peer['final_reviewed_snapshot'])
frozen=load(HERE/'FROZEN-VERIFIER-CHECKS.json')
assert len(frozen['records'])==5
for r in frozen['records']:
    assert r['exit_code']==r['version_check_exit_code']==0 and r['status'].startswith('passed')
    assert not any(r['guards'].values()) and sha(Path(r['report']))==r['report_pin']['sha256']
qualified=load(HERE/'QUALIFICATION.json')
assert qualified['status']=='passed' and qualified['tokenizer_children']==6
assert qualified['protocol_sha256']==sha(HERE/'QUALIFICATION-PROTOCOL-v2.json')
assert qualified['prior_failed_attempt_tokenizer_children']==2 and qualified['observed_E_file_count']==0
mirror=load(HERE/'MODEL-MIRROR.json')
assert mirror['status']=='verified_identical_local_mirror' and len(mirror['items'])==35
assert qualified['model_root']==mirror['target'] and not mirror['source_writes']
failed=load(HERE/'QUALIFICATION-FAILURE-CLOSEOUT-v1.json')
assert failed['prior_tokenizer_children']==2 and failed['whole_case_accepted'] is False
assert qualified['generation_calls']==qualified['server_startups']==qualified['provider_spend_usd']==0
assert qualified['replay_child_count']==0 and qualified['source_pins_unchanged']
assert qualified['all_original_payloads_identical'] and not qualified['denied_access'] and not qualified['network_attempts']
result=qualified['result']
assert result['recorded_calls']==6 and result['pure_invocations']==2
assert result['input_reserved']==14315 and result['output_reserved']==6144
assert result['actual_model_calls']==0 and result['sealed_elapsed_seconds']<300
installed_path=ROOT/'data/cache/r09-four-arm-installed-20261027/guarded-installed-verification.json'
installed=load(installed_path)
assert installed['status']=='passed' and len(installed['results'])==7
assert all(r['status']=='passed' for r in installed['results'])
assert installed['installed_authority_four_arm']==result
for key in ('original_root_access_attempts','archived_execution_attempts','repository_tools_import_attempts','network_or_child_attempts'):
    assert installed[key]==[]
relocated=load(HERE/'relocation-verification.json')
assert relocated['status']=='passed_authority_four_arm_relocation' and not any(relocated['guards'].values())
assert relocated['result']==result
wheel=ROOT/'data/cache/recovery-step9-four-arm-wheel-20261026/dist/asof_target_agents-0.3.6-py3-none-any.whl'
with ZipFile(wheel) as archive:
    members={n for n in archive.namelist() if n.startswith('asof/') and n.endswith(('.py','.json'))}
    expected={p.relative_to(ROOT/'src').as_posix() for p in (ROOT/'src/asof').rglob('*')
              if p.is_file() and p.suffix in ('.py','.json') and '__pycache__' not in p.parts}
    assert members==expected
    assert all(archive.read(n)==(ROOT/'src'/n).read_bytes() for n in members)
preserved=ROOT/'data/reference/recovery-r09-four-arm-verifier-036-20261027'
preserved.mkdir(exist_ok=False)
for path in (wheel,ROOT/'src/asof/archive/semantic_dependencies.json',ROOT/'src/asof/__init__.py'):
    with (preserved/path.name).open('xb') as stream:
        stream.write(path.read_bytes())
reports=[installed_path]
for name in ('full-validation.json','code-validation.json'):
    with (HERE/name).open('xb') as stream:
        stream.write((CACHE/name).read_bytes())
    reports.append(HERE/name)
reports += [HERE/n for n in ('CONTRACT-v2.md','CONTRACT-v2.json','INDEPENDENT-CONTRACT-REVIEW-v2.json',
    'INDEPENDENT-ENGINEERING-REVIEW.json','FROZEN-VERIFIER-CHECKS.json','QUALIFICATION-PROTOCOL-v1.json',
    'QUALIFICATION-PROTOCOL-v2.json','QUALIFICATION-FAILURE-v1.json','QUALIFICATION-FAILURE-CLOSEOUT-v1.json',
    'MODEL-MIRROR.json','STORAGE-REMEDIATION.md',
    'QUALIFICATION.json','HELPER-REVIEW.md','relocation-verification.json','CAPACITY-FOCUSED-FINAL.log',
    'CAPACITY-DOWNGRADE-BEFORE.log')]
acceptance=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),version='0.3.6',
    status='accepted_invented_authority_bound_four_arm_recorded_engineering_only',full_tests=full['tests'],
    new_regression_tests=30,independent_peer_tests=13,post_final_patch_session_capacity_tests=34,
    source_pins_rechecked=len(code['source_pins']),protected_hashes_only=2,
    installed_legacy_families=7,matching_frozen_verifiers=5,
    fixture='invented-six-v1',retrieval_policy='literal_case_overlap_then_id_v1',
    selected_ids=['id03','id04'],arms=4,recorded_cells=6,pure_results=2,tokenizer_children=6,
    prior_failed_qualification_tokenizer_children=2,total_children_across_these_two_qualification_attempts=8,
    local_mirror_bytes=mirror['verified_bytes'],mirror_source_unchanged=True,
    actual_model_calls=0,provider_spend_usd=0,input_reserved=14315,output_reserved=6144,
    fixture_declared_usage=result['fixture_declared_usage'],
    execution_outer_seconds=qualified['execution_outer_seconds'],sealed_elapsed_seconds=result['sealed_elapsed_seconds'],
    replay_seconds=qualified['replay_seconds'],peak_parent_working_set_bytes=qualified['peak_parent_working_set_bytes'],
    child_peak_memory_bytes=None,child_memory_reason='Not independently instrumented',
    real_source_expansion=False,nontrivial_real_retrieval_demonstrated=False,
    scientific_validation='not_established',human_reviews='pending',entire_R09_complete=False,
    native_R07_stop_unchanged=True,default_byte_policy_unchanged=True,
    remaining=['Nontrivial real evidence-access qualification','Fresh-case and independent human references',
        'Prospectively permitted model-quality qualification; existing native version remains stopped',
        'R10-R16 scientific and conditional programme'],
    wheel=pin(wheel),preserved_wheel=pin(preserved/wheel.name),evidence=[pin(p) for p in reports])
with (HERE/'acceptance.json').open('x',encoding='utf-8') as stream:
    json.dump(acceptance,stream,indent=2)
print(json.dumps(dict(status=acceptance['status'],tests=full['tests']['run'],acceptance_sha256=sha(HERE/'acceptance.json'))))
