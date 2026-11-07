"""One-shot, bounded continuation of untouched paired refinement calls.

The original producer remains immutable. This controller performs no acquisition,
critique, pair preparation or scoring. Captured limit failures are retained as
null outcomes only after separate authentication; all other faults stop work.
"""
import argparse
from collections.abc import Mapping
from pathlib import Path
import os
import sys
import time
from uuid import uuid4

from tether._process import ProcessLimits,validate_success_report
from tether_engine.journal import RunJournal,read_chain
from tether_engine.serde import ContractError,canonical,encode,freeze,parse_json
from experiments.labbench import model as native_model
from experiments.labbench.runtime import contain_process_tree,DeadlineWatchdog,ProcessSamples,process_sample
from experiments.litqa_comparison.pipeline import proof
from experiments.litqa_comparison.run import inventory
from experiments.litqa_refinement import admission,model,pipeline,projection,schedule
from experiments.litqa_refinement import run as previous
from experiments.litqa_refinement.access import RoleAudit
from . import contracts as c,plan,native_failure

ROOT=Path(__file__).resolve().parents[2]
KIND='sc05_refinement_recovery_frame_v2'
FRAME_FIELDS={'schema_version','kind','purpose','parent','plan','authority','code_files','qualification','output'}


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    return c.write(path,encode(value))


def code_files():
    paths={p['path']:p for p in previous.code_files()}
    # The independent parent reader is part of the admission dependency closure.
    for folder in ('experiments/litqa_refinement_recovery','experiments/litqa_analysis','experiments/litqa_refinement'):
        for item in (ROOT/folder).glob('*.py'):
            if not item.name.startswith('test_'):paths[str(item)]=proof(item)
    return sorted(paths.values(),key=lambda item:item['path'])


def coordinator_grants(baseline,parent_pair,original_frame):
    grants={item['path']:item for item in previous._grants(baseline,{'pair_prepare':parent_pair})}
    c.need(Path(original_frame['path'])==Path(parent_pair['root']).parent/'FRAME.json','Original external phase frame location differs')
    c.capture(original_frame['path'],original_frame)
    prior=grants.get(original_frame['path']);c.need(prior is None or canonical(prior)==canonical(original_frame),'Conflicting original metadata grant')
    grants[original_frame['path']]=original_frame
    return [grants[key] for key in sorted(grants)]


def preflight_request(path,expected,output):
    """Bounded metadata only; these clocks can restrict but never authorize work."""
    fp,raw=c.capture(c.path(path));c.need(fp['sha256']==expected,'External recovery frame anchor')
    frame=freeze(parse_json(raw));c.need(set(frame)==FRAME_FIELDS and frame['schema_version']==2 and frame['kind']==KIND,'Recovery frame fields/version')
    destination=c.path(output)
    c.need(destination==c.path(frame['output']) and destination.is_relative_to(ROOT/'data') and destination!=ROOT/'data'
        and not destination.exists() and destination.parent.is_dir(),'Fresh recovery data destination required')
    value=c.read(frame['plan']);limits=value['budgets']
    c.need(frame['parent']==value['parent'],'Preflight parent descriptor differs')
    inspection=c.read(frame['parent']['inspection']);inspection_root=Path(frame['parent']['inspection']['path']).parent
    c.need(inspection['kind']=='sc05_failed_production_metadata_audit_receipt_v1' and inspection['status']=='complete',
        'Preflight requires externally anchored original-root metadata')
    report_proof=inspection['files']['RESULT.json'];c.need(Path(report_proof['path'])==inspection_root/'RESULT.json','Inspection report path')
    report=c.read(report_proof)
    c.need(report['kind']=='sc05_failed_production_metadata_forensics_v1' and report['status']=='metadata_and_byte_inventory_verified'
        and report['original_root']==value['original_root'],'Preflight preserved parent root differs')
    baseline=frame['parent']['baseline_acceptance']
    protected=(c.path(value['original_root']),c.path(report['freeze_root']),c.path(frame['authority']['path']).parent,inspection_root,
        c.path(frame['parent']['source_archive']['path']).parent,c.path(baseline['replay_root']),c.path(baseline['analyzer_archive']['path']).parent)
    for original in protected:
        c.need(not destination.is_relative_to(original) and not original.is_relative_to(destination),'Preflight cannot mutate preserved original/authority inputs')
    phase=limits['phase_remaining_seconds']['repair'];outer=limits['outer_remaining_seconds']
    c.need(type(phase) is int and 0<phase<=7200 and type(outer) is int and 0<outer<=43200,
        'Preflight bounds cannot exceed original absolute caps')
    for item in (fp,frame['plan']):c.need(not Path(item['path']).is_relative_to(destination),'Preflight input/output overlap')
    return frame,fp,raw,destination,freeze(dict(repair_seconds=phase,outer_seconds=outer))


def load_frame(path,expected,output,*,reservation=None):
    fp,raw=c.capture(c.path(path));c.need(fp['sha256']==expected,'External recovery frame anchor')
    frame=freeze(parse_json(raw));c.need(set(frame)==FRAME_FIELDS and frame['schema_version']==2 and frame['kind']==KIND,'Recovery frame fields/version')
    value,authority,verified=plan.verify(frame['plan'],frame['authority'],return_parent=True)
    c.need(frame['parent']==value['parent'] and frame['purpose']==value['purpose'],'Recovery parent/purpose binding')
    c.need(canonical(frame['code_files'])==canonical(code_files()),'Current recovery source closure changed')
    destination=c.path(output)
    c.need(destination==c.path(frame['output']) and destination.is_relative_to(ROOT/'data') and destination!=ROOT/'data'
        and destination.parent.is_dir() and ((reservation is None and not destination.exists()) or
            (type(reservation) is RunJournal and reservation.output==destination and not reservation._stream.closed)),
        'Fresh or actively reserved recovery data destination required')
    original=c.read(value['original_frame'])
    c.need(canonical(original['interpreter'])==canonical(proof(sys.executable)) and
        canonical(original['generation_configuration'])==canonical(model.CONFIG),'Original interpreter/settings required')
    if frame['purpose']=='production':
        qualification=c.read(frame['qualification'])
        c.need(qualification['kind']=='sc05_refinement_recovery_qualification_v2' and qualification['status']=='passed'
            and qualification['parent_identity']==value['parent_identity'] and qualification['code_files']==frame['code_files']
            and qualification['model_provenance']==original['model_provenance'] and qualification['native_tasks']==('repair','removal')
            and qualification['automatic_retry'] is False,'Current recovery source/native qualification required')
    else:c.need(frame['qualification'] is None,'Invented qualification cannot inherit production claim')
    for source in (fp,frame['plan'],frame['authority'],value['original_frame'],*frame['code_files']):
        c.need(not c.path(source['path']).is_relative_to(destination),'Recovery input/output overlap')
    c.need(not destination.is_relative_to(c.path(value['original_root'])) and
        not destination.is_relative_to(c.path(frame['authority']['path']).parent),'Recovery cannot mutate original/authority')
    return frame,fp,value,original,destination,verified


