"""Freeze exact V2-source bindings before the first combined eight-method run."""
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
  'ADMISSION-ENVELOPE-ROOT-CORRECTION-SCOPE-v2.json':'82ff068c7ab2d6864da45a6f547b1266adbb5e278e4412092a3c23930fe3f39b',
  'ADMISSION-ENVELOPE-SOURCE-PAUSE-v2.json':'075026212bb247cc0655ed4fb517b2b8d28059adbb0dfd8c415b9276f84d971b',
  'admission_envelope_v2.py':'ea676476f37974e7e7c6c63062b27c798dec6874a3f8802f20229d13a0a71191',
  'admission_envelope_independent_tests_v1.py':'e670199a7c4c50dc7eb540f8e5a021919464e67a891ef00fa48902d21b783bcc',
  'ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json':'cb4c6dd46cd8e02bc45c9bbec69a52f0a6ee1baea633eefaed85eeb018f57cc7',
  'admission_envelope_regressions_v1.py':'5644882f8d67c0121b4967538d3af9eedf200266792bdb0d07b08e0392171e34',
  'ADMISSION-ENVELOPE-INDEPENDENT-REGRESSION-BEFORE-v1.json':'8a02fb18aed5469637e11ff990dacad35e5e4472b3d7ae217c45756ab286be05',
  'ADMISSION-ENVELOPE-ROOT-RUNNER-CORRECTION-v2.json':'97194dda516b87ef6f65f88b0b3c2dc77a006c16393c2d39342422efbd40daff',
  'run_admission_envelope_independent_v2.py':'a2c60af1ff63c1c1bf8d21b0443be5dc54ac041dd9c90bfd048599c6a32d4265',
  'run_admission_envelope_independent_v3.py':'79d45135922eba9e0b79fb34737eef39eb2a412bc40b9400106bdd65298c9b89',
 }
 pins={name:pin(HERE/name) for name in expected}
 for name,digest in expected.items():assert pins[name]['sha256']==digest,name
 assert json.loads((HERE/'ADMISSION-ENVELOPE-SOURCE-PAUSE-v2.json').read_bytes())['source']==pins['admission_envelope_v2.py']
 assert not (HERE/'ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v3.json').exists()
 ast.parse((HERE/'run_admission_envelope_independent_v3.py').read_text(encoding='utf-8'))
 value=dict(schema_version=3,status='V2_SOURCE_AND_UNCHANGED_EIGHT_METHOD_BINDINGS_FROZEN_BEFORE_FIRST_LOCAL_REPLAY',recorded_at_utc=datetime.now(timezone.utc).isoformat(),inputs=pins,freezer=pin(Path(__file__).resolve()),subject_module_name='admission_envelope_v2',original_methods=4,focused_regression_methods=4,unique_original_metadata_vectors=30,local_V2_source_imports=0,local_V2_subject_tests=0,retained_audit_and_import_map='Exact audit/active_call from pinned runnerV2; only json,re,types supplied to fresh subject. No old subject/cache fallback.',observation_only_delta='Do not encode input for per-invocation logging, avoiding any incidental coercion of the genuine int-subclass probe. Original inputs are passed untouched; corpus/test/source pins and strict comparisons remain.',chronology='OS author controls may already have run after the same source pause. Local zero counters apply only to this independent combined runner. The focused methods and their intended-green expectations predate V2 correction.',actual_target_API_calls=0,original_payload_operations=0,runtime_authorized=False)
 path=HERE/'ADMISSION-ENVELOPE-INDEPENDENT-RUN-FREEZE-v3.json'
 with path.open('xb') as out:out.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8'))
 print(json.dumps(dict(freeze=pin(path),methods=8,metadata_vectors=30)))
if __name__=='__main__':main()
