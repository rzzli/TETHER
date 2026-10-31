"""FIRST independent actual48 run; exclusive report preserves all failures."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
import types
import unittest

HERE=Path(__file__).resolve().parent
REPORT=HERE/'SHARED-OWNER-INTEGRATION-ACTUAL-FIRST-PROOF-v1.json'
STARTED=time.monotonic()

def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
 assert not REPORT.exists()
 driver_path=HERE/'shared_owner_fixture_driver_v1.py'
 raw=driver_path.read_bytes()
 assert hashlib.sha256(raw).hexdigest()=='33cc4283e95c82b3fc293b36b0e8eeadf30f4233a7e54fd1d9f77db7c15639ae'
 driver=types.ModuleType('independent_shared_owner_driver_v1');driver.__file__=str(driver_path)
 sys.modules[driver.__name__]=driver
 exec(compile(raw,str(driver_path),'exec'),driver.__dict__)
 fixture,schema,public,cohort=driver.literals()
 pins={
  'shared_owner_snapshot_validator_v1':dict(path=str(HERE/'shared_owner_snapshot_validator_v1.py'),bytes=26053,sha256='afa71df1ebba3eb7da83890b6e86675597894600cd593578b34f5f1a12cefefc'),
  'shared_owner_v1':dict(path=str(HERE/'shared_owner_v1.py'),bytes=36450,sha256='76384e02282b1ce2437b9ff342913297f58ea0858752308724bef912b9e2643b'),
  'shared_file_ports_v1':dict(path=str(HERE/'shared_file_ports_v1.py'),bytes=10636,sha256='d80f980c771e11ba0116aa3a1a8e526015ce43cafeacc6cf8bc2890f86b4c900'),
  'continue_verification_v1':dict(path=str(HERE/'continue_verification_v1.py'),bytes=4258,sha256='7f52397a8293ae133f019ede1da78881814eb547b026768f072a34e4a4cf8eb2'),
 }
 for expected in pins.values():assert pin(Path(expected['path']))==expected
 modules=driver.load_exact_modules(pins)
 runs=[]
 class ActualTests(unittest.TestCase):
  def test_all48_actual_histories_once(self):
   for case in fixture['cases']:
    with self.subTest(history=case['id']):
     if time.monotonic()-STARTED>60:raise TimeoutError('independent actual48 harness60s cap')
     run=driver.FrozenRun(modules,modules['shared_owner_snapshot_validator_v1'],fixture,schema,public,cohort,case)
     result=run.run();runs.append(result)
     self.assertTrue(result['matched'],json.dumps(dict(differences=result['differences'],protocol_errors=result['protocol_errors'],violations=result['violations']),sort_keys=True))
   self.assertEqual(len(runs),48)
 result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(ActualTests))
 dependencies=['SHARED-OWNER-INTEGRATION-FIXTURES-v3.json','SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json','SHARED-OWNER-INTEGRATION-FIXTURE-FREEZE-v3.json','SHARED-OWNER-ROOT-SOURCE-SCOPE-v1.json','SHARED-OWNER-FIRST-SOURCE-PAUSE-v1.json','SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json','SHARED-OWNER-LITERAL-INDEPENDENT-PEER-v3.json','SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json','SHARED-OWNER-SNAPSHOT-VALIDATOR-PURE-PROBES-FIRST-v1.json','SHARED-OWNER-SNAPSHOT-VALIDATOR-INDEPENDENT-PEER-v1.json']
 report=dict(schema_version=1,status='passed' if result.wasSuccessful() else 'failed',methods=result.testsRun,
  failures=[dict(test=str(t),detail=d) for t,d in result.failures],errors=[dict(test=str(t),detail=d) for t,d in result.errors],source_pins=pins,source_unchanged={name:pin(Path(v['path']))==v for name,v in pins.items()},driver=pin(driver_path),checker=pin(Path(__file__).resolve()),dependencies={n:pin(HERE/n) for n in dependencies},runs=runs,histories_executed=len(runs),histories_matched=sum(r['matched'] for r in runs),snapshot_count=sum(len(r['snapshots']) for r in runs),actual_injected_original_dispatches=sum(len(r['binding_records']) for r in runs),actual_fictional_sink_callbacks=sum(len(r['sink_records']) for r in runs),actual_captured_marker_module_execs=sum(len(r['marker_module_execs']) for r in runs),actual_marker_function_calls=sum(len(r['marker_function_calls']) for r in runs),audit_denials=driver.AUDIT_DENIALS,elapsed_seconds=time.monotonic()-STARTED,python_version=sys.version,source_import_policy='Only fresh exact pinned NEW modules registered for dataclasses, closed source imports; trusted preloaded stdlib dataclasses/hashlib/json/math/types/struct; no cached own-module/source fallback.',scope='Actual three new pure Python components under injected synthetic lifecycle only. Captured141B toy source bodies compiled/executed in memory through exact closed resolver. No model/native/Win32/FFI/old-source qualification or physical sink operations.',actual_target_API_calls=0,old_payload_or_sourceclosure_operations=0,qualification=public['qualification_exact'])
 with REPORT.open('xb') as out:out.write(driver.canonical(report)+b'\n')
 print(json.dumps(dict(proof=pin(REPORT),status=report['status'],histories=report['histories_executed'],matched=report['histories_matched'],snapshots=report['snapshot_count'],fake_original_dispatches=report['actual_injected_original_dispatches'],marker_execs=report['actual_captured_marker_module_execs'])))
 return 0 if result.wasSuccessful() else 1

if __name__=='__main__':
 try:code=main()
 except BaseException as error:
  if not REPORT.exists():
   detail=dict(schema_version=1,status='setup_failed',error_class=type(error).__name__,message=str(error)[:2048],traceback=traceback.format_exc(),checker=pin(Path(__file__).resolve()),elapsed_seconds=time.monotonic()-STARTED,actual_target_API_calls=0,runtime_authorized=False,scope='Initial harness/setup failure retained; no actual48 pass asserted.')
   with REPORT.open('xb') as out:out.write((json.dumps(detail,sort_keys=True,indent=2)+'\n').encode('utf-8'))
   print(json.dumps(dict(proof=pin(REPORT),status='setup_failed',error=type(error).__name__)))
  raise
 raise SystemExit(code)
