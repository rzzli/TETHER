"""One owned local free-text completion, with original wire bytes and no retry.

This adapter accepts only a generation projection, never an evaluator dataset.
It reuses the existing process owner, tokenizer and bounded HTTP transport, not
the multiple-choice request/response codec. The caller owns the frozen schedule,
server lifecycle and outer process watchdog. A token-limited output is a valid
fixed-budget observation; truncated input or uncertain transport is a failure.
"""
from collections.abc import Mapping
from dataclasses import asdict, dataclass
import hashlib
import math
from pathlib import Path
import re
import sys
import time

from tether_engine import agents, atomic, journal as journal_module, serde
from tether_engine.agents import Usage
from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import ContractError, canonical, encode, fingerprint, freeze, parse_json
from tether_engine.study import native
from experiments.labbench import model as shared
from . import data_views, prompts
from .data_views import _hash, _path, _read

KIND='alce_owned_free_text_call_v1'
MAX_PAYLOAD_BYTES=100*1024


def need(value,message):
    if not value:raise ContractError(message)


class ContextCapacityError(ContractError):
    """The unchanged complete input plus requested response cannot be admitted."""


@dataclass(frozen=True)
class Limits:
    context_tokens: int
    call_seconds: float

    def __post_init__(self):
        need(type(self.context_tokens) is int and 512<=self.context_tokens<=16384,
             'Explicit context within the qualified owned-server range required')
        need(type(self.call_seconds) in (int,float) and math.isfinite(self.call_seconds) and
             0<self.call_seconds<=3600,'Explicit finite call ceiling required')


def make_call(request,model_provenance,*,limits):
    """Freeze a prompt request and unrestricted free-text native payload."""
    request=prompts.validate_request(request)
    need(isinstance(limits,Limits),'Explicit generation resource limits required')
    model=native._model(model_provenance)
    need('asset_manifest_sha256' in model,'Model acquisition receipt binding required')
    config=request['configuration']
    need(config['max_new_tokens']<limits.context_tokens,'Response budget must leave input capacity')
    payload=dict(prompt=request['prompt'],seed=config['seed'],temperature=config['temperature'],
        top_p=config['top_p'],n_predict=config['max_new_tokens'],stop=['<|im_end|>'],
        stream=False,cache_prompt=False)
    need(len(canonical(payload))<=MAX_PAYLOAD_BYTES,'Complete native payload exceeds transport cap; no truncation')
    token_request=dict(content=payload['prompt'],add_special=True,parse_special=True,with_pieces=False)
    need(len(canonical(token_request))<=shared.MAX_TOKEN_REQUEST,'Complete tokenizer request exceeds cap; no truncation')
    call=dict(schema_version=1,kind=KIND,request=request,model_provenance=model,
              limits=asdict(limits),payload_sha256=fingerprint(payload))
    return freeze(call),freeze(payload)


def validate_call(call,payload):
    need(isinstance(call,Mapping) and set(call)=={'schema_version','kind','request','model_provenance','limits','payload_sha256'},
         'Exact free-text call fields required')
    need(type(call['schema_version']) is int and call['schema_version']==1 and call['kind']==KIND,'Free-text call identity')
    need(isinstance(call['limits'],Mapping) and set(call['limits'])=={'context_tokens','call_seconds'},'Exact limits required')
    expected,wire=make_call(call['request'],call['model_provenance'],limits=Limits(**call['limits']))
    need(canonical(expected)==canonical(call) and canonical(wire)==canonical(payload),'Full request/payload binding differs')
    return expected,wire


def _server(spec,bindings,call,alias):
    # This existing helper checks only assets/launcher identity, not the MCQ codec.
    shared._server_binding(spec,bindings,dict(model_provenance=call['model_provenance'],
        configuration={'context_tokens':call['limits']['context_tokens']}),native._alias(alias))


def _quote(quote,payload,call,*,pid,endpoint):
    count=shared._token_result(quote,payload)
    need(quote['owner_pid']==pid and quote['endpoint']==endpoint,'Tokenizer owner/endpoint differs')
    reserve=max(len(payload['prompt'].encode('utf-8'))+32,count)
    if count+payload['n_predict']>call['limits']['context_tokens']:
        raise ContextCapacityError('Exact prompt tokens plus response exceed context; no truncation')
    return count,Usage(reserve,payload['n_predict'],0.0)


