"""Independent all-case refinement joins and immutable evaluator capability.

The envelope reader authenticates supervision, roles, baseline and stage bytes.
This reader rebuilds each native/source/control join before keys may be opened.
"""
from collections.abc import Mapping
from dataclasses import dataclass, field
import inspect
from pathlib import Path
from weakref import WeakValueDictionary

from tether_engine.serde import encode, freeze
from experiments.litqa_analysis.scoring import paper_metrics
from experiments.litqa_analysis import inputs as original_inputs
from . import native_evaluation as native, source_evaluation as source, statistics

n = native.n
fingerprint = native.fingerprint
PHASES = ('critic', 'refinement_collect', 'pair_prepare', 'repair', 'removal')
ACCOUNT_FIELDS = ('generation_calls', 'measured_input_tokens', 'measured_output_tokens', 'reserved_input_tokens',
                  'reserved_output_tokens', 'source_http_requests', 'measured_response_bytes', 'safety_accounted_bytes')
_AUTHORITY = object()
_ISSUED = WeakValueDictionary()


def _product(value, path):
    n.need(isinstance(value, dict) and set(value) == {'path', 'sha256', 'bytes'} and
           n.safe_path(value['path']) == n.safe_path(path), 'Exact stage product location')
    return n.decode(n.verify_proof(value))


def _code(frame, name):
    matches = [p for p in frame['code_files'] if Path(p['path']).as_posix().endswith('/'+name)]
    n.need(len(matches) == 1, 'Unique pinned code role: '+name)
    n.verify_proof(matches[0])
    return matches[0]


def _usage(cell):
    out = dict.fromkeys(ACCOUNT_FIELDS, 0)
    summary = cell['summary']
    out['generation_calls'] = int(summary['generation_entered'])
    out['reserved_input_tokens'] = summary['reservation_input_tokens']
    out['reserved_output_tokens'] = summary['reservation_output_tokens']
    if summary['usage'] is not None:
        out['measured_input_tokens'] = summary['usage']['input_tokens']
        out['measured_output_tokens'] = summary['usage']['output_tokens']
    return dict(out, provider_cost_usd=0)


def _logical_resources(envelope, measured):
    ids = envelope['frame']['schedule']; rows = envelope['resources']['baseline_resources']
    n.need([r['id'] for r in rows] == ids, 'Full historical L/O-attributable resource schedule')
    model_keys = ACCOUNT_FIELDS[:5] + ('provider_cost_usd',)
    http_keys = ('requests', 'measured_response_bytes', 'safety_accounted_bytes', 'unknown_transfer_upper_bytes')
    for row in rows:
        n.need(set(row) == {'id', 'logical_model_usage', 'logical_http_usage'} and
            set(row['logical_model_usage']) == set(model_keys) and set(row['logical_http_usage']) == set(http_keys),
            'Historical attributable resource fields')
        for key, value in row['logical_model_usage'].items():
            n.need(value == 0 if key == 'provider_cost_usd' else type(value) is int and value >= 0,
                   'Historical model accounting counts')
        n.need(all(type(v) is int and v >= 0 for v in row['logical_http_usage'].values()), 'Historical HTTP accounting counts')
        m, h = row['logical_model_usage'], row['logical_http_usage']
        n.need(m['generation_calls'] <= 1 and m['measured_input_tokens'] <= m['reserved_input_tokens'] and
            m['measured_output_tokens'] <= m['reserved_output_tokens'] <= 256 and h['requests'] <= 5 and
            h['safety_accounted_bytes']-h['measured_response_bytes'] == h['unknown_transfer_upper_bytes'],
            'Historical L/O accounting bounds')
    base_model = {k: sum(r['logical_model_usage'][k] for r in rows) for k in model_keys}
    base_http = {k: sum(r['logical_http_usage'][k] for r in rows) for k in http_keys}
    h1 = measured['refinement_collect']
    new_http = dict(requests=h1['source_http_requests'], measured_response_bytes=h1['measured_response_bytes'],
        safety_accounted_bytes=h1['safety_accounted_bytes'],
        unknown_transfer_upper_bytes=h1['safety_accounted_bytes']-h1['measured_response_bytes'])
    conditions = {}
    for condition, model_phases in (('one_pass', ()), ('critique_only', ('critic',)),
                                    ('repair', ('critic', 'repair')), ('removal', ('critic', 'removal'))):
        model_usage = {k: base_model[k]+sum(measured[p][k] for p in model_phases) for k in model_keys if k != 'provider_cost_usd'}
        model_usage['provider_cost_usd'] = 0
        has_refinement = condition in ('repair', 'removal')
        attributed_http = {k: base_http[k]+(new_http[k] if has_refinement else 0) for k in http_keys}
        conditions[condition] = dict(model_usage=model_usage, attributed_http_usage=attributed_http,
            reused_original_model=base_model, reused_original_sources=base_http,
            incremental_model_phases=list(model_phases),
            refinement_source_information_dependency=condition == 'repair',
            refinement_source_control_overhead=condition == 'removal',
            refinement_source_attribution=new_http if has_refinement else {k: 0 for k in http_keys},
            generation_ceiling=3*len(ids), output_token_ceiling=768*len(ids))
    return dict(conditions=conditions, baseline_arm='L/O', reused_model_and_sources_charged_once_physically=True,
        warning='Logical condition totals overlap and must not be summed as physical work. Removal H1 is scheduling/control overhead only.')


