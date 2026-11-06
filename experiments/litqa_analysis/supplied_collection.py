"""Independent reconstruction of the privileged SC04 DOI diagnostic.

This never treats annotated source identities as ordinary retrieval. The caller
binds each expected DOI and receipt to the independently checked enclosing stage.
"""
from datetime import date, datetime
from pathlib import Path
import re
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from .collection import BASE, POLICY, BOUNDS, metadata_candidate, article, safe_url
from .native_records import canonical, decode, digest, journal, need, read
from .sources import local_path, read_article


def query_plan(plan):
    need(set(plan)=={'kind','doi','policy','metadata_url','role','ordinary_retrieval'},'Diagnostic plan fields')
    need(plan['kind']=='sc04_supplied_doi_plan_v1' and plan['role']=='supplied_source_diagnostic' and plan['ordinary_retrieval'] is False,'Diagnostic role')
    doi=plan['doi']; need(isinstance(doi,str) and len(doi)<=256 and re.fullmatch(r'10\.[0-9]{4,9}/[a-z0-9._;()/<>:-]+',doi),'Normalized literal DOI')
    policy=plan['policy']; need(set(policy)==set(POLICY)|set(BOUNDS)|{'cutoff_date'},'Diagnostic policy fields')
    need(all(policy[k]==v for k,v in POLICY.items()),'Diagnostic policy method')
    date.fromisoformat(policy['cutoff_date'])
    for key,maximum in BOUNDS.items():
        need(type(policy[key]) in ((int,float) if key.endswith('_seconds') else (int,)) and 0<policy[key]<=maximum,'Diagnostic policy bounds')
    expected=BASE+'search?'+urlencode(dict(query='DOI:"'+doi+'"',format='json',pageSize=10,resultType='core'))
    need(plan['metadata_url']==expected,'Literal DOI lookup URL'); return expected


def choose(plan,row,body):
    if row['transport_status']!='captured' or row['http_status']!=200:return None,[dict(stage='metadata',reason='http_unavailable')]
    try:
        parsed=decode(body); hits=parsed['resultList']['result']; total=parsed.get('hitCount')
        need(isinstance(hits,list) and len(hits)<=10,'Diagnostic metadata cardinality')
        need(total is None or (type(total) is int and total>=len(hits)),'Metadata total')
    except (KeyError,TypeError,ValueError): return None,[dict(stage='metadata',reason='malformed_metadata')]
    if (total is not None and total>len(hits)) or (total is None and len(hits)==10):
        return None,[dict(stage='metadata',reason='truncated_or_unknown_complete_metadata')]
    candidates={}; decisions=[]
    for rank,hit in enumerate(hits):
        if not isinstance(hit,dict) or not isinstance(hit.get('doi'),str) or hit['doi'].strip().lower()!=plan['doi']:
            decisions.append(dict(stage='metadata',rank=rank,reason='reported_doi_mismatch_or_missing')); continue
        candidate,reason=metadata_candidate(hit,plan['policy'])
        if candidate is None: decisions.append(dict(stage='metadata',rank=rank,reason=reason)); continue
        key=candidate['pmcid']
        if key in candidates and candidates[key]!=candidate:return None,decisions+[dict(stage='metadata',reason='conflicting_duplicate_metadata')]
        candidates[key]=candidate
    if len(candidates)!=1:
        return None,decisions+[dict(stage='metadata',reason='ambiguous_pmc_identity' if candidates else 'no_eligible_exact_doi')]
    return next(iter(candidates.values())),decisions


