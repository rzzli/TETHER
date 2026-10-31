"""Independent actual V3 replay: SAME frozen48 + SAME8 + pre-code SAME6.

Fresh pinned source names only. No fixture expectations/fault labels reach
under-test components; injected original and sink monitors stay unchanged.
"""
import argparse
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
PRECODE=HERE.parent/'recovery-step9-production-preflight-20261029'
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def checked(path,digest):
 raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=digest:raise RuntimeError('pin mismatch '+path.name)
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
 parser=argparse.ArgumentParser();parser.add_argument('--binding-sha256',required=True);args=parser.parse_args()
 if len(args.binding_sha256)!=64 or any(c not in '0123456789abcdef' for c in args.binding_sha256):raise ValueError('exact binding hash')
 binding_path=HERE/'INDEXED-ACCOUNTING-INDEPENDENT-SOURCE-BINDING-v3.json'
 report_path=HERE/'INDEXED-ACCOUNTING-INDEPENDENT-ACTUAL-PROOF-v3.json'
 if report_path.exists():raise RuntimeError('first report already retained; no replay')
 started=time.monotonic();D=None;pins={};runs=[];focused=[];indexed=[];record=None
 try:
  binding=json.loads(checked(binding_path,args.binding_sha256))
  if binding['schema_version']!=3 or binding['mode']!='FROZEN_V3_SOURCE_SAME48_SAME8_PRECODE6_INDEXED':raise RuntimeError('binding role')
  for group in ('source_pins','dependencies'):
   for expected in binding[group].values():
    if set(expected)!={'path','bytes','sha256'} or pin(Path(expected['path']))!=expected:raise RuntimeError('binding leaf')
  root=binding['dependencies']['INDEXED-ACCOUNTING-ROOT-SOURCE-SCOPE-v3.json']
  if root['sha256']!='7683b6f661387b12e10ab2cbf83157b56dd3d5d5e2e4439d19e9804175196f97':raise RuntimeError('root scope')
  D=load('independent_indexed_actual_driver_v2',SHARED/'shared_owner_fixture_driver_v2.py','a97ae3ca57ce6f1b97e5a382a4051714242621c11b3d1756262f1f8025c8f566')
  R=load('independent_indexed_same8_v2',SHARED/'shared_owner_five_regressions_v2.py','8fc70bcfa3a12ffd4bcae0c5fd3ba6c856960f4044bef3856d5f19537fc4367d')
  T=load('independent_indexed_precode6_v2',PRECODE/'indexed_accounting_controls_v2.py','d76e1a2d7c70a9a42fa70c5f4989f08f2e291e79f12fa53b454250998c74bf5b')
  fixture,schema,public,cohort=D.literals()
  names=('shared_owner_v3','shared_file_ports_v3','continue_verification_v3')
  if set(binding['source_pins'])!=set((*names,'shared_owner_snapshot_validator_v1')):raise RuntimeError('exact coherent source map')
  pins={n:binding['source_pins'][n] for n in (*names,'shared_owner_snapshot_validator_v1')}
  loaded=D.load_exact_modules(pins)
  roles=dict(zip(('shared_owner_v1','shared_file_ports_v1','continue_verification_v1'),(loaded[n] for n in names)))
  validator=loaded['shared_owner_snapshot_validator_v1'];roles['shared_owner_snapshot_validator_v1']=validator
  suite=unittest.TestSuite()
  class Actual48(unittest.TestCase):
   def test_all48_actual_histories_unchanged(self):
    for case in fixture['cases']:
     with self.subTest(history=case['id']):
      if time.monotonic()-started>60:raise TimeoutError('independent suite60s safety cap')
      actual=D.FrozenRun(roles,validator,fixture,schema,public,cohort,case).run();runs.append(actual)
      self.assertTrue(actual['matched'],json.dumps(dict(differences=actual['differences'],protocol_errors=actual['protocol_errors'],violations=actual['violations']),sort_keys=True))
    self.assertEqual(len(runs),48)
  suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Actual48))
  suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(R.make_tests(D,roles,fixture,public,cohort,validator,focused)))
  suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(T.make_tests(D,roles,fixture,public,cohort,validator,indexed,indexed=True)))
  result=unittest.TextTestRunner(verbosity=2,resultclass=Results).run(suite)
  record=dict(schema_version=3,status='passed' if result.wasSuccessful() else 'FIRST_FAILURES_RETAINED',methods=result.testsRun,method_outcomes=result.outcomes,failures=[dict(test=str(t),detail=d) for t,d in result.failures],errors=[dict(test=str(t),detail=d) for t,d in result.errors],runs=runs,focused_same8_observations=focused,indexed_six_control_observations=indexed,histories_executed=len(runs),histories_matched=sum(r['matched'] for r in runs),snapshot_count=sum(len(r['snapshots']) for r in runs),actual_full48_fake_dispatches=sum(len(r['binding_records']) for r in runs),actual_full48_marker_execs=sum(len(r['marker_module_execs']) for r in runs),audit_denials=D.AUDIT_DENIALS,source_pins=pins,source_unchanged={n:pin(Path(v['path']))==v for n,v in pins.items()},test_pins={n:pin(Path(v['path'])) for n,v in binding['test_pins'].items()},test_unchanged={n:pin(Path(v['path']))==v for n,v in binding['test_pins'].items()},source_binding=pin(binding_path),runner=pin(Path(__file__).resolve()),dependencies=binding['dependencies'],elapsed_seconds=time.monotonic()-started,chronology='Pre-code source d76/protocolcccf/freeze52da and accepted-V2 BEFORE24da predate indexed implementation. This first actual V3 replay preserves the SAME48/SAME8/PRECODE6 expectations. Owner author12+4 are a separately run/pinned responsibility, not counted here.',module_policy='Fresh pinned actual V3 module names only; logical role keys supply the independent harness with no old-name sys.modules aliases, cached source fallback or alternative owners.',instrumentation='Six controls replace only the initially empty actual canonical registry call-list with CountingList. Original clocks/nonce/guards/source-issued refs/dispatch monitors unchanged. Clean hot windows distinct from explicitly measured canonical reporting/cleanup; static peer needed to rule out traversal bypass or hidden hot rebuild.',scope='Actual NEW Python SOURCE/PURE injected lifecycle and algorithm controls. Same toy captured141B module bodies may compile/exec in memory with closed resolver. No real FFI, production entry, full-roster fit, original-source authentication or profile eligibility.',qualification=public['qualification_exact'],actual_target_API_calls=0,original_payload_or_sourceclosure_operations=0)
 except BaseException as error:
  record=dict(schema_version=3,status='SETUP_OR_HARNESS_ERROR_FIRST_RESULT_PRESERVED',error_class=type(error).__name__,message=str(error)[:2048],traceback=traceback.format_exc(),runs=runs,focused_same8_observations=focused,indexed_six_control_observations=indexed,source_pins=pins,source_unchanged={n:pin(Path(v['path']))==v for n,v in pins.items()},runner=pin(Path(__file__).resolve()),elapsed_seconds=time.monotonic()-started,audit_denials=[] if D is None else D.AUDIT_DENIALS,actual_target_API_calls=0,original_payload_operations=0,runtime_authorized=False)
 finally:
  if record is not None:
   with report_path.open('xb') as out:out.write((json.dumps(record,sort_keys=True,indent=2)+'\n').encode('utf-8'))
   print(json.dumps(dict(proof=pin(report_path),status=record['status'],methods=record.get('methods'),histories=len(runs),matched=sum(r.get('matched',False) for r in runs),failures=len(record.get('failures',[])),errors=len(record.get('errors',[])))))
 return 0 if record and record['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
