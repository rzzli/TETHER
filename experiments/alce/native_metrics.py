"""Pinned ALCE function bodies with explicit, provenance-bearing dependencies.

No upstream module or CLI is imported. Only named function definitions and the
native output-normalization statements are compiled after full-source hashes
match. Optional numerical/tokenizer/model dependencies are trusted Python
bindings supplied by the qualified caller; recording their provenance does not
itself qualify them. Native quirks and missingness are never silently repaired.
"""
import ast
import builtins
import collections
from collections.abc import Mapping
import copy
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import re
import string
import time

from tether_engine.serde import ContractError, canonical, encode, freeze
from .data_views import _read

COMMIT = '246c476a4edfc564266b7346b6e29ef4861ae937'
SOURCE_SHA256 = {
    'eval.py': 'e0f63bf865cacc64d7390fc62669c82b2653b1628f40051de0efdf5518064091',
    'utils.py': '92e6900b5350f7da4dc179f3d9f498f73d976377a412e8c244db8339ad7976b9',
}
QA_MODEL = 'gaotianyu1350/roberta-large-squad'
NLI_MODEL = 'google/t5_xxl_true_nli_mixture'
EVAL_FUNCTIONS = ('compute_f1','compute_exact','exact_presence','compute_rouge','compute_str_em',
                  'compute_len','compute_qa','compute_claims','compute_autoais','compute_qampari_f1')
UTIL_FUNCTIONS = ('normalize_answer','remove_citations')
METRICS = dict(str_em='compute_str_em', length='compute_len', qampari='compute_qampari_f1',
               citations='compute_autoais', claims='compute_claims', qa='compute_qa', rouge='compute_rouge')
DEPENDENCIES = dict(str_em=('np',), length=(), qampari=('np',),
                    citations=('np','sent_tokenize'), claims=('np',), qa=('np','pipeline'),
                    rouge=('sent_tokenize','rouge_scorer','scoring'))


class UnsupportedMetric(ContractError):
    """An optional native dependency has not been explicitly supplied."""


def need(value,message):
    if not value:
        raise ContractError(message)


@dataclass(frozen=True)
class Binding:
    """Trusted in-process dependency plus an immutable declaration of its origin."""
    value: object
    provenance: Mapping

    def __post_init__(self):
        p=self.provenance
        need(isinstance(p,Mapping) and set(p)=={'name','version','configuration','files'}, 'Runtime provenance schema')
        need(isinstance(p['name'],str) and p['name'] and isinstance(p['version'],str) and p['version'] and
             isinstance(p['configuration'],Mapping) and isinstance(p['files'],(list,tuple)) and p['files'],
             'Runtime version/configuration/file provenance required')
        canonical(p)
        object.__setattr__(self,'provenance',freeze(p))


class _Quiet:
    def info(self,*args,**kwargs):pass
    def warn(self,*args,**kwargs):pass
    def warning(self,*args,**kwargs):pass


def _native_json(value, path='$', nonfinite=None):
    """Preserve undefined native values as null with separate explicit flags."""
    if nonfinite is None:nonfinite=[]
    if isinstance(value,Mapping):
        return {key:_native_json(item,path+'.'+key,nonfinite) for key,item in value.items()}
    if isinstance(value,(list,tuple)):
        return [_native_json(item,f'{path}[{i}]',nonfinite) for i,item in enumerate(value)]
    if isinstance(value,(int,float)) and not isinstance(value,bool):
        if isinstance(value,float) and not math.isfinite(value):
            nonfinite.append(dict(path=path,reason='native_nonfinite',raw_value='NaN' if math.isnan(value)
                                  else ('Infinity' if value>0 else '-Infinity')))
            return None
        return value
    # NumPy scalar outputs are explicit runtime results, never silently coerced
    # arrays or complex values. Its scalar .item() retains the corresponding type.
    if type(value).__module__.startswith('numpy') and hasattr(value,'item'):
        scalar=value.item()
        need(type(scalar) in (int,float),'Scalar native numerical result required')
        return _native_json(scalar,path,nonfinite)
    need(value is None or isinstance(value,(str,bool)),'JSON-compatible native result required')
    return value


