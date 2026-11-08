"""Invented loaders/tensors only; pretrained weights are never imported or loaded."""
from contextlib import nullcontext
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from experiments.alce import native_runtime as r
from tether_engine.serde import ContractError, canonical


def put(path,value):
    path.write_bytes(canonical(value)+b'\n');return proof(path)


def proof(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


class Tensor:
    def __init__(self,shape=(1,7),device='cpu'):self.shape,self.device=shape,device
    def to(self,device):self.device=device;return self
    def __getitem__(self,item):return self


class Parameter:
    def __init__(self,dtype):self.dtype=dtype
    def is_floating_point(self):return True
    def numel(self):return 100


class Model:
    def __init__(self,dtype):
        self.dtype,self.device=dtype,'cuda:0'
        self.config=NS(pad_token_id=0,eos_token_id=1,decoder_start_token_id=0)
        self.hf_device_map={'encoder':'cuda:0','decoder':'cpu'}
        self.decoder=NS(register_forward_hook=Mock(return_value=NS(remove=lambda:None)))
        self.generate=Mock(return_value=Tensor((1,2)));self.is_quantized=False
    def eval(self):return self
    def to(self,device):self.device=device;return self
    def parameters(self):return iter([Parameter(self.dtype)])


class NativeRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.module_file=self.root/'invented_runtime.py';self.module_file.write_text('# invented dependency\n')
        self.events=[];self.end=time.monotonic()+60
        self.tokenizer=Mock(is_fast=False,legacy=True,eos_token_id=50256)
        self.tokenizer.return_value=NS(input_ids=Tensor());self.tokenizer.decode.return_value='1'
        self.model=Model('bf16')
        empty=dict(missing_keys=[],unexpected_keys=[],mismatched_keys=[],error_msgs=[])
        self.hf=NS(__file__=str(self.module_file),AutoTokenizer=NS(from_pretrained=Mock(return_value=self.tokenizer)),
            AutoModelForSeq2SeqLM=NS(from_pretrained=Mock(return_value=(self.model,empty))),
            AutoModelForQuestionAnswering=NS(from_pretrained=Mock(return_value=(Model('fp32'),empty))),
            AutoModel=NS(from_pretrained=Mock(return_value=(Model('fp32'),empty))),
            pipeline=Mock(return_value=Mock(return_value=[dict(answer='invented',score=.5)])))
        self.torch=NS(__file__=str(self.module_file),bfloat16='bf16',float32='fp32',inference_mode=nullcontext,
            cuda=NS(is_available=lambda:True,reset_peak_memory_stats=Mock(),max_memory_allocated=lambda _:42,
                    max_memory_reserved=lambda _:84))
        self.modules=dict(torch=self.torch,transformers=self.hf)

    def assets(self,product):
        root=self.root/product;root.mkdir(exist_ok=True)
        return NS(product=product,root=root,revalidate=Mock(),provenance=lambda:dict(product=product,invented=True))

    def true(self,emit=None):
        return r.TrueRuntime(self.assets('true_nli'),self.modules,deadline=self.end,
            emit=emit or (lambda e,v:self.events.append((e,v))),max_memory=dict(gpu_bytes=9_000_000_000,cpu_bytes=8*1024**3),
            offload_root=self.root/'offload')

    def request(self):
        return dict(logical_model=r.MODELS['true_nli'][0],max_new_tokens=10,premise='Invented premise',
            hypothesis='Invented claim',input_text='premise: Invented premise hypothesis: Invented claim')

    def test_true_exact_loader_tokenization_generation_and_literal_decoding(self):
        runtime=self.true();self.assertEqual(runtime(self.request()),1)
        args=self.hf.AutoModelForSeq2SeqLM.from_pretrained.call_args.kwargs
        self.assertEqual(args['dtype'],'bf16');self.assertTrue(args['local_files_only']);self.assertFalse(args['trust_remote_code'])
        self.assertEqual(args['max_memory'],{0:9_000_000_000,'cpu':8*1024**3})
        self.assertEqual(args['device_map'],'auto');self.assertEqual(args['attn_implementation'],'eager')
        self.assertEqual(self.hf.AutoTokenizer.from_pretrained.call_args.kwargs,
            dict(local_files_only=True,trust_remote_code=False,use_fast=False,legacy=True))
        self.assertEqual(self.tokenizer.call_args.kwargs,dict(return_tensors='pt',truncation=False,padding=False,add_special_tokens=True))
        self.assertEqual(self.model.generate.call_args.kwargs,r.TRUE_GENERATION)
        self.assertEqual(len(self.model.generate.call_args.args),1)
        self.assertEqual(self.tokenizer.decode.call_args.kwargs,dict(skip_special_tokens=True,clean_up_tokenization_spaces=True))
        for text in (' 1','1\n','yes','0',''):
            self.tokenizer.decode.return_value=text;self.assertEqual(runtime(self.request()),0)
        self.assertTrue(all(x['status']=='completed' for x in runtime.report()['calls']))

    def test_true_refuses_changed_request_before_model_call(self):
        runtime=self.true()
        for change in (dict(logical_model='other'),dict(max_new_tokens=9),dict(input_text='shortened'),dict(premise=None)):
            with self.subTest(change=change),self.assertRaises(ContractError):runtime(dict(self.request(),**change))
        self.model.generate.assert_not_called()

    def test_unknown_keys_dtype_quantization_device_and_fast_tokenizer_fail(self):
        for defect in ('keys','dtype','quantized','meta','fast'):
            with self.subTest(defect=defect):
                self.setUp()
                if defect=='keys':self.hf.AutoModelForSeq2SeqLM.from_pretrained.return_value=(self.model,{'missing_keys':['one']})
                if defect=='dtype':self.model.dtype='fp32'
                if defect=='quantized':self.model.is_quantized=True
                if defect=='meta':self.model.device='meta'
                if defect=='fast':self.tokenizer.is_fast=True
                with self.assertRaises(ContractError):self.true()
                self.model.generate.assert_not_called()

    def test_oom_and_post_call_deadline_preserve_failed_attempt_no_retry(self):
        runtime=self.true();self.model.generate.side_effect=RuntimeError('invented OOM')
        with self.assertRaises(RuntimeError):runtime(self.request())
        self.assertEqual(runtime.calls[0]['status'],'failed');self.assertTrue(runtime.failed)
        with self.assertRaises(ContractError):runtime(self.request())
        self.assertEqual(self.model.generate.call_count,1)

    def test_call_reservation_write_failure_is_terminal_before_model(self):
        def emit(event,value):
            if event=='call_entered':raise OSError('invented storage failure')
        runtime=self.true(emit)
        with self.assertRaises(OSError):runtime(self.request())
        self.assertTrue(runtime.failed)
        self.model.generate.assert_not_called()

    def test_qa_exact_local_checkpoint_and_native_pipeline_call(self):
        runtime=r.QARuntime(self.assets('qa_roberta'),self.modules,deadline=self.end,emit=lambda *x:None)
        answer=runtime.pipeline('question-answering',model=r.MODELS['qa_roberta'][0],device=0)
        result=answer(question=['Invented?'],context='Invented context',handle_impossible_answer=True)
        self.assertEqual(result,[dict(answer='invented',score=.5)])
        self.assertTrue(self.hf.AutoModelForQuestionAnswering.from_pretrained.call_args.kwargs['local_files_only'])
        self.assertEqual(self.hf.pipeline.call_args.kwargs['device'],0)
        with self.assertRaises(ContractError):runtime.pipeline('question-answering',model='other',device=0)
        with self.assertRaises(ContractError):answer(question=['Invented?'],context='x',handle_impossible_answer=False)

    def test_mauve_whole_distribution_native_preprocessing_and_settings(self):
        backend=NS(__file__=str(self.module_file),MODEL=None,TOKENIZER=None,MODEL_NAME=None,
                   compute_mauve=Mock(return_value=NS(mauve=.75)))
        modules=dict(self.modules,mauve=backend)
        runtime=r.MauveRuntime(self.assets('gpt2_large'),modules,deadline=self.end,emit=lambda e,v:self.events.append((e,v)))
        source=Path(__file__).resolve().parent/'fixtures/alce_native/eval.py'
        rows=[dict(question='Invented?',answer=' A\nB! ',output=' C\nD. '),
              dict(question='Another?',answer=' '.join(['x']*105),output='y')]
        self.assertEqual(runtime.metric(rows,{'eval.py':proof(source)})['native_value'],75)
        options=backend.compute_mauve.call_args.kwargs
        self.assertEqual(options['p_text'][0],'Invented? A B');self.assertEqual(options['q_text'][0],'Invented? C D')
        self.assertEqual(len(options['p_text'][1].split()),100)
        self.assertEqual({k:options[k] for k in r.MAUVE_OPTIONS},r.MAUVE_OPTIONS)
        with self.assertRaises(ContractError):runtime.metric(rows,{'eval.py':proof(source)})
        self.assertEqual(backend.compute_mauve.call_count,1)

    def test_mauve_prior_global_cache_and_model_identity_rejected(self):
        backend=NS(__file__=str(self.module_file),MODEL=object(),TOKENIZER=None,MODEL_NAME=None)
        with self.assertRaises(ContractError):r.MauveRuntime(self.assets('gpt2_large'),dict(self.modules,mauve=backend),deadline=self.end,emit=lambda *x:None)
        self.hf.AutoModel.from_pretrained.assert_not_called()

    def test_changed_runtime_source_or_expired_deadline_prevents_native_call(self):
        runtime=self.true();self.module_file.write_text('# changed runtime')
        with self.assertRaises(ContractError):runtime(self.request())
        self.model.generate.assert_not_called()
        runtime.deadline=time.monotonic()-1
        with self.assertRaises(TimeoutError):runtime(self.request())

    def test_dependency_imports_are_explicit_and_version_bound(self):
        importer=Mock(side_effect=lambda name:NS(__version__=r.VERSIONS[name]))
        with patch.object(r.importlib,'import_module',importer):r.dependencies()
        self.assertEqual([c.args[0] for c in importer.call_args_list],list(r.VERSIONS))
        with patch.object(r.importlib,'import_module',return_value=NS(__version__='wrong')):
            with self.assertRaises(ContractError):r.dependencies()

    def test_loading_info_requires_all_four_exact_empty_lists(self):
        valid=dict(missing_keys=[],unexpected_keys=[],mismatched_keys=[],error_msgs=[])
        r.loading_info(valid)
        for value in ({},{'missing_keys':[]},dict(valid,error_msgs=False),dict(valid,unexpected_keys=None),dict(valid,mismatched_keys=())):
            with self.subTest(value=value),self.assertRaises(ContractError):r.loading_info(value)


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.end=time.monotonic()+30
        self.product='qa_roberta';self.assets=self.root/'payloads/models'/self.product;self.assets.mkdir(parents=True)
        metadata=put(self.root/'METADATA.json',{'invented':True});rows=[];observed=[]
        for i,name in enumerate(sorted(r.FILES[self.product])):
            path=self.assets/name;path.write_bytes(('invented '+name).encode());p=proof(path)
            asset=dict(id=f'file{i}',product_id=self.product,destination=f'models/{self.product}/{name}',expected_bytes=p['bytes'],
                revision=dict(kind='git_commit',value=r.MODELS[self.product][1]),digest=dict(kind='content',algorithm='sha256',value=p['sha256']),metadata_proof=metadata,rights_reference='invented')
            rows.append(asset);observed.append(dict(asset,path=p['path'],bytes=p['bytes'],sha256=p['sha256'],status='completed',attempts=1))
        self.manifest=put(self.root/'MANIFEST.json',dict(kind='alce_acquisition_manifest_v1',assets=rows,limits=dict(total_seconds=30)))
        self.worker=put(self.root/'WORKER.json',dict(kind='alce_acquisition_worker_receipt_v1',status='completed',hard_parent_supervision=True,manifest=self.manifest,files=observed))
        (self.root/'stdout.bin').write_bytes(b'');(self.root/'stderr.bin').write_bytes(b'')
        process=put(self.root/'PROCESS.json',dict(returncode=0,supervision=dict(schema_version=1,method='tether.process_envelope.v1',
            limits=dict(timeout_seconds=29,max_output_bytes=4*1024**2),termination_reason='exited',execution_elapsed_seconds=.1,total_elapsed_seconds=.2,
            retained_stdout_bytes=0,retained_stderr_bytes=0,observed_stdout_bytes=0,observed_stderr_bytes=0,observed_counts_are_lower_bounds=False,
            pipe_eof=dict(stdout=True,stderr=True),process_started=True,process_reaped=True,cleanup_errors=[])))
        self.value=dict(kind='alce_acquisition_receipt_v1',status='verified',worker_receipt=self.worker,manifest=self.manifest,process=process,automatic_retries=0,range_resume=False,payload_hashes_rechecked=True)
        self.receipt=put(self.root/'RECEIPT.json',self.value)

    def test_all_selected_assets_source_bound_and_rehashed(self):
        assets=r.ModelAssets(self.receipt,self.product,deadline=self.end)
        self.assertEqual(set(assets.files),r.FILES[self.product]);assets.revalidate(self.end,full=True)

    def test_changed_payload_omission_extra_member_and_failure_marker_rejected(self):
        for defect in ('payload','omission','extra','failure'):
            with self.subTest(defect=defect):
                self.setUp()
                if defect=='payload':(self.assets/'config.json').write_bytes(b'changed')
                if defect=='omission':(self.assets/'config.json').unlink()
                if defect=='extra':(self.assets/'unlisted.bin').write_bytes(b'extra')
                if defect=='failure':(self.root/'FAILED.json').write_bytes(b'{}')
                with self.assertRaises((ContractError,FileNotFoundError)):r.ModelAssets(self.receipt,self.product,deadline=self.end)

    def test_late_identity_or_acquisition_stream_change_rejected(self):
        assets=r.ModelAssets(self.receipt,self.product,deadline=self.end)
        (self.root/'stdout.bin').write_bytes(b'late')
        with self.assertRaises(ContractError):assets.revalidate(self.end)


if __name__=='__main__':unittest.main()
