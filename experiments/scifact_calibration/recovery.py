"""Explicit apply-only recovery of a sealed calibration map after failure.

Original attempts remain failed and immutable. Exact externally anchored source,
fit, mapping, journal and terminal-process proofs are checked before reusing the
map. This module never calls a fitting routine or executes archived source.
"""
import argparse
from dataclasses import asdict
from pathlib import Path
import json
import math
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
if __name__=='__main__':sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'packages/tether/src')]

from tether import _process as process
from tether_engine import atomic,journal,serde
from experiments.scifact_calibration import evaluate as e,outcomes as o,calibration as c,statistics as s
from experiments.scifact_calibration.inputs import capture,local_path,need,digest

KIND='sc05_apply_sealed_mapping_v1'
SNAPSHOT='sc05_failed_evaluation_snapshot_v1'
ALLOWED_CHANGED={'experiments/scifact_calibration/outcomes.py','experiments/scifact_calibration/evaluate.py'}


def required_code():
    return tuple(sorted(set(e.required_code())|{Path(__file__).resolve(),Path(process.__file__).resolve()}))


def _json(item,maximum=e.MAX_FILE):return serde.parse_json(capture(item,maximum))
def _same(a,b):return serde.canonical(a)==serde.canonical(b)
def _without(value,*names):return {k:v for k,v in value.items() if k not in names}


def _tree(root,files):
    root=local_path(root)
    need(_same(e._inventory(root,e.MAX_OUTPUT),files),'Immutable parent inventory changed')
    for name,item in files.items():
        o._name(name)
        need(local_path(item['path'])==root/name,'Parent file location differs')
    return root