def _summary(rows,seconds,elapsed):
    known=[r['accounting'] for r in rows if r['accounting'] is not None]
    authenticated=[r for r in rows if r['status']=='authenticated_limit_failure']
    unknown=[r['id'] for r in rows if r['status'] in ('entered','failed','interrupted')]
    return freeze(dict(kind='sc05_recovery_stage_report_v2',status='complete' if elapsed<seconds and all(r['status'] in c.TERMINAL_STATUSES for r in rows) else 'incomplete',
        scheduled=len(rows),entered=sum(r['status']!='unexecuted' for r in rows),unexecuted=sum(r['status']=='unexecuted' for r in rows),
        rows=rows,wall_seconds=elapsed,automatic_retry=False,
        accounting=dict(known_totals={k:sum(a[k] for a in known) for k in schedule.ACCOUNT_FIELDS},provider_cost_usd=0,
            authenticated_limit_failures=len(authenticated),authenticated_limit_generation_calls=len(authenticated),
            raw_reported_unverified_usage=[r['product']['limit_failure'] for r in authenticated],
            unqualified_usage_cells=[r['id'] for r in authenticated],uncertain_cells=unknown,
            uncertain_per_cell_ceiling=c.CELL_LIMITS,measurements_complete=not authenticated and not unknown,
            historical_work_included=False)))


class RecoveryStage:
    """Durable selected original ordinals; an entered slot is never repeated."""
    def __init__(self,ids,phase,ordinals,output,*,purpose,seconds,original_slots,clock=time.monotonic):
        c.schedule(ids,purpose);c.need(phase in c.PHASES,'Recovery final phase only')
        c.need(tuple(ordinals)==tuple(sorted(set(ordinals))) and all(type(i) is int and 0<=i<len(ids) for i in ordinals),'Unique ordered recovery ordinals')
        c.need(c.finite(seconds,'stage seconds')>0,'Positive stage budget')
        self.clock=clock;self.started=clock();self.deadline=self.started+seconds;self.closed=False;self.failed=False;self.cursor=0
        self.journal=RunJournal(Path(output),kind='build');self.root=self.journal.output
        namespace=str(uuid4());slots=[]
        for ordinal in ordinals:
            slots.append(dict(ordinal=ordinal,id=ids[ordinal],phase=phase,original_slot=original_slots[ordinal],
                execution_id=f'{namespace}-{phase}-{ordinal:04d}'))
        self.config=freeze(dict(kind='sc05_recovery_stage_v2',phase=phase,purpose=purpose,ids=ids,dispatch_ordinals=ordinals,
            execution_namespace=namespace,schedule=slots,seconds=seconds,cell_limits=c.CELL_LIMITS))
        self.rows=[dict(**s,status='unexecuted',reason=None,product=None,accounting=None) for s in slots]
        write(self.root/'CONFIG.json',self.config);self.journal.append('recovery_stage_configured',config_sha256=c.fingerprint(self.config))

    def call(self,operation):
        c.need(not self.closed and not self.failed and self.cursor<len(self.rows),'Recovery stage exhausted/failed; no retry')
        c.need(self.clock()<self.deadline,'Recovery stage deadline before reservation')
        row=self.rows[self.cursor];slot=self.config['schedule'][self.cursor]
        self.journal.append('recovery_slot_reserved',slot=slot,limits=c.CELL_LIMITS);self.cursor+=1;row['status']='entered'
        try:
            result=operation(slot,self.deadline)
            c.need(isinstance(result,Mapping) and set(result)=={'status','reason','product','accounting'} and
                result['status'] in c.TERMINAL_STATUSES,'Explicit recovered terminal disposition')
            if result['status']=='authenticated_limit_failure':
                descriptor=c.read(result['product']['limit_failure'])
                c.need(result['accounting'] is None and descriptor['status']=='authenticated_limit_failure' and
                    descriptor['prediction'] is None and descriptor['qualified_usage'] is None and
                    descriptor['execution_id']==slot['execution_id'],'Authenticated failure remains unqualified/null')
            else:schedule.accounting(result['accounting'],slot['phase'],status=result['status'])
            c.need(self.clock()<self.deadline,'Recovery stage deadline after operation')
            row.update(encode(result));name=f'slots/{slot["ordinal"]:04d}.json';item=write(self.root/name,row)
            self.journal.append('recovery_slot_terminal',ordinal=slot['ordinal'],proof=item,status=row['status'])
            return freeze(row)
        except BaseException as error:
            self.failed=True;row.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',reason=type(error).__name__,product=None,accounting=None)
            item=write(self.root/f'failures/{slot["ordinal"]:04d}.json',row)
            self.journal.append('recovery_slot_failed',ordinal=slot['ordinal'],proof=item,status=row['status'])
            raise

    def finish(self):
        c.need(not self.closed,'Recovery stage already sealed')
        try:
            report=_summary(self.rows,self.config['seconds'],self.clock()-self.started)
            write(self.root/'REPORT.json',report);self.journal.append('recovery_stage_finalized',status=report['status'],report_sha256=c.fingerprint(report));self.journal.close()
            receipt=dict(kind='sc05_recovery_stage_receipt_v2',status=report['status'],files=inventory(self.root,omit=('STAGE-RECEIPT.json',)),
                seal_elapsed_seconds=self.clock()-self.started,automatic_retry=False)
            write(self.root/'STAGE-RECEIPT.json',receipt)
            if report['status']=='complete' and not 0<=receipt['seal_elapsed_seconds']<self.config['seconds']:
                write(self.root/'FINALIZATION-FAILED.json',dict(reason='stage_deadline_during_sealing'));raise TimeoutError('Recovery seal deadline')
            return report
        finally:self.closed=True;self.journal.close()


