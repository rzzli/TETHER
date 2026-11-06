"""Independent, explicitly bounded synthetic-fixture arithmetic.

Only the declared genetic_support-only synthetic scorer is qualified here.
Broader therapeutic evidence/scorers fail instead of borrowing producer logic.
"""
from itertools import combinations
import math
import statistics
import reconstruct as b

FEATURE_NAMES=('genetic_support','direction_alignment','perturbation_support','expression_relevance',
               'modality_feasibility','literature_support','safety_liability','pathway_support')
HYPOTHESIS=('target_id','indication_id','target_namespace_version','indication_namespace_version','intended_action','modality','tissue')


def rebuild(case,profile,scorer,claims,status):
    b.require(profile=='synthetic_demo' and scorer is not None and scorer['kind']=='synthetic_demo',
              'This independent arithmetic is qualified for synthetic fixtures only')
    b.require(scorer['coefficients']=={'genetic_support':0.8} and scorer['intercept']==0.25
              and scorer['required_features']==['genetic_support'] and scorer['missing_values']=={}
              and scorer['minimum_coverage']==1.0 and scorer['calibration']=='none',
              'Scorer outside the declared narrow fixture')
    observations=[claim['evidence']['observation'] for claim in claims]
    b.require(len(observations)<=20 and all(set(o['features'])<= {'genetic_support'} for o in observations),
              'Feature inputs outside the declared narrow fixture')
    scope=b.fingerprint({key:case['hypothesis'][key] for key in HYPOTHESIS})
    components=[{i} for i in range(len(observations))]
    for left,right in combinations(range(len(observations)),2):
        a,c=observations[left],observations[right]
        shared=(bool(a['dependency_group']) and a['dependency_group']==c['dependency_group']) or \
               (bool(a['study_id']) and a['study_id']==c['study_id']) or bool(set(a['context']['cohort_ids']) & set(c['context']['cohort_ids']))
        if shared:
            involved=[group for group in components if left in group or right in group]
            union=set().union(*involved)
            components=[group for group in components if group not in involved]+[union]
    values=[];included=[];excluded=[]
    for group in components:
        rows=[observations[i] for i in group]
        eligible=[row for row in rows if row['feature_scope']==scope and 'genetic_support' in row['features']]
        if not eligible:continue
        label=min(row['dependency_group'] or 'unknown-dependence:'+row['observation_id'] for row in rows)
        unique={row['features']['genetic_support'] for row in eligible}
        if len(unique)>1:excluded.append(label)
        else:
            value=next(iter(unique));b.require(type(value) in (int,float) and math.isfinite(value) and 0<=value<=1,'Invalid fixture support')
            values.append(value);included.extend(row['observation_id'] for row in eligible)
    support={'value':float(statistics.mean(values)) if values else None,
             'status':'observed' if values else 'conflicting' if excluded else 'not_measured',
             'dependency_groups':len(values),'observation_ids':sorted(included),'excluded_groups':sorted(excluded),
             'missing_reasons':['outside_applicability'] if any('genetic_support' in row['features'] and row['feature_scope']!=scope for row in observations) else []}
    features={'schema_version':'asof-features-v2','aggregation':'mean_of_unique_dependency_groups_v2','values':{
        name:(support if name=='genetic_support' else {'value':None,'status':'not_measured','dependency_groups':0,
               'observation_ids':[],'excluded_groups':[],'missing_reasons':[]}) for name in FEATURE_NAMES}}
    endpoint=case['endpoint'];h=case['hypothesis']
    reason=None;coverage=None;probability=None;contributions={};intercept=None
    if status!='completed':reason='run_incomplete'
    elif case['task']=='T6':reason='dossier_audit_has_no_clinical_probability'
    elif not (endpoint['name']==scorer['endpoint'] and endpoint['horizon_months']==scorer['horizon_months']
              and case['program']['phase_at_origin'] in scorer['phases'] and h['modality'] in scorer['modalities']
              and h['intended_action'] in scorer['intended_actions'] and h['target_namespace_version'] in scorer['target_namespace_versions']
              and h['indication_namespace_version'] in scorer['indication_namespace_versions']):reason='outside_scorer_applicability'
    else:
        coverage=1.0 if support['value'] is not None else 0.0
        if support['value'] is None:reason='required_features_missing'
        else:
            value=support['value'];coefficient=scorer['coefficients']['genetic_support'];intercept=scorer['intercept']
            contribution=value*coefficient
            contributions={'genetic_support':{'value':value,'coefficient':coefficient,'log_odds':contribution,
                'imputed':False,'observation_ids':support['observation_ids']}}
            probability=1/(1+math.exp(-(intercept+contribution)))
    prediction={'case_id':case['case_id'],'origin':case['origin'],'endpoint':endpoint['name'] if endpoint else None,
        'horizon_months':endpoint['horizon_months'] if endpoint else None,'status':'scored' if reason is None else 'audit_only' if case['task']=='T6' else 'abstained',
        'probability':probability,'reason':reason,'scorer_id':scorer['model_id'],'synthetic':True,'calibration':scorer['calibration'],
        'feature_coverage':coverage,'intercept':intercept,'contributions':contributions}
    return features,prediction


def verify(case,profile,scorer,commit):
    features,prediction=rebuild(case,profile,scorer,commit['claims'],commit['status'])
    b.require(b.canonical(features)==b.canonical(commit['features']),'Independently rebuilt fixture features differ')
    b.require(b.canonical(prediction)==b.canonical(commit['prediction']),'Independently rebuilt fixture prediction/contributions differ')
    return {'features':len(FEATURE_NAMES),'scope':'synthetic genetic-support fixture only; no clinical validity'}
