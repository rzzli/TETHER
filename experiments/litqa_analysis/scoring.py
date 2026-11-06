"""Independent all-scheduled LitQA scoring; no inference or runtime imports.

These functions score supplied records, not their provenance. The final driver
must first reconstruct those records from externally anchored native/source bytes.
"""
from collections import Counter
from uuid import UUID

from .metrics import ARMS, paired_bootstrap, precision_ratio


def need(value, message):
    if not value:
        raise ValueError(message)


def ordered(rows, ids, label):
    need(isinstance(rows, (list, tuple)) and len(rows) == len(ids) and
         all(isinstance(r, dict) for r in rows) and [r.get('id') for r in rows] == ids,
         'Complete ordered ' + label)


def score_arm(queries, references, records, evidence_ids):
    """Compute native denominators independently; preserve operational statuses."""
    ids = [q['id'] for q in queries]
    need(ids and all(isinstance(i, str) and i for i in ids) and len(set(ids)) == len(ids),
         'Unique nonempty question schedule')
    ordered(references, ids, 'references'); ordered(records, ids, 'records')
    need(set(evidence_ids) == set(ids), 'Complete offered evidence schedule')
    counts = Counter({k: 0 for k in (
        'produced', 'producer_failures', 'accepted', 'rejected', 'check_errors',
        'check_not_run', 'raw_answered', 'checked_answered', 'raw_correct',
        'correct_and_admitted', 'correct_but_rejected', 'correct_not_admitted',
        'native_unsure', 'accepted_unsure', 'incorrect_and_admitted',
        'incorrect_substantive_and_admitted', 'parse_failures', 'produced_or_parse_failure')})
    failures = {'parse_failure', 'timeout', 'error', 'interrupted', 'unexecuted', 'input_unavailable'}
    producers = Counter(); checks = Counter(); reasons = Counter(); cases = []
    for q, ref, row in zip(queries, references, records):
        need(str(UUID(q['id'])) == q['id'], 'Canonical task UUID')
        need(set(q) == {'id', 'question', 'choices'} and isinstance(q['question'], str) and q['question'].strip(),
             'Exact visible query fields')
        choices = q['choices']
        need(isinstance(choices, (list, tuple)) and 2 <= len(choices) <= 26 and
             all(isinstance(c, str) and c.startswith(f'({chr(65+i)}) ') and c[4:].strip()
                 for i, c in enumerate(choices)), 'Native sequential answer choices')
        need(set(ref) == {'id', 'answer_index', 'unsure_index'} and
             all(type(ref[k]) is int and 0 <= ref[k] < len(choices) for k in ('answer_index', 'unsure_index')) and
             ref['answer_index'] != ref['unsure_index'], 'Valid reference choices')
        # This is the released task's literal insufficient-information choice.
        unsure = [i for i, c in enumerate(choices) if c[4:] == 'Insufficient information to answer the question']
        need(unsure == [ref['unsure_index']], 'Reference/visible unsure identity')
        need(set(row) == {'id', 'producer_status', 'check_status', 'prediction', 'reason'}, 'Exact disposition fields')
        ps, cs, pred, reason = (row[k] for k in ('producer_status', 'check_status', 'prediction', 'reason'))
        need(ps in failures | {'produced'} and cs in {'accepted', 'rejected', 'error', 'not_run'}, 'Known disposition')
        need(reason is None or isinstance(reason, str) and reason.strip(), 'Explicit nonempty reason')
        offered = evidence_ids[q['id']]
        need(isinstance(offered, (list, tuple, set, frozenset)) and all(isinstance(s, str) and s.strip() for s in offered) and
             len(set(offered)) == len(offered), 'Unique offered source IDs')
        produced = ps == 'produced'; admitted = cs == 'accepted'
        if produced:
            need(isinstance(pred, dict) and set(pred) == {'answer_index', 'evidence_ids'} and
                 type(pred['answer_index']) is int and 0 <= pred['answer_index'] < len(choices), 'Native decoded choice')
            cites = pred['evidence_ids']
            need(isinstance(cites, (list, tuple)) and len(cites) <= 64 and all(isinstance(s, str) and s.strip() for s in cites) and
                 len(cites) == len(set(cites)) and set(cites) <= set(offered), 'Native offered unique citations')
            need((reason is None) == admitted, 'Admission/reason consistency')
        else:
            need(pred is None and cs == 'not_run' and reason is not None, 'Failure is null, explained and unchecked')
        is_unsure = pred['answer_index'] == ref['unsure_index'] if produced else None
        correct = bool(produced and pred['answer_index'] == ref['answer_index'])
        answered = bool(produced and not is_unsure)
        flags = dict(produced=produced, producer_failures=not produced, accepted=admitted,
            rejected=cs == 'rejected', check_errors=cs == 'error', check_not_run=cs == 'not_run',
            raw_answered=answered, checked_answered=answered and admitted, raw_correct=correct,
            correct_and_admitted=correct and admitted, correct_but_rejected=correct and cs == 'rejected',
            correct_not_admitted=correct and not admitted, native_unsure=is_unsure is True,
            accepted_unsure=is_unsure is True and admitted, incorrect_and_admitted=admitted and not correct,
            incorrect_substantive_and_admitted=admitted and answered and not correct,
            parse_failures=ps == 'parse_failure', produced_or_parse_failure=ps in ('produced', 'parse_failure'))
        counts.update({k: int(v) for k, v in flags.items()})
        producers[ps] += 1; checks[cs] += 1
        if reason is not None: reasons[reason] += 1
        cases.append(dict(id=q['id'], producer_status=ps, check_status=cs, prediction=pred,
            native_unsure=is_unsure, raw_correct=correct, correct_and_admitted=correct and admitted,
            raw_answered=answered, checked_answered=answered and admitted, reason=reason))
    total = len(ids)
    def rates(correct, answered):
        ratio = precision_ratio(correct, answered)
        return dict(accuracy=correct / total, precision=ratio['native_precision'], coverage=answered / total)
    return dict(scheduled_count=total, counts=dict(counts), producer_status_counts=dict(producers),
        check_status_counts=dict(checks), reason_counts=dict(reasons), case_results=cases,
        raw_metrics=rates(counts['raw_correct'], counts['raw_answered']),
        checked_metrics=rates(counts['correct_and_admitted'], counts['checked_answered']),
        raw_precision_defined=bool(counts['raw_answered']), checked_precision_defined=bool(counts['checked_answered']),
        statistical_raw_precision=precision_ratio(counts['raw_correct'], counts['raw_answered'])['statistical_precision'],
        statistical_checked_precision=precision_ratio(counts['correct_and_admitted'], counts['checked_answered'])['statistical_precision'],
        unchanged_raw_checked=counts['accepted'],
        provenance_validated=False)


