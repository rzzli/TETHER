"""Retain the guarded default/legacy helper with an installed interface exercise."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
old=HERE.parent/'recovery-step9-collected-composition-20261027/verify_default_installed.py'
text=old.read_text(encoding='utf-8').replace("=='0.3.7'","=='0.3.8'")
anchor="assert study_result['status'] == 'recorded_smoke_passed'"
assert text.count(anchor)==1
insert='''
from asof.study.interpretation_interface import prepare_payload, request_from_payload, validate_output
from asof.study.diagnostic import load_synthetic_request
from asof.study.diagnostic_codec import pointer
from asof.serde import ContractError, fingerprint
interface_rows=[]
for fixture in ('synthetic-context','synthetic-orientation'):
    request=load_synthetic_request(fixture)
    for arm,count in (('asof_interpretation',1),('adapted_virtual_biotech_interpretation',5)):
        history=[]
        for index in range(count):
            prepared=prepare_payload(request,arm,index,history)
            assert fingerprint(request_from_payload(prepared['payload']))==fingerprint(request)
            quote=prepared['semantic_data']['quote_catalog'][0]
            document=dict(answer_status='answered',claims=[dict(kind='source_report',
                text=pointer(encode(request),quote['request_pointer']),quote_refs=[quote['quote_id']],limitations=[])],
                unresolved=[],abstention_reason=None)
            response=validate_output(request,prepared['payload'],document)
            assert encode(response['response'])==document and response['features']=={} and response['clinical_probability'] is None
            assert response['quotes'][0]['text']==document['claims'][0]['text']
            for state in ('partial','abstained'):
                alternative=dict(document,answer_status=state,abstention_reason='Invented incomplete source.')
                if state=='abstained':alternative['claims']=[]
                validate_output(request,prepared['payload'],alternative)
            try:
                validate_output(request,prepared['payload'],dict(document,abstention_reason='Contradiction.'))
            except ContractError:
                pass
            else:
                raise AssertionError('Contradictory state accepted')
            interface_rows.append(dict(fixture=fixture,arm=arm,index=index,request_sha256=fingerprint(request),
                payload_sha256=prepared['payload_sha256'],response_sha256=fingerprint(response),states_checked=3))
            history.append(dict(stage=prepared['semantic_data']['stage'],source_ids=['E0']))
assert len(interface_rows)==12
'''
text=text.replace(anchor,anchor+insert)
anchor='result = dict(installed_retrieval_smoke='
assert text.count(anchor)==1
text=text.replace(anchor,'result = dict(installed_interpretation_interface=interface_rows, installed_retrieval_smoke=')
with (HERE/'verify_installed.py').open('x',encoding='utf-8') as stream:
    stream.write(text)
print('Created guarded default installed helper; no old helper changed')
