"""Privileged DOI lookup for SC04's separately labelled source diagnostic.

One metadata request and at most one article request per annotated DOI. This
module does not answer questions or claim ordinary retrieval performance.
"""
from datetime import datetime,timezone
from pathlib import Path
import re
import time
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from asof.atomic import publish_bytes
from asof.journal import RunJournal,read_chain
from asof.serde import canonical,encode,freeze,parse_json,safe_child,ContractError
from experiments.labbench import retrieval as legacy
from experiments.litqa_comparison.codecs import need,digest


def identity(value):
    need(isinstance(value,str) and len(value)<=256 and re.fullmatch(r'10\.[0-9]{4,9}/[a-z0-9._;()/<>:-]+',value),
         'Explicit normalized DOI required')
    return value


def plan(doi,policy=legacy.DEFAULT_POLICY):
    doi=identity(doi);policy=legacy.validate_policy(policy)
    # Literal quoted DOI on a fixed HTTPS origin. No provider URL from the
    # reference annotation is fetched. Metadata rights are examined explicitly.
    url=legacy.BASE+'search?'+urlencode(dict(query='DOI:"'+doi+'"',format='json',pageSize=10,resultType='core'))
    return freeze(dict(kind='sc04_supplied_doi_plan_v1',doi=doi,policy=policy,metadata_url=url,
                       role='supplied_source_diagnostic',ordinary_retrieval=False))


def validate_plan(value):
    need(canonical(value)==canonical(plan(value['doi'],value['policy'])),'Diagnostic plan reconstruction')
    return freeze(value)


def metadata_choice(value,record,body):
    if record['transport_status']!='captured' or record['http_status']!=200:
        return None,[dict(stage='metadata',reason='http_unavailable')]
    try:
        parsed=parse_json(body);hits=parsed['resultList']['result']
        need(isinstance(hits,list) and len(hits)<=10,'Metadata cardinality')
        total=parsed.get('hitCount')
        need(total is None or (type(total) is int and total>=len(hits)),'Metadata total count')
    except (KeyError,TypeError,ValueError):return None,[dict(stage='metadata',reason='malformed_metadata')]
    if (total is not None and total>len(hits)) or (total is None and len(hits)==10):
        return None,[dict(stage='metadata',reason='truncated_or_unknown_complete_metadata')]
    decisions=[];candidates={}
    for n,hit in enumerate(hits):
        if not isinstance(hit,dict) or not isinstance(hit.get('doi'),str) or hit['doi'].strip().lower()!=value['doi']:
            decisions.append(dict(stage='metadata',rank=n,reason='reported_doi_mismatch_or_missing'));continue
        candidate,reason=legacy._candidate(hit,value['policy'])
        if candidate is None:decisions.append(dict(stage='metadata',rank=n,reason=reason));continue
        key=candidate['pmcid']
        if key in candidates and canonical(candidates[key])!=canonical(candidate):
            return None,decisions+[dict(stage='metadata',reason='conflicting_duplicate_metadata')]
        candidates[key]=candidate
    if len(candidates)!=1:
        return None,decisions+[dict(stage='metadata',reason='ambiguous_pmc_identity' if candidates else 'no_eligible_exact_doi')]
    return next(iter(candidates.values())),decisions


def rebuild(value,records,bodies):
    value=validate_plan(value)
    need(1<=len(records)<=2 and records[0]['kind']=='metadata' and records[0]['url']==value['metadata_url'],'Exact diagnostic metadata request')
    candidate,decisions=metadata_choice(value,records[0],bodies.get('000'))
    need(len(records)==(2 if candidate else 1),'Exact diagnostic fulltext schedule')
    source=None
    if candidate is not None:
        record=records[1]
        need(record['kind']=='fulltext' and record['url']==legacy.BASE+candidate['pmcid']+'/fullTextXML','Exact diagnostic article URL')
        if record['transport_status']!='captured' or record['http_status']!=200:
            decisions.append(dict(stage='fulltext',reason='http_unavailable'))
        else:
            try:
                raw=bodies['001'];parsed=legacy.parse_article(raw,candidate)
                tree=ET.fromstring(raw)
                dois=sorted(set(''.join(n.itertext()).strip().lower() for n in tree.findall('./front/article-meta/article-id')
                                if n.get('pub-id-type')=='doi'))
                need(not dois or dois==[value['doi']],'Fulltext DOI conflicts with exact requested DOI')
                parsed.update(original=dict(path=record['body_path'],sha256=record['body_sha256'],bytes=record['body_bytes'],
                                            receipt_path=record['receipt_path']),xml_dois=dois,
                    xml_doi_unknown_reason=None if dois else 'No DOI in article front metadata; exact DOI-to-PMC mapping comes from metadata response.')
                source=parsed
            except (ValueError,ContractError):decisions.append(dict(stage='fulltext',reason='identity_rights_or_xml_rejected'))
    return freeze(dict(source=source,decisions=decisions,coverage=dict(exact_doi_resolved=candidate is not None,
        article_retained=source is not None,scope='privileged annotated paper identity; not ordinary retrieval recall',
        missingness=None if source else 'annotated source unavailable under declared access/identity/rights checks')))


