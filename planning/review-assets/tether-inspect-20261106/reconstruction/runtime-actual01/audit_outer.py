"""Read-only actual runtime anchor/process audit; no producer verifier imports."""
from collections import Counter
from pathlib import Path
import json
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import reconstruct as b
import runtime_reconstruct as r

ROOT=HERE.parents[4]
BASE=ROOT/'data/cache/tether-inspect-runtime-witnesses-20261106-attempt01'
STAGE=BASE/'runtime-stage'
SEAL='92d8f5754a2e119844df01964103c7f1f09d71e5bee5e70d6cec3ab1b344158f'
FREEZE='532b396ae05de2cdb07531898e1c0b72c3d38a557cee5c6fa5f6c70bb342a7b5'
PREP='b17fdfba429a913cb5a12bd1d1c5e0388031066ed45d7e93fca6c931fa55077c'


def process_recipe(folder,name,launch,expected_rows,oracle):
    recipe=b.load(folder/(name+'-recipe.json'),launch['recipe'])
    b.require(recipe['rows']==expected_rows and Path(recipe['output_root'])==folder/'cases'
              and recipe['oracle_path']==oracle['path']
              and recipe['oracle_proof']=={k:oracle[k] for k in ('sha256','bytes')},'Child process recipe differs')
    argv=launch['argv']
    b.require('-I' in argv and '-B' in argv and str(folder/(name+'-recipe.json')) in argv
              and launch['recipe']['sha256'] in argv,'Child launch recipe/isolation differs')
    ready=b.load(folder/name/'READY.json')
    b.require(ready=={'recipe_sha256':launch['recipe']['sha256'],'scheduled':len(expected_rows),'provider_calls':0},'Native worker readiness differs')
    return recipe


def interruption(processes,prep):
    folder=BASE/'IX06-interruption';report=b.load(folder/'RESULT.json');rows=processes['IX06']
    process_recipe(folder,'worker',report['launch'],rows,prep['process_oracle'])
    first=folder/'cases'/rows[0]['id'];second=folder/'cases'/rows[1]['id']
    b.require(b.load(first/'request.json')==rows[0] and not second.exists()
              and not (first/'receipt.json').exists() and not (folder/'worker/RESULT.json').exists(), 'Interrupted child finalized or continued')
    journal=b.read(first/'journal.jsonl',report['journal']);events=b.chain(journal)
    b.require(events[0]['event']=='reserved' and events[0]['details']=={'request_sha256':b.fingerprint(rows[0])},'Interrupted request/journal differs')
    reserved=[e['details'] for e in events if e['event']=='attempt_reserved']
    entered=[e['details'] for e in events if e['event']=='provider_entered']
    dispatched=[e['details'] for e in events if e['event']=='provider_dispatched']
    b.require(len(reserved)==len(entered)==len(dispatched)==1
              and not any(e['event'] in ('attempt_accounted','terminal','claim_committed','native_response') for e in events),
              'Interrupted prefix has repeated/settled/finalized call')
    ticket=reserved[0]
    b.require(ticket['attempt']==entered[0]['attempt']==dispatched[0]['attempt']==0
              and entered[0]['entry']==1 and ticket['request_sha256']==b.fingerprint(ticket['request'])
              and dispatched[0]['request_sha256']==ticket['request_sha256']
              and dispatched[0]['payload_sha256']==b.fingerprint(dispatched[0]['payload']), 'Interrupted live attempt bindings differ')
    b.require(dispatched[0]['payload']['messages']==[{'role':'user','content':b.canonical(ticket['request']).decode()}], 'Interrupted payload differs')
    admitted=[e['details'] for e in events if e['event']=='source_admitted']
    b.require(len(admitted)==1,'Interrupted input admission missing')
    sources=r.context_sources(rows[0],first,events,{'context_sha256':admitted[0]['context_sha256'],'commits':[]})
    b.require(report['status']=='PASS' and report['process_reaped'] is True and report['returncode']!=0
              and report['provider_dispatches']==1 and report['automatic_retry'] is False
              and report['outstanding_quote']==ticket['quote'] and report['measured_usage']==r.zero(), 'Interrupted accounting/control report differs')
    expected=[{'id':rows[0]['id'],'status':'interrupted','unresolved_calls':1},{'id':rows[1]['id'],'status':'unexecuted','unresolved_calls':0}]
    b.require(report['dispositions']==expected,'Interrupted all-scheduled dispositions differ')
    b.require(b.read(first/'journal.jsonl',report['journal'])==journal,'Independent prefix inspection changed the journal')
    return {'status':'PASS','dispositions':expected,'provider_dispatches':1,'unresolved_calls':1,
            'outstanding_quote':ticket['quote'],'measured_usage':r.zero(),'source_checks':sources,
            'process_reaped_reported':True,'returncode':report['returncode'],'journal_sha256':b.sha(journal),
            'limitation':'Reaped status is retained owned-child evidence; no process-tree/power-loss or independent historical OS observation.'}


