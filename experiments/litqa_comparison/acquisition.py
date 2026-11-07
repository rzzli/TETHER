"""Two-query balanced acquisition with exact raw-response reconstruction.

No model dispatch, answer choices or reference annotations enter this module.
The controller must verify a supplied expansion's native model provenance.
HTTP failures spend their conservative reservation; writes/integrity failures
abort. This module neither resumes a directory nor retries any request.
"""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.parse

from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal,read_chain
from tether_engine.serde import ContractError,canonical,encode,freeze,parse_json,safe_child
from experiments.labbench import retrieval as legacy
from .codecs import question_view,expanded_queries,parse_expansion,need,digest
from .selection import balanced_candidates,build_pool


def plan(question,strategy,*,policy=legacy.DEFAULT_POLICY,expansion=None):
    question=question_view(question)
    policy=legacy.validate_policy(policy)
    need(strategy in ('lexical','expanded'),'Unknown query strategy')
    if strategy=='lexical':
        need(expansion is None,'Lexical strategy cannot carry model expansion')
        queries=legacy.make_queries(question['question'],policy)
    else:
        expansion=parse_expansion(canonical(expansion))
        queries=expanded_queries(expansion,policy['cutoff_date'])
    # policy.query_algorithm identifies the inherited lexical rule only. The
    # strategy and explicit algorithm below govern actual acquisition.
    return freeze(dict(kind='sc04_query_plan_v1',question=question,strategy=strategy,expansion=expansion,
                       policy=policy,queries=queries,allocation='alternating_query_rank_unique_pmcid_v1'))


def validate_plan(value):
    need(set(value)=={'kind','question','strategy','expansion','policy','queries','allocation'},'Query plan fields')
    expected=plan(value['question'],value['strategy'],policy=value['policy'],expansion=value['expansion'])
    need(canonical(expected)==canonical(value),'Query plan reconstruction')
    return expected


def search_urls(value):
    value=validate_plan(value)
    return tuple(legacy.BASE+'search?'+urllib.parse.urlencode(dict(query=q,format='json',pageSize=10,resultType='core'))
                 for q in value['queries'])


def discover(records,bodies,policy):
    """Rebuild qualified hits and balanced allocation from original metadata."""
    lists=[[],[]];decisions=[]
    for index,record in enumerate(records):
        need(index<2,'Metadata request count')
        if record['transport_status']!='captured' or record['http_status']!=200:
            decisions.append(dict(stage='metadata',request_id=record['request_id'],reason='http_unavailable'));continue
        try:
            hits=parse_json(bodies[record['request_id']])['resultList']['result']
            need(isinstance(hits,list) and len(hits)<=10,'Metadata cardinality')
        except (KeyError,TypeError,ValueError,ContractError):
            decisions.append(dict(stage='metadata',request_id=record['request_id'],reason='invalid_metadata'));continue
        for rank,hit in enumerate(hits):
            candidate,reason=legacy._candidate(hit,policy)
            if candidate is None:
                decisions.append(dict(stage='metadata',request_id=record['request_id'],rank=rank,reason=reason))
            else:lists[index].append(dict(candidate=candidate,request_id=record['request_id'],rank=rank,query_slot=index))
    ordered=balanced_candidates(lists)
    # Same identity can appear in both queries. Conflicting identity/rights
    # metadata is reported and excluded rather than silently trusting one copy.
    versions={}
    for items in lists:
        for item in items:versions.setdefault(item['candidate']['pmcid'],set()).add(canonical(item['candidate']))
    conflicts={key for key,values in versions.items() if len(values)>1}
    decisions.extend(dict(stage='metadata',pmcid=key,reason='conflicting_duplicate_metadata') for key in sorted(conflicts))
    return freeze([x for x in ordered if x['candidate']['pmcid'] not in conflicts]),freeze(decisions)


def rebuild(value,records,bodies):
    value=validate_plan(value);policy=value['policy']
    searches=[r for r in records if r['kind']=='search']
    fulltext=[r for r in records if r['kind']=='fulltext']
    need([r['kind'] for r in records]==['search']*len(searches)+['fulltext']*len(fulltext),'Request stage order')
    need([r['url'] for r in searches]==list(search_urls(value)),'Complete search schedule')
    eligible,decisions=discover(searches,bodies,policy)
    chosen=eligible[:3]
    need([r['url'] for r in fulltext]==[legacy.BASE+x['candidate']['pmcid']+'/fullTextXML' for x in chosen],
         'Exact balanced article attempt schedule')
    sources=[];decisions=list(encode(decisions))
    for item,record in zip(chosen,fulltext):
        if record['transport_status']!='captured' or record['http_status']!=200:
            decisions.append(dict(stage='fulltext',request_id=record['request_id'],reason='http_unavailable'));continue
        try:source=legacy.parse_article(bodies[record['request_id']],item['candidate'])
        except (ContractError,ValueError):
            decisions.append(dict(stage='fulltext',request_id=record['request_id'],reason='identity_rights_or_xml_rejected'));continue
        source.update(original=dict(path=record['body_path'],sha256=record['body_sha256'],bytes=record['body_bytes'],
                                    receipt_path=record['receipt_path']),discovery_request_id=item['request_id'],
                      discovery_rank=item['rank'],discovery_query_slot=item['query_slot'])
        sources.append(source)
    pool=build_pool(value['question'],sources)
    return freeze(dict(sources=sources,pool=pool,decisions=decisions,
                       coverage=dict(eligible_metadata_articles=len(eligible),attempted_fulltext_articles=len(fulltext),
                                     retained_articles=len(sources),article_cap_exclusions=max(0,len(eligible)-3),
                                     missingness='bounded eligible subset; not biological absence')))


