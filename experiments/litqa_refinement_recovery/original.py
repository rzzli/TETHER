"""Independent reconstruction of an immutable, failed refinement parent.

No producer verifier or archived Python is executed. Complete predecessor phases,
the interrupted repair prefix, input roles and native/source joins are verified
before an operation-scoped capability is issued. This is never a v1 success root.
"""
from dataclasses import dataclass, field
from pathlib import Path
import sys
from weakref import WeakValueDictionary

from tether_engine.serde import encode, freeze
from experiments.litqa_analysis import accepted_primary, source_archive
from experiments.litqa_refinement import envelopes as old
from experiments.litqa_refinement import evaluation as joins
from experiments.litqa_refinement import native_evaluation as native
from experiments.litqa_refinement import source_evaluation as source

need = old.need


def same(left,right): return old.same(encode(left),encode(right))
def fingerprint(value): return old.fingerprint(encode(value))
PREFIX = ('critic', 'refinement_collect', 'pair_prepare')
_TOKEN = object()
_ISSUED = WeakValueDictionary()
_STATES = {}
_SEALS = {}


@dataclass(frozen=True)
class VerifiedParent:
    payload: object
    _fingerprint: str = field(repr=False)
    _token: object = field(default=None, repr=False, compare=False)
    _state_fingerprint: str = field(default='', repr=False, compare=False)


def _state(value):
    need(type(value) is VerifiedParent and _ISSUED.get(id(value)) is value and value._token is _TOKEN,
         'Issued original-parent capability required')
    need(_SEALS.get(id(value))==(value._fingerprint,value._state_fingerprint),'Original-parent issuance seal changed')
    need(fingerprint(value.payload) == value._fingerprint, 'Original-parent capability mutated')
    need(id(value) in _STATES, 'Original-parent state unavailable')
    state=_STATES[id(value)]
    need(fingerprint(state) == value._state_fingerprint,
         'Original-parent reconstructed state mutated')
    return state


def snapshot(inputs):
    """Keep immutable byte-check instructions, never a mutable verifier handle."""
    return freeze(dict(proofs=[encode(p) for _,p in sorted(inputs.proofs.items())],inventories=[
        dict(root=str(root),omit=list(omit),recursive=recursive,files=encode(files)) for root,omit,recursive,files in inputs.inventories]))


def verify_snapshot(value):
    value=encode(value);need(set(value)=={'proofs','inventories'},'Immutable verifier closure schema')
    inputs=accepted_primary._Inputs()
    for proof in value['proofs']:inputs.bound(proof)
    for entry in value['inventories']:
        need(set(entry)=={'root','omit','recursive','files'} and type(entry['recursive']) is bool,'Immutable inventory closure schema')
        actual=inputs.inventory(entry['root'],omit=entry['omit'],recursive=entry['recursive'])
        need(same(actual,entry['files']),'Original immutable inventory closure changed')
    return inputs


def _archive(inputs, descriptor, frame):
    inputs.bound(descriptor)
    pins = {Path(p['path']).relative_to(old.REPO).as_posix():p['sha256'] for p in frame['code_files']}
    need(len(pins) == len(frame['code_files']), 'Duplicate original source pin')
    archive = source_archive.load_archive(descriptor['path'], descriptor['sha256'], pins, str(old.REPO))
    for name in archive.logical_names: inputs.bound(archive.proof(name))
    # Existing independent parsers require the exact, still-installed producer
    # syntax. A later migration needs a new qualified bridge, never archive exec.
    need(same(frame['code_files'], old._closure(inputs)), 'Original executed closure changed')
    return archive


def _inspection(inputs, proof):
    receipt = inputs.json(proof); base = old.path(proof['path']).parent
    need(receipt['kind'] == 'sc05_failed_production_metadata_audit_receipt_v1' and receipt['status'] == 'complete',
         'Externally pinned failed-parent inspection receipt required')
    files = inputs.inventory(base, omit=('RECEIPT.json',))
    need(same(receipt['files'], files), 'Inspection exact inventory differs')
    report = inputs.json(files['RESULT.json'])
    need(report['kind'] == 'sc05_failed_production_metadata_forensics_v1' and
         report['status'] == 'metadata_and_byte_inventory_verified', 'Inspection result scope')
    roots = []
    for name, field_name in (('ORIGINAL-INVENTORY.json','original_root'), ('FREEZE-INVENTORY.json','freeze_root')):
        declared = inputs.json(files[name]); root = old.path(report[field_name])
        actual = inputs.inventory(root)
        need(declared['root'] == str(root) and same(declared['files'], actual), 'Original/freeze inventory changed')
        directories = sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir())
        need(declared['directories'] == directories, 'Original/freeze directories changed')
        roots.append((root,actual))
    return report, roots


