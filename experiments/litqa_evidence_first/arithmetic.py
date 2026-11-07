"""Pure independent report arithmetic; no files, reference keys or model access.

Per-case correctness flags are upstream inputs. Recounting them does not judge
truth, replay native responses, or authenticate sources. Those guarantees belong
to the separately issued whole-run capability and native scorer. The resampler
below is a separate two-column implementation; no producer/statistics/scorer
module is imported. Only Python standard-library mathematical primitives are
shared. The declared endpoints, seed and percentile convention are unchanged.
"""
from collections import Counter
from collections.abc import Mapping
from functools import lru_cache
import hashlib
import json
import math
import random

SEED, DRAWS = 20261106, 10000
CONDITIONS = ('one_pass', 'critique_only', 'repair')
CONTRASTS = (('critique_only_minus_one_pass', 'one_pass', 'critique_only'),
             ('repair_minus_one_pass', 'one_pass', 'repair'),
             ('repair_minus_critique_only', 'critique_only', 'repair'))
FIELDS = ('generation_calls', 'measured_input_tokens', 'measured_output_tokens',
          'reserved_input_tokens', 'reserved_output_tokens', 'source_http_requests',
          'measured_response_bytes', 'safety_accounted_bytes')
MODEL_FIELDS = FIELDS[:5] + ('provider_cost_usd',)
HTTP_FIELDS = ('requests', 'measured_response_bytes', 'safety_accounted_bytes', 'unknown_transfer_upper_bytes')


def need(value, message):
    if not value:
        raise ValueError(message)


