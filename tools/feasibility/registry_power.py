"""Dependency profiles and frozen synthetic power scenarios; no model predictions."""
from __future__ import annotations
import argparse
from bisect import bisect_left,bisect_right
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
from statistics import NormalDist,fmean as mean
import time

from asof.serde import sha256_file
from tools.feasibility.registry_extract import load,write
from tools.feasibility.registry_cohort import peak_memory_bytes


def placements(positive,negative):
    p,n=sorted(positive),sorted(negative)
    v10=[(bisect_left(n,x)+bisect_right(n,x))/(2*len(n)) for x in positive]
    v01=[1-(bisect_left(p,y)+bisect_right(p,y))/(2*len(p)) for y in negative]
    return v10,v01


def variance(values):
    center=mean(values)
    return math.fsum((x-center)**2 for x in values)/(len(values)-1)


def paired_stats(p_a,n_a,p_b,n_b):
    if len(p_a)!=len(p_b) or len(n_a)!=len(n_b) or min(len(p_a),len(n_a))<2:raise ValueError('Two paired observations per class required')
    if not all(math.isfinite(v) for values in [p_a,n_a,p_b,n_b] for v in values):raise ValueError('Nonfinite score')
    a10,a01=placements(p_a,n_a);b10,b01=placements(p_b,n_b)
    d10=[b-a for a,b in zip(a10,b10)];d01=[b-a for a,b in zip(a01,b01)]
    delta=mean(d10);v=variance(d10)/len(d10)+variance(d01)/len(d01)
    return {'auc_a':mean(a10),'auc_b':mean(b10),'difference':delta,'variance':v,
        'z':delta/math.sqrt(v) if v>0 else 0.0 if abs(delta)<1e-14 else None}


def wilson(k,n):
    if not 0<=k<=n or n<=0:raise ValueError('Invalid binomial counts')
    z=NormalDist().inv_cdf(.975);rate=k/n;denom=1+z*z/n
    center=(rate+z*z/(2*n))/denom
    radius=z*math.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/denom
    return [0.0 if k==0 else max(0.0,center-radius),1.0 if k==n else min(1.0,center+radius)]


def mc_pvalue(statistic,reference):
    if not reference or not math.isfinite(statistic) or any(not math.isfinite(x) for x in reference):raise ValueError('Invalid null reference')
    return (1+sum(x>=statistic for x in reference))/(len(reference)+1)


def simulate(n_case,n_control,auc,delta,rho,noise,reps,seed,alpha=.05,reference=None,collect_statistics=False):
    if min(n_case,n_control)<2:return {'estimable':False,'reason':'fewer_than_two_units_per_class','replicates':0}
    if not 0<auc<1 or not 0<auc+delta<1 or not -1<=rho<=1 or reps<1 or not 0<alpha<1:raise ValueError('Invalid simulation parameters')
    if set(noise)!={'case_to_control','control_to_case'} or not all(0<=p<=1 for p in noise.values()):raise ValueError('Invalid label-error assumptions')
    rng=random.Random(seed);normal=NormalDist();mu_a=math.sqrt(2)*normal.inv_cdf(auc);mu_b=math.sqrt(2)*normal.inv_cdf(auc+delta)
    critical=normal.inv_cdf(1-alpha/2);orthogonal=math.sqrt(1-rho*rho)
    if reference is not None and (not reference or any(not math.isfinite(x) for x in reference)):raise ValueError('Invalid null reference')
    ordered_reference=sorted(reference) if reference is not None else None
    rejected=0;valid=0;observed_case=[];deltas=[];statistics=[]
    for _ in range(reps):
        pa=[];na=[];pb=[];nb=[]
        for truth,count in [(True,n_case),(False,n_control)]:
            error=noise['case_to_control' if truth else 'control_to_case']
            for _ in range(count):
                z1=rng.gauss(0,1);z2=rng.gauss(0,1)
                a=z1+(mu_a if truth else 0);b=rho*z1+orthogonal*z2+(mu_b if truth else 0)
                label=not truth if error and rng.random()<error else truth
                if label:pa.append(a);pb.append(b)
                else:na.append(a);nb.append(b)
        if min(len(pa),len(na))<2:continue
        stats=paired_stats(pa,na,pb,nb)
        if stats['z'] is None:continue
        absolute=abs(stats['z']);valid+=1
        pvalue=(1+len(reference)-bisect_left(ordered_reference,absolute))/(len(reference)+1) if reference is not None else None
        rejected+=(pvalue<=alpha) if reference is not None else absolute>critical
        if collect_statistics:statistics.append(absolute)
        deltas.append(stats['difference']);observed_case.append(len(pa))
    result={'estimable':bool(valid),'requested_replicates':reps,'valid_replicates':valid,'invalid_replicates':reps-valid,
        'rejections':rejected,'rejection_probability':rejected/valid if valid else None,
        'monte_carlo_95_interval':wilson(rejected,valid) if valid else None,
        'mean_observed_auc_difference':mean(deltas) if valid else None,'mean_observed_case_units':mean(observed_case) if valid else None}
    if collect_statistics:result['absolute_statistics']=statistics
    return result


