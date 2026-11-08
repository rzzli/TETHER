"""Full invented source/capture joins; no released data, server or model calls."""
import copy
import json
from pathlib import Path
import time
import unittest
from unittest.mock import Mock,patch

from experiments.alce import evaluation as e,producer,prompts
from tether_engine.serde import ContractError,canonical,encode
from tests import test_alce_data_views as view_fixtures, test_alce_producer as producer_fixtures
from tests import test_alce_native_metrics as metric_fixtures
from tests.test_alce_data_views import proof,put
from tests.test_alce_producer import Response


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.view=view_fixtures.ViewsTests();self.view.setUp();self.addCleanup(self.view.doCleanups)
        self.native=metric_fixtures.NativeMetricsTests();self.native.setUp();self.addCleanup(self.native.doCleanups)
        self.generator=producer_fixtures.ProducerTests();self.generator.setUp();self.addCleanup(self.generator.doCleanups)
        self.root=self.view.root
        for family in ('qampari','eli5'):
            rows=json.loads(self.view.raw[family])
            for row in rows:row.pop('qa_pairs',None)
            self.view.raw[family]=canonical(rows)
        self.view.tar();self.view.bind();self.view.sources['eval.py']=self.native.sources['eval.py']
        self.prepared=self.view.prepare();self.prepared_root=Path(self.prepared['root'])
        self.schedule=json.loads((self.prepared_root/'SCHEDULE.json').read_bytes())
        configs={f:dict(self.generator.configuration,family=f) for f in e.FAMILIES}
        self.plan=dict(schema_version=1,kind='alce_evaluation_join_plan_v1',preparation=encode(self.prepared),
            expected_counts={f:2 for f in e.FAMILIES},generation=dict(configurations=configs,input_byte_limit=20000,
                model_provenance=encode(self.generator.model),limits=dict(context_tokens=16384,call_seconds=20)),
            owners={'owner':dict(owner_pid=24680,alias='invented-alce',server_spec=encode(self.generator.spec),
                bindings={k:str(v) for k,v in self.generator.bindings.items()})},attempts=[],native_sources=self.native.sources)
        for family in e.FAMILIES:
            cases=json.loads((self.prepared_root/f'generation/{family}.json').read_bytes())
            for ordinal,case in enumerate(cases):
                self.generator.request=prompts.build_request(case,family=family,input_byte_limit=20000,configuration=configs[family])
                self.generator.call,self.generator.payload=producer.make_call(self.generator.request,self.generator.model,
                    limits=producer.Limits(16384,20))
                text=('  Invented answer [6].\nHidden second line [1].  ' if family=='qampari'
                      else '  <|im_end|> Invented answer [1][2].\nUnscored second line [5].  ')
                execution=f'fixture-{family}-{ordinal}'
                with self.generator.wire(generation=Response(self.generator.body(content=text))):
                    value=producer.execute_once(self.generator.owner,self.generator.call,self.generator.payload,
                        output=self.generator.root/execution,deadline=time.monotonic()+20,alias='invented-alce',execution_id=execution)
                self.plan['attempts'].append(dict(family=family,ordinal=ordinal,id=case['id'],owner='owner',
                    execution_id=execution,disposition='completed',descriptor={k:value[k] for k in ('root','receipt_sha256')},
                    evidence=None,output=None))
        self.pp=put(self.root/'JOIN.json',self.plan)

    def assemble(self):return e.assemble(self.pp,deadline=time.monotonic()+60)
    def changed(self,plan):self.pp=put(self.root/'JOIN.json',plan)

    def test_complete_source_capture_join_preserves_raw_references_and_only_offered_docs(self):
        value=self.assemble();report=value.report
        self.assertTrue(report['all_scheduled_completed']);self.assertEqual(report['completed_count'],6)
        self.assertEqual(report['qualified_capture_usage']['input_tokens'],300)
        self.assertEqual(report['qualified_capture_usage']['output_tokens'],108)
        for family in e.FAMILIES:
            rows=value.rows(family);self.assertEqual(len(rows),2)
            self.assertEqual(rows[0]['answer'],'REF_SECRET')
            self.assertEqual(len(rows[0]['docs']),5)
            self.assertEqual(set(rows[0]['docs'][0]),{'title','text'})
            self.assertIn('\n',rows[0]['output']);self.assertTrue(rows[0]['output'].startswith('  '))
            with self.assertRaises(TypeError):rows[0]['docs'][0]['text']='mutate'
        self.assertTrue(e.metric_plan(value)['eligible'])
        self.assertTrue(report['runtime_qualification_external'])

    def test_missing_extra_duplicate_reordered_id_and_ordinal_reject_before_reference_reads(self):
        variants=[]
        for kind in ('missing','extra','duplicate','reorder','id','ordinal','owner','counts'):
            p=copy.deepcopy(self.plan)
            if kind=='missing':p['attempts'].pop()
            elif kind=='extra':p['attempts'].append(p['attempts'][0])
            elif kind=='duplicate':p['attempts'][1]=copy.deepcopy(p['attempts'][0])
            elif kind=='reorder':p['attempts'][0],p['attempts'][1]=p['attempts'][1],p['attempts'][0]
            elif kind=='id':p['attempts'][0]['id']='substituted'
            elif kind=='ordinal':p['attempts'][0]['ordinal']=False
            elif kind=='owner':p['owners']['owner']['owner_pid']=24681
            else:p['expected_counts'].update(asqa=1,qampari=3)
            variants.append((kind,p))
        original=Path.open
        def guarded(path,*a,**kw):
            if path.parent==self.prepared_root/'evaluation':raise AssertionError('Reference opened before capture gate')
            return original(path,*a,**kw)
        for kind,p in variants:
            self.changed(p)
            with self.subTest(kind=kind),patch.object(Path,'open',guarded),self.assertRaises(ContractError):self.assemble()

    def test_reference_contamination_and_question_source_substitution_rejected(self):
        path=self.prepared_root/'generation/asqa.json';original=path.read_bytes()
        for mutate in (lambda rows:rows[0]['docs'][0].update(answers_found=[True]),
                       lambda rows:rows[0].update(question='Different question'),
                       lambda rows:rows[0]['docs'][0].update(text='Unseen substitute')):
            rows=json.loads(original);mutate(rows);changed=put(path,rows)
            rp=self.prepared_root/'RECEIPT.json';receipt=json.loads(rp.read_bytes())
            receipt['files']['generation/asqa.json']=changed;self.plan['preparation']['receipt_sha256']=put(rp,receipt)['sha256']
            self.changed(self.plan)
            with self.assertRaises(ContractError):self.assemble()

    def test_failure_and_unexecuted_slots_remain_null_and_block_metrics(self):
        for ordinal,status in ((0,'failed'),(1,'unexecuted')):
            row=self.plan['attempts'][ordinal];row.update(disposition=status,descriptor=None,
                evidence=put(self.root/f'DECLARATION-{status}.json',dict(status=status,reason='Invented retained terminal declaration')))
        self.changed(self.plan);value=self.assemble()
        self.assertEqual(value.rows('asqa')[0]['output'],None);self.assertEqual(value.rows('asqa')[1]['output'],None)
        self.assertEqual(value.report['completed_count'],4);self.assertFalse(e.metric_plan(value)['eligible'])
        self.assertEqual(value.report['qualified_capture_usage']['input_tokens'],200)
        with self.assertRaises(ContractError):e.evaluate_family(value,'qampari',self.native.bridge(),deadline=time.monotonic()+30)

    def test_unseen_citation_six_cannot_access_original_seventh_document(self):
        value=self.assemble();bridge=self.native.bridge()
        result=e.evaluate_family(value,'qampari',bridge,deadline=time.monotonic()+30)
        self.assertEqual(result['metrics']['citations']['native_value']['citation_rec'],0)
        self.assertEqual(len(bridge.calls),0)
        self.assertEqual(result['metrics']['citations']['diagnostics']['strict_invalid_citation_token_count'],2)
        self.assertNotIn('qa',result['metrics']);self.assertNotIn('mauve',result['metrics']);self.assertNotIn('rouge',result['metrics'])
        self.assertEqual(result['scheduled_count'],2)

    def test_native_branching_reuses_one_resident_callback_and_keeps_full_denominators(self):
        value=self.assemble();seen=[];verdicts=iter([1,1,0,1]*2)
        resident=e.ResidentNLI(lambda r:(seen.append(r),next(verdicts))[1],maximum=8,deadline=time.monotonic()+30)
        bridge=self.native.bridge(callback=resident)
        # Exercise the exact citation path over the admitted full family. Other
        # native dependencies remain explicitly unqualified in this fixture.
        result=bridge.metric('citations',value.rows('asqa'),deadline=time.monotonic()+30)
        self.assertEqual(result['native_value']['citation_prec'],50)
        self.assertEqual(result['diagnostics']['scheduled_count'],2)
        self.assertEqual(len(resident.records),8)
        self.assertEqual([r['premise'] for r in seen[:4]],[
            'Title: Title0\nInvented passage0\nTitle: Title1\nInvented passage1',
            'Title: Title0\nInvented passage0','Title: Title1\nInvented passage1','Title: Title0\nInvented passage0'])

    def test_resident_cap_and_native_failure_are_not_retried_or_repaired(self):
        value=self.assemble();called=[]
        resident=e.ResidentNLI(lambda r:(called.append(r),1)[1],maximum=1,deadline=time.monotonic()+30)
        bridge=self.native.bridge(callback=resident)
        with self.assertRaisesRegex(ContractError,'ceiling'):bridge.metric('citations',value.rows('asqa'))
        self.assertEqual(len(called),1)
        self.assertTrue(resident.failed)
        bad=e.ResidentNLI(lambda r:True,maximum=3,deadline=time.monotonic()+30)
        for _ in range(2):
            with self.assertRaises(ContractError):bad({'invented':'request'})
        self.assertEqual(len(bad.records),1);self.assertTrue(bad.failed)

    def test_unique_closure_proofs_hash_once_then_recheck_at_boundary(self):
        inputs=e._Inputs(time.monotonic()+30);p=proof(self.root/'JOIN.json')
        with patch.object(e,'_hash',wraps=e._hash) as hashed:
            inputs.large(p);inputs.large(dict(p));self.assertEqual(hashed.call_count,1)
            inputs.unchanged();self.assertEqual(hashed.call_count,2)
            bad=dict(p,sha256='0'*64)
            with self.assertRaises(ContractError):inputs.large(bad)
            self.assertEqual(hashed.call_count,2)

    def test_separate_lexical_worker_needs_no_qa_mauve_or_true_model(self):
        value=self.assemble();bridge=self.native.bridge()
        result=e.evaluate_group(value,'qampari','lexical',bridge,deadline=time.monotonic()+30)
        self.assertEqual(result['status'],'completed');self.assertEqual(set(result['metrics']),{'length','str_em','qampari'})
        self.assertEqual(len(bridge.calls),0)
        later=e.evaluate_group(value,'qampari','true',bridge,deadline=time.monotonic()+30)
        self.assertEqual(set(later['metrics']),{'citations'})
        self.assertEqual(e.outcomes(value)['qampari']['status'],'completed')
        with self.assertRaises(ContractError):e.evaluate_group(value,'qampari','lexical',bridge,deadline=time.monotonic()+30)

    def test_mutated_or_copied_assembly_and_late_source_changes_fail(self):
        value=self.assemble()
        forged=object.__new__(e.Assembly);forged._rows=value._rows;forged._report=value._report
        with self.assertRaises(ContractError):e.metric_plan(forged)
        with self.assertRaises(ContractError):e.revalidate(value,deadline=float('nan'))
        original=value._report;value._report={'forged':True}
        with self.assertRaises(ContractError):e.metric_plan(value)
        value._report=original
        p=self.prepared_root/'generation/eli5.json';p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaises(ContractError):e.revalidate(value,deadline=time.monotonic()+30)

    def test_full_family_mauve_uses_one_native_normalization_and_no_reference_to_actor(self):
        value=self.assemble();bridge=self.native.bridge();received=[]
        def mauve(rows,sources):
            received.append((rows,sources));return dict(native_value=.5,scheduled_count=len(rows))
        # Pass through real preprocess and native length/STR/AIS. Explicit
        # invented values stand in for unqualified optional numerical runtimes.
        original=bridge.metric
        def metric(name,rows,**kw):
            if name in ('rouge','qa'):return {'metric':name,'invented_runtime':True}
            return original(name,rows,**kw)
        with patch.object(bridge,'metric',side_effect=metric),patch.object(bridge,'preprocess',wraps=bridge.preprocess) as preprocess:
            result=e.evaluate_family(value,'asqa',bridge,mauve=mauve,deadline=time.monotonic()+30)
        self.assertEqual(preprocess.call_count,1);self.assertEqual(len(received),1)
        rows,_=received[0];self.assertEqual(len(rows),2)
        self.assertNotIn('[1]',rows[0]['output']);self.assertNotIn('\n',rows[0]['output'])
        self.assertTrue(rows[0]['output'].startswith(' '))  # Native marker removal is not stripped again.
        self.assertIn('\n',value.rows('asqa')[0]['output'])
        self.assertEqual(result['status'],'completed')
        with self.assertRaises(ContractError):e.evaluate_family(value,'asqa',bridge,mauve=mauve,deadline=time.monotonic()+30)

    def test_native_metric_error_retains_partial_results_without_success(self):
        value=self.assemble();bridge=self.native.bridge()
        with self.assertRaises(e.native_metrics.UnsupportedMetric):
            e.evaluate_family(value,'asqa',bridge,mauve=lambda *a:None,deadline=time.monotonic()+30)
        outcome=e.outcomes(value)['asqa'];self.assertEqual(outcome['status'],'failed')
        self.assertEqual(set(outcome['metrics']),{'length','str_em'})
        with self.assertRaises(ContractError):e.evaluate_family(value,'asqa',bridge,mauve=lambda *a:None,deadline=time.monotonic()+30)

    def test_native_singleton_qa_dict_failure_is_preserved_without_normalization(self):
        value=self.assemble();answers=[]
        def pipeline(*args,**kwargs):
            def answer(**request):answers.append(request);return {'answer':'REF_SECRET_A'}
            return answer
        bridge=self.native.bridge(extra=dict(pipeline=self.native.binding(pipeline,
            logical_model=e.native_metrics.QA_MODEL,network_access=False,local_checkpoint=str(self.native.root))))
        original=bridge.metric
        def metric(name,rows,**kw):
            return {'invented_rouge_runtime':True} if name=='rouge' else original(name,rows,**kw)
        with patch.object(bridge,'metric',side_effect=metric),self.assertRaises(TypeError):
            e.evaluate_family(value,'asqa',bridge,mauve=lambda *a:None,deadline=time.monotonic()+30)
        self.assertEqual(len(answers),1);self.assertEqual(len(answers[0]['question']),1)
        outcome=e.outcomes(value)['asqa'];self.assertEqual(outcome['status'],'failed')
        self.assertEqual(outcome['error_type'],'TypeError');self.assertNotIn('qa',outcome['metrics'])

    def test_late_acquisition_failure_markers_invalidate_issued_assembly(self):
        value=self.assemble()
        for name in ('FAILURE.json','DEADLINE.json','FINALIZATION-FAILED.json',
                     'FAILED.json','SUPERVISOR-FAILED.json','STALLED.json'):
            path=self.root/name
            with self.subTest(name=name):
                put(path,{'status':'failed','reason':'Invented late acquisition contradiction'})
                try:
                    with self.assertRaises(ContractError):e.revalidate(value,deadline=time.monotonic()+30)
                finally:path.unlink()


if __name__=='__main__':unittest.main()
