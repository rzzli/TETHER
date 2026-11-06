"""Independent scripted-runtime joins; never imports the producer or Inspect.

This reconstructs the expressly bounded live witnesses. Full therapeutic policy
coverage remains the separate frozen archive suite, not an inferred guarantee.
"""
from pathlib import Path
import math
import reconstruct as b

USAGE=('input_tokens','output_tokens','cost_usd')


def usage(value):
    b.require(set(value)==set(USAGE),'Runtime usage schema differs')
    for key in USAGE:
        number=value[key]
        b.require(type(number) in ((int,float) if key=='cost_usd' else (int,))
                  and math.isfinite(number) and number>=0,'Runtime usage scalar differs')
    return dict(value)


def zero():return {'input_tokens':0,'output_tokens':0,'cost_usd':0.0}


def add(left,right):return {key:left[key]+right[key] for key in USAGE}


def reconcile(events,result,budget):
    """Independent ordered accounting, one-use dispatch and journal/ledger joins."""
    tickets={};settled=set();entered=set();dispatched=set();claims=[]
    measured=zero();estimated=zero();stopped=False
    for event in events:
        kind=event['event'];detail=event['details']
        if kind=='attempt_reserved':
            ident=detail['attempt'];quote=usage(detail['quote'])
            b.require(type(ident) is int and ident==len(tickets) and set(tickets)==settled and not stopped,'Overlapping/repeated/post-failure reservation')
            b.require(detail['request_sha256']==b.fingerprint(detail['request']),'Reserved request hash differs')
            prospective=add(add(measured,estimated),quote)
            b.require(len(tickets)<budget['max_calls'] and all(prospective[k]<=budget['max_'+k] for k in USAGE),'Unreservable runtime attempt')
            tickets[ident]=detail
        elif kind=='provider_entered':
            ident=detail['attempt']
            b.require(ident in tickets and ident not in entered and ident not in settled and detail['entry']==1,'Provider entry repeats or lacks reservation')
            entered.add(ident)
        elif kind=='provider_dispatched':
            ident=detail['attempt']
            b.require(ident in entered and ident not in dispatched and ident not in settled,'Provider dispatch order differs')
            ticket=tickets[ident]
            b.require(detail['request_sha256']==ticket['request_sha256'] and detail['payload_sha256']==b.fingerprint(detail['payload']),'Provider request/payload hash differs')
            expected={'messages':[{'role':'user','content':b.canonical(ticket['request']).decode()}],'tools':[],
                'configuration':{'temperature':0.0,'max_retries':0,'cache':False,'max_connections':1,
                                 'adaptive_connections':False,'max_tokens':ticket['quote']['output_tokens']}}
            b.require(b.canonical(detail['payload'])==b.canonical(expected),'Effective scripted provider payload differs')
            dispatched.add(ident)
        elif kind=='attempt_accounted':
            ident=detail['attempt'];actual=usage(detail['usage'])
            b.require(ident in tickets and ident not in settled and detail['request_sha256']==tickets[ident]['request_sha256'],'Unmatched/repeated accounting')
            quote=tickets[ident]['quote'];breach=any(actual[k]>quote[k] for k in USAGE)
            if detail['kind']=='measured':
                b.require(ident in dispatched,'Measured usage lacks provider dispatch')
                measured=add(measured,actual)
            else:
                b.require(detail['kind']=='estimated' and actual==quote,'Unknown response must retain exact prior quote')
                estimated=add(estimated,actual);breach=False
            b.require(detail['quote_breach'] is breach,'Quote-breach classification differs')
            settled.add(ident)
            stopped=breach or detail['outcome']!='completed'
        elif kind=='claim_committed':
            b.require(set(tickets)==settled and not stopped,'Claim precedes accounting or follows failure')
            b.require(detail['admitted_fingerprint']==b.fingerprint(detail['evidence']),'Claim evidence fingerprint differs')
            claims.append(detail)
        elif kind in ('claim_commit_budget_stop','reservation_denied'):
            stopped=True
    b.require(set(tickets)==settled,'Finalized runtime retains unresolved calls')
    b.require(len({c['claim_id'] for c in claims})==len(claims),'Duplicate committed claim identity')
    ledger=[claim for commit in result['commits'] for claim in commit['claims']]
    b.require(b.canonical(ledger)==b.canonical(claims),'Journal/ledger claims differ')
    account=result['accounting'];total=add(measured,estimated)
    for key,expected in (('calls',len(tickets)),('measured_usage',measured),('estimated_usage',estimated),
                         ('usage',total),('outstanding_reservation',zero()),('conservative_upper_usage',total),('unresolved_calls',0)):
        b.require(account[key]==expected,'Final runtime accounting differs: '+key)
    b.require(result['provider_entries']==len(entered) and result['provider_dispatches']==len(dispatched),'Provider event counts differ')
    return {'calls':len(tickets),'provider_entries':len(entered),'provider_dispatches':len(dispatched),
            'usage':total,'measured_usage':measured,'estimated_usage':estimated,'committed_claims':len(claims)}


