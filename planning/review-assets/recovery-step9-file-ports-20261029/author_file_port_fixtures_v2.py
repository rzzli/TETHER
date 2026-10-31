"""Author FICTIONAL scripts only. Does not implement or call a file port."""
import copy
import hashlib
import json
from pathlib import Path
import struct

HERE=Path(__file__).resolve().parent
SCHEMA=HERE/'FILE-PORTS-FIXTURE-SCHEMA-v2.json'
TARGET=HERE/'FILE-PORTS-FIXTURES-v2.json'
FREEZE=HERE/'FILE-PORTS-FIXTURE-FREEZE-v2.json'
INVALID=2**64-1
ROOT=r'D:\Fixture'
OUT=ROOT+r'\output'
FILE=ROOT+r'\input.bin'
NAMES=('CreateFileW','GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx','ReadFile','CloseHandle',
       'GetFileAttributesExW','FindFirstFileExW','FindNextFileW','FindClose','CreateDirectoryW','WriteFile','FlushFileBuffers')


def document(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')+b'\n'
def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def units(text):return len(text.encode('utf-16-le'))//2
def path_record(path,kind='file'):return dict(kind=kind,path=path,utf16_units=units(path))
def error(kind='SyntheticFailure',message='fictional stop'):return dict(**{'class':kind},message=message)
def raw(value=1,*,last_error=0,error_defined=False,count=None,count_defined=False,buffer=b'',buffer_defined=False):
    return dict(value=value,last_error=last_error,error_defined=error_defined,raw_count=count,raw_count_defined=count_defined,buffer_hex=buffer.hex(),buffer_defined=buffer_defined)
def slot(identity,kind='original_file',handle=101,open_state='observed_owned',close_state='not_attempted',attempts=0):
    return dict(id=identity,kind=kind,handle=handle,open_state=open_state,close_state=close_state,closer=None if handle is None else 'FindClose' if kind=='file_search' else 'CloseHandle',close_attempts=attempts)


class Fiction:
    def __init__(self,identity,family,subcase,scope='primitive',ready=True):
        self.value=dict(id=identity,required_vector=family,subcase=subcase,scope=scope,
            request=dict(actions=[],facts={}),initial=dict(origin_label='fixture-origin-A',nonce_label='fixture-nonce-A',port_label='fixture-port-A',namespace_owned=ready,reservation_ready=ready,known_read_bytes=0,hashed_bytes=0,captured_bytes=0,slots=[]),
            plan=dict(N=1,B=0,M=0,U=3,Dk=[1,1],S=2,E=175,F=9,sumRi=17,sumWj=587,capture_bytes=3,report_bytes=4096),
            path_records=[path_record(FILE),path_record(OUT,'ordinary_admitted_directory')],script=[],
            expected=dict(disposition='primitive_complete',namespace_owned=ready,reservation_ready=ready,known_read_bytes=0,hashed_bytes=0,captured_bytes=0,read_count_unknown=False,known_write_bytes=0,write_hash_bytes=0,flushed_known_bytes=0,write_count_unknown=False,slots=[],primary=None,secondary=[],terminal_ack=False,journal_recursive_events=0,api_attempts={n:0 for n in NAMES},api_returns={n:0 for n in NAMES},profile_qualified=False,runtime_authorized=False,originals_authenticated=False))
        self.ns=0;self.clock()
    @property
    def e(self):return self.value['expected']
    @property
    def facts(self):return self.value['request']['facts']
    def action(self,operation,**arguments):self.value['request']['actions'].append(dict(operation=operation,arguments=arguments));return self
    def clock(self,now_ms=None,projection=None,raises=None):
        self.ns=self.ns+1000000 if now_ms is None and self.value['script'] else 0 if now_ms is None else int(now_ms*1000000)
        self.value['script'].append(dict(kind='clock',now_ns=self.ns,raises=raises,before_projection=projection or {}))
    def api(self,name,arguments,result=None,*,raises=None,after_ms=None,after=None,pending=None):
        self.clock()
        self.value['script'].append(dict(kind='api',name=name,arguments=arguments,outcome=dict(raise_=raises,raw_return=result) if False else {'raise':raises,'raw_return':result},before_projection=pending or {}))
        self.e['api_attempts'][name]+=1
        if raises is None:
            self.e['api_returns'][name]+=1;self.clock(after_ms,after)
    def hook(self,name,raises=None,projection=None):self.value['script'].append(dict(kind='hook',name=name,raises=raises,before_projection=projection or {}))
    def owned(self,s):self.e['slots'].append(s)
    def failed(self,reason,unknown=False,deadline=False):
        self.e['disposition']='incomplete_deadline' if deadline else 'incomplete_unknown' if unknown else 'incomplete_known_failure';self.e['primary']=reason
    def close(self,identity,handle=101,kind='original_file',result=None,raises=None,after_ms=None):
        name='FindClose' if kind=='file_search' else 'CloseHandle'
        self.api(name,dict(handle=handle),raw() if result is None and raises is None else result,raises=raises,after_ms=after_ms)
        for s in self.e['slots']:
            if s['id']==identity:
                s.update(close_attempts=1,close_state='entered_return_unknown' if raises else 'returned_success' if (result is None or result['value']!=0) else 'returned_failure')
    def open(self,path=FILE,identity='o0',handle=101,result=None,raises=None,after_ms=None):
        self.api('CreateFileW',dict(path=path,desired_access=2147483648,share_mode=1,security=None,creation=3,flags=2097280,template=None),raw(handle) if result is None and raises is None else result,raises=raises,after_ms=after_ms,
                 pending={f'slots.{identity}.open_state':'entered_return_unknown','namespace_owned':True,'reservation_ready':True},after=None if raises else {f'slots.{identity}.open_state':'observed_owned'} if result is None else {})
        if result is None and raises is None:self.owned(slot(identity,handle=handle))
    def identity(self,path=FILE,handle=101,size=3,output=False):
        self.api('GetFileType',dict(handle=handle),raw(1))
        self.api('GetFileInformationByHandleEx',dict(handle=handle,info_class=9,buffer_bytes=8),raw(buffer=struct.pack('<II',128,0),buffer_defined=True))
        text='\\\\?\\'+path;buf=(text+'\0').encode('utf-16-le');buf+=b'\0'*(8202-len(buf))
        self.api('GetFinalPathNameByHandleW',dict(handle=handle,capacity=4101,flags=0),raw(units(text),buffer=buf,buffer_defined=True))
        self.api('GetFileSizeEx',dict(handle=handle),raw(buffer=struct.pack('<q',size),buffer_defined=True))
    def attrs(self,path,success=True,reparse=False):
        buf=struct.pack('<I',16|(1024 if reparse else 0))+b'\0'*32
        self.api('GetFileAttributesExW',dict(path=path,info_level=0,buffer_bytes=36),raw(1 if success else 0,last_error=0 if success else 5,error_defined=not success,buffer=buf if success else b'\0'*36,buffer_defined=success))
    def read(self,request=3,data=b'abc',ok=True,unknown=False,late=None):
        self.api('ReadFile',dict(handle=101,requested=request,overlapped=None),None if unknown else raw(1 if ok else 0,last_error=0 if ok else 5,error_defined=not ok,count=len(data) if ok else 0,count_defined=ok,buffer=data+b'\0'*(request-len(data)),buffer_defined=ok),raises=error('UnreturnedCall') if unknown else None,after_ms=late,after={'known_read_bytes':self.e['known_read_bytes']+len(data)} if ok and not unknown else {})
        if ok and not unknown:self.e['known_read_bytes']+=len(data)
        else:self.e['read_count_unknown']=True
    def hash_capture(self,data=b'abc',hash_fail=False,copy_fail=False):
        self.hook('hash_update',error() if hash_fail else None,dict(known_read_bytes=self.e['known_read_bytes']))
        if hash_fail:return
        self.e['hashed_bytes']+=len(data)
        self.hook('copy_bytes',error() if copy_fail else None,dict(hashed_bytes=self.e['hashed_bytes']))
        if not copy_fail:self.e['captured_bytes']+=len(data)
    def output_open(self,name,identity='w0',handle=201):
        path=OUT+'\\'+name
        self.api('CreateFileW',dict(path=path,desired_access=1073741952,share_mode=0,security=None,creation=1,flags=128,template=None),raw(handle),after={f'slots.{identity}.open_state':'observed_owned'})
        self.owned(slot(identity,'output_file',handle));self.identity(path,handle,0,True)
    def write(self,data=b'ABCD',handle=201,count=None,ok=True,unknown=False,late=None):
        amount=len(data) if count is None else count
        self.api('WriteFile',dict(handle=handle,data_hex=data.hex(),overlapped=None),None if unknown else raw(1 if ok else 0,last_error=0 if ok else 5,error_defined=not ok,count=amount if ok else 0,count_defined=ok),raises=error('UnreturnedCall') if unknown else None,after_ms=late,after={'known_write_bytes':self.e['known_write_bytes']+amount,'write_hash_bytes':self.e['write_hash_bytes']} if ok and not unknown else {})
        if ok and not unknown:self.e['known_write_bytes']+=amount
        else:self.e['write_count_unknown']=True
    def hash_written(self,count):self.hook('hash_update',projection={'known_write_bytes':self.e['known_write_bytes']});self.e['write_hash_bytes']+=count
    def flush(self,handle=201,ok=True,unknown=False):
        self.api('FlushFileBuffers',dict(handle=handle),None if unknown else raw(1 if ok else 0,last_error=0 if ok else 5,error_defined=not ok),raises=error('UnreturnedCall') if unknown else None)
        if ok and not unknown:self.e['flushed_known_bytes']=self.e['known_write_bytes']


def main():
    assert not TARGET.exists() and not FREEZE.exists()
    schema=json.loads(SCHEMA.read_text(encoding='utf-8'));assert pin(SCHEMA)['sha256']=='e3e20e39c08eb9718b03ef65700d375870f6bdf1d77b54279f98465ced454dfc'
    cases=[]
    def case(f):cases.append(f.value);return f
    # Baseline is a primitive composition, NOT a full checker/owner success.
    f=Fiction('success_baseline',0,'namespace_journal_and_one_original',scope='limited_composition',ready=False)
    f.action('reserve_namespace_and_journal',path=OUT);f.attrs(ROOT)
    f.api('CreateDirectoryW',dict(path=OUT,security=None),raw(),after={'namespace_owned':True,'reservation_ready':False});f.e['namespace_owned']=True;f.attrs(OUT)
    for name,identity,handle,payload in [('reservation.json','r0',201,b'fixture-reservation\n'),('journal.jsonl','j0',202,b'fixture-first-record\n')]:
        f.output_open(name,identity,handle);f.write(payload,handle);f.hash_written(len(payload));f.flush(handle)
        if name=='reservation.json':f.close(identity,handle,'output_file')
    f.e['reservation_ready']=True
    f.action('open_inspect_original',path=FILE).action('hash_capture_original',slot='o0',bytes=3).action('close_slot',slot='o0')
    f.open();f.identity();f.read();f.hash_capture();f.close('o0');f.close('j0',202,'output_file');f.e['disposition']='primitive_composition_complete';case(f)
    for fault in ('identity','log','work_deadline'):
        f=Fiction('owned_open_'+fault,1,fault);f.action('open_inspect_original',path=FILE);f.open(after_ms=295001 if fault=='work_deadline' else None)
        if fault=='identity':f.api('GetFileType',dict(handle=101),raw(3))
        elif fault=='log':f.hook('log_append',error(),{'slots.o0.open_state':'observed_owned'})
        f.failed(fault,deadline=fault=='work_deadline');f.close('o0');case(f)
    for kind in ('INVALID','NULL','unreturned'):
        f=Fiction('open_'+kind,2,kind);f.action('open_inspect_original',path=FILE)
        if kind=='unreturned':f.open(raises=error('UnreturnedCall'))
        else:f.open(result=raw(INVALID if kind=='INVALID' else None,last_error=5,error_defined=True))
        f.e['slots']=[slot('o0',handle=None,open_state='known_failure_no_handle' if kind=='INVALID' else 'malformed_or_return_unknown')];f.failed('open_'+kind,unknown=kind!='INVALID');case(f)
    f=Fiction('namespace_owned_journal_reserve_failure',3,'journal_open_invalid',ready=False);f.action('reserve_namespace_and_journal',path=OUT)
    f.api('CreateDirectoryW',dict(path=OUT,security=None),raw(),after={'namespace_owned':True,'reservation_ready':False});f.e['namespace_owned']=True
    f.api('CreateFileW',dict(path=OUT+'\\journal.jsonl',desired_access=1073741952,share_mode=0,security=None,creation=1,flags=128,template=None),raw(INVALID,last_error=5,error_defined=True));f.e['slots']=[slot('j0','output_file',None,'known_failure_no_handle')];f.failed('journal_reservation_failed');case(f)
    for fault in ('hash','copy','late','failed_count','short_read','zero_read','unreturned_read'):
        f=Fiction('read_'+fault,4,fault);f.action('hash_capture_original',slot='o0',bytes=3);f.value['initial']['slots']=[slot('o0')];f.owned(slot('o0'))
        if fault=='short_read':
            f.read(data=b'a');f.hash_capture(b'a');f.read(request=2,data=b'bc');f.hash_capture(b'bc')
        else:f.read(data=b'' if fault=='zero_read' else b'abc',ok=fault!='failed_count',unknown=fault=='unreturned_read',late=295001 if fault=='late' else None)
        if fault in ('hash','copy'):f.hash_capture(hash_fail=fault=='hash',copy_fail=fault=='copy')
        if fault!='short_read':f.failed(fault,unknown=fault in ('failed_count','unreturned_read'),deadline=fault=='late')
        f.close('o0');case(f)
    for kind,wrong in [('original_file','FindClose'),('file_search','CloseHandle')]:
        f=Fiction('wrong_closer_'+kind,5,kind);s=slot('s0',kind);f.value['initial']['slots']=[copy.deepcopy(s)];f.owned(s);f.action('close_slot',slot='s0',requested_closer=wrong);f.e.update(disposition='control_rejected',primary='wrong_closer');f.close('s0',101,kind);case(f)
    f=Fiction('uncertain_close_not_retried',5,'unreturned_close');f.value['initial']['slots']=[slot('o0')];f.owned(slot('o0'));f.action('close_slot',slot='o0');f.close('o0',raises=error('UnreturnedCall'));f.failed('close_unknown',unknown=True);case(f)
    def finddata(name,reparse=False,unterminated=False):
        buf=bytearray(592);struct.pack_into('<I',buf,0,1024 if reparse else 128)
        text=('x'*260 if unterminated else name+'\0').encode('utf-16-le');buf[44:44+len(text)]=text;return bytes(buf)
    for fault in ('empty','initial18','natural_end','unterminated','extra','reparse','overflow','next_failed'):
        f=Fiction('scan_'+fault,6,fault);directory=ROOT+'\\scan';f.action('scan_directory',path=directory,declared_empty=fault=='empty');f.attrs(directory)
        args=dict(pattern=directory+'\\*',info_level=1,search_op=0,search_filter=None,flags=0)
        if fault in ('empty','initial18'):
            f.api('FindFirstFileExW',args,raw(INVALID,last_error=2 if fault=='empty' else 18,error_defined=True,buffer=b'\0'*592,buffer_defined=False));f.e['slots']=[slot('s0','file_search',None,'known_failure_no_handle')]
            if fault=='initial18':f.failed('initial18_is_not_natural_end')
        else:
            f.api('FindFirstFileExW',args,raw(301,buffer=finddata('unexpected' if fault=='extra' else 'f0',fault=='reparse',fault=='unterminated'),buffer_defined=True),after={'slots.s0.open_state':'observed_owned'});f.owned(slot('s0','file_search',301))
            if fault=='overflow':
                for i in range(1,65):f.api('FindNextFileW',dict(handle=301,buffer_bytes=592),raw(buffer=finddata('f'+str(i)),buffer_defined=True))
                f.facts['non_dot_successes_before_stop']=65
            elif fault=='next_failed':f.api('FindNextFileW',dict(handle=301,buffer_bytes=592),raw(0,last_error=5,error_defined=True,buffer=b'\0'*592,buffer_defined=False))
            if fault=='natural_end':f.api('FindNextFileW',dict(handle=301,buffer_bytes=592),raw(0,last_error=18,error_defined=True,buffer=b'\0'*592,buffer_defined=False))
            else:f.failed('scan_'+fault,unknown=fault=='next_failed')
            f.close('s0',301,'file_search')
        case(f)
    for fault in ('zero','short','false','unreturned','flush_false','flush_unknown','false_and_close_failure'):
        f=Fiction('write_'+fault,7,fault);f.action('write_output_record',slot='w0',record_hex=b'ABCD'.hex());f.value['initial']['slots']=[slot('w0','output_file',201)];f.owned(slot('w0','output_file',201))
        f.write(count=0 if fault=='zero' else 1 if fault=='short' else None,ok=fault not in ('false','false_and_close_failure'),unknown=fault=='unreturned')
        if fault=='short':f.hash_written(1);f.write(b'BCD');f.hash_written(3);f.flush();f.close('w0',201,'output_file')
        elif fault in ('flush_false','flush_unknown'):
            f.hash_written(4);f.flush(ok=False,unknown=fault=='flush_unknown');f.failed(fault,unknown=fault=='flush_unknown');f.close('w0',201,'output_file')
        else:
            f.failed(fault,unknown=fault in ('false','unreturned','false_and_close_failure'))
            f.close('w0',201,'output_file',result=raw(0,last_error=5,error_defined=True) if fault=='false_and_close_failure' else None)
            if fault=='false_and_close_failure':f.e['secondary'].append('close_failed')
        case(f)
    f=Fiction('seal_close_return_late',8,'known_close_then_final_deadline');f.action('finalize_output',slot='seal0');f.value['initial']['slots']=[slot('seal0','output_file',201)];f.owned(slot('seal0','output_file',201))
    f.write(late=299990);f.hash_written(4);f.flush();f.close('seal0',201,'output_file',after_ms=300001);f.failed('final_clock_expired',deadline=True);case(f)
    for fault in ('acyclic','self_hash','same_path','unknown_veto'):
        f=Fiction('DAG_'+fault,9,fault,scope='control_only');f.action('validate_seal_graph',fault=fault)
        f.facts.update(nodes=['candidate','cleanup','closed_journal','receipt','seal'],edges=[['cleanup','candidate'],['receipt','candidate'],['receipt','cleanup'],['receipt','closed_journal'],['seal','receipt']],self_excluded=True)
        if fault=='self_hash':f.facts['edges'].append(['seal','seal'])
        if fault=='same_path':f.facts['same_path_nodes']=['candidate','receipt']
        if fault=='unknown_veto':f.facts['required_operation']='return_unknown'
        f.e.update(disposition='primitive_complete' if fault=='acyclic' else 'control_rejected',primary=None if fault=='acyclic' else 'DAG_'+fault);case(f)
    for cap in ('N','U','E','capture','report','read','write'):
        f=Fiction('admission_'+cap,10,cap,scope='control_composition');f.action('admit_plan',over_cap=cap)
        f.value['plan'].update(B=1,E=177);f.value['initial'].update(known_read_bytes=3,hashed_bytes=3,captured_bytes=3,slots=[slot('b0')]);f.e.update(known_read_bytes=3,hashed_bytes=3,captured_bytes=3);f.owned(slot('b0'))
        field={'N':'N','U':'U','E':'E','capture':'capture_bytes','report':'report_bytes','read':'sumRi','write':'sumWj'}[cap]
        f.value['plan'][field]={'N':257,'U':1025,'E':2049,'capture':67108865,'report':2097153,'read':18,'write':590}[cap]
        if cap=='N':f.value['plan']['E']=6*f.value['plan']['N']+2+8+161
        f.e.update(disposition='admission_rejected',primary='plan_'+cap);f.close('b0');case(f)
    for fault in ('foreign_port','foreign_nonce','serialized_ready','double_handoff','cached_own_module'):
        f=Fiction('control_'+fault,11,fault,scope='control_only');f.action('validate_handoff',fault=fault);f.facts.update(origin_label='fixture-origin-A',required_port='fixture-port-A',supplied_port='fixture-port-B' if fault=='foreign_port' else 'fixture-port-A',required_nonce='fixture-nonce-A',supplied_nonce='fixture-nonce-B' if fault=='foreign_nonce' else 'fixture-nonce-A',serialized_ready={'ready':True} if fault=='serialized_ready' else None,handoff_count=2 if fault=='double_handoff' else 1,cached_own_module=fault=='cached_own_module')
        f.e.update(disposition='control_rejected',primary=fault);case(f)
    f=Fiction('roots_C_D_counted_once',12,'deduplicated_roots',scope='metadata_primitive');f.value['path_records']=[path_record('C:\\','canonical_drive_root'),path_record('D:\\','canonical_drive_root')];f.action('inspect_ancestors',paths=['C:\\','D:\\','C:\\','D:\\']);f.value['plan']['U']=2;f.attrs('C:\\');f.attrs('D:\\');case(f)
    for use in ('original','output_file','namespace','scan_root','discovered_authority'):
        f=Fiction('root_not_'+use,13,use,scope='control_only');f.action('admit_plan',path='D:\\',use=use);f.value['path_records']=[path_record('D:\\','canonical_drive_root')];f.e.update(disposition='admission_rejected',primary='root_wrong_role');case(f)
    for value in ('D:','d:\\','relative','\\\\server\\share','\\\\?\\D:\\','E:\\'):
        f=Fiction('root_spelling_'+str(len(cases)),14,value,scope='control_only');f.action('admit_plan',path=value,use='ancestor');f.value['path_records']=[path_record(value,'canonical_drive_root')];f.e.update(disposition='admission_rejected',primary='unapproved_root_spelling');case(f)
    for size in (4096,4097):
        prefix='D:\\Fixture\\';remaining=size-units(prefix)-4;path=prefix+'\U0001f600'*(remaining//2)+('x' if remaining%2 else '')+'.bin'
        assert units(path)==size
        f=Fiction('path_UTF16_'+str(size),14,'astral_units',scope='control_only');f.action('admit_plan',path=path,use='original');f.value['path_records']=[path_record(path)];f.facts['python_characters']=len(path);f.e.update(disposition='primitive_complete' if size==4096 else 'admission_rejected',primary=None if size==4096 else 'UTF16_cap');case(f)
    for fault in ('false','unreturned','late'):
        f=Fiction('root_attrs_'+fault,15,fault,scope='metadata_primitive');f.action('inspect_ancestors',paths=['D:\\']);f.value['path_records']=[path_record('D:\\','canonical_drive_root')];f.value['plan']['U']=1
        if fault=='unreturned':f.api('GetFileAttributesExW',dict(path='D:\\',info_level=0,buffer_bytes=36),raises=error('UnreturnedCall'))
        elif fault=='late':f.api('GetFileAttributesExW',dict(path='D:\\',info_level=0,buffer_bytes=36),raw(buffer=struct.pack('<I',16)+b'\0'*32,buffer_defined=True),after_ms=295001)
        else:f.attrs('D:\\',False)
        f.failed('root_attributes_'+fault,unknown=fault in ('false','unreturned'),deadline=fault=='late');case(f)
    for fault in ('normal','late_known_write'):
        f=Fiction('output_registry_'+fault,16,fault);f.action('write_output_record',slot='w0',record_hex='41424344');f.value['initial']['slots']=[slot('w0','output_file',201)];f.owned(slot('w0','output_file',201));f.write(late=300001 if fault=='late_known_write' else None)
        f.facts.update(record_hex='41424344',returned_slice_offset=0,known_count=4,no_artifact_pin=fault=='late_known_write',no_recursive_journal_events=True)
        if fault=='late_known_write':f.e['slots'][0]['close_state']='not_dispatched_deadline';f.failed('hard_deadline',deadline=True)
        else:f.hash_written(4);f.flush();f.close('w0',201,'output_file')
        case(f)
    # Supplemental strict signed32 BOOL decoder and noncanonical success controls.
    for name in ('ReadFile','CloseHandle','CreateDirectoryW'):
        for value in (2,-1):
            f=Fiction('BOOL_'+name+'_'+str(value),None,'nonzero_signed32',scope='BOOL_primitive',ready=name!='CreateDirectoryW')
            if name=='ReadFile':
                f.value['initial']['slots']=[slot('o0')];f.owned(slot('o0'));f.action('hash_capture_original',slot='o0',bytes=3)
                f.api('ReadFile',dict(handle=101,requested=3,overlapped=None),raw(value,count=3,count_defined=True,buffer=b'abc',buffer_defined=True),after={'known_read_bytes':3})
                f.e['known_read_bytes']=3;f.hash_capture();f.close('o0')
            elif name=='CloseHandle':
                f.value['initial']['slots']=[slot('o0')];f.owned(slot('o0'));f.action('close_slot',slot='o0');f.close('o0',result=raw(value))
            else:
                f.action('create_namespace',path=OUT);f.api('CreateDirectoryW',dict(path=OUT,security=None),raw(value),after={'namespace_owned':True,'reservation_ready':False});f.e['namespace_owned']=True
            case(f)
        for value in (True,2147483648,-2147483649):
            f=Fiction('BOOL_reject_'+name+'_'+str(value),None,'strict_i32_decoder',scope='control_only');f.action('decode_raw_BOOL',api_name=name,raw_value=value)
            f.e.update(disposition='control_rejected',primary='raw_BOOL_domain');case(f)
    assert len(cases)<=96 and {row['required_vector'] for row in cases if row['required_vector'] is not None}==set(range(17))
    result=dict(schema_version=1,status='FICTIONAL_CALL_SCRIPTS_AND_AUTHORED_EXPECTATIONS_NOT_PORT_CONFORMANCE',schema_sha256=pin(SCHEMA)['sha256'],cases=cases,
        required_families=16,success_baselines=1,supplemental_BOOL_cases=15,action_schedule='Run requested primitive/control actions then owner cleanup once unless hard deadline prohibits dispatch. No repeated uncertain closer; scripts are the exact permitted call sequence.',expected_states_authored=True,port_implementation=False,actual_API_calls=0,old_original_payload_operations=0,profile_qualified=False,runtime_authorized=False)
    with TARGET.open('xb') as out:out.write(document(result))
    record=dict(schema_version=1,status='FICTIONAL_FIXTURES_FROZEN_BEFORE_PORT_IMPLEMENTATION',schema=pin(SCHEMA),schema_freeze=pin(HERE/'FILE-PORTS-FIXTURE-SCHEMA-FREEZE-v2.json'),fixtures=pin(TARGET),author=pin(Path(__file__)),case_count=len(cases),required_families=16,port_implementation_authorized=False,actual_API_authorized=False)
    with FREEZE.open('xb') as out:out.write(document(record))
    print(json.dumps(dict(fixtures=pin(TARGET),freeze=pin(FREEZE),cases=len(cases))))


if __name__=='__main__':main()