def paper_metrics(ids, annotations, observed):
    """Bibliographic identity matching, never decisive-passage/support recall."""
    need(ids and len(ids) == len(set(ids)) and set(annotations) == set(observed) == set(ids),
         'Full unique paper diagnostic schedule')
    rows = []
    for key in ids:
        for values in (annotations[key], observed[key]):
            need(isinstance(values, (list, tuple, set, frozenset)) and all(isinstance(x, str) and x for x in values),
                 'Resolved DOI identities only')
        gold, found = set(annotations[key]), set(observed[key]); matched = gold & found
        rows.append(dict(id=key, annotated_ids=sorted(gold), retrieved_ids=sorted(found), matched_ids=sorted(matched),
                         annotated_source_recall=len(matched) / len(gold) if gold else None))
    gold_count = sum(len(r['annotated_ids']) for r in rows); matches = sum(len(r['matched_ids']) for r in rows)
    any_hits = sum(bool(r['matched_ids']) for r in rows)
    all_hits = sum(bool(r['annotated_ids']) and r['annotated_ids'] == r['matched_ids'] for r in rows)
    return dict(scheduled_count=len(ids), annotated_source_count=gold_count, matched_annotated_source_count=matches,
        annotated_source_recall=matches / gold_count if gold_count else None,
        questions_with_annotations=sum(bool(r['annotated_ids']) for r in rows),
        questions_without_annotations=sum(not r['annotated_ids'] for r in rows),
        questions_with_any_annotated_source_hit=any_hits, questions_with_all_annotated_sources=all_hits,
        any_hit_per_scheduled=any_hits / len(ids), all_hit_per_scheduled=all_hits / len(ids),
        semantic_support='unevaluated', case_results=rows)


def transitions(before, after):
    a, b = before['case_results'], after['case_results']
    need(a and [r['id'] for r in a] == [r['id'] for r in b], 'Paired transition identities')
    return dict(scheduled_count=len(a),
        incorrect_to_correct=sum(not x['raw_correct'] and y['raw_correct'] for x, y in zip(a, b)),
        correct_to_incorrect=sum(x['raw_correct'] and not y['raw_correct'] for x, y in zip(a, b)),
        correct_to_correct=sum(x['raw_correct'] and y['raw_correct'] for x, y in zip(a, b)),
        incorrect_to_incorrect=sum(not x['raw_correct'] and not y['raw_correct'] for x, y in zip(a, b)),
        scope='All-scheduled transitions; incorrect includes unsure and failures; not causal error attribution.')


def factorial(arms, groups, *, replicates=10000, seed=20261106):
    need(set(arms) == set(ARMS), 'All four primary arms')
    ids = [r['id'] for r in arms[ARMS[0]]['case_results']]
    need(all([r['id'] for r in arm['case_results']] == ids for arm in arms.values()), 'Identical arm schedules')
    results = {}
    for name, field in (('raw_accuracy', 'raw_correct'), ('correct_and_admitted_yield', 'correct_and_admitted')):
        flags = {arm: [r[field] for r in score['case_results']] for arm, score in arms.items()}
        results[name] = dict(
            publication_components=paired_bootstrap(ids, flags, groups, replicates=replicates, seed=seed),
            question_sensitivity=paired_bootstrap(ids, flags, [(i,) for i in ids], replicates=replicates, seed=seed))
    return dict(metrics=results, ranking_transitions={branch: transitions(arms[branch+'/O'], arms[branch+'/R']) for branch in ('L', 'E')},
                scope='Exploratory paired contrasts; exposed public development questions; no calibrated risk guarantee.')
