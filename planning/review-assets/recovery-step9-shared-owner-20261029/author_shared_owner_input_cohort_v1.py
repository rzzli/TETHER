"""Literal toy INPUT framing only. Never opens embedded fictitious paths."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE/'SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json'
assert not OUT.exists()

cohort=dict(
 schema_version=1,
 status='AUTHORED_LITERAL_SYNTHETIC_INPUTS_NOT_BEHAVIOR_QUALIFIED',
 scope='Three invented byte blobs only. Embedded canonical DOS paths are labels, not actual source locations or authority. No blob is persisted as a source/metadata file; only this fixture container is written.',
 path_namespace='D:\\FictionalSharedOwnerCohort',
 blobs=[
  dict(id='cohort_leaf',phase='early_source',path='D:\\FictionalSharedOwnerCohort\\cohort_leaf.py',role='software',capture=True,bytes=58,sha256='2afb0c0f5d06cbbeef48871bd0b344aeaa2a47ea61d719e9906fc1cf4862080e',encoding='utf-8',utf8_hex='4d41524b4552203d2022636f686f72742d6c6561662d7631220a646566206d61726b657228293a0a2020202072657475726e204d41524b45520a',content_kind='toy_python_helper'),
  dict(id='cohort_entry',phase='early_source',path='D:\\FictionalSharedOwnerCohort\\cohort_entry.py',role='software',capture=True,bytes=83,sha256='f622ba1a5d566410a4e66fabe2ec13b42cd5ad74a971b67d1c503aadd3aad73d',encoding='utf-8',utf8_hex='66726f6d20636f686f72745f6c65616620696d706f7274206d61726b65720a6465662072756e28293a0a2020202072657475726e202822636f686f72742d656e7472792d7631222c206d61726b65722829290a',content_kind='toy_python_helper'),
  dict(id='metadata',phase='remaining_captured_input',path='D:\\FictionalSharedOwnerCohort\\metadata.json',role='owner_metadata',capture=True,bytes=68,sha256='713469e98d9e6640dc8daa7cfa23d14457bd625c850ca370e04f585d199d5955',encoding='utf-8',utf8_hex='7b22736368656d61223a2273796e7468657469632d636f686f72742d7631222c226d61726b6572223a226d657461646174612d6f6e6c79222c2276616c7565223a377d0a',content_kind='toy_metadata_json'),
 ],
 closed_modules=[
  dict(fullname='cohort_leaf',blob_id='cohort_leaf',dependencies=[],package=False),
  dict(fullname='cohort_entry',blob_id='cohort_entry',dependencies=['cohort_leaf'],package=False),
 ],
 stdlib_dependencies=[],
 loader_binding_rule='The only source import is cohort_entry -> cohort_leaf, resolved by the future source-bound closed loader from these captured bytes. No ordinary import fallback, sys.modules lookup, filesystem source import or actual archive/resource/science checker is part of this cohort.',
 expected_toy_values=dict(leaf_marker='cohort-leaf-v1',entry_run_result_tuple=['cohort-entry-v1','cohort-leaf-v1'],metadata_object=dict(schema='synthetic-cohort-v1',marker='metadata-only',value=7)),
 successful_lifecycle_input_history=[
  dict(blob_id='cohort_leaf',original_acquisition_histories=1,whole_blob_hash_histories=1,capture_histories=1,continuation_reopens=0,continuation_rehashes=0,known_read_bytes=58,hashed_bytes=58,captured_bytes=58),
  dict(blob_id='cohort_entry',original_acquisition_histories=1,whole_blob_hash_histories=1,capture_histories=1,continuation_reopens=0,continuation_rehashes=0,known_read_bytes=83,hashed_bytes=83,captured_bytes=83),
  dict(blob_id='metadata',original_acquisition_histories=1,whole_blob_hash_histories=1,capture_histories=1,continuation_reopens=0,continuation_rehashes=0,known_read_bytes=68,hashed_bytes=68,captured_bytes=68),
 ],
 totals=dict(early_sources=2,remaining_captured_inputs=1,total_blobs=3,early_bytes=141,remaining_bytes=68,total_bytes=209),
 history_scope='These are authored successful-lifecycle whole-input history expectations, not Win32/API/call/event counts or a claim that every failure completes them. Future fault fixtures must preserve observed/unknown partials. No unfrozen machine operation schedule is asserted.',
 future_fault_purpose='Inject one compile callback failure against unchanged valid helper bytes and assert no retry; the failure site/exception and concrete method schedule remain for the separately frozen integration fixtures. This file neither compiles the helpers nor implements a loader.',
 no_real_checker_implementation=True,
 fixture_behavior_qualified=False,
 original_sources_authenticated=False,
 FFI_registration_proven=False,
 production_owner_bound=False,
 profile_qualified=False,
 runtime_authorized=False,
 actual_API_calls=0,
)
# Basic author checks only; a separate checker recomputes exact literal pins.
assert len(cohort['blobs'])==3 and len({b['path'] for b in cohort['blobs']})==3
for blob in cohort['blobs']:
 raw=bytes.fromhex(blob['utf8_hex'])
 assert len(raw)==blob['bytes'] and hashlib.sha256(raw).hexdigest()==blob['sha256']
with OUT.open('xb') as out:out.write((json.dumps(cohort,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8'))
raw=OUT.read_bytes()
print(json.dumps(dict(path=str(OUT),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())))
