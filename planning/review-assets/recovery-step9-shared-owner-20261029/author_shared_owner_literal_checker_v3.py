"""Version metadata checker for exactly two preparation closures."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
text=(HERE/'check_shared_owner_integration_literals_v2.py').read_text(encoding='utf-8')
for old,new in (
 ('SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v2.json','SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json'),
 ('7ea6cb057c749e54a4fa557345ce00076fbd9b6b911eb7d767d9666fd7ddb0c8','34c3df0519df387e31439096b8c76e39fc3ce74437e1281346da58ab3a33952e'),
 ('SHARED-OWNER-INTEGRATION-FIXTURES-v2.json','SHARED-OWNER-INTEGRATION-FIXTURES-v3.json'),
 ('45b17a6c737d6dbd914557f698a74ed92bf18077a0d2b86864cec63b72d037c5','e12d6485d0bc38b38c5b4bf33edcab22c1471da15858718185f18f1b5179eee2'),
 ('SHARED-OWNER-INTEGRATION-LITERAL-PROOF-v2.json','SHARED-OWNER-INTEGRATION-LITERAL-PROOF-v3.json'),
 ('wording_delta=pin(HERE/\'SHARED-OWNER-INTEGRATION-WORDING-DELTA-PROOF-v2.json\')','closure_delta=pin(HERE/\'SHARED-OWNER-INTEGRATION-TWO-CLOSURE-DELTA-v3.json\')')):
 assert old in text,old
 text=text.replace(old,new)
text=text.replace(" if path=='$snapshot':return True", " if path=='$snapshot':return True\n if path.startswith('$binding.'):\n  p=path.split('.')\n  return len(p)==6 and p[1]=='ReadFile' and p[2].isdigit() and 0<=int(p[2])<4 and p[3].isdigit() and 1<=int(p[3])<=68 and p[4:]==['arguments','requested']")
# Preserve the old authored prefixes; v3 appends only the allowed assertions.
text=text.replace("  self.assertEqual(old['cases'],DATA['cases']);self.assertEqual(old['frames_hex'],DATA['frames_hex'])", "  for before,after in zip(old['cases'],DATA['cases']):\n   restored=dict(after,checks=before['checks']);self.assertEqual(restored,before)\n   self.assertEqual(after['checks'][:len(before['checks'])],before['checks'])\n  self.assertEqual(old['frames_hex'],DATA['frames_hex'])")
needle=" def test_source_absent_no_runtime_or_behavior_claim(self):"
assert text.count(needle)==1
new_tests=''' def test_independent17_requested_arguments_and_normalization(self):
  case=BY['short_read_attempt_exhaustion']
  requested=[c for c in case['checks'] if c['path'].startswith('$binding.')]
  self.assertEqual(len(requested),17)
  literal_size=COHORT['blobs'][0]['bytes'];self.assertEqual(literal_size,58)
  prior_literal_bytes=0
  for occurrence,(rule,check) in enumerate(zip(case['binding_overrides'],requested),1):
   counts=[a['value'] for a in rule['actions'] if a['hook']=='store_count']
   scalars=[a['value'] for a in rule['actions'] if a['hook']=='store_scalar']
   self.assertEqual(counts,[1]);self.assertEqual(scalars,[1])
   self.assertEqual(check,dict(at='final',path='$binding.ReadFile.0.'+str(occurrence)+'.arguments.requested',relation='eq',value=literal_size-prior_literal_bytes))
   prior_literal_bytes+=1
  self.assertEqual([c['value'] for c in requested],list(range(58,41,-1)))
  self.assertEqual(literal_size-prior_literal_bytes,41)
  aliases={b['id']:i for i,b in enumerate(COHORT['blobs'])}
  shapes={'CreateFileW':{'path','desired_access','share_mode','security','creation','flags','template'},'GetFileType':{'handle'},'GetFileInformationByHandleEx':{'handle','info_class','buffer_bytes'},'GetFinalPathNameByHandleW':{'handle','capacity','flags'},'GetFileSizeEx':{'handle'},'ReadFile':{'handle','requested','overlapped'},'CloseHandle':{'handle'}}
  for row in DATA['baseline_binding_inputs']:
   self.assertIn(row['file_id'],aliases)
   self.assertEqual(set(row['arguments']),shapes[row['api']])
   if row['api']=='CreateFileW':
    self.assertEqual(row['arguments'],dict(path=COHORT['blobs'][aliases[row['file_id']]]['path'],desired_access=2147483648,share_mode=1,security=None,creation=3,flags=2097280,template=None))
   elif row['api']=='ReadFile':
    self.assertEqual(row['arguments'],dict(handle=101+aliases[row['file_id']],requested=COHORT['blobs'][aliases[row['file_id']]]['bytes'],overlapped=None))
   for a in row['actions']:
    if a['hook']=='buffer_write':
     self.assertEqual(set(a),{'hook','frame_id'});self.assertIn(a['frame_id'],DATA['frames_hex'])
  self.assertIn('HARNESS-ONLY transport normalization',SCHEMA['binding_override_rule'])
  self.assertIn('NEVER the subject CallRef',SCHEMA['binding_override_rule'])

 def test_all45_finalized_noncomplete_statuses_closed_and_actual_domains_first(self):
  count=0
  for case in DATA['cases']:
   completed=any(c['path']=='status' and c['relation']=='eq' and c['value'] in ('PURE_SEAM_COMPLETE_CONSISTENT','PURE_SEAM_COMPLETE_NEGATIVE') for c in case['checks'])
   statuses=[c for c in case['checks'] if c['path']=='status' and c['relation']=='one_of']
   if completed:self.assertEqual(statuses,[])
   else:
    self.assertEqual(statuses,[dict(at='final',path='status',relation='one_of',value=['REFUSED','INCOMPLETE'])]);count+=1
  self.assertEqual(count,45)
  self.assertIn('BEFORE any expected comparison',SCHEMA['expected_comparison'])
  self.assertIn('bool never equals int',SCHEMA['expected_comparison'])
  self.assertIn('Failed-prefix and hard-cutoff monitors stay strict',SCHEMA['step_error_policy'])
  self.assertIn('No callback admitted at/after original hard_end',SCHEMA['step_error_policy'])

'''
text=text.replace(needle,new_tests+needle)
with (HERE/'check_shared_owner_integration_literals_v3.py').open('x',encoding='utf-8',newline='\n') as out:out.write(text)
print('Versioned data checker only; no fixture behavior or source execution.')