def _process(pr, frame, fp, jp, phase, inputs, files, expected_return):
    if expected_return == 0: return old._supervision(pr, frame, fp, jp, phase, inputs, files)
    command = [frame['interpreter']['path'],'-I','-B','-c',old.LAUNCHER,str(old.REPO),str(old.REPO/'src'),str(old.REPO/'packages/tether/src'),
        '--worker','--frame',fp['path'],'--frame-sha256',fp['sha256'],'--job',jp['path'],'--job-sha256',jp['sha256'],'--output',str(pr/'worker')]
    need(inputs.json(files['COMMAND.json']) == command, 'Failed phase exact command')
    value = inputs.json(files['PROCESS.json']); limits = dict(timeout_seconds=frame['phase_seconds'][phase]+60,max_output_bytes=4*1024**2)
    _terminated(value, pr, files, inputs, limits, expected_return)
    return value['supervision'],command,limits


def _terminated(value, root, files, inputs, limits, expected_return):
    need(set(value) == {'returncode','supervision'} and type(value['returncode']) is int and value['returncode'] == expected_return,
         'Original process return code')
    s = value['supervision']
    need(s['schema_version'] == 1 and s['method'] == 'tether.process_envelope.v1' and same(s['limits'],limits) and
         s['termination_reason'] == 'exited' and s['process_started'] is True and s['process_reaped'] is True and
         s['pipe_eof'] == dict(stdout=True,stderr=True) and s['cleanup_errors'] == [] and s['observed_counts_are_lower_bounds'] is False,
         'Original process terminal cleanup not proven')
    for stream in ('stdout','stderr'):
        count = len(inputs.bound(files[stream+'.bin']))
        need(type(s['retained_'+stream+'_bytes']) is int and count == s['retained_'+stream+'_bytes'] == s['observed_'+stream+'_bytes'],
             'Original process stream accounting')
    need(s['retained_stdout_bytes']+s['retained_stderr_bytes'] <= limits['max_output_bytes'] and
         old.finite(s['execution_elapsed_seconds'],'Process duration') < limits['timeout_seconds'] and
         old.finite(s['total_elapsed_seconds'],'Total process duration') >= s['execution_elapsed_seconds'], 'Original process timing')


def _stage_membership(root,phase,rows,*,incomplete=False):
    """Every retained slot/product belongs to the reconstructed schedule."""
    entered=[row for row in rows if row['status']!='unexecuted']
    successful=[row for row in entered if row['status']!='failed']
    failed=[row for row in entered if row['status']=='failed']
    products=[row for row in entered if not (phase=='refinement_collect' and row['status']=='unavailable')]
    directories=set()
    if successful:directories.add('slots')
    if failed:directories.add('failures')
    if products:directories.add('products')
    old._membership(root,{'CONFIG.json','INPUTS.json','REPORT.json','journal.jsonl','STAGE-RECEIPT.json'}|
        ({'FAILURE.json'} if incomplete else set()),directories)
    for name,values in (('slots',successful),('failures',failed)):
        if values:old._membership(root/name,{f'{row["ordinal"]:04d}.json' for row in values},set())
    if products:old._membership(root/'products',set(),{f'{row["ordinal"]:04d}' for row in products})


