"""Independent six-source acquisition, version merge and raw-span admission.

Reuse the independent original XML/receipt reader. Generated queries remain
operational provenance and never become citable scientific source nodes.
"""
from datetime import date
from pathlib import Path

from tether_engine.serde import encode
from experiments.litqa_analysis import collection as original, lineage
from experiments.litqa_analysis.sources import local_path, selected_passages
from . import native_evaluation as native

n = native.n
fingerprint = native.fingerprint


def inventory(root, receipt_sha):
    root = n.safe_path(root)
    receipt_path = root/'RECEIPT.json'; raw = n.read(receipt_path)
    n.need(n.digest(raw) == receipt_sha, 'External source receipt anchor')
    receipt = n.decode(raw)
    files = receipt['files']
    n.need(isinstance(files, dict) and len(files) <= 64, 'Source inventory cap')
    actual = set()
    for path in root.rglob('*'):
        n.safe_path(path)
        if path.is_file(): actual.add(path.relative_to(root).as_posix())
    n.need(actual == set(files)|{'RECEIPT.json'} and 'FAILURE.json' not in actual, 'Exact complete source inventory')
    proofs = [dict(path=str(receipt_path), sha256=receipt_sha, bytes=len(raw))]
    for name, value in files.items():
        n.need(isinstance(value, dict) and set(value) == {'sha256', 'bytes'}, 'Exact source file proof')
        path = local_path(root, name); got = native.proof(path)
        n.need({k: got[k] for k in ('sha256', 'bytes')} == value, 'Source inventory bytes changed')
        proofs.append(got)
    return receipt, proofs


def _bound_json(proofs, path):
    matches = [p for p in proofs if Path(p['path']) == Path(path)]
    n.need(len(matches) == 1, 'Unique inventory-bound JSON bytes')
    return n.decode(n.verify_proof(matches[0]))


def _bound_events(proofs, path):
    matches = [p for p in proofs if Path(p['path']) == Path(path)]
    n.need(len(matches) == 1, 'Unique inventory-bound journal bytes')
    raw = n.verify_proof(matches[0]); n.need(raw.endswith(b'\n'), 'Complete source journal tail')
    events = []; previous = None
    for number, line in enumerate(raw.splitlines()):
        value = n.decode(line); sha = value.pop('sha256')
        n.need(value['sequence'] == number and value['previous_sha256'] == previous and fingerprint(value) == sha,
               'Source event chain differs')
        value['sha256'] = sha; events.append(value); previous = sha
    return events


def query_projection(query, prior, critic, policy):
    """Rebuild the acquisition-role projection; do not render generated prose."""
    native.candidate(query, prior)
    native._critic_context(query, prior, critic)
    if critic['decoded'] is None:
        return dict(status='unavailable', reason='refinement_query_unavailable', cause='critic_'+critic['native_status'],
                    plan=None, critic_context_sha256=fingerprint(critic))
    terms = critic['decoded']['queries']
    question = dict(id=query['id'], question=query['question'])
    suffix = ' AND OPEN_ACCESS:Y AND (LICENSE:"cc by" OR LICENSE:"cc0") AND FIRST_PDATE:[0001-01-01 TO '+policy['cutoff_date']+']'
    queries = ['('+joiner.join('"'+word+'"' for word in words)+')'+suffix
               for joiner, words in zip((' AND ', ' OR '), terms)]
    raw_plan = dict(kind='sc04_query_plan_v1', question=question, strategy='expanded', expansion=dict(queries=terms),
                    policy=policy, queries=queries, allocation='alternating_query_rank_unique_pmcid_v1')
    original.query_plan(raw_plan)
    control = dict(query_sha256=fingerprint(query), candidate_sha256=fingerprint(prior),
        source_context_sha256=critic['source_context_sha256'], critic_context_sha256=fingerprint(critic),
        critic_native_call_sha256=critic['native_call_sha256'], is_scientific_evidence=False)
    plan = dict(kind='tether_refinement_query_plan_v1', question=question, terms=terms, control_provenance=control,
        raw_plan=raw_plan, selection_scope='option_and_candidate_informed_generated_terms',
        scientific_parents='original_public_metadata_and_fulltext_responses_only')
    return dict(status='available', reason=None, cause=None, plan=plan, critic_context_sha256=fingerprint(critic))