def _selection(query, prior, critic):
    pred = prior['prediction']
    flags = dict(producer_status=prior['producer_status'], check_status=prior['original_admission_status'],
                 native_unsure=pred is not None and pred['answer_index'] == native._query(query))
    decision, reason = statistics._selection(flags, critic)
    return dict(kind='tether_semantic_selection_v1', decision=decision, reason=reason,
        candidate_sha256=fingerprint(prior), critique_sha256=fingerprint(critic),
        retained_prediction=pred if decision == 'keep' else None, native_candidate_unchanged=True,
        scientific_correctness='unevaluated')


def _cell(stage, row, descriptor, info, code_proof):
    root = Path(stage['root'])/'products'/f'{row["ordinal"]:04d}'
    product_keys = {'call', 'native_proof', 'critic', 'semantic_selection'} if descriptor['task'] == 'critic' else {
        'call', 'native_proof', 'disposition', 'decision', 'paired_member_sha256', 'control_sha256', 'source_context_sha256'}
    n.need(set(row['product']) == product_keys, 'Exact critic/final stage product fields')
    expected = dict(task=descriptor['task'], query=descriptor['query'], candidate_context=descriptor['prior'],
                    sources=descriptor['sources'], model_provenance=descriptor['model_provenance'])
    if descriptor['task'] != 'critic':
        expected.update(critique_context=descriptor['critic'], prepared_member=descriptor['prepared_member'],
                        control_sha256=descriptor['control_sha256'])
    cell = native.reconstruct_cell(root, expected, execution_id=row['execution_id'], code_proof=code_proof, **info)
    call = row['product']['call']
    n.need(set(call) == {'root', 'summary', 'summary_proof'} and Path(call['root']) == root and
        call['summary'] == cell['summary'] and _product(call['summary_proof'], root/'SUMMARY.json') == cell['summary'],
        'Native cell stage product summary/root binding')
    expected_proof = None if cell['native_call_sha256'] is None else native.proof(root/'native/native-response.bin')
    n.need(row['product']['native_proof'] == expected_proof, 'Native raw proof stage binding')
    n.need(row['status'] == cell['summary']['status'] and row['accounting'] == _usage(cell), 'Native measured stage accounting')
    reason = None if row['status'] == 'completed' else ('critic_' if descriptor['task'] == 'critic' else '')+row['status']
    n.need(row['reason'] == reason, 'Native terminal stage reason differs')
    return cell


