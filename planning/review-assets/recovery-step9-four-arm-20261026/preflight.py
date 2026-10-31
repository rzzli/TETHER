"""One non-dispatching byte preflight over an independently anchored invented subset."""
import hashlib,json,sys,time
from pathlib import Path
from asof.serde import canonical,encode,fingerprint
from asof.study.retrieval_smoke import verify
from asof.study.retrieval_preparation import verify_retrieval_preparation,fixture_authority,authority_anchor,policy_for
from asof.study.preparation_payloads import prepare_payloads
from asof.workflow import Budget
P=Path(__file__).parent;ROOT=P.resolve().parents[2]
protocol=json.loads((P/'PREFLIGHT-PROTOCOL-v1.json').read_bytes())
def guard(event,args):
    if event in ('subprocess.Popen','os.system','socket.connect','socket.getaddrinfo'):
        raise RuntimeError('No process/network allowed in byte preflight')
    if event=='open' and isinstance(args[0],(str,bytes)):
        name=args[0].decode() if isinstance(args[0],bytes) else args[0]
        if name.replace('\\','/').lower().startswith('e:'):raise RuntimeError('No E drive access in byte preflight')
sys.addaudithook(guard)
parent=ROOT/protocol['source_parent'];anchor=protocol['parent_receipt_sha256'];started=time.monotonic()
parent_verification=verify(parent,anchor)
receipt_raw=(parent/'receipt.json').read_bytes();assert hashlib.sha256(receipt_raw).hexdigest()==anchor
receipt=json.loads(receipt_raw);strategy=protocol['policy'];child=parent/'preparation'/strategy
child_receipt_raw=(child/'receipt.json').read_bytes();child_anchor=hashlib.sha256(child_receipt_raw).hexdigest();assert child_anchor==receipt['artifacts']['preparation/'+strategy+'/receipt.json']['sha256']
authority=fixture_authority(protocol['fixture']);external=authority_anchor(authority)
child_verification=verify_retrieval_preparation(child,child_anchor,external,deadline=started+299)
child_receipt=json.loads(child_receipt_raw);raw=(child/'request.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==child_receipt['files']['request.json']['sha256'];request=json.loads(raw)
assert json.loads((child/'policy.json').read_bytes())==encode(policy_for(strategy))
assert [r['observation_id'] for r in request['source_request']['evidence']]==protocol['selected_ids']
assert encode(Budget())==protocol['budget']
cells=prepare_payloads(request);assert len(cells)==6
rows=[]
for index,cell in enumerate(cells):
    assert canonical(cell['semantic_data']['original_request'])==canonical(request)
    payload=encode(cell['payload']);assert fingerprint(payload)==cell['payload_sha256']
    name=f"{index:02d}-{cell['stage_name']}.json";document=dict(role='planning_only',execution_authorized=False,cell=encode(cell))
    with (P/name).open('xb') as f:f.write(canonical(document))
    rows.append(dict(file=name,file_sha256=fingerprint(document),arm=cell['arm'],stage=cell['stage_name'],payload_sha256=fingerprint(payload),request_sha256=fingerprint(request),evidence_sha256=fingerprint(request['source_request']['evidence']),prompt_utf8_bytes=cell['prompt_utf8_bytes'],http_payload_bytes=cell['http_payload_bytes'],conservative_input_reservation=cell['prompt_utf8_bytes']+32,output_reservation=payload['n_predict'],history_scope=cell['history_scope']))
report=dict(schema_version=1,role='planning_only',protocol_sha256=hashlib.sha256((P/'PREFLIGHT-PROTOCOL-v1.json').read_bytes()).hexdigest(),helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),parent_verification=encode(parent_verification),parent_receipt_sha256=anchor,child_receipt_sha256=child_anchor,child_verification=encode(child_verification),request_sha256=fingerprint(request),source_fields_unchanged=True,selected_ids=protocol['selected_ids'],policy=strategy,cells=rows,aggregate_input_reservation=sum(x['conservative_input_reservation'] for x in rows),aggregate_output_reservation=sum(x['output_reservation'] for x in rows),default_budget=encode(Budget()),actual_generation_calls=0,tokenizer_processes=0,network_calls=0,E_drive_operations=0,elapsed_seconds=time.monotonic()-started)
report['byte_proxy_fits']=report['aggregate_input_reservation']<=Budget().max_input_tokens and report['aggregate_output_reservation']<=Budget().max_output_tokens
report['disposition']='byte_preflight_only_no_execution' if report['byte_proxy_fits'] else 'stop_byte_proxy_exceeds_budget_no_changes_or_tokenization'
with (P/'PREFLIGHT-RESULT.json').open('xb') as f:f.write(canonical(report))
print(json.dumps({k:report[k] for k in ['aggregate_input_reservation','aggregate_output_reservation','byte_proxy_fits','disposition','request_sha256','elapsed_seconds']},indent=2))
