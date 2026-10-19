"""Pure evaluator accounting and dependence gates; no fitting or outcome inference.

Rows retain a program-level estimand for each separate endpoint. Connected
components describe dependence; neither their count nor an any-positive label
is an effective sample size. This adapter does not estimate statistical power.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
import re
import unicodedata

from asof.serde import ContractError
from tools.science.qualification import ENDPOINTS, utc, validate_outcome, validate_source_refs

STATES=('qualified_positive','qualified_negative','resolved_unqualified','unresolved','censored','competing_event')
MODES={'core':(), 'target_sensitivity':('target',), 'sponsor_sensitivity':('sponsor',),
       'target_sponsor_sensitivity':('target','sponsor')}


def text(value,field):
    if not isinstance(value,str) or not value.strip() or value!=value.strip():
        raise ContractError('Nonempty exact identity required: '+field)
    return value


def identifiers(values,field):
    if not isinstance(values,list):raise ContractError('Identifier list required: '+field)
    result=[text(value,field) for value in values]
    if len(result)!=len(set(result)):raise ContractError('Duplicate identifier: '+field)
    return tuple(sorted(result))


def sponsor_key(value):
    return ' '.join(unicodedata.normalize('NFKC',value).casefold().split())


def validate_records(records,expected_program_ids=None):
    rows={};programs={};windows=set();program_endpoints=defaultdict(set)
    for original in records:
        if not isinstance(original,dict):raise ContractError('Outcome record must be an object')
        row=dict(original)
        required={'program_id','nct_id','drug_ids','target_ids','lead_sponsors','event_id','origin_risk_qualified'}
        if not required<=row.keys():raise ContractError('Incomplete dependence/origin-risk fields')
        pid=text(row['program_id'],'program_id');nct=text(row['nct_id'],'nct_id')
        if not re.fullmatch(r'NCT\d{8}',nct):raise ContractError('Invalid source trial identity')
        if row['origin_risk_qualified'] is not None and type(row['origin_risk_qualified']) is not bool:
            raise ContractError('Origin-risk qualification must be true, false or null')
        if row.get('value') is not None and row['origin_risk_qualified'] is not True:
            raise ContractError('Binary outcome requires qualified origin risk')
        checked=validate_outcome(row)
        endpoint=row['endpoint_id'];key=(pid,endpoint)
        if key in rows:raise ContractError('Duplicate program/endpoint outcome')
        metadata={'nct_id':nct,'drug_ids':identifiers(row['drug_ids'],'drug_ids'),
            'target_ids':identifiers(row['target_ids'],'target_ids'),
            'lead_sponsors':identifiers(row['lead_sponsors'],'lead_sponsors')}
        if pid in programs and metadata!=programs[pid]:raise ContractError('Program origin metadata differs across endpoints')
        programs[pid]=metadata
        if row['event_id'] is not None:text(row['event_id'],'canonical event_id')
        state=('qualified_positive' if row['value']==1 else 'qualified_negative') if checked['binary_eligible'] else (
            'resolved_unqualified' if row['status']=='resolved' else row['status'])
        rows[key]={'record':row,'state':state,'binary_eligible':checked['binary_eligible']}
        program_endpoints[pid].add(endpoint)
        windows.add(tuple(utc(row[field]).isoformat() for field in ('origin_at','horizon_at','ascertainment_at')))
    if len(windows)>1:raise ContractError('Mixed scientific observation windows cannot be pooled')
    if expected_program_ids is not None:
        expected=identifiers(list(expected_program_ids),'expected_program_ids')
        if set(programs)!=set(expected):raise ContractError('Program membership differs from expected frozen universe')
    for pid in programs:
        if program_endpoints[pid]!=ENDPOINTS:
            raise ContractError('Each program requires each of the three endpoints exactly once')
    return rows,programs,next(iter(windows),None)


def counts(entries):
    result={state:0 for state in STATES}
    for entry in entries:result[entry['state']]+=1
    result['qualified_binary']=result['qualified_positive']+result['qualified_negative']
    result['total']=sum(result[state] for state in STATES)
    return result


def graph_profile(rows,programs,mode):
    if mode not in MODES:raise ContractError('Unknown dependence sensitivity')
    parents={pid:pid for pid in programs};keys=defaultdict(set)
    for pid,program in programs.items():
        keys[('trial',program['nct_id'])].add(pid)
        for drug in program['drug_ids']:keys[('drug',drug)].add(pid)
        if 'target' in MODES[mode]:
            for target in program['target_ids']:keys[('target',target)].add(pid)
        if 'sponsor' in MODES[mode]:
            for sponsor in program['lead_sponsors']:keys[('sponsor',sponsor_key(sponsor))].add(pid)
    for (pid,_),entry in rows.items():
        event=entry['record']['event_id']
        if event is not None:keys[('canonical_event',event)].add(pid)
    def find(pid):
        while parents[pid]!=pid:
            parents[pid]=parents[parents[pid]];pid=parents[pid]
        return pid
    shared=[]
    for (kind,value),members in sorted(keys.items()):
        ordered=sorted(members)
        if len(ordered)<2:continue
        shared.append({'kind':kind,'value':value,'program_ids':ordered})
        for pid in ordered[1:]:
            a,b=find(ordered[0]),find(pid)
            if a!=b:parents[max(a,b)]=min(a,b)
    groups=defaultdict(list)
    for pid in sorted(programs):groups[find(pid)].append(pid)
    components=[]
    for members in sorted(groups.values()):
        composition={endpoint:counts(rows[(pid,endpoint)] for pid in members) for endpoint in sorted(ENDPOINTS)}
        components.append({'component_id':'component:'+hashlib.sha256(json.dumps(members).encode()).hexdigest()[:24],
            'program_ids':members,'program_count':len(members),'endpoint_class_composition':composition,
            'mixed_qualified_classes':{endpoint:bool(c['qualified_positive'] and c['qualified_negative']) for endpoint,c in composition.items()},
            'component_analysis_label':None})
    return {'mode':mode,'program_nodes':len(programs),'outcome_rows':len(rows),
        'edge_keys':['trial','drug','canonical_event',*MODES[mode]],'component_count':len(components),
        'component_sizes':sorted((len(members) for members in groups.values()),reverse=True),
        'components':components,'shared_keys':shared,'effective_sample_size':None,
        'interpretation':'Components are dependence descriptors; endpoint classes remain program observations, with no OR aggregation or effective-N claim.'}


def score_index(scores,rows):
    """Optional externally qualified score coverage, never a power estimate.

    Each score row has program_id, endpoint_id, score (finite numeric or null),
    qualified (bool), scorer_id and source_evidence. Qualified scores require a
    retained source fingerprint/locator. One scorer vector may be assessed at a
    time; model chronology/score qualification is an upstream responsibility.
    """
    result={};scorers=set()
    for score in scores or []:
        if not isinstance(score,dict):raise ContractError('Score record must be an object')
        key=(text(score.get('program_id'),'score program_id'),text(score.get('endpoint_id'),'score endpoint_id'))
        if key not in rows or key in result:raise ContractError('Unknown or duplicate program/endpoint score')
        if type(score.get('qualified')) is not bool:raise ContractError('Score qualification must be explicit boolean')
        value=score.get('score')
        if value is not None and (type(value) not in (int,float) or not math.isfinite(value)):
            raise ContractError('Score must be finite numeric or null')
        if score['qualified']:
            if value is None:raise ContractError('Qualified score cannot be null')
            scorers.add(text(score.get('scorer_id'),'scorer_id'));validate_source_refs(score.get('source_evidence'))
        result[key]=score['qualified']
    if len(scorers)>1:raise ContractError('Different scorer vectors cannot be pooled')
    return result


def assess(records,*,expected_program_ids=None,qualified_scores=None,
           features_qualified=False,labels_qualified=False,scorer_qualified=False):
    """Return counts, four dependence profiles and explicit no-fit/power gates.

    Qualified counts and an explicit prospective score/dependence design can support
    planning without observed predictions. Optional score coverage describes a
    different empirical evaluation prerequisite; it is not a power-planning gate.
    No simulation, scores, outcomes or fitted model are manufactured here.
    """
    for flag in (features_qualified,labels_qualified,scorer_qualified):
        if type(flag) is not bool:raise ContractError('Fitting qualification gates must be explicit booleans')
    rows,programs,window=validate_records(records,expected_program_ids)
    scores=score_index(qualified_scores,rows);endpoints={}
    for endpoint in sorted(ENDPOINTS):
        entries={pid:entry for (pid,e),entry in rows.items() if e==endpoint};summary=counts(entries.values())
        binary={pid for pid,entry in entries.items() if entry['binary_eligible']}
        scored={pid for pid in binary if scores.get((pid,endpoint)) is True}
        minimum=summary['qualified_positive']>=2 and summary['qualified_negative']>=2
        score_ready=bool(binary) and scored==binary
        reasons=[]
        if not minimum:reasons.append('fewer_than_two_qualified_observations_per_class')
        if minimum:reasons.append('dependence_aware_power_design_not_supplied')
        evaluation_reasons=[]
        if not scored:evaluation_reasons.append('no_qualified_scores')
        elif not score_ready:evaluation_reasons.append('qualified_score_coverage_incomplete')
        fit_reasons=[name+'_not_qualified' for name,flag in (
            ('features',features_qualified),('labels',labels_qualified),('scorer',scorer_qualified)) if not flag]
        fit_reasons+=reasons+['power_not_qualified']
        endpoints[endpoint]={'counts':summary,'qualified_scored_binary_observations':len(scored),
            'origin_risk_false':sum(e['record']['origin_risk_qualified'] is False for e in entries.values()),
            'origin_risk_unknown':sum(e['record']['origin_risk_qualified'] is None for e in entries.values()),
            'power':{'status':'requires_dependence_aware_design' if minimum else 'nonestimable',
                'estimable':False,'estimated_power':None,'target_power':0.8,'target_auroc_difference':0.05,
                'minimum_class_counts_met':minimum,'qualified_score_coverage_complete':score_ready,
                'observed_prediction_scores_required_for_prospective_planning':False,
                'reasons':reasons,'simulations_performed':0,'effective_sample_size':None},
            'empirical_prediction_readiness':{'qualified_score_coverage_complete':score_ready,
                'reasons':evaluation_reasons},
            'calibration_precision':{'status':'not_assessed_separate_requirement','estimate':None,
                'reason':'Discrimination power target does not establish calibration precision or qualified probabilities.'},
            'fitting':{'decision':'no_fit','fit_allowed':False,'reasons':fit_reasons}}
    observations=[{'program_id':pid,'endpoint_id':endpoint,'source_value':entry['record']['value'],
        'analysis_value':entry['record']['value'] if entry['binary_eligible'] else None,
        'state':entry['state'],'source_status':entry['record']['status'],
        'origin_risk_qualified':entry['record']['origin_risk_qualified']}
        for (pid,endpoint),entry in sorted(rows.items())]
    return {'schema_version':1,'role':'evaluation_only','status':'descriptive_feasibility_only',
        'programs':len(programs),'outcome_rows':len(rows),'endpoint_ids':sorted(ENDPOINTS),
        'window':dict(zip(('origin_at','horizon_at','ascertainment_at'),window)) if window else None,
        'endpoints':endpoints,'dependence_profiles':{mode:graph_profile(rows,programs,mode) for mode in MODES},
        'observations':observations,'trained_models':0,'probabilities_derived':0,'provider_spend_usd':0,
        'limits':['Outcome contract validation is not external scientific validation.',
            'Source program endpoints are repeated observations, not independent program nodes.',
            'Unknown identifiers are not evidence of independence; sponsor matching uses exact normalized names only.',
            'Clinical estimands are not replaced with component-level any-positive proxies.',
            'Power needs prespecified dependence, paired-score/effect, label-error/missingness and significance/null-calibration assumptions.']}
