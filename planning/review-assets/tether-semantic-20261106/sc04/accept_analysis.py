"""Read-only SC04 root acceptance and report rendering (standard library only).

This checks bytes and recomputes summary arithmetic. It relies on the qualified
analysis CLI for raw native/source/lineage reconstruction; it is not a new
independent adjudication of biological truth or scientific entailment.
"""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path,PurePosixPath
import random
import re
import stat
import time
from urllib.parse import unquote,urlsplit

ROOT=Path(__file__).resolve().parents[4]
ARMS=('L/O','E/O','L/R','E/R');ALL_ARMS=ARMS+('supplied',)
PRIMARY_SHA='8de520bfdef4dbe7b6363aeb962b8c4bb453adc475297aca2fa08d88e7c10cf0'
SUPPLIED_SHA='f9dd1f8b8d0a560730d0450cec03647ec8adcba5d23e0836c16e6af03c1cf19c'
MAX_FILE=128*1024**2


def need(ok,why):
    if not ok:raise ValueError(why)


def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()


def decode(raw):
    def pairs(items):
        result={}
        for key,value in items:need(key not in result,'Duplicate JSON field');result[key]=value
        return result
    def bad(value):raise ValueError('Nonfinite JSON number')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=bad)


def regular(path):
    path=Path(path);info=path.lstat()
    need(stat.S_ISREG(info.st_mode) and not path.is_symlink() and not getattr(info,'st_file_attributes',0)&0x400,'Missing or linked/nonregular file')
    need(info.st_size<=MAX_FILE,'Acceptance file-size bound');return info


def raw(path):
    info=regular(path)
    with Path(path).open('rb') as stream:value=stream.read(MAX_FILE+1)
    after=regular(path)
    need(len(value)==info.st_size<=MAX_FILE and (info.st_size,info.st_ino,info.st_mtime_ns)==(after.st_size,after.st_ino,after.st_mtime_ns),'Changed input while reading')
    return value


def load(path):return decode(raw(path))
def proof(path):
    path=Path(path).absolute();value=raw(path);return dict(path=str(path),bytes=len(value),sha256=sha(value))
def checked_proof(value):
    need(proof(value['path'])==value,'Pinned external input bytes differ');return load(value['path'])


def safe(root,name):
    relative=PurePosixPath(name)
    need(isinstance(name,str) and name and '\\' not in name and not relative.is_absolute() and all(p not in ('.','..','') for p in relative.parts),'Unsafe inventory path')
    path=Path(root).joinpath(*relative.parts);need(path.resolve().is_relative_to(Path(root).resolve()),'Inventory escape');return path


def inventory(root,omit=(),recursive=True):
    root=Path(root).absolute();info=root.lstat()
    need(root.is_dir() and not root.is_symlink() and not getattr(info,'st_file_attributes',0)&0x400,'Linked acceptance root')
    result={};total=0;deadline=time.monotonic()+300
    for path in root.rglob('*') if recursive else root.iterdir():
        need(time.monotonic()<deadline,'Inventory traversal deadline')
        info=path.lstat();need(not path.is_symlink() and not getattr(info,'st_file_attributes',0)&0x400,'Linked inventory entry')
        if path.is_dir():continue
        name=path.relative_to(root).as_posix()
        if name in omit:continue
        total+=info.st_size;need(len(result)<60000 and total<=8*1024**3,'Inventory count/byte bounds')
        result[name]=proof(path)
    return result


def receipt(root,anchor,name='RECEIPT.json',recursive=True,expected_status='complete'):
    path=Path(root)/name;need(sha(raw(path))==anchor,'External receipt anchor mismatch');value=load(path)
    need(value['status']==expected_status and value['files']==inventory(root,omit=(name,),recursive=recursive),'Exact sealed inventory mismatch')
    return value


def chain(path):
    previous=None;events=[];data=raw(path);need(data.endswith(b'\n'),'Incomplete journal tail')
    for i,line in enumerate(data.splitlines()):
        e=decode(line);fingerprint=e.pop('sha256')
        need(e['sequence']==i and e['previous_sha256']==previous and sha(canonical(e))==fingerprint,'Journal chain mismatch')
        previous=fingerprint;events.append(e)
    return events


def utc(text):
    value=datetime.fromisoformat(text);need(value.tzinfo is not None,'Aware retained timestamp');return value.astimezone(timezone.utc)


def close(a,b,label):
    if type(a) is float or type(b) is float:
        need(type(a) in (int,float) and type(b) in (int,float) and math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12),label)
    elif isinstance(a,dict) and isinstance(b,dict):
        need(set(a)==set(b),label+' fields')
        for k in a:close(a[k],b[k],label+'.'+k)
    elif isinstance(a,list) and isinstance(b,list):
        need(len(a)==len(b),label+' count')
        for x,y in zip(a,b):close(x,y,label)
    else:need(type(a)==type(b) and a==b,label)


def normalize_doi(value):
    need(isinstance(value,str) and value.strip(),'DOI annotation');value=value.strip()
    if value.lower().startswith('doi:'):value=value[4:].strip()
    if value.startswith(('http://','https://')):
        url=urlsplit(value);need(url.netloc.lower() in ('doi.org','dx.doi.org','www.doi.org') and not url.query and not url.fragment,'Original DOI URL')
        value=unquote(url.path.lstrip('/'))
    need(re.fullmatch(r'10\.[0-9]{4,9}/[^\s"\\]+',value),'Original DOI syntax');return value.lower()


def grouping(ids,annotations):
    remaining=set(ids);groups=[]
    while remaining:
        component={next(i for i in ids if i in remaining)};papers=set()
        while True:
            papers.update(p for i in component for p in annotations[i])
            expanded=component|{i for i in remaining if papers.intersection(annotations[i])}
            if expanded==component:break
            component=expanded
        groups.append([i for i in ids if i in component]);remaining-=component
    return groups