def concurrency(processes,prep):
    folder=BASE/'IX08-concurrency';report=b.load(folder/'RESULT.json');row=processes['IX08']
    samples=[];winner=None
    for name,launch in zip(('first','second'),report['launches']):
        process_recipe(folder,name,launch,[row],prep['process_oracle'])
        worker=b.load(folder/name/'RESULT.json');pin=worker['native_log'];b.read(pin['path'],pin)
        native=b.native_log(pin['path']);b.require(len(native['samples'])==1,'Race native schedule differs')
        sample=native['samples'][0]
        b.require(sample['id']==row['id'] and sample['target']=='' and sample['epoch']==1
                  and sample['input']==b.canonical(row['input']).decode() and not sample.get('error_retries'), 'Race native request differs')
        b.require(worker['recipe_sha256']==launch['recipe']['sha256'] and worker['scheduled']==[row['id']]
                  and not worker['network']['blocked'] and worker['automatic_retry'] is False,'Race worker provenance differs')
        error=bool(sample.get('error'));b.require(worker['samples'][0]['native_error'] is error,'Race error summary differs')
        if error:
            b.require('FileExistsError' in sample['error']['message'] and not sample.get('scores')
                      and not worker['samples'][0]['record'] and not sample.get('model_usage'),'Losing native worker failed for an unrelated reason or generated')
        else:
            retained=worker['samples'][0]['record']
            b.require(retained['receipt']==report['receipt'] and Path(retained['path'])==folder/'cases'/row['id'],'Winning receipt differs')
            winner=r.runtime_record(row,folder/'cases'/row['id'],retained['receipt']['sha256'],sample,native_header=native['header'])
            b.require(len(sample['scores'])==1 and next(iter(sample['scores'].values()))['value']=='C','Race winner lacks expected native score')
        samples.append({'worker':name,'native_error':error,'native_log_sha256':pin['sha256']})
    b.require(sorted(s['native_error'] for s in samples)==[False,True]
              and [s['native_error'] for s in samples]==report['native_sample_errors']
              and winner is not None and winner['accounting']['provider_dispatches']==1
              and report['owners']==report['provider_dispatches']==1 and report['returncodes']==[0,0]
              and report['processes_reaped'] is True and report['automatic_retry'] is False,'Race owner/dispatch/control counts differ')
    b.require((folder/'START').read_bytes()==b'release both owned native workers\n','Race release barrier differs')
    return {'status':'PASS','logical_cases':1,'native_workers':2,'owners':1,'provider_dispatches':1,
            'samples':samples,'winner_accounting':winner['accounting'],'winner_source_checks':winner['sources'],
            'limitation':'One actual controlled two-worker race; not a universal filesystem concurrency theorem.'}


