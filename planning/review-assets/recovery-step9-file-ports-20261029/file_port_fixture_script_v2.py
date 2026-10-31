"""Callable FICTIONAL API/clock sequencer. No file-port state transitions or I/O."""
from dataclasses import dataclass
import re
from types import MappingProxyType

API_KEYS={
 'CreateFileW':('path','desired_access','share_mode','security','creation','flags','template'),
 'GetFileType':('handle',),'GetFileInformationByHandleEx':('handle','info_class','buffer_bytes'),
 'GetFinalPathNameByHandleW':('handle','capacity','flags'),'GetFileSizeEx':('handle',),
 'ReadFile':('handle','requested','overlapped'),'CloseHandle':('handle',),
 'GetFileAttributesExW':('path','info_level','buffer_bytes'),
 'FindFirstFileExW':('pattern','info_level','search_op','search_filter','flags'),
 'FindNextFileW':('handle','buffer_bytes'),'FindClose':('handle',),
 'CreateDirectoryW':('path','security'),'WriteFile':('handle','data_hex','overlapped'),'FlushFileBuffers':('handle',)}
BOOL_APIS=frozenset(API_KEYS)-{'CreateFileW','FindFirstFileExW','GetFileType','GetFinalPathNameByHandleW'}
HANDLE_APIS={'CreateFileW','FindFirstFileExW'}
RAW_KEYS={'value','last_error','error_defined','raw_count','raw_count_defined','buffer_hex','buffer_defined'}
CASE_KEYS={'id','required_vector','subcase','scope','request','initial','plan','path_records','script','expected'}
EXPECTED_KEYS={'disposition','namespace_owned','reservation_ready','known_read_bytes','hashed_bytes','captured_bytes','read_count_unknown','known_write_bytes','write_hash_bytes','flushed_known_bytes','write_count_unknown','slots','primary','secondary','terminal_ack','journal_recursive_events','api_attempts','api_returns','profile_qualified','runtime_authorized','originals_authenticated'}
ACTION_KEYS={'reserve_namespace_and_journal':({'path'},),'open_inspect_original':({'path'},),
 'hash_capture_original':({'slot','bytes'},),'close_slot':({'slot'},{'slot','requested_closer'}),
 'scan_directory':({'path','declared_empty'},),'inspect_ancestors':({'paths'},),
 'write_output_record':({'slot','record_hex'},),'finalize_output':({'slot'},),
 'admit_plan':({'plan_ref'},{'path','use'}),'validate_handoff':({'facts_ref'},),
 'validate_seal_graph':({'facts_ref'},),'decode_raw_BOOL':({'api_name','raw_value'},),'create_namespace':({'path'},)}
FACTS={'non_dot_successes_before_stop','nodes','edges','operation_outcomes',
 'origin_label','required_port','supplied_port','required_nonce','supplied_nonce','serialized_ready','handoff_count','cached_own_module',
 'python_characters','record_hex','returned_slice_offset','known_count','no_artifact_pin','no_recursive_journal_events'}
OPEN_STATES={'reserved','entered_return_unknown','observed_owned','known_failure_no_handle','malformed_or_return_unknown'}
CLOSE_STATES={'not_attempted','reserved_once','entered_return_unknown','returned_success','returned_failure','not_dispatched_deadline'}
HEX=re.compile(r'[0-9a-f]*\Z')


class ScriptMismatch(ValueError):pass
class SyntheticFailure(RuntimeError):pass
class UnreturnedCall(RuntimeError):pass


def need(test,reason):
    if not test:raise ScriptMismatch(reason)


def integer(value,minimum,maximum):
    return type(value) is int and minimum<=value<=maximum


def same(a,b):
    if type(a) is not type(b):return False
    if type(a) is dict:return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
    if type(a) is list:return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b


def freeze(value):
    if type(value) is dict:return MappingProxyType({k:freeze(v) for k,v in value.items()})
    if type(value) is list:return tuple(freeze(v) for v in value)
    return value


def thaw(value):
    if type(value) is MappingProxyType:return {k:thaw(v) for k,v in value.items()}
    if type(value) is tuple:return [thaw(v) for v in value]
    return value


def blob(value,maximum=65536):
    need(type(value) is str and len(value)<=maximum*2 and len(value)%2==0 and HEX.fullmatch(value) is not None,'bounded_canonical_hex')
    return bytes.fromhex(value)


def exception(spec):
    if spec is None:return None
    need(type(spec) is dict and set(spec)=={'class','message'} and type(spec['message']) is str and len(spec['message'])<=256,'exception_shape')
    classes={'SyntheticFailure':SyntheticFailure,'UnreturnedCall':UnreturnedCall,'KeyboardInterrupt':KeyboardInterrupt,'SystemExit':SystemExit,'UnicodeError':UnicodeError}
    need(spec['class'] in classes,'exception_class');return classes[spec['class']](spec['message'])


@dataclass(frozen=True,slots=True)
class RawReturn:
    value:object
    last_error:int
    error_defined:bool
    raw_count:object
    raw_count_defined:bool
    buffer:bytes
    buffer_defined:bool


