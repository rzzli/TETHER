"""Author specification DATA only. Does not encode ledgers or run producer code."""
from pathlib import Path
import json
import hashlib

ROOT = Path(__file__).resolve().parents[3]
DEST = Path(__file__).parent

def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)).replace('\\', '/'), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def layout(rows, size):
    fields = []
    offset = 0
    for name, kind, count in rows:
        fields.append(dict(name=name, offset=offset, bytes=count, type=kind))
        offset += count
    assert offset <= size
    if offset < size:
        fields.append(dict(name='reserved_zero_tail', offset=offset, bytes=size-offset, type='zero_bytes'))
    return dict(bytes=size, fields=fields)

def enum(names, start=0):
    return {name: i+start for i, name in enumerate(names)}

def write(name, value):
    path = DEST / name
    path.write_bytes((json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False)+'\n').encode())
    return pin(path)

proposal = json.loads((DEST/'ROLE-AWARE-PRODUCER-STORAGE-PROPOSAL-v2.json').read_bytes())
legacy_path = ROOT/'planning/review-assets/recovery-step9-shared-owner-20261029/SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json'
legacy = json.loads(legacy_path.read_bytes())
rows = [(x['field'], {1:'u8',2:'u16',4:'u32',8:'u64'}.get(x['bytes'],'zero_bytes'), x['bytes']) for x in proposal['representation']['call_layout'] if x['field'] != 'reserved_zero_tail']
call = layout(rows, 256)
for item in call['fields']:
    if item['name'] == 'reserved_clock_observation_1':
        item.update(name='pre_dispatch_clock_bits', type='typed_clock_bits')
    elif item['name'] == 'reserved_clock_observation_2':
        item.update(name='post_binding_clock_bits', type='typed_clock_bits')

header = layout([
    ('magic','ascii8',8), ('format_version','u16',2), ('value_schema_version','u16',2),
    ('profile','u16',2), ('phase','u16',2), ('status','u16',2), ('header_bytes','u16',2),
    ('section_count','u16',2), ('file_count','u16',2), ('call_count','u32',4),
    ('module_count','u16',2), ('diagnostic_count','u16',2), ('edge_count','u32',4),
    ('flags','u32',4), ('total_bytes','u64',8), ('captured_input_bytes','u64',8),
    ('known_read_bytes','u64',8), ('hashed_bytes','u64',8), ('copied_bytes','u64',8),
    ('origin_data_id','u64',8), ('ledger_sequence','u64',8),
    ('start_clock_bits','typed_clock_bits',8), ('latest_clock_bits','typed_clock_bits',8),
    ('freeze_clock_bits','typed_clock_bits',8), ('clock_tags','u8',1),
    ('reserved_121_127','zero_bytes',7), ('previous_ledger_sha256','digest32',32),
    ('qualification_bits','u64_must_be_zero',8), ('reserved_R','u32',4),
    ('reserved_C','u32',4), ('reserved_E','u32',4), ('early_count','u16',2),
    ('module_count_repeat','u16',2), ('read_chunk','u32',4), ('path_policy','u16',2),
    ('reserved_to_descriptors','zero_bytes',66), ('section_descriptors','8x64',512)
], 4096)
section = layout([('id','u16',2),('record_size','u16',2),('count','u32',4),('offset','u64',8),('length','u64',8),('sha256','digest32',32),('flags','u32_must_be_zero',4)],64)
file = layout([
    ('ordinal','u16',2),('role','u8',1),('capture_state','u8',1),('target_class','u8',1),
    ('open_state','u8',1),('identity_state','u8',1),('close_state','u8',1),('flags','u64',8),
    ('descriptor_id','u32',4),('path_offset','u32',4),('path_bytes','u32',4),
    ('path_utf16_units','u16',2),('reserved_30','zero_bytes',2),('expected_size','u64',8),
    ('expected_sha256','digest32',32),('actual_sha256','digest32',32),
    ('open_ordinal','optional_u32',4),('close_ordinal','optional_u32',4),
    ('known_read_bytes','u64',8),('hashed_bytes','u64',8),('captured_bytes','u64',8),
    ('query_offset','u32',4),('query_length','u32',4),('first_diagnostic','optional_u32',4),
    ('read_reservations','u32',4),('read_invocations','u32',4),('captured_blob_length','u32',4),
    ('early_ordinal','optional_u16',2),('path_id','u16',2),('read_generation','u32',4),
    ('module_ordinal','optional_u16',2)
],256)
module = layout([
    ('ordinal','u16',2),('file_ordinal','u16',2),('flags','u16',2),('dependency_count','u16',2),
    ('name_offset','u32',4),('name_length','u16',2),('reserved_14','zero_bytes',2),
    ('edge_offset','u32',4),('first_diagnostic','optional_u32',4),
    ('attempt_order','optional_u16',2),('return_order','optional_u16',2),
    ('cache_hit_count','u16',2),('reserved_30','zero_bytes',2)
],64)
diagnostic = layout([
    ('ordinal','u32',4),('state','u8',1),('flags','u8',1),('phase','u16',2),
    ('opaque_identity_id','u64',8),('call_ordinal','optional_u32',4),
    ('secondary_of','optional_u32',4),('class_bytes','u16',2),('message_bytes','u16',2),
    ('args_bytes','u16',2),('reserved_30','zero_bytes',2),('clock_bits','typed_clock_bits',8),
    ('clock_tag','u8',1),('severity','u8',1),('reserved_header','zero_bytes',86),
    ('class_utf8','fixed96',96),('message_utf8','fixed512',512),('args_utf8','fixed256',256)
],1024)
exports = json.loads((ROOT/'planning/review-assets/recovery-step9-file-ports-20261029/FILE-PORTS-DESIGN-CONTRACT-v2.json').read_bytes())['semantic_contract']['ABI']['exports']
apis = []
for ident, item in enumerate(exports, 1):
    name = item['name']
    frame = {'GetFileInformationByHandleEx':8,'GetFinalPathNameByHandleW':8202,'GetFileSizeEx':8,'GetFileAttributesExW':36,'FindFirstFileExW':592,'FindNextFileW':592}.get(name,0)
    target = 'ORIGINAL' if ident<=7 else 'ANCESTOR' if name=='GetFileAttributesExW' else 'SEARCH' if name in ('FindFirstFileExW','FindNextFileW','FindClose') else 'NAMESPACE' if name=='CreateDirectoryW' else 'GENERATED'
    apis.append(dict(id=ident,name=name,scalar=item['restype'],target=target,query_frame_bytes=frame,count_applicable=name in ('ReadFile','WriteFile'),complete_ledger_allowed=ident<=7,fragment_allowed=True))
