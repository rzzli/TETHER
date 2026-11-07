"""Raw-source lineage for the explicitly privileged-paper diagnostic.

Reference paper selection is declared separately from the public information in
the papers. This context cannot be passed off as ordinary retrieval performance.
"""
from datetime import datetime,timezone,date
from pathlib import Path
from types import SimpleNamespace
import time

from tether_engine.contracts import Availability,Profile,Snapshot,SourceNode,TemporalClass
from tether_engine.provenance import InputGraph,catalog_index
from tether_engine.serde import canonical,freeze,fingerprint,parse_json,safe_child
from tether_engine.study.stable_read import stable_files,read_file
from experiments.labbench.native_contract import validate_query
from experiments.labbench.tether_adapter import DEFAULT_CATALOG
from experiments.litqa_comparison import codecs,selection,transport
from experiments.litqa_comparison.admission import CapturedContext,check
from experiments.litqa_supplied import resolver


def capture(query,hint,descriptors,root,cutoff,model_provenance,*,catalog=None,deadline=None):
    query=validate_query(query)
    codecs.need(set(hint)=={'id','question','dois'} and hint['id']==query['id'] and hint['question']==query['question'],
                'Diagnostic question/hint identity')
    codecs.need(1<=len(hint['dois'])<=2 and len(set(hint['dois']))==len(hint['dois']) and set(descriptors)==set(hint['dois']),
                'Every annotated source requires an explicit completed resolution')
    for doi in hint['dois']:resolver.identity(doi)
    cutoff=datetime.fromisoformat(cutoff) if isinstance(cutoff,str) else cutoff
    codecs.need(isinstance(cutoff,datetime) and cutoff.tzinfo is not None,'Aware diagnostic cutoff')
    cutoff=cutoff.astimezone(timezone.utc);root=Path(root).resolve()
    end=time.monotonic()+120 if deadline is None else deadline
    effective=freeze(DEFAULT_CATALOG if catalog is None else catalog)
    receipts=[];files=[];locations={}
    for doi,descriptor in descriptors.items():
        codecs.need(set(descriptor)=={'root','receipt_sha256','plan'},'Explicit diagnostic source descriptor')
        location=Path(descriptor['root']).resolve()
        codecs.need(location.is_relative_to(root) and location!=root,'Source archive outside declared root')
        codecs.need(descriptor['plan']['doi']==doi,'Annotated/resolved DOI differs')
        locations[doi]=location;receipts.append(location/'RECEIPT.json')
    sources=[];proofs=[];availability=[];publications={};source_identity={}
    with stable_files(receipts,deadline=end):
        for doi,location in locations.items():
            raw=read_file(location/'RECEIPT.json',end,1024**2)
            codecs.need(codecs.digest(raw)==descriptors[doi]['receipt_sha256'],'Diagnostic external receipt binding')
            files.extend(safe_child(location,name) for name in parse_json(raw)['files'])
        with stable_files(files,deadline=end):
            for doi in hint['dois']:
                descriptor=descriptors[doi];location=locations[doi]
                manifest=resolver.verify(location,descriptor['receipt_sha256'],descriptor['plan'])
                source=manifest['source'];availability.append(dict(doi=doi,coverage=manifest['coverage'],decisions=manifest['decisions']))
                if source is None:continue
                sid=source['source_id'];signature=fingerprint(source)
                codecs.need(sid not in source_identity or source_identity[sid]==signature,'Conflicting same-PMC diagnostic sources')
                if sid not in source_identity:sources.append(source);source_identity[sid]=signature
                publication=source['publication_date']
                if publication is not None:codecs.need(date.fromisoformat(publication)<=cutoff.date(),'Diagnostic publication after cutoff')
                publications[doi]=dict(reported_date=publication,unknown_reason='not reported in original metadata' if publication is None else None)
                parents=[];nodes=[];prefix='doi:'+codecs.digest(doi.encode())[:24]
                for row in manifest['requests']:
                    codecs.need(row['transport_status']=='captured' and row['http_status']==200,'Retained source must have complete successful inputs')
                    receipt_path=location/row['receipt_path'];receipt=parse_json(read_file(receipt_path,end,65536))
                    observed=datetime.fromisoformat(receipt['completed_at_utc'])
                    available=Availability(None,None,None,None,observed.date(),'public_download_receipt',
                        'Present-day availability only; paper identity selected from benchmark annotation.',observed,row['receipt_sha256'])
                    node_id=prefix+':'+row['request_id'];parents.append(node_id)
                    nodes.append(SourceNode(node_id,'labbench_retrieved_literature',row['body_sha256'],
                        row['body_path'],row['body_sha256'],'agent_evidence',available,
                        TemporalClass.CONTEMPORARY,row['url'],receipt_path=row['receipt_path'],receipt_sha256=row['receipt_sha256']))
                computed=datetime.fromisoformat(manifest['computed_at']);codecs.need(computed.tzinfo is not None,'Aware derived source time')
                manifest_path=location/'MANIFEST.json';manifest_sha=codecs.digest(read_file(manifest_path,end,16*1024**2))
                nodes.append(SourceNode(prefix+':parsed','labbench_retrieved_passages',manifest_sha,'MANIFEST.json',
                    manifest_sha,'agent_evidence',Availability(None,None,None,None,computed.date(),'computed_from_verified_originals',None),
                    TemporalClass.CONTEMPORARY,'local:sc04-supplied-source-resolution',parents=tuple(parents),computed_at=computed,
                    method_id='sc04_supplied_source_resolution',method_version=codecs.digest(Path(resolver.__file__).read_bytes())))
                # Each archived receipt retains its own acquisition-root paths.
                # Verify that graph in its original root; never rewrite a receipt
                # merely to combine two independently acquired papers.
                snapshot=Snapshot(2,'sc04-supplied-'+query['id']+'-'+prefix,Profile.CONTEMPORARY,cutoff.date(),False,(),
                    tuple(nodes),str(location),manifest['coverage'],cutoff)
                graph=InputGraph(snapshot,location,catalog_index(effective));refs=tuple(n.source_id for n in nodes)
                codecs.need(graph.exclusion(refs,SimpleNamespace(cutoff=cutoff)) is None,'Ineligible diagnostic input lineage')
                proofs.extend(graph.verify(refs,{}))
            coverage=dict(annotated_dois=len(hint['dois']),retained_articles=len(sources),sources=availability,
                selection_role='supplied_source_diagnostic',ordinary_retrieval=False,
                unknown_or_unavailable_inputs=[x['doi'] for x in availability if not x['coverage']['article_retained']])
            # Identical lexical pool/selector to the new L/O arm. No key passage
            # or reference answer enters selection or the final model request.
            pool=selection.build_pool(dict(id=query['id'],question=query['question']),sources)
            selected=codecs.select_order(pool['pool'],[p['rank_id'] for p in pool['pool']])
            request,_=transport.make_answer_request(query,selected['sources'],model_provenance)
            report=freeze(dict(policy_kind='sc04_supplied_source_v1',diagnostic_only=True,ordinary_retrieval=False,
                query_sha256=fingerprint(query),hint_sha256=fingerprint(hint),selection_uses_reference_paper_identity=True,
                source_descriptors=descriptors,cutoff=cutoff.isoformat(),catalog_sha256=fingerprint(effective),publications=publications,
                source_proofs=proofs,coverage=coverage,pool=pool,sources_sha256=fingerprint(selected['sources']),
                request_sha256=fingerprint(request),scientific_support_verified=False))
    return CapturedContext(query,tuple(selected['sources']),request,report)
