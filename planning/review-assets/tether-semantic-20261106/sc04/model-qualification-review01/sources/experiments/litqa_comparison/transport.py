"""One-shot local transport for the new expansion/ranking codecs.

Reuses the pinned owned-server, native HTTP capture and exact tokenization
implementation. It does not reinterpret the archived MCQ contract. A caller
must supervise the outer worker and own scheduling, shared budgets and fallback.
"""
import math
from pathlib import Path
import time

from asof.agents import Usage
from asof.atomic import publish_bytes
from asof.serde import canonical, encode, fingerprint, freeze
from asof.study import native
from experiments.labbench import model
from . import codecs


KIND = 'sc04_structured_local_v1'


def make_request(task, question, model_provenance, pool=()):
    question = codecs.question_view(question)
    codecs.need(task in ('expand','rank'),'Unknown structured task')
    pool = codecs.validate_pool(pool)
    codecs.need(task != 'expand' or not pool,'Expansion cannot receive passages')
    payload = codecs.expansion_payload(question) if task == 'expand' else codecs.ranking_payload(question,pool)
    request = freeze(dict(schema_version=1,kind=KIND,task=task,query=question,pool=pool,
        configuration=codecs.CONFIG,model_provenance=native._model(model_provenance),payload_sha256=fingerprint(payload)))
    return request,payload


def validate_binding(request,payload):
    codecs.need(set(request) == {'schema_version','kind','task','query','pool','configuration','model_provenance','payload_sha256'},
                'Structured request fields')
    expected, rebuilt = make_request(request['task'],request['query'],request['model_provenance'],request['pool'])
    codecs.need(canonical(expected) == canonical(request) and canonical(rebuilt) == canonical(payload),'Structured request binding')


class StructuredBackend(native.LocalBackend):
    backend_id = KIND

    def __init__(self, *, owner, request, payload, tokenization, output, deadline, alias):
        validate_binding(request,payload)
        model._server_binding(owner.spec,owner.bindings,request,alias)
        self.request,self.payload,self.tokenization = [freeze(encode(x)) for x in (request,payload,tokenization)]
        self.deadline = deadline
        native._remaining(deadline)
        super().__init__(f'http://{owner.spec.host}:{owner.spec.port}','simplified',request['model_provenance'],alias,owner,output)
        count = model._token_result(tokenization,payload)
        codecs.need(tokenization['owner_pid'] == self.pid and tokenization['endpoint'] == self.endpoint,'Tokenizer owner differs')
        reserve = max(len(payload['prompt'].encode())+32,count)
        codecs.need(reserve+payload['n_predict'] <= request['configuration']['context_tokens'],'Context reservation exceeded')
        self.reservation = Usage(reserve,payload['n_predict'],0.0)

    def quote(self,request,payload):
        native._remaining(self.deadline)
        codecs.need(not self._used,'Structured call already consumed')
        validate_binding(request,payload)
        codecs.need(canonical(request) == canonical(self.request) and canonical(payload) == canonical(self.payload),'Frozen call differs')
        return self.reservation

    def _execution_deadline(self,start,timeout_seconds):
        return min(self.deadline,start+timeout_seconds)


def verify_response(request,payload,tokenization,raw,*,alias,server_spec,bindings):
    validate_binding(request,payload)
    model._server_binding(server_spec,bindings,request,alias)
    wrapper,response,usage = native._native(raw,request,payload,alias)
    count = model._token_result(tokenization,payload)
    codecs.need(wrapper['owner_pid'] == tokenization['owner_pid'] and wrapper['endpoint'] == tokenization['endpoint'], 'Response owner differs')
    codecs.need(usage.input_tokens == count,'Generation and exact token quote disagree')
    reserve = max(len(payload['prompt'].encode())+32,count)
    codecs.need(reserve+payload['n_predict'] <= request['configuration']['context_tokens'],'Replay context reservation exceeded')
    for key in ('grammar','cache_prompt'):
        codecs.need(key not in response['generation_settings'] or
            canonical(response['generation_settings'][key]) == canonical(payload[key]),'Runtime setting differs: '+key)
    raw_answer = response['content'].encode('utf-8')
    decoded = codecs.parse_expansion(raw_answer) if request['task'] == 'expand' else codecs.parse_ranking(raw_answer,request['pool'])
    return freeze(dict(decoded=decoded,usage=usage,exact_prompt_tokens=count,conservative_input_reservation=reserve))


def execute_once(owner,request,payload,*,output,journal,deadline,alias):
    """Reserve before tokenization; retain attempts and native bytes on failure.

    Failure is raised to the controller. It may use a prospectively declared
    lexical fallback, but must never redispatch this uncertain call.
    """
    validate_binding(request,payload)
    output=Path(output)
    output.mkdir(parents=False,exist_ok=False)
    started=time.monotonic()
    stage='reservation'
    state=dict(status='started',task=request['task'],request_sha256=fingerprint(request),
               payload_sha256=fingerprint(payload),generation_entered=False,measured_usage=None,
               conservative_reserved_output_tokens=payload['n_predict'],provider_cost_usd=0)
    try:
        codecs.need(type(deadline) in (int,float) and math.isfinite(deadline),'Invalid absolute deadline')
        native._remaining(deadline)
        publish_bytes(output/'request.json',canonical(request))
        publish_bytes(output/'payload.json',canonical(payload))
        journal.append('structured_call_reserved',path=str(output),**state)
        stage='tokenization'
        quote=model.tokenize_once(owner,payload,output=output/'tokenization',journal=journal,deadline=deadline)
        backend=StructuredBackend(owner=owner,request=request,payload=payload,tokenization=quote,
                                  output=output,deadline=deadline,alias=alias)
        reservation=backend.quote(request,payload)
        state['conservative_reserved_input_tokens']=reservation.input_tokens
        state['exact_prompt_tokens']=quote['token_count']
        stage='generation'
        journal.append('structured_generation_attempt',request_sha256=fingerprint(request),reservation=encode(reservation))
        state['generation_entered']=True
        generated=backend.generate(request,payload,timeout_seconds=native._remaining(deadline))
        publish_bytes(output/'native-response.bin',generated.content)
        state['measured_usage']=encode(generated.usage) if generated.usage is not None else None
        stage='verification'
        result=verify_response(request,payload,quote,generated.content,alias=alias,
                               server_spec=owner.spec,bindings=owner.bindings)
        codecs.need(canonical(result['usage']) == canonical(generated.usage),'Reported/native usage differs')
        state.update(status='completed',decoded=encode(result['decoded']))
        native._remaining(deadline)
        stage='finalization'
        state['wall_seconds']=time.monotonic()-started
        publish_bytes(output/'result.json',canonical(state))
        journal.append('structured_call_completed',result_sha256=fingerprint(state),request_sha256=fingerprint(request))
        native._remaining(deadline)
        return freeze(state)
    except BaseException as error:
        state.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',
                     stage=stage,error_type=type(error).__name__,wall_seconds=time.monotonic()-started)
        try:
            publish_bytes(output/'failure.json',canonical(state))
            journal.append('structured_call_failed',**state)
        except BaseException as secondary:
            error.add_note('Failure persistence: '+type(secondary).__name__)
        raise
