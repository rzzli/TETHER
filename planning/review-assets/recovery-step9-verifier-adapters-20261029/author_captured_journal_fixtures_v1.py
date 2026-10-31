"""Literal source-format fixtures BEFORE journal checker implementation.

This is a synthetic writer, not a checker. It serializes authored source event
projections using the documented RunJournal hash format; it never imports that
writer, a native parent, SDK, or any original runtime artifact.
"""
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import struct

HERE=Path(__file__).resolve().parent
CONTRACT=HERE/'CAPTURED-JOURNAL-CONTRACT-v1.json'
FIXTURES=HERE/'CAPTURED-JOURNAL-FIXTURES-v1.json'
FREEZE=HERE/'CAPTURED-JOURNAL-FIXTURE-FREEZE-v1.json'
POLICY='detached-recognition-parent-v7-known-launched-journal-v1'
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=sha(raw))
def chain(events):
    raw=[];previous=None
    for index,(name,details) in enumerate(events):
        row=dict(sequence=index,event=name,details=details,previous_sha256=previous)
        row['sha256']=sha(canonical(row));previous=row['sha256'];raw.append(canonical(row)+b'\n')
    return b''.join(raw)
def snapshot(total,active,pids,ordinal):
    names=('TotalUserTime','TotalKernelTime','ThisPeriodTotalUserTime','ThisPeriodTotalKernelTime',
        'TotalPageFaultCount','TotalProcesses','ActiveProcesses','TotalTerminatedProcesses')
    values=(0,0,0,0,0,total,active,0)
    return dict(query_started_monotonic_ns=ordinal*1000000,query_finished_monotonic_ns=ordinal*1000000+10,
        accounting=dict(ok=True,error=0,returned_bytes=48,raw_hex=struct.pack('<qqqqIIII',*values).hex(),decoded=dict(zip(names,values))),
        pid_list=dict(ok=True,error=0,returned_bytes=8+8*len(pids),raw_hex=struct.pack('<II16Q',active,len(pids),*(pids+[0]*(16-len(pids)))).hex(),
            assigned_count=active,listed_count=len(pids),pids=pids))
