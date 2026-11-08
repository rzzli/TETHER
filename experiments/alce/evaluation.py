"""Evaluator-only ALCE joins and full-family native metric orchestration.

Assembly attests the checked projection/capture join, not runtime qualification
or outer process ownership. No model is loaded, dispatched or acquired here.
References stay in evaluator rows. Failed/unexecuted slots have no invented
answer and prevent metric execution. Native errors/denominators are unchanged.
Deadlines are cooperative, including the existing preparation verifier's own
declared bound; an executing evaluator requires an outer hard process deadline.
"""
from collections import Counter
from collections.abc import Mapping
import hashlib
import math
from pathlib import Path
import time
import weakref

from tether_engine.serde import canonical, encode, fingerprint, freeze, parse_json
from . import data_views as views, native_metrics, producer, prompts
from .data_views import _path, _hash, _read, _tick, need

FAMILIES=views.FAMILIES
RECIPES=freeze(dict(asqa=('length','str_em','rouge','qa','mauve','citations'),
    qampari=('length','str_em','qampari','citations'),
    eli5=('length','str_em','rouge','mauve','citations','claims')))
GROUPS=freeze(dict(lexical=('length','str_em','qampari','rouge'),qa=('qa',),mauve=('mauve',),
                   true=('citations','claims')))
MAX_PLAN=16*1024**2
MAX_MEMBER=256*1024**2
MAX_CLOSURE=4*1024**3
_ISSUED=weakref.WeakKeyDictionary()


class Assembly:
    """Operation-local issued join; exposed rows are evaluator-only and immutable."""
    __slots__=('_rows','_report','__weakref__')
    def __init__(self):raise TypeError('Use assemble with an externally anchored plan')
    @property
    def report(self):return self._report
    def rows(self,family):
        _state(self);need(family in FAMILIES,'Known family required');return self._rows[family]


def _seal(value):return fingerprint(dict(rows=value._rows,report=value._report))


def _state(value):
    need(type(value)is Assembly and value in _ISSUED,'Issued evaluator assembly required')
    state=_ISSUED[value];need(state['seal']==_seal(value),'Evaluator assembly changed')
    return state


def source_pins(deadline):
    return {p.name:_hash(p,deadline) for p in [Path(__file__).resolve(),
        *[Path(m.__file__).resolve() for m in (views,producer,prompts,native_metrics)]]}


class _Inputs:
    def __init__(self,end):self.end=end;self.proofs={};self.roots={};self.absent_paths=set();self.total=0
    def bind(self,p,maximum=MAX_MEMBER):
        raw=_read(p,maximum,self.end);path=str(_path(p['path']))
        if path in self.proofs:need(self.proofs[path]==dict(p),'Conflicting file proof')
        else:
            self.total+=p['bytes'];need(self.total<=MAX_CLOSURE,'Evaluator input byte ceiling')
            self.proofs[path]=dict(p)
        return raw
    def json(self,p,maximum=MAX_MEMBER):return parse_json(self.bind(p,maximum))
    def large(self,p):
        views._proof(p);path=str(_path(p['path']))
        if path in self.proofs:
            need(self.proofs[path]==dict(p),'Conflicting large source proof');return
        need(_hash(path,self.end)==dict(p),'Large source byte proof differs')
        self.total+=p['bytes'];need(self.total<=MAX_CLOSURE,'Evaluator input byte ceiling');self.proofs[path]=dict(p)
    def collect(self,value):
        if isinstance(value,Mapping):
            if set(value)=={'path','bytes','sha256'}:self.large(value)
            else:
                for child in value.values():self.collect(child)
        elif isinstance(value,(list,tuple)):
            for child in value:self.collect(child)
    def membership(self,root):
        root=_path(root);names=[]
        for p in root.rglob('*'):
            _tick(self.end);_path(p);need(p.is_file() or p.is_dir(),'Regular closed evidence tree')
            names.append(p.relative_to(root).as_posix()+('/' if p.is_dir() else ''))
        need(len(names)<=100000,'Bounded evidence tree');names=sorted(names)
        if str(root) in self.roots:need(self.roots[str(root)]==names,'Evidence membership changed')
        else:self.roots[str(root)]=names
    def absent(self,paths):
        for path in paths:
            _tick(self.end);path=_path(path)
            need(not path.exists(),'Late acquisition terminal contradiction')
            self.absent_paths.add(str(path))
    def unchanged(self):
        for p in self.proofs.values():need(_hash(p['path'],self.end)==p,'Late evaluator input mutation')
        for root in tuple(self.roots):self.membership(root)
        self.absent(tuple(self.absent_paths))


