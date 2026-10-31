"""Freeze the single prospective collected-input qualification after validation."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


validation=ROOT/'data/cache/recovery-step9-collected-validation-20261027/code-validation.json'
checked=json.loads(validation.read_bytes())
assert checked['status']=='passed' and checked['unchanged_code'] and checked['protected_unchanged']
assert len(checked['source_pins'])==314 and all(sha(ROOT/n)==h for n,h in checked['source_pins'].items())
authority=ROOT/'planning/review-assets/recovery-step9-real-retrieval-20261027/SOURCE-AUTHORITY-v1.json'
old_protocol=json.loads((ROOT/'planning/review-assets/recovery-step9-four-arm-20261026/QUALIFICATION-PROTOCOL-v2.json').read_bytes())
mirror=ROOT/'planning/review-assets/recovery-step9-four-arm-20261026/MODEL-MIRROR.json'
assert sha(mirror)==old_protocol['mirror_sha256']
protocol=dict(schema_version=1,role='prospective_collected_source_recorded_qualification',
    created_at_utc=datetime.now(timezone.utc).isoformat(),version='0.3.7',
    helper_sha256=sha(HERE/'qualify_collected.py'),
    code_validation=dict(path=validation.relative_to(ROOT).as_posix(),sha256=sha(validation)),
    source_authority=dict(path=authority.relative_to(ROOT).as_posix(),sha256=sha(authority)),
    raw_root=r'E:\projects_data\drug_target_agents_data',model_root=old_protocol['model_root'],
    inventory_path=old_protocol['inventory_path'],model_mirror_sha256=sha(mirror),
    maximum_tokenizer_children=6,actual_model_calls=0,provider_cost_usd=0,automatic_retries=False,
    budget=old_protocol['budget'],case='existing_exposed_IL6R_RA_inhibit_antibody',fresh_case=False,
    declared_candidate_count=5,original_source_files=27,selected_strategy='literal_case_overlap_then_id_v1',
    features={},clinical_probability=None,scientific_validation='not_attempted',new_downloads=0,
    interpretation='Exact source-report copying is a recorded transport fixture, not an expert judgment or native model result')
with (HERE/'QUALIFICATION-PROTOCOL.json').open('x',encoding='utf-8') as stream:
    json.dump(protocol,stream,indent=2)
print(json.dumps(dict(status='protocol_frozen',helper_sha256=protocol['helper_sha256'],source_pins=len(checked['source_pins']))))
