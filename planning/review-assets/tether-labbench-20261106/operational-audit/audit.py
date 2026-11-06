"""Independent stdlib-only operational audit. Never imports experiment code.

No network/process dispatch, no benchmark references/provenance, no answer
scoring. Active collection reads only durable terminal cases from a captured
journal prefix. Every audit output is a new file; production paths are read-only.
"""
from collections import Counter
from datetime import datetime,timezone
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[4]
ZERO={'input_tokens':0,'output_tokens':0,'cost_usd':0.0}


def need(value,message):
    if not value:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def parse(raw):
    def pairs(items):
        result={}
        for key,value in items:
            need(key not in result,'Duplicate JSON key')
            result[key]=value
        return result
    def constant(value):raise ValueError('Nonfinite JSON constant')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)


def no_links(path):
    path=Path(path).absolute()
    for part in (*reversed(path.parents),path):
        info=part.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400,'Aliased audit input')
    return path


def child(root,relative):
    need(isinstance(relative,str) and relative and not relative.startswith(('/','\\')) and ':' not in relative,'Invalid relative proof path')
    parts=relative.replace('\\','/').split('/')
    need(all(part not in ('','.','..') for part in parts),'Unsafe relative proof path')
    root=no_links(root);path=no_links(root.joinpath(*parts))
    need(path.resolve().is_relative_to(root.resolve()),'Proof escapes root')
    return path


def read(path,cap=32*1024*1024,*,prefix=False):
    path=no_links(path);before=path.stat()
    need(stat.S_ISREG(before.st_mode) and before.st_size<=cap,'Audit input is not bounded regular file')
    with path.open('rb') as stream:
        raw=stream.read(before.st_size if prefix else cap+1)
        opened=os.fstat(stream.fileno())
    if not prefix:
        after=path.stat()
        identity=lambda value:(value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns)
        need(identity(before)==identity(opened)==identity(after) and len(raw)==before.st_size,'Audit input changed during capture')
    return raw


def read_proof(root,proof,cap=32*1024*1024):
    raw=read(child(root,proof['path']),cap)
    need(type(proof['bytes']) is int and len(raw)==proof['bytes'] and sha(raw)==proof['sha256'],'External byte proof differs')
    return raw


def timestamp(value):
    need(isinstance(value,str),'Missing UTC timestamp')
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    need(result.tzinfo is not None,'Naive timestamp')
    return result.astimezone(timezone.utc)


def argument(command,flag):
    need(isinstance(command,list) and all(isinstance(value,str) for value in command) and command.count(flag)==1,'Missing/duplicate frozen command flag')
    position=command.index(flag)
    need(position+1<len(command),'Command flag has no value')
    return command[position+1]


def recipe_policy(recipe):
    command=recipe['command']
    raw=read(argument(command,'--policy'))
    need(sha(raw)==argument(command,'--policy-sha256'),'Frozen policy file hash differs')
    seconds=float(argument(command,'--stage-seconds'))
    need(math.isfinite(seconds) and 0<seconds<=86400,'Invalid collection stage bound')
    return parse(raw),seconds


def verify_chain(raw,*,allow_tail=False):
    lines=raw.splitlines()
    if allow_tail and not raw.endswith(b'\n'):lines=lines[:-1]
    elif not raw.endswith(b'\n'):raise ValueError('Incomplete closed journal')
    result=[];previous=None
    for line in lines:
        row=parse(line);digest=row.pop('sha256')
        need(set(row)=={'sequence','event','details','previous_sha256'},'Unknown journal shape')
        need(type(row['sequence']) is int and row['sequence']==len(result) and row['previous_sha256']==previous
             and sha(canonical(row))==digest,'Journal chain mismatch')
        row['sha256']=digest;result.append(row);previous=digest
    need(result,'Empty journal')
    return result


def usage(value):
    need(set(value)==set(ZERO),'Usage fields differ')
    for key in ('input_tokens','output_tokens'):need(type(value[key]) is int and value[key]>=0,'Invalid token count')
    need(type(value['cost_usd']) in (int,float) and math.isfinite(value['cost_usd']) and value['cost_usd']==0,'Nonzero/invalid provider cost')
    return dict(value)


