"""Freeze a metadata-selected five-record real frame, with no outcome or answer reads."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

from asof.serde import canonical,encode
from asof.study.source_preparation import validate_authority

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=HERE.parent/'recovery-step9-token-aware-20261026'
CODE=ROOT/'data/cache/recovery-step9-four-arm-validation-20261026/code-validation.json'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


code=json.loads(CODE.read_bytes())
assert code['status']=='passed'
assert all(sha(ROOT/n)==h for n,h in code['source_pins'].items())
authority=json.loads((OLD/'SOURCE-AUTHORITY-v1.json').read_bytes())
packet_pin=authority['files']['artifact-packet-il6r-efo_0000685-inhibit-antibody']
packet=ROOT/packet_pin['relative_path']
assert sha(packet)==packet_pin['sha256']
rows=json.loads(packet.read_bytes())['observations']
selected=[r for r in rows if r['category']=='literature']
assert len(rows)==9 and len(selected)==5 and all(not r['features'] for r in selected)
ids=sorted(r['observation_id'] for r in selected)
authority['selection']['observation_ids']=ids
authority['expected_request_sha256']=None
validate_authority(authority)
with (HERE/'SOURCE-AUTHORITY-v1.json').open('xb') as stream:
    stream.write(canonical(authority))
frame=dict(schema_version=1,status='metadata_frame_checked_raw_requalification_pending',
    category='literature',candidate_ids=ids,existing_packet_count=9,
    candidate_count=5,selection_rule='Every existing literature record; no content/score/outcome selection',
    packet=dict(path=packet.relative_to(ROOT).as_posix(),sha256=sha(packet)),
    records=[dict(observation_id=r['observation_id'],category=r['category'],study_id=r['study_id'],
        features_empty=not bool(r['features'])) for r in selected],
    expected_request_sha256=None,expected_request_reason='Derived only after fresh source-inclusive admission',
    fresh_case=False,scientific_validation='not_attempted')
with (HERE/'FRAME-INSPECTION.json').open('x',encoding='utf-8') as stream:
    json.dump(frame,stream,indent=2)
protocol=dict(schema_version=1,created_at_utc=datetime.now(timezone.utc).isoformat(),version='0.3.6',
    status='prospective_before_qualification',source_authority_sha256=sha(HERE/'SOURCE-AUTHORITY-v1.json'),
    frame_sha256=sha(HERE/'FRAME-INSPECTION.json'),code_validation_sha256=sha(CODE),
    source_pins_path=CODE.relative_to(ROOT).as_posix(),candidate_ids=ids,category='literature',
    strategies=['id_order_v1','literal_case_overlap_then_id_v1'],
    unchanged_limits=dict(max_records=2,max_request_bytes=12000),
    new_downloads=0,new_model_calls=0,tokenizer_calls=0,provider_cost_usd=0,
    source_parent_expected_available=9,source_parent_expected_missing=65,
    preparation_seconds_limit=300,replay_seconds_limit=300,
    boundaries='Only the existing27pinnedsourcefiles; no E writes, labels, gold, reviewer answers, native or network',
    interpretation='Bounded collected-corpus mechanics only; no freshness, relevance quality or biological conclusion',
    failure='Retain failure; no policy/limit/source substitution or automatic retry')
with (HERE/'PROTOCOL-v1.json').open('x',encoding='utf-8') as stream:
    json.dump(protocol,stream,indent=2)
print(json.dumps(dict(status='prospective_five_record_protocol_sealed',candidates=ids,
    protocol_sha256=sha(HERE/'PROTOCOL-v1.json'))))
