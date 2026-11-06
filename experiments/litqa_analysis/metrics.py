"""Outcome-independent grouping and paired SC04 contrasts; standard library only."""
from collections.abc import Mapping
import math
import random

ARMS=('L/O','E/O','L/R','E/R')


def need(value,message):
    if not value:raise ValueError(message)


def publication_components(ids,dois_by_id):
    """Connect questions sharing any annotated DOI, transitively.

    Group construction must happen without consulting outcome labels. Empty
    annotation sets remain singleton questions, never discarded observations.
    """
    ids=tuple(ids);need(ids and len(set(ids))==len(ids) and set(dois_by_id)==set(ids),'Complete unique annotation schedule')
    parent=list(range(len(ids)));owner={}
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for i,key in enumerate(ids):
        values=dois_by_id[key]
        need(isinstance(values,(list,tuple,set,frozenset)) and all(isinstance(d,str) and d for d in values),'Explicit annotation identities')
        for doi in values:
            if doi in owner:
                a,b=find(i),find(owner[doi]);parent[max(a,b)]=min(a,b)
            else:owner[doi]=i
    groups={}
    for i,key in enumerate(ids):groups.setdefault(find(i),[]).append(key)
    return tuple(tuple(groups[i]) for i in sorted(groups))


def contrasts(rates):
    need(set(rates)==set(ARMS),'Exactly four primary arms')
    lo,eo,lr,er=(rates[a] for a in ARMS)
    return dict(expansion_at_lexical=eo-lo,ranking_at_lexical=lr-lo,combined_vs_lexical=er-lo,
                interaction=(er-lr)-(eo-lo),marginal_expansion=((eo-lo)+(er-lr))/2,
                marginal_ranking=((lr-lo)+(er-eo))/2)


def percentile(values,p):
    values=sorted(values);need(values and 0<=p<=1,'Percentile inputs')
    position=(len(values)-1)*p;low=math.floor(position);high=math.ceil(position)
    return values[low]+(values[high]-values[low])*(position-low)


def paired_bootstrap(ids,flags_by_arm,groups,*,replicates=10000,seed=20261106):
    ids=tuple(ids);groups=tuple(tuple(g) for g in groups)
    need(ids and len(set(ids))==len(ids),'Unique full paired schedule')
    need(set(flags_by_arm)==set(ARMS) and all(len(v)==len(ids) for v in flags_by_arm.values()),'Complete paired arm outcomes')
    need(all(type(v) in (bool,int) and v in (0,1) for values in flags_by_arm.values() for v in values),'Binary case outcomes required')
    flat=[key for group in groups for key in group]
    need(groups and all(groups) and len(flat)==len(set(flat))==len(ids) and set(flat)==set(ids),'Groups must partition full schedule')
    need(type(replicates) is int and 1<=replicates<=100000 and type(seed) is int and 0<=seed<2**32,'Declared bootstrap settings')
    index={key:i for i,key in enumerate(ids)}
    totals=[sum(flags_by_arm[a]) for a in ARMS]
    rates={arm:totals[i]/len(ids) for i,arm in enumerate(ARMS)};point=contrasts(rates)
    result=dict(case_count=len(ids),group_count=len(groups),group_sizes=[len(g) for g in groups],
        seed=seed,requested_replicates=replicates,method='paired cluster resampling; ratio recomputed per draw; linear percentile interval',
        rates=rates,contrasts={name:dict(estimate=value,ci95=None) for name,value in point.items()},
        uncertainty_estimable=len(groups)>1)
    if len(groups)==1:
        result.update(completed_replicates=0,limitation='One independent group cannot estimate between-group uncertainty.');return result
    group_totals=[(len(g),[sum(flags_by_arm[a][index[k]] for k in g) for a in ARMS]) for g in groups]
    rng=random.Random(seed);samples={name:[] for name in point}
    for _ in range(replicates):
        denominator=0;counts=[0,0,0,0]
        for _ in groups:
            size,values=group_totals[rng.randrange(len(groups))];denominator+=size
            for i,value in enumerate(values):counts[i]+=value
        values=contrasts({a:counts[i]/denominator for i,a in enumerate(ARMS)})
        for name,value in values.items():samples[name].append(value)
    for name,values in samples.items():result['contrasts'][name]['ci95']=[percentile(values,.025),percentile(values,.975)]
    result['completed_replicates']=replicates
    return result


def precision_ratio(correct,answered):
    need(type(correct) is int and type(answered) is int and 0<=correct<=answered,'Precision counts')
    return dict(native_precision=correct/answered if answered else 0.0,
                precision_defined=bool(answered),statistical_precision=correct/answered if answered else None)
