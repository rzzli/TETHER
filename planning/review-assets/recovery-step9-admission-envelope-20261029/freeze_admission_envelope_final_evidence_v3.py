"""Freeze the complete NEW pure-component evidence; no subject replay."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def checked_json(name,digest):
 path=HERE/name;assert pin(path)['sha256']==digest,name;return json.loads(path.read_bytes())
def top_ast(path):
 tree=ast.parse(path.read_text(encoding='utf-8'));named={n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};other=[ast.dump(n,include_attributes=False) for n in tree.body if not isinstance(n,(ast.FunctionDef,ast.ClassDef))];return named,other
def main():
 evidence=checked_json('ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v4.json','5ba8af6c77ddf3f7e23bb377589abcc348a7fb91a59a5766c409672a640d94cf')
 author=checked_json('ADMISSION-ENVELOPE-AUTHOR-PROOF-v3.json','e05425e0679d64adaa3c420bb3fc9d83987b44a0d99a40486933bae45b03ead3')
 assert evidence['status']=='passed' and evidence['methods']==9 and evidence['original_vectors_matched']==30
 assert not evidence['failures'] and not evidence['errors'] and not evidence['audit_denials'] and not evidence['closed_import_denials'] and not evidence['original_check_exception_identity_failures']
 assert all(evidence['input_bytes_unchanged'].values()) and not any(evidence['qualification'].values())
 assert (evidence['actual_analysis_invocations'],evidence['actual_check_invocations'],evidence['actual_check_exceptions'],len(evidence['getter_invocations']))==(59,488,18,113)
 assert author['status']=='PASS' and author['methods']==8 and author['analyze_invocations']==50 and not author['audit_denials'] and all(r['passed'] is True for r in author['results'])
 assert author['source']==pin(HERE/'admission_envelope_v3.py')
 assert pin(HERE/'check_admission_envelope_author_v3.py')['sha256']==author['checker_sha256']
 focused=evidence['focused_regression_observations'];meta=evidence['metaclass_regression_observations']
 assert len(focused)==4 and len(meta)==1
 assert focused[0]['metrics']==dict(object_calls=1,generator_resumptions=0,key_yields=0)
 assert focused[0]['profile_restored'] is True and focused[0]['source_object_code_unchanged'] is True
 assert focused[1]['actual_code']=='TYPE_DOMAIN' and focused[1]['hook_calls']==[]
 assert focused[2]['actual_code']==focused[3]['actual_code']=='MODULE_GRAPH'
 assert meta[0]['actual_code']=='TYPE_DOMAIN' and meta[0]['metaclass_equality_calls']==[]
 inputs=dict(evidence['inputs'])
 for name,expected in inputs.items():assert pin(Path(expected['path']))==expected,name
 names=[
  'admission_envelope_v1.py','admission_envelope_v2.py','admission_envelope_v3.py',
  'ADMISSION-ENVELOPE-SOURCE-PAUSE-v1.json','ADMISSION-ENVELOPE-SOURCE-PAUSE-v2.json','ADMISSION-ENVELOPE-SOURCE-PAUSE-v3.json',
  'ADMISSION-ENVELOPE-SOURCE-DELTA-v1-to-v2.diff','ADMISSION-ENVELOPE-SOURCE-DELTA-v2-to-v3.diff',
  'ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v1.json','ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v2.json','ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v3.json','ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v4.json',
  'ADMISSION-ENVELOPE-AUTHOR-FIRST-PROOF-v1.json','ADMISSION-ENVELOPE-AUTHOR-PROOF-v2.json','ADMISSION-ENVELOPE-AUTHOR-PROOF-v3.json',
  'ADMISSION-ENVELOPE-INDEPENDENT-RUN-FREEZE-v1.json','ADMISSION-ENVELOPE-INDEPENDENT-RUN-FREEZE-v2.json','ADMISSION-ENVELOPE-INDEPENDENT-RUN-FREEZE-v3.json','ADMISSION-ENVELOPE-INDEPENDENT-RUN-FREEZE-v4.json',
  'ADMISSION-ENVELOPE-PRECODE-FIXTURE-FREEZE-v1.json','ADMISSION-ENVELOPE-PRECODE-PROVENANCE-v1.json','ADMISSION-ENVELOPE-PRECODE-STRUCTURAL-PROOF-v1.json','ADMISSION-ENVELOPE-INDEPENDENT-PREPARATION-PEER-v1.json',
  'ADMISSION-ENVELOPE-REGRESSION-FREEZE-v1.json','ADMISSION-ENVELOPE-INDEPENDENT-REGRESSION-BEFORE-v1.json',
  'ADMISSION-ENVELOPE-F2-METACLASS-FREEZE-v1.json','ADMISSION-ENVELOPE-F2-METACLASS-BEFORE-v1.json',
  'ADMISSION-ENVELOPE-ROOT-SOURCE-SCOPE-v1.json','ADMISSION-ENVELOPE-ROOT-RUNNER-CORRECTION-v2.json','ADMISSION-ENVELOPE-ROOT-REGRESSION-SCOPE-v2.json','ADMISSION-ENVELOPE-ROOT-CORRECTION-SCOPE-v2.json','ADMISSION-ENVELOPE-ROOT-F2-PROBE-SCOPE-v3.json','ADMISSION-ENVELOPE-ROOT-F2-CORRECTION-SCOPE-v3.json',
  'ADMISSION-ENVELOPE-SOURCE-INDEPENDENT-HOLD-v1.json','ADMISSION-ENVELOPE-INTEGER-GUARD-REVIEW-ADDENDUM-v2.json',
  'admission_envelope_independent_tests_v1.py','admission_envelope_regressions_v1.py','admission_envelope_f2_metaclass_regression_v1.py',
  'run_admission_envelope_independent_v1.py','run_admission_envelope_independent_v2.py','run_admission_envelope_independent_v3.py','run_admission_envelope_independent_v4.py','run_admission_envelope_regressions_before_v1.py','run_admission_envelope_f2_before_v1.py',
  'check_admission_envelope_author_v1.py','check_admission_envelope_author_v2.py','check_admission_envelope_author_v3.py',
 ]
 for name in names:inputs[name]=pin(HERE/name)
 versions=[top_ast(HERE/('admission_envelope_v'+str(v)+'.py')) for v in (1,2,3)]
 assert all(set(n)==set(versions[0][0]) for n,_ in versions)
 change12=sorted(k for k in versions[0][0] if versions[0][0][k]!=versions[1][0][k]);change23=sorted(k for k in versions[1][0] if versions[1][0][k]!=versions[2][0][k])
 assert change12==['_integer','_object','_steps'] and change23==['_integer']
 assert versions[0][1]==versions[1][1]==versions[2][1]
 method_names={r['method'] for r in author['results']};method_asts=[]
 for v in (1,2,3):
  tree=ast.parse((HERE/('check_admission_envelope_author_v'+str(v)+'.py')).read_text(encoding='utf-8'))
  method_asts.append({n.name:ast.dump(n,include_attributes=False) for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name in method_names})
 assert len(method_asts[0])==8 and method_asts[0]==method_asts[1]==method_asts[2]
 value=dict(schema_version=3,status='EXACT_V3_CALCULATOR_PURE_EVIDENCE_FROZEN_FINAL_SOURCE_PEER_PENDING',recorded_at_utc=datetime.now(timezone.utc).isoformat(),inputs=inputs,freezer=pin(Path(__file__).resolve()),subject_version=3,independent_methods=9,unique_original_metadata_vectors=30,original_test_methods=4,focused_regression_methods=4,metaclass_regression_methods=1,independent_analyze_invocations=59,independent_check_invocations=488,independent_original_check_exceptions=18,independent_getter_invocations=113,author_methods_separate=8,author_analyze_invocations_separate=50,source_delta=dict(V1_to_V2=change12,V2_to_V3=change23,all_other_top_level_ASTs_and_constants_equal=True),author_eight_assertion_ASTs_unchanged=True,focused_results=focused,metaclass_result=meta,source_and_test_bytes_unchanged=True,audit_denials=[],closed_import_denials=[],qualification=evidence['qualification'],chronology=[
  'The thirty literal vectors and e670 test module froze before V1 implementation; seven structural checks were data-only, not subject qualification.',
  'First independent V1 run003b retained27 audit denials from an omitted trusted UTF16LE preload. Root9719 authorized only a separately named bootstrap correction; same source/oracle then passed original30 in0cf04.',
  'V1 author7/8 and finite source HOLDda3 remained. Four independent methods5644/c82 froze before V2 correction and reproduced four source failures8a02.',
  'V2 changed exactly _object/_integer/_steps and passed original30+focused4 in a294; author8 passed335146. This did not erase the preserved findings or authorize runtime.',
  'One additional probe within F2, d158/1b106, froze before the next correction and reproduced five harmless metaclass equality calls in c4c84 despite TYPE_DOMAIN.',
  'Root1f38 authorized only the identity guard. V3 changed only _integer, froze before imports, and passed first independent9 in5ba8 plus unchanged author8 in e054.',
  'Runner versions3/4 do not encode inputs for logging, so the genuine int/metaclass probes remain untouched. Active audit, closed json/re/types imports and trusted9719 codec bootstrap stay intact.',
  'All local pre-run zero counters describe their named independent replay only; author controls ran separately after the same source pauses. No false zero-historical-subject-execution claim.',
  'This final freeze performs NEW metadata/hash/AST checks only and does not replay the subject.'
 ],limits=[
  'A pure declared-metadata calculator only. WITHIN_DECLARED_BOUNDS_ONLY is conditional arithmetic, not executable admission or authenticated file/source availability.',
  'Logical coefficients/storage/report/output terms are assumptions, not producer-layout, measured RSS/time or physical output bounds. Calculator JSON length is distinct from prospective runtime report V.',
  'No runtime cap/role/streaming integration, actual first entry, owner/nonce/lease/clock/FFI/Win32/source-closure/resource/profile/native/scientific qualification.',
  'Finite tests and active audit are ordinary source/pure evidence, not a hostile-Python security boundary. Application/defaults remain unchanged.'
 ],actual_target_API_calls=0,original_payload_operations=0,component_accepted=False,runtime_authorized=False)
 path=HERE/'ADMISSION-ENVELOPE-ACTUAL-EVIDENCE-FREEZE-v3.json'
 with path.open('xb') as out:out.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8'))
 print(json.dumps(dict(freeze=pin(path),inputs=len(inputs),independent_methods=9,original_vectors=30,author_methods=8)))
if __name__=='__main__':main()
