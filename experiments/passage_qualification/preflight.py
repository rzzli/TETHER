"""Run corrected units, genuine distractors and a deterministic comparator before dispatch."""
import argparse
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from tether_engine.generated_claims import GeneratedRequest, Support, make_span_catalog
from tether_engine.serde import canonical, decode, fingerprint, parse_json

from . import audit, excerpts, support
from .pilot import bound, digest, read, require, save


def envelope(request,text,source_id):
    catalog=make_span_catalog(request)
    ids=[s.span_id for s in catalog.offers if request.sources[s.source_index].observation_id==source_id]
    claims=[dict(claim_id='control',text=text,uncertainty='high',hypothesis_sha256=request.case.hypothesis.key,
                span_ids=ids)] if text else []
    return canonical(dict(schema_version=2,request_sha256=fingerprint(request),offer_sha256=fingerprint(catalog),
                          claims=claims))


def reconstruct(freeze, collection):
    protocol=read(freeze/'protocol.json')
    roster=bound(freeze/'roster.json',protocol['roster'])
    docs={}
    for row in roster:
        name,case,pmcid,number,_,sha,_,_ = next(p for p in excerpts.PAPERS if p[2]==row['source'])
        raw=(collection/'cases'/case/'retrieval'/'requests'/f'{number:03}.body').read_bytes()
        require(sha==digest(raw)==row['source_sha256'],'Wrong source')
        p=ET.fromstring(raw).findall('.//body//p')[row['body_index']]
        text=' '.join(' '.join(p.itertext()).split()).encode()
        require(digest(text)==row['paragraph_sha256'],'Wrong original paragraph')
        part=text[row['start_byte']:row['end_byte']]
        require(digest(part)==row['excerpt_sha256'],'Wrong excerpt offsets')
        docs[row['id']]=f'Article label: {name} ({pmcid}).\nPublished passage: '+part.decode()
    return docs


def check(freeze,collection):
    protocol=read(freeze/'protocol.json')
    refs=bound(Path(__file__).with_name('excerpt-reference.json'),protocol['evaluator_reference'])
    rows=bound(freeze/'actor.json',protocol['actor'])
    rules=tuple(decode(support.Rule,r) for r in bound(freeze/'rules.json',protocol['rules']))
    docs=reconstruct(freeze,collection)
    results=[]
    for i,row in enumerate(rows):
        request=decode(GeneratedRequest,row)
        ref=refs['pairs'][i//2]
        require(refs['canary'] not in canonical(request).decode(),'Evaluator exposed')
        for src in request.sources:
            if src.observation_id!='editorial-note':
                require(src.text==docs[src.observation_id],'Actor excerpt differs from original')
        # The comparator receives question and offered sources only, using the
        # same declared record/field vocabulary and authenticated extraction rules.
        candidates=[]
        for rule in rules:
            if f'"{rule.series}: {rule.field} = NUMBER."' not in request.question:
                continue
            for src in request.sources:
                if (src.observation_id,src.text_sha256)==(rule.passage,rule.text_digest):
                    vals=re.findall(rule.pattern,src.text)
                    require(len(vals)==1,'Ambiguous source extraction')
                    candidates.append((rule,vals[0],src.observation_id))
        if candidates:
            require(len(candidates)==1,'Ambiguous answer')
            rule,value,source=candidates[0]
            percent='%' if rule.field.endswith(' percent') else ''
            left=f'{rule.series}: {rule.field}'
            answer=f'{left} = {value}{percent}.'
            raw=envelope(request,answer,source)
            scored=excerpts.content_review(request,raw,rules)
            require(len(scored.accepted)==1 and audit.same_answer(scored.accepted[0],ref,semantic_units=True),
                    'Unqualified oracle answer')
            wrong=envelope(request,f'{left} = {Decimal(value)+1}{percent}.',source)
            require(excerpts.content_review(request,wrong,rules).proposals[0].support==Support.CONTRADICTED,'Wrong value passed')
            if not percent:
                wrong=envelope(request,f'{left} = {value}%.',source)
                require(not excerpts.content_review(request,wrong,rules).accepted,'Forged units passed')
            mixed=envelope(request,answer[:-1]+'; unrelated material.',source)
            require(excerpts.content_review(request,mixed,rules).proposals[0].support==Support.MIXED,'Unsupported tail passed')
        else:
            require(ref[2] is None,'Checker missed an answerable slot')
        results.append(dict(case=i+1,available=bool(candidates)))
    # Check the real adapter/ledger on this table, using independent expected outcomes.
    request=decode(GeneratedRequest,rows[0])
    controls=audit.controls(request,refs['canary'],lambda q,b:excerpts.content_review(q,b,rules),refs['pairs'][0])
    first=request.sources[0]
    other=replace(first,observation_id='fixture-other',text='Second report observed 9999 articles.',
                  text_sha256=digest(b'Second report observed 9999 articles.'))
    clash=replace(request,sources=(first,other))
    rule=replace(rules[0],passage=other.observation_id,text_digest=other.text_sha256,pattern=r'observed (\d+) articles')
    raw=envelope(clash,'GLP-1 review: articles identified = 2574.',first.observation_id)
    payload=parse_json(raw)
    payload['claims'][0]['span_ids']=['s001','s002']
    checked=excerpts.content_review(clash,canonical(payload),rules+(rule,))
    require(checked.proposals[0].support==Support.MIXED and not checked.accepted,'Conflicting reports passed')
    present=sum(x['available'] for x in results)
    require(present==16 and len(results)==24,'Incomplete design')
    save(freeze/'preflight.json',dict(protocol_sha256=digest((freeze/'protocol.json').read_bytes()),
        original_windows_checked=len(docs),cases=results,adapter_controls=controls,
        constructed_conflict='withheld_mixed',deterministic_correct=present,deterministic_abstentions=24-present,
        actual_model_attempts=0,scope='Method and comparator controls only'))


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('freeze',type=Path)
    cli.add_argument('collection',type=Path)
    args=cli.parse_args()
    check(args.freeze,args.collection)
