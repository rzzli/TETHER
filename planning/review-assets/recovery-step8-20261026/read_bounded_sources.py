"""Finite selected-row source extraction governed by the retained prospective plan."""
import hashlib,json,time
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
P=Path('planning/review-assets/recovery-step8-20261026'); C=Path('data/cache/recovery-step8-source-feasibility-20261026'); O=Path('data/cache/recovery-step8-bounded-sources-20261026');O.mkdir(exist_ok=True)
ROOT=Path('E:/projects_data/drug_target_agents_data'); start=time.monotonic(); sha=lambda b:hashlib.sha256(b).hexdigest()
pb=(P/'bounded-source-plan-v1.json').read_bytes();assert sha(pb)=='bf23203020e88c591512c64b81bfedf733b641bbf6b61f7c8e10a3f89992cdc2';plan=json.loads(pb)
assert sha((P/'EXPOSURE-DRAFT-v4.json').read_bytes())==plan['exposure_v4_sha256']
assert sha((C/'file-checks.json').read_bytes())==plan['file_checks_sha256']
checks={x['source']['source_id']:x for x in json.loads((C/'file-checks.json').read_bytes())}; verified={}; outputs=[]
for context in plan['contexts']:
    result={'symbol':context['symbol'],'indication_id':context['indication_id'],'target_id':context['target_id'],'action':None,'modality':None,'tissue':None,'role':'evaluation_only','article_records':[],'offered_snippets':[],'words':0,'unoffered_snippets':0,'stop_reason':None}; stopped=False
    for loc in context['selected_record_locators']:
        source=checks[loc['source_id']]['source']; p=(ROOT/source['path']).resolve();assert p.is_relative_to(ROOT.resolve())
        if loc['source_id'] not in verified:
            h=hashlib.sha256(); before=p.stat()
            with p.open('rb') as f:
                for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
            assert h.hexdigest()==source['sha256']; after=p.stat();assert before.st_size==after.st_size and before.st_mtime_ns==after.st_mtime_ns
            receipt=(ROOT/source['receipt_path']).read_bytes();assert sha(receipt)==source['receipt_sha256']
            verified[loc['source_id']]={'sha256':h.hexdigest(),'bytes':after.st_size,'receipt_sha256':sha(receipt)}
        q=pq.ParquetFile(p); columns=list(loc['record'])+['textMiningSentences']
        projected=q.read_row_group(loc['row_group'],columns=columns).take(pa.array([loc['row']],type=pa.int64()))
        row=projected.to_pylist()[0];assert {k:row[k] for k in loc['record']}==loc['record']
        snippets=row.get('textMiningSentences') or []
        flags=sorted({a for item in snippets for a in plan['published_source_accession_flags'] if a in (item.get('text') or '')})
        record={'article_id':loc['article_id'],'source_id':loc['source_id'],'source_sha256':source['sha256'],'row_group':loc['row_group'],'row':loc['row'],'metadata':loc['record'],'raw_snippet_count':len(snippets),'flagged_accessions':flags,'raw_selected_record_sha256':sha(json.dumps(row,sort_keys=True,ensure_ascii=False).encode()),'date_disagreement':bool(row['publicationDate'] and row['publicationYear']!=int(row['publicationDate'][:4]))}
        result['article_records'].append(record)
        with (O/(loc['record']['id']+'.json')).open('xb') as f:f.write(json.dumps({'role':'evaluation_only','locator':loc,'source':source,'record':row},indent=2,ensure_ascii=False).encode())
        for index,item in enumerate(snippets):
            text=item.get('text'); words=len(text.split()) if isinstance(text,str) else 0
            if not text or flags or stopped:
                result['unoffered_snippets']+=1;continue
            if len(result['offered_snippets'])>=6:result['stop_reason']='six_snippet_cap';stopped=True;result['unoffered_snippets']+=1;continue
            if result['words']+words>1500:result['stop_reason']='next_intact_snippet_exceeds_word_cap';stopped=True;result['unoffered_snippets']+=1;continue
            result['offered_snippets'].append({'article_id':loc['article_id'],'source_id':loc['source_id'],'source_sha256':source['sha256'],'row_group':loc['row_group'],'row':loc['row'],'list_index':index,**item,'text_sha256':sha(text.encode()),'words':words,'duplicate_text':any(s['text']==text for s in result['offered_snippets'])})
            result['words']+=words
    outputs.append(result)
report={'schema_version':1,'role':'evaluation_only','plan_sha256':sha(pb),'contexts':outputs,'fresh_file_checks':verified,'elapsed_seconds':time.monotonic()-start,'fresh_hash_bytes':sum(v['bytes'] for v in verified.values()),'source_freshness':'unqualified_prior_article_and_GEO_overlap_unresolved','no_model_calls':True}
with (O/'source-qualification.json').open('xb') as f:f.write(json.dumps(report,indent=2,ensure_ascii=False).encode())
print(json.dumps({'elapsed_seconds':report['elapsed_seconds'],'fresh_hash_bytes':report['fresh_hash_bytes'],'contexts':[{'symbol':c['symbol'],'articles':len(c['article_records']),'offered_articles':len({s['article_id'] for s in c['offered_snippets']}),'snippets':len(c['offered_snippets']),'words':c['words'],'unoffered_snippets':c['unoffered_snippets'],'stop':c['stop_reason'],'flagged_accessions':[r['flagged_accessions'] for r in c['article_records']]} for c in outputs]},indent=2))
