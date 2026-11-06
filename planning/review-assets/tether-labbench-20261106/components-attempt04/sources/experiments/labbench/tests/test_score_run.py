"""Fictional post-seal evaluation cases; no original benchmark labels."""
import hashlib
from datetime import datetime,timezone
from pathlib import Path
import tempfile
import unittest
import time
from unittest.mock import patch

from asof.serde import ContractError,canonical,encode,freeze
from experiments.labbench.score_run import analytical_controls, inspect_collected_sources, normalize_identifier, source_diagnostics,score_run,_compare_recaptured_context,verify_case_pair


class SourceIdentityTests(unittest.TestCase):
    def test_normalized_aliases_and_unknown_urls(self):
        self.assertEqual(normalize_identifier('https://doi.org/10.1234/AbC?tracking=x'),'doi:10.1234/abc')
        self.assertEqual(normalize_identifier('https://pubmed.ncbi.nlm.nih.gov/123/'),'pmid:123')
        self.assertEqual(normalize_identifier('https://pmc.ncbi.nlm.nih.gov/articles/PMC456/'),'pmcid:PMC456')
        self.assertIsNone(normalize_identifier('https://example.invalid/article/a'))
        self.assertIsNone(normalize_identifier('https://user:secret@doi.org/10.1234/abc'))

    def test_aliases_collapse_but_missing_doi_is_still_a_miss(self):
        queries=[{'id':'q1','question':'Same fictional question'},{'id':'q2','question':' Same  fictional question '},
                 {'id':'q3','question':'Different fictional question'}]
        annotations={'q1':['https://doi.org/10.1234/a','https://pubmed.ncbi.nlm.nih.gov/123/'],
                     'q2':['doi:10.1234/missed','https://example.invalid/unknown'],
                     'q3':['pmid:999','pmcid:PMC999']}
        metadata=[{'doi':'10.1234/a','pmcid':'PMC456','id':'123','source':'MED'}]
        retrieved={'q1':['pmcid:PMC456'],'q2':[],'q3':[]}
        result=source_diagnostics(queries,annotations,retrieved,metadata)
        self.assertEqual(result['primary']['observed_annotated_source_hit_questions'],1)
        self.assertEqual(result['primary']['observed_annotated_source_hit_per_scheduled'],1/3)
        self.assertEqual(result['doi_identifier']['annotated_doi_count'],2)
        self.assertEqual(result['doi_identifier']['hit_doi_count'],1)
        self.assertEqual(result['doi_identifier']['recall'],.5)
        self.assertEqual(result['conditional_resolved_paper']['annotated_paper_count'],1)
        self.assertEqual(result['conditional_resolved_paper']['recall'],1)
        self.assertEqual(result['resolution']['unresolved_recognized_annotation_ids'],3)
        self.assertEqual(result['resolution']['unrecognized_annotation_values'],1)
        self.assertEqual(result['semantic_support'],'unevaluated')
        self.assertEqual(result['case_results'][0]['component_id'],result['case_results'][1]['component_id'])
        self.assertNotEqual(result['case_results'][0]['component_id'],result['case_results'][2]['component_id'])
        self.assertNotIn('annotated_ids',result['case_results'][0])

    def test_conflicting_aliases_never_merge_distinct_dois_into_one_resolved_paper(self):
        metadata=[{'doi':'10.1234/a','pmcid':'PMC1','id':'1','source':'MED'},
                  {'doi':'10.1234/b','pmcid':'PMC1','id':'1','source':'MED'}]
        result=source_diagnostics([{'id':'q','question':'Fictional'}],{'q':['doi:10.1234/a']},{'q':['pmcid:PMC1']},metadata)
        self.assertEqual(result['resolution']['conflicting_alias_components'],1)
        self.assertEqual(result['conditional_resolved_paper']['annotated_paper_count'],0)
        self.assertIsNone(result['conditional_resolved_paper']['recall'])
        self.assertEqual(result['primary']['observed_annotated_source_hit_questions'],0)

    def test_no_annotation_is_unknown_not_perfect_recall(self):
        value=source_diagnostics([{'id':'q','question':'Fictional'}],{'q':[]},{'q':[]},[])
        self.assertIsNone(value['doi_identifier']['recall'])
        self.assertIsNone(value['conditional_resolved_paper']['recall'])
        self.assertIsNone(value['case_results'][0]['annotated_source_hit'])

    def test_identical_unresolved_source_pointer_groups_without_inventing_paper(self):
        value=source_diagnostics([{'id':'a','question':'One'},{'id':'b','question':'Two'}],
            {'a':['https://example.invalid/article'],'b':['https://example.invalid/article']},{'a':[],'b':[]},[])
        self.assertEqual(value['grouping']['components'],1)
        self.assertEqual(value['conditional_resolved_paper']['annotated_paper_count'],0)


