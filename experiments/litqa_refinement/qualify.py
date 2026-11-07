"""Invented native controls for the fixed SC05 critic and paired prompts.

No benchmark question or answer is read. A successful control run still needs
independent native reconstruction and the full controller rehearsal before it
can authorize the 199-case experiment. Failed calls are never repeated here.
"""
import argparse
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
if __name__=='__main__':sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'packages/tether/src')]

from tether_engine.journal import RunJournal
from tether_engine.serde import canonical,encode,freeze,fingerprint,parse_json
from experiments.labbench.runtime import contain_process_tree,DeadlineWatchdog,ProcessSamples,process_sample
from experiments.labbench import model as native_model
from experiments.litqa_refinement import contracts,model,pipeline,run,projection
from experiments.litqa_refinement.access import RoleAudit


def controls(provenance):
    items=[]
    scenarios=(('critic-supported','critic',0,True,True,'supported'),
        ('critic-contradicted','critic',1,True,True,'contradicted'),
        ('critic-absent-source','critic',0,False,True,'insufficient'),
        ('critic-absent-candidate','critic',0,True,False,'not_assessable'),
        ('repair-preserve','repair',0,True,True,0),
        ('repair-correct','repair',1,True,True,0),
        ('repair-absent-source','repair',1,False,True,2),
        ('removal','removal',0,True,True,2))
    for ordinal,(ident,task,index,has_source,has_candidate,expected) in enumerate(scenarios,1):
        query=dict(id=f'10000000-0000-0000-0000-{ordinal:012d}',question='What color is fictional Lumarin?',
            choices=['(A) Cobalt','(B) Amber','(C) Insufficient information to answer the question'])
        text='In this invented test world, Lumarin is cobalt. It is not amber.'
        sources=[dict(source_id='invented:p0001',text=text,sha256=contracts.codecs.digest(text.encode()))] if has_source else []
        prior=contracts.candidate(query,dict(answer_index=index,evidence_ids=[sources[0]['source_id']] if sources else []) if has_candidate else None,
            producer_status='produced' if has_candidate else 'input_unavailable',
            original_admission_status=('accepted' if sources else 'rejected') if has_candidate else 'not_run',
            native_call_sha256='1'*64 if has_candidate else None,generated_at_utc=None,offered_ids=[s['source_id'] for s in sources])
        descriptor=dict(task=task,query=query,prior=prior,sources=sources,model_provenance=provenance,execution_id='sc05-control-'+ident)
        if task!='critic':
            support=('supported' if index==0 else 'contradicted') if sources else 'insufficient'
            decoded=dict(support=support,evidence_ids=[sources[0]['source_id']] if sources else [],
                criticism='The supplied passage determines the color.' if sources else 'No raw evidence is available.',queries=[['Lumarin'],['color']])
            critic=contracts.critique(query,prior,sources,decoded,native_status='completed',native_call_sha256='2'*64)
            pair=model.make_repair_pair(query,prior,critic,sources,provenance)
            descriptor.update(critic=critic,prepared_member=pair[task],control_sha256=pair['control_sha256'])
            if task=='removal':descriptor['sources']=[]
        items.append(dict(id=ident,descriptor=descriptor,expected=dict(support=expected) if task=='critic' else dict(answer_index=expected)))
    return freeze(items)


