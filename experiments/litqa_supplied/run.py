"""Supervised supplied-paper diagnostic. Never ordinary retrieval evaluation."""
import argparse
from contextlib import nullcontext
from datetime import datetime,timezone
from functools import partial
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'packages/tether/src')]
from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal
from tether_engine.serde import canonical,encode,parse_json
from experiments.labbench import model
from experiments.labbench.native_contract import validate_query
from experiments.labbench.runtime import contain_process_tree,empty_import_cache,DeadlineWatchdog,InputAudit,ProcessSamples,process_sample
from experiments.litqa_comparison import run as controller,pipeline as primary,codecs,schedule
from experiments.litqa_supplied import pipeline,resolver

PHASES=('collect','answer')
write=controller.write


def code_pins():
    pins=controller.code_pins()
    pins.update({p.relative_to(ROOT).as_posix():primary.proof(p)['sha256'] for p in (ROOT/'experiments/litqa_supplied').rglob('*.py')})
    return pins


def load_frame(path,sha):
    path=Path(path)
    codecs.need(path.is_file() and not path.is_symlink() and path.stat().st_size<=2*1024**2,'Diagnostic frame path/size')
    raw=path.read_bytes();codecs.need(codecs.digest(raw)==sha,'Diagnostic external frame anchor')
    frame=parse_json(raw)
    codecs.need(frame['kind']=='sc04_supplied_execution_v1' and frame['purpose'] in ('production','fictional_qualification'),'Diagnostic frame purpose')
    counts=(199,190,205) if frame['purpose']=='production' else (2,1,2)
    codecs.need((frame['questions'],frame['unique_dois'],frame['question_doi_pairs'])==counts,'Diagnostic full declared cohort')
    codecs.need(frame['code_pins']==code_pins() and frame['python']==primary.proof(sys.executable),'Diagnostic frozen source/interpreter')
    codecs.need(frame['generation_configuration']==encode(codecs.CONFIG) and frame['provider_cost_usd']==0 and
                frame['automatic_retry'] is False and frame['ordinary_retrieval'] is False,'Diagnostic execution policy')
    codecs.need(canonical(frame['policy'])==canonical(resolver.legacy.DEFAULT_POLICY),'Diagnostic fixed retrieval limits')
    codecs.need(frame['model']['model_receipt']['sha256']==controller.RECEIPT_SHA,'Qualified model receipt')
    codecs.need(set(frame['phase_seconds'])==set(PHASES) and all(type(v) is int and 120<=v<=7200 for v in frame['phase_seconds'].values()),'Diagnostic phase deadlines')
    codecs.need(type(frame['replay_seconds']) is int and 60<=frame['replay_seconds']<=1800,'Diagnostic replay deadline')
    return frame


def tasks(frame,phase):
    if phase=='collect':
        values=primary.read(frame['products']['doi_schedule'])
        codecs.need(len(values)==len(set(values))==frame['unique_dois'],'Diagnostic full unique DOI schedule')
        return tuple(resolver.identity(v) for v in values)
    queries=tuple(validate_query(q) for q in primary.read(frame['products']['answer_queries']))
    hints=primary.read(frame['products']['hints'])
    codecs.need(len(queries)==len(hints)==frame['questions'] and [q['id'] for q in queries]==[h['id'] for h in hints] and
                len({q['id'] for q in queries})==frame['questions'],'Diagnostic complete question schedule')
    for q,h in zip(queries,hints):
        codecs.need(set(h)=={'id','question','dois'} and h['question']==q['question'] and 1<=len(h['dois'])<=2,'Diagnostic hint projection')
        codecs.need(len(set(h['dois']))==len(h['dois']),'Duplicate diagnostic paper')
        for doi in h['dois']:resolver.identity(doi)
    codecs.need(sum(len(h['dois']) for h in hints)==frame['question_doi_pairs'] and
                {d for h in hints for d in h['dois']}==set(tasks(frame,'collect')),'Diagnostic paper schedule differs')
    return queries,hints


