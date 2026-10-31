"""Closed metadata/framing checks ONLY: no transition/fake/source execution."""
import hashlib
import json
from pathlib import Path
import struct
import unittest

HERE=Path(__file__).resolve().parent
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(name,digest):
 path=HERE/name;assert pin(path)['sha256']==digest
 return json.loads(path.read_bytes())
SCHEMA=read('SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v2.json','7ea6cb057c749e54a4fa557345ce00076fbd9b6b911eb7d767d9666fd7ddb0c8')
DATA=read('SHARED-OWNER-INTEGRATION-FIXTURES-v2.json','45b17a6c737d6dbd914557f698a74ed92bf18077a0d2b86864cec63b72d037c5')
PUBLIC=read('SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json','50ee2d7a9285370e6a3f0d18801c43e441b327f7ceac9eb46ebdf0463eff28d6')
COHORT=read('SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json','eb5147d200bcc0108b71968d69f6b251c29b56dd52d926a8606504682134d9b8')
PROPOSAL=read('SHARED-OWNER-CONTINUATION-PROPOSAL-v2.json','90fc021a044bba34953a8f8f8e42b05f5d61f49da945044e1e108f92bb1fc3cd')
BY={c['id']:c for c in DATA['cases']}
API=PROPOSAL['active_original_API_subset']

def path_valid(path):
 if path=='$snapshot':return True
 parts=path.split('.');record='snapshot'
 while parts:
  field=parts.pop(0)
  if field not in PUBLIC[record]['exact_keys']:return False
  if not parts:return True
  if record=='snapshot':
   if field in ('files','calls','stages'):
    if not parts[0].isdigit():return False
    index=int(parts.pop(0))
    if index>=dict(files=4,calls=92,stages=9)[field]:return False
    record=dict(files='file',calls='call',stages='stage')[field]
   elif field=='api_counters':
    if parts.pop(0) not in API:return False
    record='api_counter'
   elif field in ('early_context','evidence_context'):record='context'
   elif field in ('origin','plan','byte_totals','loader','journal','outputs','errors','terminal'):record=field
   else:return False
  elif record=='outputs':
   if field=='publications':
    if parts.pop(0) not in PUBLIC['enums']['publish_kind']:return False
    record='callback'
   elif field in ('reservation','journal_close'):record='callback'
   else:return False
  elif record=='call' and field in ('raw_scalar','raw_count','raw_error'):record='atom'
  elif record=='errors' and field=='primary':record='diagnostic'
  elif record=='journal' and field=='events':
   if not parts[0].isdigit() or int(parts.pop(0))>=224:return False
   record='event'
  else:return False
 return False

