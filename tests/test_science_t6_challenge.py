"""Source-only top-one task construction; no native model or scientific claims."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from tether_engine.chrono import load_snapshot
from tether_engine.contracts import Case, Category, EvidenceStatus
from tether_engine.retrieval import RetrievalPolicy
from tether_engine.serde import ContractError, decode, encode, fingerprint, read_json, sha256_file, write_json
from tools.science.comparison_workflow import STAGES
from tools.science.run_comparison import selected_store, pin
from tools.science.t6_challenge import freeze_tasks, task_store, check_reference, execute

ROOT=Path(__file__).resolve().parents[1]


class TopOneTaskTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve(); folder=self.root/'source'
        shutil.copytree(ROOT/'src/tether_engine/demo/v2',folder)
        packet=read_json(folder/'evidence.json')
        original=packet['observations'][0]
        rows=[]
        for category in Category:
            for index in range(3):
                row=deepcopy(original); row.update(observation_id=category.value+'-'+str(index),category=category.value,features={})
                rows.append(row)
        packet['observations']=rows; write_json(folder/'evidence.json',packet)
        snapshot=read_json(folder/'snapshot.json')
        snapshot['artifacts'][0]['sha256']=sha256_file(folder/'evidence.json'); write_json(folder/'snapshot.json',snapshot)
        self.case=replace(decode(Case,read_json(folder/'case.json')),task='T6',endpoint=None)
        self.store=load_snapshot(folder/'snapshot.json',self.case)
        self.policy={'schema_version':1,'stage_order':list(STAGES),'control_reserve_bytes':2048,
            'stage_guidance':{s:'Select provided source identifiers only.' for s in STAGES},
            'specialists':{c.value:'fixture' for c in Category},'selection_cap':1}
        self.retrieval=RetrievalPolicy(max_records=12,max_request_bytes=12000,wire_format='tether-shared-scientific-fields-v1')

    def test_task_projection_preserves_complete_parent_and_source_proofs(self):
        projected,proof=task_store(self.case,self.store,Category.GENETICS)
        self.assertEqual(len(projected.query(self.case,Category.GENETICS)),3)
        self.assertEqual(projected.query(self.case,Category.EXPRESSION),())
        self.assertEqual(fingerprint(projected.source_proofs),fingerprint(self.store.source_proofs))
        self.assertEqual(proof['parent_selection']['full_admitted_observed'],3*len(Category))
        self.assertEqual(len(proof['projected_records']),3)
        with self.assertRaises(ContractError): selected_store(self.case,self.store,maximum=3)

    def test_deterministic_all_dispositions_and_per_case_cap(self):
        frozen=freeze_tasks([(self.case,self.store)],self.policy,self.retrieval)
        self.assertEqual(len(frozen['tasks']),2)
        self.assertEqual([r['category'] for r in frozen['tasks']],[c.value for c in Category][:2])
        self.assertEqual(len(frozen['dispositions']),len(Category))
        self.assertTrue(all(r['disposition']=='beyond_case_cap' for r in frozen['dispositions'][2:]))
        self.assertFalse(frozen['reference_answers_opened'])
        self.assertEqual(fingerprint(frozen),fingerprint(freeze_tasks([(self.case,self.store)],self.policy,self.retrieval)))
        for task in frozen['tasks']:
            self.assertEqual(task['offered_count'],len(task['request']['evidence']))
            self.assertEqual(task['request_sha256'],fingerprint(task['request']))
            self.assertTrue(all(r['scientific_record_json'] for r in task['request']['evidence']))

    def test_total_cap_uses_original_case_order(self):
        sources=[(replace(self.case,case_id='fixture-'+str(i)),self.store) for i in range(6)]
        frozen=freeze_tasks(sources,self.policy,self.retrieval)
        self.assertEqual(len(frozen['tasks']),8)
        self.assertEqual([r['case_id'] for r in frozen['tasks']],sum((['fixture-'+str(i)]*2 for i in range(4)),[]))
        self.assertTrue(all(r['disposition']=='beyond_total_cap' for r in frozen['dispositions'][4*len(Category):]))

    def test_whole_record_bound_can_leave_no_eligible_tasks(self):
        tiny=RetrievalPolicy(max_records=1,max_request_bytes=12000,wire_format='tether-shared-scientific-fields-v1')
        frozen=freeze_tasks([(self.case,self.store)],self.policy,tiny)
        self.assertEqual(frozen['tasks'],[])
        self.assertTrue(all(r['disposition']=='insufficient_offered_candidates' for r in frozen['dispositions']))

    def test_non_topone_or_changed_caps_rejected(self):
        for policy in ({**self.policy,'selection_cap':3},{**self.policy,'selection_cap':True}):
            with self.subTest(policy=policy):
                with self.assertRaises(ContractError): freeze_tasks([(self.case,self.store)],policy,self.retrieval)
        with self.assertRaises(ContractError): freeze_tasks([(self.case,self.store)],self.policy,self.retrieval,maximum_tasks=9)

    def test_reference_gate_only_opens_metadata_and_hashes_children(self):
        approved=self.root/'data/benchmark/gold_evidence/t6-topone-20261023'; approved.mkdir(parents=True)
        children=[]
        for name in ('review-a','review-b','adjudication'):
            p=approved/(name+'.json'); p.write_bytes(b'not JSON: must never be parsed by launcher'); children.append(pin(p))
        tasks=self.root/'tasks.json'; write_json(tasks,{'fixture':True})
        manifest=approved/'freeze.json'
        seal={'schema_version':1,'role':'evaluation_only','status':'sealed_source_only_AI_reference',
            'task_manifest':pin(tasks),'reviews':children[:2],'adjudication':children[2],
            'limitations':'AI source-only reference','created_at_utc':'2026-10-23T00:00:00+00:00'}
        write_json(manifest,seal)
        with patch('tools.science.t6_challenge.ROOT',self.root):
            self.assertEqual(check_reference(pin(manifest),pin(tasks)),seal)
            Path(children[0]['path']).write_bytes(b'changed')
            with self.assertRaises(ContractError): check_reference(pin(manifest),pin(tasks))

    def test_reference_gate_rejects_duplicate_review_or_task_mismatch(self):
        approved=self.root/'data/benchmark/gold_evidence/t6-topone-20261023'; approved.mkdir(parents=True)
        p=approved/'review.json'; write_json(p,{}); reference=pin(p)
        manifest=approved/'freeze.json'; task={'path':'fixture','sha256':'a'*64,'bytes':1}
        seal={'schema_version':1,'role':'evaluation_only','status':'sealed_source_only_AI_reference',
            'task_manifest':task,'reviews':[reference,reference],'adjudication':reference,
            'limitations':'AI reference','created_at_utc':'2026-10-23T00:00:00+00:00'}
        write_json(manifest,seal)
        with patch('tools.science.t6_challenge.ROOT',self.root):
            with self.assertRaises(ContractError):check_reference(pin(manifest),task)
            with self.assertRaises(ContractError):check_reference(pin(manifest),{**task,'sha256':'b'*64})

    def test_invalid_reference_stops_before_server_and_keeps_single_use_failure(self):
        output=self.root/'runs/failed'; output.mkdir(parents=True)
        plan=output/'run-plan.json'; write_json(plan,{'root':str(output),'tasks':{'fixture':True}})
        reference=self.root/'reference.json'; write_json(reference,{})
        with patch('tools.science.t6_challenge.ROOT',self.root), \
                patch('tools.science.t6_challenge.validate_plan',return_value=([],{'tasks':[{'task_id':'fixture'}]})), \
                patch('tools.science.t6_challenge.check_reference',side_effect=ContractError('unsealed reference')), \
                patch('tools.science.t6_challenge.verify_model') as model, \
                patch('tools.science.t6_challenge.port_closed',return_value=True):
            with self.assertRaisesRegex(ContractError,'unsealed reference'):
                execute(plan,sha256_file(plan),reference,sha256_file(reference))
            model.assert_not_called()
            self.assertEqual(read_json(output/'execution-report.json')['status'],'failed')
            self.assertTrue((output/'execution/journal.jsonl').is_file())
            self.assertFalse((output/'predictions-seal.json').exists())
            with self.assertRaises(FileExistsError):
                execute(plan,sha256_file(plan),reference,sha256_file(reference))

    def test_port_not_closed_prevents_success_seal(self):
        output=self.root/'runs/cleanup'; output.mkdir(parents=True)
        server=self.root/'synthetic-server'; server.write_bytes(b'no actual execution')
        receipt=self.root/'receipt.json'; write_json(receipt,{'revision':'fixture','items':[]})
        reference=self.root/'reference.json'; write_json(reference,{})
        plan=output/'run-plan.json'; write_json(plan,{'root':str(output),'tasks':{},
            'model_receipt':pin(receipt),'role_policy':pin(receipt),'execution_order':[],
            'backend':{'retrieval':{},'max_output_tokens':1,'timeout_seconds':1,'seed':1,'selection_cap':1}})
        process=MagicMock(); process.pid=99999
        process.poll.side_effect=[None,None,0,0]
        response=MagicMock(); response.__enter__.return_value.status=200
        opener=MagicMock(); opener.open.return_value=response
        with patch('tools.science.t6_challenge.ROOT',self.root), \
                patch('tools.science.t6_challenge.validate_plan',return_value=([],{'tasks':[{'task_id':'fixture'}]})), \
                patch('tools.science.t6_challenge.check_reference',return_value={}), \
                patch('tools.science.t6_challenge.verify_model',return_value=(server,server)), \
                patch('tools.science.t6_challenge.subprocess.Popen',return_value=process), \
                patch('tools.science.t6_challenge.socket.socket'), \
                patch('tools.science.t6_challenge.urllib.request.build_opener',return_value=opener), \
                patch('tools.science.t6_challenge._owned_listener',return_value=True), \
                patch('tools.science.t6_challenge.port_closed',return_value=False):
            result=execute(plan,sha256_file(plan),reference,sha256_file(reference))
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['error_class'],'CleanupVerificationError')
        self.assertFalse((output/'predictions-seal.json').exists())

    def lifecycle_fixture(self, stack, name):
        output=self.root/'runs'/name; output.mkdir(parents=True)
        server=self.root/'synthetic-server'; server.write_bytes(b'no native execution')
        receipt=self.root/'receipt.json'; write_json(receipt,{'revision':'fixture','items':[]})
        reference=self.root/'reference.json'; write_json(reference,{})
        roles=self.root/'roles.json'; write_json(roles,self.policy)
        frozen=freeze_tasks([(self.case,self.store)],self.policy,self.retrieval)
        task=frozen['tasks'][0]
        plan=output/'run-plan.json'; write_json(plan,{'root':str(output),'tasks':{},'code':[],
            'model_receipt':pin(receipt),'role_policy':pin(roles),
            'budget':{'max_calls':16,'max_input_tokens':32000,'max_output_tokens':8000,
                      'max_cost_usd':0,'max_seconds':300,'max_retries':1},
            'execution_order':[{'task_id':task['task_id'],'arms':['tether','lexical']}],
            'backend':{'retrieval':encode(self.retrieval),'max_output_tokens':1,
                       'timeout_seconds':1,'seed':1,'selection_cap':1}})
        process=MagicMock(); process.pid=99999
        process.poll.side_effect=lambda: 0 if process.wait.called else None
        response=MagicMock(); response.__enter__.return_value.status=200
        opener=MagicMock(); opener.open.return_value=response
        mocks={}
        values={'ROOT':self.root,'validate_plan':None,'check_reference':{},
                'verify_model':(server,server),'subprocess.Popen':process,
                'socket.socket':None,'urllib.request.build_opener':opener,
                '_owned_listener':True,'port_closed':True,'PinnedRoleSelectionBackend':MagicMock()}
        for key,value in values.items():
            kwargs=({'new':value} if key=='ROOT' else {} if key=='socket.socket' else {'return_value':value})
            mocks[key]=stack.enter_context(patch('tools.science.t6_challenge.'+key,**kwargs))
        mocks['validate_plan'].return_value=([(self.case,self.store)],{'tasks':[task]})
        return output,plan,reference,process,opener,mocks

    def test_occupied_port_has_zero_native_dispatch(self):
        with ExitStack() as stack:
            output,plan,reference,process,opener,mocks=self.lifecycle_fixture(stack,'occupied')
            mocks['socket.socket'].return_value.__enter__.return_value.bind.side_effect=OSError('occupied')
            with self.assertRaises(OSError): execute(plan,sha256_file(plan),reference,sha256_file(reference))
            mocks['subprocess.Popen'].assert_not_called()
            self.assertEqual(read_json(output/'execution-report.json')['status'],'failed')
            self.assertFalse((output/'predictions-seal.json').exists())

    def test_startup_interruption_and_cleanup_error_leave_terminal_record(self):
        for cleanup_failure in (False,True):
            with self.subTest(cleanup_failure=cleanup_failure), ExitStack() as stack:
                output,plan,reference,process,opener,mocks=self.lifecycle_fixture(stack,'interrupt'+str(cleanup_failure))
                opener.open.side_effect=KeyboardInterrupt()
                if cleanup_failure: process.terminate.side_effect=OSError('cleanup failed')
                with self.assertRaises(KeyboardInterrupt):
                    execute(plan,sha256_file(plan),reference,sha256_file(reference))
                process.terminate.assert_called_once()
                report=read_json(output/'execution-report.json')
                self.assertEqual(report['status'],'failed')
                self.assertEqual(bool(report['cleanup_errors']),cleanup_failure)
                self.assertFalse((output/'predictions-seal.json').exists())

    def test_failed_arm_stops_before_any_redispatch(self):
        with ExitStack() as stack:
            output,plan,reference,process,opener,mocks=self.lifecycle_fixture(stack,'partial')
            result={'claims':[],'features':{},'probability':None,'status':'failed','calls':1,'usage':{}}
            calls=stack.enter_context(patch('tools.science.t6_challenge.run_case',return_value=result))
            stack.enter_context(patch('tools.science.t6_challenge.verify_case',return_value={}))
            # Synthetic arm files stand in for a retained failed attempt, without a native call.
            def failed(*args,**kwargs):
                folder=args[5]; folder.mkdir(parents=True)
                write_json(folder/'result.json',result); write_json(folder/'seal.json',{})
                return result
            calls.side_effect=failed
            with self.assertRaises(ContractError): execute(plan,sha256_file(plan),reference,sha256_file(reference))
            self.assertEqual(calls.call_count,1)
            self.assertEqual(read_json(output/'execution-report.json')['tasks'][0]['arms'][0]['status'],'failed')
            process.terminate.assert_called_once()

    def test_concurrent_execution_reservation_allows_only_one_owner(self):
        with ExitStack() as stack:
            output,plan,reference,process,opener,mocks=self.lifecycle_fixture(stack,'concurrent')
            entered,released=Event(),Event()
            def stop_after_reservation(value):
                entered.set()
                self.assertTrue(released.wait(5))
                raise ContractError('fixture predispatch stop')
            mocks['validate_plan'].side_effect=stop_after_reservation
            with ThreadPoolExecutor(max_workers=1) as executor:
                future=executor.submit(execute,plan,sha256_file(plan),reference,sha256_file(reference))
                self.assertTrue(entered.wait(5))
                try:
                    with self.assertRaises(FileExistsError):
                        execute(plan,sha256_file(plan),reference,sha256_file(reference))
                finally: released.set()
                with self.assertRaises(ContractError): future.result(timeout=5)
            mocks['verify_model'].assert_not_called()


if __name__=='__main__': unittest.main()
