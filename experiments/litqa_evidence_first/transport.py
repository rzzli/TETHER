"""Single-use evidence-first calls using the shared owned-server transport.

The caller reserves the phase and supervises its process. This adapter owns one
exclusive call directory, request codec and terminal record, never a retry loop.
"""
import math
from pathlib import Path
import re
import time

from tether_engine.agents import Usage
from tether_engine.atomic import publish_bytes
from tether_engine.serde import canonical, encode, fingerprint, freeze
from tether_engine.study import native
from experiments.labbench import model as mcq
from . import contracts, model

CALL_SECONDS = 120


class OutputCodecError(ValueError):
    """Authenticated complete output fails the task codec only."""


class EvidenceFirstBackend(native.LocalBackend):
    backend_id = model.KIND

    def __init__(self, *, owner, request, payload, tokenization, output, deadline, alias):
        model.validate_binding(request,payload)
        mcq._server_binding(owner.spec,owner.bindings,request,alias)
        self.request,self.payload,self.tokenization = [freeze(encode(value))
            for value in (request,payload,tokenization)]
        contracts.need(type(deadline) in (int,float) and math.isfinite(deadline),'Invalid call deadline')
        self.deadline=min(deadline,time.monotonic()+CALL_SECONDS)
        native._remaining(self.deadline)
        super().__init__(f'http://{owner.spec.host}:{owner.spec.port}','simplified',
                         request['model_provenance'],alias,owner,output)
        count=mcq._token_result(self.tokenization,self.payload)
        contracts.need(self.tokenization['owner_pid']==self.pid and
                       self.tokenization['endpoint']==self.endpoint,'Tokenizer owner differs')
        reserve=max(len(self.payload['prompt'].encode('utf-8'))+32,count)
        contracts.need(reserve+self.payload['n_predict']<=self.request['configuration']['context_tokens'],
                       'Context reservation exceeded')
        self.reservation=Usage(reserve,self.payload['n_predict'],0.0)

    def quote(self,request,payload):
        native._remaining(self.deadline)
        contracts.need(not self._used,'Refinement call already consumed')
        model.validate_binding(request,payload)
        contracts.need(canonical(request)==canonical(self.request) and canonical(payload)==canonical(self.payload),
                       'Frozen refinement call differs')
        return self.reservation

    def _execution_deadline(self,start,timeout_seconds):
        return min(self.deadline,start+timeout_seconds)


def verify_response(request,payload,tokenization,raw,*,alias,server_spec,bindings):
    """Replay source-bound native bytes; decoding cannot hide integrity errors."""
    model.validate_binding(request,payload)
    mcq._server_binding(server_spec,bindings,request,alias)
    wrapper,response,usage=native._native(raw,request,payload,alias)
    count=mcq._token_result(tokenization,payload)
    contracts.need(wrapper['owner_pid']==tokenization['owner_pid'] and
                   wrapper['endpoint']==tokenization['endpoint'],'Response owner differs')
    contracts.need(usage.input_tokens==count,'Generation and exact token quote disagree')
    reserve=max(len(payload['prompt'].encode('utf-8'))+32,count)
    contracts.need(reserve+payload['n_predict']<=request['configuration']['context_tokens'],
                   'Replay context reservation exceeded')
    for key in ('grammar','cache_prompt'):
        contracts.need(key not in response['generation_settings'] or
                       canonical(response['generation_settings'][key])==canonical(payload[key]),
                       'Runtime setting differs: '+key)
    try:
        decoded=model.decode(request,response['content'].encode('utf-8'))
    except ValueError as error:
        raise OutputCodecError(str(error)) from error
    return freeze(dict(decoded=decoded,usage=usage,exact_prompt_tokens=count,
                       conservative_input_reservation=reserve))


def execute_once(owner,request,payload,*,output,journal,deadline,alias,execution_id):
    """Reserve before tokenization and preserve uncertain attempts without retry.

On any exception the controller must inspect this exact directory. A terminal
failure dominates a result file if its later journal publication failed.
"""
    request,payload=freeze(encode(request)),freeze(encode(payload))
    model.validate_binding(request,payload)
    contracts.need(isinstance(execution_id,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',execution_id),
                   'Explicit physical execution identity required')
    output=Path(output)
    output.mkdir(parents=False,exist_ok=False)
    started=time.monotonic()
    stage='reservation'
    state=dict(status='started',execution_id=execution_id,task=request['task'],
               request_sha256=fingerprint(request),payload_sha256=fingerprint(payload),
               generation_entered=False,measured_usage=None,provider_cost_usd=0,
               conservative_reserved_output_tokens=payload['n_predict'],call_seconds_cap=CALL_SECONDS)
    try:
        contracts.need(type(deadline) in (int,float) and math.isfinite(deadline),'Invalid absolute deadline')
        deadline=min(deadline,started+CALL_SECONDS)
        native._remaining(deadline)
        publish_bytes(output/'request.json',canonical(request))
        publish_bytes(output/'payload.json',canonical(payload))
        journal.append('refinement_call_reserved',path=str(output),**state)
        stage='tokenization'
        quote=mcq.tokenize_once(owner,payload,output=output/'tokenization',journal=journal,deadline=deadline)
        backend=EvidenceFirstBackend(owner=owner,request=request,payload=payload,tokenization=quote,
                                  output=output,deadline=deadline,alias=alias)
        reservation=backend.quote(request,payload)
        state['conservative_reserved_input_tokens']=reservation.input_tokens
        state['exact_prompt_tokens']=quote['token_count']
        stage='generation'
        journal.append('refinement_generation_attempt',execution_id=execution_id,
                       request_sha256=fingerprint(request),reservation=encode(reservation))
        state['generation_entered']=True
        generated=backend.generate(request,payload,timeout_seconds=native._remaining(deadline))
        # Usage must survive failure to persist the returned body. It is still
        # unverified until full replay; keep that distinction in the record.
        state['measured_usage']=encode(generated.usage) if generated.usage is not None else None
        state['usage_verified']=False
        stage='capture'
        publish_bytes(output/'native-response.bin',generated.content)
        stage='verification'
        result=verify_response(request,payload,quote,generated.content,alias=alias,
                               server_spec=owner.spec,bindings=owner.bindings)
        contracts.need(canonical(result['usage'])==canonical(generated.usage),'Reported/native usage differs')
        state.update(status='completed',decoded=encode(result['decoded']),usage_verified=True)
        native._remaining(deadline)
        stage='finalization'
        state['wall_seconds']=time.monotonic()-started
        publish_bytes(output/'result.json',canonical(state))
        journal.append('refinement_call_completed',execution_id=execution_id,
                       result_sha256=fingerprint(state),request_sha256=fingerprint(request))
        native._remaining(deadline)
        return freeze(state)
    except BaseException as error:
        state.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',
                     stage=stage,error_type=type(error).__name__,wall_seconds=time.monotonic()-started)
        try:
            publish_bytes(output/'failure.json',canonical(state))
            journal.append('refinement_call_failed',**state)
        except BaseException as secondary:
            error.add_note('Failure persistence: '+type(secondary).__name__)
        raise
