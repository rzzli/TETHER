"""Once-only four pre-correction probes on preserved calculator V1 bytes."""
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
def checked(path,digest):
 raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,path.name;return raw
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('utf-8')
def module(name,path,digest):
 raw=checked(path,digest)
 if name in sys.modules:raise RuntimeError('cached regression harness')
 result=types.ModuleType(name);result.__file__=str(path);sys.modules[name]=result;exec(compile(raw,str(path),'exec'),result.__dict__);return result
def main():
 report_path=HERE/'ADMISSION-ENVELOPE-INDEPENDENT-REGRESSION-BEFORE-v1.json'
 if report_path.exists():raise RuntimeError('first pre-correction replay already retained')
 started=time.monotonic();record=None;observations=[];calls=[];R=None;pins={}
 try:
  freeze_path=HERE/'ADMISSION-ENVELOPE-REGRESSION-FREEZE-v1.json';freeze=json.loads(freeze_path.read_bytes())
  for name,expected in freeze['inputs'].items():assert pin(Path(expected['path']))==expected,name
  pins=dict(freeze['inputs']);pins[freeze_path.name]=pin(freeze_path)
  scope_path=HERE/'ADMISSION-ENVELOPE-ROOT-REGRESSION-SCOPE-v2.json';checked(scope_path,'f818874527df3702274cd67a00342081081295a856dc385d14bcc11693523bf1')
  assert not (HERE/'admission_envelope_v2.py').exists(),'this replay must predate correction source'
  R=module('retained_admission_codec_runner_v2',HERE/'run_admission_envelope_independent_v2.py','a2c60af1ff63c1c1bf8d21b0443be5dc54ac041dd9c90bfd048599c6a32d4265')
  assert 'A'.encode('utf-16-le','strict')==b'A\0' and R.ACTIVE[0]==0
  original_tests=R.load_test_module()
  fixture_path=HERE/'ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json';corpus=json.loads(checked(fixture_path,'cb4c6dd46cd8e02bc45c9bbec69a52f0a6ee1baea633eefaed85eeb018f57cc7'))
  source_path=HERE/'admission_envelope_v1.py';subject=R.load_subject(source_path,checked(source_path,'4c86530b2cab406d2a78bb707a9efdfab5533432d64ee34312c2ad6287124242'))
  test_pin=freeze['inputs']['admission_envelope_regressions_v1.py'];tests=module('independent_admission_four_regressions_v1',Path(test_pin['path']),test_pin['sha256'])
  def invoke(function,*args,**kwargs):
   if function is subject.analyze_admission:
    row=dict(ordinal=len(calls),check_calls=0,return_observed=False,exception_type=None);calls.append(row);original_check=kwargs['check']
    def check():row['check_calls']+=1;return original_check()
    kwargs=dict(kwargs,check=check)
    try:answer=R.active_call(function,*args,**kwargs);row['return_observed']=True;return answer
    except BaseException as error:row['exception_type']=type(error).__name__;raise
   return R.active_call(function,*args,**kwargs)
  suite=unittest.defaultTestLoader.loadTestsFromTestCase(tests.make_tests(subject,corpus,original_tests,invoke,observations))
  result=unittest.TextTestRunner(verbosity=2).run(suite)
  expected_before=result.testsRun==4 and len(result.failures)==4 and not result.errors and len(observations)==4
  record=dict(schema_version=1,status='EXPECTED_FOUR_SOURCE_BOUNDARY_FAILURES_RETAINED' if expected_before else 'UNEXPECTED_FIRST_REGRESSION_RESULT_RETAINED',methods=result.testsRun,failures=[dict(test=str(t),detail=d) for t,d in result.failures],errors=[dict(test=str(t),detail=d) for t,d in result.errors],observations=observations,actual_analysis_invocations=len(calls),actual_check_invocations=sum(row['check_calls'] for row in calls),analysis_calls=calls,source_and_harness_pins=pins,bytes_unchanged={n:pin(Path(v['path']))==v for n,v in pins.items()},runner=pin(Path(__file__).resolve()),audit_denials=R.AUDIT_DENIALS,closed_import_denials=R.IMPORT_DENIALS,elapsed_seconds=time.monotonic()-started,chronology='The exact four-method source/expectations froze before this replay and before any corrected admission_envelope_v2.py exists. Preserved source V1 only; original30/e670 unchanged.',instrumentation='Trusted CPython profiling observes only real source _object/code objects; exact built-in4096-key dict. No fake container, source-global replacement, guard removal or timing threshold. Profile restored before report getters.',scope='SOURCE/PURE pre-correction evidence only. No runtime stream/owner/FFI/source closure/resource authority.',qualification=dict(original_tests.QUALIFICATION),actual_target_API_calls=0,original_payload_operations=0,runtime_authorized=False)
 except BaseException as error:
  record=dict(status='FIRST_REGRESSION_SETUP_FAILURE_RETAINED',error_class=type(error).__name__,message=str(error)[:2048],traceback=traceback.format_exc(),observations=observations,analysis_calls=calls,pins=pins,runner=pin(Path(__file__).resolve()),audit_denials=[] if R is None else R.AUDIT_DENIALS,elapsed_seconds=time.monotonic()-started,actual_target_API_calls=0,original_payload_operations=0,runtime_authorized=False)
 finally:
  if record is not None:
   with report_path.open('xb') as out:out.write(canonical(record))
   print(json.dumps(dict(proof=pin(report_path),status=record['status'],methods=record.get('methods'),failures=len(record.get('failures',[])),errors=len(record.get('errors',[])))))
 return 0 if record and record['status']=='EXPECTED_FOUR_SOURCE_BOUNDARY_FAILURES_RETAINED' else 1
if __name__=='__main__':raise SystemExit(main())
