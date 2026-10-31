import json, hashlib
from pathlib import Path
from collections import Counter
p=Path(__file__).parent
r=json.loads((p/'report.json').read_bytes()); pairs=json.loads((p/'candidate-pair-metadata.json').read_bytes()); ids=json.loads((p/'identifier-resolution.json').read_bytes()); checks=json.loads((p/'file-checks.json').read_bytes())
counts=Counter(); years=Counter(); dates=Counter(); types=Counter(); evidence={}
with (p/'matched-metadata.jsonl').open(encoding='utf-8') as f:
    for line in f:
        row=json.loads(line); rec=row['record']; types[(rec['datasourceId'],rec['datatypeId'])]+=1
        for key,value in rec.items():
            if value is not None and value!=[]:counts[key]+=1
        years[str(rec.get('publicationYear'))]+=1
        for key in ('publicationDate','evidenceDate'):
            dates[key+':'+str(rec.get(key))]+=1
        evidence.setdefault(rec['id'],set()).add(hashlib.sha256(json.dumps(rec,sort_keys=True).encode()).hexdigest())
summary={'report':r,'metadata_nonempty_counts':counts,'publication_year_counts':years,'date_counts':dates,'source_datatypes':{'/'.join(k):v for k,v in types.items()},'unique_evidence_ids_global':len(evidence),'conflicting_metadata_ids_global':[k for k,v in evidence.items() if len(v)>1],'all_source_paths_unique':len({x['source']['path'] for x in checks})==len(checks),'all_source_hashes_unique':len({x['fresh_sha256'] for x in checks})==len(checks)}
(p/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