def refinement_collection(descriptor, expected_plan):
    descriptor = encode(descriptor)
    n.need(set(descriptor) == {'root', 'receipt_sha256', 'plan'} and descriptor['plan'] == expected_plan,
           'Refinement exact descriptor/critic-plan binding')
    root = n.safe_path(descriptor['root'])
    receipt, proofs = inventory(root, descriptor['receipt_sha256'])
    n.need(set(receipt) == {'kind', 'status', 'files', 'plan_sha256'} and
        receipt['kind'] == 'tether_refinement_collection_receipt_v1' and receipt['status'] == 'complete' and
        receipt['plan_sha256'] == fingerprint(expected_plan), 'Refinement receipt identity')
    n.need(_bound_json(proofs, root/'PLAN.json') == expected_plan, 'Refinement actual plan differs')
    raw_root = root/'raw'; raw_receipt = native.proof(raw_root/'RECEIPT.json')
    raw = original.reconstruct(raw_root, raw_receipt['sha256'], expected_plan['raw_plan'])
    raw_manifest = raw['manifest']
    manifest = dict(kind='tether_refinement_collection_v1', plan=expected_plan,
        raw_collection=dict(root=str(raw_root), receipt_sha256=raw_receipt['sha256'], plan=expected_plan['raw_plan']),
        raw_manifest_sha256=fingerprint(raw_manifest), coverage=raw_manifest['coverage'], accounting=raw['accounting'],
        request_count=len(raw_manifest['requests']), control_provenance=expected_plan['control_provenance'],
        control_is_scientific_evidence=False)
    n.need(_bound_json(proofs, root/'MANIFEST.json') == manifest, 'Independent refinement wrapper reconstruction')
    events = _bound_events(proofs, root/'journal.jsonl')
    n.need([e['event'] for e in events] == ['build_reserved', 'refinement_plan_bound', 'refinement_collection_completed'] and
        events[1]['details'] == dict(plan_sha256=fingerprint(expected_plan)) and
        events[2]['details'] == dict(manifest_sha256=fingerprint(manifest), raw_receipt_sha256=raw_receipt['sha256']),
        'Refinement wrapper journal binding')
    expected_files = {'PLAN.json', 'MANIFEST.json', 'journal.jsonl', 'raw/RECEIPT.json'} | {
        'raw/'+name for name in _bound_json(proofs, raw_root/'RECEIPT.json')['files']}
    n.need(set(receipt['files']) == expected_files, 'Unexpected refinement wrapper artifacts')
    return dict(manifest=manifest, raw=raw, proofs=proofs)


def merge_sources(old, new=None):
    """Independent original-first identity/version/rights alias decisions."""
    grouped = {}
    count = 0
    for branch, bundle in (('original', old), ('refinement', new)):
        if bundle is None: continue
        n.need(len(bundle['sources']) <= 3, 'Each original collection has at most three retained articles')
        for document in bundle['sources']:
            count += 1
            alias = dict(branch=branch, collection_root=bundle['root'], collection_receipt_sha256=bundle['receipt_sha256'],
                original=document['original'], discovery_request_id=document['discovery_request_id'])
            grouped.setdefault(document['source_id'], []).append((document, alias))
    kept, excluded = [], []
    ignore = {'original', 'discovery_request_id', 'discovery_rank', 'discovery_query_slot'}
    for key, members in grouped.items():
        first = members[0][0]; scientific = {k: v for k, v in first.items() if k not in ignore}
        aliases = [alias for _, alias in members]
        if all(doc['original']['sha256'] == first['original']['sha256'] and
               {k: v for k, v in doc.items() if k not in ignore} == scientific for doc, _ in members):
            kept.append(dict(first, receipt_aliases=aliases))
        else:
            excluded.append(dict(source_id=key, reason='conflicting_pmc_version_identity_or_rights', receipt_aliases=aliases))
    return dict(kind='tether_six_source_merge_v1', sources=kept, exclusions=excluded,
        parents=dict(original={k: old[k] for k in ('root', 'receipt_sha256')},
            refinement=None if new is None else {k: new[k] for k in ('root', 'receipt_sha256')}),
        coverage=dict(input_documents=count, merged_documents=len(kept), conflicting_documents=len(excluded),
            refinement_status='unavailable' if new is None else 'collected', scope='selected eligible subset; not biological absence'))


def _pool(query, merged):
    pool = original.pool(dict(id=query['id'], question=query['question']), merged['sources'])
    by_id = {s['source_id']: s for s in merged['sources']}
    for binding in pool['bindings']:
        source = by_id[binding['document_id']]
        span = next(p for p in source['spans'] if p['evidence_id'] == binding['span_id'])
        binding.update(original_locator=span['locator'], receipt_aliases=source['receipt_aliases'])
    pool['merge_sha256'] = fingerprint(merged)
    return pool


