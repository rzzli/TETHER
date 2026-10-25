"""Freeze and execute a bounded exposed-case interpretation development pilot.

No dataset acquisition, external provider, automatic generation retry, evaluator
join or clinical scoring. Only the launcher-owned loopback server is terminated.
"""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.request

from asof.agents import Usage
from asof.journal import RunJournal,read_chain
from asof.local_model import NoRedirect
from asof.serde import ContractError,decode,encode,fingerprint,read_json,sha256_file,write_json
from asof.workflow import Budget,add_usage
from tools.science.bounded_interpretation import (dependency_paths,prepare_input,run_interpretation,
                                                 verify_interpretation,need)
from tools.science.local_interpretation import LocalInterpreter,payload_for,validate_config
from tools.science.run_comparison import pin,check_pin,verify_model,_owned_listener

ROOT=Path(__file__).resolve().parents[2]


def code_proofs():
    paths=[Path(__file__).resolve(),ROOT/'tools/science/bounded_interpretation.py',
           ROOT/'src/asof/local_model.py',*dependency_paths()]
    return [pin(p) for p in dict.fromkeys(paths)]


def prepare(output,case,snapshot,catalog,task_specs,model_receipt,reference_seal,*,port=55585,
            max_claims=3,max_prompt_bytes=14000):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    journal=RunJournal(output/'preparation',kind='build')
    try:
        need(type(port) is int and 1024<=port<=65535,'Invalid development port')
        need(type(max_claims) is int and 1<=max_claims<=4,'Invalid local claim cap')
        need(1<=len(task_specs)<=2 and len({t['task_id'] for t in task_specs})==len(task_specs),'Pilot needs one or two unique tasks')
        receipt=read_json(Path(model_receipt));need(receipt['status']=='downloaded_hash_verified_not_inference_validated',
                                                 'Pinned model acquisition is incomplete')
        model_root=Path(receipt['root']).resolve()
        runtimes=[p for p in receipt['runtime_files'] if p['path'].replace('\\','/').endswith('/llama-server.exe')]
        need(len(runtimes)==1,'Runtime identity ambiguous')
        config=dict(schema_version=1,endpoint=f'http://127.0.0.1:{port}',model_id='Qwen/Qwen2.5-14B-Instruct-GGUF@'+receipt['revision'],
            model_provenance=dict(weights_sha256={x['name']:x['sha256'] for x in receipt['items'] if x['name'].endswith('.gguf')},
                                 runtime_sha256=runtimes[0]['sha256']),
            max_prompt_bytes=max_prompt_bytes,max_output_tokens=2048,timeout_seconds=300,seed=42)
        validate_config(config);write_json(output/'model-config.json',config)
        tasks=[]
        for task in task_specs:
            need(set(task)=={'task_id','observation_ids'} and isinstance(task['task_id'],str) and
                 re.fullmatch('[a-z][a-z0-9_-]{0,63}',task['task_id']),'Invalid pilot task')
            prepared=prepare_input(case,snapshot,catalog,max_claims=max_claims,observation_ids=task['observation_ids'])
            request_path=output/'preparation'/(task['task_id']+'-request.json')
            write_json(request_path,prepared.request);payload=payload_for(prepared.request,config)
            quote=Usage(len(payload['prompt'].encode('utf-8'))+32,config['max_output_tokens'],0)
            tasks.append(dict(**task,request=pin(request_path),request_sha256=fingerprint(prepared.request),
                              payload_sha256=fingerprint(payload),reserved=encode(quote)))
        budget=Budget();total=Usage(0,0,0)
        for task in tasks:total=add_usage(total,decode(Usage,task['reserved']))
        need(total.input_tokens<=budget.max_input_tokens and total.output_tokens<=budget.max_output_tokens and
             len(tasks)<=budget.max_calls,'Pilot worst-case requests exceed shared case budget')
        plan=dict(schema_version=2,role='development_execution_plan',root=str(output),max_claims=max_claims,
            created_at_utc=datetime.now(timezone.utc).isoformat(),case=pin(Path(case)),snapshot=pin(Path(snapshot)),
            catalog=pin(Path(catalog)) if catalog else None,model_receipt=pin(Path(model_receipt)),
            reference_seal=pin(Path(reference_seal)),model_config=pin(output/'model-config.json'),code=code_proofs(),
            tasks=tasks,budget=encode(budget),port=port,provider_spend_usd=0,
            exposure='Known exposed IL6R sources deliberately selected for development stress; no fresh holdout or blinded selection.',
            scope='Two source-scoped generation tasks, not a paired system comparison or complete scientific qualification.',
            evaluator_content_in_model_requests=False,automatic_generation_retries=False)
        write_json(output/'run-plan.json',plan);journal.append('build_completed',plan=pin(output/'run-plan.json'))
        return pin(output/'run-plan.json')
    except BaseException as error:
        journal.fail(error,'preparation');raise
    finally:journal.close()


