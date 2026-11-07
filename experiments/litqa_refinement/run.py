"""Owned-process SC05 phase controller; references and scoring stay separate.

Every phase is a new bounded process. A failed/uncertain attempt is retained and
never resumed by this command. Coordinator source verification and model actor
file grants are different roles, explicitly recorded before task inputs open.
"""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import os
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
if __name__=='__main__':sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'packages/tether/src')]

from tether._process import ProcessLimits,supervise_command,validate_success_report
from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal
from tether_engine.serde import canonical,encode,freeze,parse_json
from experiments.labbench import model as native_model
from experiments.labbench.runtime import contain_process_tree,DeadlineWatchdog,ProcessSamples,process_sample
from experiments.litqa_comparison.pipeline import proof
from experiments.litqa_comparison.run import inventory
from . import contracts,model,pipeline,projection,schedule,phase_checks
from .access import RoleAudit

KIND='sc05_refinement_execution_v1'
MODEL_RECEIPT='cc95c56ce1f497b36d6b9ed62b22721d8af7eaccc0a8c50da91439c5b076acbf'


def write(path,value):publish_bytes(Path(path),canonical(value)+b'\n')


def code_files():
    files=[]
    for name in ('src/tether_engine','packages/tether/src/tether','experiments/labbench',
                 'experiments/litqa_comparison','experiments/litqa_refinement'):
        for path in (ROOT/name).rglob('*'):
            if not path.is_file() or path.suffix not in ('.py','.json') or 'tests' in path.parts or path.name.startswith('test_'):continue
            if name.endswith('litqa_refinement') and path.name not in {
                '__init__.py','access.py','admission.py','cells.py','collection.py','contracts.py','model.py',
                'pipeline.py','projection.py','run.py','schedule.py','selection.py','transport.py','phase_checks.py'}:continue
            files.append(proof(path))
    return sorted(files,key=lambda p:p['path'])


def capture(value,maximum=16*1024**2):
    contracts.need(type(value['bytes']) is int and 0<=value['bytes']<=maximum,'Metadata byte bound')
    return pipeline.read(value,deadline=time.monotonic()+120)


def supervised(command,limits,output):
    def retain(result):
        publish_bytes(Path(output)/'stdout.bin',result.stdout)
        publish_bytes(Path(output)/'stderr.bin',result.stderr)
        write(Path(output)/'PROCESS.json',dict(returncode=result.returncode,supervision=result.supervision))
    try:result=supervise_command(command,limits=limits)
    except BaseException as error:
        partial=getattr(error,'tether_engine_result',None) or getattr(error,'result',None)
        if partial is not None:
            try:retain(partial)
            except BaseException as secondary:error.add_note('Process capture retention: '+type(secondary).__name__)
        raise
    retain(result)
    return result


def load_frame(path,expected,output):
    path=projection._path(str(Path(path).absolute()));spec=proof(path)
    contracts.need(spec['sha256']==expected and spec['bytes']<=4*1024**2,'External execution frame anchor')
    frame=capture(spec)
    fields={'schema_version','kind','purpose','schedule','baseline','interpreter','code_files','phase_seconds',
        'port','alias','model_receipt','model_license','model_spec','model_provenance','generation_configuration',
        'qualification','provider_spend_usd','automatic_retry','output'}
    contracts.need(set(frame)==fields and frame['schema_version']==1 and frame['kind']==KIND,'Execution frame fields')
    contracts.need(frame['purpose'] in ('production','fictional_qualification'),'Execution purpose')
    schedule.slots(frame['schedule'],'critic',purpose=frame['purpose'],execution_namespace='00000000-0000-0000-0000-000000000001')
    contracts.need(canonical(frame['code_files'])==canonical(code_files()),'Frozen execution code changed')
    contracts.need(canonical(frame['interpreter'])==canonical(proof(sys.executable)),'Interpreter identity differs')
    contracts.need(canonical(frame['generation_configuration'])==canonical(model.CONFIG),'Frozen generation settings differ')
    contracts.need(frame['provider_spend_usd']==0 and frame['automatic_retry'] is False,'Execution spend/retry policy')
    contracts.need(set(frame['phase_seconds'])==set(schedule.PHASES) and all(type(s) is int and 120<=s<=43200
        for s in frame['phase_seconds'].values()),'Explicit bounded phase budgets')
    contracts.need(type(frame['port']) is int and 49152<=frame['port']<=65535 and frame['alias']=='tether-sc05-refinement-qwen14b-v1','Native endpoint identity')
    contracts.need(frame['model_receipt']['sha256']==MODEL_RECEIPT,'Qualified public model required')
    root=projection._path(str(Path(output).absolute()))
    contracts.need(root==projection._path(frame['output']) and root.is_relative_to(ROOT/'data') and root!=ROOT/'data','Fresh data output root')
    contracts.need(not root.exists(),'Output already exists; inspect, never redispatch')
    for source in (spec,frame['interpreter'],frame['model_receipt'],frame['model_license'],*frame['code_files']):
        contracts.need(not projection._path(source['path']).is_relative_to(root),'Input/output overlap')
    if frame['purpose']=='production':
        qualification=capture(frame['qualification'])
        contracts.need(qualification['kind']=='sc05_refinement_native_qualification_v1' and qualification['status']=='passed'
            and canonical(qualification['code_files'])==canonical(frame['code_files'])
            and canonical(qualification['model_provenance'])==canonical(frame['model_provenance'])
            and qualification['native_tasks']==['critic','repair','removal'] and qualification['automatic_retry'] is False,
            'Current full native qualification required before production')
    else:contracts.need(frame['qualification'] is None,'Fictional qualification cannot inherit production claims')
    return frame,spec,root