def execute(frame_path,expected,output):
    frame_path=projection._path(str(frame_path))
    source=run.proof(frame_path);contracts.need(source['sha256']==expected,'Native control frame anchor')
    frame=run.capture(source);root=projection._path(str(output))
    contracts.need(frame['kind']=='sc05_refinement_native_controls_v1' and frame['purpose']=='fictional_qualification'
        and Path(frame['output'])==root and root.is_relative_to(ROOT/'data/cache') and not root.exists(),'Fresh qualification scope')
    contracts.need(canonical(frame['code_files'])==canonical(run.code_files()) and canonical(frame['qualifier'])==canonical(run.proof(__file__)),
        'Current qualification/producer sources required')
    contracts.need(canonical(frame['interpreter'])==canonical(run.proof(sys.executable)) and frame['model_receipt']['sha256']==run.MODEL_RECEIPT,
        'Qualified interpreter/model required')
    contracts.need(type(frame['seconds']) is int and 600<=frame['seconds']<=3600,'Control deadline cap')
    journal=RunJournal(root,kind='build');start=time.monotonic();end=start+frame['seconds'];owner=None;audit=None;watchdog=None;handle=None
    try:
        run.write(root/'FRAME.json',frame)
        handle=contain_process_tree();watchdog=DeadlineWatchdog(end,root/'DEADLINE.json');watchdog.__enter__()
        spec,bindings,provenance=native_model.make_server_spec(frame['model_receipt']['path'],frame['model_receipt']['sha256'],
            port=frame['port'],alias=frame['alias'],startup_seconds=180)
        contracts.need(canonical(provenance)==canonical(frame['model_provenance']) and canonical(spec)==canonical(frame['model_spec']),'Control model identity')
        contracts.need(canonical(run.proof(frame['model_license']['path']))==canonical(frame['model_license']),'Control license pin')
        items=controls(provenance);run.write(root/'CONTROLS.json',items)
        run.write(root/'MODEL.json',dict(spec=spec,bindings={k:str(v) for k,v in bindings.items()},provenance=provenance,alias=frame['alias']))
        audit=RoleAudit(inputs=[frame_path],code_files=[p['path'] for p in frame['code_files']]+[str(Path(__file__).resolve())],
            runtime_roots=(sys.prefix,sys.base_prefix),model_files=bindings.values(),output=root);audit.activate()
        (root/'server').mkdir();rows=[]
        with native_model.owned_server(spec,bindings,output=root/'server',journal=journal,parent_deadline=end-40) as owner:
            caller=pipeline.NativeCaller(owner,frame['alias'],audit)
            with ProcessSamples(owner.terminal_record['pid']) as samples:
                for index,item in enumerate(items):
                    descriptor=item['descriptor'];cell=root/'cells'/f'{index:04d}'
                    journal.append('native_control_reserved',id=item['id'],execution_id=descriptor['execution_id'],input_sha256=fingerprint(descriptor))
                    result=caller(descriptor,cell,min(end-90,time.monotonic()+120))
                    checked,usage,native=pipeline._model_result(result,descriptor,cell,end-90)
                    summary=checked['summary'];decoded=summary['decoded']
                    passed=summary['status']=='completed' and all(decoded[k]==v for k,v in item['expected'].items())
                    row=dict(id=item['id'],status=summary['status'],control_passed=passed,expected=item['expected'],decoded=decoded,
                        cell=str(cell),summary=checked['summary_proof'],native=native,accounting=usage)
                    run.write(root/'results'/f'{index:04d}.json',row);rows.append(row)
                    journal.append('native_control_completed',id=item['id'],control_passed=passed)
            run.write(root/'SERVER-RESOURCE-SAMPLES.json',samples.values)
        contracts.need(owner.terminal_record['server_stopped'] is True and audit.denials==0,'Control cleanup/access failure')
        contracts.need(canonical(frame['code_files'])==canonical(run.code_files()),'Control code changed during native execution')
        contracts.need(canonical(frame['qualifier'])==canonical(run.proof(__file__))
            and canonical(frame)==canonical(run.capture(source)),'Qualifier/frame changed during native execution')
        contracts.need(time.monotonic()<end,'Native controls exceeded their fixed time cap')
        result=dict(kind='sc05_refinement_native_controls_result_v1',status='controls_passed' if all(r['control_passed'] for r in rows) else 'controls_failed',
            rows=rows,scheduled=len(items),completed=len(rows),native_tasks=['critic','repair','removal'],
            server_terminal=owner.terminal_record,audit_denials=audit.denials,wall_seconds=time.monotonic()-start,
            worker_memory=process_sample(os.getpid()),provider_cost_usd=0,automatic_retry=False,
            independent_reconstruction_required=True,benchmark_questions_read=0)
        run.write(root/'RESULT.json',result);journal.append('native_controls_completed',status=result['status']);audit.flush();journal.close()
        # The outer supervisor seals the inventory only after this process has
        # exited. Hashing the live I/O log here would append audit entries while
        # reading that same log and produce a self-invalidating receipt.
        return freeze(result)
    except BaseException as error:
        journal.fail(error,'native_controls');run.write(root/'FAILURE.json',dict(error_type=type(error).__name__,message=str(error),automatic_retry=False))
        raise
    finally:
        if audit is not None:audit.flush()
        journal.close()
        if watchdog is not None:watchdog.__exit__(None,None,None)
        _=handle


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--frame',type=Path,required=True)
    parser.add_argument('--frame-sha256',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=execute(args.frame,args.frame_sha256,args.output);print(result['status']);raise SystemExit(result['status']!='controls_passed')