def _temporal(branch, root, manifest, cutoff, publication_cutoff):
    root = Path(root); end = lineage.aware(cutoff)
    proofs, observed, operational = [], [], []
    for row in manifest['requests']:
        if row['transport_status'] != 'captured': continue
        receipt_path = local_path(root, row['receipt_path']); raw = n.read(receipt_path)
        n.need(n.digest(raw) == row['receipt_sha256'], 'Temporal receipt captured-byte binding')
        receipt = n.decode(raw)
        timestamp = lineage.aware(receipt['completed_at_utc'])
        n.need(timestamp <= end, 'Source acquisition after availability cutoff')
        observed.append(timestamp.isoformat())
        operational.append(dict(request_id=row['request_id'], http_status=row['http_status'], receipt_path=str(receipt_path),
            receipt_sha256=row['receipt_sha256'], observed_at_utc=timestamp.isoformat(), citable=False))
        if row['http_status'] != 200: continue
        path = local_path(root, row['body_path'])
        n.need(receipt['dataset_id'] == 'labbench_retrieved_literature' and receipt['status'] == 'completed' and
            receipt['relative_path'] == row['body_path'] and receipt['sha256'] == receipt['release_id'] == row['body_sha256'] and
            receipt['bytes'] == path.stat().st_size and receipt['url'] == row['url'], 'Raw evidence receipt role/identity')
        proofs.append(dict(artifact_id=branch+':request:'+row['request_id'], dataset_id='labbench_retrieved_literature',
            release_id=row['body_sha256'], path=str(path), sha256=row['body_sha256'], role='agent_evidence', parents=[],
            receipt_path=str(receipt_path), receipt_sha256=row['receipt_sha256']))
    publications = []
    for source in manifest['sources']:
        publication = source['publication_date']
        n.need(publication is None or date.fromisoformat(publication) <= date.fromisoformat(publication_cutoff),
               'Source publication exceeds original publication cutoff')
        publications.append(dict(source_id=source['source_id'], publication_date=publication,
            unknown_reason='Original source metadata has no publication date' if publication is None else None))
    return dict(source_proofs=sorted(proofs, key=lambda p: p['artifact_id']), publications=publications,
                observed_receipt_times=observed, operational_receipts=operational)


