"""Frozen two-question exposed development pilot; no retry or scientific approval."""
import argparse
import inspect
from datetime import datetime,timezone
from pathlib import Path
import socket
import subprocess
import time
import urllib.request

from asof.agents import Usage
from asof.journal import RunJournal,read_chain
from asof.local_model import NoRedirect
from asof.serde import decode,encode,fingerprint,freeze,read_json,sha256_file,write_json
from asof.workflow import Budget,add_usage
from tools.science.bounded_interpretation import need
from tools.science.interpretation_questions import prepare_question
from tools.science.question_interpretation_local import (LocalQuestionInterpreter,payload_for,verify_local_execution,
    _preserve_primary)
from tools.science.question_interpretation_runtime import (code_paths,run_question_interpretation,
    verify_question_interpretation,inspect_question_interpretation)
from tools.science.run_comparison import pin,check_pin,verify_model,_owned_listener

ROOT=Path(__file__).resolve().parents[2]
TASKS=(('mechanism-context','mechanism-report.v1'),('mr-discovery-replication','genetic-study-report.v1'))
PLAN_KEYS={'schema_version','role','root','created_at_utc','case','snapshot','catalog','model_receipt',
    'reference_seal','mechanics_acceptance','protocol','model_config','code','tasks','budget','port',
    'max_claims','automatic_generation_retries','evaluator_content_in_model_requests','fresh_holdout',
    'provider_spend_usd','exposure'}


class FrozenLocalQuestionInterpreter:
    """Compose the qualified transport with a pre-dispatch frozen-request gate."""
    backend_id='frozen-question-pilot-local-v1'

    def __init__(self,config_path,request_sha256,payload_sha256,config_sha256):
        need(all(isinstance(v,str) and len(v)==64 and all(c in '0123456789abcdef' for c in v)
             for v in [request_sha256,payload_sha256,config_sha256]),'Invalid frozen request/payload/config identity')
        self.inner=LocalQuestionInterpreter(config_path);self.config=self.inner.config
        need(self.inner.provenance['config_sha256']==config_sha256,'Frozen local config bytes differ before dispatch')
        self.provenance=freeze(dict(kind='frozen_question_local',expected_request_sha256=request_sha256,
            expected_payload_sha256=payload_sha256,expected_config_sha256=config_sha256,
            local_provenance=encode(self.inner.provenance)))

    def _check(self,request):
        need(fingerprint(request)==self.provenance['expected_request_sha256'],'Frozen question request differs before dispatch')
        need(self.inner.provenance['config_sha256']==self.provenance['expected_config_sha256'] and
             fingerprint(payload_for(request,self.inner.config))==self.provenance['expected_payload_sha256'],
             'Frozen payload/config differs before dispatch')

    def quote(self,request):self._check(request);return self.inner.quote(request)

    def generate(self,request,timeout_seconds):
        self._check(request);return self.inner.generate(request,timeout_seconds)

    def execution_document(self):return self.inner.execution_document()


def verify_frozen_execution(request,config,response,execution,report):
    """Explicit composite verifier; no dynamic imports or calls to the endpoint."""
    need(config['backend_id']==FrozenLocalQuestionInterpreter.backend_id and
         check_pin(config['adapter_code'])==Path(__file__).resolve(),'Wrong frozen adapter identity')
    provenance=config['adapter_provenance']
    need(isinstance(provenance,dict) and set(provenance)=={'kind','expected_request_sha256','expected_payload_sha256',
         'expected_config_sha256','local_provenance'} and
         provenance['kind']=='frozen_question_local' and provenance['expected_request_sha256']==fingerprint(request),
         'Frozen question request binding differs')
    need(provenance['local_provenance']['config_sha256']==provenance['expected_config_sha256'] and
         fingerprint(payload_for(request,provenance['local_provenance']['config']))==provenance['expected_payload_sha256'],
         'Frozen payload/config binding differs')
    # The inner transport remains byte-for-byte qualified. This trusted callback
    # explicitly validates its delegation rather than importing archived code.
    inner=encode(config);inner.update(backend_id=LocalQuestionInterpreter.backend_id,
        adapter_code=pin(Path(inspect.getfile(LocalQuestionInterpreter))),adapter_provenance=provenance['local_provenance'])
    verify_local_execution(request,inner,response,execution,report)


def code_proofs():return [pin(path) for path in code_paths(Path(__file__))]


