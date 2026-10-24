"""Bounded top-one selection and legacy-byte regressions; no native model runs."""
from copy import deepcopy
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest

from asof.agents import EvidenceView, Selection, SpecialistRequest, Usage
from asof.chrono import load_snapshot
from asof.contracts import Category
from asof.local_model import (LocalSelectionBackend, parse_selection, selection_payload,
                              validate_selection_cap, verify_backend_execution)
from asof.serde import ContractError, canonical, encode, fingerprint, read_json, sha256_file, write_json
from asof.wire import FORMAT
from asof.workflow import Budget
from tools.science import comparison_workflow as comparison
from tools.science.role_backend import RoleSelectionBackend, STAGES, role_allowed_ids, role_selection_payload
from tests import test_science_comparison_workflow as fixtures


class ResponseFixture:
    def __init__(self, selected):
        self.selected, self.calls = selected, []

    def open(self, request, timeout):
        self.calls.append(request)
        return io.BytesIO(canonical({'content': json.dumps({'observation_ids': self.selected}),
                                    'tokens_evaluated': 10, 'tokens_predicted': 5, 'truncated': False}))


class SelectionCapTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'config.json'
        self.config = {'schema_version':1,'endpoint':'http://127.0.0.1:55581','model_id':'synthetic-only',
            'model_provenance':{'weights_sha256':{'fixture':'a'*64},'runtime_sha256':'b'*64},
            'retrieval':{'max_records':12,'max_request_bytes':12000},
            'max_output_tokens':256,'timeout_seconds':2,'seed':123}
        self.request = SpecialistRequest('{"action":"inhibit"}', Category.GENETICS,
            tuple(EvidenceView(str(i), 'evidence '+str(i), 'source', '{}') for i in range(4)), 'select IDs', ())

    def backend(self, selected, cap=1, role=False):
        write_json(self.path, {**self.config, 'selection_cap': cap})
        backend = (RoleSelectionBackend if role else LocalSelectionBackend)(self.path)
        backend.opener = ResponseFixture(selected)
        return backend

    def role_request(self, stage, choices):
        prior = [{'role': s, 'observation_ids': ids} for s, ids in zip(STAGES, choices)]
        return replace(self.request, instructions='Role: '+stage+'; mapped upstream specialist: fixture.',
            feedback=(canonical({'prior_role_choices': prior}).decode(),) if prior else ())

    def test_default_payload_bytes_match_prechange_fingerprints(self):
        hashes = {'canonical':'863590c2e1fc406e7264d6819f96e415c35fb9fb117b87e7ea75467ff4b9d005',
                  FORMAT:'0d6c4887797e650d38d6da6c7b90d49f1594aa555e83b7fd43c3f4a7376dae29'}
        for wire, expected in hashes.items():
            payload = selection_payload(self.request, 256, 123, wire)
            self.assertEqual(expected, fingerprint(payload))
            self.assertEqual(payload, selection_payload(self.request,256,123,wire,selection_cap=3))
        write_json(self.path, self.config)
        backend = LocalSelectionBackend(self.path)
        self.assertEqual(self.config, backend.provenance['config'])
        self.assertNotIn('selection_cap', backend.provenance['config'])

    def test_cap_binds_prompt_schema_and_preserves_all_candidates(self):
        for cap, word in ((1,'one'),(2,'two')):
            payload = selection_payload(self.request,256,123,selection_cap=cap)
            output = payload['json_schema']['properties']['observation_ids']
            self.assertEqual(cap,output['maxItems'])
            self.assertEqual(['0','1','2','3'],output['items']['enum'])
            self.assertIn('Select up to '+word+' relevant evidence ID',payload['prompt'])
            for row in self.request.evidence:
                self.assertIn(row.statement,payload['prompt'])

    def test_invalid_caps_fail_at_all_policy_entry_points(self):
        for cap in (True,False,0,-1,4,1.0,'1',None):
            with self.subTest(cap=cap):
                for call in (lambda:validate_selection_cap(cap),
                             lambda:selection_payload(self.request,256,123,selection_cap=cap),
                             lambda:parse_selection({},[],selection_cap=cap),
                             lambda:role_allowed_ids(self.request,cap),
                             lambda:comparison._baseline(self.request,'lexical',cap),
                             lambda:comparison._policy({**fixtures.synthetic_policy(),'selection_cap':cap})):
                    with self.assertRaises(ContractError): call()
                write_json(self.path,{**self.config,'selection_cap':cap})
                with self.assertRaises(ContractError): LocalSelectionBackend(self.path)

    def test_parser_and_native_adapter_reject_two_ids_under_cap_one(self):
        response = {'content':'{"observation_ids":["0","1"]}',
                    'truncated':False,'tokens_evaluated':10,'tokens_predicted':5}
        self.assertEqual(('0','1'),parse_selection(response,['0','1'])[0])
        with self.assertRaises(ContractError): parse_selection(response,['0','1'],1)
        good = self.backend(['0']); self.assertEqual(('0',),good.select(self.request).observation_ids)
        bad = self.backend(['0','1'])
        with self.assertRaises(ContractError): bad.select(self.request)
        self.assertEqual(1,len(bad.opener.calls)); self.assertEqual('failed',bad.records[0]['status'])

    def test_backend_archive_verification_rejects_resealed_cap_payload_and_response(self):
        backend = self.backend(['0']); backend.select(self.request)
        doc = {'schema_version':1,'attempts':encode(backend.records)}
        trace = [
            {'event':'bounded_retrieval','details':{'category':'genetics','attempt':1,
                'request_sha256':fingerprint(self.request),'selected_ids':['0','1','2','3']}},
            {'event':'dispatch','details':{'attempt_id':'genetics:1','request_sha256':fingerprint(self.request)}},
            {'event':'attempt_accounted','details':{'usage':encode(Usage(10,5,0)),'basis':'adapter_reported'}},
            {'event':'review','details':{'category':'genetics','selected':['0']}}]
        configuration = {'backend_provenance':backend.provenance}
        verify_backend_execution(doc,trace,configuration)
        changed = deepcopy(doc); payload=selection_payload(self.request,256,123)
        changed['attempts'][0].update(payload=payload,payload_sha256=fingerprint(payload))
        with self.assertRaises(ContractError): verify_backend_execution(changed,trace,configuration)
        changed=deepcopy(doc); entry=changed['attempts'][0]
        entry['response']['content']='{"observation_ids":["0","1"]}'
        entry['response_sha256']=fingerprint(entry['response']); entry['selection']=['0','1']
        with self.assertRaises(ContractError): verify_backend_execution(changed,trace,configuration)

    def test_prior_history_cannot_exceed_cap_even_when_latest_subset_is_valid(self):
        request = self.role_request('coordinator_synthesize',[['0','1'],['0'],['0'],['0']])
        self.assertEqual(('0',),role_allowed_ids(request))
        with self.assertRaises(ContractError): role_allowed_ids(request,1)
        backend = self.backend(['0'],role=True)
        with self.assertRaises(ContractError): backend.select(request)
        self.assertEqual([],backend.opener.calls)

    def test_empty_role_scope_enforces_zero_under_cap_one(self):
        request=self.role_request('scientific_reviewer',[['0'],['0'],[]])
        payload=role_selection_payload(request,256,123,selection_cap=1)
        output=payload['json_schema']['properties']['observation_ids']
        self.assertEqual(0,output['maxItems']); self.assertEqual(['0','1','2','3'],output['items']['enum'])
        self.assertEqual((),self.backend([],role=True).select(request).observation_ids)
        hostile=self.backend(['0'],role=True)
        with self.assertRaises(ContractError): hostile.select(request)
        self.assertEqual('failed',hostile.records[0]['status'])

    def test_both_baselines_respect_cap_and_legacy_default(self):
        request=replace(self.request,evidence=tuple(replace(r,scientific_record_json=canonical(
            {'source_locator':{'datasource_id':'same'},'source_metrics':{'score':i}}).decode())
            for i,r in enumerate(self.request.evidence)))
        for arm in ('lexical','provider_score'):
            default=comparison._baseline(request,arm)
            one=comparison._baseline(request,arm,1)
            self.assertEqual(3,len(default[0])); self.assertEqual(default[0][:1],one[0])


