"""Freeze the one allowed F2 metaclass regression before source correction."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
 expected={
  'ADMISSION-ENVELOPE-ROOT-F2-PROBE-SCOPE-v3.json':'940f439f8e1a8c9db50b2f60d2810ed9243db11baeba29e31996ff748a9b84c9',
  'ADMISSION-ENVELOPE-SOURCE-PAUSE-v2.json':'075026212bb247cc0655ed4fb517b2b8d28059adbb0dfd8c415b9276f84d971b',
  'admission_envelope_v2.py':'ea676476f37974e7e7c6c63062b27c798dec6874a3f8802f20229d13a0a71191',
  'ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v3.json':'a29436c87d0b166a3b741fa329c1382db0db6d243745e26a1695aa05fc60dbb3',
  'ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json':'cb4c6dd46cd8e02bc45c9bbec69a52f0a6ee1baea633eefaed85eeb018f57cc7',
  'admission_envelope_independent_tests_v1.py':'e670199a7c4c50dc7eb540f8e5a021919464e67a891ef00fa48902d21b783bcc',
  'admission_envelope_regressions_v1.py':'5644882f8d67c0121b4967538d3af9eedf200266792bdb0d07b08e0392171e34',
  'run_admission_envelope_independent_v2.py':'a2c60af1ff63c1c1bf8d21b0443be5dc54ac041dd9c90bfd048599c6a32d4265',
 }
 pins={name:pin(HERE/name) for name in expected}
 for name,digest in expected.items():assert pins[name]['sha256']==digest,name
 for name in ('admission_envelope_f2_metaclass_regression_v1.py','run_admission_envelope_f2_before_v1.py'):
  pins[name]=pin(HERE/name);ast.parse((HERE/name).read_text(encoding='utf-8'))
 tree=ast.parse((HERE/'admission_envelope_f2_metaclass_regression_v1.py').read_text(encoding='utf-8'))
 methods=[n.name for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
 assert len(methods)==1 and not (HERE/'admission_envelope_v3.py').exists()
 value=dict(schema_version=1,status='ONE_F2_METHOD_FROZEN_BEFORE_ANY_METACLASS_SOURCE_CORRECTION',recorded_at_utc=datetime.now(timezone.utc).isoformat(),inputs=pins,freezer=pin(Path(__file__).resolve()),methods=methods,input='Existing mixed-role baseline; only bulk size becomes an int subclass with a metaclass __eq__ that appends builtin-name labels and returns False.',expected=dict(code='TYPE_DOMAIN',producer_metaclass_equality_calls=[],source_and_oracle_unchanged=True),local_probe_subject_runs=0,source_correction_exists=False,scope='One regression within existing F2 exact-built-in/no-producer-hook contract, not a new family or a hostile-Python sandbox claim.',actual_target_API_calls=0,original_payload_operations=0,runtime_authorized=False)
 path=HERE/'ADMISSION-ENVELOPE-F2-METACLASS-FREEZE-v1.json'
 with path.open('xb') as out:out.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8'))
 print(json.dumps(dict(freeze=pin(path),probe=pins['admission_envelope_f2_metaclass_regression_v1.py'],methods=1,subject_runs=0)))
if __name__=='__main__':main()