def validate_inputs(value,fictional):
    queries=value['queries'];refs=value['references'];hints=value['hints'];ids=[q['id'] for q in queries]
    n=2 if fictional else 199
    need(len(ids)==len(set(ids))==n and [r['id'] for r in refs]==[h['id'] for h in hints]==ids,'Complete original input schedule')
    annotations={h['id']:h['dois'] for h in hints};need(value['annotations']==annotations,'Source annotation map')
    need(sum(len(v) for v in annotations.values())==(2 if fictional else 205) and len(set(d for v in annotations.values() for d in v))==(1 if fictional else 190),'Source-pair/unique-paper denominators')
    ordered=list(dict.fromkeys(d for h in hints for d in h['dois']));need(ordered==value['doi_schedule'],'DOI schedule order')
    groups=grouping(ids,annotations);need(value['groups']==groups and len(groups)==(1 if fictional else 186),'Publication dependence groups')
    if fictional:
        expected_ids=[f'00000000-0000-0000-0000-{i:012d}' for i in (901,902)]
        need(ids==expected_ids and [r['answer_index'] for r in refs]==[0,2] and all(r['unsure_index']==1 for r in refs),'Known fictional answer keys')
        need([q['question'] for q in queries]==['In the invented Lumarin experiment, what happened to cobalt uptake after treatment?',
            'In the invented Vesprine experiment, what happened to amber uptake after treatment?'],'Known fictional questions')
        need(all(q['choices']==['(A) Increased','(B) Insufficient information to answer the question','(C) Reduced'] for q in queries),'Fictional options')
    else:
        manifest=value['manifest'];need(manifest['role']=='evaluation_only' and manifest['questions']==199 and manifest['primary_answers_existed_at_freeze'] is False,'Original frozen evaluator contract')
        need(manifest['bootstrap_replicates']==10000 and manifest['seed']==20261106,'Preregistered statistical settings')
        for key in ('specification','addendum','grouping_code','freeze_helper','native_scorer'):
            p=manifest[key];need(proof(p['path'])==p,'Frozen analysis dependency')
        annotation=checked_proof(manifest['annotation_projection']);original=annotation['original'];need(proof(original['path'])==original,'Original released task bytes')
        need(annotation['role']=='diagnostic_selection_only' and annotation['ordinary_retrieval_permitted'] is False and annotation['answerer_may_read'] is False and
            annotation['correct_answers_included'] is False and annotation['key_passages_included'] is False,'Annotation isolation scope')
        rng=random.Random(20261106);built_queries=[];built_refs=[];built_hints=[]
        for line in raw(original['path']).splitlines():
            row=decode(line);values=[row['ideal'],'Insufficient information to answer the question']+row['distractors'];indices=list(range(len(values)));rng.shuffle(indices)
            built_queries.append(dict(id=row['id'],question=row['question'],choices=[f'({chr(65+i)}) {values[j]}' for i,j in enumerate(indices)]))
            built_refs.append(dict(id=row['id'],answer_index=indices.index(0),unsure_index=indices.index(1)))
            built_hints.append(dict(id=row['id'],question=row['question'],dois=[normalize_doi(x) for x in row['sources']]))
        need((queries,refs,hints)==(built_queries,built_refs,built_hints),'Original released question/choice/key/DOI projection')
        need(checked_proof(manifest['answer_queries'])==queries and checked_proof(manifest['reference_keys'])==refs,'Pinned query/key products')
        need(checked_proof(annotation['products']['hints'])==hints and checked_proof(annotation['products']['doi_schedule'])==ordered,'Pinned annotated-source products')
        need(checked_proof(manifest['groups'])['groups']==groups,'Frozen dependence grouping')
    return n,ids


def score(queries,references,records,evidence):
    ids=[q['id'] for q in queries];need([r['id'] for r in records]==ids and set(evidence)==set(ids),'Complete all-scheduled records')
    names='produced producer_failures accepted rejected check_errors check_not_run raw_answered checked_answered raw_correct correct_and_admitted correct_but_rejected correct_not_admitted native_unsure accepted_unsure incorrect_and_admitted incorrect_substantive_and_admitted parse_failures produced_or_parse_failure'.split()
    counts={k:0 for k in names};cases=[];producer=Counter();checks=Counter();reasons=Counter()
    for q,ref,row in zip(queries,references,records):
        need(set(row)=={'id','producer_status','check_status','prediction','reason'},'Disposition schema')
        need(ref['id']==q['id'] and q['choices'][ref['unsure_index']][4:]=='Insufficient information to answer the question' and ref['answer_index']!=ref['unsure_index'],'Choice/reference join')
        ps=row['producer_status'];cs=row['check_status'];pred=row['prediction'];reason=row['reason']
        need(ps in ('produced','parse_failure','timeout','error','interrupted','unexecuted','input_unavailable') and cs in ('accepted','rejected','error','not_run'),'Operational state')
        made=ps=='produced';accepted=cs=='accepted'
        if made:
            need(isinstance(pred,dict) and set(pred)=={'answer_index','evidence_ids'} and type(pred['answer_index']) is int and 0<=pred['answer_index']<len(q['choices']),'Bounded native answer index')
            need(len(pred['evidence_ids'])==len(set(pred['evidence_ids'])) and set(pred['evidence_ids'])<=set(evidence[q['id']]),'Offered source citations')
            need((reason is None)==accepted,'Admission reason')
        else:need(pred is None and cs=='not_run' and isinstance(reason,str) and reason,'Failure is explicit, unscored and unchecked')
        unsure=pred['answer_index']==ref['unsure_index'] if made else None
        correct=bool(made and pred['answer_index']==ref['answer_index']);answered=bool(made and not unsure)
        flags=dict(produced=made,producer_failures=not made,accepted=accepted,rejected=cs=='rejected',check_errors=cs=='error',check_not_run=cs=='not_run',
            raw_answered=answered,checked_answered=answered and accepted,raw_correct=correct,correct_and_admitted=correct and accepted,
            correct_but_rejected=correct and cs=='rejected',correct_not_admitted=correct and not accepted,native_unsure=unsure is True,accepted_unsure=unsure is True and accepted,
            incorrect_and_admitted=accepted and not correct,incorrect_substantive_and_admitted=accepted and answered and not correct,parse_failures=ps=='parse_failure',produced_or_parse_failure=ps in ('produced','parse_failure'))
        for k,v in flags.items():counts[k]+=int(v)
        producer[ps]+=1;checks[cs]+=1
        if reason is not None:reasons[reason]+=1
        cases.append(dict(id=q['id'],producer_status=ps,check_status=cs,prediction=pred,native_unsure=unsure,raw_correct=correct,
            correct_and_admitted=correct and accepted,raw_answered=answered,checked_answered=answered and accepted,reason=reason))
    def rates(c,a):return dict(accuracy=c/len(ids),precision=c/a if a else 0.0,coverage=a/len(ids))
    return dict(scheduled_count=len(ids),counts=counts,producer_status_counts=dict(producer),check_status_counts=dict(checks),reason_counts=dict(reasons),case_results=cases,
        raw_metrics=rates(counts['raw_correct'],counts['raw_answered']),checked_metrics=rates(counts['correct_and_admitted'],counts['checked_answered']),
        raw_precision_defined=bool(counts['raw_answered']),checked_precision_defined=bool(counts['checked_answered']),
        statistical_raw_precision=counts['raw_correct']/counts['raw_answered'] if counts['raw_answered'] else None,
        statistical_checked_precision=counts['correct_and_admitted']/counts['checked_answered'] if counts['checked_answered'] else None,
        unchanged_raw_checked=counts['accepted'],provenance_validated=True)


def contrasts(rates):
    lo,eo,lr,er=[rates[a] for a in ARMS]
    return dict(expansion_at_lexical=eo-lo,ranking_at_lexical=lr-lo,combined_vs_lexical=er-lo,interaction=(er-lr)-(eo-lo),
        marginal_expansion=((eo-lo)+(er-lr))/2,marginal_ranking=((lr-lo)+(er-eo))/2)


