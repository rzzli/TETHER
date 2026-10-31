"""One retained runner-only correction: trusted UTF16LE codec preload."""
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
 original=HERE/'run_admission_envelope_independent_v1.py'
 assert pin(original)['sha256']=='3f9f87afb4fdc94b96a2a44df9206cbf20e27b64bbeefda3a37d31518a105d28'
 correction=HERE/'ADMISSION-ENVELOPE-ROOT-RUNNER-CORRECTION-v2.json'
 assert pin(correction)['sha256']=='97194dda516b87ef6f65f88b0b3c2dc77a006c16393c2d39342422efbd40daff'
 first=HERE/'ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v1.json'
 assert pin(first)['sha256']=='003b948178c36037557a69fb2d945e36dcf0f13db21b5a9081e65f65c6801e68'
 raw=original.read_text(encoding='utf-8')
 raw=raw.replace('ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v1.json','ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v2.json')
 old='started=time.monotonic();record=None;pins={};observations=[];analysis_calls=[];getter_calls=[]'
 assert raw.count(old)==1;raw=raw.replace(old,old+';bootstrap_codec_probe=None')
 old="  tests=load_test_module();subject=load_subject(source_path,source_raw)"
 new="""  # Root-authorized trusted bootstrap only; ACTIVE is still zero and the
  # source has not loaded. This does not exempt any active invocation IO.
  correction_path=HERE/'ADMISSION-ENVELOPE-ROOT-RUNNER-CORRECTION-v2.json'
  checked(correction_path,'97194dda516b87ef6f65f88b0b3c2dc77a006c16393c2d39342422efbd40daff');pins[correction_path.name]=pin(correction_path)
  first_path=HERE/'ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v1.json'
  checked(first_path,'003b948178c36037557a69fb2d945e36dcf0f13db21b5a9081e65f65c6801e68');pins[first_path.name]=pin(first_path)
  old_runner=HERE/'run_admission_envelope_independent_v1.py'
  checked(old_runner,'3f9f87afb4fdc94b96a2a44df9206cbf20e27b64bbeefda3a37d31518a105d28');pins[old_runner.name]=pin(old_runner)
  if ACTIVE[0]!=0:raise RuntimeError('codec bootstrap under active audit')
  codec_probe='A'.encode('utf-16-le','strict')
  if codec_probe!=b'A\\x00':raise RuntimeError('trusted UTF16LE probe')
  bootstrap_codec_probe=dict(codec='utf-16-le',literal='A',encoded_hex=codec_probe.hex(),active_depth=0,before_subject_load=True,scope='trusted standard-library lazy codec initialization, not a subject IO exemption')
  tests=load_test_module();subject=load_subject(source_path,source_raw)"""
 assert raw.count(old)==1;raw=raw.replace(old,new)
 raw=raw.replace("elapsed_seconds=time.monotonic()-started,qualification=", "elapsed_seconds=time.monotonic()-started,bootstrap_codec_probe=bootstrap_codec_probe,qualification=")
 raw=raw.replace("elapsed_seconds=time.monotonic()-started,actual_target_API_calls=0,original_payload_operations=0,runtime_authorized=False)","elapsed_seconds=time.monotonic()-started,bootstrap_codec_probe=bootstrap_codec_probe,actual_target_API_calls=0,original_payload_operations=0,runtime_authorized=False)")
 old="This is the first independent subject replay after exact root source scope and source pause. Author controls are separate evidence."
 new="This is the separately named runner-v2 replay after the retained v1 trusted-codec bootstrap failure. Source, oracle, active audit and closed imports are unchanged. Author controls are separate evidence."
 assert old in raw;raw=raw.replace(old,new)
 ast.parse(raw)
 path=HERE/'run_admission_envelope_independent_v2.py'
 with path.open('xb') as out:out.write(raw.encode('utf-8'))
 # Critical audit/import functions remain byte-semantic AST equal.
 before=ast.parse(original.read_text(encoding='utf-8'));after=ast.parse(raw)
 before_defs={n.name:ast.dump(n,include_attributes=False) for n in before.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
 after_defs={n.name:ast.dump(n,include_attributes=False) for n in after.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
 unchanged=[name for name in before_defs if before_defs[name]==after_defs[name]]
 assert set(before_defs)==set(after_defs) and set(before_defs)-set(unchanged)=={'main'}
 pins={name:pin(HERE/name) for name in ('admission_envelope_v1.py','admission_envelope_independent_tests_v1.py','ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json','ADMISSION-ENVELOPE-SOURCE-PAUSE-v1.json','ADMISSION-ENVELOPE-ROOT-SOURCE-SCOPE-v1.json')}
 freeze=publish('ADMISSION-ENVELOPE-INDEPENDENT-RUN-FREEZE-v2.json',dict(schema_version=2,status='RUNNER_ONLY_CODEC_PRELOAD_FROZEN_BEFORE_ONE_CORRECTED_REPLAY',recorded_at_utc=datetime.now(timezone.utc).isoformat(),runner=pin(path),previous_runner=pin(original),first_failure=pin(first),root_correction=pin(correction),inputs=pins,unchanged_function_and_class_ASTs=unchanged,sole_changed_function='main: trusted UTF16LE probe before source loading plus proof/pin/provenance names',author=pin(Path(__file__).resolve()),active_audit_unchanged=True,closed_subject_imports_unchanged=True,source_and_oracle_unchanged=True,local_corrected_runner_subject_runs=0,actual_target_API_calls=0,original_payload_operations=0,runtime_authorized=False))
 print(json.dumps(dict(runner=pin(path),freeze=freeze,unchanged_ASTs=len(unchanged))))
if __name__=='__main__':main()