def raw_return(name,value):
    need(type(value) is dict and set(value)==RAW_KEYS,'raw_return_shape')
    scalar=value['value']
    if name in BOOL_APIS:need(integer(scalar,-2**31,2**31-1),'strict_signed32_BOOL')
    elif name in HANDLE_APIS:need(scalar is None or integer(scalar,0,2**64-1),'strict_HANDLE_scalar')
    else:need(integer(scalar,0,2**32-1),'strict_DWORD_scalar')
    need(integer(value['last_error'],0,2**32-1),'last_error_u32')
    for key in ('error_defined','raw_count_defined','buffer_defined'):need(type(value[key]) is bool,'definedness_bool')
    need(value['raw_count'] is None or integer(value['raw_count'],0,2**32-1),'raw_count_u32_or_null')
    return RawReturn(scalar,value['last_error'],value['error_defined'],value['raw_count'],value['raw_count_defined'],blob(value['buffer_hex']),value['buffer_defined'])


def arguments(name,args):
    need(type(args) is dict and set(args)==set(API_KEYS[name]),'exact_API_arguments')
    for key,value in args.items():
        if key in ('security','template','overlapped','search_filter'):need(value is None,'null_only_argument')
        elif key in ('path','pattern'):
            need(type(value) is str and len(value)<=8192,'bounded_path_string')
            try:n=len(value.encode('utf-16-le'))//2
            except UnicodeError as error:raise ScriptMismatch('scalar_path') from error
            need(n<=8192,'bounded_UTF16_path')
        elif key=='data_hex':blob(value)
        else:need(integer(value,0,2**64-1 if key=='handle' else 2**32-1),'API_integer_argument')


def validate_case(case):
    need(type(case) is dict and set(case)==CASE_KEYS,'case_shape')
    need(type(case['id']) is str and len(case['id'])<=128,'case_ID')
    need(case['required_vector'] is None or integer(case['required_vector'],0,16),'family_ID')
    request=case['request'];need(type(request) is dict and set(request)=={'actions','facts'},'request_shape')
    need(type(request['actions']) is list and len(request['actions'])<=32,'action_cap')
    for action in request['actions']:
        need(type(action) is dict and set(action)=={'operation','arguments'} and action['operation'] in ACTION_KEYS,'closed_action')
        need(type(action['arguments']) is dict and set(action['arguments']) in ACTION_KEYS[action['operation']],'closed_action_arguments')
    need(type(request['facts']) is dict and set(request['facts'])<=FACTS,'closed_control_facts')
    for action in request['actions']:
        if 'plan_ref' in action['arguments']:need(action['arguments']['plan_ref']=='case.plan','fixed_plan_reference')
        if 'facts_ref' in action['arguments']:need(action['arguments']['facts_ref']=='case.request.facts','fixed_facts_reference')
    plan=case['plan']
    need(type(plan) is dict and set(plan)=={'N','B','M','U','Dk','S','E','F','sumRi','sumWj','capture_bytes','report_bytes','file_byte_sizes'},'closed_numeric_plan_slice')
    need(all(integer(v,0,2**63-1) for k,v in plan.items() if k not in ('Dk','file_byte_sizes')),'bounded_plan_integers')
    need(type(plan['Dk']) is list and len(plan['Dk'])==2 and all(integer(v,0,9) for v in plan['Dk']),'bounded_directory_counts')
    need(type(plan['file_byte_sizes']) is list and len(plan['file_byte_sizes'])<=257 and all(integer(v,0,2**63-1) for v in plan['file_byte_sizes']),'bounded_fictional_file_sizes')
    need(type(case['script']) is list and 1<=len(case['script'])<=512,'script_cap')
    need(case['script'][0]['kind']=='clock' and case['script'][0]['now_ns']==0,'one_fictional_initial_clock')
    need(type(case['path_records']) is list and len(case['path_records'])<=16,'path_roster_cap')
    for record in case['path_records']:
        need(type(record) is dict and set(record)=={'kind','path','utf16_units'},'path_record_shape')
        path=record['path'];need(type(path) is str and len(path)<=8192,'path_string_cap')
        try:n=len(path.encode('utf-16-le'))//2
        except UnicodeError as error:raise ScriptMismatch('path_scalar') from error
        need(integer(record['utf16_units'],0,8192) and record['utf16_units']==n,'UTF16_unit_count')
    expected=case['expected'];need(type(expected) is dict and set(expected)==EXPECTED_KEYS,'expected_projection_shape')
    for key in ('namespace_owned','reservation_ready','read_count_unknown','write_count_unknown'):need(type(expected[key]) is bool,'expected_bool')
    for key in ('known_read_bytes','hashed_bytes','captured_bytes','known_write_bytes','write_hash_bytes','flushed_known_bytes'):
        need(integer(expected[key],0,67108864),'expected_count_cap')
    need(expected['primary'] is None or type(expected['primary']) is str and len(expected['primary'])<=256,'expected_primary')
    need(type(expected['secondary']) is list and len(expected['secondary'])<=16 and all(type(v) is str for v in expected['secondary']),'expected_secondary')
    need(type(expected['slots']) is list and len(expected['slots'])<=16,'expected_slot_cap')
    for entry in expected['slots']:
        need(type(entry) is dict and set(entry)=={'id','kind','handle','open_state','close_state','closer','close_attempts'},'slot_shape')
        need(type(entry['id']) is str and entry['kind'] in ('original_file','output_file','file_search'),'slot_identity')
        need(entry['handle'] is None or integer(entry['handle'],0,2**64-1),'slot_handle')
        need(entry['open_state'] in OPEN_STATES and entry['close_state'] in CLOSE_STATES and integer(entry['close_attempts'],0,1),'slot_state')
        need(entry['closer'] in (None,'CloseHandle','FindClose'),'slot_closer')
    for key in ('profile_qualified','runtime_authorized','originals_authenticated','terminal_ack'):need(expected[key] is False,'fiction_not_authority')
    need(expected['journal_recursive_events']==0 and type(expected['journal_recursive_events']) is int,'no_recursive_output_journal_events')
    need(type(expected['api_attempts']) is dict and set(expected['api_attempts'])==set(API_KEYS),'expected_API_census')
    need(type(expected['api_returns']) is dict and set(expected['api_returns'])==set(API_KEYS),'expected_return_census')
    need(all(integer(n,0,192) for n in (*expected['api_attempts'].values(),*expected['api_returns'].values())),'strict_API_counts')
    attempts={k:0 for k in API_KEYS};returns={k:0 for k in API_KEYS};previous=0;api_steps=0;total_buffer=0
    for step in case['script']:
        need(type(step) is dict and type(step.get('before_projection')) is dict,'step_and_projection')
        if step['kind']=='clock':
            need(set(step)=={'kind','now_ns','raises','before_projection'} and integer(step['now_ns'],0,600000000000),'clock_shape_or_numeric_cap')
            need(step['now_ns']>=previous,'monotonic_fictional_clock');previous=step['now_ns'];exception(step['raises'])
        elif step['kind']=='hook':
            need(set(step)=={'kind','name','raises','before_projection'} and step['name'] in ('copy_bytes','hash_update','log_append'),'hook_shape');exception(step['raises'])
        else:
            need(step['kind']=='api' and set(step)=={'kind','name','arguments','outcome','before_projection'},'API_step_shape')
            name=step['name'];need(name in API_KEYS,'closed_14_API_census');need(previous<300000000000,'no_API_dispatch_at_or_after_hard_cutoff')
            arguments(name,step['arguments']);outcome=step['outcome'];need(type(outcome) is dict and set(outcome)=={'raise','raw_return'},'API_outcome_shape')
            api_steps+=1;need(api_steps<=192,'API_steps_cap');attempts[name]+=1
            if outcome['raise'] is None:
                raw=raw_return(name,outcome['raw_return']);total_buffer+=len(raw.buffer);returns[name]+=1
            else:exception(outcome['raise']);need(outcome['raw_return'] is None,'unreturned_has_no_result')
    need(total_buffer<=2097152,'case_buffer_cap')
    need(attempts==expected['api_attempts'] and returns==expected['api_returns'],'authored_dispatch_counts_match_script')


