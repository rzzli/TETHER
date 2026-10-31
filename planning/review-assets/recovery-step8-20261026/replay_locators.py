import json,time
from pathlib import Path
import pyarrow.parquet as pq
p=Path(__file__).parent; start=time.monotonic()
checks=json.loads((p/'file-checks.json').read_bytes()); paths={x['source']['source_id']:Path('E:/projects_data/drug_target_agents_data')/x['source']['path'] for x in checks}
pairs=json.loads((p/'candidate-pair-metadata.json').read_bytes()); examples={}
for pair in pairs:
    if pair['examples']:examples.setdefault(pair['target_id'],pair['examples'][0])
results=[]
for target,row in examples.items():
    q=pq.ParquetFile(paths[row['source_id']]); t=q.read_row_group(row['row_group'],columns=list(row['record']))
    assert t.slice(row['row'],1).to_pylist()[0]==row['record']
    results.append({'target_id':target,'source_id':row['source_id'],'row_group':row['row_group'],'row':row['row'],'exact_metadata_equal':True})
(p/'locator-replay.json').write_text(json.dumps({'status':'passed','scope':'One metadata row per candidate target; no passage content read','elapsed_seconds':time.monotonic()-start,'checks':results},indent=2),encoding='utf-8')
print(len(results),'exact metadata row locators replayed')