def _plan(value):
    fields={'schema_version','kind','preparation','expected_counts','generation','owners','attempts','native_sources'}
    need(isinstance(value,dict) and set(value)==fields and type(value['schema_version'])is int
         and value['schema_version']==1 and value['kind']=='alce_evaluation_join_plan_v1','Exact evaluator join plan')
    need(set(value['preparation'])=={'root','receipt_sha256'} and set(value['expected_counts'])==set(FAMILIES)
         and all(type(n)is int and 0<n<=10000 for n in value['expected_counts'].values()),'Full explicit family counts')
    generation=value['generation']
    need(set(generation)=={'configurations','input_byte_limit','model_provenance','limits'}
         and set(generation['configurations'])==set(FAMILIES),'Complete generation controls')
    for family in FAMILIES:prompts._configuration(generation['configurations'][family],family)
    producer.Limits(**generation['limits'])
    need(type(generation['input_byte_limit'])is int and 0<generation['input_byte_limit']<=producer.MAX_PAYLOAD_BYTES,
         'Bounded original prompt bytes')
    need(isinstance(value['owners'],dict) and all(type(k)is str and k and isinstance(v,dict)
         and set(v)=={'owner_pid','alias','server_spec','bindings'} for k,v in value['owners'].items()),'External owner declarations')
    need(isinstance(value['attempts'],list) and len(value['attempts'])==sum(value['expected_counts'].values()),
         'Every scheduled attempt needs an explicit disposition')
    need(set(value['native_sources'])==set(native_metrics.SOURCE_SHA256),'Exact native source set')
    return value


