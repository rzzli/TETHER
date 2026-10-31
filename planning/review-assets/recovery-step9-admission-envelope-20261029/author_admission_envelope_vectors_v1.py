"""Author fixed synthetic metadata/literal expectations, never a calculator.

Expected numeric tables below are independently authored constants. The only
encoding check constructs the declared four-entry packet arrays in memory.
No candidate subject is imported, created, or executed.
"""
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
PREFLIGHT=HERE.parent/'recovery-step9-production-preflight-20261029'
MAX=2**63-1
DERIVED=('chunk_bytes','query_frame_bytes_per_file','event_row_bytes','packet_kind_count','current_runtime_packet_cap','N','total_bytes','positive_files','B','M','Q','R','C','E','captured_bytes','hash_only_bytes','query_witness_bytes','work_buffer_bytes','raw_payload_bytes','immutable_capture_bytes','logical_call_bytes','index_bytes','hash_state_bytes','journal_bytes','canonical_report_bytes','closure_array_bound_bytes','digest_array_bytes','packet_bound_bytes','output_reserved_bytes','peak_declared_memory_bytes','aggregate_R_range','aggregate_C_range')
CONSTANTS=dict(chunk_bytes=65536,query_frame_bytes_per_file=8218,event_row_bytes=1024,packet_kind_count=5,current_runtime_packet_cap=8192)
QUALIFICATION=dict(FFI_registration_proven=False,originals_authenticated=False,production_owner_bound=False,profile_qualified=False,real_checkers_bound=False,runtime_authorized=False,verification_complete=False)
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('utf-8')
def publish(name,value):
 path=HERE/name
 with path.open('xb') as out:out.write(canonical(value))
 return pin(path)
def report(derived,status='WITHIN_DECLARED_BOUNDS_ONLY',unknowns=(),violations=()):
 return dict(schema_version=1,status=status,derived=copy.deepcopy(derived),unknowns=list(unknowns),violations=list(violations),qualification=dict(QUALIFICATION))
def invalid(code):
 return report(dict({key:None for key in DERIVED},**CONSTANTS),'REFUSED_INVALID_METADATA',violations=[dict(code=code,file_id=None,required=None,limit=None)])