def study_accounting(events,tokenizer_requested):
    dispatch=[row['details'] for row in events if row['event']=='study_dispatch']
    accounts=[row['details'] for row in events if row['event']=='study_accounted']
    need(len(dispatch)<=1 and len(accounts)<=1 and (not accounts or dispatch),'Repeated or unreserved model accounting')
    result={'generation_attempts':int(bool(dispatch)),'tokenizer_attempts':int(tokenizer_requested),
        'measured_usage':dict(ZERO),'estimated_usage':dict(ZERO),'unresolved_generation':False,'basis':'no generation dispatch'}
    if not dispatch:return result
    reserved=usage(dispatch[0]['reserved'])
    if not accounts:
        result.update(estimated_usage=reserved,unresolved_generation=True,basis='durable dispatch without terminal accounting; conservative reservation')
    else:
        measured=usage(accounts[0]['usage']);basis=accounts[0]['basis']
        need(basis in ('adapter_reported','conservative_quote'),'Unknown charge basis')
        need(all(measured[key]<=reserved[key] for key in ZERO),'Usage exceeds reserved call budget')
        if basis=='conservative_quote':need(measured==reserved,'Conservative charge differs from reservation')
        result['measured_usage' if basis=='adapter_reported' else 'estimated_usage']=measured
        result['basis']=basis
    return result


def request_accounting(root,requests,events,policy):
    known=unknown=0;status_counts=Counter();seen_urls=set();latest=None
    starts=[row['details'] for row in events if row['event']=='retrieval_request_started']
    need(len(starts)==len(requests),'HTTP journal attempt count mismatch')
    kinds=Counter(row['kind'] for row in requests)
    need(kinds['search']<=policy['max_queries'] and kinds['fulltext']<=policy['max_articles'],'HTTP count cap exceeded')
    for index,row in enumerate(requests):
        key=f'{index:03d}'
        need(row['request_id']==key and row['url'] not in seen_urls,'Repeated or reordered HTTP request')
        seen_urls.add(row['url']);url=urlsplit(row['url'])
        need(url.scheme=='https' and url.netloc=='www.ebi.ac.uk' and not url.username and not url.password and not url.fragment,'Unapproved source origin')
        need(row['kind'] in ('search','fulltext'),'Unknown HTTP request kind')
        cap=policy['metadata_bytes' if row['kind']=='search' else 'article_bytes']
        reservation=min(cap,policy['total_bytes']-known-unknown)
        need(type(row['byte_reservation']) is int and row['byte_reservation']==reservation>0,'HTTP reservation differs')
        expected_start={name:row[name] for name in ('request_id','url','kind','byte_reservation')}|{'status':'started'}
        need(starts[index]==expected_start,'HTTP start journal differs')
        completed=[event['details'] for event in events if event['event']=='retrieval_request_completed' and event['details']['request_id']==key]
        failed=[event['details'] for event in events if event['event']=='retrieval_request_failed' and event['details']['request_id']==key]
        if row['status']=='completed':
            raw=read(child(root,row['body_path']),cap)
            need(sha(raw)==row['body_sha256'] and len(raw)==row['bytes']==row['accounted_bytes']<=reservation
                 and row['byte_accounting_basis']=='retained_response_body','HTTP retained bytes differ')
            receipt_raw=read(child(root,row['receipt_path']),65536)
            need(sha(receipt_raw)==row['receipt_sha256'],'HTTP receipt hash differs')
            receipt=parse(receipt_raw)
            need(receipt['status']=='completed' and receipt['sha256']==row['body_sha256']==receipt['release_id']
                 and receipt['dataset_id']=='labbench_retrieved_literature' and receipt['relative_path']==row['body_path']
                 and receipt['bytes']==len(raw) and receipt['url']==receipt['source_url']==row['url']
                 and receipt['http_status']==row['http_status'],'HTTP receipt/source binding differs')
            moment=timestamp(receipt['completed_at_utc']);latest=max(latest,moment) if latest else moment
            need(len(completed)==1 and completed[0]=={key:value for key,value in row.items() if key not in ('error_type','failure_cause')},'HTTP completion journal differs')
            known+=len(raw);status_counts[str(row['http_status'])]+=1
        else:
            need(row['status']=='failed' and not completed and row['accounted_bytes']==reservation
                 and row['byte_accounting_basis']=='conservative_unmeasured_reservation','Failed HTTP reservation differs')
            unknown+=reservation
        need((len(failed)==1 and failed[0]==row) if 'error_type' in row else not failed,'HTTP failure journal differs')
    return {'known_response_body_bytes':known,'unknown_transfer_upper_bytes':unknown,'safety_accounted_bytes':known+unknown,
        'request_count':len(requests),'http_status_counts':dict(status_counts),'latest_receipt_utc':latest.isoformat() if latest else None}