def native_fixture(negative=False):
    limits=dict(parent_seconds=300,child_seconds=120,child_cleanup_reserved_seconds=2,finalization_reserved_seconds=5,
        process_and_job_commit_bytes=268435456,active_processes=1,maximum_children=1,stream_bytes=65536,
        maximum_job_snapshots=40,job_pid_capacity=16,attempt_bytes=4096,result_bytes=8388608,row_bytes=65536)
    joblimits=dict(flags=8968,active_limit=1,process_commit=268435456,job_commit=268435456,peak_process_commit=2097152,peak_job_commit=2097152)
    filedata=[('D:\\synthetic\\helper.py','software',b'pure source\n'),('D:\\synthetic\\ggml-cpu-x64.dll','CPU',b'cpu'),
        ('D:\\synthetic\\shard1.gguf','model',b'a'),('D:\\synthetic\\shard2.gguf','model',b'b'),('D:\\synthetic\\shard3.gguf','model',b'c'),
        ('D:\\synthetic\\recognition.pack','pack',b'pack'),('D:\\synthetic\\protocol.json','software',b'{}'),
        ('D:\\synthetic\\run\\effective-protocol.json','software',b'{}')]
    files=[dict(path=p,role=r,bytes=len(b),sha256=sha(b)) for p,r,b in filedata]
    argv=['D:\\synthetic\\recognizer.exe','--recognize','D:\\synthetic','D:\\synthetic\\run\\execution\\child',
        'D:\\synthetic\\recognition.pack','ggml-cpu-x64.dll','D:\\synthetic\\shard1.gguf','D:\\synthetic\\shard2.gguf','D:\\synthetic\\shard3.gguf']
    environment={'TEMP':'D:\\synthetic\\run','TMP':'D:\\synthetic\\run'}
    failure=dict(error_class='RuntimeError',error='Synthetic negative\u0085\u2028\u2029profile; not an actual run.') if negative else None
    finalstatus='failed' if negative else 'recognition_observations_retained_independent_qualification_pending'
    creation=dict(setup_attempted=True,api_attempt_reserved=True,return_observed=True,returned_success=True)
    resumption=dict(create_attempted=True,creation=creation,creation_state='observed_creation_success',job_membership_observed=True,
        resume_attempted=True,resume_return_observed=True,previous_suspend_count=1,state='observed_resumed')
    finalraw=snapshot(1,0,[],4)
    hashes=[]
    for repeat in range(2):
        for item in files:
            hashes.append(dict(path=item['path'],role=item['role'],expected_bytes=item['bytes'],known_returned_bytes=item['bytes'],
                computed_sha256=item['sha256'],hash_complete=True,status='verified',pending_read=False))
    captures={name:dict(eof=True,truncated=False,observed_bytes_at_least=0,retained_bytes=0) for name in ('stdout','stderr')}
    terminal=dict(complete=True,exit_observed=True,interrupted=False,observations=dict(
        capture_drain={name:dict(status='already_observed_EOF',eof=True,polls_reserved=0,calls=[]) for name in ('stdout','stderr')},
        job_snapshot=dict(status='returned',attempt_reserved=True,call_attempted=True,return_observed=True,ordinal=4,
            raw=finalraw,value=finalraw,raw_publication='returned',predicate='passed'),
        memory_limits_and_peaks=dict(status='returned',attempt_reserved=True,call_attempted=True,return_observed=True,value=joblimits)),errors=[])
    report=dict(schema_version=1,status=finalstatus,failure=failure,returncode=2 if negative else 0,call_return_observed=True,reaped=True,
        resumption=resumption,role_hash_records=hashes,
        final_input_recheck=dict(status='completed',new_read_leases=len(files),closed_recheck_leases=len(files),
            outcomes=[dict(path=i['path'],read_lease_reserved=True,return_observed=True,close_return_observed=True) for i in files]),
        final_job_snapshot=finalraw,terminal_observation=terminal,captures=captures)
    bindings=dict(schema_version=1,policy_id=POLICY,journal_sha256=None,
        parent_reservation=dict(owner_pid=7000,created_at_utc='2026-10-29T00:00:00+00:00',status='reserved_before_journal_or_native_API'),
        protocol_sha256=sha(b'{}'),parent_limits=limits,ordered_files=files,argv=argv,environment=environment,
        expected_executable=argv[0],parent_report=report)
    events=[('build_reserved',dict(run_id='00000000-0000-4000-8000-000000000001',owner_pid=7000,created_at_utc='2026-10-29T00:00:01+00:00')),
        ('detached_recognition_attempt_reserved',dict(protocol_sha256=bindings['protocol_sha256'],limits=limits))]
    def epoch():
        for item in files:
            events.extend([('recognition_lease_attempt_reserved',dict(path=item['path'],role=item['role'])),
                ('recognition_file_hash_reserved',dict(path=item['path'],role=item['role'],expected_bytes=item['bytes'],pending_tail='unknown_until_successful_file_hash_return')),
                ('recognition_file_hash_returned',dict(path=item['path'],role=item['role'],bytes=item['bytes'],sha256=item['sha256']))])
    epoch()
    events.extend([
        ('abi_job_snapshot_observed',dict(stage='configured_empty',ordinal=1,snapshot=snapshot(0,0,[],1))),
        ('abi_job_configured_empty',dict(limits=dict(joblimits,peak_process_commit=0,peak_job_commit=0))),
        ('abi_create_suspended_reserved',dict(argv=argv,environment=environment,creation_flags=0x8040C)),
        ('abi_CreateProcessW_reserved',dict(attribute_count=2,attribute_keys=[131074,131085],noninherited_job_handle=2001)),
        ('abi_created_suspended',dict(pid=101,thread_id=102)),
        ('abi_job_snapshot_observed',dict(stage='before_resume',ordinal=2,snapshot=snapshot(1,1,[101],2))),
        ('abi_assigned_before_resume',dict(identity=dict(pid=101,thread_id=102,image=argv[0],creation_filetime=123456789000000000,directly_created_suspended=True),
            limits=joblimits,assigned_during_CreateProcessW=True,manual_assignment_fallback=False)),
        ('abi_resume_reserved',dict(pid=101)),('abi_resume_returned',dict(previous_suspend_count=1)),
        ('abi_job_snapshot_observed',dict(stage='running_first',ordinal=3,snapshot=snapshot(1,1,[101],3))),
        ('detached_ABI_terminal_call_reserved',dict(observation='terminal_job_snapshot')),
        ('abi_job_snapshot_observed',dict(stage='after_wait',ordinal=4,snapshot=finalraw)),
        ('detached_ABI_terminal_call_reserved',dict(observation='terminal_memory_limits_and_peaks')),
    ])
    epoch();events.append(('detached_recognition_terminal',dict(status=finalstatus,failure=failure)))
    return events,bindings

