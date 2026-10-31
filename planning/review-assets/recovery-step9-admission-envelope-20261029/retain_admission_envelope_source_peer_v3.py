"""Exact final calculator peer retention; metadata/AST only, no subject replay."""
import ast
import copy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PRE=ROOT.parent/'recovery-step9-production-preflight-20261029'
EXACT={
 'admission_envelope_v1.py':'4c86530b2cab406d2a78bb707a9efdfab5533432d64ee34312c2ad6287124242',
 'admission_envelope_v2.py':'ea676476f37974e7e7c6c63062b27c798dec6874a3f8802f20229d13a0a71191',
 'admission_envelope_v3.py':'24889920f1f0d4e6f26130c053adde9cdf7f9e006a250f9f9bae274e61ac0501',
 'ADMISSION-ENVELOPE-ACTUAL-EVIDENCE-FREEZE-v3.json':'23d63277955322f5f72e838a40b9fd9440c37ae1439cd13f299c70fd0b8d6a18',
 'ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v4.json':'5ba8af6c77ddf3f7e23bb377589abcc348a7fb91a59a5766c409672a640d94cf',
 'ADMISSION-ENVELOPE-AUTHOR-PROOF-v3.json':'e05425e0679d64adaa3c420bb3fc9d83987b44a0d99a40486933bae45b03ead3',
 'ADMISSION-ENVELOPE-SOURCE-INDEPENDENT-HOLD-v1.json':'da3b47e59aca5d28971d55c1fe9cfc5157e487e18940f12c93b9ac6d02615b7b',
 'ADMISSION-ENVELOPE-INTEGER-GUARD-REVIEW-ADDENDUM-v2.json':'ad5bb432e1c92f4205a0ed09e875ecdd21f7d6fab6a73e51d18e9cb966810adf',
}


def normalize(tree,names):
 tree=copy.deepcopy(tree)
 for node in tree.body:
  if isinstance(node,ast.FunctionDef) and node.name in names:node.body=[ast.Pass()]
 return ast.dump(tree,include_attributes=False)