def verify_stage(root,expected,*,ids,phase,ordinals,purpose,original_slots):
    """Reconcile accepted child bytes, original ordinals and durable events."""
    root=c.path(root);rp,raw=c.capture(root/'STAGE-RECEIPT.json');c.need(rp['sha256']==expected,'External recovered stage anchor')
    receipt=freeze(parse_json(raw))
    c.need(set(receipt)=={'kind','status','files','seal_elapsed_seconds','automatic_retry'} and
        receipt['kind']=='sc05_recovery_stage_receipt_v2' and receipt['automatic_retry'] is False,'Recovered stage receipt fields')
    c.need(canonical(receipt['files'])==canonical(inventory(root,omit=('STAGE-RECEIPT.json',))),'Recovered stage inventory differs')
    config=c.read(receipt['files']['CONFIG.json']);report=c.read(receipt['files']['REPORT.json'])
    c.schedule(ids,purpose)
    c.need(set(config)=={'kind','phase','purpose','ids','dispatch_ordinals','execution_namespace','schedule','seconds','cell_limits'} and
        config['kind']=='sc05_recovery_stage_v2' and config['phase']==phase and config['purpose']==purpose and
        tuple(config['ids'])==tuple(ids) and tuple(config['dispatch_ordinals'])==tuple(ordinals) and
        canonical(config['cell_limits'])==canonical(c.CELL_LIMITS),'Recovered stage original scope/caps')
    from uuid import UUID
    namespace=config['execution_namespace'];c.need(str(UUID(namespace))==namespace,'Recovery execution namespace')
    slots=[dict(ordinal=i,id=ids[i],phase=phase,original_slot=original_slots[i],execution_id=f'{namespace}-{phase}-{i:04d}') for i in ordinals]
    c.need(canonical(config['schedule'])==canonical(slots) and len(report['rows'])==len(slots),'Recovered stage reserved schedule differs')
    elapsed=c.finite(report['wall_seconds'],'stage elapsed');seal=c.finite(receipt['seal_elapsed_seconds'],'stage seal elapsed')
    c.need(0<=elapsed<=seal<config['seconds'],'Recovered stage deadline/order')
    events=read_chain(root/'journal.jsonl');expected_events=[('recovery_stage_configured',dict(config_sha256=c.fingerprint(config)))]
    for slot,row in zip(slots,report['rows']):
        c.need(set(row)==set(slot)|{'status','reason','product','accounting'} and all(row[k]==v for k,v in slot.items()) and
            row['status'] in c.TERMINAL_STATUSES,'Recovered terminal row identity')
        expected_events.append(('recovery_slot_reserved',dict(slot=slot,limits=c.CELL_LIMITS)))
        name=f'slots/{slot["ordinal"]:04d}.json';item=receipt['files'][name]
        c.need(c.read(item)==row,'Recovered row/file join')
        expected_events.append(('recovery_slot_terminal',dict(ordinal=slot['ordinal'],proof=item,status=row['status'])))
        if row['status']=='authenticated_limit_failure':
            lp=row['product']['limit_failure'];c.need(Path(lp['path'])==root/'limit_failures'/f'{slot["ordinal"]:04d}.json','Limit classification stays outside original cell')
            c.need(receipt['files'][f'limit_failures/{slot["ordinal"]:04d}.json']==lp,'Limit classification inventory binding')
            failure=c.read(lp)
            c.need(row['accounting'] is None and failure['status']=='authenticated_limit_failure' and failure['qualified_usage'] is None and
                failure['prediction'] is None and failure['execution_id']==slot['execution_id'],'Unqualified limit accounting/null identity')
        else:schedule.accounting(row['accounting'],phase,status=row['status'])
    rebuilt=_summary(report['rows'],config['seconds'],elapsed)
    c.need(report==rebuilt and report['status']==receipt['status']=='complete','Recovered stage counts/accounting')
    expected_events.append(('recovery_stage_finalized',dict(status=report['status'],report_sha256=c.fingerprint(report))))
    c.need(events[0]['event']=='build_reserved' and canonical([(e['event'],e['details']) for e in events[1:]])==canonical(expected_events),'Recovered stage exact durable event sequence')
    c.need(not any((root/name).exists() for name in ('FAILURE.json','DEADLINE.json','FINALIZATION-FAILED.json')),'Recovered stage terminal failure marker')
    c.need(canonical(receipt['files'])==canonical(inventory(root,omit=('STAGE-RECEIPT.json',))) and c.capture(rp['path'],rp)[0]==rp,'Recovered stage changed during verification')
    return freeze(dict(config=config,report=report,receipt=rp,seal_elapsed_seconds=seal,root=str(root)))


def worker_timing(stage,terminal,supervision,job):
    seal=c.finite(stage['seal_elapsed_seconds'],'stage seal elapsed')
    wall=c.finite(terminal['wall_seconds'],'worker wall elapsed')
    execution=c.finite(supervision['execution_elapsed_seconds'],'process execution elapsed')
    total=c.finite(supervision['total_elapsed_seconds'],'process total elapsed')
    c.need(seal<=wall<=execution<=total<=job['seconds'] and stage['config']['seconds']<=job['stage_seconds'],
        'Recovery stage/worker/process carried clock chain differs')