def _metadata(frame_path,expected,output,*,existing=False):
    anchor=dict(e.proof(frame_path),sha256=expected);frame=_json(anchor,1024**2)
    need(set(frame)=={'schema_version','kind','purpose','evaluation_frame','parent_snapshot','code_files','environment','qualification','output'}
         and frame['schema_version']==1 and frame['kind']==KIND and frame['purpose']=='evaluate','Explicit apply-only recovery authority')
    root=local_path(output)
    need(root==local_path(frame['output']) and root.is_relative_to(ROOT) and root!=ROOT and
         (existing or not root.exists()),'Recovery output must be fresh and owned')
    need(_same(frame['environment'],e.environment()),'Recovery environment differs')
    pins=frame['code_files'];need(isinstance(pins,list) and len(pins)==len({p['path'] for p in pins}) and
         set(required_code())=={local_path(p['path']) for p in pins},'Exact recovery source closure required')
    for item in pins:capture(item,8*1024**2)
    current,_,calibration,development,_=e._controls(frame['evaluation_frame']['path'],frame['evaluation_frame']['sha256'],root,existing=existing)
    need(_same(e.proof(frame['evaluation_frame']['path']),frame['evaluation_frame']),'Recovery evaluation frame bytes differ')
    bypath={p['path']:p for p in pins}
    need(all(_same(bypath.get(p['path']),p) for p in current['code_files']),'Current evaluator source not pinned by recovery')
    if current['mode']=='production':
        qualification=_json(frame['qualification'],1024**2)
        need(qualification['kind']=='sc05_calibration_recovery_qualification_v1' and qualification['status']=='passed' and
             _same(qualification['code_files'],pins) and qualification['actual_recovery_executed'] is False,
             'Current model-free recovery qualification required')
    else:need(frame['qualification'] is None,'Fictional recovery cannot claim production qualification')
    snapshot=_json(frame['parent_snapshot'],8*1024**2)
    need(set(snapshot)=={'schema_version','kind','root','files','original_frame','launch','executed_source','scope'} and
         snapshot['schema_version']==1 and snapshot['kind']==SNAPSHOT,'Exact failed-parent snapshot schema')
    parent=_tree(snapshot['root'],snapshot['files'])
    launch=snapshot['launch'];need(set(launch)=={'root','files'},'Terminal process snapshot fields')
    launch_root=_tree(launch['root'],launch['files'])
    for protected in (parent,launch_root,local_path(frame['parent_snapshot']['path']).parent):
        need(not root.is_relative_to(protected) and not protected.is_relative_to(root),'Recovery output overlaps immutable parent')
    def item(name):return snapshot['files'][name]
    old=_json(item('FRAME.json'),1024**2)
    need(_same(old,_json(snapshot['original_frame'])) and local_path(old['output'])==parent,'Original frame/output binding')
    need(_same(_without(old,'code_files','calibration_frame','development_template','output'),
               _without(current,'code_files','calibration_frame','development_template','output')),
         'Recovery changes scientific evaluation settings')
    for key,child in (('calibration_frame',calibration),('development_template',development)):
        original=_json(old[key],1024**2)
        need(_same(_without(original,'code_files'),_without(child,'code_files')),'Recovery changes scientific input/partition')
    original_pins={p['path']:p for p in old['code_files']};current_pins={p['path']:p for p in current['code_files']}
    need(set(original_pins)==set(current_pins),'Original evaluator closure changed roles')
    archive={}
    for entry in snapshot['executed_source']:
        need(set(entry)=={'original','archived'},'Archived source descriptor')
        before,archived=entry['original'],entry['archived'];path=before['path']
        need(path not in archive and _same(before,original_pins.get(path)),'Complete unique original source pins')
        need((before['bytes'],before['sha256'])==(archived['bytes'],archived['sha256']),'Archived source byte identity')
        need(local_path(archived['path']).is_relative_to(local_path(frame['parent_snapshot']['path']).parent),
             'Archived source must stay with its anchored snapshot')
        capture(archived,8*1024**2);archive[path]=archived
    need(set(archive)==set(original_pins),'Missing executed source archive')
    for path,before in original_pins.items():
        if not _same(before,current_pins[path]):
            relative=local_path(path).relative_to(ROOT).as_posix()
            need(relative in ALLOWED_CHANGED,'Recovery changes fixed optimizer/scorer/statistics code')
    need(set(launch['files'])=={'COMMAND.json','PROCESS.json','stdout.bin','stderr.bin'},'Complete terminal launch capture required')
    terminal=_json(launch['files']['PROCESS.json'])
    need(set(terminal)=={'returncode','supervision'} and type(terminal['returncode']) is int and terminal['returncode']==1,
         'Original evaluation must have a retained failed process exit')
    process.validate_success_report(terminal['supervision'],process.ProcessLimits(old['limits']['phase_seconds']+30,4*1024**2),
        launch['files']['stdout.bin']['bytes'],launch['files']['stderr.bin']['bytes'])
    command=[old['environment']['executable']['path'],'-I','-B',str(ROOT/'experiments/scifact_calibration/evaluate.py'),
        'execute','--frame',snapshot['original_frame']['path'],'--frame-sha256',snapshot['original_frame']['sha256'],'--output',str(parent)]
    need(_same(_json(launch['files']['COMMAND.json']),command),'Original failed invocation differs')
    return frame,anchor,current,calibration,development,snapshot,parent,archive,root