def author_vectors():
 files=[
  dict(id=2,path='D:\\FictionalAdmission\\leaf.py',role='captured_software',size=58,sha256='1'*64),
  dict(id=0,path='D:\\FictionalAdmission\\entry.py',role='captured_software',size=83,sha256='2'*64),
  dict(id=3,path='C:\\FictionalAdmission\\metadata.json',role='captured_metadata',size=68,sha256='3'*64),
  dict(id=1,path='D:\\FictionalAdmission\\bulk.bin',role='hash_only_bulk',size=65537,sha256='4'*64),
 ]
 limits=dict(max_files=4,max_software_file_bytes=83,max_metadata_file_bytes=68,max_bulk_file_bytes=65537,max_captured_bytes=209,max_raw_payload_bytes=106819,max_calls=93,max_events=224,max_packet_bytes=728,max_output_bytes=245260,max_report_bytes=12244,max_declared_memory_bytes=595116)
 representation=dict(call_record_bytes=11,file_index_bytes=13,module_index_bytes=17,hash_state_bytes=19,transient_bytes=23,report_base_bytes=29,report_call_bytes=31,report_file_bytes=37,report_event_bytes=41,report_copies=2,packet_overhead_bytes=43)
 baseline=dict(schema_version=1,files=files,early_ids=[2,0],modules=[dict(name='toy_leaf',file_id=2,dependencies=[],package=False),dict(name='toy_entry',file_id=0,dependencies=['toy_leaf'],package=False)],aggregate=dict(files=4,bytes=65746),limits=limits,representation=representation)
 derived=dict(CONSTANTS,N=4,total_bytes=65746,positive_files=4,B=2,M=2,Q=5,R=69,C=93,E=224,captured_bytes=209,hash_only_bytes=65537,query_witness_bytes=32872,work_buffer_bytes=73738,raw_payload_bytes=106819,immutable_capture_bytes=209,logical_call_bytes=1023,index_bytes=86,hash_state_bytes=76,journal_bytes=229376,canonical_report_bytes=12244,closure_array_bound_bytes=281,digest_array_bytes=404,packet_bound_bytes=728,output_reserved_bytes=245260,peak_declared_memory_bytes=595116,aggregate_R_range=None,aggregate_C_range=None)
 cases=[]
 def add(name,metadata,expected,basis):
  cases.append(dict(ordinal=len(cases),id=name,metadata=copy.deepcopy(metadata),expected=copy.deepcopy(expected),basis=basis))
 add('mixed_role_all_bounds_equal',baseline,report(derived),'All12 declared limits at exact required quantities; metadata IDs permuted, packet IDs ordinal; fictional coefficients only.')
 for key,code,file_id,required in (
  ('max_files','MAX_FILES',None,4),('max_software_file_bytes','MAX_SOFTWARE_FILE_BYTES',1,83),('max_metadata_file_bytes','MAX_METADATA_FILE_BYTES',2,68),('max_bulk_file_bytes','MAX_BULK_FILE_BYTES',3,65537),('max_captured_bytes','MAX_CAPTURED_BYTES',None,209),('max_raw_payload_bytes','MAX_RAW_PAYLOAD_BYTES',None,106819),('max_calls','MAX_CALLS',None,93),('max_events','MAX_EVENTS',None,224),('max_packet_bytes','MAX_PACKET_BYTES',None,728),('max_output_bytes','MAX_OUTPUT_BYTES',None,245260),('max_report_bytes','MAX_REPORT_BYTES',None,12244),('max_declared_memory_bytes','MAX_DECLARED_MEMORY_BYTES',None,595116),
 ):
  value=copy.deepcopy(baseline);value['limits'][key]=required-1
  add('isolated_'+key+'_one_over',value,report(derived,'EXCEEDS_DECLARED_BOUNDS',violations=[dict(code=code,file_id=file_id,required=required,limit=required-1)]),'Only this limit differs from exact-equality baseline; all other inputs and computed terms identical.')
 value=copy.deepcopy(baseline);value['files'][3]['size']=65536;value['aggregate']['bytes']=65745
 d=dict(derived,total_bytes=65745,Q=4,R=68,C=92,hash_only_bytes=65536,logical_call_bytes=1012,canonical_report_bytes=12213,output_reserved_bytes=245229,peak_declared_memory_bytes=595043)
 add('bulk_exact_chunk_boundary',value,report(d),'One fewer hash-only read chunk than65537; no captured-storage change.')
 value=copy.deepcopy(baseline);value['files'][3]['size']=0;value['aggregate']['bytes']=209
 d=dict(derived,total_bytes=209,positive_files=3,Q=3,R=51,C=75,hash_only_bytes=0,logical_call_bytes=825,canonical_report_bytes=11686,digest_array_bytes=400,packet_bound_bytes=724,output_reserved_bytes=244682,peak_declared_memory_bytes=593782)
 add('bulk_zero_no_read_reservation',value,report(d),'Zero-byte bulk adds no positive-file padding/read; all4 files still retain identity/closure/digest entries.')
 value=copy.deepcopy(baseline);value.update(files=None,early_ids=None,modules=None,aggregate=dict(files=213,bytes=9017363392))
 d=dict({key:None for key in DERIVED},**CONSTANTS,work_buffer_bytes=73738,aggregate_R_range=[137611,141215],aggregate_C_range=[138889,142493])
 add('aggregate_only_unknown',value,report(d,'INDETERMINATE',unknowns=['early_ids','files','modules']),'Aggregate outer ranges only; exact per-file quantities remain unknown and do not inherit aggregate hints or capacity values.')
 value=copy.deepcopy(baseline);value['representation']['report_call_bytes']=None
 d=dict(derived,canonical_report_bytes=None,output_reserved_bytes=None,peak_declared_memory_bytes=None)
 add('null_representation_stays_unknown',value,report(d,'INDETERMINATE',unknowns=['representation.report_call_bytes']),'One unknown coefficient is never a zero-cost structure.')
 value=copy.deepcopy(baseline);value['limits']['max_calls']=None
 add('null_limit_stays_unknown',value,report(derived,'INDETERMINATE',unknowns=['limits.max_calls']),'Quantities stay known while one declared comparison remains unknown.')
 value=copy.deepcopy(baseline);value['ready']=True
 add('extra_top_key_refused',value,invalid('SCHEMA_KEYS'),'Closed input shape; producer-ready flags are not authority.')
 value=copy.deepcopy(baseline);value['files'][3]['size']=True
 add('bool_size_refused',value,invalid('INTEGER_DOMAIN'),'True cannot become size1 or an aggregate-mismatch surrogate.')
 value=copy.deepcopy(baseline);value['files'][3]['size']=9223372036854775598;value['aggregate']['bytes']=MAX;value['representation']['call_record_bytes']=2147483647
 add('checked_product_overflow_refused',value,invalid('ARITHMETIC_OVERFLOW'),'All individual fields are valid; checked logical-call product exceeds2^63-1. No float/wrap/clamp/derived allocation.')
 value=copy.deepcopy(baseline);value['files'][3]['size']=9223372036854775598;value['aggregate']['bytes']=MAX;value['representation']['call_record_bytes']=None
 d=dict(derived,total_bytes=MAX,Q=140737488355331,R=140737488355395,C=140737488355419,hash_only_bytes=9223372036854775598,logical_call_bytes=None,canonical_report_bytes=4362862139027350,digest_array_bytes=418,packet_bound_bytes=742,output_reserved_bytes=4362862139260436,peak_declared_memory_bytes=None)
 violations=[dict(code='MAX_BULK_FILE_BYTES',file_id=3,required=9223372036854775598,limit=65537),dict(code='MAX_CALLS',file_id=None,required=140737488355419,limit=93),dict(code='MAX_OUTPUT_BYTES',file_id=None,required=4362862139260436,limit=245260),dict(code='MAX_PACKET_BYTES',file_id=None,required=742,limit=728),dict(code='MAX_REPORT_BYTES',file_id=None,required=4362862139027350,limit=12244)]
 add('near_max_ceiling_known_exceeds_with_unknown',value,report(d,'EXCEEDS_DECLARED_BOUNDS',unknowns=['representation.call_record_bytes'],violations=violations),'Valid exact total2^63-1 and divmod-equivalent ceiling; known exceedances outrank unrelated unknown. Premature size+65535 overflow refusal is wrong.')
 value=copy.deepcopy(baseline);value['files'][3]['id']=True
 add('bool_file_id_refused',value,invalid('INTEGER_DOMAIN'),'A boolean must not impersonate metadata ID1.')
 value=copy.deepcopy(baseline);value['files'][1]['path']='d:/fictionaladmission/LEAF.py'
 add('canonical_path_collision_refused',value,invalid('DUPLICATE_PATH'),'Both paths individually canonicalizable; ASCII-fold/slash identity collision is refused without filesystem operations.')
 value=copy.deepcopy(baseline);value['files'][3]['role']='bulk'
 add('unknown_role_refused',value,invalid('ROLE'),'No role inference from extension, size or favorable memory outcome.')
 value=copy.deepcopy(baseline);value['files'][3]['id']=2
 add('duplicate_file_id_refused',value,invalid('FILE_IDS'),'Numeric validation passes, but ID set is not the required unique permutation.')
 value=copy.deepcopy(baseline);value['modules'][1]['dependencies']=['not_declared']
 add('nonclosed_module_graph_refused',value,invalid('MODULE_GRAPH'),'Closed synthetic import graph required; no ordinary import/source fallback.')
 value=copy.deepcopy(baseline);value['modules'][0]['dependencies']=['toy_entry']
 add('cyclic_module_graph_refused',value,invalid('MODULE_GRAPH'),'Closed graph still refuses a cycle.')
 value=copy.deepcopy(baseline);value['modules'][1]['file_id']=1
 add('hash_only_module_source_refused',value,invalid('MODULE_BINDING'),'Hash-only bulk cannot supply a software module or captured-byte consumer.')
 value=copy.deepcopy(baseline);value['aggregate']['bytes']=65747
 add('aggregate_vector_mismatch_refused',value,invalid('AGGREGATE_MISMATCH'),'A supplied nonnull hint must match the exact declared vector.')
 assert len(cases)==30 and len({v['id'] for v in cases})==30
 # Fixed framing cross-check only, not evaluation of the admission formulas.
 closures=[dict(file_id=i,invoked=False,return_observed=False,success=False) for i in range(4)]
 digests=[dict(file_id=i,size=f['size'],sha256=f['sha256']) for i,f in enumerate(files)]
 assert len(canonical(closures))-1==281 and len(canonical(digests))-1==404
 return cases

