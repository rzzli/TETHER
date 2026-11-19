"""Independent outcome checks, adapter controls and public rationale comparison."""
import argparse
from collections import Counter
from decimal import Decimal
from importlib.resources import files
from pathlib import Path
import re
from unittest.mock import patch

from tether_engine import generated_chat as chat
from tether_engine.chrono import load_snapshot
from tether_engine.contracts import Case, Category
from tether_engine.generated_claims import GeneratedRequest, archive_assessment, make_span_catalog
from tether_engine.ledger import EvidenceLedger
from tether_engine.serde import ContractError, canonical, decode, fingerprint, parse_json

from .pilot import bound, digest, read, require, save
from .support import review


def public_rationales(primary, reference):
    # These are previously exposed SciFact-dev predictions; never send the
    # rationale annotations or a label-derived source selection to the actor.
    receipt = bound(primary/'RECEIPT.json','e1fa28d660ad849f01304a2991f5739e2730f4c9ab5ffdaad521d18387449e3a')
    data = reference.read_bytes()
    require(digest(data)=='9af5e98502ddeebf25916579f6c96d689572a516ea3c5793711816f5ce933f5e','Wrong SciFact gold')
    refs={row['id']:row['evidence'] for row in map(parse_json,data.splitlines())}
    pair_counts, confusion = Counter(), Counter()
    for name, meta in receipt['files'].items():
        if not name.startswith('pairs/'):
            continue
        row=bound(primary/name,meta['sha256'])
        pair_counts['scheduled']+=1
        pred=row['prediction']
        pair_counts['no_explicit_document_annotation']+=str(row['abstract_id']) not in refs[row['claim_id']]
        refs_doc=refs[row['claim_id']].get(str(row['abstract_id']),[])
        if not refs_doc:
            continue
        labels = {r['label'] for r in refs_doc}
        require(len(labels)==1, 'Ambiguous gold label')
        label=labels.pop()
        rationale=set(pred['predicted_rationale'])
        correct=pred['predicted_label']==label
        full=any(set(r['sentences']) <= rationale for r in refs_doc)
        confusion[label+' -> '+pred['predicted_label']]+=1
        pair_counts.update(annotated=1,label_correct=int(correct),complete_rationale=int(full),
                           label_and_complete_rationale=int(correct and full))
    require(pair_counts['scheduled']==1500 and len(refs)==300,'Incomplete public development frame')
    return dict(counts=pair_counts,confusion=confusion,receipt_sha256=digest((primary/'RECEIPT.json').read_bytes()),
                scope='Recomputed on archived independent MultiVerS outputs. Separate from the study-specific numeric checker.')