def _adopt(metadata):
    frame,anchor,current,_,template,snapshot,parent,archive,root=metadata
    files=snapshot['files'];values={name:_json(item) for name,item in files.items() if name.endswith('.json')}
    old=values['FRAME.json'];failure=values['FAILURE.json'];events=e._journal(capture(files['journal.jsonl']))
    need('RECEIPT.json' not in files and failure['status']=='failed' and failure['stage']=='development_reconstruction'
         and failure['automatic_retry'] is False and failure['model_calls']==failure['provider_cost_usd']==0,
         'Only a retained post-seal development failure is eligible')
    calibration=o.reconstruct_partition(current['calibration_frame']['path'],current['calibration_frame']['sha256'])
    prior=values['CALIBRATION-INPUTS.json'];rebuilt=e._partition_payload(calibration)
    need(_same(_without(prior,'proofs'),_without(rebuilt,'proofs')),'Original calibration rows or scientific lineage changed')
    # Only current reader code and its explicit child frame may be replaced.
    # Every raw/source/projection proof must still be present on both sides.
    original_pins={p['path']:p for p in old['code_files']};expected_proofs=[]
    for item in rebuilt['proofs']:
        if item['path']==current['calibration_frame']['path']:expected_proofs.append(old['calibration_frame'])
        else:expected_proofs.append(original_pins.get(item['path'],item))
    need(len(prior['proofs'])==len({p['path'] for p in prior['proofs']}) and
         _same(sorted(prior['proofs'],key=lambda p:p['path']),sorted(expected_proofs,key=lambda p:p['path'])),
         'Original and current source proof closure differs')
    for item in prior['proofs']:
        if item['path'] in archive:
            old_pin=next(p for p in old['code_files'] if p['path']==item['path'])
            need(_same(item,old_pin),'Original admitted source proof differs');capture(archive[item['path']],8*1024**2)
        else:capture(item,e.MAX_FILE)
    suite=e._suite(values['CALIBRATION-SUITE.json']);c.validate_suite(suite,calibration.rows)
    groups=(None,)+tuple(sorted(set(calibration.components.values())))
    need(suite.status=='complete' and len(suite.attempts)==len(groups) and
         tuple(g for g,_ in suite.attempts)==groups and all(f.status=='complete' for _,f in suite.attempts),'All original fits must be complete')
    need(type(suite.elapsed_seconds) in (int,float) and math.isfinite(suite.elapsed_seconds) and
         sum(f.elapsed_seconds for _,f in suite.attempts)<=suite.elapsed_seconds<=c.FIT_SECONDS*len(groups),'Original optimizer time accounting')
    need(_same(values['MAPPING.json'],suite.main.payload()),'Sealed map differs from original completed fits')
    seal=values['MAPPING-RECEIPT.json']
    expected_seal=dict(schema_version=1,kind='sc05_mapping_seal_v1',status='complete',parent_frame=snapshot['original_frame'],
        mapping=files['MAPPING.json'],map_fingerprint=suite.main.fingerprint,suite=files['CALIBRATION-SUITE.json'],
        inputs=files['CALIBRATION-INPUTS.json'],fits=len(groups),code_files=old['code_files'],environment=old['environment'])
    need(_same(seal,expected_seal) and _same(values['ENVIRONMENT.json'],old['environment']),'Original mapping seal identity')
    expected_events=['build_reserved','evaluation_configured','calibration_inputs_admitted']
    need(_same(events[1]['details'],dict(frame=snapshot['original_frame'],limits=old['limits'],automatic_retry=False)) and
         _same(events[2]['details'],dict(cases=len(calibration.ids),components=len(groups)-1)),'Original calibration admission journal')
    for ordinal,(omitted,fit) in enumerate(suite.attempts):
        expected_events+=['fit_reserved','fit_accounted']
        training=tuple(r for r in calibration.rows if calibration.components[r.id]!=omitted)
        reserved=f'fits/{ordinal:03d}-reserved.json';result=f'fits/{ordinal:03d}-result.json'
        need(_same(values[reserved],dict(ordinal=ordinal,omitted_component=omitted,training_ids=[r.id for r in training],
             input_sha256=c.digest([asdict(r) for r in training]),seconds=c.FIT_SECONDS,max_updates=c.MAX_UPDATES)) and
             _same(values[result],dict(ordinal=ordinal,omitted_component=omitted,fit=asdict(fit))),'Original fit artifact binding')
        need(_same(events[3+2*ordinal]['details'],dict(ordinal=ordinal,omitted_component=omitted,reservation=files[reserved])) and
             _same(events[4+2*ordinal]['details'],dict(ordinal=ordinal,status=fit.status,result=files[result])),'Original fit journal binding')
    need(_same(values['FIT-SCHEDULE.json'],dict(ids=calibration.ids,components=[[i,calibration.components[i]] for i in calibration.ids],
        fits=groups,constants=c.CONSTANTS,total_optimizer_seconds=c.FIT_SECONDS*len(groups))),'Original complete fit schedule')
    old_template=_json(old['development_template']);old_derived=dict(old_template,sealed_mapping=files['MAPPING.json'])
    need(_same(values['DEVELOPMENT-FRAME.json'],old_derived),'Original development authority differs')
    expected_events+=['mapping_sealed','development_open_authorized','build_failed']
    need([r['event'] for r in events]==expected_events,'Original seal must precede development and terminal failure')
    details=[dict(mapping_receipt=files['MAPPING-RECEIPT.json'],map_fingerprint=suite.main.fingerprint),
        dict(mapping_receipt_sha256=files['MAPPING-RECEIPT.json']['sha256'],derived_frame=files['DEVELOPMENT-FRAME.json'],template=old['development_template']),
        dict(error_class=failure['error_type'],message=failure['message'],stage=failure['stage'])]
    need(all(_same(row['details'],d) for row,d in zip(events[-3:],details)),'Original terminal journal details')
    need(failure['calibration_cases']==len(calibration.ids) and failure['fits_accounted']==len(groups)
         and type(failure['wall_seconds']) in (int,float) and math.isfinite(failure['wall_seconds'])
         and suite.elapsed_seconds<=failure['wall_seconds']<=old['limits']['phase_seconds'],'Original failed attempt accounting')
    fixed={'FRAME.json','ENVIRONMENT.json','CALIBRATION-INPUTS.json','FIT-SCHEDULE.json','CALIBRATION-SUITE.json',
           'MAPPING.json','MAPPING-RECEIPT.json','DEVELOPMENT-FRAME.json','FAILURE.json','journal.jsonl'}
    need(set(files)==fixed|{f'fits/{i:03d}-{suffix}.json' for i in range(len(groups)) for suffix in ('reserved','result')},
         'Unexplained failed-parent artifacts')
    adoption=dict(kind='sc05_sealed_mapping_adoption_v1',parent_snapshot=frame['parent_snapshot'],original_frame=snapshot['original_frame'],
        mapping=files['MAPPING.json'],mapping_receipt=files['MAPPING-RECEIPT.json'],map_fingerprint=suite.main.fingerprint,
        original_fits_reused=len(groups),new_fits=0,source_consistency=True,stationarity_recomputed=True,
        original_failure=files['FAILURE.json'],original_process=snapshot['launch']['files']['PROCESS.json'],
        original_attempt_remains_failed=True,archived_code_executed=False)
    return calibration,suite,adoption