def join_stages(envelope):
    """Pure join adapter. It does not by itself confer evaluator authority."""
    envelope = encode(envelope)
    frame = envelope['frame']; ids = frame['schedule']; baseline = envelope['baseline']
    n.need(len(ids) == (199 if frame['purpose'] == 'production' else 2) and len(set(ids)) == len(ids), 'Full fixed refinement schedule')
    n.need(frame['purpose'] in ('production', 'fictional_qualification') and baseline['schedule'] == ids and
           [q['id'] for q in baseline['queries']] == ids and [c['id'] for c in baseline['cases']] == ids,
           'Original baseline complete ordered schedule')
    n.need(set(envelope['phases']) == set(PHASES), 'All five sealed stages')
    for phase, stage in envelope['phases'].items():
        n.need([r['id'] for r in stage['rows']] == ids and stage['report']['rows'] == stage['rows'] and
            stage['report']['status'] == 'complete', 'Complete phase row schedule')
    model_code = _code(frame, 'experiments/litqa_refinement/model.py')
    catalog_code = _code(frame, 'experiments/labbench/tether_adapter.py')
    selection_code = _code(frame, 'experiments/litqa_refinement/selection.py')
    records = {key: [] for key in ('one_pass', 'repair', 'removal')}
    evidence = {key: {} for key in records}; critics = []; source_cases = []; case_products = []
    seen_calls = set(); measured = {phase: dict.fromkeys(ACCOUNT_FIELDS, 0) for phase in PHASES}
    phases = envelope['phases']
    for index, case in enumerate(baseline['cases']):
        query, prior = case['query'], case['candidate']; key = query['id']
        native.candidate(query, prior, case['original_selected_sources'])
        rows = {phase: phases[phase]['rows'][index] for phase in PHASES}
        n.need(all(row['ordinal'] == index and row['phase'] == phase for phase, row in rows.items()), 'Stage ordinal/phase join')
        physical = [r['execution_id'] for r in rows.values()]
        n.need(len(set(physical)) == len(physical) and not set(physical)&seen_calls, 'Distinct physical stage execution IDs')
        seen_calls.update(physical)
        critic_row = rows['critic']
        descriptor = dict(task='critic', query=query, prior=prior, sources=case['original_selected_sources'],
                          model_provenance=frame['model_provenance'])
        cell = _cell(phases['critic'], critic_row, descriptor, envelope['model_contexts']['critic'], model_code)
        critic = native.critique(query, prior, case['original_selected_sources'], cell['summary']['decoded'],
                                 cell['summary']['status'], cell['native_call_sha256'])
        root = Path(phases['critic']['root'])/'products'/f'{index:04d}'
        n.need(_product(critic_row['product']['critic'], root/'CRITIC.json') == critic and
            critic_row['product']['semantic_selection'] == _selection(query, prior, critic), 'Independent critic/selection reconstruction')
        projected = source.query_projection(query, prior, critic, case['original_collection']['plan']['policy'])
        collect_row = rows['refinement_collect']; collection_product = collect_row['product']
        n.need(set(collection_product) == {'query_projection', 'collection'} and collection_product['query_projection'] == projected,
               'Critic-only bounded acquisition projection')
        refinement = collection_product['collection']
        if projected['status'] == 'unavailable':
            n.need(collect_row['status'] == 'unavailable' and collect_row['reason'] == 'refinement_query_unavailable' and refinement is None,
                   'Unavailable source collection disposition')
        else:
            n.need(collect_row['status'] == 'completed' and collect_row['reason'] is None and refinement is not None and
                Path(refinement['root']) == Path(phases['refinement_collect']['root'])/'products'/f'{index:04d}',
                'One refinement collection at its own reserved location')
        prepare_row = rows['pair_prepare']; product = prepare_row['product']
        pairroot = Path(phases['pair_prepare']['root'])/'products'/f'{index:04d}'
        n.need(set(product) == {'query', 'prior', 'critic', 'context', 'repair', 'removal', 'control_sha256',
            'refinement_collection', 'cutoff', 'model_provenance'}, 'Paired preparation product fields')
        n.need(_product(product['query'], pairroot/'QUERY.json') == query and
            _product(product['prior'], pairroot/'PRIOR.json') == prior and
            _product(product['critic'], pairroot/'CRITIC.json') == critic, 'Paired preparation common controls')
        control = fingerprint(dict(query=query, candidate=prior, critique=critic))
        n.need(product['control_sha256'] == control and product['refinement_collection'] == refinement and
            product['model_provenance'] == frame['model_provenance'] and
            product['cutoff'] == phases['pair_prepare']['inputs']['cutoff'], 'Pair source/model/availability freeze')
        context = _product(product['context'], pairroot/'CONTEXT.json')
        rebuilt = source.reconstruct_context(context, query, prior, critic, original_descriptor=case['original_collection'],
            refinement_descriptor=refinement, cutoff=product['cutoff'], catalog_proof=catalog_code, selection_proof=selection_code)
        members = {task: native.prepare_member(task, query, prior, critic, rebuilt['sources'] if task == 'repair' else [],
            frame['model_provenance'], model_code) for task in ('repair', 'removal')}
        n.need(all(_product(product[task], pairroot/(task.upper()+'.json')) == members[task] for task in members),
               'Both native pair members frozen from same pre-repair context')
        zero = dict.fromkeys(ACCOUNT_FIELDS, 0) | dict(provider_cost_usd=0)
        n.need(prepare_row['status'] == 'completed' and prepare_row['reason'] is None and prepare_row['accounting'] == zero,
               'Pure pair preparation has no model/source dispatch')
        collection_usage = dict(zero)
        if rebuilt['wrapper'] is not None:
            wrapper = rebuilt['wrapper']['manifest']
            collection_usage.update(source_http_requests=wrapper['request_count'],
                measured_response_bytes=wrapper['accounting']['measured_response_bytes'],
                safety_accounted_bytes=wrapper['accounting']['safety_accounted_bytes'])
        n.need(collect_row['accounting'] == collection_usage, 'Collection measured and reserved accounting join')
        final_cells = {}
        for task in ('repair', 'removal'):
            row = rows[task]; raw = rebuilt['sources'] if task == 'repair' else []
            descriptor = dict(task=task, query=query, prior=prior, critic=critic, sources=raw,
                model_provenance=frame['model_provenance'], prepared_member=members[task], control_sha256=control)
            final = _cell(phases[task], row, descriptor, envelope['model_contexts'][task], model_code)
            decision = source.disposition(query, final, context)
            finalroot = Path(phases[task]['root'])/'products'/f'{index:04d}'
            n.need(row['product']['disposition'] == decision['disposition'] and
                _product(row['product']['decision'], finalroot/'DECISION.json') == decision['decision'] and
                row['product']['paired_member_sha256'] == fingerprint(members[task]) and
                row['product']['control_sha256'] == control and row['product']['source_context_sha256'] == fingerprint(context),
                'Final native/source/admission product join')
            records[task].append(decision['disposition']); evidence[task][key] = [s['source_id'] for s in raw]
            final_cells[task] = final
        records['one_pass'].append(case['original_disposition'])
        evidence['one_pass'][key] = [s['source_id'] for s in case['original_selected_sources']]
        critics.append(dict(id=key, native_status=critic['native_status'],
                            decoded=None if critic['decoded'] is None else dict(support=critic['decoded']['support'])))
        source_cases.append(dict(id=key, retained_dois=rebuilt['retained_dois'], pool_dois=rebuilt['pool_dois'],
            selected_dois=rebuilt['selected_dois'], original_selected_sources=case['original_selected_sources'],
            original_retained_dois=rebuilt['original_retained_dois'], original_pool_dois=rebuilt['original_pool_dois'],
            original_selected_dois=rebuilt['original_selected_dois'],
            selected_sources=rebuilt['sources'], source_context_changed=rebuilt['source_context_changed'],
            source_coverage=context['coverage'], source_proofs=context['source_proofs'],
            publication_cutoff=context['publication_cutoff'], acquisition_cutoff=context['cutoff'],
            temporal=context['temporal'], merged_exclusions=context['merge']['exclusions'],
            refinement_available=refinement is not None))
        case_products.append(dict(id=key, critic=critic, semantic_selection=_selection(query, prior, critic),
            original=case['original_disposition'], repair=records['repair'][-1], removal=records['removal'][-1],
            physical_execution_ids={phase: rows[phase]['execution_id'] for phase in PHASES},
            control_sha256=control, source_context_sha256=fingerprint(context)))
        for phase, row in rows.items():
            for metric in ACCOUNT_FIELDS: measured[phase][metric] += row['accounting'][metric]
    for phase in PHASES:
        n.need(measured[phase] == phases[phase]['report']['accounting']['known_totals'], 'Native/source/journal aggregate usage join')
    physical = {key: sum(row[key] for row in measured.values()) for key in ACCOUNT_FIELDS}
    n.need(physical['generation_calls'] <= 3*len(ids) and physical['source_http_requests'] <= 5*len(ids), 'Full incremental budget')
    return dict(status='independently_reconstructed', purpose=frame['purpose'], queries=baseline['queries'],
        records=records, evidence_ids=evidence, critics=critics, source_cases=source_cases, case_products=case_products,
        source_lineage_checked=True, native_calls_checked=True, cross_stage_products_checked=True,
        incremental_resources=dict(by_phase=measured, physical_totals=physical, provider_cost_usd=0,
            reused_original_work_included=False), logical_resources=_logical_resources(envelope, measured),
        scientific_support_verified=False)