def _grants(baseline,parents):
    """Exact coordinator ancestry, with no evaluator or sibling-final outputs."""
    root=Path(baseline.root);receipt=parse_json((root/'RECEIPT.json').read_bytes())
    paths={str(root/'RECEIPT.json'):proof(root/'RECEIPT.json')}
    for name in receipt['files']:
        p=projection._path(str(root/name));paths[str(p)]=proof(p)
    for entry in baseline.manifest['role_files']:
        contracts.need(set(entry)=={'proof','role'} and entry['role']!='coordinator_activation_only','Projected source role fields')
        item=encode(entry['proof']);projection._proof(item)
        previous=paths.get(item['path'])
        contracts.need(previous is None or canonical(previous)==canonical(item),'Conflicting baseline source proof')
        paths[item['path']]=item
    for descriptor in parents.values():
        package=verify_package(descriptor['root'],descriptor['package_sha256'])
        package_root=Path(descriptor['root'])
        for name,item in package['files'].items():
            paths[item['path']]=item
        paths[str(package_root/'PACKAGE-RECEIPT.json')]=proof(package_root/'PACKAGE-RECEIPT.json')
        job=parse_json((package_root/'JOB.json').read_bytes())
        for item in job['input_files']:
            old=paths.get(item['path']);contracts.need(old is None or canonical(old)==canonical(item),'Conflicting ancestor proof')
            paths[item['path']]=item
    return [paths[k] for k in sorted(paths)]


def verify_package(root,expected):
    root=projection._path(str(root));receipt_path=root/'PACKAGE-RECEIPT.json'
    contracts.need(proof(receipt_path)['sha256']==expected,'External phase receipt anchor')
    receipt=parse_json(receipt_path.read_bytes())
    contracts.need(receipt['kind']=='sc05_refinement_phase_receipt_v1' and receipt['status']=='complete','Incomplete phase package')
    contracts.need(canonical(receipt['files'])==canonical(inventory(root,omit=('PACKAGE-RECEIPT.json',))),'Phase exact byte inventory')
    terminal=parse_json((root/'worker/COMPLETE.json').read_bytes())
    contracts.need(terminal['phase']==receipt['phase'] and terminal['frame_sha256']==receipt['frame_sha256']
        and terminal['status']=='complete' and terminal['audit_denials']==0,'Phase terminal identity')
    contracts.need(terminal['provider_cost_usd']==0 and terminal['reference_keys_read'] is False
        and terminal['scientific_scoring_performed'] is False,'Phase data/spending policy')
    if receipt['phase'] in ('critic','repair','removal'):
        contracts.need(terminal['server_terminal']['server_stopped'] is True,'Native cleanup not verified')
    else:contracts.need(terminal['server_terminal'] is None,'Nonmodel phase cannot hide native execution')
    contracts.need(not any((root/'worker'/n).exists() for n in ('FAILURE.json','DEADLINE.json')),'Worker terminal failure marker')
    stage=terminal['stage_receipt']
    contracts.need(projection._path(stage['path'])==root/'worker/phase/STAGE-RECEIPT.json'
        and canonical(proof(stage['path']))==canonical(stage),'Stage output identity')
    verified=schedule.verify(root/'worker/phase',stage['sha256'],expected_phase=receipt['phase'],purpose=terminal['purpose'],deadline=time.monotonic()+300)
    contracts.need(verified['report']['status']=='complete','Incomplete child schedule')
    phase_checks.verify_phase(root,receipt,verified,deadline=time.monotonic()+300)
    return receipt