def _recheck(metadata):
    frame,anchor,current,_,_,snapshot,_,archive,_=metadata
    _tree(snapshot['root'],snapshot['files']);_tree(snapshot['launch']['root'],snapshot['launch']['files'])
    for item in (anchor,frame['parent_snapshot'],frame['evaluation_frame'],*frame['code_files'],*archive.values()):capture(item,e.MAX_FILE)
    original=_json(snapshot['original_frame'])
    for item in (original['calibration_frame'],original['development_template']):capture(item,e.MAX_FILE)
    if frame['qualification'] is not None:capture(frame['qualification'])


def execute(frame_path,expected,*,output,_clock=time.monotonic):
    metadata=_metadata(frame_path,expected,output)
    frame,anchor,current,_,template,snapshot,parent,archive,root=metadata
    events=journal.RunJournal(root,kind='build');writer=e._Writer(root,current['limits']['output_bytes'])
    start=_clock();end=start+current['limits']['phase_seconds'];stage='sealed_fit_verification'
    def bounded():need(_clock()<end,'Recovery phase deadline exceeded')
    try:
        writer.write('FRAME.json',frame)
        events.append('recovery_configured',frame=anchor,limits=current['limits'],new_fits=0,automatic_retry=False)
        bounded();calibration,suite,adoption=_adopt(metadata);bounded()
        writer.write('CALIBRATION-INPUTS.json',e._partition_payload(calibration));adopted=writer.write('ADOPTION.json',adoption)
        events.append('sealed_fit_adopted',adoption=adopted,new_fits=0)
        stage='development_reconstruction';derived=dict(template,sealed_mapping=snapshot['files']['MAPPING.json'])
        derived_proof=writer.write('DEVELOPMENT-FRAME.json',derived)
        events.append('development_open_authorized',mapping=adoption['mapping'],derived_frame=derived_proof,template=current['development_template'])
        development=o.reconstruct_partition(derived_proof['path'],derived_proof['sha256']);bounded()
        need(not set(calibration.components.values())&set(development.components.values()),'Recovery partition overlap')
        writer.write('DEVELOPMENT-INPUTS.json',e._partition_payload(development))
        stage='fixed_statistics';reports=e._reports(calibration,development,suite,purpose=current['mode']);bounded()
        for name,value in reports.items():writer.write(name.upper().replace('_','-')+'.json',value)
        events.append('statistics_completed',development_cases=len(development.ids),bootstrap_replicates=s.REPLICATES)
        stage='finalization';_recheck(metadata)
        for item in (*calibration.proofs,*development.proofs):capture(item,e.MAX_FILE)
        bounded();report=dict(schema_version=1,kind=KIND,status='complete',frame=anchor,adoption=adopted,
            calibration_cases=len(calibration.ids),development_cases=len(development.ids),original_fits_reused=len(suite.attempts),
            new_fits=0,model_calls=0,provider_cost_usd=0,bootstrap_replicates=s.REPLICATES,wall_seconds=_clock()-start,
            automatic_retry=False,original_attempt_remains_failed=True,scientific_validation='benchmark_endpoint_only')
        final=writer.write('REPORT.json',report);events.append('recovery_completed',report=final);events.close()
        inventory=e._inventory(root,current['limits']['output_bytes']);bounded()
        atomic.publish_bytes(root/'RECEIPT.json',serde.canonical(dict(schema_version=1,kind=KIND,status='complete',frame_sha256=expected,files=inventory))+b'\n')
        return serde.freeze(report)
    except BaseException as error:
        failure=dict(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',stage=stage,error_type=type(error).__name__,
            message=str(error)[:2000],new_fits=0,model_calls=0,provider_cost_usd=0,automatic_retry=False,wall_seconds=_clock()-start)
        try:
            atomic.publish_bytes(root/'FAILURE.json',serde.canonical(failure)+b'\n')
            if not events._stream.closed:events.fail(error,stage)
        except BaseException as secondary:error.add_note('Recovery failure retention: '+type(secondary).__name__)
        raise
    finally:events.close()


