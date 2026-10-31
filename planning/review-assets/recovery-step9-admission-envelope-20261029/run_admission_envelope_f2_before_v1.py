"""Once-only separately frozen F2 metaclass probe on preserved V2 source."""
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
def module(name,path,digest):
 raw=checked(path,digest)
 if name in sys.modules:raise RuntimeError('cached F2 harness')
 result=types.ModuleType(name);result.__file__=str(path);sys.modules[name]=result;exec(compile(raw,str(path),'exec'),result.__dict__);return result
def main():
 destination=HERE/'ADMISSION-ENVELOPE-F2-METACLASS-BEFORE-v1.json'
 if destination.exists():raise RuntimeError('first F2 replay already retained')
 started=time.monotonic();R=None;record=None;pins={};observations=[];calls=[]
 try:
  freeze_path=HERE/'ADMISSION-ENVELOPE-F2-METACLASS-FREEZE-v1.json';freeze=json.loads(freeze_path.read_bytes())
  for name,expected in freeze['inputs'].items():assert pin(Path(expected['path']))==expected,name
  pins=dict(freeze['inputs']);pins[freeze_path.name]=pin(freeze_path)
  scope=HERE/'ADMISSION-ENVELOPE-ROOT-F2-PROBE-SCOPE-v3.json';checked(scope,'940f439f8e1a8c9db50b2f60d2810ed9243db11baeba29e31996ff748a9b84c9')
  assert not (HERE/'admission_envelope_v3.py').exists(),'this probe must precede F2 correction source'
  R=module('retained_admission_f2_audit_v2',HERE/'run_admission_envelope_independent_v2.py','a2c60af1ff63c1c1bf8d21b0443be5dc54ac041dd9c90bfd048599c6a32d4265')
  assert R.ACTIVE[0]==0 and 'A'.encode('utf-16-le','strict')==b'A\0'
  original=R.load_test_module();corpus=json.loads(checked(HERE/'ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json','cb4c6dd46cd8e02bc45c9bbec69a52f0a6ee1baea633eefaed85eeb018f57cc7'))
  source_path=HERE/'admission_envelope_v2.py';raw=checked(source_path,'ea676476f37974e7e7c6c63062b27c798dec6874a3f8802f20229d13a0a71191')
  name='admission_envelope_v2'
  if name in sys.modules:raise RuntimeError('cached V2 source')
  subject=types.ModuleType(name);subject.__file__=str(source_path);subject.__package__=''
  allowed={'json':R.json,'re':R.re,'types':R.types}
  def importer(requested,globals=None,locals=None,fromlist=(),level=0):
   if level!=0 or requested not in allowed:R.IMPORT_DENIALS.append(dict(name=requested,level=level));raise ImportError('closed calculator import')
   return allowed[requested]
  subject.__dict__['__builtins__']=dict(vars(R.builtins),__import__=importer);sys.modules[name]=subject;R.active_call(exec,compile(raw,str(source_path),'exec'),subject.__dict__)
  test_pin=freeze['inputs']['admission_envelope_f2_metaclass_regression_v1.py'];tests=module('independent_admission_f2_probe_v1',Path(test_pin['path']),test_pin['sha256'])
  def invoke(function,*args,**kwargs):
   if function is subject.analyze_admission:
    row=dict(check_calls=0,return_observed=False);calls.append(row);original_check=kwargs['check']
    def check():row['check_calls']+=1;return original_check()
    answer=R.active_call(function,*args,**dict(kwargs,check=check));row['return_observed']=True;return answer
   return R.active_call(function,*args,**kwargs)
  result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(tests.make_tests(subject,corpus,original,invoke,observations)))
  expected=result.testsRun==1 and len(result.failures)==1 and not result.errors and len(observations)==1
  record=dict(schema_version=1,status='EXPECTED_F2_METACLASS_PROTOCOL_FAILURE_RETAINED' if expected else 'UNEXPECTED_FIRST_F2_RESULT_RETAINED',methods=result.testsRun,failures=[dict(test=str(t),detail=d) for t,d in result.failures],errors=[dict(test=str(t),detail=d) for t,d in result.errors],observations=observations,analysis_invocations=calls,actual_analysis_invocations=len(calls),actual_check_invocations=sum(row['check_calls'] for row in calls),inputs=pins,input_bytes_unchanged={n:pin(Path(v['path']))==v for n,v in pins.items()},runner=pin(Path(__file__).resolve()),audit_denials=R.AUDIT_DENIALS,closed_import_denials=R.IMPORT_DENIALS,elapsed_seconds=time.monotonic()-started,chronology='One F2 test and intended-green expectation froze before any named F2 source correction. This is the first probe on preserved V2; original30/e670/four5644 and first V2 combined result remain immutable.',qualification=dict(original.QUALIFICATION),actual_target_API_calls=0,original_payload_operations=0,runtime_authorized=False)
 except BaseException as error:
  record=dict(status='FIRST_F2_SETUP_FAILURE_RETAINED',error_class=type(error).__name__,message=str(error)[:2048],traceback=traceback.format_exc(),observations=observations,inputs=pins,runner=pin(Path(__file__).resolve()),audit_denials=[] if R is None else R.AUDIT_DENIALS,actual_target_API_calls=0,original_payload_operations=0,runtime_authorized=False)
 finally:
  if record is not None:
   with destination.open('xb') as out:out.write((json.dumps(record,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8'))
   print(json.dumps(dict(proof=pin(destination),status=record['status'],methods=record.get('methods'),failures=len(record.get('failures',[])),errors=len(record.get('errors',[])))))
 return 0 if record and record['status']=='EXPECTED_F2_METACLASS_PROTOCOL_FAILURE_RETAINED' else 1
if __name__=='__main__':raise SystemExit(main())