def main():
    seal=b.load(STAGE/'SEALED.json',SEAL);config=b.load(BASE/'freeze/FROZEN.json',FREEZE)
    b.require(seal['freeze_sha256']==FREEZE and seal['status']=='completed','Outer stage freeze/status differs')
    products=b.verify_inventory(STAGE,seal['files'],excluded=('SEALED.json',))
    b.require(b.read(STAGE/'freeze.json')==b.read(BASE/'freeze/FROZEN.json',FREEZE),'Copied runtime freeze differs')
    for name,pin in config['code_pins'].items():b.read(name,pin)
    prep=b.load(BASE/'PREPARATION.json',PREP)
    b.require(config['preparation']['sha256']==PREP,'Runtime preparation differs')
    for name,pin in prep['input_inventory'].items():b.read(b.inside(BASE,name),pin)
    ordinary_rows=b.load(prep['ordinary']['rows']['path'],prep['ordinary']['rows'])
    processes=b.load(prep['process_rows']['path'],prep['process_rows'])
    schedule=[{'id':'ordinary16','case_ids':[r['id'] for r in ordinary_rows]},
              {'id':'IX06','case_ids':[r['id'] for r in processes['IX06']]},
              {'id':'IX08','case_ids':[processes['IX08']['id']]}]
    parent=b.sealed_record(STAGE,seal['stage_receipt']['sha256'],{'operation':'native_runtime_witness_stage',
        'freeze_sha256':FREEZE,'scheduled':schedule,'automatic_retry':False})
    result=parent['result']
    b.require(result['status']=='completed' and result['error'] is None and result['provider_cost_usd']==0
              and result['automatic_retry'] is False and result['scheduled_operation_groups']==3
              and result['scheduled_logical_cases']==19,'Runtime outer totals/status differ')
    for name,pin in result['witness_outputs'].items():b.read(b.inside(BASE,name),pin)
    roots=('ordinary-cases','ordinary-worker','IX06-interruption','IX08-concurrency')
    actual={p.relative_to(BASE).as_posix() for name in roots for p in (BASE/name).rglob('*') if p.is_file()}
    b.require(actual==set(result['witness_outputs']),'Witness output inventory incomplete')
    for expected,outcome in zip(schedule,result['schedule']):
        b.require(outcome['id']==expected['id'] and outcome['case_ids']==expected['case_ids']
                  and outcome['status']=='completed' and outcome['returncode']==0 and outcome['error'] is None,'Group schedule/outcome differs')
        group=STAGE/outcome['id'];request=b.load(group/'request.json')
        attempt=b.sealed_record(group,outcome['attempt_receipt']['sha256'],request)
        b.require(attempt['result']=={k:v for k,v in outcome.items() if k!='attempt_receipt'},'Outer attempt result differs')
        b.require(request['case_ids']==expected['case_ids'] and request['automatic_retry'] is False
                  and request['argv'][0]==config['python']['path'] and '-I' in request['argv'] and '-B' in request['argv'], 'Outer dispatch request differs')
        b.successful_supervision(outcome['supervision'],request['limits'],len(b.read(group/'stdout.bin')),len(b.read(group/'stderr.bin')))
        b.read(outcome['result']['path'],outcome['result'])
        events=[e['details'] for e in parent['events'] if e['event']=='attempt_finished' and e['details']['id']==expected['id']]
        b.require(events==[outcome],'Parent/group completion journal differs')
    ordinary_pin=result['schedule'][0]['result']
    ordinary=r.reconstruct_ordinary(BASE/'PREPARATION.json',PREP,ordinary_pin['path'],ordinary_pin['sha256'])
    stopped=interruption(processes,prep);race=concurrency(processes,prep)
    dispositions=[]
    for row in ordinary['cases']:
        path=BASE/'ordinary-cases'/row['control_id']
        dispositions.append({'group':'ordinary16','id':row['control_id'],'status':row['status'],
            'receipt':{'sha256':b.sha(b.read(path/'receipt.json')),'bytes':len(b.read(path/'receipt.json'))}})
    dispositions += [{'group':'IX06','id':processes['IX06'][0]['id'],'status':'interrupted_unresolved','receipt':None},
                     {'group':'IX06','id':processes['IX06'][1]['id'],'status':'unexecuted','receipt':None},
                     {'group':'IX08','id':processes['IX08']['id'],'status':'completed','receipt':b.load(BASE/'IX08-concurrency/RESULT.json')['receipt']}]
    b.require(dispositions==result['case_dispositions'],'All19 logical dispositions differ')
    report={'schema_version':1,'status':'PASS','external_anchor_basis':'Root postexecution external SHA256, not an independently pre-recorded execution seal',
        'stage_seal_sha256':SEAL,'freeze_sha256':FREEZE,'preparation_sha256':PREP,'products':products,
        'pinned_code_and_environment_files':len(config['code_pins']),'prepared_inputs':len(prep['input_inventory']),
        'witness_output_files':len(result['witness_outputs']),'witness_output_bytes':sum(p['bytes'] for p in result['witness_outputs'].values()),
        'ordinary':ordinary,'IX06':stopped,'IX08':race,'logical_dispositions':dispositions,
        'status_counts':dict(Counter(row['status'] for row in dispositions)),'provider_cost_usd':0,'automatic_redispatch':False,
        'analyzer_sha256':b.sha(b.read(__file__)),
        'limitations':['Finite scripted witnesses, not therapeutic workflow or model quality.',
                      'General eligibility relies on reused independent validator; exact source/claims and narrow synthetic features/contributions are independently rebuilt.',
                      'IX11 write failures are retained component/mock qualification, not a new persisted native write-fault run.',
                      'Process reaping is retained direct-child evidence, not descendant containment or power-loss proof.']}
    path=HERE/'RUNTIME-RECONSTRUCTION.json'
    with path.open('xb') as stream:stream.write(b.canonical(report)+b'\n')
    print(json.dumps({'status':report['status'],'logical_cases':len(dispositions),'status_counts':report['status_counts'],
                      'report_sha256':b.sha(b.read(path))}))


if __name__=='__main__':main()