class FakeScript:
    """Return literal planned observations; never compute port ownership/state."""
    def __init__(self,case,*,observe):
        validate_case(case);need(callable(observe),'read_only_observer_required')
        self._case=freeze(case);self._steps=self._case['script'];self._index=0;self._observe=observe
        self._exceptions=tuple(exception(thaw(s['outcome']['raise'])) if s['kind']=='api' else exception(thaw(s['raises'])) for s in self._steps)
        self._returns=tuple(raw_return(s['name'],thaw(s['outcome']['raw_return'])) if s['kind']=='api' and s['outcome']['raise'] is None else None for s in self._steps)
    @property
    def index(self):return self._index
    @property
    def expected(self):return thaw(self._case['expected'])
    def _next(self,kind):
        need(self._index<len(self._steps),'extra_script_dispatch')
        step=self._steps[self._index];need(step['kind']==kind,'wrong_script_step_kind')
        required=thaw(step['before_projection']);observed=self._observe()
        need(type(observed) is dict and all(k in observed and same(observed[k],v) for k,v in required.items()),'checkpoint_before_dispatch_mismatch')
        index=self._index;self._index+=1;return step,index
    def api(self,name,args):
        step,index=self._next('api');need(name==step['name'] and same(args,thaw(step['arguments'])),'unexpected_API_dispatch')
        if self._exceptions[index] is not None:raise self._exceptions[index]
        return self._returns[index]
    def clock(self):
        step,index=self._next('clock')
        if self._exceptions[index] is not None:raise self._exceptions[index]
        return step['now_ns']/1000000000
    def hook(self,name):
        step,index=self._next('hook');need(name==step['name'],'unexpected_hook')
        if self._exceptions[index] is not None:raise self._exceptions[index]
    def assert_exhausted(self):need(self._index==len(self._steps),'unconsumed_script_steps')
