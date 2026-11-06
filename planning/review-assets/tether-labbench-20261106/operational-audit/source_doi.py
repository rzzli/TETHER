"""Posthoc explicit-DOI source diagnostic; stdlib only, no scoring or network.

Does not import production normalization, retrieval, projection or evaluation.
Read sizes follow actual fstat size in the unchanged independent audit helper.
"""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from urllib.parse import unquote,urlsplit
import xml.etree.ElementTree as ET

helper=Path(__file__).with_name('audit.py')
if hashlib.sha256(helper.read_bytes()).hexdigest()!='700ab30f03c9c61f7c8dc4dd7b39c75bb956de350d2ec10f9314025c52e5b392':raise ValueError('Independent helper changed')
spec=importlib.util.spec_from_file_location('independent_operational_v1',helper)
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
ROOT=A.ROOT
ORIGINAL_SHA='e0c988a473cd54668fd743970ea0f226861f17fb0dff4894db35d17b43993fac'
PROVENANCE_SHA='98cf6f138acdd122eb86daa46c439562ae5c1feac152a1e3cfe16dee4b8c470b'
GENERATION_SEAL='46acaabedd04b0f9a2410f8620f13f19f9927e5e6fc1d0437d8b29bc63cd8447'
COLLECTION_SHA='b75558de8fca5382729e42d7bd6adc9efabdb072791b0d75201aaff2280c47de'
PREPARATION_SHA='7c085ccf94f0e3e3270727efbc3b250e43ac52168aad009ee362662fbd58122b'
ACQUISITION_SHA='620cf7d9d166d892b8c33da9a3f6a896d0c8d3659bbc10b4b6144fcadcd723bd'


def doi(value):
    """Explicit DOI syntax only; no publisher-path, PMID or paper inference."""
    if not isinstance(value,str):return None
    text=value.strip()
    if text.lower().startswith('doi:'):text=text[4:].strip()
    if text.lower().startswith(('https://','http://')):
        try:url=urlsplit(text)
        except ValueError:return None
        if url.hostname is None or url.hostname.lower() not in {'doi.org','dx.doi.org','www.doi.org'} or url.username or url.password:return None
        text=unquote(url.path[1:] if url.path.startswith('/') else url.path)
    if re.fullmatch(r'10\.[0-9]{4,9}/[^\s]+',text) is None:return None
    return text.lower()


def xml_dois(raw):
    A.need(len(raw)<=2*1024**2 and b'<!ENTITY' not in raw.upper(),'Unsupported XML size/entity declaration')
    root=ET.fromstring(raw)
    for node in root.iter():node.tag=node.tag.rsplit('}',1)[-1]
    result=set()
    for node in root.findall('./front/article-meta/article-id'):
        if node.attrib.get('pub-id-type','').lower()=='doi':
            value=doi(''.join(node.itertext()))
            if value is not None:result.add(value)
    return result


def unresolved_kind(value):
    text=value.strip().lower()
    if 'pubmed.ncbi.nlm.nih.gov' in text or text.startswith('pmid:'):return 'pmid_not_resolved'
    if 'pmc' in text and ('ncbi.nlm.nih.gov' in text or text.startswith(('pmc','pmcid:'))):return 'pmcid_not_resolved'
    if text.startswith(('http://','https://')):return 'publisher_or_other_url_not_resolved'
    return 'other_not_resolved'


def compare(annotations,documents,selected):
    A.need(isinstance(annotations,list) and all(isinstance(value,str) for value in annotations),'Invalid source annotation array')
    gold={doi(value) for value in annotations}-{None}
    ids=[doc['id'] for doc in documents];A.need(len(set(ids))==len(ids) and selected<=set(ids),'Unknown/duplicate selected article')
    sets={name:set() for name in ('retained_metadata','selected_metadata','retained_xml','selected_xml','retained_nonconflicting','selected_nonconflicting')}
    conflicts=[];missing_metadata=missing_xml=0
    for doc in documents:
        metadata=set(doc['metadata_dois']);xml=set(doc['xml_dois']);both=metadata|xml
        missing_metadata+=not bool(metadata);missing_xml+=not bool(xml)
        sets['retained_metadata'].update(metadata);sets['retained_xml'].update(xml)
        if doc['id'] in selected:sets['selected_metadata'].update(metadata);sets['selected_xml'].update(xml)
        if len(both)>1:conflicts.append(doc['id'])
        else:
            sets['retained_nonconflicting'].update(both)
            if doc['id'] in selected:sets['selected_nonconflicting'].update(both)
    result={'annotation_value_count':len(annotations),'annotated_dois':sorted(gold),'annotated_doi_count':len(gold),
        'unresolved_annotation_value_count':sum(doi(value) is None for value in annotations),
        'unresolved_annotation_types':dict(Counter(unresolved_kind(value) for value in annotations if doi(value) is None)),
        'retained_article_count':len(documents),'selected_article_count':len(selected),'metadata_missing_article_count':missing_metadata,
        'xml_missing_article_count':missing_xml,'conflicting_article_count':len(conflicts),'conflicting_article_ids':conflicts}
    for name,values in sets.items():
        result[name+'_dois']=sorted(values);result[name+'_hit_dois']=sorted(gold&values);result[name+'_hit_count']=len(gold&values)
    return result