def verify_final_packages(files,expected):
    """Match the final tree to the exact child bytes accepted at phase closure."""
    for phase,original in expected.items():
        current={name[len(phase)+1:]:item for name,item in files.items() if name.startswith(phase+'/')}
        contracts.need(canonical(current)==canonical(original),'Accepted phase changed before final sealing: '+phase)


def worker_preflight(frame_path,frame_sha,job_path,job_sha,output):
    # Authentication and path authority precede any output reservation/write.
    frame=capture(dict(path=str(frame_path),bytes=Path(frame_path).stat().st_size,sha256=frame_sha))
    job=capture(dict(path=str(job_path),bytes=Path(job_path).stat().st_size,sha256=job_sha))
    contracts.need(frame['kind']==KIND and job['frame_sha256']==frame_sha and job['phase'] in schedule.PHASES,'Worker phase/frame')
    destination=projection._path(frame['output']);phase=job['phase']
    contracts.need(destination.is_relative_to(ROOT/'data') and destination!=ROOT/'data','Worker workspace destination')
    contracts.need(projection._path(str(frame_path))==destination/'FRAME.json'
        and projection._path(str(job_path))==destination/phase/'JOB.json'
        and projection._path(str(output))==destination/phase/'worker','Worker exact reserved paths')
    contracts.need(not Path(output).exists(),'Worker output already reserved; no retry')
    contracts.need(set(job)=={'phase','frame_sha256','parents','input_files','model_bindings','cutoff'}
        and set(job['parents'])==set(schedule.PARENTS[phase]),'Worker job fields/parent roles')
    for name,value in job['parents'].items():
        contracts.need(projection._path(value['root'])==destination/name,'Parent must be this run and required phase')
    schedule.slots(frame['schedule'],phase,purpose=frame['purpose'],execution_namespace='00000000-0000-0000-0000-000000000001')
    contracts.need(type(frame['phase_seconds'][phase]) is int and 120<=frame['phase_seconds'][phase]<=43200,'Worker phase time cap')
    contracts.need(canonical(frame['code_files'])==canonical(code_files()) and canonical(proof(sys.executable))==canonical(frame['interpreter']),'Worker current code/interpreter')
    return frame,job


