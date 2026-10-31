"""Metadata/AST-only freeze; no reviewed subject imports or execution."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
SHARED=HERE.parent/'recovery-step9-shared-owner-20261029'
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def publish(name,value):
 path=HERE/name
 with path.open('xb') as out:out.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8'))
 return pin(path)
def main():
 draft=json.loads((HERE/'INDEXED-ACCOUNTING-PRECODE-PROTOCOL-DRAFT-v1.json').read_bytes())
 expected={
  'INDEXED-ACCOUNTING-SUCCESSOR-PROPOSAL-v1.json':'7e2b1b5b71095863ab687a92f8152239c2922f0bd8ada9c875562ec15d6d9a5b',
  'INDEXED-ACCOUNTING-APPEND-ENVELOPE-CLARIFICATION-v1.json':'147dc12855fe6f9bbd5b1994bc1e389b938cb03bdc25ddb1cf4137c5fc48cfd6',
 }
 design={n:pin(HERE/n) for n in expected}
 for n,digest in expected.items():assert design[n]['sha256']==digest
 for name,old in draft['accepted_pins'].items():assert pin(Path(old['path']))==old,name
 test=pin(HERE/'indexed_accounting_controls_v1.py')
 tree=ast.parse((HERE/'indexed_accounting_controls_v1.py').read_text(encoding='utf-8'))
 tests=[node.name for node in ast.walk(tree) if isinstance(node,ast.FunctionDef) and node.name.startswith('test_')]
 assert len(tests)==6 and len(set(tests))==6
 extra=['shared_owner_fixture_driver_v2.py','shared_owner_snapshot_validator_v1.py','SHARED-OWNER-SNAPSHOT-VALIDATOR-INDEPENDENT-PEER-v1.json','SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json','SHARED-OWNER-ROOT-SOURCE-SCOPE-v1.json','SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json']
 protocol=dict(draft,status='FROZEN_PRE_CODE_SIX_CONTROLS_SOURCE_AND_EXPECTATIONS_NOT_IMPLEMENTATION_AUTHORITY',recorded_at_utc=datetime.now(timezone.utc).isoformat(),draft=pin(HERE/'INDEXED-ACCOUNTING-PRECODE-PROTOCOL-DRAFT-v1.json'),design=design,test_source=test,extra_accepted_pins={n:pin(SHARED/n) for n in extra},tests=tests)
 protocol['future_private_seams']['index']+=' Effective addendum: BaseException envelope starts BEFORE canonical append; actual append-committed-then-throw tested in BOTH modes, plus indexed helper before/after. No rollback/retry/invented entry.'
 protocol['controls'][4]['future_modes']=['canonical_append_after','before_index_helper','after_index_helper']
 protocol['controls'][5]['future_modes']=['before_defined_count_fold','after_defined_count_fold','healthy_identical_count_replay','partial_scalar_pair','defined_zero_pair']
 protocol['baseline_expected_result']=dict(hot_methods=4,hot_global_scans_expected=True,functional_methods=2,absent_future_helper_failures_accepted=False,all_first_failures_retained=True)
 protocol['counter_and_authority_limits']=[
  'CountingList installed only while actual canonical registry is empty; original owner/Origin/nonce, clocks, checks and every binding monitor remain.',
  'Base-list calls occur only inside instrumentation or harness measurement. Under-test code must not bypass instrumentation via list base methods, copied ledger, dict.values iteration, cold projection called from hot path, or alternate call authority. Static source peer required.',
  'At most one actual append per real new Read; reservations distinct from binding entry. Cleanup and named reporting are cold windows, not evidence of constant-time whole lifecycle.',
  'Frozen actual48, same8 and author16 remain required after any prospective source implementation. These six controls alone never establish full-source/native/profile qualification.',
  'No timing threshold, full-roster scalability, real entry, real FFI, file/hash closure, or original-source availability claim.'
 ]
 protocol['functional_failure_rules']=[
  'Original MemoryError propagates by identity, remains primary once. Canonical raw records are truth even if append/index/fold interrupted.',
  'Append fault leaves entered False, scalar/count UNOBSERVED, no Read dispatch and read_count_unknown False; all prior known handles remain once-cleanup eligible under original hard clock.',
  'A defined count stored before fold failure stays known58 with hash/copy0 and count_aux False. Scalar-only pair remains unknown/None; defined0 is known0, never absent evidence.',
  'Snapshot/report derives canonical facts without healing derived state or clearing fault; repeated reports cannot resume work/doublefold. Indexed work getters refuse on unhealthy accounting; cleanup is direct canonical ownership only.',
  'Clean identical raw COUNT replay contributes once. Before/after helper wrapper faults and append-after-commit faults all quarantine before any further noncleanup dispatch.'
 ]
 p=publish('INDEXED-ACCOUNTING-PRECODE-TEST-CONTRACT-v1.json',protocol)
 prospective={n:False for n in ('shared_owner_v3.py','shared_file_ports_v3.py','continue_verification_v3.py')}
 for name in prospective:
  assert not (HERE/name).exists() and not (SHARED/name).exists(),name
 freeze=dict(schema_version=1,status='TEST_SOURCE_AND_EXPECTATIONS_FROZEN_BEFORE_V3_SOURCE_AND_BEFORE_ACCEPTED_V2_PROBES',recorded_at_utc=datetime.now(timezone.utc).isoformat(),protocol=p,test_source=test,freezer=pin(Path(__file__).resolve()),design=design,subject_runs_before_this_freeze=0,prospective_files_present=prospective,implementation_authorized=False,baseline_V2_pure_tests_authorized_by='Root explicit NEW_TASK and existing 4db source scope, no new V3 code authority',actual_target_API_calls=0,original_payload_operations=0,all_real_qualification_flags_false=True)
 f=publish('INDEXED-ACCOUNTING-PRECODE-CONTROL-FREEZE-v1.json',freeze)
 print(json.dumps(dict(protocol=p,source=test,freeze=f,methods=6,subject_runs=0)))

if __name__=='__main__':main()
