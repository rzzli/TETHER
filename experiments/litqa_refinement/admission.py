"""Receipt-inclusive six-source admission, separate from generated controls.

Source preflight never constructs a model request. The raw-source DAG excludes
critic text, prior predictions and mixed query-plan manifests. Verification of
their operational receipts does not make those artifacts citable evidence.
"""
from collections.abc import Mapping
from dataclasses import dataclass,field
from datetime import date,datetime,timezone
from pathlib import Path
import time
from types import SimpleNamespace

from tether_engine.contracts import Availability,Profile,Snapshot,SourceNode,TemporalClass
from tether_engine.provenance import InputGraph,catalog_index,check_role
from tether_engine.serde import Frozen,canonical,encode,fingerprint,freeze,parse_json
from tether_engine.study.stable_read import checked_path,deadline_check,hash_file,read_file,stable_files
from experiments.labbench.native_contract import validate_query,validate_prediction,visible_unsure_index
from experiments.labbench.tether_adapter import DEFAULT_CATALOG
from experiments.litqa_comparison import acquisition,codecs
from . import collection,contracts,model,selection

_AUTHORITY=object()


def _utc(value):
    value=datetime.fromisoformat(value) if isinstance(value,str) else value
    contracts.need(isinstance(value,datetime) and value.tzinfo is not None,'Aware source cutoff required')
    return value.astimezone(timezone.utc)


def _descriptor(value,*,original):
    allowed=({'root','receipt_sha256','plan'},{'root','receipt_sha256','plan','sources'}) if original else ({'root','receipt_sha256','plan'},)
    contracts.need(isinstance(value,Mapping) and set(value) in allowed,'Exact source collection descriptor')
    contracts.need(isinstance(value['root'],str) and Path(value['root']).is_absolute(),'Absolute original source root')
    contracts.digest(value['receipt_sha256'])
    if original:
        plan=acquisition.validate_plan(value['plan'])
        contracts.need(plan['strategy']=='lexical','Original source must be the fixed L collection')
    else:collection.validate_plan(value['plan'])
    return freeze(encode(value))


def _bound_inventory(root,receipt_sha,end):
    root=Path(root).absolute();receipt_path=checked_path(root,'RECEIPT.json')
    raw=read_file(receipt_path,end,1024**2)
    contracts.need(codecs.digest(raw)==receipt_sha,'Source receipt external anchor')
    receipt=parse_json(raw)
    contracts.need(isinstance(receipt,Mapping) and isinstance(receipt.get('files'),Mapping),'Source receipt inventory')
    contracts.need(len(receipt['files'])<=64,'Bounded source receipt inventory')
    proofs=[dict(path=str(receipt_path),sha256=receipt_sha,bytes=len(raw))]
    for name,value in receipt['files'].items():
        path=checked_path(root,name)
        contracts.need(isinstance(value,Mapping) and set(value)=={'sha256','bytes'},'Source member proof fields')
        contracts.digest(value['sha256'])
        contracts.need(type(value['bytes']) is int and 0<=value['bytes']<=32*1024**2,'Source member byte bound')
        proofs.append(dict(path=str(path),**value))
    return freeze(proofs)


def _verify_members(proofs,end):
    for proof in proofs:
        observed=hash_file(proof['path'],end)
        contracts.need(canonical(observed)==canonical({k:proof[k] for k in ('sha256','bytes')}),'Source file bytes changed')


def _temporal_graph(branch,root,manifest,cutoff,publication_cutoff,catalog,end):
    nodes=[];receipt_times=[];operational=[]
    for row in manifest['requests']:
        deadline_check(end)
        if row['transport_status']!='captured':continue
        receipt_path=checked_path(root,row['receipt_path'])
        receipt=parse_json(read_file(receipt_path,end,65536))
        observed=_utc(receipt['completed_at_utc'])
        contracts.need(observed<=cutoff,'Source response was captured after the availability cutoff')
        receipt_times.append(observed.isoformat())
        operational.append(dict(request_id=row['request_id'],http_status=row['http_status'],
            receipt_path=str(receipt_path),receipt_sha256=row['receipt_sha256'],observed_at_utc=observed.isoformat(),citable=False))
        if row['http_status']!=200:continue
        availability=Availability(None,None,None,None,observed.date(),'public_download_receipt',
            'Present-day observed availability; not historical availability',observed,row['receipt_sha256'])
        nodes.append(SourceNode(branch+':request:'+row['request_id'],'labbench_retrieved_literature',
            row['body_sha256'],row['body_path'],row['body_sha256'],'agent_evidence',availability,
            TemporalClass.CONTEMPORARY,row['url'],receipt_path=row['receipt_path'],receipt_sha256=row['receipt_sha256']))
    publications=[]
    for document in manifest['sources']:
        publication=document['publication_date']
        if publication is not None:
            contracts.need(date.fromisoformat(publication)<=date.fromisoformat(publication_cutoff),
                           'Retained source publication is after original publication cutoff')
        publications.append(dict(source_id=document['source_id'],publication_date=publication,
            unknown_reason='Original source metadata has no publication date' if publication is None else None))
    proofs=()
    if nodes:
        snapshot=Snapshot(2,'sc05-'+branch,Profile.CONTEMPORARY,cutoff.date(),False,(),tuple(nodes),str(root),
            manifest['coverage'],cutoff)
        graph=InputGraph(snapshot,root,catalog);refs=tuple(n.source_id for n in nodes)
        contracts.need(graph.exclusion(refs,SimpleNamespace(cutoff=cutoff)) is None,'Ineligible raw source ancestry')
        proofs=graph.verify(refs,{})
    return freeze(dict(source_proofs=proofs,publications=publications,observed_receipt_times=receipt_times,
                       operational_receipts=operational))