def main():
 output=None
 try:
  proposal=PREFLIGHT/'ADMISSION-ENVELOPE-CALCULATOR-PROPOSAL-v1.json'
  assert pin(proposal)['sha256']=='038611daa69c5749def12d64dedc0b9afebdbfba2aff7d0e93981551e08d2cb8'
  clarification=PREFLIGHT/'ADMISSION-ENVELOPE-FINITE-CLARIFICATIONS-v2.json'
  assert pin(clarification)['sha256']=='57ff21a8955de95f61fa059543e33c1ace52726efbc36b286a52310af5addf97'
  cases=author_vectors()
  output=dict(schema_version=1,scope='FROZEN-SYNTHETIC-METADATA-ONLY-NOT-SOURCE-OR-RUNTIME-AUTHORITY',source_proposal=pin(proposal),clarification=pin(clarification),author=pin(Path(__file__).resolve()),recorded_at_utc=datetime.now(timezone.utc).isoformat(),actual_vector_count=30,reason_for_count='Root explicitly replaced the <=18 preference with <=30 actual vectors to isolate all12 limits. One equality baseline,12 independent cap-1 clones,17 strict/unknown/graph/rounding/status vectors. No compound substitute for independent limits.',vectors=cases,semantics=['Paths/IDs/digests are invented metadata labels, not authenticated files; no label is opened.','Representation coefficients are distinct fictional logical payload declarations, not measured layouts/RSS or a valid production representation.','WITHIN_DECLARED_BOUNDS_ONLY is arithmetic metadata classification; current V3 caps/runtime remain unchanged.','Every expected table is authored before the subject exists; no admission implementation/reference solver evaluates these cases.','The generic test module sends only metadata and a cancellation check, never vector IDs/expected fields/fault labels.'],coverage_limits=['Boolean rejection is isolated for size and ID, not every numeric field; static source review must still enforce exact nonbool integers everywhere.','No runtime stream, actual read/hash/copy/sink/output/Win32/source qualification is tested.','Exact-vector aggregate hint nulls, every malformed field and every package/path alias are source-review obligations beyond these finite vectors.'],subject_source_present=(HERE/'admission_envelope_v1.py').exists(),subject_imports=0,subject_tests=0,actual_target_API_calls=0,original_payload_operations=0,implementation_authorized=False)
  assert output['subject_source_present'] is False
  result=publish('ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json',output)
  print(json.dumps(dict(vectors=result,count=30,subject_runs=0)))
 except BaseException as error:
  failure=dict(status='AUTHORING_FAILURE_PRESERVED',error_class=type(error).__name__,message=str(error)[:2048],author=pin(Path(__file__).resolve()),subject_runs=0,actual_target_API_calls=0)
  publish('ADMISSION-ENVELOPE-VECTOR-AUTHORING-FAILURE-v1.json',failure)
  raise
if __name__=='__main__':main()
