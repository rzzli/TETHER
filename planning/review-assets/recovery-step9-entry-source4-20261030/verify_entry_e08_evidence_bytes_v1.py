"""Retrospective independent byte checks of retained synthetic evidence only.

This module imports no subject, harness or codec and invokes no producer.
"""
import hashlib
import json
import math
from pathlib import Path
import struct

HERE=Path(__file__).resolve().parent
PROOF=HERE/'ENTRY-E08-SUITE-PROOF-v1.json'
ART=HERE/'ENTRY-E08-SUITE-ARTIFACTS-v1'
OUT=HERE/'ENTRY-E08-SUITE-BYTE-CONSISTENCY-PROOF-v1.json'
APIS=('CreateFileW','GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx','ReadFile','CloseHandle')
AXES=('scalar','count','error_value','error_definition')
OFFSETS=(128,160,192,224)
KINDS={1:'HANDLE64',2:'BOOL32_BITS',3:'DWORD32',4:'COUNT32',5:'DEFINEDNESS'}
INVALID=(1<<64)-1


def need(ok,label):
    if not ok:raise AssertionError(label)


def typed(a,b):
    if type(a)is not type(b):return False
    if type(a)is dict:return a.keys()==b.keys()and all(typed(a[k],b[k])for k in a)
    if type(a)is list:return len(a)==len(b)and all(typed(x,y)for x,y in zip(a,b))
    if type(a)is float:return struct.pack('<d',a)==struct.pack('<d',b)
    return a==b


def pin(path):
    digest=hashlib.sha256();size=0
    with path.open('rb')as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block);size+=len(block)
    return dict(path=str(path),bytes=size,sha256=digest.hexdigest())


def axis(raw):
    need(len(raw)==32,'axis length')
    bits,epoch,k,width,pad,stage,commit,tail=struct.unpack('<QIHBBIIQ',raw)
    need(k in KINDS and epoch==1 and pad==tail==0 and stage in(0,1)and commit in(0,1)and(not commit or stage),'axis metadata')
    kind=KINDS[k];need(width==(8 if k==1 else 1 if k==5 else 4),'axis width')
    need(bits<1<<(width*8)and(k!=5 or bits in(0,1)),'axis payload domain')
    state='COMMITTED'if commit else'STAGED_UNCOMMITTED'if stage else'UNOBSERVED'
    value=None
    if commit:value=bool(bits)if k==5 else bits-(1<<32)if k==2 and bits&(1<<31)else bits
    return dict(layout_valid=True,native_state=state,kind=kind,width=width,epoch=epoch,stage_hint=stage,commit=commit,raw_payload_bits=bits,known_value=value)


def parse_row(raw):
    need(len(raw)==256,'native row length')
    schema,size,ordinal,generation,api,actor,target,file_id,requested,zero=struct.unpack_from('<HHIIHBBIII',raw)
    need(schema==1 and size==256 and generation==1 and 1<=api<=7 and actor in(0,1)and target==1,'native row header')
    need(zero==0 and raw[28:40]==bytes(12)and raw[60:64]==bytes(4)and raw[76:128]==bytes(52),'native row reserved bytes')
    axes={name:axis(raw[start:start+32])for name,start in zip(AXES,OFFSETS)}
    expected_scalar='HANDLE64'if api==1 else'DWORD32'if api in(2,4)else'BOOL32_BITS'
    need(axes['scalar']['kind']==expected_scalar and axes['count']['kind']=='COUNT32'and axes['error_value']['kind']=='DWORD32'and axes['error_definition']['kind']=='DEFINEDNESS','axis API kinds')
    return dict(ordinal=ordinal,api=APIS[api-1],api_id=api,actor=actor,file_id=file_id,requested=requested,input_handle=struct.unpack_from('<Q',raw,40)[0],native_return=struct.unpack_from('<I',raw,72)[0],axes=axes)


def native_atom(observation,tag):
    if observation['native_state']!='COMMITTED':return dict(tag='UNOBSERVED',value=None)
    value=observation['known_value']
    if tag=='HANDLE'and value==0:return dict(tag='NULL',value=None)
    return dict(tag=tag,value=value)


def delivery_atom(value,tag):
    if type(value)is dict and value.get('tag')=='UNOBSERVED':return dict(tag='UNOBSERVED',value=None)
    if value is None:return dict(tag='NULL',value=None)
    return dict(tag=tag,value=value)


