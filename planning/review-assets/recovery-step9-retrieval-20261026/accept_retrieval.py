"""Accept bounded retrieval mechanics only, with all scientific limits explicit."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
CACHE = ROOT/'data/cache/recovery-step9-retrieval-validation-20261026'


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def pin(path):
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)


full,code=load(CACHE/'full-validation.json'),load(CACHE/'code-validation.json')
assert full['status']==code['status']=='passed'
assert full['tests']==dict(run=1616,failures=0,errors=0,skipped=[])
assert full['required_probes_exit_code']==0 and code['unchanged_code'] and code['protected_unchanged']
for name,digest in code['source_pins'].items():assert sha(ROOT/name)==digest,name
for name,digest in code['protected_hashes'].items():assert sha(ROOT/name)==digest  # Hash only.
peer=load(HERE/'IMPLEMENTATION-PEER-REVIEW-final.json')
assert peer['tests']['distinct_tests']==7 and peer['tests']['failures']==peer['tests']['errors']==peer['tests']['skips']==0
for item in peer['pins']:assert sha(ROOT/item['path'])==item['sha256'],item['path']
installed_path=ROOT/'data/cache/r09retrieval-installed-20261026/guarded-installed-verification.json'
installed=load(installed_path)
assert installed['status']=='passed' and len(installed['results'])==7
assert all(row['status']=='passed' for row in installed['results'])
for key in ('original_root_access_attempts','archived_execution_attempts','repository_tools_import_attempts','network_or_child_attempts'):
    assert installed[key]==[]
assert installed['installed_retrieval_smoke']['recorded_adapter_cells']==2
assert installed['installed_retrieval_smoke']['actual_model_calls']==0
qualified=load(HERE/'QUALIFICATION.json')
assert qualified['status']=='invented_retrieval_qualification_passed' and not any(qualified['guards'].values())
assert qualified['result']['input_reserved']==15656 and qualified['result']['output_reserved']==2048
assert qualified['actual_model_calls']==qualified['tokenizer_calls']==0
assert qualified['outer_preparation_and_sealing_seconds']<300
known=load(HERE/'KNOWN-REAL-QUALIFICATION.json')
assert known['status']=='known_single_real_record_retrieval_verified'
assert known['declared_real_candidates']==1 and known['nontrivial_real_retrieval_demonstrated'] is False
assert not any(known['guards'].values()) and known['preparation_seconds']<300
assert all(r['result']['coverage']['parent_observations_available']==9 and
           r['result']['coverage']['missing_input_count']==65 and
           r['result']['coverage']['raw_qualified_candidates']==1 and
           r['result']['coverage']['selected_count']==1 for r in known['results'])
negative=load(HERE/'OLD-PARENT-REJECTION.json')
assert negative['status']=='old_parent_rejected_before_original_source_access' and not any(negative['guards'].values())
for name in ('frozen-r07-after.json','frozen-baseline-after.json','frozen-comparison-after.json',
             'frozen-034-after.json','relocation-verification.json'):
    report=load(HERE/name)
    assert report['status'].startswith('passed_') and not any(report['guards'].values())
wheel=ROOT/'data/cache/recovery-step9-retrieval-wheel-20261026/dist/asof_target_agents-0.3.5-py3-none-any.whl'
with ZipFile(wheel) as archive:
    members={n for n in archive.namelist() if n.startswith('asof/') and n.endswith(('.py','.json'))}
    expected={p.relative_to(ROOT/'src').as_posix() for p in (ROOT/'src/asof').rglob('*')
              if p.is_file() and p.suffix in ('.py','.json') and '__pycache__' not in p.parts}
    assert members==expected
    for name in members:assert archive.read(name)==(ROOT/'src'/name).read_bytes(),name
preserved=ROOT/'data/reference/recovery-r09-retrieval-verifier-035-20261026'
preserved.mkdir(exist_ok=False)
for path in (wheel,ROOT/'src/asof/archive/semantic_dependencies.json',ROOT/'src/asof/__init__.py'):
    with (preserved/path.name).open('xb') as stream:stream.write(path.read_bytes())
reports=[installed_path]
for name in ('full-validation.json','code-validation.json'):
    with (HERE/name).open('xb') as stream:stream.write((CACHE/name).read_bytes())
    reports.append(HERE/name)
reports += [HERE/name for name in ('CONTRACT-v3.md','CONTRACT-v3.json','INDEPENDENT-CONTRACT-REVIEW-v3.json',
    'IMPLEMENTATION-PEER-REVIEW-final.json','QUALIFICATION.json','KNOWN-REAL-PROTOCOL.json',
    'KNOWN-REAL-QUALIFICATION.json','OLD-PARENT-REJECTION.json','BEFORE-VERSION.json',
    'frozen-r07-after.json','frozen-baseline-after.json','frozen-comparison-after.json',
    'frozen-034-after.json','relocation-verification.json')]
result=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    status='accepted_bounded_retrieval_preparation_and_recorded_integration_only',version='0.3.5',
    full_tests=full['tests'],scoped_tests=34,peer_tests=7,source_pins_rechecked=len(code['source_pins']),
    protected_hashes_only=2,installed_legacy_families=7,invented_candidate_records=6,
    retrieval_strategies=['id_order_v1','literal_case_overlap_then_id_v1'],
    recorded_adapter_cells=2,fixture_declared_usage=dict(input_tokens=128,output_tokens=128,cost_usd=0),
    actual_model_calls=0,tokenizer_calls=0,provider_spending_usd=0,input_reserved=15656,output_reserved=2048,
    outer_preparation_and_sealing_seconds=qualified['outer_preparation_and_sealing_seconds'],
    interpretation='four_arm_access_manifests_only_not_four_arm_execution',
    real_scope='same_one_exposed_IL6R_record_current_parent_no_universe_expansion',
    real_parent_available_count=9,real_missing_inputs=65,real_source_row_qualified=1,
    real_request_sha256=known['source_request_sha256'],
    nontrivial_real_retrieval_demonstrated=False,scientific_validation='not_established',
    human_scientific_review='pending',entire_R09_complete=False,
    remaining=['Single-policy authority-aware four-arm execution contract and finite preflight',
               'Conditional explicit token-capacity integration if complete payloads require it',
               'Fresh-case/reference/reviewer qualification and prospectively gated native/scientific work'],
    wheel=pin(wheel),preserved_wheel=pin(preserved/wheel.name),evidence=[pin(p) for p in reports])
with (HERE/'acceptance.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps(dict(status=result['status'],tests=full['tests']['run'],source_pins=len(code['source_pins']),
                      acceptance_sha256=sha(HERE/'acceptance.json'))))