def _partial_stage(root, sp, frame, job, inputs, worker_seconds, process_seconds):
    receipt = inputs.json(sp); files = inputs.inventory(root,omit=('STAGE-RECEIPT.json',))
    need(set(receipt) == {'kind','status','files','seal_elapsed_seconds','automatic_retry'} and
         receipt['kind'] == 'tether_refinement_stage_receipt_v1' and receipt['status'] == 'incomplete' and
         receipt['automatic_retry'] is False and same(receipt['files'], {n:{k:p[k] for k in ('bytes','sha256')} for n,p in files.items()}),
         'Failed stage immutable receipt')
    config = inputs.json(files['CONFIG.json']); report = inputs.json(files['REPORT.json']); data = inputs.json(files['INPUTS.json'])
    namespace = config['execution_namespace']
    from uuid import UUID
    need(str(UUID(namespace)) == namespace and config['kind'] == 'tether_refinement_stage_v1' and config['phase'] == 'repair' and
         config['purpose'] == frame['purpose'] and config['ids'] == frame['schedule'] and config['cell_limits'] == old._limits('repair'),
         'Failed repair schedule/context')
    ordered = [dict(ordinal=i,id=key,phase='repair',execution_id=f'{namespace}-repair-{i:04d}') for i,key in enumerate(frame['schedule'])]
    need(config['schedule'] == ordered and 0 < old.finite(config['seconds'],'Stage budget') <= frame['phase_seconds']['repair'], 'Failed stage fixed limits')
    expected_inputs = dict(baseline=frame['baseline'],parents={n:dict(root=str(Path(a['root'])/'worker/phase'),receipt_sha256=a['stage_receipt_sha256']) for n,a in job['parents'].items()},
        cutoff=None,model_provenance=frame['model_provenance'],reference_keys_available=False,scoring_performed=False)
    need(same(data,expected_inputs), 'Failed repair exact inputs')
    elapsed = old.finite(report['wall_seconds'],'Stage duration'); seal = old.finite(receipt['seal_elapsed_seconds'],'Stage sealing')
    need(elapsed <= seal <= worker_seconds <= process_seconds and elapsed < config['seconds'], 'Failed stage/worker/process clocks')
    rows = report['rows']; need(len(rows) == len(ordered), 'Failed stage full denominator')
    events = old._events(inputs,files['journal.jsonl']); old._reserved(events[0])
    expected = [('refinement_stage_configured',dict(config_sha256=fingerprint(config)))]; failed = None; known = []
    for row,slot in zip(rows,ordered):
        need(set(row) == set(slot)|{'status','reason','product','accounting'} and all(row[k] == v for k,v in slot.items()), 'Original row identity')
        status = row['status']; index = slot['ordinal']
        if status == 'unexecuted':
            need(failed is not None and row['reason'] is None and row['product'] is None and row['accounting'] is None,
                 'Unexecuted row must follow failure without product/accounting')
            need(not any(n.startswith(f'products/{index:04d}/') or n in (f'slots/{index:04d}.json',f'failures/{index:04d}.json') for n in files),
                 'Untouched slot has entered artifacts')
            continue
        need(failed is None, 'Original resumed or repeated after failure')
        expected.append(('refinement_slot_reserved',dict(slot=slot,limits=config['cell_limits'])))
        if status == 'failed':
            failed = index
            need(row['reason'] == 'ContractError' and row['product'] is None and row['accounting'] is None, 'Failed native disposition/accounting')
            name = f'failures/{index:04d}.json'
            expected.append(('refinement_slot_failed',dict(ordinal=index,path=name,slot_sha256=fingerprint(row),status='failed',reason='ContractError')))
        else:
            need(status in old.ALLOWED['repair'] and row['product'] is not None, 'Original accepted prefix status')
            old._accounting(row['accounting'],'repair',status); known.append(row['accounting']); name=f'slots/{index:04d}.json'
            expected.append(('refinement_slot_terminal',dict(ordinal=index,path=name,slot_sha256=fingerprint(row),status=status)))
        need(same(inputs.json(files[name]),row),'Original slot/report byte binding')
    need(failed is not None, 'One original failed repair is required')
    if frame['purpose'] == 'production': need(failed == 184, 'Fixed production failure boundary')
    rebuilt = dict(kind='tether_refinement_stage_report_v1',phase='repair',purpose=frame['purpose'],status='incomplete',scheduled=len(rows),
        entered=failed+1,unexecuted=len(rows)-failed-1,rows=rows,wall_seconds=elapsed,
        accounting=dict(known_totals={k:sum(r[k] for r in known) for k in old.FIELDS},provider_cost_usd=0,
            uncertain_cells=[rows[failed]['id']],measurements_complete=False,uncertain_per_cell_ceiling=config['cell_limits'],historical_work_included=False),automatic_retry=False)
    need(same(report,rebuilt),'Failed repair independently rebuilt accounting')
    expected.append(('refinement_stage_finalized',dict(status='incomplete',report_sha256=fingerprint(report))))
    need([(e['event'],e['details']) for e in events[1:]] == expected,'Original repair exclusive event sequence')
    need(inputs.json(files['FAILURE.json']) == dict(automatic_retry=False,error_type='ContractError'),'Original stage failure marker')
    _stage_membership(root,'repair',rows,incomplete=True)
    return dict(root=str(root),rows=rows,inputs=data,report=report,failed_ordinal=failed,config=config,seal_elapsed_seconds=seal)


