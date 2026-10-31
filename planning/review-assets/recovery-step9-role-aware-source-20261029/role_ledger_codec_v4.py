"""Pure bounded ROLE_AWARE_LEDGER_1 codec. No owner, files or physical I/O."""
import hashlib
import json
import math
import re
import struct
from types import MappingProxyType

ENUMS = {'artifact': {'candidate-ledger.bin': 1, 'candidate.json': 5, 'child/attempt.json': 11, 'child/failure.json': 12, 'child/result.partial.jsonl': 10, 'cleanup.json': 6, 'failure.json': 7, 'journal.jsonl': 3, 'producer-report.json': 4, 'receipt.json': 8, 'seal.json': 9, 'stderr.bin': 14, 'stdout.bin': 13, 'terminal-ledger.bin': 2}, 'artifact_state': {'BUILDING': 1, 'ISSUED': 3, 'RESERVED': 0, 'UNISSUED_PARTIAL': 2, 'UNKNOWN_RETURN': 4}, 'buffer': {'DEFINED': 3, 'INCOMPLETE_UNKNOWN': 4, 'NOT_APPLICABLE': 0, 'RAW_RETAINED': 2, 'RESERVED': 1}, 'call_flags_bits': {'ACCOUNTING_FAULT': 15, 'BUFFER_DATA_OBSERVED': 14, 'BUFFER_PRESENT': 38, 'CAPTURE_REQUESTED': 29, 'CLOSE_RIGHT_CONSUMED': 16, 'COPY_ATTEMPTED': 27, 'COPY_RETURN_OBSERVED': 28, 'COUNT_AUX_ACK': 8, 'COUNT_DEFINED': 4, 'COUNT_DOMAIN_VALID': 19, 'COUNT_OBSERVED': 3, 'ERROR_DEFINED': 6, 'ERROR_DEFINITION_OBSERVED': 31, 'ERROR_DOMAIN_VALID': 20, 'ERROR_OBSERVED': 5, 'HASH_ATTEMPTED': 25, 'HASH_RETURN_OBSERVED': 26, 'IDENTITY_VERIFIED_AT_DISPATCH': 17, 'INPUT_HANDLE_PRESENT': 36, 'INVOKED': 0, 'MALFORMED_RAW': 30, 'POST_CLOCK_ATTEMPTED': 22, 'POST_CLOCK_RETURN_OBSERVED': 24, 'PRE_CLOCK_ATTEMPTED': 21, 'PRE_CLOCK_RETURN_OBSERVED': 23, 'QUERY_CAPTURE_OBSERVED': 12, 'QUERY_DEFINED': 13, 'QUERY_SPAN_PRESENT': 39, 'REQUESTED_PRESENT': 37, 'RIGHT_TRANSFER_ACK': 9, 'SCALAR_AUX_ACK': 7, 'SCALAR_DOMAIN_VALID': 18, 'SCALAR_NULL': 2, 'SCALAR_OBSERVED': 1, 'STOPPED': 11, 'WRAPPER_RETURNED': 10}, 'capture': {'COMPLETE': 2, 'FAILED': 3, 'NOT_REQUESTED': 0, 'PENDING': 1}, 'clock': {'F64': 2, 'I64': 1, 'UNOBSERVED': 0}, 'close': {'ENTERED_RETURN_UNKNOWN': 2, 'NOT_ATTEMPTED': 0, 'NOT_DISPATCHED_DEADLINE': 5, 'RESERVED': 1, 'RETURNED_FAILURE': 4, 'RETURNED_SUCCESS': 3}, 'diagnostic_flags_bits': {'ARGS_TRUNCATED': 2, 'CLASS_TRUNCATED': 0, 'FORMAT_FAILED': 3, 'MESSAGE_TRUNCATED': 1}, 'diagnostic_state': {'COMMITTED': 2, 'FORMAT_FALLBACK': 3}, 'file_flags_bits': {'ACTUAL_DIGEST_PRESENT': 1, 'ASSEMBLY_RETAINED': 13, 'BLOB_ISSUED': 14, 'CAPTURE_COMPLETE': 5, 'CAPTURE_REQUESTED': 2, 'CLOSE_RESERVED': 9, 'CLOSE_SUCCESS_KNOWN': 11, 'CLOSE_SUCCESS_TRUE': 12, 'COPY_UNKNOWN': 8, 'EARLY': 10, 'EXPECTED_DIGEST_PRESENT': 0, 'EXPECTED_SIZE_PRESENT': 15, 'HASH_ATTEMPTED': 3, 'HASH_COMPLETE': 4, 'HASH_UNKNOWN': 7, 'READ_UNKNOWN': 6}, 'fold': {'COMMITTED': 2, 'COMMITTING': 1, 'FAILED_AFTER_COMMIT': 4, 'FAILED_BEFORE_COMMIT': 3, 'PENDING': 0}, 'header_flags_bits': {'ACCOUNTING_FAULT': 3, 'CLOCK_INVALID': 5, 'COPY_UNKNOWN': 2, 'HASH_UNKNOWN': 1, 'PREVIOUS_LEDGER_PRESENT': 6, 'PRIMARY_PRESENT': 4, 'READ_UNKNOWN': 0}, 'identity': {'IN_PROGRESS': 1, 'NOT_ATTEMPTED': 0, 'REFUSED': 3, 'UNKNOWN': 4, 'VERIFIED': 2}, 'module_flags': {'ACCEPTED': 2, 'CACHED': 3, 'PACKAGE': 0, 'RETURN_OBSERVED': 1}, 'open': {'ENTERED_RETURN_UNKNOWN': 2, 'KNOWN_FAILURE_NO_HANDLE': 4, 'OWNED': 3, 'OWNERSHIP_UNKNOWN': 5, 'RESERVED': 1, 'UNOPENED': 0}, 'phase': {'CANDIDATE': 1, 'FRAGMENT': 0, 'TERMINAL': 2}, 'phase_code': {'RawReturn_allocation': 5, 'admit_plan': 18, 'admit_reconcile': 38, 'after_count_before_aux': 6, 'after_scalar_before_aux': 2, 'after_scalar_before_right_transfer': 3, 'archive': 40, 'authority_factory': 36, 'before_final_ack': 46, 'bind_ports': 15, 'bind_test_compiler': 17, 'bind_test_hooks': 16, 'binding_invoke': 0, 'buffer_copy': 7, 'canonical_reconcile': 48, 'capture_early': 20, 'checker_factory': 37, 'claim_continuation': 22, 'cleanup_publication': 13, 'close_wrapper': 12, 'consistency': 44, 'continue_once': 24, 'copy_bytes': 45, 'core': 43, 'diagnostic_format': 34, 'encoding': 49, 'entry': 14, 'error_copy': 4, 'final_clock': 35, 'finalize': 25, 'fragment': 53, 'freeze': 50, 'generated_checker': 51, 'handoff': 11, 'hash_remaining': 39, 'hash_update': 8, 'identity_query': 10, 'issue_continuation': 21, 'journal': 41, 'journal_append': 26, 'journal_close': 27, 'legacy_projection': 52, 'load_source': 23, 'original_close': 33, 'post_call_clock': 9, 'pre_dispatch': 1, 'publish_candidate': 28, 'publish_cleanup': 29, 'publish_failure': 30, 'publish_receipt': 31, 'publish_seal': 32, 'reserve_output': 19, 'resources': 42, 'source_admission': 47}, 'profile': {'ORIGINAL7_N4': 1, 'ORIGINAL7_PROSPECTIVE': 2, 'UNQUALIFIED_FRAGMENT': 0}, 'role': {'CAPTURED_METADATA': 2, 'CAPTURED_SOFTWARE': 1, 'HASH_ONLY_BULK': 3, 'NONE_FRAGMENT_ONLY': 0}, 'severity': {'FORMATTER_FAILURE': 3, 'PRIMARY': 1, 'SECONDARY': 2}, 'status': {'INCOMPLETE': 3, 'OBSERVED_COMPLETE': 1, 'OBSERVED_NEGATIVE': 2}, 'target': {'ANCESTOR': 2, 'GENERATED': 4, 'NAMESPACE': 5, 'ORIGINAL': 1, 'SEARCH': 3}, 'wrapper': {'NOT_RETURNED': 0, 'RAISED': 2, 'RETURNED': 1}}
APIS = [{'complete_ledger_allowed': True, 'count_applicable': False, 'fragment_allowed': True, 'id': 1, 'name': 'CreateFileW', 'query_frame_bytes': 0, 'scalar': 'HANDLE', 'target': 'ORIGINAL'}, {'complete_ledger_allowed': True, 'count_applicable': False, 'fragment_allowed': True, 'id': 2, 'name': 'GetFileType', 'query_frame_bytes': 0, 'scalar': 'DWORD', 'target': 'ORIGINAL'}, {'complete_ledger_allowed': True, 'count_applicable': False, 'fragment_allowed': True, 'id': 3, 'name': 'GetFileInformationByHandleEx', 'query_frame_bytes': 8, 'scalar': 'BOOL', 'target': 'ORIGINAL'}, {'complete_ledger_allowed': True, 'count_applicable': False, 'fragment_allowed': True, 'id': 4, 'name': 'GetFinalPathNameByHandleW', 'query_frame_bytes': 8202, 'scalar': 'DWORD', 'target': 'ORIGINAL'}, {'complete_ledger_allowed': True, 'count_applicable': False, 'fragment_allowed': True, 'id': 5, 'name': 'GetFileSizeEx', 'query_frame_bytes': 8, 'scalar': 'BOOL', 'target': 'ORIGINAL'}, {'complete_ledger_allowed': True, 'count_applicable': True, 'fragment_allowed': True, 'id': 6, 'name': 'ReadFile', 'query_frame_bytes': 0, 'scalar': 'BOOL', 'target': 'ORIGINAL'}, {'complete_ledger_allowed': True, 'count_applicable': False, 'fragment_allowed': True, 'id': 7, 'name': 'CloseHandle', 'query_frame_bytes': 0, 'scalar': 'BOOL', 'target': 'ORIGINAL'}, {'complete_ledger_allowed': False, 'count_applicable': False, 'fragment_allowed': True, 'id': 8, 'name': 'GetFileAttributesExW', 'query_frame_bytes': 36, 'scalar': 'BOOL', 'target': 'ANCESTOR'}, {'complete_ledger_allowed': False, 'count_applicable': False, 'fragment_allowed': True, 'id': 9, 'name': 'FindFirstFileExW', 'query_frame_bytes': 592, 'scalar': 'HANDLE', 'target': 'SEARCH'}, {'complete_ledger_allowed': False, 'count_applicable': False, 'fragment_allowed': True, 'id': 10, 'name': 'FindNextFileW', 'query_frame_bytes': 592, 'scalar': 'BOOL', 'target': 'SEARCH'}, {'complete_ledger_allowed': False, 'count_applicable': False, 'fragment_allowed': True, 'id': 11, 'name': 'FindClose', 'query_frame_bytes': 0, 'scalar': 'BOOL', 'target': 'SEARCH'}, {'complete_ledger_allowed': False, 'count_applicable': False, 'fragment_allowed': True, 'id': 12, 'name': 'CreateDirectoryW', 'query_frame_bytes': 0, 'scalar': 'BOOL', 'target': 'NAMESPACE'}, {'complete_ledger_allowed': False, 'count_applicable': True, 'fragment_allowed': True, 'id': 13, 'name': 'WriteFile', 'query_frame_bytes': 0, 'scalar': 'BOOL', 'target': 'GENERATED'}, {'complete_ledger_allowed': False, 'count_applicable': False, 'fragment_allowed': True, 'id': 14, 'name': 'FlushFileBuffers', 'query_frame_bytes': 0, 'scalar': 'BOOL', 'target': 'GENERATED'}]
LAYOUTS = {'header': (('magic', 0, 8, 'ascii8'), ('format_version', 8, 2, 'u16'), ('value_schema_version', 10, 2, 'u16'), ('profile', 12, 2, 'u16'), ('phase', 14, 2, 'u16'), ('status', 16, 2, 'u16'), ('header_bytes', 18, 2, 'u16'), ('section_count', 20, 2, 'u16'), ('file_count', 22, 2, 'u16'), ('call_count', 24, 4, 'u32'), ('module_count', 28, 2, 'u16'), ('diagnostic_count', 30, 2, 'u16'), ('edge_count', 32, 4, 'u32'), ('flags', 36, 4, 'u32'), ('total_bytes', 40, 8, 'u64'), ('captured_input_bytes', 48, 8, 'u64'), ('known_read_bytes', 56, 8, 'u64'), ('hashed_bytes', 64, 8, 'u64'), ('copied_bytes', 72, 8, 'u64'), ('origin_data_id', 80, 8, 'u64'), ('ledger_sequence', 88, 8, 'u64'), ('start_clock_bits', 96, 8, 'typed_clock_bits'), ('latest_clock_bits', 104, 8, 'typed_clock_bits'), ('freeze_clock_bits', 112, 8, 'typed_clock_bits'), ('clock_tags', 120, 1, 'u8'), ('reserved_121_127', 121, 7, 'zero_bytes'), ('previous_ledger_sha256', 128, 32, 'digest32'), ('qualification_bits', 160, 8, 'u64_must_be_zero'), ('reserved_R', 168, 4, 'u32'), ('reserved_C', 172, 4, 'u32'), ('reserved_E', 176, 4, 'u32'), ('early_count', 180, 2, 'u16'), ('module_count_repeat', 182, 2, 'u16'), ('read_chunk', 184, 4, 'u32'), ('path_policy', 188, 2, 'u16'), ('reserved_to_descriptors', 190, 66, 'zero_bytes'), ('section_descriptors', 256, 512, '8x64'), ('reserved_zero_tail', 768, 3328, 'zero_bytes')), 'section_descriptor': (('id', 0, 2, 'u16'), ('record_size', 2, 2, 'u16'), ('count', 4, 4, 'u32'), ('offset', 8, 8, 'u64'), ('length', 16, 8, 'u64'), ('sha256', 24, 32, 'digest32'), ('flags', 56, 4, 'u32_must_be_zero'), ('reserved_zero_tail', 60, 4, 'zero_bytes')), 'call_record': (('ordinal', 0, 4, 'u32'), ('file_id', 4, 2, 'u16'), ('api', 6, 1, 'u8'), ('record_version', 7, 1, 'u8'), ('fact_flags', 8, 8, 'u64'), ('requested', 16, 4, 'u32'), ('buffer_id', 20, 2, 'u16'), ('phase', 22, 2, 'u16'), ('generation', 24, 4, 'u32'), ('buffer_written', 28, 4, 'u32'), ('raw_scalar_bits', 32, 8, 'u64'), ('raw_count', 40, 4, 'u32'), ('raw_error', 44, 4, 'u32'), ('hashed_contribution', 48, 8, 'u64'), ('captured_contribution', 56, 8, 'u64'), ('known_count_contribution', 64, 8, 'u64'), ('query_offset', 72, 4, 'u32'), ('query_length', 76, 4, 'u32'), ('input_handle_bits', 80, 8, 'u64'), ('pre_dispatch_clock_bits', 88, 8, 'typed_clock_bits'), ('post_binding_clock_bits', 96, 8, 'typed_clock_bits'), ('error_id', 104, 4, 'optional_u32'), ('path_id', 108, 2, 'u16'), ('reserved_zero', 110, 2, 'u16'), ('fold_state', 112, 4, 'u32'), ('buffer_state', 116, 4, 'u32'), ('reserved_zero_tail', 120, 136, 'zero_bytes')), 'file_record': (('ordinal', 0, 2, 'u16'), ('role', 2, 1, 'u8'), ('capture_state', 3, 1, 'u8'), ('target_class', 4, 1, 'u8'), ('open_state', 5, 1, 'u8'), ('identity_state', 6, 1, 'u8'), ('close_state', 7, 1, 'u8'), ('flags', 8, 8, 'u64'), ('descriptor_id', 16, 4, 'u32'), ('path_offset', 20, 4, 'u32'), ('path_bytes', 24, 4, 'u32'), ('path_utf16_units', 28, 2, 'u16'), ('reserved_30', 30, 2, 'zero_bytes'), ('expected_size', 32, 8, 'u64'), ('expected_sha256', 40, 32, 'digest32'), ('actual_sha256', 72, 32, 'digest32'), ('open_ordinal', 104, 4, 'optional_u32'), ('close_ordinal', 108, 4, 'optional_u32'), ('known_read_bytes', 112, 8, 'u64'), ('hashed_bytes', 120, 8, 'u64'), ('captured_bytes', 128, 8, 'u64'), ('query_offset', 136, 4, 'u32'), ('query_length', 140, 4, 'u32'), ('first_diagnostic', 144, 4, 'optional_u32'), ('read_reservations', 148, 4, 'u32'), ('read_invocations', 152, 4, 'u32'), ('captured_blob_length', 156, 4, 'u32'), ('early_ordinal', 160, 2, 'optional_u16'), ('path_id', 162, 2, 'u16'), ('read_generation', 164, 4, 'u32'), ('module_ordinal', 168, 2, 'optional_u16'), ('reserved_zero_tail', 170, 86, 'zero_bytes')), 'module_record': (('ordinal', 0, 2, 'u16'), ('file_ordinal', 2, 2, 'u16'), ('flags', 4, 2, 'u16'), ('dependency_count', 6, 2, 'u16'), ('name_offset', 8, 4, 'u32'), ('name_length', 12, 2, 'u16'), ('reserved_14', 14, 2, 'zero_bytes'), ('edge_offset', 16, 4, 'u32'), ('first_diagnostic', 20, 4, 'optional_u32'), ('attempt_order', 24, 2, 'optional_u16'), ('return_order', 26, 2, 'optional_u16'), ('cache_hit_count', 28, 2, 'u16'), ('reserved_30', 30, 2, 'zero_bytes'), ('reserved_zero_tail', 32, 32, 'zero_bytes')), 'diagnostic_record': (('ordinal', 0, 4, 'u32'), ('state', 4, 1, 'u8'), ('flags', 5, 1, 'u8'), ('phase', 6, 2, 'u16'), ('opaque_identity_id', 8, 8, 'u64'), ('call_ordinal', 16, 4, 'optional_u32'), ('secondary_of', 20, 4, 'optional_u32'), ('class_bytes', 24, 2, 'u16'), ('message_bytes', 26, 2, 'u16'), ('args_bytes', 28, 2, 'u16'), ('reserved_30', 30, 2, 'zero_bytes'), ('clock_bits', 32, 8, 'typed_clock_bits'), ('clock_tag', 40, 1, 'u8'), ('severity', 41, 1, 'u8'), ('reserved_header', 42, 86, 'zero_bytes'), ('class_utf8', 128, 96, 'fixed96'), ('message_utf8', 224, 512, 'fixed512'), ('args_utf8', 736, 256, 'fixed256'), ('reserved_zero_tail', 992, 32, 'zero_bytes'))}
CALL_KEYS = ('ordinal', 'file_id', 'api', 'record_version', 'flags', 'requested', 'buffer_id', 'phase', 'generation', 'buffer_written', 'scalar_atom', 'count_atom', 'error_atom', 'error_definition_atom', 'hashed_contribution', 'captured_contribution', 'known_count_contribution', 'query_offset', 'query_length', 'input_handle_atom', 'pre_dispatch_clock', 'post_binding_clock', 'error_id', 'path_id', 'fold_state', 'buffer_state')
HEADER_KEYS = ('profile', 'phase', 'status', 'origin_data_id', 'ledger_sequence', 'start_clock', 'latest_clock', 'freeze_clock', 'previous_ledger_sha256', 'reserved_R', 'reserved_C', 'reserved_E', 'early_count', 'read_chunk', 'flags')

