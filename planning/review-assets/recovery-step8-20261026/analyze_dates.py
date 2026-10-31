"""Metadata-only follow-up; preserves the original feasibility artifacts and pins."""
import collections
import datetime
import hashlib
import json
import re
from pathlib import Path

BASE=Path('data/cache/recovery-step8-source-feasibility-20261026')
OUT=Path('data/cache/recovery-step8-date-followup-20261026')
OUT.mkdir(exist_ok=True)
checks=json.loads((BASE/'file-checks.json').read_bytes())
sources={c['source']['source_id']:c['source'] for c in checks}
pairs=json.loads((BASE/'candidate-pair-metadata.json').read_bytes())
names={(p['target_id'],p['disease_id']):p['symbol'] for p in pairs}
formats=collections.Counter(); deltas=collections.Counter(); dateyears=collections.Counter(); pubyears=collections.Counter(); folders=collections.Counter(); ds=collections.Counter(); combinations={}; shards={}; examples=[]; articles=set(); mismatch=0; evidence_date_equal=0
def date_kind(value):
    if value is None:return 'null'
    if not isinstance(value,str):return 'not_string'
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
        try:datetime.date.fromisoformat(value);return 'valid_iso_date'
        except ValueError:return 'invalid_iso_date'
    return 'other_format'
with (BASE/'matched-metadata.jsonl').open(encoding='utf-8') as f:
    for line in f:
        row=json.loads(line); r=row['record']; source=sources[row['source_id']]
        for field in ('publicationDate','evidenceDate'):formats[field+':'+date_kind(r[field])]+=1
        if r['publicationDate']==r['evidenceDate']:evidence_date_equal+=1
        if date_kind(r['publicationDate'])!='valid_iso_date':continue
        year=datetime.date.fromisoformat(r['publicationDate']).year
        if year==r['publicationYear']:continue
        mismatch+=1; delta=r['publicationYear']-year; deltas[delta]+=1;dateyears[year]+=1;pubyears[r['publicationYear']]+=1
        articles.update(r['literature']); folder='supplemental' if '/supplemental-' in source['path'] else 'original'
        folders[folder]+=1;ds[r['datasourceId']+'/'+r['datatypeId']]+=1
        key=r['targetId']+'|'+r['diseaseId']
        combinations.setdefault(key,{'symbol':names[r['targetId'],r['diseaseId']],'target_id':r['targetId'],'disease_id':r['diseaseId'],'rows':0})['rows']+=1
        shards.setdefault(row['source_id'],{'source_id':row['source_id'],'path':source['path'],'sha256':source['sha256'],'rows':0})['rows']+=1
        if abs(delta)>1:examples.append(row)
result={'schema_version':1,'role':'planning_only','total_matched_rows':10413,'mismatch_rows':mismatch,'mismatch_unique_article_ids':len(articles),'date_field_formats':formats,'publicationDate_equals_evidenceDate_rows_including_null':evidence_date_equal,'delta_publicationYear_minus_date_year':dict(sorted(deltas.items())),'mismatch_publicationYear_counts':dict(sorted(pubyears.items())),'mismatch_date_year_counts':dict(sorted(dateyears.items())),'mismatch_directory_counts':folders,'mismatch_source_datatypes':ds,'affected_combination_count':len(combinations),'affected_combinations':list(combinations.values()),'affected_shard_count':len(shards),'affected_shards':list(shards.values()),'large_difference_rows':examples,'policy':'No edits or precedence assigned to conflicting source date values; article timing conventions unverified'}
(OUT/'date-analysis.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('affected_combinations','affected_shards','large_difference_rows')},indent=2))