def remaining_job_budgets(value,phase,*,phase_elapsed,outer_elapsed):
    spent=c.finite(phase_elapsed,'new phase preflight elapsed');outer=c.finite(outer_elapsed,'new outer elapsed')
    c.need(spent<=outer,'New phase cannot exceed encompassing recovery elapsed')
    seconds=int(min(value['budgets']['phase_remaining_seconds'][phase]-spent,
        value['budgets']['outer_remaining_seconds']-outer-60))
    # The old stage timer began after setup. Its remaining allowance is an
    # independent ceiling; all new setup is already charged to phase/outer time.
    available=value['budgets']['repair_stage_remaining_seconds'] if phase=='repair' else seconds-90
    stage_seconds=min(seconds-90,available)
    c.need(seconds>120 and stage_seconds>0,'No carried phase/stage time left after verification')
    return seconds,stage_seconds


def admission_seconds(purpose,remaining_seconds):
    c.need(purpose in ('production','fictional_qualification'),'Explicit admission purpose')
    remaining=c.finite(remaining_seconds,'admission enclosing allowance')
    seconds=min(3600 if purpose=='production' else 600,remaining-180-90-120)
    c.need(seconds>0,'No bounded admission allowance after startup/cleanup/minimum-cell reserves')
    return seconds


def _operation(slot,end,*,case,product,caller,root,provenance,alias,server_spec,bindings):
    deadline=min(end,time.monotonic()+120)
    query,prior,critic,context,pair=pipeline._pair_inputs(product,case,provenance,deadline)
    task=slot['phase'];member=pair[task]
    descriptor=freeze(dict(task=task,query=query,prior=prior,critic=critic,sources=context.sources if task=='repair' else (),
        model_provenance=provenance,prepared_member=member,control_sha256=context.control_sha256,execution_id=slot['execution_id']))
    try:
        result=caller(descriptor,root,deadline)
    except ContractError:
        # Merely catching a ContractError does not qualify continuation. Every
        # captured byte, quote, timing and original rejection must authenticate.
        c.need(member['status']=='ready','Unavailable member cannot have a limit failure')
        files=inventory(root,omit=())
        verified=native_failure.verify_cell_limit_failure(root,files=files,expected_inputs=pipeline._cell_inputs(descriptor),
            expected_request=member['request'],expected_payload=member['payload'],execution_id=slot['execution_id'],
            owner_pid=caller.owner.terminal_record['pid'],alias=alias,server_spec=server_spec,bindings=bindings,deadline=deadline)
        limit=write(root.parent.parent/'limit_failures'/f'{slot["ordinal"]:04d}.json',verified)
        return dict(status='authenticated_limit_failure',reason='native_completion_limit',accounting=None,
            product=dict(limit_failure=limit,disposition=dict(id=query['id'],producer_status='error',check_status='not_run',prediction=None,reason='native_completion_limit'),
                paired_member_sha256=c.fingerprint(member),control_sha256=context.control_sha256,source_context_sha256=c.fingerprint(context.report)))
    call,usage,native_proof=pipeline._model_result(result,descriptor,root,deadline);summary=call['summary'];decision=None
    if summary['status']=='completed':
        c.need(member['status']=='ready' and summary['request_sha256']==c.fingerprint(member['request']),'Original frozen request differs')
        decision=admission.check(context,summary['decoded'],member['request'],task=task,expected_control_sha256=context.control_sha256,payload=member['payload'],deadline=deadline)
        disposition=dict(id=query['id'],producer_status='produced',check_status='accepted' if decision['accepted'] else 'rejected',prediction=summary['decoded'],reason=decision['reason'])
    else:disposition=dict(id=query['id'],producer_status='parse_failure' if summary['status']=='codec_failure' else 'input_unavailable',check_status='not_run',prediction=None,reason=summary['status'])
    decision_proof=write(root/'DECISION.json',decision)
    return dict(status=summary['status'],reason=None if summary['status']=='completed' else summary['status'],accounting=usage,
        product=dict(call=call,native_proof=native_proof,disposition=disposition,decision=decision_proof,paired_member_sha256=c.fingerprint(member),
            control_sha256=context.control_sha256,source_context_sha256=c.fingerprint(context.report)))


