"""First-result independent runner for one future pinned pure calculator.

Importing this harness does not import a subject. Execution requires exact
root scope and source pause pins; no old modules or file-source fallback.
"""
import argparse
import builtins
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import traceback
import types
import unittest

HERE=Path(__file__).resolve().parent
PREFLIGHT=HERE.parent/'recovery-step9-production-preflight-20261029'
ROOT_SHA='30644e8c0b59356b7dda2f9fde30f366fec80638945d051dc4c5baed1e8f74c3'
ACTIVE=[0]
AUDIT_DENIALS=[]
IMPORT_DENIALS=[]
def audit(event,args):
 if ACTIVE[0] and (event=='open' or event.startswith(('ctypes.','subprocess.','socket.','winreg.')) or event in ('os.system','os.startfile','os.listdir','os.scandir','os.remove','os.rename','os.mkdir','os.rmdir','os.symlink','os.link','os.chmod','os.chdir')):
  AUDIT_DENIALS.append(event)
  raise AssertionError('unexpected operation during pure subject invocation: '+event)
sys.addaudithook(audit)

def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def checked(path,digest):
 raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=digest:raise RuntimeError('pin mismatch: '+path.name)
 return raw
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('utf-8')
def active_call(function,*args,**kwargs):
 ACTIVE[0]+=1
 try:return function(*args,**kwargs)
 finally:ACTIVE[0]-=1
def load_test_module():
 path=HERE/'admission_envelope_independent_tests_v1.py';raw=checked(path,'e670199a7c4c50dc7eb540f8e5a021919464e67a891ef00fa48902d21b783bcc')
 name='independent_admission_test_source_v1'
 if name in sys.modules:raise RuntimeError('cached test module')
 module=types.ModuleType(name);module.__file__=str(path);sys.modules[name]=module
 exec(compile(raw,str(path),'exec'),module.__dict__)
 return module
def load_subject(source_path,raw):
 name='admission_envelope_v1'
 if name in sys.modules:raise RuntimeError('cached subject module')
 allowed={'json':json,'re':re,'types':types}
 def closed_import(requested,globals=None,locals=None,fromlist=(),level=0):
  if level!=0 or requested not in allowed:
   IMPORT_DENIALS.append(dict(name=requested,level=level))
   raise ImportError('closed calculator import: '+requested)
  return allowed[requested]
 module=types.ModuleType(name);module.__file__=str(source_path);module.__package__=''
 module.__dict__['__builtins__']=dict(vars(builtins),__import__=closed_import)
 sys.modules[name]=module
 active_call(exec,compile(raw,str(source_path),'exec'),module.__dict__)
 return module

