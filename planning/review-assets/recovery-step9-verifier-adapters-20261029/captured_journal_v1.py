"""Pure captured-byte RunJournal framing and one explicit native-v7 policy.

No filesystem/clock/native calls. Expected bindings must come from the future
owner's fresh captured context; this library does not authenticate that origin.
"""
from datetime import datetime
import hashlib
import json
import math
import re
from types import MappingProxyType

MAX_BYTES=8388608
MAX_ROW=65536
MAX_EVENTS=2048
MAX_DEPTH=64
MAX_BINDING_BYTES=4194304
MAX_BINDING_NODES=65536
POLICY='detached-recognition-parent-v7-known-launched-journal-v1'
LIMITS=dict(parent_seconds=300,child_seconds=120,child_cleanup_reserved_seconds=2,finalization_reserved_seconds=5,
    process_and_job_commit_bytes=268435456,active_processes=1,maximum_children=1,stream_bytes=65536,
    maximum_job_snapshots=40,job_pid_capacity=16,attempt_bytes=4096,result_bytes=8388608,row_bytes=65536)
BIND_KEYS={'schema_version','policy_id','journal_sha256','parent_reservation','protocol_sha256','parent_limits','ordered_files',
    'argv','environment','expected_executable','parent_report'}
REPORT_KEYS={'schema_version','status','failure','returncode','call_return_observed','reaped','resumption','role_hash_records',
    'final_input_recheck','final_job_snapshot','terminal_observation','captures'}
HEX=re.compile(r'^[0-9a-f]{64}$')
EVENT=re.compile(r'^[A-Za-z_][A-Za-z0-9_.:-]{0,127}$')
UUID4=re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
UTC=re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\+00:00$')

class CapturedJournalError(ValueError):
    def __init__(self,message,family='source_order',index=None):
        super().__init__(message[:512]);self.family=family;self.index=index
        self.events_processed=index if type(index) is int else None

def need(value,message,family='source_order',index=None):
    if not value:raise CapturedJournalError(message,family,index)

def uint(value,maximum=2**63-1):return type(value) is int and 0<=value<=maximum
def positive(value,maximum=2**32-1):return uint(value,maximum) and value>0
def digest(value):return type(value) is str and HEX.fullmatch(value) is not None
def exact(a,b):
    if type(a) is not type(b):return False
    if type(a) is dict:return a.keys()==b.keys() and all(exact(a[k],b[k]) for k in a)
    if type(a) is list:return len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b))
    return a==b
def freeze(value,check):
    count=0
    def walk(item):
        nonlocal count
        count+=1
        if count%128==0:check()
        if type(item) is dict:return MappingProxyType({k:walk(v) for k,v in item.items()})
        if type(item) is list:return tuple(walk(v) for v in item)
        return item
    check();result=walk(value);check();return result
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')

def _json(raw,index):
    def pairs(items):
        result={}
        for key,value in items:
            need(key not in result,'Duplicate JSON object name','JSON',index);result[key]=value
        return result
    try:decoded=raw.decode('utf-8','strict')
    except UnicodeError as error:raise CapturedJournalError('Invalid journal UTF8','framing',index) from error
    try:
        return json.loads(decoded,object_pairs_hook=pairs,
            parse_constant=lambda value:(_ for _ in ()).throw(CapturedJournalError('Nonfinite JSON','JSON',index)))
    except CapturedJournalError:raise
    except (ValueError,UnicodeError,RecursionError) as error:raise CapturedJournalError('Invalid scalar UTF8 JSON','JSON',index) from error

def _depth(raw,check,index):
    depth=0;quoted=False;escaped=False
    for pos,byte in enumerate(raw):
        if pos%4096==0:check()
        if quoted:
            if escaped:escaped=False
            elif byte==92:escaped=True
            elif byte==34:quoted=False
        elif byte==34:quoted=True
        elif byte in (91,123):
            depth+=1;need(depth<=MAX_DEPTH,'JSON nesting cap','depth_cap',index)
        elif byte in (93,125):
            depth-=1;need(depth>=0,'Unbalanced JSON container','JSON',index)
    need(depth==0 and not quoted,'Unfinished JSON record','JSON',index);check()