def acquire(value,output,*,deadline):
    value=validate_plan(value);policy=value['policy'];start=time.monotonic();end=min(deadline,start+60)
    journal=RunJournal(Path(output),kind='build');root=journal.output;(root/'responses').mkdir()
    records=[];bodies={}
    def request(url,kind,cap):
        need(time.monotonic()<end,'Diagnostic deadline before request')
        row=dict(request_id=f'{len(records):03d}',kind=kind,url=legacy._safe_url(url),byte_reservation=cap,transport_status='started')
        records.append(row);journal.append('http_attempt',**row)
        try:
            response=legacy.fetch_http(url,byte_limit=cap,timeout_seconds=min(20,end-time.monotonic()),deadline=end)
        except BaseException as error:
            row.update(transport_status='failed',http_status=None,accounted_bytes=cap,measured_bytes=None,error_type=type(error).__name__)
            journal.append('http_terminal',**row)
            if not isinstance(error,(OSError,TimeoutError,ContractError,ValueError)):raise
            return
        body=response['body'];need(isinstance(body,bytes) and len(body)<=cap,'Diagnostic response cap')
        legacy._safe_url(response['final_url'])
        name='responses/'+row['request_id']+'.body';receipt_name='responses/'+row['request_id']+'.receipt.json'
        publish_bytes(root/name,body)
        observed=datetime.now(timezone.utc).isoformat()
        receipt=dict(status='completed',dataset_id='labbench_retrieved_literature',release_id=digest(body),
            relative_path=name,sha256=digest(body),bytes=len(body),url=url,source_url=url,final_url=response['final_url'],
            http_status=response['status'],headers=response['headers'],completed_at_utc=observed,
            selection_role='supplied_source_diagnostic',requested_doi=value['doi'])
        publish_bytes(root/receipt_name,canonical(receipt))
        row.update(transport_status='captured',http_status=response['status'],body_path=name,body_sha256=digest(body),body_bytes=len(body),
            receipt_path=receipt_name,receipt_sha256=digest(canonical(receipt)),measured_bytes=len(body),accounted_bytes=len(body))
        bodies[row['request_id']]=body;journal.append('http_terminal',**row)
        need(time.monotonic()<end,'Diagnostic deadline after response persistence')
    try:
        publish_bytes(root/'PLAN.json',canonical(value));journal.append('plan_bound',plan_sha256=digest(canonical(value)))
        request(value['metadata_url'],'metadata',policy['metadata_bytes'])
        candidate,_=metadata_choice(value,records[0],bodies.get('000'))
        if candidate:request(legacy.BASE+candidate['pmcid']+'/fullTextXML','fulltext',policy['article_bytes'])
        derived=rebuild(value,records,bodies)
        measured=sum(r['measured_bytes'] or 0 for r in records);accounted=sum(r['accounted_bytes'] for r in records)
        manifest=dict(kind='sc04_supplied_doi_v1',plan=value,requests=records,**encode(derived),
            computed_at=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,
            accounting=dict(measured_response_bytes=measured,safety_accounted_bytes=accounted,unknown_transfer_upper_bytes=accounted-measured,
                            wire_bytes=None,retries=0,provider_cost_usd=0))
        publish_bytes(root/'MANIFEST.json',canonical(manifest));journal.append('doi_completed',manifest_sha256=digest(canonical(manifest)))
        journal.close()
        files={p.relative_to(root).as_posix():dict(sha256=digest(p.read_bytes()),bytes=p.stat().st_size)
               for p in root.rglob('*') if p.is_file()}
        publish_bytes(root/'RECEIPT.json',canonical(dict(status='complete',files=files)))
        need(time.monotonic()<end,'Diagnostic receipt deadline');return freeze(manifest)
    except BaseException as error:
        try:journal.fail(error,'doi_acquisition')
        except BaseException:pass
        publish_bytes(root/'FAILURE.json',canonical(dict(error_type=type(error).__name__,attempted_requests=len(records),
            completed_responses=len(bodies),safety_reserved_bytes=sum(r['byte_reservation'] for r in records),automatic_retry=False)))
        raise
    finally:journal.close()