class FreeTextBackend(native.LocalBackend):
    """Override only request quoting/deadline; keep the owned one-POST transport."""
    backend_id=KIND

    def __init__(self,*,owner,call,payload,tokenization,output,deadline,alias):
        self.call,self.payload=validate_call(call,payload)
        _server(owner.spec,owner.bindings,self.call,alias)
        need(type(deadline) in (int,float) and math.isfinite(deadline),'Finite inherited deadline required')
        self.deadline=deadline
        native._remaining(deadline)
        super().__init__(f'http://{owner.spec.host}:{owner.spec.port}','simplified',
            call['model_provenance'],alias,owner,output)
        self.exact_prompt_tokens,self.reservation=_quote(tokenization,self.payload,self.call,pid=self.pid,endpoint=self.endpoint)

    def quote(self,request,payload):
        native._remaining(self.deadline)
        need(not self._used,'Native free-text attempt already consumed')
        call,wire=validate_call(request,payload)
        need(canonical(call)==canonical(self.call) and canonical(wire)==canonical(self.payload),'Frozen free-text call changed')
        _server(self.owner.spec,self.owner.bindings,self.call,self.alias)
        return self.reservation

    def _execution_deadline(self,start,timeout_seconds):
        return min(self.deadline,start+timeout_seconds)


def _finish_reason(response,usage,payload):
    need(response.get('truncated') is False,'Native input was truncated or completeness is unknown')
    need(response.get('stop') is True,'Native completion has no terminal stop')
    for key in ('stopped_eos','stopped_word','stopped_limit'):
        need(key not in response or type(response[key]) is bool,'Invalid native stop flag')
    cause=response.get('stop_type')
    if cause is None:
        causes=[name for name in ('eos','word','limit') if response.get('stopped_'+name) is True]
        need(len(causes)==1,'Ambiguous native completion cause')
        cause=causes[0]
    need(cause in ('eos','word','limit'),'Unknown native completion cause')
    for name in ('eos','word','limit'):
        need('stopped_'+name not in response or response['stopped_'+name] is (name==cause),'Conflicting native stop causes')
    need(response.get('stopping_word')=='<|im_end|>' if cause=='word'
         else response.get('stopping_word') in (None,''),'Unexpected stopping word')
    if cause=='limit':need(usage.output_tokens==payload['n_predict'],'Token-limit completion differs from fixed output budget')
    return cause


def verify_response(call,payload,tokenization,raw,*,alias,server_spec,bindings,owner_pid):
    """Verify original bytes independently of the producer's decoded/usage claims."""
    call,payload=validate_call(call,payload)
    _server(server_spec,bindings,call,alias)
    spec=encode(server_spec)
    endpoint=f"http://{spec['host']}:{spec['port']}"
    need(type(owner_pid) is int and owner_pid>0,'Externally bound native owner PID required')
    count,reservation=_quote(tokenization,payload,call,pid=owner_pid,endpoint=endpoint)
    wrapper,body=native._wrapper(raw,call,payload)
    need(wrapper['owner_pid']==owner_pid and wrapper['endpoint']==endpoint,'Native wrapper owner differs')
    response=parse_json(body)
    need(isinstance(response,Mapping) and response.get('prompt')==payload['prompt'] and response.get('model')==alias,
         'Original native prompt/model echo differs')
    settings=response.get('generation_settings')
    required=('seed','temperature','top_p','n_predict','stop','stream')
    need(isinstance(settings,Mapping) and all(k in settings for k in required) and
         canonical({k:settings[k] for k in required})==canonical({k:payload[k] for k in required}),
         'Native free-text generation settings differ')
    need('cache_prompt' not in settings or settings['cache_prompt'] is False,'Native prompt cache setting differs')
    need(settings.get('grammar') in (None,'') and settings.get('json_schema') in (None,''),'Unexpected constrained-output codec')
    usage=native._usage(response)
    need(usage.input_tokens==count and usage.input_tokens<=reservation.input_tokens and
         usage.output_tokens<=reservation.output_tokens,'Native usage differs from exact quote/reservation')
    cause=_finish_reason(response,usage,payload)
    need(type(response.get('content')) is str,'Original free-text completion missing')
    decoded=prompts.decode_response(call['request'],response['content'])
    return freeze(dict(decoded=decoded,usage=encode(usage),exact_prompt_tokens=count,
        conservative_reservation=encode(reservation),finish_reason=cause,output_limit_reached=cause=='limit',
        input_truncated=False,raw_body_sha256=hashlib.sha256(body).hexdigest(),
        owner_pid=owner_pid,endpoint=endpoint,wire_elapsed_seconds=wrapper['elapsed_seconds']))


