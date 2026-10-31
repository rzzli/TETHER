"""Check staged graph structure/pins without following original descriptors."""
import collections
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
ROOT=H.parents[2]
path=H/'STAGED-NEW84-SELECTION-MANIFEST-v1.json'
raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='2aad403db06d5388bf9a8e8fb674bf2a26f8ad90a437f2db51e1e19f17ff80a9'
d=json.loads(raw)
rows=d['resources'];ids={r['resource_id'] for r in rows}
assert len(rows)==len(ids)==d['resource_count']==48
assert d['admission'] is False
assert all(d[k] is None for k in ('full_runtime_roster','full_runtime_module_rules','full_runtime_joint_reservations'))
assert all(v is False for v in d['qualification'].values())
states=collections.Counter(r['state'] for r in rows)
assert states==dict(EXISTING_PINNED_REFERENCE=27,PLANNED_SOURCE=16,UNBUILT=3,UNRESOLVED=2)
consumer_ids={c['consumer_id'] for c in d['consumers']}
assert len(consumer_ids)==len(d['consumers'])
checked=[]
for r in rows:
    assert all(c in consumer_ids for c in r['consumer_ids']),r['resource_id']
    assert all(p in ids for p in r.get('source_or_build_parents',r.get('build_parents',[]))),r['resource_id']
    if r['state'] in ('PLANNED_SOURCE','UNBUILT','UNRESOLVED'):
        assert r['actual_bytes'] is None and r['actual_path'] is None and r['actual_sha256'] is None
        assert r['null_reason'] and r['runtime_admission'] is False
    if r['kind'] in ('PYTHON_SOURCE_REFERENCE','NEW84_METADATA'):
        # ONLY these exact selected review assets are opened. Native descriptor
        # strings/paths, original artifacts and unbuilt outputs are never used.
        p=r['reference_pin'];target=(ROOT/p['path']).resolve()
        assert target.is_relative_to(ROOT/'planning/review-assets')
        body=target.read_bytes()
        assert len(body)==p['bytes'] and hashlib.sha256(body).hexdigest()==p['sha256']
        checked.append(r['resource_id'])
assert len(checked)==19
edges=d['source_reference_import_edges']
assert len(edges)==d['source_reference_import_edge_count']==8
for edge in edges:
    assert edge['from'] in ids and edge['to'] in ids
assert d['actor_census']['exact_joint_reservations'] is None
assert d['actor_census']['illustrative_existing_warning']['sum_before_directory_bootstrap_child_pipe_tail']==19079
assert d['related_deliverables']['ENTRY_SEAM']['pin'] is None
assert d['related_deliverables']['NATIVE_INPUT']['pin'] is None
report=dict(schema_version=1,status='PASS_STAGED_METADATA_STRUCTURE_ONLY',
    manifest_sha256=hashlib.sha256(raw).hexdigest(),resources=48,unique_resource_ids=48,
    states=dict(states),selected_review_asset_pins_checked=checked,import_edges_checked=8,
    resource_parent_and_consumer_references_resolve=True,
    original_or_native_descriptor_paths_followed=0,subject_imports=0,execution_admission=False,
    limitations=['Entry and native contract pins intentionally pending parallel authoring.','Actor labels are prospective; exact typed joint reservations remain null.','Existing source/metadata pins establish static references, not future file eligibility or live owner authority.','Native descriptors remain retained declarations; no target stat/open/hash.'])
outpath=H/'STAGED-NEW84-MANIFEST-ROOT-CHECK-v1.json'
with outpath.open('x',encoding='utf-8',newline='\n') as out:
    json.dump(report,out,sort_keys=True,indent=2);out.write('\n')
print(json.dumps(dict(status=report['status'],sha256=hashlib.sha256(outpath.read_bytes()).hexdigest(),resources=48,pins_checked=19)))
