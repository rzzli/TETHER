"""Seal the finite protocol only after full validation and current source checks."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CACHE=ROOT/'data/cache/recovery-step9-four-arm-validation-20261026'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


code=json.loads((CACHE/'code-validation.json').read_bytes())
full=json.loads((CACHE/'full-validation.json').read_bytes())
assert code['status']==full['status']=='passed'
assert full['tests']==dict(run=1646,failures=0,errors=0,skipped=[])
assert code['unchanged_code'] and code['protected_unchanged']
assert len(code['source_pins'])==312
assert all(sha(ROOT/n)==h for n,h in code['source_pins'].items())
old=json.loads((HERE/'TOKEN-QUOTE-PROTOCOL-v2.json').read_bytes())
manifest=CACHE/'before-source-pins.json'
assert json.loads(manifest.read_bytes())==code['source_pins']
protocol=dict(schema_version=1,role='prospective_engineering_execution_protocol',
    created_at_utc=datetime.now(timezone.utc).isoformat(),version='0.3.6',
    helper_sha256=sha(HERE/'qualify_four_arm.py'),
    source_pins=dict(path=manifest.relative_to(ROOT).as_posix(),sha256=sha(manifest)),
    full_validation_sha256=sha(CACHE/'full-validation.json'),
    code_validation_sha256=sha(CACHE/'code-validation.json'),
    inventory_path=old['inventory_path'],model_root=old['model_root'],
    fixture='invented-six-v1',policy='literal_case_overlap_then_id_v1',
    selected_ids=['id03','id04'],maximum_tokenizer_children=6,
    actual_model_calls=0,provider_cost_usd=0,automatic_retries=False,
    budget=dict(max_calls=16,max_input_tokens=32000,max_output_tokens=8000,
        max_cost_usd=0,max_seconds=300,max_retries=1),
    source_change=False,real_source_expansion=False,
    preflight_sha256=sha(HERE/'PREFLIGHT-RESULT.json'),
    interpretation='One finite invented recorded qualification, not native or scientific validation',
    helper_review_sha256=sha(HERE/'HELPER-REVIEW.md'))
with (HERE/'QUALIFICATION-PROTOCOL-v1.json').open('x',encoding='utf-8') as stream:
    json.dump(protocol,stream,indent=2)
print(json.dumps(dict(status='prospective_protocol_sealed',sha256=sha(HERE/'QUALIFICATION-PROTOCOL-v1.json'))))