def _sources(end):
    return [_hash(Path(module.__file__).resolve(),end) for module in
            (sys.modules[__name__],prompts,shared,native,atomic,journal_module,serde,agents,data_views)]


def _unchanged(proofs,end):
    for p in proofs:_read(p,2*1024**2,end)


def _failure(root,journal,state,error):
    # Each retention route is attempted even if the other route cannot write.
    for name,action in [('failure record',lambda:publish_bytes(root/'FAILURE.json',canonical(state))),
                        ('failure journal',lambda:journal.append('alce_call_failed',**state))]:
        try:action()
        except BaseException as secondary:error.add_note(name+': '+type(secondary).__name__)


def execute_once(owner,call,payload,*,output,deadline,alias,execution_id):
    """Reserve before any tokenizer/generator dispatch; never reuse an attempt."""
    started=time.monotonic()
    call,payload=validate_call(call,payload)
    need(type(deadline) in (int,float) and math.isfinite(deadline),'Finite inherited deadline required')
    end=min(deadline,started+call['limits']['call_seconds'])
    native._remaining(end)
    need(isinstance(execution_id,str) and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',execution_id),
         'Explicit physical attempt identity required')
    root=_path(output)
    need(root.parent.is_dir(),'Existing output parent required')
    _server(owner.spec,owner.bindings,call,alias)
    for value in owner.bindings.values():
        p=_path(value)
        need(root!=p and root not in p.parents,'Output overlaps a bound model/runtime input')
    sources=_sources(end)
    owner_pid=native._check_owner(owner,owner.spec.port)
    journal=RunJournal(root,kind='build')
    closed=False;stage='reservation'
    state=dict(schema_version=1,kind='alce_free_text_attempt_v1',status='started',execution_id=execution_id,
        id=call['request']['id'],family=call['request']['family'],call_sha256=fingerprint(call),
        payload_sha256=fingerprint(payload),generation_entered=False,reported_usage=None,usage_verified=False,
        conservative_reservation=None,automatic_retries=0,provider_cost_usd=0,call_seconds_cap=call['limits']['call_seconds'])
    try:
        publish_bytes(root/'INPUT.json',canonical(dict(call=call,payload=payload,alias=alias,
            server_spec=encode(owner.spec),bindings={k:str(v) for k,v in owner.bindings.items()},owner_pid=owner_pid,sources=sources)))
        journal.append('alce_call_reserved',**state)
        stage='tokenization'
        quote=shared.tokenize_once(owner,payload,output=root/'tokenization',journal=journal,deadline=end)
        backend=FreeTextBackend(owner=owner,call=call,payload=payload,tokenization=quote,output=root,deadline=end,alias=alias)
        reservation=backend.quote(call,payload)
        need(backend.pid==owner_pid,'Owned process changed during tokenization')
        state.update(conservative_reservation=encode(reservation),exact_prompt_tokens=backend.exact_prompt_tokens)
        _unchanged(sources,end)
        stage='generation'
        journal.append('alce_generation_attempt',execution_id=execution_id,call_sha256=fingerprint(call),reservation=encode(reservation))
        state['generation_entered']=True
        generated=backend.generate(call,payload,timeout_seconds=native._remaining(end))
        state['reported_usage']=encode(generated.usage) if generated.usage is not None else None
        stage='capture'
        publish_bytes(root/'native-response.bin',generated.content)
        stage='verification'
        verified=verify_response(call,payload,quote,generated.content,alias=alias,server_spec=owner.spec,
                                 bindings=owner.bindings,owner_pid=owner_pid)
        need(canonical(verified['usage'])==canonical(state['reported_usage']),'Returned/native usage differs')
        native._check_owner(owner,owner.spec.port,owner_pid)
        _unchanged(sources,end)
        state.update(status='completed',usage_verified=True,verified=verified,wall_seconds=time.monotonic()-started)
        stage='finalization'
        publish_bytes(root/'RESULT.json',canonical(state))
        journal.append('alce_call_completed',execution_id=execution_id,result_sha256=fingerprint(state))
        journal.close();closed=True
        native._remaining(end)
        files={p.relative_to(root).as_posix():_hash(p,end) for p in sorted(root.rglob('*')) if p.is_file()}
        receipt=dict(schema_version=1,kind='alce_free_text_receipt_v1',status='completed',execution_id=execution_id,
            call_sha256=fingerprint(call),files=files,automatic_retries=0,scientific_correctness_evaluated=False,
            seal_elapsed_seconds=time.monotonic()-started)
        raw=canonical(receipt);publish_bytes(root/'RECEIPT.json',raw)
        native._remaining(end)
        return freeze(dict(root=str(root),receipt_sha256=hashlib.sha256(raw).hexdigest(),result=state))
    except BaseException as error:
        state.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',stage=stage,
                     error_type=type(error).__name__,wall_seconds=time.monotonic()-started)
        _failure(root,journal,state,error)
        raise
    finally:
        if not closed:
            primary=sys.exception()
            try:journal.close()
            except BaseException as secondary:
                if primary is not None:primary.add_note('Journal close: '+type(secondary).__name__)
                else:raise