def verify(root,expected_sha,value):
    root=Path(root);value=validate_plan(value)
    receipt_raw=legacy._read(root/'RECEIPT.json',1024**2);need(digest(receipt_raw)==expected_sha,'Diagnostic external receipt anchor')
    receipt=parse_json(receipt_raw);need(receipt['status']=='complete','Incomplete diagnostic acquisition')
    need(set(receipt['files'])|{'RECEIPT.json'}=={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()},'Exact diagnostic inventory')
    raw={}
    for name,proof in receipt['files'].items():
        raw[name]=legacy._read(safe_child(root,name),16*1024**2)
        need(len(raw[name])==proof['bytes'] and digest(raw[name])==proof['sha256'],'Diagnostic file bytes')
    need(parse_json(raw['PLAN.json'])==encode(value),'Diagnostic plan binding')
    manifest=parse_json(raw['MANIFEST.json']);need(canonical(manifest['plan'])==canonical(value),'Manifest plan binding')
    records=manifest['requests'];events=read_chain(root/'journal.jsonl')
    need([e['event'] for e in events]==['build_reserved','plan_bound']+['http_attempt','http_terminal']*len(records)+['doi_completed'],'Exact diagnostic journal events')
    need(events[1]['details']==dict(plan_sha256=digest(raw['PLAN.json'])) and
         events[-1]['details']==dict(manifest_sha256=digest(raw['MANIFEST.json'])),'Diagnostic plan/terminal journal binding')
    bodies={};accounted=measured=0
    for i,row in enumerate(records):
        cap=value['policy']['metadata_bytes'] if i==0 else value['policy']['article_bytes']
        need(row['request_id']==f'{i:03d}' and row['byte_reservation']==cap,'Diagnostic reservation identity')
        started={k:row[k] for k in ('request_id','kind','url','byte_reservation')};started['transport_status']='started'
        need(encode(events[2+i*2]['details'])==started and encode(events[3+i*2]['details'])==row,'Diagnostic event bijection')
        if row['transport_status']=='failed':
            need(row['measured_bytes'] is None and row['accounted_bytes']==cap and row['http_status'] is None,'Unknown transfer reservation')
            accounted+=cap;continue
        need(row['transport_status']=='captured' and row['body_path']==f'responses/{i:03d}.body' and
             row['receipt_path']==f'responses/{i:03d}.receipt.json','Exact captured request paths')
        body=raw[row['body_path']];rbytes=raw[row['receipt_path']];r=parse_json(rbytes)
        need(digest(body)==row['body_sha256']==r['sha256']==r['release_id'] and
             len(body)==row['body_bytes']==row['measured_bytes']==row['accounted_bytes']==r['bytes']<=cap,'Diagnostic captured bytes')
        need(digest(rbytes)==row['receipt_sha256'] and r['relative_path']==row['body_path'] and
             r['url']==r['source_url']==row['url'] and r['http_status']==row['http_status'],'Diagnostic raw receipt')
        need(r['status']=='completed' and r['dataset_id']=='labbench_retrieved_literature' and
             r['requested_doi']==value['doi'] and r['selection_role']=='supplied_source_diagnostic','Diagnostic lineage role')
        need(datetime.fromisoformat(r['completed_at_utc']).tzinfo is not None,'Aware retrieval date');legacy._safe_url(r['final_url'])
        bodies[row['request_id']]=body;accounted+=len(body);measured+=len(body)
    expected=rebuild(value,records,bodies)
    need(all(canonical(manifest[k])==canonical(v) for k,v in expected.items()),'Diagnostic source reconstruction')
    need(manifest['accounting']==dict(measured_response_bytes=measured,safety_accounted_bytes=accounted,
        unknown_transfer_upper_bytes=accounted-measured,wire_bytes=None,retries=0,provider_cost_usd=0),'Diagnostic aggregate accounting')
    return freeze(manifest)
