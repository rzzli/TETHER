"""Accept only the actually retained large synthetic source/pure result."""
import hashlib
import json
from pathlib import Path

H = Path(__file__).resolve().parent
def pin(name, digest):
    path = H / name
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, name
    return dict(path=str(path.resolve()), bytes=len(raw), sha256=digest)
proof = pin('ROLE-AWARE-LARGE-INJECTED-PROOF-v3.json','7cefbe0e5dc71f950a3537be9f30790d0c7501ca7c5c3446c3c331567a98cedf')
peer = pin('ROLE-AWARE-LARGE-INJECTED-INDEPENDENT-ACTUAL-PEER-v2.json','fa6b4375559d310587cd7ea53a0679bd1434182a78c8984e1723337ecbb0f2a5')
accounting = pin('ROLE-AWARE-LARGE-ACTUAL-ACCOUNTING-RESOURCE-REVIEW-v3.json','674cdf3471c133153882752a948b8515ce8518efee0472bb2834607cad1edd24')
d, p, a = [json.loads(Path(x['path']).read_bytes()) for x in (proof,peer,accounting)]
assert p['status']=='CLEAR_SOURCE_PURE_LARGE_GENERATED_RESULT_ONLY' and p['material_blockers']==[]
assert a['status']=='CLEAR_ACTUAL_ACCOUNTING_EVIDENCE_SOURCE_PURE_ONLY_RESOURCE_FIT_UNKNOWN'
assert d['status']=='PASS_SOURCE_PURE_LARGE_GENERATED_ONLY'
assert d['first_exception'] is None and d['evidence_publication_error'] is None
assert d['audit_denials']==[] and d['monitor_violations']==[]
assert all(v is True for v in d['source_and_harness_unchanged'].values())
assert all(v is False for v in d['qualification'].values())
assert d['actual_original_dispatches']==10095 and d['actual_read_dispatch_attempts']==8799
assert d['actual_close_attempts']==d['canonical_known_successful_close_returns']==216
assert d['helper_completed_read_deliveries']==8799 and d['helper_completed_delivery_bytes']==9017363601
t=d['first_actual_terminal']
assert t['issued'] and t['finalized'] and t['pure_seam_complete']
assert t['status']=='PURE_SEAM_COMPLETE_CONSISTENT' and all(v is True for v in t['terminal'].values())
assert t['byte_totals']['hashed_bytes']==9017363601 and t['byte_totals']['captured_bytes']==209
assert t['plan']['calls_used']==10095 and t['plan']['events_used']==1331
assert d['canonical_raw_sidecar']['rows_written']==d['canonical_raw_sidecar']['rows_expected']==10095
assert d['canonical_raw_sidecar']['state']=='COMPLETE_EXISTING_FACTS'
assert d['canonical_raw_sidecar']['unencodable_atoms']==0
assert [r['counts']['calls'] for r in d['consumer_passes']]==[9879,10095]
assert [r['raw_bytes'] for r in d['consumer_passes']]==[4373152,4428448]
assert all(r['complete'] for r in d['consumer_passes'])
total=0
for entry in d['evidence']:
    path=Path(entry['path']).resolve()
    assert path.parent==H/'large-injected-evidence-v3'
    hasher=hashlib.sha256(); size=0
    with path.open('rb') as stream:
        while chunk:=stream.read(65536):hasher.update(chunk);size+=len(chunk)
    assert size==entry['bytes'] and hasher.hexdigest()==entry['sha256'],path.name
    total+=size
assert len(d['evidence'])==15 and total==23390708
result=dict(schema_version=1,status='ACCEPTED_LARGE_GENERATED_SOURCE_PURE_ONLY',
    proof=proof,independent_actual_peer=peer,actual_accounting_review=accounting,
    root_checks='Exact accepted proof/reviews, all15 retained output hashes rechecked in chunks, unchanged source/harness pins, all known source/canonical/spy/consumer/clock/close counts and false authority flags agree. No subject import, producer replay or original payload access.',
    actual_experiments=1,fictional_inputs=216,actual_bytes_hashed=9017363601,captured_bytes=209,
    fake_original_calls=10095,read_dispatches=8799,known_successful_close_returns=216,
    source_unwind_seconds=d['source_stack_unwound_elapsed'],separate_evidence_persistence_seconds=d['evidence_publication_elapsed'],
    complete_candidate_bytes=4373152,complete_terminal_bytes=4428448,
    canonical_raw_rows=10095,retained_files=15,retained_disk_bytes=total,
    source_generated_disk_bytes=8980699,harness_evidence_disk_bytes=14410009,
    logical_raw_storage_peak_bytes=2832075,actual_peak_RSS=None,
    budget=dict(reserved_C=13551,used_C=10095,reserved_E=1496,used_E=1331),
    preserved='All source/oracle/test first failures and staticV2 HOLDs remain. The actual result was not repeated. Independent reviewer first checker omitted clock-tag expectation bits; named corrected checker and both reports remain. No source/evidence defect is attributed to that reviewer setup error.',
    next='Full actual new84 source/import/content-consumer roster and concrete first-entry/native-first-return bindings. Then separately qualify14API physical output/readback, distinct84 native/integrated resources and scientific/human gates. The original-only cap is not a joint physical budget.',
    qualification={k:False for k in ('real_entry','real_FFI','physical_IO','full_real_roster','new84_runtime','RSS_or_process_fit','scientific')},
    application_changed=False,provider_spend_usd=0,project_complete=False)
path=H/'ROLE-AWARE-LARGE-INJECTED-ROOT-ACCEPTANCE-v3.json'
with path.open('x',encoding='utf-8',newline='\n') as out:
    json.dump(result,out,sort_keys=True,indent=2);out.write('\n')
print(json.dumps(dict(status=result['status'],sha256=hashlib.sha256(path.read_bytes()).hexdigest(),retained_files=15,retained_disk_bytes=total)))