def dependency_profile(programs,mode):
    if mode not in {'v04_component','shared_target_connections','shared_target_and_sponsor_connections'}:raise ValueError('Unknown graph mode')
    pids={p['program_id'] for p in programs}
    if len(pids)!=len(programs):raise ValueError('Duplicate programs')
    parent={p['dependency_component_id']:p['dependency_component_id'] for p in programs};owner={}
    def find(x):
        while x!=parent[x]:parent[x]=parent[parent[x]];x=parent[x]
        return x
    for p in programs:
        keys=[]
        if mode!='v04_component':keys+=['target:'+t for t in p['target_ids']]
        if mode=='shared_target_and_sponsor_connections':keys+=['sponsor:'+s for s in p['origin_lead_sponsors']]
        for key in keys:
            component=p['dependency_component_id']
            if key in owner:
                a,b=find(component),find(owner[key]);parent[max(a,b)]=min(a,b)
            else:owner[key]=component
    groups=defaultdict(list)
    for p in programs:groups[find(p['dependency_component_id'])].append(p)
    units=[]
    for key,ps in sorted(groups.items()):
        labels={p['label_state'] for p in ps}
        state='proxy_recorded_start' if 'recorded_next_phase_start' in labels else 'unresolved' if 'unresolved_transition' in labels else 'proxy_no_recorded_start'
        units.append({'unit_id':key,'program_ids':sorted(p['program_id'] for p in ps),'state':state})
    return {'mode':mode,'programs':len(programs),'units':len(units),'states':dict(Counter(u['state'] for u in units)),
        'largest_unit_programs':max((len(u['program_ids']) for u in units),default=0),'memberships':units,
        'interpretation':'Explicit graph components and any-program proxy endpoint; not effective sample size or validated outcomes.'}


def checked_parent(anchor):
    item=anchor['canonical_manifest'];path=Path(item['path'])
    if sha256_file(path)!=item['sha256']:raise ValueError('Changed parent seal')
    seen=set()
    for member in load(path)['files']:
        p=(path.parent/member['path']).resolve()
        if not p.is_relative_to(path.parent.resolve()) or p in seen:raise ValueError('Unsafe parent member')
        seen.add(p)
        if sha256_file(p)!=member['sha256']:raise ValueError('Changed parent artifact')
    return path.parent


