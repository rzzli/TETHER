"""Sequential, model-free SC05 calibration and retained-development evaluation.

The external frame freezes inputs, code, environment and limits. All calibration
fits must complete before a mapping is sealed and any development outcomes are
opened. Verification reconstructs source and arithmetic, never fits or dispatches.
"""
import argparse
from collections import Counter
from dataclasses import asdict
import json
import math
from pathlib import Path
import platform
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
if __name__=='__main__':
    # -I deliberately ignores PYTHONPATH. Use the same explicit repository
    # runtime as the frame-authoring controller, without mixing installed and
    # source module identities in the externally pinned code closure.
    sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'packages/tether/src')]

import tether_engine
from tether_engine import atomic, journal, serde
from experiments.scifact_calibration import calibration as c, outcomes, statistics as s
from experiments.scifact_calibration.inputs import capture, digest, local_path, need

KIND='sc05_calibration_evaluation_v1'
MAX_FILE=64*1024**2
MAX_OUTPUT=256*1024**2


def proof(path):
    path=local_path(path);size=path.stat().st_size;need(size<=MAX_FILE,'Control artifact exceeds bound')
    with path.open('rb') as stream:raw=stream.read(MAX_FILE+1)
    need(len(raw)==size,'Artifact changed during capture')
    return dict(path=str(path),bytes=len(raw),sha256=digest(raw))


def environment():
    return dict(python=sys.version,implementation=platform.python_implementation(),
        executable=proof(Path(sys.executable)),engine_version=tether_engine.__version__,float_mantissa=sys.float_info.mant_dig)


def required_code():
    return tuple(sorted({Path(module.__file__).resolve() for module in
        (sys.modules[__name__],c,outcomes,s,sys.modules['experiments.scifact_calibration.inputs'],atomic,journal,serde)}|
        {ROOT/'experiments/scifact/evaluate.py',ROOT/'experiments/scifact/native_contract.py'}))


def _json(proof_value,maximum=MAX_FILE):return serde.parse_json(capture(proof_value,maximum))
def _same(left,right):return serde.canonical(left)==serde.canonical(right)


def _controls(frame_path,external_sha,output,*,existing=False):
    path=local_path(frame_path);anchor=dict(path=str(path),bytes=path.stat().st_size,sha256=external_sha)
    frame=_json(anchor,1024**2)
    fields={'schema_version','kind','purpose','mode','calibration_frame','development_template','code_files','environment','limits','output'}
    need(set(frame)==fields and type(frame['schema_version']) is int and frame['schema_version']==1 and frame['kind']==KIND and
         frame['purpose']=='evaluate' and frame['mode'] in ('production','fictional_qualification'),'Explicit evaluation frame required')
    root=local_path(output);need(root==local_path(frame['output']) and root.is_relative_to(ROOT) and root!=ROOT,'Fresh owned output differs')
    need(existing or not root.exists(),'Output exists; never automatically repeat evaluation')
    limits=frame['limits'];need(set(limits)=={'phase_seconds','output_bytes'} and type(limits['phase_seconds']) in (int,float) and
         math.isfinite(limits['phase_seconds']) and 0<limits['phase_seconds']<=14400 and type(limits['output_bytes']) is int and
         1<=limits['output_bytes']<=MAX_OUTPUT,'Bounded evaluation limits required')
    need(_same(frame['environment'],environment()),'Executing environment differs from frozen frame')
    code=frame['code_files'];need(isinstance(code,list) and code and len({p['path'] for p in code})==len(code) and
         set(required_code())<={local_path(p['path']) for p in code},'Complete evaluator source closure required')
    for item in code:capture(item,8*1024**2)
    calibration=_json(frame['calibration_frame'],1024**2);development=_json(frame['development_template'],1024**2)
    pins={local_path(p['path']):p for p in code};protected=[];input_files=[anchor,frame['calibration_frame'],frame['development_template'],*code]
    for child,partition in ((calibration,'calibration'),(development,'dev')):
        need(child['kind']==outcomes.KIND and child['purpose']=='evaluate' and child['partition']==partition and
             child['mode']==frame['mode'] and child['sealed_mapping'] is None and child['policy']==outcomes.POLICY,'Outcome child role/template differs')
        need(all(_same(pins.get(local_path(p['path'])),p) for p in child['code_files']),'Child reader code lacks exact parent pin')
        producer=child['producer'];protected.append(local_path(producer['root']))
        transition=_json(child['preparation_transition'],1024**2)
        input_files.extend([child['preparation_transition'],producer['receipt'],producer['recipe'],producer['requests'],producer['retrieval']])
        input_files.extend(transition[k] for k in ('manifest','archive','acquisition','archive_receipt','journal','build_report'))
        protected.append(local_path(transition['manifest']['path']).parent)
        if producer['admission'] is not None:
            input_files.extend(producer['admission'].values());protected.append(local_path(producer['admission']['receipt']['path']).parent)
    need(calibration['preparation_transition']==development['preparation_transition'],'Calibration/development source release differs')
    need(not set(calibration['expected_ids'])&set(development['expected_ids']),'Calibration/development identity overlap')
    if frame['mode']=='production':need(len(calibration['expected_ids'])==69 and len(development['expected_ids'])==300,'Full frozen69/300 schedule required')
    for item in input_files:
        source=local_path(item['path']);need(not source.is_relative_to(root),'Output would contain/replace an immutable input')
    need(all(not root.is_relative_to(source) and not source.is_relative_to(root) for source in protected),'Output overlaps original producer/preparation roots')
    return frame,anchor,calibration,development,root