def bootstrap_check(report,ids,groups,flags):
    need(report['case_count']==len(ids) and report['group_count']==len(groups) and report['group_sizes']==list(map(len,groups)) and report['seed']==20261106 and report['requested_replicates']==10000,'Complete bootstrap design')
    rates={a:sum(flags[a])/len(ids) for a in ARMS};close(report['rates'],rates,'Bootstrap point rates');expected=contrasts(rates)
    need(set(report['contrasts'])==set(expected),'Complete six contrast family')
    for name,value in expected.items():close(report['contrasts'][name]['estimate'],value,'Contrast point estimate')
    need(report['uncertainty_estimable']==(len(groups)>1) and report['completed_replicates']==(10000 if len(groups)>1 else 0),'Bootstrap completion/undefined uncertainty')
    if len(groups)==1:
        need(all(v['ci95'] is None for v in report['contrasts'].values()),'Undefined one-component intervals');return
    index={key:i for i,key in enumerate(ids)};draw_units=[]
    for group in groups:draw_units.append((len(group),{a:sum(flags[a][index[i]] for i in group) for a in ARMS}))
    rng=random.Random(20261106);samples={name:[] for name in expected}
    for _ in range(10000):
        picked=[draw_units[rng.randrange(len(groups))] for _ in groups];denominator=sum(size for size,_ in picked)
        draw=contrasts({a:sum(counts[a] for _,counts in picked)/denominator for a in ARMS})
        for name,value in draw.items():samples[name].append(value)
    def percentile(values,q):
        values=sorted(values);position=(len(values)-1)*q;lo=math.floor(position);hi=math.ceil(position)
        return values[lo]+(values[hi]-values[lo])*(position-lo)
    for name,values in samples.items():close(report['contrasts'][name]['ci95'],[percentile(values,.025),percentile(values,.975)],'Recomputed paired interval')


def source_score(ids,annotations,cases,level):
    by={r['id']:r[level+'_dois'] for r in cases};need(set(by)==set(ids),'Complete source-case schedule');rows=[]
    for key in ids:
        gold=set(annotations[key]);found=set(by[key]);matched=gold&found
        rows.append(dict(id=key,annotated_ids=sorted(gold),retrieved_ids=sorted(found),matched_ids=sorted(matched),annotated_source_recall=len(matched)/len(gold) if gold else None))
    count=sum(len(r['annotated_ids']) for r in rows);hits=sum(len(r['matched_ids']) for r in rows);any_hits=sum(bool(r['matched_ids']) for r in rows)
    all_hits=sum(bool(r['annotated_ids']) and r['annotated_ids']==r['matched_ids'] for r in rows)
    return dict(scheduled_count=len(ids),annotated_source_count=count,matched_annotated_source_count=hits,annotated_source_recall=hits/count if count else None,
        questions_with_annotations=sum(bool(r['annotated_ids']) for r in rows),questions_without_annotations=sum(not r['annotated_ids'] for r in rows),
        questions_with_any_annotated_source_hit=any_hits,questions_with_all_annotated_sources=all_hits,any_hit_per_scheduled=any_hits/len(ids),all_hit_per_scheduled=all_hits/len(ids),semantic_support='unevaluated',case_results=rows)


