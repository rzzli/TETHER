"""Final independent operational audit; no production helpers, answers or dispatch.

The sibling v1 helper is hash-pinned and reused unchanged. This audit reconstructs
declared operations and bytes; it is not OS sandbox attestation or native scoring.
"""
import argparse
import base64
from collections import Counter
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HELPER_SHA='700ab30f03c9c61f7c8dc4dd7b39c75bb956de350d2ec10f9314025c52e5b392'
helper=Path(__file__).with_name('audit.py')
if hashlib.sha256(helper.read_bytes()).hexdigest()!=HELPER_SHA:raise ValueError('Independent v1 helper changed')
spec=importlib.util.spec_from_file_location('operational_audit_v1',helper)
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
need=A.need
BODY_FIELDS=('known_response_body_bytes','unknown_transfer_upper_bytes','safety_accounted_bytes','selected_text_bytes')
COLLECTION_OMIT={'journal.jsonl','manifest.json','SEALED.json','COMPLETE.json','PARTIAL.json','FAILED.json'}


def anchored(path,expected):
    raw=A.read(path);need(A.sha(raw)==expected,'External anchor mismatch: '+str(path));return A.parse(raw)


def inventory(root,declared,omit):
    root=A.no_links(root);found={}
    for path in sorted(root.rglob('*')):
        A.no_links(path)
        if not path.is_file():continue
        relative=path.relative_to(root).as_posix()
        if relative in omit:continue
        need(relative in declared,'Undeclared retained output: '+relative)
        raw=A.read_proof(root,{'path':relative,**declared[relative]})
        found[relative]=len(raw)
    need(set(found)==set(declared),'Declared output missing from exact inventory')
    return sum(found.values())


def collection_totals(manifest,schedule,maximum):
    cases=manifest['cases'];need(manifest['schedule']==schedule and len(cases)==len(schedule),'Incomplete final source schedule')
    states=('completed','failed','interrupted','unexecuted');counts=Counter();amounts=dict.fromkeys(BODY_FIELDS,0)
    with_sources=without_sources=0;stopped=False
    for ordinal,case in enumerate(cases):
        need(case['ordinal']==ordinal and case['id']==schedule[ordinal] and case['status'] in states,'Final source case identity differs')
        need(A.timestamp(case['sealed_at_utc'])<=A.timestamp(manifest['cutoff']),'Availability cutoff precedes terminal source')
        status=case['status'];amount=case['byte_accounting'];counts[status]+=1
        if stopped:need(status=='unexecuted','Source collection resumed after failure')
        if status!='completed':
            stopped=True;need(case.get('selected') is None and case.get('task_sources') is None and case['coverage'] is None,'Failed source grants passages')
            expected=dict.fromkeys(BODY_FIELDS,0)
            if status=='unexecuted':expected['basis']='no_source_dispatch'
            else:expected.update(unknown_transfer_upper_bytes=maximum,safety_accounted_bytes=maximum,
                basis='conservative_whole_case_reservation_until_source_seal')
            need(amount==expected,'Incomplete source reservation is undercharged or mislabeled')
        else:
            need(amount['basis']=='verified_retrieval_and_passage_outputs','Completed source accounting is unverified')
            articles=case['coverage']['retained_articles'];with_sources+=articles>0;without_sources+=articles==0
        for key in BODY_FIELDS:
            need(type(amount[key]) is int and amount[key]>=0,'Invalid source byte count');amounts[key]+=amount[key]
        need(amount['safety_accounted_bytes']==amount['known_response_body_bytes']+amount['unknown_transfer_upper_bytes']<=maximum,
             'Source total is inconsistent or exceeds bound')
    expected={'scheduled':len(schedule),'counts':{state:counts[state] for state in states},**amounts,
        'cases_with_sources':with_sources,'completed_without_sources':without_sources}
    need(expected==manifest['totals'],'Final source aggregate differs from all cases')
    complete=counts['completed']==len(schedule) and manifest['fatal'] is None
    need(manifest['status']==('completed' if complete else 'partial'),'False final source completion')
    return expected