def snapshot_clock(value):
    tag=value['tag'];v=value.get('value')
    if tag=='UNOBSERVED':return dict(tag=tag,bits=None,value=None,valid=False)
    if tag=='I64':return dict(tag=tag,bits=v&INVALID,value=v,valid=True)
    if tag=='F64':return dict(tag=tag,bits=int.from_bytes(bytes.fromhex(value['bits_hex']),'little'),value=v,valid=value['finite'])
    if tag=='BOOL_INVALID':return dict(tag=tag,bits=int(v),value=v,valid=False)
    return dict(tag=tag,bits=None,value=None,valid=False)


def query_expected(parsed,file):
    if parsed['api_id']==3:return struct.pack('<II',128,0)
    if parsed['api_id']==5:return struct.pack('<q',file['spec']['size'])
    path=('\\\\?\\'+file['spec']['path']).encode('utf-16-le')
    return path+bytes(8202-len(path))


def policy_data(world):
    """Recompute only retained report framing, not policy admission/ancestry."""
    value=world['policy_observation']
    need(type(value['attempted'])is bool and type(value['execution_eligible'])is bool,'policy exact bools')
    binding=value['captured_binding'];envelope=value['captured_envelope']
    prepared=value['prepared_report'];issued=value['issued_report']
    kinds=[]
    for label,report in(('prepared',prepared),('issued',issued)):
        if report is None:continue
        need(type(binding)is dict and type(envelope)is dict,'report has retained detached metadata')
        encode=lambda item:json.dumps(item,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
        nodes=envelope['nodes']
        expected=dict(schema_version=1,mode=binding['mode'],status='AUTHORING_ONLY'if binding['mode']=='AUTHORING'else'EXECUTION_BASIS_VALIDATED',
            node_count=len(nodes),edge_count=sum(len(node['pin_dependencies'])for node in nodes),
            basis_ids=binding['basis_ids'],external_anchor_ids=envelope['external_anchor_ids'],
            prior_root_ids=[pin['id']for pin in binding['prior_metadata_pins']],
            planned_ids=[node['id']for node in nodes if node['state']=='PLANNED_SOURCE'],
            unbuilt_ids=[node['id']for node in nodes if node['state']=='UNBUILT'],
            binding_sha256=hashlib.sha256(encode(binding)).hexdigest(),
            envelope_sha256=hashlib.sha256(encode(envelope)).hexdigest())
        need(typed(report,expected),'all12 retained policy report fields/counts/canonical digests')
        need(len(encode(dict(binding=binding,envelope=envelope)))<=131072,'issued/prepared metadata canonical byte cap')
        kinds.append(label)
    if issued is not None:
        need(prepared is not None and typed(prepared,issued)and value['prepared_and_issued_same_object']is True,'issued policy uses original prepared return')
        need(value['execution_eligible']is(issued['mode']=='EXECUTION'),'issued mode/eligibility data')
    else:
        need(value['execution_eligible']is False,'absent issued report stays ineligible')
        need(value['prepared_and_issued_same_object']is None,'no invented issued identity')
    if prepared is not None and issued is None:need(value['original_error']is not None,'late prepared report retains original error')
    return kinds


def main():
    totals=dict(worlds=0,artifact_files=0,artifact_bytes=0,canonical_calls=0,registered_rows=0,missing_rows=0,snapshots=0,copied_rows=0,axis_copies=0,query_files=0,query_bytes=0,complete_snapshot_projections=0,policy_observations=0,prepared_reports=0,issued_reports=0,prepared_only_reports=0,snapshot_policy_copies=0)
    location='proof';failure=None;examined=[];per_world=[]
    try:
        proof_pin=pin(PROOF);need(proof_pin['sha256']=='f1c1e9803e1128acbfd6343aa038d1ba81c902c075c770c3f8adf4b3f35073db','exact actual proof')
        proof=json.loads(PROOF.read_bytes());inventory={}
        for branch in proof['rows']:
            for wi,world in enumerate(branch['worlds'],1):
                for item in world['artifacts']:
                    p=Path(item['path']).resolve();need(p.parent==ART.resolve(),'artifact containment')
                    q={k:item[k]for k in('path','bytes','sha256')}
                    if p in inventory:need(inventory[p]==q,'duplicate artifact pin')
                    inventory[p]=q
        need(set(inventory)==set(ART.iterdir()),'complete flat artifact inventory')
        for p,item in inventory.items():
            location=str(p);actual=pin(p);need(actual==item,'artifact bytes/hash '+p.name)
            totals['artifact_files']+=1;totals['artifact_bytes']+=actual['bytes']
        for branch in proof['rows']:
            for wi,world in enumerate(branch['worlds'],1):
                totals['worlds']+=1;prefix='dispatch-%03d-world-%02d'%(proof['rows'].index(branch)+1,wi);location=prefix
                if not world['core_present']:continue
                policy_kinds=policy_data(world);totals['policy_observations']+=1
                totals['prepared_reports']+=int('prepared'in policy_kinds);totals['issued_reports']+=int('issued'in policy_kinds)
                totals['prepared_only_reports']+=int(policy_kinds==['prepared'])
                canon=ART/(prefix+'.canonical-calls.jsonl');rawp=ART/(prefix+'.canonical-native-rows.bin')
                calls=[];registered={};rawrows={}
                with canon.open('r',encoding='utf-8')as text,rawp.open('rb')as binary:
                    for line in text:
                        row=json.loads(line);need(row['ordinal']==len(calls),'canonical ordinal');calls.append(row)
                        if not row['registered']:
                            totals['missing_rows']+=1;need(row['axes']is None and row['native_record_offset']is None and not row['invoked'],'missing registration explicit');continue
                        raw=binary.read(256);parsed=parse_row(raw);index=row['ordinal']
                        need(parsed['ordinal']==index and parsed['api']==row['api'],'canonical row identity')
                        need(row['native_record_offset']==256*len(registered),'canonical offset')
                        need(typed(parsed['axes'],row['axes']),'canonical decoded axes')
                        need(parsed['native_return']==(2 if row['wrapper_return_observed']else 1 if row['invoked']else 0),'native/caller return axes')
                        if 'query'in row:
                            q=Path(row['query']['path']);blob=q.read_bytes();api=row['api']
                            need(api in('GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx'),'query API')
                            need(len(blob)==(8202 if api=='GetFinalPathNameByHandleW'else 8),'query exact width')
                            totals['query_files']+=1;totals['query_bytes']+=len(blob)
                        registered[index]=parsed;rawrows[index]=raw;totals['registered_rows']+=1
                    need(not binary.read(1),'canonical raw EOF')
                need(len(calls)==world['current_call_count']and len(registered)==world['registered_native_rows'],'canonical counts')
                totals['canonical_calls']+=len(calls)
                metadata=[p for p in inventory if p.name in(prefix+'.first_wrapper_observed.json',prefix+'.source_cached_final.json')]
                source_files={}
                for mp in metadata:
                    issued=json.loads(mp.read_bytes())
                    files={f['id']:f for f in issued['data'].get('files',[])}
                    if files:
                        if source_files:need(typed({i:f['spec']for i,f in files.items()},{i:f['spec']for i,f in source_files.items()}),'immutable descriptor continuity')
                        source_files=files
                for row in calls:
                    if 'query'not in row:continue
                    parsed=registered[row['ordinal']]
                    need(parsed['file_id']in source_files,'query has genuine snapshot descriptor provenance')
                    need(Path(row['query']['path']).read_bytes()==query_expected(parsed,source_files[parsed['file_id']]),'every query byte including partial snapshots')
                for mp in metadata:
                    location=mp.name;m=json.loads(mp.read_bytes());totals['snapshots']+=1
                    policy=m['data']['manifest_policy'];live=world['policy_observation']
                    need(set(policy)=={'attempted','prepared_report','issued_report','execution_eligible','error_identity'},'snapshot exact five policy data fields')
                    for name in('attempted','prepared_report','issued_report','execution_eligible'):
                        need(typed(policy[name],live[name]),'immutable snapshot policy values versus retained canonical fields')
                    if live['original_error']is None:need(policy['error_identity']is None,'no fabricated policy error token')
                    else:
                        need(policy['error_identity']is not None,'policy original error token retained')
                        need(typed(policy['error_identity'],m['data']['errors']['primary']['identity']),'policy/primary opaque token same identity label')
                    totals['snapshot_policy_copies']+=1
                    label=m['label'];rp=ART/(prefix+'.'+label+'.native-rows.bin');jp=ART/(prefix+'.'+label+'.native-rows.jsonl');snaps=[]
                    files={f['id']:f for f in m['data'].get('files',[])}
                    with rp.open('rb')as binary,jp.open('r',encoding='utf-8')as text:
                        for line in text:
                            record=json.loads(line);raw=binary.read(256);parsed=parse_row(raw);index=parsed['ordinal'];facts=record['facts']
                            need(record['index']==len(snaps)and facts['ordinal']==index,'snapshot ordinal')
                            need(index in rawrows and raw==rawrows[index],'immutable row versus existing final bank')
                            need(typed(record['axes'],parsed['axes']),'snapshot decoded axes')
                            canonical=calls[index]
                            need(facts['api']==canonical['api']and facts['invoked']is canonical['invoked']and facts['wrapper_return']is canonical['wrapper_return_observed']and facts['wrapper_state']==canonical['wrapper_state']and facts['stopped']is canonical['stopped'],'snapshot wrapper/stop facts')
                            for short,long in(('read_fold','read_fold'),('hash_fold','hash_fold'),('copy_fold','copy_fold')):need(facts[short]==canonical[long],'snapshot fold facts')
                            for clock in('pre_clock','post_clock'):need(typed(facts[clock],snapshot_clock(canonical[clock])),'clock raw type/value/bits')
                            tag='HANDLE'if parsed['api_id']==1 else'DWORD'if parsed['api_id']in(2,4)else'BOOL32'
                            for name,key,at in(('scalar','scalar',tag),('count','count','COUNT32'),('error_value','error','DWORD'),('error_definition','error_definition','BOOL')):
                                need(typed(facts[key],native_atom(parsed['axes'][name],at)),'copied authoritative atom')
                                need(typed(facts['python_delivery'][name],delivery_atom(canonical['python_delivery'][name],at)),'copied separate Python delivery')
                            need(facts['python_delivery']['authority']=='PYTHON_DELIVERY_ONLY_NOT_NATIVE_COMMIT','delivery authority label')
                            if 'query'in canonical:
                                q=Path(canonical['query']['path']).read_bytes();f=files[parsed['file_id']]
                                need(q==query_expected(parsed,f),'query bytes versus declared source snapshot file')
                            snaps.append((parsed,facts));totals['copied_rows']+=1;totals['axis_copies']+=4
                        need(not binary.read(1),'snapshot raw EOF')
                    need(len(snaps)==m['raw_call_count']and m['copied_native_bytes']==256*len(snaps),'snapshot copy bytes/count')
                    if not m['partial_capture']:
                        counters={api:dict(reserved=0,invocations=0,scalar_returns=0,count_values=0,wrapper_returns=0)for api in APIS}
                        groups={i:dict(known=0,hashed=0,copied=0,unknown=False)for i in files}
                        for parsed,facts in snaps:
                            a=parsed['axes'];counter=counters[parsed['api']];counter['reserved']+=1;counter['invocations']+=int(facts['invoked']);counter['scalar_returns']+=int(a['scalar']['native_state']=='COMMITTED');counter['count_values']+=int(a['count']['native_state']=='COMMITTED');counter['wrapper_returns']+=int(facts['wrapper_return'])
                            if parsed['api_id']==6:
                                defined=a['scalar']['native_state']=='COMMITTED'and a['scalar']['known_value']!=0 and a['count']['native_state']=='COMMITTED'and a['count']['known_value']<=parsed['requested'];g=groups[parsed['file_id']]
                                if defined:
                                    n=a['count']['known_value'];g['known']+=n;g['hashed']+=n*int(facts['hash_return_observed']);g['copied']+=n*int(facts['copy_return_observed'])
                                if facts['invoked']and not defined:g['unknown']=True
                        need(typed(counters,m['data']['api_counters']),'snapshot API counters from native rows')
                        for i,f in files.items():
                            g=groups[i]
                            need(f['known_read_bytes']==g['known']and f['hashed_bytes']==g['hashed']and f['captured_bytes']==g['copied']and f['read_count_unknown']is g['unknown'],'snapshot file byte projection')
                        bt=m['data']['byte_totals'];need(bt['known_read_bytes']==sum(g['known']for g in groups.values())and bt['hashed_bytes']==sum(g['hashed']for g in groups.values())and bt['captured_bytes']==sum(g['copied']for g in groups.values())and bt['read_count_unknown']is any(g['unknown']for g in groups.values()),'snapshot total byte projection')
                        totals['complete_snapshot_projections']+=1
                per_world.append(dict(branch=branch['branch'],world=wi,canonical_calls=len(calls),registered_rows=len(registered),snapshots=len(metadata)))
        examined=[dict(path=str(p),bytes=v['bytes'],sha256=v['sha256'])for p,v in inventory.items()]
    except BaseException as error:
        failure=dict(class_name=type(error).__name__,message=str(error),location=location)
    result=dict(schema_version=1,status='PASS'if failure is None else'REVIEW_CHECKER_FAILURE_RETAINED_NOT_SOURCE_RESULT',proof=pin(PROOF),checker=pin(Path(__file__)),totals=totals,failure=failure,worlds=per_world,artifact_hashes_verified=examined,activity=dict(subject_imports=0,subject_invocations=0,native_or_target_operations=0),scope='Retained synthetic evidence byte checks only; no full entry/native/physical/scientific authority.')
    with OUT.open('x',encoding='utf-8')as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(status=result['status'],proof=pin(OUT),totals=totals,failure=failure)))
    return 0 if failure is None else 1


if __name__=='__main__':raise SystemExit(main())