def plain(value):
    if isinstance(value, Mapping):
        return {key: plain(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(child) for child in value]
    return value


def canonical(value):
    return json.dumps(plain(value), ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf8')


def fingerprint(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def equal(actual, expected, label):
    if isinstance(expected, dict):
        need(type(actual) is dict and set(actual) == set(expected), label + ': keys')
        for key in expected:
            equal(actual[key], expected[key], label + '.' + key)
    elif isinstance(expected, list):
        need(type(actual) is list and len(actual) == len(expected), label + ': length')
        for index, (left, right) in enumerate(zip(actual, expected)):
            equal(left, right, label + '[' + str(index) + ']')
    elif type(expected) is float:
        need(type(actual) in (int, float) and math.isfinite(actual) and actual == expected, label + ': finite number')
    else:
        need(type(actual) is type(expected) and actual == expected, label + ': value/type')


def subset(actual, expected, label):
    need(type(actual) is dict and set(expected) <= set(actual), label + ': missing fields')
    for key, value in expected.items():
        equal(actual[key], value, label + '.' + key)


def ordered(rows, ids, label):
    need(type(rows) is list and all(type(row) is dict for row in rows) and
         [row.get('id') for row in rows] == ids, label + ': complete ordered schedule')


def ratio(numerator, denominator, *, nullable=False):
    return numerator / denominator if denominator else (None if nullable else 0.0)


def _native(rows, ids):
    ordered(rows, ids, 'Native rows')
    counts = Counter(dict.fromkeys(('produced', 'producer_failures', 'accepted', 'rejected', 'check_errors',
        'check_not_run', 'raw_answered', 'checked_answered', 'raw_correct', 'correct_and_admitted',
        'correct_but_rejected', 'correct_not_admitted', 'native_unsure', 'accepted_unsure',
        'incorrect_and_admitted', 'incorrect_substantive_and_admitted', 'parse_failures', 'produced_or_parse_failure'), 0))
    producers, checks, reasons = Counter(), Counter(), Counter()
    failures = {'parse_failure', 'timeout', 'error', 'interrupted', 'unexecuted', 'input_unavailable'}
    for row in rows:
        ps, cs, prediction, correct = (row[key] for key in ('producer_status', 'check_status', 'prediction', 'raw_correct'))
        need(ps in failures | {'produced'} and cs in ('accepted', 'rejected', 'error', 'not_run') and
             type(correct) is bool, 'Native status and upstream binary correctness')
        produced, admitted = ps == 'produced', cs == 'accepted'
        if produced:
            need(type(prediction) is dict and set(prediction) == {'answer_index', 'evidence_ids'} and
                 type(prediction['answer_index']) is int and 0 <= prediction['answer_index'] <= 25 and
                 type(row['native_unsure']) is bool and not (correct and row['native_unsure']), 'Native prediction/unsure shape')
            cites = prediction['evidence_ids']
            need(type(cites) is list and all(type(c) is str and c for c in cites) and len(cites) == len(set(cites)), 'Unique citations')
            need((row['reason'] is None) == admitted, 'Native admission/reason relation')
        else:
            need(prediction is None and cs == 'not_run' and row['native_unsure'] is None and not correct and
                 type(row['reason']) is str and row['reason'], 'Operational failure remains null and in denominator')
        need(row['reason'] is None or type(row['reason']) is str and row['reason'], 'Explicit native reason')
        unsure = row['native_unsure'] is True
        answered = produced and not unsure
        flags = dict(produced=produced, producer_failures=not produced, accepted=admitted, rejected=cs == 'rejected',
            check_errors=cs == 'error', check_not_run=cs == 'not_run', raw_answered=answered,
            checked_answered=answered and admitted, raw_correct=correct, correct_and_admitted=correct and admitted,
            correct_but_rejected=correct and cs == 'rejected', correct_not_admitted=correct and not admitted,
            native_unsure=unsure, accepted_unsure=unsure and admitted, incorrect_and_admitted=admitted and not correct,
            incorrect_substantive_and_admitted=admitted and answered and not correct, parse_failures=ps == 'parse_failure',
            produced_or_parse_failure=ps in ('produced', 'parse_failure'))
        for key in ('raw_answered', 'checked_answered', 'correct_and_admitted'):
            equal(row[key], flags[key], 'Native per-case ' + key)
        counts.update({key: int(value) for key, value in flags.items()})
        producers[ps] += 1; checks[cs] += 1
        if row['reason'] is not None: reasons[row['reason']] += 1
    result = dict(scheduled_count=len(ids), counts=dict(counts), producer_status_counts=dict(producers),
        check_status_counts=dict(checks), reason_counts=dict(reasons), case_results=rows,
        unchanged_raw_checked=counts['accepted'], provenance_validated=True)
    for label, correct, answered in (('raw', counts['raw_correct'], counts['raw_answered']),
                                     ('checked', counts['correct_and_admitted'], counts['checked_answered'])):
        result[label + '_metrics'] = dict(accuracy=correct / len(ids), precision=ratio(correct, answered), coverage=answered / len(ids))
        result[label + '_precision_defined'] = bool(answered)
        result['statistical_' + label + '_precision'] = ratio(correct, answered, nullable=True)
    return result


def _decision(row, critic):
    # Complete critique bodies are retained by the source capability. Only this
    # explicit status/support projection participates in numeric selection.
    if set(critic) == {'id', 'native_status', 'decoded'}:
        need(critic['id'] == row['id'], 'Critic identity')
    else:
        need(set(critic) == {'kind', 'query_sha256', 'candidate_sha256', 'source_context_sha256',
            'decoded', 'native_status', 'native_call_sha256', 'is_scientific_evidence'} and
            critic['kind'] == 'model_generated_critique_context_v1' and critic['is_scientific_evidence'] is False,
            'Retained typed critic context')
    need(critic['native_status'] in ('completed', 'codec_failure', 'capacity') and
         (critic['decoded'] is not None) == (critic['native_status'] == 'completed'), 'Critic disposition')
    support = None
    if critic['decoded'] is not None:
        support = critic['decoded']['support']
        need(support in ('supported', 'contradicted', 'insufficient', 'not_assessable'), 'Support category')
    if row['producer_status'] != 'produced': return 'not_applicable', 'original_candidate_unavailable'
    if row['native_unsure']: return 'not_applicable', 'original_native_unsure'
    if row['check_status'] != 'accepted': return 'withhold', 'original_not_admitted'
    if support is None: return 'withhold', 'critic_unavailable'
    return ('keep', 'critic_supported') if support == 'supported' else ('withhold', 'critic_' + support)


def _condition(rows, keeps):
    need(all(type(keep) is bool and (not keep or row['checked_answered']) for row, keep in zip(rows, keeps)), 'Retention cannot upgrade answers')
    cases = [dict(id=row['id'], raw_correct=row['raw_correct'], retained=keep,
                  correct_retained=keep and row['raw_correct']) for row, keep in zip(rows, keeps)]
    retained = sum(keeps); correct = sum(row['correct_retained'] for row in cases); size = len(rows)
    return dict(scheduled_count=size, retained=retained, correct_retained=correct, incorrect_retained=retained-correct,
        raw_accuracy=sum(row['raw_correct'] for row in rows) / size, correct_retained_yield=correct / size,
        retained_coverage=retained / size, statistical_retained_precision=ratio(correct, retained, nullable=True),
        retained_precision_defined=bool(retained), case_results=cases)


def _transitions(before, after):
    def state(row):
        if row['producer_status'] != 'produced': return 'unproduced'
        if row['native_unsure']: return 'native_unsure'
        return 'correct_substantive' if row['raw_correct'] else 'wrong_substantive'
    rows = []
    for a, b in zip(before, after):
        need(a['id'] == b['id'], 'Transition schedule')
        origin, destination = state(a), state(b)
        rows.append(dict(id=a['id'], origin=origin, destination=destination,
            both_candidates_produced=a['producer_status'] == b['producer_status'] == 'produced',
            raw_answer_index_changed=a['prediction']['answer_index'] != b['prediction']['answer_index']
                if a['prediction'] is not None and b['prediction'] is not None else None,
            repaired_wrong_substantive=origin == 'wrong_substantive' and b['raw_correct'],
            recovered_original_operational_failure=origin == 'unproduced' and b['raw_correct'],
            recovered_original_unsure=origin == 'native_unsure' and b['raw_correct'],
            damaged_correct=origin == 'correct_substantive' and not b['raw_correct'],
            persistent_wrong_substantive=origin == destination == 'wrong_substantive', repaired_answer_admitted=b['correct_and_admitted']))
    names = ('repaired_wrong_substantive', 'recovered_original_operational_failure', 'recovered_original_unsure',
             'damaged_correct', 'persistent_wrong_substantive')
    return dict(scheduled_count=len(rows), matrix=dict(Counter(row['origin'] + '_to_' + row['destination'] for row in rows)),
        case_results=rows, counts={name: sum(row[name] for row in rows) for name in names},
        raw_answer_changes=dict(both_produced=sum(row['both_candidates_produced'] for row in rows),
            answer_index_changed=sum(row['raw_answer_index_changed'] is True for row in rows),
            answer_index_unchanged=sum(row['raw_answer_index_changed'] is False for row in rows),
            unavailable_pair=sum(row['raw_answer_index_changed'] is None for row in rows)))


@lru_cache(maxsize=64)
def _interval_bytes(ids, left, right, groups):
    need(len(ids) == len(left) == len(right) and all(type(v) is bool for v in left + right), 'Paired binary outcomes')
    index = {key: i for i, key in enumerate(ids)}
    flat = [key for group in groups for key in group]
    need(groups and all(groups) and len(flat) == len(ids) == len(set(flat)) and set(flat) == set(ids), 'Complete bootstrap groups')
    aggregates = [(len(group), sum(left[index[key]] for key in group), sum(right[index[key]] for key in group)) for group in groups]
    a, b = sum(left) / len(ids), sum(right) / len(ids)
    result = dict(case_count=len(ids), group_count=len(groups), group_sizes=[len(group) for group in groups], seed=SEED,
        requested_replicates=DRAWS, completed_replicates=0, uncertainty_estimable=len(groups) > 1,
        method='paired cluster resampling; ratio recomputed per draw; linear percentile interval',
        baseline=a, new=b, estimate=b-a, ci95=None,
        limitation='One independent group cannot estimate between-group uncertainty.' if len(groups) == 1 else None)
    if len(groups) > 1:
        rng = random.Random(SEED); samples = []
        for _ in range(DRAWS):
            size = a_count = b_count = 0
            for _ in groups:
                count, a_value, b_value = aggregates[rng.randrange(len(groups))]
                size += count; a_count += a_value; b_count += b_value
            samples.append(b_count / size - a_count / size)
        samples.sort()
        def quantile(p):
            at = (len(samples) - 1) * p; low, high = math.floor(at), math.ceil(at)
            return samples[low] + (samples[high] - samples[low]) * (at-low)
        result.update(completed_replicates=DRAWS, ci95=[quantile(.025), quantile(.975)])
    return canonical(result)


def _interval(ids, left, right, groups):
    # Immutable cached bytes prevent a returned mapping poisoning later checks.
    return json.loads(_interval_bytes(tuple(ids), tuple(left), tuple(right), tuple(tuple(g) for g in groups)))


def _doi(rows, ids, observed):
    ordered(rows, ids, 'DOI annotation rows'); cases = []
    for row in rows:
        annotations = row['annotated_ids']; found = observed[row['id']]
        need(type(annotations) is list and annotations == sorted(set(annotations)) and
             all(type(x) is str and x for x in annotations), 'Unique canonical annotations')
        need(type(found) is list and len(found) == len(set(found)) and all(type(x) is str and x for x in found), 'Unique observed DOIs')
        matches = sorted(set(annotations) & set(found))
        cases.append(dict(id=row['id'], annotated_ids=annotations, retrieved_ids=sorted(found), matched_ids=matches,
            annotated_source_recall=ratio(len(matches), len(annotations), nullable=True)))
    annotation_count = sum(len(row['annotated_ids']) for row in cases)
    matched_count = sum(len(row['matched_ids']) for row in cases)
    any_hit = sum(bool(row['matched_ids']) for row in cases)
    all_hit = sum(bool(row['annotated_ids']) and row['annotated_ids'] == row['matched_ids'] for row in cases)
    return dict(scheduled_count=len(ids), annotated_source_count=annotation_count, matched_annotated_source_count=matched_count,
        annotated_source_recall=ratio(matched_count, annotation_count, nullable=True),
        questions_with_annotations=sum(bool(row['annotated_ids']) for row in cases),
        questions_without_annotations=sum(not row['annotated_ids'] for row in cases),
        questions_with_any_annotated_source_hit=any_hit, questions_with_all_annotated_sources=all_hit,
        any_hit_per_scheduled=any_hit / len(ids), all_hit_per_scheduled=all_hit / len(ids),
        semantic_support='unevaluated', case_results=cases)


def _usage(row, label, *, cells=None, no_http=False):
    need(type(row) is dict and set(row) == set(FIELDS) and
         all(type(value) is int and value >= 0 for value in row.values()), label + ': nonnegative integer usage')
    need(row['measured_input_tokens'] <= row['reserved_input_tokens'] and
         row['measured_output_tokens'] <= row['reserved_output_tokens'] and
         row['measured_response_bytes'] <= row['safety_accounted_bytes'], label + ': measured/reserved relation')
    if cells is not None:
        need(row['generation_calls'] <= cells and row['reserved_input_tokens'] <= 16128 * cells and
             row['reserved_output_tokens'] <= 256 * cells, label + ': generation/token limits')
    if no_http:
        need(all(row[key] == 0 for key in FIELDS[5:]), label + ': no new source HTTP')
    return row


def _zero_cost(value, label):
    need(type(value) in (int, float) and math.isfinite(value) and value == 0, label + ': zero finite cost')


def _sum(rows, fields=FIELDS):
    return {key: sum(row[key] for row in rows) for key in fields}


def _resources(report, ids):
    size = len(ids); phases = ('repair', 'removal'); reused_phases = ('critic', 'refinement_collect', 'pair_prepare')
    current = report['incremental_resources']
    need(set(current) == {'by_phase', 'physical_totals', 'provider_cost_usd', 'reused_original_work_included'} and
         set(current['by_phase']) == set(phases) and current['reused_original_work_included'] is False,
         'New-only physical resource schema')
    _zero_cost(current['provider_cost_usd'], 'New provider cost')
    measured = {phase: dict.fromkeys(FIELDS, 0) for phase in phases}
    for product in report['case_products']:
        need(set(product['accounting']) == set(phases), 'Every new cell accounting record')
        for phase in phases:
            usage = _usage(product['accounting'][phase], 'Cell ' + phase, cells=1, no_http=True)
            status = product[phase]['producer_status']
            need(usage['generation_calls'] == int(status in ('produced', 'parse_failure')),
                 'Complete new-cell disposition and generation count')
            if not usage['generation_calls']:
                need(usage['measured_input_tokens'] == usage['measured_output_tokens'] == 0,
                     'No measured native tokens for unentered new call')
            for key in FIELDS: measured[phase][key] += usage[key]
    for phase in phases:
        equal(current['by_phase'][phase], measured[phase], 'Independent new phase sum ' + phase)
        _usage(measured[phase], 'New phase bounds ' + phase, cells=size, no_http=True)
    physical = _sum(measured.values())
    equal(current['physical_totals'], physical, 'Independent new physical sum')
    history_wrapper = report['historical_and_logical_resources']
    need(history_wrapper['historical_work_reexecuted'] is False and history_wrapper['old_repair_outputs_adopted'] is False,
         'Historical exposure cannot become new work')
    history = history_wrapper['history']; prior = history['original_failed_exposure']
    all_phases = reused_phases + phases
    need(set(prior['verified_by_phase']) == set(all_phases) and set(history['reused_prerequisites']) == set(reused_phases),
         'Separate full earlier exposure and reused prerequisite tables')
    for phase in all_phases:
        _usage(prior['verified_by_phase'][phase], 'Earlier verified ' + phase)
    prior_totals = _sum(prior['verified_by_phase'].values())
    equal(prior['physical_totals'], prior_totals, 'Earlier verified physical totals')
    for phase in reused_phases:
        equal(history['reused_prerequisites'][phase], prior['verified_by_phase'][phase], 'Reused prerequisite ' + phase)
    need(all(value == 0 for value in prior['verified_by_phase']['removal'].values()), 'Earlier removal did not execute')
    raw = []; reserved = []; failed_ids = set()
    new_ids = {identity for row in report['case_products'] for identity in row['physical_execution_ids'].values()}
    need(type(prior['unverified_native']) is list, 'Earlier unverified usage list')
    for attempt in prior['unverified_native']:
        subset(attempt, dict(kind='sc05_authenticated_native_limit_failure_v1', status='authenticated_limit_failure',
            producer_status='error', check_status='not_run', prediction=None, original_usage_verified=False,
            qualified_usage=None, raw_usage_checked=True), 'Earlier rejected completion stays unverified')
        identity = attempt['execution_id']
        need(type(identity) is str and identity and identity not in failed_ids and identity not in new_ids,
             'Earlier failed execution cannot identify a new call')
        failed_ids.add(identity)
        a, b = attempt['raw_reported_usage'], attempt['conservative_reservation']
        for row in (a, b):
            need(set(row) == {'input_tokens', 'output_tokens', 'cost_usd'} and
                 all(type(row[key]) is int and row[key] >= 0 for key in ('input_tokens', 'output_tokens')),
                 'Separate raw/reserved original usage fields')
            _zero_cost(row['cost_usd'], 'Earlier rejected provider cost')
        need(a['input_tokens'] <= b['input_tokens'] <= 16128 and a['output_tokens'] == b['output_tokens'] == 256,
             'Earlier captured native limit usage')
        raw.append(a); reserved.append(b)
    if report['purpose'] == 'fictional_qualification':
        need(prior.get('actual_prior_model_calls') == 0 and type(prior.get('actual_prior_model_calls')) is int and
             not raw and all(value == 0 for value in prior_totals.values()), 'Invented ancestry cannot claim historical calls')
    baseline = history['baseline_resources']; ordered(baseline, ids, 'Baseline resource attribution')
    for row in baseline:
        need(set(row) == {'id', 'logical_model_usage', 'logical_http_usage'} and
             set(row['logical_model_usage']) == set(MODEL_FIELDS) and set(row['logical_http_usage']) == set(HTTP_FIELDS),
             'Baseline resource fields')
        model, http = row['logical_model_usage'], row['logical_http_usage']
        need(all(type(model[key]) is int and model[key] >= 0 for key in FIELDS[:5]) and
             all(type(value) is int and value >= 0 for value in http.values()), 'Baseline nonnegative counters')
        _zero_cost(model['provider_cost_usd'], 'Baseline provider cost')
        need(model['generation_calls'] <= 1 and model['measured_input_tokens'] <= model['reserved_input_tokens'] <= 16128 and
             model['measured_output_tokens'] <= model['reserved_output_tokens'] <= 256 and http['requests'] <= 5 and
             http['safety_accounted_bytes'] - http['measured_response_bytes'] == http['unknown_transfer_upper_bytes'],
             'Baseline measurement/reservation attribution')
    base_m = _sum([row['logical_model_usage'] for row in baseline], MODEL_FIELDS)
    base_h = _sum([row['logical_http_usage'] for row in baseline], HTTP_FIELDS)
    combined = dict(history['reused_prerequisites'], **measured)
    collection = combined['refinement_collect']
    extra_http = dict(requests=collection['source_http_requests'], measured_response_bytes=collection['measured_response_bytes'],
        safety_accounted_bytes=collection['safety_accounted_bytes'],
        unknown_transfer_upper_bytes=collection['safety_accounted_bytes'] - collection['measured_response_bytes'])
    conditions = {}
    for condition, dependencies in (('one_pass', ()), ('critique_only', ('critic',)),
                                    ('repair', ('critic', 'repair')), ('removal', ('critic', 'removal'))):
        use_refinement = condition in phases
        conditions[condition] = dict(model_usage={**{key: base_m[key] + sum(combined[p][key] for p in dependencies)
                    for key in FIELDS[:5]}, 'provider_cost_usd': 0},
            attributed_http_usage={key: base_h[key] + (extra_http[key] if use_refinement else 0) for key in HTTP_FIELDS},
            reused_original_model=base_m, reused_original_sources=base_h, incremental_model_phases=list(dependencies),
            refinement_source_information_dependency=condition == 'repair', refinement_source_control_overhead=condition == 'removal',
            refinement_source_attribution=extra_http if use_refinement else dict.fromkeys(HTTP_FIELDS, 0),
            generation_ceiling=3 * size, output_token_ceiling=768 * size)
    logical = report['logical_condition_resources']
    equal(logical['conditions'], conditions, 'Logical overlap without earlier repair costs')
    subset(logical, dict(baseline_arm='L/O', reused_model_and_sources_charged_once_physically=True), 'Logical shared-cost declaration')
    return dict(new_physical_totals=physical, reused_prerequisite_totals=_sum(history['reused_prerequisites'].values()),
        earlier_verified_totals=prior_totals, earlier_sunk_repair_verified=prior['verified_by_phase']['repair'],
        earlier_unverified_attempts=len(raw), earlier_reported_unverified=_sum(raw, ('input_tokens', 'output_tokens', 'cost_usd')),
        earlier_reserved_upper=_sum(reserved, ('input_tokens', 'output_tokens', 'cost_usd')),
        logical_condition_totals_overlap=True, raw_unverified_usage_added_to_measurements=False)


def audit_report(report, *, expected_ids, expected_groups):
    """Recompute a report against externally established order and grouping.

    No acceptance capability or receipt is issued. Truth flags, annotation
    identities and source lineage need the separate source/native/reference gate.
    """
    report = plain(report); ids = list(expected_ids); groups = [list(group) for group in expected_groups]
    need(ids and len(ids) == len(set(ids)) and all(type(key) is str and key for key in ids), 'External ordered IDs')
    flat = [key for group in groups for key in group]
    need(groups and all(groups) and len(flat) == len(ids) == len(set(flat)) and set(flat) == set(ids), 'External group partition')
    need(report['kind'] == 'sc05_evidence_first_evaluation_v1' and report['purpose'] in
         ('production', 'fictional_qualification'), 'New-condition report kind/purpose')
    need(len(ids) == (199 if report['purpose'] == 'production' else 6), 'Full new-condition schedule')
    if report['purpose'] == 'production':
        need(len(groups) == 186 and Counter(map(len, groups)) == {1: 176, 2: 7, 3: 3}, 'Original publication components')
    subset(report, dict(scheduled_count=len(ids), publication_component_count=len(groups), publication_groups=groups,
        seed=SEED, bootstrap_replicates=DRAWS, provenance_validated=True, scientific_support_verified=False,
        earlier_failed_condition_preserved=True, old_repair_outputs_adopted=False), 'Fixed report contract')
    identity = report['method_identity']
    need(type(identity) is str and len(identity) == 64 and all(c in '0123456789abcdef' for c in identity), 'New method fingerprint')
    need(set(report['native']) == set(report['conditions']) == set(CONDITIONS), 'Exact original/new conditions')
    scores = dict(report['native'], removal=report['removal_diagnostic']['native'])
    for name, score in scores.items():
        equal(score, _native(score['case_results'], ids), 'Native counts ' + name)
    equal(scores['one_pass'], scores['critique_only'], 'Critique cannot rewrite original answer')
    base = scores['one_pass']['case_results']; repaired = scores['repair']['case_results']
    removed = scores['removal']['case_results']; products = report['case_products']
    ordered(products, ids, 'Case products'); semantic = []; physical = []
    for i, product in enumerate(products):
        for name, field in (('one_pass', 'original'), ('repair', 'repair'), ('removal', 'removal')):
            equal(product[field], {key: scores[name]['case_results'][i][key] for key in
                  ('id', 'producer_status', 'check_status', 'prediction', 'reason')}, 'Product disposition ' + name)
        need(set(product['physical_execution_ids']) == {'repair', 'removal'}, 'New-only physical identities')
        physical.extend(product['physical_execution_ids'].values())
        decision, reason = _decision(base[i], product['critic'])
        subset(product['semantic_selection'], dict(decision=decision, reason=reason, native_candidate_unchanged=True,
            retained_prediction=base[i]['prediction'] if decision == 'keep' else None,
            scientific_correctness='unevaluated'), 'Unchanged critique policy')
        semantic.append(dict(id=ids[i], decision=decision, reason=reason,
            false_withholding=base[i]['correct_and_admitted'] and decision == 'withhold'))
    need(len(physical) == 2 * len(ids) == len(set(physical)) and all(type(key) is str and key for key in physical),
         'Unique full new physical schedule')
    conditions = dict(one_pass=_condition(base, [row['checked_answered'] for row in base]),
        critique_only=_condition(base, [row['decision'] == 'keep' for row in semantic]),
        repair=_condition(repaired, [row['checked_answered'] for row in repaired]))
    equal(report['conditions'], conditions, 'Condition quantities')
    false = sum(row['false_withholding'] for row in semantic)
    eligible = scores['one_pass']['counts']['correct_and_admitted']
    equal(report['semantic_selection'], dict(case_results=semantic,
        decision_counts=dict(Counter(row['decision'] for row in semantic)),
        reason_counts=dict(Counter(row['reason'] for row in semantic)), false_withholding=false,
        eligible_correct_originals=eligible, false_withholding_rate=ratio(false, eligible, nullable=True)), 'Semantic selection')
    subset(report['repair_transitions'], _transitions(base, repaired), 'Repair transitions')
    subset(report['removal_diagnostic']['transitions'], _transitions(repaired, removed), 'Removal transitions')
    need(scores['removal']['counts']['checked_answered'] == 0, 'Removal cannot admit substantive answers')
    def intervals(left, right):
        return dict(publication_components=_interval(ids, left, right, groups),
                    question_sensitivity=_interval(ids, left, right, [[key] for key in ids]))
    contrasts = {}
    for name, left, right in CONTRASTS:
        contrasts[name] = {endpoint: intervals([row[flag] for row in conditions[left]['case_results']],
                                               [row[flag] for row in conditions[right]['case_results']])
            for endpoint, flag in (('raw_accuracy', 'raw_correct'), ('correct_retained_yield', 'correct_retained'))}
    equal(report['primary_contrasts'], contrasts, 'All twelve primary intervals')
    equal(report['removal_diagnostic']['raw_accuracy_removal_minus_repair'],
          intervals([row['raw_correct'] for row in repaired], [row['raw_correct'] for row in removed]), 'Two removal intervals')
    agreement = report['native_agreement']
    subset(agreement, dict(status='PASS', generated_conditions_checked=3,
                           original_records_reused_for_critique_only=True), 'Native agreement declaration')
    comparisons = agreement['comparisons']
    need(type(comparisons) is list and len(comparisons) == 3 and
         {row['condition'] for row in comparisons} == {'one_pass', 'repair', 'removal'}, 'All three native comparisons once')
    keys = ['scheduled_count', 'counts', 'raw_metrics', 'checked_metrics', 'raw_precision_defined',
            'checked_precision_defined', 'producer_status_counts', 'check_status_counts', 'case_results']
    for row in comparisons:
        equal(row['checked_fields'], keys, 'Native comparison fields')
        subset(row['native'], {key: scores[row['condition']][key] for key in keys}, 'Native comparison quantities')
    source_rows = report['source_cases']; ordered(source_rows, ids, 'Source cases')
    need(all(type(row[key]) is bool for row in source_rows for key in ('source_context_changed', 'refinement_available')),
         'Typed source coverage flags')
    equal(report['source_context_changes'], dict(scheduled_count=len(ids),
        changed=sum(row['source_context_changed'] for row in source_rows),
        unchanged=sum(not row['source_context_changed'] for row in source_rows),
        unavailable_refinement=sum(not row['refinement_available'] for row in source_rows)), 'Coverage counts')
    annotations = None
    for field, prefix in (('source_metrics', ''), ('original_source_metrics', 'original_')):
        need(set(report[field]) == {'retained', 'pool', 'selected'}, 'All source diagnostic levels')
        for level in ('retained', 'pool', 'selected'):
            metric = report[field][level]
            equal(metric, _doi(metric['case_results'], ids, {row['id']: row[prefix + level + '_dois'] for row in source_rows}),
                  field + '.' + level)
            current = [row['annotated_ids'] for row in metric['case_results']]
            if annotations is None: annotations = current
            else: equal(current, annotations, 'Common annotations across all source diagnostics')
    resources = _resources(report, ids)
    return dict(kind='sc05_evidence_first_arithmetic_audit_v1', status='arithmetic_reconstructed',
        scheduled_count=len(ids), publication_component_count=len(groups), method_identity=identity,
        report_sha256=fingerprint(report), ordered_ids_sha256=fingerprint(ids), groups_sha256=fingerprint(groups),
        intervals_recomputed=14, seed=SEED, replicates=DRAWS, resources=resources,
        native_counts_reconstructed=True, transitions_reconstructed=True, source_identity_metrics_reconstructed=True,
        reference_truth_checked_here=False, native_source_process_verified_here=False,
        scientific_support_verified=False, acceptance_issued=False)
