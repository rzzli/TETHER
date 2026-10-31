"""Accept finite contracts and authorize source authoring, not execution."""
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
ROOT=H.parents[2]
def pin(path,digest):
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,path.name
    return dict(path=str(path.resolve()),bytes=len(raw),sha256=digest)
peer=pin(H/'ENTRY-KERNEL-OWNEROPS-INDEPENDENT-REVIEW-v2.json','09cb05805e72abae9d3aaa737bd3ee0c1bf70db517aafc3610d6d4c393587c34')
p=json.loads(Path(peer['path']).read_bytes())
assert p['status']=='CLEAR_FINITE_ENTRY_AND_NATIVE_INTERFACE_PREPARATION_ONLY' and p['material_blockers']==[]
for role,ref in p['pins'].items():
    raw=(ROOT/ref['path']).read_bytes()
    assert len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],role
manifest_check=pin(H/'STAGED-NEW84-MANIFEST-ROOT-CHECK-v1.json','03a18be759335649474186bc830fe54a94bed56775d6967ab156b9374b3a2232')
assert json.loads(Path(manifest_check['path']).read_bytes())['status']=='PASS_STAGED_METADATA_STRUCTURE_ONLY'
n=json.loads((H/'NATIVE-RAW-CARRIER-AND-BULK-LEASE-CONTRACT-v1.json').read_bytes())
layout=n['ABI_and_layout']
for name,total in (('header',128),('axis',32)):
    used=set()
    for field in layout[name]:
        region=set(range(field['offset'],field['offset']+field['bytes']))
        assert not used&region;used|=region
    assert used==set(range(total)),name
assert layout['slot_bytes']==256 and layout['axis_bytes']==32 and layout['header_bytes']==128
assert sorted(layout['axis_offsets'].values())==[128,160,192,224]
assert [r['id'] for r in n['per_API']]==list(range(1,15))
vectors=n['precode_vectors']['cases']
assert len(vectors)==n['precode_vectors']['count']==len({r['id'] for r in vectors})==25
sources=['preflight_entry_kernel_v1.py','preflight_owner_ops_v1.py','preflight_file_view_v1.py']
scope=dict(schema_version=1,status='ROOT_AUTHORIZED_CONCRETE_ENTRY_SOURCE_AUTHORING_ONLY',
    accepted_finite_peer=peer,staged_metadata_root_check=manifest_check,effective_contract_pins=p['pins'],
    structural_checks=dict(reviewed_pins=16,native_header_and_axis_no_gaps_or_overlap=True,native_slot_bytes=256,native_APIs=14,native_precode_cases=25,entry_named_cases=32,entry_branches=53),
    output_root='planning/review-assets/recovery-step9-entry-source-20261029',source_files=sources,
    authoring='Implement the real planned canonical entry/state/non-owning operations/file-view seam as three coherent Python modules. Source4 algorithms/wire codec are explicit lineage; no old owner/Origin/registry constructor or implicit import/cache fallback. Preserve all old files/evidence.',
    bootstrap='Explicit externally pinned kernel TCB performs first application clock, creates canonical Origin/nonce/Registry/raw store/facades, reserves namespace/journal prefix, then reads/hash/captures actual selected helper bytes before their closed imports. Output partial ownership and zero-open barrier remain distinct.',
    raw_backend='Initial source tests use an explicit synthetic canonical bank; all native/physical flags false. Raw store identity is fixed from bootstrap. Stage/commit facts, immutable copied snapshots and typed unrepresentability remain exact. Native C implementation and actual ABI/store proof are not authorized by this source batch.',
    fidelity='The full intended operational route remains the target. Freeze actual helper source sizes/hashes and manifest-derived complete bootstrap prefix independently before source tests. Do not force old3-file/209B/21call totals, strip prefix, replace genuine state with dictionaries, or use marker-only tests as final acceptance.',
    parallel_ownership=dict(kernel='os',owner_ops='grammar',file_view='root',independent_harness_and_static='native'),
    coordination='Kernel author publishes the concrete internal state/raw/port facade surface early. Ops/FileView adapt to that exact shared core. No copy of canonical cells into a replacement raw authority; no data-owned fields in Ops/FileView.',
    permitted='Write named new sources and independent new harness/fixtures/metadata; inspect their AST/syntax and exact deltas, pin final coherent files. Existing selected Source4 and13-source read list are text references only. Exact pure codec4 may be selected unchanged in the closed dependency graph.',
    execution_gate='No import/compile-exec/test of these new subject modules until a coherent source pause, exact actual bootstrap source manifest/harness binding and independent finite static review. Then root will authorize the first finite source/pure tests. Syntax AST parsing is allowed now. No future native output hash is required for source authoring.',
    forbidden=['subject execution before the stated gate','original or protected target access','C/C++ compiler/SDK/ctypes/Win32/native/model actions','physical14 writer/readback activation','cap lift or app/default changes','downloads or paid calls','replay of consumed native189 or old actual producer experiments'],
    qualification={k:False for k in ('real_entry','real_FFI','physical_IO','full_real_roster','new84_runtime','resource_fit','scientific')},provider_spend_usd=0)
path=H/'ENTRY-SOURCE-AUTHORING-SCOPE-v1.json'
with path.open('x',encoding='utf-8',newline='\n') as out:
    json.dump(scope,out,sort_keys=True,indent=2);out.write('\n')
print(json.dumps(dict(status=scope['status'],sha256=hashlib.sha256(path.read_bytes()).hexdigest(),pins_verified=16)))