def validate_summary(summary,inputs,primary,supplied,percase,native,recompute_intervals=True):
    n=len(inputs['queries']);ids=[q['id'] for q in inputs['queries']]
    need(summary['kind']=='sc04_all_scheduled_scientific_summary_v1' and summary['scheduled_count']==n and
        set(summary['arms'])==set(summary['source_metrics'])==set(summary['source_cases'])==set(summary['logical_arm_accounting'])==set(percase)==set(ALL_ARMS),'Complete five-arm result family')
    need(primary['queries']==supplied['queries']==inputs['queries'] and set(primary['records'])==set(ARMS) and set(supplied['records'])=={'supplied'},'Complete original query/arm join')
    for result in (primary,supplied):
        need(result['status']=='independently_reconstructed' and all(result[k] is True for k in ('source_lineage_checked','native_calls_checked','cross_stage_products_checked')),'Qualified source-inclusive reconstruction required')
    reconstructed={};all_cases={};all_records={};all_evidence={}
    for result in (primary,supplied):
        for arm,records in result['records'].items():
            expected=score(inputs['queries'],inputs['references'],records,result['evidence_ids'][arm]);close(summary['arms'][arm],expected,'All-scheduled native counts '+arm)
            reconstructed[arm]=expected;cases=result['source_cases'][arm];need([c['id'] for c in cases]==ids and cases==summary['source_cases'][arm],'Source-case result join')
            need(percase[arm]==dict(scored=expected['case_results'],sources=cases),'Per-case report join');all_cases[arm]=cases;all_records[arm]=records;all_evidence[arm]=result['evidence_ids'][arm]
            need(set(summary['source_metrics'][arm])=={'retained','pool','selected'},'Complete source layers')
            for level in ('retained','pool','selected'):close(summary['source_metrics'][arm][level],source_score(ids,inputs['annotations'],cases,level),'Source-layer coverage '+arm+' '+level)
            for c in cases:
                need(set(c['selected_dois'])<=set(c['pool_dois'])<=set(c['retained_dois']),'Source-layer set containment')
                need(0<=c['selected_passages']<=8 and 0<=c['selected_bytes']<=8000 and 0<=c['candidate_pool_bytes']<=10000 and c['extracted_paragraph_bytes']>=c['selected_bytes'],'Selected source bounds')
                usage=c['logical_model_usage'];cap=1 if arm=='supplied' else 3
                need(0<=usage['generation_calls']<=cap and 0<=usage['measured_output_tokens']<=256*cap and usage['provider_cost_usd']==0,'Logical arm model budget')
                need(usage['reserved_input_tokens']>=usage['measured_input_tokens'] and usage['reserved_output_tokens']>=usage['measured_output_tokens'],'Conservative versus measured model accounting')
                http=c['logical_http_usage'];need(http['requests']<= (4 if arm=='supplied' else 5) and http['safety_accounted_bytes']==http['measured_response_bytes']+http['unknown_transfer_upper_bytes'] and http['unknown_transfer_upper_bytes']>=0,'Logical HTTP accounting')
            account=summary['logical_arm_accounting'][arm]
            for category in ('logical_model_usage','logical_http_usage'):
                close(account[category],{k:sum(c[category][k] for c in cases) for k in cases[0][category]},'Logical aggregate '+category)
            for out,field in (('selected_text_bytes','selected_bytes'),('selected_passages','selected_passages'),('candidate_pool_bytes','candidate_pool_bytes'),('retained_original_bytes','retained_original_bytes'),('extracted_paragraph_bytes','extracted_paragraph_bytes')):
                need(account[out]==sum(c[field] for c in cases),'Logical source-byte accounting')
            need(account['native_status_counts']==dict(Counter(c['native_status'] for c in cases)) and account['no_selected_passage_cases']==sum(c['selected_passages']==0 for c in cases),'All-case native failures/missing passages')
            if arm!='supplied':
                for field in ('expansion_status','ranking_status','expansion_native_status','ranking_native_status','expansion_failure_reason','ranking_failure_reason'):
                    need(account[field+'_counts']==dict(Counter(c[field] for c in cases if c[field] is not None)),'Explicit intervention failure accounting')
    need(native['status']=='PASS' and native['arms_checked']==5 and [r['arm'] for r in native['comparisons']]==list(ALL_ARMS),'Complete independent/native agreement family')
    expected_keys=['scheduled_count','counts','raw_metrics','checked_metrics','raw_precision_defined','checked_precision_defined','producer_status_counts','check_status_counts','case_results']
    for record in native['comparisons']:
        need(record['checks']==expected_keys,'Native score comparison scope')
        for key in expected_keys:close(record['native'][key],reconstructed[record['arm']][key],'Retained native agreement '+key)
    paired=summary['paired'];need(set(paired['metrics'])=={'raw_accuracy','correct_and_admitted_yield'} and set(paired['ranking_transitions'])=={'L','E'},'Complete metric/transition family')
    for metric,field in (('raw_accuracy','raw_correct'),('correct_and_admitted_yield','correct_and_admitted')):
        need(set(paired['metrics'][metric])=={'publication_components','question_sensitivity'},'Primary and sensitivity intervals')
        flags={a:[row[field] for row in reconstructed[a]['case_results']] for a in ARMS}
        for grouping_name,groups in (('publication_components',inputs['groups']),('question_sensitivity',[[i] for i in ids])):
            if recompute_intervals:bootstrap_check(paired['metrics'][metric][grouping_name],ids,groups,flags)
            else:
                point=contrasts({a:sum(flags[a])/n for a in ARMS});report=paired['metrics'][metric][grouping_name]
                need(set(report['contrasts'])==set(point),'Complete six contrast family')
                for k,v in point.items():close(report['contrasts'][k]['estimate'],v,'Six contrast point estimate')
    for branch in ('L','E'):
        before=reconstructed[branch+'/O']['case_results'];after=reconstructed[branch+'/R']['case_results']
        transition=paired['ranking_transitions'][branch]
        for key,predicate in dict(incorrect_to_correct=lambda a,b:not a and b,correct_to_incorrect=lambda a,b:a and not b,
            correct_to_correct=lambda a,b:a and b,incorrect_to_incorrect=lambda a,b:not a and not b).items():
            need(transition[key]==sum(predicate(a['raw_correct'],b['raw_correct']) for a,b in zip(before,after)),'Paired ranking correctness transitions')
        need(transition['scheduled_count']==n,'Paired ranking denominator')
        left,right=all_evidence[branch+'/O'],all_evidence[branch+'/R']
        expected=dict(membership_changed=sum(set(left[i])!=set(right[i]) for i in ids),order_changed_with_same_membership=sum(set(left[i])==set(right[i]) and left[i]!=right[i] for i in ids),identical_selection=sum(left[i]==right[i] for i in ids))
        need(summary['ranking_selection_changes'][branch]==expected,'Passage selection change decomposition')
    available={c['id'] for c in all_cases['supplied'] if c['source_coverage']['retained_articles']>0}
    all_available={c['id'] for c in all_cases['supplied'] if not c['source_coverage']['unknown_or_unavailable_inputs']}
    def subset_score(arm,subset):
        return score([q for q in inputs['queries'] if q['id'] in subset],[r for r in inputs['references'] if r['id'] in subset],
            [r for r in all_records[arm] if r['id'] in subset],{i:all_evidence[arm][i] for i in ids if i in subset})
    need(set(summary['supplied_source_subsets'])=={'any_annotated_source_eligible','all_annotated_sources_eligible'},'Diagnostic subset family')
    for key,subset in (('any_annotated_source_eligible',available),('all_annotated_sources_eligible',all_available)):
        report=summary['supplied_source_subsets'][key]
        if subset:close(report,subset_score('supplied',subset),'Diagnostic availability subset')
        else:need(report['scheduled_count']==0 and report['metrics'] is None,'Empty diagnostic subset explicit')
    e={c['id'] for c in all_cases['E/O'] if c['expansion_native_status']=='completed'}
    l={c['id'] for c in all_cases['L/R'] if c['ranking_native_status']=='completed'}
    r={c['id'] for c in all_cases['E/R'] if c['ranking_native_status']=='completed'}
    subsets=dict(expansion_available=e,lexical_branch_ranking_available=l,expanded_branch_ranking_available=r,all_interventions_available=e&l&r)
    need(set(summary['available_intervention_subsets'])==set(subsets),'Complete intervention-available subset family')
    for name,subset in subsets.items():
        report=summary['available_intervention_subsets'][name];need(report['ids']==[i for i in ids if i in subset] and report['scheduled_count']==len(subset),'Intervention subset schedule')
        if subset:
            need(set(report['arms'])==set(ARMS),'Complete intervention subset arms')
            for arm in ARMS:close(report['arms'][arm],subset_score(arm,subset),'Intervention available subset scoring')
            close(report['raw_accuracy_contrasts'],contrasts({a:report['arms'][a]['raw_metrics']['accuracy'] for a in ARMS}),'Intervention subset contrasts')
        else:need(report['arms']=={} and report['raw_accuracy_contrasts'] is None,'Empty intervention subset explicit')
    need(summary['model_provider_spend_usd']==0,'No provider spending')
    need(summary['physical_accounting']==dict(primary=primary['resources'],supplied=supplied['resources']),'Physical resource reconstruction joins')
    return dict(questions=n,arms=5,answer_records=5*n,source_pairs=sum(len(v) for v in inputs['annotations'].values()),
        unique_papers=len(inputs['doi_schedule']),publication_groups=len(inputs['groups']),contrasts_per_metric=6,metrics=2,
        bootstrap_recomputed=recompute_intervals,scientific_validity='not_established')


