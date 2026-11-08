"""One offline full-family metric group in a separately owned process.

Lexical, QA, MAUVE and TRUE are separate jobs, never concurrent model loads in
this worker. Qualified runtime/assets and a prospective lexical seed are caller
inputs. No acquisition, generation, automatic retry or singleton-QA repair.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import math
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
for directory in (ROOT/'packages/tether/src',ROOT/'src',ROOT):
    if str(directory) not in sys.path:sys.path.insert(0,str(directory))

from tether_engine.serde import canonical,encode,fingerprint,parse_json
from experiments.alce import evaluation as join,native_metrics as metrics,native_runtime as runtime,native_worker as base
from experiments.alce.data_views import _path,_hash,_read,_tick,need

MAX_JOB=16*1024**2
PUNKT={'abbrev_types.txt','collocations.tab','ortho_context.tab','sent_starters.txt'}
VERSIONS={'np':'2.3.5','nltk':'3.9.2','rouge_scorer':'0.1.2','scoring':'0.1.2'}


def source_pins():
    from experiments.alce import generation
    end=time.monotonic()+60
    values=dict(base.source_pins())
    for module in (join,metrics,generation,sys.modules[__name__]):
        path=Path(module.__file__).resolve();values[path.relative_to(ROOT).as_posix()]=_hash(path,end)
    return values


def _fresh(output,protected,*,fresh=True):
    output=_path(output)
    need(output.parent.is_dir() and (not fresh or not output.exists()),'Fresh evaluator output with existing parent required')
    for p in protected:
        p=_path(p);need(output!=p and output not in p.parents and p not in output.parents,'Evaluator output overlaps protected evidence')
    return output


def load_job(proof,*,fresh=True):
    end=time.monotonic()+60;job=parse_json(_read(proof,MAX_JOB,end))
    need(set(job)=={'schema_version','kind','family','group','join_plan','generation','output','interpreter',
         'offline','limits','placement','acquisition_receipt','runtime_sources','lexical_sources','punkt','rng_seed','code_pins'},
         'Exact metric worker job schema')
    need(type(job['schema_version'])is int and job['schema_version']==1 and job['kind']=='alce_evaluation_worker_job_v1'
         and job['family'] in join.FAMILIES and job['group'] in join.GROUPS,'Metric job identity')
    selected=tuple(n for n in join.RECIPES[job['family']] if n in join.GROUPS[job['group']])
    need(selected,'Family has no metric in requested group')
    need(job['code_pins']==source_pins(),'Executing evaluator source closure differs')
    limits=job['limits'];keys={'seconds','process_bytes','minimum_available_host_bytes','gpu_bytes','offload_bytes',
        'max_calls','input_bytes','output_bytes','cpu_threads'}
    need(type(limits)is dict and set(limits)==keys and all(type(x)is int for x in limits.values()),'Exact integral evaluator limits')
    need(all(limits[k]>0 for k in keys-{'gpu_bytes'}) and (limits['gpu_bytes']==0 if job['group']=='lexical' else limits['gpu_bytes']>0),
         'Positive evaluator limits and explicit GPU scope')
    need(limits['seconds']<=86400 and limits['max_calls']<=1_000_000 and limits['input_bytes']<=256*1024**2
         and limits['output_bytes']<=1024**3 and limits['cpu_threads']<=64,'Evaluator hard configuration ceilings')
    need(set(job['offline'])=={'record','connection'} and type(job['runtime_sources'])is dict and type(job['lexical_sources'])is dict,
         'Explicit runtime source controls')
    required=set().union(*(set(metrics.DEPENDENCIES.get(n,()))-{'pipeline'} for n in selected))
    if job['group']=='lexical':required.add('np')  # The explicit RNG is owned even when a recipe has no ROUGE.
    need(set(job['lexical_sources'])==required,'Only required lexical dependencies may be bound')
    need((type(job['rng_seed'])is int and 0<=job['rng_seed']<2**32) if job['group']=='lexical' else job['rng_seed'] is None,
         'Prospective lexical seed required; other native seeds remain unchanged')
    need((not job['runtime_sources'] and job['acquisition_receipt'] is None and job['placement']=={}) if job['group']=='lexical'
         else bool(job['runtime_sources']) and isinstance(job['acquisition_receipt'],dict),'Exact model residency scope')
    need(isinstance(job['punkt'],dict) and set(job['punkt'])==(PUNKT if 'sent_tokenize' in required else set()),'Pinned English Punkt tables required')
    sources=[job['interpreter'],*job['offline'].values(),*job['runtime_sources'].values(),*job['lexical_sources'].values(),*job['punkt'].values()]
    for p in sources:_read(p,256*1024**2,end)
    plan=join._plan(parse_json(_read(job['join_plan'],limits['input_bytes'],end)))
    need(set(job['generation'])=={'root','receipt_sha256'},'External completed generation descriptor required')
    protected=[proof['path'],job['join_plan']['path'],job['generation']['root'],plan['preparation']['root'],
        *(p['path'] for p in sources),*(p['path'] for p in plan['native_sources'].values()),
        *(p['path'] for p in job['code_pins'].values())]
    if job['acquisition_receipt'] is not None:protected.append(_path(job['acquisition_receipt']['path']).parent)
    protected.extend(e['descriptor']['root'] for e in plan['attempts'] if e['descriptor'] is not None)
    output=_fresh(job['output'],protected,fresh=fresh)
    return job,plan,selected,output,protected


def verify_generation(descriptor):
    from experiments.alce.generation import verify_generation as verify
    return verify(descriptor)


def _admit(job,plan,end):
    generation=verify_generation(job['generation']);_tick(end)
    need(generation['root']==job['generation']['root'] and generation['receipt_sha256']==job['generation']['receipt_sha256']
         and generation['source_projection_verified'] is True and generation['wire_usage_verified'] is True,'Independent generation admission required')
    for key in ('preparation','expected_counts','generation','owners','attempts'):
        need(canonical(generation['report'][key])==canonical(plan[key]),'Join differs from completed generation: '+key)
    value=join.assemble(job['join_plan'],deadline=end)
    need(value.report['all_scheduled_completed'],'Incomplete generation never receives full-family metrics')
    return value


def _preserved_generation(descriptor,end):
    """Byte/inventory preservation after source-inclusive generation admission."""
    root=_path(descriptor['root']);rp=_hash(root/'RECEIPT.json',end)
    need(rp['sha256']==descriptor['receipt_sha256'],'Generation receipt changed after admission')
    receipt=parse_json(_read(rp,MAX_JOB,end));files=receipt['files']
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    need(actual==set(files)|{'RECEIPT.json'},'Generation membership changed after admission')
    for name,p in files.items():
        need(_path(p['path'])==root/name and _hash(root/name,end)==p,'Generation bytes changed after admission')
    return rp


def lexical_dependencies(names):
    modules={}
    for name in names:
        target={'np':'numpy','sent_tokenize':'nltk','rouge_scorer':'rouge_score.rouge_scorer','scoring':'rouge_score.scoring'}[name]
        module=importlib.import_module(target);distribution={'np':'numpy','sent_tokenize':'nltk'}.get(name,'rouge-score')
        need(importlib.metadata.version(distribution)==VERSIONS['nltk' if name=='sent_tokenize' else name],
             'Qualified lexical runtime version differs')
        modules[name]=module
    return modules


def _rng(np):
    state=np.random.get_state()
    return dict(algorithm=state[0],keys=state[1].tolist(),position=int(state[2]),has_gauss=int(state[3]),cached_gaussian=float(state[4]))


def _bindings(job,modules,output,budget,end):
    actual={name:_hash(Path(module.__file__).resolve(),end) for name,module in modules.items()}
    need(actual==job['lexical_sources'],'Actually imported lexical source differs')
    bindings={}
    for name,module in modules.items():
        files=[actual[name]];config=dict(network_access=False)
        if name=='sent_tokenize':
            directory=output/'nltk_data/tokenizers/punkt_tab/english';directory.mkdir(parents=True)
            for filename,p in sorted(job['punkt'].items()):
                raw=_read(p,16*1024**2,end);budget.reserve(len(raw))
                with (directory/filename).open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
                budget.used+=len(raw);files.append(p)
            module.data.path[:]=[str(output/'nltk_data')];value=module.sent_tokenize
            config.update(language='english',pinned_tables=True,no_download=True)
        else:value=module
        bindings[name]=metrics.Binding(value,dict(name=name,version=VERSIONS['nltk' if name=='sent_tokenize' else name],
            configuration=config,files=files))
    return bindings


def execute(job_proof,*,module_loader=runtime.dependencies,lexical_loader=lexical_dependencies,
            asset_loader=runtime.ModelAssets,resource_sampler=None):
    start=time.monotonic();job,plan,selected,output,_=load_job(job_proof);end=start+job['limits']['seconds']
    need(_path(Path(sys.executable).resolve(strict=True))==_path(job['interpreter']['path']),'Qualified evaluator interpreter required')
    output.mkdir();budget=base.OutputBudget(job['limits']['output_bytes']);journal=base.NativeJournal(output/'journal.jsonl',budget)
    value=adapter=guard=watch=bridge=None;results=[];call_files=[];rng=None;stage='admission'
    def emit(event,details):journal.append(event,**encode(details))
    def call(request,function):
        need(len(call_files)<job['limits']['max_calls'],'Metric physical call ceiling');_tick(end)
        result=function()
        record=dict(ordinal=len(call_files),request_sha256=fingerprint(request),result=encode(result))
        path=output/'calls'/f'{len(call_files):06}.json';budget.write(path,record);p=_hash(path,end);call_files.append(p)
        emit('native_call_persisted',dict(ordinal=record['ordinal'],proof=p));return result
    try:
        budget.write(output/'REQUEST.json',dict(job=job_proof,code_pins=job['code_pins'],automatic_retries=0))
        emit('evaluation_reserved',dict(family=job['family'],group=job['group'],metrics=selected))
        with base.DeadlineWatchdog(end,output/'DEADLINE.json'),base.ResourceWatchdog(output,job['limits'],sample=resource_sampler) as watch:
            guard=base.OfflineNetworkGuard(job['offline']['record'],job['offline']['connection']).install()
            for name in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_DATASETS_OFFLINE','HF_HUB_DISABLE_TELEMETRY'):os.environ[name]='1'
            for name in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):os.environ[name]=str(job['limits']['cpu_threads'])
            value=_admit(job,plan,end);generation_receipt=_preserved_generation(job['generation'],end)
            budget.write(output/'ADMISSION.json',dict(join=encode(value.report),generation=job['generation'],generation_receipt=generation_receipt))
            emit('source_capture_admitted',dict(counts=value.report['scheduled_counts'],family=job['family']))
            stage='runtime';(output/'results').mkdir();(output/'calls').mkdir()
            lexical=lexical_loader(tuple(job['lexical_sources']));bindings=_bindings(job,lexical,output,budget,end)
            if job['group']=='lexical':
                before=_rng(lexical['np']);lexical['np'].random.seed(job['rng_seed'])
                rng=dict(seed=job['rng_seed'],before=before,seeded=_rng(lexical['np']),after=None,
                    scope='Prospective worker-owned NumPy RNG; native ROUGE defaults unchanged.')
                emit('lexical_rng_seeded',dict(seed=job['rng_seed'],state_sha256=fingerprint(rng['seeded'])))
            else:
                modules=module_loader(include_mauve=job['group']=='mauve')
                need(runtime.loaded_modules(modules,end)==job['runtime_sources'],'Actually imported model runtime differs')
                torch=modules['torch'];need(torch.cuda.is_available(),'Qualified CUDA evaluator required')
                torch.set_num_threads(job['limits']['cpu_threads']);total=torch.cuda.get_device_properties(0).total_memory
                need(job['limits']['gpu_bytes']<=total,'GPU allocation ceiling exceeds hardware')
                torch.cuda.set_per_process_memory_fraction(job['limits']['gpu_bytes']/total,0)
                assets=asset_loader(job['acquisition_receipt'],dict(true='true_nli',qa='qa_roberta',mauve='gpt2_large')[job['group']],deadline=end)
                common=dict(deadline=end,emit=emit)
                if job['group']=='true':adapter=runtime.TrueRuntime(assets,modules,max_memory=job['placement'],offload_root=output/'offload',**common)
                elif job['group']=='qa':adapter=runtime.QARuntime(assets,modules,**common)
                else:adapter=runtime.MauveRuntime(assets,modules,**common)
            nli=None;mauve=None
            if job['group']=='true':
                resident=join.ResidentNLI(lambda request:call(request,lambda:adapter(request)),maximum=job['limits']['max_calls'],deadline=end)
                nli=metrics.Binding(resident,dict(name='resident-native-TRUE',version=runtime.VERSIONS['transformers'],
                    configuration=dict(logical_model=metrics.NLI_MODEL,network_access=False),files=[job['runtime_sources']['transformers']]))
            elif job['group']=='qa':
                def pipeline(*args,**kwargs):
                    answer=adapter.pipeline(*args,**kwargs)
                    def invoke(**request):return call(request,lambda:answer(**request))
                    return invoke
                bindings['pipeline']=metrics.Binding(pipeline,dict(name='native-QA',version=runtime.VERSIONS['transformers'],
                    configuration=dict(logical_model=metrics.QA_MODEL,network_access=False,local_checkpoint=str(assets.root)),
                    files=[job['runtime_sources']['transformers']]))
            elif job['group']=='mauve':mauve=lambda rows,sources:call(rows,lambda:adapter.metric(rows,sources))
            bridge=metrics.NativeBridge(plan['native_sources'],bindings=bindings,nli=nli);stage='metrics'
            for name in selected:
                emit('metric_entered',dict(name=name,scheduled_count=len(value.rows(job['family']))))
                result=join.evaluate_metric(value,job['family'],name,bridge,mauve=mauve,deadline=end)
                path=output/'results'/f'{len(results):02}-{name}.json';budget.write(path,encode(result))
                p=_hash(path,end);results.append(p);emit('metric_completed',dict(name=name,proof=p,result_sha256=fingerprint(result)))
            if rng is not None:rng['after']=_rng(lexical['np'])
            if adapter is not None:assets.revalidate(end,full=True)
            join.revalidate(value,deadline=end)
            _preserved_generation(job['generation'],end)
            need(job['code_pins']==source_pins(),'Evaluator code changed before completion')
            _read(job_proof,MAX_JOB,end);_read(job['join_plan'],job['limits']['input_bytes'],end)
            snapshot=guard.snapshot();need(snapshot['denied_network_attempts']==snapshot['dropped_event_records']==0,'Forbidden evaluator network attempt')
            emit('evaluation_completed',dict(metrics=selected,physical_calls=len(call_files)))
        complete=dict(status='completed',job=job_proof,family=job['family'],group=job['group'],metrics=selected,
            result_files=results,call_files=call_files,native=None if adapter is None else adapter.report(),
            bridge=bridge.provenance(),bridge_calls=bridge.calls,offline=snapshot,rng=rng,
            resource_samples=watch.values,wall_seconds=time.monotonic()-start,automatic_retries=0,
            scope='Full-family native metrics; model behavior qualification remains externally anchored.')
        budget.write(output/'COMPLETE.json',complete)
        files=_inventory(output,end);budget.write(output/'WORKER-RECEIPT.json',dict(kind='alce_metric_worker_receipt_v1',status='completed',files=files))
        _tick(end);return _hash(output/'WORKER-RECEIPT.json',end)
    except BaseException as error:
        try:base.write_new(output/'FAILURE.json',dict(status='failed',stage=stage,error_type=type(error).__name__,reason=str(error)[:2000],
            wall_seconds=time.monotonic()-start,automatic_retries=0,metric_outcomes=None if value is None else join.outcomes(value),
            native=None if adapter is None else adapter.report(),completed_call_files=call_files,
            offline=None if guard is None else guard.snapshot()))
        except BaseException as persistence:error.add_note('Evaluator failure retention failed: '+type(persistence).__name__)
        raise
    finally:
        if guard is not None:guard.close()


def _inventory(root,end):
    return {p.relative_to(root).as_posix():_hash(p,end) for p in sorted(root.rglob('*'))
        if p.is_file() and not p.is_relative_to(root/'offload') and p!=root/'WORKER-RECEIPT.json'}


def verify_worker(root,job_proof,job,selected,end):
    root=_path(root)
    need(not any((root/name).exists() for name in ('FAILURE.json','DEADLINE.json','RESOURCE-LIMIT.json')),'Metric worker failure dominates completion')
    rp=_hash(root/'WORKER-RECEIPT.json',end);receipt=parse_json(_read(rp,MAX_JOB,end))
    need(receipt['kind']=='alce_metric_worker_receipt_v1' and receipt['status']=='completed'
         and receipt['files']==_inventory(root,end),'Closed evaluator result inventory')
    files=receipt['files'];complete=parse_json(_read(files['COMPLETE.json'],job['limits']['output_bytes'],end))
    request=parse_json(_read(files['REQUEST.json'],MAX_JOB,end))
    need(request==dict(job=job_proof,code_pins=job['code_pins'],automatic_retries=0),'Metric job request differs')
    admission=parse_json(_read(files['ADMISSION.json'],job['limits']['output_bytes'],end))
    need(admission['generation']==job['generation'] and admission['generation_receipt']==_preserved_generation(job['generation'],end)
         and admission['join']['plan']==job['join_plan'] and admission['join']['all_scheduled_completed'] is True,
         'Metric generation/source admission differs')
    count=admission['join']['scheduled_counts'][job['family']]
    need(complete['bridge']['sources']==admission['join']['native_sources'],'Metric bridge native sources differ')
    need(complete['job']==job_proof and complete['status']=='completed' and complete['family']==job['family']
         and complete['group']==job['group'] and complete['metrics']==list(selected) and type(complete['automatic_retries'])is int
         and complete['automatic_retries']==0,'Metric terminal identity')
    wall=complete['wall_seconds'];need(type(wall)in(int,float) and math.isfinite(wall) and 0<=wall<job['limits']['seconds'],'Bounded metric worker clock')
    need(complete['offline']['denied_network_attempts']==complete['offline']['dropped_event_records']==0,'Metric offline denial')
    need(isinstance(complete['resource_samples'],list) and len(complete['resource_samples'])>=2,'Initial/final observed resources required')
    for sample in complete['resource_samples']:base.check_resources(sample,job['limits'])
    result_proofs=[files[f'results/{i:02}-{name}.json'] for i,name in enumerate(selected)]
    need(complete['result_files']==result_proofs,'Exact ordered metric result proofs')
    calls=complete['call_files'];need(len(calls)<=job['limits']['max_calls'],'Physical metric call bound')
    need(calls==[files[f'calls/{i:06}.json'] for i in range(len(calls))],'Exact ordered native call proofs')
    expected={'REQUEST.json','ADMISSION.json','COMPLETE.json','journal.jsonl',
        *(f'results/{i:02}-{n}.json' for i,n in enumerate(selected)),*(f'calls/{i:06}.json' for i in range(len(calls))),
        *(f'nltk_data/tokenizers/punkt_tab/english/{n}' for n in job['punkt'])}
    need(set(files)==expected,'Unknown/omitted evaluator evidence member')
    for name,p in job['punkt'].items():
        copied=files['nltk_data/tokenizers/punkt_tab/english/'+name]
        need(all(copied[k]==p[k] for k in ('bytes','sha256')),'Copied Punkt table differs from pinned original')
    directories={'results','calls'}|({'nltk_data','nltk_data/tokenizers','nltk_data/tokenizers/punkt_tab','nltk_data/tokenizers/punkt_tab/english'} if job['punkt'] else set())
    for p in root.rglob('*'):
        _path(p)
        if p.is_relative_to(root/'offload'):continue
        need(p.is_file() or p.relative_to(root).as_posix() in directories,'Unknown evaluator output directory')
    need(sum(p['bytes'] for p in files.values())+rp['bytes']<=job['limits']['output_bytes'],'Aggregate metric output ceiling')
    values=[parse_json(_read(p,job['limits']['output_bytes'],end)) for p in result_proofs]
    for name,value in zip(selected,values):
        need(value['family']==job['family'] and value['operation']=='metric:'+name and value['status']=='completed'
             and set(value['metrics'])=={name} and value['automatic_retries']==0 and value['scheduled_count']==count,'Metric result identity')
        if name!='mauve':need(value['metrics'][name]['provenance']==complete['bridge'],'Metric bridge provenance differs')
    call_values=[parse_json(_read(p,job['limits']['output_bytes'],end)) for p in calls]
    native=complete['native']
    if job['group']=='true':
        need(len(complete['bridge_calls'])==len(call_values) and complete['bridge_calls']==
             [c for name,value in zip(selected,values) for c in value['metrics'][name]['nli_calls']],
             'All native branching calls must join metric results')
        for c,v in zip(complete['bridge_calls'],call_values):
            need(c['status']=='completed' and c['error_type'] is None and type(c['entailment'])is int
                 and c['entailment']==v['result'] and fingerprint(c['request'])==v['request_sha256'],
                 'Branching verdict/request differs from captured native return')
    else:need(complete['bridge_calls']==[],'Only TRUE may retain branching inference calls')
    if job['group']=='lexical':
        need(native is None and not calls and complete['rng']['seed']==job['rng_seed'] and complete['rng']['after'] is not None,'Lexical RNG/accounting scope')
    else:
        need(native['failed'] is False and native['automatic_retries']==0 and native['runtime_sources']==job['runtime_sources']
             and len(native['calls'])==len(calls),'Native model accounting differs')
        for i,(record,value) in enumerate(zip(native['calls'],call_values)):
            need(record['ordinal']==value['ordinal']==i and record['status']=='completed' and record['error_type'] is None
                 and record['request_sha256']==value['request_sha256'],'Native call request/result binding')
            need(type(record['elapsed_seconds'])in(int,float) and math.isfinite(record['elapsed_seconds'])
                 and 0<=record['elapsed_seconds']<=wall,'Native call clock differs')
        need(sum(c['elapsed_seconds'] for c in native['calls'])<=wall,'Native sequential call clocks exceed worker')
        gpu=native['gpu'];need(gpu['available'] is True and all(type(gpu[k])is int and 0<=gpu[k]<=job['limits']['gpu_bytes']
             for k in ('peak_allocated_bytes','peak_reserved_bytes')),'Required bounded GPU observations')
    entered=done=observed=persisted=metric_entered=metric_done=true_count=rng_events=admissions=0;first=last=None
    for event in base.journal_rows(files['journal.jsonl'],job['limits']['output_bytes'],end):
        name=event['event'];d=event['details']
        if first is None:first=name
        need(last!='evaluation_completed' and not name.endswith('failed'),'Contradictory metric journal')
        if name=='evaluation_reserved':
            need(first==name and last is None and d==dict(family=job['family'],group=job['group'],metrics=list(selected)),
                 'Exact metric worker reservation required')
        elif name=='source_capture_admitted':
            need(admissions==0 and metric_entered==0 and d==dict(counts=admission['join']['scheduled_counts'],family=job['family']),
                 'Metric source admission observation differs');admissions+=1
        elif name=='lexical_rng_seeded':
            need(job['group']=='lexical' and rng_events==0 and metric_entered==0 and d==dict(seed=job['rng_seed'],
                state_sha256=fingerprint(complete['rng']['seeded'])),'Declared lexical RNG observation differs');rng_events+=1
        elif name=='metric_entered':
            need(metric_entered==metric_done and metric_entered<len(selected) and d==dict(name=selected[metric_entered],scheduled_count=count),
                 'Ordered metric reservation');metric_entered+=1
        elif name=='metric_completed':
            need(metric_entered==metric_done+1 and d==dict(name=selected[metric_done],proof=result_proofs[metric_done],
                result_sha256=fingerprint(values[metric_done])),'Metric result/observation differs');metric_done+=1
        elif name=='call_entered':
            need(native is not None and metric_entered==metric_done+1 and entered==done and entered==persisted and d==dict(native['calls'][entered],
                status='entered',elapsed_seconds=None,error_type=None),'Ordered native reservation');entered+=1
        elif name=='native_result_observed':
            need(entered==done+1 and observed==done and d==dict(ordinal=done,kind=native['calls'][done]['kind'],
                result_sha256=fingerprint(call_values[done]['result'])),'Native observed return differs');observed+=1
        elif name=='true_generation_observed':
            need(job['group']=='true' and true_count==done and d['ordinal']==done and type(call_values[done]['result'])is int
                 and type(d['entailment'])is int and type(d['decoded_text'])is str
                 and call_values[done]['result'] in (0,1) and d['entailment']==call_values[done]['result']==int(d['decoded_text']=='1'),
                 'Literal native TRUE result differs');true_count+=1
        elif name=='call_completed':
            need(entered==done+1 and observed==entered and d==native['calls'][done],'Native completion differs');done+=1
        elif name=='native_call_persisted':
            need(done==persisted+1 and d==dict(ordinal=persisted,proof=calls[persisted]),'Native durable return differs');persisted+=1
        elif name=='evaluation_completed':
            need(d==dict(metrics=list(selected),physical_calls=len(calls)) and metric_done==len(selected),
                 'Metric terminal accounting observation differs')
        last=name
    need(first=='evaluation_reserved' and last=='evaluation_completed' and metric_entered==metric_done==len(selected)
         and entered==done==observed==persisted==len(calls) and true_count==(len(calls) if job['group']=='true' else 0)
         and admissions==1 and rng_events==(1 if job['group']=='lexical' else 0),
         'Full metric/native journal completion required')
    need(receipt['files']==_inventory(root,end),'Late metric output drift')
    _read(job_proof,MAX_JOB,end);_read(job['join_plan'],job['limits']['input_bytes'],end)
    return rp


def supervise(job_proof,output):
    start=time.monotonic();job,plan,selected,worker,protected=load_job(job_proof)
    root=_fresh(output,[worker,*protected]);handle=base.contain_process_tree();root.mkdir()
    end=start+job['limits']['seconds']+30
    command=[job['interpreter']['path'],'-I','-B',str(Path(__file__).resolve()),'--worker','--job',job_proof['path'],'--job-sha256',job_proof['sha256']]
    try:
        base.write_new(root/'REQUEST.json',dict(job=job_proof,command=command,worker=str(worker),automatic_retries=0))
        with base.DeadlineWatchdog(end+10,root/'DEADLINE.json'):
            limits=base.processes.ProcessLimits(end-time.monotonic(),4*1024**2)
            base.write_new(root/'LIMITS.json',dict(timeout_seconds=limits.timeout_seconds,max_output_bytes=limits.max_output_bytes))
            try:result=base.processes.supervise_command(command,limits=limits)
            except BaseException as error:
                result=getattr(error,'tether_engine_result',getattr(error,'result',None))
                if result is not None:base._process_files(root,result,primary=error)
                raise
            base._process_files(root,result);need(result.returncode==0,'Metric child failed; no automatic repeat')
            base.processes.validate_success_report(result.supervision,limits,len(result.stdout),len(result.stderr))
            receipt=verify_worker(worker,job_proof,job,selected,end)
            terminal=parse_json(result.stdout)
            need(terminal==dict(status='completed',receipt=receipt),'Metric child stdout differs from closed worker receipt')
            complete=parse_json(_read(_hash(worker/'COMPLETE.json',end),job['limits']['output_bytes'],end))
            need(complete['wall_seconds']<=result.supervision['execution_elapsed_seconds'],'Metric child/process clock differs')
            need(job['code_pins']==source_pins(),'Metric supervisor code drift')
            base.write_new(root/'COMPLETE.json',dict(status='verified',job=job_proof,worker_receipt=receipt,wall_seconds=time.monotonic()-start))
            files={p.name:_hash(p,end) for p in root.iterdir() if p.is_file()}
            base.write_new(root/'RECEIPT.json',dict(kind='alce_metric_execution_receipt_v1',status='verified',files=files))
            return _hash(root/'RECEIPT.json',end)
    except BaseException as error:
        try:base.write_new(root/'FAILURE.json',dict(status='failed',error_type=type(error).__name__,reason=str(error)[:2000],automatic_retries=0))
        except BaseException as persistence:error.add_note('Metric supervisor failure retention failed: '+type(persistence).__name__)
        raise


def verify_execution(descriptor):
    """Read-only process/result reconciliation; never loads a model or dispatches."""
    end=time.monotonic()+3600;root=_path(descriptor['root']);rp=_hash(root/'RECEIPT.json',end)
    need(rp['sha256']==descriptor['receipt_sha256'],'External metric supervisor receipt required')
    receipt=parse_json(_read(rp,MAX_JOB,end));expected={'REQUEST.json','LIMITS.json','PROCESS.json','stdout.bin','stderr.bin','COMPLETE.json'}
    need(receipt['kind']=='alce_metric_execution_receipt_v1' and receipt['status']=='verified' and set(receipt['files'])==expected
         and {p.name for p in root.iterdir()}==expected|{'RECEIPT.json'},'Closed successful metric supervisor required')
    for name,p in receipt['files'].items():need(_path(p['path'])==root/name and _hash(root/name,end)==p,'Metric supervisor bytes differ')
    def read(name,maximum=MAX_JOB):return parse_json(_read(receipt['files'][name],maximum,end))
    request=read('REQUEST.json');job,plan,selected,worker,_=load_job(request['job'],fresh=False)
    command=[job['interpreter']['path'],'-I','-B',str(Path(__file__).resolve()),'--worker','--job',request['job']['path'],'--job-sha256',request['job']['sha256']]
    need(request==dict(job=request['job'],command=command,worker=str(worker),automatic_retries=0),'Exact supervised metric command required')
    limits=base.processes.ProcessLimits(**read('LIMITS.json'));process=read('PROCESS.json')
    need(0<limits.timeout_seconds<=job['limits']['seconds']+30 and limits.max_output_bytes==4*1024**2 and process['returncode']==0,
         'Metric process limit/terminal differs')
    base.processes.validate_success_report(process['supervision'],limits,receipt['files']['stdout.bin']['bytes'],receipt['files']['stderr.bin']['bytes'])
    wr=verify_worker(worker,request['job'],job,selected,end);complete=read('COMPLETE.json')
    need(read('stdout.bin')==dict(status='completed',receipt=wr) and complete['status']=='verified' and complete['job']==request['job']
         and complete['worker_receipt']==wr,'Metric process/worker completion differs')
    wc=parse_json(_read(_hash(worker/'COMPLETE.json',end),job['limits']['output_bytes'],end))
    need(type(complete['wall_seconds'])in(int,float) and math.isfinite(complete['wall_seconds'])
         and wc['wall_seconds']<=process['supervision']['execution_elapsed_seconds']<=complete['wall_seconds']<job['limits']['seconds']+30,
         'Carried metric process clocks differ')
    for p in receipt['files'].values():need(_hash(p['path'],end)==p,'Late metric supervisor mutation')
    need(_hash(root/'RECEIPT.json',end)==rp,'Late metric receipt mutation')
    return dict(root=str(root),receipt_sha256=rp['sha256'],worker_receipt=wr,process=process,complete=wc,
                scientific_metric_truth_independently_recomputed=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--job',type=Path,required=True)
    parser.add_argument('--job-sha256',required=True);parser.add_argument('--output',type=Path)
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS);args=parser.parse_args()
    p=_hash(_path(args.job),time.monotonic()+60);need(p['sha256']==args.job_sha256,'External metric job anchor required')
    if args.worker:receipt=execute(p)
    else:
        need(args.output is not None,'Fresh outer output required');receipt=supervise(p,args.output)
    print(canonical(dict(status='completed',receipt=receipt)).decode(),flush=True)


if __name__=='__main__':main()