def primary_gate(frame):
    """Production requires the whole primary execution to have finalized first."""
    if frame['purpose']=='fictional_qualification':
        codecs.need(frame['primary_execution'] is None,'Fictional trial cannot claim a production parent');return
    descriptor=frame['primary_execution'];root=Path(descriptor['root'])
    receipt=primary.read(descriptor['receipt'])
    codecs.need(Path(descriptor['receipt']['path'])==root/'ROOT-RECEIPT.json','Primary root receipt path')
    codecs.need(set(receipt['files'])=={p.name for p in root.iterdir() if p.is_file() and p.name!='ROOT-RECEIPT.json'},'Primary root inventory')
    for name,proof in receipt['files'].items():
        path=Path(proof['path'])
        codecs.need(path==root/name and not path.is_symlink() and path.stat().st_size<=8*1024**2 and
                    primary.proof(path)==proof,'Primary root file proof')
    complete=parse_json((root/'COMPLETE.json').read_bytes())
    codecs.need(complete['purpose']=='production' and complete['status']=='primary_execution_complete' and
                set(complete['phases'])==set(controller.PHASES),'Primary measurement must be complete before diagnostic acquisition')
    for phase,anchor in complete['phases'].items():
        package=controller.verify_package(anchor['root'],anchor['package_sha256'])
        codecs.need(package['phase']==phase and package['frame_sha256']==receipt['frame_sha256'],'Primary package identity')


def collected(frame,job,frame_sha):
    descriptor=job['collection'];root=Path(descriptor['root'])
    package=controller.verify_package(root,descriptor['package_sha256'])
    codecs.need(package['phase']=='collect' and package['frame_sha256']==frame_sha,'Diagnostic parent package binding')
    replay=parse_json((root/'REPLAY.json').read_bytes())
    codecs.need(replay['status']=='verified' and replay['stage_receipt_sha256']==descriptor['stage_receipt_sha256'],'Diagnostic parent replay')
    return pipeline.collection_rows(root/'worker/phase',descriptor['stage_receipt_sha256'],tasks(frame,'collect'))


def worker(args):
    journal=RunJournal(args.output,kind='build');root=journal.output;owner=None;audit=None;handle=None;watchdog=None;start=time.monotonic()
    try:
        frame=load_frame(args.frame,args.frame_sha256);job=primary.read(args.job_proof)
        phase=job['phase'];codecs.need(phase in PHASES and job['frame_sha256']==args.frame_sha256,'Diagnostic job identity')
        end=start+frame['phase_seconds'][phase];empty_import_cache(expected=job['import_cache'],cache_root=ROOT/'data/cache')
        handle=contain_process_tree();watchdog=DeadlineWatchdog(end,root/'DEADLINE.json');watchdog.__enter__()
        inputs=[args.frame,args.job]
        inputs.extend(frame['products'][k]['path'] for k in (('doi_schedule',) if phase=='collect' else ('doi_schedule','answer_queries','hints')))
        queries=tasks(frame,phase);prior=None
        if phase=='answer':
            prior=collected(frame,job,args.frame_sha256)
            inputs.extend(p for p in Path(job['collection']['root']).rglob('*') if p.is_file())
        model_frame=frame['model'];spec=bindings=provenance=None
        if phase=='answer':
            spec,bindings,provenance=model.make_server_spec(model_frame['model_receipt']['path'],model_frame['model_receipt']['sha256'],
                port=model_frame['port'],alias=model_frame['alias'],startup_seconds=180)
            codecs.need(canonical(spec)==canonical(model_frame['model_spec']) and canonical(provenance)==canonical(model_frame['model_provenance']),
                        'Diagnostic model specification differs')
            codecs.need(primary.proof(model_frame['model_license']['path'])==model_frame['model_license'],'Diagnostic model license')
            inputs.extend(bindings.values());inputs.append(model_frame['model_license']['path']);(root/'server').mkdir()
            write(root/'MODEL.json',dict(spec=spec,bindings={k:str(v) for k,v in bindings.items()},provenance=provenance,alias=model_frame['alias']))
        write(root/'CONFIG.json',dict(frame_sha256=args.frame_sha256,job=job,purpose=frame['purpose']))
        audit=InputAudit(inputs=inputs,output=root,code_roots=(ROOT/'src',ROOT/'packages/tether/src',ROOT/'experiments',
            Path(sys.prefix),Path(sys.base_prefix),Path(job['import_cache'])))
        audit.activate();fixture=nullcontext()
        if phase=='collect' and frame['purpose']=='fictional_qualification':
            from unittest.mock import patch
            from experiments.litqa_supplied.qualification_fixtures import fetch
            fixture=patch.object(resolver.legacy,'fetch_http',side_effect=fetch)
        with fixture:
            if phase=='collect':report=pipeline.collect(queries,root/'phase',seconds=max(.001,end-time.monotonic()-40),policy=frame['policy'])
            else:
                with model.owned_server(spec,bindings,output=root/'server',journal=journal,parent_deadline=end-30) as owner:
                    with ProcessSamples(owner.terminal_record['pid']) as samples:
                        report=pipeline.answer(*queries,prior,job['common_root'],root/'phase',seconds=max(.001,end-time.monotonic()-40),
                            cutoff=job['cutoff'],model_provenance=provenance,
                            call_model=partial(primary.model_call,owner=owner,model_provenance=provenance,alias=model_frame['alias']))
                    write(root/'SERVER-RESOURCE-SAMPLES.json',samples.values)
                codecs.need(owner.terminal_record['server_stopped'],'Diagnostic owned server cleanup')
        codecs.need(report['status']=='complete' and time.monotonic()<end,'Incomplete/overtime diagnostic phase')
        codecs.need(code_pins()==frame['code_pins'],'Diagnostic code changed during execution')
        audit.flush();codecs.need(audit.denials==0,'Diagnostic undeclared input access')
        complete=dict(status='complete',phase=phase,frame_sha256=args.frame_sha256,purpose=frame['purpose'],
            stage_receipt=primary.proof(root/'phase/STAGE-RECEIPT.json'),worker_wall_seconds=time.monotonic()-start,
            worker_memory=process_sample(__import__('os').getpid()),server_terminal=owner.terminal_record if owner else None,audit_denials=audit.denials)
        write(root/'COMPLETE.json',complete);journal.append('diagnostic_phase_completed',complete_sha256=primary.proof(root/'COMPLETE.json')['sha256'])
    except BaseException as error:
        journal.fail(error,'diagnostic_worker');write(root/'FAILURE.json',dict(error_type=type(error).__name__,message=str(error),automatic_retry=False));raise
    finally:
        if audit is not None:audit.flush()
        journal.close()
        if watchdog is not None:watchdog.__exit__(None,None,None)
        _=handle