def acquire(value,output,*,deadline):
    value=validate_plan(value)
    journal=RunJournal(Path(output),kind='build');root=journal.output
    start=time.monotonic();end=min(deadline,start+value['policy']['question_seconds'])
    records=[];bodies={};accounted=measured=0
    policy=value['policy']

    def request(url,kind,cap):
        nonlocal accounted,measured
        need(time.monotonic()<end,'Acquisition deadline before dispatch')
        reservation=min(cap,policy['total_bytes']-accounted)
        need(reservation>0,'Acquisition byte allowance exhausted')
        item=dict(request_id=f'{len(records):03d}',url=legacy._safe_url(url),kind=kind,byte_reservation=reservation,
                  transport_status='started')
        records.append(item)
        journal.append('http_attempt',**item)
        accounted+=reservation
        # Only transport errors become ordinary missing responses. Persistence
        # failures below remain fatal; they must not masquerade as HTTP failures.
        try:
            response=legacy.fetch_http(url,byte_limit=reservation,timeout_seconds=min(policy['request_seconds'],end-time.monotonic()),deadline=end)
        except BaseException as error:
            item.update(transport_status='failed',http_status=None,accounted_bytes=reservation,measured_bytes=None,
                        error_type=type(error).__name__,failure_cause=getattr(error,'cause_class',type(error).__name__))
            journal.append('http_terminal',**item)
            if not isinstance(error,(OSError,TimeoutError,ContractError,ValueError)):
                raise
            return
        raw=response['body']
        need(isinstance(raw,bytes) and len(raw)<=reservation,'Transport body exceeds reservation')
        legacy._safe_url(response['final_url'])
        measured+=len(raw);accounted-=reservation-len(raw)
        path=f'responses/{item["request_id"]}.body'
        receipt_path=f'responses/{item["request_id"]}.receipt.json'
        publish_bytes(safe_child(root,path),raw)
        receipt=dict(url=url,final_url=response['final_url'],http_status=response['status'],headers=response['headers'],
                     body_path=path,body_sha256=digest(raw),body_bytes=len(raw),
                     retrieved_at_utc=datetime.now(timezone.utc).isoformat())
        receipt.update(status='completed',dataset_id='labbench_retrieved_literature',release_id=digest(raw),
                       relative_path=path,sha256=digest(raw),bytes=len(raw),source_url=url,
                       completed_at_utc=receipt['retrieved_at_utc'])
        publish_bytes(safe_child(root,receipt_path),canonical(receipt))
        item.update(transport_status='captured',http_status=response['status'],accounted_bytes=len(raw),measured_bytes=len(raw),
                    body_path=path,body_sha256=digest(raw),body_bytes=len(raw),receipt_path=receipt_path,
                    receipt_sha256=digest(canonical(receipt)))
        bodies[item['request_id']]=raw
        journal.append('http_terminal',**item)
        need(time.monotonic()<end,'Acquisition deadline after response persistence')

    try:
        publish_bytes(root/'PLAN.json',canonical(value))
        journal.append('plan_bound',plan_sha256=digest(canonical(value)))
        for url in search_urls(value):request(url,'search',policy['metadata_bytes'])
        eligible,_=discover(records,bodies,policy)
        for item in eligible[:3]:request(legacy.BASE+item['candidate']['pmcid']+'/fullTextXML','fulltext',policy['article_bytes'])
        derived=rebuild(value,records,bodies)
        manifest=freeze(dict(kind='sc04_acquisition_v1',plan=value,requests=records,**encode(derived),
             computed_at=datetime.now(timezone.utc).isoformat(),
             accounting=dict(measured_response_bytes=measured,safety_accounted_bytes=accounted,
                             unknown_transfer_upper_bytes=accounted-measured,wire_bytes=None,retries=0,provider_cost_usd=0),
             wall_seconds=time.monotonic()-start))
        publish_bytes(root/'MANIFEST.json',canonical(manifest))
        journal.append('acquisition_completed',manifest_sha256=digest(canonical(manifest)),requests=len(records))
        journal.close()
        need(time.monotonic()<end,'Acquisition finalization deadline')
        inventory={p.relative_to(root).as_posix():dict(sha256=digest(p.read_bytes()),bytes=p.stat().st_size)
                   for p in root.rglob('*') if p.is_file()}
        publish_bytes(root/'RECEIPT.json',canonical(dict(status='complete',files=inventory)))
        need(time.monotonic()<end,'Acquisition receipt finalization deadline')
        return manifest
    except BaseException as error:
        # A post-close/finalization failure still gets a separate terminal file.
        try:journal.fail(error,'acquisition')
        except BaseException:pass
        publish_bytes(root/'FAILURE.json',canonical(dict(error_type=type(error).__name__,completed_requests=len(bodies),
            attempted_requests=len(records),safety_accounted_bytes=accounted,measured_response_bytes=measured,
            automatic_retry=False)))
        raise
    finally:journal.close()


