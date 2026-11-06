"""Evaluator-only LitQA2 aggregation after generation has been sealed.

No retrieval or model calls are made here. Native scoring and source-identity
alignment are distinct; annotation identity is not semantic entailment.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import datetime,timezone
import hashlib
import os
from pathlib import Path
import re
import time
from urllib.parse import unquote, urlsplit

from asof.atomic import publish_bytes
from asof.journal import RunJournal
from asof.serde import ContractError, canonical, decode, encode, fingerprint, freeze, parse_json, safe_child


def _need(value,message):
    if not value:
        raise ContractError(message)


def normalize_identifier(value):
    """Recognize explicit DOI/PMID/PMCID syntax, without a network lookup.

    An arbitrary publisher URL is unresolved. Normalization does not establish
    that a syntactically valid identifier exists or that two aliases coincide.
    """
    if not isinstance(value,str) or not value.strip():
        return None
    text=value.strip()
    if text.casefold().startswith('doi:'):
        text=text[4:].strip()
    match=re.fullmatch(r'10\.[0-9]{4,9}/[^\s]+',text,re.IGNORECASE)
    if match:
        return 'doi:'+text.casefold()
    match=re.fullmatch(r'(?:pmid:)([0-9]{1,12})',text,re.IGNORECASE)
    if match and int(match[1])>0:
        return 'pmid:'+str(int(match[1]))
    match=re.fullmatch(r'(?:pmcid:)?PMC([0-9]{1,12})',text,re.IGNORECASE)
    if match and int(match[1])>0:
        return 'pmcid:PMC'+str(int(match[1]))
    try:
        url=urlsplit(text)
    except ValueError:
        return None
    if url.scheme not in ('http','https') or url.username or url.password:
        return None
    host=(url.hostname or '').casefold()
    path=unquote(url.path)
    if host in ('doi.org','dx.doi.org','www.doi.org'):
        return normalize_identifier(path.lstrip('/'))
    if host in ('pubmed.ncbi.nlm.nih.gov','www.ncbi.nlm.nih.gov','ncbi.nlm.nih.gov','europepmc.org','www.europepmc.org'):
        match=re.fullmatch(r'/(?:pubmed/|article/MED/)?([0-9]{1,12})/?',path)
        if match:
            return normalize_identifier('pmid:'+match[1])
    if host in ('pmc.ncbi.nlm.nih.gov','www.ncbi.nlm.nih.gov','ncbi.nlm.nih.gov','europepmc.org','www.europepmc.org'):
        match=re.fullmatch(r'/(?:pmc/)?articles/(PMC[0-9]{1,12})/?',path,re.IGNORECASE)
        if match:
            return normalize_identifier(match[1])
    return None


class _Components:
    def __init__(self,values=()):
        self.parent={value:value for value in values}
    def find(self,value):
        self.parent.setdefault(value,value)
        if self.parent[value]!=value:
            self.parent[value]=self.find(self.parent[value])
        return self.parent[value]
    def union(self,left,right):
        left,right=self.find(left),self.find(right)
        if left!=right:
            self.parent[max(left,right)]=min(left,right)
    def groups(self):
        result={}
        for value in self.parent:
            result.setdefault(self.find(value),set()).add(value)
        return list(result.values())


def _record_ids(record):
    _need(isinstance(record,Mapping),'Bibliographic metadata must be objects')
    values=[]
    if record.get('doi') is not None:
        values.append(normalize_identifier(str(record['doi'])))
    if record.get('pmcid') is not None:
        values.append(normalize_identifier(str(record['pmcid'])))
    if record.get('source')=='MED' and record.get('id') is not None:
        values.append(normalize_identifier('pmid:'+str(record['id'])))
    return {value for value in values if value is not None}


def source_diagnostics(queries, annotations, retrieved_ids, bibliography):
    """Offline observed alignment; unresolved aliases never become extra papers.

    The main hit rate uses all scheduled questions. DOI recall includes every
    syntactically valid annotated DOI, even when absent from retained metadata.
    Conditional paper recall is explicitly selected by available metadata and
    must not be interpreted as complete annotation or literature recall.
    """
    _need(isinstance(queries,(list,tuple)) and queries,'Empty diagnostic schedule')
    ids=[row['id'] for row in queries]
    _need(len(set(ids))==len(ids) and set(annotations)==set(ids)==set(retrieved_ids),'Source diagnostic schedule mismatch')
    aliases=_Components()
    for record in bibliography:
        record_ids=sorted(_record_ids(record))
        for value in record_ids:
            aliases.find(value)
            aliases.union(record_ids[0],value)
    resolved,component_aliases={},{}
    conflict_aliases=set();conflicts=0
    for group in aliases.groups():
        dois=sorted(value for value in group if value.startswith('doi:'))
        if len(dois)>1:
            conflicts+=1;conflict_aliases.update(group)
            continue
        canonical=dois[0] if dois else sorted(group)[0]
        component_aliases[canonical]=group
        for value in group:resolved[value]=canonical
    links=_Components(ids)
    first_alias,first_paper,first_question,first_annotation={},{},{},{}
    counters=Counter()
    cases=[]
    for query in queries:
        key=query['id'];raw_annotations=annotations[key]
        _need(isinstance(raw_annotations,(list,tuple)) and all(isinstance(value,str) for value in raw_annotations),'Invalid annotation URL array')
        parsed=[normalize_identifier(value) for value in raw_annotations]
        gold={value for value in parsed if value is not None}
        got={normalize_identifier(value) for value in retrieved_ids[key]}
        _need(None not in got,'Retrieved identity is not an explicit supported identifier')
        expanded=set(got)
        for value in got:
            if value in resolved:expanded.update(component_aliases[resolved[value]])
        # Conflicted links are not treated as verified alias equivalences.
        gold_papers={resolved[value] for value in gold if value in resolved}
        got_papers={resolved[value] for value in got if value in resolved}
        doi_gold={value for value in gold if value.startswith('doi:')}
        doi_hits=doi_gold&{value for value in expanded if value.startswith('doi:')}
        identity_hits=(gold&expanded)-conflict_aliases
        paper_hits=gold_papers&got_papers
        has_annotations=bool(raw_annotations)
        hit=bool(identity_hits) if has_annotations else None
        unknown=sum(value is None for value in parsed)
        unresolved=gold-set(resolved)
        counters.update(scheduled=1,questions_with_annotations=has_annotations,hit_questions=hit is True,
            annotated_dois=len(doi_gold),hit_dois=len(doi_hits),resolved_papers=len(gold_papers),hit_papers=len(paper_hits),
            recognized_annotation_ids=len(gold),resolved_annotation_ids=len(gold)-len(unresolved),
            unresolved_annotation_ids=len(unresolved),unrecognized_annotation_values=unknown,
            questions_with_unresolved_annotations=bool(unresolved or unknown))
        for value in sorted(gold):
            if value in first_alias:links.union(key,first_alias[value])
            else:first_alias[value]=key
        # An identical unresolved URL is still a shared annotation pointer;
        # this conservative dependence edge does not add a paper to recall.
        for value in sorted({value.strip() for value in raw_annotations}):
            if value in first_annotation:links.union(key,first_annotation[value])
            else:first_annotation[value]=key
        for value in sorted(gold_papers):
            if value in first_paper:links.union(key,first_paper[value])
            else:first_paper[value]=key
        question=' '.join(query['question'].split())
        if question in first_question:links.union(key,first_question[question])
        else:first_question[question]=key
        cases.append({'id':key,'annotated_source_hit':hit,'annotation_value_count':len(raw_annotations),
            'recognized_annotation_id_count':len(gold),'unresolved_annotation_id_count':len(unresolved),
            'unrecognized_annotation_value_count':unknown,'annotated_doi_count':len(doi_gold),'hit_doi_count':len(doi_hits),
            'resolved_annotated_paper_count':len(gold_papers),'resolved_hit_paper_count':len(paper_hits)})
    groups=links.groups()
    component_by_id={}
    for members in groups:
        group_id=hashlib.sha256('\n'.join(sorted(members)).encode()).hexdigest()
        for key in members:component_by_id[key]=(group_id,len(members))
    for row in cases:
        row['component_id'],row['component_size']=component_by_id[row['id']]
    divide=lambda numerator,denominator:numerator/denominator if denominator else None
    return freeze({'primary':{'scheduled_count':len(ids),'questions_with_annotations':counters['questions_with_annotations'],
        'observed_annotated_source_hit_questions':counters['hit_questions'],
        'observed_annotated_source_hit_per_scheduled':counters['hit_questions']/len(ids),
        'interpretation':'Observed annotation-relative source-identity hit lower bound across all scheduled questions; unresolved does not mean absent literature'},
        'doi_identifier':{'annotated_doi_count':counters['annotated_dois'],'hit_doi_count':counters['hit_dois'],
            'recall':divide(counters['hit_dois'],counters['annotated_dois']),
            'denominator':'All distinct syntactically valid annotated DOIs per question, including ones absent from retrieved metadata'},
        'conditional_resolved_paper':{'annotated_paper_count':counters['resolved_papers'],'hit_paper_count':counters['hit_papers'],
            'recall':divide(counters['hit_papers'],counters['resolved_papers']),
            'selection_bias':'Resolution uses retained discovery metadata and is missing-not-at-random; this secondary conditional score can be perfect despite retrieval misses'},
        'resolution':{'recognized_annotation_ids':counters['recognized_annotation_ids'],'resolved_annotation_ids':counters['resolved_annotation_ids'],
            'unresolved_recognized_annotation_ids':counters['unresolved_annotation_ids'],'unrecognized_annotation_values':counters['unrecognized_annotation_values'],
            'questions_with_unresolved_annotations':counters['questions_with_unresolved_annotations'],
            'recognized_id_resolution_fraction':divide(counters['resolved_annotation_ids'],counters['recognized_annotation_ids']),
            'conflicting_alias_components':conflicts,'posthoc_network_calls':0},
        'grouping':{'components':len(groups),'component_sizes':sorted((len(group) for group in groups),reverse=True),
            'edges':'Shared normalized annotation identifier, identical annotation pointer, verified bibliographic alias component, or exact question after whitespace normalization',
            'residual_dependency':'Unknown; unresolved distinct identifiers are not asserted to represent independent papers'},
        'semantic_support':'unevaluated','case_results':cases})


def analytical_controls(choice_counts):
    _need(isinstance(choice_counts,(tuple,list)) and choice_counts and all(type(count) is int and 2<=count<=26 for count in choice_counts),'Invalid control choice counts')
    total=len(choice_counts)
    correct=sum(1/count for count in choice_counts)
    attempted=sum((count-1)/count for count in choice_counts)
    return freeze({'executed':False,'method':'Analytical expectations; no invented model or checker calls',
        'uniform_all_choices':{'expected_correct_count':correct,'expected_attempted_count':attempted,
            'expected_accuracy':correct/total,'expected_coverage':attempted/total,
            'ratio_of_expected_correct_to_expected_attempted':correct/attempted,
            'precision_caveat':'Ratio of expected counts, not the expectation of finite-sample random precision'},
        'uniform_substantive_choices':{'expected_accuracy':sum(1/(count-1) for count in choice_counts)/total,'coverage':1.0},
        'always_unsure':{'accuracy':0.0,'precision':0.0,'precision_defined':False,'coverage':0.0},
        'checked_controls':'Not computed; no simulated provenance admissions or model outputs'})


def _read_proof(root,proof,*,maximum=64*1024*1024):
    """Parse exactly the bounded captured bytes whose external proof is checked."""
    _need(isinstance(proof,Mapping) and {'path','sha256','bytes'}<=set(proof),'Missing evaluation input proof')
    path=safe_child(Path(root),proof['path'])
    _need(type(proof['bytes']) is int and 0<=proof['bytes']<=maximum,'Input byte bound exceeded')
    with path.open('rb') as stream:raw=stream.read(maximum+1)
    _need(len(raw)==proof['bytes'] and hashlib.sha256(raw).hexdigest()==proof['sha256'],'Evaluation input byte proof mismatch')
    return parse_json(raw)


def inspect_collected_sources(root,collection,queries):
    """Read captured discovery identities after collection verification.

    This helper receives no benchmark annotations. The returned metadata is
    used by the evaluator after candidates are sealed, never by the producer.
    Its sources are retained HTTP response bodies, not new posthoc searches.
    """
    _need(tuple(collection['schedule'])==tuple(query['id'] for query in queries),'Source inspection schedule mismatch')
    bibliography=[];retained={};selected={};proofs=[];coverage=[]
    _need(len(collection['cases'])==len(queries),'Source inspection omitted a task')
    for ordinal,(query,case) in enumerate(zip(queries,collection['cases'])):
        key=query['id'];retained[key]=[];selected[key]=[]
        _need(case['id']==key and case['ordinal']==ordinal,'Source inspection reordered cases')
        if case['status']!='completed':
            coverage.append({'id':key,'status':case['status'],'retained_articles':None,'selected_passages':None})
            continue
        retrieval_root=safe_child(Path(root),case['retrieval']['path'])
        with (retrieval_root/'manifest.json').open('rb') as stream:
            raw=stream.read(32*1024*1024+1)
        _need(len(raw)<=32*1024*1024 and hashlib.sha256(raw).hexdigest()==case['retrieval']['manifest_sha256'],'Source manifest anchor mismatch')
        manifest=parse_json(raw)
        for request in manifest['requests']:
            if request['kind']!='search' or request['status']!='completed' or not 200<=request['http_status']<300 or 'error_type' in request:
                continue
            proof={'path':request['body_path'],'sha256':request['body_sha256'],'bytes':request['bytes']}
            response=_read_proof(retrieval_root,proof,maximum=1024*1024)
            records=response.get('resultList',{}).get('result') if isinstance(response,Mapping) else None
            # Malformed metadata is a retained retrieval failure, not a source.
            if not isinstance(records,list) or len(records)>manifest.get('policy',{}).get('hits_per_query',10):continue
            for record in records:
                if isinstance(record,Mapping):
                    bibliography.append({field:record.get(field) for field in ('doi','pmcid','id','source')})
            proofs.append({'task_id':key,'root':str(retrieval_root),'proof':proof,'field':'resultList.result.[doi,pmcid,id,source]',
                           'role':'posthoc_bibliographic_identity_only'})
        retained[key]=['pmcid:'+source['source_id'] for source in manifest['sources']]
        packet=_read_proof(root,case['selected'])
        selected[key]=sorted({'pmcid:'+binding['document_id'] for binding in packet['bindings']})
        _need(set(selected[key])<=set(retained[key]),'Selected passage document is not retained')
        coverage.append({'id':key,'status':case['status'],'retained_articles':len(retained[key]),
            'selected_passages':len(packet['sources']),'selected_article_count':len(selected[key]),
            'selected_text_bytes':packet['coverage']['selected_text_bytes'],
            'available_text_bytes':packet['coverage']['available_text_bytes'],'retrieval_failures':len(manifest['failures']),
            'absence_of_evidence_claim':False})
    return freeze({'bibliography':bibliography,'retained_ids':retained,'selected_ids':selected,
        'inspection_provenance':proofs,'coverage':coverage,'posthoc_network_calls':0})


def _compare_recaptured_context(archived,recaptured):
    """Only mechanical re-capture time differs; input eligibility is rebuilt."""
    current=encode(recaptured)
    captured=decode(datetime,archived['captured_at_utc'])
    current['captured_at_utc']=archived['captured_at_utc']
    _need(len(current['snapshot']['sources'])==len(archived['snapshot']['sources']),'Context lineage cardinality differs')
    for new,old in zip(current['snapshot']['sources'],archived['snapshot']['sources']):
        if new['computed_at'] is not None:
            _need(decode(datetime,old['computed_at'])==captured,'Derived capture time contradicts archived context')
            new['computed_at']=old['computed_at']
    _need(canonical(current)==canonical(archived),'Source-inclusive context reconstruction differs')


def verify_case_pair(root,query,case,collection_root,collection_case,cutoff,model_provenance,configuration,alias,*,deadline):
    """Verify original source/request/native bytes before using any answer key."""
    from asof.study.session import verify_study
    from asof.study.stable_read import stable_files
    from . import model
    from .tether_adapter import capture_context,verify_candidate
    root=Path(root);row=case['disposition'];artifacts=case['artifacts']
    _need(row['id']==query['id']==case['id']==collection_case['id'],'Paired case identity differs')
    result={'id':query['id'],'producer_status':row['producer_status'],'check_status':row['check_status'],
            'paired_candidate_bytes':False,'source_inclusive_context':False,'generic_session_verification':None,
            'original_candidate_sha256':artifacts.get('candidate',{}).get('sha256')}
    supplied={}
    # Successful capture outputs are a coherent set, including when a later
    # tokenizer/generation failure prevented a candidate. Partial capture file
    # writes remain failed artifacts and are not promoted to valid evidence.
    names=('context','request','payload','sources')
    complete_context=all(name in artifacts for name in names)
    produced=row['producer_status']=='produced'
    _need(not produced or complete_context,'Produced case lacks source context')
    offered=[]
    context=None
    if complete_context:
        _need(collection_case['status']=='completed','Producer consumed incomplete source grant')
        paths=[safe_child(root,artifacts[name]['path']) for name in names]
        with stable_files(paths,deadline=deadline):
            supplied={name:_read_proof(root,artifacts[name]) for name in names}
            retrieval=collection_case['retrieval']
            context=capture_context(query,safe_child(Path(collection_root),retrieval['path']),retrieval['manifest_sha256'],
                cutoff,model_provenance,configuration,deadline=deadline)
            _compare_recaptured_context(supplied['context'],context.report)
            request,payload=model.make_request(query,context.sources,model_provenance,configuration)
            _need(canonical(request)==canonical(supplied['request']) and canonical(payload)==canonical(supplied['payload'])
                  and canonical(context.sources)==canonical(supplied['sources']),'Dispatched request/payload/source bytes differ from original capture')
            offered=[source['source_id'] for source in context.sources]
            result['source_inclusive_context']=True
    if produced:
        _need({'candidate','session_receipt','session_response','raw_response','session_configuration'}<=set(artifacts),'Produced case lacks native response/session proofs')
        receipt=_read_proof(root,artifacts['session_receipt'])
        session_root=safe_child(root,artifacts['session_receipt']['path']).parent
        session_paths=[session_root/'receipt.json',*[safe_child(session_root,name) for name in receipt['outputs']]]
        with stable_files(session_paths,deadline=deadline):
            verification=verify_study(session_root,expected_receipt_sha256=artifacts['session_receipt']['sha256'],
                                      verifier=model.MCQVerifier(model_alias=alias),deadline=deadline)
            response=_read_proof(root,artifacts['session_response'])
            candidate=_read_proof(root,artifacts['candidate'])
            session_request=_read_proof(session_root,{'path':'request.json',**receipt['outputs']['request.json']})
            session_configuration=_read_proof(root,artifacts['session_configuration'])
            _need(canonical(session_request)==canonical(supplied['request']),'Producer session/request join differs')
            _need(canonical(response)==canonical(candidate)==canonical(row['prediction']),'Raw and checked arms do not share the identical frozen native candidate')
            _need(session_configuration['caller_configuration']['source_context_sha256']==fingerprint(supplied['context']),
                  'Native session is not bound to the admitted source context')
            result['generic_session_verification']=verification
            decision=verify_candidate(context,supplied['request'],candidate)
            rebuilt=encode(decision);rebuilt['context_sha256']=fingerprint(supplied['context'])
            if row['check_status'] in ('accepted','rejected'):
                _need('decision' in artifacts,'Native admission disposition has no retained decision')
                original_decision=_read_proof(root,artifacts['decision'])
                _need(canonical(rebuilt)==canonical(original_decision),'Original native policy decision differs from replay')
                _need(row['check_status']==('accepted' if rebuilt['accepted'] else 'rejected') and row['reason']==rebuilt['reason'],
                      'Disposition contradicts original paired policy decision')
            elif 'decision' in artifacts:
                _need(canonical(rebuilt)==canonical(_read_proof(root,artifacts['decision'])),'Failed-check retained decision contradicts replay')
            result['paired_candidate_bytes']=True
    elif row['producer_status']=='parse_failure':
        _need(complete_context and 'raw_response' in artifacts,'Parse failure has no original bound response')
        raw_proof=artifacts['raw_response'];path=safe_child(root,raw_proof['path'])
        with path.open('rb') as stream:raw=stream.read(1024*1024+1)
        _need(len(raw)==raw_proof['bytes'] and hashlib.sha256(raw).hexdigest()==raw_proof['sha256'],'Malformed native output bytes differ')
        from asof.study import native
        native._native(raw,supplied['request'],supplied['payload'],alias)
        try:model.MCQVerifier(model_alias=alias).validate_response(supplied['request'],raw)
        except ContractError:pass
        else:raise ContractError('A valid native answer was mislabeled as parse failure')
    return freeze(result),tuple(offered)


def _verify_model_assets(manifest,*,deadline):
    """Hash model/runtime originals once; this does not start a server."""
    from asof.study.stable_read import hash_file,stable_files
    from . import model
    receipt=manifest['model_receipt'];limits=manifest['limits']
    spec,bindings,provenance=model.make_server_spec(receipt['path'],receipt['sha256'],port=limits['port'],
        alias=manifest['alias'],context_tokens=manifest['configuration']['context_tokens'],
        threads=limits['threads'],gpu_layers=limits['gpu_layers'])
    entries=(spec.executable,*spec.required_inputs)
    proofs=[]
    with stable_files(tuple(bindings.values()),deadline=deadline):
        for entry in entries:
            actual=hash_file(bindings[entry['logical_id']],deadline)
            _need(actual['sha256']==entry['sha256'] and actual['bytes']==entry['bytes'],'Pinned model/runtime original differs')
            proofs.append({'logical_id':entry['logical_id'],'path':str(bindings[entry['logical_id']]),**encode(actual)})
    return provenance,freeze(proofs)


def _publish(root,name,value):
    raw=canonical(value)+b'\n';publish_bytes(Path(root)/name,raw)
    return {'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}


def score_run(generation_root,expected_sealed_sha256,preparation_root,expected_preparation_manifest_sha256,
              output,*,deadline_seconds=3600):
    """Verify a sealed full schedule, then open references in this evaluator.

    A sealed partial run retains descriptive all-scheduled metrics and remains
    explicitly incomplete. A missing/changed generation seal blocks reference
    access. Output is reserved exclusively and failures are retained; no model,
    source retrieval, retries or repair are performed by this entry point.
    """
    from .run import verify_generation,source_pins
    from .collect import verify_collection
    from .data_views import verify_views
    from .evaluate import evaluate_schedule
    from .runtime import process_sample
    _need(type(deadline_seconds) in (int,float) and 0<deadline_seconds<=7200,'Invalid evaluation deadline')
    root=Path(output).absolute();journal=RunJournal(root,kind='build')
    started,cpu=time.monotonic(),time.process_time();deadline=started+deadline_seconds
    try:
        generation_root=Path(generation_root).absolute();preparation_root=Path(preparation_root).absolute()
        # This gate is intentionally before every preparation/reference read.
        generation=verify_generation(generation_root,expected_sealed_sha256)
        _need(canonical(generation['code_pins'])==canonical(source_pins()),'Executing evaluation code differs from generation freeze')
        _need(generation['mode'] in ('benchmark','fictional'),'Unknown generation population')
        if generation['mode']=='benchmark':_need(len(generation['schedule'])==199,'Incomplete benchmark schedule')
        journal.append('generation_seal_verified',root=str(generation_root),external_sealed_sha256=expected_sealed_sha256,
                       status=generation['status'],scheduled=len(generation['schedule']),verified_at_utc=datetime.now(timezone.utc).isoformat())
        queries=_read_proof(generation_root,generation['queries'],maximum=8*1024*1024)
        records=_read_proof(generation_root,generation['dispositions'])
        index=_read_proof(generation_root,generation['case_index'])
        _need(tuple(row['id'] for row in queries)==tuple(generation['schedule']) and len(index)==len(queries)==len(records),'Scheduled candidate count differs')
        collection_ref=generation['collection'];collection_root=Path(collection_ref['path'])
        collection=verify_collection(collection_root,collection_ref['manifest_sha256'],deadline=deadline,allow_partial=True)
        _need(tuple(collection['schedule'])==tuple(generation['schedule']) and collection['queries']['sha256']==generation['queries']['sha256'],
              'Collection/generation task views differ')
        model_provenance,model_proofs=_verify_model_assets(generation,deadline=deadline)
        paired=[];offered={}
        for ordinal,(query,case,col_case,record) in enumerate(zip(queries,index,collection['cases'],records)):
            _need(time.monotonic()<deadline,'Evaluation deadline exceeded')
            _need(case['ordinal']==ordinal and canonical(case['disposition'])==canonical(record),'Case index/disposition differs')
            pair,ids=verify_case_pair(generation_root,query,case,collection_root,col_case,collection['cutoff'],model_provenance,
                generation['configuration'],generation['alias'],deadline=deadline)
            paired.append(pair);offered[query['id']]=ids
            journal.append('paired_candidate_verified',id=query['id'],ordinal=ordinal,proof_sha256=fingerprint(pair))
        sources=inspect_collected_sources(collection_root,collection,queries)
        # All candidate proofs and policies have now been replayed without any
        # native answer key. Only this evaluator opens the mixed original view.
        journal.append('reference_access_started',preparation_root=str(preparation_root),
            external_manifest_sha256=expected_preparation_manifest_sha256,at_utc=datetime.now(timezone.utc).isoformat(),
            candidate_schedule_frozen=True,producer_reference_access=False)
        preparation=verify_views(preparation_root,expected_preparation_manifest_sha256)
        _need(preparation['products']['queries']['sha256']==generation['queries']['sha256'],'Reference preparation belongs to different tasks/permutations')
        references=_read_proof(preparation_root,preparation['products']['references'],maximum=8*1024*1024)
        provenance=_read_proof(preparation_root,preparation['products']['provenance'],maximum=8*1024*1024)
        _need(tuple(row['id'] for row in provenance)==tuple(generation['schedule']),'Reference provenance schedule differs')
        annotations={row['id']:row['original_fields']['sources'] for row in provenance}
        evaluation=evaluate_schedule(queries,references,records,evidence_ids_by_query=offered)
        fulltext=source_diagnostics(queries,annotations,sources['retained_ids'],sources['bibliography'])
        selected=source_diagnostics(queries,annotations,sources['selected_ids'],sources['bibliography'])
        controls=analytical_controls([len(query['choices']) for query in queries])
        groups={}
        native_by_id={row['id']:row for row in evaluation['case_results']}
        for row in fulltext['case_results']:
            group=groups.setdefault(row['component_id'],{'component_id':row['component_id'],'scheduled':0,'raw_correct':0,'correct_and_admitted':0})
            group['scheduled']+=1;group['raw_correct']+=native_by_id[row['id']]['raw_correct']
            group['correct_and_admitted']+=native_by_id[row['id']]['correct_and_admitted']
        input_provenance={'generation':{'root':str(generation_root),'external_sealed_sha256':expected_sealed_sha256},
            'collection':collection_ref,'preparation':{'root':str(preparation_root),'external_manifest_sha256':expected_preparation_manifest_sha256},
            'reference_products':{key:preparation['products'][key] for key in ('references','provenance')},
            'original_annotation_locators':[{'id':row['id'],'row_1based':row['row_1based'],'raw_line_sha256':row['raw_line_sha256'],
                'field':'sources','purpose':'evaluation_only_posthoc_source_alignment'} for row in provenance],
            'source_metadata_inspection':sources['inspection_provenance'],'model_input_proofs':model_proofs,
            'code_pins':generation['code_pins'],'posthoc_network_calls':0}
        resource_report={'generation_totals':generation['totals'],'generation_parent_resources':generation['parent_resources'],
            'generation_cleanup':generation['cleanup'],'collection_totals':collection['totals'],'collection_resources':collection['resources'],
            'evaluation_wall_seconds':time.monotonic()-started,'evaluation_cpu_seconds':time.process_time()-cpu,
            'evaluation_process_sample':process_sample(os.getpid()),'evaluation_memory_basis':'Current evaluator process lifetime peak, not incremental or GPU memory',
            'model_asset_unique_bytes_verified':sum(row['bytes'] for row in model_proofs),
            'model_asset_byte_basis':'Unique original model/runtime/receipt byte sizes; not physical I/O or transfer bytes',
            'provider_cost_usd':0,'new_model_calls':0,'new_retrieval_calls':0}
        report={'schema_version':1,'kind':'labbench_native_evaluation','status':'completed' if generation['status']=='completed' else 'descriptive_partial',
            'generation_status':generation['status'],'scheduled_count':len(queries),'raw_metrics':evaluation['raw_metrics'],
            'checked_metrics':evaluation['checked_metrics'],'counts':evaluation['counts'],'rates':evaluation['rates'],
            'metric_conventions':evaluation['metric_conventions'],'raw_precision_defined':evaluation['raw_precision_defined'],
            'checked_precision_defined':evaluation['checked_precision_defined'],'controls':controls,
            'retained_fulltext_alignment':{key:value for key,value in fulltext.items() if key!='case_results'},
            'selected_for_prompt_alignment':{key:value for key,value in selected.items() if key!='case_results'},
            'source_selection_interpretation':'Selected passages are frozen intended prompt inputs; unexecuted tasks do not imply the model received them',
            'group_outcomes':sorted(groups.values(),key=lambda row:row['component_id']),
            'scientific_validation':'Native answer-key agreement and identity alignment only; source entailment and clinical validity unevaluated',
            'reference_values_in_report':False,'paired_produced_candidates':sum(row['paired_candidate_bytes'] for row in paired),
            'resources':resource_report,'evaluation_created_at_utc':datetime.now(timezone.utc).isoformat()}
        products={}
        for name,value in [('evaluation.json',evaluation),('source-alignment.json',{'retained_fulltext':fulltext,'selected_for_prompt':selected}),
                           ('source-coverage.json',sources['coverage']),('paired-candidates.json',paired),
                           ('input-provenance.json',input_provenance),('resources.json',resource_report),('REPORT.json',report)]:
            products[name]=_publish(root,name,value)
        _need(time.monotonic()<deadline,'Evaluation finalization exceeded deadline')
        _need(canonical(generation['code_pins'])==canonical(source_pins()),'Source code changed during evaluation')
        journal.append('evaluation_completed',status=report['status'],scheduled=len(queries),products=products)
        journal_raw=(root/'journal.jsonl').read_bytes()
        seal={'schema_version':1,'kind':'labbench_native_evaluation','status':report['status'],'outputs':products,
            'journal_sha256':hashlib.sha256(journal_raw).hexdigest(),'input_anchors':input_provenance['generation'],
            'reference_values_in_public_report':False}
        _publish(root,'SEALED.json',seal)
        return freeze(report)
    except BaseException as error:
        try:
            journal.fail(error,'post_seal_native_evaluation')
            _publish(root,'FAILED.json',{'error_type':type(error).__name__,'automatic_retry':False,'new_model_calls':0,'new_retrieval_calls':0})
        except BaseException as recording_error:
            error.add_note('Evaluation failure recording: '+type(recording_error).__name__)
        raise
    finally:
        journal.close()


def main():
    import argparse
    parser=argparse.ArgumentParser(description='Evaluator-only scoring of an already sealed LitQA2 generation run')
    parser.add_argument('--generation-root',required=True)
    parser.add_argument('--expected-sealed-sha256',required=True)
    parser.add_argument('--preparation-root',required=True)
    parser.add_argument('--expected-preparation-manifest-sha256',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--deadline-seconds',type=float,default=3600)
    args=parser.parse_args()
    result=score_run(args.generation_root,args.expected_sealed_sha256,args.preparation_root,
        args.expected_preparation_manifest_sha256,args.output,deadline_seconds=args.deadline_seconds)
    # Aggregate completion only; no native reference values on stdout.
    import json
    print(json.dumps({'status':result['status'],'scheduled_count':result['scheduled_count'],
        'raw_metrics':encode(result['raw_metrics']),'checked_metrics':encode(result['checked_metrics'])}))


if __name__=='__main__':main()
