"""Independent source-version runner; no expected literal is changed."""
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
import types
import unittest

HERE=Path(__file__).resolve().parent

def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def load_harness(name,filename,digest):
 raw=(HERE/filename).read_bytes()
 if hashlib.sha256(raw).hexdigest()!=digest:raise RuntimeError('harness pin '+filename)
 if name in sys.modules:raise RuntimeError('unexpected cached harness')
 module=types.ModuleType(name);module.__file__=str(HERE/filename);sys.modules[name]=module
 exec(compile(raw,module.__file__,'exec'),module.__dict__)
 return module

def run(version,include48,report_filename,entry_path):
 report_path=HERE/report_filename;assert not report_path.exists()
 started=time.monotonic();D=None;pins={}
 try:
  D=load_harness('independent_shared_driver_v2','shared_owner_fixture_driver_v2.py','a97ae3ca57ce6f1b97e5a382a4051714242621c11b3d1756262f1f8025c8f566')
  R=load_harness('independent_shared_regressions_v2','shared_owner_five_regressions_v2.py','8fc70bcfa3a12ffd4bcae0c5fd3ba6c856960f4044bef3856d5f19537fc4367d')
  fixture,schema,public,cohort=D.literals()
  values={
   1:[('shared_owner_v1',36450,'76384e02282b1ce2437b9ff342913297f58ea0858752308724bef912b9e2643b'),('shared_file_ports_v1',10636,'d80f980c771e11ba0116aa3a1a8e526015ce43cafeacc6cf8bc2890f86b4c900'),('continue_verification_v1',4258,'7f52397a8293ae133f019ede1da78881814eb547b026768f072a34e4a4cf8eb2')],
   2:[('shared_owner_v2',36956,'0ecb8c02e3a8016f2de3a69650b34776de312ffca6f37ded85a31eba9c50c24b'),('shared_file_ports_v2',10595,'a224bfb9e9f33bf2f6b9329f0b337d0076bdab418083d05deb3f59b52722a059'),('continue_verification_v2',4258,'1d05a7398fe215cae987a76ab3960e0dc3730b89fad79caca64c466bac1f4b2f')],
  }[version]
  pins={'shared_owner_snapshot_validator_v1':dict(path=str(HERE/'shared_owner_snapshot_validator_v1.py'),bytes=26053,sha256='afa71df1ebba3eb7da83890b6e86675597894600cd593578b34f5f1a12cefefc')}
  for name,size,digest in values:pins[name]=dict(path=str(HERE/(name+'.py')),bytes=size,sha256=digest)
  loaded=D.load_exact_modules(pins)
  # Logical harness roles only; NEVER install old-name sys.modules aliases.
  modules={'shared_owner_v1':loaded[values[0][0]],'shared_file_ports_v1':loaded[values[1][0]],'continue_verification_v1':loaded[values[2][0]],'shared_owner_snapshot_validator_v1':loaded['shared_owner_snapshot_validator_v1']}
  runs=[];focused=[]
  tests=unittest.TestSuite()
  if include48:
   class Actual48(unittest.TestCase):
    def test_all48_actual_histories_unchanged(self):
     for case in fixture['cases']:
      with self.subTest(history=case['id']):
       if time.monotonic()-started>60:raise TimeoutError('actual suite60s cap')
       result=D.FrozenRun(modules,loaded['shared_owner_snapshot_validator_v1'],fixture,schema,public,cohort,case).run();runs.append(result)
       self.assertTrue(result['matched'],json.dumps(dict(differences=result['differences'],protocol_errors=result['protocol_errors'],violations=result['violations']),sort_keys=True))
     self.assertEqual(len(runs),48)
   tests.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Actual48))
  family_class=R.make_tests(D,modules,fixture,public,cohort,loaded['shared_owner_snapshot_validator_v1'],focused)
  tests.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(family_class))
  result=unittest.TextTestRunner(verbosity=1).run(tests)
  dependencies=['SHARED-OWNER-INTEGRATION-FIXTURES-v3.json','SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json','SHARED-OWNER-INTEGRATION-FIXTURE-FREEZE-v3.json','SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json','SHARED-OWNER-ROOT-CORRECTION-SCOPE-v2.json','SHARED-OWNER-SOURCE-INDEPENDENT-HOLD-v1.json','SHARED-OWNER-INTEGRATION-ACTUAL-FIRST-PROOF-v1.json','SHARED-OWNER-LATE-SEAL-FIRST-FINDING-v1.json','SHARED-OWNER-SNAPSHOT-VALIDATOR-INDEPENDENT-PEER-v1.json']
  dependencies.append('SHARED-OWNER-FIRST-SOURCE-PAUSE-v1.json' if version==1 else 'SHARED-OWNER-SOURCE-PAUSE-v2.json')
  status='passed' if result.wasSuccessful() else 'expected_before_failures' if version==1 and result.failures and not result.errors else 'failed'
  report=dict(schema_version=2,status=status,source_version=version,methods=result.testsRun,failures=[dict(test=str(t),detail=d) for t,d in result.failures],errors=[dict(test=str(t),detail=d) for t,d in result.errors],source_pins=pins,source_unchanged={name:pin(Path(v['path']))==v for name,v in pins.items()},driver=pin(HERE/'shared_owner_fixture_driver_v2.py'),regressions=pin(HERE/'shared_owner_five_regressions_v2.py'),runner=pin(Path(__file__).resolve()),entry=pin(entry_path),dependencies={n:pin(HERE/n) for n in dependencies},runs=runs,focused_observations=focused,histories_executed=len(runs),histories_matched=sum(r['matched'] for r in runs),snapshot_count=sum(len(r['snapshots']) for r in runs),actual_full48_fake_dispatches=sum(len(r['binding_records']) for r in runs),actual_full48_marker_execs=sum(len(r['marker_module_execs']) for r in runs),audit_denials=D.AUDIT_DENIALS,elapsed_seconds=time.monotonic()-started,chronology='Retrospective unchanged-v1 focused replay performed after v2 source existed; no pre-implementation-test claim.' if version==1 else 'Corrected coherent v2 source, unchanged frozen48 plus SAME8focused assertions.',module_policy='Fresh pinned actual version names only; private logical role dictionary supplies Runtime classes, no old-name sys.modules aliases/cache/source fallback.',harness_delta='V2 stop monitor also stops when raise_exception was recorded but injected binding returns normally; stricter failed-prefix monitor, not an oracle edit.',scope='Actual new Python SOURCE/PURE injected lifecycle. Four late-kind callbacks/readonly properties/known wrapper and compiler facts are deliberately focused controls. Default marker compiler executes exact captured141B in memory; late compiler failure control deliberately returns opaque object and earns NO source execution/acceptance.',actual_target_API_calls=0,old_payload_or_sourceclosure_operations=0,qualification=public['qualification_exact'])
  with report_path.open('xb') as out:out.write(D.canonical(report)+b'\n')
  print(json.dumps(dict(proof=pin(report_path),status=status,methods=result.testsRun,histories=len(runs),matched=report['histories_matched'],focused_observations=len(focused),failures=len(result.failures),errors=len(result.errors))))
  return 0 if result.wasSuccessful() or status=='expected_before_failures' else 1
 except BaseException as error:
  if not report_path.exists():
   failed=dict(status='setup_failed',error_class=type(error).__name__,message=str(error)[:2048],traceback=traceback.format_exc(),source_pins=pins,entry=pin(entry_path),runner=pin(Path(__file__).resolve()),elapsed_seconds=time.monotonic()-started,actual_target_API_calls=0,runtime_authorized=False)
   with report_path.open('xb') as out:out.write((json.dumps(failed,sort_keys=True,indent=2)+'\n').encode('utf-8'))
   print(json.dumps(dict(proof=pin(report_path),status='setup_failed',error=type(error).__name__)))
  raise