def worker_preflight(frame_path,frame_sha,job_path,job_sha,output):
    fp,raw=c.capture(c.path(frame_path));jp,jraw=c.capture(c.path(job_path))
    c.need(fp['sha256']==frame_sha and jp['sha256']==job_sha,'Worker frame/job external anchors')
    frame=freeze(parse_json(raw));job=freeze(parse_json(jraw));value=c.read(frame['plan']);authority=c.read(frame['authority'])
    c.need(set(frame)==FRAME_FIELDS and frame['kind']==KIND and frame['schema_version']==2 and job['phase'] in c.PHASES,'Worker v2 identity')
    c.schedule(value['schedule'],frame['purpose'])
    destination=c.path(frame['output']);phase=job['phase'];out=c.path(output)
    c.need(Path(frame_path)==destination/'FRAME.json' and Path(job_path)==destination/phase/'JOB.json' and out==destination/phase/'worker'
        and not out.exists(),'Worker exact fresh reserved paths')
    c.need(job['frame_sha256']==frame_sha and frame['parent']==value['parent'] and frame['purpose']==value['purpose'] and
        authority['plan']==frame['plan'] and authority['parent_identity']==value['parent_identity'] and authority['permanent'] is True,
        'Worker original authority binding')
    c.need(set(job)=={'phase','frame_sha256','input_files','model_bindings','parent_pair','baseline','dispatch_ordinals','seconds','stage_seconds','original_slots','execution_claim','phase_preflight_seconds','outer_preflight_seconds'},'Worker exact job fields')
    c.need(tuple(job['dispatch_ordinals'])==tuple(value['partition'][phase+'_dispatch']) and
        tuple(authority['allowed_dispatch'][phase])==tuple(job['dispatch_ordinals']),'Worker untouched-only dispatch set')
    c.need(job['original_slots']==(value['original_repair_slots'] if phase=='repair' else (None,)*len(value['schedule'])),
        'Worker original reservation identities differ')
    registry=c.authority_registry(original_root=value['original_root'],purpose=value['purpose'])
    c.need(Path(frame['authority']['path'])==registry/value['parent_identity']/'AUTHORITY.json' and
        value['authority_registry']==str(registry),'Worker stable permanent authority registry')
    original=c.read(value['original_frame'])
    c.need(job['baseline']==original['baseline'] and job['parent_pair']==value['completed_phases']['pair_prepare'],'Worker original source ancestry')
    c.need(120<job['seconds']<=value['budgets']['phase_remaining_seconds'][phase] and 0<job['stage_seconds']<=job['seconds']-90,'Carried worker/stage cap')
    c.need((job['seconds'],job['stage_seconds'])==remaining_job_budgets(value,phase,phase_elapsed=job['phase_preflight_seconds'],outer_elapsed=job['outer_preflight_seconds']),
        'Worker verification/startup cannot reset original remaining clocks')
    if phase=='repair':c.need(job['stage_seconds']<=value['budgets']['repair_stage_remaining_seconds'],'Original repair stage cap reset')
    c.need(canonical(frame['code_files'])==canonical(code_files()) and canonical(original['interpreter'])==canonical(proof(sys.executable)),'Worker frozen source/interpreter')
    claim=c.read(job['execution_claim']);c.need(claim['frame_sha256']==frame_sha and claim['output']==str(destination),'Permanent execution claim differs')
    expected_claim=Path(frame['authority']['path']).parent/'EXECUTION'/'CLAIM.json'
    c.need(Path(job['execution_claim']['path'])==expected_claim,'Worker exclusive execution claim location')
    phase_authority=c.read(proof(expected_claim.parent/(phase+'-AUTHORIZED-JOB.json')))
    c.need(phase_authority==freeze(dict(frame_sha256=frame_sha,job=jp,output=str(out))), 'Permanent coordinator phase authorization differs')
    # Source-rich admission is isolated from the model worker. Its result is
    # metadata only; no repaired answer or evaluator package is a worker grant.
    admission_report=admit_supervised(fp,jp,destination/phase/'admission',seconds=admission_seconds(frame['purpose'],job['seconds']))
    c.need(admission_report==admission_projection(frame,fp,job,jp,value),'Separate parent admission differs')
    # This permanent phase claim prevents a copied job from dispatching twice,
    # even if its output directory was subsequently moved or removed.
    write(expected_claim.parent/(phase+'-WORKER-CLAIM.json'),dict(frame_sha256=frame_sha,job_sha256=job_sha,output=str(out),owner_pid=os.getpid()))
    return frame,job,value,original


def admission_projection(frame,fp,job,jp,value):
    return freeze(dict(kind='sc05_recovery_worker_admission_v2',status='admitted',frame=fp,job=jp,plan=frame['plan'],authority=frame['authority'],
        parent_identity=value['parent_identity'],original_frame=value['original_frame'],partition=value['partition'],budgets=value['budgets'],
        phase=job['phase'],dispatch_ordinals=job['dispatch_ordinals'],model_or_http_execution_performed=False,scientific_answers_returned=False))


def admit(frame_path,frame_sha,job_path,job_sha,output):
    """Trusted source-rich subprocess: returns only immutable scope metadata."""
    fp,raw=c.capture(c.path(frame_path));jp,jraw=c.capture(c.path(job_path))
    c.need(fp['sha256']==frame_sha and jp['sha256']==job_sha,'Admission external request anchors')
    frame=freeze(parse_json(raw));job=freeze(parse_json(jraw))
    c.need(set(frame)==FRAME_FIELDS and frame['kind']==KIND and frame['schema_version']==2 and job['frame_sha256']==frame_sha,'Admission exact frame/job identity')
    destination=c.path(frame['output']);phase=job['phase'];c.need(phase in c.PHASES,'Admission final phase')
    c.need(Path(frame_path)==destination/'FRAME.json' and Path(job_path)==destination/phase/'JOB.json' and
        c.path(output)==destination/phase/'admission/worker','Admission exact isolated output')
    journal=RunJournal(Path(output),kind='build');root=journal.output
    try:
        write(root/'REQUEST.json',dict(frame=fp,job=jp,role='trusted_parent_admission',model_or_http_execution_performed=False))
        value,authority,verified=plan.verify(frame['plan'],frame['authority'],return_parent=True)
        c.need(frame['parent']==value['parent'] and frame['purpose']==value['purpose'] and
            tuple(job['dispatch_ordinals'])==tuple(value['partition'][phase+'_dispatch']) and
            canonical(frame['code_files'])==canonical(code_files()),'Parent admission scope/source binding')
        c.need((job['seconds'],job['stage_seconds'])==remaining_job_budgets(value,phase,phase_elapsed=job['phase_preflight_seconds'],outer_elapsed=job['outer_preflight_seconds']),
            'Parent admission remaining clocks differ')
        report=admission_projection(frame,fp,job,jp,value);write(root/'REPORT.json',report)
        journal.append('recovery_worker_admitted',report_sha256=c.fingerprint(report));journal.close()
        c.capture(fp['path'],fp);c.capture(jp['path'],jp)
        from . import original
        original.revalidate(verified)
        c.need(canonical(frame['code_files'])==canonical(code_files()),'Admission source closure changed before sealing')
        receipt=write(root/'RECEIPT.json',dict(kind='sc05_recovery_admission_receipt_v2',status='admitted',files=inventory(root,omit=('RECEIPT.json',))))
        return freeze(dict(root=str(root),receipt_sha256=receipt['sha256']))
    except BaseException as error:
        if not journal._stream.closed:journal.fail(error,'trusted_parent_admission')
        write(root/'FAILURE.json',dict(error_type=type(error).__name__,message=str(error),model_or_http_execution_performed=False,automatic_retry=False));raise
    finally:journal.close()