def review_worker(args):
    journal=RunJournal(args.output,kind='build');handle=None
    try:
        frame=load_frame(args.frame,args.frame_sha256);job=primary.read(args.job_proof);phase=job['phase'];root=args.job.parent
        codecs.need(phase in PHASES and job['frame_sha256']==args.frame_sha256,'Diagnostic review job')
        handle=contain_process_tree()
        with DeadlineWatchdog(time.monotonic()+frame['replay_seconds']-10,journal.output/'DEADLINE.json'):
            complete=parse_json((root/'worker/COMPLETE.json').read_bytes())
            codecs.need(complete['status']=='complete' and complete['phase']==phase and complete['frame_sha256']==args.frame_sha256 and
                        complete['audit_denials']==0,'Diagnostic worker terminal binding')
            sha=complete['stage_receipt']['sha256']
            if phase=='collect':
                rows=pipeline.collection_rows(root/'worker/phase',sha,tasks(frame,'collect'))
                review=dict(status='verified',unique_dois=len(rows),diagnostic_only=True,ordinary_retrieval=False)
            else:
                prior=collected(frame,job,args.frame_sha256);info=parse_json((root/'worker/MODEL.json').read_bytes())
                codecs.need(canonical(info['spec'])==canonical(frame['model']['model_spec']) and
                            canonical(info['provenance'])==canonical(frame['model']['model_provenance']) and
                            info['alias']==frame['model']['alias'] and complete['server_terminal']['server_stopped'],'Diagnostic native model binding')
                info['owner_pid']=complete['server_terminal']['pid']
                review=encode(pipeline.replay_answers(root/'worker/phase',sha,*tasks(frame,'answer'),prior,job['common_root'],
                                                      cutoff=job['cutoff'],model_info=info))
            review.update(phase=phase,frame_sha256=args.frame_sha256,stage_receipt_sha256=sha)
            write(journal.output/'REPORT.json',review);journal.append('diagnostic_replay_completed',report_sha256=primary.proof(journal.output/'REPORT.json')['sha256'])
    except BaseException as error:journal.fail(error,'diagnostic_replay');raise
    finally:journal.close();_=handle


