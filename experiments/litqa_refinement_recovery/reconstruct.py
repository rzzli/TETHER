"""Independent version-two continuation reader and immutable evaluator gate.

The failed parent is preserved as failed. Its verified prefix, rejected limit
attempt and untouched pairs are joined with newly supervised calls without
creating a fictional complete version-one run. No reference keys are read here.
"""
from dataclasses import dataclass,field
import math
import os
from pathlib import Path
import sys
from uuid import UUID
from weakref import WeakValueDictionary

from tether_engine.serde import encode,freeze
from experiments.litqa_analysis import accepted_primary,source_archive
from experiments.litqa_refinement import envelopes as old
from experiments.litqa_refinement import evaluation as joins
from experiments.litqa_refinement import native_evaluation as native,source_evaluation as source
from . import original,native_failure

need=old.need
same=original.same
fingerprint=original.fingerprint
PHASES=('repair','removal')
CELL_LIMITS=dict(generation_calls=1,reserved_input_tokens=16128,reserved_output_tokens=256,source_http_requests=0,provider_cost_usd=0,seconds=120)
LAUNCHER='import runpy,sys;sys.path[:0]=sys.argv[1:4];sys.argv=["tether-sc05-recovery-worker"]+sys.argv[4:];runpy.run_module("experiments.litqa_refinement_recovery.run",run_name="__main__")'
_TOKEN=object()
_ISSUED=WeakValueDictionary()
_SEALS={}


@dataclass(frozen=True)
class VerifiedRecovery:
    root:str
    receipt_sha256:str
    report:object
    envelope:object
    _fingerprint:str=field(repr=False)
    _token:object=field(default=None,repr=False,compare=False)
    _parent:object=field(default=None,repr=False,compare=False)
    _closure:object=field(default=None,repr=False,compare=False)


def revalidate(value):
    need(type(value) is VerifiedRecovery and _ISSUED.get(id(value)) is value and value._token is _TOKEN,
         'Issued independent recovery capability required')
    need(_SEALS.get(id(value))==(value._fingerprint,fingerprint(value._closure),id(value._parent)),
         'Recovery immutable verification closure changed')
    need(value._fingerprint==fingerprint(dict(root=value.root,receipt_sha256=value.receipt_sha256,report=value.report,envelope=value.envelope)),
         'Recovery capability mutated')
    checked=original.verify_snapshot(value._closure)
    original.revalidate(value._parent);checked.unchanged()
    return value


def _closure(inputs):
    paths={p['path']:p for p in old._closure(inputs)}
    for folder in ('experiments/litqa_refinement_recovery','experiments/litqa_analysis','experiments/litqa_refinement'):
        for item in (old.REPO/folder).glob('*.py'):
            if not item.name.startswith('test_'):
                p,_=inputs.capture(item);paths[p['path']]=p
    return [paths[k] for k in sorted(paths)]


def _budget(payload):
    p=encode(payload);failed=p['failed_ordinal'];n=len(p['schedule']);phase=p['frame']['phase_seconds'];elapsed=p['elapsed'];old_budget=p['budgets']
    partitions=dict(repair_adopted=list(range(failed)),repair_inherited_failed=[failed],repair_dispatch=list(range(failed+1,n)),removal_dispatch=list(range(n)))
    need(p['untouched_repair_ordinals']==partitions['repair_dispatch'] and p['untouched_removal_ordinals']==partitions['removal_dispatch'],'Original untouched partition differs')
    if p['purpose']=='production':
        need(n==199 and failed==184 and phase['repair']==phase['removal']==7200,'Full fixed production recovery scope')
        need(sum(r['status']=='completed' for r in p['repair_rows'])==183 and sum(r['status']=='codec_failure' for r in p['repair_rows'])==1,'Fixed inherited terminal prefix')
    else:need(p['purpose']=='fictional_qualification' and n==2,'Explicit invented recovery scope')
    need(old_budget['outer_seconds']==43200 and all(type(phase[t]) is int and 120<=phase[t]<=7200 for t in PHASES),'Original phase caps')
    spent=max(old.finite(elapsed['repair_process_total_seconds'],'Original repair process'),old.finite(elapsed['repair_worker_wall_seconds'],'Original worker'))
    sealed=old.finite(elapsed['repair_stage_seal_elapsed_seconds'],'Original repair stage');outer=old.finite(elapsed['outer_process_total_seconds'],'Original outer')
    stage=old.finite(old_budget['repair_stage_seconds'],'Original stage allowance')
    need(0<stage<=phase['repair'] and sealed<=spent<=outer,'Conservative nested original clocks')
    remaining=dict(repair=math.floor(phase['repair']-spent),removal=phase['removal']);stage_left=math.floor(stage-sealed);outer_left=math.floor(43200-outer)
    need(min(remaining.values())>120 and stage_left>0 and outer_left>120,'No carried continuation allowance')
    count=len(partitions['repair_dispatch'])+n
    limits=dict(original_phase_seconds={k:phase[k] for k in PHASES},original_outer_seconds=43200,charged_repair_seconds=spent,
        charged_repair_stage_seconds=sealed,charged_outer_seconds=outer,phase_remaining_seconds=remaining,repair_stage_remaining_seconds=stage_left,
        outer_remaining_seconds=outer_left,max_new_generation_calls=count,max_new_source_http_requests=0,max_new_reserved_input_tokens=count*16128,
        max_new_reserved_output_tokens=count*256,cell_limits=CELL_LIMITS,provider_spend_usd=0,
        clock_scope='Conservative original elapsed carry-forward; nested clocks are not summed; new startup/verification/cleanup consume remaining bounds.')
    return partitions,limits


