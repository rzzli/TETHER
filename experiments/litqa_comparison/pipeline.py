"""SC04 cross-stage operations; the CLI owns supervision and parent verification.

No reference answers are accepted. Production binds call_model to the owned,
one-shot native implementation; dependency injection exists for invented tests.
"""
from collections.abc import Mapping
from pathlib import Path
import hashlib
import time

from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal
from tether_engine.serde import canonical,encode,freeze,parse_json
from experiments.labbench.native_contract import validate_query
from . import acquisition,admission,codecs,schedule,transport


def proof(path):
    path=Path(path).resolve()
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return freeze(dict(path=str(path),sha256=digest,bytes=path.stat().st_size))


def read(proof_value,cap=32*1024**2):
    path=Path(proof_value['path'])
    codecs.need(path.is_file() and not path.is_symlink() and path.stat().st_size==proof_value['bytes']<=cap,'Product path/size')
    raw=path.read_bytes()
    codecs.need(len(raw)==proof_value['bytes'] and codecs.digest(raw)==proof_value['sha256'],'Product byte binding')
    return parse_json(raw)


def model_call(task,query,items,output,deadline,*,owner,model_provenance,alias):
    """Capture one model request; only codec/capacity failures are recoverable.

    A timeout or infrastructure/integrity exception stops the phase. There is
    no retry on this path and no request is redispatched from an old directory.
    """
    journal=RunJournal(Path(output),kind='build');root=journal.output
    request=payload=None
    try:
        publish_bytes(root/'INPUT.json',canonical(dict(task=task,query=query,items=items)))
        try:
            request,payload=(transport.make_answer_request(query,items,model_provenance) if task=='answer'
                             else transport.make_request(task,query,model_provenance,items))
            result=transport.execute_once(owner,request,payload,output=root/'native',journal=journal,
                                          deadline=deadline,alias=alias)
            summary=dict(status='completed',decoded=result['decoded'],generation_entered=True,
                         usage=result['measured_usage'],reservation_input_tokens=result['conservative_reserved_input_tokens'],
                         reservation_output_tokens=payload['n_predict'],native_result=proof(root/'native/result.json'))
        except codecs.PayloadCapacityError:
            summary=dict(status='capacity',decoded=None,generation_entered=False,usage=None,
                         reservation_input_tokens=0,reservation_output_tokens=0,native_result=None)
        except transport.OutputCodecError:
            failure=parse_json((root/'native/failure.json').read_bytes())
            codecs.need(failure['stage']=='verification' and failure['generation_entered'] and failure['measured_usage'] is not None,
                        'Recoverable codec failure lacks complete native usage')
            summary=dict(status='codec_failure',decoded=None,generation_entered=True,usage=failure['measured_usage'],
                         reservation_input_tokens=failure['conservative_reserved_input_tokens'],
                         reservation_output_tokens=payload['n_predict'],native_result=proof(root/'native/failure.json'))
        summary.update(task=task,query_sha256=codecs.digest(canonical(query)),items_sha256=codecs.digest(canonical(items)),
                       request_sha256=codecs.digest(canonical(request)) if request is not None else None,provider_cost_usd=0)
        publish_bytes(root/'SUMMARY.json',canonical(summary))
        journal.append('model_cell_completed',summary_sha256=codecs.digest(canonical(summary)),status=summary['status'])
        return freeze(dict(summary=summary,summary_proof=proof(root/'SUMMARY.json'),root=str(root.resolve())))
    except BaseException as error:
        journal.fail(error,'model_cell')
        publish_bytes(root/'FAILURE.json',canonical(dict(error_type=type(error).__name__,automatic_retry=False)))
        raise
    finally:journal.close()


def parent_rows(root,receipt_sha256,expected_stage,ids):
    """Verify complete parent bytes and scheduled identities before consuming it."""
    root=Path(root)
    state=schedule.verify(root,receipt_sha256)
    config=parse_json((root/'CONFIG.json').read_bytes());report=parse_json((root/'REPORT.json').read_bytes())
    codecs.need(config['stage']==expected_stage and tuple(config['ids'])==tuple(ids) and report['status']=='complete',
                'Required parent phase is incomplete or belongs to another schedule')
    return freeze({(r['id'],r['branch']):r for r in report['rows']})


def _model_result(value,task,query,items):
    codecs.need(isinstance(value,Mapping) and set(value)=={'summary','summary_proof','root'},'Model cell result contract')
    summary=value['summary']
    codecs.need(canonical(read(value['summary_proof']))==canonical(summary),'Model cell summary binding')
    codecs.need(summary['task']==task and summary['query_sha256']==codecs.digest(canonical(query))
                and summary['items_sha256']==codecs.digest(canonical(items)),'Model cell input identity')
    codecs.need(summary['status'] in ('completed','codec_failure','capacity'),'Unqualified model disposition')
    return freeze(encode(value))


def _collection(parent):
    product=parent['product']
    codecs.need(parent['status']=='completed','Collection must be complete, including explicit empty sources')
    manifest=acquisition.verify(product['root'],product['receipt']['sha256'],product['plan'])
    codecs.need(canonical(read(product['manifest']))==canonical(manifest),'Collection manifest reference')
    return manifest,product