def checked(path,expected,cap=2*1024**2):
    raw=A.read(path,cap);A.need(A.sha(raw)==expected,'External input anchor mismatch: '+str(path));return raw


def annotation_rows(payload):
    rows=[]
    for line in payload.splitlines(keepends=True):
        native=A.parse(line);rows.append({key:native[key] for key in ('id','question','sources')}|{'raw_line_sha256':A.sha(line)})
    return rows


def run():
    # This externally anchored gate executes before original source annotations.
    generation=ROOT/'data/benchmark/labbench/generation-20261106T011303Z-attempt01'
    checked(generation/'SEALED.json',GENERATION_SEAL,8*1024**2)
    prior=Path(__file__).with_name('GENERATION-FINAL-03.json')
    operational=A.parse(checked(prior,'abcd5878cb83f1e7e481239e347952c9ae207ef47cf373d59977af3f69810576'))
    A.need(operational['generation']['status']=='PASS' and operational['generation']['generation_sealed_sha256']==GENERATION_SEAL,'Independent generation audit did not pass')
    original_root=ROOT/'data/raw/labbench_public/20261106-attempt01'
    preparation=ROOT/'data/benchmark/labbench/preparation-20261106-attempt02'
    collection_root=ROOT/'data/benchmark/labbench/collection-20261106T011303Z-attempt01'
    receipt=A.parse(checked(original_root/'acquisition.json',ACQUISITION_SHA))
    prepared=A.parse(checked(preparation/'manifest.json',PREPARATION_SHA))
    provenance=A.parse(checked(preparation/'provenance.json',PROVENANCE_SHA))
    A.need(prepared['products']['provenance']['sha256']==PROVENANCE_SHA and prepared['acquisition_receipt_sha256']==ACQUISITION_SHA,'Projection provenance anchor differs')
    original_name='github/LitQA2/litqa-v2-public.jsonl'
    parent=[row for row in receipt['files'] if row['path']==original_name]
    A.need(len(parent)==1 and parent[0]['sha256']==ORIGINAL_SHA and parent[0]['status']==200,'Original acquisition identity differs')
    original=checked(A.child(original_root,original_name),ORIGINAL_SHA)
    A.need(len(original)==parent[0]['bytes']==200640,'Original physical size differs')
    # Mixed original containers are evaluator-only. Immediately retain only
    # id/question/sources plus locator proofs; no ideal/distractor/key-passage use.
    rows=annotation_rows(original)
    collection=A.parse(checked(collection_root/'manifest.json',COLLECTION_SHA,8*1024**2))
    queries=A.parse(A.read_proof(collection_root,collection['queries']))
    ids=[row['id'] for row in rows]
    A.need(len(ids)==len(set(ids))==199 and ids==collection['schedule']==[row['id'] for row in queries]
           and len(provenance)==len(collection['cases'])==199,'Source diagnostic changed all199 schedule')
    results=[];source_proofs=[];document_identities={};xml_cache={}
    for ordinal,(row,query,source_case,origin) in enumerate(zip(rows,queries,collection['cases'],provenance)):
        A.need(origin['id']==row['id'] and origin['row_1based']==ordinal+1 and origin['raw_line_sha256']==row['raw_line_sha256']
            and origin['original_fields']['sources']==row['sources'] and origin['original_fields']['question']==row['question']==query['question']
            and origin['query_sha256']==A.sha(A.canonical(query)),'Original annotation/provenance/query join differs')
        A.need(source_case['id']==row['id'] and source_case['ordinal']==ordinal,'Source case order differs')
        docs=[];selected_ids=set()
        if source_case['status']=='completed':
            source_root=A.child(collection_root,source_case['retrieval']['path'])
            manifest=A.parse(checked(source_root/'manifest.json',source_case['retrieval']['manifest_sha256'],8*1024**2))
            packet=A.parse(A.read_proof(collection_root,source_case['selected']))
            selected_ids={binding['document_id'] for binding in packet['bindings']}
            request_by_id={request['request_id']:request for request in manifest['requests']};search_cache={}
            for source in manifest['sources']:
                discovery=request_by_id[source['discovery_request_id']]
                if discovery['request_id'] not in search_cache:
                    search_cache[discovery['request_id']]=A.parse(A.read_proof(source_root,{'path':discovery['body_path'],
                        'sha256':discovery['body_sha256'],'bytes':discovery['bytes']},cap=1024**2))
                record=search_cache[discovery['request_id']]['resultList']['result'][source['discovery_rank']]
                A.need(record['pmcid']==source['source_id'] and record.get('doi')==source['doi'],'Retained metadata differs from original discovery row')
                proof=source['original'];payload=A.read_proof(source_root,proof,cap=2*1024**2)
                if proof['sha256'] not in xml_cache:xml_cache[proof['sha256']]=xml_dois(payload)
                metadata=doi(source['doi']);xml=xml_cache[proof['sha256']]
                doc={'id':source['source_id'],'metadata_dois':[] if metadata is None else [metadata],'xml_dois':sorted(xml)}
                docs.append(doc);document_identities.setdefault(doc['id'],set()).add((metadata,tuple(sorted(xml))))
                source_proofs.append({'task_id':row['id'],'document_id':source['source_id'],'original_path':str(source_root/proof['path']),
                    'original_sha256':proof['sha256'],'bytes':len(payload),'discovery_body_sha256':discovery['body_sha256'],
                    'discovery_rank_zero_based':source['discovery_rank'],'selected':source['source_id'] in selected_ids})
        result=compare(row['sources'],docs,selected_ids)
        results.append({'id':row['id'],'row_1based':ordinal+1,'raw_line_sha256':row['raw_line_sha256'],**result})
    counts=Counter();unresolved=Counter()
    numeric=('annotation_value_count','annotated_doi_count','unresolved_annotation_value_count','retained_article_count','selected_article_count',
        'metadata_missing_article_count','xml_missing_article_count','conflicting_article_count')
    methods=('retained_metadata','selected_metadata','retained_xml','selected_xml','retained_nonconflicting','selected_nonconflicting')
    for result in results:
        counts.update({key:result[key] for key in numeric});unresolved.update(result['unresolved_annotation_types'])
    metrics={method:{'hit_doi_pairs':sum(row[method+'_hit_count'] for row in results),'annotated_doi_pairs':counts['annotated_doi_count'],
        'hit_questions':sum(row[method+'_hit_count']>0 for row in results),'scheduled_questions':199} for method in methods}
    for metric in metrics.values():
        metric['doi_identifier_recall']=metric['hit_doi_pairs']/metric['annotated_doi_pairs'] if metric['annotated_doi_pairs'] else None
        metric['doi_hit_per_all_scheduled']=metric['hit_questions']/199
    return {'schema_version':1,'status':'PASS','kind':'independent_posthoc_explicit_doi_source_diagnostic',
        'created_at_utc':datetime.now(timezone.utc).isoformat(),'analyzer_sha256':A.sha(A.read(__file__)),
        'anchors':{'original_jsonl_sha256':ORIGINAL_SHA,'provenance_sha256':PROVENANCE_SHA,'preparation_manifest_sha256':PREPARATION_SHA,
            'acquisition_receipt_sha256':ACQUISITION_SHA,'collection_manifest_sha256':COLLECTION_SHA,'generation_sealed_sha256':GENERATION_SEAL},
        'counts':dict(counts),'metrics':metrics,'unresolved_annotation_types':dict(unresolved),
        'questions_without_explicit_doi':sum(row['annotated_doi_count']==0 for row in results),
        'distinct_annotated_dois':len({value for row in results for value in row['annotated_dois']}),
        'unique_retained_pmcids':len(document_identities),'pmcids_with_different_observed_doi_sets':sum(len(values)>1 for values in document_identities.values()),
        'cases':results,'source_proofs':source_proofs,'candidate_scoring':False,'network_calls':0,
        'interpretation':['Explicit DOI syntax diagnostic, not semantic support or literature recall',
            'All syntactically recognized DOI annotations remain in each-question denominator, including absent retrieval metadata',
            'Bare DOI, doi prefix and DOI resolver URL accepted; PMID, PMCID and publisher aliases are deliberately unresolved',
            'Metadata and XML article-front identifiers reported separately; citation DOIs are excluded; conflicting article DOI unions excluded from combined view',
            'Repeated questions/articles are not independent observations; DOI-pair counts are per-question sets',
            'Mixed original/provenance bytes inspected only after generation seal; ideal, distractors and key-passage not evaluated',
            'This subset diagnostic is not the production all-identifier alias-graph method']}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    result=run()
    with Path(args.output).open('xb') as stream:stream.write(A.canonical(result)+b'\n')
    print(json.dumps({key:result[key] for key in ('status','counts','metrics','unresolved_annotation_types','questions_without_explicit_doi')}))
