"""Native sufficient statistics and prospectively fixed paired component bootstrap."""
import math
import random

from experiments.scifact_comparison.inputs import need

# Counts are additive across claims/components, including repeated components.
FIELDS = ('abstract_gold','abstract_predicted','abstract_label_correct','abstract_rationale_correct',
          'sentence_gold','sentence_predicted','sentence_selection_correct','sentence_label_correct',
          'strict_correct','scheduled')


def case_counts(gold, prediction, *, produced=True, admitted=True):
    need(gold['id'] == prediction['id'], 'Scoring identity mismatch')
    counts = dict.fromkeys(FIELDS,0)
    counts['scheduled'] = 1
    counts['abstract_gold'] = len(gold['evidence'])
    counts['sentence_gold'] = sum(len(r['sentences']) for sets in gold['evidence'].values() for r in sets)
    counts['abstract_predicted'] = len(prediction['evidence'])
    counts['sentence_predicted'] = sum(len(p['sentences']) for p in prediction['evidence'].values())
    strict = produced and admitted and set(gold['evidence']) == set(prediction['evidence'])
    for did, predicted in prediction['evidence'].items():
        if did not in gold['evidence']:
            continue
        annotations = gold['evidence'][did]
        sets = [set(a['sentences']) for a in annotations]
        full = set(predicted['sentences'])
        cap = max(3,min(len(s) for s in sets))
        rationalized = any(s <= set(predicted['sentences'][:cap]) for s in sets)
        matched = predicted['label'] == annotations[0]['label']
        complete = set().union(*(s for s in sets if s <= full))
        counts['abstract_label_correct'] += int(matched)
        counts['abstract_rationale_correct'] += int(matched and rationalized)
        counts['sentence_selection_correct'] += len(complete)
        counts['sentence_label_correct'] += len(complete) if matched else 0
        strict = strict and matched and rationalized
    counts['strict_correct'] = int(strict)
    return tuple(counts[f] for f in FIELDS)


def metrics(values):
    need(len(values) == len(FIELDS) and all(type(x) is int and x >= 0 for x in values), 'Invalid count vector')
    c = dict(zip(FIELDS,values))
    result = {}
    for family,gold,predicted,correct in (
        ('abstract_label_only','abstract_gold','abstract_predicted','abstract_label_correct'),
        ('abstract_rationalized','abstract_gold','abstract_predicted','abstract_rationale_correct'),
        ('sentence_selection','sentence_gold','sentence_predicted','sentence_selection_correct'),
        ('sentence_label','sentence_gold','sentence_predicted','sentence_label_correct')):
        g,p,t = c[gold],c[predicted],c[correct]
        result[family+'_precision'] = t/p if p else 0.
        result[family+'_recall'] = t/g if g else 0.
        result[family+'_f1'] = 2*t/(p+g) if p+g else 0.
    result['strict_correct_per_scheduled'] = c['strict_correct']/c['scheduled'] if c['scheduled'] else 0.
    return result


def total(vectors):
    return tuple(sum(row[i] for row in vectors) for i in range(len(FIELDS)))


def percentile(values, fraction):
    ordered = sorted(values)
    need(ordered and 0 <= fraction <= 1, 'Invalid percentile')
    position = (len(ordered)-1)*fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper]-ordered[lower])*(position-lower)


def paired_bootstrap(left, right, components, *, seed=20261106, replicates=10000):
    """left=baseline, right=new condition; return new-minus-baseline intervals."""
    need(set(left) == set(right) == set(components) and left, 'Bootstrap membership differs')
    need(type(replicates) is int and replicates > 0, 'Positive bootstrap count required')
    groups = {}
    for cid in left:
        groups.setdefault(components[cid],[]).append(cid)
    keys = sorted(groups, key=str)
    a = [total([left[c] for c in groups[k]]) for k in keys]
    b = [total([right[c] for c in groups[k]]) for k in keys]
    old, new = metrics(total(list(left.values()))), metrics(total(list(right.values())))
    distributions = {key:[] for key in old}
    rng = random.Random(seed)
    for _ in range(replicates):
        selected = [rng.randrange(len(keys)) for _ in keys]
        aa = metrics(total([a[i] for i in selected]))
        bb = metrics(total([b[i] for i in selected]))
        for key in distributions:
            distributions[key].append(bb[key]-aa[key])
    return dict(seed=seed, replicates=replicates, components=len(keys), claims=len(left),
        direction='new_minus_baseline', interval='paired_component_percentile_95_linear_interpolation',
        scope='Variability within the exposed public benchmark; not independent clinical generalization.',
        metrics={k:dict(baseline=old[k], new=new[k], difference=new[k]-old[k],
                        lower=percentile(v,.025), upper=percentile(v,.975)) for k,v in distributions.items()})
