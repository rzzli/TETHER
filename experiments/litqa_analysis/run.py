"""Bounded, offline, source-inclusive scientific analysis of completed SC04 runs.

This command never dispatches models or acquisition. Only the parent launches one
owned analysis worker. Failed attempts are retained and never resumed implicitly.
"""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import stat
import sys
import time

REPO=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(REPO),str(REPO/'src'),str(REPO/'packages/tether/src')]

from experiments.litqa_analysis.native_records import canonical, decode, digest, journal, need, read
from experiments.litqa_analysis import envelopes

PRIMARY_FIXTURE_SHA='8de520bfdef4dbe7b6363aeb962b8c4bb453adc475297aca2fa08d88e7c10cf0'
SUPPLIED_FIXTURE_SHA='f9dd1f8b8d0a560730d0450cec03647ec8adcba5d23e0836c16e6af03c1cf19c'
SOURCE_ROOTS=('experiments/litqa_analysis','experiments/labbench','src/asof','packages/tether/src/tether')
OUTPUT_CAP=4*1024**2


def utc():return datetime.now(timezone.utc).isoformat()


def publish(path,value):
    payload=value if isinstance(value,bytes) else canonical(value)+b'\n'
    with Path(path).open('xb') as stream:stream.write(payload);stream.flush();os.fsync(stream.fileno())


class Journal:
    def __init__(self,root):
        self.root=Path(root).absolute();self.root.mkdir(parents=True,exist_ok=False)
        self.stream=(self.root/'journal.jsonl').open('xb');self.previous=None;self.sequence=0
        self.append('analysis_reserved',owner_pid=os.getpid(),created_at_utc=utc())
    def append(self,event,**details):
        record=dict(event=event,details=details,sequence=self.sequence,previous_sha256=self.previous)
        record['sha256']=digest(canonical(record));self.stream.write(canonical(record)+b'\n');self.stream.flush();os.fsync(self.stream.fileno())
        self.previous=record['sha256'];self.sequence+=1
    def close(self):self.stream.close()


def source_pins():
    return {p.relative_to(REPO).as_posix():envelopes.proof(p) for folder in SOURCE_ROOTS for p in sorted((REPO/folder).rglob('*.py'))}


def environment():
    packages={}
    for name in ('asof-target-agents','tether-target-agents'):
        try:packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:packages[name]=None
    return dict(python=sys.version,executable=envelopes.proof(sys.executable),platform=dict(sys_platform=sys.platform,os_name=os.name,windows_version=list(sys.getwindowsversion()) if hasattr(sys,'getwindowsversion') else None),
        installed_packages=packages,analysis_dependencies='Python standard library; separately pinned native scorer and process supervisor use local project code.')


def verify_frame(path,sha):
    frame=envelopes.anchored(path,sha)
    need(frame['kind']=='sc04_scientific_analysis_execution_v1' and frame['purpose'] in ('production','fictional_qualification'),'Analysis purpose')
    need(frame['provider_cost_usd']==0 and frame['automatic_retry'] is False,'No inference/acquisition spending or retries')
    need(type(frame['seconds']) is int and 1<=frame['seconds']<=21600 and frame['output_cap']==OUTPUT_CAP,'Analysis process bounds')
    need(frame['bootstrap_replicates']==10000 and frame['seed']==20261106,'Frozen analysis statistics')
    need(frame['code_proofs']==source_pins() and frame['environment']==environment(),'Analysis execution code/environment changed')
    return frame


def fail(log,error,stage):
    details=dict(error_type=type(error).__name__,stage=stage,automatic_retry=False,failed_at_utc=utc())
    try:log.append('analysis_failed',**details)
    except BaseException:pass
    try:publish(log.root/'FAILURE.json',details)
    except BaseException:pass


def no_dispatch(event,args):
    if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.posix_spawn','os.posix_spawnp','os.spawn'):
        raise PermissionError('Analysis worker cannot dispatch network or subprocess operations')


def worker_write_guard(root):
    """Protect originals from accidental writes; this is not a hostile-code sandbox."""
    root=Path(root).resolve()
    def permitted(path):
        if isinstance(path,int):return
        need(isinstance(path,(str,bytes,os.PathLike)),'Known analysis write path')
        resolved=Path(os.fsdecode(path)).resolve()
        if not resolved.is_relative_to(root):raise PermissionError('Analysis write outside reserved worker output')
    def audit(event,args):
        no_dispatch(event,args)
        if event=='open':
            path,mode,flags=args
            if (isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):
                permitted(path)
        elif event in ('os.remove','os.rmdir','os.mkdir','os.chmod','os.utime','os.truncate'):
            permitted(args[0])
        elif event in ('os.rename','os.replace','os.link','os.symlink'):
            permitted(args[0]);permitted(args[1])
    return audit