def context_sources(row,record_root,events,result):
    admitted=[event['details'] for event in events if event['event']=='source_admitted']
    if not admitted:
        b.require(result['context_sha256'] is None and not result['commits'],'Claim/context exists without source admission')
        return {'source_files':0,'source_rows':0,'claims_joined':0}
    b.require(len(admitted)==1,'Repeated source admission')
    report=b.load(record_root/'context.json',admitted[0]['context'])
    b.require(b.fingerprint(report)==admitted[0]['context_sha256']==result['context_sha256'],'Source context hash differs')
    source=row['input'];root=Path(source['bundle_root'])
    descriptor=b.load(b.inside(root,source['descriptor']['path']),source['descriptor'])
    case=b.load(b.inside(root,descriptor['paths']['case']))
    snapshot_path=b.inside(root,descriptor['paths']['snapshot']);snapshot=b.load(snapshot_path)
    b.require(report['case']==case and report['snapshot']==snapshot and report['descriptor_sha256']==source['descriptor']['sha256'],'Context/original input differs')
    scorer=b.load(b.inside(root,descriptor['paths']['scorer'])) if 'scorer' in descriptor['paths'] else None
    b.require(report['scorer_sha256']==b.fingerprint(scorer),'Scorer source identity differs')
    nodes={node['source_id']:node for node in snapshot['sources']}
    b.require(len(nodes)==len(snapshot['sources']),'Duplicate original lineage node')
    parents=set()
    def ancestors(key,active=()):
        b.require(key in nodes and key not in active,'Missing/cyclic original lineage node')
        parents.add(key)
        for parent in nodes[key]['parents']:ancestors(parent,active+(key,))
    for artifact in snapshot['artifacts']:
        for key in artifact['input_refs']:ancestors(key)
    proof_ids=[proof['artifact_id'] for proof in report['source_proofs']]
    b.require(len(proof_ids)==len(set(proof_ids)) and set(proof_ids)==parents|{a['artifact_id'] for a in snapshot['artifacts']},
              'Source proof set omits or adds a packet/eligible ancestor')
    originals_by_id={**nodes,**{artifact['artifact_id']:artifact for artifact in snapshot['artifacts']}}
    b.require(snapshot.get('raw_root') is None,'Runtime reconstruction only qualified for declared local fictional roots')
    for proof in report['source_proofs']:
        original=originals_by_id[proof['artifact_id']]
        b.require(b.safe(proof['path'])==b.inside(snapshot_path.parent,original['path'])
                  and proof['sha256']==original['sha256'],'Source proof differs from original lineage identity')
        b.read(proof['path'],proof['sha256'])
        if original.get('receipt_path'):
            b.require(b.safe(proof['receipt_path'])==b.inside(snapshot_path.parent,original['receipt_path'])
                      and proof['receipt_sha256']==original['receipt_sha256'],'Source receipt identity differs')
            b.read(proof['receipt_path'],proof['receipt_sha256'])
    originals={}
    for artifact in snapshot['artifacts']:
        packet=b.load(b.inside(snapshot_path.parent,artifact['path']),artifact['sha256'])
        citation={key:artifact[key] for key in ('artifact_id','dataset_id','release_id','source_url')}
        citation['artifact_sha256']=artifact['sha256']
        for observation in packet['observations']:
            ident=observation['observation_id'];b.require(ident not in originals,'Duplicate original observation')
            originals[ident]={'observation':observation,'citation':citation}
    for ident,pin in report['admitted_fingerprints'].items():
        b.require(ident in originals and b.fingerprint(originals[ident])==pin,'Admitted original row fingerprint differs')
    count=0
    reservations=[e['details'] for e in events if e['event']=='attempt_reserved']
    b.require(all(ticket['request']['context_sha256']==result['context_sha256'] for ticket in reservations),'Request/source context hash differs')
    for commit in result['commits']:
        ids=[claim['evidence']['observation']['observation_id'] for claim in commit['claims']]
        b.require(len(commit['reviewed_ids'])==len(set(commit['reviewed_ids'])),'Duplicate reviewed selection')
        b.require(ids==commit['reviewed_ids'][:len(ids)],'Claims differ from reviewed prefix')
        if len(ids)!=len(commit['reviewed_ids']):
            b.require(commit['status']=='budget_exhausted' and commit['prediction']['probability'] is None
                      and commit['prediction']['reason']=='run_incomplete','Missing explicit commit-prefix abstention')
        for claim in commit['claims']:
            grounded=claim['evidence'];obs=grounded['observation'];ident=obs['observation_id']
            b.require(grounded==originals[ident] and claim['admitted_fingerprint']==report['admitted_fingerprints'][ident],'Committed claim differs from original source row')
            b.require(claim['claim_id']=='claim-'+b.fingerprint({'case':case['case_id'],'evidence':grounded})[:20]
                      and claim['extraction_mode']=='verbatim_source_selection','Canonical claim identity differs')
            b.require(obs['status']=='observed' and obs['category']==claim['specialist']
                      and obs['target_id']==case['hypothesis']['target_id'] and obs['indication_id']==case['hypothesis']['indication_id'],'Claim case/category capability differs')
            if obs['program_id'] is not None:
                b.require(case['program'] is not None and case['program']['mapping_confidence']>0
                          and obs['program_id']==case['program']['program_id'],'Claim program capability differs')
            b.require(any(ident in ticket['request']['offered_observation_ids'] and ticket['request']['category']==claim['specialist'] for ticket in reservations),'Claim not offered to dispatched specialist')
            count+=1
    semantic_checks=[]
    if case.get('schema_version')==2:
        from fixture_semantics import verify
        for commit in result['commits']:
            semantic_checks.append(verify(case,snapshot['profile'],scorer,commit))
    return {'source_files':len(report['source_proofs']),'source_rows':len(originals),'claims_joined':count,
            'feature_prediction_checks':semantic_checks,
            'scope':'Exact original row/claim joins and declared synthetic fixture arithmetic; general eligibility algorithm not re-executed'}