class AnalyticalControlTests(unittest.TestCase):
    def test_controls_are_analytical_and_precision_is_ratio_of_expectations(self):
        value=analytical_controls([3,5])
        self.assertFalse(value['executed'])
        self.assertEqual(value['uniform_all_choices']['expected_correct_count'],1/3+1/5)
        self.assertEqual(value['uniform_all_choices']['ratio_of_expected_correct_to_expected_attempted'],(1/3+1/5)/(2/3+4/5))
        self.assertEqual(value['always_unsure']['accuracy'],0)
        self.assertFalse(value['always_unsure']['precision_defined'])


class CollectionIdentityTests(unittest.TestCase):
    def test_posthoc_metadata_capture_checks_original_bytes_and_selected_document(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);retrieval=root/'retrieval';retrieval.mkdir()
            def write(path,value):
                raw=canonical(value);path.write_bytes(raw)
                return {'path':path.relative_to(root).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
            meta=write(retrieval/'search.json',{'resultList':{'result':[{'doi':'10.1234/a','pmcid':'PMC1','id':'1','source':'MED'}]}})
            manifest=write(retrieval/'manifest.json',{'requests':[{'kind':'search','status':'completed','http_status':200,
                'body_path':'search.json','body_sha256':meta['sha256'],'bytes':meta['bytes']}],
                'sources':[{'source_id':'PMC1'},{'source_id':'PMC2'}],'failures':[]})
            selected=write(root/'selected.json',{'sources':[{'source_id':'chunk'}],'bindings':[{'document_id':'PMC1'}],
                'coverage':{'selected_text_bytes':10,'available_text_bytes':200}})
            collection={'schedule':['q'],'cases':[{'id':'q','ordinal':0,'status':'completed',
                'retrieval':{'path':'retrieval','manifest_sha256':manifest['sha256']},'selected':selected}]}
            value=inspect_collected_sources(root,freeze(collection),[{'id':'q'}])
            self.assertEqual(value['retained_ids']['q'],('pmcid:PMC1','pmcid:PMC2'))
            self.assertEqual(value['selected_ids']['q'],('pmcid:PMC1',))
            self.assertEqual(value['posthoc_network_calls'],0)
            (retrieval/'search.json').write_bytes(b'{}')
            with self.assertRaises(ContractError):inspect_collected_sources(root,collection,[{'id':'q'}])


class EvaluationGateTests(unittest.TestCase):
    def test_actual_component_pair_replay_rejects_resealed_candidate_substitution(self):
        # Reuse the fictional transport fixture, not a live server/model. Real
        # StudySession, original XML capture, InputGraph and replay all run.
        from experiments.labbench.tests import test_model as transport_fixture
        from experiments.labbench.tests import test_policy as source_fixture
        from experiments.labbench import model,retrieval
        from experiments.labbench.tether_adapter import capture_context,verify_candidate
        from asof.study.session import StudySession
        from asof.workflow import Budget
        fixture=transport_fixture.ModelTests();fixture.setUp()
        try:
            root=fixture.root;retrieval_root=root/'retrieval'
            with patch.object(retrieval,'fetch_http',source_fixture.fake_fetch):retrieval.retrieve(fixture.query['question'],retrieval_root)
            manifest_sha=hashlib.sha256((retrieval_root/'manifest.json').read_bytes()).hexdigest()
            cutoff=datetime.now(timezone.utc)
            context=capture_context(fixture.query,retrieval_root,manifest_sha,cutoff,fixture.model)
            fixture.request,fixture.payload=model.make_request(fixture.query,context.sources,fixture.model)
            case_root=root/'case';case_root.mkdir();fixture.output=case_root/'transport';fixture.output.mkdir()
            backend=fixture.backend();candidate={'answer_index':0,'evidence_ids':[context.sources[0]['source_id']]}
            body=fixture.native_body(content=canonical(candidate).decode())
            with fixture.transport(transport_fixture.Response(body)),patch.object(model.native,'_watchdog',return_value=transport_fixture.Timer()):
                with StudySession(case_root/'session',resources={},required_resources=(),
                    configuration={'task_id':fixture.query['id'],'source_context_sha256':context.sha256},
                    budget=Budget(max_calls=1,max_retries=0,max_input_tokens=16384,max_output_tokens=256,max_seconds=10)) as session:
                    produced=session.call_once(request=fixture.request,payload=fixture.payload,backend=backend,
                        verifier=model.MCQVerifier(model_alias='fictional-mcq'))
                    session.finish()
            decision=verify_candidate(context,context.request,produced)
            for name,value in [('context',context.report),('request',context.request),('payload',fixture.payload),
                ('sources',context.sources),('candidate',produced),('decision',decision)]:
                (case_root/(name+'.json')).write_bytes(canonical(value))
            names={key:key+'.json' for key in ('context','request','payload','sources','candidate','decision')}
            names.update(session_receipt='session/receipt.json',session_response='session/response.json',
                         session_configuration='session/configuration.json',raw_response='session/raw-response.bin')
            def proof(path):
                raw=path.read_bytes();return {'path':path.relative_to(root).as_posix(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
            case={'id':fixture.query['id'],'disposition':{'id':fixture.query['id'],'producer_status':'produced',
                'check_status':'accepted','prediction':encode(produced),'reason':None},
                'artifacts':{key:proof(case_root/name) for key,name in names.items()}}
            collected={'id':fixture.query['id'],'status':'completed','retrieval':{'path':'retrieval','manifest_sha256':manifest_sha}}
            result,offered=verify_case_pair(root,fixture.query,case,root,collected,cutoff,fixture.model,
                model.DEFAULT_CONFIGURATION,'fictional-mcq',deadline=time.monotonic()+30)
            self.assertTrue(result['paired_candidate_bytes']);self.assertTrue(offered)
            altered=encode(produced);altered['answer_index']=2
            (case_root/'candidate.json').write_bytes(canonical(altered))
            case['artifacts']['candidate']=proof(case_root/'candidate.json');case['disposition']['prediction']=altered
            with self.assertRaises(ContractError):verify_case_pair(root,fixture.query,case,root,collected,cutoff,fixture.model,
                model.DEFAULT_CONFIGURATION,'fictional-mcq',deadline=time.monotonic()+30)
        finally:fixture.doCleanups()

    def test_missing_generation_seal_blocks_reference_access_and_retains_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch('experiments.labbench.run.verify_generation',side_effect=ContractError('unsealed')),\
                 patch('experiments.labbench.data_views.verify_views') as references:
                with self.assertRaises(ContractError):score_run(root/'run','a'*64,root/'refs','b'*64,root/'output')
            references.assert_not_called()
            self.assertTrue((root/'output/FAILED.json').exists())
            self.assertFalse((root/'output/SEALED.json').exists())

    def test_recapture_time_only_is_normalized_not_source_eligibility(self):
        old={'captured_at_utc':'2020-01-01T00:00:00+00:00','snapshot':{'sources':[
            {'computed_at':None,'availability':'fixed-original'},
            {'computed_at':'2020-01-01T00:00:00Z','availability':'derived'}]}}
        current={'captured_at_utc':'2021-01-01T00:00:00+00:00','snapshot':{'sources':[
            {'computed_at':None,'availability':'fixed-original'},
            {'computed_at':'2021-01-01T00:00:00Z','availability':'derived'}]}}
        _compare_recaptured_context(old,current)
        current['snapshot']['sources'][0]['availability']='new-future-information'
        with self.assertRaises(ContractError):_compare_recaptured_context(old,current)

    def test_partial_schedule_stays_partial_with_zero_invented_calls_or_reference_values(self):
        # Isolates the evaluator controller from already separately qualified
        # source/model/producer verifiers. This is not a whole-pipeline fixture.
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);generation_root=root/'generation';generation_root.mkdir()
            preparation_root=root/'preparation';preparation_root.mkdir()
            def write(base,name,value):
                raw=canonical(value);(base/name).write_bytes(raw)
                return {'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
            query={'id':'00000000-0000-4000-8000-000000000001','question':'Invented?',
                   'choices':['(A) a','(B) b','(C) Insufficient information to answer the question']}
            queries=[query];ident=query['id']
            row={'id':ident,'producer_status':'unexecuted','check_status':'not_run','prediction':None,'reason':'fixture deadline'}
            case={'id':ident,'ordinal':0,'disposition':row,'artifacts':{}}
            qp=write(generation_root,'queries.json',queries)
            generation={'status':'partial','mode':'fictional','schedule':[ident],'queries':qp,'code_pins':{},
                'dispositions':write(generation_root,'dispositions.json',[row]),'case_index':write(generation_root,'case-index.json',[case]),
                'collection':{'path':str(root/'collection'),'manifest_sha256':'c'*64},'configuration':{},'alias':'fictional',
                'totals':{'generation_attempts':0},'parent_resources':{},'cleanup':'unverified_or_job_forced'}
            collection={'schedule':[ident],'queries':qp,'cases':[{'id':ident,'ordinal':0,'status':'unexecuted'}],
                'cutoff':'2020-01-01T00:00:00Z','totals':{},'resources':{}}
            preparation={'products':{'queries':qp,
                'references':write(preparation_root,'references.json',[{'id':ident,'answer_index':0,'unsure_index':2}]),
                'provenance':write(preparation_root,'provenance.json',[{'id':ident,'original_fields':{'sources':[]},'row_1based':1,'raw_line_sha256':'d'*64}])}}
            with patch('experiments.labbench.run.verify_generation',return_value=freeze(generation)),\
                 patch('experiments.labbench.run.source_pins',return_value={}),\
                 patch('experiments.labbench.collect.verify_collection',return_value=freeze(collection)),\
                 patch('experiments.labbench.data_views.verify_views',return_value=freeze(preparation)),\
                 patch('experiments.labbench.score_run._verify_model_assets',return_value=({},())),\
                 patch('experiments.labbench.runtime.process_sample',return_value=None):
                result=score_run(generation_root,'a'*64,preparation_root,'b'*64,root/'output')
                with self.assertRaises(FileExistsError):score_run(generation_root,'a'*64,preparation_root,'b'*64,root/'output')
            self.assertEqual(result['status'],'descriptive_partial')
            self.assertEqual(result['scheduled_count'],1)
            self.assertEqual(result['counts']['producer_failures'],1)
            self.assertEqual(result['resources']['new_model_calls'],0)
            self.assertTrue((root/'output/SEALED.json').exists())
            report=(root/'output/REPORT.json').read_text()
            self.assertNotIn('answer_index',report)
            self.assertNotIn('unsure_index',report)


if __name__=='__main__':unittest.main(verbosity=2)