call_flags = enum(['INVOKED','SCALAR_OBSERVED','SCALAR_NULL','COUNT_OBSERVED','COUNT_DEFINED','ERROR_OBSERVED','ERROR_DEFINED','SCALAR_AUX_ACK','COUNT_AUX_ACK','RIGHT_TRANSFER_ACK','WRAPPER_RETURNED','STOPPED','QUERY_CAPTURE_OBSERVED','QUERY_DEFINED','BUFFER_DATA_OBSERVED','ACCOUNTING_FAULT','CLOSE_RIGHT_CONSUMED','IDENTITY_VERIFIED_AT_DISPATCH','SCALAR_DOMAIN_VALID','COUNT_DOMAIN_VALID','ERROR_DOMAIN_VALID','PRE_CLOCK_ATTEMPTED','POST_CLOCK_ATTEMPTED','PRE_CLOCK_RETURN_OBSERVED','POST_CLOCK_RETURN_OBSERVED','HASH_ATTEMPTED','HASH_RETURN_OBSERVED','COPY_ATTEMPTED','COPY_RETURN_OBSERVED','CAPTURE_REQUESTED','MALFORMED_RAW','ERROR_DEFINITION_OBSERVED'])
enums = dict(
    profile={'UNQUALIFIED_FRAGMENT':0,'ORIGINAL7_N4':1,'ORIGINAL7_PROSPECTIVE':2},
    phase={'FRAGMENT':0,'CANDIDATE':1,'TERMINAL':2},
    status={'OBSERVED_COMPLETE':1,'OBSERVED_NEGATIVE':2,'INCOMPLETE':3},
    role={'NONE_FRAGMENT_ONLY':0,'CAPTURED_SOFTWARE':1,'CAPTURED_METADATA':2,'HASH_ONLY_BULK':3},
    capture={'NOT_REQUESTED':0,'PENDING':1,'COMPLETE':2,'FAILED':3},
    target={'ORIGINAL':1,'ANCESTOR':2,'SEARCH':3,'GENERATED':4,'NAMESPACE':5},
    open=enum(['UNOPENED','RESERVED','ENTERED_RETURN_UNKNOWN','OWNED','KNOWN_FAILURE_NO_HANDLE','OWNERSHIP_UNKNOWN']),
    identity=enum(['NOT_ATTEMPTED','IN_PROGRESS','VERIFIED','REFUSED','UNKNOWN']),
    close=enum(['NOT_ATTEMPTED','RESERVED','ENTERED_RETURN_UNKNOWN','RETURNED_SUCCESS','RETURNED_FAILURE','NOT_DISPATCHED_DEADLINE']),
    fold=enum(['PENDING','COMMITTING','COMMITTED','FAILED_BEFORE_COMMIT','FAILED_AFTER_COMMIT']),
    buffer=enum(['NOT_APPLICABLE','RESERVED','RAW_RETAINED','DEFINED','INCOMPLETE_UNKNOWN']),
    wrapper=enum(['NOT_RETURNED','RETURNED','RAISED']), clock={'UNOBSERVED':0,'I64':1,'F64':2},
    diagnostic_state={'COMMITTED':2,'FORMAT_FALLBACK':3}, severity={'PRIMARY':1,'SECONDARY':2,'FORMATTER_FAILURE':3},
    module_flags={'PACKAGE':0,'RETURN_OBSERVED':1,'ACCEPTED':2,'CACHED':3},
    artifact=enum([a['kind'] for a in proposal['serialization']['artifacts']],1),
    artifact_state=enum(['RESERVED','BUILDING','UNISSUED_PARTIAL','ISSUED','UNKNOWN_RETURN']),
    phase_code=enum(list(dict.fromkeys(legacy['diagnostic_phase_enum']+['source_admission','canonical_reconcile','encoding','freeze','generated_checker','legacy_projection','fragment']))),
    call_flags_bits=call_flags,
    file_flags_bits=enum(['EXPECTED_DIGEST_PRESENT','ACTUAL_DIGEST_PRESENT','CAPTURE_REQUESTED','HASH_ATTEMPTED','HASH_COMPLETE','CAPTURE_COMPLETE','READ_UNKNOWN','HASH_UNKNOWN','COPY_UNKNOWN','CLOSE_RESERVED','EARLY','CLOSE_SUCCESS_KNOWN','CLOSE_SUCCESS_TRUE','ASSEMBLY_RETAINED'])
)
contract = dict(schema_version=1,status='DRAFT_TABLES_NO_ENCODER_OR_PRODUCER',header=header,section_descriptor=section,call_record=call,file_record=file,module_record=module,diagnostic_record=diagnostic,enums=enums,apis=apis)
write('ROLE-AWARE-PRODUCER-FORMAT-TABLES-DRAFT-v1.json',contract)

# Closed remaining table additions before the first complete contract freeze.
enums['call_flags_bits'].update(INPUT_HANDLE_PRESENT=36,REQUESTED_PRESENT=37,BUFFER_PRESENT=38,QUERY_SPAN_PRESENT=39)
enums['file_flags_bits'].update(BLOB_ISSUED=14,EXPECTED_SIZE_PRESENT=15)
enums['header_flags_bits']=enum(['READ_UNKNOWN','HASH_UNKNOWN','COPY_UNKNOWN','ACCOUNTING_FAULT','PRIMARY_PRESENT','CLOCK_INVALID'])
enums['diagnostic_flags_bits']=enum(['CLASS_TRUNCATED','MESSAGE_TRUNCATED','ARGS_TRUNCATED','FORMAT_FAILED'])

call_fields=['owner','ordinal','api','file','requested','buffer','generation','scalar_fact','count_fact','error_fact','error_definition_fact','pre_clock_fact','post_clock_fact','invoked','scalar_aux_ack','count_aux_ack','right_transfer_ack','wrapper_return_fact','wrapper_raise_fact','stopped','buffer_state','buffer_written','query_bytes_ref','reservation_fold','read_fold_phase','read_contribution','hash_attempted','hash_return_fact','copy_attempted','copy_return_fact','hashed_contribution','captured_contribution','ref','diagnostic_id']
file_fields=['owner','ordinal','spec_ref','path_ref','role','size','expected_digest_ref','actual_digest_ref','early_ordinal','open_call_ref','close_call_ref','identity_query_refs','identity_witness_ref','hash_state_ref','assembly_ref','blob_ref','known_count','hashed_count','captured_count','read_reservations','capture_state','open_state','identity_state','close_state','close_reserved','read_unknown','hash_unknown','copy_unknown','ref']
module_fields=['owner','ordinal','file_ref','name_ref','dependencies_ref','package','attempt_order','return_order','accepted','cached','cache_hit_count','diagnostic_id','compiled_object_ref','ref']
live=dict(call_slot_refs=8*len(call_fields)*16384,call_primitive_payload=8*len(call_fields)*16384,file_slot_refs=8*len(file_fields)*256,file_primitive_payload=8*len(file_fields)*256,module_slot_refs=8*len(module_fields)*128,module_primitive_payload=8*len(module_fields)*128,original_path_unicode_payload=4*4100*256,module_name_unicode_payload=4*512*128,module_dependency_refs_and_integer_payload=16*128*128,exception_identity_refs=8*5056)