def _config(receipt,port):
    need(receipt.get('status')=='downloaded_hash_verified_not_inference_validated','Incomplete acquisition declaration')
    runtimes=[p for p in receipt['runtime_files'] if p['path'].replace('\\','/').endswith('/llama-server.exe')]
    need(len(runtimes)==1,'Ambiguous native runtime')
    return dict(schema_version=1,endpoint=f'http://127.0.0.1:{port}',
        model_id='Qwen/Qwen2.5-14B-Instruct-GGUF@'+receipt['revision'],
        model_provenance=dict(weights_sha256={p['name']:p['sha256'] for p in receipt['items'] if p['name'].endswith('.gguf')},
            runtime_sha256=runtimes[0]['sha256']),max_prompt_bytes=14200,max_output_tokens=2048,timeout_seconds=300,seed=42)


def _request(plan,task):
    return prepare_question(check_pin(plan['case']),check_pin(plan['snapshot']),task['family'],
        check_pin(plan['catalog']) if plan['catalog'] else None,max_claims=2,
        observation_ids=task['observation_ids']).request


def _mechanics(proof):
    """Require retained test/code evidence, not only a mutable success label."""
    acceptance=read_json(check_pin(proof))
    need(acceptance.get('status')=='passed_native_renderer_and_transport_mechanics_only' and
         acceptance.get('native_pilot_executed') is False and isinstance(acceptance.get('proofs'),list),
         'Mechanics acceptance missing')
    required={'tools/science/'+name for name in ['question_interpretation_local.py','question_interpretation_render.py',
        'question_interpretation_runtime.py','interpretation_questions.py','bounded_interpretation.py',
        'local_interpretation.py','run_interpretation_development.py']}
    guards=[];reports=[]
    for parent in acceptance['proofs']:
        evidence=read_json(check_pin(parent))
        if isinstance(evidence,dict) and 'code_pins' in evidence:guards.append(evidence)
        if isinstance(evidence,dict) and evidence.get('mode')=='full' and 'tests' in evidence:reports.append(evidence)
    need(len(guards)==1 and guards[0].get('status')=='passed' and guards[0].get('code_unchanged') is True and
         isinstance(guards[0].get('code_pins'),dict) and required<=set(guards[0]['code_pins']),
         'Retained unchanged-code guard missing')
    for name,digest in guards[0]['code_pins'].items():
        path=(ROOT/name).resolve()
        need(not Path(name).is_absolute() and path.is_relative_to(ROOT) and sha256_file(path)==digest,
             'Mechanics-tested code changed')
    need(len(reports)==1 and reports[0].get('status')=='passed' and
         type(reports[0]['tests'].get('run')) is int and reports[0]['tests']['run']>=1239 and
         reports[0]['tests'].get('failures')==0 and reports[0]['tests'].get('errors')==0 and
         reports[0]['tests'].get('skipped')==[] and reports[0].get('required_probes_exit_code')==0 and
         reports[0].get('packaging',{}).get('dependency_free_demo')=='passed','Retained full validation missing')


def prepare(output,case,snapshot,catalog,task_specs,model_receipt,reference_seal,mechanics_acceptance,
            protocol,*,port=55589):
    output=Path(output).resolve()
    for source in [case,snapshot,catalog,model_receipt,reference_seal,mechanics_acceptance,protocol]:
        if source:need(not output.is_relative_to(Path(source).resolve().parent),'Pilot output overlaps an input directory')
    output.mkdir(parents=True,exist_ok=False);journal=RunJournal(output/'preparation',kind='build')
    primary=None
    try:
        need(type(port) is int and 1024<=port<=65535,'Invalid pilot port')
        need(isinstance(task_specs,list) and len(task_specs)==2 and
             all(isinstance(t,dict) and set(t)=={'task_id','family','observation_ids'} for t in task_specs) and
             tuple((t['task_id'],t['family']) for t in task_specs)==TASKS,'Exactly the two fixed question families are required')
        plan=dict(schema_version=1,role='question_development_execution_plan',root=str(output),
            created_at_utc=datetime.now(timezone.utc).isoformat(),case=pin(Path(case)),snapshot=pin(Path(snapshot)),
            catalog=pin(Path(catalog)) if catalog else None,model_receipt=pin(Path(model_receipt)),
            reference_seal=pin(Path(reference_seal)),mechanics_acceptance=pin(Path(mechanics_acceptance)),
            protocol=pin(Path(protocol)),model_config=None,code=code_proofs(),tasks=[],budget=encode(Budget()),port=port,
            max_claims=2,automatic_generation_retries=False,evaluator_content_in_model_requests=False,
            fresh_holdout=False,provider_spend_usd=0,
            exposure='Previously exposed development case and source subsets; no holdout or matched performance claim.')
        config=_config(read_json(check_pin(plan['model_receipt'])),port)
        write_json(output/'model-config.json',config);plan['model_config']=pin(output/'model-config.json')
        for task in task_specs:
            request=_request(plan,task);payload=payload_for(request,config)
            path=output/'preparation'/(task['task_id']+'-request.json');write_json(path,request)
            plan['tasks'].append(dict(**task,request=pin(path),request_sha256=fingerprint(request),
                payload_sha256=fingerprint(payload),reserved=encode(Usage(len(payload['prompt'].encode('utf-8'))+32,2048,0.0))))
        validate_plan(plan);write_json(output/'run-plan.json',plan)
        journal.append('build_completed',plan=pin(output/'run-plan.json'));return pin(output/'run-plan.json')
    except BaseException as error:
        primary=error
        try:journal.fail(error,'question_pilot_preparation')
        except BaseException as secondary:error.add_note('Preparation terminal write failed: '+type(secondary).__name__)
        raise
    finally:
        try:journal.close()
        except BaseException as secondary:
            if primary:primary.add_note('Preparation close failed: '+type(secondary).__name__)
            else:raise


