"""Accept data-access mechanics and explicit limits, not scientific ranking quality."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def load(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def pin(path):
    path=Path(path)
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size)


protocol=load(HERE/'PROTOCOL-v1.json')
code=load(ROOT/protocol['source_pins_path'])
assert sha(ROOT/protocol['source_pins_path'])==protocol['code_validation_sha256']
assert code['status']=='passed' and all(sha(ROOT/n)==h for n,h in code['source_pins'].items())
q=load(HERE/'QUALIFICATION.json')
installed=load(HERE/'INSTALLED-VERIFICATION.json')
bounds=load(HERE/'BOUND-DIAGNOSTIC.json')
assert q['status']=='five_original_record_bounded_retrieval_verified'
assert q['declared_candidates']==q['raw_rows_equal']==5
assert q['parent_observations_available']==9 and q['missing_input_count']==65
assert q['model_calls']==q['tokenizer_calls']==q['provider_spend_usd']==q['new_downloads']==0
assert q['source_pins_unchanged'] and not any(q['guards'].values())
assert q['preparation_seconds']<300 and q['replay_seconds']<300
assert installed['status']=='installed_source_inclusive_real_retrieval_verified'
assert installed['isolated'] and not any(installed['guards'].values())
assert len(q['results'])==len(installed['results'])==2
for row,verified in zip(q['results'],installed['results']):
    assert row['strategy']==verified['strategy'] and row['replay']==verified['result']
    coverage=row['result']['coverage']
    assert coverage['declared_candidates']==coverage['raw_qualified_candidates']==5
    assert coverage['selected_count']==1 and len(coverage['excluded'])==4 and coverage['absence_claim'] is False
assert q['results'][0]['result']['coverage']['selected_rank_ids']==q['results'][1]['result']['coverage']['selected_rank_ids']
assert sum(r['individually_fits'] for r in bounds['records'])==3
assert all(r['pair_fits'] is False for r in bounds['records'] if r['pair_fits'] is not None)
evidence=[HERE/n for n in ('PROTOCOL-v1.json','FRAME-INSPECTION.json','SOURCE-AUTHORITY-v1.json',
    'QUALIFICATION.json','INSTALLED-VERIFICATION.json','BOUND-DIAGNOSTIC.json','ARROW-INSTALL.json',
    'qualify_real.py','verify_installed.py','diagnose_bounds.py')]
result=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    status='accepted_five_record_real_retrieval_mechanics_not_scientific_performance',version='0.3.6',
    original_rows_qualified=5,strategies=[r['strategy'] for r in q['results']],selected_per_strategy=1,
    policies_select_same_record=True,selected_ids=q['results'][0]['result']['coverage']['selected_rank_ids'],
    unchanged_max_records=2,unchanged_whole_request_bytes=12000,
    individually_fitting_records=3,individually_oversized_records=2,any_pair_with_selected_fits=False,
    parent_observations_available=9,missing_input_count=65,absence_claim=False,
    preparation_seconds=q['preparation_seconds'],replay_seconds=q['replay_seconds'],
    installed_source_inclusive_replay_seconds=installed['elapsed_seconds'],
    code_resource_pins_unchanged=len(code['source_pins']),new_runtime_changes=0,
    actual_model_calls=0,tokenizer_calls=0,new_downloads=0,provider_spend_usd=0,
    scientific_validation='not_established',relevance_quality_validated=False,
    fresh_case=False,real_four_arm_execution=False,entire_R09_complete=False,
    remaining=['Independent source-only references and judgments',
        'Scientific sufficiency of bounded source representation',
        'Fresh-frame qualification and separately permitted model-quality experiment',
        'R10-R16 and conditional scientific programme'],evidence=[pin(p) for p in evidence])
with (HERE/'acceptance.json').open('x',encoding='utf-8') as stream:
    json.dump(result,stream,indent=2)
print(json.dumps(dict(status=result['status'],acceptance_sha256=sha(HERE/'acceptance.json'))))