@dataclass(frozen=True)
class VerifiedRefinement:
    root: str
    receipt_sha256: str
    report: Mapping
    envelope: Mapping
    _integrity: str = field(repr=False)
    _authority: object = field(default=None, repr=False, compare=False)
    _envelope_capability: object = field(default=None, repr=False, compare=False)


def _trusted(value):
    n.need(type(value) is VerifiedRefinement and _ISSUED.get(id(value)) is value and value._authority is _AUTHORITY,
           'Independently reconstructed sealed refinement capability required')
    n.need(value._integrity == fingerprint(dict(root=value.root, receipt_sha256=value.receipt_sha256,
        report=value.report, envelope=value.envelope)), 'Immutable refinement capability fingerprint')
    n.need(value._envelope_capability is not None and fingerprint(value._envelope_capability) == fingerprint(value.envelope),
           'Retained envelope capability differs from frozen result')
    return value


def reconstruct(descriptor, *, baseline_acceptance):
    """The independent envelope must finish before any reference keys are read."""
    from . import envelopes
    envelope = envelopes.reconstruct(descriptor, baseline_acceptance=baseline_acceptance)
    n.need(envelope['supervised_root_verified'] is True and envelope['actor_roles_verified'] is True and
           envelope['baseline_verified'] is True, 'Independent supervision/actor/original baseline prerequisites')
    report = join_stages(envelope)
    envelopes.revalidate(envelope)
    descriptor = encode(descriptor); report, frozen_envelope = freeze(report), freeze(envelope)
    integrity = fingerprint(dict(root=descriptor['root'], receipt_sha256=descriptor['receipt_sha256'], report=report, envelope=frozen_envelope))
    value = VerifiedRefinement(descriptor['root'], descriptor['receipt_sha256'], report, frozen_envelope, integrity, _AUTHORITY, envelope)
    _ISSUED[id(value)] = value
    return value


