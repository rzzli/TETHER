"""Six-document raw merge, original chunk semantics and semantic withholding."""
from collections.abc import Mapping
from pathlib import Path
import re

from tether_engine.serde import canonical, encode, fingerprint, freeze
from experiments.labbench.native_contract import visible_unsure_index
from experiments.labbench.retrieval import question_tokens
from experiments.litqa_comparison import codecs
from . import contracts


def _bundle(value,branch):
    contracts.need(isinstance(value,Mapping) and set(value)=={'root','receipt_sha256','sources'},'Raw collection descriptor')
    contracts.need(isinstance(value['root'],str) and Path(value['root']).is_absolute(),'Absolute raw collection root')
    contracts.digest(value['receipt_sha256'],'Raw collection receipt digest')
    contracts.need(isinstance(value['sources'],(list,tuple)) and len(value['sources'])<=3,'Per-collection source cap')
    seen=set();result=[]
    for source in value['sources']:
        contracts.need(isinstance(source,Mapping),'Raw document required')
        sid=source.get('source_id')
        contracts.need(isinstance(sid,str) and re.fullmatch(r'PMC[0-9]+',sid) and sid not in seen,'Raw document identity')
        seen.add(sid)
        contracts.need(source.get('metadata_license') in ('cc by','cc0') and source.get('xml_license'), 'Raw rights metadata required')
        contracts.need(isinstance(source.get('original'),Mapping) and isinstance(source.get('spans'),(list,tuple)), 'Original source lineage required')
        contracts.digest(source['original'].get('sha256'),'Original body digest')
        contracts.need(type(source['original'].get('bytes')) is int and source['original']['bytes']>0,'Original body bytes')
        for key in ('path','receipt_path'):
            part=source['original'].get(key)
            contracts.need(isinstance(part,str) and part and not Path(part).is_absolute() and '\\' not in part
                and all(p not in ('','..','.') for p in part.split('/')),'Original relative locator')
        aliases=dict(branch=branch,collection_root=value['root'],collection_receipt_sha256=value['receipt_sha256'],
                     original=source['original'],discovery_request_id=source.get('discovery_request_id'))
        result.append(dict(document=encode(source),alias=aliases))
    return result


def merge_sources(original,new=None):
    """Merge already receipt-validated collections; no inferred source eligibility.

    This function is pure. The admission caller must verify both raw collections
    and their time/role ancestry. A missing new collection is explicit, never a
    fabricated empty acquisition receipt.
    """
    rows=_bundle(original,'original')+([] if new is None else _bundle(new,'refinement'))
    grouped={}
    for row in rows:grouped.setdefault(row['document']['source_id'],[]).append(row)
    sources=[];excluded=[]
    for sid,items in grouped.items():
        first=items[0]['document']
        # Discovery/rank/path vary by acquisition. All parsed scientific content,
        # identity, version and reuse terms must agree before receipt aliasing.
        ignored={'original','discovery_request_id','discovery_rank','discovery_query_slot'}
        identity=lambda s:{k:v for k,v in s.items() if k not in ignored}
        same=all(item['document']['original']['sha256']==first['original']['sha256'] and
                 canonical(identity(item['document']))==canonical(identity(first)) for item in items)
        aliases=[item['alias'] for item in items]
        if not same:
            excluded.append(dict(source_id=sid,reason='conflicting_pmc_version_identity_or_rights',receipt_aliases=aliases))
        else:
            sources.append(dict(**first,receipt_aliases=aliases))
    return freeze(dict(kind='tether_six_source_merge_v1',sources=sources,exclusions=excluded,
        parents=dict(original=dict(root=original['root'],receipt_sha256=original['receipt_sha256']),
                     refinement=None if new is None else dict(root=new['root'],receipt_sha256=new['receipt_sha256'])),
        coverage=dict(input_documents=len(rows),merged_documents=len(sources),conflicting_documents=len(excluded),
                      refinement_status='unavailable' if new is None else 'collected',
                      scope='selected eligible subset; not biological absence')))


