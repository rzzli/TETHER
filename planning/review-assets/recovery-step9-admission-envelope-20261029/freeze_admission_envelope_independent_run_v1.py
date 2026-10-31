"""Metadata/AST-only binding before the first independent subject replay."""
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
  'ADMISSION-ENVELOPE-ROOT-SOURCE-SCOPE-v1.json':'30644e8c0b59356b7dda2f9fde30f366fec80638945d051dc4c5baed1e8f74c3',
  'ADMISSION-ENVELOPE-SOURCE-PAUSE-v1.json':'1bf53afac8b3c00399d0ef0a821ed5de9055fd5ac47f3ae1287077c34ee955dd',
  'admission_envelope_v1.py':'4c86530b2cab406d2a78bb707a9efdfab5533432d64ee34312c2ad6287124242',
  'admission_envelope_independent_tests_v1.py':'e670199a7c4c50dc7eb540f8e5a021919464e67a891ef00fa48902d21b783bcc',
  'ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json':'cb4c6dd46cd8e02bc45c9bbec69a52f0a6ee1baea633eefaed85eeb018f57cc7',
  'run_admission_envelope_independent_v1.py':'3f9f87afb4fdc94b96a2a44df9206cbf20e27b64bbeefda3a37d31518a105d28',
 }
 pins={name:pin(HERE/name) for name in expected}
 for name,digest in expected.items():assert pins[name]['sha256']==digest,name
 root=json.loads((HERE/'ADMISSION-ENVELOPE-ROOT-SOURCE-SCOPE-v1.json').read_bytes());pause=json.loads((HERE/'ADMISSION-ENVELOPE-SOURCE-PAUSE-v1.json').read_bytes())
 assert pause['source']==pins['admission_envelope_v1.py'] and pause['root_scope_sha256']==pins['ADMISSION-ENVELOPE-ROOT-SOURCE-SCOPE-v1.json']['sha256']
 assert pause['trusted_imports']==['json','re','types'] and root['pure_subject_tests_authorized'] is True
 assert not (HERE/'ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v1.json').exists()
 for name in ('admission_envelope_v1.py','admission_envelope_independent_tests_v1.py','run_admission_envelope_independent_v1.py'):ast.parse((HERE/name).read_text(encoding='utf-8'))
 value=dict(schema_version=1,status='EXACT_RUNNER_SOURCE_AND_PRECODE_BINDINGS_FROZEN_BEFORE_FIRST_INDEPENDENT_EXECUTION',recorded_at_utc=datetime.now(timezone.utc).isoformat(),inputs=pins,freezer=pin(Path(__file__).resolve()),planned_subject_methods=4,unique_metadata_vectors=30,actual_function_and_check_invocations='To be observed separately; cancellation and detachment/interface controls reuse the frozen metadata.',local_independent_subject_imports=0,local_independent_subject_tests=0,chronology='OS author controls may run separately after the same pause. Local zero counters do not claim zero historical author executions; the source pause itself preceded any subject import/test.',qualification=root['qualification'],actual_target_API_calls=0,original_payload_operations=0,runtime_authorized=False)
 path=HERE/'ADMISSION-ENVELOPE-INDEPENDENT-RUN-FREEZE-v1.json'
 with path.open('xb') as out:out.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8'))
 print(json.dumps(dict(freeze=pin(path))))
if __name__=='__main__':main()
