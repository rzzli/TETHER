"""Source-inclusive independent SC04 run reconstruction; no model or network calls.

Requires a completed run and an external root receipt hash. Scientific keys and
scores are deliberately absent: the scoring layer consumes the reconstructed
records only after this complete cross-stage audit succeeds.
"""
import ast
from pathlib import Path

from . import collection, supplied_collection, envelopes, native_records, lineage
from .native_records import canonical, digest, load, need

REPO=Path(__file__).resolve().parents[2]
ARMS=('L/O','E/O','L/R','E/R')


def code_proof(envelope,name):
    frame=envelope['frame'];expected=envelope['executed_source_proofs']
    need(name in frame['code_pins'] and name in expected,'Missing executed source binding')
    archive=envelope.get('executed_source_archive')
    if archive is None:
        value=envelopes.proof(envelopes.child(REPO,name))
    else:
        from .source_archive import load_archive
        resolver=load_archive(archive['path'],archive['sha256'],frame['code_pins'],str(REPO))
        need(dict(resolver.manifest_proof,original_repository_root=str(REPO))==archive,
             'Archived producer manifest proof changed')
        value=resolver.proof(name)
    need(value==expected[name] and value['sha256']==frame['code_pins'][name],
         'Independent reader source differs from execution pin')
    return value


def catalog_code_proof(envelope):
    """Read the catalog import from pinned producer code without importing it."""
    need(envelope['kind'] in ('primary','supplied'),'Known producer kind required for catalog')
    module='litqa_comparison' if envelope['kind']=='primary' else 'litqa_supplied'
    source=code_proof(envelope,'experiments/'+module+'/admission.py')
    tree=ast.parse(native_records.verify_proof(source).decode('utf-8'))
    imports=[node for node in tree.body if isinstance(node,ast.ImportFrom) and
             any(alias.name=='DEFAULT_CATALOG' for alias in node.names)]
    need(len(imports)==1,'One pinned catalog import required')
    node=imports[0]
    need(node.level==0 and node.module is not None and node.module.startswith('experiments.labbench.') and
         len(node.module.split('.'))==3 and node.names[0].name=='DEFAULT_CATALOG' and
         len(node.names)==1 and node.names[0].asname is None,'Unsupported pinned catalog import')
    return code_proof(envelope,node.module.replace('.','/')+'.py')


def stage_map(stage):
    rows=stage['rows'];result={(r['id'],r['branch']):r for r in rows}
    need(len(result)==len(rows),'Duplicate cross-stage row');return result


def product_root(stage,row):return Path(stage['stage_root'])/'products'/f'{row["ordinal"]:04d}'


def matching(row,*,status,reason,product):
    need(canonical({k:row[k] for k in ('status','reason','product')})==canonical(dict(status=status,reason=reason,product=product)),
         'Independent cross-stage product mismatch: '+row['id']+' '+row['branch'])


def native_arguments(envelope,stage):
    frame=envelope['frame']
    info=stage['model_info'];need(info is not None,'Missing phase model identity')
    spec=info['spec']
    return dict(model_provenance=info['provenance'],alias=info['alias'],owner_pid=stage['worker']['server_terminal']['pid'],
        configuration=frame['generation_configuration'],code_proof=code_proof(envelope,'experiments/litqa_comparison/codecs.py'),
        expected_endpoint=f'http://{spec["host"]}:{spec["port"]}')


def call_descriptor(root,native):
    return dict(root=str(root),summary=native['summary'],summary_proof=envelopes.proof(root/'SUMMARY.json'))


def logical_usage(calls):
    result=dict(generation_calls=0,measured_input_tokens=0,measured_output_tokens=0,reserved_input_tokens=0,reserved_output_tokens=0,provider_cost_usd=0)
    for value in calls:
        if value is None:continue
        summary=value['summary'];usage=summary['usage']
        result['generation_calls']+=int(summary['generation_entered'])
        if usage:
            result['measured_input_tokens']+=usage['input_tokens'];result['measured_output_tokens']+=usage['output_tokens']
            result['provider_cost_usd']+=usage['cost_usd']
        result['reserved_input_tokens']+=summary['reservation_input_tokens'];result['reserved_output_tokens']+=summary['reservation_output_tokens']
    need(result['generation_calls']<=3 and result['measured_output_tokens']<=768 and result['provider_cost_usd']==0,'Logical total model budget')
    return result


