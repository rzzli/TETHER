"""Independent SC04 ordinary-collection reconstruction (standard library only).

The enclosing phase must bind the expected receipt and plan. This reader verifies
captured bytes, licenses, allocation and raw text; it does not certify scientific
support, model ranking, TETHER input admission, or unseen corpus completeness.
"""
from datetime import date, datetime
from itertools import zip_longest
from pathlib import Path
import re
from urllib.parse import urlencode, urlsplit
import xml.etree.ElementTree as ET

from .native_records import canonical, decode, digest, journal, need, read
from .sources import local_path, read_article, selected_passages

BASE = 'https://www.ebi.ac.uk/europepmc/webservices/rest/'
STOP = frozenset('a an and are as at be been being by can could did do does for from had has have how in into is it its may more most not of on or other reported shown than that the their these they this those to under using was were what when where which while who why will with would according study studies paper authors following respectively found result results demonstrate demonstrated identify identified research researchers shown show whether'.split())
POLICY = dict(schema_version=1, query_algorithm='longest_unique_question_tokens_v1',
    max_queries=2, hits_per_query=10, max_articles=3, retries=0, licenses=['cc by','cc0'])
BOUNDS = dict(metadata_bytes=1048576, article_bytes=2097152, total_bytes=8388608,
    max_passages=8, passage_bytes=1000, selected_bytes=8000, request_seconds=20., question_seconds=120.)


def tokens(question):
    ordered = {}
    for token in re.findall(r'[A-Za-z][A-Za-z0-9-]{2,}', question):
        token = token.casefold().strip('-')
        if token not in STOP: ordered.setdefault(token, None)
    return list(ordered)