class ComparisonSelectionCapTests(unittest.TestCase):
    backend=fixtures.ComparisonWorkflowTests.backend
    run_arm=fixtures.ComparisonWorkflowTests.run_arm
    verify=fixtures.ComparisonWorkflowTests.verify
    rebind=fixtures.ComparisonWorkflowTests.rebind

    def setUp(self):
        fixtures.ComparisonWorkflowTests.setUp(self)
        packet=read_json(self.fixture/'evidence.json')
        for index in range(3):
            extra=deepcopy(packet['observations'][0]); extra['observation_id']='extra-selection-fixture-'+str(index)
            packet['observations'].append(extra)
        write_json(self.fixture/'evidence.json',packet)
        snapshot=read_json(self.fixture/'snapshot.json'); snapshot['artifacts'][0]['sha256']=sha256_file(self.fixture/'evidence.json')
        write_json(self.fixture/'snapshot.json',snapshot)
        self.store=load_snapshot(self.fixture/'snapshot.json',self.case)
        self.policy['selection_cap']=1; self.config['selection_cap']=1
        write_json(self.config_path,self.config)

    def test_cap_one_matches_all_arm_packets_and_survives_semantic_verification(self):
        audits=[]
        for arm in ('asof','adapted_virtual_biotech','lexical','provider_score','no_literature','no_perturbation'):
            result,out,backend=self.run_arm(arm,backend=self.backend(take=3))
            self.assertEqual('completed',result['status'])
            self.assertTrue(all(len(ids)<=1 for ids in result['selections'].values()))
            self.verify(out)
            audits.append(result['coverage']['genetics']['retrieval'])
            for record in backend.records:
                self.assertIn('Select up to one relevant evidence ID for',record['payload']['prompt'])
                self.assertEqual(1,record['payload']['json_schema']['properties']['observation_ids']['maxItems'])
        self.assertTrue(all(a==audits[0] for a in audits))

    def test_config_policy_mismatch_fails_before_output_or_dispatch(self):
        for arm in ('asof','lexical'):
            backend=self.backend(); policy={**self.policy,'selection_cap':3}; out=self.root/('mismatch-'+arm)
            with self.assertRaisesRegex(ContractError,'selection cap'):
                comparison.run_case(self.case,self.store,backend,Budget(),arm,out,policy)
            self.assertFalse(out.exists()); self.assertEqual([],backend.opener.calls)

    def test_role_postcheck_rejects_noncompliant_backend_result(self):
        backend=self.backend()
        def invalid(request):
            return Selection(tuple(r.observation_id for r in request.evidence[:2]),Usage(0,0,0))
        backend.select=invalid
        result,out,_=self.run_arm(backend=backend)
        self.assertEqual('failed',result['status']); self.assertEqual([],result['claims'])
        self.assertEqual(1,result['calls'])

    def test_request_history_cannot_smuggle_old_cap_three_choices(self):
        base=comparison._prepare(self.case,Category.GENETICS,self.store,self.policy,
                                comparison.RetrievalPolicy(**self.config['retrieval']))[0]
        ids=[r.observation_id for r in base.evidence[:2]]
        prior=[{'role':'chief_of_staff','observation_ids':ids}]
        with self.assertRaises(ContractError):
            comparison._request(base,'coordinator_delegate',Category.GENETICS,self.policy,prior)

    def test_resealed_policy_downgrade_fails_even_without_external_config(self):
        _,out,_=self.run_arm('lexical')
        policy=read_json(out/'role-policy.json'); policy['selection_cap']=3; write_json(out/'role-policy.json',policy)
        result=read_json(out/'result.json'); result['configuration']['role_policy_sha256']=fingerprint(policy)
        write_json(out/'result.json',result)
        self.rebind(out,lambda event:event['details']['configuration'].update(role_policy_sha256=fingerprint(policy))
                    if event['event']=='comparison_plan' else None)
        with self.assertRaisesRegex(ContractError,'selection cap'):
            comparison.verify_case(out,self.case,self.store)

    def test_resealed_two_id_role_selection_cannot_pass_cap_one_verifier(self):
        _,out,backend=self.run_arm()
        ids=[r.observation_id for r in backend.records[0]['request'].evidence[:2]]
        self.rebind(out,lambda event:event['details'].update(selected=ids) if event['event']=='role_selection' else None)
        with self.assertRaises(ContractError): self.verify(out)

    def test_cap_one_payload_is_verified_without_external_config(self):
        _,out,_=self.run_arm()
        self.assertEqual('verified',comparison.verify_case(out,self.case,self.store)['status'])
        execution=read_json(out/'backend-execution.json'); record=execution['attempts'][0]['record']
        record['payload']['json_schema']['properties']['observation_ids']['maxItems']=3
        record['payload_sha256']=fingerprint(record['payload'])
        write_json(out/'backend-execution.json',execution); comparison._seal(out)
        with self.assertRaisesRegex(ContractError,'payload'):
            comparison.verify_case(out,self.case,self.store)

    def test_prioritization_question_is_bounded_and_bound_into_every_role(self):
        self.policy['prioritization_question']='Which source most directly distinguishes the proposed mechanism?'
        result,out,backend=self.run_arm('adapted_virtual_biotech')
        self.assertEqual('completed',result['status']); self.verify(out)
        self.assertEqual(5,len(backend.records))
        for record in backend.records:
            self.assertIn('Prioritization question: '+self.policy['prioritization_question'],record['request'].instructions)
            self.assertIn(self.policy['prioritization_question'],record['payload']['prompt'])
        retrieval=comparison.RetrievalPolicy(**self.config['retrieval'])
        base,audit=comparison._prepare(self.case,Category.GENETICS,self.store,self.policy,retrieval)
        without_question={k:v for k,v in self.policy.items() if k!='prioritization_question'}
        legacy,legacy_audit=comparison._prepare(self.case,Category.GENETICS,self.store,without_question,retrieval)
        self.assertEqual(legacy.evidence,base.evidence)
        self.assertNotEqual(fingerprint(audit),fingerprint(legacy_audit))
        huge={**self.policy,'prioritization_question':'x'*13000}
        with self.assertRaises(ContractError): comparison._prepare(self.case,Category.GENETICS,self.store,huge,retrieval)

    def test_invalid_prioritization_question_rejected_before_dispatch(self):
        for value in ('','  ',None,True,1,[]):
            backend=self.backend(); output=self.root/('bad-question-'+str(type(value).__name__)+str(len(str(value))))
            with self.assertRaisesRegex(ContractError,'Prioritization question'):
                comparison.run_case(self.case,self.store,backend,Budget(),'asof',output,
                                    {**self.policy,'prioritization_question':value})
            self.assertFalse(output.exists()); self.assertEqual([],backend.opener.calls)


if __name__=='__main__':
    unittest.main()
