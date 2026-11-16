"""Whole workflow/physical-call regressions; no native server or scientific claims."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import io
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch

from tether_engine.chrono import load_snapshot
from tether_engine.contracts import Case, Category
from tether_engine.local_model import LocalSelectionBackend
from tools.science.role_backend import RoleSelectionBackend
from tether_engine.serde import ContractError, canonical, decode, fingerprint, parse_json, read_json, sha256_file, write_json
from tether_engine.workflow import Budget
from tools.science.comparison_workflow import STAGES, run_case, verify_case, _seal


from tests.workflow_fixtures import ComparisonWorkflowFixture, NativeFixture, synthetic_policy


class ComparisonWorkflowTests(ComparisonWorkflowFixture, unittest.TestCase):
    def setUp(self):
        self.prepare(self.addCleanup)

    def test_adapted_executes_five_real_stages_and_exact_source_claims(self):
        result,out,backend = self.run_arm('adapted_virtual_biotech')
        self.assertEqual(result['calls'],5)
        self.assertEqual(len(backend.opener.calls),5)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['features'],{})
        self.assertIsNone(result['probability'])
        self.assertEqual(self.verify(out)['semantic_consistency'],'passed')
        self.assertEqual(result['usage']['input_tokens'],50)
        for claim in result['claims']:
            self.assertEqual(claim['source_claim_sha256'],fingerprint(self.store.lookup(claim['observation_id'])))

    def test_tether_single_specialist_and_actual_ablation_dispatch(self):
        full,_,b = self.run_arm()
        removed,_,r = self.run_arm('no_literature')
        self.assertEqual(full['calls'],1)
        self.assertEqual(removed['calls'],1)
        self.assertIsNot(b,r)
        for call in r.records:
            self.assertNotEqual(call['request'].category,Category.LITERATURE)
        self.assertEqual(len(r.opener.calls),1)

    def test_disabled_category_has_zero_backend_calls_before_retrieval(self):
        from tether_engine.chrono import EvidenceStore
        records = tuple(replace(r,observation=replace(r.observation,category=Category.LITERATURE))
                        for r in self.store.query(self.case,Category.GENETICS))
        self.store = EvidenceStore(self.store.snapshot,records,(),(),None)
        result,out,backend = self.run_arm('no_literature')
        self.assertEqual(result['calls'],0)
        self.assertFalse(backend.opener.calls)
        self.assertEqual(result['coverage']['literature']['status'],'disabled_before_retrieval')
        self.verify(out)

    def test_stopped_chain_never_commits_intermediate_selections(self):
        result,out,backend = self.run_arm('adapted_virtual_biotech',max_calls=4)
        self.assertEqual(result['status'],'budget_exhausted')
        self.assertEqual(result['calls'],4)
        self.assertEqual(result['claims'],[])
        self.verify(out)

    def test_time_expiry_during_claim_commit_retains_only_reviewed_committed_prefix(self):
        from copy import deepcopy
        from tether_engine.journal import RunJournal
        packet=read_json(self.fixture/'evidence.json')
        extra=deepcopy(packet['observations'][0]);extra['observation_id']='second-fixture-genetics-row'
        packet['observations'].append(extra)
        write_json(self.fixture/'evidence.json',packet)
        snapshot=read_json(self.fixture/'snapshot.json')
        snapshot['artifacts'][0]['sha256']=sha256_file(self.fixture/'evidence.json')
        write_json(self.fixture/'snapshot.json',snapshot)
        self.store=load_snapshot(self.fixture/'snapshot.json',self.case)
        now={'value':0.0};original=RunJournal.append
        def append(journal,kind,**details):
            result=original(journal,kind,**details)
            if kind=='claim_committed':now['value']=2.0
            return result
        with patch('tools.science.comparison_workflow.time.monotonic',lambda:now['value']),patch.object(RunJournal,'append',append):
            result,out,_=self.run_arm(backend=self.backend(take=2),max_seconds=1)
        self.assertEqual(result['status'],'budget_exhausted')
        self.assertEqual(len(result['claims']),1)
        self.assertEqual(result['coverage']['genetics']['selected'],1)
        self.verify(out)

    def test_timeout_is_durable_estimated_and_never_implicitly_repeated(self):
        result,out,backend = self.run_arm(backend=self.backend(error=TimeoutError('fixture')))
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['calls'],1)
        self.assertGreater(result['estimated_usage']['input_tokens'],0)
        self.assertEqual(result['measured_usage']['input_tokens'],0)
        self.verify(out)
        with self.assertRaises(FileExistsError):
            run_case(self.case,self.store,backend,Budget(),'tether',out,self.policy)
        self.assertEqual(len(backend.opener.calls),1)

    def test_malformed_and_interruption_keep_attempt_accounting(self):
        for name,opts in (('malformed',{'malformed':True}),('interrupted',{'error':KeyboardInterrupt()})):
            backend=self.backend(**opts);out=self.root/name
            result=run_case(self.case,self.store,backend,Budget(),'tether',out,self.policy)
            self.assertEqual(result['calls'],1)
            self.assertEqual(result['claims'],[])
            self.assertIn(result['status'],('failed','interrupted'))
            self.verify(out)

    def test_parallel_output_reservation_allows_only_one_execution(self):
        barrier=threading.Barrier(2)
        output=self.root/'same-output'
        def attempt():
            b=self.backend();barrier.wait()
            try:
                run_case(self.case,self.store,b,Budget(),'tether',output,self.policy)
                return len(b.opener.calls)
            except FileExistsError:
                return 0
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(lambda _:attempt(),range(2))),[0,1])

    def test_baselines_never_generate_features_or_call_a_model(self):
        for arm in ('lexical','provider_score'):
            result,out,backend=self.run_arm(arm)
            self.assertEqual(result['calls'],0)
            self.assertEqual(result['features'],{})
            self.assertIsNone(result['probability'])
            self.assertFalse(backend.opener.calls)
            self.verify(out)

    def test_zero_call_baseline_still_requires_expected_backend_configuration(self):
        _,out,_=self.run_arm('lexical')
        changed=dict(self.config,seed=self.config['seed']+1)
        with self.assertRaisesRegex(ContractError,'configuration'):
            verify_case(out,self.case,self.store,changed,self.policy)

    def test_zero_call_baseline_cannot_reseal_a_different_retrieval_policy(self):
        _,out,_=self.run_arm('lexical')
        result=read_json(out/'result.json')
        result['configuration']['retrieval']['max_records']+=1
        write_json(out/'result.json',result)
        self.rebind(out,lambda e:e['details']['configuration']['retrieval'].update(max_records=13)
                    if e['event']=='comparison_plan' else None)
        with self.assertRaisesRegex(ContractError,'configuration'):
            self.verify(out)

    def test_source_data_is_not_a_filesystem_capability(self):
        canary='PRIVATE-EVALUATOR-ANSWER-CANARY-729'
        secret=self.root/'private-gold-answer.txt';secret.write_text(canary)
        _,_,backend=self.run_arm()
        prompts=b'\n'.join(backend.opener.calls).decode()
        self.assertNotIn(canary,prompts)
        self.assertNotIn(str(secret),prompts)
        self.assertNotIn(str(self.fixture),prompts)

    def test_corrupted_bytes_and_rehashed_source_claim_are_rejected(self):
        _,out,_=self.run_arm()
        result=read_json(out/'result.json');result['claims'][0]['evidence']['observation']['statement']='fabricated'
        write_json(out/'result.json',result)
        _seal(out)
        with self.assertRaises(ContractError): self.verify(out)

    def test_rehashed_coverage_cannot_invent_source_count(self):
        _,out,_=self.run_arm()
        result=read_json(out/'result.json')
        result['coverage']['genetics']['available_in_collected_case_world']+=99
        write_json(out/'result.json',result);self.rebind(out)
        with self.assertRaises(ContractError):self.verify(out)

    def test_rehashed_status_cannot_invent_budget_exhaustion(self):
        _,out,_=self.run_arm()
        result=read_json(out/'result.json');result['status']='budget_exhausted'
        write_json(out/'result.json',result)
        self.rebind(out,lambda e:e['details'].update(status='budget_exhausted') if e['event']=='comparison_finalized' else None)
        with self.assertRaises(ContractError):self.verify(out)

    def test_rehashed_quote_cannot_hide_underreservation(self):
        _,out,_=self.run_arm()
        self.rebind(out,lambda e:e['details']['reserved'].update(input_tokens=1) if e['event']=='dispatch' else None)
        with self.assertRaises(ContractError):self.verify(out)

    def test_completed_native_category_cannot_be_omitted_from_result(self):
        _,out,_=self.run_arm()
        result=read_json(out/'result.json');result['selections'].pop('genetics')
        result['claims']=[];result['coverage']['genetics']['selected']=0
        write_json(out/'result.json',result)
        events=[parse_json(line) for line in (out/'journal.jsonl').read_bytes().splitlines()]
        (out/'journal.jsonl').write_bytes(b'\n'.join(canonical(e) for e in events if e['event']!='claim_committed')+b'\n')
        # Rebind sequence as well, so this tests semantics after valid byte sealing.
        self.resequence(out)
        with self.assertRaises(ContractError):self.verify(out)

    def test_completed_native_category_cannot_be_hidden_by_false_disposition(self):
        _,out,_=self.run_arm()
        result=read_json(out/'result.json');result['selections']['genetics']=[]
        result['claims']=[];result['coverage']['genetics'].update(selected=0,status='not_run_after_budget_or_failure')
        write_json(out/'result.json',result)
        events=[parse_json(line) for line in (out/'journal.jsonl').read_bytes().splitlines()]
        (out/'journal.jsonl').write_bytes(b'\n'.join(canonical(e) for e in events if e['event']!='claim_committed')+b'\n')
        self.resequence(out)
        with self.assertRaises(ContractError):self.verify(out)

    def resequence(self,out):
        events=[parse_json(line) for line in (out/'journal.jsonl').read_bytes().splitlines()]
        for i,e in enumerate(events):e['sequence']=i
        (out/'journal.jsonl').write_bytes(b'\n'.join(canonical(e) for e in events)+b'\n')
        self.rebind(out)


if __name__ == '__main__':
    unittest.main()
