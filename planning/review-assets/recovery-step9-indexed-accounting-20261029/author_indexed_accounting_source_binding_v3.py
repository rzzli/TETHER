"""Metadata/AST-only exact coherent source binding; no subject imports."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
SHARED=HERE.parent/'recovery-step9-shared-owner-20261029'
PRECODE=HERE.parent/'recovery-step9-production-preflight-20261029'
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def checked(path,digest):
 raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,path.name;return raw
def publish(name,value):
 path=HERE/name
 with path.open('xb') as out:out.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8'))
 return pin(path)
def main():
 pause_path=HERE/'INDEXED-ACCOUNTING-SOURCE-PAUSE-v3.json'
 pause=json.loads(checked(pause_path,'8c0103972a4cd33365e0b642e8d9ae44981d6121a31d644cfc2e443c1f20390c'))
 root=PRECODE/'INDEXED-ACCOUNTING-ROOT-SOURCE-SCOPE-v3.json'
 checked(root,'7683b6f661387b12e10ab2cbf83157b56dd3d5d5e2e4439d19e9804175196f97')
 names=('shared_owner_v3','shared_file_ports_v3','continue_verification_v3')
 assert pause['status']=='FIRST_COHERENT_V3_SOURCE_PAUSE_BEFORE_IMPORT_OR_TEST'
 assert pause['root_scope_sha256']==pin(root)['sha256'] and pause['subject_tests']==pause['synthetic_subject_imports']==0
 assert len(pause['source_files'])==3
 pins={}
 for name,expected in zip(names,pause['source_files']):
  path=HERE/(name+'.py')
  assert set(expected)=={'path','bytes','sha256'} and expected['path']==str(path)
  assert pin(path)==expected
  ast.parse(path.read_text(encoding='utf-8'));pins[name]=expected
 validator=SHARED/'shared_owner_snapshot_validator_v1.py'
 checked(validator,'afa71df1ebba3eb7da83890b6e86675597894600cd593578b34f5f1a12cefefc');pins[validator.stem]=pin(validator)
 test_paths=[SHARED/'shared_owner_fixture_driver_v2.py',SHARED/'shared_owner_five_regressions_v2.py',validator,PRECODE/'indexed_accounting_controls_v2.py']
 test_pins={path.name:pin(path) for path in test_paths}
 for name,digest in {
  'shared_owner_fixture_driver_v2.py':'a97ae3ca57ce6f1b97e5a382a4051714242621c11b3d1756262f1f8025c8f566',
  'shared_owner_five_regressions_v2.py':'8fc70bcfa3a12ffd4bcae0c5fd3ba6c856960f4044bef3856d5f19537fc4367d',
  'indexed_accounting_controls_v2.py':'d76e1a2d7c70a9a42fa70c5f4989f08f2e291e79f12fa53b454250998c74bf5b',
 }.items():assert test_pins[name]['sha256']==digest
 dependencies={pause_path.name:pin(pause_path),root.name:pin(root)}
 for name in ('INDEXED-ACCOUNTING-SUCCESSOR-PROPOSAL-v1.json','INDEXED-ACCOUNTING-APPEND-ENVELOPE-CLARIFICATION-v1.json','INDEXED-ACCOUNTING-PRECODE-TEST-CONTRACT-v2.json','INDEXED-ACCOUNTING-PRECODE-CONTROL-FREEZE-v2.json','INDEXED-ACCOUNTING-ACTUAL-V2-BEFORE-PROOF-v2.json','INDEXED-ACCOUNTING-INDEPENDENT-PRECODE-PEER-v2.json'):
  dependencies[name]=pin(PRECODE/name)
 for name in ('SHARED-OWNER-SCOPED-ACCEPTANCE-v2.json','SHARED-OWNER-INTEGRATION-FIXTURES-v3.json','SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json','SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json','SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json','SHARED-OWNER-SNAPSHOT-VALIDATOR-INDEPENDENT-PEER-v1.json'):
  dependencies[name]=pin(SHARED/name)
 runner=HERE/'run_indexed_accounting_actual_v3_v1.py';ast.parse(runner.read_text(encoding='utf-8'))
 binding=publish('INDEXED-ACCOUNTING-INDEPENDENT-SOURCE-BINDING-v3.json',dict(schema_version=3,mode='FROZEN_V3_SOURCE_SAME48_SAME8_PRECODE6_INDEXED',recorded_at_utc=datetime.now(timezone.utc).isoformat(),source_pins=pins,test_pins=test_pins,dependencies=dependencies,runner=pin(runner),author=pin(Path(__file__).resolve()),source_module_load_order=[*names,validator.stem],logical_role_keys_are_harness_only=True,source_tests_before_this_binding=0,scope='Metadata-only actual source/pure binding. No target API, source closure, real entry or physical output authority.',all_real_qualification_flags_false=True))
 freeze=publish('INDEXED-ACCOUNTING-INDEPENDENT-RUN-FREEZE-v3.json',dict(schema_version=3,status='ACTUAL_COHERENT_SOURCE_MODULE_AND_DEPENDENCY_MAP_FROZEN_BEFORE_FIRST_INDEPENDENT_RUN',recorded_at_utc=datetime.now(timezone.utc).isoformat(),binding=binding,runner=pin(runner),sources=pins,test_sources=test_pins,precode_source_and_expectations_predate_V3=True,planned_methods=15,planned_histories=48,planned_same8_regressions=8,planned_precode_controls=6,author16_separate=True,source_tests_before_this_freeze=0,actual_target_API_calls=0,original_payload_operations=0,runtime_authorized=False))
 print(json.dumps(dict(binding=binding,freeze=freeze,runner=pin(runner))))
if __name__=='__main__':main()