MAX_BYTES=14800384
TOP_KEYS=('header','files','calls','queries','paths','modules','module_names','module_edges','diagnostics')
WIDTHS=(256,256,1,1,64,1,2,1024)
SECTIONS=('files','calls','queries','paths','modules','module_names','module_edges','diagnostics')
INVALID=(1<<64)-1
ZERO32=bytes(32)
ERROR_NAMES=('TYPE_DOMAIN','SCHEMA_KEYS','INTEGER_DOMAIN','SIZE_CAP','OVERFLOW','MAGIC_VERSION','RESERVED_NONZERO','SECTION_LAYOUT','SECTION_DIGEST','TRAILING_BYTES','ENUM_DOMAIN','ATOM_DOMAIN','STATE_CONTRADICTION','QUERY_SPAN','PATH_DOMAIN','MODULE_GRAPH','ROLE_CAPTURE','CLOCK_DOMAIN','DIAGNOSTIC_LAYOUT','REFERENCE_DOMAIN','UNENCODABLE_RAW','LEGACY_NOT_REPRESENTABLE','UNISSUED_ARTIFACT')

class FormatError(ValueError):
    __slots__=('_code','_offset','_path')
    def __init__(self,code,offset=None,path=()):
        ValueError.__init__(self,code)
        object.__setattr__(self,'_code',code);object.__setattr__(self,'_offset',offset);object.__setattr__(self,'_path',tuple(path))
    def __setattr__(self,key,value):
        if key in ('code','offset','path','_code','_offset','_path'):raise TypeError('immutable FormatError metadata')
        BaseException.__setattr__(self,key,value)
    code=property(lambda self:self._code)
    offset=property(lambda self:self._offset)
    path=property(lambda self:self._path)

