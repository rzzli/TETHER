"""Author only the normative framing closure; no parser/runtime implementation."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE/'UNICODE-WIRE-DESIGN-CONTRACT-v2.json'
OUT=HERE/'UNICODE-WIRE-FRAMING-CONTRACT-v1.json'
FREEZE=HERE/'UNICODE-WIRE-FRAMING-CONTRACT-FREEZE-v1.json'
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def pin(p):
    raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(p,v):
    with p.open('x',encoding='utf-8') as out:json.dump(v,out,sort_keys=True,indent=2);out.write('\n')
def main():
    assert not OUT.exists() and not FREEZE.exists(),'Preserve framing closure'
    d=json.loads(BASE.read_text(encoding='utf-8'));assert pin(BASE)['sha256']=='ddf9fd360d72def0b91bd99b047422bf8ee623c0f8d6e0ba73535e04a7af1abc'
    statuses=['native_member','native_token_rejection','native_eog_rejection','native_EOG_disagreement',
        'not_attempted_QC_unknown','harness_raw_nul_rejection','harness_utf8_rejection']
    reasons=['mode_argv_invalid','pin_header_ineligible','version_or_defaults_mismatch','export_resolution_failed',
        'module_policy_rejected','platform_metadata_incomplete','payload_descriptor_mismatch','payload_hash_or_lease_failed',
        'pack_framing_or_binding_failed','native_call_budget_exceeded','token_work_budget_exceeded','cooperative_deadline_expired',
        'native_call_exception','native_return_or_shape_invalid','native_ownership_or_cleanup_unknown','sampler_or_model_null_return',
        'native_cleanup_failed','document_QC_unknown','case_expectation_mismatch','required_coverage_unavailable','required_coverage_unknown',
        'analyzer_or_selector_disagreement','selected_prefix_observation_failed','row_or_artifact_cap_exceeded','output_publication_failed',
        'output_commit_failed','unicode_batch_accounting_incomplete','bridge_invariant_failed','nonprotocol_cpp_exception','unknown_cpp_exception']
    qc_reasons=['raw_NUL','raw_utf8','ledger_schema','ledger_arrays','ledger_lengths','token_cap','token_id','ordinary_EOG','piece_length','piece_hex','roundtrip',
        'missing_ledger','harness_ledger_present','tokenize_size_invalid','tokenize_size_changed','piece_size_invalid','piece_size_changed']
    seven=['status','native_member','all_input_tokens_admitted','first_rejected_token_index','first_rejected_byte_start','first_rejected_byte_end','completion_EOG']
    f=dict(schema_version=1,framing_id='unicode-controls-closed-framing-v1',
        profile_binding=dict(profile_id='actual-v3-fullresponse-unicode-controls-v1',cases=84,native_byte_eligible=78,harness_ineligible=6,population=68,
            corpus_sha256='13e2c2f2900802729c0d39fa9b7851c56ab3db6afdc45c4b15c2f7f80bd6523c',
            population_rule='Exact frozen native-byte-eligible AND authored generation-member AND semantic-eligible. No observed native outcome/QC may filter or replace it.'),
        observation=dict(exact_keys=seven,status_enum=statuses,ordinary_membership_union={
            'native_member':dict(native_member=True,all_input_tokens_admitted=True,rejection_fields=None,EOG='All observed sorted EOG IDs exactlyonce, every admittedTrue'),
            'native_token_rejection':dict(native_member=False,all_input_tokens_admitted=False,rejection_fields='Strict original token ordinalr and exact cumulative original piece interval, including allowed zero-length interval',EOG=None),
            'native_eog_rejection':dict(native_member=False,all_input_tokens_admitted=True,rejection_fields=None,EOG='Every observed EOG exactlyonce, every admittedFalse'),
            'native_EOG_disagreement':dict(native_member=None,all_input_tokens_admitted=True,rejection_fields=None,EOG='Every observed EOG exactlyonce, at leastoneTrue and at leastoneFalse')},
            native_token_rejection_does_not_drop_ledger=True,EOG_disagreement_does_not_change_geometry=True,
            native_null_is_not_false=True,all_union_fields_are_exact_types=True,
            not_attempted_QC_unknown='Wrapper is PRESENT with all seven keys; status not_attempted_QC_unknown, other6values JSONnull. No sampler call for that document; prior known tokenizer/piece work remains counted. QCunknown is not a declared harness exclusion.'),
        harness=dict(observation_wrapper='Always the exact seven-key OBJECT, never observation:null. Only native_member and other six nonstatus observation fields are null; status is the exact declared guard reason.',
            exact_observation=dict(status='harness_raw_nul_rejection OR harness_utf8_rejection',native_member=None,all_input_tokens_admitted=None,
                first_rejected_token_index=None,first_rejected_byte_start=None,first_rejected_byte_end=None,completion_EOG=None),
            case_shape='QC exact{status:harness_ineligible,reason:same guard status}; ledger:null; compact_analysis PRESENT exact{counts:null,matrix:null,zero_piece_count:null}; matches_authored_native_expectation:null; authored native_member:null.',
            calls='Zero per-document tokenizer/piece/sampler/apply/accept calls; common setup calls are not falsely reported as zero.',
            analyzer_mapping='The accepted analyzer calls this harness_ineligible/harness_declared when its ledger isNone. The native guard reason remains separately retained; do not require its reason string to equal analyzer harness_declared.',
            counts='Six declared exclusions have known population contribution0 by frozen declaration, not observed boundary absence. Unexpected QCunknown never changes native-byte eligibility or becomes a seventh harness exclusion.'),
        QC=dict(status_enum=['ok','harness_ineligible','unknown'],ok_reason=None,harness_reason_enum=['harness_raw_nul_rejection','harness_utf8_rejection'],
            unknown_reason_enum=qc_reasons,geometry_only=True,
            unknown_shape='QCunknown keeps ledger:null, compact_analysis exact3keys allnull, observation status not_attempted_QC_unknown and other6fieldsnull, matches:null. An already valid ledger/geometry is NEVER nulled by token/EOG membership failure.',
            reason_scope='A native QCunknown reason describes the bounded source observation; the pure analyzer supplied ledgerNone reports missing_ledger. Parent retains the original reason and compares null measurement semantics, not invented reason equivalence.',
            overall='Any unexpected QCunknown or ambiguous native outcome makes the whole profile unqualified even if all required geometry classes are knownavailable.'),
        failure=dict(child_error_class_enum=['BridgeError','StandardException','UnknownException'],reason_code_enum=reasons,
            enum_grammar='Exact listed ASCII identifiers only; no arbitrary exception/document/piece text in JSONL or stdout. Std exception=>StandardException/nonprotocol_cpp_exception; catchall=>UnknownException/unknown_cpp_exception. Unclassified bridge invariant=>BridgeError/bridge_invariant_failed.',
            JSONL_exact_body_keys=['primary_failure_id','error_class','reason_code','diagnostic_file','profile_qualification'],
            diagnostic_file_enum=[None,'failure.json'],profile_qualification='not_established',JSONL_bytes_including_LF=8192,
            primary_failure_id='SHA256(canonical{pid,error_class,reason_code,elapsed_ms,row_sequence_reserved}); pid binds the captured child/attempt. Intended failure sequence is known even when publication outcome is unknown.',
            marker='Separate failure.json<=65536; mandatory failure veto if present. Common bounded native snapshot plus schema_version/statusfailed/profile_id/pid/elapsed_ms/row_sequence_reserved/primary_failure_id/error_class/reason_code/failure_row_publication/diagnostic; no event/body/row_sequence successful-row impersonation.',
            publication_exact_keys=['attempt_reserved','write_attempted','return_observed','known_bytes','sha256','error_class'],
            publication='Three flags strictbool; known_bytes strict uint0..8192 ornull; sha256 lower64hex onlyafter entire exact row+LF knownwritten; otherwise null. error_class null or oneof child_error_class_enum. Returned publication implies attempted+reserved; a pending write is unknown, never zero bytes received.',
            diagnostic='Exact{kind,value}. kind none=>value null; module_policy_rejection=>the separately retained bounded numeric-UTF16/raw/report metadata schema, same primaryfailure. Metadata is reported/lexical context only, no filesystem/image authenticity. If it cannot fit64KiB, retain bounded primary/no-diagnostic marker rather than clip into a complete diagnostic.',
            order='Try the bounded JSONLfailure row once, then independently try marker even if rowpublication failed; marker records the observed rowoutcome. Earlier row never hashes a future marker, preventing cycles.',
            stdout='Fixed bounded class/reason/primaryfailureID only; no large module diagnostic copied to stdout. Stream caps remain65536.',
            parent_scope='These enums describe CHILD wire only. Parent keeps its separately reviewed primary/secondary Python error and interruption identities; this contract never relabels or suppresses them.'),
        partial_history=dict(scope='All scenarios below are literal synthetic framing/history expectations, not observations or a complete native run. Full profile acceptance isfalse for every isolated fragment/history.',
            EOF='Strict UTF8 and final ASCII LF required to accept any complete row; a truncated final row is a retained unknown tail, not an ignored successful footer.',
            native_tail='Attempted-minus-returned and work after last acknowledged snapshot remain unknown. No inferred return, retry, automatic release of an unknown pointer or no-calls claim from absent rows.',
            declared_population_unchanged=True,history_expectations=[
                dict(id='no_capture',validated_case_rows=0,measured_global_counts=None,tail='unknown',profile_qualified=False),
                dict(id='typed_setup_prefix_only',validated_case_rows=0,known_setup_vectors='Exact captured15-stage prefix only',future_calls='unknown after last acknowledged snapshot',profile_qualified=False),
                dict(id='before_case_without_result',validated_case_rows=0,source_computed_at_last_snapshot=0,current_case_outcome=None,remaining_cases='unknown',profile_qualified=False),
                dict(id='first_result_write_lag',validated_case_rows=1,source_computed_at_row=1,source_written_at_row=0,current_row_write_increment='not witnessed until later snapshot',global_counts=None,profile_qualified=False),
                dict(id='next_before_case_witness',validated_case_rows=1,source_computed_at_row=1,source_written_at_row=1,remaining_cases='unknown',profile_qualified=False),
                dict(id='known_member_mismatch',validated_geometry_case_rows=1,native_member=False,matches=False,geometry='retained',population='still declared',profile_qualified=False),
                dict(id='mixed_EOG_known_geometry',validated_geometry_case_rows=1,native_member=None,matches=None,geometry='retained',population='still declared',profile_qualified=False),
                dict(id='pending_sampler_creation',sampler_init_attempted=1,sampler_init_returned=0,owned_pointer='unknown not guessedNone',dependent_model_backend_release='blocked',profile_qualified=False),
                dict(id='pending_model_release',model_free_attempted=1,model_free_returned=0,model_release_unknown=True,backend_free_attempted=0,profile_qualified=False),
                dict(id='known_required_class_zero',coverage_complete=True,required_available=False,selectors='null onlyfor knownzero class, other firstboundaries unchanged',replace_or_search=False,profile_qualified=False),
                dict(id='population_geometry_unknown',coverage_complete=False,counts=None,matrix=None,selectors=None,selected_prefixes=None,required_available=None,known_lower_bounds='retained separately',profile_qualified=False),
                dict(id='wrong_case_body_after_good_snapshot',validated_case_rows=0,validated_native_rows=0,validated_harness_rows=0,source_computed_instrumentation=1,profile_qualified=False),
                dict(id='complete_rows_then_marker',child_rows='may look complete',failure_marker=True,profile_qualified=False),
                dict(id='complete_child_without_owner_gates',child_rows='may be complete',owner_or_external_qualification='not established',profile_qualified=False)]),
        scope_and_caps=dict(fragment_types=['fixed_header','grammar_record','stage_record','case_record','ID'],complete_profile_packs=0,
            synthetic_rows='Datatype/byte/geometry examples may lack their setup prefix or use independent fieldmaxima. Label that scope; never count them as an actual successful native history.',
            positive_complete_rows='188+U<=192 under the base design, U<=4 unique selections; reserved envelope276 unchanged.',
            rowcaps='Each footer/global JSONL row<=8192 inclLF, each case/selected<=65536;16footer rows, no pooled-row exception. attemptfile4096/failurefile65536 are separate files; JSONL7995392/allstructured8065024 reservations unchanged.',
            raw_document_population='All84 frozen rows remain, including78eligible/6declaredharness and68fixedpopulation; no token IDs or native outcomes used to author corpus, classes or selection rule.',
            implementation_authorized=False,execution_authorized=False,scientific_validation='not_established'))
    payload=dict(base_design_semantic_sha256=d['semantic_sha256'],framing_semantics=f)
    value=dict(schema_version=1,status='NORMATIVE_FRAMING_CLOSURE_BEFORE_LITERAL_FIXTURES_AND_ANY_IMPLEMENTATION',
        recorded_at_utc=datetime.now(timezone.utc).isoformat(),base_design=pin(BASE),base_design_semantic_sha256=d['semantic_sha256'],
        framing_semantics=f,effective_wire_semantics_sha256=hashlib.sha256(canonical(payload)).hexdigest(),
        fingerprint_rule='SHA256(canonical{base_design_semantic_sha256,framing_semantics}) with sorted compact ensure_asciiFalse UTF8/no nonfinite. Excludes author/time/future code/proof/build/pack hashes.',
        fingerprint_usage='This EFFECTIVE fingerprint replaces the base-only placeholder at every future packheader/row/headerdescriptor wire_semantics_sha256 site. Both preserved contracts remain exact review inputs; no future current-code/proof cycle.',
        author=pin(Path(__file__)),activity=dict(new_metadata_only=True,target_native_SDK_compiler_tokenizer_calls=0,CPU_GGUF_oldpack_operations=0,
            full_profile_pack_builder_or_bridge_decoder_parent_runtime_implementations=0))
    write(OUT,value)
    write(FREEZE,dict(schema_version=1,status='NORMATIVE_CLOSURE_FROZEN_BEFORE_LITERAL_FRAMING_AUTHOR_RUN',contract=pin(OUT),author=pin(Path(__file__)),
        effective_wire_semantics_sha256=value['effective_wire_semantics_sha256'],observation_statuses=len(statuses),child_failure_reasons=len(reasons),partial_history_scenarios=14,
        implementation_authorized=False,execution_authorized=False))
    print(json.dumps(dict(contract=pin(OUT),freeze=pin(FREEZE),effective_wire_semantics_sha256=value['effective_wire_semantics_sha256'])))
if __name__=='__main__':main()