def _phases(root,files,frame,fp,model,base_grants,inputs,reservation):
    failure = inputs.json(files['FAILURE.json']); anchors = failure['completed_phases']
    need(set(failure) == {'automatic_retry','completed_phases','error_type','message','stage','wall_seconds'} and
         set(anchors) == set(PREFIX) and failure['automatic_retry'] is False and failure['stage'] == 'repair' and
         failure['error_type'] == 'ValueError' and failure['message'] == 'Refinement worker failed; no automatic retry', 'Original failure terminal')
    old._membership(root,{'FRAME.json','FAILURE.json','journal.jsonl'}|{p+'-ANCHOR.json' for p in PREFIX},(*PREFIX,'repair'))
    events = old._events(inputs,files['journal.jsonl']); expected_events=[]; prior_grants={}; stages={}; resources={}; contexts={}; pairs={}
    for phase in (*PREFIX,'repair'):
        failed = phase == 'repair'; pr=root/phase; pf=inputs.inventory(pr,omit=() if failed else ('PACKAGE-RECEIPT.json',))
        anchor = None if failed else anchors[phase]
        if not failed:
            need(set(anchor)=={'root','package_sha256','stage_receipt_sha256'} and anchor['root']==str(pr) and
                 inputs.json(files[phase+'-ANCHOR.json'])==anchor,'Original phase anchor')
            pp=files[phase+'/PACKAGE-RECEIPT.json']; package=inputs.json(pp)
            need(pp['sha256']==anchor['package_sha256'] and same(package,dict(kind='sc05_refinement_phase_receipt_v1',status='complete',phase=phase,frame_sha256=fp['sha256'],files=pf)), 'Original complete phase inventory')
        old._membership(pr,{'JOB.json','COMMAND.json','PROCESS.json','stdout.bin','stderr.bin'}|(set() if failed else {'PACKAGE-RECEIPT.json'}),{'worker'})
        jp=pf['JOB.json']; job=inputs.json(jp); grants=dict(base_grants)
        for parent in old.PARENTS[phase]:
            for name,p in prior_grants[parent].items():
                need(name not in grants or grants[name]==p,'Conflicting original ancestry'); grants[name]=p
        expected_job=dict(phase=phase,frame_sha256=fp['sha256'],parents={p:anchors[p] for p in old.PARENTS[phase]},
            input_files=[grants[k] for k in sorted(grants)],model_bindings=model['bindings'],cutoff=job['cutoff'] if phase=='pair_prepare' else None)
        need(same(job,expected_job),'Original coordinator exact role grants')
        for p in job['input_files']: inputs.bound(p)
        prior_grants[phase]=dict(grants); prior_grants[phase].update({p['path']:p for p in pf.values()})
        if not failed: prior_grants[phase][pp['path']]=pp
        supervision,command,limits=_process(pr,frame,fp,jp,phase,inputs,pf,1 if failed else 0)
        expected_events.append(('refinement_phase_reserved',dict(phase=phase,job=jp,command=command,limits=limits)))
        if not failed: expected_events.append(('refinement_phase_completed',dict(phase=phase,anchor=anchor)))
        wr=pr/'worker'; we=old._events(inputs,pf['worker/journal.jsonl']); worker_res=old._reserved(we[0]); is_model=phase in old.MODEL_PHASES
        old._chronology(reservation['created_at_utc'],worker_res['created_at_utc'],phase,job)
        need(same(inputs.json(pf['worker/CONFIG.json']),dict(frame_sha256=fp['sha256'],job_sha256=jp['sha256'],phase=phase,purpose=frame['purpose'],
             worker_pid=worker_res['owner_pid'],python_version=sys.version,coordinator_grants=job['input_files'])) and same(inputs.json(pf['worker/MODEL.json']),model),'Original worker/model identity')
        terminal=inputs.json(pf['worker/'+('FAILURE.json' if failed else 'COMPLETE.json')]); wall=old.finite(terminal['wall_seconds'],'Worker wall')
        need(wall < frame['phase_seconds'][phase], 'Original worker phase cap')
        if failed:
            old._membership(wr,('CONFIG.json','FAILURE.json','MODEL.json','io-audit.jsonl','journal.jsonl'),('phase','server'))
            need(set(terminal)=={'automatic_retry','error_type','message','server_terminal','stage','wall_seconds'} and
                 terminal['automatic_retry'] is False and terminal['error_type']=='ContractError' and terminal['message']=='Unqualified native completion cause' and
                 terminal['stage']=='phase_execution','Original failed worker reason')
        else:
            old._membership(wr,{'CONFIG.json','COMPLETE.json','MODEL.json','io-audit.jsonl','journal.jsonl'}|({'SERVER-RESOURCE-SAMPLES.json'} if is_model else set()),{'phase'}|({'server'} if is_model else set()))
            need(set(terminal)=={'status','phase','purpose','frame_sha256','stage_receipt','wall_seconds','worker_memory','server_terminal','audit_denials','provider_cost_usd','reference_keys_read','scientific_scoring_performed'} and
                 terminal['status']=='complete' and terminal['phase']==phase and terminal['purpose']==frame['purpose'] and terminal['frame_sha256']==fp['sha256'] and
                 type(terminal['audit_denials']) is int and terminal['audit_denials']==0 and terminal['provider_cost_usd']==0 and terminal['reference_keys_read'] is False and terminal['scientific_scoring_performed'] is False,'Original completed worker scope')
        sp=pf['worker/phase/STAGE-RECEIPT.json']
        if failed: stage=_partial_stage(wr/'phase',sp,frame,job,inputs,wall,supervision['execution_elapsed_seconds'])
        else:
            need(sp==terminal['stage_receipt'] and sp['sha256']==anchor['stage_receipt_sha256'],'Original worker/stage anchor')
            stage=old._stage(wr/'phase',sp,phase,frame,job,inputs,worker_seconds=wall,process_seconds=supervision['execution_elapsed_seconds'])
            _stage_membership(wr/'phase',phase,stage['rows'])
        stages[phase]=stage; server=terminal['server_terminal']; worker_events=[]
        if is_model:
            old._membership(wr/'server',('server-command.json','server.stdout.log','server.stderr.log'),())
            need(server['started'] is True and server['server_stopped'] is True and type(server['pid']) is int and server['pid']>0 and
                 type(server['exit_code']) is int and server['secondary_failures']==[] and old.finite(server['elapsed_seconds'],'Server wall')<=wall and
                 same(inputs.json(pf['worker/server/server-command.json']),model['spec']),'Original native ownership/cleanup')
            need(server.get('error_class')==('ContractError' if failed else None),'Original server error scope')
            worker_events=[('server_started',dict(pid=server['pid'])),('server_ready',dict(pid=server['pid'])),('server_terminal',server)]
            contexts[phase]=dict(model_provenance=model['provenance'],alias=model['alias'],owner_pid=server['pid'],endpoint=f'http://127.0.0.1:{frame["port"]}')
            if not failed:
                samples=inputs.json(pf['worker/SERVER-RESOURCE-SAMPLES.json']); need(isinstance(samples,list) and 0<len(samples)<=100000,'Original native samples')
                for sample in samples:
                    need(set(sample)=={'monotonic','value','error_class'},'Original sample schema');old.finite(sample['monotonic'],'Sample time');old._memory(sample['value'])
        else: need(server is None,'Original nonmodel phase server')
        worker_events.append(('build_failed',dict(error_class='ContractError',message='Unqualified native completion cause',stage='phase_execution')) if failed else ('refinement_worker_completed',dict(terminal_sha256=fingerprint(terminal))))
        need([(e['event'],e['details']) for e in we[1:]]==worker_events,'Original worker lifecycle journal')
        entered=stage['rows'][:stage['failed_ordinal']+1] if failed else stage['rows']
        audit=old._audit(wr,phase,frame,job,fp,jp,model,entered,inputs,pf['worker/io-audit.jsonl'])
        resources[phase]=dict(supervision=supervision,worker_wall_seconds=wall,stage_accounting=stage['report']['accounting'],io_audit=audit,
            server_terminal=server,worker_memory=None if failed else old._memory(terminal['worker_memory']))
        if phase=='pair_prepare': pairs=dict(descriptor=dict(root=stage['root'],receipt_sha256=sp['sha256']),products=[r['product'] for r in stage['rows']],cutoff=job['cutoff'])
    expected_events.append(('build_failed',dict(error_class='ValueError',message='Refinement worker failed; no automatic retry',stage='repair')))
    need([(e['event'],e['details']) for e in events[1:]]==expected_events,'Original root dispatch/failed journal')
    wall=old.finite(failure['wall_seconds'],'Failed original wall')
    need(sum(r['supervision']['execution_elapsed_seconds'] for r in resources.values())<=wall<=sum(v+60 for v in frame['phase_seconds'].values())+600,'Original aggregate process wall')
    return stages,resources,contexts,pairs,wall