def validate_plan(plan):
    need(isinstance(plan,dict) and type(plan['schema_version']) is int and plan['schema_version']==2 and
         type(plan['max_claims']) is int and 1<=plan['max_claims']<=4 and
         type(plan['port']) is int and 1024<=plan['port']<=65535 and
         plan['role']=='development_execution_plan' and plan['provider_spend_usd']==0 and
         plan['automatic_generation_retries'] is False and plan['evaluator_content_in_model_requests'] is False,
         'Pilot boundary contradiction')
    budget=decode(Budget,plan['budget']);budget.validate()
    need(plan['budget']==encode(Budget()),'Pilot must retain default shared case budget')
    for proof in plan['code']+[plan['case'],plan['snapshot'],plan['model_receipt'],plan['reference_seal'],plan['model_config']]:check_pin(proof)
    need(plan['code']==code_proofs(),'Pilot execution code differs')
    if plan['catalog']:check_pin(plan['catalog'])
    config=read_json(check_pin(plan['model_config']));validate_config(config)
    receipt=read_json(check_pin(plan['model_receipt']))
    expected_weights={x['name']:x['sha256'] for x in receipt['items'] if x['name'].endswith('.gguf')}
    runtime_entries=[p for p in receipt['runtime_files'] if p['path'].replace('\\','/').endswith('/llama-server.exe')]
    need(len(runtime_entries)==1 and config['model_provenance']['weights_sha256']==expected_weights and
         config['model_provenance']['runtime_sha256']==runtime_entries[0]['sha256'] and
         config['model_id']=='Qwen/Qwen2.5-14B-Instruct-GGUF@'+receipt['revision'],
         'Model/runtime provenance contradicts pinned receipt')
    need(config['endpoint']==f"http://127.0.0.1:{plan['port']}",'Pilot endpoint/port differs')
    need(1<=len(plan['tasks'])<=2,'Invalid task count')
    for task in plan['tasks']:
        need(re.fullmatch('[a-z][a-z0-9_-]{0,63}',task['task_id']) is not None,'Unsafe task ID')
        request=prepare_input(plan['case']['path'],plan['snapshot']['path'],plan['catalog']['path'] if plan['catalog'] else None,
                              max_claims=plan['max_claims'],observation_ids=task['observation_ids']).request
        need(fingerprint(request)==task['request_sha256']==fingerprint(read_json(check_pin(task['request']))) and
             fingerprint(payload_for(request,config))==task['payload_sha256'],'Frozen development request differs')
        expected=Usage(len(payload_for(request,config)['prompt'].encode('utf-8'))+32,config['max_output_tokens'],0)
        need(task['reserved']==encode(expected),'Frozen quote differs')
    need(len({t['task_id'] for t in plan['tasks']})==len(plan['tasks']),'Duplicate task')