class _Writer:
    def __init__(self,root,maximum):self.root=root;self.maximum=maximum;self.total=0
    def write(self,name,value):
        outcomes._name(name);raw=serde.canonical(serde.encode(value))+b'\n'
        need(len(raw)<=MAX_FILE and self.total+len(raw)<=self.maximum,'Evaluation output byte budget exceeded')
        target=self.root/name;target.parent.mkdir(parents=True,exist_ok=True)
        atomic.publish_bytes(target,raw);self.total+=len(raw)
        return dict(path=str(target),bytes=len(raw),sha256=digest(raw))


def _suite_payload(suite):
    return dict(schema_version=1,kind='sc05_complete_calibration_suite_v1',status=suite.status,reason=suite.reason,
        main=suite.main.payload() if suite.main else None,
        deletion_maps=[[group,mapping.payload()] for group,mapping in suite.deletion_maps],
        held_out_scores=suite.held_out_scores,attempts=[[group,asdict(fit)] for group,fit in suite.attempts],
        coefficient_ranges=suite.coefficient_ranges,elapsed_seconds=suite.elapsed_seconds,
        case_statuses=suite.case_statuses,component_assignments=suite.component_assignments)


def _suite(value):
    need(value['schema_version']==1 and value['kind']=='sc05_complete_calibration_suite_v1','Suite artifact identity')
    def mapping(p):return c.mapping_from_payload(p,expected_fingerprint=c.digest(p))
    return c.CalibrationSuite(value['status'],value['reason'],mapping(value['main']) if value['main'] else None,
        tuple((g,mapping(p)) for g,p in value['deletion_maps']),tuple(tuple(row) for row in value['held_out_scores']),
        tuple((g,c.FitResult(**p)) for g,p in value['attempts']),tuple(tuple(row) for row in value['coefficient_ranges']),
        value['elapsed_seconds'],tuple(tuple(row) for row in value['case_statuses']),tuple(tuple(row) for row in value['component_assignments']))


def _partition_payload(partition):
    return dict(schema_version=1,kind='sc05_evaluator_partition_v1',partition=partition.partition,
        ids=partition.ids,components=[[i,partition.components[i]] for i in partition.ids],rows=[asdict(row) for row in partition.rows],
        cases=partition.cases,proofs=tuple(sorted(partition.proofs,key=lambda value:value['path'])),
        coverage=partition.coverage,mapping_fingerprint=partition.mapping_fingerprint)