def source_usage(manifests):
    """Logical charges: shared captures count in each consuming arm."""
    return dict(requests=sum(len(m['requests']) for m in manifests),
        measured_response_bytes=sum(m['accounting']['measured_response_bytes'] for m in manifests),
        safety_accounted_bytes=sum(m['accounting']['safety_accounted_bytes'] for m in manifests),
        unknown_transfer_upper_bytes=sum(m['accounting']['unknown_transfer_upper_bytes'] for m in manifests))


def text_usage(sources, pool):
    return dict(retained_original_bytes=sum(s['original']['bytes'] for s in sources),
        extracted_paragraph_bytes=sum(len(span['text'].encode()) for s in sources for span in s['spans']),
        candidate_pool_bytes=sum(len(p['text'].encode()) for p in pool['pool']))


def primary_verified(envelope):
    """Internal join layer; the public entry verifies the envelope first."""
    from . import auxiliary_native
    frame=envelope['frame'];phases=envelope['phases'];cutoff=envelope['complete']['source_cutoff']
    queries=envelopes.external(frame['query_products']['answer_queries']);source_queries=envelopes.external(frame['query_products']['source_queries'])
    q_by={q['id']:q for q in queries};s_by={q['id']:q for q in source_queries}
    expansion_rows=stage_map(phases['expand']);collection_rows=stage_map(phases['collect']);ranking_rows=stage_map(phases['rank'])
    expansion_calls={};rank_calls={};collected={}
    expansion_args=native_arguments(envelope,phases['expand'])
    for row in phases['expand']['rows']:
        root=product_root(phases['expand'],row);query=s_by[row['id']]
        native=auxiliary_native.reconstruct(root,query,task='expand',**expansion_args)
        need(load(root/'INPUT.json')['items']==[],'Expansion reads no passages')
        call=call_descriptor(root,native);good=native['summary']['status']=='completed'
        matching(row,status='completed' if good else 'fallback',reason=None if good else native['summary']['status'],
            product=dict(call=call,expansion=native['prediction'] if good else None,strategy='expanded' if good else 'lexical'))
        expansion_calls[row['id']]=native
    for row in phases['collect']['rows']:
        root=product_root(phases['collect'],row);product=row['product'];parent=expansion_rows[(row['id'],'shared')]
        good=parent['status']=='completed';strategy='expanded' if row['branch']=='E' and good else 'lexical'
        plan=product['plan'];need(plan['question']==s_by[row['id']] and plan['strategy']==strategy and plan['policy']==frame['policy'] and
            plan['expansion']==(parent['product']['expansion'] if strategy=='expanded' else None),'Question-only collection/expansion join')
        receipt=envelopes.proof(root/'RECEIPT.json')
        result=collection.reconstruct(root,receipt['sha256'],plan)
        matching(row,status='completed',reason=None,product=dict(root=str(root),receipt=receipt,plan=plan,
            manifest=envelopes.proof(root/'MANIFEST.json'),expansion_available=good,query_branch=row['branch'],expansion_parent_sha256=digest(canonical(parent))))
        collected[(row['id'],row['branch'])]=result
    rank_args=native_arguments(envelope,phases['rank'])
    for row in phases['rank']['rows']:
        key=(row['id'],row['branch']);result=collected[key];parent=collection_rows[key];pool=result['manifest']['pool']['pool']
        root=product_root(phases['rank'],row)
        common=dict(collection_receipt_sha256=parent['product']['receipt']['sha256'],pool_sha256=digest(canonical(pool)))
        if not pool:
            need(not root.exists(),'Empty pool dispatched a model ranker')
            matching(row,status='not_applicable',reason='empty eligible passage pool',product=dict(order=[],call=None,**common));rank_calls[key]=None
        else:
            native=auxiliary_native.reconstruct(root,s_by[row['id']],task='rank',**rank_args)
            need(load(root/'INPUT.json')['items']==pool,'Ranker exact source pool')
            good=native['summary']['status']=='completed';call=call_descriptor(root,native)
            matching(row,status='completed' if good else 'fallback',reason=None if good else native['summary']['status'],
                product=dict(order=native['prediction'] if good else [p['rank_id'] for p in pool],call=call,**common));rank_calls[key]=native
    records={arm:[] for arm in ARMS};evidence_ids={arm:{} for arm in ARMS};cases={arm:[] for arm in ARMS}
    answer_args=native_arguments(envelope,phases['answer']);catalog=catalog_code_proof(envelope)
    for row in phases['answer']['rows']:
        key=(row['id'],row['branch'][0]);query=q_by[row['id']];result=collected[key];parent=collection_rows[key];ranking=ranking_rows[key]
        root=product_root(phases['answer'],row);pool=result['manifest']['pool']['pool']
        order=ranking['product']['order'] if row['branch'].endswith('/R') else [p['rank_id'] for p in pool]
        native=native_records.reconstruct(root,query,**answer_args);context=load(root/'CONTEXT.json')
        checked=lineage.primary(context,query,result,parent['product']['root'],parent['product']['receipt']['sha256'],order,cutoff,
            native['summary']['request_sha256'],catalog)
        need(native['sources']==checked['sources'],'Answer offered passages differ from reconstructed selection')
        disposition=lineage.disposition(query,native,context);call=call_descriptor(root,native)
        matching(row,status='completed',reason=None,product=dict(call=call,**disposition,context=envelopes.proof(root/'CONTEXT.json'),
            collection_receipt_sha256=parent['product']['receipt']['sha256'],ranking_parent_sha256=digest(canonical(ranking)),order=order))
        arm=row['branch'];records[arm].append(disposition['disposition']);evidence_ids[arm][query['id']]=[s['source_id'] for s in checked['sources']]
        charged=[native,expansion_calls[query['id']] if arm[0]=='E' else None,rank_calls[key] if arm.endswith('/R') else None]
        cases[arm].append(dict(id=query['id'],retained_dois=result['retained_dois'],pool_dois=result['pool_dois'],selected_dois=checked['source_metrics']['selected_dois'],
            source_coverage=result['manifest']['coverage'],source_decisions=result['manifest']['decisions'],
            source_identity=[{k:a[k] for k in ('source_id','metadata_doi_raw','xml_dois_raw','reconciled_doi','doi_basis','doi_unknown_reason')} for a in result['articles'].values()],
            selected_bytes=checked['source_metrics']['selected_bytes'],selected_passages=len(checked['sources']),native_status=native['summary']['status'],
            expansion_status=expansion_rows[(query['id'],'shared')]['status'],ranking_status=ranking['status'],
            expansion_failure_reason=expansion_rows[(query['id'],'shared')]['reason'],ranking_failure_reason=ranking['reason'],
            expansion_native_status=expansion_calls[query['id']]['summary']['status'],
            ranking_native_status=rank_calls[key]['summary']['status'] if rank_calls[key] else 'not_applicable',
            logical_model_usage=logical_usage(charged),logical_http_usage=source_usage([result['manifest']]),
            **text_usage(result['manifest']['sources'],result['manifest']['pool'])))
    return dict(queries=queries,records=records,evidence_ids=evidence_ids,source_cases=cases,
        scope='All primary source, expansion, ranking, answer, eligibility and cross-stage products independently reconstructed; correctness scoring is separate.')


