"""Focused synthetic before-fix witnesses; never actual old archive bytes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'captured_archive_v1.py'
OUT=HERE/'CAPTURED-NATIVE-ARCHIVE-SELF-REVIEW-BEFORE-v2.json'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')+b'\n'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=sha(raw))
def main():
    assert not OUT.exists(),'Preserve witness'
    spec=importlib.util.spec_from_file_location('archive_before_narrow_correction',SOURCE);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    fixture=HERE/'CAPTURED-NATIVE-ARCHIVE-FIXTURES-v3.json';case=json.loads(fixture.read_text(encoding='utf-8'))['cases'][0]
    c=case['captured'];b=case['bindings'];p=lambda v:m.MetadataPin(**v)
    captured=m.CapturedArchive(bytes.fromhex(c['protocol_hex']),bytes.fromhex(c['authority_hex']),tuple((x['locator'],bytes.fromhex(x['raw_hex'])) for x in c['run_files']))
    bindings=m.ArchiveBindings(b['policy_id'],b['run_root'],p(b['protocol_pin']),p(b['authority_pin']),p(b['helper_pin']),tuple(map(p,b['static_software_pins'])),tuple(m.DynamicPin(x['role'],p(x['pin'])) for x in b['dynamic_pins']),tuple(map(p,b['payload_descriptors'])))
    total=[0]
    def count():total[0]+=1
    m.check_archive(captured,bindings,check=count)
    swallowed=None
    for threshold in range(1,min(total[0],2048)+1):
        marker=ValueError('synthetic callback must propagate once');seen=[0];raised=[False]
        def deadline():
            seen[0]+=1
            if seen[0]==threshold:raised[0]=True;raise marker
        try:result=m.check_archive(captured,bindings,check=deadline).to_dict()
        except BaseException as e:
            assert e is marker
        else:
            if raised[0]:swallowed=dict(threshold=threshold,callback_calls=seen[0],returned_status=result['captured_graph_status'],issues=result['issues']);break
    assert swallowed is not None,'Current source did not reproduce suspected callback swallowing'
    files=dict(captured.run_files);files['execution/child/attempt.json']+=b'\n'
    def metadata(raw):return dict(bytes=len(raw),sha256=sha(raw))
    def anchored(name):return dict(path=b['run_root']+'\\'+name.replace('/','\\'),**metadata(files[name]))
    receipt=json.loads(files['receipt.json']);receipt['outputs']={key:metadata(files[key]) for key in receipt['outputs']};files['receipt.json']=canonical(receipt)
    cleanup=json.loads(files['post-lease-cleanup.json']);cleanup['earlier_receipt']=anchored('receipt.json');files['post-lease-cleanup.json']=canonical(cleanup)
    seal=json.loads(files['terminal-seal.json']);seal['earlier_receipt']=anchored('receipt.json');seal['cleanup_artifact']=anchored('post-lease-cleanup.json');seal['outputs']={key:metadata(files[key]) for key in seal['outputs']};files['terminal-seal.json']=canonical(seal)
    malformed=m.CapturedArchive(captured.protocol_bytes,captured.authority_bytes,tuple(files.items()))
    second=m.check_archive(malformed,bindings,check=lambda:None).to_dict()
    assert second['captured_graph_status']=='consistent_captured_graph','Current source did not reproduce extra-LF acceptance'
    value=dict(schema_version=1,status='TWO_NARROW_SELF_REVIEW_FINDINGS_REPRODUCED_BEFORE_CORRECTION',source=pin(SOURCE),fixtures=pin(fixture),recorder=pin(Path(__file__)),
        earlier_passed_proof=pin(HERE/'CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v1.json'),
        findings=[dict(id='callback_ValueError_swallowed',observed=swallowed,expected='Exact callback exception propagates immediately, never a graph result'),
            dict(id='child_marker_extra_LF',observed=second['captured_graph_status'],expected='Strict source child marker has exactly one terminalLF',method='Changed attempt bytes and independently rebound receipt,cleanup,terminal hashes/maps; no stale digest shortcut')],
        profile_qualified=False,old_archive_replay=False,original_payload_operations=0,SDK_OS_native_calls=0)
    with OUT.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(pin(OUT)))
if __name__=='__main__':main()