@dataclass(frozen=True)
class CapturedMergedContext(Frozen):
    query: Mapping
    sources: tuple
    report: Mapping
    control_sha256: str
    _file_proofs: tuple=field(repr=False)
    _inventories: tuple=field(repr=False)
    _integrity: str=field(repr=False)
    _authority: object=field(default=None,repr=False,compare=False)


def _trusted(context):
    contracts.need(isinstance(context,CapturedMergedContext) and context._authority is _AUTHORITY,
                   'Verified merged-source capability required')
    expected=fingerprint(dict(query=context.query,sources=context.sources,report=context.report,
        control_sha256=context.control_sha256,file_proofs=context._file_proofs,inventories=context._inventories))
    contracts.need(expected==context._integrity,'Merged context integrity differs')
    return context


def revalidate(context,*,deadline=None):
    context=_trusted(context);end=collection._end(deadline)
    paths=tuple(p['path'] for p in context._file_proofs)
    with stable_files(paths,deadline=end):
        _verify_members(context._file_proofs,end)
        for root,names in context._inventories:
            current={path.relative_to(root).as_posix() for path in Path(root).rglob('*') if path.is_file()}
            contracts.need(current==set(names),'Source inventory changed after capture')
            for name in current:checked_path(root,name)
        deadline_check(end)
    return context


def capture(query,original_descriptor,refinement_descriptor,cutoff,*,control_sha256,
            unavailable_reason=None,deadline=None,catalog=None):
    """Verify all source bytes/time/roles and select raw passages; no model prep."""
    query=validate_query(query);contracts.digest(control_sha256,'Pre-repair control digest')
    original=_descriptor(original_descriptor,original=True)
    refinement=None if refinement_descriptor is None else _descriptor(refinement_descriptor,original=False)
    if refinement is None:
        contracts.need(isinstance(unavailable_reason,str) and unavailable_reason=='refinement_query_unavailable',
                       'Missing refinement needs explicit unavailability')
    else:contracts.need(unavailable_reason is None,'Collected refinement cannot be marked unavailable')
    question=dict(id=query['id'],question=query['question']);cutoff=_utc(cutoff);end=collection._end(deadline)
    contracts.need(original['plan']['question']==question,'Original query/source identity')
    publication_cutoff=original['plan']['policy']['cutoff_date']
    contracts.need(date.fromisoformat(publication_cutoff)<=cutoff.date(),'Publication cutoff exceeds availability cutoff')
    effective=freeze(DEFAULT_CATALOG if catalog is None else catalog);index=catalog_index(effective)
    # Enforce roles even for empty/failed source collections.
    check_role('labbench_retrieved_literature','agent_evidence',index)
    check_role('labbench_retrieved_passages','agent_evidence',index)
    if refinement is not None:
        contracts.need(refinement['plan']['question']==question and refinement['plan']['control_provenance']['query_sha256']==fingerprint(query),
                       'Refinement query/control identity')
        contracts.need(refinement['plan']['raw_plan']['policy']['cutoff_date']==publication_cutoff,
                       'Refinement publication cutoff differs from original')
    original_root=Path(original['root']);proofs=list(_bound_inventory(original_root,original['receipt_sha256'],end))
    inventories=[(str(original_root),tuple(['RECEIPT.json']+[str(Path(p['path']).relative_to(original_root).as_posix()) for p in proofs[1:]]))]
    if refinement is not None:
        more=_bound_inventory(Path(refinement['root']),refinement['receipt_sha256'],end);proofs.extend(more)
        inventories.append((refinement['root'],tuple(['RECEIPT.json']+[str(Path(p['path']).relative_to(refinement['root']).as_posix()) for p in more[1:]])))
    unique={}
    for proof in proofs:
        contracts.need(proof['path'] not in unique or unique[proof['path']]==proof,'Conflicting original file proofs')
        unique[proof['path']]=proof
    proofs=tuple(unique.values())
    with stable_files(tuple(p['path'] for p in proofs),deadline=end):
        _verify_members(proofs,end)
        old=acquisition.verify(original_root,original['receipt_sha256'],original['plan'])
        if 'sources' in original:contracts.need(canonical(original['sources'])==canonical(old['sources']),'Projected original source content changed')
        old_temporal=_temporal_graph('original',original_root,old,cutoff,publication_cutoff,index,end)
        old_bundle=dict(root=str(original_root),receipt_sha256=original['receipt_sha256'],sources=old['sources'])
        original_selected=codecs.select_order(old['pool']['pool'],[p['rank_id'] for p in old['pool']['pool']])['sources']
        new_bundle=new_temporal=new_manifest=None
        if refinement is not None:
            wrapper=collection.verify(refinement['root'],refinement['receipt_sha256'],refinement['plan'],deadline=end)
            raw=wrapper['raw_collection'];new_root=Path(raw['root'])
            new_manifest=acquisition.verify(new_root,raw['receipt_sha256'],raw['plan'])
            new_temporal=_temporal_graph('refinement',new_root,new_manifest,cutoff,publication_cutoff,index,end)
            new_bundle=dict(root=str(new_root),receipt_sha256=raw['receipt_sha256'],sources=new_manifest['sources'])
        merged=selection.merge_sources(old_bundle,new_bundle);pool=selection.build_pool(question,merged)
        selected=selection.select_raw(pool);ids={s['source_id'] for s in selected['sources']}
        bindings=tuple(b for b in pool['bindings'] if b['source_id'] in ids)
        report=freeze(dict(policy_kind='tether_sc05_merged_raw_source_v1',query_sha256=fingerprint(query),
            cutoff=cutoff.isoformat(),publication_cutoff=publication_cutoff,catalog_sha256=fingerprint(effective),
            original_descriptor=original,refinement_descriptor=refinement,
            unavailable_reason=unavailable_reason,merge=merged,pool=pool,selection=selected,bindings=bindings,
            original_selected_sources=original_selected,sources_sha256=fingerprint(selected['sources']),
            temporal=dict(original=old_temporal,refinement=new_temporal),
            source_proofs=tuple(old_temporal['source_proofs'])+(() if new_temporal is None else tuple(new_temporal['source_proofs'])),
            control_sha256=control_sha256,control_provenance=None if refinement is None else refinement['plan']['control_provenance'],
            control_is_scientific_evidence=False,operational_proofs=proofs,operational_proofs_citable=False,
            coverage=dict(original=old['coverage'],refinement=None if new_manifest is None else new_manifest['coverage'],
                merged=merged['coverage'],selection=selected,missingness='bounded collected subset; not biological absence'),
            source_decisions=dict(original=old['decisions'],refinement=None if new_manifest is None else new_manifest['decisions']),
            semantic_support='unevaluated',method=dict(selection='sc05_six_source_original_span_v1',
                code_sha256=codecs.digest(Path(selection.__file__).read_bytes()))))
        deadline_check(end)
        integrity=fingerprint(dict(query=query,sources=selected['sources'],report=report,control_sha256=control_sha256,
                                   file_proofs=proofs,inventories=inventories))
        return CapturedMergedContext(query,tuple(selected['sources']),report,control_sha256,proofs,tuple(inventories),integrity,_AUTHORITY)