def execute(phase,queries,output,*,seconds,parents=None,policy=None,cutoff=None,model_provenance=None,call_model=None):
    """Run every phase slot or retain a partial all-scheduled report on failure.

    parents are already source-inclusive verified stage rows from the controller.
    Native candidate/reference correctness is deliberately not computed here.
    """
    codecs.need(phase in ('expand','collect','rank','answer'),'Unsupported primary phase')
    checker=validate_query if phase=='answer' else codecs.question_view
    queries=tuple(checker(q) for q in queries);by_id={q['id']:q for q in queries}
    codecs.need(len(by_id)==len(queries),'Duplicate query ID')
    parents={} if parents is None else parents
    required={'expand':(), 'collect':('expand',), 'rank':('collect',), 'answer':('collect','rank')}[phase]
    codecs.need(set(parents)==set(required),'Exact required parent phases')
    for name in required:
        expected={(slot['id'],slot['branch']) for slot in schedule.slots(tuple(by_id),name)}
        codecs.need(set(parents[name])==expected,'Complete parent cohort required before dispatch')
    if phase=='collect':codecs.need(policy is not None,'Explicit collection policy required')
    else:codecs.need(callable(call_model),'Explicit owned model caller required')
    stage=schedule.Stage(tuple(by_id),phase,output,seconds=seconds)
    (stage.root/'products').mkdir()
    try:
        def operation(slot,end):
            q=by_id[slot['id']];branch=slot['branch'];cell=stage.root/'products'/f'{slot["ordinal"]:04d}'
            deadline=min(end-10,time.monotonic()+120)
            if phase=='expand':
                call=_model_result(call_model('expand',q,(),cell,deadline),'expand',q,())
                good=call['summary']['status']=='completed'
                expansion=codecs.parse_expansion(canonical(call['summary']['decoded'])) if good else None
                return dict(status='completed' if good else 'fallback',reason=None if good else call['summary']['status'],
                            product=dict(call=call,expansion=expansion,strategy='expanded' if good else 'lexical'))
            if phase=='collect':
                expansion=parents['expand'][(q['id'],'shared')]
                expected_strategy='expanded' if branch=='E' and expansion['status']=='completed' else 'lexical'
                plan=acquisition.plan(q,expected_strategy,policy=policy,
                    expansion=expansion['product']['expansion'] if expected_strategy=='expanded' else None)
                acquisition.acquire(plan,cell,deadline=deadline)
                receipt=proof(cell/'RECEIPT.json')
                acquisition.verify(cell,receipt['sha256'],plan)
                return dict(status='completed',reason=None,product=dict(root=str(cell.resolve()),receipt=receipt,plan=plan,
                    manifest=proof(cell/'MANIFEST.json'),expansion_available=expansion['status']=='completed',
                    query_branch=branch,expansion_parent_sha256=codecs.digest(canonical(expansion))))
            if phase=='rank':
                parent=parents['collect'][(q['id'],branch)];manifest,collection=_collection(parent)
                pool=manifest['pool']['pool']
                if not pool:
                    return dict(status='not_applicable',reason='empty eligible passage pool',product=dict(order=[],call=None,
                        collection_receipt_sha256=collection['receipt']['sha256'],pool_sha256=codecs.digest(canonical(pool))))
                call=_model_result(call_model('rank',q,pool,cell,deadline),'rank',q,pool)
                good=call['summary']['status']=='completed'
                order=codecs.parse_ranking(canonical(dict(order=call['summary']['decoded'])),pool) if good else tuple(p['rank_id'] for p in pool)
                return dict(status='completed' if good else 'fallback',reason=None if good else call['summary']['status'],
                    product=dict(order=order,call=call,collection_receipt_sha256=collection['receipt']['sha256'],pool_sha256=codecs.digest(canonical(pool))))
            # All collection and ranking parents must be sealed before this
            # phase starts; no answer can feed back into query/ranking stages.
            query_branch=branch[0];parent=parents['collect'][(q['id'],query_branch)]
            manifest,collection=_collection(parent)
            ranking=parents['rank'][(q['id'],query_branch)]
            codecs.need(ranking['product']['collection_receipt_sha256']==collection['receipt']['sha256'] and
                        ranking['product']['pool_sha256']==codecs.digest(canonical(manifest['pool']['pool'])), 'Rank/collection identity mismatch')
            order=ranking['product']['order'] if branch.endswith('/R') else [p['rank_id'] for p in manifest['pool']['pool']]
            context=admission.capture(q,collection['root'],collection['receipt']['sha256'],collection['plan'],cutoff,
                                      model_provenance,order=order,deadline=deadline)
            call=_model_result(call_model('answer',q,context.sources,cell,deadline),'answer',q,context.sources)
            if call['summary']['status']=='completed':
                codecs.need(call['summary']['request_sha256']==codecs.digest(canonical(context.request)),
                            'Actual answer request differs from admitted context')
                prediction=call['summary']['decoded'];decision=admission.check(context,prediction,context.request)
                row=dict(id=q['id'],producer_status='produced',check_status='accepted' if decision['accepted'] else 'rejected',
                         prediction=prediction,reason=decision['reason'])
            else:
                decision=None
                row=dict(id=q['id'],producer_status='parse_failure' if call['summary']['status']=='codec_failure' else 'input_unavailable',
                         check_status='not_run',prediction=None,reason=call['summary']['status'])
            publish_bytes(cell/'CONTEXT.json',canonical(context.report))
            return dict(status='completed',reason=None,product=dict(call=call,disposition=row,decision=decision,
                context=proof(cell/'CONTEXT.json'),collection_receipt_sha256=collection['receipt']['sha256'],
                ranking_parent_sha256=codecs.digest(canonical(ranking)),order=order))
        for _ in stage.schedule:stage.call(operation)
        return stage.finish()
    except BaseException as error:
        if not stage.closed:
            try:stage.finish()
            except BaseException as secondary:error.add_note('Partial stage finalization: '+type(secondary).__name__)
        raise