def verify(output,receipt_sha256):
    root=local_path(output);anchor=dict(e.proof(root/'RECEIPT.json'),sha256=receipt_sha256);receipt=_json(anchor)
    need(set(receipt)=={'schema_version','kind','status','frame_sha256','files'} and receipt['kind']==KIND and
         receipt['status']=='complete' and not (root/'FAILURE.json').exists(),'Completed recovery receipt required')
    actual=e._inventory(root,e.MAX_OUTPUT);actual.pop('RECEIPT.json')
    need(_same(actual,receipt['files']),'Recovery exact inventory differs')
    values={name:_json(item) for name,item in actual.items() if name.endswith('.json')}
    report=values['REPORT.json'];frame_proof=report['frame']
    metadata=_metadata(frame_proof['path'],receipt['frame_sha256'],root,existing=True)
    frame,_,current,_,template,snapshot,_,_,_=metadata
    need(_same(frame_proof,e.proof(frame_proof['path'])) and _same(values['FRAME.json'],frame),'Retained recovery frame differs')
    calibration,suite,adoption=_adopt(metadata)
    need(_same(values['ADOPTION.json'],adoption) and _same(values['CALIBRATION-INPUTS.json'],e._partition_payload(calibration)),'Original-fit adoption reconstruction differs')
    derived=dict(template,sealed_mapping=snapshot['files']['MAPPING.json'])
    need(_same(values['DEVELOPMENT-FRAME.json'],derived),'Recovered development authority differs')
    development=o.reconstruct_partition(actual['DEVELOPMENT-FRAME.json']['path'],actual['DEVELOPMENT-FRAME.json']['sha256'])
    need(not set(calibration.components.values())&set(development.components.values()) and
         _same(values['DEVELOPMENT-INPUTS.json'],e._partition_payload(development)),'Recovered development inputs differ')
    reports=e._reports(calibration,development,suite,purpose=current['mode'])
    for name,value in reports.items():
        observed=values[name.upper().replace('_','-')+'.json']
        if name=='bootstrap':
            need(type(observed['wall_seconds']) in (int,float) and math.isfinite(observed['wall_seconds']) and observed['wall_seconds']>=0,'Recovery bootstrap time')
            value=dict(value,wall_seconds=observed['wall_seconds'])
        need(_same(observed,value),'Recovered deterministic statistics differ')
    events=e._journal(capture(actual['journal.jsonl']))
    need([r['event'] for r in events]==['build_reserved','recovery_configured','sealed_fit_adopted','development_open_authorized',
         'statistics_completed','recovery_completed'],'Recovery journal ordering differs')
    details=[dict(frame=frame_proof,limits=current['limits'],new_fits=0,automatic_retry=False),dict(adoption=actual['ADOPTION.json'],new_fits=0),
        dict(mapping=adoption['mapping'],derived_frame=actual['DEVELOPMENT-FRAME.json'],template=current['development_template']),
        dict(development_cases=len(development.ids),bootstrap_replicates=s.REPLICATES),dict(report=actual['REPORT.json'])]
    need(all(_same(row['details'],value) for row,value in zip(events[1:],details)),'Recovery journal artifact binding')
    expected=dict(schema_version=1,kind=KIND,status='complete',frame=frame_proof,adoption=actual['ADOPTION.json'],
        calibration_cases=len(calibration.ids),development_cases=len(development.ids),original_fits_reused=len(suite.attempts),
        new_fits=0,model_calls=0,provider_cost_usd=0,bootstrap_replicates=s.REPLICATES,wall_seconds=report['wall_seconds'],
        automatic_retry=False,original_attempt_remains_failed=True,scientific_validation='benchmark_endpoint_only')
    need(_same(report,expected) and type(report['wall_seconds']) in (int,float) and math.isfinite(report['wall_seconds']) and
         values['BOOTSTRAP.json']['wall_seconds']<=report['wall_seconds']<current['limits']['phase_seconds'],'Recovery terminal accounting')
    need(set(actual)=={'FRAME.json','CALIBRATION-INPUTS.json','ADOPTION.json','DEVELOPMENT-FRAME.json','DEVELOPMENT-INPUTS.json',
         'ANALYSIS-ROWS.json','POINT-SUMMARY.json','BOOTSTRAP.json','HELD-OUT.json','SENSITIVITY.json','REPORT.json','journal.jsonl'},
         'Unexplained recovery artifact')
    _recheck(metadata)
    for item in (*calibration.proofs,*development.proofs,*actual.values(),anchor):capture(item,e.MAX_FILE)
    return serde.freeze(dict(status='verified',byte_integrity=True,source_consistency=True,arithmetic_consistency=True,
        original_fits_reused=len(suite.attempts),new_fits=0,model_calls=0,original_attempt_remains_failed=True,
        independent_biological_validation=False,receipt=anchor))


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    execute_parser=commands.add_parser('execute');execute_parser.add_argument('--frame',required=True)
    execute_parser.add_argument('--frame-sha256',required=True);execute_parser.add_argument('--output',required=True)
    verify_parser=commands.add_parser('verify');verify_parser.add_argument('--output',required=True);verify_parser.add_argument('--receipt-sha256',required=True)
    args=parser.parse_args();result=execute(args.frame,args.frame_sha256,output=args.output) if args.command=='execute' else verify(args.output,args.receipt_sha256)
    print(json.dumps(serde.encode(result),sort_keys=True))


if __name__=='__main__':main()
