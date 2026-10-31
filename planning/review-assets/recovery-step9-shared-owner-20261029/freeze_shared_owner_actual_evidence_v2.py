"""Read-only final source/pure evidence binding, never an execution grant."""
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
after_path=HERE/'SHARED-OWNER-INTEGRATION-ACTUAL-PROOF-v2.json'
before_path=HERE/'SHARED-OWNER-FIVE-REGRESSIONS-BEFORE-v2.json'
assert pin(after_path)['sha256']=='14d78f96fbdb20e2c40e1884c278704f9da93b02c46cd502df87cf1f756698e3'
assert pin(before_path)['sha256']=='44eddebb07ef0a1e9a9c463881c67b585ca086febe173e914da1a5e790c63e4e'
after=json.loads(after_path.read_bytes());before=json.loads(before_path.read_bytes())
assert after['status']=='passed' and after['methods']==9
assert after['histories_executed']==after['histories_matched']==48
assert after['snapshot_count']==372 and not after['audit_denials']
assert before['methods']==8 and len(before['failures'])==8 and not before['errors']
for report in (before,after):
 assert all(report['source_unchanged'].values())
 for name,expected in report['source_pins'].items():assert pin(Path(expected['path']))==expected
 for expected in report['dependencies'].values():assert pin(Path(expected['path']))==expected
 for field in ('driver','regressions','runner','entry'):assert pin(Path(report[field]['path']))==report[field]
 assert all(v is False for v in report['qualification'].values())
names=['SHARED-OWNER-INTEGRATION-ACTUAL-PROOF-v2.json','SHARED-OWNER-FIVE-REGRESSIONS-BEFORE-v2.json','SHARED-OWNER-INTEGRATION-ACTUAL-FIRST-PROOF-v1.json','shared_owner_fixture_driver_v1.py','shared_owner_fixture_driver_v2.py','shared_owner_five_regressions_v2.py','shared_owner_actual_suite_runner_v2.py','check_shared_owner_five_before_v2.py','check_shared_owner_integration_actual_v2.py','shared_owner_snapshot_validator_v1.py','SHARED-OWNER-SNAPSHOT-VALIDATOR-PURE-PROBES-FIRST-v1.json','SHARED-OWNER-SNAPSHOT-VALIDATOR-INDEPENDENT-PEER-v1.json','shared_owner_v2.py','shared_file_ports_v2.py','continue_verification_v2.py','SHARED-OWNER-SOURCE-PAUSE-v2.json','SHARED-OWNER-ROOT-CORRECTION-SCOPE-v2.json','SHARED-OWNER-SOURCE-INDEPENDENT-HOLD-v1.json','SHARED-OWNER-WRAPPER-RETURN-BEFORE-v1.json','SHARED-OWNER-CONTINUATION-OWNER-BEFORE-v1.json','SHARED-OWNER-LATE-SEAL-FIRST-FINDING-v1.json','SHARED-OWNER-ADJACENT-IDENTITY-RETURN-BEFORE-v1.json','SHARED-OWNER-INTEGRATION-FIXTURES-v3.json','SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json','SHARED-OWNER-INTEGRATION-FIXTURE-FREEZE-v3.json','SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json','SHARED-OWNER-LITERAL-INDEPENDENT-PEER-v3.json']
value=dict(schema_version=2,status='EXACT_CORRECTED_SOURCE_PURE_EVIDENCE_FROZEN_FOR_FINAL_INDEPENDENT_PEER',pins={name:pin(HERE/name) for name in names},freezer=pin(Path(__file__).resolve()),summary=dict(actual_methods=9,frozen_histories_executed=48,frozen_histories_matched=48,strictly_validated_history_snapshots=372,actual_full48_injected_original_dispatches=518,actual_full48_captured_marker_module_execs=34,focused_same_assertion_methods=8,retrospective_v1_focused_failures=8,retrospective_v1_focused_errors=0,after_failures=0,after_errors=0,after_elapsed_seconds=after['elapsed_seconds'],audit_denials=[]),chronology=dict(frozen48_oracle_predates_all_three_subject_implementations=True,original_five_family_functional_witnesses_and_first48_failures_predate_fixes=True,consolidated_focused_module_authored_after_v2_source=True,consolidated_focused_module_run_retrospectively_on_unchanged_v1_then_on_frozen_v2=True,consolidated_module_preregistered_or_pre_fix_authored=False,first_v1_47_of48_failure_preserved=True),source_scope='Five corrections only: known normal wrapper return; readonly Continuation issuer; readonly original Origin; known candidate/cleanup/receipt/seal callbackACK terminal projections; known late compiler returnednames before acceptance. Source APIs/fields/caps and golden48/e12 unchanged.',harness_scope='Fresh exact new module source maps only, no old-name sys.modules fallback. Driver v2 adds stricter stop monitor after reported stop plusnormalbindingreturn; actualSnapshot recursively validated BEFORE every expected comparison. Same8 focused assertions distinguish known callback/return facts from completion. Marker141B actualsourceexec uses closed resolver; focused latecompiler deliberately returns opaque object and earns no source execution/acceptance.',nonclaims=['Real first process entry/timer before imports','C/ctypes return-conversion/first-storage atomicity','Win32 file ports or physical sink I/O','Fresh-original/source closure availability/lease qualification','Production owner/loader/checker or full roster/budget/memory fit','Original failed native experiment repair or rerun','Profile/model/tokenizer/grammar/scientific qualification'],additional_actual_execution=False,actual_target_API_calls=0,old_payload_or_sourceclosure_operations=0,qualification=after['qualification'])
path=HERE/'SHARED-OWNER-INTEGRATION-ACTUAL-EVIDENCE-FREEZE-v2.json'
with path.open('xb') as out:out.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8'))
print(json.dumps(dict(freeze=pin(path),actual_proof=pin(after_path),retrospective_before=pin(before_path))))
