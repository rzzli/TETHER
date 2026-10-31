import csv, hashlib, json, time
from pathlib import Path
from collections import Counter
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

START=time.monotonic()
OUT=Path(__file__).parent
ROOT=Path('E:/projects_data/drug_target_agents_data')
INV=Path('data/derived/literature-coverage-20261017T082208Z/inspection.json')
inventory=json.loads(INV.read_bytes())
GENES='IL17A IL17RA IL23R IL12B TYK2 BTK IL12RB1 IL12RB2 CD80 CD86 CTLA4 ITGA4 MADCAM1 FCGRT'.split()
checks=[]
stats=Counter()
def sha(data): return hashlib.sha256(data).hexdigest()
def canonical(obj): return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def write(name,obj): (OUT/name).write_bytes(json.dumps(obj,indent=2,ensure_ascii=False).encode())
def event(**kw):
    kw['elapsed_seconds']=time.monotonic()-START
    with (OUT/'progress.jsonl').open('a') as f: f.write(json.dumps(kw)+'\n')
    print(json.dumps(kw),flush=True)
def checked(entry):
    s=entry['source']; p=(ROOT/s['path']).resolve()
    assert p.is_relative_to(ROOT.resolve())
    assert s['role'] in ('agent_evidence','reference') and s['parents']==[]
    rp=(ROOT/s['receipt_path']).resolve(); assert rp.is_relative_to(ROOT.resolve())
    raw=rp.read_bytes(); assert sha(raw)==s['receipt_sha256']; r=json.loads(raw)
    assert r['sha256']==s['sha256'] and r['bytes']==entry['bytes']
    assert r['relative_path'].replace('\\','/')==s['path']
    before=p.stat(); h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    after=p.stat(); assert before.st_size==after.st_size==entry['bytes'] and before.st_mtime_ns==after.st_mtime_ns
    assert h.hexdigest()==s['sha256']
    stats['fresh_hash_bytes']+=before.st_size;stats['receipt_bytes']+=len(raw)
    checks.append({'source':s,'bytes':before.st_size,'fresh_sha256':h.hexdigest(),'receipt_fresh_sha256':sha(raw)})
    return p
def parquet(entry):
    p=checked(entry); q=pq.ParquetFile(p)
    assert q.schema_arrow.names==entry['columns'] and q.metadata.num_rows==entry['rows']
    assert sha(canonical(q.schema_arrow.names))==entry['schema_sha256']
    return q

