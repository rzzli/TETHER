"""Retain one pending F2 guard risk; metadata/AST only, no subject replay."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
 inputs={}
 for name,digest in {
  'admission_envelope_v2.py':'ea676476f37974e7e7c6c63062b27c798dec6874a3f8802f20229d13a0a71191',
  'ADMISSION-ENVELOPE-SOURCE-PAUSE-v2.json':'075026212bb247cc0655ed4fb517b2b8d28059adbb0dfd8c415b9276f84d971b',
  'ADMISSION-ENVELOPE-SOURCE-INDEPENDENT-HOLD-v1.json':'da3b47e59aca5d28971d55c1fe9cfc5157e487e18940f12c93b9ac6d02615b7b',
 }.items():
  p=ROOT/name;b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==digest
  inputs[name]=dict(path=str(p),bytes=len(b),sha256=digest)
  if name.endswith('.py'):tree=ast.parse(b)
 function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_integer')
 expression=next(n for n in ast.walk(function) if isinstance(n,ast.Compare) and any(isinstance(op,ast.In) for op in n.ops))
 report=dict(schema_version=1,status='HOLD_EXISTING_F2_GUARD_RISK_PENDING_ONE_PREFX_OBSERVATION',
  reviewer='native_039_acceptance_audit',inputs=inputs,existing_family='F2 exact built-in numeric capture without producer hooks',
  source_line=expression.lineno,expression=ast.unparse(expression),
  risk='Tuple membership uses equality rather than exact identity. A supplied int subclass whose metaclass overrides equality may execute that hook while the numeric whitelist is tested, before TYPE_DOMAIN refusal.',
  contract='Effective57ff requires exact built-in capture without arbitrary input protocols; the explicit check callable is the only intended injected callback. Rejecting the value afterward does not erase a hook invocation.',
  actual_subject_observation=None,
  finite_probe_plan='One root-authorized analyze call on the frozen V2 using a numeric int-subclass field and a metaclass equality hook that records calls and returns False. Expected TYPE_DOMAIN with zero producer-hook calls. Preserve current source, original30/four regression modules and all first results. No source-global substitution or new contract family.',
  possible_minimal_correction='Only if confirmed: use exact identity alternatives for the existing whitelist, in a separately named successor. No API/schema/formula/cap/role/vector change.',
  root_direction='Delivered root message agrees this is within F2, authorizes retention of this finite addendum and will separately authorize one pre-fix observation before any source change.',
  other_review_scope='The three planned V2 corrections are present. Original30 plus four regressions and author controls remain distinct evidence; final clearance is withheld pending first independent V2 proof and the single observation.',
  further_families_requested=0,reviewer_subject_imports=0,reviewer_subject_tests=0,source_edits=0,
  actual_API_calls=0,original_payload_operations=0,source_correction_authorized=False,
  runtime_authorized=False,profile_qualified=False,verification_complete=False)
 out=ROOT/'ADMISSION-ENVELOPE-INTEGER-GUARD-REVIEW-ADDENDUM-v2.json'
 with out.open('x',encoding='utf-8',newline='\n') as s:json.dump(report,s,indent=2,sort_keys=True,allow_nan=False);s.write('\n')
 text='''# Pending numeric-guard observation

The frozen V2 numeric whitelist uses equality-based tuple membership. An int subclass with custom metaclass equality may therefore execute a producer hook before refusal. This is a possible regression within existing F2, not a fourth contract family.

The reviewer has not executed the subject. Root will authorize exactly one recorded pre-fix observation on frozen V2; source, original30 and four regressions stay unchanged. Expected behavior is TYPE_DOMAIN with zero producer-hook calls. If confirmed, identity alternatives in this whitelist are the proposed minimal correction, requiring separate root scope and a named successor.

Final clearance remains pending. [Exact addendum](ADMISSION-ENVELOPE-INTEGER-GUARD-REVIEW-ADDENDUM-v2.json).
'''
 md=ROOT/'ADMISSION-ENVELOPE-INTEGER-GUARD-REVIEW-ADDENDUM-v2.md'
 with md.open('x',encoding='utf-8',newline='\n') as s:s.write(text)
 for p in (out,md):
  b=p.read_bytes();print(json.dumps(dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())))


if __name__=='__main__':main()
