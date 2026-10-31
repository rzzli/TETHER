"""Author DESIGN JSON and sizing evidence only; no pack/bridge/runtime adapter."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
CORPUS=HERE.parent/'recovery-step9-unicode-control-20261029'
OUT=HERE/'UNICODE-WIRE-DESIGN-CONTRACT-v1.json'
RECORD=HERE/'UNICODE-WIRE-DESIGN-FREEZE-v1.json'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def sha(v):return hashlib.sha256(v).hexdigest()
def pin(p):
    raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=sha(raw))
def write(p,v):
    with p.open('x',encoding='utf-8') as out:json.dump(v,out,sort_keys=True,ensure_ascii=True,indent=2);out.write('\n')

def main():
    assert not OUT.exists() and not RECORD.exists(),'Preserve versioned design'
    names=['UNICODE-CONTROL-FIXTURE-FREEZE-v1.json','UNICODE-CONTROL-SCOPED-ACCEPTANCE-v1.json',
        'UNICODE-CONTROL-CONTRACT-v2.json','UNICODE-CONTROL-CORPUS-v1.json','UNICODE-CONTROL-STAGES-v1.json',
        'UNICODE-CONTROL-INDEPENDENT-SEMANTIC-PROOF-v1.json','UNICODE-PIECE-ANALYZER-CONTRACT-v1.json',
        'UNICODE-PIECE-ANALYZER-SCOPED-ACCEPTANCE-v2.json','UNICODE-PIECE-ANALYZER-INDEPENDENT-PEER-v1.json',
        'unicode_piece_analyzer_v1.py']
    basis={name:pin(CORPUS/name) for name in names}
    assert basis[names[0]]['sha256']=='e6e8419c0ad37db007263de0a57e0ce66a20f7481f35686427076ea36c7106b3'
    assert basis['UNICODE-PIECE-ANALYZER-SCOPED-ACCEPTANCE-v2.json']['sha256']=='f895b990247a6c2bfd287c55cdf4015f58f2d995e1dab17d922ff14f5a246140'
    c=json.loads((CORPUS/'UNICODE-CONTROL-CORPUS-v1.json').read_text(encoding='utf-8'))['cases']
    stages=json.loads((CORPUS/'UNICODE-CONTROL-STAGES-v1.json').read_text(encoding='utf-8'))['stages']
    eligible=[x for x in c if x['expected']['native_byte_eligible']]
    assert len(c)==84 and len(stages)==4 and len(eligible)==78 and sum(x['coverage_population'] for x in c)==68
    strata=list(dict.fromkeys(x['stratum'] for x in c));assert len(strata)==6
    grammar_order=list(dict.fromkeys(x['grammar_sha256'] for x in stages));assert len(grammar_order)==2
    api_names=['ggml_backend_dev_count','ggml_backend_dev_get','ggml_backend_dev_name','ggml_backend_dev_type','ggml_backend_load',
        'ggml_backend_reg_count','ggml_backend_reg_dev_count','ggml_backend_reg_dev_get','ggml_backend_reg_get','ggml_backend_reg_name',
        'llama_backend_free','llama_backend_init','llama_model_default_params','llama_model_free','llama_model_get_vocab',
        'llama_model_load_from_splits','llama_sampler_accept','llama_sampler_apply','llama_sampler_free','llama_sampler_init_grammar',
        'llama_token_to_piece','llama_tokenize','llama_version','llama_vocab_is_eog','llama_vocab_n_tokens']
    hard=dict(zip(api_names,[2,2,2,2,1,2,3,3,2,2,1,1,1,1,1,1,1000000,1013184,206,206,2000000,412,1,262144,1]))
    fixed=dict(zip(api_names,[2,2,2,2,1,2,3,3,2,2,1,1,1,1,1,1,69108,74356,82,82,124520,156,1,262144,1]))
    classes=['pending_width2','pending_width3','pending_width4','same_piece_complete_scalar_then_pending']
    booleans=['last_pointer_nonnull','last_apply_return_observed','last_apply_shape_valid','cpu_load_return_observed','cpu_registry_nonnull',
        'backend_init_return_observed','backend_owned','model_load_return_observed','model_return_nonnull','model_owned',
        'model_free_attempted','model_free_return_observed','model_release_unknown','backend_free_attempted','backend_free_return_observed',
        'backend_release_unknown','cleanup_failed','last_EOG_returned','last_EOG_value']
    bounds=dict(total_attempted=[0,4276181],total_returned=[0,4276181],exceptions=[0,4276181],sampler_nonnull_returns=[0,82],
        samplers_owned=[0,82],sampler_release_unknown=[0,82],sampler_free_returned_nonnull=[0,82],token_work_reserved=[0,1000000],
        cases_computed=[0,84],case_results_written=[0,84],selected_prefixes_computed=[0,4],selected_prefix_results_written=[0,4],
        EOG_ids_examined=[0,262144],last_scalar=[-9223372036854775808,9223372036854775807],last_tokenize_return=[-2147483648,2147483647],
        last_piece_return=[-2147483648,2147483647],current_case_index=[-1,83],current_selected_prefix_index=[-1,3],last_EOG_id=[-1,262143],
        last_return_kind=[0,4],last_apply_logit_kind=[0,3])
    state_schema={name:'strict bool' for name in booleans};state_schema.update({name:dict(strict_int_range=value) for name,value in bounds.items()})
    state_schema.update(coverage_state=['not_computed','complete_available','complete_unavailable','unknown'],
        last_attempt=['null']+api_names,last_return=['null']+api_names,stratum_computed='exact six strict uint0..84 values in frozen stratum order',
        stratum_results_written='exact six strict uint0..84 values in frozen stratum order')
    assert len(state_schema)==45
    state_max={name:False for name in booleans}
    state_max.update({name:max(value,key=lambda x:len(str(x))) for name,value in bounds.items()})
    longest_api=max(api_names,key=len)
    state_max.update(coverage_state='complete_unavailable',last_attempt=longest_api,last_return=longest_api,
        stratum_computed=[84]*6,stratum_results_written=[84]*6)
    common=dict(schema_version=1,row_sequence=275,event='unicode_case_result',elapsed_ms=120000,wire_semantics_sha256='f'*64,
        native_call_contract_sha256='30d82a42c5338789644fea00f666e264fb3e4114637c2c37330386a177f17861',
        native_call_counters={k:dict(attempted=v,returned=v) for k,v in hard.items()},native_call_scope='explicit_bridge_export_calls_only',
        unrecorded_killed_tail='unknown_since_last_acknowledged_snapshot',native_state=state_max)
    body_max=dict(case_ordinal=83,case_id='x'*128,stage_instance_id='x'*64,grammar_sha256='f'*64,raw_sha256='f'*64,raw_bytes=1024,
        authored_expected=dict(native_member=False,generation_member=False,semantic_eligible=False,coverage_population=False),
        QC=dict(status='harness_ineligible',reason='x'*64),
        observation=dict(status='native_EOG_disagreement',native_member=None,all_input_tokens_admitted=False,first_rejected_token_index=4127,
            first_rejected_byte_start=1024,first_rejected_byte_end=1024,completion_EOG=[dict(id=262143,admitted=False) for _ in range(64)]),
        ledger=dict(token_ids=[],piece_byte_lengths=[],piece_hex=[]),
        compact_analysis=dict(counts={k:4128 for k in classes},matrix=[[4128]*3 for _ in range(4)],zero_piece_count=4128),
        matches_authored_native_expectation=False)
    max_case=dict(common,body=body_max)
    # A sizing envelope, not a semantically valid counter/state/native fixture.
    fixed_overhead=len(canonical(max_case))+1-6 # exclude the three [] array encodings, include LF
    assert fixed_overhead+64<=8192,'Explicit schema no longer meets frozen fixed-overhead reserve'
    Bsum=sum(x['bytes'] for x in eligible);Nsum=sum(x['prospective_token_cap'] for x in eligible)
    assert Bsum==14941 and Nsum==62260 and sum(fixed.values())==530477 and sum(hard.values())==4276181
    pack_fields=[['magic','8 raw bytes R09NU01 followed by NUL'],['version','u32le exact1'],
        ['wire_semantics_sha256','32 raw digest bytes'],['corpus_sha256','32 raw digest bytes'],['stages_sha256','32 raw digest bytes'],
        ['profile_contract_sha256','32 raw digest bytes'],['analyzer_contract_sha256','32 raw digest bytes'],
        ['stage_count','u32le exact4'],['grammar_count','u32le exact2'],['case_count','u32le exact84'],['class_count','u32le exact4'],
        ['grammars','two records in first frozen-stage hash appearance order'],['stages','four records in frozen stage order'],
        ['cases','84 records in exact frozen ordinal order; no prefix records or runtime-selected subset']]
    semantics=dict(schema_version=1,wire_id='unicode-controls-singleton-wire-v1',profile_id='actual-v3-fullresponse-unicode-controls-v1',
        scope='Distinct model-specific vocabulary/document/EOG observation design. No scientific or full-mask qualification.',
        mode=dict(name='--unicode-controls',argc=9,argv=['EXE','--unicode-controls','RUNTIME_DIRECTORY','EXCLUSIVE_CHILD_OUTPUT','NEW_UNICODE_PACK','PINNED_CPU_BASENAME','SHARD0','SHARD1','SHARD2'],
            expected_llama_version='0.7.0-dev',effective_params='Exact separately bound accepted recognition overrides; vocab_only/no_alloc/load0/lazy0, explicit three shards, no inference context'),
        module_policy=dict(ABI_preserved='807995 semantic boundary unchanged',recognition_id='trusted-System32-recognition-v1',
            recognition_sha256='4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713',
            pre_cpu='self+core4 exactly once; CPU forbidden',post_cpu='self+core4+the one exact eligible pinned CPU exactly once',
            trusted_platform='Lexical metadata context only, never image authenticity or an authority flag. No reported-platform image opens.',
            module_events={'exact_core_modules_loaded_exports_resolved':'pre_cpu','cpu_registry_verified_before_llama_backend_init':'post_cpu',
                'backend_init_returned_exact_CPU_identity_rechecked':'post_cpu','all_vocabulary_ids_EOG_enumerated':'post_cpu','unicode_batch_returned':'post_cpu'}),
        corpus=dict(cases=84,native_byte_eligible=78,harness_ineligible=6,coverage_population=68,authored_native_members=69,authored_native_nonmembers=9,
            stage_instances=4,unique_grammars=2,strata=[dict(name=k,cases=sum(x['stratum']==k for x in c)) for k in strata],
            corpus_sha256=basis['UNICODE-CONTROL-CORPUS-v1.json']['sha256'],stages_sha256=basis['UNICODE-CONTROL-STAGES-v1.json']['sha256'],
            case_order='No reorder/filter/replacement/adaptive corpus. Every authored expectation is retained separately from observed membership/QC.',
            harness='One raw-NUL and five invalid-UTF8 controls: exact declared reason, ledger null/native_member null; zero per-document native calls. No synthetic false membership.'),
        pack=dict(header=pack_fields,integers='Unsigned exact u32 little endian unless specified; reject overflow/truncation/count mismatch before allocation.',
            ID='u32 byte length then ASCII [A-Za-z0-9][A-Za-z0-9_./-]{0,127}; stage IDs length<=64; exact frozen IDs still required.',
            grammar_record=['ID grammar/0 or grammar/1','32-byte grammar SHA256','u32 length1..65536','exact original grammar UTF8 bytes without NUL'],
            stage_record=['ID exact frozen stage ID','32-byte request SHA256','32-byte payload SHA256','u32 grammar index0..1'],
            case_record=['ID','u32 ordinal0..83','u32 stage index0..3','u32 stratum index0..5','32-byte raw SHA256','u32 document length1..1024','exact raw bytes',
                'six u32 ternary expectations in fixed order: project_JSON_parse,Unicode_scalar_JSON,complete_v3_semantic_validation,generation_grammar_membership,native_membership,JSON_syntax; false0,true1,null2',
                'u32 native-byte eligibility false0/true1','u32 harness kind eligible0/invalid_UTF8_1/raw_NUL_2','u32 token cap min65536,4B+32'],
            strictness='Exact frozen raw bytes/stage/grammar/dimensions and complete consumption; no trailing bytes/duplicate IDs. No observed token IDs or selected cuts in pack.',
            maximum_bytes=20971520,exact_future_pack_sha256=None,independent_roundtrip_required=True),
        framing=dict(encoding='Strict scalar UTF8, no BOM; one compact JSON object per ASCII LF. No CRLF/blank/incomplete/duplicate-key/nonfinite rows.',
            ordering='Contiguous exact int row_sequence starts0; no bool counters; closed root/body key sets by event; no ready/verified qualification fields.',
            row_bytes_including_LF=65536,setup_row_bytes_including_LF=8192,maximum_JSONL_bytes=8388608,
            common_row_keys=list(common)+['body'],native_state_fields=state_schema,native_state_count=45,
            snapshot_semantics='Attempted/returned/state captured before post-call checks; current row excludes its own acknowledged-write increment. Next/final row witnesses it; failed/killed tails unknown.'),
        case_row=dict(event='unicode_case_result',body_keys=list(body_max),
            authored_expected='Exact4keys native_member/generation_member/semantic_eligible/coverage_population; first three bool|null, last strictbool; copied frozen values are expectations, never admission.',
            QC='Exact status/reason; status ok with reason null, harness_ineligible with declared reason, or unknown with bounded reason enum<=64 ASCII bytes.',
            observation='Exact7keys shown in sizing template. native_member bool only after known complete observation, else null. Token rejection uses valid first-rejected index/byte span and completion_EOG null; all-token observations retain all sorted EOG IDs/admitted strictbools. Mixed EOG outcomes are QCunknown/native_member null.',
            ledger='Exact three arrays token_ids/piece_byte_lengths/piece_hex; equal N, strict IDs0..nv-1 excluding EOG, canonical lowercase even hex incl empty, lengths match and sum/concat exactly raw. All original empty pieces/indices retained. Null for harness/failedQC; no clipping/repair.',
            compact_analysis='Exact counts4/matrix4x3/zero_piece_count, independently reconstructible from full ledger and frozen raw bytes; all null for declared harness or unexpected QCunknown.',
            matches_authored_native_expectation='Strictbool iff native_member observed bool; otherwise null. Parent recomputes from immutable frozen source, not this field.',
            strict_parent_commit='Commit case/native/harness/stratum validated counters only after complete row schema, reference, accounting and body checks pass.'),
        coverage=dict(analyzer_contract_sha256='05c214f42e9214691b5675cca58e67a6265dd069d2e7829f604df23c7ccca3e6',
            classes=classes,population='Frozen native_byte_eligible AND generation_member AND semantic_eligible; never observed membership/QC as a filter.',
            all_case_ledgers='Eligible nonpopulation cases also retain full arrays and geometry; six declared exclusions have null measurements and known population contribution0 by declaration.',
            compact_summary_keys=['coverage_complete','all_case_QC_complete','counts','matrix','known_counts_lower_bound','known_matrix_lower_bound','unknown_population_ordinals','selectors','selected_prefixes','required_available'],
            geometry='Exact accepted analyzer intervals/matrix units, including wholly-contained complete scalar within same piece; all boundaries reconstructible, not serialized as thousands of objects.',
            whole_corpus='Evaluate all84 once before selection; retain every case outcome and all counts. Safe membership mismatch does not remove it or stop the remaining safe scan.',
            selector='First(case ordinal,original token ordinal) per class across all declared population, class-priority order as above; de-duplicate equal pair, preserve all class references, at most4.',
            unknown='Any population QCunknown makes complete counts/matrix/selectors/selected_prefixes/required_available null; known lower bounds stay distinct. Excluded QCunknown still makes whole profile negative.',
            unavailable='Known count0 -> required_available false; missing any required class fails profile after complete safe data collection. No alternative/adaptive corpus or second tokenization.',
            selected_prefix_body_keys=['selection_index','case_ordinal','token_ordinal','take_tokens','byte_cut','classes','pending_interval','piece_interval','complete_widths','witnesses','prefix_sha256','observation','matches_expected'],
            selected_prefix='Use original token IDs through selected piece, including earlier empty tokens. Fresh sampler, no re-tokenization; all ordinary tokens admitted and every EOG rejected. EOG never accepted. Preserve failed outcome without choosing a replacement.',
            selected_witnesses='Earliest contained scalar interval per distinct width1..4, sorted; classes/witnesses recomputed independently, not trusted child eligibility.'),
        event_order=dict(setup_events=['before_explicit_required_OpenMP_dependency_load','exact_core_modules_loaded_exports_resolved','typed_version_and_defaults_observed',
                'unicode_pack_verified_before_backend_or_model','before_exact_shard_hash[0]','exact_shard_hash_returned[0]',
                'before_exact_shard_hash[1]','exact_shard_hash_returned[1]','before_exact_shard_hash[2]','exact_shard_hash_returned[2]',
                'three_exact_shards_hash_verified_and_read_leased','cpu_registry_verified_before_llama_backend_init',
                'backend_init_returned_exact_CPU_identity_rechecked','before_model_load_from_three_explicit_splits','all_vocabulary_ids_EOG_enumerated'],
            per_case='For each ordinal0..83: unicode_before_case then unicode_case_result. No prefix row interleaving before all84 case results.',
            after_cases=['unicode_coverage_summary','unicode_selection_plan','unicode_selected_prefix_result[0..U-1]','unicode_cleanup_returned','unicode_batch_returned','child_normal_completion'],
            ordinary_failure='One bounded failure row and independent failure marker if writable. No complete batch/normal footer; preceding acknowledged rows remain partial, no retrofit.',
            setup_bodies='Existing typed ABI/layout/default/effective-params/shard/CPU/EOG payload structures are separately source-bound in future implementation; add exact wire/profile/hash/pack/stage metadata only. Their row bytes must fit8192 or explicitly fail without truncation.',
            before_case_body_keys=['case_ordinal','case_id','stage_instance_id','grammar_sha256','raw_sha256','raw_bytes','declared_native_byte_eligible'],
            coverage_body='The exact compact_summary_keys above plus case_counts{expected84,computed84,written84,native78,harness6,population68}; each count exactint and source-linked.',
            selection_plan_body='Exact selectors/selected_prefixes from compact summary; parent recomputes before any selected-prefix acceptance; U exact de-duplicated count0..4.',
            cleanup_body_keys=['sampler_init_returns','sampler_free_returns','samplers_owned','sampler_release_unknown','model_free_return_observed','backend_free_return_observed','cleanup_failed'],
            batch_body_keys=['cases_computed','case_results_written','stratum_computed','stratum_results_written','native_case_results','harness_dispositions','selected_prefixes_computed','selected_prefix_results_written','required_available','all_case_QC_complete','all_expected_membership_outcomes_match','total_token_work_reserved','module_policy_id','module_policy_sha256','module_policy_phase','modules','scientific_validation'],
            batch_success='84/84, six exact strata,78 known membership outcomes and6 exact harness dispositions; required availability/allQC/all matches true; U prefix results pass; all calls returned/no owned or unknown release; cleanup observed. Still observation status only, never scientific/profile authority.',
            normal_completion_body_keys=['status','elapsed_ms'],normal_completion_status='unicode_controls_observations_complete_independent_qualification_pending'),
        API_accounting=dict(scope='Explicit own bridge export calls only, not DLL-internal/OS/GPU/I/O/inference absence.',names=api_names,
            hard_caps=hard,total_hard_attempt_cap=4276181,positive_fixed_profile_upper_bounds=fixed,positive_fixed_profile_upper_sum=530477,
            attempts='Reserve before API entry and token work before loops; count return/ownership/seen results immediately before deadline/logging. Never infer a return or retry a pending creation/free.',
            stage_schedule='Exact source-derived API deltas required at every setup/before-case/result/coverage/prefix/cleanup frame. A typed-version no-backend/model claim requires corresponding counters0, not monotonicity alone.',
            document_tokenizer='At most2calls per78eligible docs; false/false add-special/parse-special. Retry only the initial negative required-size convention, once, within per-case cap; record changed/invalid sizing as unknown QC.',
            pieces='At most2calls per original document token with counted bytes and bounded returned size<=B; no per-prefix piece/tokenizer calls.',
            singleton='Apply to one ordinary candidate then accept only admitted ordinary IDs; stop that sampler at first rejection but retain entire precomputed ledger. If all admitted, query every EOG on unchanged state, never accept EOG.',
            derived_counts='Let D=sum document N, P=sum unique selected take_tokens, A=document+prefix ordinary attempts, R=ordinary accepted, Z=number of samplers reaching all-token completion, E=observed EOGcount. tokenize<=156; piece<=2D; sampler init/free=78+U when allQCgood; accept=R<=D+P; apply=A+Z*E<=D+P+(78+U)*E; EOGenumeration=nv.',
            sampler_expectation='78+U only for complete allQCgood run, U unique selected boundaries<=4. Never copy old190 or treat known unavailable classes as observed prefix rejections.',
            unknown_cleanup='Unknown sampler init/free blocks dependent model/backend cleanup; unknown model load/free blocks backend teardown. Clear actionable owned pointer at once-only release reservation; retain primary+secondary failures. No automatic retry.',
            interrupted_or_deadline='No new work after interruption/work cutoff. Mandatory safe known-owned cleanup may bypass cooperative work tick but stays under external120s/caps; nonreturn/late cleanup veto complete profile.'),
        bounds=dict(profile_cases=96,actual_cases=84,stage_instances=4,unique_grammars=2,document_bytes=1024,actual_max_document_bytes=420,
            per_case_N='min65536,4B+32',maximum_N=4128,actual_max_N=1712,actual_eligible_bytes=Bsum,actual_document_token_cap_sum=Nsum,
            actual_total_token_work_upper=69108,general_total_token_work_upper=412800,hard_token_work_cap=1000000,
            vocabulary=262144,EOG=64,grammar_bytes=65536,pack_bytes=20971520,cooperative_work_ms=117000,parent_child_work_cutoff_seconds=118,
            whole_child_seconds=120,child_cleanup_reserved_seconds=2,owner_seconds=300,final_work_cutoff_seconds=295,owner_finalization_reserved_seconds=5,
            process_and_job_commit_bytes=268435456,active_processes=1,children=1,module_reports=64,stream_bytes_each=65536),
        wire_size=dict(case_arrays='IDs<=7N+1; lengths<=B+2N+1 because positive decimal digits<=length and zero consumesone; hex<=2B+3N+1; total<=12N+3B+3 forN>=1. Null/failedQC rows have bounded overhead only.',
            fixed_case_sizing_envelope=max_case,measured_fixed_case_bytes_including_LF_excluding_three_arrays=fixed_overhead,
            envelope_scope='Field maxima may be mutually inconsistent; this is a conservative byte-size envelope, not a valid native trace or sampled outcome.',
            reserve='Frozen8192 fixed overhead plus64 punctuation/LF margin absorbs the arrays constant3; do not add3 twice.',
            maximum_case_row_bytes=60864,actual_case_bound_bytes=30060,
            JSONL_buckets=dict(before_case=dict(rows=96,bytes_each=8192),case=dict(rows=96,bytes_each=65536),setup=dict(rows=64,bytes_each=8192),selected=dict(rows=4,bytes_each=65536),footer=dict(max_rows=16,pooled_bytes=131072)),
            footer_pool='At most one failure JSONL row<=65536 consumes8 of16 footer byte units; <=8 other footer rows<=8192 fit remaining units. Coverage/selection/cleanup/batch/normal use5 ofthose8. Failure is not an added277th row.',
            maximum_JSONL_rows=276,fixed84_JSONL_rows=252,maximum_reserved_JSONL_bytes=7995392,fixed84_reserved_JSONL_bytes=7110656,
            attempt_file_bytes=4096,failure_marker_file_bytes=65536,structured_all_artifact_reserved_bytes=8065024,structured_all_artifact_ceiling=8388608,
            attempt_scope='attempt.json is a separate file, not an extra JSONL row. Any attempt event copied into JSONL consumes an allocated setup/footer row. Independent failure marker may mirror the bounded failure row.',
            row_admission='Compute exact serialized bytes/caps and reserve before writing; no clipping, token dropping or favorable omission. Module/report failure metadata must fit its explicit bucket or fail with bounded marker; no universal path-size fit claim.'),
        parent_verifier=dict(execute_signature='execute(config,protocol_sha256,*,owner_started=trusted_original_start)',
            role_binding='Acyclic exact software static roster+4dynamic source/evidence records+5payload descriptors(CPU,threeGGUF,newpack), disjoint canonical path roles before reads. No inherited oldEXE or current-proof cycles.',
            preparation='Metadata/software-only bounded60s; zero payload stat/lstat/open/hash or constructors. Exact future pack/build/EXE and authority remain unbound here.',
            runtime='Single first owner clock before driver/helper import/validation/hash; live original-path leases and source-inclusive initial/child/final whole-shard hashing still mandatory. Final bulk hashing ends by owner_end-5.',
            immutable_source='Use owner-local captured bytes/live leases/source-map context, never serialized already_verified flags or cross-run caches.',
            strict_result='Recompute every row/source binding/stage schedule, all case body checks before acceptance counters, pure analyzer geometry/globalselectors and all selected-prefix outcomes; no five-rowABI success route.',
            gate_separation='New versioned captured-byte archive/journal/resource/case checker required. Generic chain-only pass and earlier known-launched v7 policy are not this new Unicode policy.',
            terminal='Required post-original-lease cleanup artifact and terminal seal bind earlier receipts/primary+late errors; missing seal/unknown outcome/incomplete stage is unqualified. Source negative stays negative.',
            future_positive_status='unicode_controls_observations_retained_independent_qualification_pending',
            owner_budget='No timing fit inferred from smaller corpus or static calls. Whole independent verification has its own single300s incl imports/preflight/finalseal; no merge of postdeadline checks.',
            forbidden='No second census/OS tracing, old189 repair/replay, full-vocabulary mask, model inference/context/server, extra corpus/tokenization search or scientific/human acceptance.'),
        review_gates=['Review this exact design/schema/arithmetic before any bridge/pack/parent implementation',
            'Literal new pack/row/partial/failure fixtures before adapters; exact stage-delta and max-overhead source/pure regressions',
            'Separately bound C++/header/pack/source ports/parent/real checker origin and resource proofs; source-only does not qualify platform APIs',
            'Independent compiler-only build verification, metadata-only acyclic preparation, exact peer/root decision before any payload or target run'],
        execution_authorized=False,original_profile='FAILED/consumed unchanged',old_external_verification='INCOMPLETE_TIMEOUT unchanged',scientific_validation='not_established')
    value=dict(schema_version=1,status='FROZEN_DESIGN_FOR_REVIEW_NOT_IMPLEMENTATION_AUTHORITY',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        semantic_contract=semantics,semantic_sha256=sha(canonical(semantics)),basis=basis,
        source_format_reads=['Retained recognition child/header/wire text for25export names/caps, size conventions and singleton observation structure only. No original source graph qualification or input hash pass.'],
        activity=dict(new_metadata_reads_only=True,CPU_GGUF_oldpack_reads=0,target_native_SDK_tokenizer_compiler_calls=0,
            bridge_pack_parent_runtime_implementations=0,old_profile_edits_or_retries=0),author=pin(Path(__file__)))
    write(OUT,value)
    freeze=dict(schema_version=1,status='DESIGN_AND_ROW_SIZE_ENVELOPE_FROZEN_FOR_ROOT_AND_INDEPENDENT_REVIEW',
        contract=pin(OUT),author=pin(Path(__file__)),semantic_sha256=value['semantic_sha256'],
        fixed_case_overhead_bytes=fixed_overhead,maximum_case_bytes=60864,maximum_reserved_all_structured_bytes=8065024,
        source_pure_only=True,execution_authorized=False,implementation_authorized=False)
    write(RECORD,freeze);print(json.dumps(dict(contract=pin(OUT),freeze=pin(RECORD),semantic_sha256=value['semantic_sha256'],fixed_overhead=fixed_overhead)))
if __name__=='__main__':main()