def revalidate(value):
    state=_state(value);checked=verify_snapshot(state['closure'])
    need(fingerprint(old._adopt(encode(state['baseline_acceptance'])))==state['adopted_sha256'],'Accepted baseline changed')
    _archive(checked,encode(state['source_archive']),encode(state['frame']));checked.unchanged()
    return True


def _semantic_prefix(frame,baseline,stages,contexts,model,inputs,files):
    """Rebuild raw sources, both paired requests and every entered native call."""
    from .native_failure import verify_cell_limit_failure
    model_code=joins._code(frame,'experiments/litqa_refinement/model.py')
    catalog_code=joins._code(frame,'experiments/labbench/tether_adapter.py')
    selection_code=joins._code(frame,'experiments/litqa_refinement/selection.py')
    prepared=[];critics=[];source_cases=[];repair_records=[];failed_call=None
    measured={phase:dict.fromkeys(old.FIELDS,0) for phase in stages};physical=set()
    failed=stages['repair']['failed_ordinal']
    for index,case in enumerate(baseline['cases']):
        query,prior=case['query'],case['candidate']; key=query['id']
        native.candidate(query,prior,case['original_selected_sources'])
        rows={phase:stage['rows'][index] for phase,stage in stages.items()}
        need(all(row['ordinal']==index and row['id']==key and row['phase']==phase for phase,row in rows.items()),'Original cross-stage identities')
        for row in rows.values():
            need(row['execution_id'] not in physical,'Original physical ID repeated');physical.add(row['execution_id'])
        critic_row=rows['critic'];descriptor=dict(task='critic',query=query,prior=prior,sources=case['original_selected_sources'],model_provenance=frame['model_provenance'])
        cell=joins._cell(stages['critic'],critic_row,descriptor,contexts['critic'],model_code)
        critic=native.critique(query,prior,case['original_selected_sources'],cell['summary']['decoded'],cell['summary']['status'],cell['native_call_sha256'])
        critic_root=Path(stages['critic']['root'])/'products'/f'{index:04d}'
        need(joins._product(critic_row['product']['critic'],critic_root/'CRITIC.json')==critic and
             critic_row['product']['semantic_selection']==joins._selection(query,prior,critic),'Original independent critic/selection join')
        projected=source.query_projection(query,prior,critic,case['original_collection']['plan']['policy'])
        cr=rows['refinement_collect'];cp=cr['product']
        need(set(cp)=={'query_projection','collection'} and cp['query_projection']==projected,'Original critic-only acquisition plan')
        refinement=cp['collection']
        if projected['status']=='unavailable':
            need(cr['status']=='unavailable' and cr['reason']=='refinement_query_unavailable' and refinement is None,'Original unavailable collection')
        else:
            need(cr['status']=='completed' and cr['reason'] is None and refinement is not None and
                 Path(refinement['root'])==Path(stages['refinement_collect']['root'])/'products'/f'{index:04d}','Original exact collection slot')
        pair_row=rows['pair_prepare'];product=pair_row['product'];pair_root=Path(stages['pair_prepare']['root'])/'products'/f'{index:04d}'
        need(set(product)=={'query','prior','critic','context','repair','removal','control_sha256','refinement_collection','cutoff','model_provenance'},'Original pair product fields')
        need(joins._product(product['query'],pair_root/'QUERY.json')==query and joins._product(product['prior'],pair_root/'PRIOR.json')==prior and
             joins._product(product['critic'],pair_root/'CRITIC.json')==critic,'Original paired input identity')
        control=fingerprint(dict(query=query,candidate=prior,critique=critic))
        need(product['control_sha256']==control and product['refinement_collection']==refinement and product['model_provenance']==frame['model_provenance'] and
             product['cutoff']==stages['pair_prepare']['inputs']['cutoff'],'Original paired source/model/time freeze')
        context=joins._product(product['context'],pair_root/'CONTEXT.json')
        rebuilt=source.reconstruct_context(context,query,prior,critic,original_descriptor=case['original_collection'],
            refinement_descriptor=refinement,cutoff=product['cutoff'],catalog_proof=catalog_code,selection_proof=selection_code)
        members={task:native.prepare_member(task,query,prior,critic,rebuilt['sources'] if task=='repair' else [],frame['model_provenance'],model_code) for task in ('repair','removal')}
        need(all(joins._product(product[task],pair_root/(task.upper()+'.json'))==members[task] for task in members),'Both original paired requests independently reconstructed')
        zero=dict.fromkeys(old.FIELDS,0)|dict(provider_cost_usd=0)
        need(pair_row['status']=='completed' and pair_row['reason'] is None and pair_row['accounting']==zero,'Original pure pair preparation')
        collect_usage=dict(zero)
        if rebuilt['wrapper'] is not None:
            wrapper=rebuilt['wrapper']['manifest'];collect_usage.update(source_http_requests=wrapper['request_count'],
                measured_response_bytes=wrapper['accounting']['measured_response_bytes'],safety_accounted_bytes=wrapper['accounting']['safety_accounted_bytes'])
        need(cr['accounting']==collect_usage,'Original HTTP body/accounting join')
        row=rows['repair'];raw=rebuilt['sources'];descriptor=dict(task='repair',query=query,prior=prior,critic=critic,sources=raw,
            model_provenance=frame['model_provenance'],prepared_member=members['repair'],control_sha256=control)
        if index<failed:
            final=joins._cell(stages['repair'],row,descriptor,contexts['repair'],model_code)
            decision=source.disposition(query,final,context);cellroot=Path(stages['repair']['root'])/'products'/f'{index:04d}'
            need(row['product']['disposition']==decision['disposition'] and joins._product(row['product']['decision'],cellroot/'DECISION.json')==decision['decision'] and
                 row['product']['paired_member_sha256']==fingerprint(members['repair']) and row['product']['control_sha256']==control and
                 row['product']['source_context_sha256']==fingerprint(context),'Original accepted repair native/admission join')
            repair_records.append(decision['disposition'])
        elif index==failed:
            member=members['repair'];need(member['status']=='ready','Failed native call must have a ready request')
            cellroot=Path(stages['repair']['root'])/'products'/f'{index:04d}';prefix=f'repair/worker/phase/products/{index:04d}/'
            cellfiles={name[len(prefix):]:p for name,p in files.items() if name.startswith(prefix)}
            expected_inputs=dict(task='repair',query=query,candidate_context=prior,sources=raw,model_provenance=frame['model_provenance'],
                critique_context=critic,prepared_member=member,control_sha256=control)
            failed_call=encode(verify_cell_limit_failure(cellroot,files=cellfiles,expected_inputs=expected_inputs,
                expected_request=member['request'],expected_payload=member['payload'],execution_id=row['execution_id'],
                owner_pid=contexts['repair']['owner_pid'],alias=model['alias'],server_spec=model['spec'],bindings=model['bindings']))
            need(failed_call['producer_status']=='error' and failed_call['check_status']=='not_run' and failed_call['prediction'] is None and
                 failed_call['original_usage_verified'] is False and failed_call['qualified_usage'] is None,'Failed original cannot become an answer or qualified usage')
            repair_records.append(dict(id=key,producer_status='error',check_status='not_run',prediction=None,reason='native_completion_limit'))
        else: repair_records.append(None)
        prepared.append(dict(query=query,prior=prior,critic=critic,context=context,members=members,sources=raw,control_sha256=control))
        critics.append(dict(id=key,native_status=critic['native_status'],decoded=None if critic['decoded'] is None else dict(support=critic['decoded']['support'])))
        source_cases.append(dict(id=key,retained_dois=rebuilt['retained_dois'],pool_dois=rebuilt['pool_dois'],selected_dois=rebuilt['selected_dois'],
            original_selected_sources=case['original_selected_sources'],original_retained_dois=rebuilt['original_retained_dois'],original_pool_dois=rebuilt['original_pool_dois'],
            original_selected_dois=rebuilt['original_selected_dois'],selected_sources=rebuilt['sources'],source_context_changed=rebuilt['source_context_changed'],
            source_coverage=context['coverage'],source_proofs=context['source_proofs'],publication_cutoff=context['publication_cutoff'],acquisition_cutoff=context['cutoff'],
            temporal=context['temporal'],merged_exclusions=context['merge']['exclusions'],refinement_available=refinement is not None))
        for phase,row in rows.items():
            if row['accounting'] is not None:
                for metric in old.FIELDS:measured[phase][metric]+=row['accounting'][metric]
    for phase in stages:need(measured[phase]==stages[phase]['report']['accounting']['known_totals'],'Original verified known-total arithmetic')
    return dict(failed_ordinal=failed,failed_call=failed_call,prepared=prepared,critics=critics,source_cases=source_cases,
        repair_records=repair_records,measured=measured,physical_ids=sorted(physical),model_code=model_code)