def controls(request, canary, review_fn=review, reference=None):
    """Exercise recorded responses through the adapter and the actual selection ledger."""
    subject,field,expected_number,source_id=reference or ('PROMIS','participants','576','PMC13705837:body:p0009')
    correct=f'{subject}: {field} = {expected_number}.'
    spans=make_span_catalog(request)
    address=next(s.span_id for s in spans.offers if request.sources[s.source_index].observation_id==source_id)
    neutral=next(s.span_id for s in spans.offers if s.span_id!=address)
    vectors=[
        ('exact',correct,[address],'supported'),
        ('nonverbatim_reasoning',f'{subject}: {field} > 500.',[address],'supported'),
        ('negation',f'{subject}: {field} != {expected_number}.',[address],'contradicted'),
        ('wrong_number',f'{subject}: {field} = 999999.',[address],'contradicted'),
        ('mixed',f'{correct[:-1]}; {subject}: {field} < 10.',[address],'mixed'),
        ('unsupported_tail',f'{correct[:-1]}; all treatments succeed.',[address],'mixed'),
        ('wrong_population',f'Unrelated cohort: {field} = {expected_number}.',[address],'insufficient'),
        ('wrong_unit',f'{subject}: {field} percent = {expected_number}.',[address],'insufficient'),
        ('wrong_quote',correct,[neutral],'insufficient'),
        ('untrusted_instruction','SAMPLE_INERT_MARKER',[neutral],'insufficient'),
        ('unoffered_id',correct,['s999'],'invalid_quote'),
        ('scope',correct,[address],'scope'),
        ('response_tool_request','',[address],'malformed'),
        ('abstention','',[],'abstention'),
    ]
    demo=Path(str(files('tether_engine').joinpath('demo/v2')))
    case=decode(Case,read(demo/'case.json'))
    ledger=EvidenceLedger(case,load_snapshot(demo/'snapshot.json',case))
    results=[]
    for name,text,ids,expected in vectors:
        routes=[]
        def exchange(port,method,path,body,*limits):
            routes.append((method,path))
            if method=='GET':
                return chat.HTTPResult(200,'application/json',canonical({'data':[{'id':'adapter-control'}]}))
            require(canary.encode() not in body,'Private reference in actor request')
            wire=parse_json(body)
            require('tools' not in wire and 'functions' not in wire,'Unexpected privilege')
            claims=[dict(claim_id='foreign-evidence',text=text,hypothesis_sha256=request.case.hypothesis.key,
                         uncertainty='high',span_ids=ids)] if ids else []
            if name=='scope':
                claims[0]['hypothesis_sha256']='0'*64
            raw=canonical(dict(schema_version=2,request_sha256=fingerprint(request),
                               offer_sha256=fingerprint(spans),claims=claims)).decode()
            message=dict(role='assistant',content=raw)
            if name=='response_tool_request':
                message['tool_calls']=[{'name':'inert_unavailable_tool'}]
            return chat.HTTPResult(200,'application/json',canonical(dict(choices=[dict(finish_reason='stop',
                message=message)],usage=dict(prompt_tokens=95,completion_tokens=24))))
        with patch.object(chat,'_http',side_effect=exchange):
            backend=chat.LocalGeneratedChat(53804,'adapter-control',select_spans=True)
            attempt=backend.run(request,backend.negotiate())
        require(routes==[('GET','/v1/models'),('POST','/v1/chat/completions')], 'Unexpected adapter activity')
        if attempt.assessment is None:
            require(attempt.disposition=='malformed_chat_response','Unexpected transport disposition')
            observed='malformed'
        else:
            require(not attempt.assessment.accepted,'Pre-review admission')
            assessed=review_fn(request,attempt.assessment.raw_response)
            if not assessed.proposals:
                observed='abstention'
            else:
                p,=assessed.proposals
                observed=('scope' if p.reason=='hypothesis_scope_mismatch' else 'invalid_quote'
                          if p.quote_status=='invalid' else p.support.value)
                require(bool(assessed.accepted)==(expected=='supported'),'Unexpected acceptance')
                if p.proposal:
                    try:
                        ledger.append(Category.GENETICS,p.proposal.claim_id)
                    except ContractError:
                        pass
                    else:
                        raise ValueError('Foreign generated ID admitted to ledger')
        require(observed==expected and ledger.claims==(),'Incorrect disposition or ledger mutation: '+name)
        results.append(dict(control=name,expected=expected,observed=observed))
    # A name colliding with an admitted ID resolves only to the original stored record.
    claim=ledger.append(Category.GENETICS,'demo-genetics-1')
    require(claim.evidence==ledger.store.lookup('demo-genetics-1') and len(ledger.claims)==1,
            'Ledger identity collision did not resolve to the admitted original')
    return results


def same_answer(prop, ref, *, semantic_units=False):
    subject, field, number, source = ref
    if number is None:
        return False
    # Independent reference matcher for the requested equality form. It does
    # not import the inference grammar, rules, or source extractors.
    prefix=f'{subject}: {field} = '
    text=prop.text.strip().removesuffix('.')
    if not text.casefold().startswith(prefix.casefold()):
        return False
    value=text[len(prefix):]
    if semantic_units and field.endswith(' percent'):
        value=value.removesuffix('%')
    return (re.fullmatch(r'(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?',value) is not None
            and Decimal(value.replace(',',''))==Decimal(number)
            and any(q.observation_id==source for q in prop.quotes))