def _parse(raw,check):
    need(callable(check),'Required owner deadline callback','argument')
    check();need(type(raw) is bytes,'Exact captured bytes required','argument')
    need(0<len(raw)<=MAX_BYTES,'Journal input byte cap','input_cap')
    need(not raw.startswith(b'\xef\xbb\xbf') and raw.endswith(b'\n'),'BOM or missing final LF','framing')
    hasher=hashlib.sha256()
    for at in range(0,len(raw),65536):check();hasher.update(raw[at:at+65536]);check()
    records=[];previous=None;start=0
    while start<len(raw):
        check();index=len(records);need(index<MAX_EVENTS,'Journal event cap','event_cap',index)
        end=raw.find(b'\n',start);need(end>=start,'Missing LF','framing',index)
        need(0<end-start<=MAX_ROW,'Empty/oversized journal row','row_cap' if end-start>MAX_ROW else 'framing',index)
        line=raw[start:end];need(not line.endswith(b'\r'),'CRLF is not writer framing','framing',index)
        _depth(line,check,index);record=_json(line,index);check()
        need(type(record) is dict and set(record)=={'sequence','event','details','previous_sha256','sha256'},'Exact journal envelope','JSON',index)
        need(type(record['sequence']) is int and record['sequence']==index,'Strict sequence counter','counter_type',index)
        need(type(record['event']) is str and EVENT.fullmatch(record['event']) is not None,'Event identifier','JSON',index)
        need(type(record['details']) is dict,'Details object required','JSON',index)
        need(digest(record['sha256']),'Lowercase digest required','chain',index)
        need(record['previous_sha256'] is None if index==0 else digest(record['previous_sha256']),'Previous digest shape','chain',index)
        need(record['previous_sha256']==previous,'Previous digest mismatch','chain',index)
        try:encoded=canonical(record)
        except (ValueError,UnicodeError,RecursionError) as error:raise CapturedJournalError('Nonfinite/non-scalar JSON value','JSON',index) from error
        check();need(encoded==line,'Noncanonical journal row','canonical',index)
        unsigned={k:v for k,v in record.items() if k!='sha256'};check()
        need(hashlib.sha256(canonical(unsigned)).hexdigest()==record['sha256'],'Journal digest mismatch','chain',index);check()
        records.append(record);previous=record['sha256'];start=end+1
    need(records,'Empty execution trace','framing');check()
    return records,dict(journal_sha256=hasher.hexdigest(),bytes=len(raw),events=len(records),tip_sha256=previous,
        first_event=records[0]['event'],chain_integrity_validated=True,source_order_validated=False,profile_qualified=False,
        resource_semantics_validated=False,scientific_validation='not_established')

def check_chain(raw,*,check):
    """Writer envelope only; never a native/event-policy or profile pass."""
    records,summary=_parse(raw,check);summary['records']=records;check();return freeze(summary,check)

def _copy_bindings(value,check):
    # Bound the entire object graph BEFORE canonical serialization/traversal.
    count=0;strings=0;active=set()
    def walk(item,depth):
        nonlocal count,strings
        count+=1
        if count%128==0:check()
        need(count<=MAX_BINDING_NODES and depth<=MAX_DEPTH,'Binding graph bounds','binding_schema')
        if item is None or type(item) is bool:return item
        if type(item) is int:
            need(-2**63<=item<2**64,'Binding integer bound','binding_schema');return item
        if type(item) is float:
            need(math.isfinite(item),'Binding finite number required','binding_schema');return item
        if type(item) is str:
            need(len(item)<=MAX_BINDING_BYTES,'Binding string length','binding_schema')
            try:strings+=len(item.encode('utf-8','strict'))
            except UnicodeError as error:raise CapturedJournalError('Binding scalar string required','binding_schema') from error
            need(strings<=MAX_BINDING_BYTES,'Binding aggregate text cap','binding_schema');return item
        need(type(item) in (dict,MappingProxyType,list,tuple),'Plain bounded binding values required','binding_schema')
        need(id(item) not in active,'Binding cycle','binding_schema');active.add(id(item))
        try:
            if type(item) in (dict,MappingProxyType):
                result={}
                for key,child in item.items():
                    need(type(key) is str and key not in ('already_verified','ready','passed'),'Unknown ready/proof binding field','binding_schema')
                    result[walk(key,depth+1)]=walk(child,depth+1)
                return result
            return [walk(child,depth+1) for child in item]
        finally:active.remove(id(item))
    check();copied=walk(value,1);check();need(len(canonical(copied))<=MAX_BINDING_BYTES,'Canonical binding byte cap','binding_schema');check()
    return copied

