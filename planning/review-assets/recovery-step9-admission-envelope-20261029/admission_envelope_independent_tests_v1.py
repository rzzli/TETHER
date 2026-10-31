"""Pre-code independent calculator tests. No calculator import or IO here.

The test harness supplies a freshly pinned subject and frozen literal data.
Only metadata and a zero-argument cancellation check reach the subject.
"""
import copy
import json
import unittest

MAX=2**63-1
TOP=('schema_version','status','derived','unknowns','violations','qualification')
DERIVED=('chunk_bytes','query_frame_bytes_per_file','event_row_bytes','packet_kind_count','current_runtime_packet_cap','N','total_bytes','positive_files','B','M','Q','R','C','E','captured_bytes','hash_only_bytes','query_witness_bytes','work_buffer_bytes','raw_payload_bytes','immutable_capture_bytes','logical_call_bytes','index_bytes','hash_state_bytes','journal_bytes','canonical_report_bytes','closure_array_bound_bytes','digest_array_bytes','packet_bound_bytes','output_reserved_bytes','peak_declared_memory_bytes','aggregate_R_range','aggregate_C_range')
CONSTANTS=dict(chunk_bytes=65536,query_frame_bytes_per_file=8218,event_row_bytes=1024,packet_kind_count=5,current_runtime_packet_cap=8192)
QUALIFICATION=dict(FFI_registration_proven=False,originals_authenticated=False,production_owner_bound=False,profile_qualified=False,real_checkers_bound=False,runtime_authorized=False,verification_complete=False)
CAPS=('MAX_FILES','MAX_SOFTWARE_FILE_BYTES','MAX_METADATA_FILE_BYTES','MAX_BULK_FILE_BYTES','MAX_CAPTURED_BYTES','MAX_RAW_PAYLOAD_BYTES','MAX_CALLS','MAX_EVENTS','MAX_PACKET_BYTES','MAX_OUTPUT_BYTES','MAX_REPORT_BYTES','MAX_DECLARED_MEMORY_BYTES')
INVALID=('SCHEMA_KEYS','TYPE_DOMAIN','INTEGER_DOMAIN','ROLE','PATH_IDENTITY','DUPLICATE_PATH','FILE_IDS','DIGEST_FORMAT','MODULE_GRAPH','MODULE_BINDING','AGGREGATE_MISMATCH','ARITHMETIC_OVERFLOW')
STATUSES=('REFUSED_INVALID_METADATA','EXCEEDS_DECLARED_BOUNDS','INDETERMINATE','WITHIN_DECLARED_BOUNDS_ONLY')
LIMITS=('max_files','max_software_file_bytes','max_metadata_file_bytes','max_bulk_file_bytes','max_captured_bytes','max_raw_payload_bytes','max_calls','max_events','max_packet_bytes','max_output_bytes','max_report_bytes','max_declared_memory_bytes')
REPRESENTATION=('call_record_bytes','file_index_bytes','module_index_bytes','hash_state_bytes','transient_bytes','report_base_bytes','report_call_bytes','report_file_bytes','report_event_bytes','report_copies','packet_overhead_bytes')
UNKNOWN=set(('files','early_ids','modules','aggregate.files','aggregate.bytes'))|{'limits.'+key for key in LIMITS}|{'representation.'+key for key in REPRESENTATION}

def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)+'\n').encode('utf-8')
def require(ok,message):
 if not ok:raise AssertionError(message)
def equal_typed(actual,expected,path='$'):
 require(type(actual) is type(expected),path+' exact type')
 if type(expected) is dict:
  require(set(actual)==set(expected),path+' exact keys')
  for key in expected:equal_typed(actual[key],expected[key],path+'.'+key)
 elif type(expected) is list:
  require(len(actual)==len(expected),path+' length')
  for index,value in enumerate(expected):equal_typed(actual[index],value,path+'['+str(index)+']')
 else:require(actual==expected,path+' literal value')
def validate_report(value):
 require(type(value) is dict and set(value)==set(TOP),'report exact keys')
 require(type(value['schema_version']) is int and value['schema_version']==1,'version')
 require(type(value['status']) is str and value['status'] in STATUSES,'status')
 d=value['derived'];require(type(d) is dict and set(d)==set(DERIVED),'derived exact keys')
 for key,expected in CONSTANTS.items():require(type(d[key]) is int and d[key]==expected,'constant '+key)
 for key in DERIVED[5:]:
  x=d[key]
  if key in ('aggregate_R_range','aggregate_C_range'):
   require(x is None or type(x) is list and len(x)==2 and all(type(n) is int and 0<=n<=MAX for n in x) and x[0]<=x[1],'range '+key)
  else:require(x is None or type(x) is int and 0<=x<=MAX,'integer '+key)
 unknown=value['unknowns'];require(type(unknown) is list and all(type(x) is str and x in UNKNOWN for x in unknown),'unknown domain')
 require(unknown==sorted(set(unknown)),'unknown sorting')
 violations=value['violations'];require(type(violations) is list,'violations list')
 for item in violations:
  require(type(item) is dict and set(item)=={'code','file_id','required','limit'},'violation keys')
  require(type(item['code']) is str and item['code'] in (*CAPS,*INVALID),'code')
  require(item['file_id'] is None or type(item['file_id']) is int and 0<=item['file_id']<256,'file ordinal')
  for key in ('required','limit'):require(item[key] is None or type(item[key]) is int and 0<=item[key]<=MAX,'violation numeric')
 require(violations==sorted(violations,key=lambda v:(v['code'],-1 if v['file_id'] is None else v['file_id'])),'violation order')
 require(len({(v['code'],v['file_id']) for v in violations})==len(violations),'duplicate violation')
 equal_typed(value['qualification'],QUALIFICATION,'qualification')
 if value['status']=='REFUSED_INVALID_METADATA':
  require(len(violations)==1 and violations[0]['code'] in INVALID and all(violations[0][k] is None for k in ('file_id','required','limit')),'invalid refusal')
  require(not unknown and all(d[k] is None for k in DERIVED[5:]),'invalid safe projection')
 elif value['status']=='EXCEEDS_DECLARED_BOUNDS':require(bool(violations) and all(v['code'] in CAPS for v in violations),'exceeds')
 elif value['status']=='INDETERMINATE':require(bool(unknown) and not violations,'indeterminate')
 else:require(not unknown and not violations,'within')
 return value