contract.update(
    status='COMPLETE_SCHEMA_DATA_ONLY_PENDING_INDEPENDENT_PEER',
    basis=[pin(DEST/'ROLE-AWARE-PRODUCER-DESIGN-ACCEPTANCE-v2.json'),pin(DEST/'ROLE-AWARE-PRODUCER-STORAGE-PROPOSAL-v2.json'),pin(DEST/'ROLE-AWARE-PRODUCER-F1-DESIGN-ADDENDUM-v2.json'),pin(DEST/'ROLE-AWARE-PRODUCER-PRECODE-SCHEMA-QUESTIONS-v1.json'),pin(legacy_path)],
    identity=dict(format_id='ROLE_AWARE_LEDGER_1',magic_hex=b'RAPLEDG1'.hex(),format_version=1,value_schema=2,endianness='little',integer_input='Exact builtin int only; bool/subclasses refused by type identity before comparison. No coercion/metaclass equality.',meaning='Decoded data has no source/owner/physical authority; format support is not active dispatch scope.'),
    api=dict(
        encode_ledger='encode_ledger(value: exact builtin closed dict, *, check)->exact bytes',
        decode_ledger='decode_ledger(raw: exact bytes, *, check)->immutable DecodedLedger',
        decoded_getters=['to_dict(): detached ordinary copy','to_bytes(): exact original immutable bytes; cache-only'],
        fragment_entry='Same encode_ledger/decode_ledger public APIs, header.profile UNQUALIFIED_FRAGMENT. No private API or fake complete profile.',
        projection='project_legacy(snapshot: exact same-owner source-issued ProducerSnapshot, *, check)->immutable LegacySnapshot. This is a PRODUCER-adapter, not pure decoder API; dict and DecodedLedger refuse.',
        cancellation='First check before structural capture; bounded exact-builtin detached capture with no callbacks/custom container traversal; check after capture, during bounded decode/hash steps, and after immutable bytes/report preparation before return. Every check exception propagates by identity. No clock or authority is supplied by check.',
        value_shape=dict(exact_keys=['header','files','calls','queries','paths','modules','module_names','module_edges','diagnostics'],header_keys=['profile','phase','status','origin_data_id','ledger_sequence','start_clock','latest_clock','freeze_clock','previous_ledger_sha256','reserved_R','reserved_C','reserved_E','early_count','read_chunk','flags'],table_input='Each record has EXACT nonreserved layout keys. Enums use exact named strings, flags use a closed dict of every named bit->exact bool. raw_scalar_bits is supplied as scalar_atom; raw_count as count_atom; raw_error as error_atom; input_handle_bits as input_handle_atom; both clock-bit fields as typed clock atoms. All other layout names unchanged. Offsets/lengths/digests in section descriptors/header are derived, never caller-ready claims.',pools='queries/paths/module_names exact bytes; module_edges exact tuple of module ordinals; arrays exact lists. Expected/actual digests bytes32 or None, optional ordinals None. Null/absent typed values must match flags. Reserved fields are absent from value and emitted zero.',atoms='Exact keys tag/value. Raw tags UNOBSERVED,NULL,HANDLE,BOOL,DWORD,COUNT32; clocks UNOBSERVED,I64,F64. Unobserved/null value None, other value exact declared builtin scalar. No inferred tag from falsey value.'),
    ),
    sections=[dict(id=i,name=n,record_bytes=s,length=length) for i,n,s,length in [(1,'files',256,'256*N'),(2,'calls',256,'256*used_C'),(3,'queries',8218,'8218*N; fragment exact applicable frame size'),(4,'paths',1,'sum original UTF8 bytes'),(5,'modules',64,'64*M'),(6,'module_names',1,'sum ASCII name bytes'),(7,'module_edges',2,'2*edge_count'),(8,'diagnostics',1024,'1024*committed_D')]],
    framing=dict(
        header='4096 bytes, descriptors at256..767 ID order1..8; all other reserved bytes zero. Header_bytes4096/section_count8/module_count_repeat==module_count/path_policy1/qualification_bits0. magic/version/schema/enums/counts must match.',
        sections='First offset4096; exact contiguous order, offset[i+1]=offset[i]+length[i], including empty sections. No gaps/overlap/wrap/padding/trailing bytes. total_bytes equals final end and len(raw). Checked sums/products and capacities before slicing/allocation; full maximum14800384. Every descriptor SHA256 covers exact section; empty uses SHA256(empty).',
        scalar_encoding='u8/u16/u32/u64 unsigned little endian with checked exact range; optional_u16 absent0xffff/optional_u32 absent0xffffffff. Absent digest32 allzero only when presence flagfalse. Reserved fields and unused high bits must be zero, never observed evidence.',
        counts='Original profiles:1<=N<=bound; file/path ordinals0..N-1; descriptor IDs unique permutation0..N-1. Calls exact reserved prefix0..used_C-1, used_C<=reserved_C. Modules0..M-1. Committed diagnostics exact prefix; borrowed/unfilled slots not serialized.',
        previous='Candidate phase sequence1 and previous32 zero. Terminal sequence2 and previousSHA256(issued candidate bytes), or zero only if candidate absent. Fragment sequence0. Manifest must agree; no SHA(empty) fallback or selfhash.',
        profile1='ORIGINAL7_N4: N<=4/file<=4096/captured<=16384/chunk65536/R<=68/C<=92/E<=224/B<=2/M<=2. These are new-format invariant fixtures; unchanged accepted legacy source/caps remain separate.',
        profile2='ORIGINAL7_PROSPECTIVE: N<=256/M<=128/B<=128/captured-file<=8388608/captured sum<=33554432/chunk1048576/C<=16384/E<=2240/D<=5056. Exact complete descriptor/module graph required, never aggregate-only/null resources.',
        formulas='Both profiles require R=sum(ceil(size/chunk)+16 for positive originals), C=6N+R, E=6N+2B+2M+192. Exact integer divmod, no float ceiling. All recorded reservations/debits within these bounds. Prospective profile is not activated or certified by64KiB calculator.',
        fragment='Profile0/phaseFRAGMENT/statusINCOMPLETE: file_count1/call_count1/M0, R=C=E=0, qualification0, one typed target descriptor roleNONE_FRAGMENT_ONLY, expected-size/digest absent, one raw call ordinal0. API1..14 allowed; query section length is exactly its API frame0/8/36/592/8202. No complete-ledger checker accepts profile0; no physical capacity or owner authority follows.'),
    raw_atoms=dict(
        presence='UNOBSERVED=>observedfalse/nullfalse/bits0; NULL=>observedtrue/nulltrue/bits0; HANDLE0=>observedtrue/nullfalse/bits0. Count/error observed0 uses presence=true/value0. Presence derives from canonical sentinel identity, never aux flags.',
        domains='HANDLE unsigned64 or observedNULL. INVALID_HANDLE=18446744073709551615 means known failure/no handle; HANDLE0 or NULL is ownership-unknown/no guessed close. DWORD/COUNT32 unsigned32 with high32 zero. BOOL exact signed32 represented low32 two-complement/high32zero; every nonzero2/-1 succeeds,0 fails. Raw NULL for BOOL/DWORD is retainable malformed negative only: MALFORMED_RAW,domain-validfalse,STOPPED,statusINCOMPLETE.',
        applicability='IDs1/9 HANDLE; IDs2/4 DWORD; remaining BOOL. Count only6/13; error DWORD any entered API. COUNT_DEFINED requires invoked+valid nonzeroBOOL+observedCOUNT32<=requested and matching buffer/data domain. Failed/unknown scalar leaves raw count undefined even if0 observed. Error definition is a separate observed sentinel-or-bool; ERROR_DEFINED requires ERROR_DEFINITION_OBSERVED and API failure. Undefined raw error/count retained, never successful zero.',
        inputs='INPUT_HANDLE_PRESENT only APIs2..7/10..11/13..14; absent bits0 versus presentHANDLE0 distinct. REQUESTED_PRESENT onlyRead/Write; absent requested0, present known0 legal fragment only. BUFFER_PRESENT requires buffer_id0read/1query/2write/3control, generation and buffer_written in capacity; absent ID0xffff/generation0/written0. Original Read requested1..min(chunk,remaining); fragment requestDWORD may be0 and never allocates that payload. QUERY_SPAN_PRESENT only applicable query APIs, exact owning frame offset/size.',
        unsupported='Raw malformed object/out-of-width integer is retained in canonical source slot, stops work and cannot issue a lossless ledger. Encoder refuses UNENCODABLE_RAW instead of wrap/clamp/default. A bounded failure diagnostic is not exact replacement raw facts. No decoder can invent a successful original from malformed record.',
        scope='APIs8..14 only fragments. FindClose only search, CloseHandle only file; target_class table is exact. Their scopes do not enter7-original C/query8218N arithmetic.'),
    flag_state_rules=dict(
        bits='fact_flags0..31 named bool bits;32..33 preclock tag,34..35 postclock tag;36..39 named input/request/buffer/query presence;40..63zero. File flags0..15 named,16..63zero. Header flags0..5 named,6..31zero. Unnamed module/diagnostic bits zero.',
        invoked='Unentered record: no scalar/count/error/aux/contribution, no read_unknown; optional attempted/returned preclock allowed. Entered/no scalar is returnunknown, notzero. No raw fact before entered. Reserved quota may be consumed before entered without APIattempt.',
        wrapper='WRAPPER_RETURNED is normal binding return, independent of STOPPED. Returned+stopped legal/monotone; wrapperstate RETURNED iff flagtrue; RAISED iff invoked+stopped+notreturned; otherwise NOT_RETURNED. Late/raise never erases known raw atoms/normal return.',
        aux='scalaraux requires scalarobserved, countaux requires countobserved. righttransfer requires observed usableHANDLE and same canonical owned right; missing ACK does not erase owned rawhandle. No ack alone creates ownership.',
        fold='PENDING/COMMITTING/COMMITTED/FAILED_BEFORE/FAILED_AFTER closed. Failed phases require ACCOUNTING_FAULT+STOPPED. Raw-defined count remains known even if contribution cache update interrupted. Identical duplicate facts idempotent; conflicting store refuses and never overwrites first. Canonical report may derive once from slots; it never heals failed cache or resumes work.',
        contributions='Only originalRead carries known/hash/copy amounts. Known=rawdefinedcount else0. Hash/copy=count only if its opaque return fact was observed; otherwise lowerbound0 and fileHASH_UNKNOWN/COPY_UNKNOWN if operation attempted. Hash-only copy flags/contributionfalse0. Captured copy requires countdefined and returns; <=defined count, file totals canonical sum once. Undefined/read nonreturn keeps unknown tail, notzero.',
        close='Consumed reservation precedes once-onlyclose dispatch. Known success from invoked observed validBOOL!=0, even later wrapper raises. FailedBOOL0 is failedcleanup, not contradiction. Unreturned/unentered has nullable success; no retry after consumed attempt. Source cell open handle remains canonical cleanup authority through fold/cache failure.'),
    clocks=dict(
        tags='UNOBSERVED0/bits0; I64 tag1 exact signed64 two-complement; F64 tag2 exact finite IEEE754bits including negativezero. Header clock_tags low2start,next2latest,next2freeze,top2zero. Call tags bits32..35. No bool/subclass, tag3, integer-to-float conversion or rounded big integer.',
        sites='Start is original first-entry returned sample; latest last observed owner sample at snapshot capture; freeze final returned preissuance sample. Pre_dispatch sampled after canonical reservation before enteredAPI; post_binding sampled after normal binding return before deadline check. Attempt flag reserved before sampling; returned raw clock slot assigned before validation/deadline. Clockthrow=attempted/no returned sample. Late returned values retained and veto eligibility.',
        narrowed_domain='Versioned successor accepts signed64 int or finitebinary64. Start+295/+300 must stay same-type representable finite and strictlygreater before first dispatch, elseCLOCK_DOMAIN. Nondecreasing compare uses exact original typed values. Unsupported value stays source canonical but prevents issuance. Old48 is in-domain; this does not claim compatibility with arbitrary huge historical Python ints.',
        authority='Header samples are data, not proof of true first entry/class/nonce continuity. Real trustedkernel/origin adoption and outer watchdog remain pending.'),
    query_paths=dict(
        spans='Original filef span8218*f: attrs8@+0, finalpath8202@+8, size8@+8210. Full frames retained. API2 noframe. Per-call spans exactly its own file/API. Fragment frame starts0 with exact API size. Missing capture has flagsfalse/length0/offset0 and reserved zero storage, never observed zeros. No frame alias across calls/files.',
        interpretation='Attrs <II attributes/reparse_tag; verified original nondirectory/nonreparse. Finalframe4101 UTF16LE units; returnedDWORD n1..4100 and unitn NUL. All8202 raw bytes retained, tail not presumed defined. Size <q nonnegative==expected. Fragment attrs36/Find592 rawbytes cannot prove original identity.',
        path_policy='Original strictUTF8 validscalars/noNUL, C/D absolute, <=4096 UTF16 units. ASCII casefold/slash key only; reject dot/dotdot/empty components, reservedDOS, trailingdot/space, forbidden controls/chars per pinned legacy path_key. Preserve original spelling. Final comparison strips native leading\\?\\ only; never open reportedpath. Original paths packed in file order with exact no-gap owned spans; byte and UTF16 counts recompute. Fragment targetlabel boundedUTF8 may contain searchwildcard and is not admitted original.',
        lifetime='Original UTF8 pool<=3*4100*N retained once; final raw UTF16 stays in query frame. One128KiB comparison workspace, no second retained decodedfinalpath pool. Query/read generation reuse only after complete required capture/hash/copy; failed/unknown copy quarantines current buffer. Uninitialized memory never gets QUERY_DEFINED.'),
    diagnostics=dict(
        borrow='D=2*(N+E+32)<=5056; one serial operation borrows TWO free slots before dispatch. Nested source helpers share this guard. Normal success releases both uncommitted borrows only after last throwablepostcheck/unwind. No permanent2*C consumption. Latch original exception reference before formatting.',
        commit='New original commits one ordinal; identitydedup byis returns existing ordinal. Formatter failure commits second original object with literal fallback, no recursiveformat. Committed metadata immutable and neverreused; owner primary/secondary getters remain originalobjects. Unfilled/borrowed slots notserialized. One failed formatter cannot rewrite primary.',
        protected='Healthy firstwork guard borrows2, leaving D-2=2*(N+E+31) protected. First workfailure commits<=2 and stopsnewwork. Remaining <=N closes +E remaining journal/callbackdispatches +31 otherterminal/check/format operations, <=2 fresherrors each, fit that reserve. No recursion/unbounded hooks. Cleanup guard borrows2; nonmandatorypublications must preserve2*remaining mandatoryclose attempts. Repeated sameerror uses no newslot. Unexpected exhaustion marks internalincomplete and cannot silently drop errors or use successful-call leakage to suppress owned mandatorycleanup.',
        record='Only stateCOMMITTED/FORMAT_FALLBACK wire records. opaque_identity_id=ordinal+1 is DATA, notPythonobjectid/token. Optional parent/call0xffffffff. Payload validUTF8 prefixes96/512/256, lengths checked/zero remainder. Flags bit0class-truncated/1message/2args/3format-failed, otherszero. Phase enumerated. args bounded metadata text notobjects. Diagnosticclock copies known sample, neverresamples. Partialformat remains private/unissued.',
        proof_limit='The source implementation must debit these guardedoperation counts and prove bounds with meaningful faultcontrols before qualification. Exception graphs/objectheaders remain unknownheap beyond1024B encoded metadata.'),
    files_modules=dict(
        files='Ordinal/path_id equalposition, descriptorid permutation. Expected digest/size present for originalprofiles, actual digest separatepresence. Absent digest allzero only flagfalse. Open/close absent0xffffffff; early/moduleabsent0xffff. File/header totals equal canonical rawcontribution sums. blobissued and complete are sourceobservations, not decoder-created bytecapabilities.',
        capture='Capturedroles requesttrue and PENDING/COMPLETE/FAILED. COMPLETE requires actual immutable blob issued,length=size,copied=size,hashcomplete/matching expected. Zero captured issues actualb-empty. Hashonly NOT_REQUESTED,requestfalse,capturecompletefalse,copied0,blobabsent,noassembly/copyunknown. FAILED plus COPY_UNKNOWN distinguishes uncertain tail. Digest alone never byteevidence.',
        modules='ASCII dotted identifiers<=512B, uniquenames/sourcepaths, capturedsoftware source for accepted module. Ordered unique dependencyordinals/no self/cycle/unlistedimports. Pools packed no gaps. PACKAGE/RETURN_OBSERVED/ACCEPTED/CACHED onlybits0..3. CACHED=>ACCEPTED=>RETURN_OBSERVED. Attempt/returnorders independentlycontiguous optional0xffff; knownlatereturned unaccepted/notcached valid. Totalcachehits<=M and load+cacheobservations<=2M, no unbounded retainednames. Refuse before capoverflow; sourceproposal must separately demonstrate48parity.',
        identity='Wire IDs never ownerbrands. All numericdomains exactbuiltins checked by typeidentity before comparisons; no metaclass/coercion. File identityverified requires fourquery API rawfacts, correctsize/path/attrs/type and original-clock acceptance sourcefact; data alone does not authenticate filesystem.'),
    live_first_fact=dict(
        authority='Canonical PREALLOCATED PYTHON SLOTS; encoded256B cells are DERIVED, not first-fact authority. Allocate/bind RawCarrier to canonicalowner/call/registry/buffer before invoke. Its scalar/count/error/error-definition/clock/opaque-return slots start as uniqueUNOBSERVED. No packed byte/flag is used to determine whether raw0/NULL was observed.',
        algorithm=['Retain returned raw object with one direct slotassignment when previousslot isUNOBSERVED, before typechecking/cache/fold/format/clock/packing. If already observed preservefirst and validate identicalduplicate afterward.','Observedness is slotisnotUNOBSERVED, not a laterboolflag; interruption afterassignment retains0/None even if ACK/flag writes neverhappen.','Only afterfirststore validate exacttype/domain and reconcile. Error-definition is its own sentinel-or-bool atom; missingdefinition ispending, notfalse.','Any cache/encoding fault latches originalobject/quarantineswork, keeps canonicalfacts and oncecleanup. Reporting derives rawknown contribution in one coldlinearpass; no healing/retry.','Hash/copy return is also sentinel-or-original returnslot, registered before contributioncounter; no-return keeps unknownoperation tail.','Encoder snapshots canonical sourcefields and independently derives flags; partialpacking never mutates sourcecell or issues eligible bytes.'],
        FFI_limit='Application ordering only after native-to-Python conversion; not an atomic no-allocation OS guarantee. Interruption before directslotassignment remainsunknown. Real wrapper/entry/conversion window pending. Legacy injected hooks test their deliveryboundary only.',
        ports=['reserve_call(api,file_ref,requested,buffer_ref)->source-issued CallLease/RawCarrier before invocation','trusted binding writes converted rawvalue directly in boundcarrier before reconcile; no rawhandle transfer from serializeddata','AdoptionHooks.reconcile(call_ref) validates/folds; legacy store_scalar/count/error pure-injected shim obeys same first-slot law after its foreign-ref precondition','owner.snapshot()->same-owner ProducerSnapshot with immutable diagnostics and genuine opaque refs','owner.freeze_generated(kind)->source-issued GeneratedArtifactBytes onceperkind','owner.generated_bytes(kind)->actual exact immutable bytes onlyifeligible','project_legacy(ProducerSnapshot)->strict capture-only LegacySnapshot'],
        slot_fields=dict(call=call_fields,file=file_fields,module=module_fields),
        additional_live_payload_terms=live,additional_live_payload_bytes=sum(live.values()),
        combined_conservative_named_payload_bytes=113985546+sum(live.values()),
        budget='Keep prior113985546 encoded/named reserve unchanged conservatively, ADD explicit live references/primitive/stringpayload rather than call encodedcells livePythonfacts.8B references assume64bit runtime; per-slot primitivepayload conservatively<=8B for in-domainfields, aliases charged more thanonce. Originalpath Unicodepayload4*4100*N, names4*512*M and edge refs+integers explicitlyseparate from wirepools. PyObject/slotcontainerheaders/dict/allocator/exception/module graphs and malformedobjectpayload are UNKNOWNRSS, neverzero. Unencodableraw prevents admission. No256MiBfit follows.'),
    generated=dict(
        artifact_caps=proposal['serialization']['artifacts'],store_bytes=40139776,assembly_max=14800384,
        issued='Same-owner source-issued GeneratedArtifactBytes carries owner/origin/nonce/registryrefs outsidewire,kind,phase,ACTUAL exactbytes,length/hash. Candidate/terminal distinct immutableobjects neveraliasedlivecells/assemblies/eachother. Decoder cannot mintthisbrand.',
        transitions='RESERVED->BUILDING->ISSUED aftercomplete freeze/hash/validation/originalclock. Failedfreeze->UNISSUED_PARTIAL discard; unknownreturn/release->UNKNOWN_RETURN quarantineoneassembly, nosecondbuild/retry. Knownlatereturn retainedinobservation/ineligible. Store slot notfileexistence.',
        checker='Source-boundchecker receives exact source-issued bytescontext for sameowner/kind/phase, validatesactualobjectlength/caps and consumes/decodes/hashes ALL bytes under checkcallback, then source-issued observation boundto exactcontext/bytes. Manifest/iterator/digest/count/readyflag cannot substitute. Requiredartifact set and semantic gate dependon actualconsumer graph, stillmissing.',
        input='Inputcontext keeps all specs/digests/roles, but blobs onlycompleted capturedsubset. bytes_for(hashonly) raisesCaptureNotRequested without reread/promotion. Digest-onlyobservation cannot satisfy byte/AST/PE/parser gate evenif getterrefusal caught. Generatedcontext links exactinputcontext/earlycontext; no secondowner or mirroredregistry.',
        physical='Known immutable storebytes and callbackACK do NOT prove physicalWrite/Flush/Close/readback; full14APIreservation and implementation remainsunqualified.'),
    publication=dict(
        report_exact_keys=['schema_version','format_id','profile','phase','status','counts','totals','ledger_refs','artifacts','diagnostic_counts','qualification'],
        packet_exact_keys=['schema_version','kind','scope','status','elapsed','totals','gates','ledger_refs','links','diagnostic_counts','qualification'],
        reference_exact_keys=['kind','phase','bytes','sha256'],
        artifact_exact_keys=['kind','state','attempted','return_observed','eligible','bytes','sha256','phase'],
        nested=dict(counts=['N','used_C','M','used_E'],totals=['known_read_bytes','hashed_bytes','copied_bytes','captured_input_bytes','generated_bytes','read_unknown','hash_unknown','copy_unknown'],diagnostic_counts=['committed','primary','secondary','formatter'],ledger_refs=['candidate','terminal'],links=['journal','producer_report','cleanup','receipt'],qualification=['originals','real_entry','real_FFI','physical_IO','new84_runtime','resource_fit','scientific']),
        encoding='Exact canonicalUTF8JSON sortkeys/separatorscomma-colon/ensure_asciiTrue/allow_nanFalse plus ONE LF; no BOM/extrakeys/duplicatekeys/alternatewhitespace/trailingLF. Enumstrings exact. Ref bytes/hash nulluntilknowncomplete. Actual packets/report<=8192 beforeissuance; full file/callarrays forbidden.',
        membership='14 registry slots, each atmostoneattempt and oneeligiblebytesobject; reservation!=fileexistence. candidate-ledger/candidate onlynormalacceptedwork; terminal/cleanup/failure maynegative/incomplete. Childattempt precedesobservedchildtrace; childfailure conditionalnegative, streamsindependent. receipt/seal onlyallrequiredgates+knownclosures+journalclose. Missing/unknownmandatoryartifact or failuremarker vetoespass.',
        DAG='candidateledger->candidate preclose; closes->terminalledger->cleanup/report; failureprejournalclose ifallowed; consumedjournalclose forbidsappend regardlessACK. receipt references prior terminal/cleanup/report/journal, seal priorreceipt/pins. Currentpacket/report selfrefnull; noforward/cyclic/selfhash. FinalACK in-memory afteroriginalfinalclock; postsealerror noadditionalwrites.',
        elapsed='Typed clockatom latest-start onlyifrepresentable else null+incomplete; no newclock orfloatcoercion. Data gates exactorderedsubset of pinned requiredgateorder, not realauthority. Everyqualification boolfalse; profilepass nevercomes from decode.'),
    legacy_projection=dict(
        reference=pin(legacy_path),
        input='EXACT same-owner source-issued ProducerSnapshot; genuineopaque tokens/refleaves alreadyissuedby owner. Dict/DecodedLedger/plainstructural projection refused beforecomparison. DecodeddiagnosticIDs neverminttokens. This API belongsproducer adapter aftersourceauthorization.',
        roles={'software':'CAPTURED_SOFTWARE','owner_metadata':'CAPTURED_METADATA','artifact':'CAPTURED_METADATA'},
        representability='Only N4/allcapture/size<=4096/sum<=16384/M<=2/B<=2/existing7API/lifecycle/legacyenum domain. Hashonly/profile2/newtarget/unknownnewphase refusesLEGACY_NOT_REPRESENTABLE. An oldrefusal remainsactualrefusal; newprofile cannot upgradesuccess.',
        fields='Validate complete actual successorSnapshot against new schema first; every pinned50ee key is copied from actualsourceobservations. Calls/counters/flags/stage/loader/journal/terminal/origin/callback facts unchanged. Omit only explicitnewrole/capturestate/store fields. Never fabricatecapturecomplete, dropcalls, normalizeBOOL, resampleclock, changestatus or recategorizeunknown.',
        atoms='UNOBSERVED->tagUNOBSERVED/valueNone; observedNULL->NULL/None; HANDLE0->HANDLE/0; signedBOOL2/-1 and rawCOUNT0+definedness unchanged. Knownwrapperreturn+stopped, lateknownACK and knownloaderreturned names preserved.',
        diagnostics='Diagnostic.identity keeps exactopaque tokenobject from sourcesnapshot; owner.exception_for_token(token) returns actualoriginalexception. No BaseExceptionleaf in immutablemetadata, no laterargs mutation changesissueddiagnostic. Packedordinal is onlydata, never token. Identityassertions remainEXTERNAL actualis checks.',
        identities=['Continuation.owner is canonicalowner','Origin/nonce/registry/sink/loader/journal sameobjects','fullctx.early_context is originalearlyctx','early immutable byteobjects identicalinfullcontext','file/call refs canonical before/aftercontinue/close','observation.context exactownerissuedcontext','diagnostictoken resolves originalgetterobject'],
        proof_scope='Unchanged48+8+16 actualproducerintegration afterfuture source; purecodecliterals onlyprove data/refusal, notownercontinuity.'),
    validation=dict(
        order=['exactbuiltin/containercardinality detachedcapture','header/version/profile/reserved/count/checkedsize','sectionorder/length/hash/completeconsumption','fieldenum/width/typedraw/clock/flag','file/path/queryspan','modulegraph/roles/loadorder','callordinal/API/state/count/contribution/close','canonicalfile/header sums and diagnostics','phase/previouspins/manifestmembership/DAG','immutableoutput thenfinalcheck'],
        error_codes=enum(['TYPE_DOMAIN','SCHEMA_KEYS','INTEGER_DOMAIN','SIZE_CAP','OVERFLOW','MAGIC_VERSION','RESERVED_NONZERO','SECTION_LAYOUT','SECTION_DIGEST','TRAILING_BYTES','ENUM_DOMAIN','ATOM_DOMAIN','STATE_CONTRADICTION','QUERY_SPAN','PATH_DOMAIN','MODULE_GRAPH','ROLE_CAPTURE','CLOCK_DOMAIN','DIAGNOSTIC_LAYOUT','REFERENCE_DOMAIN','UNENCODABLE_RAW','LEGACY_NOT_REPRESENTABLE','UNISSUED_ARTIFACT'],1),
        error='FormatError firstcode/offset/path only. Checkexceptions neverwrapped. Invalidcomplete cannot fallbackfragment/legacy. No decodedready/sourceauthentication.'),
    question_answers={f'Q{i}': name for i,name in enumerate(['header/sections/framing/publication','live_first_fact','apis/raw_atoms','flag_state_rules','clocks','query_paths','diagnostics','files_modules','generated','legacy_projection'],1)},
    fixture_plan=dict(
        maximum_histories=40,
        codec_only=['independentliteral header/section/record bytes for all14typedAPIatoms incl2/-1/0,NULL/HANDLE0/INVALID,count0definedundefined','tinycandidate/terminal observedcomplete/negative/partial and API8..14fragments','I64above2^53/negative0/finiteF64late andinvalidclocktypes/bits','eachreservedbyte/unknownenum/flag/length/span/hash/truncation/trailing/duplicate mutation','role/capture/zero/path/query/diag/module refs and syntheticmaxmetadata shape','independentliteral decodefields/encodebytes, notencoderdecoderagreementalone'],
        producer_only_pending=['faultafter firstslotassignment before flags/cache/pack keepsknown0/NULL/count and quarantines','>=16384 successful fictionaloperations releaseunfilledDslots; firstfault/protectedcleanup/formatteroriginalidentity','genuine issuedbytes/nonaliasing/freezeunissued/actualfullbyteconsumer','actualsource N4legacy48+8+16+externalidentity/hashonlygetterrefusal'],
        scope='Independentliteral corpus/testcontract freezes BEFORE encoder source scope. Livecontrols waitgenuineproducersource, notfixturestubs.'),
    qualification=dict(schema_design_only=True,encoder_implemented=False,producer_implemented=False,real_entry=False,real_FFI=False,physical_IO=False,full_roster_admitted=False,new84_runtime=False,resource_fit=False,scientific=False),
    memory_scope='256MiB belongs vocabulary-only/new84 harness ceiling, not inferenceRAM/VRAM/KVfit. Fullmodelinference allocation/deployment remains separatelyundeclared/unqualified.',
    activity=dict(subject_imports=0,subject_tests=0,original_or_payload_operations=0,native_SDK_compiler_IO=0)
)
# Final explicit cross-field and source/value boundaries; no encoder implementation.
enums['header_flags_bits']['PREVIOUS_LEDGER_PRESENT']=6
contract['framing']['previous']='Candidate phase sequence1 and PREVIOUS_LEDGER_PRESENT=false/payloadzero. Terminal sequence2 and flagtrue iff an issued candidate exists; its payload is the exact SHA256(candidate bytes), including the hypothetical allzero digest. Without candidate flagfalse/payloadzero. Fragment sequence0/flagfalse. Manifest agrees; no SHA(empty) fallback, selfhash or wire owner token.'
contract['raw_atoms']['applicability']='IDs1/9 HANDLE; IDs2/4 DWORD; all others BOOL. Count only6/13. COUNT_DEFINED iff invoked, valid observed nonzero signedBOOL and observed exactCOUNT32<=requested. This preserves known returned counts even when buffer capture/copy is missing; hashing/copying additionally requires observed bufferdata/written>=count. Failed/unknown scalar leaves observed raw count undefined, even0. Error DWORD may be observed for any enteredAPI; definition has its own sentinel-or-bool observation. ERROR_DEFINED requires definitionobserved and failurebranch. Undefined raw values are retained, never used as a known result.'
contract['flag_state_rules']['bits']='Call bits0..31 named bool;32..33 preclock tag/34..35 postclock tag;36..39 named input/request/buffer/query presence;40..63zero. File0..15 named/16..63zero. Header0..6 named/7..31zero. Module0..3 and diagnostic0..3 only; every other bit zero.'
contract['flag_state_rules']['additional_exact_relations']=[
    'SCALAR_DOMAIN_VALID/COUNT_DOMAIN_VALID/ERROR_DOMAIN_VALID equal recomputed atom domain validity when observed, false when absent. MALFORMED_RAW iff a retained representable atom violates the API type (NULL for nonHANDLE); that requires STOPPED and INCOMPLETE. Unsupported objects cannot be encoded.',
    'PRE/POST clock return-observed equals typed clock tag!=UNOBSERVED and implies its attempted bit. POST attempted implies WRAPPER_RETURNED. Unreturned attempted clock does not become zero. No tag without returned bit.',
    'HASH/COPY return-observed implies its attempted bit. These bits only on originalRead6; copy only if captured role. Hash/copy contribution requires countdefined, observedbufferdata with written>=count and matching generation. A failed opaque update cannot claim its tailzero; fileunknown flag records it.',
    'QUERY_CAPTURE_OBSERVED requires API-specific full frame bytes and query-span-present with exact offset/length. QUERY_DEFINED implies captureobserved and valid successful raw API result, but does NOT imply acceptable path/size/reparse semantics. Negative identity may retain a fully defined malformed/unexpected frame.',
    'BUFFER_DATA_OBSERVED requires invoked+bufferpresent, written<=requested forRead/Write or<=framecapacity. Observed empty write can have written0; absent data must have written0. No hash/copy from unobserved data.',
    'RIGHT_TRANSFER_ACK only CreateFile1 or fragmentFindFirst9 and observed usableHANDLE; raw owned handle remains canonical even ACKabsent. CLOSE_RIGHT_CONSUMED only CloseHandle7/fragmentFindClose11, can be true on a reserved-but-unentered close. It never grants a second attempt.',
    'IDENTITY_VERIFIED_AT_DISPATCH required for entered originalRead; not required for cleanupClose of a handle whose identity failed. CAPTURE_REQUESTED equals the declared file role for all original calls. Fragments with NONE role set itfalse.',
    'File CLOSE_SUCCESS_KNOWN iff closeordinal refers to an invoked observed validBOOL; CLOSE_SUCCESS_TRUE iff known and nonzero. Known failure maps RETURNED_FAILURE, known success RETURNED_SUCCESS. Unknown or unentered never maps knownfalse/success.',
    'Header unknown flags equal OR of file read/hash/copy unknown axes; primary/accounting/clockinvalid are snapshot facts and require INCOMPLETE/NEGATIVE, never OBSERVED_COMPLETE. OBSERVED_COMPLETE is structural observation completeness only and all exported qualification bits remainfalse.'
]
contract['diagnostics']['args_encoding']='args_utf8 is canonical JSON array of at most8 immutable repr strings, not arbitrary text. It must fit256 UTF8 bytes including brackets/escapes; choose bounded valid string prefixes and set ARGS_TRUNCATED if any reduction/removal is required. Never cut raw JSON mid-token. Emptyfallback is literal[]. Exact decoded array is retained in ProducerSnapshot; legacy projection refuses if truncation makes the source legacy metadata unrepresentable. class/message remain valid UTF8 prefix fields.'
contract['legacy_projection']['diagnostic_limits']='The producer retains already-issued immutable diagnostic metadata and genuine tokens. Projection requires its actual class/message/args metadata to fit pinned legacy limits without substitution; otherwise LEGACY_NOT_REPRESENTABLE. It never invents an8-element args list from a single formatted string or recomputes str/repr from a mutated exception. Packed args canonical JSON preserves list boundaries; truncation is explicit.'
contract['publication']['nested_rules']=dict(
    counts='All four exact integer fields, nonnegative within header/event bounds.',
    totals='Exact nonnegative integer byte fields, three exactbool unknown axes. They are source-observed lower bounds when unknown; no default0 tail.',
    diagnostic_counts='Four exact nonnegative ints; committed=primary+secondary, primary0or1, formatter<=secondary.',
    reference='Exactly kind/phase/bytes/sha256. Enumkind, phase, positive exact bytecount<=artifactcap, lower64hex SHA. Reference object nullable as whole; never partial numeric/hash ready claim.',
    artifacts='Exactly fourteen entries in enum order; each has closed fields. bytes/hash null before completed known bytes; eligible only ISSUED with actual source-bound store object. A known late returned full snapshot may retain bytes/hash but eligiblefalse and UNKNOWN_RETURN/UNISSUED state; it does not satisfy a gate.',
    gates='Exact ordered prefix of pinned required_gate_order, strings only. Decoder validates spelling/order but cannot mint their source authority.',
    qualification='Seven exactbool fields, each false in encoded format. No caller can set themtrue to issue runtime permission.'
)
contract['value_api_details']=dict(
    call_exact_keys=['ordinal','file_id','api','record_version','flags','requested','buffer_id','phase','generation','buffer_written','scalar_atom','count_atom','error_atom','hashed_contribution','captured_contribution','known_count_contribution','query_offset','query_length','input_handle_atom','pre_dispatch_clock','post_binding_clock','error_id','path_id','fold_state','buffer_state'],
    record_version=1,
    flags='Every named boolean bit supplied as exactbool and cross-validated, clock tags derived from clockatoms; no raw integer flagword in valueAPI.',
    files='Every nonreserved file layout key exactly; enum fields namedstrings, flags closed booldict, expected/actual digests None orbytes32. Optional integer fields None or exactint. No convenience keys.',
    modules='Every nonreserved modulelayout key exactly; flags closed booldict, optional orders/diagnostic None orint. Pools carry names/edges.',
    diagnostics='Every nonreserved diagnosticlayout key exactly; state/severity/phase namedstrings, flags closedbooldict, class_utf8/message_utf8 exact validUTF8 bytes of declaredlength, args_utf8 exact canonicalJSON bytes; zero field padding is encoderderived, not input. clock_bits supplied as clock_atom; clock_tag derived. Optionalrefs None/int.',
    header='The exact keys in api.value_shape.header_keys; enums namedstrings and flags closedbooldict. Clock fields typedatoms; previous_ledger_sha256 bytes32 orNone matching presence flag. Header derived counts/total/sectiondigests not accepted as caller authority.'
)
contract['diagnostics']['operation_debits']='Each source operation has one pre-reserved guard shared by nested helpers. Normal guard exits after postclock/check and any required reconcile/hash/copy step, releasing only unused slots. The source must count actual remaining close/journal/terminal operations; no caller-declared ready/debit flag. If a capacity invariant fails, the original capacity error latches in the protected terminal reserve and future work stops; unattempted optional publication is refused before dispatch. Actual native/physical cleanup behavior remains gated.'
contract['authoring_activity']={'oversized_initial_shell_command':'Windows launcher error206 before process creation; no data or subject read/execution from that attempt. Retained data-author helper writes specification only.','under_test_source_imports':0,'under_test_source_runs':0,'encoder_implementation':False}
contract['live_first_fact']['commit_mechanism']='RawCarrier is a fixed source-owned __slots__ class with ordinary builtin member slots and no custom __setattr__, property/descriptor hook, weakref callback or destructor on the commit fields. The unique global UNOBSERVED sentinel stays strongly referenced. The commit operation is the ordinary member reference assignment, retaining the exact returned object; it does not call a user coercion/encoder or create a tuple/dict/packed record. This is an application-level commit point, not an OS/FFI atomic-return guarantee. Duplicate/conflicting observations are checked only after the first slot is safely present.'
contract['live_first_fact']['first_error']='The first original exception is assigned to the owner primary slot before diagnostics, wrapper-state formatting or other throwable observation work. Source entry barriers consult that canonical slot/accounting-fault reference, not a later serialized stopped flag. Same original object rethrows do not consume another diagnostic. Malformed raw objects remain referenced but can make bounded serialization unavailable, which is an explicit incomplete condition.'
write('ROLE-AWARE-PRODUCER-FORMAT-CONTRACT-v1.json',contract)
