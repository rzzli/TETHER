"""Evaluate a fully reconstructed continuation without relabelling its parent.

Original and continued calls keep separate physical identities. Reference inputs
remain closed until the new recovery reader has issued and revalidated its own
capability; an incomplete version-one execution is never promoted to that type.
"""
from collections.abc import Mapping
import inspect

from tether_engine.serde import encode, freeze
from experiments.litqa_analysis.scoring import paper_metrics
from experiments.litqa_refinement import evaluation as original_evaluation
from experiments.litqa_refinement import statistics
from experiments.litqa_refinement import native_evaluation as native
from experiments.litqa_refinement import source_evaluation as source

n = native.n
AUTHORITY_KIND = 'sc05_refinement_recovery_evaluation_authority_v1'
REPORT_KIND = 'sc05_refinement_recovery_evaluation_v1'


def _revalidate(value):
    # The independent recovery reader owns capability issuance. Keeping this
    # import local also keeps the pure scoring helper independent of that reader.
    from . import reconstruct
    return reconstruct.revalidate(value)


def _authority(value, descriptor, native_scorer, native_scorer_archive):
    n.need(isinstance(descriptor, Mapping) and set(descriptor) == {'path', 'sha256', 'bytes'},
           'External recovery evaluation authority required')
    authority = n.decode(n.verify_proof(encode(descriptor)))
    fields = {'kind', 'role', 'purpose', 'created_at_utc', 'producer', 'baseline_acceptance',
              'original_producer_descriptor', 'original_inputs', 'endpoint_freeze',
              'native_scorer', 'native_scorer_dependencies', 'native_scorer_archive'}
    n.need(set(authority) == fields and authority['kind'] == AUTHORITY_KIND
           and authority['role'] == 'evaluation_only', 'Explicit recovery evaluator authority')
    n.need(authority['purpose'] == value.report['purpose'] and authority['producer'] ==
           dict(root=value.root, receipt_sha256=value.receipt_sha256),
           'Recovery execution and evaluator authority differ')
    source.lineage.aware(authority['created_at_utc'])
    n.need(authority['baseline_acceptance'] == encode(value.envelope['baseline_acceptance']),
           'Original accepted baseline authority differs')
    n.need(authority['original_producer_descriptor'] ==
           encode(value.envelope['original_producer_descriptor']), 'Failed parent binding differs')
    endpoints = n.decode(n.verify_proof(authority['endpoint_freeze']))
    expected = original_evaluation.endpoint_contract(
        endpoints['declared_at_utc'], endpoints['implementation_note'], endpoints['endpoint_addendum'])
    n.need(endpoints == expected and source.lineage.aware(endpoints['declared_at_utc']) <=
           source.lineage.aware(value.envelope['original_started_at_utc']),
           'Endpoints must precede original production, not merely its continuation')
    n.need(callable(native_scorer) and getattr(native_scorer, '__name__', None) == 'evaluate_schedule',
           'Pinned native scorer function required')
    scorer_path = inspect.getsourcefile(native_scorer)
    n.need(scorer_path is not None and n.safe_path(scorer_path) ==
           n.safe_path(authority['native_scorer']['path']), 'Actual native scorer differs')
    n.verify_proof(authority['native_scorer'])
    dependencies = authority['native_scorer_dependencies']
    n.need(isinstance(dependencies, list) and dependencies, 'Native scorer dependency proofs required')
    imported = native_scorer.__globals__
    expected_paths = {str(n.safe_path(inspect.getsourcefile(imported[key]))) for key in
                      ('freeze', 'evidence_ids', 'validate_prediction', 'validate_query', 'visible_unsure_index')}
    n.need(len(dependencies) == len(expected_paths) and
           {str(n.safe_path(item['path'])) for item in dependencies} == expected_paths,
           'Exact loaded native scorer dependency closure required')
    for item in dependencies:
        n.verify_proof(item)
    if native_scorer_archive is None:
        n.need(authority['native_scorer_archive'] is None, 'Original scorer archive required')
    else:
        n.need(encode(native_scorer_archive.manifest_proof) == authority['native_scorer_archive'],
               'Native scorer archive differs')
    return authority


