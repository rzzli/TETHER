"""Fixed all-scheduled refinement estimands; provenance is a separate gate.

Native candidate scoring and the paired sampler come from the independent
LitQA reader. Semantic withholding never edits a native prediction record.
"""
from collections import Counter
from collections.abc import Mapping

from tether_engine.serde import encode
from experiments.litqa_analysis.metrics import paired_bootstrap as _bootstrap
from experiments.litqa_analysis.scoring import score_arm

SEED = 20261106
REPLICATES = 10000
CONDITIONS = ('one_pass', 'critique_only', 'repair')
CONTRASTS = (('critique_only_minus_one_pass', 'one_pass', 'critique_only'),
             ('repair_minus_one_pass', 'one_pass', 'repair'),
             ('repair_minus_critique_only', 'critique_only', 'repair'))
ENDPOINTS = ('raw_accuracy', 'correct_retained_yield')


def need(value, message):
    if not value:
        raise ValueError(message)


def membership(ids, groups, purpose):
    ids = tuple(ids)
    groups = tuple(tuple(g) for g in groups)
    need(purpose in ('production', 'fictional_qualification'), 'Explicit evaluation purpose')
    need(ids and len(set(ids)) == len(ids), 'Unique scheduled IDs')
    flat = [i for g in groups for i in g]
    need(groups and all(groups) and len(flat) == len(ids) == len(set(flat)) and
         set(flat) == set(ids), 'Publication groups partition every scheduled ID')
    if purpose == 'production':
        need(len(ids) == 199 and len(groups) == 186 and
             Counter(map(len, groups)) == {1: 176, 2: 7, 3: 3},
             'Original 199-question / 186-component production membership')
    return ids, groups


def paired_bootstrap(ids, left, right, groups):
    """Reuse the qualified sampler, retaining only right-minus-left.

    Duplicated slots are a pure two-condition adapter, not four experimental
    arms. Every draw remains the same original whole-publication draw.
    """
    raw = _bootstrap(ids, {'L/O': left, 'E/O': right, 'L/R': left, 'E/R': right},
                     groups, replicates=REPLICATES, seed=SEED)
    return {k: raw[k] for k in ('case_count', 'group_count', 'group_sizes', 'seed',
            'requested_replicates', 'completed_replicates', 'method', 'uncertainty_estimable')} | {
        'baseline': raw['rates']['L/O'], 'new': raw['rates']['E/O'],
        **raw['contrasts']['expansion_at_lexical'],
        'limitation': raw.get('limitation')}


def _selection(row, critic):
    """Independent policy reconstruction from native flags and critic output."""
    if row['producer_status'] != 'produced':
        return 'not_applicable', 'original_candidate_unavailable'
    if row['native_unsure']:
        return 'not_applicable', 'original_native_unsure'
    if row['check_status'] != 'accepted':
        return 'withhold', 'original_not_admitted'
    if critic['decoded'] is None:
        return 'withhold', 'critic_unavailable'
    support = critic['decoded']['support']
    return ('keep', 'critic_supported') if support == 'supported' else ('withhold', 'critic_' + support)


def _condition(score, keep):
    cases = []
    for row, selected in zip(score['case_results'], keep):
        need(type(selected) is bool and (not selected or row['checked_answered']),
             'Semantic selection cannot upgrade unproduced, unsure or unadmitted candidates')
        cases.append(dict(id=row['id'], raw_correct=row['raw_correct'], retained=selected,
                          correct_retained=selected and row['raw_correct']))
    n = score['scheduled_count']
    selected = sum(keep)
    correct = sum(r['correct_retained'] for r in cases)
    return dict(scheduled_count=n, retained=selected, correct_retained=correct,
                incorrect_retained=selected-correct, raw_accuracy=score['raw_metrics']['accuracy'],
                correct_retained_yield=correct/n, retained_coverage=selected/n,
                statistical_retained_precision=correct/selected if selected else None,
                retained_precision_defined=bool(selected), case_results=cases)


def _transitions(before, after):
    counts = Counter()
    rows = []
    for a, b in zip(before['case_results'], after['case_results']):
        need(a['id'] == b['id'], 'Transition schedule identity')
        if a['producer_status'] != 'produced':
            origin = 'unproduced'
        elif a['native_unsure']:
            origin = 'native_unsure'
        else:
            origin = 'correct_substantive' if a['raw_correct'] else 'wrong_substantive'
        if b['producer_status'] != 'produced':
            destination = 'unproduced'
        elif b['native_unsure']:
            destination = 'native_unsure'
        else:
            destination = 'correct_substantive' if b['raw_correct'] else 'wrong_substantive'
        key = origin + '_to_' + destination
        counts[key] += 1
        rows.append(dict(id=a['id'], origin=origin, destination=destination,
                         both_candidates_produced=a['producer_status'] == b['producer_status'] == 'produced',
                         raw_answer_index_changed=(a['prediction']['answer_index'] != b['prediction']['answer_index'])
                             if a['prediction'] is not None and b['prediction'] is not None else None,
                         repaired_wrong_substantive=origin == 'wrong_substantive' and b['raw_correct'],
                         recovered_original_operational_failure=origin == 'unproduced' and b['raw_correct'],
                         recovered_original_unsure=origin == 'native_unsure' and b['raw_correct'],
                         damaged_correct=origin == 'correct_substantive' and not b['raw_correct'],
                         persistent_wrong_substantive=origin == destination == 'wrong_substantive',
                         repaired_answer_admitted=b['correct_and_admitted']))
    flags = ('repaired_wrong_substantive', 'recovered_original_operational_failure',
             'recovered_original_unsure', 'damaged_correct', 'persistent_wrong_substantive')
    return dict(scheduled_count=len(rows), matrix=dict(counts),
                counts={f: sum(r[f] for r in rows) for f in flags}, case_results=rows,
                raw_answer_changes=dict(both_produced=sum(r['both_candidates_produced'] for r in rows),
                    answer_index_changed=sum(r['raw_answer_index_changed'] is True for r in rows),
                    answer_index_unchanged=sum(r['raw_answer_index_changed'] is False for r in rows),
                    unavailable_pair=sum(r['raw_answer_index_changed'] is None for r in rows)),
                scope='Raw candidate transitions; admission remains separate. Not causal error attribution.')


