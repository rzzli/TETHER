"""Retain the finite three-finding source HOLD; metadata/AST only."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PRE=ROOT.parent/'recovery-step9-production-preflight-20261029'
PINS={
 'admission_envelope_v1.py':'4c86530b2cab406d2a78bb707a9efdfab5533432d64ee34312c2ad6287124242',
 'ADMISSION-ENVELOPE-SOURCE-PAUSE-v1.json':'1bf53afac8b3c00399d0ef0a821ed5de9055fd5ac47f3ae1287077c34ee955dd',
 'ADMISSION-ENVELOPE-ROOT-SOURCE-SCOPE-v1.json':'30644e8c0b59356b7dda2f9fde30f366fec80638945d051dc4c5baed1e8f74c3',
 'ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v1.json':'003b948178c36037557a69fb2d945e36dcf0f13db21b5a9081e65f65c6801e68',
 'ADMISSION-ENVELOPE-ROOT-RUNNER-CORRECTION-v2.json':'97194dda516b87ef6f65f88b0b3c2dc77a006c16393c2d39342422efbd40daff',
 'ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v2.json':'0cf04ddbe83d147ce33b48b8b70e104430d841093a5999ddd9307a3062fa15a1',
 'ADMISSION-ENVELOPE-AUTHOR-FIRST-PROOF-v1.json':'c3f79da767d1270d437692e5e05c5378f9aea0736b307b4fec1168cd468f5113',
 'ADMISSION-ENVELOPE-ROOT-REGRESSION-SCOPE-v2.json':'f818874527df3702274cd67a00342081081295a856dc385d14bcc11693523bf1',
 'ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json':'cb4c6dd46cd8e02bc45c9bbec69a52f0a6ee1baea633eefaed85eeb018f57cc7',
 'admission_envelope_independent_tests_v1.py':'e670199a7c4c50dc7eb540f8e5a021919464e67a891ef00fa48902d21b783bcc',
}


def main():
 raw={};pins={}
 def capture(path,expected):
  b=path.read_bytes();digest=hashlib.sha256(b).hexdigest();assert digest==expected,path.name
  raw[path.name]=b;pins[path.name]=dict(path=str(path),bytes=len(b),sha256=digest)
 for name,digest in PINS.items():capture(ROOT/name,digest)
 capture(PRE/'ADMISSION-ENVELOPE-CALCULATOR-PROPOSAL-v1.json','038611daa69c5749def12d64dedc0b9afebdbfba2aff7d0e93981551e08d2cb8')
 capture(PRE/'ADMISSION-ENVELOPE-FINITE-CLARIFICATIONS-v2.json','57ff21a8955de95f61fa059543e33c1ace52726efbc36b286a52310af5addf97')
 tree=ast.parse(raw['admission_envelope_v1.py']);functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
 assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='len' for n in ast.walk(functions['_object']))
 corrected=json.loads(raw['ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v2.json']);assert corrected['status']=='passed' and corrected['matched_vector_count']==30 and corrected['methods']==4
 assert corrected['failures']==corrected['errors']==corrected['audit_denials']==[]
 author=json.loads(raw['ADMISSION-ENVELOPE-AUTHOR-FIRST-PROOF-v1.json']);assert author['methods']==8 and sum(r['passed'] for r in author['results'])==7
 findings=[
  dict(id='F1',kind='bounded structural capture',source_line=32,
   issue='_object iterates all caller keys for type validation and builds sets before refusing the wrong cardinality.',
   implication='An oversized exact built-in dictionary can force work/allocation beyond the promised fixed-size callback-free structural snapshot. The current source has no len guard in _object.',
   required='After exact dict type, reject the wrong key count in constant time before bounded key traversal/set construction; preserve ordinary key/type refusal semantics.',
   evidence='Static source and root confirmation; deterministic per-generator traversal probe is authorized but not yet executed by this reviewer.'),
  dict(id='F2',kind='exact built-in error domain',source_line=39,
   issue='_integer returns INTEGER_DOMAIN for an int subclass, while the effective exact-container rule requires TYPE_DOMAIN for subclasses.',
   implication='The frozen domain/error contract is not met, even though the object is rejected without numeric coercion.',
   required='Distinguish forbidden subclasses from ordinary wrong numeric values without calling conversion or arbitrary object hooks; bool remains INTEGER_DOMAIN.',
   evidence=pins['ADMISSION-ENVELOPE-AUTHOR-FIRST-PROOF-v1.json']),
  dict(id='F3',kind='deterministic validation precedence',source_line=155,
   issue='_steps computes the total size and checks aggregate consistency before declared module graph/binding validation, contrary to 57ff validation order.',
   implication='A typed cycle plus aggregate mismatch produces AGGREGATE_MISMATCH, and a typed cycle plus overflowing size sum reaches ARITHMETIC_OVERFLOW, before the required MODULE_GRAPH refusal.',
   required='Validate graph/binding first, then optional aggregate consistency and checked arithmetic in the declared order. Do not change fields, formulas or the thirty original expectations.',
   evidence='Static source ordering and root confirmation; the two exact before controls are authorized separately.'),
 ]
 report=dict(schema_version=1,status='HOLD_FINITE_THREE_SOURCE_BOUNDARIES',material_blockers=findings,
  reviewer='native_039_acceptance_audit',source=pins['admission_envelope_v1.py'],helper_sha256=PINS['admission_envelope_v1.py'],inputs=pins,
  finite_batch_complete=True,
  existing_evidence=dict(
   corrected_independent_methods=4,frozen_vectors_matched=30,actual_analyze_calls=54,check_invocations=462,injected_check_exceptions=18,report_getters=105,
   author_methods=8,author_passes=7,author_failures=1,
   first_runner='003b9481 preserves the trusted codec-load setup failure; it is not an arithmetic diagnosis. Named runner correction97194dda preloads UTF-16-LE before ACTIVE without changing source/oracle/audit semantics.'),
  confirmed_positive_scope=[
   'All thirty original literal vectors pass in corrected independent proof0cf04. This does not cover the three retained boundaries.',
   'The source imports json/re/types only, allocates metadata-sized structures rather than represented R/C/byte pools, and computes the twelve frozen comparisons and None/overflow projections consistently in the exercised corpus.',
   'Callback checks are outside private metadata-error catch regions, including final report/byte preparation; cached getters do not re-enter callbacks. Captured inputs and report outputs are detached/immutable in the exercised controls.',
  ],
  required_pre_fix_regressions=[
   'Oversized exact built-in dictionary: trusted profiling counts the actual key-validation generator, requiring zero traversal before size refusal. No timing proxy, source-global replacement or fake input container.',
   'An int-subclass numeric field returns TYPE_DOMAIN with no conversion/traversal hook.',
   'Cycle plus aggregate mismatch returns MODULE_GRAPH.',
   'Cycle plus otherwise overflowing known size sum returns MODULE_GRAPH before arithmetic.',
  ],
  authorization='Root scope f8188745 authorizes four frozen pre-fix controls only. No source correction is authorized by this HOLD; preserve source4c8653, all thirty expectations and both runner outcomes until subsequent root scope.',
  reviewer_subject_imports=0,reviewer_subject_tests=0,reviewed_source_or_fixture_edits=0,
  actual_API_calls=0,original_payload_operations=0,source_correction_authorized=False,
  production_owner_bound=False,runtime_authorized=False,profile_qualified=False,verification_complete=False)
 dest=ROOT/'ADMISSION-ENVELOPE-SOURCE-INDEPENDENT-HOLD-v1.json'
 with dest.open('x',encoding='utf-8',newline='\n') as s:json.dump(report,s,indent=2,sort_keys=True,allow_nan=False);s.write('\n')
 note='''# Admission-envelope first-source peer

**HOLD_FINITE_THREE_SOURCE_BOUNDARIES.** Source `4c86530b…` remains frozen. The fixed batch is: key traversal/set allocation before constant-time cardinality refusal; int-subclass INTEGER_DOMAIN instead of required TYPE_DOMAIN; and aggregate/total arithmetic before required graph/binding validation.

Corrected runner proof `0cf04ddb…` passes all30 original vectors/four methods with no audit denials. The first codec-load failure `003b9481…` is separately preserved as harness setup evidence. Author proof `c3f79da7…` passes7/8 and directly confirms the subclass code mismatch. Passing the original corpus does not close the three boundaries.

Root regression scope `f8188745…` permits exactly four pre-fix controls: deterministic key-generator traversal, int subclass, cycle+aggregate mismatch, and cycle+size-sum overflow. Freeze those expectations and retain actual V1 failures before any separately named source correction. No fourth family or original-oracle change is requested.

This peer read source/AST and retained evidence without importing/replaying the subject. No runtime, file/native, payload/source-closure or broader fit claim follows. Exact pins and correction requirements: [HOLD JSON](ADMISSION-ENVELOPE-SOURCE-INDEPENDENT-HOLD-v1.json).
'''
 md=ROOT/'ADMISSION-ENVELOPE-SOURCE-INDEPENDENT-HOLD-v1.md'
 with md.open('x',encoding='utf-8',newline='\n') as s:s.write(note)
 for path in (dest,md):
  b=path.read_bytes();print(json.dumps(dict(path=str(path),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())))


if __name__=='__main__':main()