def _authority(frame,parent,root,inputs):
    payload=encode(parent.payload);p=inputs.json(frame['plan']);a=inputs.json(frame['authority'])
    identity=fingerprint(dict(original_root=os.path.normcase(payload['original_root']),frame_sha256=payload['frame_proof']['sha256']))
    registry=(old.REPO/'data/benchmark/litqa_refinement_recovery/authorities') if payload['purpose']=='production' else Path(payload['original_root']).parent/'recovery-authorities'
    parts,budgets=_budget(payload)
    expected=dict(schema_version=2,kind='sc05_refinement_recovery_plan_v2',purpose=payload['purpose'],parent=frame['parent'],parent_identity=identity,
        original_root=payload['original_root'],original_frame=payload['frame_proof'],schedule=payload['schedule'],
        original_repair_slots=[r['execution_id'] for r in payload['repair_rows']],authority_registry=str(registry),
        completed_phases=payload['completed_phases'],pair_prepare=payload['pair_prepare'],partition=parts,budgets=budgets,
        automatic_retry=False,new_source_collection=False,reference_keys_available=False,
        original_failure_policy='Inherited failure stays error/not_run/null; authenticated new completion-limit failures may advance to the next untouched slot without retry.',failed_call=payload['failed_call'])
    need(same(p,expected),'Independently derived original continuation plan differs')
    authority_path=registry/identity/'AUTHORITY.json'
    need(old.path(frame['authority']['path'])==authority_path and a==dict(schema_version=2,kind='sc05_refinement_recovery_authority_v2',parent_identity=identity,
         plan=frame['plan'],allowed_dispatch=dict(repair=parts['repair_dispatch'],removal=parts['removal_dispatch']),permanent=True,automatic_retry=False),
         'Stable permanent parent authority differs')
    execution=authority_path.parent/'EXECUTION';claim_proof,claim_raw=inputs.capture(execution/'CLAIM.json');claim=old.decode(claim_raw)
    need(claim==dict(kind='sc05_recovery_execution_claim_v2',frame_sha256=inputs.capture(root/'FRAME.json')[0]['sha256'],output=str(root),automatic_retry=False),
         'Exclusive original-parent execution claim differs')
    old._membership(authority_path.parent,('AUTHORITY.json',),('EXECUTION',))
    old._membership(execution,('CLAIM.json','repair-WORKER-CLAIM.json','removal-WORKER-CLAIM.json','repair-AUTHORIZED-JOB.json','removal-AUTHORIZED-JOB.json'),())
    for protected in (old.path(payload['original_root']),old.path(payload['freeze_root']),registry,old.path(frame['plan']['path']).parent):
        need(not root.is_relative_to(protected) and not protected.is_relative_to(root),'Recovery output/protected ancestor overlap')
    return p,a,claim_proof


def _frame(frame,root,inputs):
    fields={'schema_version','kind','purpose','parent','plan','authority','code_files','qualification','output'}
    need(set(frame)==fields and type(frame['schema_version']) is int and frame['schema_version']==2 and frame['kind']=='sc05_refinement_recovery_frame_v2',
         'Distinct version-two recovery frame required')
    need(set(frame['parent'])=={'inspection','source_archive','baseline_acceptance'},'Recovery failed-parent descriptor')
    need(old.path(frame['output'])==root and root.is_relative_to(old.REPO/'data') and root!=old.REPO/'data','Recovery output identity')
    need(same(frame['code_files'],_closure(inputs)),'Recovery executed source closure changed')
    parent=original.reconstruct(frame['parent']['inspection'],frame['parent']['source_archive'],baseline_acceptance=frame['parent']['baseline_acceptance'])
    need(frame['purpose']==parent.payload['purpose'],'Recovery/failed-parent purpose differs')
    if frame['purpose']=='production':
        q=inputs.json(frame['qualification'])
        identity=fingerprint(dict(original_root=os.path.normcase(parent.payload['original_root']),frame_sha256=parent.payload['frame_proof']['sha256']))
        need(q['kind']=='sc05_refinement_recovery_qualification_v2' and q['status']=='passed' and q['parent_identity']==identity and
             same(q['code_files'],frame['code_files']) and same(q['model_provenance'],parent.payload['frame']['model_provenance']) and
             q['native_tasks']==list(PHASES) and q['automatic_retry'] is False,'Recovery native/source qualification')
    else:need(frame['qualification'] is None,'Fictional recovery cannot inherit production qualification')
    plan,authority,claim=_authority(frame,parent,root,inputs)
    return parent,plan,authority,claim


