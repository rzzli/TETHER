"""Fixed immutable captured-source format tables; no filesystem/runtime authority."""
from types import MappingProxyType

def _freeze(value):
    if type(value) is dict: return MappingProxyType({key:_freeze(item) for key,item in value.items()})
    if type(value) is list: return tuple(_freeze(item) for item in value)
    return value

SOURCE_PINS = ('ddf9fd360d72def0b91bd99b047422bf8ee623c0f8d6e0ba73535e04a7af1abc', '4c4645f53c878e03cf1f0eaec575b3dcf1dcc006375aadc0080819393e4c3d24', 'edacdc2bddbceab5735699ee9d973f89bad46b64713b193fe43ab80ed989101f')
TABLES = _freeze({'API_accounting': {'after_cases_and_prefix_exact_delta': {'batch': 'Exact totalattempts=returns and every per-API '
                                                                    'value equals setup+all recorded per-case/prefix '
                                                                    'deltas+cleanup; sampler init/free=78+U only if '
                                                                    'all documentQCok. Last state no owned/unknown '
                                                                    'releases, exceptions0.',
                                                           'cleanup': 'After all samplers knownreleased, model_free1 '
                                                                      'thenbackend_free1; no further '
                                                                      'version/defaults/registry/vocab/tokenizer/sampler '
                                                                      'work. Unknown dependencies block unsafe '
                                                                      'downstream release.',
                                                           'coverage_and_selection': 'Zero native delta. All84 case '
                                                                                     'writes witnessed; declared '
                                                                                     'counts/geometry independent of '
                                                                                     'native membership.',
                                                           'normal': 'No native delta after batch; no new '
                                                                     'original-input/payload reads by child after its '
                                                                     'known leases are closed.',
                                                           'prefix': 'One new sampler/init/free for each '
                                                                     'UNIQUEselected pair only; zero tokenize/piece '
                                                                     'delta. Replay original take_tokens. Apply/accept '
                                                                     'formula same as document withN=take_tokens; '
                                                                     'expected result requires all prefix tokens '
                                                                     'admitted+everyEOGfalse.'},
                    'attempts': 'Reserve before API entry and token work before loops; count return/ownership/seen '
                                'results immediately before deadline/logging. Never infer a return or retry a pending '
                                'creation/free.',
                    'derived_counts': 'Let D=sum document N, P=sum unique selected take_tokens, A=document+prefix '
                                      'ordinary attempts, R=ordinary accepted, Z=number of samplers reaching all-token '
                                      'completion, E=observed EOGcount. tokenize<=156; piece<=2D; sampler '
                                      'init/free=78+U when allQCgood; accept=R<=D+P; apply=A+Z*E<=D+P+(78+U)*E; '
                                      'EOGenumeration=nv.',
                    'document_tokenizer': 'At most2calls per78eligible docs; false/false add-special/parse-special. '
                                          'Retry only the initial negative required-size convention, once, within '
                                          'per-case cap; record changed/invalid sizing as unknown QC.',
                    'hard_caps': {'ggml_backend_dev_count': 2,
                                  'ggml_backend_dev_get': 2,
                                  'ggml_backend_dev_name': 2,
                                  'ggml_backend_dev_type': 2,
                                  'ggml_backend_load': 1,
                                  'ggml_backend_reg_count': 2,
                                  'ggml_backend_reg_dev_count': 3,
                                  'ggml_backend_reg_dev_get': 3,
                                  'ggml_backend_reg_get': 2,
                                  'ggml_backend_reg_name': 2,
                                  'llama_backend_free': 1,
                                  'llama_backend_init': 1,
                                  'llama_model_default_params': 1,
                                  'llama_model_free': 1,
                                  'llama_model_get_vocab': 1,
                                  'llama_model_load_from_splits': 1,
                                  'llama_sampler_accept': 1000000,
                                  'llama_sampler_apply': 1013184,
                                  'llama_sampler_free': 206,
                                  'llama_sampler_init_grammar': 206,
                                  'llama_token_to_piece': 2000000,
                                  'llama_tokenize': 412,
                                  'llama_version': 1,
                                  'llama_vocab_is_eog': 262144,
                                  'llama_vocab_n_tokens': 1},
                    'interrupted_or_deadline': 'No new work after interruption/work cutoff. Mandatory safe known-owned '
                                               'cleanup may bypass cooperative work tick but stays under '
                                               'external120s/caps; nonreturn/late cleanup veto complete profile.',
                    'names': ['ggml_backend_dev_count',
                              'ggml_backend_dev_get',
                              'ggml_backend_dev_name',
                              'ggml_backend_dev_type',
                              'ggml_backend_load',
                              'ggml_backend_reg_count',
                              'ggml_backend_reg_dev_count',
                              'ggml_backend_reg_dev_get',
                              'ggml_backend_reg_get',
                              'ggml_backend_reg_name',
                              'llama_backend_free',
                              'llama_backend_init',
                              'llama_model_default_params',
                              'llama_model_free',
                              'llama_model_get_vocab',
                              'llama_model_load_from_splits',
                              'llama_sampler_accept',
                              'llama_sampler_apply',
                              'llama_sampler_free',
                              'llama_sampler_init_grammar',
                              'llama_token_to_piece',
                              'llama_tokenize',
                              'llama_version',
                              'llama_vocab_is_eog',
                              'llama_vocab_n_tokens'],
                    'per_case_exact_delta': {'QC_ok_tokenizer': 'For N>=1, tokenize=1 ifN==1 else2; '
                                                                'piece=N+count(piece_byte_length>1) with capacity1 '
                                                                'initial call and exactlyone required-size retry. '
                                                                'Other capacities/retries are forbidden.',
                                             'QC_unknown': 'Retain explicit finite failure/partial known counters, not '
                                                           'a successful delta formula or zero. If a critical native '
                                                           'return/ownership is unknown, stop further native work and '
                                                           'leave tail unknown.',
                                             'before_case': 'Exact prior cumulative counts; sets current_case_index=i, '
                                                            'computed=i/written=i, strata prefix counts from frozen '
                                                            'cases0..i-1; no API dispatch yet.',
                                             'case_snapshot': 'Computed increments only when case body computed, '
                                                              'before publication; result-written excludes current '
                                                              'row. Parent commits its validated counters only after '
                                                              'all body/schema/accounting checks pass.',
                                             'grammar_observation': 'Sampler init1 and known once-free1. If first '
                                                                    'ordinary rejection at r: apply=r+1, accept=r, '
                                                                    'completion_EOG null. Otherwise apply=N+E,accept=N '
                                                                    'and exact allEOG vector, including disagreement. '
                                                                    'No EOG accepts.',
                                             'harness_case': 'Zero native delta, ledger null, native observation null, '
                                                             'exact declared reason. Computed=i+1/written=i at current '
                                                             'case row; witness write only later.'},
                    'pieces': 'At most2calls per original document token with counted bytes and bounded returned '
                              'size<=B; no per-prefix piece/tokenizer calls.',
                    'positive_fixed_profile_upper_bounds': {'ggml_backend_dev_count': 2,
                                                            'ggml_backend_dev_get': 2,
                                                            'ggml_backend_dev_name': 2,
                                                            'ggml_backend_dev_type': 2,
                                                            'ggml_backend_load': 1,
                                                            'ggml_backend_reg_count': 2,
                                                            'ggml_backend_reg_dev_count': 3,
                                                            'ggml_backend_reg_dev_get': 3,
                                                            'ggml_backend_reg_get': 2,
                                                            'ggml_backend_reg_name': 2,
                                                            'llama_backend_free': 1,
                                                            'llama_backend_init': 1,
                                                            'llama_model_default_params': 1,
                                                            'llama_model_free': 1,
                                                            'llama_model_get_vocab': 1,
                                                            'llama_model_load_from_splits': 1,
                                                            'llama_sampler_accept': 69108,
                                                            'llama_sampler_apply': 74356,
                                                            'llama_sampler_free': 82,
                                                            'llama_sampler_init_grammar': 82,
                                                            'llama_token_to_piece': 124520,
                                                            'llama_tokenize': 156,
                                                            'llama_version': 1,
                                                            'llama_vocab_is_eog': 262144,
                                                            'llama_vocab_n_tokens': 1},
                    'positive_fixed_profile_upper_sum': 530477,
                    'sampler_expectation': '78+U only for complete allQCgood run, U unique selected boundaries<=4. '
                                           'Never copy old190 or treat known unavailable classes as observed prefix '
                                           'rejections.',
                    'scope': 'Explicit own bridge export calls only, not DLL-internal/OS/GPU/I/O/inference absence.',
                    'singleton': 'Apply to one ordinary candidate then accept only admitted ordinary IDs; stop that '
                                 'sampler at first rejection but retain entire precomputed ledger. If all admitted, '
                                 'query every EOG on unchanged state, never accept EOG.',
                    'stage_schedule': 'The complete15row cumulative25API vectors above are normative, including every '
                                      'zero. A source claim contradicting its vector rejects even when counters are '
                                      'monotone and under caps. Variable nv is resolved ONLY from the observed '
                                      'vocabulary_count row.',
                    'total_hard_attempt_cap': 4276181,
                    'unknown_cleanup': 'Unknown sampler init/free blocks dependent model/backend cleanup; unknown '
                                       'model load/free blocks backend teardown. Clear actionable owned pointer at '
                                       'once-only release reservation; retain primary+secondary failures. No automatic '
                                       'retry.'},
 'bounds': {'EOG': 64,
            'active_processes': 1,
            'actual_cases': 84,
            'actual_document_token_cap_sum': 62260,
            'actual_eligible_bytes': 14941,
            'actual_max_N': 1712,
            'actual_max_document_bytes': 420,
            'actual_total_token_work_upper': 69108,
            'child_cleanup_reserved_seconds': 2,
            'children': 1,
            'cooperative_work_ms': 117000,
            'document_bytes': 1024,
            'final_work_cutoff_seconds': 295,
            'general_total_token_work_upper': 412800,
            'grammar_bytes': 65536,
            'hard_token_work_cap': 1000000,
            'maximum_N': 4128,
            'module_reports': 64,
            'owner_finalization_reserved_seconds': 5,
            'owner_seconds': 300,
            'pack_bytes': 20971520,
            'parent_child_work_cutoff_seconds': 118,
            'per_case_N': 'min65536,4B+32',
            'process_and_job_commit_bytes': 268435456,
            'profile_cases': 96,
            'stage_instances': 4,
            'stream_bytes_each': 65536,
            'unique_grammars': 2,
            'vocabulary': 262144,
            'whole_child_seconds': 120},
 'case_row': {'QC': 'Token/piece GEOMETRY ONLY: exact status/reason, ok+nullreason, declared '
                    'harness_ineligible+exactreason, or unknown+finite identifier reason<=64. Ordinary-token '
                    'rejection, EOG rejection or mixed EOG does not discard a valid ledger or change coverage '
                    'population/counts. Native ownership/nonreturn/shape faults independently stop further unsafe '
                    'work.',
              'authored_expected': 'Exact4keys native_member/generation_member/semantic_eligible/coverage_population; '
                                   'first three bool|null, last strictbool; copied frozen values are expectations, '
                                   'never admission.',
              'body_keys': ['case_ordinal',
                            'case_id',
                            'stage_instance_id',
                            'grammar_sha256',
                            'raw_sha256',
                            'raw_bytes',
                            'authored_expected',
                            'QC',
                            'observation',
                            'ledger',
                            'compact_analysis',
                            'matches_authored_native_expectation'],
              'compact_analysis': 'Exact counts4/matrix4x3/zero_piece_count, independently reconstructible from full '
                                  'ledger and frozen raw bytes; all null for declared harness or unexpected QCunknown.',
              'event': 'unicode_case_result',
              'ledger': 'Exact three arrays token_ids/piece_byte_lengths/piece_hex; equal N, strict IDs0..nv-1 '
                        'excluding EOG, canonical lowercase even hex incl empty, lengths match and sum/concat exactly '
                        'raw. All original empty pieces/indices retained. Null for harness/failedQC; no '
                        'clipping/repair.',
              'matches_authored_native_expectation': 'Strictbool iff native_member observed bool; otherwise null. '
                                                     'Parent recomputes from immutable frozen source, not this field.',
              'native_observation_failure': 'Mixed EOG is observation.status native_EOG_disagreement, '
                                            'native_member/matches null; retain QCok/fullarrays/geometry if those '
                                            'checks passed. Overall profile fails. Native token rejection is known '
                                            'nativefalse and still retains the full precomputed token/piece ledger.',
              'observation': 'Exact7keys from sizing template. native_member is true for all ordinary admitted+all EOG '
                             'admitted; false for an ordinary-token rejection or all ordinary admitted+all EOG '
                             'rejected; null for mixed EOG/unknown observation. Rejection span indexes the retained '
                             'ORIGINAL ledger. EOG results retain all sorted observed IDs/admitted strictbools '
                             'whenever the full-token point is reached.',
              'strict_parent_commit': 'Commit case/native/harness/stratum validated counters only after complete row '
                                      'schema, reference, accounting and body checks pass.'},
 'closure': {'QC': {'geometry_only': True,
                    'harness_reason_enum': ['harness_raw_nul_rejection', 'harness_utf8_rejection'],
                    'ok_reason': None,
                    'overall': 'Any unexpected QCunknown or ambiguous native outcome makes the whole profile '
                               'unqualified even if all required geometry classes are knownavailable.',
                    'reason_scope': 'A native QCunknown reason describes the bounded source observation; the pure '
                                    'analyzer supplied ledgerNone reports missing_ledger. Parent retains the original '
                                    'reason and compares null measurement semantics, not invented reason equivalence.',
                    'status_enum': ['ok', 'harness_ineligible', 'unknown'],
                    'unknown_reason_enum': ['raw_NUL',
                                            'raw_utf8',
                                            'ledger_schema',
                                            'ledger_arrays',
                                            'ledger_lengths',
                                            'token_cap',
                                            'token_id',
                                            'ordinary_EOG',
                                            'piece_length',
                                            'piece_hex',
                                            'roundtrip',
                                            'missing_ledger',
                                            'harness_ledger_present',
                                            'tokenize_size_invalid',
                                            'tokenize_size_changed',
                                            'piece_size_invalid',
                                            'piece_size_changed'],
                    'unknown_shape': 'QCunknown keeps ledger:null, compact_analysis exact3keys allnull, observation '
                                     'status not_attempted_QC_unknown and other6fieldsnull, matches:null. An already '
                                     'valid ledger/geometry is NEVER nulled by token/EOG membership failure.'},
             'failure': {'JSONL_bytes_including_LF': 8192,
                         'JSONL_exact_body_keys': ['primary_failure_id',
                                                   'error_class',
                                                   'reason_code',
                                                   'diagnostic_file',
                                                   'profile_qualification'],
                         'child_error_class_enum': ['BridgeError', 'StandardException', 'UnknownException'],
                         'diagnostic': 'Exact{kind,value}. kind none=>value null; module_policy_rejection=>the '
                                       'separately retained bounded numeric-UTF16/raw/report metadata schema, same '
                                       'primaryfailure. Metadata is reported/lexical context only, no filesystem/image '
                                       'authenticity. If it cannot fit64KiB, retain bounded primary/no-diagnostic '
                                       'marker rather than clip into a complete diagnostic.',
                         'diagnostic_file_enum': [None, 'failure.json'],
                         'enum_grammar': 'Exact listed ASCII identifiers only; no arbitrary exception/document/piece '
                                         'text in JSONL or stdout. Std '
                                         'exception=>StandardException/nonprotocol_cpp_exception; '
                                         'catchall=>UnknownException/unknown_cpp_exception. Unclassified bridge '
                                         'invariant=>BridgeError/bridge_invariant_failed.',
                         'marker': 'Separate failure.json<=65536; mandatory failure veto if present. Common bounded '
                                   'native snapshot plus '
                                   'schema_version/statusfailed/profile_id/pid/elapsed_ms/row_sequence_reserved/primary_failure_id/error_class/reason_code/failure_row_publication/diagnostic; '
                                   'no event/body/row_sequence successful-row impersonation.',
                         'order': 'Try the bounded JSONLfailure row once, then independently try marker even if '
                                  'rowpublication failed; marker records the observed rowoutcome. Earlier row never '
                                  'hashes a future marker, preventing cycles.',
                         'parent_scope': 'These enums describe CHILD wire only. Parent keeps its separately reviewed '
                                         'primary/secondary Python error and interruption identities; this contract '
                                         'never relabels or suppresses them.',
                         'primary_failure_id': 'SHA256(canonical{pid,error_class,reason_code,elapsed_ms,row_sequence_reserved}); '
                                               'pid binds the captured child/attempt. Intended failure sequence is '
                                               'known even when publication outcome is unknown.',
                         'profile_qualification': 'not_established',
                         'publication': 'Three flags strictbool; known_bytes strict uint0..8192 ornull; sha256 '
                                        'lower64hex onlyafter entire exact row+LF knownwritten; otherwise null. '
                                        'error_class null or oneof child_error_class_enum. Returned publication '
                                        'implies attempted+reserved; a pending write is unknown, never zero bytes '
                                        'received.',
                         'publication_exact_keys': ['attempt_reserved',
                                                    'write_attempted',
                                                    'return_observed',
                                                    'known_bytes',
                                                    'sha256',
                                                    'error_class'],
                         'reason_code_enum': ['mode_argv_invalid',
                                              'pin_header_ineligible',
                                              'version_or_defaults_mismatch',
                                              'export_resolution_failed',
                                              'module_policy_rejected',
                                              'platform_metadata_incomplete',
                                              'payload_descriptor_mismatch',
                                              'payload_hash_or_lease_failed',
                                              'pack_framing_or_binding_failed',
                                              'native_call_budget_exceeded',
                                              'token_work_budget_exceeded',
                                              'cooperative_deadline_expired',
                                              'native_call_exception',
                                              'native_return_or_shape_invalid',
                                              'native_ownership_or_cleanup_unknown',
                                              'sampler_or_model_null_return',
                                              'native_cleanup_failed',
                                              'document_QC_unknown',
                                              'case_expectation_mismatch',
                                              'required_coverage_unavailable',
                                              'required_coverage_unknown',
                                              'analyzer_or_selector_disagreement',
                                              'selected_prefix_observation_failed',
                                              'row_or_artifact_cap_exceeded',
                                              'output_publication_failed',
                                              'output_commit_failed',
                                              'unicode_batch_accounting_incomplete',
                                              'bridge_invariant_failed',
                                              'nonprotocol_cpp_exception',
                                              'unknown_cpp_exception'],
                         'stdout': 'Fixed bounded class/reason/primaryfailureID only; no large module diagnostic '
                                   'copied to stdout. Stream caps remain65536.'},
             'framing_id': 'unicode-controls-closed-framing-v1',
             'harness': {'analyzer_mapping': 'The accepted analyzer calls this harness_ineligible/harness_declared '
                                             'when its ledger isNone. The native guard reason remains separately '
                                             'retained; do not require its reason string to equal analyzer '
                                             'harness_declared.',
                         'calls': 'Zero per-document tokenizer/piece/sampler/apply/accept calls; common setup calls '
                                  'are not falsely reported as zero.',
                         'case_shape': 'QC exact{status:harness_ineligible,reason:same guard status}; ledger:null; '
                                       'compact_analysis PRESENT exact{counts:null,matrix:null,zero_piece_count:null}; '
                                       'matches_authored_native_expectation:null; authored native_member:null.',
                         'counts': 'Six declared exclusions have known population contribution0 by frozen declaration, '
                                   'not observed boundary absence. Unexpected QCunknown never changes native-byte '
                                   'eligibility or becomes a seventh harness exclusion.',
                         'exact_observation': {'all_input_tokens_admitted': None,
                                               'completion_EOG': None,
                                               'first_rejected_byte_end': None,
                                               'first_rejected_byte_start': None,
                                               'first_rejected_token_index': None,
                                               'native_member': None,
                                               'status': 'harness_raw_nul_rejection OR harness_utf8_rejection'},
                         'observation_wrapper': 'Always the exact seven-key OBJECT, never observation:null. Only '
                                                'native_member and other six nonstatus observation fields are null; '
                                                'status is the exact declared guard reason.'},
             'observation': {'EOG_disagreement_does_not_change_geometry': True,
                             'all_union_fields_are_exact_types': True,
                             'exact_keys': ['status',
                                            'native_member',
                                            'all_input_tokens_admitted',
                                            'first_rejected_token_index',
                                            'first_rejected_byte_start',
                                            'first_rejected_byte_end',
                                            'completion_EOG'],
                             'native_null_is_not_false': True,
                             'native_token_rejection_does_not_drop_ledger': True,
                             'not_attempted_QC_unknown': 'Wrapper is PRESENT with all seven keys; status '
                                                         'not_attempted_QC_unknown, other6values JSONnull. No sampler '
                                                         'call for that document; prior known tokenizer/piece work '
                                                         'remains counted. QCunknown is not a declared harness '
                                                         'exclusion.',
                             'ordinary_membership_union': {'native_EOG_disagreement': {'EOG': 'Every observed EOG '
                                                                                              'exactlyonce, at '
                                                                                              'leastoneTrue and at '
                                                                                              'leastoneFalse',
                                                                                       'all_input_tokens_admitted': True,
                                                                                       'native_member': None,
                                                                                       'rejection_fields': None},
                                                           'native_eog_rejection': {'EOG': 'Every observed EOG '
                                                                                           'exactlyonce, every '
                                                                                           'admittedFalse',
                                                                                    'all_input_tokens_admitted': True,
                                                                                    'native_member': False,
                                                                                    'rejection_fields': None},
                                                           'native_member': {'EOG': 'All observed sorted EOG IDs '
                                                                                    'exactlyonce, every admittedTrue',
                                                                             'all_input_tokens_admitted': True,
                                                                             'native_member': True,
                                                                             'rejection_fields': None},
                                                           'native_token_rejection': {'EOG': None,
                                                                                      'all_input_tokens_admitted': False,
                                                                                      'native_member': False,
                                                                                      'rejection_fields': 'Strict '
                                                                                                          'original '
                                                                                                          'token '
                                                                                                          'ordinalr '
                                                                                                          'and exact '
                                                                                                          'cumulative '
                                                                                                          'original '
                                                                                                          'piece '
                                                                                                          'interval, '
                                                                                                          'including '
                                                                                                          'allowed '
                                                                                                          'zero-length '
                                                                                                          'interval'}},
                             'status_enum': ['native_member',
                                             'native_token_rejection',
                                             'native_eog_rejection',
                                             'native_EOG_disagreement',
                                             'not_attempted_QC_unknown',
                                             'harness_raw_nul_rejection',
                                             'harness_utf8_rejection']},
             'partial_history': {'EOF': 'Strict UTF8 and final ASCII LF required to accept any complete row; a '
                                        'truncated final row is a retained unknown tail, not an ignored successful '
                                        'footer.',
                                 'declared_population_unchanged': True,
                                 'history_expectations': [{'id': 'no_capture',
                                                           'measured_global_counts': None,
                                                           'profile_qualified': False,
                                                           'tail': 'unknown',
                                                           'validated_case_rows': 0},
                                                          {'future_calls': 'unknown after last acknowledged snapshot',
                                                           'id': 'typed_setup_prefix_only',
                                                           'known_setup_vectors': 'Exact captured15-stage prefix only',
                                                           'profile_qualified': False,
                                                           'validated_case_rows': 0},
                                                          {'current_case_outcome': None,
                                                           'id': 'before_case_without_result',
                                                           'profile_qualified': False,
                                                           'remaining_cases': 'unknown',
                                                           'source_computed_at_last_snapshot': 0,
                                                           'validated_case_rows': 0},
                                                          {'current_row_write_increment': 'not witnessed until later '
                                                                                          'snapshot',
                                                           'global_counts': None,
                                                           'id': 'first_result_write_lag',
                                                           'profile_qualified': False,
                                                           'source_computed_at_row': 1,
                                                           'source_written_at_row': 0,
                                                           'validated_case_rows': 1},
                                                          {'id': 'next_before_case_witness',
                                                           'profile_qualified': False,
                                                           'remaining_cases': 'unknown',
                                                           'source_computed_at_row': 1,
                                                           'source_written_at_row': 1,
                                                           'validated_case_rows': 1},
                                                          {'geometry': 'retained',
                                                           'id': 'known_member_mismatch',
                                                           'matches': False,
                                                           'native_member': False,
                                                           'population': 'still declared',
                                                           'profile_qualified': False,
                                                           'validated_geometry_case_rows': 1},
                                                          {'geometry': 'retained',
                                                           'id': 'mixed_EOG_known_geometry',
                                                           'matches': None,
                                                           'native_member': None,
                                                           'population': 'still declared',
                                                           'profile_qualified': False,
                                                           'validated_geometry_case_rows': 1},
                                                          {'dependent_model_backend_release': 'blocked',
                                                           'id': 'pending_sampler_creation',
                                                           'owned_pointer': 'unknown not guessedNone',
                                                           'profile_qualified': False,
                                                           'sampler_init_attempted': 1,
                                                           'sampler_init_returned': 0},
                                                          {'backend_free_attempted': 0,
                                                           'id': 'pending_model_release',
                                                           'model_free_attempted': 1,
                                                           'model_free_returned': 0,
                                                           'model_release_unknown': True,
                                                           'profile_qualified': False},
                                                          {'coverage_complete': True,
                                                           'id': 'known_required_class_zero',
                                                           'profile_qualified': False,
                                                           'replace_or_search': False,
                                                           'required_available': False,
                                                           'selectors': 'null onlyfor knownzero class, other '
                                                                        'firstboundaries unchanged'},
                                                          {'counts': None,
                                                           'coverage_complete': False,
                                                           'id': 'population_geometry_unknown',
                                                           'known_lower_bounds': 'retained separately',
                                                           'matrix': None,
                                                           'profile_qualified': False,
                                                           'required_available': None,
                                                           'selected_prefixes': None,
                                                           'selectors': None},
                                                          {'id': 'wrong_case_body_after_good_snapshot',
                                                           'profile_qualified': False,
                                                           'source_computed_instrumentation': 1,
                                                           'validated_case_rows': 0,
                                                           'validated_harness_rows': 0,
                                                           'validated_native_rows': 0},
                                                          {'child_rows': 'may look complete',
                                                           'failure_marker': True,
                                                           'id': 'complete_rows_then_marker',
                                                           'profile_qualified': False},
                                                          {'child_rows': 'may be complete',
                                                           'id': 'complete_child_without_owner_gates',
                                                           'owner_or_external_qualification': 'not established',
                                                           'profile_qualified': False}],
                                 'native_tail': 'Attempted-minus-returned and work after last acknowledged snapshot '
                                                'remain unknown. No inferred return, retry, automatic release of an '
                                                'unknown pointer or no-calls claim from absent rows.',
                                 'scope': 'All scenarios below are literal synthetic framing/history expectations, not '
                                          'observations or a complete native run. Full profile acceptance isfalse for '
                                          'every isolated fragment/history.'},
             'profile_binding': {'cases': 84,
                                 'corpus_sha256': '13e2c2f2900802729c0d39fa9b7851c56ab3db6afdc45c4b15c2f7f80bd6523c',
                                 'harness_ineligible': 6,
                                 'native_byte_eligible': 78,
                                 'population': 68,
                                 'population_rule': 'Exact frozen native-byte-eligible AND authored generation-member '
                                                    'AND semantic-eligible. No observed native outcome/QC may filter '
                                                    'or replace it.',
                                 'profile_id': 'actual-v3-fullresponse-unicode-controls-v1'},
             'schema_version': 1,
             'scope_and_caps': {'complete_profile_packs': 0,
                                'execution_authorized': False,
                                'fragment_types': ['fixed_header',
                                                   'grammar_record',
                                                   'stage_record',
                                                   'case_record',
                                                   'ID'],
                                'implementation_authorized': False,
                                'positive_complete_rows': '188+U<=192 under the base design, U<=4 unique selections; '
                                                          'reserved envelope276 unchanged.',
                                'raw_document_population': 'All84 frozen rows remain, '
                                                           'including78eligible/6declaredharness and68fixedpopulation; '
                                                           'no token IDs or native outcomes used to author corpus, '
                                                           'classes or selection rule.',
                                'rowcaps': 'Each footer/global JSONL row<=8192 inclLF, each '
                                           'case/selected<=65536;16footer rows, no pooled-row exception. '
                                           'attemptfile4096/failurefile65536 are separate files; '
                                           'JSONL7995392/allstructured8065024 reservations unchanged.',
                                'scientific_validation': 'not_established',
                                'synthetic_rows': 'Datatype/byte/geometry examples may lack their setup prefix or use '
                                                  'independent fieldmaxima. Label that scope; never count them as an '
                                                  'actual successful native history.'}},
 'coverage': {'all_case_ledgers': 'Eligible nonpopulation cases also retain full arrays and geometry; six declared '
                                  'exclusions have null measurements and known population contribution0 by '
                                  'declaration.',
              'analyzer_contract_sha256': '05c214f42e9214691b5675cca58e67a6265dd069d2e7829f604df23c7ccca3e6',
              'classes': ['pending_width2',
                          'pending_width3',
                          'pending_width4',
                          'same_piece_complete_scalar_then_pending'],
              'compact_summary_keys': ['coverage_complete',
                                       'all_case_QC_complete',
                                       'counts',
                                       'matrix',
                                       'known_counts_lower_bound',
                                       'known_matrix_lower_bound',
                                       'unknown_population_ordinals',
                                       'selectors',
                                       'selected_prefixes',
                                       'required_available'],
              'geometry': 'Exact accepted analyzer intervals/matrix units, including wholly-contained complete scalar '
                          'within same piece; all boundaries reconstructible, not serialized as thousands of objects.',
              'population': 'Frozen native_byte_eligible AND generation_member AND semantic_eligible; never observed '
                            'membership/QC as a filter.',
              'selected_prefix': 'Use ORIGINAL token IDs through the selected piece, including empty tokens. Fresh '
                                 'sampler, no retokenization. Success requires all ordinary prefix tokens admitted '
                                 'then every EOG rejected; ordinary rejection is a failed observed prefix, not an '
                                 'excuse to select another boundary. Geometry selection remains unchanged by all '
                                 'grammar outcomes.',
              'selected_prefix_body_keys': ['selection_index',
                                            'case_ordinal',
                                            'token_ordinal',
                                            'take_tokens',
                                            'byte_cut',
                                            'classes',
                                            'pending_interval',
                                            'piece_interval',
                                            'complete_widths',
                                            'witnesses',
                                            'prefix_sha256',
                                            'observation',
                                            'matches_expected'],
              'selected_witnesses': 'Earliest contained scalar interval per distinct width1..4, sorted; '
                                    'classes/witnesses recomputed independently, not trusted child eligibility.',
              'selector': 'First(case ordinal,original token ordinal) per class across all declared population, '
                          'class-priority order as above; de-duplicate equal pair, preserve all class references, at '
                          'most4.',
              'unavailable': 'Known count0 -> required_available false; missing any required class fails profile after '
                             'complete safe data collection. No alternative/adaptive corpus or second tokenization.',
              'unknown': 'Any population QCunknown makes complete '
                         'counts/matrix/selectors/selected_prefixes/required_available null; known lower bounds stay '
                         'distinct. Excluded QCunknown still makes whole profile negative.',
              'whole_corpus': 'Evaluate all84 once before selection; retain every case outcome and all counts. Safe '
                              'membership mismatch does not remove it or stop the remaining safe scan.'},
 'event_order': {'after_cases': ['unicode_coverage_summary',
                                 'unicode_selection_plan',
                                 'unicode_selected_prefix_result[0..U-1]',
                                 'unicode_cleanup_returned',
                                 'unicode_batch_returned',
                                 'child_normal_completion'],
                 'batch_body_keys': ['cases_computed',
                                     'case_results_written',
                                     'stratum_computed',
                                     'stratum_results_written',
                                     'native_case_results',
                                     'harness_dispositions',
                                     'selected_prefixes_computed',
                                     'selected_prefix_results_written',
                                     'required_available',
                                     'all_case_QC_complete',
                                     'all_expected_membership_outcomes_match',
                                     'total_token_work_reserved',
                                     'module_policy_id',
                                     'module_policy_sha256',
                                     'module_policy_phase',
                                     'modules',
                                     'scientific_validation'],
                 'batch_success': '84/84, six exact strata,78 known membership outcomes and6 exact harness '
                                  'dispositions; required availability/allQC/all matches true; U prefix results pass; '
                                  'all calls returned/no owned or unknown release; cleanup observed. Still observation '
                                  'status only, never scientific/profile authority.',
                 'before_case_body_keys': ['case_ordinal',
                                           'case_id',
                                           'stage_instance_id',
                                           'grammar_sha256',
                                           'raw_sha256',
                                           'raw_bytes',
                                           'declared_native_byte_eligible'],
                 'cleanup_body_keys': ['sampler_init_returns',
                                       'sampler_free_returns',
                                       'samplers_owned',
                                       'sampler_release_unknown',
                                       'model_free_return_observed',
                                       'backend_free_return_observed',
                                       'cleanup_failed'],
                 'complete_success_row_positions': 'Setup rows0..14; before_case15+2i/result16+2i fori0..83; '
                                                   'coverage183; selection184; prefix185..184+U; cleanup185+U; '
                                                   'batch186+U; normal187+U. Complete row count188+U<=192. Reserved '
                                                   'profile envelopes276rows remain unchanged; failure after late '
                                                   'publication still consumes an existing footer slot.',
                 'coverage_body': 'The exact compact_summary_keys above plus '
                                  'case_counts{expected84,computed84,written84,native78,harness6,population68}; each '
                                  'count exactint and source-linked.',
                 'failure_body': 'primary_failure_id is SHA256 of '
                                 'canonical{pid,reason_code,error_class,elapsed_ms,row_sequence_reserved}. '
                                 'error_class/reason_code are finite ASCII enums, diagnostic_file is literal '
                                 'failure.json or null, profile_qualification is literal not_established. Common '
                                 'bounded native snapshot is still present. Max8192 inclLF.',
                 'failure_body_keys': ['primary_failure_id',
                                       'error_class',
                                       'reason_code',
                                       'diagnostic_file',
                                       'profile_qualification'],
                 'failure_marker': 'Separate<=65536 UTF8 JSON object contains the same primary identity and bounded '
                                   'raw module diagnostic when relevant. Failure JSONL is attempted first; marker '
                                   'records its actual reserved/attempted/return/unknown publication outcome and exact '
                                   'row SHA only if fully known. Marker attempt is independent even if JSONL failed. '
                                   'No future marker digest in the earlier row; no hash cycle.',
                 'normal_completion_body_keys': ['status', 'elapsed_ms'],
                 'normal_completion_status': 'unicode_controls_observations_complete_independent_qualification_pending',
                 'ordinary_failure': 'A pre-completion failure prevents a complete-success batch/normal sequence. A '
                                     'later publication/commit/cleanup fault can occur after complete-looking rows; '
                                     'any failure marker, parent failure or missing/failed terminal seal vetoes '
                                     'qualification. Do not rewrite earlier rows.',
                 'per_case': 'For each ordinal0..83: unicode_before_case then unicode_case_result. No prefix row '
                             'interleaving before all84 case results.',
                 'selection_plan_body': 'Exact selectors/selected_prefixes from compact summary; parent recomputes '
                                        'before any selected-prefix acceptance; U exact de-duplicated count0..4.',
                 'setup_body_schemas': {'all_vocabulary_ids_EOG_enumerated': {'exact_body_keys': ['vocabulary_count',
                                                                                                  'EOG_ids',
                                                                                                  'EOG_JSON_sha256',
                                                                                                  'module_policy_id',
                                                                                                  'module_policy_sha256',
                                                                                                  'module_policy_phase',
                                                                                                  'modules'],
                                                                              'fields': {'EOG_JSON_sha256': 'SHA256 of '
                                                                                                            'exact '
                                                                                                            'compact '
                                                                                                            'EOG ID '
                                                                                                            'JSON '
                                                                                                            'array',
                                                                                         'EOG_ids': 'Sorted '
                                                                                                    'unique1..64 '
                                                                                                    'strictints0..nv-1, '
                                                                                                    'source enumerates '
                                                                                                    'EVERY id0..nv-1 '
                                                                                                    'exactlyonce',
                                                                                         'module_policy_id': {'const': 'trusted-System32-recognition-v1'},
                                                                                         'module_policy_phase': 'Expected '
                                                                                                                'event-derived '
                                                                                                                'pre_cpu '
                                                                                                                'or '
                                                                                                                'post_cpu '
                                                                                                                'constant; '
                                                                                                                'parent '
                                                                                                                'supplies '
                                                                                                                'trusted '
                                                                                                                'phase '
                                                                                                                'to '
                                                                                                                'matcher.',
                                                                                         'module_policy_sha256': {'const': '4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713'},
                                                                                         'modules': 'Array1..64 '
                                                                                                    'exact{name,path} '
                                                                                                    'reports; exact '
                                                                                                    'pre/post matcher '
                                                                                                    'required, no '
                                                                                                    'reported-path '
                                                                                                    'filesystem '
                                                                                                    'operations. '
                                                                                                    'Entire serialized '
                                                                                                    'setup row<=8192 '
                                                                                                    'or explicit '
                                                                                                    'row-cap failure.',
                                                                                         'vocabulary_count': 'Strictint '
                                                                                                             'nv1..262144'}},
                                        'backend_init_returned_exact_CPU_identity_rechecked': {'exact_body_keys': ['module_policy_id',
                                                                                                                   'module_policy_sha256',
                                                                                                                   'module_policy_phase',
                                                                                                                   'modules'],
                                                                                               'fields': {'module_policy_id': {'const': 'trusted-System32-recognition-v1'},
                                                                                                          'module_policy_phase': 'Expected '
                                                                                                                                 'event-derived '
                                                                                                                                 'pre_cpu '
                                                                                                                                 'or '
                                                                                                                                 'post_cpu '
                                                                                                                                 'constant; '
                                                                                                                                 'parent '
                                                                                                                                 'supplies '
                                                                                                                                 'trusted '
                                                                                                                                 'phase '
                                                                                                                                 'to '
                                                                                                                                 'matcher.',
                                                                                                          'module_policy_sha256': {'const': '4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713'},
                                                                                                          'modules': 'Array1..64 '
                                                                                                                     'exact{name,path} '
                                                                                                                     'reports; '
                                                                                                                     'exact '
                                                                                                                     'pre/post '
                                                                                                                     'matcher '
                                                                                                                     'required, '
                                                                                                                     'no '
                                                                                                                     'reported-path '
                                                                                                                     'filesystem '
                                                                                                                     'operations. '
                                                                                                                     'Entire '
                                                                                                                     'serialized '
                                                                                                                     'setup '
                                                                                                                     'row<=8192 '
                                                                                                                     'or '
                                                                                                                     'explicit '
                                                                                                                     'row-cap '
                                                                                                                     'failure.'}},
                                        'before_exact_shard_hash': {'exact_body_keys': ['index',
                                                                                        'path',
                                                                                        'expected_bytes'],
                                                                    'fields': {'expected_bytes': 'Exact descriptor '
                                                                                                 'byte count, strict '
                                                                                                 'uint64',
                                                                               'index': 'Exact int0,1,2 according to '
                                                                                        'fixed occurrence order',
                                                                               'path': 'Exact known parent-bound '
                                                                                       'descriptor path, not reported '
                                                                                       'platform path'}},
                                        'before_explicit_required_OpenMP_dependency_load': {'exact_body_keys': ['dependency_native_initialization_possible'],
                                                                                            'fields': {'dependency_native_initialization_possible': {'const': True}}},
                                        'before_model_load_from_three_explicit_splits': {'exact_body_keys': ['effective_params',
                                                                                                             'empty_devices_array_nonnull',
                                                                                                             'cooperative_deadline_not_interruptible_native_call'],
                                                                                         'fields': {'cooperative_deadline_not_interruptible_native_call': {'const': True},
                                                                                                    'effective_params': {'exact_typed_value': {'check_tensors': False,
                                                                                                                                               'devices_null': False,
                                                                                                                                               'kv_overrides_null': True,
                                                                                                                                               'lazy_mode': 0,
                                                                                                                                               'load_mode': 0,
                                                                                                                                               'load_mtp': False,
                                                                                                                                               'main_gpu': -1,
                                                                                                                                               'n_gpu_layers': 0,
                                                                                                                                               'no_alloc': True,
                                                                                                                                               'no_host': False,
                                                                                                                                               'progress_callback_null': True,
                                                                                                                                               'progress_userdata_null': True,
                                                                                                                                               'split_mode': 0,
                                                                                                                                               'tensor_buft_overrides_null': True,
                                                                                                                                               'tensor_split_null': True,
                                                                                                                                               'use_extra_bufts': False,
                                                                                                                                               'vocab_only': True}},
                                                                                                    'empty_devices_array_nonnull': {'const': True}}},
                                        'cpu_registry_verified_before_llama_backend_init': {'exact_body_keys': ['registry_count',
                                                                                                                'device_count',
                                                                                                                'registry_name',
                                                                                                                'device_name',
                                                                                                                'module_policy_id',
                                                                                                                'module_policy_sha256',
                                                                                                                'module_policy_phase',
                                                                                                                'modules'],
                                                                                            'fields': {'device_count': {'const': 1},
                                                                                                       'device_name': {'const': 'CPU'},
                                                                                                       'module_policy_id': {'const': 'trusted-System32-recognition-v1'},
                                                                                                       'module_policy_phase': 'Expected '
                                                                                                                              'event-derived '
                                                                                                                              'pre_cpu '
                                                                                                                              'or '
                                                                                                                              'post_cpu '
                                                                                                                              'constant; '
                                                                                                                              'parent '
                                                                                                                              'supplies '
                                                                                                                              'trusted '
                                                                                                                              'phase '
                                                                                                                              'to '
                                                                                                                              'matcher.',
                                                                                                       'module_policy_sha256': {'const': '4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713'},
                                                                                                       'modules': 'Array1..64 '
                                                                                                                  'exact{name,path} '
                                                                                                                  'reports; '
                                                                                                                  'exact '
                                                                                                                  'pre/post '
                                                                                                                  'matcher '
                                                                                                                  'required, '
                                                                                                                  'no '
                                                                                                                  'reported-path '
                                                                                                                  'filesystem '
                                                                                                                  'operations. '
                                                                                                                  'Entire '
                                                                                                                  'serialized '
                                                                                                                  'setup '
                                                                                                                  'row<=8192 '
                                                                                                                  'or '
                                                                                                                  'explicit '
                                                                                                                  'row-cap '
                                                                                                                  'failure.',
                                                                                                       'registry_count': {'const': 1},
                                                                                                       'registry_name': {'const': 'CPU'}}},
                                        'exact_core_modules_loaded_exports_resolved': {'exact_body_keys': ['module_policy_id',
                                                                                                           'module_policy_sha256',
                                                                                                           'module_policy_phase',
                                                                                                           'modules',
                                                                                                           'layouts'],
                                                                                       'fields': {'layouts': {'exact_typed_value': {'array_offsets': {'data': 0,
                                                                                                                                                      'selected': 16,
                                                                                                                                                      'size': 8,
                                                                                                                                                      'sorted': 24},
                                                                                                                                    'bool_size': 1,
                                                                                                                                    'candidate_offsets': {'id': 0,
                                                                                                                                                          'logit': 4,
                                                                                                                                                          'p': 8},
                                                                                                                                    'model_offsets': {'check_tensors': 73,
                                                                                                                                                      'devices': 0,
                                                                                                                                                      'kv_overrides': 64,
                                                                                                                                                      'lazy_mode': 28,
                                                                                                                                                      'load_mode': 24,
                                                                                                                                                      'load_mtp': 77,
                                                                                                                                                      'main_gpu': 32,
                                                                                                                                                      'n_gpu_layers': 16,
                                                                                                                                                      'no_alloc': 76,
                                                                                                                                                      'no_host': 75,
                                                                                                                                                      'progress_callback': 48,
                                                                                                                                                      'progress_callback_user_data': 56,
                                                                                                                                                      'split_mode': 20,
                                                                                                                                                      'tensor_buft_overrides': 8,
                                                                                                                                                      'tensor_split': 40,
                                                                                                                                                      'use_extra_bufts': 74,
                                                                                                                                                      'vocab_only': 72},
                                                                                                                                    'model_params_align': 8,
                                                                                                                                    'model_params_size': 80,
                                                                                                                                    'pointer': 8,
                                                                                                                                    'token_array_size': 32,
                                                                                                                                    'token_data_size': 12,
                                                                                                                                    'token_size': 4}},
                                                                                                  'module_policy_id': {'const': 'trusted-System32-recognition-v1'},
                                                                                                  'module_policy_phase': 'Expected '
                                                                                                                         'event-derived '
                                                                                                                         'pre_cpu '
                                                                                                                         'or '
                                                                                                                         'post_cpu '
                                                                                                                         'constant; '
                                                                                                                         'parent '
                                                                                                                         'supplies '
                                                                                                                         'trusted '
                                                                                                                         'phase '
                                                                                                                         'to '
                                                                                                                         'matcher.',
                                                                                                  'module_policy_sha256': {'const': '4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713'},
                                                                                                  'modules': 'Array1..64 '
                                                                                                             'exact{name,path} '
                                                                                                             'reports; '
                                                                                                             'exact '
                                                                                                             'pre/post '
                                                                                                             'matcher '
                                                                                                             'required, '
                                                                                                             'no '
                                                                                                             'reported-path '
                                                                                                             'filesystem '
                                                                                                             'operations. '
                                                                                                             'Entire '
                                                                                                             'serialized '
                                                                                                             'setup '
                                                                                                             'row<=8192 '
                                                                                                             'or '
                                                                                                             'explicit '
                                                                                                             'row-cap '
                                                                                                             'failure.'}},
                                        'exact_shard_hash_returned': {'exact_body_keys': ['index', 'bytes', 'sha256'],
                                                                      'fields': {'bytes': 'Exact descriptor byte '
                                                                                          'count, strictuint64',
                                                                                 'index': 'Same fixed index',
                                                                                 'sha256': 'Exact descriptor '
                                                                                           'lower64hex'}},
                                        'three_exact_shards_hash_verified_and_read_leased': {'exact_body_keys': ['weight_file_hash_reads',
                                                                                                                 'tensor_weight_allocation_claim'],
                                                                                             'fields': {'tensor_weight_allocation_claim': {'const': False},
                                                                                                        'weight_file_hash_reads': {'const': True}}},
                                        'typed_version_and_defaults_observed': {'exact_body_keys': ['version',
                                                                                                    'defaults',
                                                                                                    'no_backend_or_model_call_so_far'],
                                                                                'fields': {'defaults': {'exact_typed_value': {'check_tensors': False,
                                                                                                                              'devices_null': True,
                                                                                                                              'kv_overrides_null': True,
                                                                                                                              'lazy_mode': 1,
                                                                                                                              'load_mode': -1,
                                                                                                                              'load_mtp': False,
                                                                                                                              'main_gpu': 0,
                                                                                                                              'n_gpu_layers': -1,
                                                                                                                              'no_alloc': False,
                                                                                                                              'no_host': False,
                                                                                                                              'progress_callback_null': True,
                                                                                                                              'progress_userdata_null': True,
                                                                                                                              'split_mode': 1,
                                                                                                                              'tensor_buft_overrides_null': True,
                                                                                                                              'tensor_split_null': True,
                                                                                                                              'use_extra_bufts': True,
                                                                                                                              'vocab_only': False}},
                                                                                           'no_backend_or_model_call_so_far': {'const': True},
                                                                                           'version': {'const': '0.7.0-dev'}}},
                                        'unicode_pack_verified_before_backend_or_model': {'exact_body_keys': ['pack_sha256',
                                                                                                              'wire_semantics_sha256',
                                                                                                              'corpus_sha256',
                                                                                                              'stages_sha256',
                                                                                                              'cases',
                                                                                                              'stage_instances',
                                                                                                              'unique_grammars',
                                                                                                              'coverage_classes'],
                                                                                          'fields': {'cases': {'const': 84},
                                                                                                     'corpus_sha256': {'const': '13e2c2f2900802729c0d39fa9b7851c56ab3db6afdc45c4b15c2f7f80bd6523c'},
                                                                                                     'coverage_classes': {'const': 4},
                                                                                                     'pack_sha256': 'Exact '
                                                                                                                    'future '
                                                                                                                    'bound '
                                                                                                                    'newpack '
                                                                                                                    'SHA256; '
                                                                                                                    'lower64hex',
                                                                                                     'stage_instances': {'const': 4},
                                                                                                     'stages_sha256': {'const': 'ad688168a366d5e95413ec69731d030c54431663e6574fb93445ced2b580413a'},
                                                                                                     'unique_grammars': {'const': 2},
                                                                                                     'wire_semantics_sha256': 'Exact '
                                                                                                                              'current '
                                                                                                                              'semantic '
                                                                                                                              'fingerprint'}}},
                 'setup_events': [{'body_selectors': {},
                                   'cumulative_attempted_equals_returned': {'ggml_backend_dev_count': 0,
                                                                            'ggml_backend_dev_get': 0,
                                                                            'ggml_backend_dev_name': 0,
                                                                            'ggml_backend_dev_type': 0,
                                                                            'ggml_backend_load': 0,
                                                                            'ggml_backend_reg_count': 0,
                                                                            'ggml_backend_reg_dev_count': 0,
                                                                            'ggml_backend_reg_dev_get': 0,
                                                                            'ggml_backend_reg_get': 0,
                                                                            'ggml_backend_reg_name': 0,
                                                                            'llama_backend_free': 0,
                                                                            'llama_backend_init': 0,
                                                                            'llama_model_default_params': 0,
                                                                            'llama_model_free': 0,
                                                                            'llama_model_get_vocab': 0,
                                                                            'llama_model_load_from_splits': 0,
                                                                            'llama_sampler_accept': 0,
                                                                            'llama_sampler_apply': 0,
                                                                            'llama_sampler_free': 0,
                                                                            'llama_sampler_init_grammar': 0,
                                                                            'llama_token_to_piece': 0,
                                                                            'llama_tokenize': 0,
                                                                            'llama_version': 0,
                                                                            'llama_vocab_is_eog': 0,
                                                                            'llama_vocab_n_tokens': 0},
                                   'event': 'before_explicit_required_OpenMP_dependency_load'},
                                  {'body_selectors': {'module_policy_phase': 'pre_cpu'},
                                   'cumulative_attempted_equals_returned': {'ggml_backend_dev_count': 0,
                                                                            'ggml_backend_dev_get': 0,
                                                                            'ggml_backend_dev_name': 0,
                                                                            'ggml_backend_dev_type': 0,
                                                                            'ggml_backend_load': 0,
                                                                            'ggml_backend_reg_count': 0,
                                                                            'ggml_backend_reg_dev_count': 0,
                                                                            'ggml_backend_reg_dev_get': 0,
                                                                            'ggml_backend_reg_get': 0,
                                                                            'ggml_backend_reg_name': 0,
                                                                            'llama_backend_free': 0,
                                                                            'llama_backend_init': 0,
                                                                            'llama_model_default_params': 0,
                                                                            'llama_model_free': 0,
                                                                            'llama_model_get_vocab': 0,
                                                                            'llama_model_load_from_splits': 0,
                                                                            'llama_sampler_accept': 0,
                                                                            'llama_sampler_apply': 0,
                                                                            'llama_sampler_free': 0,
                                                                            'llama_sampler_init_grammar': 0,
                                                                            'llama_token_to_piece': 0,
                                                                            'llama_tokenize': 0,
                                                                            'llama_version': 0,
                                                                            'llama_vocab_is_eog': 0,
                                                                            'llama_vocab_n_tokens': 0},
                                   'event': 'exact_core_modules_loaded_exports_resolved'},
                                  {'body_selectors': {},
                                   'cumulative_attempted_equals_returned': {'ggml_backend_dev_count': 0,
                                                                            'ggml_backend_dev_get': 0,
                                                                            'ggml_backend_dev_name': 0,
                                                                            'ggml_backend_dev_type': 0,
                                                                            'ggml_backend_load': 0,
                                                                            'ggml_backend_reg_count': 0,
                                                                            'ggml_backend_reg_dev_count': 0,
                                                                            'ggml_backend_reg_dev_get': 0,
                                                                            'ggml_backend_reg_get': 0,
                                                                            'ggml_backend_reg_name': 0,
                                                                            'llama_backend_free': 0,
                                                                            'llama_backend_init': 0,
                                                                            'llama_model_default_params': 1,
                                                                            'llama_model_free': 0,
                                                                            'llama_model_get_vocab': 0,
                                                                            'llama_model_load_from_splits': 0,
                                                                            'llama_sampler_accept': 0,
                                                                            'llama_sampler_apply': 0,
                                                                            'llama_sampler_free': 0,
                                                                            'llama_sampler_init_grammar': 0,
                                                                            'llama_token_to_piece': 0,
                                                                            'llama_tokenize': 0,
                                                                            'llama_version': 1,
                                                                            'llama_vocab_is_eog': 0,
                                                                            'llama_vocab_n_tokens': 0},
                                   'event': 'typed_version_and_defaults_observed'},
                                  {'body_selectors': {},
                                   'cumulative_attempted_equals_returned': {'ggml_backend_dev_count': 0,
                                                                            'ggml_backend_dev_get': 0,
                                                                            'ggml_backend_dev_name': 0,
                                                                            'ggml_backend_dev_type': 0,
                                                                            'ggml_backend_load': 0,
                                                                            'ggml_backend_reg_count': 0,
                                                                            'ggml_backend_reg_dev_count': 0,
                                                                            'ggml_backend_reg_dev_get': 0,
                                                                            'ggml_backend_reg_get': 0,
                                                                            'ggml_backend_reg_name': 0,
                                                                            'llama_backend_free': 0,
                                                                            'llama_backend_init': 0,
                                                                            'llama_model_default_params': 1,
                                                                            'llama_model_free': 0,
                                                                            'llama_model_get_vocab': 0,
                                                                            'llama_model_load_from_splits': 0,
                                                                            'llama_sampler_accept': 0,
                                                                            'llama_sampler_apply': 0,
                                                                            'llama_sampler_free': 0,
                                                                            'llama_sampler_init_grammar': 0,
                                                                            'llama_token_to_piece': 0,
                                                                            'llama_tokenize': 0,
                                                                            'llama_version': 1,
                                                                            'llama_vocab_is_eog': 0,
                                                                            'llama_vocab_n_tokens': 0},
                                   'event': 'unicode_pack_verified_before_backend_or_model'},
                                  {'body_selectors': {'index': 0},
                                   'cumulative_attempted_equals_returned': {'ggml_backend_dev_count': 0,
                                                                            'ggml_backend_dev_get': 0,
                                                                            'ggml_backend_dev_name': 0,
                                                                            'ggml_backend_dev_type': 0,
                                                                            'ggml_backend_load': 0,
                                                                            'ggml_backend_reg_count': 0,
                                                                            'ggml_backend_reg_dev_count': 0,
                                                                            'ggml_backend_reg_dev_get': 0,
                                                                            'ggml_backend_reg_get': 0,
                                                                            'ggml_backend_reg_name': 0,
                                                                            'llama_backend_free': 0,
                                                                            'llama_backend_init': 0,
                                                                            'llama_model_default_params': 1,
                                                                            'llama_model_free': 0,
                                                                            'llama_model_get_vocab': 0,
                                                                            'llama_model_load_from_splits': 0,
                                                                            'llama_sampler_accept': 0,
                                                                            'llama_sampler_apply': 0,
                                                                            'llama_sampler_free': 0,
                                                                            'llama_sampler_init_grammar': 0,
                                                                            'llama_token_to_piece': 0,
                                                                            'llama_tokenize': 0,
                                                                            'llama_version': 1,
                                                                            'llama_vocab_is_eog': 0,
                                                                            'llama_vocab_n_tokens': 0},
                                   'event': 'before_exact_shard_hash'},
                                  {'body_selectors': {'index': 0},
                                   'cumulative_attempted_equals_returned': {'ggml_backend_dev_count': 0,
                                                                            'ggml_backend_dev_get': 0,
                                                                            'ggml_backend_dev_name': 0,
                                                                            'ggml_backend_dev_type': 0,
                                                                            'ggml_backend_load': 0,
                                                                            'ggml_backend_reg_count': 0,
                                                                            'ggml_backend_reg_dev_count': 0,
                                                                            'ggml_backend_reg_dev_get': 0,
                                                                            'ggml_backend_reg_get': 0,
                                                                            'ggml_backend_reg_name': 0,
                                                                            'llama_backend_free': 0,
                                                                            'llama_backend_init': 0,
                                                                            'llama_model_default_params': 1,
                                                                            'llama_model_free': 0,
                                                                            'llama_model_get_vocab': 0,
                                                                            'llama_model_load_from_splits': 0,
                                                                            'llama_sampler_accept': 0,
                                                                            'llama_sampler_apply': 0,
                                                                            'llama_sampler_free': 0,
                                                                            'llama_sampler_init_grammar': 0,
                                                                            'llama_token_to_piece': 0,
                                                                            'llama_tokenize': 0,
                                                                            'llama_version': 1,
                                                                            'llama_vocab_is_eog': 0,
                                                                            'llama_vocab_n_tokens': 0},
                                   'event': 'exact_shard_hash_returned'},
                                  {'body_selectors': {'index': 1},
                                   'cumulative_attempted_equals_returned': {'ggml_backend_dev_count': 0,
                                                                            'ggml_backend_dev_get': 0,
                                                                            'ggml_backend_dev_name': 0,
                                                                            'ggml_backend_dev_type': 0,
                                                                            'ggml_backend_load': 0,
                                                                            'ggml_backend_reg_count': 0,
                                                                            'ggml_backend_reg_dev_count': 0,
                                                                            'ggml_backend_reg_dev_get': 0,
                                                                            'ggml_backend_reg_get': 0,
                                                                            'ggml_backend_reg_name': 0,
                                                                            'llama_backend_free': 0,
                                                                            'llama_backend_init': 0,
                                                                            'llama_model_default_params': 1,
                                                                            'llama_model_free': 0,
                                                                            'llama_model_get_vocab': 0,
                                                                            'llama_model_load_from_splits': 0,
                                                                            'llama_sampler_accept': 0,
                                                                            'llama_sampler_apply': 0,
                                                                            'llama_sampler_free': 0,
                                                                            'llama_sampler_init_grammar': 0,
                                                                            'llama_token_to_piece': 0,
                                                                            'llama_tokenize': 0,
                                                                            'llama_version': 1,
                                                                            'llama_vocab_is_eog': 0,
                                                                            'llama_vocab_n_tokens': 0},
                                   'event': 'before_exact_shard_hash'},
                                  {'body_selectors': {'index': 1},
                                   'cumulative_attempted_equals_returned': {'ggml_backend_dev_count': 0,
                                                                            'ggml_backend_dev_get': 0,
                                                                            'ggml_backend_dev_name': 0,
                                                                            'ggml_backend_dev_type': 0,
                                                                            'ggml_backend_load': 0,
                                                                            'ggml_backend_reg_count': 0,
                                                                            'ggml_backend_reg_dev_count': 0,
                                                                            'ggml_backend_reg_dev_get': 0,
                                                                            'ggml_backend_reg_get': 0,
                                                                            'ggml_backend_reg_name': 0,
                                                                            'llama_backend_free': 0,
                                                                            'llama_backend_init': 0,
                                                                            'llama_model_default_params': 1,
                                                                            'llama_model_free': 0,
                                                                            'llama_model_get_vocab': 0,
                                                                            'llama_model_load_from_splits': 0,
                                                                            'llama_sampler_accept': 0,
                                                                            'llama_sampler_apply': 0,
                                                                            'llama_sampler_free': 0,
                                                                            'llama_sampler_init_grammar': 0,
                                                                            'llama_token_to_piece': 0,
                                                                            'llama_tokenize': 0,
                                                                            'llama_version': 1,
                                                                            'llama_vocab_is_eog': 0,
                                                                            'llama_vocab_n_tokens': 0},
                                   'event': 'exact_shard_hash_returned'},
                                  {'body_selectors': {'index': 2},
                                   'cumulative_attempted_equals_returned': {'ggml_backend_dev_count': 0,
                                                                            'ggml_backend_dev_get': 0,
                                                                            'ggml_backend_dev_name': 0,
                                                                            'ggml_backend_dev_type': 0,
                                                                            'ggml_backend_load': 0,
                                                                            'ggml_backend_reg_count': 0,
                                                                            'ggml_backend_reg_dev_count': 0,
                                                                            'ggml_backend_reg_dev_get': 0,
                                                                            'ggml_backend_reg_get': 0,
                                                                            'ggml_backend_reg_name': 0,
                                                                            'llama_backend_free': 0,
                                                                            'llama_backend_init': 0,
                                                                            'llama_model_default_params': 1,
                                                                            'llama_model_free': 0,
                                                                            'llama_model_get_vocab': 0,
                                                                            'llama_model_load_from_splits': 0,
                                                                            'llama_sampler_accept': 0,
                                                                            'llama_sampler_apply': 0,
                                                                            'llama_sampler_free': 0,
                                                                            'llama_sampler_init_grammar': 0,
                                                                            'llama_token_to_piece': 0,
                                                                            'llama_tokenize': 0,
                                                                            'llama_version': 1,
                                                                            'llama_vocab_is_eog': 0,
                                                                            'llama_vocab_n_tokens': 0},
                                   'event': 'before_exact_shard_hash'},
                                  {'body_selectors': {'index': 2},
                                   'cumulative_attempted_equals_returned': {'ggml_backend_dev_count': 0,
                                                                            'ggml_backend_dev_get': 0,
                                                                            'ggml_backend_dev_name': 0,
                                                                            'ggml_backend_dev_type': 0,
                                                                            'ggml_backend_load': 0,
                                                                            'ggml_backend_reg_count': 0,
                                                                            'ggml_backend_reg_dev_count': 0,
                                                                            'ggml_backend_reg_dev_get': 0,
                                                                            'ggml_backend_reg_get': 0,
                                                                            'ggml_backend_reg_name': 0,
                                                                            'llama_backend_free': 0,
                                                                            'llama_backend_init': 0,
                                                                            'llama_model_default_params': 1,
                                                                            'llama_model_free': 0,
                                                                            'llama_model_get_vocab': 0,
                                                                            'llama_model_load_from_splits': 0,
                                                                            'llama_sampler_accept': 0,
                                                                            'llama_sampler_apply': 0,
                                                                            'llama_sampler_free': 0,
                                                                            'llama_sampler_init_grammar': 0,
                                                                            'llama_token_to_piece': 0,
                                                                            'llama_tokenize': 0,
                                                                            'llama_version': 1,
                                                                            'llama_vocab_is_eog': 0,
                                                                            'llama_vocab_n_tokens': 0},
                                   'event': 'exact_shard_hash_returned'},
                                  {'body_selectors': {},
                                   'cumulative_attempted_equals_returned': {'ggml_backend_dev_count': 0,
                                                                            'ggml_backend_dev_get': 0,
                                                                            'ggml_backend_dev_name': 0,
                                                                            'ggml_backend_dev_type': 0,
                                                                            'ggml_backend_load': 0,
                                                                            'ggml_backend_reg_count': 0,
                                                                            'ggml_backend_reg_dev_count': 0,
                                                                            'ggml_backend_reg_dev_get': 0,
                                                                            'ggml_backend_reg_get': 0,
                                                                            'ggml_backend_reg_name': 0,
                                                                            'llama_backend_free': 0,
                                                                            'llama_backend_init': 0,
                                                                            'llama_model_default_params': 1,
                                                                            'llama_model_free': 0,
                                                                            'llama_model_get_vocab': 0,
                                                                            'llama_model_load_from_splits': 0,
                                                                            'llama_sampler_accept': 0,
                                                                            'llama_sampler_apply': 0,
                                                                            'llama_sampler_free': 0,
                                                                            'llama_sampler_init_grammar': 0,
                                                                            'llama_token_to_piece': 0,
                                                                            'llama_tokenize': 0,
                                                                            'llama_version': 1,
                                                                            'llama_vocab_is_eog': 0,
                                                                            'llama_vocab_n_tokens': 0},
                                   'event': 'three_exact_shards_hash_verified_and_read_leased'},
                                  {'body_selectors': {'module_policy_phase': 'post_cpu'},
                                   'cumulative_attempted_equals_returned': {'ggml_backend_dev_count': 1,
                                                                            'ggml_backend_dev_get': 1,
                                                                            'ggml_backend_dev_name': 1,
                                                                            'ggml_backend_dev_type': 1,
                                                                            'ggml_backend_load': 1,
                                                                            'ggml_backend_reg_count': 1,
                                                                            'ggml_backend_reg_dev_count': 2,
                                                                            'ggml_backend_reg_dev_get': 2,
                                                                            'ggml_backend_reg_get': 1,
                                                                            'ggml_backend_reg_name': 1,
                                                                            'llama_backend_free': 0,
                                                                            'llama_backend_init': 0,
                                                                            'llama_model_default_params': 1,
                                                                            'llama_model_free': 0,
                                                                            'llama_model_get_vocab': 0,
                                                                            'llama_model_load_from_splits': 0,
                                                                            'llama_sampler_accept': 0,
                                                                            'llama_sampler_apply': 0,
                                                                            'llama_sampler_free': 0,
                                                                            'llama_sampler_init_grammar': 0,
                                                                            'llama_token_to_piece': 0,
                                                                            'llama_tokenize': 0,
                                                                            'llama_version': 1,
                                                                            'llama_vocab_is_eog': 0,
                                                                            'llama_vocab_n_tokens': 0},
                                   'event': 'cpu_registry_verified_before_llama_backend_init'},
                                  {'body_selectors': {'module_policy_phase': 'post_cpu'},
                                   'cumulative_attempted_equals_returned': {'ggml_backend_dev_count': 2,
                                                                            'ggml_backend_dev_get': 2,
                                                                            'ggml_backend_dev_name': 2,
                                                                            'ggml_backend_dev_type': 2,
                                                                            'ggml_backend_load': 1,
                                                                            'ggml_backend_reg_count': 2,
                                                                            'ggml_backend_reg_dev_count': 3,
                                                                            'ggml_backend_reg_dev_get': 3,
                                                                            'ggml_backend_reg_get': 2,
                                                                            'ggml_backend_reg_name': 2,
                                                                            'llama_backend_free': 0,
                                                                            'llama_backend_init': 1,
                                                                            'llama_model_default_params': 1,
                                                                            'llama_model_free': 0,
                                                                            'llama_model_get_vocab': 0,
                                                                            'llama_model_load_from_splits': 0,
                                                                            'llama_sampler_accept': 0,
                                                                            'llama_sampler_apply': 0,
                                                                            'llama_sampler_free': 0,
                                                                            'llama_sampler_init_grammar': 0,
                                                                            'llama_token_to_piece': 0,
                                                                            'llama_tokenize': 0,
                                                                            'llama_version': 1,
                                                                            'llama_vocab_is_eog': 0,
                                                                            'llama_vocab_n_tokens': 0},
                                   'event': 'backend_init_returned_exact_CPU_identity_rechecked'},
                                  {'body_selectors': {},
                                   'cumulative_attempted_equals_returned': {'ggml_backend_dev_count': 2,
                                                                            'ggml_backend_dev_get': 2,
                                                                            'ggml_backend_dev_name': 2,
                                                                            'ggml_backend_dev_type': 2,
                                                                            'ggml_backend_load': 1,
                                                                            'ggml_backend_reg_count': 2,
                                                                            'ggml_backend_reg_dev_count': 3,
                                                                            'ggml_backend_reg_dev_get': 3,
                                                                            'ggml_backend_reg_get': 2,
                                                                            'ggml_backend_reg_name': 2,
                                                                            'llama_backend_free': 0,
                                                                            'llama_backend_init': 1,
                                                                            'llama_model_default_params': 1,
                                                                            'llama_model_free': 0,
                                                                            'llama_model_get_vocab': 0,
                                                                            'llama_model_load_from_splits': 0,
                                                                            'llama_sampler_accept': 0,
                                                                            'llama_sampler_apply': 0,
                                                                            'llama_sampler_free': 0,
                                                                            'llama_sampler_init_grammar': 0,
                                                                            'llama_token_to_piece': 0,
                                                                            'llama_tokenize': 0,
                                                                            'llama_version': 1,
                                                                            'llama_vocab_is_eog': 0,
                                                                            'llama_vocab_n_tokens': 0},
                                   'event': 'before_model_load_from_three_explicit_splits'},
                                  {'body_selectors': {'module_policy_phase': 'post_cpu'},
                                   'cumulative_attempted_equals_returned': {'ggml_backend_dev_count': 2,
                                                                            'ggml_backend_dev_get': 2,
                                                                            'ggml_backend_dev_name': 2,
                                                                            'ggml_backend_dev_type': 2,
                                                                            'ggml_backend_load': 1,
                                                                            'ggml_backend_reg_count': 2,
                                                                            'ggml_backend_reg_dev_count': 3,
                                                                            'ggml_backend_reg_dev_get': 3,
                                                                            'ggml_backend_reg_get': 2,
                                                                            'ggml_backend_reg_name': 2,
                                                                            'llama_backend_free': 0,
                                                                            'llama_backend_init': 1,
                                                                            'llama_model_default_params': 1,
                                                                            'llama_model_free': 0,
                                                                            'llama_model_get_vocab': 1,
                                                                            'llama_model_load_from_splits': 1,
                                                                            'llama_sampler_accept': 0,
                                                                            'llama_sampler_apply': 0,
                                                                            'llama_sampler_free': 0,
                                                                            'llama_sampler_init_grammar': 0,
                                                                            'llama_token_to_piece': 0,
                                                                            'llama_tokenize': 0,
                                                                            'llama_version': 1,
                                                                            'llama_vocab_is_eog': 'observed '
                                                                                                  'vocabulary_count nv',
                                                                            'llama_vocab_n_tokens': 1},
                                   'event': 'all_vocabulary_ids_EOG_enumerated'}],
                 'setup_scalar_state_rules': {'CPU_before_init': 'cpu load return/nonNull true; backend/model '
                                                                 'ownedfalse, init/load/free counters0. Exact CPU '
                                                                 'identity2-level source vector above.',
                                              'EOG_enumerated': 'model load return/nonNull/modelownedtrue; borrowed '
                                                                'vocabulary nonNull; EOG_ids_examined nv, last_EOG_id '
                                                                'nv-1, all attempted=returned, coverage_state '
                                                                'not_computed.',
                                              'all_setup_rows': 'exceptions0; cases computed/written0; both '
                                                                'six-stratum arrays all0; selected computed/written0; '
                                                                'token_work0; no sampler init/free or ownership.',
                                              'backend_returned_and_before_model': 'backend init returned/ownedtrue; '
                                                                                   'model load/free counters0 and '
                                                                                   'modelownedfalse.',
                                              'through_typed_defaults_and_shards': 'CPU/backend/model/load/free '
                                                                                   'attempted and returned0; '
                                                                                   'owned/return flagsfalse, '
                                                                                   'coverage_state not_computed.'},
                 'typed_constant_rules': 'All embedded expected defaults/layout/effective objects compare recursively '
                                         'with EXACT types (bool cannot equal1). Future EXE/pin paths stay unbound; '
                                         'these are typed source expectations, not execution authority.'},
 'external_pending': ['Exact child/EXE/source/header/policy/pack/contract/protocol authority, original file '
                      'availability/fresh hashes/live leases and capture provenance.',
                      'Module reports use the exact4d pre/post lexical matcher with event-derived phase and declared '
                      'self/runtime context. Actual loaded-module/file identity and CPU/registry/API effects are not '
                      'authenticated by JSON or reported paths.',
                      'Parent journal/creation/resumption/PID/exit/reaping/captureEOF/byte caps, raw resource '
                      'limits/peaks, cleanup completeness, exclusive archive universe/marker/seal DAG and '
                      'same-owner300s clock.',
                      'Closed actual checker/source-loader/productionengine integration. No missing gate may be '
                      "replaced with a stub, dict readyflag, reusable receipt or this component's diagnostic summary.",
                      'Whole-profile native qualification, integrated applications, inference/masking and scientific '
                      'validation. Old189negative/timeout remains unchanged.'],
 'framing': {'common_row_keys': ['schema_version',
                                 'row_sequence',
                                 'event',
                                 'elapsed_ms',
                                 'wire_semantics_sha256',
                                 'native_call_contract_sha256',
                                 'native_call_counters',
                                 'native_call_scope',
                                 'unrecorded_killed_tail',
                                 'native_state',
                                 'body'],
             'encoding': 'Strict scalar UTF8, no BOM; one compact JSON object per ASCII LF. No '
                         'CRLF/blank/incomplete/duplicate-key/nonfinite rows.',
             'maximum_JSONL_bytes': 8388608,
             'native_state_count': 45,
             'native_state_fields': {'EOG_ids_examined': {'strict_int_range': [0, 262144]},
                                     'backend_free_attempted': 'strict bool',
                                     'backend_free_return_observed': 'strict bool',
                                     'backend_init_return_observed': 'strict bool',
                                     'backend_owned': 'strict bool',
                                     'backend_release_unknown': 'strict bool',
                                     'case_results_written': {'strict_int_range': [0, 84]},
                                     'cases_computed': {'strict_int_range': [0, 84]},
                                     'cleanup_failed': 'strict bool',
                                     'coverage_state': ['not_computed',
                                                        'complete_available',
                                                        'complete_unavailable',
                                                        'unknown'],
                                     'cpu_load_return_observed': 'strict bool',
                                     'cpu_registry_nonnull': 'strict bool',
                                     'current_case_index': {'strict_int_range': [-1, 83]},
                                     'current_selected_prefix_index': {'strict_int_range': [-1, 3]},
                                     'exceptions': {'strict_int_range': [0, 4276181]},
                                     'last_EOG_id': {'strict_int_range': [-1, 262143]},
                                     'last_EOG_returned': 'strict bool',
                                     'last_EOG_value': 'strict bool',
                                     'last_apply_logit_kind': {'strict_int_range': [0, 3]},
                                     'last_apply_return_observed': 'strict bool',
                                     'last_apply_shape_valid': 'strict bool',
                                     'last_attempt': [None,
                                                      'ggml_backend_dev_count',
                                                      'ggml_backend_dev_get',
                                                      'ggml_backend_dev_name',
                                                      'ggml_backend_dev_type',
                                                      'ggml_backend_load',
                                                      'ggml_backend_reg_count',
                                                      'ggml_backend_reg_dev_count',
                                                      'ggml_backend_reg_dev_get',
                                                      'ggml_backend_reg_get',
                                                      'ggml_backend_reg_name',
                                                      'llama_backend_free',
                                                      'llama_backend_init',
                                                      'llama_model_default_params',
                                                      'llama_model_free',
                                                      'llama_model_get_vocab',
                                                      'llama_model_load_from_splits',
                                                      'llama_sampler_accept',
                                                      'llama_sampler_apply',
                                                      'llama_sampler_free',
                                                      'llama_sampler_init_grammar',
                                                      'llama_token_to_piece',
                                                      'llama_tokenize',
                                                      'llama_version',
                                                      'llama_vocab_is_eog',
                                                      'llama_vocab_n_tokens'],
                                     'last_piece_return': {'strict_int_range': [-2147483648, 2147483647]},
                                     'last_pointer_nonnull': 'strict bool',
                                     'last_return': [None,
                                                     'ggml_backend_dev_count',
                                                     'ggml_backend_dev_get',
                                                     'ggml_backend_dev_name',
                                                     'ggml_backend_dev_type',
                                                     'ggml_backend_load',
                                                     'ggml_backend_reg_count',
                                                     'ggml_backend_reg_dev_count',
                                                     'ggml_backend_reg_dev_get',
                                                     'ggml_backend_reg_get',
                                                     'ggml_backend_reg_name',
                                                     'llama_backend_free',
                                                     'llama_backend_init',
                                                     'llama_model_default_params',
                                                     'llama_model_free',
                                                     'llama_model_get_vocab',
                                                     'llama_model_load_from_splits',
                                                     'llama_sampler_accept',
                                                     'llama_sampler_apply',
                                                     'llama_sampler_free',
                                                     'llama_sampler_init_grammar',
                                                     'llama_token_to_piece',
                                                     'llama_tokenize',
                                                     'llama_version',
                                                     'llama_vocab_is_eog',
                                                     'llama_vocab_n_tokens'],
                                     'last_return_kind': {'strict_int_range': [0, 4]},
                                     'last_scalar': {'strict_int_range': [-9223372036854775808, 9223372036854775807]},
                                     'last_tokenize_return': {'strict_int_range': [-2147483648, 2147483647]},
                                     'model_free_attempted': 'strict bool',
                                     'model_free_return_observed': 'strict bool',
                                     'model_load_return_observed': 'strict bool',
                                     'model_owned': 'strict bool',
                                     'model_release_unknown': 'strict bool',
                                     'model_return_nonnull': 'strict bool',
                                     'sampler_free_returned_nonnull': {'strict_int_range': [0, 82]},
                                     'sampler_nonnull_returns': {'strict_int_range': [0, 82]},
                                     'sampler_release_unknown': {'strict_int_range': [0, 82]},
                                     'samplers_owned': {'strict_int_range': [0, 82]},
                                     'selected_prefix_results_written': {'strict_int_range': [0, 4]},
                                     'selected_prefixes_computed': {'strict_int_range': [0, 4]},
                                     'stratum_computed': 'exact six strict uint0..84 values in frozen stratum order',
                                     'stratum_results_written': 'exact six strict uint0..84 values in frozen stratum '
                                                                'order',
                                     'token_work_reserved': {'strict_int_range': [0, 1000000]},
                                     'total_attempted': {'strict_int_range': [0, 4276181]},
                                     'total_returned': {'strict_int_range': [0, 4276181]}},
             'ordering': 'Contiguous exact int row_sequence starts0; no bool counters; closed root/body key sets by '
                         'event; no ready/verified qualification fields.',
             'row_bytes_including_LF': 65536,
             'schema_version_note': 'Wire version1 remains prospective; v1 proposal was never implemented. This '
                                    'corrected design is separately retained v2.',
             'setup_row_bytes_including_LF': 8192,
             'snapshot_semantics': 'Attempted/returned/state captured before post-call checks; current row excludes '
                                   'its own acknowledged-write increment. Next/final row witnesses it; failed/killed '
                                   'tails unknown.',
             'strict_string_identifiers': 'Reason/status/event enum tokens use only ASCII letters/digits/underscore, '
                                          'and case/stage IDs use the fixed pack-ID grammar. Free exception text is '
                                          'never an unbounded status/reason.'},
 'times': {'failure_ID': 'SHA256 of canonical compact sorted UTF8 object with exactly '
                         'pid,error_class,reason_code,elapsed_ms,row_sequence_reserved. elapsed_ms is the shared '
                         'failure_identity_elapsed_ms. JSONL-only recomputation uses declared expected childPID, '
                         'failure root.elapsed_ms/root.row_sequence and body class/reason. Marker-only recomputation '
                         'uses its own declared PID/elapsed/reserved sequence; actual process/owner provenance is '
                         'external.',
           'failure_reservation': 'After the primary class/reason and intended failure sequence are fixed, capture ONE '
                                  'failure_identity_elapsed_ms. Use that same value as failure JSONL common '
                                  'root.elapsed_ms and as marker.elapsed_ms; do not resample either for identity. It '
                                  'is>=the prior completed root sample when one exists. Marker publication may occur '
                                  'later; its completion time is not represented or inferred by the reused field.',
           'normal_completion': 'Normal body.elapsed_ms is sampled during body construction before the outer row '
                                'sample. Require previous completed root.elapsed_ms<=normal body.elapsed_ms<=normal '
                                'root.elapsed_ms; equality is allowed but not required. This is sequential-sample '
                                'ordering, not a same-clock-read assertion.',
           'same_failure_binding': 'With both records, require marker PID==expected childPID, marker '
                                   'elapsed_ms==failure common elapsed_ms, marker reserved sequence==failure root '
                                   'row_sequence, and equal class/reason/primaryID. The normal-completion body time is '
                                   'unrelated to failure identity except nondecreasing chronology; never substitute '
                                   'marker write time or a parent wall time.',
           'scope': 'Prospective v2 source/validator requirements filling previously unspecified sample conventions. '
                    'These are not claims of already implemented or old-run behavior; frozen base/framing artifacts '
                    'remain unchanged.',
           'types': 'Every root/body/marker elapsed_ms sample is exact uint64 milliseconds0..2^64-1, '
                    'neverbool/float/string. Completed row root samples are nondecreasing. Reused identity samples are '
                    'labelled logical reservation time, not publication/flush/close completion time.',
           'whole_child_budget': 'For complete-success consistency ALL completed rows, including cleanup/batch/normal, '
                                 'and both normal root/body samples are<=120000. Cleanup/failure rows may retain late '
                                 'reported uint64 values as negative/partial evidence rather than disappear; they '
                                 'cannot make a positive budget claim. Known reported budget violations are separately '
                                 'retained and veto strict success. Actual native/parent elapsed and cleanup deadlines '
                                 'still require external clock/resource binding.',
           'work_budget': 'For complete-success consistency every occurrence of an enumerated work event has common '
                          'root.elapsed_ms<=117000. This includes all15 setup occurrences and all ordinary '
                          'case/coverage/selection/prefix work; the set is event-derived, not caller-labelled.',
           'work_events': ['before_explicit_required_OpenMP_dependency_load',
                           'exact_core_modules_loaded_exports_resolved',
                           'typed_version_and_defaults_observed',
                           'unicode_pack_verified_before_backend_or_model',
                           'before_exact_shard_hash',
                           'exact_shard_hash_returned',
                           'three_exact_shards_hash_verified_and_read_leased',
                           'cpu_registry_verified_before_llama_backend_init',
                           'backend_init_returned_exact_CPU_identity_rechecked',
                           'before_model_load_from_three_explicit_splits',
                           'all_vocabulary_ids_EOG_enumerated',
                           'unicode_before_case',
                           'unicode_case_result',
                           'unicode_coverage_summary',
                           'unicode_selection_plan',
                           'unicode_selected_prefix_result']}})
