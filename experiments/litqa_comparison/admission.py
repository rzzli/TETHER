"""Source-inclusive TETHER admission for SC04's new selection/answer contract.

Native model execution replay is a separate mandatory controller gate. This
module checks actual input lineage and available source bindings, not entailment.
"""
from datetime import datetime,timezone,date
from pathlib import Path
from types import SimpleNamespace
import time
from dataclasses import dataclass
from collections.abc import Mapping

from asof.contracts import Availability,Profile,Snapshot,SourceNode,TemporalClass
from asof.provenance import InputGraph,catalog_index
from asof.serde import Frozen,canonical,encode,freeze,fingerprint,parse_json,safe_child
from asof.study.stable_read import stable_files,read_file
from experiments.labbench.native_contract import validate_query,validate_prediction,visible_unsure_index
from experiments.labbench.tether_adapter import DEFAULT_CATALOG
from . import acquisition,codecs,transport


@dataclass(frozen=True)
class CapturedContext(Frozen):
    query: Mapping
    sources: tuple
    request: Mapping
    report: Mapping


def capture(query,root,receipt_sha256,query_plan,cutoff,model_provenance,*,order=None,catalog=None,deadline=None):
    query=validate_query(query)
    codecs.need(query_plan['question']=={'id':query['id'],'question':query['question']},'Acquisition/answer question differs')
    cutoff=datetime.fromisoformat(cutoff) if isinstance(cutoff,str) else cutoff
    codecs.need(isinstance(cutoff,datetime) and cutoff.tzinfo is not None,'Exact aware evidence cutoff required')
    cutoff=cutoff.astimezone(timezone.utc)
    root=Path(root).resolve();receipt_path=root/'RECEIPT.json'
    end=time.monotonic()+120 if deadline is None else deadline
    effective=freeze(DEFAULT_CATALOG if catalog is None else catalog)
    with stable_files((receipt_path,),deadline=end):
        raw=read_file(receipt_path,end,1024**2)
        codecs.need(codecs.digest(raw)==receipt_sha256,'Source external anchor mismatch')
        paths=[safe_child(root,name) for name in parse_json(raw)['files']]
        with stable_files(paths,deadline=end):
            manifest=acquisition.verify(root,receipt_sha256,query_plan)
            pool=manifest['pool']['pool']
            order=tuple(p['rank_id'] for p in pool) if order is None else tuple(order)
            selected=codecs.select_order(pool,order)
            selected_ids={s['source_id'] for s in selected['sources']}
            bindings=tuple(b for b in manifest['pool']['bindings'] if b['source_id'] in selected_ids)
            by_request={r['request_id']:r for r in manifest['requests']}
            used=set();publications={}
            for source in manifest['sources']:
                publication=source['publication_date']
                if publication is not None:codecs.need(date.fromisoformat(publication)<=cutoff.date(),'Publication after evidence cutoff')
                publications[source['source_id']]=dict(reported_date=publication,
                    unknown_reason='not reported in original metadata' if publication is None else None)
                matches=[r for r in manifest['requests'] if r.get('body_path')==source['original']['path']]
                codecs.need(len(matches)==1,'Original source request ambiguity')
                used.update((source['discovery_request_id'],matches[0]['request_id']))
            nodes=[]
            for key in sorted(used):
                row=by_request[key]
                codecs.need(row['transport_status']=='captured' and row['http_status']==200,'Ineligible original response')
                receipt=parse_json(read_file(safe_child(root,row['receipt_path']),end,65536))
                observed=datetime.fromisoformat(receipt['completed_at_utc'])
                availability=Availability(None,None,None,None,observed.date(),'public_download_receipt',
                    'Present-day download bound, not historical availability',observed,row['receipt_sha256'])
                nodes.append(SourceNode('request:'+key,'labbench_retrieved_literature',row['body_sha256'],row['body_path'],
                    row['body_sha256'],'agent_evidence',availability,TemporalClass.CONTEMPORARY,row['url'],
                    receipt_path=row['receipt_path'],receipt_sha256=row['receipt_sha256']))
            proofs=()
            if nodes:
                computed=datetime.fromisoformat(manifest['computed_at'])
                codecs.need(computed.tzinfo is not None,'Derived timestamp awareness')
                manifest_sha=codecs.digest(read_file(root/'MANIFEST.json',end,32*1024**2))
                nodes.append(SourceNode('parsed-manifest','labbench_retrieved_passages',manifest_sha,'MANIFEST.json',manifest_sha,
                    'agent_evidence',Availability(None,None,None,None,computed.date(),'computed_from_verified_originals',None),
                    TemporalClass.CONTEMPORARY,'local:sc04-balanced-source-extraction',parents=tuple(n.source_id for n in nodes),
                    computed_at=computed,method_id='sc04_balanced_acquisition_raw_pool',
                    method_version=codecs.digest(Path(acquisition.__file__).read_bytes())))
                snapshot=Snapshot(2,'sc04-'+query['id'],Profile.CONTEMPORARY,cutoff.date(),False,(),tuple(nodes),str(root),
                                  manifest['coverage'],cutoff)
                graph=InputGraph(snapshot,root,catalog_index(effective));refs=tuple(n.source_id for n in nodes)
                codecs.need(graph.exclusion(refs,SimpleNamespace(cutoff=cutoff)) is None,'Ineligible evidence lineage')
                proofs=graph.verify(refs,{})
            request,_=transport.make_answer_request(query,selected['sources'],model_provenance)
            report=freeze(dict(policy_kind='sc04_source_backed_v1',query_sha256=fingerprint(query),
                source_receipt_sha256=receipt_sha256,query_plan_sha256=fingerprint(query_plan),cutoff=cutoff.isoformat(),
                catalog_sha256=fingerprint(effective),publications=publications,source_proofs=proofs,
                sources_sha256=fingerprint(selected['sources']),bindings=bindings,order=order,
                request_sha256=fingerprint(request),coverage=manifest['coverage'],selection=selected,
                semantic_support='unevaluated',lineage_scope='All retained eligible articles, not only cited passages'))
            return CapturedContext(query,selected['sources'],request,report)


def check(context,prediction,request):
    codecs.need(isinstance(context,CapturedContext),'Trusted captured context required')
    codecs.need(context.report['query_sha256']==fingerprint(context.query) and
                context.report['sources_sha256']==fingerprint(context.sources) and
                context.report['request_sha256']==fingerprint(context.request),'Captured context differs')
    accepted=False;reason=None;validated=None
    try:
        codecs.need(canonical(request)==canonical(context.request),'Request differs from admitted evidence')
        validated=validate_prediction(prediction,context.query,[s['source_id'] for s in context.sources])
        codecs.need(validated['answer_index']==visible_unsure_index(context.query) or bool(validated['evidence_ids']),
                    'Substantive answer requires admitted evidence')
        accepted=True
    except (ValueError,TypeError) as error:reason=str(error)
    return freeze(dict(accepted=accepted,reason=reason,prediction=validated,
                       request_sha256=fingerprint(context.request),context_sha256=fingerprint(context.report),
                       semantic_support='unevaluated'))