def accounting_join(events,tokenizer_requested,declared):
    rebuilt=A.study_accounting(events,tokenizer_requested)
    need(A.canonical(rebuilt)==A.canonical(declared),'Case accounting differs from durable journal')
    return rebuilt


def candidate_join(root,case,query):
    row=case['disposition'];artifacts=case['artifacts']
    need(set(row)=={'id','producer_status','check_status','prediction','reason'} and row['id']==query['id'],'Disposition identity/fields differ')
    statuses={'produced','parse_failure','timeout','error','interrupted','unexecuted','input_unavailable'}
    need(row['producer_status'] in statuses and row['check_status'] in {'accepted','rejected','error','not_run'},'Unknown disposition status')
    if row['producer_status']!='produced':
        need(row['prediction'] is None and row['check_status']=='not_run' and bool(row['reason']),'Operational failure promoted to native answer')
        return False
    required={'candidate','session_response','request','payload','context','sources'}
    need(required<=set(artifacts),'Produced candidate lacks original proof')
    value={key:A.parse(A.read_proof(root,artifacts[key])) for key in required}
    candidate=value['candidate'];request=value['request'];context=value['context'];sources=value['sources']
    need(candidate==value['session_response']==row['prediction'],'Raw/checked candidate identity differs')
    need(set(candidate)=={'answer_index','evidence_ids'} and type(candidate['answer_index']) is int
         and 0<=candidate['answer_index']<len(query['choices']) and isinstance(candidate['evidence_ids'],list),'Invalid native candidate')
    citations=candidate['evidence_ids'];need(all(isinstance(x,str) for x in citations) and len(set(citations))==len(citations),'Invalid duplicate citation')
    need(all(set(source)=={'source_id','sha256','text'} and A.sha(source['text'].encode())==source['sha256'] for source in sources),'Offered source bytes differ')
    ids=[source['source_id'] for source in sources];need(len(set(ids))==len(ids) and set(citations)<=set(ids),'Unknown/duplicate offered source')
    fingerprint=lambda value:A.sha(A.canonical(value))
    need(request['query']==query and request['sources']==sources and request['payload_sha256']==fingerprint(value['payload'])
         and context['task_id']==query['id'] and context['request_sha256']==fingerprint(request)
         and context['query_sha256']==fingerprint(query) and context['sources_sha256']==fingerprint(sources),'Request/source/context binding differs')
    if row['check_status'] in ('accepted','rejected'):
        decision=A.parse(A.read_proof(root,artifacts['decision']))
        need(decision['accepted'] is (row['check_status']=='accepted') and decision['reason']==row['reason']
             and decision['prediction']==candidate and decision['request_sha256']==fingerprint(request)
             and decision['context_sha256']==fingerprint(context) and decision['semantic_support']=='unevaluated','Policy disposition/candidate join differs')
        unsure=[i for i,text in enumerate(query['choices']) if text[4:]=='Insufficient information to answer the question']
        need(len(unsure)==1,'Visible refusal choice is ambiguous')
        backed=candidate['answer_index']==unsure[0] or bool(citations)
        need(decision['accepted'] is backed,'Source-backed admission contradicts offered evidence')
    else:need(row['check_status']=='error' and bool(row['reason']),'Produced result has no accounted policy decision')
    return True


def generation_totals(index,schedule,declared):
    need(len(index)==len(schedule) and all(row['ordinal']==i and row['id']==schedule[i] for i,row in enumerate(index)),
         'Generation omitted or reordered scheduled cases')
    result={'scheduled':len(schedule),'generation_attempts':0,'tokenizer_attempts':0,'unresolved_generation':0,
        'measured_usage':dict(A.ZERO),'estimated_usage':dict(A.ZERO),
        'producer_statuses':dict(Counter(row['disposition']['producer_status'] for row in index)),
        'check_statuses':dict(Counter(row['disposition']['check_status'] for row in index))}
    for row in index:
        amount=row['accounting']
        for key in ('generation_attempts','tokenizer_attempts','unresolved_generation'):result[key]+=amount[key]
        for basis in ('measured_usage','estimated_usage'):
            for key,value in A.usage(amount[basis]).items():result[basis][key]+=value
    need(result==declared,'Generation totals differ from every scheduled case')
    return result