def completed_case(root,case,frozen_policy,code_pins):
    policy=case['effective_policy']
    for key,value in frozen_policy.items():
        if key in ('question_seconds','request_seconds'):need(0<policy[key]<=value,'Effective time limit increased')
        else:need(policy[key]==value,'Frozen retrieval policy changed')
    need(policy['request_seconds']<=policy['question_seconds'],'HTTP deadline exceeds case deadline')
    retrieval_root=child(root,case['retrieval']['path'])
    raw=read(retrieval_root/'manifest.json');manifest=parse(raw)
    need(sha(raw)==case['retrieval']['manifest_sha256'],'Case retrieval anchor mismatch')
    need(manifest['policy']==policy and manifest['retriever_sha256']==code_pins['retrieval.py'],'Retrieval method identity differs')
    journal_raw=read(retrieval_root/'journal.jsonl');events=verify_chain(journal_raw)
    need(parse(read(retrieval_root/'COMPLETE.json'))=={'manifest_sha256':sha(raw),'journal_sha256':sha(journal_raw)},'Retrieval completion bytes differ')
    need(events[-1]['event']=='build_completed' and events[-1]['details']['manifest_sha256']==sha(raw),'Retrieval journal not terminal')
    amounts=request_accounting(retrieval_root,manifest['requests'],events,policy)
    costs=manifest['costs']
    need(costs['downloaded_bytes']==amounts['known_response_body_bytes'] and costs['safety_accounted_bytes']==amounts['safety_accounted_bytes']
         and costs['unmeasured_transfer_upper_bytes']==amounts['unknown_transfer_upper_bytes'] and costs['provider_usd']==0 and costs['retries']==0,'Retained source totals differ')
    packet=parse(read_proof(root,case['selected']));sources=parse(read_proof(root,case['task_sources']))
    need(sources==packet['sources'] and len(sources)==len(packet['bindings'])<=policy['max_passages'],'Selected source interface differs')
    need(len({item['source_id'] for item in sources})==len(sources),'Duplicate selected identity')
    documents={row['source_id']:row for row in manifest['sources']}
    need(len(documents)==len(manifest['sources'])<=policy['max_articles'],'Duplicate/excess retained document')
    selected_bytes=0
    for item,binding in zip(sources,packet['bindings']):
        need(set(item)=={'source_id','sha256','text'} and binding['source_id']==item['source_id'],'Task source field/identity differs')
        raw_text=item['text'].encode();selected_bytes+=len(raw_text)
        need(sha(raw_text)==item['sha256'] and len(raw_text)<=policy['passage_bytes'],'Selected passage bytes differ')
        document=documents[binding['document_id']]
        spans={row['evidence_id']:row for row in document['spans']}
        need(len(spans)==len(document['spans']),'Duplicate extracted span identity')
        span=spans[binding['span_id']]
        need(sha(span['text'].encode())==span['text_sha256']==binding['parent_text_sha256']
             and binding['original_sha256']==document['original']['sha256'],'Selected passage parent differs')
        start,end=binding['character_start'],binding['character_end']
        need(type(start) is int and type(end) is int and 0<=start<end<=len(span['text']) and span['text'][start:end]==item['text'],'Selected character locator differs')
    need(selected_bytes==packet['coverage']['selected_text_bytes']<=policy['selected_bytes'],'Selected text aggregate differs')
    expected={'known_response_body_bytes':amounts['known_response_body_bytes'],'unknown_transfer_upper_bytes':amounts['unknown_transfer_upper_bytes'],
        'safety_accounted_bytes':amounts['safety_accounted_bytes'],'selected_text_bytes':selected_bytes,'basis':'verified_retrieval_and_passage_outputs'}
    need(case['byte_accounting']==expected,'Case byte accounting differs from original responses')
    need(case['coverage']['retained_articles']==len(documents) and case['coverage']['selected_passages']==len(sources)
         and case['coverage']['absence_of_evidence_claim'] is False and manifest['coverage']['absence_of_evidence_claim'] is False,'Source coverage declaration differs')
    if amounts['latest_receipt_utc']:need(timestamp(amounts['latest_receipt_utc'])<=timestamp(case['sealed_at_utc']),'Case predates source receipt')
    return {'id':case['id'],'ordinal':case['ordinal'],'status':case['status'],**amounts,'selected_text_bytes':selected_bytes,
        'retained_articles':len(documents),'selected_passages':len(sources),'retrieval_manifest_sha256':sha(raw)}