def query_plan(plan):
    need(set(plan) == {'kind','question','strategy','expansion','policy','queries','allocation'}, 'Plan fields')
    need(plan['kind'] == 'sc04_query_plan_v1' and plan['allocation'] == 'alternating_query_rank_unique_pmcid_v1', 'Plan algorithm')
    question = plan['question']; policy = plan['policy']
    need(set(question) == {'id','question'} and all(isinstance(v,str) and v.strip() for v in question.values()), 'Question-only plan')
    need(len(question['id'].encode()) <= 256 and len(question['question'].encode()) <= 10000, 'Question input bounds')
    need(set(policy) == set(POLICY)|set(BOUNDS)|{'cutoff_date'}, 'Policy fields')
    need(all(policy[k] == v for k,v in POLICY.items()), 'Policy method differs')
    for key, maximum in BOUNDS.items():
        need(type(policy[key]) in ((int,float) if key.endswith('_seconds') else (int,)) and 0 < policy[key] <= maximum, 'Policy bounds')
    cutoff = date.fromisoformat(policy['cutoff_date'])
    suffix = ' AND OPEN_ACCESS:Y AND (LICENSE:"cc by" OR LICENSE:"cc0") AND FIRST_PDATE:[0001-01-01 TO '+policy['cutoff_date']+']'
    if plan['strategy'] == 'lexical':
        need(plan['expansion'] is None, 'Lexical expansion forbidden')
        words = tokens(question['question']); words = sorted(enumerate(words), key=lambda x:(-len(x[1]),x[0]))
        words = [w for _,w in words[:8]]
        terms = [(' AND ',words[:3]),(' OR ',words)] if words else []
    else:
        need(plan['strategy'] == 'expanded', 'Unknown collection strategy')
        expansion = plan['expansion']; need(isinstance(expansion,dict) and set(expansion)=={'queries'}, 'Expansion fields')
        lists=expansion['queries']; need(isinstance(lists,list) and len(lists)==2, 'Two expansion lists')
        for words in lists:
            need(isinstance(words,list) and 1<=len(words)<=4, 'Expansion term count')
            need(all(isinstance(w,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 -]{0,79}',w) and w==w.strip() and '  ' not in w for w in words), 'Expansion term syntax')
            need(len(set(w.casefold() for w in words))==len(words), 'Expansion repeated terms')
        need(cutoff.isoformat()==policy['cutoff_date'], 'Expansion canonical cutoff')
        terms = [(' AND ',lists[0]),(' OR ',lists[1])]
    queries = ['('+joiner.join('"'+w+'"' for w in words)+')'+suffix for joiner,words in terms]
    if plan['strategy']=='lexical': queries = list(dict.fromkeys(queries))
    need(plan['queries']==queries, 'Query reconstruction')
    return [BASE+'search?'+urlencode(dict(query=q,format='json',pageSize=10,resultType='core')) for q in queries]


def safe_url(value):
    parsed=urlsplit(value)
    need(parsed.scheme=='https' and parsed.netloc=='www.ebi.ac.uk' and not parsed.fragment and
        (parsed.path=='/europepmc/webservices/rest/search' or
         (re.fullmatch(r'/europepmc/webservices/rest/PMC[0-9]+/fullTextXML',parsed.path) and not parsed.query)), 'Unapproved captured URL')


def metadata_candidate(hit, policy):
    if not isinstance(hit,dict): return None,'invalid_metadata_record'
    if not isinstance(hit.get('pmcid'),str) or not re.fullmatch(r'PMC[0-9]+',hit['pmcid']): return None,'missing_or_invalid_pmcid'
    if hit.get('isOpenAccess')!='Y' or hit.get('license') not in policy['licenses']: return None,'unsupported_or_unknown_metadata_license'
    publication=hit.get('firstPublicationDate')
    if publication is not None:
        try:
            if date.fromisoformat(publication)>date.fromisoformat(policy['cutoff_date']): return None,'future_or_invalid_publication_date'
        except (ValueError,TypeError): return None,'future_or_invalid_publication_date'
    return dict(pmcid=hit['pmcid'],title=hit.get('title'),doi=hit.get('doi'),firstPublicationDate=publication,license=hit['license']),None


def discover(records,bodies,policy):
    branches=[[],[]]; decisions=[]; versions={}
    for slot,record in enumerate(records):
        need(slot<2,'Metadata count bound')
        if record['transport_status']!='captured' or record['http_status']!=200:
            decisions.append(dict(stage='metadata',request_id=record['request_id'],reason='http_unavailable')); continue
        try:
            hits=decode(bodies[record['request_id']])['resultList']['result']
            need(isinstance(hits,list) and len(hits)<=10,'Metadata cardinality')
        except (KeyError,TypeError,ValueError):
            decisions.append(dict(stage='metadata',request_id=record['request_id'],reason='invalid_metadata')); continue
        for rank,hit in enumerate(hits):
            candidate,reason=metadata_candidate(hit,policy)
            if reason: decisions.append(dict(stage='metadata',request_id=record['request_id'],rank=rank,reason=reason)); continue
            branches[slot].append(dict(candidate=candidate,request_id=record['request_id'],rank=rank,query_slot=slot))
            versions.setdefault(candidate['pmcid'],set()).add(canonical(candidate))
    conflicts={key for key,values in versions.items() if len(values)>1}
    decisions += [dict(stage='metadata',pmcid=key,reason='conflicting_duplicate_metadata') for key in sorted(conflicts)]
    ordered=[]; seen=set()
    for pair in zip_longest(*branches):
        for item in pair:
            if item is not None and item['candidate']['pmcid'] not in seen:
                key=item['candidate']['pmcid']; seen.add(key)
                if key not in conflicts: ordered.append(item)
    return ordered,decisions


def article(payload,candidate):
    """Reconstruct every descriptive source field from the captured article."""
    need(len(payload)<=2097152 and b'<!ENTITY' not in payload.upper(), 'Article bound/entities')
    tree=ET.fromstring(payload)
    ids=[''.join(node.itertext()).strip().removeprefix('PMC') for node in tree.findall('.//article-id') if node.get('pub-id-type') in ('pmc','pmcid')]
    need(candidate['pmcid'].removeprefix('PMC') in ids, 'XML article identity')
    licenses=[]; granted=set()
    for element in tree.findall('.//license'):
        text=' '.join(' '.join(element.itertext()).split())
        links=[v for node in element.iter() for k,v in node.attrib.items() if k.endswith('href')]
        licenses.append(dict(text=text,links=links)); terms=(text+' '+' '.join(links)).casefold()
        restricted=('noncommercial','non-commercial','no derivatives','noderivatives','sharealike','share-alike','/by-nc','/by-nd','/by-sa')
        need(not any(v in terms for v in restricted), 'Restricted XML license')
        if any(re.search(r'creativecommons\.org/licenses/by/[0-9.]+/?$',v.casefold()) for v in links) or 'creative commons attribution license' in terms or 'creative commons attribution (cc by) license' in terms: granted.add('cc by')
        if any('creativecommons.org/publicdomain/zero/' in v.casefold() for v in links) or 'creative commons cc0' in terms: granted.add('cc0')
    need(granted=={candidate['license']}, 'Missing/ambiguous XML rights')
    spans=[]; counts={}
    for section,path in (('abstract','.//abstract//p'),('body','.//body//p')):
        nodes=tree.findall(path); counts[section+'_paragraphs']=len(nodes); need(len(nodes)<=10000,'XML paragraph count')
        for index,node in enumerate(nodes):
            text=' '.join(' '.join(node.itertext()).split())
            if text: spans.append(dict(evidence_id=f'{candidate["pmcid"]}:{section}:p{index:04d}', source_id=candidate['pmcid'],text=text,
                text_sha256=digest(text.encode()),locator=dict(xml_path=path,paragraph_index=index)))
    need(tree.find('.//body') is not None and spans,'Missing article body/paragraphs')
    return dict(source_id=candidate['pmcid'],title=candidate['title'],doi=candidate['doi'],publication_date=candidate['firstPublicationDate'],
        publication_date_unknown=candidate['firstPublicationDate'] is None,metadata_license=candidate['license'],xml_license=licenses,spans=spans,
        extraction=dict(method='ElementTree_abstract_and_body_paragraphs_itertext_whitespace_v1',**counts,
            table_cells_without_paragraph_markup_included=False,figure_images_included=False,supplement_files_included=False,original_fulltext_retained=True))


def pool(question,sources):
    words=set(tokens(question['question'])); chunks=[]; ids=set(); span_ids=set()
    for source in sources:
        need(source['source_id'] not in ids,'Repeated source'); ids.add(source['source_id'])
        for span in source['spans']:
            need(span['evidence_id'] not in span_ids,'Repeated span'); span_ids.add(span['evidence_id'])
            text=span['text']; need(digest(text.encode())==span['text_sha256'],'Pool parent digest')
            start=0
            while start<len(text):
                end=min(start+1000,len(text))
                while len(text[start:end].encode())>1000: end-=1
                need(end>start,'UTF8 chunk boundary')
                if end<len(text):
                    space=text.rfind(' ',start,end)
                    if space>start: end=space+1
                part=text[start:end]; key=f'{span["evidence_id"]}:c{start}-{end}'
                score=len(words & set(re.findall(r'[a-z][a-z0-9-]{2,}',part.casefold())))
                chunks.append((score,dict(source_id=key,text=part,sha256=digest(part.encode())),
                    dict(source_id=key,document_id=source['source_id'],span_id=span['evidence_id'],character_start=start,character_end=end,
                        parent_text_sha256=span['text_sha256'],original_sha256=source['original']['sha256'])))
                start=end
    ranked=sorted(chunks,key=lambda c:-c[0]); selected=[]; bindings=[]; size=0
    for _,item,binding in ranked:
        length=len(item['text'].encode())
        if len(selected)<16 and size+length<=10000:
            selected.append(dict(rank_id=f'p{len(selected):02d}',**item)); bindings.append(binding); size+=length
    return dict(pool=selected,bindings=bindings,coverage=dict(available_chunks=len(chunks),pool_chunks=len(selected),pool_text_bytes=size,
        excluded_chunks=len(chunks)-len(selected),available_text_bytes=sum(len(c[1]['text'].encode()) for c in chunks),
        scope='bounded raw paragraph chunks; no absence-of-evidence claim'),question_sha256=digest(question['question'].encode()))


def selection(pool_records,order=None):
    """Exact bounded selection for lexical order or independently verified permutation."""
    by_rank={p['rank_id']:p for p in pool_records}
    need(len(by_rank)==len(pool_records),'Duplicate pool ranks')
    if order is None: order=list(by_rank)
    need(len(order)==len(by_rank) and set(order)==set(by_rank),'Selection order is not an exact permutation')
    result=[]; size=0
    for rank in order:
        p=by_rank[rank]; amount=len(p['text'].encode())
        if len(result)<8 and size+amount<=8000:
            result.append({k:p[k] for k in ('source_id','sha256','text')}); size+=amount
    return result


def reconstruct(root,expected_receipt_sha256,expected_plan=None):
    root=Path(root).resolve(); receipt_raw=read(root/'RECEIPT.json',1048576)
    need(digest(receipt_raw)==expected_receipt_sha256,'External collection receipt anchor')
    receipt=decode(receipt_raw); need(receipt['status']=='complete','Incomplete collection receipt')
    actual=set()
    for path in root.rglob('*'):
        need(not path.is_symlink() and not (getattr(path.lstat(),'st_file_attributes',0)&0x400),'Linked collection entry')
        if path.is_file(): actual.add(path.relative_to(root).as_posix())
    need(actual==set(receipt['files'])|{'RECEIPT.json'},'Exact collection file inventory')
    raw={}
    for name,proof in receipt['files'].items():
        content=read(local_path(root,name)); need(len(content)==proof['bytes'] and digest(content)==proof['sha256'],'Collection file proof')
        raw[name]=content
    plan=decode(raw['PLAN.json']); urls=query_plan(plan)
    if expected_plan is not None: need(plan==expected_plan,'Enclosing phase query plan differs')
    manifest=decode(raw['MANIFEST.json']); need(manifest['kind']=='sc04_acquisition_v1' and manifest['plan']==plan,'Collection kind/plan')
    events=journal(root/'journal.jsonl'); records=manifest['requests']
    need(len(records)<=5 and [e['event'] for e in events]==['build_reserved','plan_bound']+['http_attempt','http_terminal']*len(records)+['acquisition_completed'],'Exact collection events')
    need(events[1]['details']==dict(plan_sha256=digest(raw['PLAN.json'])) and events[-1]['details']==dict(manifest_sha256=digest(raw['MANIFEST.json']),requests=len(records)), 'Collection plan/completion journal binding')
    bodies={}; measured=accounted=0; required={'PLAN.json','MANIFEST.json','journal.jsonl'}
    for i,record in enumerate(records):
        need(record['request_id']==f'{i:03d}' and record['kind'] in ('search','fulltext'),'HTTP request sequence')
        cap=plan['policy']['metadata_bytes' if record['kind']=='search' else 'article_bytes']
        reserve=min(cap,plan['policy']['total_bytes']-accounted)
        need(reserve>0 and record['byte_reservation']==reserve,'HTTP reservation')
        start=dict(request_id=f'{i:03d}',url=record['url'],kind=record['kind'],byte_reservation=reserve,transport_status='started')
        need(events[2+2*i]['details']==start and events[3+2*i]['details']==record,'HTTP event-record bijection')
        safe_url(record['url'])
        if record['transport_status']=='failed':
            need(record['http_status'] is None and record['measured_bytes'] is None and record['accounted_bytes']==reserve,'Failed HTTP reservation')
            need(set(record)==set(start)|{'http_status','accounted_bytes','measured_bytes','error_type','failure_cause'},'Failed HTTP fields')
            accounted+=reserve; continue
        need(record['transport_status']=='captured','Unfinished HTTP attempt')
        body_path=f'responses/{i:03d}.body'; receipt_path=f'responses/{i:03d}.receipt.json'
        need(record['body_path']==body_path and record['receipt_path']==receipt_path,'Unique HTTP capture paths')
        required.update((body_path,receipt_path)); body=raw[body_path]; transport=decode(raw[receipt_path]); amount=len(body); sha=digest(body)
        need(digest(raw[receipt_path])==record['receipt_sha256'],'HTTP receipt fingerprint')
        need(sha==record['body_sha256']==transport['body_sha256']==transport['sha256']==transport['release_id'],'HTTP body digest')
        need(amount==record['body_bytes']==record['measured_bytes']==record['accounted_bytes']==transport['body_bytes']==transport['bytes']<=reserve,'HTTP measured accounting')
        need(transport['body_path']==transport['relative_path']==body_path and transport['url']==transport['source_url']==record['url'] and transport['http_status']==record['http_status'],'HTTP receipt identity')
        need(transport['status']=='completed' and transport['dataset_id']=='labbench_retrieved_literature','HTTP lineage dataset')
        need(transport['completed_at_utc']==transport['retrieved_at_utc'] and datetime.fromisoformat(transport['completed_at_utc']).tzinfo is not None,'Aware HTTP availability')
        safe_url(transport['final_url']); bodies[record['request_id']]=body; measured+=amount; accounted+=amount
    need(set(raw)==required,'Unexpected collection artifact')
    searches=[r for r in records if r['kind']=='search']; fulltext=[r for r in records if r['kind']=='fulltext']
    need([r['kind'] for r in records]==['search']*len(searches)+['fulltext']*len(fulltext),'HTTP stage ordering')
    need([r['url'] for r in searches]==urls,'Complete search schedule')
    eligible,decisions=discover(searches,bodies,plan['policy']); chosen=eligible[:3]
    need([r['url'] for r in fulltext]==[BASE+c['candidate']['pmcid']+'/fullTextXML' for c in chosen],'Balanced article attempt schedule')
    sources=[]
    for selected,record in zip(chosen,fulltext):
        if record['transport_status']!='captured' or record['http_status']!=200:
            decisions.append(dict(stage='fulltext',request_id=record['request_id'],reason='http_unavailable')); continue
        try: source=article(bodies[record['request_id']],selected['candidate'])
        except (ValueError,ET.ParseError):
            decisions.append(dict(stage='fulltext',request_id=record['request_id'],reason='identity_rights_or_xml_rejected')); continue
        source.update(original=dict(path=record['body_path'],sha256=record['body_sha256'],bytes=record['body_bytes'],receipt_path=record['receipt_path']),
            discovery_request_id=selected['request_id'],discovery_rank=selected['rank'],discovery_query_slot=selected['query_slot'])
        sources.append(source)
    need(manifest['sources']==sources and manifest['decisions']==decisions,'Original source/decision reconstruction')
    expected_pool=pool(plan['question'],sources); need(manifest['pool']==expected_pool,'Complete raw-pool reconstruction')
    coverage=dict(eligible_metadata_articles=len(eligible),attempted_fulltext_articles=len(fulltext),retained_articles=len(sources),article_cap_exclusions=max(0,len(eligible)-3),missingness='bounded eligible subset; not biological absence')
    need(manifest['coverage']==coverage,'Collection coverage reconstruction')
    accounting=dict(measured_response_bytes=measured,safety_accounted_bytes=accounted,unknown_transfer_upper_bytes=accounted-measured,wire_bytes=None,retries=0,provider_cost_usd=0)
    need(manifest['accounting']==accounting,'Collection aggregate accounting')
    articles={s['source_id']:read_article(root,s) for s in sources}
    pool_report=selected_passages(expected_pool['pool'],expected_pool['bindings'],articles)
    return dict(manifest=manifest,articles=articles,retained_dois=sorted({a['reconciled_doi'] for a in articles.values() if a['reconciled_doi']}),
        pool_dois=pool_report['selected_dois'],accounting=accounting,checks_scope='Externally anchored captures, query/allocation, rights, raw source/pool and HTTP accounting; enclosing phase, native ranking, TETHER admission and scientific validity are separate.')