def revalidate(value):
    value = _trusted(value)
    from . import envelopes
    envelopes.revalidate(value._envelope_capability)
    return value


def endpoint_contract(declared_at_utc, implementation_note, endpoint_addendum):
    """Prospective evaluator-only policy; persist and pin before benchmark work."""
    source.lineage.aware(declared_at_utc)
    for item in (implementation_note, endpoint_addendum): n.verify_proof(item)
    return dict(kind='sc05_refinement_endpoint_contract_v1', role='evaluation_only', declared_at_utc=declared_at_utc,
        implementation_note=encode(implementation_note), endpoint_addendum=encode(endpoint_addendum), baseline_arm='L/O',
        primary_conditions=list(statistics.CONDITIONS), primary_contrasts=[name for name, _, _ in statistics.CONTRASTS],
        primary_interval_endpoints=list(statistics.ENDPOINTS), bootstrap_seed=statistics.SEED,
        bootstrap_replicates=statistics.REPLICATES, publication_components=186, scheduled_questions=199,
        question_sensitivity=True, diagnostic_contrast='removal_minus_repair', diagnostic_interval_endpoint='raw_accuracy',
        conditional_precision='point_only_null_if_no_retained_substantive_answers',
        group_policy='original_shared_annotated_doi_connected_components')