def cleanup_join(manifest,terminal,index):
    normal=bool(terminal and terminal['cleanup']=='normal_verified' and terminal['server_terminal']['server_stopped'] is True)
    need(manifest['cleanup']==('normal_verified' if normal else 'unverified_or_job_forced'),'Cleanup claim differs from owned-server terminal')
    complete=normal and terminal['status']=='completed' and manifest['failure_reason'] is None and all(row['terminal_basis']=='worker_terminal' for row in index)
    need(manifest['status']==('completed' if complete else 'partial'),'Generation completion contradicts cleanup/case terminals')


def supervision(report,root,prefix,seconds,cap):
    need(report['termination_reason']=='exited' and report['process_started'] is True and report['process_reaped'] is True
         and report['pipe_eof']=={'stdout':True,'stderr':True} and report['cleanup_errors']==[]
         and report['observed_counts_are_lower_bounds'] is False,'Successful process supervision is incomplete')
    need(report['limits']['timeout_seconds']==seconds and report['limits']['max_output_bytes']==cap,'Supervisor limits differ from recipe')
    for key in ('execution_elapsed_seconds','total_elapsed_seconds'):
        need(type(report[key]) in (int,float) and math.isfinite(report[key]) and report[key]>=0,'Invalid supervisor duration')
    need(report['execution_elapsed_seconds']<seconds and report['total_elapsed_seconds']>=report['execution_elapsed_seconds'],'Successful process exceeded deadline')
    total=0
    for stream in ('stdout','stderr'):
        count=len(A.read(Path(root)/(prefix+'.'+stream)));total+=count
        need(report['retained_'+stream+'_bytes']==report['observed_'+stream+'_bytes']==count,'Supervisor stream bytes differ')
    need(total<=cap,'Supervisor output exceeds cap')


def final_collection(freeze_path,freeze_sha,manifest_sha):
    # Reuses independent v1 original-body, receipt, journal, passage/locator checks.
    report=A.audit_collection(freeze_path,freeze_sha,expected_manifest_sha=manifest_sha)
    frozen=anchored(freeze_path,freeze_sha);root=Path(frozen['collection_output']);manifest=anchored(root/'manifest.json',manifest_sha)
    recipe=anchored(frozen['collection_recipe']['path'],frozen['collection_recipe']['sha256'])
    policy,seconds=A.recipe_policy(recipe)
    config=A.parse(A.read_proof(root,manifest['configuration']))
    need(manifest['policy']==policy and manifest['stage_seconds']==seconds and manifest['code_pins']==config['code_pins']
         and manifest['queries']==config['queries'],'Final source manifest differs from frozen configuration')
    totals=collection_totals(manifest,config['schedule'],policy['total_bytes'])
    output_bytes=inventory(root,manifest['outputs'],COLLECTION_OMIT)
    seal=A.parse(A.read(root/'SEALED.json'));flag='COMPLETE.json' if manifest['status']=='completed' else 'PARTIAL.json'
    need(A.parse(A.read(root/flag))==seal and not (root/('PARTIAL.json' if flag=='COMPLETE.json' else 'COMPLETE.json')).exists()
         and not (root/'FAILED.json').exists(),'Contradictory collection terminal flags')
    events=A.verify_chain(A.read(root/'journal.jsonl'));last=events[-1]['details']
    need(last['status']==manifest['status'] and last['scheduled']==199 and last['cutoff']==manifest['cutoff']
         and A.read_proof(root,last['manifest'])==A.read(root/'manifest.json'),'Final collection journal/manifest differs')
    control=Path(frozen['collection_control_output']);control_status=None
    if manifest['status']=='completed':
        need(A.read(control/'recipe.json')==A.read(frozen['collection_recipe']['path']),'Supervised collection recipe bytes differ')
        control_events=A.verify_chain(A.read(control/'journal.jsonl'));dispatch=[e['details'] for e in control_events if e['event']=='collection_child_dispatch']
        need(len(dispatch)==1 and dispatch[0]['recipe_sha256']==frozen['collection_recipe']['sha256'] and dispatch[0]['command']==recipe['command']
             and dispatch[0]['retries']==0,'Collection dispatch differs or repeated')
        control_status=A.parse(A.read(control/'COMPLETE.json'));supervised=A.parse(A.read(control/'SUPERVISION.json'))
        need(control_events[-1]['event']=='collection_child_completed' and control_events[-1]['details']==control_status
             and control_status['manifest_sha256']==manifest_sha and control_status['retries']==0 and supervised['returncode']==0
             and not (control/'FAILED.json').exists(),'Collection parent terminal contradicts child')
        supervision(supervised['supervision'],control,'child',recipe['parent_seconds'],8*1024**2)
    report.update(final_audit=True,limits=['Independent declared bytes, journals, timing and source locators; no native answers or semantic validation',
        'Body-byte totals exclude wire overhead; full process isolation is not independently attested'],
        all_case_totals=totals,exact_inventory_files=len(manifest['outputs']),inventory_product_bytes=output_bytes,control_completion=control_status)
    return report