def summarize(queries, references, records, offered, critics, groups, *, purpose='production'):
    """Pure arithmetic only; callers must first independently verify all inputs.

    records/offered have one_pass, repair, removal keys. critics are minimal
    {id,native_status,decoded}; decoded contains only the independently parsed
    support category. This function neither reads keys nor asserts provenance.
    """
    queries, references, records, offered, critics = map(encode, (queries, references, records, offered, critics))
    ids, groups = membership([q['id'] for q in queries], groups, purpose)
    need(set(records) == set(offered) == {'one_pass', 'repair', 'removal'}, 'Exact generated conditions')
    need(isinstance(critics, list) and [r.get('id') for r in critics] == list(ids), 'Complete ordered critic schedule')
    for row in critics:
        need(set(row) == {'id', 'native_status', 'decoded'} and row['native_status'] in
             ('completed', 'codec_failure', 'capacity'), 'Exact critic metric projection')
        decoded = row['decoded']
        need((decoded is not None) == (row['native_status'] == 'completed'), 'Critic decode/status consistency')
        if decoded is not None:
            need(isinstance(decoded, Mapping) and set(decoded) == {'support'} and decoded['support'] in
                 ('supported', 'contradicted', 'insufficient', 'not_assessable'), 'Finite critic support')
    scores = {name: score_arm(queries, references, records[name], offered[name]) for name in records}
    # Removal has an empty citable-source set even when generated controls carry information.
    need(all(not offered['removal'][key] for key in ids), 'Removal evidence allowlist must be empty')
    need(scores['removal']['counts']['checked_answered'] == 0, 'Removal cannot admit substantive answers')
    base = scores['one_pass']
    decisions = [_selection(row, c) for row, c in zip(base['case_results'], critics)]
    conditions = dict(one_pass=_condition(base, [r['checked_answered'] for r in base['case_results']]),
        critique_only=_condition(base, [d == 'keep' for d, _ in decisions]),
        repair=_condition(scores['repair'], [r['checked_answered'] for r in scores['repair']['case_results']]))
    need(conditions['critique_only']['correct_retained'] <= conditions['one_pass']['correct_retained'],
         'Critique-only cannot create correct original candidates')
    semantic_rows = [dict(id=key, decision=d, reason=r, false_withholding=bool(
        original['correct_and_admitted'] and d == 'withhold'))
        for key, (d, r), original in zip(ids, decisions, base['case_results'])]
    false = sum(row['false_withholding'] for row in semantic_rows)
    eligible_correct = base['counts']['correct_and_admitted']
    contrasts = {}
    for name, left, right in CONTRASTS:
        contrasts[name] = {}
        for endpoint, field in (('raw_accuracy', 'raw_correct'), ('correct_retained_yield', 'correct_retained')):
            a = [r[field] for r in conditions[left]['case_results']]
            b = [r[field] for r in conditions[right]['case_results']]
            contrasts[name][endpoint] = dict(
                publication_components=paired_bootstrap(ids, a, b, groups),
                question_sensitivity=paired_bootstrap(ids, a, b, [(i,) for i in ids]))
    diagnostic_flags = {name: [r['raw_correct'] for r in scores[name]['case_results']] for name in ('repair', 'removal')}
    diagnostic = dict(native=scores['removal'], raw_accuracy_removal_minus_repair=dict(
        publication_components=paired_bootstrap(ids, diagnostic_flags['repair'], diagnostic_flags['removal'], groups),
        question_sensitivity=paired_bootstrap(ids, diagnostic_flags['repair'], diagnostic_flags['removal'], [(i,) for i in ids])),
        transitions=_transitions(scores['repair'], scores['removal']),
        scope='Raw-passage dependence conditional on unchanged generated context; substantive admitted yield is mechanically zero.')
    return dict(kind='tether_refinement_statistics_v1', purpose=purpose, scheduled_count=len(ids),
        publication_component_count=len(groups), publication_groups=[list(g) for g in groups],
        seed=SEED, bootstrap_replicates=REPLICATES,
        native=dict(one_pass=scores['one_pass'], critique_only=scores['one_pass'], repair=scores['repair']),
        conditions=conditions, primary_contrasts=contrasts,
        semantic_selection=dict(case_results=semantic_rows, decision_counts=dict(Counter(d for d, _ in decisions)),
            reason_counts=dict(Counter(r for _, r in decisions)), false_withholding=false,
            eligible_correct_originals=eligible_correct,
            false_withholding_rate=false/eligible_correct if eligible_correct else None),
        repair_transitions=_transitions(base, scores['repair']), removal_diagnostic=diagnostic,
        provenance_validated=False,
        limitations=['Exposed public development questions; no independent generalization estimate.',
            'Conditional precision is undefined for zero retained substantive answers.',
            'Native correctness and mechanical admission do not establish source support.',
            'The conditions have shared dependencies and different actual computation.'])
