"""Freeze exactly four intended-correctness controls before correction code."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
 names={
  'ADMISSION-ENVELOPE-ROOT-REGRESSION-SCOPE-v2.json':'f818874527df3702274cd67a00342081081295a856dc385d14bcc11693523bf1',
  'ADMISSION-ENVELOPE-SOURCE-PAUSE-v1.json':'1bf53afac8b3c00399d0ef0a821ed5de9055fd5ac47f3ae1287077c34ee955dd',
  'admission_envelope_v1.py':'4c86530b2cab406d2a78bb707a9efdfab5533432d64ee34312c2ad6287124242',
  'ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json':'cb4c6dd46cd8e02bc45c9bbec69a52f0a6ee1baea633eefaed85eeb018f57cc7',
  'admission_envelope_independent_tests_v1.py':'e670199a7c4c50dc7eb540f8e5a021919464e67a891ef00fa48902d21b783bcc',
  'ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v1.json':'003b948178c36037557a69fb2d945e36dcf0f13db21b5a9081e65f65c6801e68',
  'ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v2.json':'0cf04ddbe83d147ce33b48b8b70e104430d841093a5999ddd9307a3062fa15a1',
  'run_admission_envelope_independent_v2.py':'a2c60af1ff63c1c1bf8d21b0443be5dc54ac041dd9c90bfd048599c6a32d4265',
  'ADMISSION-ENVELOPE-SOURCE-INDEPENDENT-HOLD-v1.json':'da3b47e59aca5d28971d55c1fe9cfc5157e487e18940f12c93b9ac6d02615b7b',
 }
 pins={name:pin(HERE/name) for name in names}
 for name,digest in names.items():assert pins[name]['sha256']==digest,name
 for name in ('admission_envelope_regressions_v1.py','run_admission_envelope_regressions_before_v1.py'):
  pins[name]=pin(HERE/name);ast.parse((HERE/name).read_text(encoding='utf-8'))
 tree=ast.parse((HERE/'admission_envelope_regressions_v1.py').read_text(encoding='utf-8'))
 methods=[n.name for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
 assert len(methods)==4
 assert not (HERE/'admission_envelope_v2.py').exists()
 value=dict(schema_version=1,status='FOUR_REGRESSION_METHODS_AND_EXPECTATIONS_FROZEN_BEFORE_SOURCE_CORRECTION',recorded_at_utc=datetime.now(timezone.utc).isoformat(),inputs=pins,freezer=pin(Path(__file__).resolve()),methods=methods,expected_green=[dict(method=methods[0],input='Exact built-in dictionary with4096 bounded ordinary string keys, including the seven valid top keys.',expectation='SCHEMA_KEYS with exactly one real source _object call and zero key-validation generator yields/resumptions before rejection. Profile original restored; no source-code/global replacement.'),dict(method=methods[1],input='Only bulk size replaced by an int subclass; all hooks instrumented to fail if entered.',expectation='TYPE_DOMAIN, zero protocol hooks and all-false qualification.'),dict(method=methods[2],input='Valid baseline plus toy_leaf↔toy_entry cycle and aggregate bytes65747 instead of65746.',expectation='MODULE_GRAPH before aggregate consistency; safe refusal projection.'),dict(method=methods[3],input='Valid baseline plus same cycle, bulk size2^63-1 and aggregate.bytes=None, so a later size sum would overflow.',expectation='MODULE_GRAPH before total arithmetic; safe refusal projection.')],profiling='Trusted CPython sys.setprofile is installed outside audited invocation and observes actual code objects/generator yields only. Source _object and actual built-in dict are unchanged. No timing or complete operation-count inference.',local_regression_subject_runs=0,correction_source_exists=False,original_30_and_test_module_unchanged=True,source_correction_authorized=False,scope='Exactly four NEW pure pre-fix methods on preserved source V1. No runtime/native/source-closure/resource/model or actual file operation.',actual_target_API_calls=0,original_payload_operations=0,qualification=dict(FFI_registration_proven=False,originals_authenticated=False,production_owner_bound=False,profile_qualified=False,real_checkers_bound=False,runtime_authorized=False,verification_complete=False))
 path=HERE/'ADMISSION-ENVELOPE-REGRESSION-FREEZE-v1.json'
 with path.open('xb') as out:out.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8'))
 print(json.dumps(dict(freeze=pin(path),regressions=pins['admission_envelope_regressions_v1.py'],runner=pins['run_admission_envelope_regressions_before_v1.py'],methods=4,subject_runs=0)))
if __name__=='__main__':main()
