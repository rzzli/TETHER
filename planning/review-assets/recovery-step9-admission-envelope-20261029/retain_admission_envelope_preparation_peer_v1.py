"""Finite frozen-fixture review, not a reusable admission calculator.

Only fixed corpus cases are inspected. No subject or test module is imported.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PRE=ROOT.parent/'recovery-step9-production-preflight-20261029'
EXPECTED={
 'ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json':'cb4c6dd46cd8e02bc45c9bbec69a52f0a6ee1baea633eefaed85eeb018f57cc7',
 'admission_envelope_independent_tests_v1.py':'e670199a7c4c50dc7eb540f8e5a021919464e67a891ef00fa48902d21b783bcc',
 'ADMISSION-ENVELOPE-PRECODE-STRUCTURAL-PROOF-v1.json':'d0def250de6789e43c86bc01cdaf6244adfdfe009206ab26224fad349b52832d',
 'ADMISSION-ENVELOPE-PRECODE-PROVENANCE-v1.json':'47fd6844946e7eab60672787704ecf85082f660e15031303fde71f0d1dd5d40f',
 'ADMISSION-ENVELOPE-PRECODE-FIXTURE-FREEZE-v1.json':'5478b0144c737ff8876c9273fe5281790f3fe97aa5b7cfac2bae4b1d4d222bc6',
}


def main():
 raw={};pins={}
 def capture(path,expected=None,size=None):
  assert path.parent in (ROOT,PRE),str(path)
  key=str(path)
  if key not in pins:
   b=path.read_bytes();raw[path.name]=b;pins[key]=dict(path=key,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
  if expected is not None:assert pins[key]['sha256']==expected,path.name
  if size is not None:assert pins[key]['bytes']==size,path.name
  return pins[key]
 for name,digest in EXPECTED.items():capture(ROOT/name,digest)
 proposal=capture(PRE/'ADMISSION-ENVELOPE-CALCULATOR-PROPOSAL-v1.json','038611daa69c5749def12d64dedc0b9afebdbfba2aff7d0e93981551e08d2cb8')
 clarification=capture(PRE/'ADMISSION-ENVELOPE-FINITE-CLARIFICATIONS-v2.json','57ff21a8955de95f61fa059543e33c1ace52726efbc36b286a52310af5addf97')
 freeze=json.loads(raw['ADMISSION-ENVELOPE-PRECODE-FIXTURE-FREEZE-v1.json'])
 def pinwalk(v):
  if type(v) is dict:
   if {'path','bytes','sha256'}<=set(v):capture(Path(v['path']),v['sha256'],v['bytes'])
   else:
    for child in v.values():pinwalk(child)
  elif type(v) is list:
   for child in v:pinwalk(child)
 pinwalk(freeze)
 corpus=json.loads(raw['ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json']);vs=corpus['vectors'];assert len(vs)==30
 assert [v['ordinal'] for v in vs]==list(range(30)) and len({v['id'] for v in vs})==30
 baseline=vs[0];meta=baseline['metadata'];expected=baseline['expected'];d=expected['derived']
 assert [f['id'] for f in meta['files']]==[2,0,3,1]
 assert [f['role'] for f in meta['files']]==['captured_software','captured_software','captured_metadata','hash_only_bulk']
 assert meta['early_ids']==[2,0] and [m['file_id'] for m in meta['modules']]==[2,0]
 assert meta['modules'][0]['dependencies']==[] and meta['modules'][1]['dependencies']==['toy_leaf']
 canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
 arithmetic=[]
 # Only these six fixed, semantically valid literal cases are recomputed. This
 # is arithmetic corroboration, not a general validator/status solver.
 for index in (0,13,14,16,17,21):
  case=vs[index];m=case['metadata'];e=case['expected']['derived'];r=m['representation']
  n=4;b=2;modules=2;cap=209;bulk=m['files'][3]['size']
  q=sum(divmod(f['size'],65536)[0]+bool(divmod(f['size'],65536)[1]) for f in m['files'])
  positive=sum(f['size']>0 for f in m['files']);reads=q+16*positive;calls=6*n+reads;events=224
  closures=len(canonical([dict(file_id=i,invoked=False,return_observed=False,success=False) for i in range(4)]))
  digests=len(canonical([dict(file_id=i,size=f['size'],sha256=f['sha256']) for i,f in enumerate(m['files'])]))
  packet=43+closures+digests;journal=1024*events
  report=None if r['report_call_bytes'] is None else 29+calls*31+4*37+events*41
  logical=None if r['call_record_bytes'] is None else calls*11
  output=None if report is None else journal+5*packet+report
  peak=None if logical is None or report is None else 106819+209+23+logical+86+76+2*journal+5*packet+2*report
  checks=dict(N=n,B=b,M=modules,total_bytes=cap+bulk,positive_files=positive,Q=q,R=reads,C=calls,E=events,captured_bytes=cap,hash_only_bytes=bulk,
   query_witness_bytes=4*8218,work_buffer_bytes=73738,raw_payload_bytes=106819,immutable_capture_bytes=209,logical_call_bytes=logical,index_bytes=86,hash_state_bytes=76,
   journal_bytes=journal,canonical_report_bytes=report,closure_array_bound_bytes=closures,digest_array_bytes=digests,packet_bound_bytes=packet,output_reserved_bytes=output,peak_declared_memory_bytes=peak)
  for key,value in checks.items():assert type(e[key]) is type(value) and e[key]==value,(case['id'],key,e[key],value)
  arithmetic.append(dict(vector=case['id'],derived_fields_checked=len(checks),Q=q,R=reads,C=calls,packet=packet,output=output,peak=peak))
 assert (d['Q'],d['R'],d['C'],d['E'],d['raw_payload_bytes'],d['packet_bound_bytes'],d['canonical_report_bytes'],d['output_reserved_bytes'],d['peak_declared_memory_bytes'])==(5,69,93,224,106819,728,12244,245260,595116)
 fields=list(meta['limits']);assert len(fields)==12
 cap_records=[]
 for case in vs[1:13]:
  changed=[key for key in fields if case['metadata']['limits'][key]!=meta['limits'][key]];assert len(changed)==1
  key=changed[0];target=copy.deepcopy(meta);target['limits'][key]-=1;assert case['metadata']==target
  assert case['expected']['derived']==d and case['expected']['unknowns']==[]
  assert case['expected']['status']=='EXCEEDS_DECLARED_BOUNDS' and len(case['expected']['violations'])==1
  v=case['expected']['violations'][0];assert v['code']==key.upper() and v['required']==meta['limits'][key] and v['limit']==meta['limits'][key]-1
  ordinal={'max_software_file_bytes':1,'max_metadata_file_bytes':2,'max_bulk_file_bytes':3}.get(key)
  assert v['file_id']==ordinal
  cap_records.append(dict(limit=key,equality=meta['limits'][key],one_over_limit=v['limit'],violation=v))
 assert {row['limit'] for row in cap_records}==set(fields)
 aggregate=vs[15]['expected'];assert aggregate['status']=='INDETERMINATE' and aggregate['unknowns']==['early_ids','files','modules']
 assert aggregate['derived']['aggregate_R_range']==[137611,141215] and aggregate['derived']['aggregate_C_range']==[138889,142493]
 assert aggregate['derived']['work_buffer_bytes']==73738 and aggregate['derived']['N'] is None and aggregate['violations']==[]
 assert vs[16]['expected']['unknowns']==['representation.report_call_bytes'] and vs[17]['expected']['unknowns']==['limits.max_calls']
 near=vs[21];assert near['metadata']['aggregate']['bytes']==2**63-1 and near['expected']['status']=='EXCEEDS_DECLARED_BOUNDS'
 assert near['expected']['unknowns']==['representation.call_record_bytes']
 assert [v['code'] for v in near['expected']['violations']]==['MAX_BULK_FILE_BYTES','MAX_CALLS','MAX_OUTPUT_BYTES','MAX_PACKET_BYTES','MAX_REPORT_BYTES']
 over=vs[20];assert over['metadata']['representation']['call_record_bytes']==2**31-1
 assert near['expected']['derived']['C']*(2**31-1)>2**63-1
 invalid={18:'SCHEMA_KEYS',19:'INTEGER_DOMAIN',20:'ARITHMETIC_OVERFLOW',22:'INTEGER_DOMAIN',23:'DUPLICATE_PATH',24:'ROLE',25:'FILE_IDS',26:'MODULE_GRAPH',27:'MODULE_GRAPH',28:'MODULE_BINDING',29:'AGGREGATE_MISMATCH'}
 constants={'chunk_bytes':65536,'query_frame_bytes_per_file':8218,'event_row_bytes':1024,'packet_kind_count':5,'current_runtime_packet_cap':8192}
 for index,code in invalid.items():
  e=vs[index]['expected'];assert e['status']=='REFUSED_INVALID_METADATA' and e['unknowns']==[]
  assert e['violations']==[dict(code=code,file_id=None,required=None,limit=None)]
  assert all(e['derived'][k]==v for k,v in constants.items())
  assert all(v is None for k,v in e['derived'].items() if k not in constants)
 for case in vs:assert all(value is False for value in case['expected']['qualification'].values())
 test_tree=ast.parse(raw['admission_envelope_independent_tests_v1.py'])
 imports=[ast.unparse(n) for n in test_tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
 assert imports==['import copy','import json','import unittest']
 tests=[n.name for n in ast.walk(test_tree) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')];assert len(tests)==4
 proof=json.loads(raw['ADMISSION-ENVELOPE-PRECODE-STRUCTURAL-PROOF-v1.json']);assert proof['status']=='passed' and proof['methods']==7 and proof['failures']==proof['errors']==[]
 report=dict(schema_version=1,status='CLEAR_CALCULATOR_DESIGN_AND_LITERAL_PREPARATION_ONLY',material_blockers=[],reviewer='native_039_acceptance_audit',
  effective_design=[proposal,clarification],inputs=pins,
  scope='Metadata-only finite design/oracle peer. No admission solver, subject import or test execution by reviewer.',
  arithmetic_records=arithmetic,independent_limit_contract=cap_records,actual_literal_vectors=30,
  semantic_review=[
   'Strict identity uses the declared ID permutation for module/early bindings and canonical list ordinals for sizing and violations; no file authenticity is inferred.',
   'All three roles are represented. Hash-only bulk contributes reads/call retention but no captured assembly; it is excluded from importable module binding.',
   'The equality case independently binds all12 declared limits, and each one-over clone changes exactly one limit. No combined failure substitutes for isolated enforcement.',
   'Zero versus exact-chunk/plus-one sizes, unknown representation and unknown limit, aggregate-only informational ranges, known exceeds with an unrelated unknown, and checked product overflow have distinct literal projections.',
   'Invalid schema/integer/path/role/ID/graph/binding/aggregate cases were read against the fixed contract and retained error mapping. Overflow preserves only five constants, with no unsafe echoed value or inferred zero.',
   'Logical storage includes captured assembly and immutable bytes separately, query frames and work buffers, full call/index/hash-state terms, journal retention/join workspace, all five packet capacities and declared report copies. These remain conditional declarations, not layout/RSS/time proof.'
  ],
  planned_test_review=dict(methods=tests,import_dependencies=imports,subject_runs=0,
   controls='Future tests grade exact types/JSON for all30 vectors; second-callback input mutation; detached nested output/range and retained byte identity; six representative cancellation classes at first/middle/final actual check sites; and required callable interface. No source is imported by the test module.'),
  coverage_limits=[
   'Thirty vectors are exact, not exhaustive strict-domain/path/graph coverage. In particular bool representation/limit cases were traded for independent overflow and precedence branches; all-field strictness remains a source-review obligation.',
   'Six cancellation families are representative rather than every BaseException class. Future code review must keep every check outside metadata-error catches and the final check after report/byte preparation.',
   'The calculator JSON bytes are not the prospective runtime report V. No packet transport/layout, original roster, streaming, runtime cap, native/FFI/source/resource/scientific fit or authority is proved.',
   'The baseline metadata envelope has C93/R69, outside the current runtime C92/R68; WITHIN_DECLARED_BOUNDS_ONLY intentionally does not admit that runtime plan.',
   'Source-only implementation requires a separate root decision, passing actual30+API controls and an independent exact source peer. Current indexed runtime and all prior failed/timeout evidence remain unchanged.'
  ],reviewed_artifact_edits=0,reviewer_subject_imports=0,reviewer_subject_tests=0,actual_API_calls=0,original_payload_operations=0,
  implementation_authorized=False,production_owner_bound=False,runtime_authorized=False,profile_qualified=False,verification_complete=False)
 dest=ROOT/'ADMISSION-ENVELOPE-INDEPENDENT-PREPARATION-PEER-v1.json'
 with dest.open('x',encoding='utf-8',newline='\n') as stream:json.dump(report,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
 note='''# Admission-envelope preparation peer

**CLEAR_CALCULATOR_DESIGN_AND_LITERAL_PREPARATION_ONLY.** No scoped blocker in effective proposal `038611da…` plus clarification `57ff21a8…`, the30 literal vectors `cb4c6dd4…`, test source `e670199a…` and freeze `5478b014…`.

Independent fixed-case arithmetic confirms the mixed-role baseline: Q5/R69/C93/E224; raw106819; closure281/digest404/packet728; report12244/output245260/peak595116. All12 limits are equal at that baseline, and each isolated one-over vector changes only its own limit and expects exactly its violation. Fixed arithmetic also matches zero/exact-chunk, unknown coefficients, and near-maximum safe-ceiling cases. Explicit overflow and known-exceeds-with-unknown projections are distinct. Invalid cases retain only the five constants and one safe error code.

The future four-method suite checks exact result types and canonical bytes, detached caller/output state, retained byte identity, representative check-exception identities and required callable input. The reviewer read this source but did not import or run it or any subject. Seven structural data-only methods are retained; they are not calculator success.

Coverage remains finite. Not every bool/path/graph failure or BaseException subclass is isolated, so later source review must enforce the complete contract. Declared coefficients and report V are conditional logical assumptions, not actual runtime JSON transport, physical memory or time fit. The baseline itself exceeds the unchanged runtime R68/C92 and grants no runtime admission. No original, streaming, FFI/native, source/checker/resource or scientific gate is closed.

Exact pins, fixed arithmetic and the independent12-bound acceptance contract are in the [peer JSON](ADMISSION-ENVELOPE-INDEPENDENT-PREPARATION-PEER-v1.json). Implementation and later source acceptance require root's separate decision.
'''
 md=ROOT/'ADMISSION-ENVELOPE-INDEPENDENT-PREPARATION-PEER-v1.md'
 with md.open('x',encoding='utf-8',newline='\n') as stream:stream.write(note)
 for path in (dest,md):
  b=path.read_bytes();print(json.dumps(dict(path=str(path),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())))


if __name__=='__main__':main()