def verify_attempt(root,receipt_sha256,*,call,payload,owner_pid,alias,server_spec,bindings,deadline):
    """Replay a completed attempt's bytes/usage; no scorer/model/dataset opens."""
    root=_path(root)
    need(type(receipt_sha256) is str and re.fullmatch('[0-9a-f]{64}',receipt_sha256),'External receipt digest required')
    need(type(deadline) in (int,float) and math.isfinite(deadline),'Finite verification deadline required')
    for name in ('FAILURE.json','DEADLINE.json','FINALIZATION-FAILED.json','native-failure-wrapper.json'):
        need(not (root/name).exists(),'Attempt contains a terminal failure marker')
    rp=dict(path=str(root/'RECEIPT.json'),bytes=(root/'RECEIPT.json').stat().st_size,sha256=receipt_sha256)
    receipt=parse_json(_read(rp,4*1024**2,deadline))
    need(set(receipt)=={'schema_version','kind','status','execution_id','call_sha256','files',
                        'automatic_retries','scientific_correctness_evaluated','seal_elapsed_seconds'} and
         type(receipt['schema_version']) is int and receipt['schema_version']==1 and
         receipt.get('kind')=='alce_free_text_receipt_v1' and receipt.get('status')=='completed' and
         type(receipt.get('automatic_retries')) is int and receipt['automatic_retries']==0 and
         receipt.get('call_sha256')==fingerprint(call) and receipt['scientific_correctness_evaluated'] is False,
         'Completed externally bound attempt required')
    expected={'INPUT.json','RESULT.json','journal.jsonl','native-response.bin',
              'tokenization/request.json','tokenization/body.bin','tokenization/result.json'}
    need(set(receipt['files'])==expected,'Closed successful attempt inventory differs')
    def membership():
        names={p.relative_to(root).as_posix() for p in root.rglob('*')}
        need(names==expected|{'RECEIPT.json','tokenization'},'Unclaimed file/directory in completed attempt')
    membership()
    captured={}
    for name,p in receipt['files'].items():
        need(p['path']==str(root/name),'Receipt member location differs')
        captured[name]=_read(p,4*1024**2,deadline)
    inputs=parse_json(captured['INPUT.json'])
    need(set(inputs)=={'call','payload','alias','server_spec','bindings','owner_pid','sources'} and
         canonical(inputs['call'])==canonical(call) and canonical(inputs['payload'])==canonical(payload) and
         inputs['owner_pid']==owner_pid and inputs['alias']==alias and
         canonical(inputs['server_spec'])==canonical(server_spec) and
         inputs['bindings']=={k:str(v) for k,v in bindings.items()},'External expected call/owner differs')
    need(inputs['sources']==_sources(deadline),'Current adapter/prompt/transport source differs')
    tokenization=parse_json(captured['tokenization/result.json'])
    need(captured['tokenization/request.json']==canonical(tokenization['tokenizer_request']) and
         hashlib.sha256(captured['tokenization/body.bin']).hexdigest()==tokenization['body_sha256'],'Original token capture differs')
    verified=verify_response(call,payload,tokenization,captured['native-response.bin'],alias=alias,
                             server_spec=server_spec,bindings=bindings,owner_pid=owner_pid)
    result=parse_json(captured['RESULT.json'])
    need(result.get('status')=='completed' and result.get('usage_verified') is True and
         result.get('generation_entered') is True and result['execution_id']==receipt['execution_id'] and
         result['call_sha256']==fingerprint(call) and result['payload_sha256']==fingerprint(payload) and
         canonical(result['verified'])==canonical(verified) and canonical(result['reported_usage'])==canonical(verified['usage']) and
         canonical(result['conservative_reservation'])==canonical(verified['conservative_reservation']) and
         result['exact_prompt_tokens']==verified['exact_prompt_tokens'],'Result/native accounting differs')
    need(set(result)=={'schema_version','kind','status','execution_id','id','family','call_sha256','payload_sha256',
        'generation_entered','reported_usage','usage_verified','conservative_reservation','automatic_retries',
        'provider_cost_usd','call_seconds_cap','exact_prompt_tokens','verified','wall_seconds'} and
        type(result['schema_version']) is int and result['schema_version']==1 and result['kind']=='alce_free_text_attempt_v1' and
        result['id']==call['request']['id'] and result['family']==call['request']['family'] and
        type(result['automatic_retries']) is int and result['automatic_retries']==0 and
        type(result['provider_cost_usd']) in (int,float) and result['provider_cost_usd']==0 and
        result['call_seconds_cap']==call['limits']['call_seconds'],'Exact terminal identity/scope differs')
    wall,seal=result['wall_seconds'],receipt['seal_elapsed_seconds']
    need(all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in (wall,seal)) and
         tokenization['elapsed_seconds']+verified['wire_elapsed_seconds']<=wall<=seal<call['limits']['call_seconds'],
         'Native/tokenizer/attempt clock relationship differs')
    events=read_chain(root/'journal.jsonl')
    need([e['event'] for e in events]==['build_reserved','alce_call_reserved','mcq_tokenize_attempt',
        'mcq_tokenize_terminal','alce_generation_attempt','alce_call_completed'],'Attempt lifecycle differs')
    need(events[-1]['details']==dict(execution_id=result['execution_id'],result_sha256=fingerprint(result)) and
         events[-2]['details']==dict(execution_id=result['execution_id'],call_sha256=fingerprint(call),
             reservation=verified['conservative_reservation']),'Terminal/dispatch journal binding differs')
    initial={k:v for k,v in result.items() if k not in ('verified','wall_seconds','exact_prompt_tokens')}
    initial.update(status='started',generation_entered=False,reported_usage=None,usage_verified=False,conservative_reservation=None)
    need(events[1]['details']==initial and events[2]['details']==dict(payload_sha256=fingerprint(payload),
        request_sha256=hashlib.sha256(captured['tokenization/request.json']).hexdigest(),owner_pid=owner_pid) and
        events[3]['details']==dict(proof_sha256=fingerprint(tokenization),token_count=verified['exact_prompt_tokens'],
            error_class=None,elapsed_seconds=tokenization['elapsed_seconds']),'Reservation/tokenizer journal binding differs')
    for p in receipt['files'].values():_read(p,4*1024**2,deadline)
    _unchanged(inputs['sources'],deadline)
    _read(rp,4*1024**2,deadline);membership();native._remaining(deadline)
    return freeze(dict(status='wire_and_usage_verified',result=result,receipt_sha256=receipt_sha256,
                       scientific_correctness_evaluated=False))
