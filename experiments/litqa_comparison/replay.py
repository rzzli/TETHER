"""Source-inclusive reconstruction of SC04 phase products, without dispatch.

This maintained verifier is not the later independent scientific analysis.
It reconstructs every cross-stage edge, actual native request, raw-response
accounting, source selection and admission decision before allowing consumption.
"""
from pathlib import Path

from asof.journal import read_chain
from asof.serde import canonical,encode,parse_json,freeze
from asof.study import native
from experiments.labbench import model
from . import acquisition,admission,codecs,pipeline,transport


def load(path):return parse_json(Path(path).read_bytes())


def model_cell(root,task,query,items,model_info):
    root=Path(root).resolve()
    codecs.need(load(root/'INPUT.json')==encode(dict(task=task,query=query,items=items)),'Model cell input substitution')
    events=read_chain(root/'journal.jsonl');summary=load(root/'SUMMARY.json')
    expected_files={'INPUT.json','SUMMARY.json','journal.jsonl'}
    request=payload=None
    capacity=False
    try:
        request,payload=(transport.make_answer_request(query,items,model_info['provenance']) if task=='answer'
                         else transport.make_request(task,query,model_info['provenance'],items))
    except codecs.PayloadCapacityError:capacity=True
    if capacity:
        expected=dict(status='capacity',decoded=None,generation_entered=False,usage=None,
                      reservation_input_tokens=0,reservation_output_tokens=0,native_result=None)
        expected_events=['build_reserved','model_cell_completed']
    else:
        native_root=root/'native'
        codecs.need(canonical(load(native_root/'request.json'))==canonical(request) and
                    canonical(load(native_root/'payload.json'))==canonical(payload),'Rebuilt model request/payload differ')
        quote=load(native_root/'tokenization/result.json')
        raw=(native_root/'native-response.bin').read_bytes()
        try:
            verified=transport.verify_response(request,payload,quote,raw,alias=model_info['alias'],
                server_spec=model_info['spec'],bindings=model_info['bindings'])
            status='completed';decoded=verified['decoded'];terminal_name='result.json'
        except transport.OutputCodecError:
            status='codec_failure';decoded=None;terminal_name='failure.json'
        # This second read of the captured response is in memory, not another
        # inference call. It preserves usage even when only task decoding fails.
        wrapper,response,usage=native._native(raw,request,payload,model_info['alias'])
        tokens=model._token_result(quote,payload)
        codecs.need(wrapper['owner_pid']==quote['owner_pid']==model_info['owner_pid'],'Worker/quote/native owner mismatch')
        codecs.need((native_root/'tokenization/body.bin').read_bytes()==__import__('base64').b64decode(quote['body_base64'],validate=True),
                    'Original tokenizer body differs')
        codecs.need(canonical(load(native_root/'tokenization/request.json'))==canonical(quote['tokenizer_request']),
                    'Original tokenizer request differs')
        reserve=max(len(payload['prompt'].encode())+32,tokens)
        terminal=load(native_root/terminal_name)
        codecs.need(terminal['task']==task and terminal['request_sha256']==codecs.digest(canonical(request)) and
                    terminal['payload_sha256']==codecs.digest(canonical(payload)) and terminal['generation_entered'] is True
                    and canonical(terminal['measured_usage'])==canonical(usage) and
                    terminal['conservative_reserved_input_tokens']==reserve and terminal['conservative_reserved_output_tokens']==256,
                    'Native terminal input/accounting differs')
        if status=='completed':
            codecs.need(terminal['status']=='completed' and canonical(terminal['decoded'])==canonical(decoded),'Native success disposition')
        else:
            codecs.need(terminal['status']=='failed' and terminal['stage']=='verification' and terminal['error_type']=='OutputCodecError',
                        'Codec fallback cannot conceal integrity failure')
        expected=dict(status=status,decoded=decoded,generation_entered=True,usage=encode(usage),
                      reservation_input_tokens=reserve,reservation_output_tokens=256,native_result=pipeline.proof(native_root/terminal_name))
        terminal_event='structured_call_completed' if status=='completed' else 'structured_call_failed'
        expected_events=['build_reserved','structured_call_reserved','mcq_tokenize_attempt','mcq_tokenize_terminal',
                         'structured_generation_attempt',terminal_event,'model_cell_completed']
        codecs.need([e['event'] for e in events]==expected_events,'Exact native call event sequence')
        expected_reserved=dict(path=str(native_root),status='started',task=task,request_sha256=codecs.digest(canonical(request)),
            payload_sha256=codecs.digest(canonical(payload)),generation_entered=False,measured_usage=None,
            conservative_reserved_output_tokens=256,provider_cost_usd=0)
        codecs.need(encode(events[1]['details'])==expected_reserved,'Native reservation differs')
        codecs.need(encode(events[2]['details'])==dict(payload_sha256=codecs.digest(canonical(payload)),
            request_sha256=codecs.digest(canonical(quote['tokenizer_request'])),owner_pid=quote['owner_pid']), 'Tokenizer dispatch binding')
        codecs.need(encode(events[3]['details'])==dict(proof_sha256=codecs.digest(canonical(quote)),token_count=tokens,
            error_class=None,elapsed_seconds=quote['elapsed_seconds']),'Tokenizer terminal binding')
        codecs.need(encode(events[4]['details'])==dict(request_sha256=codecs.digest(canonical(request)),
            reservation=dict(input_tokens=reserve,output_tokens=256,cost_usd=0.0)),'Generation reservation differs')
        terminal_details=dict(result_sha256=codecs.digest(canonical(terminal)),request_sha256=codecs.digest(canonical(request))) if status=='completed' else terminal
        codecs.need(canonical(events[5]['details'])==canonical(terminal_details),'Native terminal journal binding')
        expected_files|={'native/request.json','native/payload.json','native/native-response.bin','native/'+terminal_name,
                         'native/tokenization/request.json','native/tokenization/result.json','native/tokenization/body.bin'}
    expected.update(task=task,query_sha256=codecs.digest(canonical(query)),items_sha256=codecs.digest(canonical(items)),
                    request_sha256=codecs.digest(canonical(request)) if request is not None else None,provider_cost_usd=0)
    codecs.need(canonical(summary)==canonical(expected),'Model summary does not reconstruct')
    codecs.need([e['event'] for e in events]==expected_events,'Model call events differ')
    codecs.need(encode(events[-1]['details'])==dict(summary_sha256=codecs.digest(canonical(summary)),status=summary['status']),
                'Model summary journal binding')
    # Answer admission adds one context file only after native completion.
    files={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if task=='answer':expected_files.add('CONTEXT.json')
    codecs.need(files==expected_files,'Unexpected/missing model cell artifact')
    return freeze(dict(summary=expected,summary_proof=pipeline.proof(root/'SUMMARY.json'),root=str(root)))


def phase(root,receipt_sha256,kind,queries,*,parents=None,policy=None,model_info=None,cutoff=None):
    root=Path(root).resolve();ids=[q['id'] for q in queries]
    rows=pipeline.parent_rows(root,receipt_sha256,kind,ids);by_id={q['id']:q for q in queries}
    parents={} if parents is None else parents
    for row in rows.values():
        q=by_id[row['id']];branch=row['branch'];cell=root/'products'/f'{row["ordinal"]:04d}'
        if kind=='expand':
            call=model_cell(cell,'expand',q,(),model_info);good=call['summary']['status']=='completed'
            expected=dict(status='completed' if good else 'fallback',reason=None if good else call['summary']['status'],
                product=dict(call=call,expansion=call['summary']['decoded'] if good else None,strategy='expanded' if good else 'lexical'))
        elif kind=='collect':
            expansion=parents['expand'][(q['id'],'shared')]
            strategy='expanded' if branch=='E' and expansion['status']=='completed' else 'lexical'
            plan=acquisition.plan(q,strategy,policy=policy,expansion=expansion['product']['expansion'] if strategy=='expanded' else None)
            receipt=pipeline.proof(cell/'RECEIPT.json')
            acquisition.verify(cell,receipt['sha256'],plan)
            expected=dict(status='completed',reason=None,product=dict(root=str(cell),receipt=receipt,plan=plan,
                manifest=pipeline.proof(cell/'MANIFEST.json'),expansion_available=expansion['status']=='completed',
                query_branch=branch,expansion_parent_sha256=codecs.digest(canonical(expansion))))
        elif kind=='rank':
            manifest,collection=pipeline._collection(parents['collect'][(q['id'],branch)])
            pool=manifest['pool']['pool']
            common=dict(collection_receipt_sha256=collection['receipt']['sha256'],pool_sha256=codecs.digest(canonical(pool)))
            if not pool:
                expected=dict(status='not_applicable',reason='empty eligible passage pool',product=dict(order=[],call=None,**common))
                codecs.need(not cell.exists(),'Empty pool unexpectedly dispatched a ranker')
            else:
                call=model_cell(cell,'rank',q,pool,model_info);good=call['summary']['status']=='completed'
                expected=dict(status='completed' if good else 'fallback',reason=None if good else call['summary']['status'],
                    product=dict(order=call['summary']['decoded'] if good else [p['rank_id'] for p in pool],call=call,**common))
        elif kind=='answer':
            manifest,collection=pipeline._collection(parents['collect'][(q['id'],branch[0])])
            ranking=parents['rank'][(q['id'],branch[0])]
            order=ranking['product']['order'] if branch.endswith('/R') else [p['rank_id'] for p in manifest['pool']['pool']]
            context=admission.capture(q,collection['root'],collection['receipt']['sha256'],collection['plan'],cutoff,
                                      model_info['provenance'],order=order)
            codecs.need(canonical(load(cell/'CONTEXT.json'))==canonical(context.report),'Admitted context does not reconstruct')
            call=model_cell(cell,'answer',q,context.sources,model_info)
            if call['summary']['status']=='completed':
                prediction=call['summary']['decoded'];decision=admission.check(context,prediction,context.request)
                disposition=dict(id=q['id'],producer_status='produced',check_status='accepted' if decision['accepted'] else 'rejected',
                                 prediction=prediction,reason=decision['reason'])
            else:
                decision=None
                disposition=dict(id=q['id'],producer_status='parse_failure' if call['summary']['status']=='codec_failure' else 'input_unavailable',
                                 check_status='not_run',prediction=None,reason=call['summary']['status'])
            expected=dict(status='completed',reason=None,product=dict(call=call,disposition=disposition,decision=decision,
                context=pipeline.proof(cell/'CONTEXT.json'),collection_receipt_sha256=collection['receipt']['sha256'],
                ranking_parent_sha256=codecs.digest(canonical(ranking)),order=order))
        else:raise ValueError('Unsupported replay phase')
        codecs.need(canonical({k:row[k] for k in ('status','reason','product')})==canonical(expected),'Cross-stage product substitution')
    return freeze(dict(status='verified',phase=kind,slots=len(rows),rows=rows,
                       scope='Source-inclusive maintained replay; scientific correctness evaluated separately.'))