def admit_supervised(fp,jp,output,*,seconds):
    root=c.path(output);root.mkdir(exist_ok=False)
    command=[str(sys.executable),'-I','-B','-c','import runpy,sys;sys.path[:0]=sys.argv[1:4];sys.argv=["tether-sc05-recovery-admission"]+sys.argv[4:];runpy.run_module("experiments.litqa_refinement_recovery.run",run_name="__main__")',
        str(ROOT),str(ROOT/'src'),str(ROOT/'packages/tether/src'),'--admission','--frame',fp['path'],'--frame-sha256',fp['sha256'],
        '--job',jp['path'],'--job-sha256',jp['sha256'],'--output',str(root/'worker')]
    limits=ProcessLimits(seconds,4*1024**2);write(root/'COMMAND.json',command)
    try:
        result=previous.supervised(command,limits,root)
        c.need(result.returncode==0,'Separate parent admission failed; no model dispatch')
        validate_success_report(result.supervision,limits,len(result.stdout),len(result.stderr))
        rp,raw=c.capture(root/'worker/RECEIPT.json');receipt=freeze(parse_json(raw))
        c.need(set(receipt)=={'kind','status','files'} and receipt['kind']=='sc05_recovery_admission_receipt_v2' and receipt['status']=='admitted' and
            canonical(receipt['files'])==canonical(inventory(root/'worker',omit=('RECEIPT.json',))),'Separate admission receipt/inventory')
        c.need(not any((root/'worker'/name).exists() for name in ('FAILURE.json','DEADLINE.json')),'Separate admission failed marker')
        report=c.read(receipt['files']['REPORT.json'])
        c.need(report['frame']==fp and report['job']==jp and report['model_or_http_execution_performed'] is False and report['scientific_answers_returned'] is False,'Separate admission request/role binding')
        write(root/'COMPLETE.json',dict(status='admitted',receipt=rp,frame=fp,job=jp,model_or_http_execution_performed=False))
        return report
    except BaseException as error:
        write(root/'FAILURE.json',dict(error_type=type(error).__name__,message=str(error),model_or_http_execution_performed=False,automatic_retry=False));raise


def worker(frame_path,frame_sha,job_path,job_sha,output):
    started=time.monotonic();frame,job,value,old=worker_preflight(frame_path,frame_sha,job_path,job_sha,output)
    journal=RunJournal(Path(output),kind='build');root=journal.output;owner=audit=watchdog=stage=None;handle=None
    try:
        phase=job['phase'];end=started+job['seconds'];handle=contain_process_tree();watchdog=DeadlineWatchdog(end,root/'DEADLINE.json');watchdog.__enter__()
        write(root/'CONFIG.json',dict(frame_sha256=frame_sha,job_sha256=job_sha,phase=phase,purpose=frame['purpose'],worker_pid=os.getpid(),python_version=sys.version,coordinator_grants=job['input_files']))
        inputs=[frame_path,job_path,old['model_receipt']['path'],old['model_license']['path'],*[p['path'] for p in job['input_files']]]
        audit=RoleAudit(inputs=inputs,code_files=[p['path'] for p in frame['code_files']],runtime_roots=(sys.base_prefix,sys.prefix),model_files=list(job['model_bindings'].values()),output=root);audit.activate()
        for item in job['input_files']:c.need(canonical(proof(item['path']))==canonical(item),'Original coordinator proof changed')
        baseline=projection.verify_baseline_projection(old['baseline'],value['schedule'])
        expected=coordinator_grants(baseline,job['parent_pair'],value['original_frame'])
        c.need(canonical(expected)==canonical(job['input_files']),'Worker exact source-only coordinator grants')
        pairroot=Path(job['parent_pair']['root'])/'worker/phase'
        pair=schedule.verify(pairroot,job['parent_pair']['stage_receipt_sha256'],expected_ids=value['schedule'],expected_phase='pair_prepare',purpose=frame['purpose'],deadline=end-90)
        cases={case['id']:case for case in baseline.cases};products={r['id']:r['product'] for r in pair['report']['rows']}
        spec,bindings,provenance=native_model.make_server_spec(old['model_receipt']['path'],old['model_receipt']['sha256'],port=old['port'],alias=old['alias'],startup_seconds=180)
        c.need(canonical(spec)==canonical(old['model_spec']) and canonical(provenance)==canonical(old['model_provenance']) and
            {k:str(v) for k,v in bindings.items()}==dict(job['model_bindings']),'Original native model identity')
        c.need(canonical(proof(old['model_license']['path']))==canonical(old['model_license']),'Original model terms changed')
        write(root/'MODEL.json',dict(spec=encode(spec),bindings={k:str(v) for k,v in bindings.items()},provenance=provenance,alias=old['alias']))
        (root/'server').mkdir()
        with native_model.owned_server(spec,bindings,output=root/'server',journal=journal,parent_deadline=end-40) as owner:
            caller=pipeline.NativeCaller(owner,old['alias'],audit)
            stage=RecoveryStage(value['schedule'],phase,job['dispatch_ordinals'],root/'phase',purpose=frame['purpose'],
                seconds=min(job['stage_seconds'],end-time.monotonic()-90),original_slots=job['original_slots'])
            pair_inputs=pipeline.read(proof(pairroot/'INPUTS.json'),deadline=end-90)
            write(stage.root/'INPUTS.json',dict(baseline=job['baseline'],parent_pair=job['parent_pair'],original_cutoff=pair_inputs['cutoff'],reference_keys_available=False,scoring_performed=False))
            with ProcessSamples(owner.terminal_record['pid']) as samples:
                for _ in job['dispatch_ordinals']:
                    stage.call(lambda slot,deadline:_operation(slot,deadline,case=cases[slot['id']],product=products[slot['id']],caller=caller,
                        root=stage.root/'products'/f'{slot["ordinal"]:04d}',provenance=provenance,alias=old['alias'],server_spec=spec,bindings=bindings))
                report=stage.finish()
            write(root/'SERVER-RESOURCE-SAMPLES.json',samples.values)
        audit.flush();c.need(owner.terminal_record['server_stopped'] is True and report['status']=='complete' and audit.denials==0 and time.monotonic()<end,'Recovery worker failed cleanup/coverage/time/access')
        c.need(canonical(frame['code_files'])==canonical(code_files()),'Recovery code changed during worker')
        terminal=dict(status='complete',phase=phase,purpose=frame['purpose'],frame_sha256=frame_sha,stage_receipt=proof(root/'phase/STAGE-RECEIPT.json'),
            wall_seconds=time.monotonic()-started,worker_memory=process_sample(os.getpid()),server_terminal=encode(owner.terminal_record),audit_denials=audit.denials,
            provider_cost_usd=0,reference_keys_read=False,scientific_scoring_performed=False)
        write(root/'COMPLETE.json',terminal);journal.append('recovery_worker_completed',terminal_sha256=c.fingerprint(terminal));return freeze(terminal)
    except BaseException as error:
        if stage is not None and not stage.closed:
            try:stage.finish()
            except BaseException as secondary:error.add_note('Recovery partial stage retention: '+type(secondary).__name__)
        journal.fail(error,'recovery_worker');write(root/'FAILURE.json',dict(stage='recovery_worker',error_type=type(error).__name__,message=str(error),automatic_retry=False,
            server_terminal=None if owner is None else encode(owner.terminal_record),wall_seconds=time.monotonic()-started));raise
    finally:
        if audit is not None:audit.flush()
        journal.close()
        if watchdog is not None:watchdog.__exit__(None,None,None)
        _=handle