def fictional_inputs(primary,supplied):
    need(primary['root_sha256']==PRIMARY_FIXTURE_SHA and supplied['root_sha256']==SUPPLIED_FIXTURE_SHA,'Exact externally anchored fictional fixtures')
    need(primary['frame']['purpose']==supplied['frame']['purpose']=='fictional_qualification','Fictional mode cannot score production')
    queries=envelopes.external(primary['frame']['query_products']['answer_queries'])
    need(queries==envelopes.external(supplied['frame']['products']['answer_queries']),'Fictional common queries')
    ids=[f'00000000-0000-0000-0000-{i:012d}' for i in (901,902)]
    expected=[dict(id=ids[0],question='In the invented Lumarin experiment, what happened to cobalt uptake after treatment?',
        choices=['(A) Increased','(B) Insufficient information to answer the question','(C) Reduced']),
        dict(id=ids[1],question='In the invented Vesprine experiment, what happened to amber uptake after treatment?',
        choices=['(A) Increased','(B) Insufficient information to answer the question','(C) Reduced'])]
    need(queries==expected,'Known invented questions and options')
    hints=envelopes.external(supplied['frame']['products']['hints'])
    need(hints==[dict(id=q['id'],question=q['question'],dois=['10.1234/invented']) for q in queries],'Invented source annotations')
    return dict(queries=queries,references=[dict(id=ids[0],answer_index=0,unsure_index=1),dict(id=ids[1],answer_index=2,unsure_index=1)],
        hints=hints,doi_schedule=['10.1234/invented'],groups=[ids],annotations={i:['10.1234/invented'] for i in ids},
        scope='Known invented controls only; not a production scientific result.')


def reconstructed(envelope):
    from experiments.litqa_analysis import reconstruct_run
    result=reconstruct_run.primary_verified(envelope) if envelope['kind']=='primary' else reconstruct_run.supplied_verified(envelope)
    return dict(status='independently_reconstructed',root=envelope['root'],root_sha256=envelope['root_sha256'],
        frame_sha256=envelope['frame_sha256'],purpose=envelope['frame']['purpose'],resources=envelope['resources'],**result,
        source_lineage_checked=True,native_calls_checked=True,cross_stage_products_checked=True,scientific_correctness_scored=False,
        model_weight_bytes_rehashed=False)


def scientific_work(frame,log):
    from experiments.litqa_analysis import inputs, aggregate
    start=time.monotonic();stage='verify_primary'
    def progress(event,**details):log.append(event,at_utc=utc(),elapsed_seconds=time.monotonic()-start,**details)
    progress('primary_verification_started')
    primary=envelopes.verify_run(frame['primary']['root'],frame['primary']['root_sha256'],kind='primary')
    progress('primary_envelope_verified',questions=len(primary['frame']['schedule']))
    supplied=envelopes.verify_run(frame['supplied']['root'],frame['supplied']['root_sha256'],kind='supplied')
    progress('supplied_envelope_verified',questions=supplied['frame']['questions'])
    if frame['purpose']=='production':
        pair=envelopes.verify_pair(primary,supplied)
        need(frame['analysis_inputs'] is not None,'Production requires frozen original evaluator inputs')
        answer_start=journal(Path(primary['phases']['answer']['root'])/'worker/journal.jsonl')[0]['details']['created_at_utc']
        checked=inputs.verify(frame['analysis_inputs']['path'],frame['analysis_inputs']['sha256'],answer_started_at=answer_start)
        need(checked['queries']==envelopes.external(primary['frame']['query_products']['answer_queries']) and
            checked['hints']==envelopes.external(supplied['frame']['products']['hints']) and
            checked['doi_schedule']==envelopes.external(supplied['frame']['products']['doi_schedule']),'Original full question/reference-source projection join')
        need(supplied['frame']['source_projection']['sha256']==checked['manifest']['annotation_projection']['sha256'],'Diagnostic original annotation projection')
        scorer_proof=checked['manifest']['native_scorer'];count=199
    else:
        need(frame['analysis_inputs'] is None,'Fictional analysis cannot consume production keys')
        checked=fictional_inputs(primary,supplied);count=2
        pair=dict(status='fictional_fixture_pair',production_pair_gate=False,scope='Only exact retained fictional anchors and questions; production ordering gate is not relaxed.')
        scorer_proof=envelopes.proof(REPO/'experiments/labbench/evaluate.py')
        need(scorer_proof['sha256']==primary['frame']['code_pins']['experiments/labbench/evaluate.py'],'Fictional native scorer source')
    publish(log.root/'INPUTS.json',checked);publish(log.root/'PAIR.json',pair)
    progress('original_inputs_verified',questions=count,reference_pairs=sum(len(h['dois']) for h in checked['hints']),publication_groups=len(checked['groups']))
    primary_result=reconstructed(primary);publish(log.root/'PRIMARY-RECONSTRUCTION.json',primary_result)
    progress('primary_reconstructed',questions=count,answers=4*count)
    supplied_result=reconstructed(supplied);publish(log.root/'SUPPLIED-RECONSTRUCTION.json',supplied_result)
    progress('supplied_reconstructed',questions=count,answers=count)
    summary=aggregate.summarize(primary_result,supplied_result,checked,expected_count=count,replicates=frame['bootstrap_replicates'],seed=frame['seed'])
    publish(log.root/'RESULTS.json',summary);progress('independent_metrics_completed',arms=5,bootstrap_replicates=frame['bootstrap_replicates'])
    need(envelopes.proof(scorer_proof['path'])==scorer_proof and Path(scorer_proof['path']).resolve()==(REPO/'experiments/labbench/evaluate.py').resolve(),'Pinned native scoring implementation')
    from experiments.labbench.evaluate import evaluate_schedule
    agreement=aggregate.native_agreement(summary,primary_result,supplied_result,checked,evaluate_schedule)
    publish(log.root/'NATIVE-AGREEMENT.json',agreement)
    percase={arm:dict(scored=summary['arms'][arm]['case_results'],sources=summary['source_cases'][arm]) for arm in summary['arms']}
    publish(log.root/'PER-CASE.json',percase)
    from experiments.labbench.runtime import process_sample
    resources=dict(analysis_wall_seconds=time.monotonic()-start,analysis_process=process_sample(os.getpid()),
        experiment_physical=summary['physical_accounting'],experiment_logical=summary['logical_arm_accounting'],provider_cost_usd=0,
        limits='Analysis measurement ends before final receipt publication; process peak is not aggregate machine RAM. No GPU/energy measurement.')
    publish(log.root/'RESOURCES.json',resources)
    progress('native_agreement_completed',arms=agreement['arms_checked'])
    return dict(status='complete',purpose=frame['purpose'],questions=count,answer_records=5*count,
        independent_native_agreement=agreement['status'],provider_cost_usd=0,scientific_validation='not_established',
        scope='Complete scheduled finite LitQA2 comparisons; public-development experimental estimates, not clinical or independent biological validation.')