def supplied_verified(envelope):
    frame=envelope['frame'];phases=envelope['phases'];cutoff=envelope['complete']['source_cutoff']
    queries=envelopes.external(frame['products']['answer_queries']);hints=envelopes.external(frame['products']['hints'])
    q_by={q['id']:q for q in queries};h_by={h['id']:h for h in hints};collected={};descriptors={}
    for row in phases['collect']['rows']:
        root=product_root(phases['collect'],row);product=row['product'];plan=product['plan']
        need(plan['doi']==row['id'] and plan['policy']==frame['policy'],'Diagnostic resolution schedule/policy')
        receipt=envelopes.proof(root/'RECEIPT.json');result=supplied_collection.reconstruct(root,receipt['sha256'],plan)
        matching(row,status='completed',reason=None,product=dict(root=str(root),receipt=receipt,plan=plan,manifest=envelopes.proof(root/'MANIFEST.json')))
        collected[row['id']]=result;descriptors[row['id']]=dict(root=str(root),receipt_sha256=receipt['sha256'],plan=plan)
    records=[];evidence_ids={};cases=[];answer_args=native_arguments(envelope,phases['answer'])
    catalog=catalog_code_proof(envelope)
    for row in phases['answer']['rows']:
        root=product_root(phases['answer'],row);query=q_by[row['id']];hint=h_by[row['id']]
        selected_desc={d:descriptors[d] for d in hint['dois']};selected_results={d:collected[d] for d in hint['dois']}
        native=native_records.reconstruct(root,query,**answer_args);context=load(root/'CONTEXT.json')
        checked=lineage.supplied(context,query,hint,selected_results,selected_desc,cutoff,native['summary']['request_sha256'],catalog)
        need(native['sources']==checked['sources'],'Diagnostic answer differs from annotated-source selection')
        disposition=lineage.disposition(query,native,context);call=call_descriptor(root,native)
        matching(row,status='completed',reason=None,product=dict(call=call,**disposition,context=envelopes.proof(root/'CONTEXT.json'),
            hint_sha256=digest(canonical(hint)),diagnostic_only=True))
        records.append(disposition['disposition']);evidence_ids[query['id']]=[s['source_id'] for s in checked['sources']]
        cases.append(dict(id=query['id'],retained_dois=checked['retained_dois'],pool_dois=checked['pool_dois'],selected_dois=checked['source_metrics']['selected_dois'],
            source_coverage=checked['context']['coverage'],selected_bytes=checked['source_metrics']['selected_bytes'],selected_passages=len(checked['sources']),
            native_status=native['summary']['status'],logical_model_usage=logical_usage([native]),
            logical_http_usage=source_usage([r['manifest'] for r in selected_results.values()]),
            **text_usage([r['source'] for r in selected_results.values() if r['source']],checked['context']['pool'])))
    return dict(queries=queries,records={'supplied':records},evidence_ids={'supplied':evidence_ids},source_cases={'supplied':cases},
        diagnostic_resolutions=[dict(doi=d,coverage=r['coverage'],decisions=r['decisions']) for d,r in collected.items()],
        scope='All privileged source resolutions, raw passages, eligibility and answer products independently reconstructed; ordinary retrieval and scientific correctness are not established.')


def reconstruct(root,expected_root_sha256,*,source_archive=None):
    envelope=envelopes.verify_run(root,expected_root_sha256,source_archive=source_archive)
    primary=envelope['frame']['kind']=='sc04_primary_execution_v1'
    result=primary_verified(envelope) if primary else supplied_verified(envelope)
    return dict(status='independently_reconstructed',root=envelope['root'],root_sha256=expected_root_sha256,
        frame_sha256=envelope['frame_sha256'],purpose=envelope['frame']['purpose'],resources=envelope['resources'],**result,
        executed_source_proofs=envelope['executed_source_proofs'],executed_source_archive=envelope['executed_source_archive'],
        source_lineage_checked=True,native_calls_checked=True,cross_stage_products_checked=True,scientific_correctness_scored=False,
        model_weight_bytes_rehashed=False,model_identity_scope='Pinned receipt/runtime/model identities and owned request echoes; assets were verified before inference, not rehashed by this analysis.')
