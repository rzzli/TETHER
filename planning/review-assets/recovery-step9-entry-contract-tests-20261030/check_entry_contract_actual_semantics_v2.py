"""Retained branch/provenance review only. No subject import or replay.

The independent peer owns every artifact hash and raw/copy/query byte stream;
this checker reviews declared controls, source bindings and retained semantics.
"""
import collections
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def pin(path):
    path=Path(path).resolve();raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def read_exact(p):
    assert pin(p['path'])==p
    return json.loads(Path(p['path']).read_bytes().decode('utf-8'))


def metadata(world,label):
    suffix='.'+label+'.json'
    choices=[r for r in world['artifacts'] if r['path'].endswith(suffix)]
    if not choices and label=='source_cached_final' and world.get('same_snapshot_object'):
        return metadata(world,'first_wrapper_observed')
    assert len(choices)==1
    # Artifact byte hashes are independently reviewed by Grammar. Do not
    # duplicate its full streams or treat JSON labels as a new live brand.
    value=json.loads(Path(choices[0]['path']).read_bytes().decode('utf-8'))
    assert value['genuine_source_snapshot'] is True
    return value


def main():
    path=HERE/'ENTRY-CONTRACT-SUITE-PROOF-v2.json';proof_pin=pin(path)
    assert proof_pin['bytes']==6337722 and proof_pin['sha256']=='5c193cdb20df9fca83641059ed3c2ae419ff36ba05bdfb42ab1f5ffaf9cda7a1'
    p=json.loads(path.read_bytes().decode('utf-8'))
    binding=read_exact(p['binding']);scope=read_exact(binding['execution_scope'])
    prep=read_exact(p['preparation']);inputs=read_exact(p['inputs']);freeze=read_exact(p['freeze'])
    read_exact(p['source_pause']);contract=read_exact(prep['case_contract'])
    for value in [*p['source_map'].values(),*prep['harness'].values()]:
        assert pin(value['path'])==value
    assert p['source_map']==inputs['source_map']==freeze['source_map']==binding['source_map']
    assert prep['harness']==freeze['harness']==binding['harness']
    assert binding['allow_large_stream'] is p['allow_large_stream'] is True
    assert binding['deadline_seconds']==60
    expected=[(r['id'],v)for r in contract['cases']for v in contract['branch_expansion'].get(r['id'],[None])]
    assert len(expected)==53
    assert [(r['case'],r['variant'])for r in p['rows']]==expected
    assert [(r['case'],r['variant'])for r in inputs['branches']]==expected
    assert len({r['branch']for r in p['rows']})==53
    assert p['declared_named_controls']==32 and p['declared_branches']==p['actually_entered_branches']==53
    assert p['status']=='COMPLETED_WITH_EXPLICIT_DEFERRED_BRANCHES'
    assert p['counts']==dict(PASS=50,DEFERRED=3,FAIL=0,NOT_REACHED=0,UNKNOWN_DEADLINE=0)
    assert p['static_metadata_passes']==1 and p['runtime_or_mixed_assertion_passes']==49
    assert p['setup_error'] is p['deadline_error'] is None and p['audit_denials']==p['changed_pins']==[]
    assert p['cooperative_deadline_late'] is False
    deferred={r['branch'] for r in p['rows']if r['outcome']=='DEFERRED'}
    assert deferred=={'E08','E16/Source4_constructor','E16/Source4_start_injected'}
    rows={r['branch']:r for r in p['rows']};worlds=[];calls=collections.Counter()
    artifact_refs=[];compiler_callbacks=0
    for row,declared in zip(p['rows'],inputs['branches']):
        assert row['coverage_class']==declared['coverage_class']
        assert row['first_error'] is None and row['cleanup_errors']==row['evidence_errors']==row['source_world_constructor_errors']==[]
        assert row['action_outcome']==('DEFERRED'if row['branch']in deferred else'PASS')
        if row['branch']in deferred:assert row['deferred_reason'] is not None
        else:assert row['deferred_reason'] is None
        for world in row['worlds']:
            worlds.append(world);artifact_refs.extend(world['artifacts'])
            calls.update(c['api']for c in world['actual_original_calls'])
            compiler_callbacks+=len(world['compiler_callbacks'])
            if world['core_present']:
                if world['source_identity_comparison_available']:
                    assert world['source_identity_stable'] is True
                else:
                    assert world['source_identity_stable'] is None and world['source_identity_comparison_reason']
    assert len(worlds)==p['worlds_constructed']==p['world_construction_attempts']==55
    assert sum(w['actual_entry_attempts']for w in worlds)==p['actual_entry_attempts']==52
    assert sum(w['core_present']for w in worlds)==48
    assert set(calls)=={'CreateFileW','GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx','ReadFile','CloseHandle'}
    assert dict(calls)==dict(CreateFileW=102,GetFileType=91,GetFileInformationByHandleEx=91,
                            GetFinalPathNameByHandleW=91,GetFileSizeEx=91,ReadFile=3904,CloseHandle=90)
    assert len(artifact_refs)==len({r['path']for r in artifact_refs})==594
    # First-sample/absent-state and reserved/uninvoked distinctions.
    w=rows['E02']['worlds'][0];assert w['first_clock']['value']==100 and not w['core_present'] and not w['actual_original_calls']
    w=rows['E03']['worlds'][0];assert w['first_clock']['tag']=='UNOBSERVED' and not w['core_present'] and not w['actual_original_calls']
    w=rows['E05']['worlds'][0]
    assert w['current_call_count']==1 and w['registered_native_rows']==0 and not w['actual_original_calls']
    partial=metadata(w,'first_wrapper_observed')
    assert partial['partial_capture'] is True and partial['raw_call_count']==partial['copied_native_bytes']==0
    # Complete actual helper-plus-toy prefix and original time continuity.
    toy=rows['E07']['worlds'][0]
    assert toy['full_geometry']==inputs['toy_geometry'] and len(toy['actual_original_calls'])==51
    assert sum(toy['delivered_bytes'].values())==2196378 and len(toy['compiler_callbacks'])==5
    assert rows['E09']['notes'][0]['elapsed_original']==40
    assert rows['E09']['worlds'][0]['origin']['start']['value']==100
    assert rows['E09']['worlds'][0]['origin']['now']['value']==140
    # Expected injected failures are test PASS, not claims of source success.
    assert rows['E17']['worlds'][0]['original_primary']['type']=='builtins.KeyboardInterrupt'
    assert sum(rows['E17']['worlds'][0]['close_attempts'].values())==1
    assert sum(rows['E18']['worlds'][0]['close_attempts'].values())==0
    assert rows['E18']['notes'][0]['native']['native_state']=='STAGED_UNCOMMITTED'
    for variant,cache in (('before_commit',0),('after_commit',58)):
        r=rows['E21/'+variant];n=r['notes'][0]
        assert n['raw_count']==n['cold_known_bytes']==58 and n['cache_known_bytes']==cache
        assert n['no_healing'] is n['no_double_fold'] is True
        assert sum(c['api']=='ReadFile'for c in r['worlds'][0]['actual_original_calls'])==1
    assert rows['E22/handle_NULL']['notes'][0]['python_delivery']==dict(tag='NULL',value=None)
    assert rows['E22/handle0']['notes'][0]['python_delivery']==dict(tag='HANDLE',value=0)
    for branch in ('E22/handle_NULL','E22/handle0'):
        assert rows[branch]['notes'][0]['native']['known_value']==0
    assert rows['E22/BOOL0']['notes'][0]['known_success'] is False
    assert rows['E22/BOOLminus1']['notes'][0]['native']['known_value']==-1
    assert rows['E24']['notes'][0]['post_cutoff_dispatches']==0
    assert rows['E26']['notes'][0]['known_raw_count']==58 and rows['E26']['notes'][0]['wrapper_return_observed'] is True
    assert rows['E27']['notes'][0]['namespace_owned'] is True and rows['E27']['notes'][0]['reservation_ready'] is False
    assert not rows['E27']['worlds'][0]['actual_original_calls']
    # E28 deliberately preserves earlier copied metadata, not a live table.
    w=rows['E28']['worlds'][0]
    initial=metadata(w,'first_wrapper_observed');final=metadata(w,'source_cached_final')
    assert initial['raw_call_count']==1 and final['raw_call_count']==2
    original=initial['data']['errors']['primary'];later=final['data']['errors']['primary']
    assert original==later and 'E28 immutable original diagnostic' in original['message']
    assert w['original_primary']['args']==['later mutation']
    assert not rows['E29']['worlds'] and rows['E29']['coverage_class']=='STATIC_METADATA_ONLY'
    # E32 is a real completed procedural stream in this explicitly authorized run.
    large=rows['E32']['worlds'][0];note=rows['E32']['notes'][0]
    assert large['full_geometry']==inputs['large_geometry']
    assert len(large['actual_original_calls'])==3842
    assert sum(c['api']=='ReadFile'for c in large['actual_original_calls'])==3812
    assert sum(large['delivered_bytes'].values())==3992098940
    assert sum(large['close_attempts'].values())==5 and all(x==1 for x in large['close_attempts'].values())
    assert note['streamed_bulk_bytes']==3991999872 and note['hash_only_capture_refused'] is True
    assert note['native_route']=='NATIVE_ROUTE_UNAVAILABLE' and note['qualified_native_lease']=='DEFERRED_PREREQUISITE'
    assert note['physical_joint_admission'] is note['full_real_roster'] is note['whole_R09'] is False
    assert p['complete_entry_gate'] is False and p['native25']=='NOT_EXECUTED'
    assert all(p['qualification'][key]is False for key in ('native','physical_io','real_first_entry','whole_r09','full_real_roster','resource_fit','scientific'))
    result=dict(schema_version=1,status='CLEAR_SCOPED_SOURCE_PURE_BRANCH_RESULTS_WITH_THREE_DEFERRED_ACTIONS',
                material_blockers=[],reviewer_role='Independent of Source3 implementation; author of the pre-frozen assertion functions. Byte/hash review is a separate peer lane.',
                proof=proof_pin,checker=pin(__file__),binding=p['binding'],execution_scope=binding['execution_scope'],
                source_pause=p['source_pause'],source_map=p['source_map'],freeze=p['freeze'],preparation=p['preparation'],
                branch_counts=p['counts'],declared_named_controls=32,entered_literal_branches=53,
                runtime_or_mixed_assertion_passes=49,static_metadata_passes=1,
                deferred_actions=[dict(branch=b,reason=rows[b]['deferred_reason']['args'])for b in sorted(deferred)],
                world_fixtures=55,retainer_first_sample_attempts=52,canonical_cores_present=48,
                available_identity_comparisons_passed=46,partial_entry_comparisons_unavailable=2,
                original_callback_counts=dict(calls),total_original_callbacks=sum(calls.values()),
                helper_compiler_callback_attempts=compiler_callbacks,
                artifact_references=594,artifact_bytes_review='Grammar separately verifies every artifact hash and raw/canonical/copied/query bytes; not duplicated here.',
                selected_causal_facts=['Absent Core differs from UNOBSERVED first sample; reserved/uninvoked/missing-native row remains partial.',
                    'Actual99000B helpers plus141B toy sources preserve original refs, blobs and spent40-second clock window.',
                    'Staged bits grant no close right; committed77 survives original interrupt; known0/unknown count and error-definition axes remain distinct.',
                    'Interrupted58-byte read fold reports58 without healing/retry; signedBOOL-1 and false closer0 retain once-only rights.',
                    'Hard/invalid/late clocks preserve raw facts while blocking dispatch/eligibility.',
                    'Earlier E28 snapshot keeps one copied row and original diagnostic after later args mutation/cleanup; cached final has two rows.',
                    'E31 actual codec decode remains structural and cannot mint owner/legacy identity.'],
                E32=dict(actual_periodic_bulk_bytes=3991999872,total_known_read_bytes=3992098940,
                         actual_ReadFile_callbacks=3812,actual_original7_callbacks=3842,once_close_callbacks=5,
                         geometry=inputs['large_geometry'],reference=prep['large_reference'],
                         hash_only_capture_refused=True,native_route='NATIVE_ROUTE_UNAVAILABLE',joint_physical_admission=False),
                unexpected_setup_action_cleanup_evidence_audit_pin_deadline_errors=0,
                elapsed_seconds=p['elapsed_seconds'],timing_scope=p['evidence_persistence'],
                source_execution_or_replay_by_reviewer=0,broad_entry_gate=False,
                limitations=['Three declared actions remain deferred; this is not32/53 complete entry acceptance.',
                    'Expected negative-source exceptions are retained controls;50PASS means assertions passed, not every source operation succeeded.',
                    'Synthetic original7/data contexts only; native25, real14API/FFI/first-entry/physical outputs/full roster/new84 remain unqualified.',
                    '9.172s includes per-world evidence persistence and excludes final proof write; no RSS/commit/VRAM/production-fit inference.',
                    'Scientific/human gates and application/default status are unaffected.'])
    out=HERE/'ENTRY-CONTRACT-SUITE-ACTUAL-BRANCH-REVIEW-v2.json'
    with out.open('xb')as stream:stream.write((json.dumps(result,indent=2,sort_keys=True)+'\n').encode('utf-8'))
    print(json.dumps(dict(review=pin(out),callbacks=dict(calls),artifact_refs=len(artifact_refs))))


if __name__=='__main__':main()