try:
    hgnc_entry=next(e for e in inventory['files'] if e['source']['dataset_id']=='hgnc_symbols')
    hgnc=[]
    with checked(hgnc_entry).open(encoding='utf-8-sig',newline='') as f:
        for n,r in enumerate(csv.DictReader(f,delimiter='\t'),2):
            if r['symbol'] in GENES: hgnc.append({k:r[k] for k in ('hgnc_id','symbol','status','ensembl_gene_id')}|{'line':n})
    targets=[]; diseases=[]
    for e in inventory['files']:
        ds=e['source']['dataset_id']
        if ds not in ('ot_target','ot_disease'): continue
        q=parquet(e)
        cols=['id','approvedSymbol','approvedName','biotype'] if ds=='ot_target' else ['id','name']
        for rg in range(q.num_row_groups):
            t=q.read_row_group(rg,columns=cols)
            for i,r in enumerate(t.to_pylist()):
                if ds=='ot_target' and r['approvedSymbol'] in GENES: targets.append(r|{'source_id':e['source']['source_id'],'row_group':rg,'row':i})
                if ds=='ot_disease' and r['name'].lower().replace("'",'') in ('rheumatoid arthritis','ulcerative colitis','crohn disease','crohns disease','psoriasis'): diseases.append(r|{'source_id':e['source']['source_id'],'row_group':rg,'row':i})
    write('identifier-resolution.json',{'hgnc':hgnc,'targets':targets,'diseases':diseases})
    assert len(targets)==len(hgnc)==14 and len(diseases)>=4
    for t in targets:
        hs=[h for h in hgnc if h['symbol']==t['approvedSymbol']]
        assert len(hs)==1 and hs[0]['status']=='Approved' and hs[0]['ensembl_gene_id']==t['id']
    tids={t['id']:t['approvedSymbol'] for t in targets}; dids={d['id']:d['name'] for d in diseases}
    pairs={(t,d):{'target_id':t,'symbol':tids[t],'disease_id':d,'disease':dids[d],'physical_matches':0,'ids':{},'articles':set(),'contexts':Counter(),'examples':[]} for t in tids for d in dids}
    files=[e for e in inventory['files'] if e['source']['dataset_id']=='ot_evidence' and Path(e['source']['path']).parent.name in ('europepmc','sourceId=europepmc')]
    assert len(files)==100
    fields=['id','targetId','diseaseId','datasourceId','datatypeId','literature','pmcIds','publicationDate','publicationYear','evidenceDate','studyId','ancestry','ancestryId','cellType','biosamplesFromSource']
    with (OUT/'matched-metadata.jsonl').open('w',encoding='utf-8') as dest:
        for fi,e in enumerate(sorted(files,key=lambda e:e['source']['path'])):
            q=parquet(e); cols=[c for c in fields if c in q.schema_arrow.names]
            for rg in range(q.num_row_groups):
                meta=q.metadata.row_group(rg)
                stats['projected_compressed_column_bytes']+=sum(meta.column(j).total_compressed_size for j in range(meta.num_columns) if meta.column(j).path_in_schema.split('.')[0] in cols)
                offset=0
                for b in q.iter_batches(batch_size=65536,row_groups=[rg],columns=cols):
                    stats['physical_rows_scanned']+=b.num_rows
                    mask=pc.and_(pc.is_in(b.column('targetId'),value_set=pa.array(list(tids))),pc.is_in(b.column('diseaseId'),value_set=pa.array(list(dids))))
                    mask=pc.and_(mask,pc.and_(pc.not_equal(b.column('datatypeId'),'known_drug'),pc.not_equal(b.column('datasourceId'),'chembl')))
                    loc=pc.indices_nonzero(mask).to_pylist(); selected=b.filter(mask)
                    stats['selected_arrow_bytes']+=selected.nbytes
                    for rowidx,r in zip(loc,selected.to_pylist()):
                        stats['selected_rows']+=1; pair=pairs[r['targetId'],r['diseaseId']]; pair['physical_matches']+=1
                        row={'source_id':e['source']['source_id'],'source_sha256':e['source']['sha256'],'row_group':rg,'row':offset+rowidx,'record':r}
                        dest.write(json.dumps(row,ensure_ascii=False)+'\n')
                        key=r['id']; fingerprint=sha(canonical(r)); pair['ids'].setdefault(key,set()).add(fingerprint)
                        pair['articles'].update(str(v) for v in (r.get('literature') or []))
                        for c in cols:
                            if r[c] is not None and r[c]!=[]: pair['contexts'][c]+=1
                        if len(pair['examples'])<3: pair['examples'].append(row)
                    offset+=b.num_rows
            if (fi+1)%10==0:event(files=fi+1,**stats)
    output=[]
    article_pairs={}
    for pair in pairs.values():
        pair['unique_evidence_ids']=len(pair['ids']);pair['duplicate_id_rows']=pair['physical_matches']-len(pair['ids'])
        pair['conflicting_metadata_ids']=[k for k,v in pair.pop('ids').items() if len(v)>1]
        pair['article_ids']=sorted(pair.pop('articles'));pair['unique_article_ids']=len(pair['article_ids'])
        pair.update(action=None,modality=None,tissue=None,case_key=None,exposure_status='pending_independent_audit',reviewer_coverage='pending',source_text_sufficiency='not_assessed')
        for a in pair['article_ids']:article_pairs.setdefault(a,[]).append([pair['target_id'],pair['disease_id']])
        output.append(pair)
    write('candidate-pair-metadata.json',output);write('cross-pair-publications.json',article_pairs);write('file-checks.json',checks)
    report={'schema_version':1,'status':'metadata_feasibility_checked_not_case_freeze','inventory_path':str(INV),'inventory_sha256':sha(INV.read_bytes()),'original_manifest_sha256_retained_not_reopened':inventory['manifest_sha256'],'catalog_sha256':sha(Path('data/catalog/sources.json').read_bytes()),'files_fresh_hashed':len(checks),'statistics':dict(stats),'elapsed_seconds':time.monotonic()-START,'pairs':len(output),'pairs_with_selected_rows':sum(p['physical_matches']>0 for p in output),'unique_article_ids_across_pairs':len(article_pairs),'shared_articles_across_pairs':sum(len(v)>1 for v in article_pairs.values()),'scope':'Only the existing 100 Europe PMC shards and 12 identifier files; no whole-release completeness or biological absence claim','pending':['exposure register merge','HR3 relevant reviewer coverage','passage sufficiency and bounded payload qualification','case/action/modality/tissue assignment and split freeze']}
    write('report.json',report);event(status='complete',**stats)
except BaseException as exc:
    write('failure.json',{'type':type(exc).__name__,'message':str(exc),'elapsed_seconds':time.monotonic()-START});write('file-checks.json',checks);raise