class Results(unittest.TextTestResult):
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.outcomes=[]
 def addSuccess(self,test):self.outcomes.append(dict(test=str(test),status='passed'));super().addSuccess(test)
 def addFailure(self,test,error):self.outcomes.append(dict(test=str(test),status='failure'));super().addFailure(test,error)
 def addError(self,test,error):self.outcomes.append(dict(test=str(test),status='error'));super().addError(test,error)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source-sha256',required=True);parser.add_argument('--source-pause-sha256',required=True);args=parser.parse_args()
 for digest in (args.source_sha256,args.source_pause_sha256):
  if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise ValueError('exact hash required')
 destination=HERE/'ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v2.json'
 if destination.exists():raise RuntimeError('first result retained; no repeat')
 started=time.monotonic();record=None;pins={};observations=[];analysis_calls=[];getter_calls=[];bootstrap_codec_probe=None
 try:
  root_path=HERE/'ADMISSION-ENVELOPE-ROOT-SOURCE-SCOPE-v1.json';root=json.loads(checked(root_path,ROOT_SHA));pins[root_path.name]=pin(root_path)
  if root['subject_path']!=str(HERE/'admission_envelope_v1.py') or root['source_implementation_authorized'] is not True or root['pure_subject_tests_authorized'] is not True or root['actual_runtime_authorized'] is not False:raise RuntimeError('root source role')
  for name,expected in root['inputs'].items():
   if Path(name).name!=name or expected['path'] not in (str(HERE/name),str(PREFLIGHT/name)):raise RuntimeError('technical dependency locator')
   if set(expected)!={'path','bytes','sha256'} or pin(Path(expected['path']))!=expected:raise RuntimeError('technical dependency pin')
   pins[name]=expected
  pause_path=HERE/'ADMISSION-ENVELOPE-SOURCE-PAUSE-v1.json';pause=json.loads(checked(pause_path,args.source_pause_sha256));pins[pause_path.name]=pin(pause_path)
  source_path=HERE/'admission_envelope_v1.py';source_pin=pin(source_path)
  if source_pin['sha256']!=args.source_sha256 or pause['source']!=source_pin:raise RuntimeError('paused source pin')
  source_raw=checked(source_path,args.source_sha256);pins[source_path.name]=source_pin
  corpus_path=HERE/'ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json';fixtures=json.loads(checked(corpus_path,'cb4c6dd46cd8e02bc45c9bbec69a52f0a6ee1baea633eefaed85eeb018f57cc7'))
  # Root-authorized trusted bootstrap only; ACTIVE is still zero and the
  # source has not loaded. This does not exempt any active invocation IO.
  correction_path=HERE/'ADMISSION-ENVELOPE-ROOT-RUNNER-CORRECTION-v2.json'
  checked(correction_path,'97194dda516b87ef6f65f88b0b3c2dc77a006c16393c2d39342422efbd40daff');pins[correction_path.name]=pin(correction_path)
  first_path=HERE/'ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v1.json'
  checked(first_path,'003b948178c36037557a69fb2d945e36dcf0f13db21b5a9081e65f65c6801e68');pins[first_path.name]=pin(first_path)
  old_runner=HERE/'run_admission_envelope_independent_v1.py'
  checked(old_runner,'3f9f87afb4fdc94b96a2a44df9206cbf20e27b64bbeefda3a37d31518a105d28');pins[old_runner.name]=pin(old_runner)
  if ACTIVE[0]!=0:raise RuntimeError('codec bootstrap under active audit')
  codec_probe='A'.encode('utf-16-le','strict')
  if codec_probe!=b'A\x00':raise RuntimeError('trusted UTF16LE probe')
  bootstrap_codec_probe=dict(codec='utf-16-le',literal='A',encoded_hex=codec_probe.hex(),active_depth=0,before_subject_load=True,scope='trusted standard-library lazy codec initialization, not a subject IO exemption')
  tests=load_test_module();subject=load_subject(source_path,source_raw)
  def invoke(function,*values,**kwargs):
   if function is subject.analyze_admission:
    row=dict(ordinal=len(analysis_calls),metadata_sha256=hashlib.sha256(canonical(values[0])).hexdigest(),check_callable=callable(kwargs.get('check')),check_calls=0,check_returns=0,check_exceptions=0,check_exception_types=[],return_observed=False,exception_type=None,check_exception_propagated_by_identity=None)
    analysis_calls.append(row);observed_exceptions=[]
    original_check=kwargs.get('check')
    if callable(original_check):
     def observed_check():
      row['check_calls']+=1
      try:answer=original_check()
      except BaseException as error:
       row['check_exceptions']+=1;row['check_exception_types'].append(type(error).__name__);observed_exceptions.append(error)
       raise
      row['check_returns']+=1;return answer
     kwargs=dict(kwargs,check=observed_check)
    try:
     answer=active_call(function,*values,**kwargs);row['return_observed']=True
     if observed_exceptions:row['check_exception_propagated_by_identity']=False
     return answer
    except BaseException as error:
     row['exception_type']=type(error).__name__
     if observed_exceptions:row['check_exception_propagated_by_identity']=any(error is value for value in observed_exceptions)
     raise
   getter=dict(name=getattr(function,'__name__','unknown'),return_observed=False,exception_type=None);getter_calls.append(getter)
   try:answer=active_call(function,*values,**kwargs);getter['return_observed']=True;return answer
   except BaseException as error:getter['exception_type']=type(error).__name__;raise
  suite=unittest.defaultTestLoader.loadTestsFromTestCase(tests.make_tests(subject,fixtures,invoke,observations))
  result=unittest.TextTestRunner(verbosity=2,resultclass=Results).run(suite)
  matched=[o for o in observations if 'vector' in o]
  stable={name:pin(Path(value['path']))==value for name,value in pins.items()}
  identity_errors=[row for row in analysis_calls if row['check_exception_propagated_by_identity'] is False]
  passed=result.wasSuccessful() and len(matched)==30 and not AUDIT_DENIALS and not IMPORT_DENIALS and all(stable.values()) and not identity_errors
  record=dict(schema_version=1,status='passed' if passed else 'FIRST_FAILURES_RETAINED',methods=result.testsRun,method_outcomes=result.outcomes,failures=[dict(test=str(t),detail=d) for t,d in result.failures],errors=[dict(test=str(t),detail=d) for t,d in result.errors],observations=observations,unique_frozen_metadata_vectors=30,matched_vector_count=len(matched),actual_analysis_invocations=len(analysis_calls),actual_analysis_normal_returns=sum(row['return_observed'] for row in analysis_calls),actual_analysis_exceptions=sum(row['exception_type'] is not None for row in analysis_calls),actual_check_invocations=sum(row['check_calls'] for row in analysis_calls),actual_check_normal_returns=sum(row['check_returns'] for row in analysis_calls),actual_check_exceptions=sum(row['check_exceptions'] for row in analysis_calls),original_check_exception_identity_failures=identity_errors,analysis_invocations=analysis_calls,report_getter_invocations=getter_calls,audit_denials=list(AUDIT_DENIALS),closed_import_denials=list(IMPORT_DENIALS),inputs=pins,input_bytes_unchanged=stable,runner=pin(Path(__file__).resolve()),elapsed_seconds=time.monotonic()-started,bootstrap_codec_probe=bootstrap_codec_probe,qualification=fixtures['vectors'][0]['expected']['qualification'],scope='One NEW pure metadata calculator and frozen tests. Logical bounds and encoded calculator reports only; no runtime/resource/producer/original/source/FFI/profile qualification.',counting='Thirty distinct encoded metadata vectors are separate from actual analyze/check/getter and exception invocations. Interface and mutation/check controls reuse frozen metadata. Audit monitors preserve denied attempts even if subject catches them.',loader='Fresh admission_envelope_v1 only from same verified bytes; trusted preloaded json/re/types only, closed imports, no cached source fallback. Ordinary injected pure checks remain opaque callbacks; wrapper preserves each raised exception object.',chronology='Expectations and test module froze before implementation. This is the separately named runner-v2 replay after the retained v1 trusted-codec bootstrap failure. Source, oracle, active audit and closed imports are unchanged. Author controls are separate evidence.',limitations=['Audit covers operations during actual NEW source definition/invocations and calculator checks, not a hostile-Python security sandbox or physical resource bound.','No measured RSS/time/throughput or actual first-entry owner/source-roster authority; no current runtime cap lift or application change.','No stream/Sink/OS/model/native/output/source-closure replay.'],actual_target_API_calls=0,original_payload_or_sourceclosure_operations=0,application_changed=False,runtime_authorized=False)
 except BaseException as error:
  record=dict(schema_version=1,status='FIRST_SETUP_OR_SUBJECT_FAILURE_RETAINED',error_class=type(error).__name__,message=str(error)[:2048],traceback=traceback.format_exc(),observations=observations,analysis_invocations=analysis_calls,report_getter_invocations=getter_calls,inputs=pins,runner=pin(Path(__file__).resolve()),audit_denials=list(AUDIT_DENIALS),closed_import_denials=list(IMPORT_DENIALS),elapsed_seconds=time.monotonic()-started,bootstrap_codec_probe=bootstrap_codec_probe,actual_target_API_calls=0,original_payload_operations=0,runtime_authorized=False)
 finally:
  if record is not None:
   with destination.open('xb') as out:out.write(canonical(record))
   print(json.dumps(dict(proof=pin(destination),status=record['status'],methods=record.get('methods'),metadata_vectors=30,actual_analysis_invocations=len(analysis_calls),actual_check_invocations=sum(row['check_calls'] for row in analysis_calls))))
 return 0 if record and record['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
