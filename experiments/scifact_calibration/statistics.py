"""Prespecified selective/reliability summaries and paired component resampling.

No thresholds, bins, fitting settings or subsets are selected using outcomes.
Missing denominators remain undefined. Bootstrap uncertainty is conditional on
the one fitted mapping and is separate from deletion sensitivity ranges.
"""
from collections import Counter
from dataclasses import dataclass, replace
import math
import random
import time

from .calibration import apply_mapping, need, probability, validate_suite

THRESHOLDS = (0., .5, .7, .9, .95)
PRIMARY_THRESHOLD = .9
BIN_EDGES = (0., .2, .4, .6, .8, 1.)
REPLICATES = 10000
SEED = 20261106


@dataclass(frozen=True)
class AnalysisRow:
    id: int
    raw: float | None
    calibrated: float | None
    produced: bool
    admitted: bool
    strict_success: int


def validate_rows(rows, ids, components, purpose):
    rows, ids = tuple(rows), tuple(ids)
    need(purpose in ('production', 'calibration_diagnostic', 'fictional_qualification'), 'Explicit statistics purpose')
    need(ids and len(ids) == len(set(ids)) and all(type(i) is int and i > 0 for i in ids) and
         all(isinstance(r, AnalysisRow) for r in rows) and tuple(r.id for r in rows) == ids,
         'Complete ordered statistics schedule')
    need(set(components) == set(ids) and all(isinstance(components[i], str) and components[i] for i in ids),
         'Exact frozen component membership')
    if purpose == 'production':
        need(len(ids) == 300 and len(set(components.values())) == 247, 'Full 300-claim/247-component development schedule')
    if purpose == 'calibration_diagnostic':
        need(len(ids)==69 and len(set(components.values()))==49 and
             Counter(Counter(components.values()).values())=={1:32,2:15,3:1,4:1},'Full69/49 calibration diagnostic')
    for row in rows:
        need(type(row.produced) is bool and type(row.admitted) is bool and (row.produced or not row.admitted) and
             type(row.strict_success) is int and row.strict_success in (0, 1) and
             (not row.strict_success or row.produced and row.admitted), 'Strict operational success fields')
        for score in (row.raw, row.calibrated):
            if score is not None:
                probability(score)
    return rows, ids


def ratio(numerator, denominator):
    return numerator/denominator if denominator else None


def bin_index(score):
    score = probability(score)
    return next((i for i, upper in enumerate(BIN_EDGES[1:-1]) if score < upper), 4)


def loss(score, y):
    clipped = min(1-1e-6, max(1e-6, score))
    return -(math.log(clipped) if y else math.log1p(-clipped)), clipped != score


def point_summary(rows, ids, components, *, purpose='production'):
    rows, ids = validate_rows(rows, ids, components, purpose)
    all_groups = set(components.values()); total_correct = sum(r.strict_success for r in rows)
    result = dict(scheduled=len(rows), components=len(all_groups), primary_threshold=PRIMARY_THRESHOLD,
        thresholds=list(THRESHOLDS), operational=dict(produced=sum(r.produced for r in rows),
            admitted=sum(r.admitted for r in rows), unproduced=sum(not r.produced for r in rows),
            produced_but_rejected=sum(r.produced and not r.admitted for r in rows)), conditions={})
    for name in ('raw', 'calibrated'):
        available = [r for r in rows if getattr(r, name) is not None]
        points = []
        for threshold in THRESHOLDS:
            selected = [r for r in available if r.produced and r.admitted and getattr(r, name) >= threshold]
            correct = sum(r.strict_success for r in selected); count = len(selected)
            points.append(dict(threshold=threshold, scheduled=len(rows), scheduled_components=len(all_groups),
                available=len(available), available_components=len({components[r.id] for r in available}),
                accepted=count, accepted_components=len({components[r.id] for r in selected}),
                correct_accepted=correct, incorrect_accepted=count-correct,
                correct_withheld=total_correct-correct, incorrect_withheld=len(rows)-count-(total_correct-correct),
                coverage=count/len(rows), strict_correct_yield=correct/len(rows),
                conditional_error=ratio(count-correct,count), conditional_precision=ratio(correct,count)))
        bins=[]
        for i in range(5):
            members=[r for r in available if bin_index(getattr(r,name))==i]
            bins.append(dict(lower=BIN_EDGES[i], upper=BIN_EDGES[i+1], upper_inclusive=i==4,
                count=len(members), components=len({components[r.id] for r in members}),
                mean_score=ratio(math.fsum(getattr(r,name) for r in members),len(members)),
                empirical_strict_correctness=ratio(sum(r.strict_success for r in members),len(members))))
        result['conditions'][name]=dict(available=len(available), missing=len(rows)-len(available), operating_points=points,
            reliability_bins=bins, descriptive_ece=math.fsum(b['count']*abs(b['mean_score']-b['empirical_strict_correctness'])
                for b in bins if b['count'])/len(available) if available else None)
    paired=[r for r in rows if r.raw is not None and r.calibrated is not None]
    proper=dict(scheduled=len(rows), paired_available=len(paired), missing=len(rows)-len(paired),
                full_cohort=len(paired)==len(rows), components=len({components[r.id] for r in paired}), conditions={})
    for name in ('raw','calibrated'):
        losses=[loss(getattr(r,name),r.strict_success) for r in paired]
        proper['conditions'][name]=dict(brier=ratio(math.fsum((getattr(r,name)-r.strict_success)**2 for r in paired),len(paired)),
            log_loss=ratio(math.fsum(x[0] for x in losses),len(paired)), log_loss_clipped=sum(x[1] for x in losses))
    proper['calibrated_minus_raw']={key:(proper['conditions']['calibrated'][key]-proper['conditions']['raw'][key]
        if paired else None) for key in ('brier','log_loss')}
    result['proper_scores']=proper
    return result


