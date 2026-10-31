"""First coherent V2-source replay: original30/four methods + same focused4."""
import builtins
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
import types
import unittest
HERE=Path(__file__).resolve().parent
PREFLIGHT=HERE.parent/'recovery-step9-production-preflight-20261029'
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def checked(path,digest):
 raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,path.name;return raw
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('utf-8')
def load_harness(name,path,digest):
 raw=checked(path,digest)
 if name in sys.modules:raise RuntimeError('cached harness module')
 module=types.ModuleType(name);module.__file__=str(path);sys.modules[name]=module;exec(compile(raw,str(path),'exec'),module.__dict__);return module
def main():
 destination=HERE/'ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v3.json'
 if destination.exists():raise RuntimeError('first V2-source replay already retained')
 started=time.monotonic();R=None;record=None;pins={};observations=[];focused=[];calls=[];getters=[]
 try:
  for filename,digest in (
   ('ADMISSION-ENVELOPE-ROOT-SOURCE-SCOPE-v1.json','30644e8c0b59356b7dda2f9fde30f366fec80638945d051dc4c5baed1e8f74c3'),
   ('ADMISSION-ENVELOPE-ROOT-CORRECTION-SCOPE-v2.json','82ff068c7ab2d6864da45a6f547b1266adbb5e278e4412092a3c23930fe3f39b'),
  ):
   path=HERE/filename;authority=json.loads(checked(path,digest));pins[filename]=pin(path)
   for name,expected in authority['inputs'].items():
    if Path(name).name!=name or expected['path'] not in (str(HERE/name),str(PREFLIGHT/name)):raise RuntimeError('technical locator')
    if pin(Path(expected['path']))!=expected:raise RuntimeError('technical pin')
    if name in pins and pins[name]!=expected:raise RuntimeError('conflicting dependency')
    pins[name]=expected
  correction=authority
  if correction['target']!=str(HERE/'admission_envelope_v2.py') or correction['source_correction_authorized'] is not True:raise RuntimeError('correction role')
  pause_path=HERE/'ADMISSION-ENVELOPE-SOURCE-PAUSE-v2.json';pause=json.loads(checked(pause_path,'075026212bb247cc0655ed4fb517b2b8d28059adbb0dfd8c415b9276f84d971b'));pins[pause_path.name]=pin(pause_path)
  source_path=HERE/'admission_envelope_v2.py';raw=checked(source_path,'ea676476f37974e7e7c6c63062b27c798dec6874a3f8802f20229d13a0a71191');pins[source_path.name]=pin(source_path)
  if pause['source']!=pins[source_path.name]:raise RuntimeError('coherent source pause')
  helper_path=HERE/'run_admission_envelope_independent_v2.py';pins[helper_path.name]=pin(helper_path)
  R=load_harness('retained_admission_audit_utilities_v2',helper_path,'a2c60af1ff63c1c1bf8d21b0443be5dc54ac041dd9c90bfd048599c6a32d4265')
  codec_path=HERE/'ADMISSION-ENVELOPE-ROOT-RUNNER-CORRECTION-v2.json';checked(codec_path,'97194dda516b87ef6f65f88b0b3c2dc77a006c16393c2d39342422efbd40daff');pins[codec_path.name]=pin(codec_path)
  if R.ACTIVE[0]!=0 or 'A'.encode('utf-16-le','strict')!=b'A\0':raise RuntimeError('trusted codec bootstrap')
  original=R.load_test_module()
  corpus_path=HERE/'ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json';corpus=json.loads(checked(corpus_path,'cb4c6dd46cd8e02bc45c9bbec69a52f0a6ee1baea633eefaed85eeb018f57cc7'))
  focused_path=HERE/'admission_envelope_regressions_v1.py';pins[focused_path.name]=pin(focused_path)
  regression=load_harness('independent_admission_same_four_v1',focused_path,'5644882f8d67c0121b4967538d3af9eedf200266792bdb0d07b08e0392171e34')
  # Same closed imports and active audit as retained runner V2; only new
  # source module identity changes. No cached V1 subject is ever imported.
  name='admission_envelope_v2'
  if name in sys.modules:raise RuntimeError('cached V2 subject')
  allowed={'json':R.json,'re':R.re,'types':R.types}
  def importer(requested,globals=None,locals=None,fromlist=(),level=0):
   if level!=0 or requested not in allowed:
    R.IMPORT_DENIALS.append(dict(name=requested,level=level));raise ImportError('closed calculator import: '+requested)
   return allowed[requested]
  subject=types.ModuleType(name);subject.__file__=str(source_path);subject.__package__='';subject.__dict__['__builtins__']=dict(vars(builtins),__import__=importer);sys.modules[name]=subject
  R.active_call(exec,compile(raw,str(source_path),'exec'),subject.__dict__)
  def invoke(function,*args,**kwargs):
   if function is subject.analyze_admission:
    # Do not encode/coerce input for logging: focused tests include an actual
    # int subclass whose protocols must remain entirely untouched.
    row=dict(ordinal=len(calls),check_callable=callable(kwargs.get('check')),check_calls=0,check_returns=0,check_exceptions=0,return_observed=False,exception_type=None,original_check_exception_identity=None);calls.append(row)
    original_check=kwargs.get('check');stops=[]
    if callable(original_check):
     def check():
      row['check_calls']+=1
      try:answer=original_check()
      except BaseException as error:row['check_exceptions']+=1;stops.append(error);raise
      row['check_returns']+=1;return answer
     kwargs=dict(kwargs,check=check)
    try:
     answer=R.active_call(function,*args,**kwargs);row['return_observed']=True
     if stops:row['original_check_exception_identity']=False
     return answer
    except BaseException as error:
     row['exception_type']=type(error).__name__
     if stops:row['original_check_exception_identity']=any(error is stop for stop in stops)
     raise
   item=dict(name=getattr(function,'__name__','unknown'),return_observed=False,exception_type=None);getters.append(item)
   try:answer=R.active_call(function,*args,**kwargs);item['return_observed']=True;return answer
   except BaseException as error:item['exception_type']=type(error).__name__;raise
  suite=unittest.TestSuite()
  suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(original.make_tests(subject,corpus,invoke,observations)))
  suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(regression.make_tests(subject,corpus,original,invoke,focused)))
  result=unittest.TextTestRunner(verbosity=2,resultclass=R.Results).run(suite)
  matched=[o for o in observations if 'vector' in o];stable={n:pin(Path(v['path']))==v for n,v in pins.items()};identity_failures=[row for row in calls if row['original_check_exception_identity'] is False]
  passed=result.wasSuccessful() and result.testsRun==8 and len(matched)==30 and len(focused)==4 and not R.AUDIT_DENIALS and not R.IMPORT_DENIALS and all(stable.values()) and not identity_failures
  record=dict(schema_version=3,status='passed' if passed else 'FIRST_V2_SOURCE_FAILURES_RETAINED',methods=result.testsRun,method_outcomes=result.outcomes,failures=[dict(test=str(t),detail=d) for t,d in result.failures],errors=[dict(test=str(t),detail=d) for t,d in result.errors],original_observations=observations,focused_regression_observations=focused,unique_original_metadata_vectors=30,original_vectors_matched=len(matched),focused_methods=4,actual_analysis_invocations=len(calls),actual_analysis_returns=sum(row['return_observed'] for row in calls),actual_analysis_exceptions=sum(row['exception_type'] is not None for row in calls),actual_check_invocations=sum(row['check_calls'] for row in calls),actual_check_returns=sum(row['check_returns'] for row in calls),actual_check_exceptions=sum(row['check_exceptions'] for row in calls),original_check_exception_identity_failures=identity_failures,analysis_invocations=calls,getter_invocations=getters,inputs=pins,input_bytes_unchanged=stable,audit_denials=list(R.AUDIT_DENIALS),closed_import_denials=list(R.IMPORT_DENIALS),runner=pin(Path(__file__).resolve()),elapsed_seconds=time.monotonic()-started,qualification=dict(original.QUALIFICATION),chronology='Same original30/e670 and same four5644 tests, all frozen before V2 correction; four BEFORE failures8a02 preserved. First coherent V2-source replay only. Initial codec failure and subsequent runner-only correction remain distinct.',scope='Pure metadata source component only. No original source/FFI/runtime/stream/physical output/resource/profile authority.',loader='Fresh admission_envelope_v2 from same pinned bytes; exact trusted json/re/types only; retained9719 codec bootstrap and active audit unchanged. No old subject imported or cached source fallback.',logging='Per-invocation metadata encoding is omitted so int-subclass protocols are never touched by observation. Source receives original unmodified inputs; exact corpus/source/test pins and strict expected comparisons remain.',actual_target_API_calls=0,original_payload_operations=0,runtime_authorized=False)
 except BaseException as error:
  record=dict(status='FIRST_V2_SOURCE_SETUP_OR_SUBJECT_FAILURE_RETAINED',error_class=type(error).__name__,message=str(error)[:2048],traceback=traceback.format_exc(),observations=observations,focused=focused,analysis_invocations=calls,getter_invocations=getters,inputs=pins,runner=pin(Path(__file__).resolve()),audit_denials=[] if R is None else R.AUDIT_DENIALS,elapsed_seconds=time.monotonic()-started,actual_target_API_calls=0,original_payload_operations=0,runtime_authorized=False)
 finally:
  if record is not None:
   with destination.open('xb') as out:out.write(canonical(record))
   print(json.dumps(dict(proof=pin(destination),status=record['status'],methods=record.get('methods'),unique_metadata_vectors=30,actual_analysis_invocations=len(calls),actual_check_invocations=sum(row['check_calls'] for row in calls))))
 return 0 if record and record['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())