def _fit_partition(partition,writer,events,*,purpose,clock,deadline):
    rows,ids,groups=partition.rows,partition.ids,partition.components;unique=tuple(sorted(set(groups.values())))
    need(tuple(r.id for r in rows)==ids and set(groups)==set(ids) and len(unique)>=2,'Complete calibration fit schedule')
    if purpose=='production':need(len(ids)==69 and len(unique)==49 and Counter(Counter(groups.values()).values())=={1:32,2:15,3:1,4:1},'Full69/49 calibration fit required')
    for row in rows:c._validate_calibration_row(row)
    schedule=(None,)+unique;writer.write('FIT-SCHEDULE.json',dict(ids=ids,components=[[i,groups[i]] for i in ids],fits=schedule,
        constants=c.CONSTANTS,total_optimizer_seconds=c.FIT_SECONDS*len(schedule)))
    started=clock();attempts=[];maps=[];held={}
    def fit_clock():
        now=clock();need(now<=min(deadline,started+c.FIT_SECONDS*len(schedule)),
                         'Evaluation phase/optimizer deadline exceeded during fit');return now
    for ordinal,omitted in enumerate(schedule):
        training=tuple(r for r in rows if groups[r.id]!=omitted)
        reservation=writer.write(f'fits/{ordinal:03d}-reserved.json',dict(ordinal=ordinal,omitted_component=omitted,
            training_ids=[r.id for r in training],input_sha256=c.digest([asdict(r) for r in training]),seconds=c.FIT_SECONDS,max_updates=c.MAX_UPDATES))
        events.append('fit_reserved',ordinal=ordinal,omitted_component=omitted,reservation=reservation)
        if clock()>deadline or clock()-started>c.FIT_SECONDS*len(schedule):
            fit=c.FitResult('unexecuted','Fixed evaluation/optimizer deadline exceeded',None,None,None,None,0,None,0.,False,False,False)
        else:fit=c.fit_coefficients(tuple(r.confidence.logit for r in training),tuple(r.strict_success for r in training),clock=fit_clock)
        attempts.append((omitted,fit));result=writer.write(f'fits/{ordinal:03d}-result.json',dict(ordinal=ordinal,omitted_component=omitted,fit=asdict(fit)))
        events.append('fit_accounted',ordinal=ordinal,status=fit.status,result=result)
        if fit.status!='complete':continue
        mapping=c.FittedMap(fit.a,fit.b,tuple(r.id for r in training),c.digest(tuple(r.confidence.logit for r in training)),
            c.digest(tuple(r.strict_success for r in training)),c.digest([(r.id,groups[r.id]) for r in training]),
            c.digest([asdict(r) for r in training]),fit)
        maps.append((omitted,mapping))
        if omitted is not None:
            held.update((r.id,c.apply_mapping(mapping,r.confidence.score,expected_fingerprint=mapping.fingerprint)) for r in rows if groups[r.id]==omitted)
    complete=len(attempts)==len(schedule) and all(fit.status=='complete' for _,fit in attempts)
    deleted=tuple(maps[1:]) if complete else ()
    suite=c.CalibrationSuite('complete' if complete else 'incomplete',None if complete else 'One or more fixed fits incomplete',
        maps[0][1] if complete else None,deleted,tuple((i,held[i]) for i in ids) if complete else (),tuple(attempts),
        tuple((name,min(getattr(m,name) for _,m in deleted),max(getattr(m,name) for _,m in deleted)) for name in ('a','b')) if complete else (),
        clock()-started,tuple((r.id,r.confidence.status) for r in rows),tuple((i,groups[i]) for i in ids))
    writer.write('CALIBRATION-SUITE.json',_suite_payload(suite))
    need(complete,'All fixed main/deletion fits must complete; no map or development evaluation authorized')
    need(math.isfinite(suite.elapsed_seconds) and 0<=suite.elapsed_seconds<=c.FIT_SECONDS*len(schedule),'Total optimizer elapsed bound')
    c.validate_suite(suite,rows)
    return suite