def check(context,prediction,request,*,task,expected_control_sha256,payload=None,deadline=None):
    context=_trusted(context);accepted=False;reason=None;validated=None;mechanical=False
    # A broken original-byte/deadline invariant is an operational failure, not
    # an ordinary scientific rejection or an empty-evidence observation.
    revalidate(context,deadline=deadline)
    try:
        contracts.need(task in ('repair','removal') and request.get('task')==task,'Repair/removal task identity')
        contracts.need(expected_control_sha256==context.control_sha256,'Expected common control identity')
        contracts.need(canonical(request['query'])==canonical(context.query),'Actual query/options differ')
        prior=contracts.validate_candidate(context.query,request['candidate_context'],
            [s['source_id'] for s in context.report['original_selected_sources']])
        critique=contracts.validate_critique(context.query,prior,request['critique_context'],context.report['original_selected_sources'])
        actual_control=fingerprint(dict(query=context.query,candidate=prior,critique=critique))
        contracts.need(actual_control==expected_control_sha256,'Actual pre-repair generated context differs')
        control=context.report['control_provenance']
        if control is not None:
            contracts.need(control['candidate_sha256']==fingerprint(prior) and control['critic_context_sha256']==fingerprint(critique)
                and control['critic_native_call_sha256']==critique['native_call_sha256']
                and control['source_context_sha256']==critique['source_context_sha256'], 'Acquisition critic differs from repair control')
        sources=context.sources if task=='repair' else ()
        contracts.need(canonical(request['sources'])==canonical(sources),'Actual current raw-source selection differs')
        if payload is None:_,payload=model._request(task,context.query,prior,critique,sources,request['model_provenance'])
        model.validate_binding(request,payload)
        validated=validate_prediction(prediction,context.query,[s['source_id'] for s in sources])
        if validated['answer_index']!=visible_unsure_index(context.query) and not validated['evidence_ids']:
            mechanical=task=='removal'
            raise ValueError('raw_source_removal_mechanically_rejects_substantive_answer' if mechanical else
                             'Substantive answer requires current admitted raw evidence')
        accepted=True
    except (ValueError,TypeError,KeyError,OSError) as error:reason=str(error)
    return freeze(dict(accepted=accepted,reason=reason,prediction=validated,task=task,
        request_sha256=fingerprint(request),context_sha256=fingerprint(context.report),control_sha256=context.control_sha256,
        raw_removal_mechanical_rejection=mechanical,semantic_support='unevaluated'))