def worker(frame_path,sha,output):
    log=Journal(output);stage='worker_frame_validation'
    try:
        # Install only after the worker owns its new output; all later writes stay here.
        sys.addaudithook(worker_write_guard(log.root))
        frame=verify_frame(frame_path,sha);log.append('worker_frame_verified',frame_sha256=sha)
        stage='scientific_reconstruction_and_scoring';complete=scientific_work(frame,log)
        stage='worker_finalization';verify_frame(frame_path,sha)
        publish(log.root/'COMPLETE.json',complete);log.append('analysis_completed',complete_sha256=digest(read(log.root/'COMPLETE.json')))
        log.close();files=envelopes.inventory(log.root)
        publish(log.root/'RECEIPT.json',dict(status='complete',frame_sha256=sha,files=files))
        print(json.dumps(dict(status='complete',receipt_sha256=digest(read(log.root/'RECEIPT.json')))))
    except BaseException as error:fail(log,error,stage);raise
    finally:log.close()


def execute(args):
    # Reserve before reading any run, receipt, model record, or source file.
    log=Journal(args.output);stage='analysis_frame'
    try:
        need(type(args.seconds) is int and 1<=args.seconds<=21600,'Analysis process seconds')
        need((args.analysis_inputs is None)==(args.analysis_inputs_sha256 is None),'Paired analysis input path/hash')
        need(not args.fictional or args.analysis_inputs is None,'Fictional mode has no production evaluator inputs')
        if not args.fictional:need(args.analysis_inputs is not None,'Production requires original frozen evaluator manifest')
        for value in (args.primary_root_sha256,args.supplied_root_sha256):need(isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value),'External root SHA256')
        frame=dict(kind='sc04_scientific_analysis_execution_v1',purpose='fictional_qualification' if args.fictional else 'production',created_at_utc=utc(),
            primary=dict(root=str(Path(args.primary_root).absolute()),root_sha256=args.primary_root_sha256),
            supplied=dict(root=str(Path(args.supplied_root).absolute()),root_sha256=args.supplied_root_sha256),
            analysis_inputs=None if args.analysis_inputs is None else dict(path=str(Path(args.analysis_inputs).absolute()),sha256=args.analysis_inputs_sha256),
            seconds=args.seconds,output_cap=OUTPUT_CAP,bootstrap_replicates=10000,seed=20261106,provider_cost_usd=0,automatic_retry=False,
            code_proofs=source_pins(),environment=environment())
        publish(log.root/'FRAME.json',frame);sha=digest(read(log.root/'FRAME.json'));log.append('analysis_frame_frozen',frame_sha256=sha)
        from tether._process import ProcessLimits,supervise_command,validate_success_report
        limits=ProcessLimits(timeout_seconds=args.seconds,max_output_bytes=OUTPUT_CAP)
        worker_root=log.root/'worker';cache=log.root/'import-cache';cache.mkdir()
        command=[sys.executable,'-I','-B','-X','pycache_prefix='+str(cache),str(Path(__file__).resolve()),'worker',
            '--frame',str(log.root/'FRAME.json'),'--frame-sha256',sha,'--output',str(worker_root)]
        publish(log.root/'COMMAND.json',dict(argv=command,limits=limits.payload(),subprocesses_permitted_in_worker=False,network_permitted=False))
        stage='supervised_analysis';log.append('analysis_worker_started',output=str(worker_root),seconds=args.seconds)
        try:result=supervise_command(command,limits=limits)
        except BaseException as error:
            result=getattr(error,'tether_engine_result',None)
            if result is None:result=getattr(error,'result',None)
            if result is not None:
                publish(log.root/'SUPERVISION.json',result.supervision);publish(log.root/'stdout.log',result.stdout);publish(log.root/'stderr.log',result.stderr)
            raise
        publish(log.root/'SUPERVISION.json',result.supervision);publish(log.root/'stdout.log',result.stdout);publish(log.root/'stderr.log',result.stderr)
        need(result.returncode==0,'Analysis worker did not complete')
        validate_success_report(result.supervision,limits,len(result.stdout),len(result.stderr))
        terminal=decode(result.stdout.strip());need(terminal['status']=='complete','Analysis worker success record')
        worker_receipt=envelopes.anchored(worker_root/'RECEIPT.json',terminal['receipt_sha256'])
        need(worker_receipt['status']=='complete' and worker_receipt['frame_sha256']==sha and worker_receipt['files']==envelopes.inventory(worker_root,omit=('RECEIPT.json',)),'Analysis worker exact final files')
        need(not list(cache.iterdir()),'Unexpected analysis import-cache writes')
        verify_frame(log.root/'FRAME.json',sha)
        complete=dict(status='complete',purpose=frame['purpose'],frame_sha256=sha,worker_receipt=envelopes.proof(worker_root/'RECEIPT.json'),
            scientific_summary=envelopes.proof(worker_root/'RESULTS.json'),provider_cost_usd=0,automatic_retry=False)
        publish(log.root/'COMPLETE.json',complete);log.append('analysis_worker_accepted',worker_receipt_sha256=terminal['receipt_sha256'])
        log.append('analysis_report_sealed',complete_sha256=digest(read(log.root/'COMPLETE.json')));log.close()
        publish(log.root/'RECEIPT.json',dict(status='complete',files=envelopes.inventory(log.root)))
        print(json.dumps(dict(status='complete',output=str(log.root),receipt_sha256=digest(read(log.root/'RECEIPT.json')))))
    except BaseException as error:fail(log,error,stage);raise
    finally:log.close()