def worker(frame_path,frame_sha,job_path,job_sha,output):
    started=time.monotonic()
    frame,job=worker_preflight(frame_path,frame_sha,job_path,job_sha,output)
    journal=RunJournal(output,kind='build');root=journal.output
    owner=None;audit=None;watchdog=None;handle=None;stage='metadata'
    try:
        phase=job['phase'];end=started+frame['phase_seconds'][phase]
        handle=contain_process_tree();watchdog=DeadlineWatchdog(end,root/'DEADLINE.json');watchdog.__enter__()
        write(root/'CONFIG.json',dict(frame_sha256=frame_sha,job_sha256=job_sha,phase=phase,purpose=frame['purpose'],
            worker_pid=os.getpid(),python_version=sys.version,coordinator_grants=job['input_files']))
        inputs=[frame_path,job_path,frame['model_receipt']['path'],frame['model_license']['path']]
        inputs.extend(p['path'] for p in job['input_files'])
        model_paths=list(job['model_bindings'].values())
        audit=RoleAudit(inputs=inputs,code_files=[p['path'] for p in frame['code_files']],runtime_roots=(sys.base_prefix,sys.prefix),
            model_files=model_paths,output=root);audit.activate()
        stage='input_verification'
        # Hash all exact grants before loading the projected task container.
        for item in job['input_files']:
            contracts.need(canonical(proof(item['path']))==canonical(item),'Coordinator grant changed')
        baseline_root=Path(frame['baseline']['root'])
        baseline=projection.PreparedBaseline(str(baseline_root),frame['baseline']['receipt_sha256'],
            freeze(parse_json((baseline_root/'BASELINE.json').read_bytes())))
        contracts.need(tuple(baseline.manifest['schedule'])==tuple(frame['schedule']),'Worker full schedule')
        parents={name:dict(root=str(Path(d['root'])/'worker/phase'),receipt_sha256=d['stage_receipt_sha256'])
            for name,d in job['parents'].items()}
        spec,bindings,provenance=native_model.make_server_spec(frame['model_receipt']['path'],frame['model_receipt']['sha256'],
            port=frame['port'],alias=frame['alias'],startup_seconds=180)
        contracts.need(canonical(spec)==canonical(frame['model_spec']) and canonical(provenance)==canonical(frame['model_provenance'])
            and {k:str(v) for k,v in bindings.items()}==dict(job['model_bindings']),'Native model identity')
        contracts.need(canonical(proof(frame['model_license']['path']))==canonical(frame['model_license']),'Model terms changed')
        write(root/'MODEL.json',dict(spec=encode(spec),bindings={k:str(v) for k,v in bindings.items()},provenance=provenance,alias=frame['alias']))
        stage='phase_execution'
        kwargs=dict(purpose=frame['purpose'],seconds=max(.001,end-time.monotonic()-90),parents=parents,
            cutoff=job['cutoff'],model_provenance=provenance)
        if phase in ('critic','repair','removal'):
            (root/'server').mkdir()
            with native_model.owned_server(spec,bindings,output=root/'server',journal=journal,parent_deadline=end-40) as owner:
                caller=pipeline.NativeCaller(owner,frame['alias'],audit)
                with ProcessSamples(owner.terminal_record['pid']) as samples:
                    report=pipeline.execute(phase,baseline,root/'phase',call_model=caller,**kwargs)
                write(root/'SERVER-RESOURCE-SAMPLES.json',samples.values)
            contracts.need(owner.terminal_record['server_stopped'] is True,'Owned native cleanup not established')
        else:report=pipeline.execute(phase,baseline,root/'phase',**kwargs)
        stage='finalization';audit.flush()
        contracts.need(report['status']=='complete' and audit.denials==0 and time.monotonic()<end,'Phase incomplete/overtime/denied')
        contracts.need(canonical(frame['code_files'])==canonical(code_files()),'Code changed during phase')
        terminal=dict(status='complete',phase=phase,purpose=frame['purpose'],frame_sha256=frame_sha,
            stage_receipt=proof(root/'phase/STAGE-RECEIPT.json'),wall_seconds=time.monotonic()-started,
            worker_memory=process_sample(os.getpid()),server_terminal=owner.terminal_record if owner else None,
            audit_denials=audit.denials,provider_cost_usd=0,reference_keys_read=False,scientific_scoring_performed=False)
        write(root/'COMPLETE.json',terminal);journal.append('refinement_worker_completed',terminal_sha256=contracts.codecs.digest(canonical(terminal)))
        return terminal
    except BaseException as error:
        journal.fail(error,stage)
        write(root/'FAILURE.json',dict(stage=stage,error_type=type(error).__name__,message=str(error),automatic_retry=False,
            server_terminal=owner.terminal_record if owner else None,wall_seconds=time.monotonic()-started))
        raise
    finally:
        if audit is not None:audit.flush()
        journal.close()
        if watchdog is not None:watchdog.__exit__(None,None,None)
        _=handle