def execute(frame_path,expected,*,output):
    started=time.monotonic();frame,fp,raw,root,bounds=preflight_request(frame_path,expected,output)
    journal=RunJournal(root,kind='build');anchors={};accepted={};watchdog=phase_watchdog=None;handle=None;current='parent_preflight'
    try:
        request=write(root/'REQUEST.json',dict(kind='sc05_recovery_preflight_request_v2',frame=fp,output=str(root),
            preflight_bounds=bounds,metadata_only_before_admission=True,automatic_retry=False))
        journal.append('recovery_preflight_started',request=request,frame=fp,limits=bounds)
        (root/'FRAME.json').write_bytes(raw)
        handle=contain_process_tree()
        end=started+bounds['outer_seconds'];watchdog=DeadlineWatchdog(end,root/'DEADLINE.json');watchdog.__enter__()
        phase_watchdog=DeadlineWatchdog(started+bounds['repair_seconds'],root/'repair-DEADLINE.json');phase_watchdog.__enter__()
        frame,checked_fp,value,old,checked_root,parent=load_frame(frame_path,expected,output,reservation=journal)
        c.need(checked_fp==fp and checked_root==root and bounds==freeze(dict(repair_seconds=value['budgets']['phase_remaining_seconds']['repair'],
            outer_seconds=value['budgets']['outer_remaining_seconds'])),'Semantic admission differs from bounded preflight metadata')
        c.need(time.monotonic()<min(end,started+bounds['repair_seconds']),'Parent admission exceeded carried deadline')
        from . import original
        original.revalidate(parent);c.need(parent.payload['frame']==old,'Original parent changed')
        journal.append('recovery_preflight_admitted',parent_identity=value['parent_identity'],original_frame=value['original_frame'],plan=frame['plan'],authority=frame['authority'])
        execution=Path(frame['authority']['path']).parent/'EXECUTION';execution.mkdir(exist_ok=False)
        claim=write(execution/'CLAIM.json',dict(kind='sc05_recovery_execution_claim_v2',frame_sha256=expected,output=str(root),automatic_retry=False))
        baseline=projection.verify_baseline_projection(old['baseline'],value['schedule'])
        grants=coordinator_grants(baseline,value['completed_phases']['pair_prepare'],value['original_frame'])
        spec,bindings,provenance=native_model.make_server_spec(old['model_receipt']['path'],old['model_receipt']['sha256'],port=old['port'],alias=old['alias'],startup_seconds=180)
        c.need(canonical(spec)==canonical(old['model_spec']) and canonical(provenance)==canonical(old['model_provenance']),'Original model changed before recovery')
        for phase in c.PHASES:
            phase_started=started if phase=='repair' else time.monotonic()
            if phase=='removal':
                phase_watchdog=DeadlineWatchdog(phase_started+value['budgets']['phase_remaining_seconds'][phase],root/'removal-DEADLINE.json');phase_watchdog.__enter__()
            current=phase;original.revalidate(parent);pr=root/phase;pr.mkdir()
            now=time.monotonic();phase_elapsed=now-phase_started;outer_elapsed=now-started
            seconds,stage_seconds=remaining_job_budgets(value,phase,phase_elapsed=phase_elapsed,outer_elapsed=outer_elapsed)
            old_slots=[r['execution_id'] for r in parent.payload['repair_rows']] if phase=='repair' else [None]*len(value['schedule'])
            job=dict(phase=phase,frame_sha256=expected,input_files=grants,model_bindings={k:str(v) for k,v in bindings.items()},
                parent_pair=value['completed_phases']['pair_prepare'],baseline=old['baseline'],dispatch_ordinals=value['partition'][phase+'_dispatch'],
                seconds=seconds,stage_seconds=stage_seconds,original_slots=old_slots,execution_claim=claim,
                phase_preflight_seconds=phase_elapsed,outer_preflight_seconds=outer_elapsed)
            jp=write(pr/'JOB.json',job)
            write(execution/(phase+'-AUTHORIZED-JOB.json'),dict(frame_sha256=expected,job=jp,output=str(pr/'worker')))
            command=[str(sys.executable),'-I','-B','-c','import runpy,sys;sys.path[:0]=sys.argv[1:4];sys.argv=["tether-sc05-recovery-worker"]+sys.argv[4:];runpy.run_module("experiments.litqa_refinement_recovery.run",run_name="__main__")',
                str(ROOT),str(ROOT/'src'),str(ROOT/'packages/tether/src'),'--worker','--frame',str(root/'FRAME.json'),'--frame-sha256',expected,'--job',jp['path'],'--job-sha256',jp['sha256'],'--output',str(pr/'worker')]
            limits=ProcessLimits(seconds,4*1024**2);write(pr/'COMMAND.json',command)
            journal.append('recovery_phase_reserved',phase=phase,job=jp,command=command,limits=limits.payload())
            result=previous.supervised(command,limits,pr)
            c.need(result.returncode==0,'Recovery worker failed; no automatic retry');validate_success_report(result.supervision,limits,len(result.stdout),len(result.stderr))
            terminal=c.read(proof(pr/'worker/COMPLETE.json'))
            c.need(terminal['status']=='complete' and terminal['phase']==phase and terminal['frame_sha256']==expected and terminal['audit_denials']==0
                and terminal['server_terminal']['server_stopped'] is True,'Recovery child terminal identity/cleanup')
            c.need(not any((pr/'worker'/name).exists() for name in ('FAILURE.json','DEADLINE.json','FINALIZATION-FAILED.json')),'Recovery worker failure marker')
            c.need(Path(terminal['stage_receipt']['path'])==pr/'worker/phase/STAGE-RECEIPT.json' and
                canonical(terminal['stage_receipt'])==canonical(proof(pr/'worker/phase/STAGE-RECEIPT.json')),'Recovery stage terminal proof identity')
            checked=verify_stage(pr/'worker/phase',terminal['stage_receipt']['sha256'],ids=value['schedule'],phase=phase,
                ordinals=job['dispatch_ordinals'],purpose=frame['purpose'],original_slots=old_slots)
            worker_timing(checked,terminal,result.supervision,job)
            c.need(canonical(code_files())==canonical(frame['code_files']),'Recovery source closure changed')
            elapsed=time.monotonic()-phase_started
            c.need(elapsed<value['budgets']['phase_remaining_seconds'][phase],'Recovery entire phase exceeds carried allowance')
            write(pr/'PHASE-TIMING.json',dict(phase=phase,start_offset_seconds=phase_started-started,preflight_seconds=phase_elapsed,
                charged_wall_seconds=elapsed,remaining_limit_seconds=value['budgets']['phase_remaining_seconds'][phase],
                scope='Includes new verification, startup, admission, native execution and child sealing; final parent revalidation and root sealing use the outer watchdog.'))
            files=inventory(pr,omit=('PACKAGE-RECEIPT.json',));pp=write(pr/'PACKAGE-RECEIPT.json',dict(kind='sc05_recovery_phase_receipt_v2',status='complete',phase=phase,frame_sha256=expected,files=files))
            accepted[phase]=freeze(dict(files,**{'PACKAGE-RECEIPT.json':pp}));anchors[phase]=dict(root=str(pr),package_sha256=pp['sha256'],stage_receipt_sha256=terminal['stage_receipt']['sha256'])
            write(root/(phase+'-ANCHOR.json'),anchors[phase]);journal.append('recovery_phase_completed',phase=phase,anchor=anchors[phase])
            phase_watchdog.__exit__(None,None,None);phase_watchdog=None
        original.revalidate(parent);c.need(time.monotonic()<end,'Recovery aggregate remaining deadline')
        write(root/'COMPLETE.json',dict(status='recovery_execution_complete',purpose=frame['purpose'],phases=anchors,parent=frame['parent'],plan=frame['plan'],authority=frame['authority'],
            scheduled=len(value['schedule']),new_scheduled=value['budgets']['max_new_generation_calls'],inherited_failed_ordinal=parent.payload['failed_ordinal'],
            wall_seconds=time.monotonic()-started,provider_cost_usd=0,scientific_scoring_performed=False,automatic_retry=False))
        journal.append('recovery_execution_completed',phases=list(anchors));journal.close()
        files=inventory(root,omit=('ROOT-RECEIPT.json',),seconds=min(600,max(.001,end-time.monotonic())))
        previous.verify_final_packages(files,accepted);c.need(time.monotonic()<end,'Recovery final seal deadline')
        receipt=write(root/'ROOT-RECEIPT.json',dict(kind='sc05_refinement_recovery_root_receipt_v2',status='recovery_execution_complete',frame_sha256=expected,files=files))
        return freeze(dict(root=str(root),receipt_sha256=receipt['sha256']))
    except BaseException as error:
        if not journal._stream.closed:journal.fail(error,current)
        write(root/'FAILURE.json',dict(stage=current,error_type=type(error).__name__,message=str(error),completed_phases=anchors,automatic_retry=False,wall_seconds=time.monotonic()-started));raise
    finally:
        journal.close()
        if phase_watchdog is not None:phase_watchdog.__exit__(None,None,None)
        if watchdog is not None:watchdog.__exit__(None,None,None)
        _=handle


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--frame',type=Path,required=True);parser.add_argument('--frame-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True);group=parser.add_mutually_exclusive_group();group.add_argument('--worker',action='store_true');group.add_argument('--admission',action='store_true');parser.add_argument('--job',type=Path);parser.add_argument('--job-sha256')
    args=parser.parse_args()
    if args.admission:
        c.need(args.job is not None and args.job_sha256,'Admission anchored job required');print(encode(admit(args.frame,args.frame_sha256,args.job,args.job_sha256,args.output)))
    elif args.worker:
        c.need(args.job is not None and args.job_sha256,'Worker anchored job required');worker(args.frame,args.frame_sha256,args.job,args.job_sha256,args.output)
    else:print(encode(execute(args.frame,args.frame_sha256,output=args.output)))


if __name__=='__main__':main()
