"""Prospective design correction only; no wire/parser/pack/runtime implementation."""
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OLD=HERE/'UNICODE-WIRE-DESIGN-CONTRACT-v1.json'
OUT=HERE/'UNICODE-WIRE-DESIGN-CONTRACT-v2.json'
FREEZE=HERE/'UNICODE-WIRE-DESIGN-FREEZE-v2.json'
SOURCE_METADATA=HERE.parent/'recovery-step9-native-recognition-20261028'/'RECOGNITION-EXECUTION-CONTRACT-v1.json'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(p):
    raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=sha(raw))
def write(p,v):
    with p.open('x',encoding='utf-8') as out:json.dump(v,out,sort_keys=True,indent=2,ensure_ascii=True);out.write('\n')
def main():
    assert not OUT.exists() and not FREEZE.exists(),'Preserve versioned design'
    prior=json.loads(OLD.read_text(encoding='utf-8'));assert pin(OLD)['sha256']=='e7219e813562423ab9b71f39073be486c62ebf8357551f7b79c8956a2ef13302'
    s=copy.deepcopy(prior['semantic_contract'])
    metadata=json.loads(SOURCE_METADATA.read_text(encoding='utf-8'))
    exact_typed={k:metadata[k] for k in ('expected_defaults','expected_layouts','effective_params')}
    assert len(exact_typed['expected_defaults'])==17 and len(exact_typed['effective_params'])==17
    s['framing']['schema_version_note']='Wire version1 remains prospective; v1 proposal was never implemented. This corrected design is separately retained v2.'
    s['framing']['strict_string_identifiers']='Reason/status/event enum tokens use only ASCII letters/digits/underscore, and case/stage IDs use the fixed pack-ID grammar. Free exception text is never an unbounded status/reason.'
    s['wire_size']['JSONL_buckets']['footer']=dict(max_rows=16,bytes_each=8192,maximum_bytes=131072)
    s['wire_size']['footer_pool']='Exactly the frozen per-row bound: <=16 actual footer/global JSONL rows, EACH<=8192 including LF. Failure JSONL is one ofthose rows, not a64KiB pooled exception. Independent failure.json<=65536 is a separate file.'
    s['wire_size']['attempt_scope']='attempt.json<=4096 is a separate file, not an additional JSONL row. Any attempt/failure copied into JSONL consumes an existing setup/footer row with its exact row cap. No277th row.'
    s['wire_size']['failure_JSONL_bytes']=8192
    s['wire_size']['failure_body']='Closed small primary-failure tag/identity plus bounded snapshot and a fixed failure.json filename; large module-rejection diagnostic metadata appears only in the separate<=65536-byte marker.'
    envelope=s['wire_size']['fixed_case_sizing_envelope'];envelope['body']['observation']['native_member']=False
    # Every string in the mathematical envelope has a bounded finite enum/ID spelling;
    # false has5bytes versus null4, and is the independent field-size maximum here.
    fixed=len(canonical(envelope))+1-6
    assert fixed==6408 and fixed+64<=8192
    s['wire_size']['measured_fixed_case_bytes_including_LF_excluding_three_arrays']=fixed
    s['wire_size']['envelope_scope']='Conservative independent field-size maxima with finite identifier/enum spellings, including false rather than null. Mutually inconsistent counter/observation values are permitted only in this mathematical sizing envelope; it is not a valid trace or measured outcome.'
    s['case_row']['observation']='Exact7keys from sizing template. native_member is true for all ordinary admitted+all EOG admitted; false for an ordinary-token rejection or all ordinary admitted+all EOG rejected; null for mixed EOG/unknown observation. Rejection span indexes the retained ORIGINAL ledger. EOG results retain all sorted observed IDs/admitted strictbools whenever the full-token point is reached.'
    s['case_row']['QC']='Token/piece GEOMETRY ONLY: exact status/reason, ok+nullreason, declared harness_ineligible+exactreason, or unknown+finite identifier reason<=64. Ordinary-token rejection, EOG rejection or mixed EOG does not discard a valid ledger or change coverage population/counts. Native ownership/nonreturn/shape faults independently stop further unsafe work.'
    s['case_row']['native_observation_failure']='Mixed EOG is observation.status native_EOG_disagreement, native_member/matches null; retain QCok/fullarrays/geometry if those checks passed. Overall profile fails. Native token rejection is known nativefalse and still retains the full precomputed token/piece ledger.'
    s['coverage']['selected_prefix']='Use ORIGINAL token IDs through the selected piece, including empty tokens. Fresh sampler, no retokenization. Success requires all ordinary prefix tokens admitted then every EOG rejected; ordinary rejection is a failed observed prefix, not an excuse to select another boundary. Geometry selection remains unchanged by all grammar outcomes.'
    s['event_order']['ordinary_failure']='A pre-completion failure prevents a complete-success batch/normal sequence. A later publication/commit/cleanup fault can occur after complete-looking rows; any failure marker, parent failure or missing/failed terminal seal vetoes qualification. Do not rewrite earlier rows.'
    s['event_order']['failure_body_keys']=['primary_failure_id','error_class','reason_code','diagnostic_file','profile_qualification']
    s['event_order']['failure_body']='primary_failure_id is SHA256 of canonical{pid,reason_code,error_class,elapsed_ms,row_sequence_reserved}. error_class/reason_code are finite ASCII enums, diagnostic_file is literal failure.json or null, profile_qualification is literal not_established. Common bounded native snapshot is still present. Max8192 inclLF.'
    s['event_order']['failure_marker']='Separate<=65536 UTF8 JSON object contains the same primary identity and bounded raw module diagnostic when relevant. Failure JSONL is attempted first; marker records its actual reserved/attempted/return/unknown publication outcome and exact row SHA only if fully known. Marker attempt is independent even if JSONL failed. No future marker digest in the earlier row; no hash cycle.'
    keys=s['API_accounting']['names']
    s['framing']['native_state_fields']['last_attempt']=[None]+keys
    s['framing']['native_state_fields']['last_return']=[None]+keys
    def vec(**changes):
        d=dict.fromkeys(keys,0);d.update(changes);return d
    zero=vec();typed=vec(llama_version=1,llama_model_default_params=1)
    cpu=vec(llama_version=1,llama_model_default_params=1,ggml_backend_load=1,
        ggml_backend_dev_count=1,ggml_backend_dev_get=1,ggml_backend_dev_name=1,ggml_backend_dev_type=1,
        ggml_backend_reg_count=1,ggml_backend_reg_dev_count=2,ggml_backend_reg_dev_get=2,ggml_backend_reg_get=1,ggml_backend_reg_name=1)
    backend=vec(llama_version=1,llama_model_default_params=1,llama_backend_init=1,ggml_backend_load=1,
        ggml_backend_dev_count=2,ggml_backend_dev_get=2,ggml_backend_dev_name=2,ggml_backend_dev_type=2,
        ggml_backend_reg_count=2,ggml_backend_reg_dev_count=3,ggml_backend_reg_dev_get=3,ggml_backend_reg_get=2,ggml_backend_reg_name=2)
    vocab=copy.deepcopy(backend);vocab.update(llama_model_load_from_splits=1,llama_model_get_vocab=1,llama_vocab_n_tokens=1,llama_vocab_is_eog='observed vocabulary_count nv')
    def fields(**items):return dict(exact_body_keys=list(items),fields=items)
    policy=dict(module_policy_id=dict(const='trusted-System32-recognition-v1'),module_policy_sha256=dict(const='4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713'),
        module_policy_phase='Expected event-derived pre_cpu or post_cpu constant; parent supplies trusted phase to matcher.',
        modules='Array1..64 exact{name,path} reports; exact pre/post matcher required, no reported-path filesystem operations. Entire serialized setup row<=8192 or explicit row-cap failure.')
    bodies={
        'before_explicit_required_OpenMP_dependency_load':fields(dependency_native_initialization_possible=dict(const=True)),
        'exact_core_modules_loaded_exports_resolved':fields(**policy,layouts=dict(exact_typed_value=exact_typed['expected_layouts'])),
        'typed_version_and_defaults_observed':fields(version=dict(const='0.7.0-dev'),defaults=dict(exact_typed_value=exact_typed['expected_defaults']),no_backend_or_model_call_so_far=dict(const=True)),
        'unicode_pack_verified_before_backend_or_model':fields(pack_sha256='Exact future bound newpack SHA256; lower64hex',wire_semantics_sha256='Exact current semantic fingerprint',corpus_sha256=dict(const=s['corpus']['corpus_sha256']),stages_sha256=dict(const=s['corpus']['stages_sha256']),cases=dict(const=84),stage_instances=dict(const=4),unique_grammars=dict(const=2),coverage_classes=dict(const=4)),
        'before_exact_shard_hash':fields(index='Exact int0,1,2 according to fixed occurrence order',path='Exact known parent-bound descriptor path, not reported platform path',expected_bytes='Exact descriptor byte count, strict uint64'),
        'exact_shard_hash_returned':fields(index='Same fixed index',bytes='Exact descriptor byte count, strictuint64',sha256='Exact descriptor lower64hex'),
        'three_exact_shards_hash_verified_and_read_leased':fields(weight_file_hash_reads=dict(const=True),tensor_weight_allocation_claim=dict(const=False)),
        'cpu_registry_verified_before_llama_backend_init':fields(registry_count=dict(const=1),device_count=dict(const=1),registry_name=dict(const='CPU'),device_name=dict(const='CPU'),**policy),
        'backend_init_returned_exact_CPU_identity_rechecked':fields(**policy),
        'before_model_load_from_three_explicit_splits':fields(effective_params=dict(exact_typed_value=exact_typed['effective_params']),empty_devices_array_nonnull=dict(const=True),cooperative_deadline_not_interruptible_native_call=dict(const=True)),
        'all_vocabulary_ids_EOG_enumerated':fields(vocabulary_count='Strictint nv1..262144',EOG_ids='Sorted unique1..64 strictints0..nv-1, source enumerates EVERY id0..nv-1 exactlyonce',EOG_JSON_sha256='SHA256 of exact compact EOG ID JSON array',**policy)}
    plan=[]
    def add(event,vector,**selectors):plan.append(dict(event=event,body_selectors=selectors,cumulative_attempted_equals_returned=vector))
    add('before_explicit_required_OpenMP_dependency_load',zero)
    add('exact_core_modules_loaded_exports_resolved',zero,module_policy_phase='pre_cpu')
    add('typed_version_and_defaults_observed',typed)
    add('unicode_pack_verified_before_backend_or_model',typed)
    for i in range(3):add('before_exact_shard_hash',typed,index=i);add('exact_shard_hash_returned',typed,index=i)
    add('three_exact_shards_hash_verified_and_read_leased',typed)
    add('cpu_registry_verified_before_llama_backend_init',cpu,module_policy_phase='post_cpu')
    add('backend_init_returned_exact_CPU_identity_rechecked',backend,module_policy_phase='post_cpu')
    add('before_model_load_from_three_explicit_splits',backend)
    add('all_vocabulary_ids_EOG_enumerated',vocab,module_policy_phase='post_cpu')
    assert len(plan)==15 and sum(cpu.values())==14 and sum(backend.values())==24
    s['event_order']['setup_events']=plan
    s['event_order']['setup_body_schemas']=bodies
    del s['event_order']['setup_bodies']
    s['event_order']['setup_scalar_state_rules']={
        'all_setup_rows':'exceptions0; cases computed/written0; both six-stratum arrays all0; selected computed/written0; token_work0; no sampler init/free or ownership.',
        'through_typed_defaults_and_shards':'CPU/backend/model/load/free attempted and returned0; owned/return flagsfalse, coverage_state not_computed.',
        'CPU_before_init':'cpu load return/nonNull true; backend/model ownedfalse, init/load/free counters0. Exact CPU identity2-level source vector above.',
        'backend_returned_and_before_model':'backend init returned/ownedtrue; model load/free counters0 and modelownedfalse.',
        'EOG_enumerated':'model load return/nonNull/modelownedtrue; borrowed vocabulary nonNull; EOG_ids_examined nv, last_EOG_id nv-1, all attempted=returned, coverage_state not_computed.'}
    s['API_accounting']['stage_schedule']='The complete15row cumulative25API vectors above are normative, including every zero. A source claim contradicting its vector rejects even when counters are monotone and under caps. Variable nv is resolved ONLY from the observed vocabulary_count row.'
    s['API_accounting']['per_case_exact_delta']={
        'before_case':'Exact prior cumulative counts; sets current_case_index=i, computed=i/written=i, strata prefix counts from frozen cases0..i-1; no API dispatch yet.',
        'harness_case':'Zero native delta, ledger null, native observation null, exact declared reason. Computed=i+1/written=i at current case row; witness write only later.',
        'QC_ok_tokenizer':'For N>=1, tokenize=1 ifN==1 else2; piece=N+count(piece_byte_length>1) with capacity1 initial call and exactlyone required-size retry. Other capacities/retries are forbidden.',
        'grammar_observation':'Sampler init1 and known once-free1. If first ordinary rejection at r: apply=r+1, accept=r, completion_EOG null. Otherwise apply=N+E,accept=N and exact allEOG vector, including disagreement. No EOG accepts.',
        'QC_unknown':'Retain explicit finite failure/partial known counters, not a successful delta formula or zero. If a critical native return/ownership is unknown, stop further native work and leave tail unknown.',
        'case_snapshot':'Computed increments only when case body computed, before publication; result-written excludes current row. Parent commits its validated counters only after all body/schema/accounting checks pass.'}
    s['API_accounting']['after_cases_and_prefix_exact_delta']={
        'coverage_and_selection':'Zero native delta. All84 case writes witnessed; declared counts/geometry independent of native membership.',
        'prefix':'One new sampler/init/free for each UNIQUEselected pair only; zero tokenize/piece delta. Replay original take_tokens. Apply/accept formula same as document withN=take_tokens; expected result requires all prefix tokens admitted+everyEOGfalse.',
        'cleanup':'After all samplers knownreleased, model_free1 thenbackend_free1; no further version/defaults/registry/vocab/tokenizer/sampler work. Unknown dependencies block unsafe downstream release.',
        'batch':'Exact totalattempts=returns and every per-API value equals setup+all recorded per-case/prefix deltas+cleanup; sampler init/free=78+U only if all documentQCok. Last state no owned/unknown releases, exceptions0.',
        'normal':'No native delta after batch; no new original-input/payload reads by child after its known leases are closed.'}
    s['event_order']['complete_success_row_positions']='Setup rows0..14; before_case15+2i/result16+2i fori0..83; coverage183; selection184; prefix185..184+U; cleanup185+U; batch186+U; normal187+U. Complete row count188+U<=192. Reserved profile envelopes276rows remain unchanged; failure after late publication still consumes an existing footer slot.'
    s['event_order']['typed_constant_rules']='All embedded expected defaults/layout/effective objects compare recursively with EXACT types (bool cannot equal1). Future EXE/pin paths stay unbound; these are typed source expectations, not execution authority.'
    value=dict(schema_version=1,status='CORRECTED_DESIGN_FOR_REVIEW_NO_IMPLEMENTATION_AUTHORITY',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        semantic_contract=s,semantic_sha256=sha(canonical(s)),basis=prior['basis'],preserved_proposal=pin(OLD),author=pin(Path(__file__)),
        correction_basis='Root/OS bounded design batch: fixed per-row footer cap, exactsetup schema/vectors, native outcome vsgeometryQC separation; source/pure design only.',
        source_format_read=dict(path=str(SOURCE_METADATA),fields=list(exact_typed),fresh_original_source_qualification=False,
            CPU_GGUF_oldpack_paths_opened=False,declared_fixed_ABI_acceptance_sha256='024e053664ba45dbda59096ea3a11ab4351fc52fc6f06300af045bc152d2991b'),
        activity=dict(bridge_pack_parent_runtime_implementations=0,target_native_SDK_tokenizer_compiler_calls=0,CPU_GGUF_oldpack_reads=0))
    write(OUT,value)
    record=dict(schema_version=1,status='CORRECTED_DESIGN_FROZEN_FOR_REVIEW_BEFORE_LITERAL_FRAMING_FIXTURES',contract=pin(OUT),author=pin(Path(__file__)),
        semantic_sha256=value['semantic_sha256'],fixed_case_overhead_bytes=fixed,footer_rows_each_max8192=True,implementation_authorized=False,execution_authorized=False)
    write(FREEZE,record);print(json.dumps(dict(contract=pin(OUT),freeze=pin(FREEZE),semantic_sha256=value['semantic_sha256'],fixed_overhead=fixed)))
if __name__=='__main__':main()
