"""Reserved critic/repair cells with explicit codec and capacity dispositions.

Only complete native codec failures and known prompt capacity failures may
continue. Transport, integrity and interruption failures terminate the attempt.
"""
from pathlib import Path

from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal
from tether_engine.serde import canonical, encode, freeze, parse_json, fingerprint
from experiments.litqa_comparison.codecs import PayloadCapacityError
from experiments.litqa_comparison.pipeline import proof
from . import contracts, model, transport


def _execute(inputs,build,*,owner,output,deadline,alias,execution_id):
    journal=RunJournal(Path(output),kind='build');root=journal.output
    request=payload=None
    try:
        publish_bytes(root/'INPUT.json',canonical(inputs))
        journal.append('refinement_cell_reserved',execution_id=execution_id,task=inputs['task'],
                       input_sha256=fingerprint(inputs))
        try:
            request,payload=build()
            result=transport.execute_once(owner,request,payload,output=root/'native',journal=journal,
                                          deadline=deadline,alias=alias,execution_id=execution_id)
            summary=dict(status='completed',decoded=result['decoded'],generation_entered=True,
                         usage=result['measured_usage'],reservation_input_tokens=result['conservative_reserved_input_tokens'],
                         reservation_output_tokens=payload['n_predict'],native_result=proof(root/'native/result.json'))
        except PayloadCapacityError:
            summary=dict(status='capacity',decoded=None,generation_entered=False,usage=None,
                         reservation_input_tokens=0,reservation_output_tokens=0,native_result=None)
        except transport.OutputCodecError:
            failure=parse_json((root/'native/failure.json').read_bytes())
            contracts.need(failure['stage']=='verification' and failure['generation_entered'] and
                           failure['measured_usage'] is not None and failure['execution_id']==execution_id,
                           'Recoverable codec failure lacks native accounting')
            summary=dict(status='codec_failure',decoded=None,generation_entered=True,usage=failure['measured_usage'],
                         reservation_input_tokens=failure['conservative_reserved_input_tokens'],
                         reservation_output_tokens=payload['n_predict'],native_result=proof(root/'native/failure.json'))
        summary.update(task=inputs['task'],execution_id=execution_id,input_sha256=fingerprint(inputs),
                       request_sha256=fingerprint(request) if request is not None else None,provider_cost_usd=0,
                       automatic_retry=False,scientific_correctness='unevaluated')
        publish_bytes(root/'SUMMARY.json',canonical(summary))
        journal.append('refinement_cell_completed',execution_id=execution_id,
                       summary_sha256=fingerprint(summary),status=summary['status'])
        return freeze(dict(summary=summary,summary_proof=proof(root/'SUMMARY.json'),root=str(root)))
    except BaseException as error:
        try:
            journal.fail(error,'refinement_cell')
            publish_bytes(root/'FAILURE.json',canonical(dict(error_type=type(error).__name__,
                          execution_id=execution_id,automatic_retry=False)))
        except BaseException as secondary:error.add_note('Cell failure persistence: '+type(secondary).__name__)
        raise
    finally:journal.close()


def call_critic(query,prior,sources,model_provenance,*,owner,output,deadline,alias,execution_id):
    inputs=freeze(dict(task='critic',query=query,candidate_context=prior,sources=sources,
                       model_provenance=model_provenance))
    return _execute(inputs,lambda:model.make_critic_request(inputs['query'],inputs['candidate_context'],
                    inputs['sources'],inputs['model_provenance']),
                    owner=owner,output=output,deadline=deadline,alias=alias,execution_id=execution_id)


def call_pair_member(query,prior,critique,sources,model_provenance,prepared_member,task,*,
                     control_sha256,owner,output,deadline,alias,execution_id):
    """Execute only this member of the coordinator's pre-generation frozen pair.

    The coordinator pins both members before either dispatch. The removal actor
    receives neither the factual member nor its raw sources or generated answer.
    Its own common control hash and request are reconstructed independently.
    """
    inputs=freeze(dict(task=task,query=query,candidate_context=prior,critique_context=critique,
                       sources=sources,model_provenance=model_provenance,prepared_member=prepared_member,
                       control_sha256=control_sha256))
    def build():
        task=inputs['task'];query=inputs['query'];prior=inputs['candidate_context'];critique=inputs['critique_context']
        sources=inputs['sources'];prepared_member=inputs['prepared_member'];model_provenance=inputs['model_provenance']
        contracts.need(task in ('repair','removal'),'Unknown paired member')
        contracts.need(task!='removal' or not sources,'Removal actor cannot receive raw evidence')
        contracts.need(inputs['control_sha256']==fingerprint(dict(query=query,candidate=prior,critique=critique)),
                       'Common pre-generation control context differs')
        contracts.need(set(prepared_member)=={'status','request','payload'},'Frozen member fields')
        try:
            request,payload=model._request(task,query,prior,critique,sources,model_provenance)
        except PayloadCapacityError:
            contracts.need(canonical(prepared_member)==canonical(dict(status='capacity',request=None,payload=None)),
                           'Frozen capacity disposition differs')
            raise
        contracts.need(canonical(prepared_member)==canonical(dict(status='ready',request=request,payload=payload)),
                       'Pre-generation member differs')
        return request,payload
    return _execute(inputs,build,owner=owner,output=output,deadline=deadline,alias=alias,execution_id=execution_id)
