"""Evaluator-only exact-ID triage and bounded public-original transport.

Discovery, document identity, historical availability and clinical qualification are
separate. An identifier in a paper or a successful GET qualifies none of the latter.
"""
from __future__ import annotations

from datetime import datetime,timezone
import copy
import hashlib
import ipaddress
import re
import time
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

from asof.serde import ContractError,write_json
from asof.journal import RunJournal

NCT=re.compile(r'(?<![A-Za-z0-9_])NCT[0-9]{8}(?![A-Za-z0-9_])',re.I)
SAFE_HEADERS={'date','last-modified','etag','content-type','content-length','content-disposition','cache-control','location'}


def require(condition,message):
    if not condition:raise ContractError(message)


def trial_id(value):
    require(isinstance(value,str) and re.fullmatch(r'NCT[0-9]{8}',value) is not None,'Exact canonical NCT identifier required')
    return value


def triage_hits(nct,items):
    """Never inspect query labels as evidence of a returned item's identity."""
    trial_id(nct);require(isinstance(items,list),'Result items must be an array')
    decisions=[]
    for index,item in enumerate(items):
        require(isinstance(item,dict) and all(isinstance(item.get(k,''),str) for k in ('title','url','excerpt')),
            'Invalid discovery item')
        content='\n'.join(item.get(k,'') for k in ('title','url','excerpt'))
        identifiers=sorted({m.group().upper() for m in NCT.finditer(content)})
        hit=nct in identifiers
        decisions.append({'index':index,'exact_requested_identifier_observed':hit,'observed_nct_ids':identifiers,
            'status':'candidate_identifier_hit_unverified' if hit else 'rejected_no_exact_identifier',
            'item_content_sha256':hashlib.sha256(content.encode()).hexdigest(),
            'primary_document_identity_qualified':False,'historical_availability_qualified':False,
            'clinical_label_contribution':False})
    return decisions


def registry_document_refs(nct,payload):
    """Project document links from the observed v2 format, with no results payload."""
    trial_id(nct);require(isinstance(payload,dict),'Registry payload required')
    protocol=payload.get('protocolSection',{})
    require(isinstance(protocol,dict),'Invalid protocol section')
    identification=protocol.get('identificationModule',{})
    require(isinstance(identification,dict),'Invalid identification module')
    require(identification.get('nctId')==nct,'Registry resource identity differs from requested trial')
    section=payload.get('documentSection')
    require(section is None or isinstance(section,dict),'Invalid document section')
    module=(section or {}).get('largeDocumentModule')
    require(module is None or isinstance(module,dict),'Invalid document module')
    docs=(module or {}).get('largeDocs',[])
    require(isinstance(docs,list) and len(docs)<=100,'Invalid or oversized document listing')
    refs=[];seen=set()
    for doc in docs:
        require(isinstance(doc,dict),'Invalid document reference')
        require(all(doc.get(k) is None or isinstance(doc[k],str) for k in ('date','uploadDate','label','typeAbbrev')),
            'Document descriptive fields must be strings or null')
        require(all(doc.get(k) is None or type(doc[k]) is bool for k in ('hasProtocol','hasSap','hasIcf')),
            'Document flags must be booleans or null')
        filename=doc.get('filename')
        require(isinstance(filename,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*\.pdf',filename) is not None,
            'Unapproved document filename')
        require(filename not in seen,'Duplicate document reference');seen.add(filename)
        size=doc.get('size');require(size is None or type(size) is int and size>0,'Invalid reported document size')
        refs.append({'nct_id':nct,'filename':filename,'url':f'https://cdn.clinicaltrials.gov/large-docs/{nct[-2:]}/{nct}/{filename}',
            'source_json_pointer':'/documentSection/largeDocumentModule/largeDocs/'+str(len(refs)),
            'source_reported_date':doc.get('date'),'source_reported_upload_date':doc.get('uploadDate'),
            'reported_bytes':size,'label':doc.get('label'),'document_type':doc.get('typeAbbrev'),
            'has_protocol':doc.get('hasProtocol'),'has_sap':doc.get('hasSap'),'has_icf':doc.get('hasIcf'),
            'identity_basis':'linked_from_exact_registry_identificationModule.nctId',
            'original_document_bytes_checked':False,'historical_availability_qualified':False,
            'clinical_scope_qualified':False,'clinical_label_contribution':False})
    return {'nct_id':nct,'role':'evaluation_only','temporal_classification':'contemporary_only',
        'document_refs':refs,'listing_presence':'listed' if docs else 'not_listed_in_supplied_current_payload',
        'absence_claim':False,'clinical_label_contribution':False}


def public_url(url,allowed_hosts):
    require(isinstance(url,str) and not any(c.isspace() for c in url),'Invalid public URL')
    try:
        parts=urllib.parse.urlsplit(url);host=parts.hostname;port=parts.port
    except ValueError as error:raise ContractError('Invalid public URL authority') from error
    require(host is not None and '.' in host and not host.endswith('.') and host!='localhost','Public provider hostname required')
    try:ipaddress.ip_address(host)
    except ValueError:pass
    else:raise ContractError('Literal IP endpoints are not approved public providers')
    require(parts.scheme=='https' and host in allowed_hosts and not parts.username and not parts.password and
        port in (None,443) and not parts.fragment and not parts.query,'URL outside frozen HTTPS host policy')
    return url


class BoundRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self,hosts,deadline=None):self.hosts=hosts;self.redirects=0;self.deadline=deadline
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        require(self.deadline is None or time.monotonic()<=self.deadline,'Retrieval elapsed budget exceeded')
        self.redirects+=1;require(self.redirects<=5,'Redirect bound exceeded')
        public_url(newurl,self.hosts)
        return super().redirect_request(request,fp,code,msg,headers,newurl)