def experiment_root(descriptor,result,fictional):
    expected_status='primary_execution_complete' if set(result['records'])==set(ARMS) else 'diagnostic_execution_complete'
    root=Path(descriptor['root']).absolute();anchor=descriptor['root_sha256'];rec=receipt(root,anchor,'ROOT-RECEIPT.json',recursive=False,expected_status=expected_status)
    complete=load(root/'COMPLETE.json');frame=load(root/'FRAME.json');need(rec['frame_sha256']==sha(raw(root/'FRAME.json'))==result['frame_sha256'],'Original execution frame anchor')
    need(result['root']==str(root) and result['root_sha256']==anchor and complete['status']==expected_status and complete['purpose']==frame['purpose']==('fictional_qualification' if fictional else 'production'),'Original run identity/purpose')
    phases=('expand','collect','rank','answer') if frame['kind']=='sc04_primary_execution_v1' else ('collect','answer')
    need(set(complete['phases'])==set(phases),'Original complete phase family');files=len(rec['files']);journals=0
    for phase in phases:
        p=root/phase;d=complete['phases'][phase];need(Path(d['root'])==p and load(root/(phase+'-ANCHOR.json'))==d,'Original phase anchor identity')
        package=receipt(p,d['package_sha256'],'PACKAGE-RECEIPT.json');need(package['frame_sha256']==rec['frame_sha256'] and package['phase']==phase,'Original phase package frame')
        files+=len(package['files']);need(not any(Path(n).name in ('FAILURE.json','DEADLINE.json','FINALIZATION-FAILED.json') for n in package['files']),'Failed original package cannot pass')
        for name in package['files']:
            if Path(name).name=='journal.jsonl':chain(safe(p,name));journals+=1
    root_events=chain(root/'journal.jsonl');journals+=1
    for name,fingerprint in frame['code_pins'].items():need(proof(safe(ROOT,name))['sha256']==fingerprint,'Original executed source code changed')
    return dict(root=root,frame=frame,complete=complete,files=files,journals=journals,root_events=root_events)


def physical_accounting(experiment,result,primary):
    root=experiment['root'];phases=experiment['complete']['phases'];physical=result['resources'];derived={}
    for phase in phases:
        stage=root/phase/'worker/phase';reported=physical['phases'][phase]
        if phase=='collect':
            requests=[]
            for path in sorted((stage/'products').glob('*/MANIFEST.json')):requests.extend(load(path)['requests'])
            measured=sum(r['measured_bytes'] or 0 for r in requests);accounted=sum(r['accounted_bytes'] for r in requests)
            expected=dict(attempted_requests=len(requests),captured_requests=sum(r['transport_status']=='captured' for r in requests),failed_requests=sum(r['transport_status']=='failed' for r in requests),
                http_200=sum(r['http_status']==200 for r in requests),measured_response_bytes=measured,reserved_response_bytes=sum(r['byte_reservation'] for r in requests),safety_accounted_bytes=accounted,
                unknown_transfer_upper_bytes=accounted-measured,wire_bytes=None,retries=0,provider_cost_usd=0)
            close(reported['http'],expected,'Physical HTTP phases');close(physical['physical_http'],expected,'Physical HTTP total');continue
        totals=dict(generation_calls=0,tokenizer_calls=0,measured_input_tokens=0,measured_output_tokens=0,reserved_input_tokens=0,reserved_output_tokens=0,provider_cost_usd=0)
        for path in sorted((stage/'products').glob('*/SUMMARY.json')):
            call=load(path);totals['generation_calls']+=int(call['generation_entered']);totals['tokenizer_calls']+=int(call['generation_entered'])
            if call['usage']:
                totals['measured_input_tokens']+=call['usage']['input_tokens'];totals['measured_output_tokens']+=call['usage']['output_tokens'];totals['provider_cost_usd']+=call['usage']['cost_usd']
            totals['reserved_input_tokens']+=call['reservation_input_tokens'];totals['reserved_output_tokens']+=call['reservation_output_tokens']
        close(reported['model'],totals,'Physical model phase');derived[phase]=totals
    total={k:sum(value[k] for value in derived.values()) for k in next(iter(derived.values()))};close(physical['physical_model'],total,'Physical model sum')
    n=len(result['queries']);need(total['generation_calls']<=n*(7 if primary else 1) and total['measured_output_tokens']<=256*n*(7 if primary else 1) and total['provider_cost_usd']==0,'Physical total budget')
    if primary:
        # Each output arm is physically distinct; expansion and ranking are shared.
        answers={a:dict(generation_calls=0,measured_input_tokens=0,measured_output_tokens=0,reserved_input_tokens=0,reserved_output_tokens=0,provider_cost_usd=0) for a in ARMS}
        for path in sorted((root/'answer/worker/phase/slots').glob('*.json')):
            row=load(path);call=row['product']['call']['summary'];arm=answers[row['branch']]
            arm['generation_calls']+=int(call['generation_entered']);arm['reserved_input_tokens']+=call['reservation_input_tokens'];arm['reserved_output_tokens']+=call['reservation_output_tokens']
            if call['usage']:
                arm['measured_input_tokens']+=call['usage']['input_tokens'];arm['measured_output_tokens']+=call['usage']['output_tokens'];arm['provider_cost_usd']+=call['usage']['cost_usd']
        rankings={b:{k:0 for k in answers['L/O']} for b in ('L','E')}
        for path in sorted((root/'rank/worker/phase/slots').glob('*.json')):
            row=load(path);entry=row['product']['call']
            if entry is None:continue
            call=entry['summary'];arm=rankings[row['branch']];arm['generation_calls']+=int(call['generation_entered']);arm['reserved_input_tokens']+=call['reservation_input_tokens'];arm['reserved_output_tokens']+=call['reservation_output_tokens']
            if call['usage']:
                arm['measured_input_tokens']+=call['usage']['input_tokens'];arm['measured_output_tokens']+=call['usage']['output_tokens'];arm['provider_cost_usd']+=call['usage']['cost_usd']
        for arm in ARMS:
            charged=dict(answers[arm])
            for extra in ([derived['expand']] if arm[0]=='E' else [])+([rankings[arm[0]]] if arm.endswith('/R') else []):
                for k in charged:charged[k]+=extra[k]
            actual={k:sum(c['logical_model_usage'][k] for c in result['source_cases'][arm]) for k in charged};close(actual,charged,'Logical versus actual shared model charges')
    else:
        actual={k:sum(c['logical_model_usage'][k] for c in result['source_cases']['supplied']) for k in ('generation_calls','measured_input_tokens','measured_output_tokens','reserved_input_tokens','reserved_output_tokens','provider_cost_usd')}
        close(actual,{k:total[k] for k in actual},'Diagnostic logical/physical model equality')
    for path in sorted((root/'answer/worker/phase/slots').glob('*.json')):
        row=load(path);arm=row['branch'] if primary else 'supplied';records={r['id']:r for r in result['records'][arm]}
        need(row['product']['disposition']==records[row['id']],'Original execution answer disposition join')