def assemble(plan_proof,*,deadline):
    """Read-only full join. References are opened only in this evaluator role.

    Each completed response is independently replayed from its original native
    capture. Failure declarations are retained as declarations, not promoted to
    verified usage or scientific observations. Outer process validity and model
    qualification must be established separately by the caller.
    """
    need(type(deadline) in (int,float) and math.isfinite(deadline),'Finite absolute join deadline')
    inputs=_Inputs(deadline);plan=_plan(inputs.json(plan_proof,MAX_PLAN));inputs.collect(source_pins(deadline))
    for name,p in plan['native_sources'].items():
        need(p['sha256']==native_metrics.SOURCE_SHA256[name],'Pinned native metric source differs');inputs.bind(p,1024**2)
    root=_path(plan['preparation']['root']);rp=_hash(root/'RECEIPT.json',deadline)
    need(rp['sha256']==plan['preparation']['receipt_sha256'],'Preparation external receipt differs')
    receipt=inputs.json(rp,MAX_PLAN);inputs.membership(root)
    need(receipt['kind']=='alce_data_preparation_receipt_v1' and receipt['status']=='prepared','Completed preparation required')
    files=receipt['files']
    for name,p in files.items():need(_path(p['path'])==root/name,'Preparation file location differs')
    schedule=inputs.json(files['SCHEDULE.json'],MAX_PLAN)
    need(set(schedule)==set(FAMILIES) and {f:len(schedule[f]) for f in FAMILIES}==plan['expected_counts'],
         'Full original family denominators differ')
    projections={f:views.load_generation(files[f'generation/{f}.json']) for f in FAMILIES}
    for f in FAMILIES:inputs.bind(files[f'generation/{f}.json'])
    need(all(len(projections[f])==len(schedule[f]) for f in FAMILIES),'Projection/schedule count differs')
    expected=[(f,i,s,projections[f][i]) for f in FAMILIES for i,s in enumerate(schedule[f])]
    outputs={f:[] for f in FAMILIES};products=[];physical=set();attempt_roots=set();usage=dict(input_tokens=0,output_tokens=0,cost_usd=0.0)
    generation=plan['generation']
    for entry,(family,ordinal,s,case) in zip(plan['attempts'],expected):
        _tick(deadline)
        base={'family','ordinal','id','owner','execution_id','disposition','descriptor','evidence'}
        need(set(entry) in (base,base|{'output'}) and entry.get('output') is None,'No copied answer or unknown attempt fields')
        need(type(entry['ordinal'])is int and entry['ordinal']==ordinal and entry['family']==family
             and entry['id']==s['id']==case['id'] and type(s['row_ordinal'])is int and s['row_ordinal']==ordinal,
             'Exact original family/ordinal/identity order differs')
        request=prompts.build_request(case,family=family,input_byte_limit=generation['input_byte_limit'],
                                      configuration=generation['configurations'][family])
        call,payload=producer.make_call(request,generation['model_provenance'],limits=producer.Limits(**generation['limits']))
        disposition=entry['disposition'];need(disposition in ('completed','failed','unexecuted'),'Explicit attempt disposition')
        if disposition=='completed':
            need(entry['owner'] in plan['owners'] and entry['evidence'] is None
                 and isinstance(entry['descriptor'],dict) and set(entry['descriptor'])=={'root','receipt_sha256'}
                 and type(entry['execution_id'])is str and entry['execution_id'] and entry['execution_id'] not in physical,
                 'Unique completed physical execution descriptor')
            owner=plan['owners'][entry['owner']];descriptor=entry['descriptor'];aroot=_path(descriptor['root'])
            need(str(aroot) not in attempt_roots,'Repeated attempt directory');attempt_roots.add(str(aroot));physical.add(entry['execution_id'])
            verified=producer.verify_attempt(aroot,descriptor['receipt_sha256'],call=call,payload=payload,
                owner_pid=owner['owner_pid'],alias=owner['alias'],server_spec=owner['server_spec'],bindings=owner['bindings'],deadline=deadline)
            result=verified['result'];need(result['execution_id']==entry['execution_id'],'Physical execution identity differs')
            raw=result['verified']['decoded']['raw_text'];outputs[family].append(raw)
            for key in usage:usage[key]+=result['reported_usage'][key]
            ap=_hash(aroot/'RECEIPT.json',deadline);need(ap['sha256']==descriptor['receipt_sha256'],'Late attempt anchor drift')
            captured=inputs.json(ap,4*1024**2);inputs.collect(captured['files']);inputs.membership(aroot)
            invocation=inputs.json(captured['files']['INPUT.json'],4*1024**2);inputs.collect(invocation['sources'])
            products.append(dict(family=family,ordinal=ordinal,id=case['id'],disposition=disposition,
                execution_id=entry['execution_id'],descriptor=descriptor,raw_output_sha256=hashlib.sha256(raw.encode()).hexdigest(),
                usage=encode(result['reported_usage']),reservation=encode(result['conservative_reservation']),
                finish_reason=result['verified']['finish_reason'],source_ids=request['source_ids']))
        else:
            need(entry['descriptor'] is None and isinstance(entry['evidence'],dict),'Explicit non-success evidence proof')
            evidence=inputs.json(entry['evidence'],4*1024**2);outputs[family].append(None)
            products.append(dict(family=family,ordinal=ordinal,id=case['id'],disposition=disposition,
                execution_id=entry['execution_id'],evidence=entry['evidence'],declared_evidence=evidence,
                usage=None,reservation=None,raw_output_sha256=None,disposition_is_external_declaration=True))
    # This source-inclusive reader opens evaluator references; no actor gets it.
    _tick(deadline);verified=views.verify_preparation(root,plan['preparation']['receipt_sha256']);_tick(deadline)
    need(dict(verified['counts'])==plan['expected_counts'],'Reconstructed family counts differ')
    request=inputs.json(files['REQUEST.json'],MAX_PLAN);inputs.collect(request)
    acquisition_root=_path(request['acquisition_receipt']['path']).parent
    inputs.absent(acquisition_root/name for name in ('FAILURE.json','DEADLINE.json','FINALIZATION-FAILED.json',
        'FAILED.json','SUPERVISOR-FAILED.json','STALLED.json'))
    evaluator=inputs.json(files['EVALUATION.json'],MAX_PLAN);inputs.collect(evaluator)
    joined={}
    for family in FAMILIES:
        originals=inputs.json(files[f'evaluation/{family}.json']);need(len(originals)==len(schedule[family]),'Original full-family count differs')
        joined[family]=[]
        for ordinal,(original,case,s,raw) in enumerate(zip(originals,projections[family],schedule[family],outputs[family])):
            need(original['question']==case['question'] and s['question_sha256']==hashlib.sha256(original['question'].encode()).hexdigest()
                 and s['original_document_count']==len(original['docs']) and s['selected_document_count']==len(case['docs']),
                 'Original question/document identity differs')
            offered=[dict(title=d['title'],text=d['text']) for d in case['docs']]
            need(offered==[dict(title=d['title'],text=d['text']) for d in original['docs'][:5]],'Offered source projection differs')
            # Preserve references/unknown original metadata only in this evaluator.
            row=dict(original,docs=offered,output=raw);joined[family].append(row)
    for p in files.values():inputs.bind(p)
    inputs.unchanged()
    counts={f:dict(Counter(p['disposition'] for p in products if p['family']==f)) for f in FAMILIES}
    report=dict(kind='alce_source_capture_join_v1',plan=plan_proof,preparation=plan['preparation'],
        scheduled_counts=plan['expected_counts'],dispositions=counts,products=products,
        completed_count=len(physical),all_scheduled_completed=len(physical)==len(products),
        qualified_capture_usage=usage,unqualified_usage_not_included=True,offered_document_limit=5,
        raw_references_role='evaluator_only',native_sources=plan['native_sources'],
        runtime_qualification_external=True,outer_process_qualification_external=True,scientific_correctness_evaluated=False)
    value=object.__new__(Assembly);value._rows=freeze(joined);value._report=freeze(report)
    _ISSUED[value]=dict(seal=_seal(value),inputs=inputs,used=set(),outcomes={})
    return value


