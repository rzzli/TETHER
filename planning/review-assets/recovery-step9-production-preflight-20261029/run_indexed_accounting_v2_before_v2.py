"""Fresh accepted-V2 pure BEFORE replay of already frozen six controls.

No prospective indexed source is imported. Test expectations are immutable
pre-code data. Report is exclusive, including setup errors or test failures.
"""
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
import types
import unittest

HERE=Path(__file__).resolve().parent
SHARED=HERE.parent/'recovery-step9-shared-owner-20261029'
REPORT=HERE/'INDEXED-ACCOUNTING-ACTUAL-V2-BEFORE-PROOF-v2.json'
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def checked(path,digest):
 raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=digest:raise RuntimeError('pin mismatch: '+path.name)
 return raw
def load(name,path,digest):
 raw=checked(path,digest)
 if name in sys.modules:raise RuntimeError('unexpected cached harness '+name)
 module=types.ModuleType(name);module.__file__=str(path);sys.modules[name]=module
 exec(compile(raw,str(path),'exec'),module.__dict__)
 return module
class Results(unittest.TextTestResult):
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.outcomes=[]
 def addSuccess(self,test):self.outcomes.append(dict(test=str(test),status='passed'));super().addSuccess(test)
 def addFailure(self,test,error):self.outcomes.append(dict(test=str(test),status='failed_assertion'));super().addFailure(test,error)
 def addError(self,test,error):self.outcomes.append(dict(test=str(test),status='error'));super().addError(test,error)
def main():
 if REPORT.exists():raise RuntimeError('first result already retained; no repeat')
 started=time.monotonic();observations=[];D=None;pins={};record=None
 try:
  freeze=json.loads(checked(HERE/'INDEXED-ACCOUNTING-PRECODE-CONTROL-FREEZE-v2.json','52da9451c215d50f4b3e559a47eb4c286dd7e33fc884b8bf67430d9e6ac9703d'))
  contract=json.loads(checked(HERE/'INDEXED-ACCOUNTING-PRECODE-TEST-CONTRACT-v2.json','cccf8a1f4f6219ff51ade0279e82f587cfbe76c969e1be69125c0cc72ff2a3bd'))
  for group in (contract['accepted_pins'],contract['extra_accepted_pins'],contract['design']):
   for expected in group.values():assert pin(Path(expected['path']))==expected
  D=load('independent_indexed_baseline_driver_v2',SHARED/'shared_owner_fixture_driver_v2.py','a97ae3ca57ce6f1b97e5a382a4051714242621c11b3d1756262f1f8025c8f566')
  T=load('independent_indexed_precode_controls_v2',HERE/'indexed_accounting_controls_v2.py',contract['test_source']['sha256'])
  fixture,schema,public,cohort=D.literals()
  role_names=('shared_owner_v2','shared_file_ports_v2','continue_verification_v2')
  pins={name:contract['accepted_pins'][name+'.py'] for name in role_names}
  pins['shared_owner_snapshot_validator_v1']=contract['extra_accepted_pins']['shared_owner_snapshot_validator_v1.py']
  loaded=D.load_exact_modules(pins)
  roles=dict(zip(('shared_owner_v1','shared_file_ports_v1','continue_verification_v1'),(loaded[n] for n in role_names)))
  roles['shared_owner_snapshot_validator_v1']=loaded['shared_owner_snapshot_validator_v1']
  Controls=T.make_tests(D,roles,fixture,public,cohort,loaded['shared_owner_snapshot_validator_v1'],observations,indexed=False)
  result=unittest.TextTestRunner(verbosity=2,resultclass=Results).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
  expected_names=('test_01_clean_handle_no_global_scan','test_02_clean_known_bytes_no_global_scan','test_03_real_ref_guard_no_membership_scan','test_04_real_read_admission_no_global_quota_scan')
  failed_names={str(test).split(' ',1)[0] for test,_ in result.failures}
  expected_before=result.testsRun==6 and len(result.failures)==4 and not result.errors and failed_names==set(expected_names)
  record=dict(schema_version=1,status='EXPECTED_ACTUAL_V2_HOT_SCAN_FAILURES_FUNCTIONAL_RAW_CHECKS_PASS' if expected_before else 'UNEXPECTED_FIRST_RESULT_PRESERVED',methods=result.testsRun,method_outcomes=result.outcomes,failures=[dict(test=str(test),detail=detail) for test,detail in result.failures],errors=[dict(test=str(test),detail=detail) for test,detail in result.errors],observations=observations,audit_denials=D.AUDIT_DENIALS,source_pins=pins,source_unchanged={n:pin(Path(v['path']))==v for n,v in pins.items()},test_source=pin(HERE/'indexed_accounting_controls_v2.py'),runner=pin(Path(__file__).resolve()),freeze=pin(HERE/'INDEXED-ACCOUNTING-PRECODE-CONTROL-FREEZE-v2.json'),contract=pin(HERE/'INDEXED-ACCOUNTING-PRECODE-TEST-CONTRACT-v2.json'),dependencies={n:pin(HERE/n) for n in contract['design']},accepted_harness=pin(SHARED/'shared_owner_fixture_driver_v2.py'),elapsed_seconds=time.monotonic()-started,chronology='Test source+protocol froze before this first v2-control accepted-V2 replay (v1 first replay remains preserved) and before prospective indexed V3 code. Failure expectations were frozen from source/design, not generated from these observations.',source_mode='accepted_v2_actual_append_and_raw_store_boundaries_no_missing_future_API',instrumentation='HARNESS_ONLY actual empty canonical list replacement before first fact. Actual source operations counted; named cold reports allowed. No subject clock/guard/binding monitor replaced.',limits='Deterministic list access evidence for these fixed valid N3 worlds, not timing or a full-roster-fit proof. Future source peer must rule out instrumentation bypass and hidden hot rebuild. Two prospective-cache failure submodes are not V2 observations.',qualification=public['qualification_exact'],actual_target_API_calls=0,original_payload_or_sourceclosure_operations=0,prospective_source_executed=False)
 except BaseException as error:
  record=dict(schema_version=1,status='SETUP_OR_HARNESS_ERROR_FIRST_RESULT_PRESERVED',error_class=type(error).__name__,message=str(error)[:2048],traceback=traceback.format_exc(),observations=observations,source_pins=pins,source_unchanged={n:pin(Path(v['path']))==v for n,v in pins.items()},runner=pin(Path(__file__).resolve()),elapsed_seconds=time.monotonic()-started,audit_denials=[] if D is None else D.AUDIT_DENIALS,actual_target_API_calls=0,original_payload_operations=0,implementation_authorized=False)
 finally:
  if record is not None:
   with REPORT.open('xb') as out:out.write((json.dumps(record,sort_keys=True,indent=2)+'\n').encode('utf-8'))
   print(json.dumps(dict(proof=pin(REPORT),status=record['status'],methods=record.get('methods'),failures=len(record.get('failures',[])),errors=len(record.get('errors',[])))))
 return 0 if record and record['status']=='EXPECTED_ACTUAL_V2_HOT_SCAN_FAILURES_FUNCTIONAL_RAW_CHECKS_PASS' else 1

if __name__=='__main__':raise SystemExit(main())
