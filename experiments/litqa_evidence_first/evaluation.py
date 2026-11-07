"""Evaluate a separately frozen full condition after independent reconstruction.

The earlier failed repair is exposure history, never a replacement answer or an
observation in the new condition. Numerical summaries retain the original
endpoints and all scheduled questions. Reference access requires an issued
evidence-first capability; the pure arithmetic helper grants no such access.

The six-case evaluator branch uses separate invented substantive reference keys
for engineering tests. Actual synthetic native qualification, including conflict
and empty-context unsure answers, uses the expectation checker instead of these
LitQA correctness estimands.
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
AUTHORITY_KIND = 'sc05_evidence_first_evaluation_authority_v1'
REPORT_KIND = 'sc05_evidence_first_evaluation_v1'
FICTIONAL_INPUT_KIND = 'sc05_evidence_first_fictional_evaluation_inputs_v1'


def _same(left, right):
    return n.canonical(encode(left)) == n.canonical(encode(right))


def _revalidate(value):
    from . import reconstruct
    return reconstruct.revalidate(value)


def _authority(value, descriptor, native_scorer, native_scorer_archive):
    n.need(isinstance(descriptor, Mapping) and set(descriptor) == {'path', 'sha256', 'bytes'},
           'External evidence-first evaluation authority required')
    authority = n.decode(n.verify_proof(encode(descriptor)))
    fields = {'kind', 'role', 'purpose', 'created_at_utc', 'producer', 'baseline_acceptance',
              'original_producer_descriptor', 'original_inputs', 'endpoint_freeze', 'method',
              'protocol', 'native_scorer', 'native_scorer_dependencies', 'native_scorer_archive'}
    n.need(set(authority) == fields and authority['kind'] == AUTHORITY_KIND and
           authority['role'] == 'evaluation_only', 'Explicit evidence-first evaluator authority')
    n.need(authority['purpose'] == value.report['purpose'] and
           _same(authority['producer'], value.envelope['producer']), 'New execution authority differs')
    source.lineage.aware(authority['created_at_utc'])
    for key in ('baseline_acceptance', 'original_producer_descriptor', 'original_inputs',
                'endpoint_freeze', 'method', 'protocol'):
        n.need(_same(authority[key], value.envelope[key]), 'Execution-bound evaluator ' + key + ' differs')
    method = authority['method']
    n.need(isinstance(method, dict) and set(method) == {'proof', 'identity'} and
           method['identity'] == value.report['method_identity'], 'Exact new method identity required')
    method_value = n.decode(n.verify_proof(method['proof']))
    n.need(n.digest(n.canonical(method_value)) == method['identity'], 'New method bytes differ')
    protocol = n.decode(n.verify_proof(authority['protocol']))
    n.need(protocol['kind'] == 'sc05_evidence_first_protocol_v1' and
           _same(protocol['original_inputs'], authority['original_inputs']) and
           _same(protocol['endpoints'], authority['endpoint_freeze']) and
           _same(n.decode(n.verify_proof(protocol['method'])), method_value),
           'Prospective method, endpoint and original-input bindings differ')
    declared = source.lineage.aware(protocol['created_at_utc'])
    n.need(declared == source.lineage.aware(value.envelope['protocol_declared_at_utc']) and
           declared <= source.lineage.aware(value.envelope['new_started_at_utc']),
           'New method protocol must precede new execution')
    endpoints = n.decode(n.verify_proof(authority['endpoint_freeze']))
    expected = original_evaluation.endpoint_contract(
        endpoints['declared_at_utc'], endpoints['implementation_note'], endpoints['endpoint_addendum'])
    n.need(_same(endpoints, expected) and source.lineage.aware(endpoints['declared_at_utc']) <=
           source.lineage.aware(value.envelope['original_started_at_utc']),
           'Unchanged endpoints must precede original execution')
    n.need(callable(native_scorer) and getattr(native_scorer, '__name__', None) == 'evaluate_schedule',
           'Pinned native scorer function required')
    scorer_path = inspect.getsourcefile(native_scorer)
    n.need(scorer_path is not None and n.safe_path(scorer_path) ==
           n.safe_path(authority['native_scorer']['path']), 'Actual native scorer differs')
    n.verify_proof(authority['native_scorer'])
    dependencies = authority['native_scorer_dependencies']
    imported = native_scorer.__globals__
    expected_paths = {str(n.safe_path(inspect.getsourcefile(imported[key]))) for key in
                     ('freeze', 'evidence_ids', 'validate_prediction', 'validate_query', 'visible_unsure_index')}
    n.need(isinstance(dependencies, list) and len(dependencies) == len(expected_paths) and
           {str(n.safe_path(item['path'])) for item in dependencies} == expected_paths,
           'Exact loaded native scorer dependency closure required')
    for proof in dependencies:
        n.verify_proof(proof)
    if native_scorer_archive is None:
        n.need(authority['native_scorer_archive'] is None, 'Original scorer archive required')
    else:
        n.need(_same(native_scorer_archive.manifest_proof, authority['native_scorer_archive']),
               'Original scorer archive differs')
    controls = [method['proof'], authority['protocol'], protocol['method'],
                endpoints['implementation_note'], endpoints['endpoint_addendum']]
    return authority, controls


def _inputs(authority, native_scorer_archive, original_started_at):
    if authority['purpose'] == 'production':
        proof = authority['original_inputs']
        return original_evaluation.original_inputs.verify(proof['path'], proof['sha256'],
            answer_started_at=original_started_at, native_scorer_archive=native_scorer_archive)
    manifest = n.decode(n.verify_proof(authority['original_inputs']))
    n.need(set(manifest) == {'kind', 'role', 'queries', 'references', 'groups', 'annotations'} and
           manifest['kind'] == FICTIONAL_INPUT_KIND and manifest['role'] == 'evaluation_only' and
           len(manifest['queries']) == 6 and
           set(manifest['annotations']) == {q['id'] for q in manifest['queries']},
           'Exactly six invented evaluator-only cases required')
    return manifest


def score_records(report, inputs, *, native_scorer):
    """Pure fixed estimands, without execution, source or scientific attestation."""
    report, inputs = encode(report), encode(inputs)
    n.need(_same(inputs['queries'], report['queries']), 'Original options, order or membership changed')
    summary = statistics.summarize(report['queries'], inputs['references'], report['records'],
        report['evidence_ids'], report['critics'], inputs['groups'], purpose=report['purpose'])
    comparisons = []
    keys = ('scheduled_count', 'counts', 'raw_metrics', 'checked_metrics', 'raw_precision_defined',
            'checked_precision_defined', 'producer_status_counts', 'check_status_counts', 'case_results')
    for arm in ('one_pass', 'repair', 'removal'):
        observed = encode(native_scorer(report['queries'], inputs['references'], report['records'][arm],
                                       evidence_ids_by_query=report['evidence_ids'][arm]))
        independent = summary['removal_diagnostic']['native'] if arm == 'removal' else summary['native'][arm]
        for key in keys:
            n.need(_same(observed[key], independent[key]), 'Independent/native evidence-first score mismatch: ' + arm + ' ' + key)
        comparisons.append(dict(condition=arm, checked_fields=list(keys), native=observed))
    ids = [q['id'] for q in report['queries']]
    sources = report['source_cases']
    n.need([row['id'] for row in sources] == ids and
           [row['id'] for row in report['case_products']] == ids, 'Full ordered source and product schedules required')
    n.need(all(type(row[key]) is bool for row in sources for key in
               ('source_context_changed', 'refinement_available')), 'Typed source missingness flags required')
    metrics = {level: paper_metrics(ids, inputs['annotations'],
        {row['id']: row[level + '_dois'] for row in sources}) for level in ('retained', 'pool', 'selected')}
    original_metrics = {level: paper_metrics(ids, inputs['annotations'],
        {row['id']: row['original_' + level + '_dois'] for row in sources}) for level in ('retained', 'pool', 'selected')}
    summary.update(kind=REPORT_KIND, method_identity=report['method_identity'],
        condition_scope='Separate full evidence-first condition; all new repair/removal dispositions are retained.',
        native_agreement=dict(status='PASS', generated_conditions_checked=3,
            original_records_reused_for_critique_only=True, comparisons=comparisons),
        source_metrics=metrics, original_source_metrics=original_metrics,
        source_metrics_scope='Unchanged sealed source ancestors; the new condition performs no retrieval.',
        source_context_changes=dict(scheduled_count=len(ids),
            changed=sum(row['source_context_changed'] for row in sources),
            unchanged=sum(not row['source_context_changed'] for row in sources),
            unavailable_refinement=sum(not row['refinement_available'] for row in sources)),
        source_cases=sources, case_products=report['case_products'],
        incremental_resources=report['incremental_resources'],
        logical_condition_resources=report['logical_resources'],
        accounting_scope='New physical calls are separate from reused baseline/critic/source attribution and '
                         'earlier failed-condition sunk costs. Logical condition costs overlap; do not sum them.',
        scientific_support_verified=False)
    summary['limitations'].append('The method was proposed after a failed synthetic gate; prior failed-condition exposure is retained separately.')
    return freeze(summary)


def evaluate(value, authority_descriptor, *, native_scorer, native_scorer_archive=None):
    """Open references only after issued whole-run source/native verification."""
    value = _revalidate(value)
    authority, controls = _authority(value, authority_descriptor, native_scorer, native_scorer_archive)
    inputs = _inputs(authority, native_scorer_archive, value.envelope['original_started_at_utc'])
    input_proofs = original_evaluation._input_proofs(authority, inputs)
    result = encode(score_records(value.report, inputs, native_scorer=native_scorer))
    result.update(provenance_validated=True,
        execution_proof=encode(value.envelope['producer']),
        original_producer_descriptor=encode(value.envelope['original_producer_descriptor']),
        historical_and_logical_resources=encode(value.envelope['resources']),
        evaluator_authority=encode(authority_descriptor), method=encode(authority['method']),
        protocol=encode(authority['protocol']), earlier_failed_condition_preserved=True,
        old_repair_outputs_adopted=False)
    for scores in result['native'].values():
        scores['provenance_validated'] = True
    result['removal_diagnostic']['native']['provenance_validated'] = True
    _revalidate(value)
    n.verify_proof(encode(authority_descriptor))
    for proof in (authority['original_inputs'], authority['endpoint_freeze'], authority['native_scorer'],
                  *authority['native_scorer_dependencies'], *controls, *input_proofs):
        n.verify_proof(proof)
    return freeze(result)