class LiteralChecks(unittest.TestCase):
 def test_exact48_groups_schema_and_preserved_delta(self):
  self.assertEqual(len(DATA['cases']),48);self.assertEqual(len(BY),48)
  self.assertEqual({c['group'] for c in DATA['cases']},{g['id'] for g in PROPOSAL['pure_fixture_matrix']})
  old=json.loads((HERE/'SHARED-OWNER-INTEGRATION-FIXTURES-v1.json').read_bytes())
  self.assertEqual(old['cases'],DATA['cases']);self.assertEqual(old['frames_hex'],DATA['frames_hex'])
  for c in DATA['cases']:
   self.assertEqual(set(c),set(SCHEMA['case_exact_keys']))
   self.assertLessEqual(len(c['steps']),32);self.assertLessEqual(len(c['checks']),180)
   self.assertLessEqual(len(c['binding_overrides']),17)
   self.assertEqual(c['steps'][0],dict(op='setup'))

 def test_closed_steps_and_expected_projection_domains(self):
  for c in DATA['cases']:
   with self.subTest(history=c['id']):
    names={'final'}|{s['name'] for s in c['steps'] if s['op']=='snapshot'}
    if any(s['op']=='foreign_control' for s in c['steps']):names.add('after_rejected_control')
    for s in c['steps']:
     self.assertIn(s['op'],SCHEMA['step_exact_keys']);self.assertEqual(set(s),set(SCHEMA['step_exact_keys'][s['op']]))
     if s['op']=='admit':self.assertIn(s['spec_variant'],SCHEMA['spec_variants'])
     if s['op']=='continue':self.assertIn(s['factory_variant'],SCHEMA['factory_variants'])
     if s['op'] in ('load','probe_load_refused'):self.assertEqual(s['module'],'cohort_entry')
     if s['op']=='clock_set':self.assertIs(type(s['value']),int);self.assertGreaterEqual(s['value'],100)
    observed={}
    for check in c['checks']:
     self.assertEqual(set(check),set(SCHEMA['check_exact_keys']))
     self.assertIn(check['at'],names);self.assertIn(check['relation'],SCHEMA['check_relations'])
     self.assertTrue(path_valid(check['path']),check['path'])
     if check['relation']=='eq':
      key=(check['at'],check['path'])
      if key in observed:self.assertEqual(observed[key],check['value'],'Conflicting authored assertions')
      observed[key]=check['value']
     if check['relation']=='original_exception_is':self.assertIn(check['value'],DATA['exception_inputs'])
    self.assertTrue(any(x['path']=='qualification' and x['value']==PUBLIC['qualification_exact'] for x in c['checks']))

 def test_exact_active_binding_hooks_frames_and_prefix(self):
  frames=DATA['frames_hex']
  for name,hx in frames.items():
   self.assertIs(type(hx),str);self.assertEqual(bytes.fromhex(hx).hex(),hx)
   self.assertLessEqual(len(bytes.fromhex(hx)),65536)
  for i,blob in enumerate(COHORT['blobs']):
   self.assertEqual(frames[blob['id']+'_read'],blob['utf8_hex'])
   raw=bytes.fromhex(frames[blob['id']+'_final_path']);prefix=blob['path'].encode('utf-16-le')
   self.assertEqual(len(raw),8202);self.assertEqual(raw,prefix+b'\0'*(8202-len(prefix)))
   self.assertEqual(struct.unpack('<q',bytes.fromhex(frames[blob['id']+'_size']))[0],blob['bytes'])
  leaf=bytes.fromhex(COHORT['blobs'][0]['utf8_hex'])
  self.assertEqual(b''.join(bytes.fromhex(frames['leaf_byte_'+str(i)]) for i in range(17)),leaf[:17])
  self.assertEqual(len(leaf)-17,41)
  for c in DATA['cases']:
   for rule in c['binding_overrides']:
    self.assertEqual(set(rule),set(SCHEMA['binding_override_exact_keys']))
    self.assertIn(rule['api'],API);self.assertIs(type(rule['file_id']),int);self.assertIn(rule['file_id'],(0,1,2))
    self.assertIn(rule['return'],('normal_None','throw_original'))
    self.assertLessEqual(len(rule['actions']),12)
    for a in rule['actions']:
     self.assertEqual(set(a),set(SCHEMA['binding_action_exact_shapes'][a['hook']]))
     if a['hook']=='buffer_write':self.assertIn(a['frame'],frames)
     if a['hook'] in ('store_scalar','store_count','store_error'):
      self.assertTrue(a['value'] is None or type(a['value']) is int)
     if a['hook']=='store_count':self.assertEqual(rule['api'],'ReadFile');self.assertGreaterEqual(a['value'],0)
     if a['hook']=='raise_exception':self.assertIn(a['exception'],DATA['exception_inputs']);self.assertIn(a['phase'],PUBLIC['diagnostic_phase_enum'])

 def test_callbacks_generic_fault_sites_and_no_publication_injection(self):
  for c in DATA['cases']:
   for rule in c['callback_rules']:
    self.assertEqual(set(rule),set(SCHEMA['callback_rule_exact_keys']))
    self.assertIn(rule['target'],SCHEMA['callback_targets']);self.assertEqual(rule['occurrence'],1)
    for a in rule['actions']:
     self.assertEqual(set(a),set(SCHEMA['callback_action_exact_shapes'][a['action']]))
     if a['action']=='throw_original':self.assertIn(a['exception'],DATA['exception_inputs'])
     if a['action']=='emit_forbidden':self.assertIn(a['event'],PUBLIC['event_names'])
  post=BY['postseal_no_new_output']['callback_rules'][0]
  self.assertEqual(post['target'],'before_final_ack');self.assertEqual(post['actions'][0]['action'],'emit_forbidden')
  cap=BY['publication_attempt_or_size_cap']
  self.assertEqual(cap['binding_overrides'],[]);self.assertEqual(cap['callback_rules'],[])
  self.assertIn('NOT exercised',cap['coverage'][0])
  forged=BY['forged_derived_caps'];self.assertTrue(any(x['relation']=='unchanged_since' for x in forged['checks']))

 def test_baseline_counts_and_explicit53_event_order(self):
  calls=DATA['baseline_binding_inputs'];self.assertEqual(len(calls),21)
  for api in API:self.assertEqual(sum(x['api']==api for x in calls),3)
  self.assertEqual(DATA['common']['expected_plan'],dict(N=3,B=2,M=2,R=51,C=69,E=218))
  rows=DATA['expected_baseline_serialized_rows'];self.assertEqual(len(rows),53)
  self.assertEqual([r['sequence'] for r in rows],list(range(53)))
  for r in rows:
   self.assertEqual(set(r),set(PUBLIC['serialized_journal_row']['exact_keys']))
   self.assertIn(r['event'],PUBLIC['event_names']);self.assertNotIn('acknowledged',r)
   encoded=json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('utf-8')+b'\n'
   self.assertLessEqual(len(encoded),1024)
  self.assertEqual([r['file_id'] for r in rows if r['event']=='original_close_reserved'],[2,1,0])
  self.assertEqual([r['module'] for r in rows if r['event']=='source_compile_reserved'],['cohort_entry','cohort_leaf'])
  self.assertEqual([r['module'] for r in rows if r['event']=='source_compile_returned'],['cohort_leaf','cohort_entry'])
  self.assertEqual([r['stage'] for r in rows if r['event']=='stage_reserved'],PUBLIC['stage_names'])

 def test_source_absent_no_runtime_or_behavior_claim(self):
  for name in ('shared_owner_v1.py','shared_file_ports_v1.py','continue_verification_v1.py'):self.assertFalse((HERE/name).exists())
  self.assertFalse(DATA['reviewed_components_imported']);self.assertFalse(DATA['toy_helpers_executed'])
  self.assertFalse(DATA['source_implementation_authorized']);self.assertFalse(DATA['fixture_behavior_qualified'])
  self.assertEqual(DATA['actual_API_calls'],0);self.assertEqual(DATA['fake_binding_dispatches'],0)
  self.assertTrue(all(type(v) is bool and v is False for v in DATA['qualification'].values()))