def revalidate(value,*,deadline):
    need(type(deadline) in (int,float) and math.isfinite(deadline),'Finite absolute revalidation deadline')
    state=_state(value);state['inputs'].end=deadline;_tick(deadline);state['inputs'].unchanged();return value


def metric_plan(value):
    _state(value)
    return freeze(dict(full_family_required=True,recipes=RECIPES,counts=value.report['scheduled_counts'],
        eligible=value.report['all_scheduled_completed'],qampari_cot=False,at_most_citations=3,
        worker_groups={f:{g:[n for n in RECIPES[f] if n in names] for g,names in GROUPS.items()} for f in FAMILIES},
        branching_nli_workload='Native joint/single/leave-one-out calls depend on preceding verdicts; use one resident bounded callback.',
        runtime_qualification_external=True))


class ResidentNLI:
    """Cap physical calls to an already qualified resident callback; no loading.

    One reserved failure exhausts this operation-local route. A counter is not
    process supervision, runtime qualification, or a durable recovery authority.
    """
    def __init__(self,callback,*,maximum,deadline):
        need(callable(callback) and type(maximum)is int and maximum>0
             and type(deadline) in (int,float) and math.isfinite(deadline),'Explicit resident callback/bounds')
        self.callback,self.maximum,self.deadline=callback,maximum,deadline;self.records=[];self.failed=False
    def __call__(self,request):
        need(not self.failed,'Failed resident operation cannot repeat')
        try:
            _tick(self.deadline);need(len(self.records)<self.maximum,'Resident NLI call ceiling')
        except BaseException:
            self.failed=True;raise
        record=dict(request_sha256=fingerprint(request),status='entered',result=None);self.records.append(record)
        try:
            verdict=self.callback(request);need(type(verdict)is int and verdict in (0,1),'Native integer verdict required')
            _tick(self.deadline);record.update(status='completed',result=verdict);return verdict
        except BaseException:
            self.failed=True;record['status']='failed';raise