def audit_collection(freeze_path,expected_freeze_sha,*,expected_manifest_sha=None):
    freeze_raw=read(freeze_path);need(sha(freeze_raw)==expected_freeze_sha,'External freeze anchor differs')
    frozen=parse(freeze_raw)
    for relative,digest in (frozen['code_pins']|frozen['driver_code_pins']).items():need(sha(read(child(ROOT,relative)))==digest,'Frozen implementation differs: '+relative)
    recipe_ref=frozen['collection_recipe'];recipe_raw=read(recipe_ref['path'])
    need(sha(recipe_raw)==recipe_ref['sha256'],'Frozen collection recipe differs')
    recipe=parse(recipe_raw);root=Path(frozen['collection_output'])
    policy,stage_seconds=recipe_policy(recipe)
    need(recipe['code_pins']==frozen['code_pins']|frozen['driver_code_pins'] and recipe['scheduled_count']==199,'Dispatch recipe source/population differs')
    need(argument(recipe['command'],'--query-sha256')==frozen['queries']['sha256']
         and Path(argument(recipe['command'],'--queries'))==Path(frozen['queries']['path'])
         and Path(argument(recipe['command'],'--output'))==root,'Frozen command task/output binding differs')
    raw=read(root/'configuration.json');configuration=parse(raw)
    journal_raw=read(root/'journal.jsonl',prefix=True);events=verify_chain(journal_raw,allow_tail=True)
    configured=[row['details'] for row in events if row['event']=='collection_configured']
    need(len(configured)==1 and read_proof(root,configured[0]['configuration'])==raw,'Collection configuration journal differs')
    need(configuration['input_roles']=={'queries':'answerer_input'} and configuration['retries']==0,'Reference role or retry policy changed')
    query_raw=read_proof(root,configuration['queries']);queries=parse(query_raw)
    need(sha(query_raw)==frozen['queries']['sha256'] and len(query_raw)==frozen['queries']['bytes'],'Task-only input anchor differs')
    need(all(set(query)=={'id','question','choices'} for query in queries),'Oracle fields in task view')
    schedule=[query['id'] for query in queries]
    need(len(schedule)==199 and len(set(schedule))==199 and configuration['schedule']==schedule,'Frozen all199 schedule differs')
    for name,digest in configuration['code_pins'].items():need(frozen['code_pins']['experiments/labbench/'+name]==digest,'Collection source subpin differs')
    need(configuration['policy']==policy and configuration['stage_seconds']==stage_seconds,'Frozen collection limits differ')
    terminals=[row['details'] for row in events if row['event']=='collection_case_terminal']
    reservations=[row['details'] for row in events if row['event']=='collection_case_reserved']
    need(len({row['ordinal'] for row in reservations})==len(reservations),'Repeated collection dispatch')
    for row in reservations:need(type(row['ordinal']) is int and 0<=row['ordinal']<199 and row['id']==schedule[row['ordinal']],'Reserved task differs')
    completed=[];states=Counter();incomplete=False
    for ordinal,terminal in enumerate(terminals):
        need(terminal['ordinal']==ordinal and terminal['id']==schedule[ordinal],'Terminal case order/cardinality differs')
        case=parse(read_proof(root,terminal['case']))
        need(case['ordinal']==ordinal and case['id']==schedule[ordinal] and case['status']==terminal['status']
             and case['query_sha256']==sha(canonical(queries[ordinal])),'Case identity differs from frozen task')
        if incomplete:need(case['status']=='unexecuted','Dispatch continued after fatal collection case')
        if case['status']=='completed':completed.append(completed_case(root,case,configuration['policy'],configuration['code_pins']))
        else:
            need(case['status'] in ('failed','interrupted','unexecuted') and case['reason'],'Unknown/unexplained collection case')
            incomplete=True
        states[case['status']]+=1
    need(len(terminals)<=199 and len(reservations)<=len(terminals)+1,'Collection schedule loss or extra dispatch')
    totals={name:sum(row[name] for row in completed) for name in ('known_response_body_bytes','unknown_transfer_upper_bytes','safety_accounted_bytes','selected_text_bytes','request_count')}
    final=None
    if expected_manifest_sha is not None:
        manifest_raw=read(root/'manifest.json');need(sha(manifest_raw)==expected_manifest_sha,'External final collection anchor differs')
        manifest=parse(manifest_raw)
        need(manifest['schedule']==schedule and len(terminals)==199 and len(manifest['cases'])==199,'Final collection omits scheduled task')
        seal=parse(read(root/'SEALED.json'));closed_journal=read(root/'journal.jsonl');closed_events=verify_chain(closed_journal)
        need(seal['manifest_sha256']==expected_manifest_sha and seal['journal_sha256']==sha(closed_journal),'Final collection seal differs')
        need(closed_events[-1]['event']=='collection_sealed','Final collection journal incomplete')
        need(all(timestamp(row['sealed_at_utc'])<=timestamp(manifest['cutoff']) for row in manifest['cases']),'Availability cutoff precedes terminal case')
        for row,terminal in zip(manifest['cases'],terminals):need(canonical(row)==canonical(parse(read_proof(root,terminal['case']))),'Final manifest case differs from durable terminal')
        for relative,proof in manifest['outputs'].items():read_proof(root,{'path':relative,**proof})
        final={'status':manifest['status'],'manifest_sha256':expected_manifest_sha,'cutoff':manifest['cutoff'],'output_files':len(manifest['outputs'])}
    return {'schema_version':1,'status':'PASS','scope':'independent operational accounting; no references, native scores or semantic source judgment',
        'checked_at_utc':datetime.now(timezone.utc).isoformat(),'freeze_sha256':expected_freeze_sha,'collection_recipe_sha256':sha(recipe_raw),
        'collection_root':str(root),'scheduled':199,'terminal_cases_observed':len(terminals),'pending_at_captured_prefix':199-len(terminals),
        'terminal_states':dict(states),'verified_completed_cases':completed,'completed_case_totals':totals,
        'captured_journal_bytes':len(journal_raw),'captured_journal_sha256':sha(journal_raw),'captured_terminal_event_sha256':events[-1]['sha256'],
        'frozen_code_pins':frozen['code_pins'],'final_collection':final,'reference_access':False,'native_scoring':False,
        'limits':['Active prefix is a point-in-time observation, not final completeness proof','Body bytes exclude HTTP/TLS/wire overhead',
                  'Selected text/parent hashes and character slices checked; independent XML biological interpretation not performed']}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--freeze',required=True);parser.add_argument('--freeze-sha256',required=True)
    parser.add_argument('--collection-manifest-sha256');parser.add_argument('--output',required=True)
    args=parser.parse_args()
    result=audit_collection(args.freeze,args.freeze_sha256,expected_manifest_sha=args.collection_manifest_sha256)
    with Path(args.output).open('xb') as stream:stream.write(canonical(result)+b'\n')
    print(json.dumps({key:result[key] for key in ('status','scheduled','terminal_cases_observed','pending_at_captured_prefix','terminal_states')}))


if __name__=='__main__':main()