def _authority(value, descriptor, native_scorer, native_scorer_archive):
    n.need(isinstance(descriptor, Mapping) and set(descriptor) == {'path', 'sha256', 'bytes'}, 'External evaluation authority proof')
    raw = n.verify_proof(encode(descriptor)); authority = n.decode(raw)
    n.need(set(authority) == {'kind', 'role', 'purpose', 'created_at_utc', 'producer', 'baseline_acceptance',
        'original_inputs', 'endpoint_freeze', 'native_scorer', 'native_scorer_dependencies', 'native_scorer_archive'},
        'Explicit evaluation-only authority fields')
    n.need(authority['kind'] == 'sc05_refinement_evaluation_authority_v1' and authority['role'] == 'evaluation_only' and
        authority['purpose'] == value.report['purpose'] and authority['producer'] ==
        dict(root=value.root, receipt_sha256=value.receipt_sha256), 'Sealed producer/evaluator authority binding')
    source.lineage.aware(authority['created_at_utc'])
    n.need(authority['baseline_acceptance'] == encode(value.envelope['baseline_acceptance']), 'Original accepted baseline authority')
    endpoints = n.decode(n.verify_proof(authority['endpoint_freeze']))
    rebuilt = endpoint_contract(endpoints['declared_at_utc'], endpoints['implementation_note'], endpoints['endpoint_addendum'])
    n.need(endpoints == rebuilt and source.lineage.aware(endpoints['declared_at_utc']) <=
        source.lineage.aware(value.envelope['started_at_utc']), 'Endpoint contract must precede benchmark execution')
    n.need(callable(native_scorer) and getattr(native_scorer, '__name__', None) == 'evaluate_schedule', 'Pinned native scorer function')
    scorer_path = inspect.getsourcefile(native_scorer)
    n.need(scorer_path is not None and n.safe_path(scorer_path) == n.safe_path(authority['native_scorer']['path']),
           'Actual loaded native scorer differs from authority')
    n.verify_proof(authority['native_scorer'])
    n.need(isinstance(authority['native_scorer_dependencies'], list) and authority['native_scorer_dependencies'],
           'Native scorer dependency proofs required')
    imported = native_scorer.__globals__
    dependency_paths = {str(n.safe_path(inspect.getsourcefile(imported[key]))) for key in
                        ('freeze', 'evidence_ids', 'validate_prediction', 'validate_query', 'visible_unsure_index')}
    n.need({str(n.safe_path(item['path'])) for item in authority['native_scorer_dependencies']} == dependency_paths,
           'Exact loaded native scorer dependency closure')
    for item in authority['native_scorer_dependencies']: n.verify_proof(item)
    if native_scorer_archive is None:
        n.need(authority['native_scorer_archive'] is None, 'Original scorer source archive required')
    else:
        n.need(encode(native_scorer_archive.manifest_proof) == authority['native_scorer_archive'], 'Explicit original scorer archive binding')
    return authority


def _inputs(authority, native_scorer_archive):
    descriptor = authority['original_inputs']
    manifest = n.decode(n.verify_proof(descriptor))
    if authority['purpose'] == 'production':
        return original_inputs.verify(descriptor['path'], descriptor['sha256'], native_scorer_archive=native_scorer_archive)
    n.need(set(manifest) == {'kind', 'role', 'queries', 'references', 'groups', 'annotations'} and
        manifest['kind'] == 'sc05_fictional_evaluation_inputs_v1' and manifest['role'] == 'evaluation_only',
        'Invented inputs must remain explicitly fictional and evaluation-only')
    n.need(len(manifest['queries']) == 2 and set(manifest['annotations']) == {q['id'] for q in manifest['queries']},
           'Complete invented input schedule')
    return manifest


