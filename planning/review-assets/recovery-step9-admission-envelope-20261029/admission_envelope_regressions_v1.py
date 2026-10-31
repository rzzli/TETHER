"""Four independent regressions frozen before any calculator correction.

No subject import, fake input container, source-global mutation or reference
calculator. The profiler observes the real _object generator under CPython.
"""
import copy
import sys
import types
import unittest

def make_tests(subject,corpus,original_tests,invoke,observations):
 baseline=next(v for v in corpus['vectors'] if v['id']=='mixed_role_all_bounds_equal')
 refusal=next(v for v in corpus['vectors'] if v['id']=='extra_top_key_refused')['expected']
 def metadata():return copy.deepcopy(baseline['metadata'])
 def expected(code):
  value=copy.deepcopy(refusal);value['violations'][0]['code']=code;return value
 def analyze(value):return invoke(subject.analyze_admission,value,check=lambda:None)
 def validate(report,label,code,extra=None):
  raw=invoke(report.to_dict);original_tests.validate_report(raw)
  observations.append(dict(method=label,actual_code=raw['violations'][0]['code'] if raw['violations'] else None,expected_code=code,qualification=raw['qualification'],**(extra or {})))
  original_tests.equal_typed(raw,expected(code))
  original_tests.equal_typed(invoke(report.to_json_bytes),original_tests.canonical(expected(code)))
 class Regressions(unittest.TestCase):
  def test_01_oversized_real_dict_refused_before_key_traversal(self):
   value=metadata()
   for index in range(4096-len(value)):value['extra_'+str(index)]=None
   self.assertIs(type(value),dict);self.assertEqual(len(value),4096)
   self.assertTrue(all(type(key) is str for key in value))
   object_code=subject._object.__code__
   generators=tuple(c for c in object_code.co_consts if type(c) is types.CodeType and c.co_name=='<genexpr>')
   self.assertTrue(generators,'observe the actual key-validation generator, not a fake substitute')
   measured=dict(object_calls=0,generator_resumptions=0,key_yields=0)
   def profile(frame,event,arg):
    if frame.f_code is object_code and event=='call':measured['object_calls']+=1
    if any(frame.f_code is code for code in generators):
     if event=='call':measured['generator_resumptions']+=1
     elif event=='return' and arg is True:measured['key_yields']+=1
   previous=sys.getprofile();self.assertIsNone(previous,'trusted profile channel must be unoccupied')
   sys.setprofile(profile)
   try:report=analyze(value)
   finally:sys.setprofile(previous)
   # Record real before evidence even when the traversal assertion fails.
   raw=invoke(report.to_dict);original_tests.validate_report(raw)
   observations.append(dict(method='oversized_real_dict',input_type='exact_builtin_dict',actual_keys=4096,allowed_keys=7,metrics=dict(measured),actual_code=raw['violations'][0]['code'],expected_code='SCHEMA_KEYS',expected_key_yields=0,source_object_code_unchanged=subject._object.__code__ is object_code,profile_restored=sys.getprofile() is previous,qualification=raw['qualification']))
   original_tests.equal_typed(raw,expected('SCHEMA_KEYS'))
   self.assertEqual(measured['object_calls'],1)
   self.assertEqual(measured['key_yields'],0,'oversized exact dict must be rejected before traversing keys')
   self.assertEqual(measured['generator_resumptions'],0,'size refusal must precede the key generator')
   self.assertIs(subject._object.__code__,object_code)
  def test_02_int_subclass_is_type_domain_without_hooks(self):
   value=metadata();hooks=[]
   def forbidden(name):
    def hook(*args,**kwargs):hooks.append(name);raise AssertionError('forbidden numeric protocol: '+name)
    return hook
   methods={name:forbidden(name) for name in ('__int__','__index__','__float__','__repr__','__str__','__lt__','__le__','__gt__','__ge__','__eq__','__hash__','__add__','__radd__','__mul__','__rmul__')}
   ProbeInt=type('ProbeInt',(int,),methods)
   value['files'][3]['size']=ProbeInt(65537)
   report=analyze(value)
   try:validate(report,'int_subclass','TYPE_DOMAIN',dict(hook_calls=list(hooks),expected_hook_calls=0))
   finally:self.assertEqual(hooks,[],'do not traverse/coerce/format int subclasses')
  def test_03_cycle_precedes_aggregate_mismatch(self):
   value=metadata();value['modules'][0]['dependencies']=['toy_entry'];value['aggregate']['bytes']=65747
   validate(analyze(value),'cycle_and_aggregate_mismatch','MODULE_GRAPH')
  def test_04_cycle_precedes_total_overflow(self):
   value=metadata();value['modules'][0]['dependencies']=['toy_entry'];value['files'][3]['size']=2**63-1;value['aggregate']['bytes']=None
   validate(analyze(value),'cycle_and_total_overflow','MODULE_GRAPH')
 return Regressions