def percentile(values, fraction):
    ordered=sorted(values);need(ordered and 0<=fraction<=1,'Percentile inputs')
    position=(len(ordered)-1)*fraction;lower=math.floor(position);upper=math.ceil(position)
    return ordered[lower]+(ordered[upper]-ordered[lower])*(position-lower)


def _ratios(rows):
    """All endpoint sufficient statistics per original claim, before resampling."""
    output={}; both=[r.raw is not None and r.calibrated is not None for r in rows]
    for name in ('raw','calibrated'):
        for key in ('brier','log_loss'):
            output[(name,'proper',key)]=(
                tuple(((getattr(r,name)-r.strict_success)**2 if key=='brier' else loss(getattr(r,name),r.strict_success)[0])
                      if ok else 0. for r,ok in zip(rows,both)),tuple(int(x) for x in both))
        for ti,threshold in enumerate(THRESHOLDS):
            selected=tuple(int(r.produced and r.admitted and getattr(r,name) is not None and getattr(r,name)>=threshold) for r in rows)
            good=tuple(s*r.strict_success for s,r in zip(selected,rows));bad=tuple(s-g for s,g in zip(selected,good))
            for metric,num,den in (('coverage',selected,(1,)*len(rows)),('strict_correct_yield',good,(1,)*len(rows)),
                                   ('conditional_error',bad,selected),('conditional_precision',good,selected)):
                output[(name,'selection',ti,metric)]=(num,den)
        for i in range(5):
            selected=tuple(int(getattr(r,name) is not None and bin_index(getattr(r,name))==i) for r in rows)
            output[(name,'bin',i,'correctness')]=(tuple(s*r.strict_success for s,r in zip(selected,rows)),selected)
            output[(name,'bin',i,'mean_score')]=(tuple(getattr(r,name) if s else 0. for s,r in zip(selected,rows)),selected)
    return output