def reconstruct_context(context, query, prior, critic, *, original_descriptor, refinement_descriptor, cutoff,
                        catalog_proof, selection_proof):
    """Reconstruct the full source context, including unused successful parents."""
    context, query, prior, critic, old_descriptor, new_descriptor = map(encode,
        (context, query, prior, critic, original_descriptor, refinement_descriptor))
    n.need(set(old_descriptor) in ({'root', 'receipt_sha256', 'plan'}, {'root', 'receipt_sha256', 'plan', 'sources'}),
           'Original collection exact descriptor')
    n.need(old_descriptor['plan']['strategy'] == 'lexical' and old_descriptor['plan']['question'] ==
        dict(id=query['id'], question=query['question']), 'Fixed original L-branch question collection')
    old_root = n.safe_path(old_descriptor['root'])
    _, old_proofs = inventory(old_root, old_descriptor['receipt_sha256'])
    old = original.reconstruct(old_root, old_descriptor['receipt_sha256'], old_descriptor['plan'])
    if 'sources' in old_descriptor: n.need(old_descriptor['sources'] == old['manifest']['sources'], 'Original projected articles differ')
    old_items = original.selection(old['manifest']['pool']['pool'])
    native.candidate(query, prior, old_items)
    expected_critic = native.critique(query, prior, old_items, critic['decoded'], critic['native_status'], critic['native_call_sha256'])
    n.need(critic == expected_critic, 'Actual critic original raw-source binding')
    projected = query_projection(query, prior, critic, old_descriptor['plan']['policy'])
    publication_cutoff = old_descriptor['plan']['policy']['cutoff_date']; cutoff = lineage.aware(cutoff).isoformat()
    n.need(date.fromisoformat(publication_cutoff) <= lineage.aware(cutoff).date(), 'Publication cutoff exceeds availability date')
    catalog = lineage.catalog(catalog_proof)
    old_temporal = _temporal('original', old_root, old['manifest'], cutoff, publication_cutoff)
    old_bundle = dict(root=str(old_root), receipt_sha256=old_descriptor['receipt_sha256'], sources=old['manifest']['sources'])
    new = wrapper = new_bundle = new_temporal = None
    operational = list(old_proofs)
    if projected['status'] == 'unavailable':
        n.need(new_descriptor is None, 'Unavailable critic cannot invent refinement collection')
    else:
        n.need(new_descriptor is not None, 'Valid critic requires the one scheduled refinement collection')
        wrapper = refinement_collection(new_descriptor, projected['plan']); new = wrapper['raw']
        new_raw = wrapper['manifest']['raw_collection']
        new_temporal = _temporal('refinement', new_raw['root'], new['manifest'], cutoff, publication_cutoff)
        new_bundle = dict(root=new_raw['root'], receipt_sha256=new_raw['receipt_sha256'], sources=new['manifest']['sources'])
        operational += wrapper['proofs']
    merged = merge_sources(old_bundle, new_bundle); pool = _pool(query, merged)
    items = original.selection(pool['pool']); chosen = dict(pool_count=len(pool['pool']),
        selected_bytes=sum(len(s['text'].encode()) for s in items), sources=items, unselected_count=len(pool['pool'])-len(items))
    selected_ids = {s['source_id'] for s in items}; bindings = [b for b in pool['bindings'] if b['source_id'] in selected_ids]
    control = fingerprint(dict(query=query, candidate=prior, critique=critic))
    n.verify_proof(selection_proof)
    expected = dict(policy_kind='tether_sc05_merged_raw_source_v1', query_sha256=fingerprint(query), cutoff=cutoff,
        publication_cutoff=publication_cutoff, catalog_sha256=fingerprint(catalog), original_descriptor=old_descriptor,
        refinement_descriptor=new_descriptor, unavailable_reason='refinement_query_unavailable' if new_descriptor is None else None,
        merge=merged, pool=pool, selection=chosen, bindings=bindings, original_selected_sources=old_items,
        sources_sha256=fingerprint(items), temporal=dict(original=old_temporal, refinement=new_temporal),
        source_proofs=old_temporal['source_proofs']+([] if new_temporal is None else new_temporal['source_proofs']),
        control_sha256=control, control_provenance=None if new_descriptor is None else projected['plan']['control_provenance'],
        control_is_scientific_evidence=False, operational_proofs=operational, operational_proofs_citable=False,
        coverage=dict(original=old['manifest']['coverage'], refinement=None if new is None else new['manifest']['coverage'],
            merged=merged['coverage'], selection=chosen, missingness='bounded collected subset; not biological absence'),
        source_decisions=dict(original=old['manifest']['decisions'], refinement=None if new is None else new['manifest']['decisions']),
        semantic_support='unevaluated', method=dict(selection='sc05_six_source_original_span_v1', code_sha256=selection_proof['sha256']))
    n.need(context == expected, 'Complete independent six-source context reconstruction')
    articles = {}
    for bundle, rebuilt in ((old_bundle, old), (new_bundle, new)):
        if bundle is None: continue
        for source in merged['sources']:
            if source['source_id'] not in articles and any(a['collection_root'] == bundle['root'] for a in source['receipt_aliases']):
                articles[source['source_id']] = rebuilt['articles'][source['source_id']]
    metrics = selected_passages(items, bindings, articles)
    pool_metrics = selected_passages(pool['pool'], pool['bindings'], articles)
    original_metrics = selected_passages(old_items, old['manifest']['pool']['bindings'], old['articles'])
    # Recheck complete parent bytes at the join boundary, not only during their individual parses.
    for item in operational: n.verify_proof(item)
    return dict(context=expected, sources=items, source_lineage_checked=True, scientific_support_verified=False,
        original=old, refinement=new, wrapper=wrapper,
        retained_dois=sorted({a['reconciled_doi'] for a in articles.values() if a['reconciled_doi']}),
        pool_dois=pool_metrics['selected_dois'], selected_dois=metrics['selected_dois'], source_metrics=metrics,
        original_retained_dois=old['retained_dois'], original_pool_dois=old['pool_dois'],
        original_selected_dois=original_metrics['selected_dois'],
        source_context_changed=items != old_items, projected_refinement=projected)


def disposition(query, native_cell, context):
    summary = native_cell['summary']; task = summary['task']
    n.need(task in ('repair', 'removal'), 'Final answer disposition task')
    if summary['status'] != 'completed':
        return dict(disposition=dict(id=query['id'], producer_status='parse_failure' if summary['status'] == 'codec_failure'
            else 'input_unavailable', check_status='not_run', prediction=None, reason=summary['status']), decision=None)
    pred = summary['decoded']; unsure = native._query(query)
    mechanical = task == 'removal' and pred['answer_index'] != unsure and not pred['evidence_ids']
    accepted = pred['answer_index'] == unsure or bool(pred['evidence_ids'])
    reason = None if accepted else ('raw_source_removal_mechanically_rejects_substantive_answer' if mechanical else
                                    'Substantive answer requires current admitted raw evidence')
    decision = dict(accepted=accepted, reason=reason, prediction=pred, task=task,
        request_sha256=summary['request_sha256'], context_sha256=fingerprint(context), control_sha256=context['control_sha256'],
        raw_removal_mechanical_rejection=mechanical, semantic_support='unevaluated')
    return dict(disposition=dict(id=query['id'], producer_status='produced', check_status='accepted' if accepted else 'rejected',
                                 prediction=pred, reason=reason), decision=decision)
