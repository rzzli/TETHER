"""Full-schedule collection/answer operations for the supplied-paper diagnostic.

The separate controller must supervise these operations, freeze inputs and model
assets, and require the primary sources to be sealed before diagnostic collection.
"""
from pathlib import Path
import time

from tether_engine.atomic import publish_bytes
from tether_engine.serde import canonical,freeze
from experiments.labbench.native_contract import validate_query
from experiments.litqa_comparison import codecs,schedule,pipeline as primary,replay as native_replay
from experiments.litqa_supplied import resolver,admission


def _finish_failed(stage,error):
    if not stage.closed:
        try:stage.finish()
        except BaseException as secondary:error.add_note('Diagnostic partial finalization: '+type(secondary).__name__)


def collect(dois,output,*,seconds,policy):
    dois=tuple(resolver.identity(x) for x in dois)
    stage=schedule.Stage(dois,'supplied',output,seconds=seconds)
    (stage.root/'products').mkdir()
    try:
        def operation(slot,end):
            root=stage.root/'products'/f'{slot["ordinal"]:04d}';plan=resolver.plan(slot['id'],policy)
            resolver.acquire(plan,root,deadline=min(end-10,time.monotonic()+60))
            receipt=primary.proof(root/'RECEIPT.json');resolver.verify(root,receipt['sha256'],plan)
            return dict(status='completed',reason=None,product=dict(root=str(root.resolve()),receipt=receipt,plan=plan,
                        manifest=primary.proof(root/'MANIFEST.json')))
        for _ in stage.schedule:stage.call(operation)
        return stage.finish()
    except BaseException as error:_finish_failed(stage,error);raise


def collection_rows(root,sha,dois):
    rows=primary.parent_rows(root,sha,'supplied',dois)
    for (doi,branch),row in rows.items():
        codecs.need(branch=='shared' and row['status']=='completed' and row['product']['plan']['doi']==doi,'Diagnostic resolution identity')
        product=row['product'];manifest=resolver.verify(product['root'],product['receipt']['sha256'],product['plan'])
        codecs.need(canonical(manifest)==canonical(primary.read(product['manifest'])),'Diagnostic manifest reference')
    return rows


def descriptors(hint,collected):
    result={}
    for doi in hint['dois']:
        codecs.need((doi,'shared') in collected,'Missing diagnostic source resolution')
        product=collected[(doi,'shared')]['product']
        result[doi]=dict(root=product['root'],receipt_sha256=product['receipt']['sha256'],plan=product['plan'])
    return result


def _disposition(query,call,context):
    if call['summary']['status']=='completed':
        codecs.need(call['summary']['request_sha256']==codecs.digest(canonical(context.request)),'Diagnostic actual request differs from admission')
        prediction=call['summary']['decoded'];decision=admission.check(context,prediction,context.request)
        disposition=dict(id=query['id'],producer_status='produced',check_status='accepted' if decision['accepted'] else 'rejected',
                         prediction=prediction,reason=decision['reason'])
    else:
        decision=None
        disposition=dict(id=query['id'],producer_status='parse_failure' if call['summary']['status']=='codec_failure' else 'input_unavailable',
                         check_status='not_run',prediction=None,reason=call['summary']['status'])
    return disposition,decision


def answer(queries,hints,collected,common_root,output,*,seconds,cutoff,model_provenance,call_model):
    queries=tuple(validate_query(q) for q in queries)
    codecs.need([q['id'] for q in queries]==[h['id'] for h in hints],'Diagnostic full question/hint schedule')
    by_id={q['id']:q for q in queries};by_hint={h['id']:h for h in hints}
    expected_dois={d for h in hints for d in h['dois']}
    codecs.need(set(collected)=={(d,'shared') for d in expected_dois},'Complete unique DOI resolution cohort required')
    stage=schedule.Stage(tuple(by_id),'supplied',output,seconds=seconds)
    (stage.root/'products').mkdir()
    try:
        def operation(slot,end):
            q=by_id[slot['id']];hint=by_hint[slot['id']];root=stage.root/'products'/f'{slot["ordinal"]:04d}'
            deadline=min(end-10,time.monotonic()+120)
            context=admission.capture(q,hint,descriptors(hint,collected),common_root,cutoff,model_provenance,deadline=deadline)
            call=primary._model_result(call_model('answer',q,context.sources,root,deadline),'answer',q,context.sources)
            disposition,decision=_disposition(q,call,context)
            publish_bytes(root/'CONTEXT.json',canonical(context.report))
            return dict(status='completed',reason=None,product=dict(call=call,disposition=disposition,decision=decision,
                context=primary.proof(root/'CONTEXT.json'),hint_sha256=codecs.digest(canonical(hint)),diagnostic_only=True))
        for _ in stage.schedule:stage.call(operation)
        return stage.finish()
    except BaseException as error:_finish_failed(stage,error);raise


def replay_answers(root,sha,queries,hints,collected,common_root,*,cutoff,model_info):
    root=Path(root).resolve();by_id={q['id']:q for q in queries};by_hint={h['id']:h for h in hints}
    codecs.need(tuple(by_id)==tuple(by_hint),'Replay diagnostic schedule')
    rows=primary.parent_rows(root,sha,'supplied',tuple(by_id))
    for row in rows.values():
        q=by_id[row['id']];hint=by_hint[row['id']];cell=root/'products'/f'{row["ordinal"]:04d}'
        context=admission.capture(q,hint,descriptors(hint,collected),common_root,cutoff,model_info['provenance'])
        codecs.need(canonical(native_replay.load(cell/'CONTEXT.json'))==canonical(context.report),'Diagnostic context replay')
        call=native_replay.model_cell(cell,'answer',q,context.sources,model_info)
        disposition,decision=_disposition(q,call,context)
        expected=dict(call=call,disposition=disposition,decision=decision,context=primary.proof(cell/'CONTEXT.json'),
                      hint_sha256=codecs.digest(canonical(hint)),diagnostic_only=True)
        codecs.need(row['status']=='completed' and row['reason'] is None and canonical(row['product'])==canonical(expected),
                    'Diagnostic answer product reconstruction')
    return freeze(dict(status='verified',questions=len(rows),diagnostic_only=True,ordinary_retrieval=False,
                       scientific_correctness='not evaluated by maintained replay'))
