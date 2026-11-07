"""Supervise one explicitly pinned calibration worker; no implicit recovery.

This coordinator reads only launch metadata and terminal artifacts. Preparation,
calibration-label scoring and fitting are separate roles, never worker inputs.
"""
import argparse
import hashlib
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if __name__ == '__main__':
    sys.path[:0] = [str(ROOT), str(ROOT/'src'), str(ROOT/'packages/tether/src')]

from tether._process import ProcessLimits, supervise_command, validate_success_report
from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal
from tether_engine.serde import canonical, freeze, parse_json
from experiments.scifact_calibration.inputs import anchored, capture, digest, local_path, need

KIND = 'sc05_calibration_supervision_v1'


def _proof(path):
    path=local_path(path)
    with path.open('rb') as stream: sha=hashlib.file_digest(stream,'sha256').hexdigest()
    return dict(path=str(path),bytes=path.stat().st_size,sha256=sha)


def load_frame(path,expected_sha256,output):
    raw,proof=anchored(path,expected_sha256,1024**2)
    frame=parse_json(raw)
    need(isinstance(frame,dict) and set(frame)=={'schema_version','kind','purpose','mode',
         'recipe','worker','interpreter','code_files','limits','output'},'Calibration supervisor fields')
    need(type(frame['schema_version']) is int and frame['schema_version']==1 and frame['kind']==KIND
         and frame['purpose']=='calibrate' and frame['mode'] in ('qualification','production'),'Supervisor contract')
    root=local_path(output)
    need(root==local_path(frame['output']) and root.is_relative_to(ROOT) and root!=ROOT,
         'Reserved workspace output differs')
    need(not root.exists(),'Output already reserved; inspect, never redispatch')
    need(isinstance(frame['limits'],dict) and set(frame['limits'])=={'process_seconds','console_bytes'},'Process limit fields')
    limits=ProcessLimits(frame['limits']['process_seconds'],frame['limits']['console_bytes'])
    limits.validate()
    need(limits.timeout_seconds<=43200,'Calibration phase exceeds twelve-hour bound')
    need(isinstance(frame['code_files'],list) and frame['code_files'],'Source closure required')
    for item in (proof,frame['recipe'],frame['worker'],frame['interpreter'],*frame['code_files']):
        path=local_path(item['path'])
        need(not path.is_relative_to(root),'Output overlaps input')
    paths=[str(local_path(p['path'])).casefold() for p in frame['code_files']]
    need(len(paths)==len(set(paths)) and str(Path(__file__).resolve()).casefold() in paths,'Unique pinned coordinator closure required')
    need(str(local_path(frame['worker']['path'])).casefold() in paths,'Worker missing from source closure')
    if frame['mode']=='production':
        need(local_path(frame['worker']['path'])==Path(__file__).with_name('worker.py'),
             'Production must use the calibration worker')
    return raw,proof,frame,root,limits


def _worker_status(root,frame,recipe):
    need(not any((root/name).exists() for name in
                 ('FAILURE.json','PAIR-TIMEOUT.json','DEADLINE.json','FINALIZATION-FAILED.json')),
         'Worker has a terminal failure marker')
    path=local_path(root/'STATUS.json')
    need(path.stat().st_size<=1024**2,'Worker terminal bound')
    status_raw=capture(_proof(path),1024**2)
    status=parse_json(status_raw)
    need(status.get('schema_version')==1 and status.get('kind')=='sc05_calibration_worker_status_v1'
         and status.get('status')=='completed' and status.get('recipe_sha256')==frame['recipe']['sha256'],
         'Worker did not complete this recipe')
    need(type(status.get('io_denials')) is int and status['io_denials']==0
         and status.get('hard_deadline') is False and status.get('references_read') is False
         and status.get('scientific_scoring_performed') is False and status.get('automatic_retry') is False
         and status.get('error') is None,'Worker execution policy did not hold')
    count=status['counts']; n=len(recipe['schedule'])
    expected=dict(scheduled_claims=n,scheduled_pairs=5*n,completed_claims=n,complete_prediction_claims=n,
                  completed_pairs=5*n,input_unavailable_pairs=0,overlength_pairs=0,unexpected_failed_pairs=0)
    need(count==expected and all(type(v) is int for v in count.values()),'Incomplete calibration schedule')
    receipt_path=local_path(root/'RECEIPT.json')
    need(receipt_path.stat().st_size<=8*1024**2,'Worker receipt bound')
    receipt_raw=capture(_proof(receipt_path),8*1024**2)
    receipt=parse_json(receipt_raw)
    need(set(receipt)=={'schema_version','kind','status','recipe_sha256','files'}
         and receipt['schema_version']==1 and receipt['kind']=='sc05_calibration_worker_receipt_v1'
         and receipt['status']=='completed' and receipt['recipe_sha256']==frame['recipe']['sha256'],
         'Worker receipt identity differs')
    observed=_inventory(root,recipe['output_bytes']+8*1024**2)
    need(observed['STATUS.json']==dict(bytes=len(status_raw),sha256=digest(status_raw)) and
         observed['RECEIPT.json']==dict(bytes=len(receipt_raw),sha256=digest(receipt_raw)),
         'Verified worker control bytes changed during capture')
    verified_files=freeze(observed)
    observed.pop('RECEIPT.json')
    paths={name:dict(path=str(root/name),**value) for name,value in observed.items()}
    need(canonical(paths)==canonical(receipt['files']),'Worker receipt inventory differs')
    observed.pop('STATUS.json')
    paths.pop('STATUS.json')
    need(canonical(paths)==canonical(status.get('files')),'Worker status inventory differs')
    return freeze(status),verified_files


