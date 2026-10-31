"""Explain unchanged whole-request limits without changing the selected universe or policy."""
import json
from pathlib import Path

from asof.agents import make_request
from asof.contracts import Category
from asof.serde import parse_json
from asof.study.retrieval_preparation import _records,policy_for
from asof.wire import request_bytes

HERE=Path(__file__).resolve().parent
q=parse_json((HERE/'QUALIFICATION.json').read_bytes())
root=Path(q['output'])
request=parse_json((root/'source/request.json').read_bytes())
case,records=_records(request)
policy=policy_for('id_order_v1')
selected=q['results'][0]['result']['coverage']['selected_rank_ids']
chosen=next(r for r in records if r.observation.observation_id==selected[0])
rows=[]
for record in records:
    single=len(request_bytes(make_request(case,Category.LITERATURE,(record,)),policy['wire_format']))
    pair=None if record==chosen else len(request_bytes(make_request(case,Category.LITERATURE,(chosen,record)),policy['wire_format']))
    rows.append(dict(observation_id=record.observation.observation_id,single_whole_request_bytes=single,
        individually_fits=single<=policy['max_request_bytes'],
        whole_request_bytes_with_selected_record=pair,
        pair_fits=None if pair is None else pair<=policy['max_request_bytes']))
report=dict(schema_version=1,kind='read_only_bound_explanation',max_request_bytes=policy['max_request_bytes'],
    selected_ids=selected,records=rows,policies_or_sources_changed=False,
    interpretation='Exclusion can mean cumulative whole-request size, not individual oversize; no evidence-quality claim')
with (HERE/'BOUND-DIAGNOSTIC.json').open('x',encoding='utf-8') as stream:
    json.dump(report,stream,indent=2)
print(json.dumps(report,indent=2))
