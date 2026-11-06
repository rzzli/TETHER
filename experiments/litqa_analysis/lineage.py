"""Independent reconstruction of the declared primary source-admission record.

Finite SC04 policy only, not a general replacement for TETHER's input graph.
Call after independent collection verification and with the frozen catalog code.
"""
import ast
from datetime import date, datetime, timezone
from pathlib import Path

from . import collection
from .native_records import canonical, digest, need, load, read, verify_proof
from .sources import local_path, selected_passages


def catalog(code_proof):
    tree = ast.parse(verify_proof(code_proof).decode('utf-8'))
    nodes = [n.value for n in tree.body if isinstance(n, ast.Assign) and
             any(isinstance(t, ast.Name) and t.id == 'DEFAULT_CATALOG' for t in n.targets)]
    need(len(nodes) == 1 and isinstance(nodes[0], ast.Call) and isinstance(nodes[0].func, ast.Name) and
         nodes[0].func.id == 'freeze' and len(nodes[0].args) == 1, 'Pinned literal source catalog')
    value = ast.literal_eval(nodes[0].args[0])
    need(value['schema_version'] == 1 and {d['dataset_id'] for d in value['datasets']} ==
         {'labbench_retrieved_literature', 'labbench_retrieved_passages'}, 'Declared SC04 catalog datasets')
    need(all(d['roles'] == ['agent_evidence'] for d in value['datasets']), 'Evidence-only source roles')
    return value


def aware(value):
    parsed = datetime.fromisoformat(value)
    need(parsed.tzinfo is not None, 'Aware lineage timestamp')
    return parsed.astimezone(timezone.utc)


def original_proofs(root, manifest, cutoff, prefix='request:', derived_id='parsed-manifest', all_requests=False):
    """Prove every retained article parent, including uncited originals."""
    root = Path(root).resolve(); cutoff = aware(cutoff); by_id = {r['request_id']: r for r in manifest['requests']}
    need(len(by_id) == len(manifest['requests']), 'Unique source request IDs')
    sources = manifest['sources'] if 'sources' in manifest else ([manifest['source']] if manifest['source'] else [])
    used = set(); publications = {}
    for source in sources:
        publication = source['publication_date']
        need(publication is None or date.fromisoformat(publication) <= cutoff.date(), 'Future source publication')
        publications[source['source_id']] = dict(reported_date=publication,
            unknown_reason='not reported in original metadata' if publication is None else None)
        matches = [r for r in manifest['requests'] if r.get('body_path') == source['original']['path']]
        need(len(matches) == 1, 'Unambiguous original article parent')
        if not all_requests: used.update((source['discovery_request_id'], matches[0]['request_id']))
    if all_requests and sources: used = set(by_id)
    proofs = []
    for key in sorted(used):
        row = by_id[key]
        need(row['transport_status'] == 'captured' and row['http_status'] == 200, 'Successful retained parent')
        path = local_path(root, row['body_path']); receipt_path = local_path(root, row['receipt_path'])
        receipt_raw = read(receipt_path); receipt = load(receipt_path); raw = read(path)
        need(digest(receipt_raw) == row['receipt_sha256'], 'Original receipt fingerprint')
        need(aware(receipt['completed_at_utc']) <= cutoff, 'Future parent availability')
        need(receipt['status'] == 'completed' and receipt['dataset_id'] == 'labbench_retrieved_literature' and
             receipt['sha256'] == receipt['release_id'] == row['body_sha256'] == digest(raw) and
             receipt['bytes'] == len(raw) and receipt['relative_path'] == row['body_path'], 'Eligible receipt identity')
        proofs.append(dict(artifact_id=prefix+key, dataset_id='labbench_retrieved_literature', parents=[],
            path=str(path), sha256=digest(raw), release_id=digest(raw), role='agent_evidence',
            receipt_path=str(receipt_path), receipt_sha256=digest(receipt_raw)))
    if proofs:
        aware(manifest['computed_at'])  # computation date is not information availability
        parsed_sha = digest(read(root/'MANIFEST.json'))
        parents = [p['artifact_id'] for p in proofs]
        proofs.append(dict(artifact_id=derived_id, dataset_id='labbench_retrieved_passages', parents=parents,
            path=str(root/'MANIFEST.json'), sha256=parsed_sha, release_id=parsed_sha, role='agent_evidence'))
    return sorted(proofs, key=lambda p:p['artifact_id']), publications


def primary(context, query, reconstructed, root, receipt_sha, order, cutoff, request_sha, catalog_proof):
    manifest = reconstructed['manifest']; plan = manifest['plan'] if 'plan' in manifest else load(Path(root)/'PLAN.json')
    need(plan['question'] == {'id':query['id'], 'question':query['question']}, 'Source/query lineage identity')
    pool = manifest['pool']; items = collection.selection(pool['pool'], order)
    chosen = dict(pool_count=len(pool['pool']), selected_bytes=sum(len(s['text'].encode()) for s in items),
                  sources=items, unselected_count=len(pool['pool'])-len(items))
    selected_ids = {s['source_id'] for s in chosen['sources']}
    bindings = [b for b in pool['bindings'] if b['source_id'] in selected_ids]
    proofs, publications = original_proofs(root, manifest, cutoff)
    expected = dict(policy_kind='sc04_source_backed_v1', query_sha256=digest(canonical(query)),
        source_receipt_sha256=receipt_sha, query_plan_sha256=digest(canonical(plan)), cutoff=aware(cutoff).isoformat(),
        catalog_sha256=digest(canonical(catalog(catalog_proof))), publications=publications, source_proofs=proofs,
        sources_sha256=digest(canonical(chosen['sources'])), bindings=bindings, order=list(order),
        request_sha256=request_sha, coverage=manifest['coverage'], selection=chosen,
        semantic_support='unevaluated', lineage_scope='All retained eligible articles, not only cited passages')
    need(canonical(context) == canonical(expected), 'Complete independently reconstructed admission context')
    selected = selected_passages(chosen['sources'], bindings, reconstructed['articles'])
    return dict(context=expected, sources=chosen['sources'], source_metrics=selected,
                source_lineage_checked=True, scientific_support_verified=False)