def verify_session_bytes(root,case,events):
    artifacts=case['artifacts'];receipt=A.parse(A.read_proof(root,artifacts['session_receipt']))
    session=A.child(root,artifacts['session_receipt']['path']).parent
    expected={'request.json','payload.json','configuration.json','raw-response.bin','response.json','report.json','journal.jsonl'}
    need(set(receipt['outputs'])==expected,'Successful session proof set differs')
    raw={name:A.read_proof(session,{'path':name,**proof}) for name,proof in receipt['outputs'].items()}
    need(A.parse(raw['request.json'])==A.parse(A.read_proof(root,artifacts['request']))
         and A.parse(raw['payload.json'])==A.parse(A.read_proof(root,artifacts['payload'])),'Session dispatched different request/payload')
    wrapper=A.parse(raw['raw-response.bin']);body=base64.b64decode(wrapper['body_base64'],validate=True)
    request=A.parse(raw['request.json']);payload=A.parse(raw['payload.json']);body_value=A.parse(body)
    need(A.sha(body)==wrapper['body_sha256'] and wrapper['http_status']==200 and wrapper['complete'] is True
         and wrapper['request_sha256']==A.sha(A.canonical(request)) and wrapper['payload_sha256']==A.sha(A.canonical(payload))
         and body_value['prompt']==payload['prompt'] and A.parse(body_value['content'])==case['disposition']['prediction'],
         'Original native response differs from same candidate/request')
    report=A.parse(raw['report.json']);amount=case['accounting']
    native_usage={'input_tokens':body_value['tokens_evaluated'],'output_tokens':body_value['tokens_predicted'],'cost_usd':0.0}
    need(A.usage(native_usage)==amount['measured_usage']==report['measured_usage'] and report['estimated_usage']==amount['estimated_usage']==A.ZERO
         and report['calls']==amount['generation_attempts']==1,'Native response/report/journal usage differs')
    token=A.parse(A.read_proof(root,artifacts['tokenization']));token_body=A.read_proof(root,artifacts['tokenization_body'])
    need(base64.b64decode(token['body_base64'],validate=True)==token_body and A.sha(token_body)==token['body_sha256']
         and token['complete'] is True and token['http_status']==200 and token['payload_sha256']==wrapper['payload_sha256']
         and len(A.parse(token_body)['tokens'])==token['token_count']==native_usage['input_tokens'],'Tokenizer/native measured input usage differs')
    for event,name in (('study_response_captured','raw-response.bin'),('study_response_accepted','response.json'),('study_completed','report.json')):
        matches=[row['details'] for row in events if row['event']==event];need(len(matches)==1,'Missing/repeated successful session event')
        # Journal event schemas use semantic fingerprints for accepted response.
        expected_sha=A.sha(raw[name]) if name=='raw-response.bin' else A.sha(A.canonical(A.parse(raw[name])))
        keys=('content_sha256',) if name=='raw-response.bin' else ('response_sha256',) if name=='response.json' else ('report_sha256',)
        need(matches[0][keys[0]]==expected_sha,'Session journal/original output differs')