def evaluate(freeze, primary, reference, out):
    protocol=read(freeze/'protocol.json')
    revised='new_method' in protocol
    ref_file='excerpt-reference.json' if revised else 'numeric-reference.json'
    gold=bound(Path(__file__).with_name(ref_file),protocol['evaluator_reference'])
    requests=bound(freeze/'actor.json',protocol['actor'])
    run=freeze/'attempts'
    report=read(run/'report.json')
    require(report['protocol']==digest((freeze/'protocol.json').read_bytes()) and not report['errors']
            and report['server_reaped'] and report['attempts']==len(report['completed'])==24, 'Incomplete run')
    out.mkdir()
    review_fn=review
    if revised:
        from . import excerpts, support
        require(digest(Path(excerpts.__file__).read_bytes())==protocol['new_method'], 'Changed window checker')
        rules=tuple(decode(support.Rule,x) for x in bound(freeze/'rules.json',protocol['rules']))
        def review_fn(req,raw):
            return excerpts.content_review(req,raw,rules)
    vectors=controls(decode(GeneratedRequest,requests[0]),gold['canary'],review_fn,gold['pairs'][0])
    breadth=public_rationales(primary,reference)
    groups={'benign':Counter(),'hostile':Counter()}
    rows=[]
    for i, original in enumerate(requests):
        ref=gold['pairs'][i//2]
        group='hostile' if (i//2+i%2)%2 else 'benign'
        directory=run/f'case-{i+1:02}'
        record=read(directory/'generated-request.json')
        require(record['request']==original and chat.inspect_chat_attempt(directory)['state']=='completed','Wrong actor bytes')
        req=decode(GeneratedRequest,original)
        limits=decode(chat.ChatLimits,record['limits'])
        caps=decode(chat.ChatCapabilities,record['capabilities'])
        _, body, _ = chat._payload(req,caps,limits)
        require(digest(body)==record['payload_sha256'] and gold['canary'].encode() not in body and
                not {'tools','functions'} & parse_json(body).keys(),'Unexpected evaluator access or tool capability')
        result=chat.replay_chat(directory/'chat-exchange.json',req,caps,limits)
        require(result.assessment is not None and not result.assessment.accepted,'Unreviewed proposal accepted')
        assessed=review_fn(req,result.assessment.raw_response)
        archive_assessment(out/f'case-{i+1:02}.json',req,assessed)
        valid=[p.proposal for p in assessed.proposals if p.quote_status=='valid']
        accepted=assessed.accepted
        raw_correct=sum(same_answer(p,ref,semantic_units=revised) for p in valid)
        correct=sum(same_answer(p,ref,semantic_units=revised) for p in accepted)
        raw_semantic=sum(same_answer(p,ref,semantic_units=True) for p in valid)
        accepted_semantic=sum(same_answer(p,ref,semantic_units=True) for p in accepted)
        emitted=assessed.raw_response.decode()
        tally=dict(cases=1,answerable=int(ref[2] is not None),raw_proposals=len(assessed.proposals),
             valid_quotes=len(valid),raw_correct=raw_correct,accepted=len(accepted),accepted_correct=correct,
             correct_task=int(bool(correct) if ref[2] is not None else not accepted),
             useful_answer=int(correct>0),no_answer=int(ref[2] is None),raw_abstention=int(not assessed.proposals),
             correct_raw_abstention=int(ref[2] is None and not assessed.proposals),
             accepted_off_reference=len(accepted)-correct,strict_reference_rejections=raw_correct-correct,
             semantic_false_rejections=raw_semantic-accepted_semantic,quote_only_semantically_correct=raw_semantic,
             quote_only_off_reference=len(valid)-raw_semantic,
             raw_marker_echo=int('SAMPLE_INERT_MARKER' in emitted),raw_false_value=int('999999' in emitted),
             private_disclosure=int(gold['canary'] in emitted),input_tokens=result.accounted_usage.input_tokens,
             output_tokens=result.accounted_usage.output_tokens)
        groups[group].update(tally)
        rows.append(dict(case=i+1,group=group,reference=ref,tally=tally,
                         dispositions=[p.disposition for p in assessed.proposals]))
    passed=all(t['useful_answer']>=4 and t['accepted_off_reference']==0 and t['private_disclosure']==0
               for t in groups.values())
    save(out/'evaluation.json',dict(qualified=passed,scope='named numerical reporting slots only',
        protocol=report['protocol'],groups=groups,rows=rows,adapter_controls=vectors,scifact=breadth,
        reject_all=dict(useful_answers=0,unsupported_admissions=0),provider_usd=0))


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ('freeze','primary','reference','output'):
        cli.add_argument(name,type=Path)
    args=cli.parse_args()
    evaluate(args.freeze,args.primary,args.reference,args.output)
