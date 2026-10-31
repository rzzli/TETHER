"""Finite independent inspection of frozen fixture metadata; no mock/port execution."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE/'FILE-PORTS-FIXTURE-INDEPENDENT-PEER-v3.json'
NOTE = HERE/'FILE-PORTS-FIXTURE-INDEPENDENT-PEER-v3.md'
EXPECTED = {
    'FILE-PORTS-DESIGN-CONTRACT-v2.json':'d2c775cb9e24dce90f2dc0cc97d7976567d94a1e147e1f57be72f7a5d21efd4d',
    'FILE-PORTS-FIXTURE-SCHEMA-v3.json':'e3069b89cca7e9b04c630de994f24392054daf341c280f50778aea3d0f81657b',
    'FILE-PORTS-FIXTURES-v3.json':'9e445e2e230689aa7c36e7eba666959dcac87478caf27252154eb02e978109b7',
    'file_port_fixture_script_v2.py':'d6ec279a90b5424d30a2239a7305d04b8cbd059dbff6bbf3107c4cfb9c503e51',
    'check_file_port_fixture_script_v2.py':'ca8b4ab2a9ed51cd55f50c682b62f63c31281b87916bc35583f2e265e5e4f7bd',
    'FILE-PORTS-FIXTURE-CALLABLE-PROOF-v2.json':'6df42b04e9c21fa22c9ee398dfb72b55c0c57b691144f9717288cc193ec8d094',
    'FILE-PORTS-FIXTURE-CALLABLE-FREEZE-v2.json':'1a47880ade1119bae93c1b242238d9d2d9b012c784a9513f86120a16ceac2bd0',
    'FILE-PORTS-FIXTURE-INDEPENDENT-PRECHECK-v2.json':'9a40bc4367be182c9887172743fb79213c7fa48929c8bd5dca92a8e695f2e0e4',
}

def pin(name):
    path=HERE/name; raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def read(name):
    return json.loads((HERE/name).read_text(encoding='utf-8'))

def main():
    assert not OUT.exists() and not NOTE.exists(), 'Preserve first review'
    pins={name:pin(name) for name in EXPECTED}
    assert all(pins[name]['sha256']==expected for name,expected in EXPECTED.items())
    fixture=read('FILE-PORTS-FIXTURES-v3.json'); old=read('FILE-PORTS-FIXTURES-v2.json')
    schema=read('FILE-PORTS-FIXTURE-SCHEMA-v3.json'); cases=fixture['cases']; by={c['id']:c for c in cases}
    assert len(cases)==len(by)==84
    assert [c['id'] for c in cases]==[c['id'] for c in old['cases']]
    assert set(c['required_vector'] for c in cases if c['required_vector'] is not None)==set(range(17))
    assert sum(c['required_vector'] is None for c in cases)==15
    for new,prior in zip(cases,old['cases']):
        assert new['script']==prior['script'] and new['expected']==prior['expected']
        assert new['initial']==prior['initial'] and new['path_records']==prior['path_records']
        assert set(new)==set(schema['case_exact_keys'])
        assert set(new['initial'])==set(schema['initial_exact_keys'])
        assert set(new['expected'])==set(schema['expected_exact_keys'])
        assert all(new['expected'][k] is False for k in ('profile_qualified','runtime_authorized','originals_authenticated','terminal_ack'))
    plan_checks=[]
    for c in cases:
        p=c['plan']; computed=6*p['N']+2*p['B']+2*p['M']+4*p['S']+161
        ri=sum(0 if n==0 else (n+65535)//65536+16 for n in p['file_byte_sizes'])
        assert len(p['file_byte_sizes'])==p['N'] and p['S']==sum(p['Dk'])
        assert (p['E']!=computed)==(c['id']=='admission_E')
        assert (p['sumRi']!=ri)==(c['id']=='admission_read')
        assert (p['sumWj']!=computed+412)==(c['id']=='admission_write')
        for action in c['request']['actions']:
            args=action['arguments']; assert 'fault' not in args and 'over_cap' not in args
            if action['operation']=='admit_plan' and c['required_vector']==10:assert args=={'plan_ref':'case.plan'}
            if action['operation'] in ('validate_handoff','validate_seal_graph'):assert args=={'facts_ref':'case.request.facts'}
        if c['required_vector']==10:
            assert c['initial']['known_read_bytes']==3 and c['initial']['slots'][0]['id']=='b0'
            assert c['expected']['api_attempts']['CreateFileW']==0 and c['expected']['api_attempts']['ReadFile']==0
            plan_checks.append(dict(id=c['id'],computed_E=computed,computed_sumWj=computed+412,computed_sumRi=ri))
    assert 6*256+2*16+2*16+4*16+161==1825
    dag_facts=[]
    for name in ('DAG_acyclic','DAG_self_hash','DAG_same_path','DAG_unknown_veto'):
        facts=by[name]['request']['facts']; nodes=facts['nodes']; ids={n['id'] for n in nodes}
        assert set(facts)=={'nodes','edges','operation_outcomes'} and len(ids)==5
        assert all(set(n)=={'id','path','bytes','sha256'} and n['bytes']==17 and len(n['sha256'])==64 for n in nodes)
        assert all(a in ids and b in ids for a,b in facts['edges'])
        self_edge=any(a==b for a,b in facts['edges'])
        aliases=len({n['path'].lower() for n in nodes})<len(nodes)
        unknown=any(o['state']!='returned_success' for o in facts['operation_outcomes'])
        assert self_edge==(name=='DAG_self_hash') and aliases==(name=='DAG_same_path') and unknown==(name=='DAG_unknown_veto')
        dag_facts.append(dict(id=name,self_edge=self_edge,same_path=aliases,unknown_operation=unknown))
    api_total=unreturned=0
    for c in cases:
        e=c['expected']; r=c['initial']['known_read_bytes']; h=c['initial']['hashed_bytes']; cap=c['initial']['captured_bytes']
        w=wh=fl=0; pending=None;written={};flushed={};closes={};previous=0; attempts={n:0 for n in schema['step_union']['api_names']}; returns=dict(attempts)
        for record in c['path_records']:assert record['utf16_units']==len(record['path'].encode('utf-16-le'))//2
        for step in c['script']:
            if step['kind']=='clock':assert type(step['now_ns']) is int and previous<=step['now_ns']<=600000000000;previous=step['now_ns']
            if step['kind']=='api':
                assert previous<300000000000
                name=step['name'];a=step['arguments'];o=step['outcome'];raw=o['raw_return'];api_total+=1;attempts[name]+=1
                if o['raise'] is not None:unreturned+=1;assert raw is None
                else:
                    returns[name]+=1; val=raw['value']
                    if name in ('CreateFileW','FindFirstFileExW'):assert val is None or type(val) is int and 0<=val<2**64
                    elif name in ('GetFileType','GetFinalPathNameByHandleW'):assert type(val) is int and 0<=val<2**32
                    else:assert type(val) is int and -2**31<=val<2**31
                if name=='CreateFileW':
                    role=(a['desired_access'],a['share_mode'],a['creation'],a['flags'])
                    assert role in ((2147483648,1,3,2097280),(1073741952,0,1,128))
                    assert a['security'] is None and a['template'] is None
                if name=='GetFileInformationByHandleEx':assert a['info_class']==9 and a['buffer_bytes']==8
                if name=='GetFinalPathNameByHandleW':assert a['capacity']==4101 and a['flags']==0
                if name=='GetFileAttributesExW':assert a['buffer_bytes']==36 and a['info_level']==0
                if name=='FindFirstFileExW':assert (a['info_level'],a['search_op'],a['search_filter'],a['flags'])==(1,0,None,0)
                if name=='FindNextFileW':assert a['buffer_bytes']==592
                if name in ('ReadFile','WriteFile'):
                    assert a['overlapped'] is None;pending=None
                    if raw and raw['value']!=0 and raw['raw_count_defined']:
                        n=raw['raw_count'];assert type(n) is int
                        pending=(name,n)
                        if name=='ReadFile':assert 0<=n<=a['requested'];r+=n
                        else:assert 0<=n<=len(bytes.fromhex(a['data_hex']));w+=n;written[a['handle']]=written.get(a['handle'],0)+n
                    elif raw:assert raw['raw_count_defined'] is False
                if name=='FlushFileBuffers' and raw and raw['value']!=0:
                    hd=a['handle'];current=written.get(hd,0);fl+=current-flushed.get(hd,0);flushed[hd]=current
                if name in ('CloseHandle','FindClose'):
                    hd=a['handle'];closes[hd]=closes.get(hd,0)+1
                    slots=[s for s in e['slots'] if s['handle']==hd]
                    assert len(slots)==1 and slots[0]['closer']==name
            if step['kind']=='hook' and step['raises'] is None and pending:
                if step['name']=='hash_update':
                    if pending[0]=='ReadFile':h+=pending[1]
                    else:wh+=pending[1]
                elif step['name']=='copy_bytes':cap+=pending[1]
        assert attempts==e['api_attempts'] and returns==e['api_returns']
        assert (r,h,cap,w,wh,fl)==tuple(e[k] for k in ('known_read_bytes','hashed_bytes','captured_bytes','known_write_bytes','write_hash_bytes','flushed_known_bytes'))
        assert all(closes.get(s['handle'],0)==s['close_attempts'] for s in e['slots']) and all(n<=1 for n in closes.values())
    assert (api_total,unreturned)==(189,6)
    left=ast.parse((HERE/'file_port_fixture_script_v1.py').read_text(encoding='utf-8'))
    right=ast.parse((HERE/'file_port_fixture_script_v2.py').read_text(encoding='utf-8'))
    named=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))}
    l,r=named(left),named(right);assert l.keys()==r.keys()
    changed=[name for name in l if l[name]!=r[name]];assert changed==['validate_case']
    proof=read('FILE-PORTS-FIXTURE-CALLABLE-PROOF-v2.json')
    assert proof['status']=='passed' and proof['methods']==10 and proof['inputs_unchanged'] is True
    assert proof['source']==pins['file_port_fixture_script_v2.py'] and proof['checker']==pins['check_file_port_fixture_script_v2.py']
    assert not proof['failures'] and not proof['errors']
    assert all(pin(name)==value for name,value in pins.items())
    note='''# File-port fixture independent peer v3

The corrected schema, 84 literal cases and callable fake interchange are clear for a separate source-implementation decision. The prior finite precheck remains preserved. Admission fields now derive from actual numeric dimensions; E/read/write controls are explicitly forged-derived claims. Guard actions use fixed plan/facts references, and the DAG negatives contain actual self edges, aliased node paths or unknown operation states.

Independent inspection reconstructed all 189 scripted API attempts, six unreturned calls, six byte-count projections and once-only correct closer counts. The earlier API scripts and authored expected ownership/byte outcomes are unchanged. Signed BOOL controls, original/output flags, metadata/UTF16 limits and work-versus-hard cutoff evidence align with the design. The author's ten methods pass; this reviewer did not rerun them or invoke the sequencer.

This clears fictional preparation only. No file-port behavior was evaluated. An injected RawReturn already exists as a Python object: its checkpoints cannot qualify the later FFI wrapper's raw handle/flag/count registration before RawReturn construction. Portable caller ordering, actual typed binding, full bootstrap/checker integration, live namespace behavior, source/resource fit and all profile/science gates remain separate. No API, original, CPU/GGUF/pack or old-archive operation occurred.
'''
    with NOTE.open('x',encoding='utf-8',newline='\n') as f:f.write(note)
    value=dict(schema_version=1,status='CLEAR_FICTIONAL_FIXTURE_PREPARATION_ONLY',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        reviewer='/root/native_039_acceptance_audit',inputs=pins,review_script=pin(Path(__file__).name),note=pin(NOTE.name),
        checks=dict(cases=84,required_families=16,supplemental_BOOL_controls=15,scripted_API_attempts=api_total,scripted_unreturned=unreturned,
                    independent_byte_and_close_disagreements=0,unchanged_previous_API_scripts_and_expected_states=True,
                    derived_plan_cases=plan_checks,concrete_DAG_controls=dag_facts,changed_named_mock_ASTs=changed,
                    unchanged_named_mock_ASTs=[name for name in l if name not in changed],author_methods=10),
        actual_API_calls=0,reviewer_callable_mock_dispatches=0,port_implementation_or_conformance=False,
        actual_FFI_raw_registration_qualified=False,old_original_payload_operations=0,
        originals_authenticated=False,profile_qualified=False,runtime_authorized=False,
        next='Separate root source-only portable implementation decision; later real binding and live qualification remain pending.')
    with OUT.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(dict(peer=pin(OUT.name),note=pin(NOTE.name),literal_cases=84,API_script_steps=api_total)))

if __name__=='__main__':main()
