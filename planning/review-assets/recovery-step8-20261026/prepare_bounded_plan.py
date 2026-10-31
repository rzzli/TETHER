"""Prospective metadata-only selection. Never opens source text."""
import datetime,hashlib,json
from pathlib import Path
P=Path('planning/review-assets/recovery-step8-20261026'); C=Path('data/cache/recovery-step8-source-feasibility-20261026')
sha=lambda b:hashlib.sha256(b).hexdigest()
v=P/'EXPOSURE-DRAFT-v4.json'; assert sha(v.read_bytes())=='7fa00b8859b8c196b429981d3e0a32ab45c068e79d08eb38053c1e3eb743905d'
g=json.loads(v.read_bytes())['selection_guard']; pool=sorted(g['conservative_nonmatch_pool'],key=lambda r:(r['symbol'],r['indication_id']))
assert len(pool)==25
selected=[];seen=set()
for r in pool:
    if r['target_id'] in seen:continue
    assert r['target_id'] not in g['confirmed_prior_target_exclusions']
    assert r['target_id'] not in {x['target_id'] for x in g['published_vignette_target_family_exclusions']}
    selected.append(r|{'action':None,'modality':None,'tissue':None,'purpose':'Target–disease source-reporting qualification only; no intervention conclusion'})
    seen.add(r['target_id'])
    if len(selected)==2:break
rows=[json.loads(line) for line in (C/'matched-metadata.jsonl').read_text(encoding='utf-8').splitlines()]
for q in selected:
    matches=[r for r in rows if r['record']['targetId']==q['target_id'] and r['record']['diseaseId']==q['indication_id']]
    expanded=[(r,a) for r in matches for a in sorted(set(r['record']['literature'] or []))]
    expanded.sort(key=lambda ra:(ra[0]['record']['id'],ra[1],ra[0]['source_id'],ra[0]['row_group'],ra[0]['row']))
    articles=[]; locators=[]
    for r,a in expanded:
        if a in articles:continue
        articles.append(a);locators.append({'article_id':a,**r})
        if len(articles)==3:break
    q.update(total_matching_metadata_rows=len(matches),selected_article_ids=articles,selected_record_locators=locators)
plan={'schema_version':1,'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'role':'evaluation_only','purpose':'Prospective development-only source qualification, not fresh cases or model requests','exposure_v4_sha256':sha(v.read_bytes()),'input_metadata_sha256':sha((C/'matched-metadata.jsonl').read_bytes()),'file_checks_sha256':sha((C/'file-checks.json').read_bytes()),'contexts':selected,'target_family_definition':'Distinct approved HGNC/Ensembl target identity groups; no inferred paralog grouping','selection_rule':'First two distinct targets by approved symbol then intended disease ID after v4 conservative exclusions. First three unique article IDs by evidence ID, article ID, source ID, row-group and row. First intact nonempty snippets in source list order across those fixed records. No source success or model-performance selection.','limits':{'contexts':2,'unique_articles_per_context':3,'intact_snippets_per_context':6,'source_words_per_context':1500},'text_handling':'Copy exact source text. Count words with whitespace split. Preserve empty/duplicate records and flags in audit. Never clip; stop and record if next intact snippet would exceed word cap; no replacement article/context. At six snippets, retain remaining snippet counts as unreviewed, not absent.','published_source_accession_flags':g['published_source_accession_flags'],'source_exposure':'Prior article and GEO-to-PMID crosswalk unresolved. Detect explicit flagged accessions in offered text; withhold flagged snippet/article without replacement. No freshness certification.','date_policy':'Retain original conflicting dates; no chronology conclusions or silent repair. Contemporary availability only via verified observation <= selected cutoff; future source information excluded.','metadata_lookup_limit':'At most six unique selected articles, official Europe PMC/PubMed identity/date/license metadata only; no full-text fetch','no_generation':True,'no_case_or_split_freeze':True,'human_gate':'HR3 source-only judgments and coverage pending; reviewer names do not block this preparation'}
out=P/'bounded-source-plan-v1.json'
with out.open('xb') as f:f.write(json.dumps(plan,indent=2,ensure_ascii=False).encode())
(P/'bounded-source-plan-v1.sha256').write_text(sha(out.read_bytes())+'\n',encoding='ascii')
print(json.dumps({'plan_sha256':sha(out.read_bytes()),'contexts':[(q['symbol'],q['indication_id'],q['selected_article_ids'],q['total_matching_metadata_rows']) for q in selected]},indent=2))