def inspect(output):
    root=Path(output);raw=read(root/'journal.jsonl');lines=raw.splitlines(keepends=True)
    events=[];previous=None;tail=0;error=None
    for number,line in enumerate(lines):
        if not line.endswith(b'\n'):tail=len(line);break
        try:
            event=decode(line);sha=event.pop('sha256')
            need(event['sequence']==number and event['previous_sha256']==previous and digest(canonical(event))==sha,'Inspection journal chain')
            previous=sha;events.append(event)
        except (ValueError,KeyError,TypeError) as exc:error=type(exc).__name__;break
    print(json.dumps(dict(output=str(root),verified_events=len(events),last_verified_event=events[-1]['event'] if events else None,
        trailing_uncommitted_bytes=tail,chain_error=error,receipt_present=(root/'RECEIPT.json').exists(),
        completion_verified=False,failure_present=(root/'FAILURE.json').exists(),automatic_retry=False)))


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('execute')
    for key in ('primary-root','primary-root-sha256','supplied-root','supplied-root-sha256','output'):p.add_argument('--'+key,required=True)
    p.add_argument('--analysis-inputs');p.add_argument('--analysis-inputs-sha256');p.add_argument('--fictional',action='store_true');p.add_argument('--seconds',type=int,default=1800)
    w=commands.add_parser('worker');w.add_argument('--frame',required=True);w.add_argument('--frame-sha256',required=True);w.add_argument('--output',required=True)
    i=commands.add_parser('inspect');i.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.command=='execute':execute(args)
    elif args.command=='worker':worker(args.frame,args.frame_sha256,args.output)
    else:inspect(args.output)


if __name__=='__main__':main()