def accept(root,anchor,controls_path,controls_sha,fictional=False):
    root=Path(root).absolute();sealed=receipt(root,anchor);frame=load(root/'FRAME.json');complete=load(root/'COMPLETE.json')
    need(frame['kind']=='sc04_scientific_analysis_execution_v1' and frame['purpose']==complete['purpose']==('fictional_qualification' if fictional else 'production'),'Explicit acceptance purpose')
    need(complete['status']=='complete' and complete['frame_sha256']==sha(raw(root/'FRAME.json')) and complete['provider_cost_usd']==frame['provider_cost_usd']==0 and complete['automatic_retry'] is False,'Completed analysis frame/status')
    need(frame['bootstrap_replicates']==10000 and frame['seed']==20261106,'Frozen analysis settings')
    need(complete['worker_receipt']==proof(root/'worker/RECEIPT.json') and complete['scientific_summary']==proof(root/'worker/RESULTS.json'),'Analysis worker/summary receipt binding')
    worker_receipt=receipt(root/'worker',complete['worker_receipt']['sha256']);need(worker_receipt['frame_sha256']==complete['frame_sha256'],'Worker frame binding')
    for name,p in frame['code_proofs'].items():need(Path(p['path'])==safe(ROOT,name) and proof(p['path'])==p,'Current qualified analysis code differs')
    need(sha(raw(controls_path))==controls_sha,'External full-controls anchor');controls=load(controls_path)
    need(controls['status']=='PASS' and controls['tests']>=146 and controls['failures']==controls['errors']==controls['skipped']==0,'Complete current regression gate')
    for name,fingerprint in controls['source_sha256'].items():
        name=Path(name).as_posix();need(name in frame['code_proofs'] and frame['code_proofs'][name]['sha256']==fingerprint,'Tests do not cover current analysis source bytes')
    root_events=chain(root/'journal.jsonl');worker_events=chain(root/'worker/journal.jsonl')
    need([e['event'] for e in root_events]==['analysis_reserved','analysis_frame_frozen','analysis_worker_started','analysis_worker_accepted','analysis_report_sealed'],'Complete analysis parent journal')
    need(root_events[1]['details']['frame_sha256']==complete['frame_sha256'] and root_events[-2]['details']['worker_receipt_sha256']==complete['worker_receipt']['sha256'] and root_events[-1]['details']['complete_sha256']==sha(raw(root/'COMPLETE.json')),'Analysis parent event fingerprints')
    need([e['event'] for e in worker_events]==['analysis_reserved','worker_frame_verified','primary_verification_started','primary_envelope_verified','supplied_envelope_verified','original_inputs_verified','primary_reconstructed','supplied_reconstructed','independent_metrics_completed','native_agreement_completed','analysis_completed'],'Complete scientific worker stages')
    need(worker_events[1]['details']['frame_sha256']==complete['frame_sha256'] and worker_events[-1]['details']['complete_sha256']==sha(raw(root/'worker/COMPLETE.json')),'Analysis worker event fingerprints')
    worker_complete=load(root/'worker/COMPLETE.json');need(worker_complete['status']=='complete' and worker_complete['purpose']==frame['purpose'] and worker_complete['independent_native_agreement']=='PASS' and worker_complete['scientific_validation']=='not_established','Scientific completion scope')
    supervision=load(root/'SUPERVISION.json');need(supervision['process_reaped'] is True and supervision['termination_reason']=='exited' and supervision['cleanup_errors']==[] and supervision['execution_elapsed_seconds']<frame['seconds'],'Owned analysis completion/deadline')
    need(supervision['retained_stdout_bytes']==len(raw(root/'stdout.log')) and supervision['retained_stderr_bytes']==len(raw(root/'stderr.log')) and len(raw(root/'stdout.log'))+len(raw(root/'stderr.log'))<=frame['output_cap'],'Analysis retained stream accounting')
    terminal=decode(raw(root/'stdout.log'));need(terminal['status']=='complete' and terminal['receipt_sha256']==complete['worker_receipt']['sha256'],'Worker printed receipt anchor')
    inputs=load(root/'worker/INPUTS.json');summary=load(root/'worker/RESULTS.json');primary=load(root/'worker/PRIMARY-RECONSTRUCTION.json');supplied=load(root/'worker/SUPPLIED-RECONSTRUCTION.json')
    n,ids=validate_inputs(inputs,fictional);need(worker_complete['questions']==n and worker_complete['answer_records']==5*n,'Complete worker scientific denominator')
    left=experiment_root(frame['primary'],primary,fictional);right=experiment_root(frame['supplied'],supplied,fictional)
    need(left['frame']['generation_configuration']==right['frame']['generation_configuration']==frame.get('generation_configuration',left['frame']['generation_configuration']),'Same compared generation configuration')
    need(left['frame']['model_provenance']==right['frame']['model']['model_provenance'] and left['frame']['alias']==right['frame']['model']['alias'],'Same answer model identity')
    for key,fingerprint in left['frame']['code_pins'].items():need(right['frame']['code_pins'].get(key)==fingerprint,'Same primary producer code')
    need(checked_proof(left['frame']['query_products']['answer_queries'])==checked_proof(right['frame']['products']['answer_queries'])==inputs['queries'],'Original experiment question/choice join')
    need(checked_proof(right['frame']['products']['hints'])==inputs['hints'] and checked_proof(right['frame']['products']['doi_schedule'])==inputs['doi_schedule'],'Original diagnostic DOI hints/schedule join')
    pair=load(root/'worker/PAIR.json')
    if fictional:
        need(frame['analysis_inputs'] is None and frame['primary']['root_sha256']==PRIMARY_SHA and frame['supplied']['root_sha256']==SUPPLIED_SHA and pair['status']=='fictional_fixture_pair' and pair['production_pair_gate'] is False,'Exact fictional-only roots')
    else:
        manifest=frame['analysis_inputs'];need(manifest is not None and sha(raw(manifest['path']))==manifest['sha256'] and load(manifest['path'])==inputs['manifest'],'Frozen evaluator input external anchor')
        need(pair['status']=='verified' and pair['primary_root_sha256']==frame['primary']['root_sha256'] and pair['supplied_root_sha256']==frame['supplied']['root_sha256'],'Production paired roots verified')
        descriptor=right['frame']['primary_execution'];need(Path(descriptor['root'])==left['root'] and descriptor['receipt']==proof(left['root']/'ROOT-RECEIPT.json') and descriptor['receipt']['sha256']==frame['primary']['root_sha256'],'Diagnostic commits to finalized primary run')
        need(checked_proof(right['frame']['primary_frame'])==left['frame'],'Diagnostic primary frame input')
        answer_start=chain(left['root']/'answer/worker/journal.jsonl')[0]['details']['created_at_utc']
        need(utc(inputs['manifest']['created_at_utc'])<utc(answer_start),'Analysis decisions fixed before primary answers')
        need(utc(left['complete']['source_cutoff'])<=utc(right['frame']['created_at_utc'])<=utc(right['root_events'][0]['details']['created_at_utc'])<=utc(right['complete']['source_cutoff']),'Declared primary/diagnostic ordering')
    checks=validate_summary(summary,inputs,primary,supplied,load(root/'worker/PER-CASE.json'),load(root/'worker/NATIVE-AGREEMENT.json'))
    need([r['doi'] for r in summary['diagnostic_resolutions']]==inputs['doi_schedule'],'Complete190-DOI diagnostic resolutions')
    physical_accounting(left,primary,True);physical_accounting(right,supplied,False)
    resources=load(root/'worker/RESOURCES.json');need(resources['experiment_physical']==summary['physical_accounting'] and resources['experiment_logical']==summary['logical_arm_accounting'] and resources['provider_cost_usd']==0,'Resource report joins')
    need(summary['diagnostic_resolutions']==supplied['diagnostic_resolutions'],'Diagnostic resolution report join')
    report=dict(status='PASS',purpose=frame['purpose'],analysis_receipt=proof(root/'RECEIPT.json'),analysis_frame=proof(root/'FRAME.json'),
        controls=proof(controls_path),acceptance_code=proof(Path(__file__)),source_pins_checked=len(frame['code_proofs']),
        sealed_files_checked=len(sealed['files'])+len(worker_receipt['files'])+left['files']+right['files'],journals_checked=2+left['journals']+right['journals'],**checks,
        primary_root_receipt=proof(left['root']/'ROOT-RECEIPT.json'),supplied_root_receipt=proof(right['root']/'ROOT-RECEIPT.json'),
        numerical_prediction_scope='Public-development MCQ answering only; no calibrated clinical probability or therapeutic claim.',
        scientific_validation='not_established',byte_integrity='verified',summary_arithmetic='recomputed',
        raw_source_and_native_semantics='Performed by the pinned qualified analysis CLI; this acceptance rechecks byte inventories and cross-joins, not a third full parser.',
        limits=['No independent biological adjudication. Paper identity is not answer support.','Local timestamps are not trusted-clock attestation.',
                '128 MiB per file, 60,000 files and 8 GiB per inventory, 300-second traversal checks; OS blocking I/O is not preempted.',
                'Model weights are not rehashed; pinned receipts and owned-generation identities are retained.',
                'Fictional qualification never substitutes for the199-question production gate.'])
    return report,summary,inputs,frame,resources