def make_tests(subject,fixtures,invoke,observations):
 cases=fixtures['vectors'];baseline=next(v for v in cases if v['id']=='mixed_role_all_bounds_equal')
 aggregate=next(v for v in cases if v['id']=='aggregate_only_unknown')
 def analyze(metadata,check):return invoke(subject.analyze_admission,metadata,check=check)
 def get(report,expected):
  require(type(report) is subject.EnvelopeReport,'source result class')
  actual=invoke(report.to_dict);validate_report(actual);equal_typed(actual,expected)
  raw=invoke(report.to_json_bytes);require(type(raw) is bytes,'immutable bytes')
  require(raw==canonical(expected),'exact canonical bytes')
  require(invoke(report.to_json_bytes) is raw,'retained bytes identity')
  return actual,raw
 class Tests(unittest.TestCase):
  def test_01_all_30_frozen_metadata_vectors(self):
   self.assertEqual(len(cases),30)
   for vector in cases:
    with self.subTest(vector=vector['id']):
     metadata=copy.deepcopy(vector['metadata']);before=copy.deepcopy(metadata);count=[0]
     def check():count[0]+=1;return False # Ignored cancellation return, not authority.
     report=analyze(metadata,check);actual,raw=get(report,vector['expected'])
     equal_typed(metadata,before)
     observations.append(dict(vector=vector['id'],matched=True,status=actual['status'],check_calls=count[0],calculator_json_bytes=len(raw)))
  def test_02_detached_input_and_output(self):
   metadata=copy.deepcopy(baseline['metadata']);calls=[0]
   def mutate_after_snapshot():
    calls[0]+=1
    if calls[0]==2:
     metadata['files'][0]['size']=0;metadata['modules'][1]['dependencies'].append('not_declared');metadata['limits'].clear()
    return None
   report=analyze(metadata,mutate_after_snapshot)
   self.assertGreaterEqual(calls[0],2,'post-snapshot check must be exercised')
   actual,raw=get(report,baseline['expected']);at_return=calls[0]
   actual['derived']['N']=999;actual['qualification']['runtime_authorized']=True;actual['unknowns'].append('files');actual['violations'].append(dict(code='MAX_FILES',file_id=None,required=999,limit=0))
   get(report,baseline['expected']);self.assertEqual(calls[0],at_return,'cache-only report getters')
   with self.assertRaises((AttributeError,TypeError)):setattr(report,'caller_added_mutable_field',[])
   unknown_report=analyze(copy.deepcopy(aggregate['metadata']),lambda:None)
   unknown,encoded=get(unknown_report,aggregate['expected']);unknown['derived']['aggregate_R_range'][0]=0
   get(unknown_report,aggregate['expected'])
   observations.append(dict(control='input_and_nested_output_detachment',matched=True,check_calls=calls[0],retained_bytes=True))
  def test_03_original_check_exception_identity(self):
   count=[0]
   def count_check():count[0]+=1
   get(analyze(copy.deepcopy(baseline['metadata']),count_check),baseline['expected'])
   self.assertGreaterEqual(count[0],2)
   positions=sorted({1,(count[0]+1)//2,count[0]})
   families=(ValueError,TypeError,UnicodeError,MemoryError,KeyboardInterrupt,SystemExit)
   for family in families:
    for position in positions:
     with self.subTest(family=family.__name__,position=position):
      original=family('synthetic calculator cancellation');seen=[0]
      def check():
       seen[0]+=1
       if seen[0]==position:raise original
      try:analyze(copy.deepcopy(baseline['metadata']),check)
      except BaseException as actual:self.assertIs(actual,original)
      else:self.fail('calculator swallowed original cancellation')
      self.assertEqual(seen[0],position,'work continued after check interruption')
      observations.append(dict(control='check_identity',family=family.__name__,position=position,matched=True))
  def test_04_required_check_interface(self):
   for value in (None,False,1):
    with self.subTest(type=type(value).__name__):
     with self.assertRaises(TypeError):analyze(copy.deepcopy(baseline['metadata']),value)
   observations.append(dict(control='required_callable_interface',matched=True))
 return Tests
