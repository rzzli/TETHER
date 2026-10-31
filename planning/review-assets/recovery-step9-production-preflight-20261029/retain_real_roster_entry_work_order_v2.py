"""Resolve the reviewed three-way staging decision; no subject execution."""
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
S=H.parent/'recovery-step9-role-aware-source-20261029'
def pin(path,digest):
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==digest,path.name
    return dict(path=str(path.resolve()),bytes=len(raw),sha256=digest)
basis=dict(
    proposal=pin(H/'NEXT-REAL-ROSTER-ENTRY-METADATA-PREPARATION-v1.json','0600e21bd1f6780434deae10c2ad04f2dfa044f6fb76b0b6b0a736f3f7c0a1f0'),
    independent_critical_review=pin(H/'NEXT-REAL-ROSTER-ENTRY-INDEPENDENT-REVIEW-v1.json','86b18693f4c4eed059143f5eecd91737aa582cd99850220d516122798d72a6df'),
    actual_large_acceptance=pin(S/'ROLE-AWARE-LARGE-INJECTED-ROOT-ACCEPTANCE-v3.json','93eeaef97a34bc07d99e00dc4c0cb84b24cee4fd8a19cde7342301579e7872e0'),
    current_project_QA=pin(S/'ROLE-AWARE-LARGE-INJECTED-CURRENT-DOCS-QA-v2.json','ad2a96c78392a80752217cd7b956451e807a6f2082b62a84816b8df2f42d9b54'),
)
decision=dict(schema_version=1,status='ROOT_AUTHORIZED_FINITE_STAGED_ROSTER_AND_ENTRY_CONTRACT_PREPARATION',basis=basis,
    decision='Adopt the three finite corrections in86b18693. Prepare a concrete staged selection manifest, canonical entry/operations/file-view interface with pre-code controls, and native raw-cell/bulk-lease contracts. This is the next major engineering stage; Source4 and all accepted evidence stay unchanged.',
    canonical_entry=dict(
        target_sources=['preflight_entry_kernel_v1.py','preflight_owner_ops_v1.py','preflight_file_view_v1.py'],
        rule='The minimal externally pinned entry creates the actual Origin/nonce/Registry/lease-output-budget state before verified helper work. OwnerOps/FileView are non-owning views over that exact state. No Source4 SharedOwner/start_injected call, copied Origin class, numeric caller-start, registry replacement or serialized authority.',
        bootstrap='State the trusted interpreter/entry pre-initialization boundary explicitly. The clock is the first application event. Class/namespace identity comes from the actual executing kernel supplied in the closed map, not a module-name lookup or duplicated source definition.',
        source_reuse='Reuse Source4 algorithms and exact wire/first-fact invariants by explicit source lineage; this does not qualify a new owner/native binding or permit replaying the consumed original experiment.'),
    staged_manifest=dict(
        states=['EXISTING_PINNED_REFERENCE','PLANNED_SOURCE','AUTHORED_SOURCE','UNBUILT','BUILT_UNADMITTED','UNRESOLVED','EXECUTION_FROZEN'],
        rule='Existing references and intended dependencies can be selected now. Unauthored/unbuilt entries have null size/hash with a reason. Their authoring is allowed after the relevant source contract, without requiring their future output hashes. A later build records actual bytes; only then can a distinct complete execution manifest and joint reservation be frozen.',
        fields='Stable resource/consumer/actor IDs, exact pin or null reason, state, source/build parents, imports, byte consumer, capture/hash-only request, native-route qualification, historical/current availability and explicit missingness. No old189 pack/EXE or old16 outputs fill a gap.',
        admission=False),
    native_boundary=dict(
        planned_source='preflight_file14_raw_v1.c',
        rule='Freeze preallocated canonical raw-cell/observedness layout and per-API semantics before native implementation/build. A later native bridge records raw scalars/counts before Python conversion. Python caches are derived. Do not claim atomicity over native return/interruption/ABI/OS scheduling; keep those trust limits explicit. Pure stubs cannot qualify native-first behavior.',
        current_Source4='Retains its accepted first-Python-visible synthetic evidence only. This work order neither upgrades that claim nor rewrites its source.'),
    bulk_consumption=dict(
        captured='Python imports and small byte parsers require same-owner immutable captured bytes. Per-file8MiB/total32MiB remain unchanged.',
        native='A separate PLANNED held-lease NativeInput route must bind canonical owner/Origin/registry, actual immutable file identity/path lifetime, child/image policy and launch ownership. Until qualified it is UNIMPLEMENTED_NATIVE_CONSUMER. Digest/path/extension is not authority; hash_only_bulk.bytes_for still refuses.',
        core4='Explicit historical core4 entries total5,232,640B. Resolve their PE/content consumers and capture role; do not infer fresh eligibility or promote by extension.'),
    actor_census='Keep original reads, writer/flush, readback, ancestry/search/directories, bootstrap, child/Job/pipe and final tail separately typed and jointly budgeted.19079 is an illustrative conservative warning before additional actors, not a new cap, observed count or admitted fit. No API8-14 physical activation.',
    deliverables=[
        dict(id='ROSTER_GRAPH',owner='native',output='STAGED-NEW84-SELECTION-MANIFEST-v1.json',scope='Finite selected NEW source/text import graph and retained descriptor references plus all planned/unbuilt/missing nodes; no execution admission.'),
        dict(id='ENTRY_SEAM',owner='grammar',output='ENTRY-KERNEL-OWNEROPS-CONTRACT-v1.json',scope='Exact public state/continuation/adoption surface, executing-kernel closed import identity, non-owning Ops/FileView, operation transitions and independent pre-code cases. No implementation yet.'),
        dict(id='NATIVE_INPUT',owner='os',output='NATIVE-RAW-CARRIER-AND-BULK-LEASE-CONTRACT-v1.json',scope='Concrete bounded raw-cell and bulk-lease authority/consumer interfaces,14API actor distinctions, remaining trust limits and pre-code vectors. No C/native build or execution yet.'),
    ],
    source_authoring_next='After the three finite deliverables are mutually consistent and reviewed, root will authorize the named concrete entry/OwnerOps/FileView source batch and unchanged pre-code controls. Do not require final native/parent/model outputs to authorize this source work. Native compilation and actual runtime remain later distinct gates.',
    permitted_reads='Exact Source4 source text througha746; accepted NEW Unicode codec/analyzer/observer/resource/archive/journal source/contract files reached through retained acceptance pins, with a finite enumerated path/hash list before AST import inspection;458a/3a7e/980b/retainedABI/core4/six frozen84 descriptor metadata andb181 first-entry review. Never follow embedded target paths.',
    forbidden=['original target stat/open/hash or directory discovery','protected outcome files','subject imports/execution','C++/C compiler/SDK/ctypes/Win32/native/model actions','downloads or paid access','cap changes/application default changes','old experiment replay','automatic execution admission'],
    current_docs='The major large-producer assessment/ten-doc QA is complete. Append pending next-stage TODOs only; do not mark the broader R09 or human/scientific gates complete.',
    qualification={k:False for k in ('real_entry','real_FFI','physical_IO','full_real_roster','new84_runtime','resource_fit','scientific')},provider_spend_usd=0)
path=H/'REAL-ROSTER-ENTRY-ROOT-WORK-ORDER-v2.json'
with path.open('x',encoding='utf-8',newline='\n') as out:
    json.dump(decision,out,sort_keys=True,indent=2);out.write('\n')
print(json.dumps(dict(status=decision['status'],sha256=hashlib.sha256(path.read_bytes()).hexdigest())))