def pct(value):return 'undefined' if value is None else f'{100*value:.1f}%'
def cell(value):return str(value).replace('|','\\|').replace('\n',' ')
def ci(value):return 'undefined (one publication group)' if value is None else f'[{100*value[0]:+.2f}, {100*value[1]:+.2f}]'


def render(report,summary,inputs,resources):
    n=report['questions'];fictional=report['purpose']=='fictional_qualification'
    peak=(resources.get('analysis_process') or {}).get('process_peak_working_set_bytes')
    peak_text='unavailable' if peak is None else f'{peak:,} bytes'
    lines=['# TETHER SC04 — '+('fictional analysis qualification' if fictional else 'LitQA2 retrieval comparison'),'',
        '**'+('Fictional controls only. These are not benchmark performance results.' if fictional else 'All 199 original public-development questions are included in every arm.')+'**','',
        'The source-inclusive analysis and this root acceptance pass their declared technical checks. Scientific and clinical validity remain unestablished.','',
        '## What was compared','',
        '| Arm | Retrieval | Passage selection |','|---|---|---|',
        '| L/O | Question-only lexical queries | Lexical selection |','| E/O | Model-expanded queries, with declared fallback | Lexical selection |',
        '| L/R | Question-only lexical queries | Model ranking, with declared fallback |','| E/R | Model-expanded queries, with declared fallback | Model ranking, with declared fallback |',
        '| Supplied source | Privileged annotated paper identities | Lexical selection |','',
        'The supplied-source diagnostic is not ordinary retrieval. All five arms use the same frozen answer producer. The older baseline has different acquisition time, prompt and allocation; it is a historical control.','',
        '## Answers across the full schedule','',
        '| Arm | Correct | Correct and admitted | Substantive answers | Raw accuracy | Substantive precision | Unsure | Operational failures | Rejected |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for arm in ALL_ARMS:
        m=summary['arms'][arm];c=m['counts'];lines.append(f'| {arm} | {c["raw_correct"]}/{n} | {c["correct_and_admitted"]}/{n} | {c["raw_answered"]}/{n} | {pct(m["raw_metrics"]["accuracy"])} | {pct(m["statistical_raw_precision"])} | {c["native_unsure"]} | {c["producer_failures"]} | {c["rejected"]} |')
    lines+=['','Operational failures remain in the accuracy and coverage denominators. An explicit unsure response is distinct from a malformed or unavailable result. Admission verifies the declared source obligations, not answer entailment.','',
        '## Paired effects','',
        f'{report["publication_groups"]} publication components group questions sharing annotated papers. Each primary contrast uses 10,000 paired component-bootstrap draws when uncertainty is estimable; question-level intervals are retained as sensitivity analyses.','',
        '| Contrast | Raw accuracy change (percentage points) | 95% component interval | Correct-and-admitted change | 95% component interval |',
        '|---|---:|---|---:|---|']
    left=summary['paired']['metrics']['raw_accuracy']['publication_components']['contrasts'];right=summary['paired']['metrics']['correct_and_admitted_yield']['publication_components']['contrasts']
    for key in ('expansion_at_lexical','ranking_at_lexical','combined_vs_lexical','interaction','marginal_expansion','marginal_ranking'):
        lines.append(f'| {key.replace("_"," ")} | {100*left[key]["estimate"]:+.2f} | {ci(left[key]["ci95"])} | {100*right[key]["estimate"]:+.2f} | {ci(right[key]["ci95"])} |')
    lines+=['','These are exploratory effects on an exposed development set. No threshold was fitted to these evaluated answers. All six contrasts are reported; intervention-available subsets are secondary and retained in RESULTS.json.','',
        '## Annotated paper coverage','',f'The schedule contains {report["source_pairs"]} question–paper pairs and {report["unique_papers"]} distinct annotated papers. Identity matches do not establish decisive-passage recall or scientific support.','',
        '| Arm | Retained pair matches | Candidate-pool pair matches | Selected pair matches | Questions with any selected match | Questions with all annotated sources selected |',
        '|---|---:|---:|---:|---:|---:|']
    for arm in ALL_ARMS:
        m=summary['source_metrics'][arm];lines.append(f'| {arm} | {m["retained"]["matched_annotated_source_count"]}/{report["source_pairs"]} | {m["pool"]["matched_annotated_source_count"]}/{report["source_pairs"]} | {m["selected"]["matched_annotated_source_count"]}/{report["source_pairs"]} | {m["selected"]["questions_with_any_annotated_source_hit"]}/{n} | {m["selected"]["questions_with_all_annotated_sources"]}/{n} |')
    lines+=['','## Failures and interventions','', '| Arm | Answer status counts | Expansion failures | Ranking failures | No selected passage |','|---|---|---|---|---:|']
    for arm in ALL_ARMS:
        a=summary['logical_arm_accounting'][arm];lines.append(f'| {arm} | {cell(a["native_status_counts"])} | {cell(a.get("expansion_failure_reason_counts",{}))} | {cell(a.get("ranking_failure_reason_counts",{}))} | {a["no_selected_passage_cases"]} |')
    reasons=Counter(d['reason'] for r in summary['diagnostic_resolutions'] for d in r['decisions'])
    lines+=['',f'Diagnostic source decisions: `{dict(reasons)}`. These counts describe resolution decisions, not mutually exclusive questions. Missing collection is not biological absence.','',
        'The frozen answer pipeline cannot gracefully finalize every over-capacity admission case: an overlong payload can abort before a model-cell capacity record. A completed run has passed its declared path; no broader capacity guarantee follows.','',
        '## Physical resources','', '| Run | Generation calls | Input tokens | Output tokens | HTTP attempts | Measured response bytes | Unknown-transfer upper bytes | Worker wall seconds |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,p in summary['physical_accounting'].items():
        m=p['physical_model'];h=p['physical_http'];lines.append(f'| {name} | {m["generation_calls"]} | {m["measured_input_tokens"]} | {m["measured_output_tokens"]} | {h["attempted_requests"]} | {h["measured_response_bytes"]} | {h["unknown_transfer_upper_bytes"]} | {p["worker_wall_seconds_sum"]:.3f} |')
    lines+=['','Provider spending: **$0**. Shared expansion, ranking and collection can appear in multiple logical arm totals; those totals must not be summed as physical cost. Token reservations and measured usage are separate. Energy, GPU memory and aggregate machine memory were not measured.','',
        f'Analysis worker: {resources["analysis_wall_seconds"]:.3f}s; process peak working set: {peak_text}. This is a process peak, not whole-machine RAM.','',
        '## What acceptance establishes','',
        f'- Externally anchored analysis receipt: `{report["analysis_receipt"]["sha256"]}`.',
        f'- {report["sealed_files_checked"]} sealed inventory entries and {report["journals_checked"]} journal chains checked.',
        f'- {report["source_pins_checked"]} qualified analysis source files matched.',
        '- Original choices, reference keys, source annotations, complete denominators, all-five-arm accounting and paired arithmetic reconcile.',
        '- The pinned analysis CLI performed raw native/source/lineage reconstruction. Root acceptance rechecks its bytes, joins and arithmetic.','',
        '**Not established:** untouched-test generalization, independent biological correctness, clinical benefit, calibrated clinical probabilities, or superiority to the original Virtual Biotech system.','',
        '[Acceptance record](ROOT-ACCEPTANCE.json) · [Reproduction instructions](REPRODUCE.md)','']
    return '\n'.join(lines)


def reproduce(report,frame):
    command=['python -I -B experiments/litqa_analysis/run.py execute',
        '  --primary-root "'+frame['primary']['root']+'" --primary-root-sha256 '+frame['primary']['root_sha256'],
        '  --supplied-root "'+frame['supplied']['root']+'" --supplied-root-sha256 '+frame['supplied']['root_sha256']]
    if frame['purpose']=='fictional_qualification':command.append('  --fictional')
    else:command.append('  --analysis-inputs "'+frame['analysis_inputs']['path']+'" --analysis-inputs-sha256 '+frame['analysis_inputs']['sha256'])
    command.append('  --output data/benchmark/litqa_comparison/analysis-NEW-ATTEMPT --seconds '+str(frame['seconds']))
    return '\n'.join(['# Reproduce the SC04 analysis','',
        'Run from the repository root with the qualified Python 3.11 interpreter and matching source bytes. Original datasets, model-run captures and frozen inputs remain external or ignored; Git alone is insufficient.','',
        'The command reads completed captures and performs no new inference or download. Use a fresh output directory. Preserve the printed receipt hash outside the output tree.','',
        '```powershell',' `\n'.join(command),'```','',
        'Then run root acceptance with the new receipt and the current retained regression record:','',
        '```powershell','python -I -B planning/review-assets/tether-semantic-20261106/sc04/accept_analysis.py `',
        '  --analysis <completed-analysis-path> --analysis-sha256 <externally-saved-receipt-sha256> `',
        '  --controls "'+report['controls']['path']+'" --controls-sha256 '+report['controls']['sha256']+' `',
        ('  --fictional `' if frame['purpose']=='fictional_qualification' else '  `'),
        '  --output planning/review-assets/tether-semantic-20261106/sc04/acceptance-NEW-ATTEMPT','```','',
        'For production, both complete source-inclusive runs are required, including the separately labelled supplied-source diagnostic and the original 199-question frozen evaluator inputs. Fictional mode accepts only the two retained fictional roots and never substitutes for production.','',
        'The analysis CLI has a supervised worker deadline and retained failure logs. This acceptance utility bounds file sizes, inventory counts and traversal duration but cannot preempt blocking OS I/O. A failed attempt must be inspected and preserved; no command resumes or retries it automatically.',''])


def write(path,value):
    data=value if isinstance(value,bytes) else value.encode() if isinstance(value,str) else canonical(value)+b'\n'
    with Path(path).open('xb') as stream:stream.write(data)


class Log:
    def __init__(self,root):
        self.root=Path(root).absolute();self.root.mkdir(parents=True,exist_ok=False);self.previous=None;self.number=0
        self.stream=(self.root/'journal.jsonl').open('xb');self.append('acceptance_reserved',created_at_utc=datetime.now(timezone.utc).isoformat())
    def append(self,event,**details):
        record=dict(event=event,details=details,sequence=self.number,previous_sha256=self.previous);record['sha256']=sha(canonical(record))
        self.stream.write(canonical(record)+b'\n');self.stream.flush();self.previous=record['sha256'];self.number+=1
    def close(self):self.stream.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis',type=Path,required=True);p.add_argument('--analysis-sha256',required=True)
    p.add_argument('--controls',type=Path,required=True);p.add_argument('--controls-sha256',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--fictional',action='store_true');args=p.parse_args()
    log=Log(args.output)
    try:
        log.append('acceptance_started',analysis=str(args.analysis.absolute()),analysis_sha256=args.analysis_sha256)
        report,summary,inputs,frame,resources=accept(args.analysis,args.analysis_sha256,args.controls,args.controls_sha256,args.fictional)
        write(log.root/'ROOT-ACCEPTANCE.json',report);write(log.root/'RESULTS.md',render(report,summary,inputs,resources));write(log.root/'REPRODUCE.md',reproduce(report,frame))
        log.append('acceptance_completed',report_sha256=sha(raw(log.root/'ROOT-ACCEPTANCE.json')));log.close()
        write(log.root/'RECEIPT.json',dict(status='complete',files=inventory(log.root)))
        print(json.dumps(dict(status='PASS',purpose=report['purpose'],output=str(log.root),receipt_sha256=sha(raw(log.root/'RECEIPT.json')),questions=report['questions'])))
    except BaseException as error:
        failure=dict(error_type=type(error).__name__,automatic_retry=False)
        try:log.append('acceptance_failed',**failure);write(log.root/'FAILURE.json',failure)
        except BaseException:pass
        raise
    finally:log.close()


if __name__=='__main__':main()
