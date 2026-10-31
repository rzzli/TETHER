"""Retain first failure and authorize the bounded three-finding source fix."""
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
ROOT=H.parents[2]
def pin(name,digest):
    path=H/name;raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==digest,name
    return dict(path=str(path.resolve()),bytes=len(raw),sha256=digest)
proof=pin('ENTRY-SOURCE1-SMOKE-PROOF-v1.json','6ec80005b91a664c6016b2beed48a74f41239827a08d8b112c45f2b9ab5865a3')
d=json.loads(Path(proof['path']).read_bytes())
assert d['status']=='EXPECTED_ENTRY_SETUP_FAILURE_RETAINED' and d['actual_entry_attempts']==1
assert d['entry_error']['code']=='INVALID_INPUT'
assert any(f['function']=='__post_init__' and f['file'].endswith('preflight_entry_kernel_v1.py') for f in d['entry_error']['frames'])
assert d['observations']['original_dispatches']==d['observations']['helper_compiler_callbacks']==0
assert d['audit_denials']==d['changed_pins']==[]
assert d['intended_checks']['test02_normal_captured_helpers_finish']=='NOT_REACHED'
assert d['intended_checks']['test03_staged_scalar_has_no_cleanup_authority']=='NOT_REACHED'
scope=dict(schema_version=1,status='ROOT_AUTHORIZED_SOURCE2_THREE_FINDING_CORRECTION_ONLY_NO_EXECUTION',
    source1_first_actual_failure=proof,
    static_reviews=[pin('ENTRY-OPS-FILEVIEW-STATIC-REVIEW-v3.json','f0bed08a9d9945e52e947a7c2d7be44487f37845a56456550453cbbdcb11cf4b'),pin('ENTRY-KERNEL-FILEVIEW-INDEPENDENT-STATIC-REVIEW-v1.json','d0e59419fee82b675ae9a24b34c256b030094690b99d21f895439a0ee8361962')],
    pre_fix_checks=pin('ENTRY-INITIAL-REGRESSION-FREEZE-v1.json','4fc87eec8904b341d3abdfc538d682cdfb149cf8ec3bc161d9b836c2ca0f639f'),
    evidence='One actual Source1 entry failed at the backend method gate. First clock, original error and unchanged source/harness pins retained; no original dispatch/helper execution. F1/F2 are statically confirmed but were NOT_REACHED dynamically. Do not describe them as reproduced.',
    output_root='planning/review-assets/recovery-step9-entry-source2-20261030',
    modules=['preflight_entry_kernel_v2','preflight_owner_ops_v2','preflight_file_view_v2'],
    namespace='Coherently update new own imports, EntryPlan defaults and explicit trusted kernel key/cycle checks to_v2. Actual executing namespace/class identity remains mandatory. Public contract signatures and exact codec4 stay unchanged. No stale module/source fallback.',
    corrections=[
        dict(id='F3',rule='Bootstrap binding precondition requires callable invoke_reserved, matching the exact SyntheticRawBackend. No runtime alias/workaround.'),
        dict(id='F1',rule='Expose the declared sink.close_journal callback through the stable same-core facade, preserving consumed once-close/ACK/clock semantics.'),
        dict(id='F2',rule='Canonical bank publishes/commits before cache authority. Add state.committed_fact(call,axis) as inspection-only committed-native observation or UNOBSERVED. Handles, count definedness, cold canonical projections, raw snapshot facts and Ops close/wire rows use that bank authority, never uncommitted caches. Commit-then-cache failure retains known facts; no reporting reconciliation/fold/cache repair or healing quarantine. Distinct Python delivery observations may be retained separately, never promoted to native facts.')],
    preservation='Every Source1 source/pause/helper/fixture/binding/attempt/proof and static review remains at its original path. Write only the new Source2 cohort; no old file overwrite, source1 retry or consumed native189 replay.',
    ownership=dict(kernel='os',owner_ops='grammar',file_view='root',independent_harness='native'),
    validation='The three pre-fix regression expectations already exist. Native derives a separately named Source2 harness/binding/actual helper prefix without weakening them. Freeze all final source/helper sizes/hashes and static review before Root authorizes first corrected tests. Full32/53/native25 scope remains separate and excludes unavailable qualified native branches honestly.',
    permitted='Only bounded source corrections/coherent renames, independent harness preparation, AST/symbol/static checks and exact source pause. No import/compile-exec/test of Source2 subjects yet.',
    forbidden=['Source1 edits/retry','new native/physical/model/paid/download actions','original/protected targets','cap changes','new unreviewed features','application/default changes'],
    qualification=False,provider_spend_usd=0)
path=H/'ENTRY-SOURCE2-CORRECTION-AUTHORING-SCOPE-v1.json'
with path.open('x',encoding='utf-8',newline='\n')as out:
    json.dump(scope,out,sort_keys=True,indent=2);out.write('\n')
print(json.dumps(dict(status=scope['status'],sha256=hashlib.sha256(path.read_bytes()).hexdigest())))
