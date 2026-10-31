"""Literal finite history roster, no transition interpreter or component use."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
# Branches and expected causal predicates are authored before implementation.
# Exact public observation keys await the source author's DATA skeleton.
rows=[
 ('baseline_consistent','baseline','unchanged cohort; all fixture handlers consistent','209 known/hash/capture bytes;21 actual calls; same owner/early bytes; all three once-closed; pure seam consistent only'),
 ('baseline_core_negative','baseline','typed core fixture-handler negative after prior required stages','209 known/hash/capture bytes and all closure/final acknowledgment retained; pure seam complete negative, no real qualification'),
 ('work_cutoff_before_stage','spent_origin','start100; bootstrap/loader spends289s; next required work check395','no remaining work admitted at395; original start100/work395/hard400; once cleanup only before400'),
 ('hard_cutoff_before_cleanup','spent_origin','same original clock advances400 before pending cleanup dispatch','no later original or sink callback; close remains not dispatched/unknown as applicable; incomplete in-memory result'),
 ('foreign_origin','foreign_or_duplicate','second typed origin with equal100/395/400 numeric values','reject foreign identity before remaining acquire/compile or reset'),
 ('foreign_nonce','foreign_or_duplicate','second source-issued nonce','reject without subject-owner nonce/registry/time mutation'),
 ('foreign_registry','foreign_or_duplicate','second source-issued registry/call reference','reject before dispatch; no copied close right'),
 ('foreign_port','foreign_or_duplicate','second non-owning file view or injected binding identity','reject before new original call; retain original bound port'),
 ('copied_continuation_dict','foreign_or_duplicate','ordinary dict copying reported fields/ready values','reject as ordinary data; no authority from serialized fields'),
 ('repeated_continuation_claim','foreign_or_duplicate','claim genuine token twice','second claim rejects without event/close/namespace increment'),
 ('early_role_changed','early_role_alias','later exact authority changes leaf role software to owner_metadata','reject before remaining open; early bytes not rehashed as workaround'),
 ('early_capture_changed','early_role_alias','later exact authority changes leaf captureTrue toFalse','reject before remaining open; no copied capture eligibility'),
 ('early_hash_changed','early_role_alias','later authority changes only leaf expected hash','reject exact descriptor mismatch; current known bytes/digest retained'),
 ('canonical_path_alias','early_role_alias','pre-open full tuple adds canonical case/slash alias of existing leaf','reject before reserve/open; no larger plan or invented input blob'),
 ('early_closed_success','early_liveness','close early leaf true before continuation claim','close consumed once; claim rejected; no event increment or reopen'),
 ('early_closed_failure','early_liveness','close early leaf false before source load','no source execution/cache eligibility; failed consumed right not retried'),
 ('early_close_unobserved','early_liveness','early leaf closer invocation reserved, wrapper throws without scalar','no source execution; unknown consumed close right not retried'),
 ('compile_original_failure','source_import_failure','compiler callback raises original MemoryError on entry compile','same error retained; attempted compile not retried; early leases centrally cleaned'),
 ('undeclared_source_import','source_import_failure','source compiler requests undeclared module through resolver','no ordinary import/sys.modules/path fallback; dependency refusal retained'),
 ('cache_return_after_early_close','source_import_failure','load entry once, close its early source, request same module again','cached module does not bypass current source liveness; no new compilation'),
 ('open_scalar_then_KI','raw_open_wrapper_fault','first usable handle101 stored then KeyboardInterrupt before auxiliary acknowledgment','owned handle survives; exact original primary; one legal close; no identity/content work'),
 ('open_scalar_then_SE','raw_open_wrapper_fault','first usable handle101 stored then SystemExit before right transfer acknowledgment','owned handle survives false aux; exact original primary; one legal close'),
 ('open_scalar_unobserved','raw_open_wrapper_fault','invoke wrapper returnsNone normally without scalar storage','wrapper return known, raw return unknown; no guessed handle/close or source progress'),
 ('open_observed_NULL','raw_open_wrapper_fault','store observedNone for CreateFileW','NULL differs from UNOBSERVED; ownership unknown, no guessed close or source content'),
 ('open_observed_INVALID','raw_open_wrapper_fault','store uint64INVALID for CreateFileW plus defined error2','known failed open/no right; not normalized toNULL or unobserved'),
 ('read_count_then_deadline','late_count','first leaf read stores nonzeroBOOL/count58 then advances originalclock395','known58 survives post-clock; hash/capture0, no read reuse/new work; source incomplete'),
 ('read_hash_KI','late_count','first leaf read count58 known, hash hook throws originalKeyboardInterrupt','known58 retained; hash/capture uncommitted, exact original error, stopped buffer generation retained'),
 ('read_copy_MemoryError','late_count','first leaf hash58 returns, capture copy hook throws originalMemoryError','known/hash58 retained; capture0, stopped current buffer kept, no further read'),
 ('read_defined_zero','late_count','first leaf successfulBOOL/count0','raw known0/count-defined distinctunknown, but cannot satisfy58 remaining bytes; no EOF/full-hash pass'),
 ('read_false_observed_zero','late_count','first leaf rawBOOL0/count0 observed','count observed but notdefined; no false known0 completeness, stop future read/reuse'),
 ('wrapper_return_then_later_stop','returned_wrapper_then_error','first leaf ReadFile wrapper returned then post-wrapper publication error','portable wrapper counter remains1 for that read; raw/count contributions once; legal cleanup only'),
 ('injected_source_error_class','returned_wrapper_then_error','fresh exported source error class raised by capture hook','same actual object latched once; class identity does not exempt it; stopped bytes retained'),
 ('reservation_foreign_ack','reservation_or_append_fault','sink reserve returns foreign token','no output ownership; no later append/publish/journalclose callbacks or original opens'),
 ('reservation_unreturned','reservation_or_append_fault','sink reserve raises after attempt','ownership unknown, no later sink callbacks or original opens; original exception retained'),
 ('owned_append_original_failure','reservation_or_append_fault','owned append reserves ordinal then raises originalRuntimeError','ordinal retained/notreused; no recursive API journal; canonical originals once-cleaned'),
 ('checker_factory_unbranded','checker_binding','ordinary callable/checker dict lacks source-issued test brand','real checker binding refused; no defaultstub/pure marker loader promotion'),
 ('checker_foreign_context','checker_binding','typed test handler returns observation bound to other EvidenceContext','reject before stage proof; same subject context stays current'),
 ('checker_return_late','checker_binding','typed observation returns while sameclock advances395','return observed but gate incomplete; cleanup before400 only; no late consistent completion'),
 ('original_close_false','close_and_terminal_faults','metadata closer storesBOOL0','right consumed exactlyonce; no successful seal/positive final gate'),
 ('original_close_unreturned','close_and_terminal_faults','metadata closer wrapper raises with rawscalarUNOBSERVED','unknown close retained/no retry; no successful seal'),
 ('seal_ack_late','close_and_terminal_faults','seal callback returns exactack after advancing400','known seal return retained but finalclock fails; no completion or later sink call'),
 ('postseal_no_new_output','close_and_terminal_faults','after successful seal try a consumed publication kind/append','reject before sink dispatch; no secondkind attempt, postseal failure in-memory only'),
 ('preopen_roster_bounds','budget_and_output_caps','five-entry/B3/M3 malformed descriptor/graph combinations using only existing blob labels','reject before original open/output ownership; no new payload or cap extension'),
 ('forged_derived_caps','budget_and_output_caps','full_specs dict or unexpected claimed_C/claimed_E argument','strict interface rejects; no new claimed-bound API; valid tuple still derivesR51/C69/E218'),
 ('short_read_attempt_exhaustion','budget_and_output_caps','permitted small successful slices until admitted read attempts consumed','known slices counted once; next read refused at fixed quota, no generation/cap reset'),
 ('publication_attempt_or_size_cap','budget_and_output_caps','repeat consumed publication kind or payload8193B','reject before callback; attempted/unknown prior kind never reopened; actuals not assumedzero'),
 ('snapshot_and_exception_mutation','immutability','mutate detached snapshot containers and originalException.args after issuance','issued metadata unchanged; original exception getter remains sameobject; no diagnostic authority'),
 ('foreign_diagnostic_and_nonowning_view','immutability','foreign diagnostic identity token or nonowning view used as call/ref','reject before ownership/dispatch mutation; source-issued identities not reproduced by equalfields'),
]
assert len(rows)==48 and len({r[0] for r in rows})==48 and len({r[1] for r in rows})==14
value=dict(schema_version=1,status='UNFROZEN_LITERAL_ROSTER_AWAITING_PUBLIC_OBSERVATION_DATA_SCHEMA',proposal_sha256='90fc021a044bba34953a8f8f8e42b05f5d61f49da945044e1e108f92bb1fc3cd',cohort_sha256='eb5147d200bcc0108b71968d69f6b251c29b56dd52d926a8606504682134d9b8',source_implementation_authorized=False,reviewed_components_imported=False,toy_helpers_executed=False,actual_API_calls=0,cases=[dict(id=i,group=g,input_branch=b,authored_causal_expectation=e) for i,g,b,e in rows])
path=HERE/'SHARED-OWNER-INTEGRATION-HISTORY-ROSTER-DRAFT-v1.json'
with path.open('xb') as out:out.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8'))
raw=path.read_bytes();print(json.dumps(dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),histories=48,groups=14)))