def _selected(source,names):
    tree=ast.parse(source)
    functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    need(all(name in functions for name in names),'Pinned native function missing')
    need(all(not functions[name].decorator_list for name in names),'Unexpected native decorator')
    return tree,[functions[name] for name in names]


def _preprocessing(tree):
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    positions=[i for i,node in enumerate(main.body) if isinstance(node,ast.Assign) and
               len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='normalized_data']
    need(len(positions)==1,'Native preprocessing location')
    index=positions[0]
    body=copy.deepcopy(main.body[index-1:index+2])
    need(len(body)==3 and isinstance(body[0],ast.For) and isinstance(body[1],ast.Assign) and
         isinstance(body[2],ast.For),'Native preprocessing statements')
    wrapper=ast.parse('def _preprocess(data):\n    pass\n').body[0]
    wrapper.body=body+[ast.Return(value=ast.Tuple(elts=[ast.Name(id='data',ctx=ast.Load()),
                                                      ast.Name(id='normalized_data',ctx=ast.Load())],ctx=ast.Load()))]
    return ast.fix_missing_locations(wrapper)


class NativeBridge:
    """Operation-local native metrics; no default model/runtime acquisition route."""
    def __init__(self, source_proofs, *, revision=COMMIT, bindings=None, nli=None):
        need(revision==COMMIT and isinstance(source_proofs,Mapping) and set(source_proofs)==set(SOURCE_SHA256),
             'Exact pinned ALCE source revision required')
        self._sources=freeze(source_proofs)
        self._bindings=dict(bindings or {})
        need(set(self._bindings)<={'np','sent_tokenize','pipeline','rouge_scorer','scoring'} and
             all(isinstance(v,Binding) for v in self._bindings.values()),'Explicit supported runtime bindings only')
        need(nli is None or isinstance(nli,Binding) and callable(nli.value),'Explicit NLI callback binding')
        self._nli=nli
        self._calls=[]
        self._events=[]
        self._sentence_counts=[]
        self._deadline=None
        self._active=False
        source={}
        for name,p in self._sources.items():
            need(p['sha256']==SOURCE_SHA256[name],'Native source hash differs')
            source[name]=_read(p,1024**2,time.monotonic()+60).decode('utf-8')
        eval_tree,eval_functions=_selected(source['eval.py'],EVAL_FUNCTIONS)
        _,util_functions=_selected(source['utils.py'],UTIL_FUNCTIONS)
        preprocessor=_preprocessing(eval_tree)
        self._ast_proofs={node.name:hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()
                          for node in [*eval_functions,*util_functions,preprocessor]}
        # No NumPy/Torch/Transformers/NLTK/Mauve imports occur at construction.
        allowed=('len','int','str','list','dict','set','sum','min','max','any','enumerate','range','zip')
        safe_builtins={name:getattr(builtins,name) for name in allowed}
        safe_builtins['print']=self._print
        safe_builtins['__import__']=self._blocked_import
        self._globals=dict(__builtins__=safe_builtins,re=re,string=string,collections=collections,
            copy=copy,logger=_Quiet(),tqdm=lambda values:values,QA_MODEL=QA_MODEL,AUTOAIS_MODEL=NLI_MODEL,
            autoais_model=object(),autoais_tokenizer=object(),_run_nli_autoais=self._run_nli)
        self._globals.update({key:binding.value for key,binding in self._bindings.items()})
        if 'sent_tokenize' in self._bindings:
            self._globals['sent_tokenize']=self._sent_tokenize
        module=ast.fix_missing_locations(ast.Module(body=[*util_functions,*eval_functions,preprocessor],type_ignores=[]))
        exec(compile(module,'<pinned-ALCE-selected-functions>','exec'),self._globals)
        self._revalidate()

    @staticmethod
    def _blocked_import(name,*args,**kwargs):
        raise UnsupportedMetric('Native optional import is not admitted: '+name)

    def _print(self,*args,**kwargs):
        # The native multicitation summary is preserved without printing data.
        self._events.append(' '.join(str(v) for v in args))

    def _tick(self):
        if self._deadline is not None and time.monotonic()>=self._deadline:
            raise TimeoutError('Native metric deadline expired')

    def _revalidate(self):
        end=self._deadline if self._deadline is not None else time.monotonic()+60
        for name,p in self._sources.items():
            need(p['sha256']==SOURCE_SHA256[name],'Native source identity')
            _read(p,1024**2,end)
        for binding in [*self._bindings.values(),*([self._nli] if self._nli is not None else [])]:
            for p in binding.provenance['files']:
                _read(p,256*1024**2,end)

    def provenance(self):
        return freeze(dict(upstream_revision=COMMIT,sources=self._sources,function_ast_sha256=self._ast_proofs,
            runtime_bindings={k:v.provenance for k,v in self._bindings.items()},
            nli_binding=None if self._nli is None else self._nli.provenance,
            dependency_qualification='External caller responsibility; file proofs alone do not qualify runtime behavior.',
            nli_adapter='Native request text and integer verdict interface; inference is supplied by the explicit callback.',
            full_upstream_module_executed=False,implicit_model_loads=False))

    @property
    def calls(self):return freeze(self._calls)

    def _sent_tokenize(self,text):
        values=self._bindings['sent_tokenize'].value(text)
        self._sentence_counts.append(len(values))
        return values

    def _run_nli(self,passage,claim):
        self._tick()
        if self._nli is None:
            raise UnsupportedMetric('Explicit qualified NLI callback required')
        need(isinstance(passage,str) and isinstance(claim,str),'Native NLI text types')
        request=dict(ordinal=len(self._calls),logical_model=NLI_MODEL,premise=passage,hypothesis=claim,
            input_text='premise: {} hypothesis: {}'.format(passage,claim),max_new_tokens=10,
            entailment_rule="decoded text is exactly '1'",binding=self._nli.provenance)
        request['call_id']=hashlib.sha256(canonical(request)).hexdigest()
        record=dict(request=request,status='entered',entailment=None,error_type=None)
        self._calls.append(record)
        try:
            verdict=self._nli.value(freeze(request))
            need(type(verdict) is int and verdict in (0,1),'NLI callback must return native integer0/1')
            self._tick()
            record.update(status='completed',entailment=verdict)
            return verdict
        except BaseException as error:
            record.update(status='failed',error_type=type(error).__name__)
            raise

    def preprocess(self, rows):
        """Exact native first-line preprocessing and a separate citation-free copy."""
        need(isinstance(rows,(list,tuple)) and all(isinstance(row,Mapping) and
             isinstance(row.get('output'),str) for row in rows),'Explicit captured output rows required')
        self._revalidate()
        values=copy.deepcopy(encode(rows))
        citation,normalized=self._globals['_preprocess'](values)
        self._revalidate()
        return freeze(dict(citation=citation,normalized=normalized))

    def exact(self,gold,prediction):
        need(isinstance(gold,str) and isinstance(prediction,str),'Exact metric string inputs')
        self._revalidate()
        return freeze(dict(exact=self._globals['compute_exact'](gold,prediction),
                           f1=self._globals['compute_f1'](gold,prediction)))

    def _diagnostics(self, rows, metric, qampari, sentence_begin):
        result=dict(scheduled_count=len(rows),empty_output_count=sum(not r['output'].strip() for r in rows),
            qa_missing_or_empty_count=sum(not isinstance(r.get('qa_pairs'),list) or not r['qa_pairs'] for r in rows),
            strict_citation_token_count=0,strict_invalid_citation_token_count=0,
            duplicate_citation_occurrences=0,native_empty_sentence_rows=None)
        for row in rows:
            tokens=[int(x) for x in re.findall(r'\[(\d+)\]',row['output'])]
            result['strict_citation_token_count']+=len(tokens)
            result['strict_invalid_citation_token_count']+=sum(x<1 or x>len(row.get('docs',[])) for x in tokens)
            result['duplicate_citation_occurrences']+=len(tokens)-len(set(tokens))
        if metric=='citations':
            if qampari:
                counts=[len([r['question']+' '+s.strip() for s in r['output'].rstrip().rstrip('.').rstrip(',').split(',')]) for r in rows]
            else:
                # Observe native calls; do not invoke the tokenizer again for diagnostics.
                counts=self._sentence_counts[sentence_begin:]
                need(len(counts)==len(rows),'Native sentence observations must cover all rows')
            result['native_empty_sentence_rows']=sum(n==0 for n in counts)
        result['scope']='Supplemental all-scheduled/missingness/citation-syntax counts; not replacements for native denominators or evidence truth.'
        return result

    def metric(self,name,rows,*,qampari=False,at_most_citations=3,cot=False,deadline=None):
        """Preprocess captured outputs as native main does, then run one metric.

        Citation scoring receives the first-line text with citations intact;
        other metrics receive the native citation-removed copy. Deadlines are
        cooperative. A model-bearing caller still needs process supervision.
        """
        if name=='mauve':
            raise UnsupportedMetric('Native MAUVE hardcoded model/import requires a separately qualified offline feature backend')
        need(name in METRICS and not self._active,'Known non-reentrant native metric required')
        need(isinstance(rows,(list,tuple)) and rows and all(isinstance(r,Mapping) and
             isinstance(r.get('output'),str) for r in rows),'Nonempty complete captured-output rows required')
        need(type(qampari) is bool and type(cot) is bool and type(at_most_citations) is int and
             at_most_citations>0,'Native metric options')
        need(deadline is None or type(deadline) in (int,float) and math.isfinite(deadline), 'Finite metric deadline required')
        for key in DEPENDENCIES[name]:
            if key not in self._bindings:
                raise UnsupportedMetric('Explicit native dependency required: '+key)
        if name in ('citations','claims') and self._nli is None:
            raise UnsupportedMetric('Explicit native NLI callback required')
        if name=='qa':
            config=self._bindings['pipeline'].provenance['configuration']
            need(config.get('logical_model')==QA_MODEL and config.get('network_access') is False and
                 isinstance(config.get('local_checkpoint'),str) and Path(config['local_checkpoint']).is_absolute(),
                 'Offline native QA checkpoint binding required')
        self._deadline,self._active=deadline,True
        begin,events,sentence_begin=len(self._calls),len(self._events),len(self._sentence_counts)
        try:
            self._tick();self._revalidate()
            citation,normalized=self._globals['_preprocess'](copy.deepcopy(encode(rows)))
            data=citation if name=='citations' else normalized
            kwargs=(dict(qampari=qampari,at_most_citations=at_most_citations) if name=='citations'
                    else dict(cot=cot) if name=='qampari' else {})
            value=self._globals[METRICS[name]](data,**kwargs)
            self._tick();self._revalidate()
            flags=[];native_value=_native_json(value,nonfinite=flags)
            diagnostics=self._diagnostics(citation,name,qampari,sentence_begin)
            self._tick();self._revalidate()
            return freeze(dict(metric=name,native_value=native_value,native_nonfinite=flags,
                diagnostics=diagnostics,nli_calls=self._calls[begin:],native_messages=self._events[events:],
                provenance=self.provenance(),scientific_truth_verified=False,automatic_retries=0))
        finally:
            self._active=False
            self._deadline=None