if __name__=='__main__':
 report_path=HERE/'SHARED-OWNER-INTEGRATION-LITERAL-PROOF-v2.json';assert not report_path.exists()
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LiteralChecks))
 report=dict(schema_version=1,status='passed' if result.wasSuccessful() else 'failed',methods=result.testsRun,failures=[dict(test=str(t),detail=d) for t,d in result.failures],errors=[dict(test=str(t),detail=d) for t,d in result.errors],fixture=pin(HERE/'SHARED-OWNER-INTEGRATION-FIXTURES-v2.json'),schema=pin(HERE/'SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v2.json'),public_schema=pin(HERE/'SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json'),public_peer=pin(HERE/'SHARED-OWNER-PUBLIC-DATA-INDEPENDENT-PEER-v2.json'),root_scope=pin(HERE/'SHARED-OWNER-ROOT-PREPARATION-SCOPE-v2.json'),cohort=pin(HERE/'SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json'),checker=pin(Path(__file__).resolve()),wording_delta=pin(HERE/'SHARED-OWNER-INTEGRATION-WORDING-DELTA-PROOF-v2.json'),histories=48,groups=14,expected_baseline_fake_calls=21,reserved_call_capacity=69,reserved_event_capacity=218,expected_baseline_journal_rows=53,current_fake_dispatches=0,actual_API_calls=0,toy_helpers_executed=False,under_test_imported=False,fixture_behavior_qualified=False,qualification=PUBLIC['qualification_exact'],scope='Literal schema/frame/count/callback/expected-projection checks ONLY. No transition interpreter, generic fake binding, source helper, reviewed component or native code was executed.')
 with report_path.open('xb') as out:out.write((json.dumps(report,sort_keys=True,indent=2)+'\n').encode('utf-8'))
 print(json.dumps(dict(proof=pin(report_path),status=report['status'],methods=result.testsRun)))
 raise SystemExit(0 if result.wasSuccessful() else 1)
