"""SC05 phase integration with sealed all-case barriers and actor projections.

The outer controller owns processes, model assets and role-specific file access.
No keys, reference-paper annotations or scientific correctness enter this layer.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import time

from tether_engine.atomic import publish_bytes
from tether_engine.serde import canonical,encode,fingerprint,freeze,parse_json
from tether_engine.study.stable_read import checked_path,hash_file,read_file
from experiments.litqa_comparison.pipeline import proof
from . import admission,cells,collection,contracts,model,projection,schedule,selection
from .access import RoleAudit


def read(value,*,deadline=None):
    projection._proof(value);end=collection._end(deadline)
    path=Path(value['path']);raw=read_file(path,end,64*1024**2)
    contracts.need(len(raw)==value['bytes'] and contracts.codecs.digest(raw)==value['sha256'],'Phase product proof changed')
    return freeze(parse_json(raw))


@dataclass(frozen=True)
class NativeCaller:
    """Production bridge: every request goes through its reserved native cell."""
    owner: object
    alias: str
    audit: RoleAudit|None = None

    def __call__(self,descriptor,output,deadline):
        if self.audit is not None:
            contracts.need(type(self.audit) is RoleAudit,'Concrete actor audit required')
            with self.audit.actor(descriptor['task'],output):
                return self._call(descriptor,output,deadline)
        return self._call(descriptor,output,deadline)

    def _call(self,descriptor,output,deadline):
        common=dict(owner=self.owner,output=output,deadline=deadline,alias=self.alias,execution_id=descriptor['execution_id'])
        if descriptor['task']=='critic':
            contracts.need(set(descriptor)=={'task','query','prior','sources','model_provenance','execution_id'},'Critic actor projection')
            return cells.call_critic(descriptor['query'],descriptor['prior'],descriptor['sources'],descriptor['model_provenance'],**common)
        contracts.need(set(descriptor)=={'task','query','prior','critic','sources','model_provenance','execution_id',
            'prepared_member','control_sha256'},'Paired actor projection')
        return cells.call_pair_member(descriptor['query'],descriptor['prior'],descriptor['critic'],descriptor['sources'],
            descriptor['model_provenance'],descriptor['prepared_member'],descriptor['task'],control_sha256=descriptor['control_sha256'],**common)


def _cell_inputs(descriptor):
    result=dict(task=descriptor['task'],query=descriptor['query'],candidate_context=descriptor['prior'],
                sources=descriptor['sources'],model_provenance=descriptor['model_provenance'])
    if descriptor['task']!='critic':result.update(critique_context=descriptor['critic'],
        prepared_member=descriptor['prepared_member'],control_sha256=descriptor['control_sha256'])
    return freeze(result)


def _model_result(result,descriptor,root,end):
    contracts.need(isinstance(result,Mapping) and set(result)=={'summary','summary_proof','root'},'Reserved cell result contract')
    contracts.need(Path(result['root'])==root and Path(result['summary_proof']['path'])==root/'SUMMARY.json','Cell result root identity')
    summary=read(result['summary_proof'],deadline=end)
    contracts.need(canonical(summary)==canonical(result['summary']) and summary['task']==descriptor['task']
        and summary['execution_id']==descriptor['execution_id'] and summary['input_sha256']==fingerprint(_cell_inputs(descriptor)),
        'Cell actual task/input/reservation binding')
    contracts.need(canonical(parse_json(read_file(root/'INPUT.json',end,64*1024**2)))==canonical(_cell_inputs(descriptor)),
        'Cell exact actor-visible input projection')
    contracts.need(summary['status'] in ('completed','codec_failure','capacity') and summary['automatic_retry'] is False
        and summary['provider_cost_usd']==0,'Cell terminal status/spending')
    generated=summary['status']!='capacity'
    contracts.need(summary['generation_entered'] is generated,'Cell generation count/status')
    values=encode(schedule.zero_accounting());values['generation_calls']=int(generated)
    values['reserved_input_tokens']=summary['reservation_input_tokens'];values['reserved_output_tokens']=summary['reservation_output_tokens']
    native_proof=None
    if generated:
        usage=summary['usage'];contracts.need(isinstance(usage,Mapping) and set(usage)=={'input_tokens','output_tokens','cost_usd'}
            and usage['cost_usd']==0,'Measured native usage required')
        values.update(measured_input_tokens=usage['input_tokens'],measured_output_tokens=usage['output_tokens'])
        contracts.need(values['reserved_output_tokens']==model.CONFIG['n_predict'],'Native output reservation differs')
        native_proof=proof(checked_path(root,'native/native-response.bin'))
        contracts.need(summary['native_result'] is not None,'Native terminal proof missing')
        contracts.need(Path(summary['native_result']['path'])==root/'native'/('result.json' if summary['status']=='completed' else 'failure.json'),
                       'Native terminal proof must belong to this reserved cell')
        terminal=read(summary['native_result'],deadline=end)
        contracts.need(terminal['execution_id']==descriptor['execution_id'] and terminal['generation_entered'] is True,
                       'Native terminal execution identity')
    else:
        contracts.need(summary['usage'] is None and summary['decoded'] is None and summary['native_result'] is None,'Capacity cell cannot invent native output')
    values=schedule.accounting(values,descriptor['task'])
    if summary['status']!='completed':contracts.need(summary['decoded'] is None,'Unavailable native decode must be null')
    return freeze(result),values,native_proof


def _baseline(value,purpose):
    contracts.need(isinstance(value,projection.PreparedBaseline),'Verified baseline descriptor required')
    verified=projection.verify_baseline_projection(dict(root=value.root,receipt_sha256=value.receipt_sha256),value.manifest['schedule'])
    contracts.need(verified.manifest['purpose']==purpose and canonical(verified.manifest)==canonical(value.manifest),'Baseline immutable purpose/contents')
    return verified


def _parents(phase,descriptors,ids,purpose,end):
    descriptors={} if descriptors is None else descriptors
    contracts.need(set(descriptors)==set(schedule.PARENTS[phase]),'Exact required parent phases')
    result={}
    for name in schedule.PARENTS[phase]:
        descriptor=descriptors[name]
        contracts.need(isinstance(descriptor,Mapping) and set(descriptor)=={'root','receipt_sha256'},'Stage parent descriptor fields')
        verified=schedule.verify(descriptor['root'],descriptor['receipt_sha256'],expected_ids=ids,
            expected_phase=name,purpose=purpose,deadline=end)
        contracts.need(verified['report']['status']=='complete','Every parent case must be sealed before dispatch')
        result[name]={row['id']:row for row in verified['report']['rows']}
    return freeze(result)


def _critic(parent,case,end):
    product=parent['product'];query=case['query'];prior=case['candidate'];sources=case['original_selected_sources']
    value=read(product['critic'],deadline=end)
    expected=contracts.validate_critique(query,prior,value,sources)
    contracts.need(canonical(product['semantic_selection'])==canonical(selection.select_original(query,prior,expected)),
                   'Critique-only deterministic selection differs')
    return expected


def _collection_parent(parent,expected_projection,end):
    product=parent['product']
    contracts.need(canonical(product['query_projection'])==canonical(expected_projection),'Actual critic-term projection differs')
    if expected_projection['status']=='unavailable':
        contracts.need(parent['status']=='unavailable' and product['collection'] is None,'Unavailable critic cannot fabricate acquisition')
        return None
    contracts.need(parent['status']=='completed' and product['collection'] is not None,'Expected refinement acquisition is incomplete')
    descriptor=product['collection'];collection.verify(descriptor['root'],descriptor['receipt_sha256'],descriptor['plan'],deadline=end)
    contracts.need(canonical(descriptor['plan'])==canonical(expected_projection['plan']),'Actual refinement source plan differs')
    return descriptor


def _pair_inputs(product,case,model_provenance,end):
    query=read(product['query'],deadline=end);prior=read(product['prior'],deadline=end);critique=read(product['critic'],deadline=end)
    contracts.need(canonical(query)==canonical(case['query']) and canonical(prior)==canonical(case['candidate']),
                   'Prepared pair differs from fixed original candidate/query')
    contracts.validate_critique(query,prior,critique,case['original_selected_sources'])
    control=fingerprint(dict(query=query,candidate=prior,critique=critique))
    contracts.need(control==product['control_sha256'] and canonical(model_provenance)==canonical(product['model_provenance']),
                   'Prepared pair common control/model identity')
    context=admission.capture(query,case['original_collection'],product['refinement_collection'],product['cutoff'],
        control_sha256=control,unavailable_reason='refinement_query_unavailable' if product['refinement_collection'] is None else None,deadline=end)
    contracts.need(canonical(context.report)==canonical(read(product['context'],deadline=end)),'Prepared merged scientific context changed')
    expected=model.make_repair_pair(query,prior,critique,context.sources,model_provenance)
    pair={task:read(product[task],deadline=end) for task in ('repair','removal')}
    contracts.need(all(canonical(pair[task])==canonical(expected[task]) for task in pair),'Both pre-generation pair members must match')
    return query,prior,critique,context,freeze(pair)


def execute(phase,baseline,output,*,purpose,seconds,parents=None,cutoff=None,
            model_provenance=None,call_model=None,acquire_sources=None):
    """One complete phase, with durable per-cell failure and no implicit retry."""
    contracts.need(isinstance(baseline,projection.PreparedBaseline),'Prepared baseline required')
    ids=baseline.manifest['schedule'];stage=schedule.Stage(ids,phase,output,purpose=purpose,seconds=seconds)
    try:
        verified=_baseline(baseline,purpose);cases={case['id']:case for case in verified.cases}
        parent_rows=_parents(phase,parents,ids,purpose,stage.deadline)
        if phase in ('critic','repair','removal'):
            contracts.need(callable(call_model),'Explicit reserved model-cell caller required')
            if purpose=='production':
                contracts.need(isinstance(call_model,NativeCaller) and type(call_model.audit) is RoleAudit
                    and call_model.audit.active,'Production requires owned reserved native cells and an active actor audit')
        if acquire_sources is not None:contracts.need(purpose=='fictional_qualification','Injected acquisition is fictional-only')
        acquire=collection.acquire if acquire_sources is None else acquire_sources
        if phase=='pair_prepare':
            cutoff=admission._utc(cutoff).isoformat()
            contracts.need(model_provenance is not None,'Prospective pair model identity required')
        # Scope metadata is coordinator-only. Model actor projections below
        # contain only their own ID's controls and their own raw-passage list.
        publish_bytes(stage.root/'INPUTS.json',canonical(dict(baseline=dict(root=verified.root,receipt_sha256=verified.receipt_sha256),
            parents={} if parents is None else parents,cutoff=cutoff,model_provenance=model_provenance,
            reference_keys_available=False,scoring_performed=False)))

        def operation(slot,end):
            case=cases[slot['id']];query=case['query'];prior=case['candidate'];sources=case['original_selected_sources']
            root=stage.root/'products'/f'{slot["ordinal"]:04d}';deadline=min(end,time.monotonic()+120)
            if phase=='critic':
                descriptor=freeze(dict(task='critic',query=query,prior=prior,sources=sources,
                    model_provenance=model_provenance,execution_id=slot['execution_id']))
                call,usage,native_proof=_model_result(call_model(descriptor,root,deadline),descriptor,root,deadline)
                summary=call['summary']
                if summary['status']=='completed':
                    expected,_=model.make_critic_request(query,prior,sources,model_provenance)
                    contracts.need(summary['request_sha256']==fingerprint(expected),'Actual critic request differs from original source/control context')
                critique=contracts.critique(query,prior,sources,summary['decoded'],native_status=summary['status'],
                    native_call_sha256=None if native_proof is None else native_proof['sha256'])
                publish_bytes(root/'CRITIC.json',canonical(critique))
                return dict(status=summary['status'],reason=None if summary['status']=='completed' else 'critic_'+summary['status'],
                    product=dict(call=call,native_proof=native_proof,critic=proof(root/'CRITIC.json'),
                                 semantic_selection=selection.select_original(query,prior,critique)),accounting=usage)
            if phase=='refinement_collect':
                critique=_critic(parent_rows['critic'][query['id']],case,deadline)
                projected=collection.from_critic(query,prior,critique,sources,policy=case['original_collection']['plan']['policy'])
                if projected['status']=='unavailable':
                    return dict(status='unavailable',reason=projected['reason'],
                        product=dict(query_projection=projected,collection=None),accounting=schedule.zero_accounting())
                acquire(projected['plan'],root,deadline=deadline)
                receipt=proof(root/'RECEIPT.json');manifest=collection.verify(root,receipt['sha256'],projected['plan'],deadline=deadline)
                usage=encode(schedule.zero_accounting());usage.update(source_http_requests=manifest['request_count'],
                    measured_response_bytes=manifest['accounting']['measured_response_bytes'],
                    safety_accounted_bytes=manifest['accounting']['safety_accounted_bytes'])
                return dict(status='completed',reason=None,product=dict(query_projection=projected,
                    collection=dict(root=str(root),receipt_sha256=receipt['sha256'],plan=projected['plan'])),accounting=usage)
            if phase=='pair_prepare':
                root.mkdir(parents=True,exist_ok=False)
                critique=_critic(parent_rows['critic'][query['id']],case,deadline)
                projected=collection.from_critic(query,prior,critique,sources,policy=case['original_collection']['plan']['policy'])
                refinement=_collection_parent(parent_rows['refinement_collect'][query['id']],projected,deadline)
                control=fingerprint(dict(query=query,candidate=prior,critique=critique))
                context=admission.capture(query,case['original_collection'],refinement,cutoff,control_sha256=control,
                    unavailable_reason='refinement_query_unavailable' if refinement is None else None,deadline=deadline)
                pair=model.make_repair_pair(query,prior,critique,context.sources,model_provenance)
                values=dict(QUERY=query,PRIOR=prior,CRITIC=critique,CONTEXT=context.report,REPAIR=pair['repair'],REMOVAL=pair['removal'])
                for name,value in values.items():publish_bytes(root/(name+'.json'),canonical(value))
                return dict(status='completed',reason=None,product=dict(query=proof(root/'QUERY.json'),prior=proof(root/'PRIOR.json'),
                    critic=proof(root/'CRITIC.json'),context=proof(root/'CONTEXT.json'),repair=proof(root/'REPAIR.json'),removal=proof(root/'REMOVAL.json'),
                    control_sha256=control,refinement_collection=refinement,cutoff=cutoff,model_provenance=model_provenance),
                    accounting=schedule.zero_accounting())
            product=parent_rows['pair_prepare'][query['id']]['product']
            query,prior,critique,context,pair=_pair_inputs(product,case,model_provenance,deadline)
            current=context.sources if phase=='repair' else ()
            descriptor=freeze(dict(task=phase,query=query,prior=prior,critic=critique,sources=current,
                model_provenance=model_provenance,prepared_member=pair[phase],control_sha256=context.control_sha256,
                execution_id=slot['execution_id']))
            call,usage,native_proof=_model_result(call_model(descriptor,root,deadline),descriptor,root,deadline)
            summary=call['summary'];decision=None
            if summary['status']=='completed':
                member=pair[phase];contracts.need(member['status']=='ready' and summary['request_sha256']==fingerprint(member['request']),
                                                'Actual native request differs from frozen paired request')
                decision=admission.check(context,summary['decoded'],member['request'],task=phase,
                    expected_control_sha256=context.control_sha256,payload=member['payload'],deadline=deadline)
                disposition=dict(id=query['id'],producer_status='produced',check_status='accepted' if decision['accepted'] else 'rejected',
                    prediction=summary['decoded'],reason=decision['reason'])
            else:
                disposition=dict(id=query['id'],producer_status='parse_failure' if summary['status']=='codec_failure' else 'input_unavailable',
                    check_status='not_run',prediction=None,reason=summary['status'])
            publish_bytes(root/'DECISION.json',canonical(decision))
            return dict(status=summary['status'],reason=None if summary['status']=='completed' else summary['status'],
                product=dict(call=call,native_proof=native_proof,disposition=disposition,decision=proof(root/'DECISION.json'),
                    paired_member_sha256=fingerprint(pair[phase]),control_sha256=context.control_sha256,
                    source_context_sha256=fingerprint(context.report)),accounting=usage)

        for _ in stage.config['schedule']:stage.call(operation)
        return stage.finish()
    except BaseException as error:
        if not stage.closed:
            try:
                publish_bytes(stage.root/'FAILURE.json',canonical(dict(error_type=type(error).__name__,automatic_retry=False)))
                stage.finish()
            except BaseException as failure:error.add_note('Stage failure persistence: '+type(failure).__name__)
        raise
