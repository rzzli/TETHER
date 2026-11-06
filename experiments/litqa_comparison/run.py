"""Owned-process controller for the SC04 primary four-arm experiment.

The supplied-source diagnostic and scientific evaluator are separate stages.
Successful primary execution alone never completes SC04. No automatic resume.
"""
import argparse
from contextlib import nullcontext
from datetime import datetime,timezone
from functools import partial
import json
import os
import stat
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'packages/tether/src')]
from asof.atomic import publish_bytes
from asof.journal import RunJournal
from asof.serde import canonical,encode,freeze,parse_json
from tether._process import ProcessLimits,supervise_command,validate_success_report
from experiments.labbench import model
from experiments.labbench.runtime import contain_process_tree,empty_import_cache,process_sample,InputAudit,DeadlineWatchdog,ProcessSamples
from experiments.labbench.native_contract import validate_query
from experiments.litqa_comparison import acquisition,codecs,pipeline,replay,schedule

PHASES=('expand','collect','rank','answer')
PARENTS={'expand':(),'collect':('expand',),'rank':('collect',),'answer':('collect','rank')}
RECEIPT_SHA='cc95c56ce1f497b36d6b9ed62b22721d8af7eaccc0a8c50da91439c5b076acbf'


def write(path,value):publish_bytes(Path(path),canonical(value)+b'\n')


def code_pins():
    paths=[]
    for folder in ('src/asof','packages/tether/src/tether','experiments/labbench','experiments/litqa_comparison'):
        paths.extend((ROOT/folder).rglob('*.py'))
    return {p.relative_to(ROOT).as_posix():pipeline.proof(p)['sha256'] for p in sorted(paths)}


def load_frame(path,expected):
    path=Path(path)
    codecs.need(path.is_file() and not path.is_symlink() and path.stat().st_size<=2*1024**2,'Frame path/size')
    raw=path.read_bytes();codecs.need(codecs.digest(raw)==expected,'Frame external anchor differs')
    frame=parse_json(raw)
    codecs.need(frame['kind']=='sc04_primary_execution_v1' and frame['purpose'] in ('production','fictional_qualification'),
                'Unknown execution purpose')
    count=199 if frame['purpose']=='production' else 2
    codecs.need(frame['count']==len(frame['schedule'])==count and len(set(frame['schedule']))==count,'Required full schedule')
    codecs.need(frame['phases']==list(PHASES) and frame['conditions']==['L/O','E/O','L/R','E/R','supplied_source_pending_separate_execution'],
                'Declared comparison scope differs')
    codecs.need(frame['provider_spend_usd']==0 and frame['automatic_retry'] is False,'Execution spending/retry policy')
    codecs.need(code_pins()==frame['code_pins'],'Frozen execution sources changed')
    codecs.need(pipeline.proof(sys.executable)==frame['python'],'Interpreter bytes differ')
    codecs.need(frame['generation_configuration']==encode(codecs.CONFIG),'Generation settings differ')
    codecs.need(frame['python_version']==sys.version,'Interpreter version differs')
    codecs.need(set(frame['phase_seconds'])==set(PHASES),'Phase deadline set differs')
    for seconds in frame['phase_seconds'].values():
        codecs.need(type(seconds) is int and 120<=seconds<=21600,'Invalid phase deadline')
    codecs.need(type(frame['replay_seconds']) is int and 60<=frame['replay_seconds']<=1800,'Invalid replay deadline')
    codecs.need(type(frame['port']) is int and 49152<=frame['port']<=65535,'Invalid local port')
    codecs.need(frame['alias']=='tether-sc04-primary-qwen14b-v1','Model alias differs')
    codecs.need(frame['model_receipt']['sha256']==RECEIPT_SHA,'Unqualified model receipt')
    codecs.need(set(frame['query_products'])=={'source_queries','answer_queries'},'Task products differ')
    codecs.need(canonical(frame['policy'])==canonical(acquisition.legacy.DEFAULT_POLICY),'Frozen retrieval policy differs')
    return frame


def validate_products(frame):
    # Coordinator-only: source/ranking workers must never open answer choices.
    source=queries(frame,'expand');answers=queries(frame,'answer')
    codecs.need(canonical(source)==canonical([dict(id=q['id'],question=q['question']) for q in answers]),'Task role projections differ')


