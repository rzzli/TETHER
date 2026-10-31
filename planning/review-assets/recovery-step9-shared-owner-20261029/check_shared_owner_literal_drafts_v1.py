"""Data-only framing checks; no fake binding or toy source is executed."""
import hashlib
import json
from pathlib import Path
import struct
import unittest

HERE=Path(__file__).resolve().parent
def read(name,digest):
 raw=(HERE/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
 return json.loads(raw)
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
ROSTER=read('SHARED-OWNER-INTEGRATION-HISTORY-ROSTER-DRAFT-v1.json','ec53fce7dbb317bb284b0c8924eac4655b28c04df86166178b4538191cb0850a')
INPUTS=read('SHARED-OWNER-INTEGRATION-BINDING-INPUTS-DRAFT-v1.json','3c9f1c84571f740affa7f9730b4afe7c88c4d9724669557d3202b122dd1aa2c3')
COHORT=read('SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json','eb5147d200bcc0108b71968d69f6b251c29b56dd52d926a8606504682134d9b8')
PROPOSAL=read('SHARED-OWNER-CONTINUATION-PROPOSAL-v2.json','90fc021a044bba34953a8f8f8e42b05f5d61f49da945044e1e108f92bb1fc3cd')

class DraftChecks(unittest.TestCase):
 def test_all48_predeclared_histories_cover14groups(self):
  self.assertEqual(len(ROSTER['cases']),48)
  self.assertEqual(len({r['id'] for r in ROSTER['cases']}),48)
  self.assertEqual({r['group'] for r in ROSTER['cases']},{r['id'] for r in PROPOSAL['pure_fixture_matrix']})
 def test_literal_input_frames_and_no_body_substitution(self):
  frames=INPUTS['frames_hex'];self.assertEqual(struct.unpack('<II',bytes.fromhex(frames['attributes_normal'])),(128,0))
  for blob in COHORT['blobs']:
   identity=blob['id'];path_frame=bytes.fromhex(frames[identity+'_final_path'])
   self.assertEqual(len(path_frame),8202)
   prefix=blob['path'].encode('utf-16-le');self.assertEqual(path_frame[:len(prefix)],prefix)
   self.assertEqual(path_frame[len(prefix):],b'\0'*(8202-len(prefix)))
   self.assertEqual(struct.unpack('<q',bytes.fromhex(frames[identity+'_size']))[0],blob['bytes'])
   self.assertEqual(frames[identity+'_read'],blob['utf8_hex'])
 def test_baseline21_fake_inputs_are_separate_from69_capacity(self):
  calls=INPUTS['baseline_binding_script'];self.assertEqual(len(calls),21)
  self.assertEqual([c['ordinal'] for c in calls],list(range(21)))
  self.assertEqual({c['api'] for c in calls},set(PROPOSAL['active_original_API_subset']))
  for api in PROPOSAL['active_original_API_subset']:self.assertEqual(sum(c['api']==api for c in calls),3)
  self.assertEqual([c['file_id'] for c in calls[-3:]],['metadata','cohort_entry','cohort_leaf'])
  N,B,M=3,2,2;R=sum((b['bytes']+65535)//65536+16 for b in COHORT['blobs'])
  self.assertEqual(INPUTS['capacity_distinction'],dict(N=N,B=B,M=M,R=R,C=6*N+R,E=6*N+2*B+2*M+64+128))
  self.assertEqual((R,6*N+R,6*N+2*B+2*M+64+128),(51,69,218))
 def test_hook_data_types_and_scope(self):
  for call in INPUTS['baseline_binding_script']:
   self.assertEqual(call['binding_return'],'normal_None')
   self.assertEqual(sum(a['hook']=='store_scalar' for a in call['actions']),1)
   for action in call['actions']:
    if action['hook'] in ('store_scalar','store_count'):self.assertIs(type(action['value']),int)
    elif action['hook']=='buffer_write':self.assertIn(action['frame_id'],INPUTS['frames_hex'])
    else:self.fail('Unclosed hook')
    if action['hook']=='store_count':self.assertEqual(call['api'],'ReadFile')
  self.assertEqual(INPUTS['binding_dispatches'],0)
  self.assertFalse(INPUTS['source_helpers_executed']);self.assertFalse(ROSTER['source_implementation_authorized'])

if __name__=='__main__':
 path=HERE/'SHARED-OWNER-LITERAL-DRAFT-FRAMING-PROOF-v1.json';assert not path.exists()
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DraftChecks))
 report=dict(schema_version=1,status='draft_framing_passed' if result.wasSuccessful() else 'failed',methods=result.testsRun,failures=[dict(test=str(t),detail=d) for t,d in result.failures],errors=[dict(test=str(t),detail=d) for t,d in result.errors],roster=pin(HERE/'SHARED-OWNER-INTEGRATION-HISTORY-ROSTER-DRAFT-v1.json'),binding_inputs=pin(HERE/'SHARED-OWNER-INTEGRATION-BINDING-INPUTS-DRAFT-v1.json'),checker=pin(Path(__file__).resolve()),scope='Draft literal metadata/framing only; final public snapshot/schema and concrete histories remain unfrozen, no transition interpreter or fake/native binding or source helper run.',actual_API_calls=0,fake_dispatches=0,toy_helpers_executed=False,under_test_sources_imported=False,fixture_behavior_qualified=False,runtime_authorized=False)
 with path.open('xb') as out:out.write((json.dumps(report,sort_keys=True,indent=2)+'\n').encode('utf-8'))
 print(json.dumps(dict(proof=pin(path),status=report['status'])))
 raise SystemExit(0 if result.wasSuccessful() else 1)