def _analysis_rows(development,mapping):
    return tuple(s.AnalysisRow(r.id,r.confidence.score,c.apply_mapping(mapping,r.confidence.score,
        expected_fingerprint=mapping.fingerprint),r.produced,r.admitted,r.strict_success) for r in development.rows)


def _reports(calibration,development,suite,*,purpose):
    rows=_analysis_rows(development,suite.main)
    return dict(analysis_rows=[asdict(row) for row in rows],
        point_summary=s.point_summary(rows,development.ids,development.components,purpose=purpose),
        bootstrap=s.paired_bootstrap(rows,development.ids,development.components,purpose=purpose),
        held_out=s.held_out_summary(calibration.rows,suite,purpose='calibration_diagnostic' if purpose=='production' else purpose),
        sensitivity=s.deletion_sensitivity(rows,development.ids,development.components,suite,calibration_rows=calibration.rows,purpose=purpose))


def _inventory(root,maximum):
    found={};total=0
    for path in sorted(root.rglob('*')):
        local_path(path)
        if path.is_dir():continue
        need(path.is_file() and len(found)<512,'Unexpected evaluator artifact/count')
        item=proof(path);total+=item['bytes'];need(total<=maximum,'Final output byte bound')
        found[path.relative_to(root).as_posix()]=item
    return found


def execute(frame_path,external_sha,*,output,_clock=time.monotonic):
    frame,anchor,calibration_frame,template,root=_controls(frame_path,external_sha,output)
    events=journal.RunJournal(root,kind='build');writer=_Writer(root,frame['limits']['output_bytes'])
    started=_clock();deadline=started+frame['limits']['phase_seconds'];stage='calibration_reconstruction';suite=None;calibration=None
    def bounded():need(_clock()<=deadline,'Evaluation phase deadline exceeded')
    try:
        writer.write('FRAME.json',frame);writer.write('ENVIRONMENT.json',environment())
        events.append('evaluation_configured',frame=anchor,limits=frame['limits'],automatic_retry=False)
        bounded();calibration=outcomes.reconstruct_partition(frame['calibration_frame']['path'],frame['calibration_frame']['sha256'])
        writer.write('CALIBRATION-INPUTS.json',_partition_payload(calibration))
        events.append('calibration_inputs_admitted',cases=len(calibration.ids),components=len(set(calibration.components.values())))
        stage='fixed_fits';bounded();suite=_fit_partition(calibration,writer,events,purpose=frame['mode'],clock=_clock,deadline=deadline)
        bounded();stage='mapping_seal'
        for item in frame['code_files']:capture(item,8*1024**2)
        map_proof=writer.write('MAPPING.json',suite.main.payload())
        seal=writer.write('MAPPING-RECEIPT.json',dict(schema_version=1,kind='sc05_mapping_seal_v1',status='complete',
            parent_frame=anchor,mapping=map_proof,map_fingerprint=suite.main.fingerprint,
            suite=proof(root/'CALIBRATION-SUITE.json'),inputs=proof(root/'CALIBRATION-INPUTS.json'),
            fits=len(suite.attempts),code_files=frame['code_files'],environment=frame['environment']))
        events.append('mapping_sealed',mapping_receipt=seal,map_fingerprint=suite.main.fingerprint)
        stage='development_reconstruction';bounded()
        dev_frame=serde.encode(template);dev_frame['sealed_mapping']=map_proof
        derived=writer.write('DEVELOPMENT-FRAME.json',dev_frame)
        events.append('development_open_authorized',mapping_receipt_sha256=seal['sha256'],derived_frame=derived,
                      template=frame['development_template'])
        development=outcomes.reconstruct_partition(derived['path'],derived['sha256'])
        need(not set(calibration.components.values())&set(development.components.values()),'Calibration/development source-component overlap')
        writer.write('DEVELOPMENT-INPUTS.json',_partition_payload(development))
        stage='fixed_statistics';bounded();reports=_reports(calibration,development,suite,purpose=frame['mode']);bounded()
        for name,value in reports.items():writer.write(name.upper().replace('_','-')+'.json',value)
        events.append('statistics_completed',development_cases=len(development.ids),bootstrap_replicates=reports['bootstrap']['completed_replicates'])
        stage='finalization'
        # Revalidate immutable inputs without re-reading outcome values or fitting.
        for item in (*calibration.proofs,*development.proofs,*frame['code_files'],anchor):capture(item,MAX_FILE)
        bounded();report=dict(schema_version=1,kind=KIND,status='complete',frame=anchor,mapping_receipt=seal,
            calibration_cases=len(calibration.ids),calibration_components=len(set(calibration.components.values())),fits=len(suite.attempts),
            development_cases=len(development.ids),development_components=len(set(development.components.values())),
            bootstrap_replicates=reports['bootstrap']['completed_replicates'],wall_seconds=_clock()-started,
            provider_cost_usd=0,model_calls=0,automatic_retry=False,scientific_validation='benchmark_endpoint_only',
            uncertainty_scope='Conditional bootstrap; deletion ranges are sensitivity, not confidence intervals.')
        report_proof=writer.write('REPORT.json',report);events.append('evaluation_completed',report=report_proof);events.close()
        files=_inventory(root,frame['limits']['output_bytes']);bounded();atomic.publish_bytes(root/'RECEIPT.json',serde.canonical(dict(
            schema_version=1,kind=KIND,status='complete',frame_sha256=external_sha,files=files))+b'\n')
        return serde.freeze(report)
    except BaseException as error:
        failure=dict(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',stage=stage,error_type=type(error).__name__,
            message=str(error)[:2000],automatic_retry=False,model_calls=0,provider_cost_usd=0,wall_seconds=_clock()-started,
            calibration_cases=None if calibration is None else len(calibration.ids),fits_accounted=None if suite is None else len(suite.attempts))
        try:
            atomic.publish_bytes(root/'FAILURE.json',serde.canonical(failure)+b'\n')
            if not events._stream.closed:events.fail(error,stage)
        except BaseException as secondary:error.add_note('Failure retention: '+type(secondary).__name__)
        raise
    finally:events.close()


