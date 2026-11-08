"""Local-only native evaluator adapters; loading is explicit and lazy.

These adapters retain the pinned evaluator's arithmetic and model identities.
They do not establish hardware feasibility or scientific accuracy. A dedicated
worker with a hard deadline, offline guard, and external process supervision is
required. Placement limits are hints, not operating-system memory limits.
"""
from __future__ import annotations

import ast
from collections import Counter
from collections.abc import Mapping
import hashlib
import importlib
import math
import os
from pathlib import Path
import string
import time
import types

from tether_engine.serde import canonical, encode, freeze, parse_json
from .data_views import _acquisition_process, _hash, _identity, _path, _read, _tick, need


MODELS = {
    'true_nli': ('google/t5_xxl_true_nli_mixture', 'aa6cfe1dd4257853bfdd772992045f41bfc14988'),
    'qa_roberta': ('gaotianyu1350/roberta-large-squad', '02bcd9fab9c9d84a346389074e0bcdf770c5141b'),
    'gpt2_large': ('openai-community/gpt2-large', '32b71b12589c2f8d625668d2335a01cac3249519'),
}
FILES = {
    'true_nli': {'README.md', 'config.json', 'generation_config.json', 'pytorch_model.bin.index.json',
        'special_tokens_map.json', 'spiece.model', 'tokenizer_config.json',
        *(f'pytorch_model-{i:05}-of-00005.bin' for i in range(1, 6))},
    'qa_roberta': {'README.md', 'config.json', 'pytorch_model.bin', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json'},
    'gpt2_large': {'README.md', 'config.json', 'generation_config.json', 'pytorch_model.bin',
        'merges.txt', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json'},
}
VERSIONS = {'torch': '2.7.1+cu128', 'transformers': '4.57.1', 'accelerate': '1.11.0'}
TRUE_GENERATION = dict(max_new_tokens=10, min_length=0, min_new_tokens=None, early_stopping=False,
    max_time=None, do_sample=False, num_beams=1, num_beam_groups=1, use_cache=True,
    temperature=1.0, top_k=50, top_p=1.0, typical_p=1.0, repetition_penalty=1.0,
    encoder_repetition_penalty=1.0, length_penalty=1.0, no_repeat_ngram_size=0,
    encoder_no_repeat_ngram_size=0, bad_words_ids=None, forced_bos_token_id=None,
    forced_eos_token_id=None, renormalize_logits=False, remove_invalid_values=False,
    num_return_sequences=1, return_dict_in_generate=False, pad_token_id=0, bos_token_id=None,
    eos_token_id=1, decoder_start_token_id=0, cache_implementation=None, cache_config=None,
    prefill_chunk_size=None, stop_strings=None, token_healing=False, assistant_model=None,
    disable_compile=True)
MAUVE_OPTIONS = dict(num_buckets='auto', pca_max_data=-1, kmeans_explained_var=0.9,
    kmeans_num_redo=5, kmeans_max_iter=500, featurize_model_name='gpt2-large', device_id=0,
    max_text_length=512, divergence_curve_discretization_size=25, mauve_scaling_factor=5,
    verbose=True, seed=25, batch_size=8, use_float64=False)


class ModelAssets:
    """Selected model bytes admitted through an externally anchored acquisition.

No file is imported or deserialized here. Strong hashing occurs on admission and
explicit full revalidation. Intermediate identity checks only detect drift; they
are not advertised as substitutes for a final strong hash check.
"""
    def __init__(self, acquisition_receipt, product, *, deadline):
        need(product in MODELS, 'Known exact model product required')
        _tick(deadline)
        receipt = parse_json(_read(acquisition_receipt, 16*1024**2, deadline))
        root = _path(acquisition_receipt['path']).parent
        need(receipt.get('kind') == 'alce_acquisition_receipt_v1' and receipt.get('status') == 'verified'
             and type(receipt.get('automatic_retries')) is int and receipt.get('automatic_retries') == 0 and receipt.get('range_resume') is False
             and receipt.get('payload_hashes_rechecked') is True, 'Verified acquisition required')
        for name in ('FAILED.json', 'SUPERVISOR-FAILED.json', 'STALLED.json', 'DEADLINE.json', 'FAILURE.json'):
            need(not (root/name).exists(), 'Acquisition has a failure marker')
        worker = parse_json(_read(receipt['worker_receipt'], 16*1024**2, deadline))
        manifest = parse_json(_read(receipt['manifest'], 16*1024**2, deadline))
        need(manifest.get('kind')=='alce_acquisition_manifest_v1', 'Exact acquisition manifest kind')
        need(worker.get('kind') == 'alce_acquisition_worker_receipt_v1' and worker.get('status') == 'completed'
             and worker.get('hard_parent_supervision') is True and worker.get('manifest') == receipt['manifest'],
             'Source worker receipt binding')
        process = _acquisition_process(receipt['process'], root, manifest['limits']['total_seconds'], deadline)
        selected = [a for a in manifest['assets'] if a['product_id'] == product]
        need(len(selected) == len(FILES[product]) and len({a['id'] for a in selected}) == len(selected), 'Full selected model membership')
        observed = {a['id']: a for a in worker['files']}
        need(len(observed) == len(worker['files']), 'Unique worker asset IDs')
        proofs = {}
        for row in selected:
            destination = Path(row['destination'])
            need(destination.as_posix() == f'models/{product}/{destination.name}' and destination.name in FILES[product]
                 and row['revision'] == dict(kind='git_commit', value=MODELS[product][1]), 'Pinned model revision/destination')
            actual = observed[row['id']]
            need(actual['status'] == 'completed' and type(actual['attempts']) is int and actual['attempts'] == 1
                 and all(actual[k] == row[k] for k in ('destination', 'expected_bytes', 'digest', 'revision', 'metadata_proof', 'rights_reference')),
                 'Selected asset source binding')
            path = _path(root/'payloads'/destination)
            expected = dict(path=str(path), bytes=row['expected_bytes'], sha256=actual['sha256'])
            need(actual['path'] == str(path) and actual['bytes'] == row['expected_bytes'] and _hash(path, deadline) == expected,
                 'Selected model content bytes differ')
            if row['digest']['kind'] == 'content':
                need(row['digest'] == dict(kind='content', algorithm='sha256', value=expected['sha256']), 'Upstream content digest differs')
            else:
                raw = _read(expected, 16*1024**2, deadline)
                blob = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
                need(row['digest'] == dict(kind='git_blob', algorithm='sha1', value=blob), 'Upstream Git blob differs')
            need(destination.name not in proofs, 'Duplicate selected filename')
            proofs[destination.name] = expected
        self.root = _path(root/'payloads/models'/product)
        need(set(proofs) == FILES[product] and {p.name for p in self.root.iterdir()} == FILES[product], 'Closed selected model directory')
        self.product, self.files = product, freeze(proofs)
        self._acquisition_root = root
        self._controls = freeze(dict(acquisition=acquisition_receipt, worker=receipt['worker_receipt'], manifest=receipt['manifest'], process=process))
        self._identities = {name: _identity(_path(p['path']).stat()) for name, p in proofs.items()}

    def revalidate(self, deadline, *, full=False):
        _tick(deadline)
        for name in ('FAILED.json','SUPERVISOR-FAILED.json','STALLED.json','DEADLINE.json','FAILURE.json'):
            need(not (self._acquisition_root/name).exists(), 'Acquisition late failure marker')
        need({p.name for p in self.root.iterdir()} == set(self.files), 'Model directory membership changed')
        for name, p in self.files.items():
            path = _path(p['path'])
            need(_identity(path.stat()) == self._identities[name], 'Model file identity changed')
            if full: need(_hash(path, deadline) == dict(p), 'Model content changed')
        for key in ('acquisition', 'worker', 'manifest'):
            _read(self._controls[key], 16*1024**2, deadline)
        process = self._controls['process']
        _read(process['proof'], 1024**2, deadline)
        for p in process['streams'].values(): need(_hash(p['path'], deadline) == dict(p), 'Acquisition stream changed')

    def provenance(self):
        return freeze(dict(product=self.product, logical_model=MODELS[self.product][0], revision=MODELS[self.product][1],
                           local_checkpoint=str(self.root), files=self.files, acquisition=self._controls))


def dependencies(*, include_mauve=False):
    """Lazy imports; caller installs the qualified offline guard first."""
    result = {name: importlib.import_module(name) for name in VERSIONS}
    for name, expected in VERSIONS.items(): need(result[name].__version__ == expected, 'Qualified runtime version differs: '+name)
    if include_mauve:
        result['mauve'] = importlib.import_module('mauve.compute_mauve')
    return result


def loaded_modules(modules, deadline):
    return {name: _hash(Path(module.__file__).resolve(), deadline) for name, module in modules.items()}


def loading_info(info):
    keys={'missing_keys','unexpected_keys','mismatched_keys','error_msgs'}
    need(isinstance(info, Mapping) and set(info)==keys and all(type(info[k])is list and info[k]==[] for k in keys),
         'Four explicit empty weight-error lists required')


def parameter_info(model, dtype):
    counts, elements = Counter(), 0
    for parameter in model.parameters():
        if parameter.is_floating_point(): need(parameter.dtype == dtype, 'Native parameter dtype differs')
        counts[str(parameter.dtype)] += parameter.numel(); elements += parameter.numel()
    need(elements > 0 and not getattr(model, 'is_quantized', False), 'Full unquantized model parameters required')
    return dict(elements=elements, dtype_elements=dict(counts))


def _gpu(torch):
    if not torch.cuda.is_available(): return dict(available=False, peak_allocated_bytes=None, peak_reserved_bytes=None)
    return dict(available=True, peak_allocated_bytes=int(torch.cuda.max_memory_allocated(0)),
                peak_reserved_bytes=int(torch.cuda.max_memory_reserved(0)))


def _finite_time(deadline):
    need(type(deadline) in (int,float) and math.isfinite(deadline), 'Finite absolute runtime deadline required')
    _tick(deadline)


class _Runtime:
    def __init__(self, assets, modules, *, deadline, emit):
        _finite_time(deadline)
        self.assets, self.modules, self.deadline, self.emit = assets, modules, deadline, emit
        self.calls, self.failed, self.used = [], False, False
        self._module_proofs = loaded_modules(modules, deadline)
        self.assets.revalidate(deadline)
        self.torch, self.hf = modules['torch'], modules['transformers']
        if self.torch.cuda.is_available(): self.torch.cuda.reset_peak_memory_stats(0)

    def check(self):
        _tick(self.deadline); need(not self.failed, 'Failed runtime is never automatically resumed')
        self.assets.revalidate(self.deadline)
        for p in self._module_proofs.values():
            need(_hash(p['path'], self.deadline) == p, 'Loaded runtime source changed')

    def call(self, kind, request, function):
        self.check()
        record = dict(ordinal=len(self.calls), kind=kind, request_sha256=hashlib.sha256(canonical(request)).hexdigest(),
                      status='entered', elapsed_seconds=None, error_type=None)
        self.calls.append(record)
        started = time.monotonic()
        try:
            self.emit('call_entered', dict(record))
            result = function()
            self.check()
            self.emit('native_result_observed',dict(ordinal=record['ordinal'],kind=kind,
                result_sha256=hashlib.sha256(canonical(result)).hexdigest()))
            record.update(status='completed', elapsed_seconds=time.monotonic()-started)
            self.emit('call_completed', dict(record))
            return result
        except BaseException as error:
            self.failed = True
            record.update(status='failed', elapsed_seconds=time.monotonic()-started, error_type=type(error).__name__)
            try: self.emit('call_failed', dict(record))
            except BaseException as persistence: error.add_note('Call failure retention failed: '+type(persistence).__name__)
            raise

    def report(self):
        return freeze(dict(model=self.assets.provenance(), runtime_sources=self._module_proofs, calls=self.calls,
                           gpu=_gpu(self.torch), failed=self.failed, automatic_retries=0))


class TrueRuntime(_Runtime):
    def __init__(self, assets, modules, *, deadline, emit, max_memory, offload_root):
        need(assets.product == 'true_nli', 'Exact TRUE assets required')
        need(type(max_memory) is dict and set(max_memory) == {'gpu_bytes','cpu_bytes'} and
             all(type(v) is int and v > 0 for v in max_memory.values()), 'Explicit CPU/GPU placement bytes required')
        offload = _path(offload_root)
        need(offload.parent.is_dir() and not offload.exists() and not offload.is_relative_to(assets.root)
             and not assets.root.is_relative_to(offload), 'Fresh separate weight offload directory required')
        super().__init__(assets, modules, deadline=deadline, emit=emit)
        need(self.torch.cuda.is_available(), 'Declared CUDA TRUE placement unavailable')
        offload.mkdir()
        emit('model_load_entered', dict(product='true_nli', dtype='bfloat16', placement=max_memory, offload=str(offload)))
        self.tokenizer = self.hf.AutoTokenizer.from_pretrained(str(assets.root), local_files_only=True,
            trust_remote_code=False, use_fast=False, legacy=True)
        self.model, info = self.hf.AutoModelForSeq2SeqLM.from_pretrained(str(assets.root), local_files_only=True,
            trust_remote_code=False, use_safetensors=False, dtype=self.torch.bfloat16, device_map='auto',
            max_memory={0:max_memory['gpu_bytes'], 'cpu':max_memory['cpu_bytes']}, offload_folder=str(offload),
            offload_state_dict=True, output_loading_info=True, attn_implementation='eager')
        loading_info(info); self.model.eval()
        self.parameters = parameter_info(self.model, self.torch.bfloat16)
        need(not self.tokenizer.is_fast and getattr(self.tokenizer, 'legacy', None) is True,
             'Slow legacy TRUE tokenizer required')
        for name, value in dict(pad_token_id=0,eos_token_id=1,decoder_start_token_id=0).items():
            need(getattr(self.model.config,name) == value, 'TRUE generation token identity differs')
        need(str(self.model.device) != 'meta', 'Model input device is not materialized')
        self.cache_observations = []
        self._hook = self.model.decoder.register_forward_hook(self._cache)
        self.check()
        emit('model_load_completed', dict(product='true_nli', parameters=self.parameters,
            device_map=dict(self.model.hf_device_map), input_device=str(self.model.device), generation=TRUE_GENERATION))

    def _cache(self, module, args, output):
        cache = getattr(output, 'past_key_values', None)
        if cache is None: return
        tensors = []
        for kind in ('self_attention_cache','cross_attention_cache'):
            for i, layer in enumerate(getattr(getattr(cache,kind,None),'layers',())):
                for field in ('keys','values'):
                    value = getattr(layer,field,None)
                    if value is not None:
                        tensors.append(dict(kind=kind,layer=i,field=field,dtype=str(value.dtype),
                                            device=str(value.device),shape=list(value.shape),bytes=value.numel()*value.element_size()))
        need(len(tensors) <= 192, 'Unexpected cache instrumentation scope')
        if len(self.cache_observations) < 10:
            self.cache_observations.append(dict(type=type(cache).__name__,tensors=tensors or None,
                observed=bool(tensors),reason=None if tensors else 'unsupported_or_empty_cache_introspection'))

    def __call__(self, request):
        need(isinstance(request,Mapping) and request.get('logical_model') == MODELS['true_nli'][0]
             and request.get('max_new_tokens') == 10 and type(request.get('premise')) is str
             and type(request.get('hypothesis')) is str and request.get('input_text') ==
             f"premise: {request['premise']} hypothesis: {request['hypothesis']}", 'Exact native TRUE request required')
        def generate():
            self.cache_observations = []
            encoded = self.tokenizer(request['input_text'], return_tensors='pt', truncation=False,
                padding=False, add_special_tokens=True)
            ids = encoded.input_ids.to(self.model.device)
            need(len(ids.shape)==2 and ids.shape[0]==1, 'One complete TRUE input required')
            self.emit('true_tokens_prepared', dict(input_tokens=int(ids.shape[-1]), truncation=False,
                forwarded_fields=['input_ids']))
            with self.torch.inference_mode(): outputs=self.model.generate(ids, **TRUE_GENERATION)
            result=self.tokenizer.decode(outputs[0], skip_special_tokens=True, clean_up_tokenization_spaces=True)
            need(type(result) is str, 'Native decoded text required')
            self.emit('true_generation_observed', dict(output_tokens=int(outputs.shape[-1]),
                ordinal=len(self.calls)-1,decoded_text=result, entailment=int(result=='1'), cache=self.cache_observations or None,
                cache_instrumentation_reason=None if self.cache_observations and all(x['observed'] for x in self.cache_observations)
                    else 'unsupported_or_no_native_cache_observation',gpu=_gpu(self.torch)))
            return int(result=='1')
        return self.call('true_nli', request, generate)


class QARuntime(_Runtime):
    def __init__(self, assets, modules, *, deadline, emit):
        need(assets.product=='qa_roberta', 'Exact native QA assets required')
        super().__init__(assets,modules,deadline=deadline,emit=emit)
        need(self.torch.cuda.is_available(), 'Native QA device0 unavailable')
        emit('model_load_entered', dict(product='qa_roberta', dtype='float32'))
        tokenizer=self.hf.AutoTokenizer.from_pretrained(str(assets.root),local_files_only=True,trust_remote_code=False,use_fast=True)
        model,info=self.hf.AutoModelForQuestionAnswering.from_pretrained(str(assets.root),local_files_only=True,
            trust_remote_code=False,use_safetensors=False,dtype=self.torch.float32,output_loading_info=True,attn_implementation='eager')
        loading_info(info);model.eval();self.parameters=parameter_info(model,self.torch.float32)
        self._pipeline=self.hf.pipeline('question-answering',model=model,tokenizer=tokenizer,device=0)
        self.check();emit('model_load_completed',dict(product='qa_roberta',parameters=self.parameters))

    def pipeline(self, task, *, model, device):
        need(task=='question-answering' and model==MODELS['qa_roberta'][0] and type(device)is int and device==0,
             'Exact original QA pipeline invocation required')
        def answer(*,question,context,handle_impossible_answer):
            need(isinstance(question,(list,tuple)) and question and all(type(q)is str for q in question)
                 and type(context)is str and handle_impossible_answer is True, 'Native QA request shape')
            request=dict(question=list(question),context=context,handle_impossible_answer=True)
            return self.call('qa',request,lambda:self._pipeline(**request))
        return answer


class MauveRuntime(_Runtime):
    def __init__(self,assets,modules,*,deadline,emit):
        need(assets.product=='gpt2_large' and 'mauve' in modules,'Exact native MAUVE assets/runtime required')
        super().__init__(assets,modules,deadline=deadline,emit=emit)
        need(self.torch.cuda.is_available(),'Native MAUVE device0 unavailable')
        backend=modules['mauve']
        need(backend.MODEL is None and backend.TOKENIZER is None and backend.MODEL_NAME is None,'Fresh MAUVE process/global cache required')
        emit('model_load_entered',dict(product='gpt2_large',dtype='float32'))
        tokenizer=self.hf.AutoTokenizer.from_pretrained(str(assets.root),local_files_only=True,trust_remote_code=False)
        model,info=self.hf.AutoModel.from_pretrained(str(assets.root),local_files_only=True,trust_remote_code=False,
            use_safetensors=False,pad_token_id=tokenizer.eos_token_id,dtype=self.torch.float32,
            output_loading_info=True,attn_implementation='eager')
        loading_info(info);model=model.to('cuda:0').eval();self.parameters=parameter_info(model,self.torch.float32)
        backend.MODEL,backend.TOKENIZER,backend.MODEL_NAME=model,tokenizer,'gpt2-large'
        self.backend=backend;self.check()
        emit('model_load_completed',dict(product='gpt2_large',parameters=self.parameters,settings=MAUVE_OPTIONS))

    def metric(self,normalized_rows,source_proofs):
        from .native_metrics import SOURCE_SHA256, _native_json
        need(not self.used,'MAUVE full-family distribution is evaluated once per worker')
        need(isinstance(normalized_rows,(list,tuple)) and normalized_rows and all(isinstance(r,Mapping)
             and all(type(r.get(k))is str for k in ('question','answer','output')) for r in normalized_rows),
             'Complete original-order normalized family required')
        p=source_proofs['eval.py'];need(p['sha256']==SOURCE_SHA256['eval.py'],'Exact native MAUVE source')
        raw=_read(p,1024**2,self.deadline)
        nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='compute_mauve']
        need(len(nodes)==1 and not nodes[0].decorator_list,'Single undecorated native MAUVE function')
        def compute(**kwargs):
            expected={k:MAUVE_OPTIONS[k] for k in ('device_id','max_text_length','verbose','batch_size','featurize_model_name')}
            need(set(kwargs)==set(expected)|{'p_text','q_text'} and all(kwargs[k]==v for k,v in expected.items()),'Native MAUVE call drift')
            self.emit('mauve_distribution_prepared',dict(scheduled_count=len(normalized_rows),
                p_count=len(kwargs['p_text']),q_count=len(kwargs['q_text']),settings=MAUVE_OPTIONS))
            return self.backend.compute_mauve(p_text=kwargs['p_text'],q_text=kwargs['q_text'],**MAUVE_OPTIONS)
        proxy=types.SimpleNamespace(compute_mauve=compute)
        def importer(name,*args,**kwargs):
            need(name=='mauve','Only explicit local MAUVE runtime import admitted');return proxy
        env=dict(__builtins__={'__import__':importer},logger=types.SimpleNamespace(info=lambda *a:None),string=string)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pinned-native-mauve>','exec'),env)
        self.used=True
        def evaluate():
            result=env['compute_mauve'](encode(normalized_rows))
            _read(p,1024**2,self.deadline)
            flags=[]; value=_native_json(result,nonfinite=flags)
            need(value is None or type(value)in(int,float),'Native scalar full-distribution MAUVE required')
            return freeze(dict(native_value=value,native_nonfinite=flags,
                               scheduled_count=len(normalized_rows),settings=MAUVE_OPTIONS))
        return self.call('mauve',normalized_rows,evaluate)