def _evaluate(value,family,names,label,bridge,mauve,deadline):
    state=_state(value);need(family in FAMILIES and value.report['all_scheduled_completed'],
        'All scheduled outputs must be admitted before native metrics')
    need(names and len(set(names))==len(names) and all(name in RECIPES[family] for name in names),'Declared native metric subset')
    need(isinstance(bridge,native_metrics.NativeBridge) and canonical(bridge.provenance()['sources'])==canonical(value.report['native_sources']),
         'Exact native bridge source identity')
    need(all((family,name) not in state['used'] for name in names),'Metric operation already reserved; no automatic retry')
    if 'mauve' in names:need(callable(mauve),'Explicit full-family native MAUVE callback required')
    revalidate(value,deadline=deadline);rows=value.rows(family)
    aggregate=state['outcomes'].setdefault(family,dict(family=family,status='partial',scheduled_count=len(rows),
        metrics={},failures={},automatic_retries=0))
    result=dict(family=family,operation=label,status='started',scheduled_count=len(rows),metrics={},automatic_retries=0)
    try:
        for name in names:
            _tick(deadline);state['used'].add((family,name))
            if name=='mauve':
                normalized=bridge.preprocess(rows)['normalized']
                result['metrics'][name]=mauve(normalized,value.report['native_sources'])
            else:result['metrics'][name]=bridge.metric(name,rows,qampari=family=='qampari',cot=False,
                                                       at_most_citations=3,deadline=deadline)
            aggregate['metrics'][name]=result['metrics'][name]
        revalidate(value,deadline=deadline);result['status']='completed'
        if not aggregate['failures']:
            aggregate['status']='completed' if set(aggregate['metrics'])==set(RECIPES[family]) else 'partial'
        return freeze(result)
    except BaseException as error:
        failure=dict(error_type=type(error).__name__,nli_calls=bridge.calls,
                     operation=label,completed_metrics=list(result['metrics']))
        aggregate.update(status='failed',error_type=type(error).__name__)
        aggregate['failures'][label]=failure
        raise


def evaluate_metric(value,family,name,bridge,*,mauve=None,deadline):
    """One metric over the full family; no sibling metric/runtime required."""
    return _evaluate(value,family,(name,),'metric:'+name,bridge,mauve,deadline)


def evaluate_group(value,family,group,bridge,*,mauve=None,deadline):
    """Full-family work for one separately supervised resident worker kind.

    Lexical, QA, MAUVE and TRUE have independent process lifetimes. The caller
    supplies only this group's qualified runtime. No previous metric is rerun.
    Issuance/reservations are in-process; durable jobs and process replay belong
    to the external evaluator controller, not this helper.
    """
    need(family in FAMILIES and group in GROUPS,'Known family/worker group')
    names=tuple(n for n in RECIPES[family] if n in GROUPS[group])
    return _evaluate(value,family,names,'group:'+group,bridge,mauve,deadline)


def evaluate_family(value,family,bridge,*,mauve=None,deadline):
    """In-process convenience only; not the sequential production worker plan.

    Native exceptions propagate; raw text is preprocessed once per metric and
    MAUVE receives one normalized full-family copy. Use evaluate_group for
    production worker lifetimes with separate model residency.
    """
    need(family in FAMILIES,'Known family')
    return _evaluate(value,family,RECIPES[family],'family',bridge,mauve,deadline)


def outcomes(value):
    """Partial/complete metric records; no receipt or success inferred on failure."""
    return freeze(_state(value)['outcomes'])
