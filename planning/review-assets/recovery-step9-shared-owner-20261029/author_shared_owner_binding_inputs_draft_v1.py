"""Invented seven-API binding input bytes only; no dispatch or component use."""
import hashlib
import json
from pathlib import Path
import struct

HERE=Path(__file__).resolve().parent
raw=(HERE/'SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='eb5147d200bcc0108b71968d69f6b251c29b56dd52d926a8606504682134d9b8'
cohort=json.loads(raw)
frames={'attributes_normal':struct.pack('<II',128,0).hex()}
calls=[]
for index,blob in enumerate(cohort['blobs']):
 identity=blob['id'];handle=101+index
 path_utf16=blob['path'].encode('utf-16-le')
 frames[identity+'_final_path']=(path_utf16+b'\0'*(8202-len(path_utf16))).hex()
 frames[identity+'_size']=struct.pack('<q',blob['bytes']).hex()
 frames[identity+'_read']=blob['utf8_hex']
 rows=[
  ('CreateFileW',dict(path=blob['path'],desired_access=2147483648,share_mode=1,security=None,creation=3,flags=2097280,template=None),None,handle,None),
  ('GetFileType',dict(handle=handle),None,1,None),
  ('GetFileInformationByHandleEx',dict(handle=handle,info_class=9,buffer_bytes=8),'attributes_normal',1,None),
  ('GetFinalPathNameByHandleW',dict(handle=handle,capacity=4101,flags=0),identity+'_final_path',len(path_utf16)//2,None),
  ('GetFileSizeEx',dict(handle=handle),identity+'_size',1,None),
  ('ReadFile',dict(handle=handle,requested=blob['bytes'],overlapped=None),identity+'_read',1,blob['bytes']),
 ]
 for api,args,frame,scalar,count in rows:
  actions=[]
  if frame is not None:actions.append(dict(hook='buffer_write',frame_id=frame))
  actions.append(dict(hook='store_scalar',value=scalar))
  if count is not None:actions.append(dict(hook='store_count',value=count))
  calls.append(dict(ordinal=len(calls),api=api,file_id=identity,arguments=args,actions=actions,binding_return='normal_None'))
for index in (2,1,0):
 calls.append(dict(ordinal=len(calls),api='CloseHandle',file_id=cohort['blobs'][index]['id'],arguments=dict(handle=101+index),actions=[dict(hook='store_scalar',value=1)],binding_return='normal_None'))
assert len(calls)==21 and all(sum(c['api']==api for c in calls)==3 for api in {c['api'] for c in calls})
value=dict(schema_version=1,status='UNFROZEN_LITERAL_BINDING_INPUT_DRAFT_NOT_DISPATCH_HISTORY',cohort_sha256=hashlib.sha256(raw).hexdigest(),scope='All frames/scalars/handles are invented seven-API fake inputs. Query paths are the fictitious cohort labels; no embedded file/handle exists. Buffer references and generation must be source-issued and supplied by the future generic fixture driver; frame labels never enter under-test logic.',frames_hex=frames,baseline_binding_script=calls,expected_successful_actual_original_calls=21,expected_per_API_attempts=3,capacity_distinction=dict(N=3,B=2,M=2,R=51,C=69,E=218),buffer_resolution='Each buffer_write uses the current exact reserved CallRef buffer+generation, resolved by the harness through the agreed source-issued interface, never a caller-ready buffer dict. Exact public field names await the DATA schema.',reviewed_component_imports=False,source_helpers_executed=False,binding_dispatches=0,actual_API_calls=0,FFI_registration_proven=False,runtime_authorized=False)
path=HERE/'SHARED-OWNER-INTEGRATION-BINDING-INPUTS-DRAFT-v1.json'
with path.open('xb') as out:out.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8'))
result=path.read_bytes();print(json.dumps(dict(path=str(path),bytes=len(result),sha256=hashlib.sha256(result).hexdigest())))
