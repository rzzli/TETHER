"""Observe old structural preparation only; this is not an eligible admitted case."""
import json
from asof.serde import encode
from asof.study.diagnostic import load_synthetic_request
from asof.study.diagnostic_codec import bind_question
from asof.study.interpretation_interface import prepare_payload

request=encode(load_synthetic_request('synthetic-orientation'))
for row in request['source_request']['evidence']:
    row['statement']=row['scientific_record']['statement']=''
    row['scientific_record']['source_metrics']={}
request=bind_question(request['source_request'],request['question']['question_id'])
prepared=prepare_payload(request,'asof_interpretation',0,[])
print(json.dumps(dict(version_under_probe='0.3.8',behavior='prepared_empty_quote_catalog',
    quote_count=len(prepared['semantic_data']['quote_catalog']),execution_authorized=prepared['execution_authorized'],
    admitted_source_eligibility='not_established_in_pure_codec',model_calls=0,
    new_policy='Reject no-quote structural inputs before any future native dispatch; no change to admitted source requirements')))