def _inventory(root,maximum):
    files={};total=0
    for path in sorted(root.rglob('*')):
        local_path(path)
        if path.is_dir():continue
        need(path.is_file() and len(files)<10000,'Unexpected output file/count')
        size=path.stat().st_size;total+=size
        need(size<=128*1024**2 and total<=maximum,'Calibration output byte bound')
        proof=_proof(path)
        files[path.relative_to(root).as_posix()]={k:proof[k] for k in ('bytes','sha256')}
    return files


def execute(frame_path,expected_sha256,*,output):
    raw,frame_proof,frame,root,limits=load_frame(frame_path,expected_sha256,output)
    journal=RunJournal(root,kind='build')
    started=time.monotonic();stage='pinning';entered=False
    try:
        publish_bytes(root/'FRAME.json',raw)
        for item in (frame['interpreter'],frame['worker'],*frame['code_files']):capture(item)
        recipe_raw=capture(frame['recipe'],1024**2);recipe=parse_json(recipe_raw)
        need(recipe.get('kind')=='sc05_calibration_worker_v1' and recipe.get('purpose')=='calibrate'
             and recipe.get('mode')==frame['mode'],'Worker recipe role differs')
        pins={str(local_path(p['path'])).casefold():p for p in frame['code_files']}
        grants=recipe.get('code_files')
        need(isinstance(grants,list) and grants and all(isinstance(p,dict) and
             canonical(pins.get(str(local_path(p['path'])).casefold()))==canonical(p) for p in grants),
             'Worker source grants lack exact coordinator pins')
        ids=recipe['schedule']
        need(isinstance(ids,list) and ids==sorted(set(ids)) and all(type(i) is int and i>=0 for i in ids)
             and (len(ids)==69 if frame['mode']=='production' else 1<=len(ids)<=8),'Worker calibration schedule')
        need(type(recipe['phase_seconds']) in (int,float) and 0<recipe['phase_seconds']<=limits.timeout_seconds,
             'Worker phase cap exceeds supervisor limit')
        need(type(recipe['output_bytes']) is int and 1<=recipe['output_bytes']<=2*1024**3,'Worker output cap')
        publish_bytes(root/'RECIPE.json',recipe_raw)
        command=[frame['interpreter']['path'],'-I','-B',frame['worker']['path'],
                 '--recipe',frame['recipe']['path'],'--recipe-sha256',frame['recipe']['sha256'],
                 '--output',str(root/'worker')]
        publish_bytes(root/'COMMAND.json',canonical(command))
        journal.append('calibration_worker_reserved',frame_sha256=frame_proof['sha256'],
                       recipe_sha256=frame['recipe']['sha256'],command=command,limits=limits.payload())
        stage='worker';entered=True
        result=supervise_command(command,limits=limits)
        stage='terminal'
        _retain_process(root,result)
        need(result.returncode==0,'Calibration worker returned nonzero')
        validate_success_report(result.supervision,limits,len(result.stdout),len(result.stderr))
        status,worker_files=_worker_status(root/'worker',frame,recipe)
        for item in (frame['interpreter'],frame['worker'],*frame['code_files'],frame['recipe']):capture(item)
        journal.append('calibration_worker_completed',status_sha256=digest(canonical(status)),
                       worker_status_sha256=worker_files['STATUS.json']['sha256'])
        report=dict(schema_version=1,kind=KIND,status='completed',frame=frame_proof,
                    recipe_sha256=frame['recipe']['sha256'],worker_status=status,
                    wall_seconds=time.monotonic()-started,automatic_retry=False,
                    scientific_validation='not_evaluated',provider_cost_usd=0)
        publish_bytes(root/'REPORT.json',canonical(report))
        journal.close()
        # Console and coordinator metadata have their own bounded allowance.
        files=_inventory(root,recipe['output_bytes']+limits.max_output_bytes+8*1024**2)
        need(canonical({name.removeprefix('worker/'):value for name,value in files.items() if name.startswith('worker/')})
             ==canonical(worker_files),'Verified worker output changed before final seal')
        publish_bytes(root/'RECEIPT.json',canonical(dict(status='completed',files=files)))
        return freeze(report)
    except BaseException as error:
        partial=getattr(error,'tether_engine_result',None)
        if partial is not None:
            try:_retain_process(root,partial)
            except BaseException as secondary:error.add_note('Process artifact persistence: '+type(secondary).__name__)
        failure=dict(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',stage=stage,
                     error_type=type(error).__name__,worker_entered=entered,automatic_retry=False,
                     frame_sha256=frame_proof['sha256'],wall_seconds=time.monotonic()-started)
        try:
            publish_bytes(root/'FAILURE.json',canonical(failure))
            if not journal._stream.closed:journal.append('calibration_supervision_failed',**failure)
        except BaseException as secondary:error.add_note('Failure persistence: '+type(secondary).__name__)
        raise
    finally:journal.close()


def _retain_process(root,result):
    for name,raw in (('stdout.bin',result.stdout),('stderr.bin',result.stderr),
                     ('PROCESS.json',canonical(dict(returncode=result.returncode,supervision=result.supervision)))):
        publish_bytes(root/name,raw)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frame',required=True);parser.add_argument('--frame-sha256',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    execute(args.frame,args.frame_sha256,output=args.output)


if __name__=='__main__':main()