def validate_plan(plan):
    need(isinstance(plan,dict) and set(plan)==PLAN_KEYS,'Invalid question pilot plan fields')
    need(type(plan['schema_version']) is int and plan['schema_version']==1 and
         plan['role']=='question_development_execution_plan' and type(plan['port']) is int and
         1024<=plan['port']<=65535 and type(plan['max_claims']) is int and plan['max_claims']==2 and
         plan['automatic_generation_retries'] is False and plan['evaluator_content_in_model_requests'] is False and
         plan['fresh_holdout'] is False and type(plan['provider_spend_usd']) is int and plan['provider_spend_usd']==0,
         'Question pilot boundary contradiction')
    need(fingerprint(plan['budget'])==fingerprint(encode(Budget())),'Default shared-case budget must remain unchanged')
    for proof in plan['code']+[plan[key] for key in ['case','snapshot','model_receipt','reference_seal',
                                                   'mechanics_acceptance','protocol','model_config']]:check_pin(proof)
    need(plan['code']==code_proofs(),'Question pilot code closure differs')
    if plan['catalog']:check_pin(plan['catalog'])
    _mechanics(plan['mechanics_acceptance'])
    config=read_json(check_pin(plan['model_config']))
    need(fingerprint(config)==fingerprint(_config(read_json(check_pin(plan['model_receipt'])),plan['port'])),
         'Model/runtime declaration or generation limits differ')
    need(isinstance(plan['tasks'],list) and len(plan['tasks'])==2 and
         all(isinstance(t,dict) and set(t)=={'task_id','family','observation_ids','request','request_sha256',
              'payload_sha256','reserved'} for t in plan['tasks']) and
         tuple((t['task_id'],t['family']) for t in plan['tasks'])==TASKS,'Fixed question/task pack differs')
    total=Usage(0,0,0.0)
    for task in plan['tasks']:
        need(isinstance(task['observation_ids'],list) and task['observation_ids'] and
             len(set(task['observation_ids']))==len(task['observation_ids']) and
             all(isinstance(v,str) and v for v in task['observation_ids']),'Invalid selected-source IDs')
        request=_request(plan,task);payload=payload_for(request,config)
        need(fingerprint(request)==task['request_sha256']==fingerprint(read_json(check_pin(task['request']))) and
             fingerprint(payload)==task['payload_sha256'],'Frozen request/payload differs')
        quote=Usage(len(payload['prompt'].encode('utf-8'))+32,2048,0.0)
        need(fingerprint(task['reserved'])==fingerprint(encode(quote)),'Frozen reservation differs')
        total=add_usage(total,quote)
    need(total.input_tokens<=32000 and total.output_tokens<=8000,'Shared-case reservation exceeded')