def run(protocol,freeze,output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    try:
        policy=load(protocol);pin=load(freeze)
        if policy['protocol_id'] not in {'registry-feasibility-power-v0.1','registry-feasibility-power-v0.2'} or policy['role']!='evaluation_only':raise ValueError('Invalid power protocol')
        calibrated=policy['protocol_id'].endswith('v0.2')
        if sha256_file(protocol)!=pin['protocol']['sha256']:raise ValueError('Changed power protocol')
        for p in pin['parents']:
            if sha256_file(Path(p['path']))!=p['sha256']:raise ValueError('Changed parent anchor')
        if calibrated and sha256_file(Path(policy['parent_diagnostic']))!=pin['diagnostic_sha256']:raise ValueError('Changed calibration diagnostic')
        root=checked_parent(load(pin['parents'][0]['path']));scope=checked_parent(load(pin['parents'][1]['path']))
        programs=[json.loads(line) for line in (root/'cohort-v04/cohort.jsonl').read_text(encoding='utf-8').splitlines()]
        audits={p['program_id']:p for p in load(scope/'program-scope.json')}
        if set(audits)!={p['program_id'] for p in programs}:raise ValueError('Scope and cohort membership differ')
        write(output/'execution.json',{'protocol_sha256':sha256_file(protocol),'code_sha256':sha256_file(Path(__file__)),'role':'evaluation_only'})
        held={pid for pid,a in audits.items() if a['prior_risk_alerts'] or a['clinical_scope'] in {'outside_disease_focus','broad_condition_requires_review'}}
        profiles={}
        for view,ps in [('base',programs),('uncertainty_hold',[p for p in programs if p['program_id'] not in held])]:
            for mode in policy['analysis_units']:profiles[view+':'+mode]=dependency_profile(ps,mode)
        write(output/'sample-profiles.json',profiles)
        scenarios=[]
        for key,profile in profiles.items():
            scenarios.append({'name':key,'n_case':profile['states'].get('proxy_recorded_start',0),
                'n_control':profile['states'].get('proxy_no_recorded_start',0),'reps':policy['primary_replicates']})
        for n in policy['hypothetical_positive_units']:scenarios.append({'name':f'hypothetical:{n}','n_case':n,
            'n_control':policy['hypothetical_no_recorded_units'],'reps':policy['grid_replicates']})
        results=[]
        def one(spec,auc,delta,rho,noise,reps,reference=None,collect=False,seed_tag='power'):
            config={**spec,'auc':auc,'delta':delta,'rho':rho,'noise':noise,'reps':reps}
            seed=int(hashlib.sha256((str(policy['seed'])+(seed_tag if calibrated else '')+json.dumps(config,sort_keys=True)).encode()).hexdigest()[:16],16)
            result=simulate(spec['n_case'],spec['n_control'],auc,delta,rho,noise,reps,seed,policy['alpha'],reference,collect)
            return {**config,'result':result}
        references={};reference_rows=[]
        def reference_for(spec,auc,rho,noise):
            if not calibrated or min(spec['n_case'],spec['n_control'])<2:return None
            key=json.dumps([spec['n_case'],spec['n_control'],auc,rho,noise],sort_keys=True)
            if key not in references:
                row=one(spec,auc,0,rho,noise,policy['calibration_replicates'],collect=True,seed_tag='null_reference')
                references[key]=row['result']['absolute_statistics'];reference_rows.append(row)
            return references[key]
        base=scenarios[0];calibration=[]
        for rho in policy['within_class_score_correlation']:
            ref=reference_for(base,policy['baseline_auc'][0],rho,policy['label_error'][0])
            item=one(base,policy['baseline_auc'][0],0,rho,policy['label_error'][0],policy['null_replicates'],ref,seed_tag='heldout_null_validation')
            interval=item['result'].get('monte_carlo_95_interval')
            item['nominal_alpha_in_mc_interval']=bool(interval and interval[0]<=policy['alpha']<=interval[1]);calibration.append(item)
            if calibrated:
                limit=policy['alpha']+NormalDist().inv_cdf(1-.05/3)*math.sqrt(policy['alpha']*(1-policy['alpha'])*(1/policy['null_replicates']+1/policy['calibration_replicates']))
                item['inflation_acceptance_limit']=limit
                item['calibration_passed']=bool(item['result'].get('rejection_probability') is not None and item['result']['rejection_probability']<=limit)
        write(output/'null-calibration.json',calibration)
        for spec in scenarios:
            for auc in policy['baseline_auc']:
                for rho in policy['within_class_score_correlation']:
                    for noise in policy['label_error']:
                        ref=reference_for(spec,auc,rho,noise)
                        results.append(one(spec,auc,policy['auc_difference'],rho,noise,spec['reps'],ref))
            print(json.dumps({'stage':'scenario_complete','name':spec['name'],'n_case':spec['n_case'],'n_control':spec['n_control']}),flush=True)
        write(output/'power-scenarios.json',results)
        if calibrated:write(output/'calibration-references.json',reference_rows)
        costs=policy['annotation_cost_scenarios']
        write(output/'annotation-cost-scenarios.json',[{'cases':n,'reviewers':costs['reviewers'],'minutes_per_case':minutes,
            'reviewer_hours':n*costs['reviewers']*minutes/60,'measured':False} for n in costs['cases'] for minutes in costs['minutes_per_case']])
        report={'role':'evaluation_only','decision':'revise_before_clinical_training_or_locked_evaluation',
            'sample_profiles':{k:{x:y for x,y in v.items() if x!='memberships'} for k,v in profiles.items()},
            'scenario_rows':len(results),'nominal_target_power':policy['target_power'],
            'null_calibration_warnings':sum(not c.get('calibration_passed',c['nominal_alpha_in_mc_interval']) for c in calibration),
            'test_method':'finite_rank_parametric_null_calibration' if calibrated else 'asymptotic_normal_approximation',
            'assumption_warning':'Synthetic normal-score power conditional on proxy class sizes, not empirical model performance or clinical-label validity.',
            'clinical_readiness':{'independent_scientific_review':False,'adjudicated_negatives_or_censoring':False,
                'full_regimen_population_equivalence':False,'locked_model_window_chronology':'Task 3 pending'},
            'next':'Task 3 chronology/window/preregistration audit; do not train from these proxy labels.',
            'clinical_probabilities':None,'training_labels':0,'provider_spend_usd':0}
        write(output/'summary.json',report)
    except BaseException as exc:
        write(output/'failure.json',{'type':type(exc).__name__,'error':str(exc),'automatic_retry':False});raise
    finally:write(output/'resources.json',{'elapsed_seconds':time.monotonic()-started,'peak_memory_bytes':peak_memory_bytes(),'provider_spend_usd':0})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--protocol',type=Path,required=True);p.add_argument('--freeze',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.protocol,a.freeze,a.output)
