"""Extend the retained dependency-free installed check with native-wrapper fixtures."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
text=(HERE.parent/'recovery-step9-interface-20261027/verify_installed.py').read_text(encoding='utf-8')
assert text.count("=='0.3.8'")==1
text=text.replace("=='0.3.8'","=='0.3.9'")
addition='''
# Explicitly invented native-wrapper bytes; no HTTP adapter or process is started.
import base64
from contextlib import closing
from asof.journal import RunJournal
from asof.study import native
from asof.study.native_interpretation import validate_native_response
from asof.study.native_accounting import accounting
original=load_synthetic_request('synthetic-orientation')
stage=dict(original_request=encode(original),fixture='installed_wrapper_only')
payload=prepare_payload(original,'asof_interpretation',0,[])['payload']
document=dict(answer_status='abstained',claims=[],unresolved=[],abstention_reason='Invented wrapper only.')
body=dict(prompt=payload['prompt'],model='fixture',
    generation_settings={k:encode(payload[k]) for k in ('seed','temperature','n_predict','stop','stream')},
    truncated=False,stop=True,stop_type='eos',stopped_limit=False,stopping_word='',
    tokens_evaluated=20,tokens_predicted=5,content=canonical(document).decode())
raw=canonical(body)
wrapper=dict(schema_version=1,kind=native.PROTOCOL,request_sha256=fingerprint(stage),payload_sha256=fingerprint(payload),
    owner_pid=4242,endpoint='http://127.0.0.1:55581',http_status=200,body_base64=base64.b64encode(raw).decode(),
    body_sha256=hashlib.sha256(raw).hexdigest(),complete=True,error_class=None,elapsed_seconds=0.01)
response=validate_native_response(stage,payload,canonical(wrapper),model_alias='fixture')
assert response['response']['answer_status']=='abstained' and response['features']=={} and response['clinical_probability'] is None
rejected=[]
for key,value in (('request_sha256','a'*64),('body_sha256','b'*64),('complete',False)):
    try:validate_native_response(stage,payload,canonical(dict(wrapper,**{key:value})),model_alias='fixture')
    except ContractError:rejected.append(key)
    else:raise AssertionError('Invalid wrapper accepted')
account_root=REPORT.parent/'native-wrapper-accounting'
with closing(RunJournal(account_root,kind='build')) as journal:
    journal.append('native_context_qualified',context=dict(endpoint=wrapper['endpoint'],owner_pid=4242,model_alias='fixture',model_provenance={}))
child=account_root/'cells/00'
child.parent.mkdir()
with closing(RunJournal(child,kind='build')) as journal:
    journal.append('study_dispatch',request_sha256=fingerprint(stage),payload_sha256=fingerprint(payload))
    journal.append('study_accounted',usage=dict(input_tokens=20,output_tokens=5,cost_usd=0.0),basis='adapter_reported')
(child/'request.json').write_bytes(canonical(stage))
(child/'payload.json').write_bytes(canonical(payload))
(child/'raw-response.bin').write_bytes(canonical(wrapper))
native_fixture_accounting=accounting(account_root,'simulated_native_transport')
assert native_fixture_accounting['actual_model_calls']==native_fixture_accounting['known_http_attempts']==0
assert native_fixture_accounting['known_simulated_model_calls']==1
assert native_fixture_accounting['simulated_transport_usage']==dict(input_tokens=20,output_tokens=5,cost_usd=0.0)
native_wrapper_exercise=dict(role='invented_wrapper_only',positive_cases=1,negative_cases=rejected,
    accounting=native_fixture_accounting,actual_native_servers=0,network_calls=0)

'''
text=text.replace('from asof.serde import ContractError, fingerprint','from asof.serde import ContractError, fingerprint, canonical')
assert text.count('records = []')==1
text=text.replace('records = []',addition+'records = []')
text=text.replace('result = dict(installed_interpretation_interface=', 'result = dict(installed_native_wrapper=native_wrapper_exercise, installed_interpretation_interface=')
with (HERE/'verify_default_installed.py').open('x',encoding='utf-8') as stream:stream.write(text)