def _stage(root,sp,phase,frame,job,plan,inputs,worker_seconds,process_seconds):
    receipt=inputs.json(sp);files=inputs.inventory(root,omit=('STAGE-RECEIPT.json',))
    need(set(receipt)=={'kind','status','files','seal_elapsed_seconds','automatic_retry'} and receipt['kind']=='sc05_recovery_stage_receipt_v2' and
         receipt['status']=='complete' and receipt['automatic_retry'] is False and same(receipt['files'],files),'Complete recovery stage inventory')
    config=inputs.json(files['CONFIG.json']);report=inputs.json(files['REPORT.json']);data=inputs.json(files['INPUTS.json'])
    namespace=config['execution_namespace'];need(str(UUID(namespace))==namespace,'New physical execution namespace')
    ordered=[dict(ordinal=i,id=plan['schedule'][i],phase=phase,original_slot=job['original_slots'][i],execution_id=f'{namespace}-{phase}-{i:04d}') for i in job['dispatch_ordinals']]
    need(set(config)=={'kind','phase','purpose','ids','dispatch_ordinals','execution_namespace','schedule','seconds','cell_limits'} and
         config['kind']=='sc05_recovery_stage_v2' and config['phase']==phase and config['purpose']==frame['purpose'] and config['ids']==plan['schedule'] and
         config['dispatch_ordinals']==job['dispatch_ordinals'] and config['schedule']==ordered and config['cell_limits']==CELL_LIMITS,
         'Recovery stage original ordinal/identity binding')
    seconds=old.finite(config['seconds'],'Recovery stage cap');elapsed=old.finite(report['wall_seconds'],'Recovery stage duration');seal=old.finite(receipt['seal_elapsed_seconds'],'Recovery seal')
    need(0<seconds<=job['stage_seconds'] and elapsed<=seal<seconds and seal<=worker_seconds<=process_seconds,'Recovery stage/worker/process clocks')
    need(data==dict(baseline=job['baseline'],parent_pair=job['parent_pair'],original_cutoff=plan['pair_prepare']['cutoff'],reference_keys_available=False,scoring_performed=False),
         'Recovery retained source cutoff/input role')
    rows=report['rows'];need(len(rows)==len(ordered),'Every permitted continuation slot required')
    events=old._events(inputs,files['journal.jsonl']);old._reserved(events[0]);expected=[('recovery_stage_configured',dict(config_sha256=fingerprint(config)))]
    known=[];unqualified=[]
    for row,slot in zip(rows,ordered):
        need(set(row)==set(slot)|{'status','reason','product','accounting'} and all(row[k]==v for k,v in slot.items()) and
             row['status'] in ('completed','codec_failure','capacity','authenticated_limit_failure') and row['product'] is not None,'Recovery terminal row identity')
        if row['status']=='authenticated_limit_failure':
            need(row['accounting'] is None and row['reason']=='native_completion_limit','Rejected completion stays unqualified');unqualified.append(row)
        else:old._accounting(row['accounting'],phase,row['status']);known.append(row['accounting'])
        proof=files[f'slots/{row["ordinal"]:04d}.json'];need(inputs.json(proof)==row,'Recovery row byte binding')
        expected += [('recovery_slot_reserved',dict(slot=slot,limits=CELL_LIMITS)),('recovery_slot_terminal',dict(ordinal=row['ordinal'],proof=proof,status=row['status']))]
    directory_names=({'slots','products'} if rows else set())|({'limit_failures'} if unqualified else set())
    old._membership(root,('CONFIG.json','INPUTS.json','REPORT.json','journal.jsonl','STAGE-RECEIPT.json'),directory_names)
    if rows:
        old._membership(root/'slots',{f'{row["ordinal"]:04d}.json' for row in rows},())
        old._membership(root/'products',(),{f'{row["ordinal"]:04d}' for row in rows})
    if unqualified:old._membership(root/'limit_failures',{f'{row["ordinal"]:04d}.json' for row in unqualified},())
    rebuilt=dict(kind='sc05_recovery_stage_report_v2',status='complete',scheduled=len(rows),entered=len(rows),unexecuted=0,rows=rows,wall_seconds=elapsed,automatic_retry=False,
        accounting=dict(known_totals={k:sum(a[k] for a in known) for k in old.FIELDS},provider_cost_usd=0,authenticated_limit_failures=len(unqualified),
            authenticated_limit_generation_calls=len(unqualified),raw_reported_unverified_usage=[r['product']['limit_failure'] for r in unqualified],
            unqualified_usage_cells=[r['id'] for r in unqualified],uncertain_cells=[],uncertain_per_cell_ceiling=CELL_LIMITS,measurements_complete=not unqualified,historical_work_included=False))
    need(same(report,rebuilt),'Recovery independently rebuilt stage accounting')
    expected.append(('recovery_stage_finalized',dict(status='complete',report_sha256=fingerprint(report))))
    need([(e['event'],e['details']) for e in events[1:]]==expected,'Recovery exclusive dispatch journal')
    return dict(root=str(root),rows=rows,inputs=data,report=report,files=files)


