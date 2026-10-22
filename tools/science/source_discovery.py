"""Evaluator-only publisher routing; candidates never become clinical evidence."""
from __future__ import annotations
import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit

from asof.serde import ContractError,read_json,sha256_file
from tools.science.source_retrieval import public_url,trial_id,triage_hits


def require(condition,message):
    if not condition:raise ContractError(message)


def official_links(html,base_url,allowed_hosts):
    """Only actual anchor hrefs can authenticate an explicit publisher link."""
    require(isinstance(html,str),'HTML text required')
    require(isinstance(allowed_hosts,list) and all(isinstance(h,str) for h in allowed_hosts),'Approved hosts required')
    public_url(base_url,[urlsplit(base_url).hostname])
    links=set()
    class Anchors(HTMLParser):
        def handle_starttag(self,tag,attrs):
            if tag.lower()!='a':return
            hrefs=[value for key,value in attrs if key.lower()=='href']
            if len(hrefs)!=1 or not isinstance(hrefs[0],str):return
            href=hrefs[0]
            if href!=href.strip() or any(ord(c)<32 for c in href):return
            url=urljoin(base_url,href)
            try:public_url(url,allowed_hosts)
            except (ContractError,ValueError):return
            links.add(url)
    parser=Anchors(convert_charrefs=True);parser.feed(html);parser.close()
    return sorted(links)


def candidate_routes(nct,items,routes):
    """A pinned publisher/path and report terms justify a bounded fetch only.

    Missing NCT in a snippet is allowed here: exact document identity still needs
    original bytes or a separately reviewed authoritative trial-document bridge.
    """
    trial_id(nct);triage=triage_hits(nct,items)
    require(isinstance(routes,list),'Frozen routes required')
    seen=set()
    for route in routes:
        require(isinstance(route,dict),'Invalid route')
        rid=route.get('route_id');host=route.get('host');prefix=route.get('path_prefix');terms=route.get('required_terms')
        require(isinstance(rid,str) and rid and rid not in seen,'Unique route ID required');seen.add(rid)
        require(isinstance(host,str),'Exact publisher host required');public_url('https://'+host+'/',[host])
        require(isinstance(prefix,str) and prefix.startswith('/') and not any(c in prefix for c in ('?','#','\\','%'))
            and not any(c.isspace() for c in prefix) and all(p not in ('.','..') for p in prefix.split('/')),'Unsafe frozen path prefix')
        require(isinstance(terms,list) and terms and all(isinstance(t,str) and t.strip()==t and t for t in terms),'Report identity terms required')
        require(isinstance(route.get('bridge_sha256'),str) and re.fullmatch('[0-9a-f]{64}',route['bridge_sha256']),
            'Frozen publisher bridge commitment required')
    candidates=[]
    for index,item in enumerate(items):
        url=item.get('url','');content='\n'.join(item.get(k,'') for k in ('title','url','excerpt')).casefold()
        for route in routes:
            try:public_url(url,[route['host']])
            except (ContractError,ValueError):continue
            path=urlsplit(url).path;prefix=route['path_prefix']
            boundary=path==prefix or path.startswith(prefix if prefix.endswith('/') else prefix+'/')
            if not boundary or not all(term.casefold() in content for term in route['required_terms']):continue
            candidates.append({'nct_id':nct,'item_index':index,'route_id':route['route_id'],'url':url,
                'bridge_sha256':route['bridge_sha256'],'status':'official_candidate_unverified',
                'exact_nct_in_return':triage[index]['exact_requested_identifier_observed'],
                'item_content_sha256':triage[index]['item_content_sha256'],
                'primary_document_identity_qualified':False,'clinical_scope_qualified':False,
                'historical_availability_qualified':False,'clinical_label_contribution':False})
    return candidates


def qualify_original(nct,candidate,receipt,expected_sha256,output_root):
    """Recheck physical bytes; a different official copy still needs review."""
    trial_id(nct)
    require(isinstance(candidate,dict) and candidate.get('status')=='official_candidate_unverified','Unverified candidate required')
    require(isinstance(candidate.get('bridge_sha256'),str) and re.fullmatch('[0-9a-f]{64}',candidate['bridge_sha256']),
        'Publisher bridge commitment required')
    require(candidate.get('nct_id')==nct and receipt.get('nct_id')==nct,'Trial identity mismatch')
    require(candidate.get('url')==receipt.get('requested_url'),'Receipt is for a different candidate URL')
    require(receipt.get('http_status')==200,'Successful original response required')
    require(isinstance(expected_sha256,str) and re.fullmatch('[0-9a-f]{64}',expected_sha256),'Expected original commitment required')
    body=receipt.get('body');require(isinstance(body,dict),'Original body receipt required')
    root=Path(output_root).resolve();path=Path(body.get('path','')).resolve()
    control_path=root/'control.json';receipt_path=root/'receipt.json'
    require(control_path.is_file() and receipt_path.is_file(),'Retained control and receipt required')
    require(sha256_file(control_path)==receipt.get('control_sha256'),'Physical control differs from admitted receipt')
    require(read_json(receipt_path)==receipt,'Supplied receipt differs from retained receipt')
    control=read_json(control_path)
    require(control.get('nct_id')==nct and control.get('url')==candidate['url'],'Control differs from requested candidate')
    public_url(candidate['url'],control.get('allowed_hosts',[]))
    public_url(receipt.get('response_url'),control.get('allowed_hosts',[]))
    require(path.is_relative_to(root) and path!=root and path.is_file(),'Original outside approved output root')
    require(type(body.get('bytes')) is int and 0<body['bytes']<=16*1024*1024 and path.stat().st_size==body['bytes'],
        'Original byte count differs from receipt or exceeds bound')
    with path.open('rb') as stream:
        signature=stream.read(5);stream.seek(0);digest=hashlib.file_digest(stream,'sha256').hexdigest()
    require(signature==b'%PDF-' and digest==body.get('sha256'),'Original bytes or PDF signature differ from receipt')
    exact=digest==expected_sha256
    return {'nct_id':nct,'status':'exact_original_identity' if exact else 'different_bytes_requires_review',
        'body_sha256':digest,'expected_sha256':expected_sha256,'primary_document_identity_qualified':exact,
        'identity_basis':'Frozen original byte commitment with externally retained trial-document proof' if exact else None,
        'clinical_scope_qualified':False,'historical_availability_qualified':False,'clinical_label_contribution':False,
        'different_bytes_are_not_automatically_a_mirror':True}