def reconstruct(inspection_proof, source_archive_proof, *, baseline_acceptance):
    inputs=accepted_primary._Inputs(); inspected,roots=_inspection(inputs,encode(inspection_proof))
    (root,files),(frozen,freeze_files)=roots; fp=files['FRAME.json'];frame=inputs.json(fp)
    need(fp==inspected['original_frame'] and files['FAILURE.json']==inspected['original_failure'] and
         files['FRAME.json']['sha256']==freeze_files['FRAME.json']['sha256'],'Original inspection frame/failure bindings')
    _archive(inputs,encode(source_archive_proof),frame);model=old._frame(frame,root,inputs)
    adopted=old._adopt(encode(baseline_acceptance));baseline,grants=old._baseline(frame['baseline'],frame,adopted,inputs)
    events=old._events(inputs,files['journal.jsonl']);reservation=old._reserved(events[0])
    stages,resources,contexts,pairs,wall=_phases(root,files,frame,fp,model,grants,inputs,reservation)
    launch={name[len('launch/'):]:p for name,p in freeze_files.items() if name.startswith('launch/')}
    process=inputs.json(launch['PROCESS.json']);_terminated(process,frozen/'launch',launch,inputs,dict(timeout_seconds=43200,max_output_bytes=4*1024**2),1)
    need(process['supervision']['execution_elapsed_seconds']>=wall,'Outer process must contain original controller')
    repair=stages['repair'];failed=repair['failed_ordinal'];n=len(frame['schedule'])
    # Scientific/native source joins are filled before capability issuance below.
    semantic=_semantic_prefix(frame,baseline,stages,contexts,model,inputs,files)
    need(semantic['failed_ordinal']==failed,'Authenticated failed call boundary differs')
    payload=dict(kind='sc05_verified_failed_parent_v2',purpose=frame['purpose'],original_root=str(root),freeze_root=str(frozen),
        original_producer_descriptor=dict(inspection=encode(inspection_proof),source_archive=encode(source_archive_proof),original_frame=fp,original_failure=files['FAILURE.json']),
        frame=frame,frame_proof=fp,schedule=frame['schedule'],completed_phases=inputs.json(files['FAILURE.json'])['completed_phases'],
        repair_rows=[dict(ordinal=r['ordinal'],id=r['id'],execution_id=r['execution_id'],status=r['status'],accounting=r['accounting'],
            row_proof=None if r['status']=='unexecuted' else files[f'repair/worker/phase/{"failures" if r["status"]=="failed" else "slots"}/{r["ordinal"]:04d}.json']) for r in repair['rows']],
        failed_ordinal=failed,failed_call=semantic['failed_call'],untouched_repair_ordinals=list(range(failed+1,n)),untouched_removal_ordinals=list(range(n)),
        pair_prepare=pairs,elapsed=dict(outer_process_total_seconds=process['supervision']['total_elapsed_seconds'],
            repair_process_total_seconds=resources['repair']['supervision']['total_elapsed_seconds'],repair_worker_wall_seconds=resources['repair']['worker_wall_seconds'],
            repair_stage_seal_elapsed_seconds=repair['seal_elapsed_seconds'],original_controller_wall_seconds=wall),
        budgets=dict(outer_seconds=43200,phase_seconds=frame['phase_seconds'],repair_stage_seconds=repair['config']['seconds'],cell_limits=old._limits('repair')),
        source_archive=encode(source_archive_proof),source_pins=frame['code_files'],model_proofs=dict(receipt=frame['model_receipt'],license=frame['model_license'],interpreter=frame['interpreter']),
        original_started_at_utc=reservation['created_at_utc'],baseline_acceptance=encode(baseline_acceptance),
        resources=dict(phases=resources,original_resources=adopted['report']['resources'],baseline_resources=[dict(id=r['id'],logical_model_usage=r['logical_model_usage'],logical_http_usage=r['logical_http_usage']) for r in adopted['report']['source_cases']['L/O']]),
        archived_code_executed=False,reference_keys_read=False,scoring_performed=False,automatic_retry=False)
    inputs.unchanged();frozen_payload=freeze(payload)
    data=freeze(dict(closure=snapshot(inputs),frame=frame,source_archive=encode(source_archive_proof),baseline_acceptance=encode(baseline_acceptance),
        adopted_sha256=fingerprint(adopted),baseline=baseline,stages=stages,contexts=contexts,model=model,semantic=semantic))
    result=VerifiedParent(frozen_payload,fingerprint(frozen_payload),_TOKEN,fingerprint(data))
    _ISSUED[id(result)]=result
    _STATES[id(result)]=data
    _SEALS[id(result)]=(result._fingerprint,result._state_fingerprint)
    import weakref
    weakref.finalize(result,_STATES.pop,id(result),None)
    weakref.finalize(result,_SEALS.pop,id(result),None)
    return result