def require(ok,code='STATE_CONTRADICTION',path=(),offset=None):
    if not ok:raise FormatError(code,offset,path)
def integer(v,cap=(1<<64)-1,path=(),minimum=0):
    require(type(v) is int,'TYPE_DOMAIN',path)
    require(minimum<=v<=cap,'INTEGER_DOMAIN',path)
    return v
def keys(v,names,path=()):
    require(type(v) is dict,'TYPE_DOMAIN',path)
    require(len(v)==len(names),'SCHEMA_KEYS',path)
    require(all(type(k) is str for k in v),'TYPE_DOMAIN',path)
    require(set(v)==set(names),'SCHEMA_KEYS',path)
def enum_id(group,value,path=()):
    require(type(value) is str,'TYPE_DOMAIN',path)
    require(value in ENUMS[group],'ENUM_DOMAIN',path)
    return ENUMS[group][value]
def enum_name(group,value,offset=None):
    for name,number in ENUMS[group].items():
        if number==value:return name
    raise FormatError('ENUM_DOMAIN',offset)
def flags_bits(group,value,path=()):
    table=ENUMS[group];keys(value,table,path)
    require(all(type(v) is bool for v in value.values()),'TYPE_DOMAIN',path)
    return sum((1<<table[k]) for k,v in value.items() if v)
def flags_value(group,bits,offset=None,extra_mask=0):
    mask=sum(1<<n for n in ENUMS[group].values())|extra_mask
    require(bits&~mask==0,'RESERVED_NONZERO',offset=offset)
    return {k:bool(bits&(1<<n))for k,n in ENUMS[group].items()}
def _capture(value,depth=0,budget=None):
    if budget is None:budget=[0]
    budget[0]+=1;require(depth<=20 and budget[0]<=3000000,'SIZE_CAP')
    t=type(value)
    if value is None or t is bool or t is int or t is float:return value
    if t is str:require(len(value)<=65536,'SIZE_CAP');return value
    if t is bytes:require(len(value)<=MAX_BYTES,'SIZE_CAP');return value
    if t is dict:
        require(len(value)<=128,'SIZE_CAP')
        require(all(type(k) is str for k in value),'TYPE_DOMAIN')
        return {k:_capture(v,depth+1,budget)for k,v in value.items()}
    if t is list or t is tuple:
        require(len(value)<=65536,'SIZE_CAP')
        items=[_capture(v,depth+1,budget)for v in value]
        return tuple(items) if t is tuple else items
    raise FormatError('TYPE_DOMAIN')
class _FrozenList(tuple):pass
def _freeze(v):
    if type(v) is dict:return MappingProxyType({k:_freeze(x)for k,x in v.items()})
    if type(v) is list:return _FrozenList(_freeze(x)for x in v)
    if type(v) is tuple:return tuple(_freeze(x)for x in v)
    return v
def _thaw(v):
    if type(v) is MappingProxyType:return {k:_thaw(x)for k,x in v.items()}
    if type(v) is _FrozenList:return [_thaw(x)for x in v]
    if type(v) is tuple:return tuple(_thaw(x)for x in v)
    return v
class DecodedLedger:
    __slots__=('_data','_raw')
    def __init__(self,value,raw):object.__setattr__(self,'_data',_freeze(value));object.__setattr__(self,'_raw',raw)
    def __setattr__(self,k,v):raise TypeError('immutable decoded data')
    def to_dict(self):return _thaw(self._data)
    def to_bytes(self):return self._raw

def clock_bits(atom,path=()):
    keys(atom,('tag','value'),path);tag=atom['tag'];v=atom['value']
    require(type(tag) is str and tag in ENUMS['clock'],'CLOCK_DOMAIN',path)
    if tag=='UNOBSERVED':require(v is None,'CLOCK_DOMAIN',path);return 0,0
    if tag=='I64':
        require(type(v) is int and -(1<<63)<=v<(1<<63),'CLOCK_DOMAIN',path)
        return 1,v&INVALID
    require(type(v) is float and math.isfinite(v),'CLOCK_DOMAIN',path)
    return 2,struct.unpack('<Q',struct.pack('<d',v))[0]
def clock_atom(tag,bits,offset=None):
    require(tag in (0,1,2),'CLOCK_DOMAIN',offset=offset)
    if tag==0:require(bits==0,'RESERVED_NONZERO',offset=offset);return dict(tag='UNOBSERVED',value=None)
    if tag==1:return dict(tag='I64',value=bits if bits<(1<<63)else bits-(1<<64))
    v=struct.unpack('<d',struct.pack('<Q',bits))[0]
    require(math.isfinite(v),'CLOCK_DOMAIN',offset=offset)
    return dict(tag='F64',value=v)