def execute_phase(args,frame,phase,output,collection,cutoff):
    journal=RunJournal(output,kind='build');root=journal.output
    try:
        cache=(ROOT/'data/cache'/('sc04-diagnostic-'+root.parent.name+'-'+phase+'-imports')).resolve()
        job=dict(phase=phase,frame_sha256=args.frame_sha256,collection=collection,cutoff=cutoff,common_root=str(root.parent.resolve()),import_cache=str(cache))
        write(root/'JOB.json',job);job_proof=primary.proof(root/'JOB.json')
        command=[sys.executable,'-I','-B','-X','pycache_prefix='+str(cache),str(Path(__file__).resolve()),'worker',
            '--frame',str(args.frame.resolve()),'--frame-sha256',args.frame_sha256,'--job',job_proof['path'],
            '--job-sha256',job_proof['sha256'],'--output',str((root/'worker').resolve())]
        limits=controller.ProcessLimits(timeout_seconds=frame['phase_seconds'][phase],max_output_bytes=4*1024**2)
        write(root/'COMMAND.json',dict(command=command,limits=limits.payload()));journal.append('diagnostic_worker_dispatch',phase=phase)
        controller.supervised(command,limits,root,'execution')
        command[6]='review-worker';command[4]+='-review';command[-1]=str((root/'review').resolve())
        limits=controller.ProcessLimits(timeout_seconds=frame['replay_seconds'],max_output_bytes=4*1024**2)
        write(root/'REVIEW-COMMAND.json',dict(command=command,limits=limits.payload()));journal.append('diagnostic_replay_dispatch',phase=phase)
        controller.supervised(command,limits,root,'review')
        review=parse_json((root/'review/REPORT.json').read_bytes())
        codecs.need(review['status']=='verified' and review['frame_sha256']==args.frame_sha256 and review['phase']==phase,'Diagnostic replay terminal')
        write(root/'REPLAY.json',review);journal.append('diagnostic_phase_verified',stage_receipt_sha256=review['stage_receipt_sha256']);journal.close()
        write(root/'PACKAGE-RECEIPT.json',dict(status='complete',phase=phase,frame_sha256=args.frame_sha256,files=controller.inventory(root)))
        return dict(root=str(root.resolve()),package_sha256=primary.proof(root/'PACKAGE-RECEIPT.json')['sha256'],stage_receipt_sha256=review['stage_receipt_sha256'])
    except BaseException as error:
        try:journal.fail(error,'diagnostic_supervision')
        except BaseException:pass
        write(root/'FAILURE.json',dict(error_type=type(error).__name__,message=str(error),automatic_retry=False));raise
    finally:journal.close()


def execute(args):
    journal=RunJournal(args.output,kind='build');phases={};watchdog=None;handle=None;cutoff=None
    try:
        frame=load_frame(args.frame,args.frame_sha256)
        handle=contain_process_tree();watchdog=DeadlineWatchdog(time.monotonic()+sum(frame['phase_seconds'].values())+2*frame['replay_seconds']+1800,journal.output/'DEADLINE.json');watchdog.__enter__()
        tasks(frame,'answer');primary_gate(frame)
        write(journal.output/'FRAME.json',frame)
        for phase in PHASES:
            if phase=='answer':cutoff=datetime.now(timezone.utc).isoformat()
            journal.append('diagnostic_phase_started',phase=phase)
            phases[phase]=execute_phase(args,frame,phase,journal.output/phase,phases.get('collect'),cutoff)
            write(journal.output/(phase+'-ANCHOR.json'),phases[phase]);journal.append('diagnostic_phase_accepted',phase=phase,**phases[phase])
            print(json.dumps(dict(phase=phase,status='verified')),flush=True)
        write(journal.output/'COMPLETE.json',dict(status='diagnostic_execution_complete',purpose=frame['purpose'],phases=phases,source_cutoff=cutoff,
            scientific_scoring_performed=False,sc04_complete=False,ordinary_retrieval=False,provider_cost_usd=0))
        journal.append('diagnostic_report_sealed',complete_sha256=primary.proof(journal.output/'COMPLETE.json')['sha256'])
    except BaseException as error:
        journal.fail(error,'diagnostic_controller');write(journal.output/'FAILURE.json',dict(error_type=type(error).__name__,message=str(error),completed_phases=list(phases),automatic_retry=False));raise
    finally:
        journal.close()
        if watchdog is not None:watchdog.__exit__(None,None,None)
        _=handle
    write(journal.output/'ROOT-RECEIPT.json',dict(status='diagnostic_execution_complete',frame_sha256=args.frame_sha256,
        files={p.name:primary.proof(p) for p in journal.output.iterdir() if p.is_file()}))
    print(json.dumps(dict(root_receipt_sha256=primary.proof(journal.output/'ROOT-RECEIPT.json')['sha256'])),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('execute','worker','review-worker'))
    parser.add_argument('--frame',type=Path,required=True);parser.add_argument('--frame-sha256',required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--job',type=Path);parser.add_argument('--job-sha256');args=parser.parse_args()
    if args.mode!='execute':args.job_proof=dict(path=str(args.job.resolve()),sha256=args.job_sha256,bytes=args.job.stat().st_size)
    if args.mode=='execute':execute(args)
    elif args.mode=='worker':worker(args)
    else:review_worker(args)


if __name__=='__main__':main()