def _journal(raw):
    need(raw.endswith(b'\n'),'Truncated evaluation journal');events=[];previous=None
    for line in raw.splitlines():
        row=serde.parse_json(line);sha=row.pop('sha256')
        need(type(row['sequence']) is int and row['sequence']==len(events) and row['previous_sha256']==previous and
             digest(serde.canonical(row))==sha,'Evaluation journal chain differs')
        previous=sha;row['sha256']=sha;events.append(row)
    return events


def verify(output,receipt_sha256):
    """Source-inclusive deterministic arithmetic reconstruction; never refit.

    A source audit and the independently coded strict outcome reader precede
    arithmetic replay. Reusing the qualified statistics functions is not claimed
    to be a separately implemented statistical oracle or clinical validation.
    """
    root=local_path(output);receipt_proof=dict(proof(root/'RECEIPT.json'),sha256=receipt_sha256);receipt=_json(receipt_proof,8*1024**2)
    need(set(receipt)=={'schema_version','kind','status','frame_sha256','files'} and receipt['kind']==KIND and receipt['status']=='complete','Completed evaluation receipt required')
    need(not (root/'FAILURE.json').exists(),'Failure marker dominates apparent completion')
    actual=_inventory(root,MAX_OUTPUT);actual.pop('RECEIPT.json')
    need(_same(actual,receipt['files']),'Evaluation inventory differs')
    values={name:_json(item) for name,item in actual.items() if name.endswith('.json')}
    report=values['REPORT.json'];frame_anchor=report['frame']
    frame,anchor,_,template,_=_controls(frame_anchor['path'],receipt['frame_sha256'],root,existing=True)
    need(_same(values['FRAME.json'],frame) and _same(anchor,frame_anchor) and _same(values['ENVIRONMENT.json'],frame['environment']),'Retained control/environment differs')
    events=_journal(capture(actual['journal.jsonl']))
    need(events and events[0]['event']=='build_reserved' and events[-1]['event']=='evaluation_completed' and
         not any(e['event'] in ('build_failed','build_interrupted') for e in events),'Evaluation did not complete cleanly')
    calibration=outcomes.reconstruct_partition(frame['calibration_frame']['path'],frame['calibration_frame']['sha256'])
    need(_same(values['CALIBRATION-INPUTS.json'],_partition_payload(calibration)),'Calibration source/row reconstruction differs')
    suite=_suite(values['CALIBRATION-SUITE.json']);c.validate_suite(suite,calibration.rows)
    need(type(suite.elapsed_seconds) in (int,float) and math.isfinite(suite.elapsed_seconds) and
         sum(fit.elapsed_seconds for _,fit in suite.attempts)<=suite.elapsed_seconds<=c.FIT_SECONDS*len(suite.attempts),
         'Optimizer elapsed accounting differs')
    need(_same(values['MAPPING.json'],suite.main.payload()),'Sealed map differs from completed suite')
    seal=values['MAPPING-RECEIPT.json'];expected_seal=dict(schema_version=1,kind='sc05_mapping_seal_v1',status='complete',parent_frame=anchor,
        mapping=actual['MAPPING.json'],map_fingerprint=suite.main.fingerprint,suite=actual['CALIBRATION-SUITE.json'],inputs=actual['CALIBRATION-INPUTS.json'],
        fits=len(suite.attempts),code_files=frame['code_files'],environment=frame['environment'])
    need(_same(seal,expected_seal) and _same(report['mapping_receipt'],actual['MAPPING-RECEIPT.json']),'Mapping seal binding differs')
    dev_frame=serde.encode(template);dev_frame['sealed_mapping']=actual['MAPPING.json']
    need(_same(values['DEVELOPMENT-FRAME.json'],dev_frame),'Development frame changed frozen template')
    development=outcomes.reconstruct_partition(actual['DEVELOPMENT-FRAME.json']['path'],actual['DEVELOPMENT-FRAME.json']['sha256'])
    need(not set(calibration.components.values())&set(development.components.values()) and
         _same(values['DEVELOPMENT-INPUTS.json'],_partition_payload(development)),'Development source/row reconstruction differs')
    reports=_reports(calibration,development,suite,purpose=frame['mode'])
    for name,expected in reports.items():
        observed=values[name.upper().replace('_','-')+'.json']
        if name=='bootstrap':
            need(type(observed['wall_seconds']) in (int,float) and math.isfinite(observed['wall_seconds']) and observed['wall_seconds']>=0,'Bootstrap elapsed time')
            expected=dict(expected,wall_seconds=observed['wall_seconds'])
        need(_same(observed,expected),'Recomputed fixed statistics differ: '+name)
    expected_events=['build_reserved','evaluation_configured','calibration_inputs_admitted']
    groups=(None,)+tuple(sorted(set(calibration.components.values())))
    for ordinal,(omitted,fit) in enumerate(suite.attempts):
        expected_events+=['fit_reserved','fit_accounted'];training=tuple(r for r in calibration.rows if calibration.components[r.id]!=omitted)
        reserved=values[f'fits/{ordinal:03d}-reserved.json'];result=values[f'fits/{ordinal:03d}-result.json']
        need(_same(reserved,dict(ordinal=ordinal,omitted_component=omitted,training_ids=[r.id for r in training],
             input_sha256=c.digest([asdict(r) for r in training]),seconds=c.FIT_SECONDS,max_updates=c.MAX_UPDATES)) and
             _same(result,dict(ordinal=ordinal,omitted_component=omitted,fit=asdict(fit))),'Fit reservation/result differs')
        need(_same(events[3+2*ordinal]['details'],dict(ordinal=ordinal,omitted_component=omitted,reservation=actual[f'fits/{ordinal:03d}-reserved.json'])) and
             _same(events[4+2*ordinal]['details'],dict(ordinal=ordinal,status=fit.status,result=actual[f'fits/{ordinal:03d}-result.json'])),'Journal fit accounting differs')
    expected_events+=['mapping_sealed','development_open_authorized','statistics_completed','evaluation_completed']
    need([e['event'] for e in events]==expected_events,'Fit/seal/development execution ordering differs')
    need(_same(values['FIT-SCHEDULE.json'],dict(ids=calibration.ids,components=[[i,calibration.components[i]] for i in calibration.ids],
        fits=groups,constants=c.CONSTANTS,total_optimizer_seconds=c.FIT_SECONDS*len(groups))),'Full fixed fit schedule differs')
    position=3+2*len(groups)
    expected_details=[dict(mapping_receipt=actual['MAPPING-RECEIPT.json'],map_fingerprint=suite.main.fingerprint),
        dict(mapping_receipt_sha256=actual['MAPPING-RECEIPT.json']['sha256'],derived_frame=actual['DEVELOPMENT-FRAME.json'],template=frame['development_template']),
        dict(development_cases=len(development.ids),bootstrap_replicates=s.REPLICATES),dict(report=actual['REPORT.json'])]
    need(all(_same(event['details'],expected) for event,expected in zip(events[position:],expected_details)),'Final journal bindings differ')
    need(_same(events[1]['details'],dict(frame=anchor,limits=frame['limits'],automatic_retry=False)) and
         _same(events[2]['details'],dict(cases=len(calibration.ids),components=len(set(calibration.components.values())))),'Input admission accounting differs')
    expected_report=dict(schema_version=1,kind=KIND,status='complete',frame=anchor,mapping_receipt=actual['MAPPING-RECEIPT.json'],
        calibration_cases=len(calibration.ids),calibration_components=len(set(calibration.components.values())),fits=len(groups),
        development_cases=len(development.ids),development_components=len(set(development.components.values())),bootstrap_replicates=s.REPLICATES,
        wall_seconds=report['wall_seconds'],provider_cost_usd=0,model_calls=0,automatic_retry=False,scientific_validation='benchmark_endpoint_only',
        uncertainty_scope='Conditional bootstrap; deletion ranges are sensitivity, not confidence intervals.')
    need(type(report['wall_seconds']) in (int,float) and math.isfinite(report['wall_seconds']) and
         max(suite.elapsed_seconds,values['BOOTSTRAP.json']['wall_seconds'])<=report['wall_seconds']<=frame['limits']['phase_seconds'] and
         _same(report,expected_report),'Terminal report/accounting differs')
    fixed={'FRAME.json','ENVIRONMENT.json','CALIBRATION-INPUTS.json','FIT-SCHEDULE.json','CALIBRATION-SUITE.json','MAPPING.json','MAPPING-RECEIPT.json',
        'DEVELOPMENT-FRAME.json','DEVELOPMENT-INPUTS.json','ANALYSIS-ROWS.json','POINT-SUMMARY.json','BOOTSTRAP.json','HELD-OUT.json','SENSITIVITY.json','REPORT.json','journal.jsonl'}
    need(set(actual)==fixed|{f'fits/{i:03d}-{suffix}.json' for i in range(len(groups)) for suffix in ('reserved','result')},'Unexplained evaluator files')
    for item in (*calibration.proofs,*development.proofs,*actual.values(),receipt_proof):capture(item,MAX_FILE)
    return serde.freeze(dict(status='verified',byte_integrity=True,source_consistency=True,arithmetic_consistency=True,
        independent_biological_validation=False,calibration_cases=len(calibration.ids),development_cases=len(development.ids),
        fits=len(groups),bootstrap_replicates=s.REPLICATES,receipt=receipt_proof))


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('execute');run.add_argument('--frame',required=True);run.add_argument('--frame-sha256',required=True);run.add_argument('--output',required=True)
    check=sub.add_parser('verify');check.add_argument('--output',required=True);check.add_argument('--receipt-sha256',required=True)
    args=parser.parse_args()
    result=execute(args.frame,args.frame_sha256,output=args.output) if args.command=='execute' else verify(args.output,args.receipt_sha256)
    print(json.dumps(serde.encode(result),sort_keys=True))


if __name__=='__main__':main()