def paired_bootstrap(rows, ids, components, *, purpose='production'):
    """10,000 shared whole-component draws; claim-weighted ratios per draw."""
    started=time.monotonic();rows,ids=validate_rows(rows,ids,components,purpose)
    keys=tuple(sorted(set(components.values())));positions={key:[] for key in keys}
    for i,ident in enumerate(ids):positions[components[ident]].append(i)
    specs=_ratios(rows); vectors=[]; vector_index={}; bindings={}; observed={}; contributors={}
    for endpoint,(num,den) in specs.items():
        pair=[]
        for values in (num,den):
            grouped=tuple(math.fsum(values[i] for i in positions[key]) for key in keys)
            if grouped not in vector_index:
                vector_index[grouped]=len(vectors);vectors.append(grouped)
            pair.append(vector_index[grouped])
        bindings[endpoint]=tuple(pair);observed[endpoint]=ratio(math.fsum(num),math.fsum(den))
        contributors[endpoint]=sum(any(den[i]>0 for i in positions[key]) for key in keys)
    samples={endpoint:[] for endpoint in specs};undefined=dict.fromkeys(specs,0)
    diffs={key[1:]:[] for key in specs if key[0]=='raw' and key[1]!='bin'}
    undefined_diffs=dict.fromkeys(diffs,0);rng=random.Random(SEED)
    for _ in range(REPLICATES):
        selected=Counter(rng.randrange(len(keys)) for _ in keys)
        values=[math.fsum(v[i]*count for i,count in selected.items()) for v in vectors]
        current={}
        for endpoint,(ni,di) in bindings.items():
            value=ratio(values[ni],values[di]);current[endpoint]=value
            if value is None:undefined[endpoint]+=1
            else:samples[endpoint].append(value)
        for endpoint in diffs:
            a,b=current[('raw',)+endpoint],current[('calibrated',)+endpoint]
            if a is None or b is None:undefined_diffs[endpoint]+=1
            else:diffs[endpoint].append(b-a)
    def interval(values, missing, count):
        if count<2:return None,'fewer_than_two_observed_denominator_components'
        if missing:return None,'undefined_denominator_in_bootstrap_draws'
        return [percentile(values,.025),percentile(values,.975)],None
    estimates=[]
    for endpoint in specs:
        ci,reason=interval(samples[endpoint],undefined[endpoint],contributors[endpoint])
        estimates.append(dict(endpoint=list(endpoint),estimate=observed[endpoint],ci95=ci,
            undefined_replicates=undefined[endpoint],denominator_components=contributors[endpoint],undefined_reason=reason))
    differences=[]
    for endpoint in diffs:
        a,b=('raw',)+endpoint,('calibrated',)+endpoint
        ci,reason=interval(diffs[endpoint],undefined_diffs[endpoint],min(contributors[a],contributors[b]))
        differences.append(dict(endpoint=list(endpoint),estimate=observed[b]-observed[a] if observed[a] is not None and observed[b] is not None else None,
            ci95=ci,undefined_replicates=undefined_diffs[endpoint],undefined_reason=reason,
            denominator_components=dict(raw=contributors[a],calibrated=contributors[b])))
    return dict(seed=SEED,replicates=REPLICATES,completed_replicates=REPLICATES,scheduled=len(ids),components=len(keys),
        component_order=list(keys),component_sizes=[len(positions[k]) for k in keys],estimates=estimates,
        calibrated_minus_raw=differences,wall_seconds=time.monotonic()-started,
        interval='paired_whole_component_linear_percentile_95',
        scope='Conditional on the one fitted map; excludes fitting uncertainty, grouping error, exposure and distribution shift.')


def deletion_sensitivity(rows, ids, components, suite, *, calibration_rows, purpose='production'):
    rows,ids=validate_rows(rows,ids,components,purpose)
    validate_suite(suite,calibration_rows)
    if purpose=='production':need(len(suite.deletion_maps)==49,'All49 deletion maps required')
    results=[]
    for component,mapping in suite.deletion_maps:
        changed=tuple(replace(r,calibrated=apply_mapping(mapping,r.raw,expected_fingerprint=mapping.fingerprint)) for r in rows)
        results.append(dict(omitted_component=component,map_fingerprint=mapping.fingerprint,
            operating_points=point_summary(changed,ids,components,purpose=purpose)['conditions']['calibrated']['operating_points']))
    ranges=[]
    for i,threshold in enumerate(THRESHOLDS):
        metrics={}
        for key in ('accepted','correct_accepted','incorrect_accepted','coverage','strict_correct_yield','conditional_error','conditional_precision'):
            values=[r['operating_points'][i][key] for r in results];present=[v for v in values if v is not None]
            metrics[key]=dict(minimum=min(present) if present else None,maximum=max(present) if present else None,
                              undefined_maps=len(values)-len(present),range_over_defined_maps_only=bool(len(values)-len(present)))
        ranges.append(dict(threshold=threshold,metrics=metrics))
    return dict(maps=len(results),coefficient_ranges=list(suite.coefficient_ranges),operating_point_ranges=ranges,
        per_deletion=results,confidence_interval=False,
        scope='Deletion sensitivity only. Overlapping training folds are not independent model samples.')


def held_out_summary(calibration_rows, suite, *, purpose='calibration_diagnostic'):
    """Descriptive aggregate of every fixed component-deletion prediction."""
    rows=tuple(calibration_rows);ids,components=validate_suite(suite,rows)
    need(tuple(r.id for r in rows)==ids,'Complete held-out outcome schedule')
    held=dict(suite.held_out_scores)
    projected=tuple(AnalysisRow(r.id,r.confidence.score,held[r.id],r.produced,r.admitted,r.strict_success) for r in rows)
    summary=point_summary(projected,ids,components,purpose=purpose)
    return dict(summary=summary,maps=len(suite.deletion_maps),confidence_interval=False,
        scope='All held-out calibration claims; descriptive only, with overlapping training folds. No independent fitted-model sampling claim.')