def main():
    assert not FIXTURES.exists() and not FREEZE.exists(),'Preserve preimplementation fixtures'
    cases=[]
    def add(identity,events=None,bindings=None,raw=None,chain_valid=True,native_complete=False,family=None,kind='literal',recipe=None):
        if raw is None:raw=chain(events)
        bindings=copy.deepcopy(bindings)
        if bindings is not None:bindings['journal_sha256']=sha(raw)
        cases.append(dict(id=identity,kind=kind,raw_hex=raw.hex() if kind=='literal' else None,bytes=len(raw),sha256=sha(raw),recipe=recipe,
            bindings=bindings,expected_chain_valid=chain_valid,expected_native_complete=native_complete,error_family=family,
            real_profile_qualified=False))
    events,bindings=native_fixture();negative,negativebindings=native_fixture(True)
    add('valid/native_positive',events,bindings,native_complete=True)
    add('valid/native_consistent_negative_with_unicode_separators',negative,negativebindings,native_complete=True)
    app=[('run_reserved',events[0][1]),('synthetic_application_event',{'note':'Writer envelope only; no native meaning.'})]
    add('valid/application_chain_only',app,bindings,native_complete=False,family='outside_native_policy')
    base=chain(events)
    for identity,raw in [('missing_final_LF',base[:-1]),('BOM',b'\xef\xbb\xbf'+base),('CRLF',base.replace(b'\n',b'\r\n')),
        ('blank_record',base+b'\n'),('invalid_UTF8',base.replace(b'build_reserved',b'build_\xffreserved',1))]:
        add('framing/'+identity,bindings=bindings,raw=raw,chain_valid=False,family='framing')
    rows=[json.loads(row) for row in base.split(b'\n') if row]
    changed=copy.deepcopy(rows);changed[1]['previous_sha256']='0'*64
    add('chain/wrong_previous',bindings=bindings,raw=b''.join(canonical(row)+b'\n' for row in changed),chain_valid=False,family='chain')
    changed=copy.deepcopy(rows);changed[1]['sha256']='0'*64
    add('chain/wrong_digest',bindings=bindings,raw=b''.join(canonical(row)+b'\n' for row in changed),chain_valid=False,family='chain')
    first=canonical(rows[0])
    add('JSON/duplicate_name',bindings=bindings,raw=first[:-1]+b',"sequence":0}\n'+base[len(first)+1:],chain_valid=False,family='JSON')
    add('JSON/nonfinite',bindings=bindings,raw=first.replace(b'"sequence":0',b'"sequence":NaN')+b'\n',chain_valid=False,family='JSON')
    changed=copy.deepcopy(rows);changed[0]['sequence']=False;unsigned={k:v for k,v in changed[0].items() if k!='sha256'};changed[0]['sha256']=sha(canonical(unsigned))
    add('types/bool_sequence',bindings=bindings,raw=b''.join(canonical(row)+b'\n' for row in changed),chain_valid=False,family='counter_type')
    add('canonical/outside_whitespace',bindings=bindings,raw=first.replace(b',',b', ',1)+b'\n'+base[len(first)+1:],chain_valid=False,family='canonical')
    def event_attack(identity,mutator,family):
        value=copy.deepcopy(events);mutator(value);add('native/'+identity,value,bindings,native_complete=False,family=family)
    event_attack('protocol_mismatch',lambda e:e[1][1].update(protocol_sha256='0'*64),'reference')
    event_attack('bool_created_PID',lambda e:next(d for n,d in e if n=='abi_created_suspended').update(pid=True),'counter_type')
    event_attack('bool_hash_bytes',lambda e:next(d for n,d in e if n=='recognition_file_hash_returned').update(bytes=True),'counter_type')
    event_attack('hash_source_mismatch',lambda e:next(d for n,d in e if n=='recognition_file_hash_returned').update(sha256='0'*64),'reference')
    event_attack('unknown_event',lambda e:e.insert(2,('dispatch',dict(ready=True))),'source_order')
    event_attack('duplicate_resume',lambda e:e.insert(next(i for i,(n,d) in enumerate(e) if n=='abi_resume_returned'),('abi_resume_reserved',dict(pid=101))),'source_order')
    def swap(e):
        a=next(i for i,(n,d) in enumerate(e) if n=='abi_created_suspended');b=next(i for i,(n,d) in enumerate(e) if n=='abi_resume_reserved');e[a],e[b]=e[b],e[a]
    event_attack('reordered_creation_resume',swap,'source_order')
    event_attack('terminal_disagrees_report',lambda e:e[-1][1].update(status='failed',failure=dict(error_class='RuntimeError',error='Unbound')),'reference')
    event_attack('snapshot_disagrees_report',lambda e:next(d for n,d in e if n=='abi_job_snapshot_observed' and d['stage']=='after_wait')['snapshot'].update(query_finished_monotonic_ns=999999999),'reference')
    add('incomplete/no_terminal',events[:-1],bindings,family='incomplete_scope')
    add('incomplete/prelaunch_prefix',events[:2],bindings,family='incomplete_scope')
    badbinding=copy.deepcopy(bindings);badbinding['already_verified']=True
    add('bindings/unknown_ready_flag',events,badbinding,family='binding_schema')
    large=[('build_reserved',dict(events[0][1],note='x'*65536))]
    add('caps/row',large,bindings,chain_valid=False,family='row_cap')
    many=[('build_reserved',events[0][1])]+[('synthetic',{})]*2048
    add('caps/events',many,bindings,chain_valid=False,family='event_cap')
    nested=0
    for _ in range(63):nested=[nested]
    add('caps/nesting',[('build_reserved',dict(events[0][1],nested=nested))],bindings,chain_valid=False,family='depth_cap')
    # Fixed recipe avoids embedding a16MiB hex string in this small fixture file.
    too_big=b'\n'*(8388608+1)
    add('caps/input',bindings=bindings,raw=too_big,chain_valid=False,family='input_cap',kind='fixed_recipe',recipe=dict(byte_hex='0a',repeat=8388609))
    value=dict(schema_version=1,status='FROZEN_LITERAL_SOURCE_FORMAT_EXPECTATIONS_BEFORE_CHECKER_CODE',contract=pin(CONTRACT),
        cases=cases,synthetic_only=True,
        source_scope='Eight tiny fictitious file-role records and source-format report projections are test metadata, not real execution configuration/admission/model artifacts.',
        method='Authored native source order/details/projections, writer-style canonical chain serialization, then explicitly labeled byte or rechained semantic faults.',
        clocks='Future pure tests must inject deadlines at bounded hash/parse/semantic points; no actual clocks/profile execution is present.',
        native_resource_truth='Raw snapshot fields have actual SDK record shape but are invented bytes. Resource semantics remain a separate checker gate.',
        live_original_or_payload_reads=0,SDK_native_compiler_calls=0,checker_implemented=False)
    with FIXTURES.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,ensure_ascii=True,indent=2);out.write('\n')
    freeze=dict(schema_version=1,status='CONTRACT_AND_LITERAL_FIXTURES_FROZEN_BEFORE_IMPLEMENTATION',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        contract=pin(CONTRACT),spec=pin(HERE/'CAPTURED-JOURNAL-SPEC-v1.md'),fixtures=pin(FIXTURES),generator=pin(Path(__file__)),
        fixture_count=len(cases),literal_fixtures=sum(c['kind']=='literal' for c in cases),fixed_recipes=sum(c['kind']=='fixed_recipe' for c in cases),
        maximum_literal_bytes=max(c['bytes'] for c in cases if c['kind']=='literal'),base_native_events=len(events),file_bindings=8,
        source_note='No checker implementation exists; only this synthetic fixture writer ran. No actualRunJournal/SDK/parent helper or oldartifact was imported/opened.',
        implementation_authorized=False,execution_authorized=False,real_profile_qualified=False)
    with FREEZE.open('x',encoding='utf-8') as out:json.dump(freeze,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(freeze=pin(FREEZE),fixtures=pin(FIXTURES),count=len(cases),base_events=len(events))))
if __name__=='__main__':main()