def execute(plan_proof):
    plan_path=check_pin(plan_proof);plan=read_json(plan_path);output=Path(plan['root']).resolve()
    need(plan_path.resolve()==output/'run-plan.json','Moved plan output root')
    journal=RunJournal(output/'execution',kind='build');process=None;error=None
    result=dict(status='running',plan=plan_proof,tasks=[],measured_usage=encode(Usage(0,0,0)),
                estimated_usage=encode(Usage(0,0,0)),server_stopped=False,provider_spend_usd=0,
                scientific_quality='not_evaluated',clinical_probability=None)
    try:
        validate_plan(plan);receipt=read_json(check_pin(plan['model_receipt']))
        journal.append('model_verification_started');server,model=verify_model(receipt)
        config=read_json(check_pin(plan['model_config']))
        need(sha256_file(server)==config['model_provenance']['runtime_sha256'],'Runtime provenance differs')
        journal.append('model_verification_passed',runtime=pin(server))
        with socket.socket() as probe:probe.bind(('127.0.0.1',plan['port']))
        argv=[str(server),'--model',str(model),'--host','127.0.0.1','--port',str(plan['port']),
              '--ctx-size','16384','--parallel','1','--n-gpu-layers','99','--threads','8',
              '--alias','asof-interpretation-development','--no-webui','--offline']
        write_json(output/'server-command.json',dict(argv=argv,runtime_sha256=sha256_file(server)))
        with (output/'server.stdout.log').open('xb') as stdout,(output/'server.stderr.log').open('xb') as stderr:
            process=subprocess.Popen(argv,stdout=stdout,stderr=stderr,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        journal.append('server_started',pid=process.pid)
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect());deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            need(process.poll() is None,'Owned model server exited during startup')
            try:
                with opener.open(config['endpoint']+'/health',timeout=1) as health:
                    if health.status==200:break
            except OSError:time.sleep(1)
        else:raise TimeoutError('Owned model server did not become ready')
        need(_owned_listener(process.pid,plan['port']),'Loopback listener is not launcher-owned')
        journal.append('server_ready',pid=process.pid)
        started=time.monotonic();used=Usage(0,0,0);calls=0;original=decode(Budget,plan['budget'])
        for task in plan['tasks']:
            remaining=Budget(original.max_calls-calls,original.max_input_tokens-used.input_tokens,
                original.max_output_tokens-used.output_tokens,0,original.max_seconds-(time.monotonic()-started),original.max_retries)
            remaining.validate();job=output/'tasks'/task['task_id'];backend=LocalInterpreter(check_pin(plan['model_config']))
            journal.append('task_dispatch',task_id=task['task_id'],request_sha256=task['request_sha256'])
            task_error=None
            try:
                report=run_interpretation(plan['case']['path'],plan['snapshot']['path'],job,backend,
                    plan['catalog']['path'] if plan['catalog'] else None,budget=remaining,max_claims=plan['max_claims'],
                    observation_ids=task['observation_ids'])
                verify_interpretation(job)
                need(report['status']=='interpretation_contract_completed_not_scientific_validation','Task abstained before generation')
                result['tasks'].append(dict(task_id=task['task_id'],report=pin(job/'report.json'),
                    receipt=pin(job/'receipt.json'),response=pin(job/'response.json')))
            except BaseException as task_exception:
                task_error=task_exception
            finally:
                try:
                    if (job/'journal.jsonl').exists():
                        for event in read_chain(job/'journal.jsonl',allow_incomplete_tail=True):
                            if event['event']=='interpretation_accounted':
                                amount=decode(Usage,encode(event['details']['usage']));amount.validate();used=add_usage(used,amount);calls+=1
                                key='measured_usage' if event['details']['basis']=='adapter_reported' else 'estimated_usage'
                                result[key]=encode(add_usage(decode(Usage,result[key]),amount))
                except BaseException as accounting_error:
                    journal.append('task_accounting_failed',task_id=task['task_id'],error_class=type(accounting_error).__name__,
                                   original_error_class=type(task_error).__name__ if task_error else None)
                    if task_error is None:task_error=accounting_error
                result['calls']=calls
            if task_error is not None:raise task_error
            write_json(output/'execution-report.json',result)
        result['status']='all_development_outputs_contract_verified'
    except BaseException as exc:
        error=exc;result.update(status='failed',error_class=type(exc).__name__)
    finally:
        try:
            if process is not None:
                try:
                    if process.poll() is None:process.terminate()
                    try:process.wait(timeout=30)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
                    result['server_stopped']=process.poll() is not None
                except BaseException as cleanup_error:
                    result['cleanup_error_class']=type(cleanup_error).__name__
                    if error is None:error=cleanup_error
            if error is not None:result.update(status='failed',error_class=type(error).__name__)
            try:
                write_json(output/'execution-report.json',result)
            except BaseException as report_error:
                journal.append('execution_report_write_failed',error_class=type(report_error).__name__)
                if error is None:error=report_error
            if error is not None:journal.fail(error,'development_execution')
            else:journal.append('build_completed',report=pin(output/'execution-report.json'))
        finally:journal.close()
    if error is not None:raise error
    seal=dict(role='sealed_development_interpretations_before_scientific_review',created_at_utc=datetime.now(timezone.utc).isoformat(),
        plan=plan_proof,execution_report=pin(output/'execution-report.json'),tasks=result['tasks'],
        proofs=[pin(output/name) for name in ['execution/journal.jsonl','preparation/journal.jsonl',
                 'server-command.json','server.stdout.log','server.stderr.log']],
        fresh_holdout=False,scientific_quality='not_evaluated',clinical_probability=None)
    write_json(output/'predictions-seal.json',seal);return pin(output/'predictions-seal.json')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--sha256',required=True);args=parser.parse_args()
    proof=pin(args.plan);need(proof['sha256']==args.sha256,'Explicit frozen plan hash differs')
    print(execute(proof))


if __name__=='__main__':main()