def _audit(root,phase,frame,job,fp,jp,model,rows,inputs,proof,old_frame):
    raw=inputs.bound(proof);need(raw.endswith(b'\n'),'Complete continuation role audit')
    records=[old.decode(line) for line in raw.splitlines()];need(records,'Nonempty continuation role audit')
    explicit={fp['path'],jp['path'],old_frame['model_receipt']['path'],old_frame['model_license']['path']}|{p['path'] for p in job['input_files']}
    shared={p['path'] for p in frame['code_files']}|set(model['bindings'].values());runtime=(Path(sys.prefix).resolve(),Path(sys.base_prefix).resolve())
    role='coordinator';active=None;entered=0
    for item in records:
        if 'event' in item:
            if item['event']=='actor_entered':
                need(set(item)=={'event','role','output','coordinator_inputs_granted'} and role=='coordinator' and item['role']==phase and
                     item['coordinator_inputs_granted'] is False and entered<len(rows),'Exclusive continuation actor entry')
                active=root/'phase/products'/f'{rows[entered]["ordinal"]:04d}'
                need(old.path(item['output'])==active,'Only permitted untouched actor output');role=phase;entered+=1
            else:
                need(set(item)=={'event','role','output'} and item['event']=='actor_exited' and role==phase and item['role']==phase and
                     item['output']==str(active),'Continuation actor scope closed');role='coordinator';active=None
            continue
        need(item['role']==role and item['allowed'] is True and type(item['flags']) is int,'Continuation role/denial contradiction')
        if item['path'] is None:
            need(set(item)=={'path','descriptor','mode','flags','allowed','basis','role'} and type(item['descriptor']) is int and item['descriptor']>=0 and
                 item['basis']=='existing_descriptor','Continuation existing descriptor audit');continue
        need(set(item)=={'path','mode','flags','allowed','basis','role'},'Continuation file audit schema')
        p=source_archive._absolute(item['path']);ancestor=p
        while not ancestor.exists():need(ancestor.parent!=ancestor,'No audit path ancestor');ancestor=ancestor.parent
        old.path(ancestor);writing=bool(item['flags']&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        own=p.is_relative_to(root if role=='coordinator' else active);common=str(p) in shared or any(p.is_relative_to(r) for r in runtime)
        granted=role=='coordinator' and str(p) in explicit
        basis='role_output' if own else 'code_model_runtime' if common and not writing else 'coordinator_input' if granted and not writing else 'denied'
        need(basis!='denied' and item['basis']==basis,'Independent continuation actor path reclassification')
    need(role=='coordinator' and entered==len(rows),'Exactly permitted continuation actors exited')
    return dict(recorded_operations=len(records),actor_cells=entered,denied_operations=0,scope='Recorded Python opens; no hostile native-code OS sandbox attestation')


def resource_tables(original_measured,continued_measured,attempts,envelope):
    """Verified token arithmetic never absorbs a rejected completion's usage."""
    phases=old.PHASES;fields=old.FIELDS
    tables=[]
    for supplied in (original_measured,continued_measured):
        need(set(supplied)==set(phases),'Full phase resource table')
        table=encode(supplied)
        for row in table.values():
            need(set(row)==set(fields) and all(type(v) is int and v>=0 for v in row.values()),'Verified resource integer schema')
            need(row['measured_input_tokens']<=row['reserved_input_tokens'] and row['measured_output_tokens']<=row['reserved_output_tokens'] and
                 row['measured_response_bytes']<=row['safety_accounted_bytes'],'Verified measured/reserved ordering')
        tables.append(table)
    original_measured,continued_measured=tables
    need(all(continued_measured[p][k]==0 for p in ('critic','refinement_collect','pair_prepare') for k in fields) and
         all(continued_measured[p]['source_http_requests']==continued_measured[p]['measured_response_bytes']==continued_measured[p]['safety_accounted_bytes']==0 for p in phases),
         'Continuation cannot reacquire sources or repeat prerequisite phases')
    need(all(original_measured['removal'][k]==0 for k in fields),'Original removal must not have started')
    verified={p:{k:original_measured[p][k]+continued_measured[p][k] for k in fields} for p in phases}
    totals={k:sum(row[k] for row in verified.values()) for k in fields};attempts=encode(attempts);seen=set()
    for a in attempts:
        need(set(a)=={'phase','ordinal','origin','execution_id','descriptor','raw_reported_usage','conservative_reservation'} and
             a['phase'] in PHASES and a['origin'] in ('original','continuation') and type(a['ordinal']) is int and 0<=a['ordinal']<len(envelope['frame']['schedule']),
             'Separate rejected-attempt attribution fields')
        need(a['execution_id'] not in seen,'Rejected physical attempt repeated');seen.add(a['execution_id'])
        d=a['descriptor']
        need(d['kind']=='sc05_authenticated_native_limit_failure_v1' and d['status']=='authenticated_limit_failure' and d['execution_id']==a['execution_id'] and
             d['task']==a['phase'] and d['producer_status']=='error' and d['check_status']=='not_run' and d['prediction'] is None and
             d['original_usage_verified'] is False and d['qualified_usage'] is None and d['raw_usage_checked'] is True and
             d['raw_reported_usage']==a['raw_reported_usage'] and d['conservative_reservation']==a['conservative_reservation'],'Rejected usage cannot become qualified')
        raw,reserve=a['raw_reported_usage'],a['conservative_reservation']
        need(set(raw)==set(reserve)=={'input_tokens','output_tokens','cost_usd'} and
             all(type(x['cost_usd']) in (int,float) and x['cost_usd']==0 and math.isfinite(x['cost_usd']) for x in (raw,reserve)) and
             all(type(x[k]) is int and x[k]>=0 for x in (raw,reserve) for k in ('input_tokens','output_tokens')) and
             raw['input_tokens']<=reserve['input_tokens']<=16128 and raw['output_tokens']==reserve['output_tokens']==256,'Rejected raw/reserved bounds')
    inherited=[a for a in attempts if a['origin']=='original'];new=[a for a in attempts if a['origin']=='continuation']
    need(len(inherited)==1 and inherited[0]['phase']=='repair','Exactly one inherited rejected original call')
    reported={k:sum(a['raw_reported_usage'][k] for a in attempts) for k in ('input_tokens','output_tokens','cost_usd')}
    reserved={k:sum(a['conservative_reservation'][k] for a in attempts) for k in ('input_tokens','output_tokens','cost_usd')}
    observed=dict(generation_calls=totals['generation_calls']+len(attempts),source_http_requests=totals['source_http_requests'],provider_cost_usd=0)
    need(observed['generation_calls']<=3*len(envelope['frame']['schedule']) and observed['source_http_requests']<=5*len(envelope['frame']['schedule']),
         'Original plus continuation exceeds fixed full-case budget')
    resources=dict(verified=dict(by_phase=verified,physical_totals=totals),original_attempt=dict(verified_by_phase=original_measured,unverified_native_attempts=inherited),
        continuation=dict(verified_by_phase=continued_measured,unverified_native_attempts=new),
        unverified_native=dict(attempts=attempts,count=len(attempts),reported_totals=reported,reserved_upper_totals=reserved,original_count=len(inherited),continuation_count=len(new)),
        observed_dispatch_totals=observed,provider_cost_usd=0,reused_original_work_included=False)
    logical=joins._logical_resources(encode(envelope),verified)
    logical['unverified_native_condition_attribution']={condition:[a for a in attempts if a['phase']==condition] if condition in PHASES else []
        for condition in ('one_pass','critique_only','repair','removal')}
    logical['model_usage_scope']='Condition model_usage fields contain qualified native usage only; rejected completion reports and bounds remain separately attributed.'
    return resources,logical


def _command(interpreter,mode,fp,jp,output):
    launcher=LAUNCHER if mode=='worker' else LAUNCHER.replace('tether-sc05-recovery-worker','tether-sc05-recovery-admission')
    return [interpreter,'-I','-B','-c',launcher,str(old.REPO),str(old.REPO/'src'),str(old.REPO/'packages/tether/src'),
        '--'+mode,'--frame',fp['path'],'--frame-sha256',fp['sha256'],'--job',jp['path'],'--job-sha256',jp['sha256'],'--output',str(output)]


def _admission_limit(purpose,seconds):
    need(purpose in ('production','fictional_qualification'),'Explicit admission purpose')
    remaining=old.finite(seconds,'Admission enclosing allowance')
    allowance=min(3600 if purpose=='production' else 600,remaining-180-90-120)
    need(allowance>0,'Admission cannot consume startup, cleanup and minimum-cell reserves')
    return allowance


def _preflight(root,fp,frame,plan,inputs,proof):
    request=inputs.json(proof)
    need(isinstance(request,dict) and set(request)=={'kind','frame','output','preflight_bounds','metadata_only_before_admission','automatic_retry'},
         'Recovery preflight request fields')
    external=request['frame'];inputs.bound(external)
    need(external['sha256']==fp['sha256'] and external['bytes']==fp['bytes'] and
         not old.path(external['path']).is_relative_to(root),'External preflight frame differs or overlaps output')
    bounds=dict(repair_seconds=plan['budgets']['phase_remaining_seconds']['repair'],outer_seconds=plan['budgets']['outer_remaining_seconds'])
    need(all(type(bounds[key]) is int and 0<bounds[key]<=ceiling for key,ceiling in (('repair_seconds',7200),('outer_seconds',43200))),
         'Preflight cannot exceed inherited absolute clocks')
    need(same(request,dict(kind='sc05_recovery_preflight_request_v2',frame=external,output=str(root),preflight_bounds=bounds,
         metadata_only_before_admission=True,automatic_retry=False)),'Recovery preflight reset or scope differs')
    return [('recovery_preflight_started',dict(request=proof,frame=external,limits=bounds)),
        ('recovery_preflight_admitted',dict(parent_identity=plan['parent_identity'],original_frame=plan['original_frame'],
            plan=frame['plan'],authority=frame['authority']))]


def _admission(pr,fp,jp,job,frame,plan,inputs,old_frame,worker_res):
    root=pr/'admission';files=inputs.inventory(root)
    old._membership(root,('COMMAND.json','PROCESS.json','stdout.bin','stderr.bin','COMPLETE.json'),('worker',))
    wr=root/'worker';old._membership(wr,('REQUEST.json','REPORT.json','journal.jsonl','RECEIPT.json'),())
    command=_command(old_frame['interpreter']['path'],'admission',fp,jp,wr)
    need(inputs.json(files['COMMAND.json'])==command,'Separate trusted admission command')
    process=inputs.json(files['PROCESS.json']);limits=dict(timeout_seconds=_admission_limit(frame['purpose'],job['seconds']),max_output_bytes=4*1024**2)
    original._terminated(process,root,files,inputs,limits,0)
    receipt=inputs.json(files['worker/RECEIPT.json']);wf=inputs.inventory(wr,omit=('RECEIPT.json',))
    need(receipt==dict(kind='sc05_recovery_admission_receipt_v2',status='admitted',files=wf),'Trusted admission byte inventory')
    need(inputs.json(files['COMPLETE.json'])==dict(status='admitted',receipt=files['worker/RECEIPT.json'],frame=fp,job=jp,model_or_http_execution_performed=False),
         'Trusted admission terminal binding')
    need(inputs.json(wf['REQUEST.json'])==dict(frame=fp,job=jp,role='trusted_parent_admission',model_or_http_execution_performed=False),'Trusted admission request scope')
    expected=dict(kind='sc05_recovery_worker_admission_v2',status='admitted',frame=fp,job=jp,plan=frame['plan'],authority=frame['authority'],
        parent_identity=plan['parent_identity'],original_frame=plan['original_frame'],partition=plan['partition'],budgets=plan['budgets'],phase=job['phase'],
        dispatch_ordinals=job['dispatch_ordinals'],model_or_http_execution_performed=False,scientific_answers_returned=False)
    report=inputs.json(wf['REPORT.json']);need(report==expected,'Separate trusted parent admission differs')
    events=old._events(inputs,wf['journal.jsonl']);reservation=old._reserved(events[0])
    need([(e['event'],e['details']) for e in events[1:]]==[('recovery_worker_admitted',dict(report_sha256=fingerprint(report)))],
         'Trusted admission journal binding')
    need(reservation['owner_pid']!=worker_res['owner_pid'] and old.historical.utc(reservation['created_at_utc'])<=old.historical.utc(worker_res['created_at_utc']),
         'Source-rich admission must use a separate process before model worker reservation')
    return dict(supervision=process['supervision'],receipt=files['worker/RECEIPT.json'],report=wf['REPORT.json'],source_rich_admission_separate_process=True)


def _envelope(descriptor,baseline_acceptance):
    need(isinstance(descriptor,dict) and set(descriptor)=={'root','receipt_sha256'},'External recovery root receipt required')
    inputs=accepted_primary._Inputs();root=old.path(descriptor['root']);rp,receipt=inputs.anchored(root/'ROOT-RECEIPT.json',descriptor['receipt_sha256'])
    files=inputs.inventory(root,omit=('ROOT-RECEIPT.json',))
    need(receipt==dict(kind='sc05_refinement_recovery_root_receipt_v2',status='recovery_execution_complete',frame_sha256=files['FRAME.json']['sha256'],files=files),
         'Recovery complete root byte inventory')
    old._membership(root,{'FRAME.json','REQUEST.json','COMPLETE.json','ROOT-RECEIPT.json','journal.jsonl'}|{p+'-ANCHOR.json' for p in PHASES},PHASES)
    need(not any(Path(n).name in ('DEADLINE.json','FINALIZATION-FAILED.json') for n in files),'Recovery deadline/finalization failure dominates success')
    fp=files['FRAME.json'];frame=inputs.json(fp)
    need(same(frame['parent']['baseline_acceptance'],baseline_acceptance),'Separate baseline acceptance differs from recovery parent')
    parent,plan,authority,claim=_frame(frame,root,inputs)
    state=original._state(parent);old_frame=encode(state['frame']);model=encode(state['model']);payload=encode(parent.payload)
    original_job_path=str(Path(payload['original_root'])/'repair/JOB.json')
    original_proofs={p['path']:encode(p) for p in state['closure']['proofs']}
    old_job=inputs.json(original_proofs[original_job_path]);grant_map={p['path']:p for p in old_job['input_files']}
    original_frame=encode(payload['frame_proof'])
    need(original_frame['path']==str(Path(payload['completed_phases']['pair_prepare']['root']).parent/'FRAME.json'),
         'Original external phase frame location differs')
    need(original_frame['path'] not in grant_map or same(grant_map[original_frame['path']],original_frame),'Conflicting original metadata grant')
    grant_map[original_frame['path']]=original_frame;grants=[grant_map[k] for k in sorted(grant_map)]
    for proof in grants:inputs.bound(proof)
    complete=inputs.json(files['COMPLETE.json']);events=old._events(inputs,files['journal.jsonl']);reserved=old._reserved(events[0])
    need(set(complete)=={'status','purpose','phases','parent','plan','authority','scheduled','new_scheduled','inherited_failed_ordinal','wall_seconds','provider_cost_usd','scientific_scoring_performed','automatic_retry'} and
         complete['status']=='recovery_execution_complete' and complete['purpose']==frame['purpose'] and set(complete['phases'])==set(PHASES) and
         complete['parent']==frame['parent'] and complete['plan']==frame['plan'] and complete['authority']==frame['authority'] and
         complete['scheduled']==len(plan['schedule']) and complete['new_scheduled']==plan['budgets']['max_new_generation_calls'] and
         complete['inherited_failed_ordinal']==payload['failed_ordinal'] and complete['provider_cost_usd']==0 and
         complete['scientific_scoring_performed'] is False and complete['automatic_retry'] is False,'Recovery full denominator and inherited failure')
    need(old.historical.utc(payload['original_started_at_utc'])<=old.historical.utc(reserved['created_at_utc']),'Recovery predates original attempt')
    phases={};resources={};contexts={};expected_events=_preflight(root,fp,frame,plan,inputs,files['REQUEST.json'])
    physical=set(state['semantic']['physical_ids']);total_seconds=0;failure_paths=set()
    for phase in PHASES:
        pr=root/phase;anchor=complete['phases'][phase]
        need(set(anchor)=={'root','package_sha256','stage_receipt_sha256'} and anchor['root']==str(pr) and inputs.json(files[phase+'-ANCHOR.json'])==anchor,
             'Recovery phase exact anchor')
        pp=files[phase+'/PACKAGE-RECEIPT.json'];package=inputs.json(pp);pf=inputs.inventory(pr,omit=('PACKAGE-RECEIPT.json',))
        need(pp['sha256']==anchor['package_sha256'] and package==dict(kind='sc05_recovery_phase_receipt_v2',status='complete',phase=phase,frame_sha256=fp['sha256'],files=pf),
             'Recovery phase byte inventory')
        old._membership(pr,('JOB.json','COMMAND.json','PROCESS.json','stdout.bin','stderr.bin','PACKAGE-RECEIPT.json','PHASE-TIMING.json'),('worker','admission'))
        jp=pf['JOB.json'];job=inputs.json(jp)
        fields={'phase','frame_sha256','input_files','model_bindings','parent_pair','baseline','dispatch_ordinals','seconds','stage_seconds','original_slots','execution_claim','phase_preflight_seconds','outer_preflight_seconds'}
        need(set(job)==fields and job['phase']==phase and job['frame_sha256']==fp['sha256'] and job['input_files']==grants and job['model_bindings']==model['bindings'] and
             job['parent_pair']==payload['completed_phases']['pair_prepare'] and job['baseline']==old_frame['baseline'] and
             job['dispatch_ordinals']==plan['partition'][phase+'_dispatch'] and job['execution_claim']==claim and
             job['original_slots']==([r['execution_id'] for r in payload['repair_rows']] if phase=='repair' else [None]*len(plan['schedule'])),
             'Continuation source-only grants, original slots and immutable execution claim')
        preflight=old.finite(job['phase_preflight_seconds'],'New phase preflight');outer=old.finite(job['outer_preflight_seconds'],'New outer preflight')
        need(preflight<=outer and total_seconds<=outer,'Nested continuation preflight clocks')
        seconds=int(min(plan['budgets']['phase_remaining_seconds'][phase]-preflight,plan['budgets']['outer_remaining_seconds']-outer-60))
        stage_seconds=min(seconds-90,plan['budgets']['repair_stage_remaining_seconds'] if phase=='repair' else seconds-90)
        need(seconds>120 and stage_seconds>0 and type(job['seconds']) is int and job['seconds']==seconds and job['stage_seconds']==stage_seconds,'Continuation cannot reset preflight budgets')
        limits=dict(timeout_seconds=seconds,max_output_bytes=4*1024**2);command=_command(old_frame['interpreter']['path'],'worker',fp,jp,pr/'worker')
        need(inputs.json(pf['COMMAND.json'])==command,'Recovery exact isolated worker command')
        process=inputs.json(pf['PROCESS.json']);original._terminated(process,pr,pf,inputs,limits,0);supervision=process['supervision'];total_seconds+=supervision['execution_elapsed_seconds']
        timing=inputs.json(pf['PHASE-TIMING.json'])
        need(set(timing)=={'phase','start_offset_seconds','preflight_seconds','charged_wall_seconds','remaining_limit_seconds','scope'} and
             timing['phase']==phase and timing['preflight_seconds']==preflight and timing['remaining_limit_seconds']==plan['budgets']['phase_remaining_seconds'][phase],
             'Entire continuation phase clock binding')
        offset=old.finite(timing['start_offset_seconds'],'Phase start offset');charged=old.finite(timing['charged_wall_seconds'],'Entire phase elapsed')
        need(offset<=outer and (offset==0 if phase=='repair' else offset>0) and preflight<=charged and supervision['total_elapsed_seconds']<=charged<timing['remaining_limit_seconds'],
             'Verification/startup/execution inside remaining phase allowance')
        expected_events += [('recovery_phase_reserved',dict(phase=phase,job=jp,command=command,limits=limits)),('recovery_phase_completed',dict(phase=phase,anchor=anchor))]
        wr=pr/'worker';old._membership(wr,('CONFIG.json','COMPLETE.json','MODEL.json','io-audit.jsonl','journal.jsonl','SERVER-RESOURCE-SAMPLES.json'),('phase','server'))
        we=old._events(inputs,pf['worker/journal.jsonl']);worker_res=old._reserved(we[0]);terminal=inputs.json(pf['worker/COMPLETE.json'])
        need(old.historical.utc(reserved['created_at_utc'])<=old.historical.utc(worker_res['created_at_utc']),'Recovery worker chronology')
        need(inputs.json(pf['worker/CONFIG.json'])==dict(frame_sha256=fp['sha256'],job_sha256=jp['sha256'],phase=phase,purpose=frame['purpose'],
             worker_pid=worker_res['owner_pid'],python_version=sys.version,coordinator_grants=grants) and inputs.json(pf['worker/MODEL.json'])==model,'Recovery actual worker/model identity')
        execution=Path(claim['path']).parent
        authority_proof,_=inputs.capture(execution/(phase+'-AUTHORIZED-JOB.json'));worker_claim,_=inputs.capture(execution/(phase+'-WORKER-CLAIM.json'))
        need(inputs.json(authority_proof)==dict(frame_sha256=fp['sha256'],job=jp,output=str(wr)) and
             inputs.json(worker_claim)==dict(frame_sha256=fp['sha256'],job_sha256=jp['sha256'],output=str(wr),owner_pid=worker_res['owner_pid']),
             'Permanent per-phase authorization/one-worker claim')
        admission=_admission(pr,fp,jp,job,frame,plan,inputs,old_frame,worker_res)
        need(set(terminal)=={'status','phase','purpose','frame_sha256','stage_receipt','wall_seconds','worker_memory','server_terminal','audit_denials','provider_cost_usd','reference_keys_read','scientific_scoring_performed'} and
             terminal['status']=='complete' and terminal['phase']==phase and terminal['purpose']==frame['purpose'] and terminal['frame_sha256']==fp['sha256'] and
             type(terminal['audit_denials']) is int and terminal['audit_denials']==0 and terminal['provider_cost_usd']==0 and
             terminal['reference_keys_read'] is False and terminal['scientific_scoring_performed'] is False,'Recovery worker successful scope')
        wall=old.finite(terminal['wall_seconds'],'Recovery worker wall');need(admission['supervision']['execution_elapsed_seconds']<=wall<seconds,'Admission inside recovery worker budget')
        sp=pf['worker/phase/STAGE-RECEIPT.json'];need(sp==terminal['stage_receipt'] and sp['sha256']==anchor['stage_receipt_sha256'],'Recovery stage anchor')
        stage=_stage(wr/'phase',sp,phase,frame,job,plan,inputs,wall,supervision['execution_elapsed_seconds']);phases[phase]=stage
        for row in stage['rows']:
            need(row['execution_id'] not in physical,'Old or new physical execution identity repeated');physical.add(row['execution_id'])
            if row['status']=='authenticated_limit_failure':failure_paths.add(f'{phase}/worker/phase/products/{row["ordinal"]:04d}/FAILURE.json')
        server=terminal['server_terminal'];old._membership(wr/'server',('server-command.json','server.stdout.log','server.stderr.log'),())
        need(server['started'] is True and server['server_stopped'] is True and type(server['pid']) is int and server['pid']>0 and
             type(server['exit_code']) is int and server['secondary_failures']==[] and 'error_class' not in server and
             old.finite(server['elapsed_seconds'],'Recovery server elapsed')<=wall and inputs.json(pf['worker/server/server-command.json'])==model['spec'],
             'Recovery owned native lifecycle')
        need([(e['event'],e['details']) for e in we[1:]]==[('server_started',dict(pid=server['pid'])),('server_ready',dict(pid=server['pid'])),
             ('server_terminal',server),('recovery_worker_completed',dict(terminal_sha256=fingerprint(terminal)))],'Recovery worker/server journal')
        samples=inputs.json(pf['worker/SERVER-RESOURCE-SAMPLES.json']);need(isinstance(samples,list) and 0<len(samples)<=100000,'Recovery resource samples')
        for sample in samples:
            need(set(sample)=={'monotonic','value','error_class'},'Recovery sample schema');old.finite(sample['monotonic'],'Sample clock');old._memory(sample['value'])
        audit=_audit(wr,phase,frame,job,fp,jp,model,stage['rows'],inputs,pf['worker/io-audit.jsonl'],old_frame)
        contexts[phase]=dict(model_provenance=model['provenance'],alias=model['alias'],owner_pid=server['pid'],endpoint=f'http://127.0.0.1:{old_frame["port"]}')
        resources[phase]=dict(supervision=supervision,worker_wall_seconds=wall,worker_memory=old._memory(terminal['worker_memory']),
            stage_accounting=stage['report']['accounting'],io_audit=audit,server_terminal=server,admission=admission,phase_timing=timing)
    need({n for n in files if Path(n).name=='FAILURE.json'}==failure_paths,'Only authenticated rejected cell failures may coexist with completed recovery')
    expected_events.append(('recovery_execution_completed',dict(phases=list(PHASES))))
    need([(e['event'],e['details']) for e in events[1:]]==expected_events,'Recovery exact phase reservation/terminal sequence')
    wall=old.finite(complete['wall_seconds'],'Recovery root wall')
    need(total_seconds<=wall<plan['budgets']['outer_remaining_seconds'],'Recovery total remaining deadline')
    envelope=dict(root=str(root),root_receipt_sha256=rp['sha256'],frame=old_frame,recovery_frame=frame,phases=phases,model_contexts=contexts,
        original_producer_descriptor=payload['original_producer_descriptor'],original_started_at_utc=payload['original_started_at_utc'],started_at_utc=reserved['created_at_utc'],
        baseline_acceptance=payload['baseline_acceptance'],baseline=encode(state['baseline']),supervised_root_verified=True,actor_roles_verified=True,baseline_verified=True,
        resources=dict(original_attempt=payload['resources'],continuation=dict(phases=resources,wall_seconds=wall),original_resources=payload['resources']['original_resources'],
            baseline_resources=payload['resources']['baseline_resources'],historical_work_reexecuted=False),
        proofs=dict(final_root_receipt=rp,original_inspection=frame['parent']['inspection'],original_source_archive=frame['parent']['source_archive'],
            original_frame=payload['frame_proof'],original_failure=payload['original_producer_descriptor']['original_failure'],authority=frame['authority'],execution_claim=claim),
        original_preserved_as_failed=True,archived_code_executed=False,scientific_correctness_scored=False)
    return envelope,parent,inputs


def _attempt(phase,ordinal,origin,descriptor):
    d=encode(descriptor)
    return dict(phase=phase,ordinal=ordinal,origin=origin,execution_id=d['execution_id'],descriptor=d,
        raw_reported_usage=d['raw_reported_usage'],conservative_reservation=d['conservative_reservation'])


def _join(envelope,parent,inputs):
    state=original._state(parent);semantic=encode(state['semantic']);baseline=encode(state['baseline']);frame=encode(state['frame'])
    model=encode(state['model']);ids=frame['schedule'];failed=semantic['failed_ordinal'];phases=envelope['phases']
    mapped={phase:{row['ordinal']:row for row in phases[phase]['rows']} for phase in PHASES}
    need(set(mapped['repair'])==set(range(failed+1,len(ids))) and set(mapped['removal'])==set(range(len(ids))), 'Exact final untouched continuation coverage')
    records=dict(one_pass=[],repair=[],removal=[]);evidence={k:{} for k in records};cases=[]
    continued={p:dict.fromkeys(old.FIELDS,0) for p in old.PHASES}
    attempts=[_attempt('repair',failed,'original',semantic['failed_call'])]
    for i,case in enumerate(baseline['cases']):
        prepared=semantic['prepared'][i];query=prepared['query'];prior=prepared['prior'];critic=prepared['critic'];context=prepared['context']
        control=prepared['control_sha256'];key=query['id'];need(key==ids[i] and case['query']==query,'Original complete query order')
        records['one_pass'].append(case['original_disposition']);evidence['one_pass'][key]=[s['source_id'] for s in case['original_selected_sources']]
        physical={phase:state['stages'][phase]['rows'][i]['execution_id'] for phase in original.PREFIX}
        origins={p:'original' for p in original.PREFIX}
        for task in PHASES:
            raw=prepared['sources'] if task=='repair' else [];evidence[task][key]=[s['source_id'] for s in raw]
            if task=='repair' and i<=failed:
                decision=semantic['repair_records'][i];need(decision is not None,'Original entered repair disposition missing')
                records[task].append(decision);physical[task]=state['stages']['repair']['rows'][i]['execution_id'];origins[task]='original';continue
            row=mapped[task][i];stage=phases[task];member=prepared['members'][task];cellroot=Path(stage['root'])/'products'/f'{i:04d}'
            descriptor=dict(task=task,query=query,prior=prior,critic=critic,sources=raw,model_provenance=frame['model_provenance'],prepared_member=member,control_sha256=control)
            if row['status']=='authenticated_limit_failure':
                product=row['product'];need(set(product)=={'limit_failure','disposition','paired_member_sha256','control_sha256','source_context_sha256'} and
                    row['accounting'] is None and row['reason']=='native_completion_limit' and member['status']=='ready','Authenticated continuation failure product')
                expected=dict(task=task,query=query,candidate_context=prior,critique_context=critic,sources=raw,model_provenance=frame['model_provenance'],
                    prepared_member=member,control_sha256=control)
                prefix=f'products/{i:04d}/';cellfiles={name[len(prefix):]:p for name,p in stage['files'].items() if name.startswith(prefix)}
                verified=native_failure.verify_cell_limit_failure(cellroot,files=cellfiles,expected_inputs=expected,expected_request=member['request'],expected_payload=member['payload'],
                    execution_id=row['execution_id'],owner_pid=envelope['model_contexts'][task]['owner_pid'],alias=model['alias'],server_spec=model['spec'],bindings=model['bindings'])
                proof=stage['files'][f'limit_failures/{i:04d}.json']
                need(proof==product['limit_failure'] and same(inputs.json(proof),verified),'Independently authenticated continuation rejected response')
                decision=dict(id=key,producer_status='error',check_status='not_run',prediction=None,reason='native_completion_limit')
                attempts.append(_attempt(task,i,'continuation',verified))
            else:
                cell=joins._cell(stage,row,descriptor,envelope['model_contexts'][task],semantic['model_code'])
                checked=source.disposition(query,cell,context);decision=checked['disposition'];product=row['product']
                need(joins._product(product['decision'],cellroot/'DECISION.json')==checked['decision'],'Continuation independent raw-span admission')
                for field in old.FIELDS:continued[task][field]+=row['accounting'][field]
            need(product['disposition']==decision and product['paired_member_sha256']==fingerprint(member) and product['control_sha256']==control and
                 product['source_context_sha256']==fingerprint(context),'Continuation native/source/original pair join')
            records[task].append(decision);physical[task]=row['execution_id'];origins[task]='continuation'
        cases.append(dict(id=key,critic=critic,semantic_selection=joins._selection(query,prior,critic),original=records['one_pass'][-1],repair=records['repair'][-1],removal=records['removal'][-1],
            physical_execution_ids=physical,physical_execution_origins=origins,control_sha256=control,source_context_sha256=fingerprint(context)))
    for phase in PHASES:need(continued[phase]==phases[phase]['report']['accounting']['known_totals'],'Continuation native verified accounting differs')
    old_measured={phase:semantic['measured'].get(phase,dict.fromkeys(old.FIELDS,0)) for phase in old.PHASES}
    resources,logical=resource_tables(old_measured,continued,attempts,envelope)
    need(all([r['id'] for r in values]==ids for values in records.values()),'Every original case retained exactly once')
    need(records['repair'][failed]==dict(id=ids[failed],producer_status='error',check_status='not_run',prediction=None,reason='native_completion_limit'),
         'Inherited failure cannot become a produced answer')
    return dict(status='independently_reconstructed_recovery',purpose=frame['purpose'],queries=baseline['queries'],records=records,evidence_ids=evidence,
        critics=semantic['critics'],source_cases=semantic['source_cases'],case_products=cases,incremental_resources=resources,logical_resources=logical,
        source_lineage_checked=True,native_calls_checked=True,cross_stage_products_checked=True,original_preserved_as_failed=True,
        inherited_failed_ordinal=failed,failed_completion_answers_accepted=False,scientific_support_verified=False)


def reconstruct(descriptor,*,baseline_acceptance):
    envelope,parent,inputs=_envelope(encode(descriptor),encode(baseline_acceptance))
    report=_join(envelope,parent,inputs)
    original.revalidate(parent);inputs.unchanged()
    root=envelope['root'];sha=envelope['root_receipt_sha256'];frozen_report=freeze(report);frozen_envelope=freeze(envelope)
    value=VerifiedRecovery(root,sha,frozen_report,frozen_envelope,
        fingerprint(dict(root=root,receipt_sha256=sha,report=frozen_report,envelope=frozen_envelope)),_TOKEN,parent,original.snapshot(inputs))
    _ISSUED[id(value)]=value
    _SEALS[id(value)]=(value._fingerprint,fingerprint(value._closure),id(parent))
    import weakref
    weakref.finalize(value,_SEALS.pop,id(value),None)
    return value
