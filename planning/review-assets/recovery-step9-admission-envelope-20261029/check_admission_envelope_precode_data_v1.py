"""Structural/framing checks of fixed metadata only; no subject calculator."""
import ast
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import traceback
import types
import unittest
HERE=Path(__file__).resolve().parent
PREFLIGHT=HERE.parent/'recovery-step9-production-preflight-20261029'
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('utf-8')
def publish(name,value):
 path=HERE/name
 with path.open('xb') as out:out.write(canonical(value))
 return pin(path)
def main():
 proof_path=HERE/'ADMISSION-ENVELOPE-PRECODE-STRUCTURAL-PROOF-v1.json'
 if proof_path.exists():raise RuntimeError('first structural result already retained')
 observations=[];record=None
 try:
  corpus_path=HERE/'ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json';corpus=json.loads(corpus_path.read_bytes())
  assert pin(corpus_path)['sha256']=='cb4c6dd46cd8e02bc45c9bbec69a52f0a6ee1baea633eefaed85eeb018f57cc7'
  test_path=HERE/'admission_envelope_independent_tests_v1.py';raw=test_path.read_bytes();test_pin=pin(test_path)
  ast.parse(raw)
  module=types.ModuleType('precode_calculator_test_format_only');exec(compile(raw,str(test_path),'exec'),module.__dict__)
  cases=corpus['vectors'];byid={v['id']:v for v in cases};baseline=byid['mixed_role_all_bounds_equal'];proposal=json.loads(Path(corpus['source_proposal']['path']).read_bytes())
  class Checks(unittest.TestCase):
   def test_01_pins_and_absent_subject(self):
    for key in ('source_proposal','clarification'):self.assertEqual(pin(Path(corpus[key]['path'])),corpus[key])
    self.assertFalse((HERE/'admission_envelope_v1.py').exists());self.assertEqual(corpus['subject_tests'],0)
   def test_02_closed_cases_and_expected_domains(self):
    self.assertEqual(len(cases),30);self.assertEqual(len(byid),30)
    self.assertEqual([v['ordinal'] for v in cases],list(range(30)))
    self.assertEqual(set(module.DERIVED),set(proposal['result']['derived']['exact_keys']))
    self.assertEqual(set(module.TOP),set(proposal['result']['exact_keys']))
    for vector in cases:
     self.assertEqual(set(vector),{'ordinal','id','metadata','expected','basis'})
     module.validate_report(vector['expected'])
     self.assertEqual(json.loads(canonical(vector['metadata'])),vector['metadata'])
   def test_03_all_12_isolated_boundaries(self):
    isolated=[v for v in cases if v['id'].startswith('isolated_')]
    self.assertEqual(len(isolated),12)
    seen=set()
    for vector in isolated:
     changed=[key for key in baseline['metadata']['limits'] if vector['metadata']['limits'][key]!=baseline['metadata']['limits'][key]]
     self.assertEqual(len(changed),1);key=changed[0];seen.add(key)
     restored=copy.deepcopy(vector['metadata']);restored['limits'][key]+=1
     self.assertEqual(restored,baseline['metadata'])
     self.assertEqual(vector['expected']['derived'],baseline['expected']['derived'])
     violation=vector['expected']['violations'];self.assertEqual(len(violation),1)
     self.assertEqual((violation[0]['required'],violation[0]['limit']),(baseline['metadata']['limits'][key],baseline['metadata']['limits'][key]-1))
     self.assertEqual(violation[0]['code'],key.upper())
    self.assertEqual(seen,set(module.LIMITS))
   def test_04_discriminating_baseline_and_fixed_framing(self):
    m=baseline['metadata'];d=baseline['expected']['derived']
    self.assertEqual([f['id'] for f in m['files']],[2,0,3,1]);self.assertEqual(m['early_ids'],[2,0])
    self.assertEqual([f['size'] for f in m['files']],[58,83,68,65537])
    self.assertEqual((d['N'],d['B'],d['M'],d['Q'],d['R'],d['C'],d['E']),(4,2,2,5,69,93,224))
    closure=[dict(file_id=i,invoked=False,return_observed=False,success=False) for i in range(4)]
    digests=[dict(file_id=i,size=f['size'],sha256=f['sha256']) for i,f in enumerate(m['files'])]
    self.assertEqual((len(canonical(closure))-1,len(canonical(digests))-1),(281,404))
    self.assertEqual((d['raw_payload_bytes'],d['immutable_capture_bytes'],d['logical_call_bytes'],d['index_bytes'],d['hash_state_bytes'],d['journal_bytes'],d['canonical_report_bytes'],d['packet_bound_bytes'],d['output_reserved_bytes'],d['peak_declared_memory_bytes']),(106819,209,1023,86,76,229376,12244,728,245260,595116))
   def test_05_zero_ceiling_unknown_and_overflow_literals(self):
    near=byid['near_max_ceiling_known_exceeds_with_unknown'];size=near['metadata']['files'][3]['size'];q,r=divmod(size,65536)
    self.assertEqual((size,q,r),(9223372036854775598,140737488355327,65326))
    self.assertEqual(near['expected']['derived']['Q'],q+1+3)
    self.assertEqual(near['expected']['derived']['total_bytes'],2**63-1)
    self.assertEqual(near['expected']['status'],'EXCEEDS_DECLARED_BOUNDS')
    self.assertEqual(near['expected']['unknowns'],['representation.call_record_bytes'])
    self.assertEqual(byid['checked_product_overflow_refused']['expected']['violations'][0]['code'],'ARITHMETIC_OVERFLOW')
    self.assertEqual(byid['bulk_zero_no_read_reservation']['expected']['derived']['R'],51)
    self.assertEqual(byid['bulk_exact_chunk_boundary']['expected']['derived']['R'],68)
    agg=byid['aggregate_only_unknown']['expected']['derived'];self.assertEqual((agg['N'],agg['R'],agg['C']),(None,None,None))
    self.assertEqual((agg['work_buffer_bytes'],agg['aggregate_R_range'],agg['aggregate_C_range']),(73738,[137611,141215],[138889,142493]))
   def test_06_exact_encoded_expectations_are_metadata_only(self):
    for vector in cases:
     encoded=canonical(vector['expected']);input_bytes=canonical(vector['metadata'])
     self.assertLessEqual(len(encoded),8192);self.assertLessEqual(len(input_bytes),8192)
     observations.append(dict(id=vector['id'],metadata_bytes=len(input_bytes),metadata_sha256=hashlib.sha256(input_bytes).hexdigest(),calculator_json_bytes=len(encoded),calculator_json_sha256=hashlib.sha256(encoded).hexdigest(),status=vector['expected']['status']))
    self.assertNotEqual(len(canonical(baseline['expected'])),baseline['expected']['derived']['canonical_report_bytes'])
   def test_07_test_source_is_generic_and_has_no_subject_import(self):
    tree=ast.parse(raw)
    imports={node.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for node in n.names}
    self.assertEqual(imports,{'copy','json','unittest'})
    forbidden={'open','eval','exec','compile','__import__'}
    self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in forbidden for n in ast.walk(tree)))
    self.assertEqual(pin(test_path),test_pin)
  result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
  record=dict(schema_version=1,status='passed' if result.wasSuccessful() else 'FIRST_STRUCTURAL_FAILURES_RETAINED',methods=result.testsRun,failures=[dict(test=str(t),detail=d) for t,d in result.failures],errors=[dict(test=str(t),detail=d) for t,d in result.errors],corpus=pin(corpus_path),test_source=test_pin,checker=pin(Path(__file__).resolve()),framing=observations,actual_metadata_vectors=30,independent_bound_vectors=12,subject_imports=0,subject_tests=0,actual_target_API_calls=0,original_payload_operations=0,scope='Data shape/framing/literal-boundary checks only. This does not execute or qualify the future admission calculator.',calculator_json_is_not_prospective_runtime_report_V=True)
 except BaseException as error:
  record=dict(status='STRUCTURAL_SETUP_FAILURE_PRESERVED',error_class=type(error).__name__,message=str(error)[:2048],traceback=traceback.format_exc(),checker=pin(Path(__file__).resolve()),subject_imports=0,subject_tests=0,actual_target_API_calls=0)
 finally:
  if record is not None:
   proof=publish(proof_path.name,record);print(json.dumps(dict(proof=proof,status=record['status'],methods=record.get('methods'))))
 return 0 if record and record['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())
