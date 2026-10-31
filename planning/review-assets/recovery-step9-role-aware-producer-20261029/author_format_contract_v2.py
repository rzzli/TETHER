"""Apply the five approved specification-DATA clarifications; no codec/producer."""
from pathlib import Path
import json
import hashlib
import copy

ROOT=Path(__file__).resolve().parents[3]
DEST=Path(__file__).parent

def pin(path):
    raw=path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)).replace('\\','/'),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def write(name,value):
    path=DEST/name
    path.write_bytes((json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode())
    return pin(path)

before=DEST/'ROLE-AWARE-PRODUCER-FORMAT-CONTRACT-v1.json'
assert pin(before)['sha256']=='d5f28f0b5aa151515941b6a39b03d3a811c6012fa055490a4103927871fa69e4'
old=json.loads(before.read_bytes())
value=copy.deepcopy(old)
value['schema_version']=2
value['status']='COMPLETE_SCHEMA_V2_FIVE_GROUP_CLARIFICATION_ONLY_PENDING_PEER'
value['preserved_schema']=pin(before)
value['correction_scope']=pin(DEST/'ROLE-AWARE-PRODUCER-FORMAT-ROOT-CLARIFICATION-CHOICE-v2.json')
value['preserved_hold']=pin(DEST/'ROLE-AWARE-PRODUCER-FORMAT-INDEPENDENT-REVIEW-v1.json')
assert value['correction_scope']['sha256']=='97c2c67232660c6c5e9a457a62aec07afef2a1754e6bc28ba87a67b51d2dd9d4'
assert value['preserved_hold']['sha256']=='44eee60666d9ee62e2e821bfd0710c754e1934c68f14fff59d4a8b97a7bc4c3b'
value['document_version_rule']='Document revision2 closes the initial unimplemented format. Wire format_version1/value_schema2/magic and all byte offsets remain as v1 except the type annotation of optional error_id; no issued v1 bytes, implementation or goldens exist to inherit.'

# S1: unique byte-pool descriptor sizes/counts, including the empty fragment.
sizes={1:256,2:256,3:1,4:1,5:64,6:1,7:2,8:1024}
counts={1:'len(files)=N',2:'len(calls)=used_C',3:'len(queries) in bytes',4:'len(paths) in bytes',5:'len(modules)=M',6:'len(module_names) in bytes',7:'len(module_edges) entries',8:'len(diagnostics)=committed_D'}
for section in value['sections']:
    ident=section['id']
    section['record_bytes']=sizes[ident]
    section['descriptor_record_size']=sizes[ident]
    section['descriptor_count']=counts[ident]
value['framing']['descriptor_sizes']='Queries, paths and module_names ALWAYS have record_size1 and count=byte_length, including empty pools and fragment queries. Module_edges record_size2/count=tuple length. Files256/countN, calls256/countused_C, modules64/countM, diagnostics1024/countcommitted_D. For every section length=record_size*count; empty fixed tables retain their nonzero fixed record_size with count0. No 8218-byte descriptor record type remains:8218*N is the original query pool length, not descriptor record_size.'

# S2: absent expected size and input argument HANDLE0 have unique encodings.
value['files_modules']['expected_size']='Fragment expected_size is None iff EXPECTED_SIZE_PRESENT=false and encoded u64 bits0. An original known empty expected_size is exact int0 with presence=true. Originals require present size0..2^63-1. This is independent of expected digest presence. Decoder returns None versus0 exactly; no inference from zero bits.'
value['raw_atoms']['input_handle_domain']='input_handle_atom has ONLY UNOBSERVED/None or HANDLE/exact unsigned64. UNOBSERVED means INPUT_HANDLE_PRESENT=false/bits0; HANDLE means presence=true, including HANDLE0/INVALID as unqualified fragment negative data. NULL input refuses ATOM_DOMAIN: this field has no input-null bit and must not collide with HANDLE0. This restriction does NOT change the raw returned scalar NULL representation. Entered original operations require their canonical usable owned input handle; no guessed ownership from argument bits.'
value['value_api_details']['files']+=' expected_size may be None only under fragment absence law; wire bits0 plus EXPECTED_SIZE_PRESENT=false, distinct from present int0.'

# S3: definition is its own three-state atom, not raw error-code presence.
keys=value['value_api_details']['call_exact_keys']
keys.insert(keys.index('error_atom')+1,'error_definition_atom')
value['api']['value_shape']['atoms']+=' Error definition has its own atom: {tag:UNOBSERVED,value:None} or {tag:DEFINEDNESS,value:exact bool}. This atom is not a raw signed BOOL and is independent of error_atom observedness.'
value['raw_atoms']['error_definition_states']=[
    dict(atom=dict(tag='UNOBSERVED',value=None),ERROR_DEFINITION_OBSERVED=False,ERROR_DEFINED=False),
    dict(atom=dict(tag='DEFINEDNESS',value=False),ERROR_DEFINITION_OBSERVED=True,ERROR_DEFINED=False),
    dict(atom=dict(tag='DEFINEDNESS',value=True),ERROR_DEFINITION_OBSERVED=True,ERROR_DEFINED=True)
]
value['raw_atoms']['error_definition_rule']='The two bits are derived from the exact error_definition_atom and cross-checked against supplied flags. False/true with ERROR_DEFINITION_OBSERVED=false is invalid. Observed True requires invoked, domain-valid observed scalar in the per-API error-probe branch below. True is applicability knowledge, not proof that a DWORD error return exists or is nonzero. Raw error DWORD may arrive with definition still UNOBSERVED; applicable definition True may be stored before error_atom and survive a missing return. Observed False may coexist with an observed but undefined raw DWORD. Never infer missing=False, discard raw error or normalize True-on-success to False; reject incompatible definition True as STATE_CONTRADICTION.'
error_table=[]
for api in value['apis']:
    name=api['name']
    if api['scalar']=='HANDLE':
        branch='observed HANDLE exact18446744073709551615 (INVALID_HANDLE_VALUE) only'
        note='Observed NULL or HANDLE0 is unexpected ownership-unknown, not the documented INVALID branch; definition True is refused there.'
    elif api['scalar']=='DWORD':
        branch='observed domain-valid DWORD exact0 only'
        note='Nonzero DWORD, including a required-size response, is outside the error-probe branch.'
    else:
        branch='observed domain-valid signed32 BOOL exact0 only'
        note='Any nonzero signed32 result, including2 and-1, is outside the error-probe branch.'
    if name=='GetFileType':
        note+=' DWORD0 can mean FILE_TYPE_UNKNOWN. A defined error DWORD0 is known NO_ERROR, not undefined; it still does not prove required FILE_TYPE_DISK1.'
    if name=='FindFirstFileExW':
        note+=' Defined error2 may support a future explicitly scoped empty-search interpretation; fragment decoding alone does not authorize or complete a scan.'
    if name=='FindNextFileW':
        note+=' Defined error18 may support a future explicitly scoped end-of-directory interpretation; missing/undefined error18 cannot imply EOF.'
    error_table.append(dict(api_id=api['id'],api=name,definition_true_branch=branch,raw_error_type='DWORD exact0..4294967295, including0',raw_error_return_required_for_definition=False,definition_on_success='UNOBSERVED or observedFalse only',note=note))
value['raw_atoms']['per_API_error_probe_table']=error_table
value['raw_atoms']['error_transport']='This table defines applicability of an already-declared typed error transport, not a new GetLastError export or an instruction to dispatch it. Raw scalar is committed first; definition and raw error each have independent first slots. Actual wrapper transport/probe ordering and last-error clearing/caching semantics remain a source-bound physical-interface prerequisite; format decoding never invokes a probe.'
value['raw_atoms']['applicability']='IDs1/9 HANDLE; IDs2/4 DWORD; other APIs BOOL. Count applies only6/13. COUNT_DEFINED iff invoked, valid observed nonzero signed32 BOOL, and observed exactCOUNT32<=requested, independently of buffer capture; hash/copy additionally requires observed buffer/written>=count. Error observedness and definition follow the explicit three-state atom and per-API table; neither implies the other. Raw observed error0 is never used as an undefined sentinel.'
value['flag_state_rules']['error_definition']='ERROR_DEFINED implies ERROR_DEFINITION_OBSERVED, but neither ERROR_DEFINED nor its observation implies ERROR_OBSERVED. ERROR_OBSERVED likewise does not imply definition observed. A True definition requires the exact per-API branch even in a negative/fragment record. Pending raw error and undefined observed values remain distinct.'

# S4: exact result/error/publication/legacy value surfaces.
for field in value['call_record']['fields']:
    if field['name']=='error_id':
        assert field['offset']==104 and field['bytes']==4
        field['type']='optional_u32'
value['value_api_details']['optional_error_id']='Call.error_id is None iff encoded u32=0xffffffff; otherwise exact nonbool int0..committed_D-1, pointing to that actual diagnostic. Raw error DWORD is separate and may be0; diagnostic ordinal0 is valid and not absence.'
value['api']['decoded_surface']=dict(
    to_dict='Returns EXACT canonical encode-value shape/types, not a binary-layout dump: nine keys in api.value_shape; list tables; bytes pools/digests; tuple module_edges; named-string enums; closed bool flag dicts; exact typed raw/definition/clock atoms; optional None values restored. It includes no derived header totals/section descriptor fields/reserved padding or extra convenience data. Optional error_id and fragment expected_size restore None. All data are detached from callers; module_edges remains a tuple, not a list.',
    to_bytes='Returns the exact original immutable raw bytes held by DecodedLedger, without re-encoding or callbacks. No owner/token capability is attached.',
    getters='Both getters are cache-only: no validation callback, clock, filesystem access, hashing or original-value reinterpretation. A dictionary/list mutation in one to_dict result cannot affect the object or later results.',
    encode_canonicalization='Encoder validates and captures its exact ordinary input before callbacks after capture. A canonical in-domain input is reproduced by decode(encode(value)).to_dict with exactly these container types and tagged values; no bool/int coercion, input NULL normalization, alias-key support or scalar-value normalization.'
)
value['validation']['FormatError_surface']=dict(
    code='Exact builtin str, one key/name of validation.error_codes. The numeric enum ID is not the public .code value.',
    offset='None for value-input or nonlocal errors; otherwise exact nonbool int in0..len(raw), representing the first offending/missing byte boundary. len(raw) is allowed for truncation. No negative offset or guessed offset for value mode.',
    path='Exact tuple of internal exact builtin str field names and nonnegative exact nonbool int positions/ordinals. Root path is(). It never contains an offending supplied object/value, coerced repr or user-created subclass. No file path or source authority is implied.',
    invariants='The three public values are fixed at construction. Check-callback exceptions propagate unchanged and are not converted to FormatError; getter calls never invoke check.'
)
value['publication']['constants']=dict(packet_schema_version=2,packet_scope='role_aware_producer_format_v1',report_schema_version=2,report_format_id='ROLE_AWARE_LEDGER_1',status=['OBSERVED_COMPLETE','OBSERVED_NEGATIVE','INCOMPLETE'],packet_kind=['candidate','cleanup','failure','receipt','seal'],packet_kind_to_artifact={'candidate':'candidate.json','cleanup':'cleanup.json','failure':'failure.json','receipt':'receipt.json','seal':'seal.json'},report_scope_key_allowed=False)
value['publication']['constant_rules']='Packets require schema_version exact int2 and scope exact role_aware_producer_format_v1; report requires schema_version int2/format_id ROLE_AWARE_LEDGER_1 with NO extra scope key. Status is exactly one of the three declared new format status strings for both; do not inherit legacy pure_shared_owner_seam or legacy completion statuses. Profile/phase are exact existing named enums. Kind aliases map to five artifact filenames only. Structural OBSERVED_COMPLETE never mints source, physical or scientific completion authority.'
value['legacy_projection']['BOOL_mapping']='New raw atom tagBOOL maps to legacy atom tagBOOL32 with the IDENTICAL signed32 Python integer, including2/-1/0. The reverse harness mapping BOOL32->BOOL changes the tag only. Never normalize any nonzero value to1 or boolTrue. HANDLE/DWORD/COUNT32/NULL/UNOBSERVED retain their existing tags and first observed values.'
value['legacy_projection']['input_error_id']='Optional packed diagnostic ID is data only. Genuine producer projection preserves the actual opaque diagnostic identity token already issued by its canonical owner; None maps to absence, ordinal0 never fabricates a token.'

# S5: logical information allowances only; ALL boxed implementation storage unknown.
first=value['live_first_fact']
first['additional_live_accounting_kind']='LOGICAL_REFERENCE_AND_VALUE_BIT_ALLOWANCE_ONLY'
first['budget']='13,823,488 and combined127,809,034 are logical reference/value-bit allowances only, not physical live-payload bounds. Eight value bytes mean an in-domain information-bit allowance; they do NOT bound CPython integer digits, boxed float/numeric payload, object storage or slot containers. ALL boxed numeric/object storage, headers, dictionaries, containers, allocator, malformed returns and exception/module graphs remain unknown implementation memory. Eight-byte reference bits assume a prospective64-bit representation, not measured Python allocation. The F1 store/assembly byte ownership is unchanged; no heap/RSS/time/256MiB fit follows.'
first['additional_live_payload_terms_label']='Legacy field spelling is retained only to keep arithmetic auditable. Each entry is a logical reference/value-bit allowance, not a physical allocation bound; primitive_payload in a key never means boxed primitive allocation.'
value['memory_scope']+=' The13,823,488 logical live allowance excludes ALL boxed numeric digit/storage and does not close the memory gate.'

result=write('ROLE-AWARE-PRODUCER-FORMAT-CONTRACT-v2.json',value)

def diff(left,right,path=''):
    if type(left) is not type(right):
        return [path]
    if type(left) is dict:
        out=[]
        for key in sorted(set(left)|set(right)):
            child=path+'.'+key if path else key
            out.extend([child] if key not in left or key not in right else diff(left[key],right[key],child))
        return out
    if type(left) is list:
        if len(left)!=len(right):
            return [path]
        out=[]
        for i,(a,b) in enumerate(zip(left,right)):
            out.extend(diff(a,b,path+'['+str(i)+']'))
        return out
    return [] if left==right else [path]

changes=diff(old,value)
delta=dict(schema_version=2,status='FIVE_APPROVED_SCHEMA_GROUPS_ONLY_NO_CODE_OR_GOLDENS',preserved_schema=pin(before),preserved_freeze=pin(DEST/'ROLE-AWARE-PRODUCER-FORMAT-FREEZE-v1.json'),hold=value['preserved_hold'],root_choice=value['correction_scope'],successor=result,changed_paths=changes,groups=dict(S1='Uniform byte-pool descriptor counts',S2='Absent size/input HANDLE tag domain',S3='Independent three-state error definition and14 exact API branches',S4='Canonical decode/error/publication/error_id/BOOL32 value surfaces',S5='Logical-only live bit allowances; boxed implementation memory unknown'),unchanged=dict(offsets_and_widths=True,only_layout_annotation='call.error_id optional_u32, same104/4',role_capture_first_fact_clock_DIAG_F1_rules=True,scientific_and_inactive_profile_limits=True,artifact_store40139776=True,live_allowance13823488_and_combined127809034=True,physical_and_full84_gates_pending=True),activity=dict(encoder_or_producer_source=False,golden_generation=False,subject_tests=0,original_native_runtime_operations=0))
delta_pin=write('ROLE-AWARE-PRODUCER-FORMAT-DELTA-v2.json',delta)
print(json.dumps(dict(schema=result,delta=delta_pin,changed_paths=len(changes)),indent=2))
