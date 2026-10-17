"""Versioned evaluator-only advancement rules; authored evidence is not gold.

No data access, model calls, retrospective subgroup inference or training labels.
"""
from datetime import date
import hashlib
import json

from tools.feasibility.program_outcomes import date_bounds


RELATIONS = {
    'product_relation': {'same_product', 'documented_alias', 'different_product_or_payload', 'unknown'},
    'regimen_relation': {'same_composition_route_schedule', 'changed_partner_route_or_schedule', 'unknown'},
    'dose_relation': {'same_dose', 'selection_from_origin_options', 'outside_origin_options', 'unknown'},
    'population_relation': {'same_core_population', 'origin_documented_nested_stratum',
                            'new_or_expanded_population', 'unknown'},
}
ALLOWED = {
    'product_relation': {'same_product', 'documented_alias'},
    'regimen_relation': {'same_composition_route_schedule'},
    'dose_relation': {'same_dose', 'selection_from_origin_options'},
    'population_relation': {'same_core_population', 'origin_documented_nested_stratum'},
}


def validate_policy(policy):
    if policy.get('protocol_id') != 'program-advancement-development-v0.3':
        raise ValueError('Unsupported advancement policy')
    if policy.get('role') != 'evaluation_only' or policy.get('clinical_training_labels') is not False:
        raise ValueError('Evaluator isolation required')
    if policy.get('allowed_phase_edges') != [[1, 2], [2, 3]]:
        raise ValueError('Unsupported phase policy')
    identity=policy.get('identity_rules',{})
    for key, values in [('allowed_product',ALLOWED['product_relation']),
                        ('allowed_regimen',ALLOWED['regimen_relation']),
                        ('allowed_dose',ALLOWED['dose_relation']),
                        ('allowed_population',ALLOWED['population_relation'])]:
        if set(identity.get(key,[])) != values:
            raise ValueError('Unsupported identity policy')
    if not date.fromisoformat(policy['origin']) < date.fromisoformat(policy['endpoint']):
        raise ValueError('Invalid observation window')


def evaluate(fact, policy):
    validate_policy(policy)
    for key, allowed in RELATIONS.items():
        if fact.get(key) not in allowed:raise ValueError('Invalid or missing relation: '+key)
    for key in ['origin_active','origin_at_risk']:
        if fact.get(key) is not None and type(fact[key]) is not bool:
            raise ValueError('Activity/risk requires boolean or null')
    for key in ['origin_stage','next_stage']:
        if fact.get(key) is not None and (type(fact[key]) is not int or fact[key] not in [1,2,3]):
            raise ValueError('Stage requires a resolved numerical phase or null')
    if fact.get('event_kind') not in {'experimental_regimen_first_dose','trial_any_arm_first_dose','enrollment_only','none'}:
        raise ValueError('Invalid event kind')
    if fact.get('bounds_quality') not in {'supported','conditional','unknown'}:
        raise ValueError('Invalid date bound quality')
    if fact.get('historical_content') not in {'verified','conditional','unavailable'}:
        raise ValueError('Invalid source qualification')
    if fact.get('event_linkage') not in {'reviewed','candidate','unknown'}:
        raise ValueError('Invalid event linkage')
    reasons=[]; scope_reasons=[]
    for key,allowed in ALLOWED.items():
        if fact[key] not in allowed:scope_reasons.append(key+':'+fact[key])
    narrowed=(fact['dose_relation']=='selection_from_origin_options' or
              fact['population_relation']=='origin_documented_nested_stratum')
    explicit_mismatch=any(fact[k] in {'different_product_or_payload','changed_partner_route_or_schedule',
                                    'new_or_expanded_population'} for k in RELATIONS)
    scope=('non_equivalent' if explicit_mismatch else 'unresolved') if scope_reasons else (
        'admissible_with_narrower_coverage' if narrowed else 'admissible_same_scope')
    reasons.extend(scope_reasons)
    if fact.get('origin_active') is not True:reasons.append('origin_arm_activity_unqualified')
    if fact.get('origin_at_risk') is not True:reasons.append('origin_risk_set_unqualified')
    edge=[fact.get('origin_stage'),fact.get('next_stage')]
    if edge not in policy['allowed_phase_edges']:reasons.append('next_numerical_phase_unqualified')
    if fact['event_kind']!='experimental_regimen_first_dose':reasons.append('experimental_regimen_receipt_not_established')
    interval=fact.get('event_interval') or {};low=interval.get('lower');high=interval.get('upper')
    for value in [low,high]:
        if value:date.fromisoformat(value)
    if low and high and low>high:raise ValueError('Reversed event interval')
    within=bool(low and high and policy['origin']<low<=high<=policy['endpoint'])
    if not within:reasons.append('incident_interval_not_within_window')
    if fact['bounds_quality']!='supported':reasons.append('event_bounds_'+fact['bounds_quality'])
    report=date_bounds(fact.get('report_date'))
    if not report or report[1]>policy['endpoint']:reasons.append('report_not_established_by_endpoint')
    if report and low and report[1]<low:raise ValueError('Report precedes lower event bound')
    if report and high and report[1]<high:raise ValueError('Report precedes upper event bound')
    if fact['historical_content']!='verified':reasons.append('historical_content_'+fact['historical_content'])
    if not fact.get('canonical_event_id') or fact['event_linkage']!='reviewed':reasons.append('canonical_event_link_unqualified')
    if fact.get('role')!='evaluation_only':raise ValueError('Evaluator-only evidence required')
    return {'candidate_id':fact['candidate_id'],'primary_qualification':'qualified' if not reasons else 'unresolved_or_inapplicable',
            'scope_relation':scope,'blocking_reasons':reasons,'event_interval_within_window':within,
            'strict_same_population_and_dose':not scope_reasons and not narrowed,
            'descriptive_trial_initiation_report':fact['event_kind']=='trial_any_arm_first_dose',
            'canonical_event_id':fact.get('canonical_event_id'),'clinical_training_label':None,
            'role':'evaluation_only','policy_id':policy['protocol_id']}


def group_shared_events(facts, results):
    by_case={r['candidate_id']:r for r in results}
    if len(by_case)!=len(results) or len({f['candidate_id'] for f in facts})!=len(facts):
        raise ValueError('Duplicate candidate application')
    if set(by_case)!={f['candidate_id'] for f in facts}:raise ValueError('Missing candidate result')
    groups={}
    for f in facts:
        event=f.get('canonical_event_id')
        if not event:continue
        group=groups.setdefault(event,{'canonical_event_id':event,'candidate_ids':[],
            'qualified_candidate_ids':[],'claim_signatures':[],'count_as_independent_per_predecessor':False})
        group['candidate_ids'].append(f['candidate_id'])
        if by_case[f['candidate_id']]['primary_qualification']=='qualified':group['qualified_candidate_ids'].append(f['candidate_id'])
        claim={k:f.get(k) for k in ['event_kind','event_interval','next_stage']}
        signature=hashlib.sha256(json.dumps(claim,sort_keys=True).encode()).hexdigest()
        if signature not in group['claim_signatures']:group['claim_signatures'].append(signature)
    for group in groups.values():
        group['reconciliation_required']=len(group['claim_signatures'])>1
        group['qualified_unique_event_count']=int(bool(group['qualified_candidate_ids']) and not group['reconciliation_required'])
        group['split_dependency_component']='shared-event:'+group['canonical_event_id']
    return list(groups.values())