def reconstruct(root,expected_receipt_sha256,expected_plan=None):
    root=Path(root).resolve(); receipt_raw=read(root/'RECEIPT.json',1048576)
    need(digest(receipt_raw)==expected_receipt_sha256,'External diagnostic receipt anchor')
    receipt=decode(receipt_raw); need(receipt['status']=='complete','Incomplete diagnostic receipt')
    actual=set()
    for path in root.rglob('*'):
        need(not path.is_symlink() and not (getattr(path.lstat(),'st_file_attributes',0)&0x400),'Linked diagnostic entry')
        if path.is_file():actual.add(path.relative_to(root).as_posix())
    need(actual==set(receipt['files'])|{'RECEIPT.json'},'Exact diagnostic file inventory')
    raw={}
    for name,proof in receipt['files'].items():
        content=read(local_path(root,name),16*1024**2)
        need(len(content)==proof['bytes'] and digest(content)==proof['sha256'],'Diagnostic file proof'); raw[name]=content
    plan=decode(raw['PLAN.json']); url=query_plan(plan)
    if expected_plan is not None:need(plan==expected_plan,'Enclosing phase diagnostic plan differs')
    manifest=decode(raw['MANIFEST.json']); need(manifest['kind']=='sc04_supplied_doi_v1' and manifest['plan']==plan,'Diagnostic manifest plan')
    events=journal(root/'journal.jsonl'); rows=manifest['requests']
    need(1<=len(rows)<=2 and [e['event'] for e in events]==['build_reserved','plan_bound']+['http_attempt','http_terminal']*len(rows)+['doi_completed'],'Exact diagnostic events')
    need(events[1]['details']==dict(plan_sha256=digest(raw['PLAN.json'])) and events[-1]['details']==dict(manifest_sha256=digest(raw['MANIFEST.json'])),'Diagnostic event file binding')
    bodies={}; measured=accounted=0; required={'PLAN.json','MANIFEST.json','journal.jsonl'}
    for i,row in enumerate(rows):
        kind='metadata' if i==0 else 'fulltext'; cap=plan['policy']['metadata_bytes' if i==0 else 'article_bytes']
        need(row['kind']==kind and row['request_id']==f'{i:03d}' and row['byte_reservation']==cap,'Diagnostic request sequence/reservation')
        started=dict(request_id=f'{i:03d}',kind=kind,url=row['url'],byte_reservation=cap,transport_status='started')
        need(events[2+2*i]['details']==started and events[3+2*i]['details']==row,'Diagnostic request event bijection')
        safe_url(row['url'])
        if row['transport_status']=='failed':
            need(set(row)==set(started)|{'http_status','accounted_bytes','measured_bytes','error_type'},'Failed diagnostic request fields')
            need(row['measured_bytes'] is None and row['accounted_bytes']==cap and row['http_status'] is None,'Diagnostic unknown transfer accounting')
            accounted+=cap;continue
        need(row['transport_status']=='captured','Diagnostic unresolved transfer')
        name=f'responses/{i:03d}.body'; receipt_name=f'responses/{i:03d}.receipt.json'
        need(row['body_path']==name and row['receipt_path']==receipt_name,'Diagnostic original paths'); required.update((name,receipt_name))
        body=raw[name]; transport=decode(raw[receipt_name]); amount=len(body); sha=digest(body)
        need(digest(raw[receipt_name])==row['receipt_sha256'],'Diagnostic original receipt hash')
        need(sha==row['body_sha256']==transport['sha256']==transport['release_id'],'Diagnostic raw body hash')
        need(amount==row['body_bytes']==row['measured_bytes']==row['accounted_bytes']==transport['bytes']<=cap,'Diagnostic measured bytes')
        need(transport['relative_path']==name and transport['url']==transport['source_url']==row['url'] and transport['http_status']==row['http_status'],'Diagnostic raw receipt identity')
        need(transport['status']=='completed' and transport['dataset_id']=='labbench_retrieved_literature' and transport['requested_doi']==plan['doi'] and transport['selection_role']=='supplied_source_diagnostic','Diagnostic input role')
        need(datetime.fromisoformat(transport['completed_at_utc']).tzinfo is not None,'Diagnostic aware public availability')
        safe_url(transport['final_url']); bodies[row['request_id']]=body; accounted+=amount; measured+=amount
    need(set(raw)==required,'Unexpected diagnostic artifact')
    need(rows[0]['url']==url,'Exact diagnostic metadata URL')
    candidate,decisions=choose(plan,rows[0],bodies.get('000'))
    need(len(rows)==(2 if candidate else 1),'Exact conditional diagnostic article schedule')
    source=None
    if candidate:
        row=rows[1];need(row['url']==BASE+candidate['pmcid']+'/fullTextXML','Diagnostic candidate article URL')
        if row['transport_status']!='captured' or row['http_status']!=200: decisions.append(dict(stage='fulltext',reason='http_unavailable'))
        else:
            try:
                source=article(bodies['001'],candidate); tree=ET.fromstring(bodies['001'])
                dois=sorted(set(''.join(node.itertext()).strip().lower() for node in tree.findall('./front/article-meta/article-id') if node.get('pub-id-type')=='doi'))
                need(not dois or dois==[plan['doi']],'Original front DOI conflict')
                source.update(original=dict(path=row['body_path'],sha256=row['body_sha256'],bytes=row['body_bytes'],receipt_path=row['receipt_path']),xml_dois=dois,
                    xml_doi_unknown_reason=None if dois else 'No DOI in article front metadata; exact DOI-to-PMC mapping comes from metadata response.')
            except (ValueError,ET.ParseError):
                source=None;decisions.append(dict(stage='fulltext',reason='identity_rights_or_xml_rejected'))
    coverage=dict(exact_doi_resolved=candidate is not None,article_retained=source is not None,
        scope='privileged annotated paper identity; not ordinary retrieval recall',
        missingness=None if source else 'annotated source unavailable under declared access/identity/rights checks')
    need(manifest['source']==source and manifest['decisions']==decisions and manifest['coverage']==coverage,'Diagnostic original source/decision/coverage reconstruction')
    accounting=dict(measured_response_bytes=measured,safety_accounted_bytes=accounted,unknown_transfer_upper_bytes=accounted-measured,wire_bytes=None,retries=0,provider_cost_usd=0)
    need(manifest['accounting']==accounting,'Diagnostic aggregate accounting')
    articles={} if source is None else {source['source_id']:read_article(root,source)}
    return dict(manifest=manifest,source=source,articles=articles,coverage=coverage,decisions=decisions,receipt_sha256=expected_receipt_sha256,accounting=accounting,
        checks_scope='Externally anchored annotated-DOI selection, captured rights/identity/text and transport accounting. Enclosing phase, combined pool, TETHER admission and scientific support are separate.')
