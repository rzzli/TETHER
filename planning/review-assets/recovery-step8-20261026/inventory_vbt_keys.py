"""Inventory only three identity columns of the pinned local VB mapping."""
import hashlib,json,time
from pathlib import Path
from collections import defaultdict
import pyarrow.parquet as pq
import pyarrow
ROOT=Path(__file__).resolve().parents[3]
CACHE=ROOT/'data/cache/recovery-step8-exposure-20261026'
SOURCE=Path(r'E:\projects_data\drug_target_agents_data\reference\vbt_linkage\71f9da6\chembl_clinical_nct_data.parquet')
RECEIPT=Path(r'E:\projects_data\drug_target_agents_data\manifests\receipts\vbt-linkage-71f9da6.json')
COLUMNS=('targetId','diseaseId','nct_id')
def pin(p):
    with p.open('rb') as stream: sha=hashlib.file_digest(stream,'sha256').hexdigest()
    return dict(path=str(p),sha256=sha,bytes=p.stat().st_size)
started=time.monotonic()
r=json.loads(RECEIPT.read_bytes())
p=pin(SOURCE)
assert p['sha256']==r['sha256'] and p['bytes']==r['bytes']
assert r['url'].endswith('/71f9da68c95c5ee0ef4c1d9b8f45f10693de022d/datasets/clinical_trials/chembl_clinical_nct_data.parquet')
pf=pq.ParquetFile(SOURCE)
assert all(str(pf.schema_arrow.field(c).type)=='string' for c in COLUMNS)
rows=0;missing=0;trials=set();groups=defaultdict(lambda:[0,set()]);other=[]
for batch in pf.iter_batches(batch_size=4096,columns=list(COLUMNS),use_threads=False):
    assert tuple(batch.schema.names)==COLUMNS
    for row in batch.to_pylist():
        rows+=1
        target,disease,trial=(row[c] for c in COLUMNS)
        if trial:trials.add(trial)
        if not target or not disease:
            missing+=1;continue
        key=(target.strip().upper(),disease.strip().upper().replace('EFO:','EFO_').replace('MONDO:','MONDO_'))
        groups[key][0]+=1
        if trial:groups[key][1].add(trial)
assert rows==pf.metadata.num_rows
keys=[dict(target_id=k[0],indication_id=k[1],mapping_rows=v[0],distinct_trial_ids=len(v[1])) for k,v in sorted(groups.items())]
artifact=CACHE/'virtual-biotech-identity-keys-v1.json'
assert not artifact.exists()
artifact.write_text(json.dumps(dict(schema_version=1,role='evaluation_only',agent_visible=False,scope='All identity pairs in retained pinned mapping, not a qualified published evaluated subset',source=p,projection=list(COLUMNS),keys=keys),separators=(',',':'))+'\n',encoding='utf-8')
assert pin(SOURCE)==p
summary=dict(schema_version=1,role='evaluation_only',agent_visible=False,status='complete_projection_of_local_mapping_only',repository_revision='71f9da68c95c5ee0ef4c1d9b8f45f10693de022d',source=p,receipt=pin(RECEIPT),source_matches_local_receipt=True,publisher_hash_verified=r['publisher_hash_verified'],schema_columns=pf.schema_arrow.names,projected_columns=list(COLUMNS),excluded_columns=[c for c in pf.schema_arrow.names if c not in COLUMNS],projection_applied_before_python_conversion=True,rows_scanned=rows,rows_with_missing_target_or_indication=missing,distinct_target_indication_pairs=len(keys),distinct_trials=len(trials),distinct_targets=len({k[0] for k in groups}),distinct_indications=len({k[1] for k in groups}),key_inventory=pin(artifact),pyarrow_version=pyarrow.__version__,elapsed_seconds=time.monotonic()-started,clinical_fields_decoded=False,clinical_labels_read=False,normalized_outcomes_read=False,terms_basis='Pinned competitor README states Open Targets data CC0; no independent legal or upstream-per-record terms adjudication performed.',limitation='Local mapping covers published repository mapping universe. Evaluated-label subset, article vignette universe and single-cell trial-feature case list are not inferred from linkage membership. No action/modality/tissue or outcome inferred.')
summary_path=ROOT/'planning/review-assets/recovery-step8-20261026/virtual-biotech-mapping-metadata-v1.json'
assert not summary_path.exists()
summary_path.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