def generation_amendment(frozen,freeze_sha,amended):
    need(amended['schema_version']==1 and amended['kind']=='labbench_generation_freeze'
         and amended['original_freeze']['sha256']==freeze_sha,'Generation amendment has no original external anchor')
    for key in ('queries','configuration','generation_limits','alias','model_receipt','generation_output'):
        need(amended[key]==frozen[key],'Prospective amendment changed scientific configuration: '+key)
    need(amended['mode']=='benchmark' and amended['scheduled_count']==199,'Amendment changed population')
    old=frozen['code_pins'];new=amended['code_pins'];change=amended['change_control'];allowed='experiments/labbench/run.py'
    need(set(old)==set(new) and {key for key in old if old[key]!=new[key]}=={allowed}
         and change['changed_files']==[allowed] and change['previous_sha256']==old[allowed]
         and change['new_sha256']==new[allowed] and bool(change['reason']),'Undeclared generation source change')
    for field,digest in (('previous_source',old[allowed]),('new_source',new[allowed])):
        if field in change:
            proof=change[field];raw=A.read(proof['path'])
            need(A.sha(raw)==proof['sha256']==digest and len(raw)==proof['bytes'],'Archived changed source differs')
    return new


def final_generation(freeze_path,freeze_sha,collection_sha,sealed_sha,*,generation_freeze_path,generation_freeze_sha,collection_audit_path,collection_audit_sha):
    frozen=anchored(freeze_path,freeze_sha);root=Path(frozen['generation_output'])
    amended=anchored(generation_freeze_path,generation_freeze_sha)
    expected_pins=generation_amendment(frozen,freeze_sha,amended)
    need(Path(amended['original_freeze']['path'])==Path(freeze_path),'Amendment original freeze path differs')
    original_audit=anchored(collection_audit_path,collection_audit_sha)['collection']
    need(original_audit['status']=='PASS' and original_audit['final_audit'] is True and original_audit['freeze_sha256']==freeze_sha
         and original_audit['final_collection']['manifest_sha256']==collection_sha and original_audit['scheduled']==199
         and original_audit['terminal_cases_observed']==199 and original_audit['frozen_code_pins']==frozen['code_pins'],
         'Original source audit was not independently completed under acquisition freeze')
    collection_root=Path(frozen['collection_output']);collection=anchored(collection_root/'manifest.json',collection_sha)
    need(amended['collection']['path']==frozen['collection_output'] and amended['collection']['manifest_sha256']==collection_sha
         and A.sha(A.read(collection_root/'SEALED.json'))==amended['collection']['seal_sha256'],'Amendment source manifest/seal differs')
    inventory(collection_root,collection['outputs'],COLLECTION_OMIT)
    seal=anchored(root/'SEALED.json',sealed_sha);manifest=anchored(root/'manifest.json',seal['manifest_sha256'])
    need(manifest['kind']==seal['kind']=='labbench_generation' and manifest['status']==seal['status'],'Generation seal identity differs')
    output_bytes=inventory(root,seal['outputs'],{'SEALED.json'})
    recipe=A.parse(A.read_proof(root,manifest['recipe']));queries=A.parse(A.read_proof(root,manifest['queries']))
    need(manifest['queries']['sha256']==frozen['queries']['sha256'] and manifest['queries']['bytes']==frozen['queries']['bytes'], 'Frozen task view differs')
    schedule=[q['id'] for q in queries];need(len(schedule)==199 and len(set(schedule))==199 and schedule==manifest['schedule'],'Generation schedule differs')
    need(all(set(q)=={'id','question','choices'} for q in queries),'Oracle fields in generation tasks')
    for key,expected in [('collection',{'path':frozen['collection_output'],'manifest_sha256':collection_sha}),('model_receipt',frozen['model_receipt']),
                         ('alias',frozen['alias']),('configuration',frozen['configuration']),('limits',frozen['generation_limits'])]:
        need(manifest[key]==recipe[key]==expected,'Frozen generation recipe mismatch: '+key)
    need(manifest['code_pins']==recipe['code_pins']==expected_pins and recipe['expected_count']==199
         and manifest['mode']==recipe['mode']=='benchmark','Generation code/population changed')
    for relative,digest in expected_pins.items():need(A.sha(A.read(A.child(A.ROOT,relative)))==digest,'Amended generation code changed')
    anchored(frozen['model_receipt']['path'],frozen['model_receipt']['sha256'])
    parent=A.verify_chain(A.read(root/'journal.jsonl'));need(parent[-1]['event']=='generation_sealed' and parent[-1]['sha256']==seal['journal_terminal_sha256'],'Generation journal incomplete')
    dispatched=[e['details'] for e in parent if e['event']=='generation_worker_dispatch']
    need(len(dispatched)==1 and dispatched[0]['recipe_sha256']==manifest['recipe']['sha256'],'Generation worker repeated or recipe changed')
    events=A.verify_chain(A.read(root/'worker/journal.jsonl'),allow_tail=manifest['status']=='partial')
    scheduled={};terminals={}
    for event in events:
        if event['event'] not in ('case_reserved','case_terminal','case_unexecuted'):continue
        detail=event['details'];ordinal=detail['ordinal']
        need(type(ordinal) is int and 0<=ordinal<199 and detail['id']==schedule[ordinal],'Worker journal identity differs')
        if event['event']=='case_terminal':
            need(scheduled.get(ordinal)=='case_reserved' and ordinal not in terminals,'Repeated/unreserved case terminal');terminals[ordinal]=detail
        else:need(ordinal not in scheduled,'Repeated case dispatch');scheduled[ordinal]=event['event']
    index=A.parse(A.read_proof(root,manifest['case_index']));rows=A.parse(A.read_proof(root,manifest['dispositions']))
    need(rows==[case['disposition'] for case in index],'Index/disposition candidate join differs')
    totals=generation_totals(index,schedule,manifest['totals']);paired=0
    for case,query,source in zip(index,queries,collection['cases']):
        ordinal=case['ordinal'];case_root=root/'worker/cases'/f'{ordinal:03d}'
        need(case['path']==f'worker/cases/{ordinal:03d}','Case path differs from frozen order')
        for proof in case['artifacts'].values():A.read_proof(root,proof)
        session_path=case_root/'session/journal.jsonl';session_events=A.verify_chain(A.read(session_path),allow_tail=True) if session_path.exists() else []
        accounting_join(session_events,(case_root/'tokenization/request.json').exists(),case['accounting'])
        need(not (case['accounting']['generation_attempts'] or case['accounting']['tokenizer_attempts']) or scheduled.get(ordinal)=='case_reserved','Unreserved model operation')
        if ordinal in terminals:
            status=anchored(case_root/'status.json',terminals[ordinal]['status_sha256'])
            need(status['disposition']==case['disposition'] and status['accounting']==case['accounting'] and status['resources']==case['resources']
                 and status['ordinal']==ordinal and status['id']==query['id'] and case['terminal_basis']=='worker_terminal','Case terminal/index differs')
        else:
            need(case['terminal_basis']=='parent_recovered_no_replay' and case['disposition']['producer_status']==('error' if scheduled.get(ordinal)=='case_reserved' else 'unexecuted'),
                 'Missing terminal promoted to produced result')
        is_produced=candidate_join(root,case,query);paired+=is_produced
        if is_produced:
            need(source['status']=='completed','Model consumed incomplete source grant')
            need(A.parse(A.read_proof(root,case['artifacts']['sources']))==A.parse(A.read_proof(Path(frozen['collection_output']),source['task_sources'])), 'Model consumed passages different from source grant')
            context=A.parse(A.read_proof(root,case['artifacts']['context']))
            need(A.timestamp(context['cutoff_utc'])==A.timestamp(collection['cutoff']) and context['retrieval_manifest_sha256']==source['retrieval']['manifest_sha256'], 'Captured source cutoff/root differs')
            verify_session_bytes(root,case,session_events)
    need(parent[-1]['details']['totals']==totals and parent[-1]['details']['manifest_sha256']==seal['manifest_sha256']
         and parent[-1]['details']['scheduled']==199 and parent[-1]['details']['status']==manifest['status'],'Parent final accounting differs')
    terminal=A.parse(A.read_proof(root,manifest['worker_terminal'])) if manifest['worker_terminal'] else None
    if terminal:need(terminal['journal_terminal_sha256']==events[-1]['sha256'] and events[-1]['event']=='worker_terminal'
                     and terminal['server_terminal']==events[-1]['details']['server_terminal'],'Worker cleanup terminal is not journal-bound')
    cleanup_join(manifest,terminal,index)
    flag='COMPLETE.json' if manifest['status']=='completed' else 'PARTIAL.json'
    need(A.parse(A.read(root/flag))=={'status':manifest['status'],'manifest_sha256':seal['manifest_sha256'],'cleanup':manifest['cleanup']}
         and not (root/('PARTIAL.json' if flag=='COMPLETE.json' else 'COMPLETE.json')).exists(),'Generation terminal marker differs')
    if manifest['status']=='completed':
        need(manifest['supervision']['returncode']==0 and not (root/'FAILURE.json').exists(),'Completed worker failed')
        supervision(manifest['supervision']['report'],root,'worker',manifest['limits']['stage_seconds'],manifest['limits']['process_output_bytes'])
    need(manifest['provider_cost_usd']==0 and manifest['automatic_retries'] is False and manifest['reference_access']=='not_performed'
         and manifest['answer_correctness']=='not_evaluated','Generation scope changed')
    return {'schema_version':1,'status':'PASS','scope':'independent generation operations and same-candidate identity; no native answers or scoring',
        'freeze_sha256':freeze_sha,'generation_freeze_sha256':generation_freeze_sha,'collection_audit_sha256':collection_audit_sha,
        'collection_manifest_sha256':collection_sha,'generation_sealed_sha256':sealed_sha,
        'generation_manifest_sha256':seal['manifest_sha256'],'generation_status':manifest['status'],'totals':totals,
        'paired_candidate_joins':paired,'inventory_product_bytes':output_bytes,'inventory_files':len(seal['outputs']),
        'cleanup':manifest['cleanup'],'reference_access':False,'native_scoring':False,
        'limitations':['Model/runtime receipt is anchored; multi-GB model assets are rehashed by production scorer separately',
            'Declared journals/resources are reconciled; OS isolation and biological entailment are not independently attested']}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',required=True);parser.add_argument('--freeze-sha256',required=True)
    parser.add_argument('--collection-manifest-sha256',required=True);parser.add_argument('--generation-sealed-sha256');parser.add_argument('--output',required=True)
    parser.add_argument('--generation-freeze');parser.add_argument('--generation-freeze-sha256')
    parser.add_argument('--collection-audit');parser.add_argument('--collection-audit-sha256')
    args=parser.parse_args();result={'checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'auditor_sha256':A.sha(A.read(__file__)),'helper_sha256':HELPER_SHA}
    if args.generation_sealed_sha256:
        need(all((args.generation_freeze,args.generation_freeze_sha256,args.collection_audit,args.collection_audit_sha256)),
             'Generation audit requires independently anchored amended freeze and original collection audit')
        result['collection']=anchored(args.collection_audit,args.collection_audit_sha256)['collection']
        result['generation']=final_generation(args.freeze,args.freeze_sha256,args.collection_manifest_sha256,args.generation_sealed_sha256,
            generation_freeze_path=args.generation_freeze,generation_freeze_sha=args.generation_freeze_sha256,
            collection_audit_path=args.collection_audit,collection_audit_sha=args.collection_audit_sha256)
    else:result['collection']=final_collection(args.freeze,args.freeze_sha256,args.collection_manifest_sha256)
    with Path(args.output).open('xb') as stream:stream.write(A.canonical(result)+b'\n')
    print(json.dumps({'status':'PASS','collection':result['collection']['final_collection'],'generation':result.get('generation',{}).get('totals')}))


if __name__=='__main__':main()