def build_pool(question,merged):
    """SC04 UTF8/overlap semantics over up to six raw sources, with one global cap.

    The old three-document adapter is deliberately not called. Its contiguous
    paragraph chunking is reproduced unchanged here; common tokenization, pool
    validation and final selection primitives remain shared.
    """
    question=codecs.question_view(question)
    contracts.need(isinstance(merged,Mapping) and merged.get('kind')=='tether_six_source_merge_v1', 'Six-source merge required')
    sources=merged['sources']
    contracts.need(isinstance(sources,(list,tuple)) and len(sources)<=6,'Merged six-source cap')
    tokens=set(question_tokens(question['question']));chunks=[];seen_sources=set();seen_spans=set()
    for source in sources:
        sid=source['source_id']
        contracts.need(sid not in seen_sources,'Duplicate merged source');seen_sources.add(sid)
        contracts.need(source.get('receipt_aliases'),'Merged document needs original receipt aliases')
        for span in source['spans']:
            text=span['text']
            contracts.need(isinstance(text,str) and text.strip() and codecs.digest(text.encode())==span['text_sha256'],'Parent paragraph hash')
            contracts.need(span['source_id']==sid and span['evidence_id'] not in seen_spans,'Parent span identity')
            seen_spans.add(span['evidence_id']);start=0
            while start<len(text):
                end=min(len(text),start+1000)
                while len(text[start:end].encode())>1000:end-=1
                contracts.need(end>start,'Invalid UTF8 boundary')
                if end<len(text):
                    boundary=text.rfind(' ',start,end)
                    if boundary>start:end=boundary+1
                chunk=text[start:end];key=span['evidence_id']+f':c{start}-{end}'
                words=set(re.findall(r'[a-z][a-z0-9-]{2,}',chunk.casefold()))
                chunks.append(dict(task=dict(source_id=key,text=chunk,sha256=codecs.digest(chunk.encode())),
                    score=len(tokens & words),binding=dict(source_id=key,document_id=sid,span_id=span['evidence_id'],
                        character_start=start,character_end=end,parent_text_sha256=span['text_sha256'],
                        original_sha256=source['original']['sha256'],original_locator=span['locator'],
                        receipt_aliases=source['receipt_aliases'])))
                start=end
    ordered=sorted(enumerate(chunks),key=lambda item:(-item[1]['score'],item[0]))
    pool=[];bindings=[];used=0
    for _,chunk in ordered:
        size=len(chunk['task']['text'].encode())
        if len(pool)>=codecs.MAX_POOL or used+size>codecs.MAX_POOL_BYTES:continue
        pool.append(dict(rank_id=f'p{len(pool):02d}',**chunk['task']));bindings.append(chunk['binding']);used+=size
    pool=codecs.validate_pool(pool)
    return freeze(dict(pool=pool,bindings=bindings,question_sha256=codecs.digest(question['question'].encode()),
        merge_sha256=fingerprint(merged),coverage=dict(available_chunks=len(chunks),pool_chunks=len(pool),
            pool_text_bytes=used,excluded_chunks=len(chunks)-len(pool),
            available_text_bytes=sum(len(c['task']['text'].encode()) for c in chunks),
            scope='bounded raw paragraph chunks; no absence-of-evidence claim')))


def select_raw(pool):
    return codecs.select_order(pool['pool'],[item['rank_id'] for item in pool['pool']])


def select_original(query,prior,critique):
    """A separate deterministic policy; never changes native prediction/status."""
    prior=contracts.validate_candidate(query,prior)
    critique=contracts.validate_critique(query,prior,critique)
    prediction=prior['prediction'];decision='withhold'
    if prediction is None:decision,reason='not_applicable','original_candidate_unavailable'
    elif prediction['answer_index']==visible_unsure_index(query):decision,reason='not_applicable','original_native_unsure'
    elif prior['original_admission_status']!='accepted':reason='original_not_admitted'
    elif critique['decoded'] is None:reason='critic_unavailable'
    elif critique['decoded']['support']=='supported':decision,reason='keep','critic_supported'
    else:reason='critic_'+critique['decoded']['support']
    return freeze(dict(kind='tether_semantic_selection_v1',decision=decision,reason=reason,
        candidate_sha256=fingerprint(prior),critique_sha256=fingerprint(critique),
        retained_prediction=prediction if decision=='keep' else None,
        native_candidate_unchanged=True,scientific_correctness='unevaluated'))