def _input_proofs(authority, inputs):
    """Retain the evaluator's complete original file closure for final recheck."""
    found = {}
    def visit(value):
        if isinstance(value, dict):
            if set(value) == {'path', 'sha256', 'bytes'}:
                key = value['path']; old = found.setdefault(key, value)
                n.need(old == value, 'Conflicting evaluator input byte proofs')
            else:
                for child in value.values(): visit(child)
        elif isinstance(value, list):
            for child in value: visit(child)
    visit(authority['original_inputs'])
    if authority['purpose'] == 'production':
        manifest = inputs['manifest']; selected = dict(manifest)
        # The explicitly supplied source archive replaces only this unavailable
        # historical code locator, never reference keys or original task data.
        if authority['native_scorer_archive'] is not None:
            selected.pop('native_scorer', None)
            visit(inputs['native_scorer_binding']['archived'])
            visit(inputs['native_scorer_binding']['archive'])
        visit(selected)
        projected = n.decode(n.verify_proof(manifest['annotation_projection']))
        visit(projected)
    for item in found.values(): n.verify_proof(item)
    return list(found.values())


def evaluate(value, authority_descriptor, *, native_scorer, native_scorer_archive=None):
    """Read references only after all sealed execution/source/native joins pass."""
    value = revalidate(value)
    authority = _authority(value, authority_descriptor, native_scorer, native_scorer_archive)
    inputs = _inputs(authority, native_scorer_archive)
    input_proofs = _input_proofs(authority, inputs)
    report = encode(value.report)
    n.need(inputs['queries'] == report['queries'], 'Original option/order/query membership unchanged')
    summary = statistics.summarize(report['queries'], inputs['references'], report['records'], report['evidence_ids'],
        report['critics'], inputs['groups'], purpose=report['purpose'])
    comparisons = []
    keys = ('scheduled_count', 'counts', 'raw_metrics', 'checked_metrics', 'raw_precision_defined',
            'checked_precision_defined', 'producer_status_counts', 'check_status_counts', 'case_results')
    for arm in ('one_pass', 'repair', 'removal'):
        observed = encode(native_scorer(report['queries'], inputs['references'], report['records'][arm],
                                       evidence_ids_by_query=report['evidence_ids'][arm]))
        independent = summary['removal_diagnostic']['native'] if arm == 'removal' else summary['native'][arm]
        for key in keys:
            n.need(n.canonical(observed[key]) == n.canonical(independent[key]), 'Independent/native score mismatch '+arm+' '+key)
        comparisons.append(dict(condition=arm, checked_fields=list(keys), native=observed))
    ids = [q['id'] for q in report['queries']]
    source_metrics = {level: paper_metrics(ids, inputs['annotations'],
        {row['id']: row[level+'_dois'] for row in report['source_cases']}) for level in ('retained', 'pool', 'selected')}
    original_source_metrics = {level: paper_metrics(ids, inputs['annotations'],
        {row['id']: row['original_'+level+'_dois'] for row in report['source_cases']}) for level in ('retained', 'pool', 'selected')}
    # Native critique-only scores are exactly the original native records; no fourth generation/scoring identity is invented.
    summary.update(provenance_validated=True, native_agreement=dict(status='PASS', generated_conditions_checked=3,
        original_records_reused_for_critique_only=True, comparisons=comparisons), source_metrics=source_metrics,
        source_metrics_scope='Eligible merged repair sources; original source metrics apply equally to one-pass and critique-only.',
        original_source_metrics=original_source_metrics,
        source_context_changes=dict(scheduled_count=len(ids), changed=sum(row['source_context_changed'] for row in report['source_cases']),
            unchanged=sum(not row['source_context_changed'] for row in report['source_cases']),
            unavailable_refinement=sum(not row['refinement_available'] for row in report['source_cases'])),
        source_cases=report['source_cases'], case_products=report['case_products'],
        incremental_resources=report['incremental_resources'], historical_and_logical_resources=encode(value.envelope['resources']),
        logical_condition_resources=report['logical_resources'],
        execution_proof=dict(root=value.root, receipt_sha256=value.receipt_sha256),
        evaluator_authority=encode(authority_descriptor), scientific_support_verified=False)
    for native_score in summary['native'].values(): native_score['provenance_validated'] = True
    summary['removal_diagnostic']['native']['provenance_validated'] = True
    revalidate(value)
    n.verify_proof(encode(authority_descriptor))
    for item in (authority['original_inputs'], authority['endpoint_freeze'], authority['native_scorer'],
                 *authority['native_scorer_dependencies']): n.verify_proof(item)
    for item in input_proofs: n.verify_proof(item)
    return freeze(summary)