def main():
 raw={};pins={}
 def pin(path,digest=None,size=None):
  assert path.parent in (ROOT,PRE),str(path)
  key=str(path)
  if key not in pins:
   b=path.read_bytes();raw[path.name]=b;pins[key]=dict(path=key,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
  if digest is not None:assert pins[key]['sha256']==digest,path.name
  if size is not None:assert pins[key]['bytes']==size,path.name
  return pins[key]
 for name,digest in EXACT.items():pin(ROOT/name,digest)
 freeze=json.loads(raw['ADMISSION-ENVELOPE-ACTUAL-EVIDENCE-FREEZE-v3.json'])
 assert len(freeze['inputs'])==55
 for item in list(freeze['inputs'].values())+[freeze['freezer']]:pin(Path(item['path']),item['sha256'],item['bytes'])
 trees={version:ast.parse(raw['admission_envelope_v'+str(version)+'.py']) for version in (1,2,3)}
 assert normalize(trees[1],{'_object','_integer','_steps'})==normalize(trees[2],{'_object','_integer','_steps'})
 assert normalize(trees[2],{'_integer'})==normalize(trees[3],{'_integer'})
 tops={v:{n.name:ast.dump(n,include_attributes=False) for n in trees[v].body if isinstance(n,(ast.FunctionDef,ast.ClassDef))} for v in (1,2,3)}
 assert [k for k in tops[1] if tops[1][k]!=tops[2][k]]==['_object','_integer','_steps']
 assert [k for k in tops[2] if tops[2][k]!=tops[3][k]]==['_integer']
 integer=next(n for n in trees[3].body if isinstance(n,ast.FunctionDef) and n.name=='_integer')
 assert not any(isinstance(n,ast.Compare) and any(isinstance(op,(ast.In,ast.NotIn,ast.Eq,ast.NotEq)) for op in n.ops) for n in ast.walk(integer))
 imports=[ast.unparse(n) for n in trees[3].body if isinstance(n,(ast.Import,ast.ImportFrom))]
 assert imports==['import json','import re','from types import MappingProxyType']
 old=ROOT/'check_admission_envelope_author_v1.py';new=ROOT/'check_admission_envelope_author_v3.py';pin(old);pin(new)
 fa={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw[old.name]).body if isinstance(n,ast.FunctionDef) and n.name.startswith('t') and n.name[1:3].isdigit()}
 fb={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw[new.name]).body if isinstance(n,ast.FunctionDef) and n.name.startswith('t') and n.name[1:3].isdigit()};assert fa==fb and len(fa)==8
 proof=json.loads(raw['ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v4.json'])
 assert proof['status']=='passed' and proof['methods']==9 and proof['original_vectors_matched']==30
 assert proof['failures']==proof['errors']==proof['audit_denials']==proof['closed_import_denials']==[]
 assert proof['actual_analysis_invocations']==59 and proof['actual_check_invocations']==488 and proof['actual_check_exceptions']==18
 assert len(proof['focused_regression_observations'])==4 and len(proof['metaclass_regression_observations'])==1
 assert proof['focused_regression_observations'][0]['metrics']['key_yields']==0
 assert proof['focused_regression_observations'][1]['actual_code']=='TYPE_DOMAIN'
 assert all(x['actual_code']=='MODULE_GRAPH' for x in proof['focused_regression_observations'][2:])
 assert proof['metaclass_regression_observations'][0]['metaclass_equality_calls']==[]
 author=json.loads(raw['ADMISSION-ENVELOPE-AUTHOR-PROOF-v3.json']);assert author['methods']==8 and all(r['passed'] for r in author['results'])
 report=dict(schema_version=1,status='CLEAR_PURE_METADATA_CALCULATOR_SOURCE_V3',material_blockers=[],reviewer='native_039_acceptance_audit',
  source=pins[str(ROOT/'admission_envelope_v3.py')],helper_sha256=EXACT['admission_envelope_v3.py'],inputs=pins,
  evidence_freeze=pins[str(ROOT/'ADMISSION-ENVELOPE-ACTUAL-EVIDENCE-FREEZE-v3.json')],direct_freeze_pins_verified=55,
  resolved_findings=[
   dict(id='F1',resolution='Exact dict type and O(1) cardinality refusal precede key traversal/set allocation. The same profiled4096-key input now yields0 keys, with profiling restored.'),
   dict(id='F2',resolution='Numeric capture rejects subclasses as TYPE_DOMAIN without conversion or metaclass equality protocols. Exact built-in identity alternatives retain ordinary bool/float/string INTEGER_DOMAIN behavior. Same int-subclass and F2 metaclass observations both have no hooks.'),
   dict(id='F3',resolution='Module graph/binding validation now precedes optional aggregate consistency and checked total arithmetic. Both compound cycle cases return MODULE_GRAPH before mismatch/overflow.'),
  ],
  delta_review=dict(V1_to_V2_changed=['_object','_integer','_steps'],V2_to_V3_changed=['_integer'],other_top_level_ASTs_constants_imports_signatures_equal=True,new_or_removed_definitions=0,unchanged_author_assertion_bodies=8),
  static_review=[
   'The structural snapshot accepts only declared exact built-in containers/scalars and bounded lists/strings. It is detached before subsequent callbacks; raw caller hooks/coercions and mutable aliases are not used.',
   'ID permutation, lexical C/D paths, role/capture/module graph/binding, optional aggregate hints and deterministic validation order match the effective finite contract. Metadata identity is not file authenticity.',
   'Ceiling arithmetic uses quotient/remainder, checked sums/products avoid float/wrap/clamp, and None propagates without a fabricated zero. Exact known comparisons precede indeterminate status; aggregate-only ranges remain informational.',
   'All twelve independent declared limits compare their exact computed terms, with canonical ordinal violations and complete sizing arrays. Work/storage/output terms are logical declarations, not empirical RSS/time or actual producer layout.',
   'Check callbacks are outside metadata-error catches, including the final callback after immutable report/encoded-byte preparation. Getters return cached bytes or detached containers without callbacks/recalculation.',
   'There is no I/O, source loader, runtime constructor or loop/allocation over represented R/C/byte totals. Only bounded metadata and at most256 sizing rows are allocated. Imports remain json/re/types only.',
  ],
  retained_tests=dict(independent_methods=9,original_frozen_vectors=30,focused_three_family_methods=4,F2_metaclass_methods=1,analyze_invocations=59,check_invocations=488,preserved_check_exceptions=18,getter_invocations=113,author_methods_separate=8,author_analyze_calls_separate=50,audit_denials=0,closed_import_denials=0),
  preserved_history=[
   'The first003b runner retains trusted UTF-16 codec-load denials; root9719 authorized only a named pre-ACTIVE codec preload. Corrected0cf then passed the original30; no source arithmetic finding is inferred from the setup failure.',
   'Source V1/HOLD da3, author7/8 and pre-fix8a02 retain four failures. The four-method5644/c82 freeze predates V2 correction.',
   'V2 passed original30+four and author8 but the separately frozen d158/1b106 F2 observation c4c84 retained five equality-hook calls. V3 changes only that identity guard; earlier states and tests remain unchanged.',
   'Thirty/e670, four/5644 and one/d158 expectations are source-independent frozen inputs; no oracle was changed to fit a subject. Author8 assertions are identical across source versions.',
  ],
  scope_limits=[
   'This reviewer read source/AST and retained proofs and verified pins; no peer subject import, replay or new probe occurred.',
   'Clearance is for one pure metadata calculator. WITHIN_DECLARED_BOUNDS_ONLY is not executable admission, original authentication, capture/streaming support or a runtime cap lift.',
   'The30 corpus and representative API probes are finite rather than exhaustive; generic domain/graph correctness is supported by this source review, not a claim of all possible Python behavior or concurrent hostile atomicity.',
   'Calculator JSON bytes are not prospective runtime report V. Logical coefficients, slots, arrays and estimated peak are conditional declarations, not measured physical layout/RSS/300s fit.',
   'Real first-entry,14-export/FFI/physical sink, source/checker binding, full roster/new Unicode/resource/native/scientific/human gates remain open. Original failed recognition and whole-check timeout, application/default and provider/workers/monitor are unchanged.',
  ],
  reviewed_source_or_harness_or_oracle_edits=0,reviewer_subject_runs=0,actual_API_calls=0,original_payload_operations=0,
  root_component_acceptance_separate=True,FFI_registration_proven=False,originals_authenticated=False,production_owner_bound=False,real_checkers_bound=False,runtime_authorized=False,profile_qualified=False,verification_complete=False)
 dest=ROOT/'ADMISSION-ENVELOPE-SOURCE-INDEPENDENT-PEER-v3.json'
 with dest.open('x',encoding='utf-8',newline='\n') as s:json.dump(report,s,indent=2,sort_keys=True,allow_nan=False);s.write('\n')
 note='''# Admission-envelope corrected source peer

**CLEAR_PURE_METADATA_CALCULATOR_SOURCE_V3.** No material blocker remains in source `24889920…` and final evidence freeze `23d63277…`. All55 direct freeze pins were verified.

The three original findings close: key count is refused before traversal; numeric subclasses are rejected without equality/conversion hooks; graph/binding precedes aggregate consistency and arithmetic. The V2 guard regression is corrected with exact identity alternatives. Only `_object`, `_integer` and `_steps` changed from V1 to V2; only `_integer` changed from V2 to V3. Other ASTs/constants/API/imports and eight author assertion bodies remain equal.

The exact first V3 independent proof `5ba8af6c…` passes all30 original vectors, the same four boundary regressions and the same metaclass probe: nine methods,59 analyze calls,488 checks,18 preserved original check exceptions and113 getters. Author eight separately pass50 calls. The4096-key probe yields zero keys; both cycle cases select MODULE_GRAPH; integer and metaclass hooks are empty. No audit/import denial occurred. The reviewer did not rerun the subject.

All initial failures remain: codec bootstrap003b/correction9719, source V1/HOLD and four-before8a02, V2 passing suites plus the five-hook F2 beforec4c84. No corpus/test expectation was changed. The report is immutable/cached, callback errors stay outside data catches, and represented calls/bytes never drive allocations.

This is a metadata-only calculator, not runtime admission. Logical coefficients and report V establish no physical layout, time/RSS fit, original identity, streaming/native/FFI/source/checker or scientific qualification. Current runtime caps and the old failed profile/timeout remain unchanged. Root acceptance is separate. [Exact peer JSON](ADMISSION-ENVELOPE-SOURCE-INDEPENDENT-PEER-v3.json).
'''
 md=ROOT/'ADMISSION-ENVELOPE-SOURCE-INDEPENDENT-PEER-v3.md'
 with md.open('x',encoding='utf-8',newline='\n') as s:s.write(note)
 for p in (dest,md):
  b=p.read_bytes();print(json.dumps(dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())))


if __name__=='__main__':main()
