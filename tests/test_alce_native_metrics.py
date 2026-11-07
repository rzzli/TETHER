"""Exact pinned ALCE bodies, invented rows, and explicitly unqualified test runtimes.

These controls qualify bridge semantics and request construction. They do not
qualify NumPy, NLTK, ROUGE, QA, TRUE, MAUVE, or any scientific prediction.
"""
import ast
import builtins
import copy
import hashlib
import json
import math
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments.alce import native_metrics as n
from tether_engine.serde import ContractError, canonical, encode


FIXTURES=Path(__file__).resolve().parent/'fixtures/alce_native'


def proof(path):
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


class InventedMean:
    """Only the mean operation used by these native functions; not NumPy."""
    @staticmethod
    def mean(values):
        return sum(values)/len(values) if values else float('nan')


def sentences(text):
    """Deterministic invented tokenizer: one nonempty text is one sentence."""
    return [text] if text.strip() else []


def row(output='The cobalt lamp [1].', **kw):
    value=dict(question='Which fictional lamp?',output=output,
        docs=[dict(title='First',text='A cobalt lamp.'),dict(title='Second',text='An amber lamp.')])
    value.update(kw)
    return value


class NativeMetricsTests(unittest.TestCase):
    def setUp(self):
        workspace=Path(__file__).resolve().parents[1]/'data/cache'
        workspace.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=workspace.resolve(),prefix='alce-native-invented-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.sources={}
        for name in n.SOURCE_SHA256:
            target=self.root/name
            target.write_bytes((FIXTURES/name).read_bytes())
            self.sources[name]=proof(target)
        self.runtime=self.root/'invented-runtime.json'
        self.runtime.write_text('{"scope":"invented test dependency, not qualified model"}',encoding='utf-8')
        self.seen=[]

    def binding(self,value,**configuration):
        return n.Binding(value,dict(name='invented-test-dependency',version='1',
            configuration=configuration,files=[proof(self.runtime)]))

    def bridge(self, verdicts=None, *, callback=None, extra=None):
        iterator=iter([1]*100 if verdicts is None else verdicts)
        def infer(request):
            self.seen.append(request)
            return next(iterator)
        bindings=dict(np=self.binding(InventedMean),sent_tokenize=self.binding(sentences))
        bindings.update(extra or {})
        return n.NativeBridge(self.sources,bindings=bindings,nli=self.binding(callback or infer))

    def test_fixture_exact_hashes_license_and_function_bodies(self):
        declaration=json.loads((FIXTURES/'SOURCE.json').read_text(encoding='utf-8'))
        self.assertEqual(declaration['revision'],n.COMMIT)
        for name,p in declaration['files'].items():
            raw=(FIXTURES/name).read_bytes()
            self.assertEqual((len(raw),hashlib.sha256(raw).hexdigest()),(p['bytes'],p['sha256']))
        self.assertIn('Princeton Natural Language Processing',(FIXTURES/'LICENSE').read_text())
        bridge=self.bridge();hashes=bridge.provenance()['function_ast_sha256']
        for name,names in [('eval.py',n.EVAL_FUNCTIONS),('utils.py',n.UTIL_FUNCTIONS)]:
            functions={x.name:x for x in ast.parse((FIXTURES/name).read_bytes()).body if isinstance(x,ast.FunctionDef)}
            for function in names:
                self.assertEqual(hashes[function],hashlib.sha256(ast.dump(functions[function],include_attributes=False).encode()).hexdigest())

    def test_selected_ast_never_imports_full_native_module_or_loaders(self):
        old=builtins.__import__
        def guarded(name,*args,**kw):
            if name.split('.')[0] in {'torch','transformers','numpy','nltk','rouge_score','mauve','utils'}:
                raise AssertionError('Unplanned dependency import: '+name)
            return old(name,*args,**kw)
        with patch('builtins.__import__',side_effect=guarded):
            bridge=self.bridge()
            self.assertEqual(bridge.metric('citations',[row()])['native_value']['citation_rec'],100)
            self.assertEqual(bridge.metric('claims',[row(claims=['A cobalt lamp.'])])['native_value'],100)
        self.assertNotIn('main',bridge._globals)
        self.assertNotIn('AutoModelForSeq2SeqLM',bridge._globals)
        self.assertFalse(bridge.provenance()['full_upstream_module_executed'])

    def test_wrong_revision_source_substitution_and_source_drift_fail(self):
        with self.assertRaises(ContractError):n.NativeBridge(self.sources,revision='0'*40)
        changed=dict(self.sources);changed['eval.py']=dict(changed['eval.py'],sha256='0'*64)
        with self.assertRaises(ContractError):n.NativeBridge(changed)
        bridge=self.bridge()
        Path(self.sources['eval.py']['path']).write_bytes(b'not upstream')
        with self.assertRaises(ContractError):bridge.metric('length',[row()])

    def test_runtime_proof_drift_rejected_before_callback(self):
        bridge=self.bridge();self.runtime.write_bytes(b'changed runtime')
        with self.assertRaises(ContractError):bridge.metric('citations',[row()])
        self.assertEqual(len(self.seen),0)

    def test_preprocessing_preserves_native_firstline_marker_and_citation_quirks(self):
        original=[row('  Answer [1] <|im_end|>\r\nSecond [2] line  ')]
        before=copy.deepcopy(original)
        value=self.bridge().preprocess(original)
        self.assertEqual(value['citation'][0]['output'],'Answer [1] \r')
        self.assertEqual(value['normalized'][0]['output'],'Answer \r')
        self.assertEqual(original,before)
        self.assertEqual(self.bridge().preprocess([row('<|im_end|>')])['citation'][0]['output'],'')
        # Native remove_citations deletes unmatched closers and its exact " |" sequence.
        self.assertEqual(self.bridge().preprocess([row('x [12 incomplete] | y]')])['normalized'][0]['output'],'x incomplete y')

    def test_metric_routes_normalized_firstline_without_changing_input(self):
        rows=[row('  Cobalt [1].\nignored words and citations [2] ')]
        before=copy.deepcopy(rows)
        result=self.bridge().metric('length',rows)
        self.assertEqual(result['native_value'],1)
        self.assertEqual(result['diagnostics']['strict_citation_token_count'],1)
        self.assertEqual(rows,before)

    def test_exact_and_f1_native_normalization(self):
        bridge=n.NativeBridge(self.sources)
        self.assertEqual(dict(bridge.exact('The cobalt-lamp!','cobaltlamp')),dict(exact=1,f1=1))
        self.assertEqual(bridge.exact('red blue','red')['f1'],2/3)
        self.assertEqual(bridge.exact('','')['f1'],1)
        self.assertEqual(bridge.exact('','lamp')['f1'],0)

    def test_strem_substring_and_empty_pairs_are_not_silently_repaired(self):
        bridge=self.bridge()
        result=bridge.metric('str_em',[row('Copperton.',qa_pairs=[dict(short_answers=['copper'])])])
        self.assertEqual(result['native_value'],(100,100))
        result=bridge.metric('str_em',[row('',qa_pairs=[])])
        self.assertIsNone(result['native_value'][0]);self.assertEqual(result['native_value'][1],0)
        self.assertEqual(result['native_nonfinite'][0]['raw_value'],'NaN')
        self.assertEqual(result['diagnostics']['qa_missing_or_empty_count'],1)
        canonical(result)  # Strict JSON has no literal NaN.

    def test_native_firstrow_missing_qa_returns_zero_with_separate_missingness(self):
        called=[]
        def pipeline(*args,**kw):called.append((args,kw));raise AssertionError('No model for missing QA')
        config=dict(logical_model=n.QA_MODEL,network_access=False,local_checkpoint=str(self.root/'checkpoint'))
        bridge=self.bridge(extra=dict(pipeline=self.binding(pipeline,**config)))
        rows=[row(),row(qa_pairs=[dict(question='Invented?',short_answers=['cobalt'])])]
        result=bridge.metric('qa',rows)
        self.assertEqual(dict(result['native_value']),{'QA-EM':0,'QA-F1':0,'QA-Hit':0})
        self.assertEqual(result['diagnostics']['qa_missing_or_empty_count'],1)
        self.assertEqual(called,[])
        self.assertEqual(bridge.metric('str_em',rows)['native_value'],(0,0))

    def test_qa_native_model_id_context_and_aggregation_with_explicit_fake(self):
        calls=[]
        def pipeline(*args,**kw):
            calls.append((args,kw))
            def qa(**kw):
                calls.append(kw)
                return [dict(answer='cobalt') for _ in kw['question']]
            return qa
        config=dict(logical_model=n.QA_MODEL,network_access=False,local_checkpoint=str(self.root/'checkpoint'))
        bridge=self.bridge(extra=dict(pipeline=self.binding(pipeline,**config)))
        result=bridge.metric('qa',[row('',qa_pairs=[dict(question='Invented?',short_answers=['the cobalt'])])])
        self.assertEqual(dict(result['native_value']),{'QA-EM':100,'QA-F1':100,'QA-Hit':100})
        self.assertEqual(calls[0],(('question-answering',),dict(model=n.QA_MODEL,device=0)))
        self.assertEqual(calls[1],dict(question=['Invented?'],context=' ',handle_impossible_answer=True))
        with self.assertRaises(ZeroDivisionError):bridge.metric('qa',[row(qa_pairs=[])])

    def test_qa_offline_binding_and_optional_missing_dependencies_fail_before_use(self):
        bridge=n.NativeBridge(self.sources)
        for metric in ('str_em','qampari','citations','claims','qa','rouge','mauve'):
            with self.subTest(metric=metric),self.assertRaises(n.UnsupportedMetric):bridge.metric(metric,[row()])
        called=[]
        bridge=self.bridge(extra=dict(pipeline=self.binding(lambda *a,**kw:called.append(True),logical_model=n.QA_MODEL,network_access=True,local_checkpoint=str(self.root))))
        with self.assertRaises(ContractError):bridge.metric('qa',[row()])
        self.assertEqual(called,[])

    def test_qampari_duplicates_cot_and_zero_prediction_native_values(self):
        bridge=self.bridge()
        result=bridge.metric('qampari',[row('Cobalt, cobalt, amber, wrong.',answers=[['cobalt'],['amber'],['green']])])
        value=result['native_value']
        self.assertEqual(value['num_preds'],4)
        self.assertEqual(value['qampari_prec'],75)
        self.assertAlmostEqual(value['qampari_rec'],200/3)
        self.assertAlmostEqual(value['qampari_f1'],100*12/17)
        self.assertEqual(bridge.metric('qampari',[row('thought: cobalt [1], amber.',answers=[['cobalt'],['amber']])],cot=True)['native_value']['qampari_f1'],100)
        self.assertEqual(bridge.metric('qampari',[row('no colon',answers=[['cobalt']])],cot=True)['native_value']['num_preds'],0)
        self.assertEqual(bridge.metric('qampari',[row('',answers=[['cobalt']])])['native_value']['qampari_prec'],0)
        with self.assertRaises(ZeroDivisionError):bridge.metric('qampari',[row('cobalt',answers=[])])

    def test_citation_single_request_exact_native_format_and_sent_field(self):
        bridge=self.bridge([1])
        result=bridge.metric('citations',[row('The cobalt lamp [1].',docs=[dict(title='First',text='ignored',sent='Actual selected sentence.')])])
        self.assertEqual(dict(result['native_value']),dict(citation_rec=100,citation_prec=100))
        request=self.seen[0]
        self.assertEqual(request['premise'],'Title: First\nActual selected sentence.')
        self.assertEqual(request['hypothesis'],'The cobalt lamp.')
        self.assertEqual(request['input_text'],'premise: Title: First\nActual selected sentence. hypothesis: The cobalt lamp.')
        self.assertEqual(request['max_new_tokens'],10)
        self.assertEqual(request['logical_model'],n.NLI_MODEL)
        self.assertFalse(result['scientific_truth_verified'])
        with self.assertRaises(TypeError):request['premise']='changed'

    def test_citation_joint_single_and_leaveoneout_order(self):
        result=self.bridge([1,1,0,1]).metric('citations',[row('Cobalt [1][2].')])
        self.assertEqual(result['native_value']['citation_rec'],100)
        self.assertEqual(result['native_value']['citation_prec'],50)
        passages=[r['premise'] for r in self.seen]
        first='Title: First\nA cobalt lamp.';second='Title: Second\nAn amber lamp.'
        self.assertEqual(passages,[first+'\n'+second,first,second,first])
        self.assertEqual(len({r['call_id'] for r in self.seen}),4)
        self.assertEqual([x['status'] for x in result['nli_calls']],['completed']*4)

    def test_citation_complementary_evidence_and_duplicates_preserve_native_calls(self):
        value=self.bridge([1,0,0,0,0]).metric('citations',[row('Cobalt [1][2].')])
        self.assertEqual(value['native_value']['citation_prec'],100)
        self.assertEqual(len(self.seen),5)
        self.seen=[]
        value=self.bridge([1,1,1]).metric('citations',[row('Cobalt [1][1].')])
        self.assertEqual(value['native_value']['citation_prec'],100)
        self.assertEqual(len(self.seen),3)
        self.assertEqual(value['diagnostics']['duplicate_citation_occurrences'],1)

    def test_citation_zero_missing_outofrange_and_unclosed_bracket_native_quirks(self):
        for output,expected,calls,invalid,tokens in [('Cobalt [0].',100,1,1,1),('Cobalt [3].',0,0,1,1),
                ('Cobalt.',0,0,0,0),('Cobalt [-1].',0,0,0,0),('Cobalt [1',100,1,0,0)]:
            with self.subTest(output=output):
                self.seen=[]
                value=self.bridge().metric('citations',[row(output)])
                self.assertEqual(value['native_value']['citation_rec'],expected)
                self.assertEqual(len(self.seen),calls)
                self.assertEqual(value['diagnostics']['strict_invalid_citation_token_count'],invalid)
                self.assertEqual(value['diagnostics']['strict_citation_token_count'],tokens)
                if '[0]' in output:self.assertEqual(self.seen[0]['premise'],'Title: Second\nAn amber lamp.')

    def test_citation_cap_range_check_order_and_qampari_question_prefix(self):
        docs=[dict(title=str(i),text=str(i)) for i in range(4)]
        result=self.bridge([1,1,1,1]).metric('citations',[row('Cobalt [1][2][3][4].',docs=docs)])
        self.assertEqual(len(result['nli_calls']),4)
        self.assertNotIn('Title: 3',self.seen[0]['premise'])
        self.seen=[]
        result=self.bridge().metric('citations',[row('Cobalt [1][2][3][9].',docs=docs)])
        self.assertEqual(result['native_value']['citation_rec'],0);self.assertEqual(self.seen,[])
        result=self.bridge().metric('citations',[row('cobalt [1], amber [2].')],qampari=True)
        self.assertEqual([r['hypothesis'] for r in self.seen],['Which fictional lamp? cobalt','Which fictional lamp? amber'])
        self.assertEqual(result['native_value']['citation_rec'],100)

    def test_empty_citation_denominator_and_nan_are_explicit_not_zero(self):
        called=[]
        def tokenize(text):called.append(text);return sentences(text)
        bridge=self.bridge(extra=dict(sent_tokenize=self.binding(tokenize)))
        result=bridge.metric('citations',[row(''),row()])
        self.assertEqual(result['native_value']['citation_rec'],100)
        self.assertEqual(result['diagnostics']['scheduled_count'],2)
        self.assertEqual(result['diagnostics']['native_empty_sentence_rows'],1)
        self.assertEqual(len(called),2)  # Supplemental diagnostics do not retokenize.
        result=bridge.metric('citations',[row('')])
        self.assertEqual(dict(result['native_value']),dict(citation_rec=None,citation_prec=None))
        self.assertEqual(len(result['native_nonfinite']),2);canonical(result)
        result=bridge.metric('citations',[row('')],qampari=True)
        self.assertEqual(result['native_value']['citation_rec'],0)
        self.assertEqual(result['diagnostics']['native_empty_sentence_rows'],0)

    def test_eli5_claim_requests_and_native_empty_claim_failure(self):
        bridge=self.bridge([1,0])
        result=bridge.metric('claims',[row('Cobalt [1].\nDiscarded.',claims=['Cobalt.','Amber.'])])
        self.assertEqual(result['native_value'],50)
        self.assertEqual([r['premise'] for r in self.seen],['Cobalt.','Cobalt.'])
        self.assertEqual([r['hypothesis'] for r in self.seen],['Cobalt.','Amber.'])
        with self.assertRaises(ZeroDivisionError):bridge.metric('claims',[row(claims=[])])

    def test_nli_failure_wrong_type_and_deadline_never_retry_or_synthesize_zero(self):
        for failure in (RuntimeError('invented inference failure'),KeyboardInterrupt()):
            called=[]
            def callback(request):called.append(request);raise failure
            bridge=self.bridge(callback=callback)
            with self.assertRaises(type(failure)):bridge.metric('citations',[row()])
            self.assertEqual(len(called),1)
            self.assertEqual(bridge.calls[0]['status'],'failed')
            self.assertIsNone(bridge.calls[0]['entailment'])
        for verdict in (True,False,2,None,'1',float('nan')):
            with self.subTest(verdict=verdict):
                bridge=self.bridge([verdict])
                with self.assertRaises(ContractError):bridge.metric('citations',[row()])
                self.assertEqual(len(bridge.calls),1)
        bridge=self.bridge()
        with self.assertRaises(TimeoutError):bridge.metric('citations',[row()],deadline=time.monotonic()-1)
        self.assertEqual(len(bridge.calls),0)
        def late(request):time.sleep(.02);return 1
        bridge=self.bridge(callback=late)
        with self.assertRaises(TimeoutError):bridge.metric('citations',[row()],deadline=time.monotonic()+.01)
        self.assertLessEqual(len(bridge.calls),1)

    def test_inflight_dependency_mutation_fails_after_callback(self):
        def callback(request):self.runtime.write_bytes(b'changed during inference');return 1
        bridge=self.bridge(callback=callback)
        with self.assertRaises(ContractError):bridge.metric('citations',[row()])
        self.assertEqual(len(bridge.calls),1)

    def test_rouge_native_lowercase_sentence_join_best_reference_and_explicit_backends(self):
        calls=[];aggregated=[]
        class Scorer:
            def __init__(self,metrics,use_stemmer):calls.append((metrics,use_stemmer))
            def score(self,reference,hypothesis):
                calls.append((reference,hypothesis))
                return {'rougeLsum':SimpleNamespace(fmeasure=.75 if reference=='better' else .25)}
        class Aggregator:
            def add_scores(self,scores):aggregated.append(scores['rougeLsum'].fmeasure)
            def aggregate(self):return {'rougeLsum':SimpleNamespace(mid=SimpleNamespace(fmeasure=sum(aggregated)/len(aggregated)))}
        bridge=self.bridge(extra=dict(rouge_scorer=self.binding(SimpleNamespace(RougeScorer=Scorer)),
            scoring=self.binding(SimpleNamespace(BootstrapAggregator=Aggregator))))
        result=bridge.metric('rouge',[row('COBALT [1].',annotations=[dict(long_answer='WORSE'),dict(long_answer='BETTER')])])
        self.assertEqual(result['native_value'],75)
        self.assertEqual(calls,[(['rougeLsum'],True),('worse','cobalt.'),('better','cobalt.')])
        self.assertEqual(aggregated,[.75])


if __name__=='__main__':unittest.main()