def runtime_record(row,root,receipt_sha256,native=None,*,native_header=None):
    root=Path(root);record=b.sealed_record(root,receipt_sha256,row);result=record['result'];events=record['events']
    b.require(result['control_id']==row['id'],'Runtime record identity differs')
    summary=reconcile(events,result,row['budget'])
    source=context_sources(row,root,events,result)
    responses={};response_pins={};qualified_reviews=[]
    tickets={e['details']['attempt']:e['details'] for e in events if e['event']=='attempt_reserved'}
    for event in events:
        detail=event['details']
        if event['event']=='native_response':
            attempt=detail['attempt'];b.require(attempt not in responses,'Duplicate native response')
            responses[attempt]=b.load(root/f'response-{attempt:03d}.json',detail['response'])
            response_pins[attempt]=detail['response']
            response=responses[attempt]
            b.require(response['completion']==row['steps'][attempt]['script']['content'],'Captured response differs from frozen scripted output')
            b.require(len(response['choices'])==1 and response['choices'][0]['message']['content']==response['completion'],
                      'Captured native message/completion differs')
        if event['event']=='attempt_accounted' and detail['kind']=='measured':
            response=responses.get(detail['attempt']);b.require(response is not None,'Measured accounting lacks captured native response')
            b.require(detail['response_sha256']==response_pins[detail['attempt']]['sha256'],'Accounting bound to another response')
            b.require(usage({k:response['usage']['total_cost' if k=='cost_usd' else k] for k in USAGE})==detail['usage'],'Measured/native response usage differs')
            b.require(response['usage']['total_tokens']==detail['usage']['input_tokens']+detail['usage']['output_tokens'],'Native token total differs')
            choice=b.parse(response['completion'].encode())
            b.require(set(choice)=={'observation_ids'} and type(choice['observation_ids']) is list
                      and len(choice['observation_ids'])==len(set(choice['observation_ids'])),'Measured response not structurally qualified')
            b.require(set(choice['observation_ids'])<=set(tickets[detail['attempt']]['request']['offered_observation_ids']),
                      'Measured response selects outside the request')
            if not detail['quote_breach']:qualified_reviews.append(choice['observation_ids'])
            before=[e for e in events if e['event']=='inspect_before_model' and e['details']['identity']['attempt']==detail['attempt']]
            used=[e for e in events if e['event']=='inspect_model_usage' and e['details']['identity']['attempt']==detail['attempt']]
            b.require(len(before)==len(used)==1,'Qualified response lacks required hooks')
            b.require(before[0]['details']['identity']==used[0]['details']['identity'] and used[0]['details']['retries']==0,
                      'Hook invocation identity/retry differs')
            hook_usage=used[0]['details']['usage']
            b.require(all(hook_usage.get(key)==response['usage'].get(key) for key in ('input_tokens','output_tokens','total_tokens','total_cost')),
                      'Hook usage contradicts captured response')
    b.require([commit['reviewed_ids'] for commit in result['commits']]==qualified_reviews[:len(result['commits'])],
              'Committed review differs from native selected IDs')
    if result['status'] in ('completed','budget_exhausted'):
        b.require(len(result['commits'])==len(qualified_reviews),'Qualified response has no commit outcome')
    if native is not None:
        b.require(native['id']==row['id'] and native['epoch']==1 and native['target']==''
                  and native['input']==b.canonical(row['input']).decode() and not native.get('error_retries'),'Native runtime request/isolation differs')
        if result['last_response_content'] is not None:
            b.require(native['output']['completion']==result['last_response_content'],'Native runtime candidate differs')
        for event in events:
            if event['event'] in ('inspect_before_model','inspect_model_usage'):
                identity=event['details']['identity']
                b.require(identity['control_id']==row['id'] and identity['epoch']==native['epoch']
                          and identity['native_sample_uuid']==native['uuid'],'Hook sample/epoch identity differs')
                if native_header is not None:
                    b.require(identity['run_id']==native_header['eval']['run_id']
                              and identity['eval_id']==native_header['eval']['eval_id']
                              and identity['task_name']==native_header['eval']['task'],'Hook run/eval/task identity differs')
                b.require(identity['attempt'] in tickets,'Hook has no corresponding reserved attempt')
        model_events=[event for event in native.get('events',[]) if event['event']=='model']
        known_native={key:sum(response.get('usage',{}).get(key,0) for response in responses.values()) for key in ('input_tokens','output_tokens','total_tokens')}
        observed={key:sum(value.get(key,0) for value in native.get('model_usage',{}).values()) for key in known_native}
        event_usage={key:sum((event.get('output',{}).get('usage') or {}).get(key,0) for event in model_events) for key in known_native}
        b.require(observed==event_usage,'Native sample aggregate differs from its model-event usage')
        for key in observed:b.require(type(observed[key]) is int and observed[key]>=0,'Native usage count invalid')
        # Failed/cancelled calls may have native usage but no returned captured
        # response. These are not fabricated zeros or forced into measured policy.
        b.require(all(observed[key]>=known_native[key] for key in observed),'Native aggregate usage smaller than captured responses')
        summary['native_reported_usage']=observed
        summary['captured_response_usage']=known_native
        summary['native_error']=bool(native.get('error'))
    return {'control_id':row['id'],'status':result['status'],'accounting':summary,'sources':source,
            'result':result,'events':events}