def atom_bits(atom,expected,path=(),input_handle=False):
    keys(atom,('tag','value'),path);tag,v=atom['tag'],atom['value']
    require(type(tag) is str,'TYPE_DOMAIN',path)
    if tag=='UNOBSERVED':require(v is None,'ATOM_DOMAIN',path);return 0,False,False
    if tag=='NULL':require(not input_handle and v is None,'ATOM_DOMAIN',path);return 0,True,True
    require(tag==expected,'ATOM_DOMAIN',path)
    if tag=='BOOL':integer(v,(1<<31)-1,path,-(1<<31));return v&0xffffffff,True,False
    integer(v,INVALID if tag=='HANDLE'else 0xffffffff,path)
    return v,True,False
def atom_value(bits,expected,observed,null=False,offset=None):
    if not observed:require(bits==0 and not null,'RESERVED_NONZERO',offset=offset);return dict(tag='UNOBSERVED',value=None)
    if null:require(bits==0,'ATOM_DOMAIN',offset=offset);return dict(tag='NULL',value=None)
    if expected!='HANDLE':require(bits>>32==0,'ATOM_DOMAIN',offset=offset)
    value=bits-(1<<32) if expected=='BOOL' and bits&(1<<31)else bits
    return dict(tag=expected,value=value)
def _api(name,path=()):
    require(type(name) is str,'TYPE_DOMAIN',path)
    for item in APIS:
        if item['name']==name:return item
    raise FormatError('ENUM_DOMAIN',path=path)
def _atomtag(api):return 'HANDLE' if api['scalar']=='HANDLE'else 'DWORD'if api['scalar']=='DWORD'else'BOOL'
def _probe(api,scalar):
    return scalar['tag']==('HANDLE' if api['scalar']=='HANDLE'else 'DWORD'if api['scalar']=='DWORD'else'BOOL') and scalar['value']==(INVALID if api['scalar']=='HANDLE'else 0)
def _optional(v,cap,path=()):
    if v is not None:
        require(type(v)is int,'TYPE_DOMAIN',path);require(0<=v<=cap,'REFERENCE_DOMAIN',path)