def disposition(query, native, context):
    """Reproduce finite citation-admission rule, never semantic support."""
    summary = native['summary']; prediction = native['prediction']
    if summary['status'] != 'completed':
        need(summary['status'] in ('codec_failure', 'capacity'), 'Known complete-run failure class')
        return dict(disposition=dict(id=query['id'], producer_status='parse_failure' if summary['status']=='codec_failure'
            else 'input_unavailable', check_status='not_run', prediction=None, reason=summary['status']), decision=None)
    unsure = next(i for i,c in enumerate(query['choices']) if c[4:] == 'Insufficient information to answer the question')
    allowed = {s['source_id'] for s in native['sources']}
    need(set(prediction['evidence_ids']) <= allowed, 'Native offered citations')
    accepted = prediction['answer_index'] == unsure or bool(prediction['evidence_ids'])
    reason = None if accepted else 'Substantive answer requires admitted evidence'
    return dict(disposition=dict(id=query['id'], producer_status='produced', check_status='accepted' if accepted else 'rejected',
        prediction=prediction, reason=reason), decision=dict(accepted=accepted, reason=reason, prediction=prediction,
        request_sha256=summary['request_sha256'], context_sha256=digest(canonical(context)), semantic_support='unevaluated'))


def supplied(context, query, hint, reconstructed_by_doi, descriptors, cutoff, request_sha, catalog_proof):
    """Reconstruct privileged source selection and each original receipt root."""
    need(set(hint) == {'id','question','dois'} and hint['id'] == query['id'] and hint['question'] == query['question'],
         'Diagnostic hint/query identity')
    need(1 <= len(hint['dois']) <= 2 and len(set(hint['dois'])) == len(hint['dois']) and
         set(descriptors) == set(reconstructed_by_doi) == set(hint['dois']), 'Complete annotated source resolutions')
    sources=[]; proofs=[]; publications={}; availability=[]; articles={}; identities={}
    for doi in hint['dois']:
        rebuilt=reconstructed_by_doi[doi]; descriptor=descriptors[doi]; manifest=rebuilt['manifest']; source=manifest['source']
        need(set(descriptor)=={'root','receipt_sha256','plan'} and descriptor['plan']['doi']==doi and
             descriptor['plan']==manifest['plan'] and descriptor['receipt_sha256']==rebuilt['receipt_sha256'], 'Diagnostic descriptor identity')
        availability.append(dict(doi=doi,coverage=manifest['coverage'],decisions=manifest['decisions']))
        if source is None: continue
        sid=source['source_id']; signature=digest(canonical(source))
        need(sid not in identities or identities[sid]==signature, 'Conflicting duplicate diagnostic article')
        if sid not in identities: sources.append(source); identities[sid]=signature
        prefix='doi:'+digest(doi.encode())[:24]
        parent_proofs, reported=original_proofs(descriptor['root'],manifest,cutoff,prefix+':',prefix+':parsed',True)
        proofs.extend(parent_proofs); publications[doi]=reported[sid]; articles.update(rebuilt['articles'])
    pool=collection.pool(dict(id=query['id'],question=query['question']),sources)
    items=collection.selection(pool['pool'])
    coverage=dict(annotated_dois=len(hint['dois']),retained_articles=len(sources),sources=availability,
        selection_role='supplied_source_diagnostic',ordinary_retrieval=False,
        unknown_or_unavailable_inputs=[r['doi'] for r in availability if not r['coverage']['article_retained']])
    expected=dict(policy_kind='sc04_supplied_source_v1',diagnostic_only=True,ordinary_retrieval=False,
        query_sha256=digest(canonical(query)),hint_sha256=digest(canonical(hint)),selection_uses_reference_paper_identity=True,
        source_descriptors=descriptors,cutoff=aware(cutoff).isoformat(),catalog_sha256=digest(canonical(catalog(catalog_proof))),
        publications=publications,source_proofs=proofs,coverage=coverage,pool=pool,sources_sha256=digest(canonical(items)),
        request_sha256=request_sha,scientific_support_verified=False)
    need(canonical(context)==canonical(expected), 'Complete independently reconstructed diagnostic context')
    selected=selected_passages(items,pool['bindings'],articles)
    pool_metrics=selected_passages(pool['pool'],pool['bindings'],articles)
    return dict(context=expected,sources=items,source_metrics=selected,source_lineage_checked=True,
        scientific_support_verified=False,retained_dois=sorted({a['reconciled_doi'] for a in articles.values() if a['reconciled_doi']}),
        pool_dois=pool_metrics['selected_dois'])