def verify(root,expected_receipt_sha256,expected_plan):
    root=Path(root);expected_plan=validate_plan(expected_plan)
    receipt_raw=legacy._read(root/'RECEIPT.json',1024*1024)
    need(digest(receipt_raw)==expected_receipt_sha256,'Acquisition external receipt anchor')
    receipt=parse_json(receipt_raw)
    need(receipt['status']=='complete','Incomplete acquisition')
    files={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    need(files==set(receipt['files'])|{'RECEIPT.json'},'Exact acquisition file inventory')
    raw={}
    for name,proof in receipt['files'].items():
        raw[name]=legacy._read(safe_child(root,name),32*1024**2)
        need(len(raw[name])==proof['bytes'] and digest(raw[name])==proof['sha256'],'Acquisition file proof')
    need(parse_json(raw['PLAN.json'])==encode(expected_plan),'Expected plan differs')
    manifest=parse_json(raw['MANIFEST.json']);need(manifest['plan']==encode(expected_plan),'Manifest plan differs')
    events=read_chain(root/'journal.jsonl');records=manifest['requests']
    need([e['event'] for e in events]==['build_reserved','plan_bound']+['http_attempt','http_terminal']*len(records)+['acquisition_completed'],
         'Exact acquisition event sequence')
    need(events[1]['details']['plan_sha256']==digest(raw['PLAN.json']) and
         events[-1]['details']==dict(manifest_sha256=digest(raw['MANIFEST.json']),requests=len(records)), 'Terminal and plan journal binding')
    measured=accounted=0;bodies={}
    for i,record in enumerate(records):
        need(record['request_id']==f'{i:03d}','Request identity/order')
        cap=expected_plan['policy']['metadata_bytes'] if record['kind']=='search' else expected_plan['policy']['article_bytes']
        reserve=min(cap,expected_plan['policy']['total_bytes']-accounted)
        need(reserve>0 and record['byte_reservation']==reserve,'Request reservation/accounting')
        started=dict(request_id=record['request_id'],url=record['url'],kind=record['kind'],byte_reservation=reserve,transport_status='started')
        need(encode(events[2+2*i]['details'])==started and encode(events[3+2*i]['details'])==record,'Request event bijection')
        if record['transport_status']=='failed':
            need(record['measured_bytes'] is None and record['accounted_bytes']==reserve and record['http_status'] is None,'Failed transfer reservation')
            accounted+=reserve;continue
        need(record['transport_status']=='captured','Unfinished HTTP attempt')
        need(record['body_path']==f'responses/{i:03d}.body' and record['receipt_path']==f'responses/{i:03d}.receipt.json',
             'Unique per-request capture paths')
        body=raw[record['body_path']];rbytes=raw[record['receipt_path']];r=parse_json(rbytes)
        need(digest(body)==record['body_sha256']==r['body_sha256'] and len(body)==record['body_bytes']==r['body_bytes']==record['measured_bytes']==record['accounted_bytes']<=reserve,'Captured transfer accounting')
        need(digest(rbytes)==record['receipt_sha256'] and r['body_path']==record['body_path'] and
             r['url']==record['url'] and r['http_status']==record['http_status'],'Transport receipt binding')
        need(r['status']=='completed' and r['dataset_id']=='labbench_retrieved_literature' and r['release_id']==r['sha256']==r['body_sha256']
             and r['bytes']==r['body_bytes'] and r['relative_path']==r['body_path'] and r['source_url']==r['url']
             and r['completed_at_utc']==r['retrieved_at_utc'],'Public-download lineage receipt fields')
        observed=datetime.fromisoformat(r['completed_at_utc']);need(observed.tzinfo is not None,'Aware download timestamp')
        legacy._safe_url(r['final_url'])
        bodies[record['request_id']]=body;measured+=len(body);accounted+=len(body)
    expected=rebuild(expected_plan,records,bodies)
    need(all(canonical(manifest[k])==canonical(v) for k,v in expected.items()),'Source/pool/coverage reconstruction')
    need(manifest['accounting']==dict(measured_response_bytes=measured,safety_accounted_bytes=accounted,
        unknown_transfer_upper_bytes=accounted-measured,wire_bytes=None,retries=0,provider_cost_usd=0),'Aggregate accounting')
    return freeze(manifest)
