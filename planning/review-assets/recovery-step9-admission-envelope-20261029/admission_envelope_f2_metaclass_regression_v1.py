"""One pre-fix F2 probe: exact type refusal must not call metaclass equality."""
import copy
import unittest

def make_tests(subject,corpus,original_tests,invoke,observations):
 baseline=next(v for v in corpus['vectors'] if v['id']=='mixed_role_all_bounds_equal')
 template=next(v for v in corpus['vectors'] if v['id']=='extra_top_key_refused')['expected']
 class F2Probe(unittest.TestCase):
  def test_int_subclass_metaclass_equality_is_never_invoked(self):
   metadata=copy.deepcopy(baseline['metadata']);hooks=[]
   class ProbeMeta(type):
    def __eq__(cls,other):
     label=next((name for value,name in ((int,'int'),(bool,'bool'),(float,'float'),(str,'str'),(type(None),'NoneType')) if other is value),'other')
     hooks.append(label)
     return False
   class ProbeInt(int,metaclass=ProbeMeta):pass
   metadata['files'][3]['size']=ProbeInt(65537)
   self.assertEqual(hooks,[],'probe setup must not call the hook')
   report=invoke(subject.analyze_admission,metadata,check=lambda:None)
   actual=invoke(report.to_dict);original_tests.validate_report(actual)
   expected=copy.deepcopy(template);expected['violations'][0]['code']='TYPE_DOMAIN'
   observations.append(dict(method='F2_metaclass_equality',actual_code=actual['violations'][0]['code'],expected_code='TYPE_DOMAIN',metaclass_equality_calls=list(hooks),expected_hook_count=0,harmless_hook_return=False,qualification=actual['qualification']))
   original_tests.equal_typed(actual,expected)
   self.assertEqual(hooks,[],'exact type guards must use identity, not producer equality')
 return F2Probe