def queries(frame,phase):
    key='answer_queries' if phase=='answer' else 'source_queries'
    rows=pipeline.read(frame['query_products'][key])
    codecs.need(len(rows)==frame['count'] and [q['id'] for q in rows]==frame['schedule'],'Task product order/count differs')
    checker=validate_query if phase=='answer' else codecs.question_view
    return tuple(checker(row) for row in rows)


def inventory(root,*,omit=(),seconds=180):
    root=Path(root).absolute();end=time.monotonic()+seconds;result={};total=0
    def linked(p):return p.is_symlink() or bool(getattr(p.lstat(),'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT)
    codecs.need(not linked(root),'Linked package root')
    for p in root.rglob('*'):
        codecs.need(time.monotonic()<end,'Package inventory deadline')
        codecs.need(not linked(p),'Linked package artifact')
        if not p.is_file() or p.relative_to(root).as_posix() in omit:continue
        total+=p.stat().st_size
        codecs.need(len(result)<60000 and p.stat().st_size<=128*1024**2 and total<=8*1024**3,'Package inventory bounds')
        result[p.relative_to(root).as_posix()]=pipeline.proof(p)
    codecs.need(time.monotonic()<end,'Package inventory finalization deadline')
    return result


def verify_package(root,expected):
    root=Path(root)
    raw=(root/'PACKAGE-RECEIPT.json').read_bytes()
    codecs.need(codecs.digest(raw)==expected,'Phase package external anchor')
    receipt=parse_json(raw)
    actual=inventory(root,omit=('PACKAGE-RECEIPT.json',))
    codecs.need(canonical(receipt['files'])==canonical(actual),'Phase package byte inventory changed')
    return receipt


def load_parents(descriptors,phase,ids,frame_sha=None):
    codecs.need(set(descriptors)==set(PARENTS[phase]),'Required parent descriptor set')
    result={}
    for name,description in descriptors.items():
        root=Path(description['root'])
        package=verify_package(root,description['package_sha256'])
        codecs.need(package['status']=='complete' and package['phase']==name,'Parent package phase differs')
        if frame_sha is not None:codecs.need(package['frame_sha256']==frame_sha,'Parent frame differs')
        review=parse_json((root/'REPLAY.json').read_bytes())
        codecs.need(review['status']=='verified' and review['phase']==name and
                    review['stage_receipt_sha256']==description['stage_receipt_sha256'],'Parent replay not accepted')
        result[name]=pipeline.parent_rows(root/'worker/phase',description['stage_receipt_sha256'],name,ids)
    return result


def worker(args):
    journal=RunJournal(args.output,kind='build');root=journal.output
    started=time.monotonic();owner=None;audit=None;handle=None;watchdog=None;stage='frame'
    try:
        frame=load_frame(args.frame,args.frame_sha256)
        job=pipeline.read(dict(path=str(args.job.resolve()),sha256=args.job_sha256,bytes=args.job.stat().st_size))
        codecs.need(job['phase'] in PHASES and job['frame_sha256']==args.frame_sha256,'Worker phase/frame binding')
        phase=job['phase'];limit=frame['phase_seconds'][phase];end=started+limit
        empty_import_cache(expected=job['worker_import_cache'],cache_root=ROOT/'data/cache')
        handle=contain_process_tree()
        watchdog=DeadlineWatchdog(end,root/'DEADLINE.json');watchdog.__enter__()
        parent_rows=load_parents(job['parents'],phase,frame['schedule'],args.frame_sha256)
        tasks=queries(frame,phase)
        write(root/'CONFIG.json',dict(frame_sha256=args.frame_sha256,job=job,phase=phase,planned_seconds=limit,
            purpose=frame['purpose'],cutoff=job['cutoff'],python_version=sys.version,worker_pid=os.getpid()))
        # Allow only the declared task product, model files and prior accepted
        # phase artifacts. Reference originals are never granted to the worker.
        inputs=[args.frame,args.job]
        key='answer_queries' if phase=='answer' else 'source_queries'
        inputs.append(frame['query_products'][key]['path'])
        for parent in job['parents'].values():inputs.extend(p for p in Path(parent['root']).rglob('*') if p.is_file())
        spec=bindings=provenance=None
        if phase!='collect':
            stage='model_spec'
            spec,bindings,provenance=model.make_server_spec(frame['model_receipt']['path'],frame['model_receipt']['sha256'],
                port=frame['port'],alias=frame['alias'],startup_seconds=180)
            codecs.need(canonical(spec)==canonical(frame['model_spec']) and
                        canonical(provenance)==canonical(frame['model_provenance']),'Frozen native model specification differs')
            inputs.extend(bindings.values())
            inputs.append(frame['model_license']['path'])
            codecs.need(pipeline.proof(frame['model_license']['path'])==frame['model_license'],'Model license changed')
            write(root/'MODEL.json',dict(spec=encode(spec),bindings={k:str(v) for k,v in bindings.items()},
                                        provenance=provenance,alias=frame['alias']))
            (root/'server').mkdir()
        audit=InputAudit(inputs=inputs,output=root,code_roots=(ROOT/'src',ROOT/'packages/tether/src',ROOT/'experiments',
            Path(sys.base_prefix),Path(sys.prefix),Path(job['worker_import_cache'])))
        audit.activate()
        stage='phase_execution'
        fixture_context=nullcontext()
        if frame['purpose']=='fictional_qualification' and phase=='collect':
            from unittest.mock import patch
            from experiments.litqa_comparison.qualification_fixtures import fetch
            fixture_context=patch.object(acquisition.legacy,'fetch_http',side_effect=fetch)
        with fixture_context:
            if phase=='collect':
                report=pipeline.execute(phase,tasks,root/'phase',seconds=max(.001,end-time.monotonic()-40),
                    parents=parent_rows,policy=frame['policy'])
            else:
                with model.owned_server(spec,bindings,output=root/'server',journal=journal,parent_deadline=end-30) as owner:
                    caller=partial(pipeline.model_call,owner=owner,model_provenance=provenance,alias=frame['alias'])
                    with ProcessSamples(owner.terminal_record['pid']) as samples:
                        report=pipeline.execute(phase,tasks,root/'phase',seconds=max(.001,end-time.monotonic()-40),
                            parents=parent_rows,policy=frame['policy'],cutoff=job['cutoff'],model_provenance=provenance,call_model=caller)
                    write(root/'SERVER-RESOURCE-SAMPLES.json',samples.values)
                codecs.need(owner.terminal_record['server_stopped'] is True,'Owned model cleanup unverified')
        stage='finalization'
        codecs.need(report['status']=='complete' and time.monotonic()<end,'Incomplete or overtime phase')
        codecs.need(code_pins()==frame['code_pins'],'Sources changed during phase')
        audit.flush();codecs.need(audit.denials==0,'Undeclared worker file access')
        journal.append('phase_completed',phase=phase,stage_receipt_sha256=pipeline.proof(root/'phase/STAGE-RECEIPT.json')['sha256'])
        write(root/'COMPLETE.json',dict(status='complete',phase=phase,purpose=frame['purpose'],frame_sha256=args.frame_sha256,
            stage_receipt=pipeline.proof(root/'phase/STAGE-RECEIPT.json'),wall_seconds=time.monotonic()-started,
            worker_memory=process_sample(os.getpid()),server_terminal=owner.terminal_record if owner else None,
            audit_denials=audit.denials,provider_cost_usd=0,benchmark_questions=frame['count'] if frame['purpose']=='production' else 0))
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


def review_worker(args):
    """Separate bounded process: source-inclusive replay after inference exits."""
    journal=RunJournal(args.output,kind='build');handle=None
    try:
        frame=load_frame(args.frame,args.frame_sha256)
        job=pipeline.read(dict(path=str(args.job.resolve()),sha256=args.job_sha256,bytes=args.job.stat().st_size))
        codecs.need(job['frame_sha256']==args.frame_sha256 and job['phase'] in PHASES,'Replay job/frame binding')
        handle=contain_process_tree()
        with DeadlineWatchdog(time.monotonic()+frame['replay_seconds']-10,journal.output/'DEADLINE.json'):
            phase=job['phase'];root=args.job.parent
            complete=parse_json((root/'worker/COMPLETE.json').read_bytes())
            codecs.need(complete['frame_sha256']==args.frame_sha256 and complete['phase']==phase and
                        complete['status']=='complete' and complete['audit_denials']==0,'Worker completion differs')
            tasks=queries(frame,phase);prior=load_parents(job['parents'],phase,frame['schedule'],args.frame_sha256)
            model_info=None
            if phase!='collect':
                model_info=parse_json((root/'worker/MODEL.json').read_bytes())
                codecs.need(canonical(model_info['spec'])==canonical(frame['model_spec']) and
                            canonical(model_info['provenance'])==canonical(frame['model_provenance']) and
                            model_info['alias']==frame['alias'],'Replay model/frame differs')
                codecs.need(complete['server_terminal']['server_stopped'] is True,'Model server cleanup incomplete')
                model_info['owner_pid']=complete['server_terminal']['pid']
            checked=replay.phase(root/'worker/phase',complete['stage_receipt']['sha256'],phase,tasks,
                                parents=prior,policy=frame['policy'],model_info=model_info,cutoff=job['cutoff'])
            report={k:v for k,v in checked.items() if k!='rows'}
            report.update(stage_receipt_sha256=complete['stage_receipt']['sha256'],frame_sha256=args.frame_sha256)
            write(journal.output/'REPORT.json',report)
            journal.append('replay_completed',report_sha256=pipeline.proof(journal.output/'REPORT.json')['sha256'])
    except BaseException as error:
        journal.fail(error,'source_inclusive_replay');raise
    finally:journal.close();_=handle


def supervised(command,limits,root,label):
    result=None
    try:
        result=supervise_command(command,limits=limits)
    except BaseException as error:
        result=getattr(error,'tether_engine_result',getattr(error,'result',None));raise
    finally:
        if result is not None:
            publish_bytes(root/(label+'-stdout.txt'),result.stdout);publish_bytes(root/(label+'-stderr.txt'),result.stderr)
            write(root/(label+'-SUPERVISION.json'),dict(returncode=result.returncode,supervision=result.supervision))
    codecs.need(result.returncode==0,label+' worker failed; retained state is never automatically resumed')
    validate_success_report(result.supervision,limits,len(result.stdout),len(result.stderr))
    return result


def execute_phase(frame_path,frame_sha,frame,phase,output,parents,cutoff):
    root=Path(output);journal=RunJournal(root,kind='build');result=None
    try:
        cache=(ROOT/'data/cache'/('sc04-'+root.parent.name+'-'+phase+'-imports')).resolve()
        job=dict(phase=phase,frame_sha256=frame_sha,parents=parents,cutoff=cutoff,worker_import_cache=str(cache))
        write(root/'JOB.json',job)
        command=[sys.executable,'-I','-B','-X','pycache_prefix='+str(cache),str(Path(__file__).resolve()),'worker',
            '--frame',str(Path(frame_path).resolve()),'--frame-sha256',frame_sha,'--job',str((root/'JOB.json').resolve()),
            '--job-sha256',pipeline.proof(root/'JOB.json')['sha256'],'--output',str((root/'worker').resolve())]
        limits=ProcessLimits(timeout_seconds=frame['phase_seconds'][phase],max_output_bytes=4*1024**2)
        write(root/'COMMAND.json',dict(command=command,limits=limits.payload()))
        journal.append('phase_worker_dispatch',phase=phase,job_sha256=pipeline.proof(root/'JOB.json')['sha256'])
        supervised(command,limits,root,'execution')
        complete=parse_json((root/'worker/COMPLETE.json').read_bytes())
        codecs.need(complete['frame_sha256']==frame_sha and complete['phase']==phase and complete['status']=='complete','Worker completion differs')
        review_command=list(command)
        review_command[review_command.index('worker')]='review-worker'
        review_command[-1]=str((root/'review').resolve())
        review_command[4]='pycache_prefix='+str(cache)+'-review'
        review_limits=ProcessLimits(timeout_seconds=frame['replay_seconds'],max_output_bytes=4*1024**2)
        write(root/'REVIEW-COMMAND.json',dict(command=review_command,limits=review_limits.payload()))
        journal.append('phase_replay_dispatch',phase=phase)
        supervised(review_command,review_limits,root,'review')
        checked=parse_json((root/'review/REPORT.json').read_bytes())
        codecs.need(checked['status']=='verified' and checked['phase']==phase and checked['frame_sha256']==frame_sha and
                    checked['stage_receipt_sha256']==complete['stage_receipt']['sha256'],'Replay terminal binding')
        write(root/'REPLAY.json',checked)
        journal.append('phase_package_verified',phase=phase,stage_receipt_sha256=complete['stage_receipt']['sha256'])
        journal.close()
        files=inventory(root)
        write(root/'PACKAGE-RECEIPT.json',dict(status='complete',phase=phase,frame_sha256=frame_sha,files=files))
        return dict(root=str(root.resolve()),package_sha256=pipeline.proof(root/'PACKAGE-RECEIPT.json')['sha256'],
                    stage_receipt_sha256=complete['stage_receipt']['sha256'])
    except BaseException as error:
        try:journal.fail(error,'phase_supervision_or_replay')
        except BaseException:pass
        recovery=None
        if (root/'worker/phase/CONFIG.json').exists():
            try:recovery=schedule.inspect(root/'worker/phase')
            except BaseException as failure:recovery=dict(status='uncertain',error_type=type(failure).__name__,automatic_resume=False)
        write(root/'FAILURE.json',dict(error_type=type(error).__name__,message=str(error),recovery=recovery,automatic_retry=False))
        raise
    finally:journal.close()


def execute(args):
    journal=RunJournal(args.output,kind='build');parents={};cutoff=None;handle=None;watchdog=None
    try:
        frame=load_frame(args.frame,args.frame_sha256)
        validate_products(frame)
        handle=contain_process_tree()
        watchdog=DeadlineWatchdog(time.monotonic()+sum(frame['phase_seconds'].values())+4*frame['replay_seconds']+3600,
                                  journal.output/'DEADLINE.json');watchdog.__enter__()
        write(journal.output/'FRAME.json',frame)
        for phase in PHASES:
            if phase=='answer':cutoff=datetime.now(timezone.utc).isoformat()
            selected={name:parents[name] for name in PARENTS[phase]}
            journal.append('phase_started',phase=phase)
            parents[phase]=execute_phase(args.frame,args.frame_sha256,frame,phase,journal.output/phase,selected,cutoff)
            write(journal.output/(phase+'-ANCHOR.json'),parents[phase])
            journal.append('phase_accepted',phase=phase,**parents[phase])
            print(json.dumps(dict(phase=phase,status='verified')),flush=True)
        journal.append('primary_comparison_executed',scientific_scoring_performed=False,supplied_source_complete=False)
        write(journal.output/'COMPLETE.json',dict(status='primary_execution_complete',purpose=frame['purpose'],
            phases=parents,source_cutoff=cutoff,scientific_scoring_performed=False,supplied_source_complete=False,
            sc04_complete=False,provider_cost_usd=0))
        journal.append('primary_report_sealed',complete_sha256=pipeline.proof(journal.output/'COMPLETE.json')['sha256'])
    except BaseException as error:
        journal.fail(error,'primary_comparison')
        write(journal.output/'FAILURE.json',dict(error_type=type(error).__name__,message=str(error),completed_phases=list(parents),automatic_retry=False))
        raise
    finally:
        journal.close()
        if watchdog is not None:watchdog.__exit__(None,None,None)
        _=handle
    # This compact root receipt binds all phase package anchors transitively.
    # Its external hash must be retained by the qualification/analysis caller.
    files={p.name:pipeline.proof(p) for p in journal.output.iterdir() if p.is_file()}
    write(journal.output/'ROOT-RECEIPT.json',dict(status='primary_execution_complete',frame_sha256=args.frame_sha256,files=files))
    print(json.dumps(dict(root_receipt_sha256=pipeline.proof(journal.output/'ROOT-RECEIPT.json')['sha256'])),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('execute','worker','review-worker'))
    parser.add_argument('--frame',type=Path,required=True);parser.add_argument('--frame-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--job',type=Path);parser.add_argument('--job-sha256')
    args=parser.parse_args()
    if args.mode=='worker':worker(args)
    elif args.mode=='review-worker':review_worker(args)
    else:execute(args)


if __name__=='__main__':main()