def execute(frame_path,expected,*,output):
    frame,frame_proof,root=load_frame(frame_path,expected,output)
    started=time.monotonic();journal=RunJournal(root,kind='build');parents={};accepted={};stage='baseline'
    try:
        raw=Path(frame_path).read_bytes()
        contracts.need(contracts.codecs.digest(raw)==expected,'Execution frame changed before retention')
        publish_bytes(root/'FRAME.json',raw)
        baseline=projection.verify_baseline_projection(frame['baseline'],frame['schedule'])
        contracts.need(baseline.manifest['purpose']==frame['purpose'],'Baseline purpose differs')
        spec,bindings,provenance=native_model.make_server_spec(frame['model_receipt']['path'],frame['model_receipt']['sha256'],
            port=frame['port'],alias=frame['alias'],startup_seconds=180)
        contracts.need(canonical(spec)==canonical(frame['model_spec']) and canonical(provenance)==canonical(frame['model_provenance']),'Frozen native model differs')
        for phase in schedule.PHASES:
            stage=phase;phase_root=root/phase;phase_root.mkdir()
            required={key:parents[key] for key in schedule.PARENTS[phase]}
            job=dict(phase=phase,frame_sha256=expected,parents=required,input_files=_grants(baseline,required),
                model_bindings={k:str(v) for k,v in bindings.items()},
                cutoff=datetime.now(timezone.utc).isoformat() if phase=='pair_prepare' else None)
            write(phase_root/'JOB.json',job);job_proof=proof(phase_root/'JOB.json')
            # -I discards cwd from sys.path. The tiny pinned launcher below adds
            # only this repository; imports never execute archived project code.
            command=[str(sys.executable),'-I','-B','-c',
                'import runpy,sys;sys.path[:0]=sys.argv[1:4];sys.argv=["tether-sc05-worker"]+sys.argv[4:];runpy.run_module("experiments.litqa_refinement.run",run_name="__main__")',
                str(ROOT),str(ROOT/'src'),str(ROOT/'packages/tether/src'),'--worker','--frame',str(root/'FRAME.json'),
                '--frame-sha256',expected,'--job',job_proof['path'],'--job-sha256',job_proof['sha256'],'--output',str(phase_root/'worker')]
            limits=ProcessLimits(frame['phase_seconds'][phase]+60,4*1024**2)
            write(phase_root/'COMMAND.json',command)
            journal.append('refinement_phase_reserved',phase=phase,job=job_proof,command=command,limits=limits.payload())
            result=supervised(command,limits,phase_root)
            contracts.need(result.returncode==0,'Refinement worker failed; no automatic retry')
            validate_success_report(result.supervision,limits,len(result.stdout),len(result.stderr))
            terminal=parse_json((phase_root/'worker/COMPLETE.json').read_bytes())
            contracts.need(terminal['status']=='complete' and terminal['phase']==phase and terminal['frame_sha256']==expected,'Worker terminal identity')
            contracts.need(canonical(code_files())==canonical(frame['code_files']),'Execution code changed')
            receipt=dict(kind='sc05_refinement_phase_receipt_v1',status='complete',phase=phase,frame_sha256=expected,
                files=inventory(phase_root,omit=('PACKAGE-RECEIPT.json',)))
            write(phase_root/'PACKAGE-RECEIPT.json',receipt)
            digest=proof(phase_root/'PACKAGE-RECEIPT.json')['sha256'];verified=verify_package(phase_root,digest)
            accepted[phase]=freeze(dict(verified['files'],**{'PACKAGE-RECEIPT.json':proof(phase_root/'PACKAGE-RECEIPT.json')}))
            parents[phase]=dict(root=str(phase_root),package_sha256=digest,stage_receipt_sha256=terminal['stage_receipt']['sha256'])
            write(root/(phase+'-ANCHOR.json'),parents[phase]);journal.append('refinement_phase_completed',phase=phase,anchor=parents[phase])
        write(root/'COMPLETE.json',dict(status='refinement_execution_complete',purpose=frame['purpose'],phases=parents,
            scheduled=len(frame['schedule']),wall_seconds=time.monotonic()-started,provider_cost_usd=0,
            scientific_scoring_performed=False,automatic_retry=False))
        journal.append('refinement_execution_completed',phases=list(parents));journal.close()
        final_files=inventory(root,omit=('ROOT-RECEIPT.json',),seconds=600)
        verify_final_packages(final_files,accepted)
        receipt=dict(kind='sc05_refinement_root_receipt_v1',status='refinement_execution_complete',frame_sha256=expected,files=final_files)
        write(root/'ROOT-RECEIPT.json',receipt)
        return freeze(dict(root=str(root),receipt_sha256=proof(root/'ROOT-RECEIPT.json')['sha256']))
    except BaseException as error:
        if not journal._stream.closed:journal.fail(error,stage)
        write(root/'FAILURE.json',dict(stage=stage,error_type=type(error).__name__,message=str(error),
            completed_phases=parents,automatic_retry=False,wall_seconds=time.monotonic()-started))
        raise
    finally:journal.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frame',type=Path,required=True);parser.add_argument('--frame-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--worker',action='store_true')
    parser.add_argument('--job',type=Path);parser.add_argument('--job-sha256');args=parser.parse_args()
    if args.worker:
        contracts.need(args.job is not None and args.job_sha256,'Worker job required')
        worker(args.frame,args.frame_sha256,args.job,args.job_sha256,args.output)
    else:print(encode(execute(args.frame,args.frame_sha256,output=args.output)))


if __name__=='__main__':main()