def fetch_control(control,output,*,open_response=None):
    """One attempt, exclusive output, capped original bytes and sanitized receipt.

    open_response is an injected response factory for offline transport regressions.
    No response can qualify a historical version, trial scope or clinical endpoint.
    """
    output=Path(output).resolve();journal=RunJournal(output,kind='build');stage='control'
    try:
        control=copy.deepcopy(control)
        seconds=control.get('max_elapsed_seconds',120);timeout=control.get('request_timeout_seconds',40)
        require(type(seconds) is int and 1<=seconds<=120 and type(timeout) is int and 1<=timeout<=40,'Invalid transport time bounds')
        started=time.monotonic();deadline=started+seconds
        nct=trial_id(control['nct_id']);url=control['url'];hosts=control['allowed_hosts']
        require(isinstance(hosts,list) and hosts and all(isinstance(h,str) and h for h in hosts),'Frozen hosts required')
        public_url(url,hosts)
        cap=control['max_bytes'];require(type(cap) is int and 1<=cap<=16*1024*1024,'Invalid original byte bound')
        expected=control.get('expected_sha256')
        require(expected is None or isinstance(expected,str) and re.fullmatch('[0-9a-f]{64}',expected),'Invalid original commitment')
        write_json(output/'control.json',control)
        control_sha=hashlib.sha256((output/'control.json').read_bytes()).hexdigest()
        journal.append('build_stage',stage=stage,url=url,nct_id=nct,automatic_retry=False)
        request=urllib.request.Request(url,headers={'User-Agent':'AsOf-source-readiness/0.1','Accept-Encoding':'identity'})
        if open_response is None:
            opener=urllib.request.build_opener(BoundRedirect(hosts,deadline))
            def open_response(request):
                try:return opener.open(request,timeout=timeout)
                except urllib.error.HTTPError as response:return response
        with open_response(request) as response:
            final_url=response.geturl();public_url(final_url,hosts)
            status=response.status;headers={k:v for k,v in response.headers.items() if k.lower() in SAFE_HEADERS}
            length=response.headers.get('Content-Length')
            require(length is None or isinstance(length,str) and length.isdecimal() and int(length)<=cap,'Original Content-Length exceeds bound or is malformed')
            digest=hashlib.sha256();total=0;first=b'';partial=output/'body.partial'
            with partial.open('xb') as stream:
                while True:
                    require(time.monotonic()<=deadline,'Retrieval elapsed budget exceeded')
                    chunk=response.read(min(64*1024,cap-total+1))
                    require(time.monotonic()<=deadline,'Retrieval elapsed budget exceeded')
                    if not chunk:break
                    require(total+len(chunk)<=cap,'Original response exceeds explicit byte bound')
                    if not first:first=chunk[:16]
                    stream.write(chunk);digest.update(chunk);total+=len(chunk)
            require(length is None or int(length)==total,'Original response length differs from header')
        body=output/'body.original';partial.rename(body)
        match=(digest.hexdigest()==expected) if expected else None
        pdf_ok=first.startswith(b'%PDF-') if control.get('expected_format')=='pdf' else None
        require(hashlib.sha256((output/'control.json').read_bytes()).hexdigest()==control_sha,'Control bytes changed during retrieval')
        result={'schema_version':1,'status':'original_received' if status==200 else 'http_access_failure',
            'role':'evaluation_only','nct_id':nct,'requested_url':url,'response_url':final_url,'http_status':status,
            'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'response_headers':headers,
            'header_filter':'Provenance allowlist; cookies and authentication headers excluded.',
            'body':{'path':str(body),'sha256':digest.hexdigest(),'bytes':total},
            'expected_sha256':expected,'matches_retained_original':match,'pdf_signature_matches':pdf_ok,
            'control_sha256':control_sha,
            'transport_control_passed':status==200 and match is True and pdf_ok is not False,
            'historical_availability_qualified':False,'clinical_scope_qualified':False,'clinical_label_contribution':False,
            'automatic_retry':False,'provider_spend_usd':0}
        result['elapsed_seconds']=time.monotonic()-started
        write_json(output/'receipt.json',result)
        journal.append('build_completed',receipt_sha256=hashlib.sha256((output/'receipt.json').read_bytes()).hexdigest())
        return result
    except BaseException as error:
        journal.fail(error,stage);write_json(output/'failure.json',{'stage':stage,'error_class':type(error).__name__,
            'message':str(error),'automatic_retry':False});raise
    finally:journal.close()