def score_records(report, inputs, *, native_scorer):
    """Pure all-case quantities, without issuing scientific/provenance authority.

    Operational errors remain null predictions in the unchanged native scorer.
    This function neither reads input files nor grants reference access; the
    capability-gated ``evaluate`` entry point owns those operations.
    """
    report, inputs = encode(report), encode(inputs)
    n.need(inputs['queries'] == report['queries'], 'Original options, order or membership changed')
    summary = statistics.summarize(
        report['queries'], inputs['references'], report['records'], report['evidence_ids'],
        report['critics'], inputs['groups'], purpose=report['purpose'])
    comparisons = []
    keys = ('scheduled_count', 'counts', 'raw_metrics', 'checked_metrics', 'raw_precision_defined',
            'checked_precision_defined', 'producer_status_counts', 'check_status_counts', 'case_results')
    for arm in ('one_pass', 'repair', 'removal'):
        observed = encode(native_scorer(report['queries'], inputs['references'], report['records'][arm],
                                       evidence_ids_by_query=report['evidence_ids'][arm]))
        independent = summary['removal_diagnostic']['native'] if arm == 'removal' else summary['native'][arm]
        for key in keys:
            n.need(n.canonical(observed[key]) == n.canonical(independent[key]),
                   'Independent/native recovery score mismatch: ' + arm + ' ' + key)
        comparisons.append(dict(condition=arm, checked_fields=list(keys), native=observed))
    ids = [query['id'] for query in report['queries']]
    source_cases = report['source_cases']
    n.need([row['id'] for row in source_cases] == ids, 'Full ordered source case schedule required')
    current_metrics = {level: paper_metrics(ids, inputs['annotations'],
        {row['id']: row[level + '_dois'] for row in source_cases}) for level in ('retained', 'pool', 'selected')}
    original_metrics = {level: paper_metrics(ids, inputs['annotations'],
        {row['id']: row['original_' + level + '_dois'] for row in source_cases})
        for level in ('retained', 'pool', 'selected')}
    summary.update(
        kind=REPORT_KIND, provenance_validated=False,
        native_agreement=dict(status='PASS', generated_conditions_checked=3,
            original_records_reused_for_critique_only=True, comparisons=comparisons),
        source_metrics=current_metrics, original_source_metrics=original_metrics,
        source_metrics_scope='Original sealed merged repair sources; continuation adds no retrieval or context.',
        source_context_changes=dict(scheduled_count=len(ids),
            changed=sum(row['source_context_changed'] for row in source_cases),
            unchanged=sum(not row['source_context_changed'] for row in source_cases),
            unavailable_refinement=sum(not row['refinement_available'] for row in source_cases)),
        source_cases=source_cases, case_products=report['case_products'],
        incremental_resources=report['incremental_resources'],
        logical_condition_resources=report['logical_resources'],
        accounting_scope='Qualified measured totals, unverified reported usage and reservation bounds remain separate. '
                         'An inherited failure is not retroactively completed or assigned an answer.',
        scientific_support_verified=False)
    return freeze(summary)


def evaluate(value, authority_descriptor, *, native_scorer, native_scorer_archive=None):
    """Open original references only after full independent recovery verification."""
    value = _revalidate(value)
    authority = _authority(value, authority_descriptor, native_scorer, native_scorer_archive)
    # These unchanged helpers verify original task/reference/group/annotation
    # files and the existing native-scorer archive. No new reference is derived.
    inputs = original_evaluation._inputs(authority, native_scorer_archive)
    input_proofs = original_evaluation._input_proofs(authority, inputs)
    result = encode(score_records(value.report, inputs, native_scorer=native_scorer))
    result.update(
        provenance_validated=True,
        execution_proof=dict(root=value.root, receipt_sha256=value.receipt_sha256),
        original_producer_descriptor=encode(value.envelope['original_producer_descriptor']),
        historical_and_logical_resources=encode(value.envelope['resources']),
        evaluator_authority=encode(authority_descriptor),
        original_failure_preserved=True, completed_or_entered_calls_repeated=False)
    for scores in result['native'].values():
        scores['provenance_validated'] = True
    result['removal_diagnostic']['native']['provenance_validated'] = True
    _revalidate(value)
    n.verify_proof(encode(authority_descriptor))
    for proof in (authority['original_inputs'], authority['endpoint_freeze'], authority['native_scorer'],
                  *authority['native_scorer_dependencies'], *input_proofs):
        n.verify_proof(proof)
    return freeze(result)
