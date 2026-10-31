"""Bind the same nine predeclared methods to the frozen V3 source only."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def publish(name,value):
 path=HERE/name
 with path.open('xb') as out:out.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8'))
 return pin(path)
def main():
 original=HERE/'run_admission_envelope_independent_v3.py';assert pin(original)['sha256']=='79d45135922eba9e0b79fb34737eef39eb2a412bc40b9400106bdd65298c9b89'
 scope=HERE/'ADMISSION-ENVELOPE-ROOT-F2-CORRECTION-SCOPE-v3.json';assert pin(scope)['sha256']=='1f38f0424b9a97b320593ddbdec1f7968f1c12a2457ff86cd0585901acdda893'
 pause=HERE/'ADMISSION-ENVELOPE-SOURCE-PAUSE-v3.json';assert pin(pause)['sha256']=='f5636f7420f818a7c0f212c678bfa8d959b94cdc67b1ad8199e288c7d22a19e5'
 source=HERE/'admission_envelope_v3.py';assert pin(source)['sha256']=='24889920f1f0d4e6f26130c053adde9cdf7f9e006a250f9f9bae274e61ac0501'
 assert json.loads(pause.read_bytes())['source']==pin(source)
 raw=original.read_text(encoding='utf-8')
 raw=raw.replace('ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v3.json','ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v4.json')
 replacements={
  'source replay: original30/four methods + same focused4.':'source replay: original30/four methods + same focused4 + same F2 method.',
  'observations=[];focused=[];calls=[];getters=[]':'observations=[];focused=[];metaclass=[];calls=[];getters=[]',
  "pause_path=HERE/'ADMISSION-ENVELOPE-SOURCE-PAUSE-v2.json'":"pause_path=HERE/'ADMISSION-ENVELOPE-SOURCE-PAUSE-v3.json'",
  '075026212bb247cc0655ed4fb517b2b8d28059adbb0dfd8c415b9276f84d971b':'f5636f7420f818a7c0f212c678bfa8d959b94cdc67b1ad8199e288c7d22a19e5',
  "source_path=HERE/'admission_envelope_v2.py'":"source_path=HERE/'admission_envelope_v3.py'",
  'ea676476f37974e7e7c6c63062b27c798dec6874a3f8802f20229d13a0a71191':'24889920f1f0d4e6f26130c053adde9cdf7f9e006a250f9f9bae274e61ac0501',
  "name='admission_envelope_v2'":"name='admission_envelope_v3'",
  "result.testsRun==8":"result.testsRun==9",
  "len(focused)==4 and":"len(focused)==4 and len(metaclass)==1 and",
  "focused_regression_observations=focused,":"focused_regression_observations=focused,metaclass_regression_observations=metaclass,",
  "focused_methods=4,":"focused_methods=4,metaclass_methods=1,",
  "Same original30/e670 and same four5644 tests, all frozen before V2 correction; four BEFORE failures8a02 preserved. First coherent V2-source replay only.":"Same original30/e670, same four5644, and same F2 d158 tests. Their expected states froze before the corresponding implementation/corrections. Both BEFORE proofs8a02/c4c8 and first V2 pass a294 remain preserved. First coherent V3-source replay only.",
  "Fresh admission_envelope_v2 from":"Fresh admission_envelope_v3 from",
 }
 for old,new in replacements.items():assert old in raw,old;raw=raw.replace(old,new)
 anchor="  pause_path=HERE/'ADMISSION-ENVELOPE-SOURCE-PAUSE-v3.json'"
 insertion="""  final_scope_path=HERE/'ADMISSION-ENVELOPE-ROOT-F2-CORRECTION-SCOPE-v3.json'
  final_scope=json.loads(checked(final_scope_path,'1f38f0424b9a97b320593ddbdec1f7968f1c12a2457ff86cd0585901acdda893'));pins[final_scope_path.name]=pin(final_scope_path)
  if final_scope['target']!='admission_envelope_v3.py' or final_scope['source_correction_authorized'] is not True:raise RuntimeError('F2 correction role')
  for filename,digest in final_scope['inputs'].items():
   if Path(filename).name!=filename:raise RuntimeError('F2 technical locator')
   checked(HERE/filename,digest);pins[filename]=pin(HERE/filename)
"""
 assert raw.count(anchor)==1;raw=raw.replace(anchor,insertion+anchor)
 anchor="  suite=unittest.TestSuite()"
 insertion="""  f2_path=HERE/'admission_envelope_f2_metaclass_regression_v1.py';pins[f2_path.name]=pin(f2_path)
  f2=load_harness('independent_admission_same_f2_v1',f2_path,'d158e3db6f2ebc4aedcfc168d2dcd9ffb383047c850e10c842c8855ca4990f93')
"""
 assert raw.count(anchor)==1;raw=raw.replace(anchor,insertion+anchor)
 anchor="  result=unittest.TextTestRunner(verbosity=2,resultclass=R.Results).run(suite)"
 insertion="  suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(f2.make_tests(subject,corpus,original,invoke,metaclass)))\n"
 assert raw.count(anchor)==1;raw=raw.replace(anchor,insertion+anchor)
 raw=raw.replace('FIRST_V2_SOURCE_','FIRST_V3_SOURCE_').replace('First coherent V2-source','First coherent V3-source')
 ast.parse(raw)
 runner=HERE/'run_admission_envelope_independent_v4.py'
 with runner.open('xb') as out:out.write(raw.encode('utf-8'))
 expected={
  'admission_envelope_independent_tests_v1.py':'e670199a7c4c50dc7eb540f8e5a021919464e67a891ef00fa48902d21b783bcc',
  'ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json':'cb4c6dd46cd8e02bc45c9bbec69a52f0a6ee1baea633eefaed85eeb018f57cc7',
  'admission_envelope_regressions_v1.py':'5644882f8d67c0121b4967538d3af9eedf200266792bdb0d07b08e0392171e34',
  'admission_envelope_f2_metaclass_regression_v1.py':'d158e3db6f2ebc4aedcfc168d2dcd9ffb383047c850e10c842c8855ca4990f93',
 }
 pins={name:pin(HERE/name) for name in expected}
 for name,digest in expected.items():assert pins[name]['sha256']==digest,name
 pins.update({p.name:pin(p) for p in (scope,pause,source,runner,original)})
 assert not (HERE/'ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v4.json').exists()
 freeze=publish('ADMISSION-ENVELOPE-INDEPENDENT-RUN-FREEZE-v4.json',dict(schema_version=4,status='V3_SOURCE_SAME_NINE_METHODS_FROZEN_BEFORE_FIRST_LOCAL_REPLAY',recorded_at_utc=datetime.now(timezone.utc).isoformat(),inputs=pins,author=pin(Path(__file__).resolve()),original_methods=4,unique_original_metadata_vectors=30,focused_methods=4,metaclass_methods=1,local_source_imports=0,local_source_tests=0,source_module_name='admission_envelope_v3',codec_and_audit='Retained9719 bootstrap and exact active audit utilities a2c60af1; trusted subject imports remain json/re/types only.',chronology='OS author controls may run separately after the same pause. All test source and expected states are unchanged and predate their corresponding fixes. Prior sources/proofs remain immutable.',actual_target_API_calls=0,original_payload_operations=0,runtime_authorized=False))
 print(json.dumps(dict(runner=pin(runner),freeze=freeze,methods=9,unique_metadata_vectors=30)))
if __name__=='__main__':main()
