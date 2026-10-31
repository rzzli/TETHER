"""Captured native-v7 archive graph only; no paths, files, SDK or native calls.

External metadata is a declared context, not authenticated authority. Every
result keeps original/source/directory/profile qualification false.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
import re
from types import MappingProxyType

POLICY='captured-native-recognition-v7-archive-v1'
POSITIVE='recognition_observations_retained_independent_qualification_pending'
MAX_TOTAL=33554432
MAX_JSON=2097152
MAX_FILES=64
MAX_NODES=100000
MAX_EDGES=4096
ROOT_FILES=frozenset(('parent-reservation.json','effective-protocol.json','parent-report.json','stdout.bin','stderr.bin','receipt.json',
    'post-lease-cleanup.json','terminal-seal.json','failure.json','late-failure.json','after-seal-failure.json','terminal-publication-error.json','journal-close-error.json'))
CHILD_FILES=frozenset(('execution/child/attempt.json','execution/child/result.jsonl','execution/child/result.partial.jsonl','execution/child/failure.json'))
ALLOWED=ROOT_FILES|CHILD_FILES|{'execution/journal.jsonl'}
VETO_FILES=frozenset(('failure.json','late-failure.json','after-seal-failure.json','terminal-publication-error.json','journal-close-error.json',
    'execution/child/failure.json','execution/child/result.partial.jsonl'))
LABELS=('current_parent','current_authority','current_binding_checker','current_binding_proof')
HEX=re.compile(r'^[0-9a-f]{64}$')
UUID=re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
UTC=re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{6})?\+00:00$')
CONFIG_KEYS=frozenset(('schema_version','kind','mode','helper','executable','software_inputs','payload_inputs','inputs','output','argv','command_line','environment',
    'limits','creation_flags','maximum_attempts','automatic_retry','module_policy_id','module_policy_sha256','expected_version','expected_pack_sha256','contract_sha256',
    'parent_seconds','child_seconds','cooperative_work_ms','full_vocabulary_mask','inference','scientific_validation','execution_authorized_by_preparation','hash_pass_policy','periodic_job_seconds','original_SDK_general_gate'))
AUTHORITY_KEYS=frozenset(('schema_version','status','mode','execution_authorized','runtime_qualified','executable','verified_build','source','compiled_source_copy',
    'runtime_pin_header','execution_contract','expected_pack_metadata','module_policy_id','module_policy_sha256','software_inputs','payload_descriptors','closure_scope','dynamic_dependencies'))
RECEIPT_KEYS=frozenset(('schema_version','status','outputs','protocol_sha256','failure_veto'))
CLEANUP_KEYS=frozenset(('schema_version','status','earlier_status','primary_failure','primary_failure_marker','earlier_receipt','parent_elapsed_after_leases_seconds','parent_deadline_exceeded','close_errors','outcomes'))
SEAL_KEYS=frozenset(('schema_version','status','required','earlier_receipt','cleanup_artifact','primary_failure_marker','late_failure_marker','outputs','parent_elapsed_before_terminal_seal_seconds','failure_veto'))
NORMAL_LATE_KEYS=frozenset(('schema_version','authoritative','automatic_retry','phase','error_class','primary_failure','primary_failure_marker','cleanup_artifact','close_errors','parent_deadline_exceeded'))
EXCEPTION_LATE_KEYS=frozenset(('authoritative','automatic_retry','phase','error_class','error','primary_failure','primary_failure_marker','close_outcomes'))
LIMITS=dict(parent_seconds=300,child_seconds=120,child_cleanup_reserved_seconds=2,finalization_reserved_seconds=5,process_and_job_commit_bytes=268435456,
    active_processes=1,maximum_children=1,stream_bytes=65536,maximum_job_snapshots=40,job_pid_capacity=16,attempt_bytes=4096,result_bytes=8388608,row_bytes=65536)
FIXED=dict(schema_version=1,kind='detached_singleton_recognition_observation_v1',mode='--recognize',creation_flags=525324,maximum_attempts=1,automatic_retry=False,
    module_policy_id='trusted-System32-recognition-v1',module_policy_sha256='4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713',expected_version='0.7.0-dev',
    contract_sha256='30d82a42c5338789644fea00f666e264fb3e4114637c2c37330386a177f17861',parent_seconds=300,child_seconds=120,cooperative_work_ms=117000,
    full_vocabulary_mask=False,inference=False,scientific_validation='not_established',execution_authorized_by_preparation=False,original_SDK_general_gate=False)
HASH_POLICY=dict(driver_model_passes=0,parent_initial=1,child=1,parent_final=1,external_verifier_separately_timed=True)

def _scalar(value):
    return value is None or type(value) in (str,int,bool,float)

@dataclass(frozen=True,slots=True)
class MetadataPin:
    path: object
    bytes: object
    sha256: object
    def __post_init__(self):
        if not all(_scalar(v) for v in (self.path,self.bytes,self.sha256)):raise TypeError('immutable_pin_scalars')

@dataclass(frozen=True,slots=True)
class DynamicPin:
    role: object
    pin: MetadataPin
    def __post_init__(self):
        if not _scalar(self.role) or type(self.pin) is not MetadataPin:raise TypeError('immutable_dynamic_pin')

@dataclass(frozen=True,slots=True)
class CapturedArchive:
    protocol_bytes: bytes|None
    authority_bytes: bytes|None
    run_files: tuple
    def __post_init__(self):
        if any(v is not None and type(v) is not bytes for v in (self.protocol_bytes,self.authority_bytes)):raise TypeError('exact_captured_bytes')
        if type(self.run_files) is not tuple or len(self.run_files)>MAX_FILES:raise ValueError('capture_file_bound')
        if any(type(p) is not tuple or len(p)!=2 or type(p[0]) is not str or type(p[1]) is not bytes for p in self.run_files):raise TypeError('immutable_capture_pairs')

@dataclass(frozen=True,slots=True)
class ArchiveBindings:
    policy_id: object
    run_root: object
    protocol_pin: MetadataPin
    authority_pin: MetadataPin
    helper_pin: MetadataPin
    static_software_pins: tuple
    dynamic_pins: tuple
    payload_descriptors: tuple
    def __post_init__(self):
        if not _scalar(self.policy_id) or not _scalar(self.run_root):raise TypeError('immutable_binding_scalars')
        if any(type(p) is not MetadataPin for p in (self.protocol_pin,self.authority_pin,self.helper_pin)):raise TypeError('typed_binding_pin')
        for items,kind in ((self.static_software_pins,MetadataPin),(self.dynamic_pins,DynamicPin),(self.payload_descriptors,MetadataPin)):
            if type(items) is not tuple or len(items)>256 or any(type(p) is not kind for p in items):raise TypeError('immutable_pin_roster')

def _freeze(value,check):
    count=0
    def walk(v):
        nonlocal count
        count+=1
        if count%128==0:check()
        if type(v) is dict:return MappingProxyType({k:walk(x) for k,x in v.items()})
        if type(v) is list:return tuple(walk(x) for x in v)
        return v
    check();out=walk(value);check();return out
def _thaw(value):
    if type(value) is MappingProxyType:return {k:_thaw(v) for k,v in value.items()}
    if type(value) is tuple:return [_thaw(v) for v in value]
    return value

@dataclass(frozen=True,slots=True)
class CapturedArchiveResult:
    _data: object
    def to_dict(self):return _thaw(self._data)
    @property
    def profile_qualified(self):return False
    @property
    def originals_authenticated(self):return False
    @property
    def actual_directory_complete(self):return False
    @property
    def source_qualified(self):return False

class _Bad(ValueError):
    pass
def _need(value,message):
    if not value:raise _Bad(message[:512])
def _uint(v,maxi=2**63-1):return type(v) is int and 0<=v<=maxi
def _number(v):return type(v) in (int,float) and math.isfinite(v) and v>=0
def _hex(v):return type(v) is str and HEX.fullmatch(v) is not None
def _same(a,b):
    if type(a) is not type(b):return False
    if type(a) is dict:return a.keys()==b.keys() and all(_same(a[k],b[k]) for k in a)
    if type(a) is list:return len(a)==len(b) and all(_same(x,y) for x,y in zip(a,b))
    return a==b
def _canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
def _shape(v,keys,node):_need(type(v) is dict and v.keys()==frozenset(keys),'closed_schema:'+node)
def _text(v,maximum=32767):
    _need(type(v) is str and len(v)<=maximum,'bounded_scalar_text')
    try:v.encode('utf-8','strict')
    except UnicodeError as e:raise _Bad('non_scalar_text') from e
    return v
def _path(v):
    _text(v);_need(len(v)>=4 and v[0] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz' and v[1:3] in (':\\',':/'),'absolute_DOS_metadata')
    parts=v[3:].replace('/','\\').split('\\')
    for part in parts:
        _need(part not in ('','.','..') and not part.endswith(('.',' ')) and not any(ord(c)<32 or ord(c)==127 or c in '<>:"|?*~' for c in part),'canonical_DOS_component')
        _need(part.split('.',1)[0].lower() not in {'con','prn','aux','nul',*[f'com{i}' for i in range(1,10)],*[f'lpt{i}' for i in range(1,10)]},'DOS_device_component')
    return v.replace('/','\\').translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'))
def _locator(v):
    _text(v,256);_need(v and '\\' not in v and ':' not in v and not v.startswith('/') and all(p not in ('','.','..') and not p.endswith(('.',' ')) for p in v.split('/')),'relative_locator')
    _need(not any(ord(c)<32 or ord(c)==127 for c in v),'relative_locator_control');_need(v in ALLOWED,'unsupported_locator')
    return v
def _pin(v):
    if type(v) is MetadataPin:v=dict(path=v.path,bytes=v.bytes,sha256=v.sha256)
    _shape(v,('path','bytes','sha256'),'pin');_path(v['path']);_need(_uint(v['bytes']) and _hex(v['sha256']),'strict_pin_counter_or_digest')
    return v
def _utc(v):
    _need(type(v) is str and UTC.fullmatch(v) is not None,'source_UTC_shape')
    try:datetime.fromisoformat(v)
    except ValueError as e:raise _Bad('source_UTC_value') from e

class _Analysis:
    def __init__(self,check):
        self.check=check;self.nodes={};self.edges=[];self.vetoes=[];self.missing=set();self.issues=[];self.json_nodes=0
        self.incomplete=False;self.binding='unresolved';self.receipt_status='unresolved';self.terminal_match=None
    def missing_node(self,node):
        self.check();self.missing.add(node);self.incomplete=True
    def incomplete_reason(self,code):
        self.check();self.incomplete=True;self.issues.append(code)
    def negative(self,reason):
        self.check()
        if reason not in self.vetoes:self.vetoes.append(reason)
    def hash(self,raw):
        h=hashlib.sha256()
        for offset in range(0,len(raw),65536):self.check();h.update(raw[offset:offset+65536]);self.check()
        self.check();return dict(bytes=len(raw),sha256=h.hexdigest())
    def json(self,raw,node,cap=MAX_JSON,canonical=True):
        self.check();_need(0<len(raw)<=cap,'JSON_byte_cap:'+node)
        _need(raw.endswith(b'\n') and not raw.endswith(b'\r\n') and not raw.startswith(b'\xef\xbb\xbf'),'JSON_LF_or_BOM:'+node)
        depth=0;quoted=False;escaped=False;atom=False
        for i,b in enumerate(raw[:-1]):
            if i%4096==0:self.check()
            if quoted:
                if escaped:escaped=False
                elif b==92:escaped=True
                elif b==34:quoted=False
            elif b==34:quoted=True;self.json_nodes+=1;atom=False
            elif b in (123,91):depth+=1;self.json_nodes+=1;atom=False
            elif b in (125,93):depth-=1;atom=False
            elif b in (44,58,9,10,13,32):atom=False
            elif not atom:atom=True;self.json_nodes+=1
            _need(0<=depth<=32 and self.json_nodes<=MAX_NODES,'JSON_depth_or_aggregate_node_cap')
        _need(not quoted and depth==0,'JSON_unfinished:'+node)
        def pairs(items):
            out={}
            for k,v in items:_need(k not in out,'duplicate_JSON_key:'+node);out[k]=v
            return out
        try:
            value=json.loads(raw.decode('utf-8','strict'),object_pairs_hook=pairs,
                parse_constant=lambda _:(_ for _ in ()).throw(_Bad('nonfinite_JSON:'+node)))
            self.check();encoded=_canonical(value)
        except _Bad:raise
        except (ValueError,UnicodeError,RecursionError) as e:raise _Bad('invalid_scalar_JSON:'+node) from e
        self.check()
        if canonical:_need(encoded+b'\n'==raw,'noncanonical_parent_JSON:'+node)
        _need(type(value) is dict,'JSON_object_required:'+node);return value
    def edge(self,source,target):
        self.check();_need(len(self.edges)<MAX_EDGES,'graph_edge_cap');self.edges.append((source,target))
    def pin_link(self,source,pin,target,files,root):
        self.check();p=_pin(pin);_locator(target);_need(p['path']==root+'\\'+target.replace('/','\\'),'cross_root_or_wrong_pin_locator')
        self.edge(source,target)
        if target not in files:self.missing_node(target);return
        _need(_same({k:p[k] for k in ('bytes','sha256')},self.nodes[target]),'pin_bytes_or_digest:'+target)
    def optional_pin(self,source,pin,target,files,root):
        if pin is not None:self.pin_link(source,pin,target,files,root)
    def output_map(self,source,value,files,allowed):
        self.check();_need(type(value) is dict and len(value)<=MAX_FILES,'output_map_shape')
        for key,p in value.items():
            self.check();_locator(key);_need(key in allowed,'future_or_self_map_edge:'+source)
            _shape(p,('bytes','sha256'),'output_map_pin');_need(_uint(p['bytes']) and _hex(p['sha256']),'output_map_pin_types')
            self.edge(source,key);_need(key in files,'dangling_output_map_edge:'+key)
            _need(_same(p,self.nodes[key]),'output_map_digest_or_size:'+key)
    def cycles(self):
        graph={};state={}
        for a,b in self.edges:graph.setdefault(a,[]).append(b)
        for start in graph:
            self.check()
            if state.get(start)==2:continue
            stack=[(start,False)]
            while stack:
                self.check();node,exit=stack.pop()
                if exit:state[node]=2;continue
                _need(state.get(node)!=1,'cyclic_captured_graph')
                if state.get(node)==2:continue
                state[node]=1;stack.append((node,True))
                for nxt in reversed(graph.get(node,())):
                    _need(state.get(nxt)!=1,'cyclic_captured_graph');stack.append((nxt,False))

def _declared(a,b,cfg,auth):
    a.check();_need(b.policy_id==POLICY,'unsupported_archive_policy');root=b.run_root;root_key=_path(root)
    context_protocol,context_authority,helper=map(_pin,(b.protocol_pin,b.authority_pin,b.helper_pin))
    static=[_pin(v) for v in b.static_software_pins];dynamic=[]
    _need(len(b.dynamic_pins)==4 and tuple(x.role for x in b.dynamic_pins)==LABELS,'four_labelled_dynamic_pins')
    for x in b.dynamic_pins:a.check();dynamic.append(_pin(x.pin))
    payload=[_pin(v) for v in b.payload_descriptors];_need(len(payload)==5,'five_payload_descriptors')
    _need(_same(dynamic[0],helper) and _same(dynamic[1],context_authority),'dynamic_helper_or_authority_binding')
    _need(len(static)+len(dynamic)+len(payload)<=256,'declared_input_cap')
    seen={};allpins=static+dynamic+payload
    for p in allpins:
        a.check();key=_path(p['path']);_need(key not in seen,'declared_role_alias_collision');seen[key]=p
        _need(not key.startswith(root_key+'\\') and key!=root_key,'run_output_in_declared_inputs')
        _need(key!=_path(context_protocol['path']),'protocol_in_static_or_payload_inputs')
    _need(payload[0]['path'].replace('/','\\').rsplit('\\',1)[-1]=='ggml-cpu-x64.dll','CPU_descriptor_basename')
    _need(all(p['path'].lower().endswith('.gguf') for p in payload[1:4]),'ordered_model_descriptor_roles')
    _need(all(not p['path'].lower().endswith('.gguf') for p in static+dynamic+[payload[0],payload[4]]),'model_role_alias')
    if cfg is not None:
        _shape(cfg,CONFIG_KEYS,'configuration')
        for key,value in FIXED.items():a.check();_need(_same(cfg[key],value),'configuration_fixed_value:'+key)
        _need(_same(cfg['limits'],LIMITS) and _same(cfg['hash_pass_policy'],HASH_POLICY),'configuration_limits_or_hash_policy')
        _need(_number(cfg['periodic_job_seconds']) and 0<cfg['periodic_job_seconds']<=120,'configuration_periodic_interval')
        _need(_same(cfg['helper'],helper),'configuration_helper_pin');_pin(cfg['executable'])
        for name,expected in (('software_inputs',static+dynamic),('payload_inputs',payload),('inputs',allpins)):
            _need(type(cfg[name]) is list and len(cfg[name])==len(expected),'configuration_roster_length:'+name)
            for pin in cfg[name]:a.check();_pin(pin)
            _need(_same(cfg[name],expected),'configuration_exact_roster:'+name)
        _need(cfg['output']==root and cfg['expected_pack_sha256']==payload[4]['sha256'],'configuration_output_or_pack')
        cpu_path=payload[0]['path'].replace('/','\\');runtime=cpu_path.rsplit('\\',1)[0]
        expected=[cfg['executable']['path'],'--recognize',runtime,root+'\\execution\\child',payload[4]['path'],'ggml-cpu-x64.dll',*[p['path'] for p in payload[1:4]]]
        _need(type(cfg['argv']) is list and _same(cfg['argv'],expected),'configuration_nine_argv')
        _text(cfg['command_line']);_need(type(cfg['environment']) is dict and all(type(k) is str and type(v) is str for k,v in cfg['environment'].items()),'configuration_environment')
    if auth is not None:
        _shape(auth,AUTHORITY_KEYS,'authority')
        expected=dict(schema_version=1,status='verified_build_software_and_descriptor_basis_not_execution_permission',mode='--recognize',execution_authorized=False,runtime_qualified=False,
            module_policy_id=FIXED['module_policy_id'],module_policy_sha256=FIXED['module_policy_sha256'],dynamic_dependencies=list(LABELS),software_inputs=static,payload_descriptors=payload)
        for key,value in expected.items():a.check();_need(_same(auth[key],value),'authority_binding:'+key)
        _text(auth['closure_scope']);static_by={_path(p['path']):p for p in static}
        for key in ('executable','verified_build','source','compiled_source_copy','runtime_pin_header','execution_contract','expected_pack_metadata'):
            a.check();p=_pin(auth[key]);_need(_path(p['path']) in static_by and _same(p,static_by[_path(p['path'])]),'authority_direct_static_reference:'+key)
            a.edge('@authority','@declared:'+_path(p['path']))
        _need(auth['execution_contract']['sha256']==FIXED['contract_sha256'],'authority_contract_fingerprint')
        if cfg is not None:_need(_same(cfg['executable'],auth['executable']),'authority_executable_matches_configuration')
    for pin in allpins:a.edge('@protocol','@authority' if _same(pin,context_authority) else '@declared:'+_path(pin['path']))
    a.binding='consistent_declared_bindings'
    return root,context_protocol,context_authority

def _marker(a,node,v):
    a.check();_need(v.get('authoritative') is True and v.get('automatic_retry') is False,'malformed_authoritative_marker:'+node)
    _need(not any(k in v for k in ('ready','verified','already_verified')),'marker_ready_field:'+node)
    if 'schema_version' in v:_need(type(v['schema_version']) is int and v['schema_version']==1,'marker_schema_version:'+node)

def _headers(a,raw,reservation,cfg):
    a.check();end=raw.find(b'\n');end2=raw.find(b'\n',end+1) if end>=0 else -1
    if end<0 or end2<0:a.incomplete_reason('journal_header_prefix_missing');return
    previous=None
    for index,line in enumerate((raw[:end+1],raw[end+1:end2+1])):
        a.check();row=a.json(line,'journal_header_'+str(index),65536);_shape(row,('sequence','event','details','previous_sha256','sha256'),'journal_header')
        _need(type(row['sequence']) is int and row['sequence']==index,'journal_header_sequence')
        _need(row['previous_sha256']==previous and _hex(row['sha256']),'journal_header_previous')
        unsigned={k:v for k,v in row.items() if k!='sha256'};_need(hashlib.sha256(_canonical(unsigned)).hexdigest()==row['sha256'],'journal_header_digest')
        if index==0:
            _need(row['event']=='build_reserved','journal_first_kind');d=row['details'];_shape(d,('run_id','owner_pid','created_at_utc'),'build_reserved')
            _need(type(d['run_id']) is str and UUID.fullmatch(d['run_id']) is not None,'journal_run_UUID')
            _need(_uint(d['owner_pid'],2**32-1) and d['owner_pid']>0,'journal_owner_PID');_utc(d['created_at_utc'])
            if reservation is not None:_need(type(reservation['owner_pid']) is int and reservation['owner_pid']==d['owner_pid'],'reservation_journal_owner')
        else:
            _need(row['event']=='detached_recognition_attempt_reserved','journal_second_kind');_shape(row['details'],('protocol_sha256','limits'),'attempt_header')
            if cfg is not None:_need(row['details']['protocol_sha256']==a.nodes['@protocol']['sha256'] and _same(row['details']['limits'],cfg['limits']),'journal_protocol_or_limits')
        previous=row['sha256']

def _run_graph(a,files,docs,cfg,root):
    report=docs.get('parent-report.json');receipt=docs.get('receipt.json');cleanup=docs.get('post-lease-cleanup.json');seal=docs.get('terminal-seal.json')
    required=('parent-reservation.json','effective-protocol.json','parent-report.json','execution/journal.jsonl','receipt.json','post-lease-cleanup.json','terminal-seal.json')
    for name in required:
        if name not in files:a.missing_node(name)
    reservation=docs.get('parent-reservation.json')
    if reservation is not None:
        _shape(reservation,('owner_pid','created_at_utc','status'),'parent_reservation')
        _need(_uint(reservation['owner_pid'],2**32-1) and reservation['owner_pid']>0 and reservation['status']=='reserved_before_journal_or_native_API','parent_reservation_PID_or_status');_utc(reservation['created_at_utc'])
    if 'execution/journal.jsonl' in files:_headers(a,files['execution/journal.jsonl'],reservation,cfg)
    if report is not None:
        _need(type(report.get('schema_version')) is int and report['schema_version']==1 and report.get('status') in (POSITIVE,'failed') and report.get('automatic_retry') is False,'report_required_projection')
        for key in ('reaped','call_return_observed'):
            if key in report:_need(type(report[key]) is bool,'report_bool:'+key)
        if 'returncode' in report:_need(_uint(report['returncode'],2**32-1),'report_returncode')
        if report['status']=='failed' or report.get('failure') is not None:a.negative('report_failure')
        for key in ('finalization_errors','terminal_observation_errors','cleanup_errors'):
            if key in report:_need(type(report[key]) is list,'report_error_list');
            if report.get(key):a.negative('report_'+key)
        if report.get('failure') is not None:_need(type(report['failure']) is dict and report['failure'],'report_failure_shape')
    for name in ('failure.json','terminal-publication-error.json','journal-close-error.json'):
        if name in docs:_marker(a,name,docs[name])
    if 'execution/child/attempt.json' in docs:
        attempt=docs['execution/child/attempt.json'];_need(type(attempt.get('schema_version')) is int and attempt['schema_version']==1 and attempt.get('mode')=='--recognize' and attempt.get('status')=='claimed_before_native_load' and attempt.get('draft') is True,'child_attempt_projection')
    final='execution/child/result.jsonl' in files;partial='execution/child/result.partial.jsonl' in files;child_failure='execution/child/failure.json' in files
    _need(not(final and (partial or child_failure)),'conflicting_child_final_partial_or_failure')
    if child_failure:
        child=docs.get('execution/child/failure.json');_need(child is not None and type(child.get('schema_version')) is int and child['schema_version']==1 and child.get('status')=='failed','child_failure_projection')
    if (final or partial or child_failure) and 'execution/child/attempt.json' not in files:a.missing_node('execution/child/attempt.json')
    if not(final or partial):a.incomplete_reason('child_result_not_created_or_unobserved')
    if report is not None and report['status']==POSITIVE and not a.vetoes:
        if report.get('call_return_observed') is not True or report.get('reaped') is not True or 'returncode' not in report:a.incomplete_reason('normal_child_return_fields_missing')
        elif report['returncode']!=0:a.negative('nonzero_child_return')
    late=docs.get('late-failure.json');late_exception=False
    if late is not None:
        _marker(a,'late-failure.json',late)
        if late.get('phase')=='post_lease_cleanup_or_terminal_sealing':
            _shape(late,EXCEPTION_LATE_KEYS,'exception_late_failure');late_exception=True
            _text(late['error_class'],128);_text(late['error'],512);_need(type(late['close_outcomes']) is list,'exception_close_outcomes')
            a.incomplete_reason('exception_variant_terminal_return_unproven')
        else:
            _shape(late,NORMAL_LATE_KEYS,'normal_late_failure');_need(type(late['schema_version']) is int and late['schema_version']==1 and late['phase']=='post_receipt_lease_cleanup' and late['error_class']=='LeaseCleanupOrParentDeadline','normal_late_constants')
            _need(type(late['parent_deadline_exceeded']) is bool and type(late['close_errors']) is list,'normal_late_flags')
            a.pin_link('late-failure.json',late['cleanup_artifact'],'post-lease-cleanup.json',files,root)
    if receipt is not None:
        _shape(receipt,RECEIPT_KEYS,'receipt');_need(type(receipt['schema_version']) is int and receipt['schema_version']==1 and receipt['status'] in (POSITIVE,'failed'),'receipt_constants');_text(receipt['failure_veto'],1024)
        if receipt['status']=='failed':a.negative('receipt_failed')
        if cfg is not None:_need(receipt['protocol_sha256']==a.nodes['@protocol']['sha256'],'receipt_protocol_SHA')
        if report is not None:_need(receipt['status']==report['status'],'receipt_report_status')
        excluded={'receipt.json','post-lease-cleanup.json','terminal-seal.json','late-failure.json','after-seal-failure.json','terminal-publication-error.json','journal-close-error.json'}
        expected=set(files)-excluded
        if 'failure.json' in expected and (report is None or report.get('failure') is None):expected.remove('failure.json')
        a.output_map('receipt.json',receipt['outputs'],files,ALLOWED-excluded)
        _need(set(receipt['outputs'])==expected,'early_receipt_source_membership')
        a.receipt_status='incomplete_early_branch' if any(x not in files for x in required[:4]) else 'matched_source_membership'
    if cleanup is not None:
        _shape(cleanup,CLEANUP_KEYS,'cleanup');_need(type(cleanup['schema_version']) is int and cleanup['schema_version']==1 and cleanup['status'] in ('failed','close_outcomes_retained') and cleanup['earlier_status'] in (POSITIVE,'failed'),'cleanup_constants')
        _need(_number(cleanup['parent_elapsed_after_leases_seconds']) and type(cleanup['parent_deadline_exceeded']) is bool and type(cleanup['close_errors']) is list and type(cleanup['outcomes']) is list and len(cleanup['outcomes'])<=256,'cleanup_scalar_projection')
        if cleanup['status']=='failed' or cleanup['primary_failure'] is not None or cleanup['close_errors'] or cleanup['parent_deadline_exceeded']:a.negative('cleanup_failure')
        if cleanup['primary_failure'] is not None:_need(type(cleanup['primary_failure']) is dict,'cleanup_primary_shape')
        for outcome in cleanup['outcomes']:
            a.check();_need(type(outcome) is dict,'cleanup_outcome_shape')
            for key in ('closed_before','close_attempted','close_return_observed','close_success','closed_after'):
                if key in outcome:_need(type(outcome[key]) is bool,'cleanup_outcome_bool')
            if outcome.get('prior_cleanup_errors') or outcome.get('primary_validation_error') or outcome.get('close_error') or outcome.get('closed_after') is False:a.negative('cleanup_outcome_error')
        a.optional_pin('post-lease-cleanup.json',cleanup['earlier_receipt'],'receipt.json',files,root)
        a.optional_pin('post-lease-cleanup.json',cleanup['primary_failure_marker'],'failure.json',files,root)
        if receipt is not None:_need(cleanup['earlier_receipt'] is not None,'cleanup_missing_existing_receipt_pin')
        if report is not None and cleanup['earlier_status']!=report['status']:
            pub=docs.get('terminal-publication-error.json');failure=cleanup['primary_failure']
            if report['status']==POSITIVE and cleanup['earlier_status']=='failed' and type(failure) is dict and failure.get('phase')=='terminal_publication' and pub is not None:
                _need(_same(pub.get('publication_error'),failure) and _same(pub.get('primary_failure'),failure) and failure in pub.get('finalization_errors',[]),'post_receipt_publication_phase')
                if 'failure.json' in docs:_need(all(_same(docs['failure.json'].get(k),v) for k,v in failure.items()),'post_receipt_primary_marker')
            else:a.incomplete_reason('earlier_status_timing_unproven')
        if report is not None and report.get('failure') is not None:_need(_same(report['failure'],cleanup['primary_failure']),'primary_failure_preservation')
        if late is not None:
            _need(_same(late['primary_failure'],cleanup['primary_failure']) and _same(late['primary_failure_marker'],cleanup['primary_failure_marker']),'late_cleanup_primary_links')
            if not late_exception:_need(_same(late['close_errors'],cleanup['close_errors']) and late['parent_deadline_exceeded'] is cleanup['parent_deadline_exceeded'],'normal_late_cleanup_flags')
    if seal is not None:
        _shape(seal,SEAL_KEYS,'terminal_seal');_need(type(seal['schema_version']) is int and seal['schema_version']==1 and seal['status'] in (POSITIVE,'failed') and seal['required'] is True and _number(seal['parent_elapsed_before_terminal_seal_seconds']),'terminal_seal_constants');_text(seal['failure_veto'],1024)
        if seal['status']=='failed':a.negative('terminal_seal_failed')
        a.pin_link('terminal-seal.json',seal['cleanup_artifact'],'post-lease-cleanup.json',files,root)
        a.optional_pin('terminal-seal.json',seal['earlier_receipt'],'receipt.json',files,root);a.optional_pin('terminal-seal.json',seal['primary_failure_marker'],'failure.json',files,root)
        a.optional_pin('terminal-seal.json',seal['late_failure_marker'],'late-failure.json',files,root)
        if cleanup is not None:
            _need(_same(seal['earlier_receipt'],cleanup['earlier_receipt']) and _same(seal['primary_failure_marker'],cleanup['primary_failure_marker']),'seal_cleanup_link_agreement')
            if cleanup['primary_failure'] is not None or cleanup['primary_failure_marker'] is not None or cleanup['close_errors'] or cleanup['parent_deadline_exceeded']:_need(seal['status']=='failed','positive_seal_over_preterminal_failure')
        expected=set(files)-{'terminal-seal.json','after-seal-failure.json'}
        if late_exception:
            expected.discard('late-failure.json');_need(seal['late_failure_marker'] is None,'post_terminal_exception_cannot_be_older_pin')
        elif late is not None:_need(seal['late_failure_marker'] is not None,'normal_late_marker_pin_missing')
        a.output_map('terminal-seal.json',seal['outputs'],files,ALLOWED-{'terminal-seal.json','after-seal-failure.json'})
        _need(set(seal['outputs'])==expected,'terminal_captured_universe_membership');a.terminal_match=not late_exception
    after=docs.get('after-seal-failure.json')
    if after is not None:
        _shape(after,('authoritative','automatic_retry','error_class','terminal_seal'),'after_seal_failure');_marker(a,'after-seal-failure.json',after)
        _need(after['error_class']=='ParentDeadlineAfterTerminalSeal','after_seal_class');a.pin_link('after-seal-failure.json',after['terminal_seal'],'terminal-seal.json',files,root)
    for stream in ('stdout.bin','stderr.bin'):
        if stream not in files:a.missing_node(stream)

def check_archive(captured,bindings,*,check):
    """Return captured graph consistency only; callback exceptions propagate."""
    if not callable(check):raise TypeError('required_deadline_callback')
    check()
    if type(captured) is not CapturedArchive or type(bindings) is not ArchiveBindings:raise TypeError('typed_immutable_archive_and_bindings_required')
    a=_Analysis(check);files={};docs={};bad=False
    # Filename veto is independent of successful marker parsing and graph checks.
    for name,_ in captured.run_files:
        check()
        if name in VETO_FILES:a.negative(name)
    try:
        total=sum(len(raw) for _,raw in captured.run_files)+sum(len(v) for v in (captured.protocol_bytes,captured.authority_bytes) if v is not None)
        _need(total<=MAX_TOTAL,'total_captured_byte_cap')
        seen=set()
        for name,raw in captured.run_files:
            check();_locator(name);key=name.lower();_need(key not in seen,'duplicate_or_alias_locator');seen.add(key)
            cap=65536 if name in ('stdout.bin','stderr.bin') or name.startswith('execution/child/') and name.endswith('.json') else 8388608 if name.endswith('.jsonl') else 4194304 if name=='parent-report.json' else MAX_JSON
            _need(len(raw)<=cap,'captured_leaf_byte_cap:'+name);files[name]=raw;a.nodes[name]=a.hash(raw)
        for name,raw,pin in (('@protocol',captured.protocol_bytes,bindings.protocol_pin),('@authority',captured.authority_bytes,bindings.authority_pin)):
            check();expected=_pin(pin)
            if raw is None:a.missing_node(name);continue
            _need(len(raw)<=MAX_JSON,'technical_JSON_cap');a.nodes[name]=a.hash(raw);_need(_same(a.nodes[name],{k:expected[k] for k in ('bytes','sha256')}),'technical_capture_pin:'+name)
            docs[name]=a.json(raw,name)
        cfg,auth=docs.get('@protocol'),docs.get('@authority');root,_,_=_declared(a,bindings,cfg,auth)
        if captured.protocol_bytes is not None and 'effective-protocol.json' in files:_need(files['effective-protocol.json']==captured.protocol_bytes,'protocol_effective_exact_bytes')
        for name,raw in files.items():
            check()
            if name.endswith('.json') and name!='effective-protocol.json':docs[name]=a.json(raw,name,65536 if name.startswith('execution/child/') else 4194304 if name=='parent-report.json' else MAX_JSON,canonical=not name.startswith('execution/child/'))
        _run_graph(a,files,docs,cfg,root);a.cycles()
    except _Bad as error:bad=True;a.issues.append(str(error))
    check();status='inconsistent_captured_graph' if bad else 'incomplete_captured_graph' if a.incomplete else 'consistent_captured_graph'
    disposition='source_negative' if a.vetoes else 'source_positive_observations_pending' if status=='consistent_captured_graph' else 'unresolved'
    value=dict(captured_graph_status=status,terminal_captured_universe_matches=a.terminal_match,early_receipt_membership_status=a.receipt_status,
        declared_binding_consistency=a.binding,source_terminal_disposition=disposition,failure_vetoes=list(a.vetoes),missing_nodes=sorted(a.missing),issues=list(a.issues),
        node_count=len(a.nodes),edge_count=len(a.edges),node_digests=dict(a.nodes),profile_qualified=False,originals_authenticated=False,actual_directory_complete=False,source_qualified=False,
        complete_journal_chain_validated=False,resource_or_profile_semantics_validated=False,owner_context_provenance_established=False)
    return CapturedArchiveResult(_freeze(value,check))