def path_key(path):
    require(type(path) is str and len(path)>=4 and path[0]in'CcDd' and path[1]==':'and path[2]in'/\\','PATH_DOMAIN')
    try:raw=path.encode('utf-16-le','strict')
    except UnicodeError:raise FormatError('PATH_DOMAIN')from None
    require(len(raw)//2<=4096,'PATH_DOMAIN')
    result=path.replace('/','\\')
    for part in result[3:].split('\\'):
        require(part not in('','.','..')and not part.endswith((' ','.'))and not any(ord(c)<32 or ord(c)==127 or c in '<>:"|?*~'for c in part),'PATH_DOMAIN')
        require(part.split('.',1)[0].lower()not in{'con','prn','aux','nul',*[f'com{i}'for i in range(1,10)],*[f'lpt{i}'for i in range(1,10)]},'PATH_DOMAIN')
    return result.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'))
def _row_keys(layout):return tuple(n for n,_,_,t in LAYOUTS[layout]if not t.startswith('zero')and not n.startswith('reserved_zero'))
def _check_widths(row,layout):
    for name,_,size,kind in LAYOUTS[layout]:
        if name not in row or kind=='zero_bytes'or name.startswith('reserved_zero'):continue
        value=row[name]
        if type(value)is str or type(value)is dict or type(value)is bytes:continue
        if value is None:
            require(kind.startswith('optional')or kind=='digest32'or name in('expected_size','buffer_id'),'TYPE_DOMAIN');continue
        if kind in('u8','u16','u32','u64')or kind.startswith('optional'):integer(value,(1<<(size*8))-1)
FILE_KEYS=_row_keys('file_record')
MODULE_KEYS=_row_keys('module_record')
DIAG_KEYS=tuple('clock_atom'if n=='clock_bits'else n for n in _row_keys('diagnostic_record')if n!='clock_tag')

def validate_value(v,check):
    keys(v,TOP_KEYS);h=v['header'];keys(h,HEADER_KEYS,('header',))
    profile=enum_id('profile',h['profile']);enum_id('phase',h['phase']);enum_id('status',h['status'])
    flags_bits('header_flags_bits',h['flags'])
    for k in('origin_data_id','ledger_sequence','reserved_R','reserved_C','reserved_E','early_count','read_chunk'):integer(h[k],path=('header',k))
    for k in('start_clock','latest_clock','freeze_clock'):clock_bits(h[k],('header',k))
    start=h['start_clock']['value'];latest=h['latest_clock']['value'];end=h['freeze_clock']['value']
    if start is not None:
        for reserve in(295,300):
            later=start+reserve
            require(type(later)is type(start)and (type(later)is int and -(1<<63)<=later<(1<<63)or type(later)is float and math.isfinite(later))and later>start,'CLOCK_DOMAIN')
    require(latest is None or start is None or latest>=start,'CLOCK_DOMAIN')
    require(end is None or latest is None or end>=latest,'CLOCK_DOMAIN')
    require(h['previous_ledger_sha256']is None or type(h['previous_ledger_sha256'])is bytes and len(h['previous_ledger_sha256'])==32,'TYPE_DOMAIN')
    require(h['flags']['PREVIOUS_LEDGER_PRESENT']==(h['previous_ledger_sha256']is not None),'STATE_CONTRADICTION')
    for k,cap in(('files',256),('calls',16384),('modules',128),('diagnostics',5056)):
        require(type(v[k])is list,'TYPE_DOMAIN',(k,));require(len(v[k])<=cap,'SIZE_CAP',(k,))
    for k,cap in(('queries',8218*256),('paths',3*4100*256),('module_names',512*128)):
        require(type(v[k])is bytes,'TYPE_DOMAIN',(k,));require(len(v[k])<=cap,'SIZE_CAP',(k,))
    require(type(v['module_edges'])is tuple,'TYPE_DOMAIN',('module_edges',));require(len(v['module_edges'])<=128*128,'SIZE_CAP')
    fs,cs,ms,ds=v['files'],v['calls'],v['modules'],v['diagnostics'];N=len(fs);require(N>0,'SIZE_CAP')
    if profile==0:
        require(N==1 and len(cs)==1 and not ms and not ds and h['phase']=='FRAGMENT'and h['status']=='INCOMPLETE','STATE_CONTRADICTION')
        require(h['reserved_R']==h['reserved_C']==h['reserved_E']==h['early_count']==h['read_chunk']==h['ledger_sequence']==0,'RESERVED_NONZERO')
    else:
        require(N<= (4 if profile==1 else 256)and len(ms)<=(2 if profile==1 else 128)and h['early_count']<=(2 if profile==1 else 128),'SIZE_CAP')
        require(h['read_chunk']==(65536 if profile==1 else 1048576),'STATE_CONTRADICTION')
        require(h['phase']in('CANDIDATE','TERMINAL')and h['ledger_sequence']==(1 if h['phase']=='CANDIDATE'else 2),'STATE_CONTRADICTION')
        require(h['phase']!='CANDIDATE'or h['previous_ledger_sha256']is None,'STATE_CONTRADICTION')
        require(len(v['queries'])==8218*N,'QUERY_SPAN')
    check();path_end=0;seen=set();descriptor_ids=[];captured=0
    for i,f in enumerate(fs):
        keys(f,FILE_KEYS,('files',i));_check_widths(f,'file_record');require(f['ordinal']==i and f['path_id']==i,'REFERENCE_DOMAIN')
        for field,group in(('role','role'),('capture_state','capture'),('target_class','target'),('open_state','open'),('identity_state','identity'),('close_state','close')):enum_id(group,f[field])
        flags_bits('file_flags_bits',f['flags']);ff=f['flags']
        for k in('descriptor_id','path_offset','path_bytes','path_utf16_units','known_read_bytes','hashed_bytes','captured_bytes','query_offset','query_length','read_reservations','read_invocations','captured_blob_length','read_generation'):integer(f[k],path=('files',i,k))
        for k in('open_ordinal','close_ordinal'):_optional(f[k],len(cs)-1)
        _optional(f['first_diagnostic'],len(ds)-1);_optional(f['module_ordinal'],len(ms)-1);_optional(f['early_ordinal'],N-1)
        for k,flag in(('expected_sha256','EXPECTED_DIGEST_PRESENT'),('actual_sha256','ACTUAL_DIGEST_PRESENT')):
            require((f[k]is not None)==ff[flag],'STATE_CONTRADICTION')
            require(f[k]is None or type(f[k])is bytes and len(f[k])==32,'TYPE_DOMAIN')
        require((f['expected_size']is not None)==ff['EXPECTED_SIZE_PRESENT'],'STATE_CONTRADICTION')
        if f['expected_size']is not None:integer(f['expected_size'],(1<<63)-1)
        require(f['path_offset']==path_end and 0<f['path_bytes']<=3*4100 and path_end+f['path_bytes']<=len(v['paths']),'PATH_DOMAIN')
        raw=v['paths'][path_end:path_end+f['path_bytes']];path_end+=len(raw)
        try:path=raw.decode('utf-8','strict');units=len(path.encode('utf-16-le','strict'))//2
        except UnicodeError:raise FormatError('PATH_DOMAIN')from None
        require('\0'not in path and units==f['path_utf16_units'],'PATH_DOMAIN')
        if profile:
            key=path_key(path);require(key not in seen,'PATH_DOMAIN');seen.add(key)
            require(f['target_class']=='ORIGINAL'and f['role']!='NONE_FRAGMENT_ONLY'and ff['EXPECTED_SIZE_PRESENT']and ff['EXPECTED_DIGEST_PRESENT'],'ROLE_CAPTURE')
            require(f['query_offset']==8218*i and f['query_length']==8218,'QUERY_SPAN')
        else:require(f['expected_size']is None and f['expected_sha256']is None and f['role']=='NONE_FRAGMENT_ONLY','STATE_CONTRADICTION')
        descriptor_ids.append(f['descriptor_id']);requested=f['role']in('CAPTURED_SOFTWARE','CAPTURED_METADATA')
        require(ff['CAPTURE_REQUESTED']==requested,'ROLE_CAPTURE')
        if not requested:require(f['capture_state']=='NOT_REQUESTED'and not ff['CAPTURE_COMPLETE']and not ff['BLOB_ISSUED']and not ff['COPY_UNKNOWN']and f['captured_bytes']==f['captured_blob_length']==0,'ROLE_CAPTURE')
        else:
            require(f['capture_state']!='NOT_REQUESTED','ROLE_CAPTURE');captured+=f['expected_size']or 0
            require((f['capture_state']=='COMPLETE')==ff['CAPTURE_COMPLETE'],'ROLE_CAPTURE')
            if ff['CAPTURE_COMPLETE']:require(ff['HASH_COMPLETE']and ff['BLOB_ISSUED']and f['captured_bytes']==f['captured_blob_length']==f['expected_size']and f['actual_sha256']==f['expected_sha256'],'ROLE_CAPTURE')
            require(not profile or f['expected_size']<=(4096 if profile==1 else 8388608),'SIZE_CAP')
        if f['expected_size']is not None:require(f['known_read_bytes']<=f['expected_size']and f['hashed_bytes']<=f['known_read_bytes']and f['captured_bytes']<=f['known_read_bytes'],'STATE_CONTRADICTION')
    require(path_end==len(v['paths'])and sorted(descriptor_ids)==list(range(N)),'PATH_DOMAIN')
    if profile:
        R=sum(n['expected_size']//h['read_chunk']+int(n['expected_size']%h['read_chunk']!=0)+16 for n in fs if n['expected_size'])
        require(h['reserved_R']==R and h['reserved_C']==6*N+R and h['reserved_E']==6*N+2*h['early_count']+2*len(ms)+192,'STATE_CONTRADICTION')
        require(h['reserved_C']<=(92 if profile==1 else 16384)and h['reserved_E']<=(224 if profile==1 else 2240)and captured<=(16384 if profile==1 else 33554432)and len(cs)<=h['reserved_C'],'SIZE_CAP')
    groups=[dict(known=0,hashed=0,copied=0,reads=0,reserved=0,unknown=False)for _ in fs]
    for i,c in enumerate(cs):
        keys(c,CALL_KEYS,('calls',i));_check_widths(c,'call_record');require(c['ordinal']==i and c['record_version']==1,'REFERENCE_DOMAIN');integer(c['file_id'],N-1);f=fs[c['file_id']];cf=c['flags']
        api=_api(c['api']);require(not profile or api['id']<=7,'ENUM_DOMAIN')
        flags_bits('call_flags_bits',cf);enum_id('phase_code',c['phase']);enum_id('fold',c['fold_state']);enum_id('buffer',c['buffer_state'])
        for k in('requested','generation','buffer_written','hashed_contribution','captured_contribution','known_count_contribution','query_offset','query_length','path_id'):integer(c[k],path=('calls',i,k))
        require(c['path_id']==c['file_id'],'REFERENCE_DOMAIN');_optional(c['buffer_id'],65534);_optional(c['error_id'],len(ds)-1,('calls',i,'error_id'))
        _,so,snull=atom_bits(c['scalar_atom'],_atomtag(api));_,co,_=atom_bits(c['count_atom'],'COUNT32');_,eo,_=atom_bits(c['error_atom'],'DWORD');_,hi,_=atom_bits(c['input_handle_atom'],'HANDLE',input_handle=True)
        require(cf['SCALAR_OBSERVED']==so and cf['SCALAR_NULL']==snull and cf['COUNT_OBSERVED']==co and cf['ERROR_OBSERVED']==eo and cf['INPUT_HANDLE_PRESENT']==hi,'STATE_CONTRADICTION')
        valid_scalar=so and(not snull or api['scalar']=='HANDLE')
        require(cf['SCALAR_DOMAIN_VALID']==valid_scalar and cf['COUNT_DOMAIN_VALID']==co and cf['ERROR_DOMAIN_VALID']==eo,'STATE_CONTRADICTION')
        require(cf['MALFORMED_RAW']==(so and not valid_scalar),'STATE_CONTRADICTION')
        if cf['MALFORMED_RAW']:require(cf['STOPPED']and h['status']=='INCOMPLETE','STATE_CONTRADICTION')
        if c['fold_state']in('FAILED_BEFORE_COMMIT','FAILED_AFTER_COMMIT'):require(cf['ACCOUNTING_FAULT']and cf['STOPPED'],'STATE_CONTRADICTION')
        require(api['count_applicable']or not co,'ATOM_DOMAIN')
        da=c['error_definition_atom'];keys(da,('tag','value'))
        if da['tag']=='UNOBSERVED':require(da['value']is None,'ATOM_DOMAIN');de=False;dv=False
        else:require(da['tag']=='DEFINEDNESS'and type(da['value'])is bool,'ATOM_DOMAIN');de=True;dv=da['value']
        require(cf['ERROR_DEFINITION_OBSERVED']==de and cf['ERROR_DEFINED']==dv,'STATE_CONTRADICTION')
        if dv:require(cf['INVOKED']and valid_scalar and _probe(api,c['scalar_atom']),'STATE_CONTRADICTION')
        for field,prefix in(('pre_dispatch_clock','PRE'),('post_binding_clock','POST')):
            tag,_=clock_bits(c[field]);require(cf[prefix+'_CLOCK_RETURN_OBSERVED']==(tag!=0)and(not tag or cf[prefix+'_CLOCK_ATTEMPTED']),'STATE_CONTRADICTION')
        pre=c['pre_dispatch_clock']['value'];post=c['post_binding_clock']['value']
        require(pre is None or post is None or post>=pre,'CLOCK_DOMAIN')
        require(not cf['POST_CLOCK_ATTEMPTED']or cf['WRAPPER_RETURNED'],'STATE_CONTRADICTION')
        require(cf['INVOKED']or not(so or co or eo or cf['WRAPPER_RETURNED']),'STATE_CONTRADICTION')
        require(not cf['SCALAR_AUX_ACK']or so,'STATE_CONTRADICTION');require(not cf['COUNT_AUX_ACK']or co,'STATE_CONTRADICTION')
        require(cf['CAPTURE_REQUESTED']==f['flags']['CAPTURE_REQUESTED'],'ROLE_CAPTURE')
        require(cf['BUFFER_PRESENT']==(c['buffer_id']is not None),'STATE_CONTRADICTION')
        if not cf['BUFFER_PRESENT']:require(c['generation']==c['buffer_written']==0,'STATE_CONTRADICTION')
        if not cf['REQUESTED_PRESENT']:require(c['requested']==0,'STATE_CONTRADICTION')
        require(cf['REQUESTED_PRESENT']==api['count_applicable'],'STATE_CONTRADICTION')
        defined=bool(api['count_applicable']and so and not snull and c['scalar_atom']['value']!=0 and co and c['count_atom']['value']<=c['requested'])
        require(cf['COUNT_DEFINED']==defined,'STATE_CONTRADICTION')
        frame=api['query_frame_bytes']
        if frame:
            off=(8218*c['file_id']+{'GetFileInformationByHandleEx':0,'GetFinalPathNameByHandleW':8,'GetFileSizeEx':8210}[api['name']])if profile else 0
            require(c['query_offset']==off and c['query_length']==frame and off+frame<=len(v['queries'])and cf['QUERY_SPAN_PRESENT'],'QUERY_SPAN')
        else:require(c['query_length']==c['query_offset']==0 and not cf['QUERY_SPAN_PRESENT'],'QUERY_SPAN')
        if cf['QUERY_CAPTURE_OBSERVED']:require(frame>0 and cf['BUFFER_DATA_OBSERVED']and c['buffer_written']==frame,'QUERY_SPAN')
        if cf['QUERY_DEFINED']:require(cf['QUERY_CAPTURE_OBSERVED']and so and not snull and c['scalar_atom']['value']not in(0,INVALID),'STATE_CONTRADICTION')
        if not cf['BUFFER_DATA_OBSERVED']:require(c['buffer_written']==0,'STATE_CONTRADICTION')
        require(not cf['HASH_RETURN_OBSERVED']or cf['HASH_ATTEMPTED'],'STATE_CONTRADICTION');require(not cf['COPY_RETURN_OBSERVED']or cf['COPY_ATTEMPTED'],'STATE_CONTRADICTION')
        if cf['HASH_RETURN_OBSERVED']or cf['COPY_RETURN_OBSERVED']:
            require(defined and cf['BUFFER_DATA_OBSERVED']and c['buffer_written']>=c['count_atom']['value'],'STATE_CONTRADICTION')
        require(not cf['RIGHT_TRANSFER_ACK']or api['id']in(1,9)and so and c['scalar_atom']['value']not in(None,0,INVALID),'STATE_CONTRADICTION')
        if api['id']==6:
            g=groups[c['file_id']];g['reserved']+=1;g['reads']+=int(cf['INVOKED']);g['unknown']|=cf['INVOKED']and not defined
            contribution=c['count_atom']['value']if defined else 0;require(c['known_count_contribution']==contribution,'STATE_CONTRADICTION');g['known']+=contribution
            for bit,name,groupname in(('HASH_RETURN_OBSERVED','hashed_contribution','hashed'),('COPY_RETURN_OBSERVED','captured_contribution','copied')):
                require(c[name]==(contribution if cf[bit]else 0),'STATE_CONTRADICTION');g[groupname]+=c[name]
            if cf['COPY_ATTEMPTED']:require(f['flags']['CAPTURE_REQUESTED'],'ROLE_CAPTURE')
        else:require(c['known_count_contribution']==c['hashed_contribution']==c['captured_contribution']==0,'STATE_CONTRADICTION')
        if profile:require(api['target']=='ORIGINAL','STATE_CONTRADICTION')
        else:require(f['target_class']==api['target']and len(v['queries'])==frame,'QUERY_SPAN')
        check()
    if profile:
        for f,g in zip(fs,groups):
            require((f['known_read_bytes'],f['hashed_bytes'],f['captured_bytes'],f['read_invocations'],f['read_reservations'])==(g['known'],g['hashed'],g['copied'],g['reads'],g['reserved']),'STATE_CONTRADICTION')
            require(f['flags']['READ_UNKNOWN']==g['unknown'],'STATE_CONTRADICTION')
    for f in fs:
        close=f['close_ordinal'];known=False;success=False
        if close is not None:
            c=cs[close];require(c['file_id']==f['ordinal']and c['api']in('CloseHandle','FindClose'),'REFERENCE_DOMAIN')
            known=c['flags']['INVOKED']and c['scalar_atom']['tag']=='BOOL';success=known and c['scalar_atom']['value']!=0
        require(f['flags']['CLOSE_SUCCESS_KNOWN']==known and f['flags']['CLOSE_SUCCESS_TRUE']==bool(success),'STATE_CONTRADICTION')
        if known:require(f['close_state']==('RETURNED_SUCCESS'if success else'RETURNED_FAILURE'),'STATE_CONTRADICTION')
        if f['identity_state']=='VERIFIED':
            related=[c for c in cs if c['file_id']==f['ordinal']and c['api']in('GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx')]
            require(len(related)==4 and tuple(c['api']for c in related)==('GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx'),'STATE_CONTRADICTION')
            require(all(c['flags']['SCALAR_OBSERVED']and c['flags']['SCALAR_DOMAIN_VALID']for c in related)and related[0]['scalar_atom']['value']==1,'STATE_CONTRADICTION')
            require(all(c['flags']['QUERY_DEFINED']for c in related[1:]),'STATE_CONTRADICTION')
            frame=f['query_offset'];attrs,_=struct.unpack_from('<II',v['queries'],frame);size=struct.unpack_from('<q',v['queries'],frame+8210)[0]
            require(not attrs&(16|1024)and size==f['expected_size'],'STATE_CONTRADICTION')
            length=related[2]['scalar_atom']['value'];require(0<length<=4100,'PATH_DOMAIN')
            pathraw=v['queries'][frame+8:frame+8+8202];require(pathraw[length*2:length*2+2]==b'\0\0','PATH_DOMAIN')
            try:finalpath=pathraw[:length*2].decode('utf-16-le','strict');original=v['paths'][f['path_offset']:f['path_offset']+f['path_bytes']].decode('utf-8')
            except UnicodeError:raise FormatError('PATH_DOMAIN')from None
            if finalpath.startswith('\\\\?\\'):finalpath=finalpath[4:]
            require(path_key(finalpath)==path_key(original),'PATH_DOMAIN')
    name_end=edge_end=0;names=[];graph=[]
    for i,m in enumerate(ms):
        keys(m,MODULE_KEYS);_check_widths(m,'module_record');require(m['ordinal']==i,'REFERENCE_DOMAIN');integer(m['file_ordinal'],N-1);require(fs[m['file_ordinal']]['role']=='CAPTURED_SOFTWARE','MODULE_GRAPH')
        flags_bits('module_flags',m['flags']);require(not m['flags']['CACHED']or m['flags']['ACCEPTED'],'MODULE_GRAPH');require(not m['flags']['ACCEPTED']or m['flags']['RETURN_OBSERVED'],'MODULE_GRAPH')
        require(m['name_offset']==name_end and 0<m['name_length']<=512 and name_end+m['name_length']<=len(v['module_names']),'MODULE_GRAPH')
        raw=v['module_names'][name_end:name_end+m['name_length']];name_end+=len(raw)
        try:name=raw.decode('ascii')
        except UnicodeError:raise FormatError('MODULE_GRAPH')from None
        require(re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*',name,re.ASCII)is not None and name not in names,'MODULE_GRAPH');names.append(name)
        require(m['edge_offset']==edge_end and m['dependency_count']<=len(ms)and edge_end+m['dependency_count']<=len(v['module_edges']),'MODULE_GRAPH')
        deps=v['module_edges'][edge_end:edge_end+m['dependency_count']];edge_end+=len(deps)
        require(all(type(x)is int and 0<=x<len(ms)and x!=i for x in deps)and len(set(deps))==len(deps),'MODULE_GRAPH');graph.append(deps)
        _optional(m['first_diagnostic'],len(ds)-1)
        for k in('attempt_order','return_order'):_optional(m[k],len(ms)-1)
        integer(m['cache_hit_count'],len(ms))
    require(name_end==len(v['module_names'])and edge_end==len(v['module_edges']),'MODULE_GRAPH')
    done=set()
    def visit(i,trail):
        require(i not in trail,'MODULE_GRAPH')
        if i in done:return
        for j in graph[i]:visit(j,trail+(i,))
        done.add(i)
    for i in range(len(ms)):visit(i,())
    for i,x in enumerate(ds):
        keys(x,DIAG_KEYS);_check_widths(x,'diagnostic_record');require(x['ordinal']==i and x['opaque_identity_id']==i+1,'DIAGNOSTIC_LAYOUT');enum_id('diagnostic_state',x['state']);enum_id('phase_code',x['phase']);enum_id('severity',x['severity']);flags_bits('diagnostic_flags_bits',x['flags'])
        _optional(x['call_ordinal'],len(cs)-1);_optional(x['secondary_of'],i-1);clock_bits(x['clock_atom'])
        for k,limit in(('class',96),('message',512),('args',256)):
            raw=x[k+'_utf8'];require(type(raw)is bytes and len(raw)==x[k+'_bytes']and len(raw)<=limit,'DIAGNOSTIC_LAYOUT')
            try:raw.decode('utf-8','strict')
            except UnicodeError:raise FormatError('DIAGNOSTIC_LAYOUT')from None
        try:args=json.loads(x['args_utf8'])
        except (UnicodeError,ValueError):raise FormatError('DIAGNOSTIC_LAYOUT')from None
        require(type(args)is list and len(args)<=8 and all(type(a)is str for a in args),'DIAGNOSTIC_LAYOUT')
        require((json.dumps(args,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)).encode()==x['args_utf8'],'DIAGNOSTIC_LAYOUT')
    return v

_FMT={1:'B',2:'H',4:'I',8:'Q'}
def _put(dst,offset,size,value):
    if type(value)is bytes:require(len(value)==size,'INTEGER_DOMAIN');dst[offset:offset+size]=value
    else:integer(value,(1<<(8*size))-1);struct.pack_into('<'+_FMT[size],dst,offset,value)
def _layout_write(dst,base,layout,values):
    for name,off,size,kind in LAYOUTS[layout]:
        if kind=='zero_bytes'or name.startswith('reserved_zero')or name=='section_descriptors':continue
        value=values[name]
        if value is None:value=(1<<(8*size))-1 if kind.startswith('optional')else bytes(size)if kind=='digest32'else 0
        _put(dst,base+off,size,value)
def _layout_read(raw,base,layout):
    out={}
    for name,off,size,kind in LAYOUTS[layout]:
        require(base+off+size<=len(raw),'SECTION_LAYOUT',offset=min(len(raw),base+off))
        if kind=='zero_bytes'or name.startswith('reserved_zero'):
            require(not any(raw[base+off:base+off+size]),'RESERVED_NONZERO',offset=base+off);continue
        if name=='section_descriptors':continue
        value=raw[base+off:base+off+size]if size not in _FMT or kind in('digest32','ascii8')else struct.unpack_from('<'+_FMT[size],raw,base+off)[0]
        if kind.startswith('optional')and value==(1<<(size*8))-1:value=None
        if kind.endswith('must_be_zero'):require(value==0,'RESERVED_NONZERO',offset=base+off)
        out[name]=value
    return out
def _pack_file(dst,offset,row):
    q=dict(row)
    for field,group in(('role','role'),('capture_state','capture'),('target_class','target'),('open_state','open'),('identity_state','identity'),('close_state','close')):q[field]=enum_id(group,q[field])
    q['flags']=flags_bits('file_flags_bits',q['flags']);_layout_write(dst,offset,'file_record',q)
def _pack_call(dst,offset,row):
    q=dict(row);api=_api(q.pop('api'));q['api']=api['id'];q['fact_flags']=flags_bits('call_flags_bits',q.pop('flags'))
    for field,expected,target in(('scalar_atom',_atomtag(api),'raw_scalar_bits'),('count_atom','COUNT32','raw_count'),('error_atom','DWORD','raw_error'),('input_handle_atom','HANDLE','input_handle_bits')):q[target]=atom_bits(q.pop(field),expected,input_handle=field=='input_handle_atom')[0]
    q.pop('error_definition_atom')
    for field,target,shift in(('pre_dispatch_clock','pre_dispatch_clock_bits',32),('post_binding_clock','post_binding_clock_bits',34)):
        tag,bits=clock_bits(q.pop(field));q[target]=bits;q['fact_flags']|=tag<<shift
    q['buffer_id']=65535 if q['buffer_id']is None else q['buffer_id']
    for field,group in(('phase','phase_code'),('fold_state','fold'),('buffer_state','buffer')):q[field]=enum_id(group,q[field])
    _layout_write(dst,offset,'call_record',q)
def _pack_module(dst,offset,row):
    q=dict(row);q['flags']=flags_bits('module_flags',q['flags']);_layout_write(dst,offset,'module_record',q)
def _pack_diag(dst,offset,row):
    q=dict(row);q['flags']=flags_bits('diagnostic_flags_bits',q['flags'])
    for k,g in(('state','diagnostic_state'),('phase','phase_code'),('severity','severity')):q[k]=enum_id(g,q[k])
    q['clock_tag'],q['clock_bits']=clock_bits(q.pop('clock_atom'))
    for k,size in(('class_utf8',96),('message_utf8',512),('args_utf8',256)):q[k]=q[k]+bytes(size-len(q[k]))
    _layout_write(dst,offset,'diagnostic_record',q)
ROW_WRITERS=(_pack_file,_pack_call,None,None,_pack_module,None,None,_pack_diag)
class ByteChunks:
    """Private construction stream, never an issued-byte/checker capability."""
    __slots__=('length','factory')
    def __init__(self,length,factory):integer(length,MAX_BYTES);require(callable(factory),'TYPE_DOMAIN');self.length=length;self.factory=factory
    def __len__(self):return self.length
def pack_row_tuple_into(dst,offset,kind,fields):
    """Operational helper: one checked row, never a whole call dictionary list."""
    names={'files':FILE_KEYS,'calls':CALL_KEYS,'modules':MODULE_KEYS,'diagnostics':DIAG_KEYS}[kind]
    require(type(fields)is tuple and len(fields)==len(names),'SCHEMA_KEYS')
    ROW_WRITERS[SECTIONS.index(kind)](dst,offset,dict(zip(names,fields)))
def build_ledger(header,files,calls,queries,paths,modules,module_names,module_edges,diagnostics,check,capture_header=None):
    """Internal source consumer may supply sized reiterable row streams."""
    values=(files,calls,queries,paths,modules,module_names,module_edges,diagnostics)
    sizes=(len(files)*256,len(calls)*256,len(queries),len(paths),len(modules)*64,len(module_names),len(module_edges)*2,len(diagnostics)*1024)
    require(4096+sum(sizes)<=MAX_BYTES,'SIZE_CAP');out=bytearray(4096+sum(sizes));offset=4096;descs=[]
    for i,(name,items,size,width)in enumerate(zip(SECTIONS,values,sizes,WIDTHS)):
        if ROW_WRITERS[i]:
            for j,row in enumerate(items):
                if type(row)is tuple:pack_row_tuple_into(out,offset+j*width,name,row)
                else:ROW_WRITERS[i](out,offset+j*width,row)
                check()
        elif name=='module_edges':
            for j,item in enumerate(items):_put(out,offset+2*j,2,item)
        elif type(items)is ByteChunks:
            at=offset
            for chunk in items.factory():
                require(type(chunk)is bytes and at+len(chunk)<=offset+size,'SECTION_LAYOUT')
                out[at:at+len(chunk)]=chunk;at+=len(chunk);check()
            require(at==offset+size,'SECTION_LAYOUT')
        else:out[offset:offset+size]=items
        check();digest=hashlib.sha256(memoryview(out)[offset:offset+size]).digest()
        descs.append(dict(id=i+1,record_size=width,count=size//width,offset=offset,length=size,sha256=digest,flags=0));offset+=size
    h=dict(header() if callable(header) else header);ctags=[]
    for field in('start_clock','latest_clock','freeze_clock'):
        tag,bits=clock_bits(h.pop(field));h[field+'_bits']=bits;ctags.append(tag)
    h.update(magic=b'RAPLEDG1',format_version=1,value_schema_version=2,profile=enum_id('profile',h['profile']),phase=enum_id('phase',h['phase']),status=enum_id('status',h['status']),header_bytes=4096,section_count=8,file_count=len(files),call_count=len(calls),module_count=len(modules),diagnostic_count=len(diagnostics),edge_count=len(module_edges),total_bytes=len(out),captured_input_bytes=sum(row[FILE_KEYS.index('captured_blob_length')]if type(row)is tuple else row['captured_blob_length']for row in files),known_read_bytes=sum(row[FILE_KEYS.index('known_read_bytes')]if type(row)is tuple else row['known_read_bytes']for row in files),hashed_bytes=sum(row[FILE_KEYS.index('hashed_bytes')]if type(row)is tuple else row['hashed_bytes']for row in files),copied_bytes=sum(row[FILE_KEYS.index('captured_bytes')]if type(row)is tuple else row['captured_bytes']for row in files),module_count_repeat=len(modules),qualification_bits=0,path_policy=1,clock_tags=sum(t<<(2*i)for i,t in enumerate(ctags)))
    h['flags']=flags_bits('header_flags_bits',h['flags'])
    if capture_header is not None:
        frozen=[]
        for name,_,size,kind in LAYOUTS['header']:
            if kind=='zero_bytes'or name=='section_descriptors':continue
            value=h[name]
            if value is None:value=bytes(size)if kind=='digest32'else 0
            frozen.append((name,value))
        capture_header(tuple(frozen))
    _layout_write(out,0,'header',h)
    for i,desc in enumerate(descs):_layout_write(out,256+i*64,'section_descriptor',desc)
    result=bytes(out);check();return result
def encode_ledger(value,*,check):
    require(callable(check),'TYPE_DOMAIN');check();v=_capture(value);check();validate_value(v,check)
    return build_ledger(v['header'],*(v[k]for k in SECTIONS),check)

def _unpack_file(raw,offset):
    q=_layout_read(raw,offset,'file_record');q['flags']=flags_value('file_flags_bits',q['flags'],offset+8)
    for k,g in(('role','role'),('capture_state','capture'),('target_class','target'),('open_state','open'),('identity_state','identity'),('close_state','close')):q[k]=enum_name(g,q[k],offset)
    for k,flag in(('expected_sha256','EXPECTED_DIGEST_PRESENT'),('actual_sha256','ACTUAL_DIGEST_PRESENT')):
        if not q['flags'][flag]:require(q[k]==ZERO32,'RESERVED_NONZERO',offset=offset);q[k]=None
    if not q['flags']['EXPECTED_SIZE_PRESENT']:require(q['expected_size']==0,'RESERVED_NONZERO',offset=offset+32);q['expected_size']=None
    return q
def _unpack_call(raw,offset):
    q=_layout_read(raw,offset,'call_record');number=q['api'];require(1<=number<=14,'ENUM_DOMAIN',offset=offset+6);api=APIS[number-1];q['api']=api['name'];bits=q.pop('fact_flags');q['flags']=flags_value('call_flags_bits',bits,offset+8,15<<32);f=q['flags']
    for target,source,expected,obs,null in(('scalar_atom','raw_scalar_bits',_atomtag(api),f['SCALAR_OBSERVED'],f['SCALAR_NULL']),('count_atom','raw_count','COUNT32',f['COUNT_OBSERVED'],False),('error_atom','raw_error','DWORD',f['ERROR_OBSERVED'],False),('input_handle_atom','input_handle_bits','HANDLE',f['INPUT_HANDLE_PRESENT'],False)):
        q[target]=atom_value(q.pop(source),expected,obs,null,offset)
    q['error_definition_atom']=dict(tag='DEFINEDNESS',value=f['ERROR_DEFINED'])if f['ERROR_DEFINITION_OBSERVED']else dict(tag='UNOBSERVED',value=None)
    require(f['ERROR_DEFINITION_OBSERVED']or not f['ERROR_DEFINED'],'STATE_CONTRADICTION',offset=offset)
    q['pre_dispatch_clock']=clock_atom((bits>>32)&3,q.pop('pre_dispatch_clock_bits'),offset+88);q['post_binding_clock']=clock_atom((bits>>34)&3,q.pop('post_binding_clock_bits'),offset+96)
    if q['buffer_id']==65535:q['buffer_id']=None
    for k,g in(('phase','phase_code'),('fold_state','fold'),('buffer_state','buffer')):q[k]=enum_name(g,q[k],offset)
    return q
def _unpack_module(raw,offset):
    q=_layout_read(raw,offset,'module_record');q['flags']=flags_value('module_flags',q['flags'],offset+4);return q
def _unpack_diag(raw,offset):
    q=_layout_read(raw,offset,'diagnostic_record');q['flags']=flags_value('diagnostic_flags_bits',q['flags'],offset+5)
    for k,g in(('state','diagnostic_state'),('phase','phase_code'),('severity','severity')):q[k]=enum_name(g,q[k],offset)
    q['clock_atom']=clock_atom(q.pop('clock_tag'),q.pop('clock_bits'),offset+32)
    for k,cap in(('class',96),('message',512),('args',256)):
        n=q[k+'_bytes'];require(n<=cap,'DIAGNOSTIC_LAYOUT',offset=offset);rawbytes=q[k+'_utf8'];require(not any(rawbytes[n:]),'RESERVED_NONZERO',offset=offset);q[k+'_utf8']=rawbytes[:n]
    return q
READERS=(_unpack_file,_unpack_call,None,None,_unpack_module,None,None,_unpack_diag)
def decode_ledger(raw,*,check):
    require(callable(check),'TYPE_DOMAIN');check();require(type(raw)is bytes,'TYPE_DOMAIN');require(4096<=len(raw)<=MAX_BYTES,'SIZE_CAP',offset=len(raw))
    h=_layout_read(raw,0,'header');require(h['magic']==b'RAPLEDG1'and h['format_version']==1 and h['value_schema_version']==2,'MAGIC_VERSION',offset=0)
    require(h['total_bytes']<=len(raw),'SECTION_LAYOUT',offset=40);require(h['total_bytes']==len(raw),'TRAILING_BYTES',offset=h['total_bytes'])
    require(h['header_bytes']==4096 and h['section_count']==8 and h['path_policy']==1,'SECTION_LAYOUT',offset=18)
    for k in('profile','phase','status'):h[k]=enum_name(k,h[k],0)
    require(1<=h['file_count']<=(4 if h['profile']=='ORIGINAL7_N4'else 256)and h['call_count']<=(92 if h['profile']=='ORIGINAL7_N4'else 16384)and h['module_count']<=(2 if h['profile']=='ORIGINAL7_N4'else 128)and h['diagnostic_count']<=5056 and h['edge_count']<=16384,'SIZE_CAP',offset=22)
    require(h['module_count']==h['module_count_repeat'],'SECTION_LAYOUT',offset=18)
    h['flags']=flags_value('header_flags_bits',h['flags'],36);require(h['clock_tags']&192==0,'RESERVED_NONZERO',offset=120)
    for i,k in enumerate(('start_clock','latest_clock','freeze_clock')):h[k]=clock_atom((h['clock_tags']>>(2*i))&3,h.pop(k+'_bits'),96+8*i)
    if not h['flags']['PREVIOUS_LEDGER_PRESENT']:require(h['previous_ledger_sha256']==ZERO32,'RESERVED_NONZERO',offset=128);h['previous_ledger_sha256']=None
    if h['profile']=='UNQUALIFIED_FRAGMENT':require(h['reserved_R']==h['reserved_C']==h['reserved_E']==0,'RESERVED_NONZERO',offset=168)
    counts=(h['file_count'],h['call_count'],None,None,h['module_count'],None,h['edge_count'],h['diagnostic_count']);result={};expected=4096
    for i,(name,width)in enumerate(zip(SECTIONS,WIDTHS)):
        pos=256+64*i;desc=_layout_read(raw,pos,'section_descriptor');require(desc['flags']==0,'RESERVED_NONZERO',offset=pos+56)
        require(desc['id']==i+1 and desc['record_size']==width and desc['offset']==expected and desc['length']==desc['count']*width and expected+desc['length']<=len(raw),'SECTION_LAYOUT',offset=pos)
        if counts[i]is not None:require(desc['count']==counts[i],'SECTION_LAYOUT',offset=pos+4)
        segment=memoryview(raw)[expected:expected+desc['length']];check();require(hashlib.sha256(segment).digest()==desc['sha256'],'SECTION_DIGEST',offset=pos+24)
        if READERS[i]:result[name]=[READERS[i](raw,expected+j*width)for j in range(desc['count'])]
        elif name=='module_edges':result[name]=tuple(struct.unpack_from('<H',raw,expected+j*2)[0]for j in range(desc['count']))
        else:result[name]=bytes(segment)
        expected+=desc['length']
    require(expected==len(raw),'SECTION_LAYOUT',offset=expected)
    result['header']={k:h[k]for k in HEADER_KEYS};validate_value(result,check)
    for field,key in(('captured_input_bytes','captured_blob_length'),('known_read_bytes','known_read_bytes'),('hashed_bytes','hashed_bytes'),('copied_bytes','captured_bytes')):require(h[field]==sum(f[key]for f in result['files']),'STATE_CONTRADICTION',offset=48)
    out=DecodedLedger(result,raw);check();return out

def iter_checked_records(raw,*,check):
    """Read ALL actual bytes; yield one row, never a second call table.

    This internal consumer does not create a producer or provenance. The owner
    compares each tuple to its canonical frozen-phase source fields.
    """
    require(type(raw)is bytes and 4096<=len(raw)<=MAX_BYTES,'TYPE_DOMAIN');check()
    h=_layout_read(raw,0,'header')
    require(h['magic']==b'RAPLEDG1'and h['format_version']==1 and h['value_schema_version']==2,'MAGIC_VERSION')
    require(h['total_bytes']==len(raw)and h['section_count']==8 and h['header_bytes']==4096,'SECTION_LAYOUT')
    require(h['file_count']<=256 and h['call_count']<=16384 and h['module_count']<=128 and h['diagnostic_count']<=5056 and h['edge_count']<=16384,'SIZE_CAP')
    yield 'header',0,h
    expected=4096;counts=(h['file_count'],h['call_count'],None,None,h['module_count'],None,h['edge_count'],h['diagnostic_count'])
    names=(FILE_KEYS,CALL_KEYS,None,None,MODULE_KEYS,None,None,DIAG_KEYS)
    for i,(name,width)in enumerate(zip(SECTIONS,WIDTHS)):
        pos=256+64*i;desc=_layout_read(raw,pos,'section_descriptor')
        require(desc['flags']==0,'RESERVED_NONZERO',offset=pos+56)
        require(desc['id']==i+1 and desc['record_size']==width and desc['offset']==expected and desc['length']==desc['count']*width and expected+desc['length']<=len(raw),'SECTION_LAYOUT',offset=pos)
        if counts[i]is not None:require(desc['count']==counts[i],'SECTION_LAYOUT',offset=pos)
        view=memoryview(raw)[expected:expected+desc['length']];check();require(hashlib.sha256(view).digest()==desc['sha256'],'SECTION_DIGEST',offset=pos+24)
        if READERS[i]:
            for j in range(desc['count']):
                row=READERS[i](raw,expected+j*width);yield name,j,tuple(row[k]for k in names[i]);check()
        elif name=='module_edges':
            for j in range(desc['count']):yield name,j,struct.unpack_from('<H',raw,expected+2*j)[0]
        else:yield name,0,view
        expected+=desc['length']
    require(expected==len(raw),'TRAILING_BYTES',offset=expected);check()
