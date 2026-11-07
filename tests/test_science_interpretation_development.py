"""Frozen development-launcher gates; no native process, model or network."""
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_science_local_interpretation as fixtures
from tether_engine.serde import ContractError,read_json,write_json,encode
from tether_engine.journal import read_chain,RunJournal
from tether_engine.agents import Usage
from tools.science.run_comparison import pin,check_pin
from tools.science import run_interpretation_development as launch


class InterpretationDevelopmentTests(unittest.TestCase):
    def setUp(self):fixtures.LocalInterpretationTests.setUp(self)

    def prepare(self):
        receipt=self.root/'model-receipt.json';reference=self.root/'reference.json'
        write_json(receipt,dict(status='downloaded_hash_verified_not_inference_validated',
            root=str(self.root/'models'),revision='fictional-revision',
            runtime_files=[dict(path='runtime/llama-server.exe',sha256='1'*64)],
            items=[dict(name='fixture.gguf',sha256='0'*64)]))
        write_json(reference,dict(role='evaluation_only',fixture=True))
        return launch.prepare(self.root/'pilot',self.inputs/'case.json',self.inputs/'snapshot.json',None,
            [dict(task_id='fixture',observation_ids=self.ids)],receipt,reference)

    def test_valid_plan_has_no_evaluator_content_in_model_request(self):
        plan=read_json(check_pin(self.prepare()));launch.validate_plan(plan)
        request=read_json(check_pin(plan['tasks'][0]['request']))
        self.assertNotIn('reference_seal',request);self.assertFalse(plan['evaluator_content_in_model_requests'])

    def test_model_weight_provenance_matches_receipt(self):
        plan=read_json(check_pin(self.prepare()));config_path=Path(plan['model_config']['path']);config=read_json(config_path)
        config['model_provenance']['weights_sha256']['fixture.gguf']='f'*64
        write_json(config_path,config);plan['model_config']=pin(config_path)
        with self.assertRaises(ContractError):launch.validate_plan(plan)

    def test_report_failure_keeps_original_error_terminal_and_closed(self):
        for name,fail_report in [('ordinary',False),('disk-failure',True)]:
            output=self.root/name;output.mkdir();plan=output/'run-plan.json';write_json(plan,dict(root=str(output)))
            original=launch.write_json
            def write(path,value):
                if fail_report and path.name=='execution-report.json':raise OSError('fixture disk failure')
                return original(path,value)
            with (patch.object(launch,'validate_plan',side_effect=ContractError('original failure')),
                  patch.object(launch,'write_json',side_effect=write),patch.object(launch.subprocess,'Popen') as opened):
                with self.assertRaises(ContractError):launch.execute(pin(plan))
                opened.assert_not_called()
            journal=output/'execution/journal.jsonl';events=read_chain(journal)
            self.assertEqual(events[-1]['event'],'build_failed')
            moved=journal.with_name('closed-journal.jsonl');journal.rename(moved);moved.rename(journal)

    def test_existing_output_not_replaced(self):
        proof=self.prepare()
        with self.assertRaises(FileExistsError):self.prepare()
        check_pin(proof)

    def test_missing_code_proof_rejected(self):
        plan=read_json(check_pin(self.prepare()));plan['code']=plan['code'][1:]
        with self.assertRaises(ContractError):launch.validate_plan(plan)

    def test_resealed_request_cannot_change_source_scope(self):
        plan=read_json(check_pin(self.prepare()));task=plan['tasks'][0];path=Path(task['request']['path'])
        request=read_json(path);request['hypothesis_key']='changed';write_json(path,request)
        task['request']=pin(path)
        with self.assertRaises(ContractError):launch.validate_plan(plan)

    def test_default_shared_budget_is_preserved(self):
        plan=read_json(check_pin(self.prepare()));plan['budget']['max_cost_usd']=1
        with self.assertRaises(ContractError):launch.validate_plan(plan)

    def test_repair_claim_cap_is_bound_into_frozen_request(self):
        proof=self.prepare();original=read_json(check_pin(proof))
        repaired=launch.prepare(self.root/'repair',self.inputs/'case.json',self.inputs/'snapshot.json',None,
            [dict(task_id='fixture',observation_ids=self.ids)],original['model_receipt']['path'],
            original['reference_seal']['path'],max_claims=2,max_prompt_bytes=14200)
        plan=read_json(check_pin(repaired));launch.validate_plan(plan)
        request=read_json(check_pin(plan['tasks'][0]['request']))
        self.assertEqual(request['bounds']['max_claims'],2)
        self.assertEqual(read_json(check_pin(plan['model_config']))['max_prompt_bytes'],14200)

    def test_task_timeout_and_report_failure_keep_primary_cause(self):
        proof=self.prepare();server=self.root/'fake-server.exe';server.write_bytes(b'never executed')
        class Process:
            pid=1234;stopped=False
            def poll(self):return 0 if self.stopped else None
            def terminate(self):self.stopped=True
            def wait(self,timeout):self.stopped=True;return 0
        process=Process()
        class Health:
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):pass
        class Opener:
            def open(self,*args,**kwargs):return Health()
        def fail_task(case,snapshot,job,backend,*args,**kwargs):
            journal=RunJournal(job,kind='build')
            journal.append('interpretation_accounted',basis='conservative_quote',usage=encode(Usage(2,3,0)))
            journal.fail(TimeoutError('original timeout'),'dispatch');journal.close()
            raise TimeoutError('original timeout')
        original=launch.write_json;counter={'writes':0}
        def fail_report(path,value):
            if path.name=='execution-report.json':
                counter['writes']+=1
                if counter['writes']==1:raise OSError('report fixture failure')
            return original(path,value)
        with (patch.object(launch,'verify_model',return_value=(server,self.root/'fake.gguf')),
              patch.object(launch,'sha256_file',return_value='1'*64),patch.object(launch.socket,'socket'),
              patch.object(launch.subprocess,'Popen',return_value=process),
              patch.object(launch.urllib.request,'build_opener',return_value=Opener()),
              patch.object(launch,'_owned_listener',return_value=True),
              patch.object(launch,'run_interpretation',side_effect=fail_task),
              patch.object(launch,'write_json',side_effect=fail_report)):
            with self.assertRaises(TimeoutError):launch.execute(proof)
        self.assertTrue(process.stopped)
        events=read_chain(self.root/'pilot/execution/journal.jsonl')
        self.assertEqual(events[-1]['event'],'build_failed')
        self.assertEqual(events[-1]['details']['error_class'],'TimeoutError')


if __name__=='__main__':unittest.main()