def _start(plan,output,journal,ownership):
    """Caller owns and cleans process even if readiness fails after launch."""
    receipt=read_json(check_pin(plan['model_receipt']));server,model=verify_model(receipt)
    config=read_json(check_pin(plan['model_config']))
    need(sha256_file(server)==config['model_provenance']['runtime_sha256'],'Runtime provenance differs')
    with socket.socket() as probe:probe.bind(('127.0.0.1',plan['port']))
    argv=[str(server),'--model',str(model),'--host','127.0.0.1','--port',str(plan['port']),
        '--ctx-size','16384','--parallel','1','--n-gpu-layers','99','--threads','8',
        '--alias','asof-question-development','--no-webui','--offline']
    write_json(output/'server-command.json',dict(argv=argv,runtime_sha256=sha256_file(server)))
    with _preserve_primary((output/'server.stdout.log').open('xb')) as stdout,\
         _preserve_primary((output/'server.stderr.log').open('xb')) as stderr:
        process=subprocess.Popen(argv,stdout=stdout,stderr=stderr,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        ownership['process']=process
        return process


def _ready(plan,process):
    config=read_json(check_pin(plan['model_config']));deadline=time.monotonic()+180
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    while time.monotonic()<deadline:
        need(process.poll() is None,'Owned server exited during startup')
        try:
            with _preserve_primary(opener.open(config['endpoint']+'/health',timeout=1)) as response:
                if response.status==200:break
        except OSError:time.sleep(1)
    else:raise TimeoutError('Owned question server did not become ready')
    need(_owned_listener(process.pid,plan['port']),'Question listener not owned by launcher')


def _remaining_budget(budget,calls,used,elapsed):
    remaining=Budget(budget.max_calls-calls,budget.max_input_tokens-used.input_tokens,
        budget.max_output_tokens-used.output_tokens,0,budget.max_seconds-elapsed,budget.max_retries)
    remaining.validate();return remaining


def _match_task(plan,task,job,report,expected_budget):
    receipt=read_json(job/'receipt.json');config=read_json(job/'configuration.json')
    provenance=config['adapter_provenance']
    need(fingerprint(read_json(job/'request.json'))==task['request_sha256']==report['request_sha256']==
         receipt['request_sha256']==provenance['expected_request_sha256'],'Frozen task request/report/receipt differs')
    need(provenance['expected_config_sha256']==provenance['local_provenance']['config_sha256']==plan['model_config']['sha256'] and
         provenance['expected_payload_sha256']==task['payload_sha256'] and
         fingerprint(provenance['local_provenance']['config'])==fingerprint(read_json(check_pin(plan['model_config']))),
         'Frozen task payload/config differs')
    need(fingerprint(config['budget'])==fingerprint(encode(decode(Budget,encode(expected_budget)))),
         'Frozen task effective budget differs')


def execute(plan_proof):
    path=check_pin(plan_proof);plan=read_json(path);output=Path(plan['root']).resolve()
    need(path.resolve()==output/'run-plan.json','Moved question pilot plan')
    journal=RunJournal(output/'execution',kind='build');process=None;primary=None;ownership={};seal_proof=None
    result=dict(status='running',plan=plan_proof,tasks=[],calls=0,measured_usage=encode(Usage(0,0,0.0)),
        estimated_usage=encode(Usage(0,0,0.0)),server_stopped=False,provider_spend_usd=0,
        scientific_quality='not_evaluated',clinical_probability=None,secondary_failures=[])
    def secondary(error,stage):
        nonlocal primary
        result['secondary_failures'].append(dict(stage=stage,error_class=type(error).__name__))
        if primary:primary.add_note(stage+': '+type(error).__name__)
        else:primary=error
    try:
        validate_plan(plan);journal.append('question_pilot_validated',plan=plan_proof)
        process=_start(plan,output,journal,ownership);journal.append('server_started',pid=process.pid)
        _ready(plan,process);journal.append('server_ready',pid=process.pid)
        started=time.monotonic();used=Usage(0,0,0.0);budget=Budget()
        for task in plan['tasks']:
            validate_plan(plan)
            need(process.poll() is None and _owned_listener(process.pid,plan['port']),'Owned server unavailable before task')
            elapsed=time.monotonic()-started;remaining=_remaining_budget(budget,result['calls'],used,elapsed)
            job=output/'tasks'/task['task_id'];task_error=None
            journal.append('question_task_started',task_id=task['task_id'],request_sha256=task['request_sha256'],
                elapsed_seconds=elapsed,effective_budget=encode(decode(Budget,encode(remaining))))
            try:
                report=run_question_interpretation(plan['case']['path'],plan['snapshot']['path'],task['family'],job,
                    FrozenLocalQuestionInterpreter(check_pin(plan['model_config']),task['request_sha256'],
                        task['payload_sha256'],plan['model_config']['sha256']),
                    plan['catalog']['path'] if plan['catalog'] else None,
                    budget=remaining,max_claims=2,observation_ids=task['observation_ids'],adapter_verifier=verify_frozen_execution)
                verify_question_interpretation(job,adapter_verifier=verify_frozen_execution)
                _match_task(plan,task,job,report,remaining)
                need(report['calls']==1 and report['status']=='question_contract_completed_not_scientific_validation',
                     'Task was not generated and contract-verified')
                result['tasks'].append(dict(task_id=task['task_id'],receipt=pin(job/'receipt.json'),response=pin(job/'response.json')))
            except BaseException as error:task_error=error
            finally:
                try:
                    if (job/'journal.jsonl').is_file():
                        inspected=inspect_question_interpretation(job)
                        measured=decode(Usage,inspected['measured_usage']);estimated=decode(Usage,inspected['estimated_upper_usage'])
                        used=add_usage(used,add_usage(measured,estimated));result['calls']+=inspected['calls']
                        for name,value in [('measured_usage',measured),('estimated_usage',estimated)]:
                            result[name]=encode(add_usage(decode(Usage,result[name]),value))
                        journal.append('question_task_accounted',task_id=task['task_id'],calls=inspected['calls'],
                            measured_usage=encode(measured),estimated_usage=encode(estimated))
                except BaseException as account_error:
                    if task_error:task_error.add_note('Task accounting failed: '+type(account_error).__name__)
                    else:task_error=account_error
            if task_error:raise task_error
            write_json(output/'execution-report.json',result)
        result['status']='all_question_outputs_contract_verified'
    except BaseException as error:primary=error
    finally:
        if process is None:process=ownership.get('process')
        if process is not None:
            try:
                if process.poll() is None:process.terminate()
                try:process.wait(timeout=30)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
                result['server_stopped']=process.poll() is not None
                need(result['server_stopped'],'Owned server not stopped')
            except BaseException as error:secondary(error,'server_cleanup')
        if primary:result.update(status='failed',error_class=type(primary).__name__)
        try:write_json(output/'execution-report.json',result)
        except BaseException as error:secondary(error,'report_write')
        try:
            if primary:journal.fail(primary,'question_pilot_execution')
            else:journal.append('build_completed',report=pin(output/'execution-report.json'))
        except BaseException as error:secondary(error,'terminal_journal')
        if primary is None:
            try:
                seal=dict(role='question_predictions_sealed_before_scientific_review',
                    created_at_utc=datetime.now(timezone.utc).isoformat(),plan=plan_proof,
                    execution_report=pin(output/'execution-report.json'),tasks=result['tasks'],
                    proofs=[pin(output/name) for name in ['execution/journal.jsonl','preparation/journal.jsonl',
                        'server-command.json','server.stdout.log','server.stderr.log']],
                    fresh_holdout=False,scientific_quality='not_evaluated',clinical_probability=None)
                write_json(output/'predictions-seal.json',seal);seal_proof=pin(output/'predictions-seal.json')
            except BaseException as error:
                secondary(error,'prediction_seal');result.update(status='failed',error_class=type(primary).__name__)
                try:write_json(output/'execution-report.json',result)
                except BaseException as write_error:secondary(write_error,'failed_seal_report')
                try:journal.fail(primary,'question_prediction_seal')
                except BaseException as journal_error:secondary(journal_error,'failed_seal_journal')
        try:journal.close()
        except BaseException as error:secondary(error,'journal_close')
        if primary:
            result.update(status='failed',error_class=type(primary).__name__)
            try:write_json(output/'execution-report.json',result)
            except BaseException as error:secondary(error,'final_failure_report')
            try:write_json(output/'failure.json',dict(schema_version=1,status='failed',plan=plan_proof,
                error_class=type(primary).__name__,secondary_failures=result['secondary_failures'],
                qualification='Failed controller state; no prediction or scientific qualification'))
            except BaseException as error:secondary(error,'failure_snapshot')
    if primary:raise primary
    return seal_proof


def verify_predictions(proof):
    """Offline source-inclusive bundle verification; not execution attestation."""
    path=check_pin(proof);output=path.parent;seal=read_json(path)
    need(path.name=='predictions-seal.json' and not (output/'failure.json').exists(),'Failed or foreign pilot seal')
    need(set(seal)=={'role','created_at_utc','plan','execution_report','tasks','proofs','fresh_holdout',
         'scientific_quality','clinical_probability'} and seal['role']=='question_predictions_sealed_before_scientific_review' and
         seal['fresh_holdout'] is False and seal['scientific_quality']=='not_evaluated' and
         seal['clinical_probability'] is None,'Contradictory pilot seal')
    plan=read_json(check_pin(seal['plan']));need(output==Path(plan['root']).resolve() and
         check_pin(seal['plan'])==output/'run-plan.json','Pilot plan/root differs');validate_plan(plan)
    names=['execution/journal.jsonl','preparation/journal.jsonl','server-command.json','server.stdout.log','server.stderr.log']
    need(isinstance(seal['proofs'],list) and len(seal['proofs'])==len(names) and
         all(check_pin(p)==output/name for p,name in zip(seal['proofs'],names)),'Pilot lifecycle proofs differ')
    need(check_pin(seal['execution_report'])==output/'execution-report.json','Foreign pilot report')
    report=read_json(output/'execution-report.json')
    need(report['status']=='all_question_outputs_contract_verified' and report['server_stopped'] is True and
         type(report['calls']) is int and report['calls']==2 and report['plan']==seal['plan'] and
         report['tasks']==seal['tasks'] and len(seal['tasks'])==2 and report['secondary_failures']==[] and
         report['scientific_quality']=='not_evaluated' and report['clinical_probability'] is None and
         type(report['provider_spend_usd']) is int and report['provider_spend_usd']==0,'Pilot report inconsistent')
    events=read_chain(output/'execution/journal.jsonl')
    need(events[-1]['event']=='build_completed' and events[-1]['details']['report']==seal['execution_report'],
         'Pilot journal terminal/report differs')
    started=[e['details'] for e in events if e['event']=='question_task_started']
    accounted=[e['details'] for e in events if e['event']=='question_task_accounted']
    need(len(started)==len(accounted)==2,'Pilot task accounting incomplete')
    measured=Usage(0,0,0.0);estimated=Usage(0,0,0.0);last_elapsed=-1;budget=Budget()
    for index,(task,item) in enumerate(zip(plan['tasks'],seal['tasks'])):
        job=output/'tasks'/task['task_id']
        need(set(item)=={'task_id','receipt','response'} and item['task_id']==task['task_id'] and
             check_pin(item['receipt'])==job/'receipt.json' and check_pin(item['response'])==job/'response.json',
             'Pilot task output identity differs')
        verify_question_interpretation(job,adapter_verifier=verify_frozen_execution)
        inspected=inspect_question_interpretation(job);task_report=read_json(job/'report.json')
        elapsed=started[index].get('elapsed_seconds')
        need(type(elapsed) in (int,float) and 0<=elapsed<budget.max_seconds and elapsed>=last_elapsed,
             'Pilot task elapsed time outside shared budget')
        last_elapsed=elapsed;remaining=_remaining_budget(budget,index,add_usage(measured,estimated),elapsed)
        _match_task(plan,task,job,task_report,remaining)
        need(inspected['calls']==1 and not inspected['unresolved_attempts'] and inspected['failure'] is None and
             fingerprint(read_json(job/'request.json'))==task['request_sha256']==task_report['request_sha256'] and
             started[index]==dict(task_id=task['task_id'],request_sha256=task['request_sha256'],elapsed_seconds=elapsed,
                 effective_budget=encode(decode(Budget,encode(remaining)))),
             'Pilot task differs from frozen request')
        detail=dict(task_id=task['task_id'],calls=1,measured_usage=encode(decode(Usage,inspected['measured_usage'])),
            estimated_usage=encode(decode(Usage,inspected['estimated_upper_usage'])))
        need(fingerprint(accounted[index])==fingerprint(detail),'Pilot journal/task usage differs')
        measured=add_usage(measured,decode(Usage,inspected['measured_usage']))
        estimated=add_usage(estimated,decode(Usage,inspected['estimated_upper_usage']))
    need(fingerprint(report['measured_usage'])==fingerprint(encode(measured)) and
         fingerprint(report['estimated_usage'])==fingerprint(encode(estimated)),'Pilot aggregate usage differs')
    return dict(status='source_inclusive_question_pilot_mechanics_verified',calls=2,
        source_admission='replayed',scientific_validation='not_performed',execution_attestation=False,
        measured_usage=encode(measured),estimated_usage=encode(estimated),clinical_probability=None)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--sha256',required=True);args=parser.parse_args()
    proof=pin(args.plan);need(proof['sha256']==args.sha256,'Explicit frozen plan hash differs');print(execute(proof))


if __name__=='__main__':main()