def reconstruct_ordinary(preparation_path,preparation_sha256,worker_result_path,worker_result_sha256):
    """Read the separately frozen ordinary-witness recipe and sealed worker result."""
    preparation_path=Path(preparation_path)
    prepared=b.load(preparation_path,preparation_sha256);root=preparation_path.parent
    for name,pin in prepared['input_inventory'].items():b.read(b.inside(root,name),pin)
    recipe_pin=prepared['ordinary_recipe'];recipe=b.load(recipe_pin['path'],recipe_pin)
    rows=b.load(prepared['ordinary']['rows']['path'],prepared['ordinary']['rows'])
    b.require(recipe['rows']==rows and len(rows)==prepared['ordinary']['scheduled'],'Ordinary recipe/input schedule differs')
    oracle=b.load(prepared['ordinary']['oracle']['path'],prepared['ordinary']['oracle'])
    b.require(recipe['oracle_path']==prepared['ordinary']['oracle']['path']
              and recipe['oracle_proof']=={k:prepared['ordinary']['oracle'][k] for k in ('sha256','bytes')},'Ordinary oracle binding differs')
    worker=b.load(worker_result_path,worker_result_sha256)
    b.require(worker['recipe_sha256']==recipe_pin['sha256'] and worker['scheduled']==[row['id'] for row in rows]
              and worker['provider_cost_usd']==0 and worker['automatic_retry'] is False
              and not worker['scientific_inference'] and not worker['network']['blocked'],'Witness worker scope differs')
    native_pin=worker['native_log'];b.read(native_pin['path'],native_pin)
    native=b.native_log(native_pin['path']);byid={sample['id']:sample for sample in native['samples']}
    reports={sample['id']:sample for sample in worker['samples']}
    expected={item['control_id']:item['fields'] for item in oracle['cases']}
    ids=[row['id'] for row in rows]
    b.require(len(reports)==len(worker['samples']) and set(reports)<=set(ids) and set(byid)<=set(ids)
              and set(expected)==set(ids),'Native/worker/oracle schedule identity differs')
    summaries=[]
    for row in rows:
        ident=row['id'];summary=reports.get(ident);sample=byid.get(ident)
        if summary is None or sample is None or summary['record'] is None:
            summaries.append({'control_id':ident,'status':'missing','expected_fields_match':False});continue
        record=summary['record'];case_path=Path(recipe['output_root'])/ident
        b.require(b.safe(record['path'])==b.safe(case_path),'Witness case path differs from scheduled output')
        checked=runtime_record(row,case_path,record['receipt']['sha256'],sample,native_header=native['header'])
        misses=[]
        for field,value in expected[ident].items():
            actual=checked['result']
            try:
                for part in field.split('.'):actual=actual[int(part)] if isinstance(actual,list) else actual[part]
            except (KeyError,IndexError,ValueError,TypeError):actual=b.MISSING
            if not b.same(actual,value):misses.append(field)
        native_error=bool(sample.get('error'))
        b.require(summary['native_error'] is native_error and summary['epoch']==sample['epoch'],'Native worker summary differs')
        scores=sample.get('scores') or {}
        b.require({key:score['value'] for key,score in scores.items()}==summary['native_scores'],'Native score summary differs')
        if checked['status'] in ('error','timeout','interrupted'):
            b.require(native_error and not scores,'Failed runtime sample was scored as normal completion')
        else:
            b.require(not native_error and len(scores)==1,'Completed runtime sample lacks native scoring')
            b.require(next(iter(scores.values()))['value']==('I' if misses else 'C'),'Native witness score contradicts expected fields')
        summaries.append({key:checked[key] for key in ('control_id','status','accounting','sources')}|
                         {'expected_fields_match':not misses,'expected_field_mismatches':misses,'native_error':native_error})
    known={key:sum(value.get(key,0) for sample in native['samples'] for value in sample.get('model_usage',{}).values())
           for key in ('input_tokens','output_tokens','total_tokens')}
    declared={key:sum(value.get(key,0) for value in worker['native_usage'].values()) for key in known}
    b.require(known==declared,'Worker/native aggregate usage differs')
    matched=sum(item['expected_fields_match'] for item in summaries)
    return {'schema_version':1,'status':'PASS' if matched==len(rows) else 'FAIL','scheduled':len(rows),'expected_fields_matched':matched,
            'preparation_sha256':preparation_sha256,'worker_result_sha256':worker_result_sha256,'native_log_sha256':native_pin['sha256'],
            'calls':sum(item.get('accounting',{}).get('calls',0) for item in summaries),
            'provider_dispatches':sum(item.get('accounting',{}).get('provider_dispatches',0) for item in summaries),
            'native_reported_usage':known,'cases':summaries,'provider_cost_usd':0,'automatic_redispatch':False,
            'limitations':['Finite scripted ordinary controls; process interruption/concurrency are separate.',
                          'Original source rows/accounting and declared synthetic fixture features/contributions are rebuilt; general therapeutic eligibility/scoring is not reimplemented.',
                          'Native error samples remain on the schedule even though Inspect does not score them.']}