def _shape(value,keys,message,family='reference'):
    need(type(value) is dict and set(value)==set(keys),message,family)
def _utc(value):
    need(type(value) is str and UTC.fullmatch(value) is not None,'Writer UTC timestamp','reference')
    try:return datetime.fromisoformat(value)
    except ValueError as error:raise CapturedJournalError('Invalid writer UTC timestamp','reference') from error
def _path_key(value):
    need(type(value) is str and 0<len(value)<=32767 and '\0' not in value,'Bounded path metadata','binding_schema')
    return value.replace('/','\\').translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'))
def _job_limits(value):
    _shape(value,('flags','active_limit','process_commit','job_commit','peak_process_commit','peak_job_commit'),'Job limit record')
    for key,expected in dict(flags=8968,active_limit=1,process_commit=268435456,job_commit=268435456).items():
        need(type(value[key]) is int and value[key]==expected,'Source Job limit differs','counter_type')
    need(uint(value['peak_process_commit'],268435456) and uint(value['peak_job_commit'],268435456),'Bounded source peaks','counter_type')

def check_native_v7(raw,bindings,*,check):
    """Exact known-launched v7 order/reference gate; no old run is replayed."""
    rows,summary=_parse(raw,check);b=_copy_bindings(bindings,check)
    _shape(b,BIND_KEYS,'Closed native binding schema','binding_schema')
    need(type(b['schema_version']) is int and b['schema_version']==1 and b['policy_id']==POLICY,'Explicit native-v7 policy required','binding_schema')
    need(digest(b['journal_sha256']) and b['journal_sha256']==summary['journal_sha256'],'Captured journal digest binding','reference')
    _shape(b['parent_reservation'],('owner_pid','created_at_utc','status'),'Parent reservation projection','binding_schema')
    reservation=b['parent_reservation'];need(positive(reservation['owner_pid']) and reservation['status']=='reserved_before_journal_or_native_API','Parent owner reservation','counter_type')
    parent_date=_utc(reservation['created_at_utc'])
    need(digest(b['protocol_sha256']) and exact(b['parent_limits'],LIMITS),'Exact protocol/parent-limit bindings','binding_schema')
    need(type(b['argv']) is list and len(b['argv'])==9 and all(type(v) is str and v and '\0' not in v for v in b['argv'])
        and b['argv'][1]=='--recognize' and b['argv'][0]==b['expected_executable'],'Exact recognition argv binding','binding_schema')
    need(type(b['environment']) is dict and all(type(k) is str and type(v) is str for k,v in b['environment'].items()),'Environment projection','binding_schema')
    files=b['ordered_files'];need(type(files) is list and 1<=len(files)<=256,'File epoch bound','binding_schema');paths=set()
    for item in files:
        check();_shape(item,('path','role','bytes','sha256'),'File projection','binding_schema');key=_path_key(item['path'])
        need(key not in paths and item['role'] in ('software','CPU','model','pack') and uint(item['bytes']) and digest(item['sha256']),'Strict unique file binding','binding_schema');paths.add(key)
    report=b['parent_report'];_shape(report,REPORT_KEYS,'Closed parent report projection','binding_schema')
    need(type(report['schema_version']) is int and report['schema_version']==1 and report['call_return_observed'] is True and report['reaped'] is True,'Observed/reaped parent reference','reference')
    need(uint(report['returncode'],2**32-1),'Observed exit code','counter_type')
    if report['status']=='recognition_observations_retained_independent_qualification_pending':
        need(report['failure'] is None and report['returncode']==0,'Positive source terminal reference','reference')
    else:
        need(report['status']=='failed' and type(report['failure']) is dict and report['failure'],'Failed source terminal reference','reference')
    hashes=report['role_hash_records'];need(type(hashes) is list and len(hashes)==2*len(files),'Two complete source hash-reference epochs','reference')
    recheck=report['final_input_recheck'];_shape(recheck,('status','new_read_leases','closed_recheck_leases','outcomes'),'Recheck projection')
    need(recheck['status']=='completed' and type(recheck['new_read_leases']) is int and recheck['new_read_leases']==len(files)
        and type(recheck['closed_recheck_leases']) is int and recheck['closed_recheck_leases']==len(files)
        and type(recheck['outcomes']) is list and len(recheck['outcomes'])==len(files),'Complete final recheck reference','reference')
    for item,outcome in zip(files,recheck['outcomes']):
        check();_shape(outcome,('path','read_lease_reserved','return_observed','close_return_observed'),'Recheck outcome projection')
        need(outcome['path']==item['path'] and all(outcome[k] is True for k in ('read_lease_reserved','return_observed','close_return_observed')),'Known recheck outcome','reference')
    resumption=report['resumption']
    need(type(resumption) is dict and resumption.get('state')=='observed_resumed' and resumption.get('resume_attempted') is True
        and resumption.get('resume_return_observed') is True and type(resumption.get('previous_suspend_count')) is int
        and resumption['previous_suspend_count']==1 and resumption.get('job_membership_observed') is True,'Resumption source reference','reference')
    terminal=report['terminal_observation']
    need(type(terminal) is dict and terminal.get('complete') is True and terminal.get('exit_observed') is True and terminal.get('interrupted') is False,'Known complete terminal observation required','incomplete_scope')
    observations=terminal.get('observations');need(type(observations) is dict and set(observations)=={'capture_drain','job_snapshot','memory_limits_and_peaks'},'Terminal observation records','reference')
    captures=report['captures'];_shape(captures,('stdout','stderr'),'Capture references')
    calls=[];drains=observations['capture_drain'];_shape(drains,('stdout','stderr'),'Drain references')
    for stream in ('stdout','stderr'):
        capture=captures[stream];need(type(capture) is dict and capture.get('eof') is True and capture.get('truncated') is False
            and uint(capture.get('retained_bytes'),65536) and uint(capture.get('observed_bytes_at_least'))
            and capture['retained_bytes']==capture['observed_bytes_at_least'],'Known capture EOF/count references','reference')
        drain=drains[stream];need(type(drain) is dict and drain.get('eof') is True and type(drain.get('calls')) is list,'Drain source projection','reference')
        for index,call in enumerate(drain['calls']):
            check();need(type(call) is dict and positive(call.get('poll'),64) and all(call.get(k) is True for k in ('attempt_reserved','call_attempted','return_observed')),'Known drain invocation','reference')
            available=call.get('value');need(available is None or uint(available,2**32-1),'Available-byte source result','counter_type')
            item=[('capture_available_'+stream,'/terminal_observation/observations/capture_drain/'+stream+'/calls/'+str(index))]
            if 'read' in call:
                read=call['read'];need(type(available) is int and available>0 and type(read) is dict and all(read.get(k) is True for k in ('attempt_reserved','call_attempted','return_observed')),'Known paired read source result','reference')
                need(type(read.get('value')) is dict and set(read['value'])=={'bytes'} and positive(read['value']['bytes'],min(4096,available)),'Bounded read source count','counter_type')
                item.append(('capture_read_'+stream,item[0][1]+'/read'))
            else:need(not (type(available) is int and available>0),'Missing paired drain read','reference')
            calls.append((call['poll'],item))
    calls.sort(key=lambda p:p[0]);need([p for p,_ in calls]==list(range(1,len(calls)+1)) and len(calls)<=64,'Global terminal poll order','reference')
    expected_calls=[item for _,items in calls for item in items]
    index=0;refs=[];snapshot_ordinal=0
    def take(name):
        nonlocal index
        check();need(index<len(rows),'Missing known-launched source event: '+name,'incomplete_scope',index)
        row=rows[index];need(row['event']==name,'Unexpected native source event/order','outside_native_policy' if index==0 else 'source_order',index)
        index+=1;return row['details'],row['sequence']
    def equal(actual,expected,message,sequence):need(exact(actual,expected),message,'reference',sequence)
    def snap(stage):
        nonlocal snapshot_ordinal
        details,sequence=take('abi_job_snapshot_observed');snapshot_ordinal+=1
        _shape(details,('stage','ordinal','snapshot'),'Source Job snapshot event')
        need(details['stage']==stage and type(details['ordinal']) is int and details['ordinal']==snapshot_ordinal<=40,'Source snapshot stage/ordinal','counter_type',sequence)
        need(type(details['snapshot']) is dict,'Opaque bounded raw-resource record','reference',sequence)
        refs.append(dict(journal_sequence=sequence,kind='raw_job_snapshot',pointer='/details/snapshot',stage=stage,ordinal=snapshot_ordinal))
        return details['snapshot']
    def epoch(number):
        for offset,item in enumerate(files):
            check();details,sequence=take('recognition_lease_attempt_reserved');equal(details,dict(path=item['path'],role=item['role']),'Lease source binding',sequence)
            details,sequence=take('recognition_file_hash_reserved');equal(details,dict(path=item['path'],role=item['role'],expected_bytes=item['bytes'],pending_tail='unknown_until_successful_file_hash_return'),'Hash reservation binding',sequence)
            details,sequence=take('recognition_file_hash_returned')
            need(type(details) is dict and uint(details.get('bytes')),'Strict hash-return byte counter','counter_type',sequence)
            equal(details,dict(path=item['path'],role=item['role'],bytes=item['bytes'],sha256=item['sha256']),'Hash return binding',sequence)
            observed=hashes[number*len(files)+offset]
            expected=dict(path=item['path'],role=item['role'],expected_bytes=item['bytes'],known_returned_bytes=item['bytes'],computed_sha256=item['sha256'],hash_complete=True,status='verified',pending_read=False)
            equal(observed,expected,'Source hash-report projection',sequence)
            refs.append(dict(journal_sequence=sequence,kind='source_hash_return',report_pointer='/role_hash_records/'+str(number*len(files)+offset)))
    details,sequence=take('build_reserved');_shape(details,('run_id','owner_pid','created_at_utc'),'Native build reservation schema')
    need(type(details['run_id']) is str and UUID4.fullmatch(details['run_id']) is not None,'Writer UUID4 identifier','reference',sequence)
    need(type(details['owner_pid']) is int and details['owner_pid']==reservation['owner_pid'],'Reserved parent PID','counter_type',sequence)
    need(_utc(details['created_at_utc'])>=parent_date,'Journal precedes parent reservation','reference',sequence)
    details,sequence=take('detached_recognition_attempt_reserved');equal(details,dict(protocol_sha256=b['protocol_sha256'],limits=b['parent_limits']),'Attempt protocol/limit reference',sequence)
    epoch(0);snap('configured_empty')
    details,sequence=take('abi_job_configured_empty');_shape(details,('limits',),'Empty Job event');_job_limits(details['limits'])
    details,sequence=take('abi_create_suspended_reserved');equal(details,dict(argv=b['argv'],environment=b['environment'],creation_flags=0x8040C),'Exact launch config reference',sequence)
    details,sequence=take('abi_CreateProcessW_reserved');_shape(details,('attribute_count','attribute_keys','noninherited_job_handle'),'CreateProcess reservation')
    need(type(details['attribute_count']) is int and details['attribute_count']==2 and exact(details['attribute_keys'],[131074,131085]) and positive(details['noninherited_job_handle'],2**64-1),'Exact creation-time attributes','counter_type',sequence)
    details,sequence=take('abi_created_suspended');_shape(details,('pid','thread_id'),'Created identity event')
    need(positive(details['pid']) and positive(details['thread_id']),'Created PID/thread counters','counter_type',sequence);pid,tid=details['pid'],details['thread_id']
    snap('before_resume');details,sequence=take('abi_assigned_before_resume')
    _shape(details,('identity','limits','assigned_during_CreateProcessW','manual_assignment_fallback'),'Assigned identity event')
    identity=details['identity'];_shape(identity,('pid','thread_id','image','creation_filetime','directly_created_suspended'),'Owned identity projection')
    need(type(identity['pid']) is int and identity['pid']==pid and type(identity['thread_id']) is int and identity['thread_id']==tid
        and identity['image']==b['expected_executable'] and positive(identity['creation_filetime'],2**63-1) and identity['directly_created_suspended'] is True
        and details['assigned_during_CreateProcessW'] is True and details['manual_assignment_fallback'] is False,'Assigned source linkage','reference',sequence)
    _job_limits(details['limits'])
    details,sequence=take('abi_resume_reserved');equal(details,dict(pid=pid),'Resume PID linkage',sequence)
    details,sequence=take('abi_resume_returned');equal(details,dict(previous_suspend_count=1),'One observed resume',sequence)
    snap('running_first')
    while index<len(rows) and rows[index]['event']=='abi_job_snapshot_observed' and rows[index]['details'].get('stage')=='running_periodic':snap('running_periodic')
    for label,pointer in expected_calls:
        details,sequence=take('detached_ABI_terminal_call_reserved');equal(details,dict(observation=label),'Capture-call record binding',sequence)
        refs.append(dict(journal_sequence=sequence,kind='terminal_call',report_pointer=pointer))
    details,sequence=take('detached_ABI_terminal_call_reserved');equal(details,dict(observation='terminal_job_snapshot'),'Terminal Job reservation',sequence)
    final=snap('after_wait');equal(final,report['final_job_snapshot'],'Final raw snapshot report binding',index-1)
    job=observations['job_snapshot']
    need(type(job) is dict and all(job.get(k) is True for k in ('attempt_reserved','call_attempted','return_observed'))
        and type(job.get('ordinal')) is int and job['ordinal']==snapshot_ordinal and job.get('raw_publication')=='returned'
        and job.get('predicate')=='passed' and exact(job.get('raw'),final) and exact(job.get('value'),final),'Terminal raw snapshot reference','reference')
    details,sequence=take('detached_ABI_terminal_call_reserved');equal(details,dict(observation='terminal_memory_limits_and_peaks'),'Terminal memory reservation',sequence)
    memory=observations['memory_limits_and_peaks'];need(type(memory) is dict and memory.get('status')=='returned'
        and all(memory.get(k) is True for k in ('attempt_reserved','call_attempted','return_observed')),'Known memory return reference','reference');_job_limits(memory.get('value'))
    epoch(1);details,sequence=take('detached_recognition_terminal');equal(details,dict(status=report['status'],failure=report['failure']),'Terminal source report binding',sequence)
    need(index==len(rows),'Trailing native journal event','source_order',index);check()
    summary.update(status='complete_known_launched_native_journal',source_order_validated=True,policy_id=POLICY,
        source_terminal_status=report['status'],file_epochs=2,file_hash_returns=len(hashes),snapshot_records=snapshot_ordinal,
        terminal_capture_reservations=len(expected_calls),record_references=refs,profile_qualified=False,
        resource_semantics_validated=False,owner_context_provenance_established_by_this_function=False)
    check();return freeze(summary,check)
