"""Source-inclusive technical audit of development sizing, never independent gold.

Checks original JSONL bytes rather than trusting the SQLite index. An independent
relaxed intervention scan flags possible missed events; it cannot estimate recall.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import time

from tether_engine.serde import sha256_file
from tools.feasibility.registry_extract import load, write
from tools.feasibility.registry_cohort import norm, category, start_bounds, mapping


def source_check(program, event, row, origin, endpoint):
    """Check literal event fields independently of the builder's arm index."""
    s=row['study'];errors=[]
    if s['nct_id']!=event['nct_id']:errors.append('nct_mismatch')
    if category(s['phase'])!='PHASE'+str(program['origin_phase']+1):errors.append('phase_mismatch')
    if s['nct_id'] in program['origin_trials']:errors.append('not_distinct_trial')
    if program['condition'] not in {norm(c['name']) for c in row['conditions']}:errors.append('condition_mismatch')
    if event['status']=='recorded_next_phase_start':
        lo,hi,_=start_bounds(s.get('start_date'),s.get('start_month_year'))
        if category(s.get('start_date_type'))!='ACTUAL' or not lo or not origin<lo<=hi<=endpoint:errors.append('actual_window_mismatch')
        if category(s.get('overall_status'))=='WITHDRAWN':errors.append('withdrawn_actual_contradiction')
        for key in ['study_first_posted_date','last_update_posted_date']:
            if not s.get(key) or s[key]>event['source_proof']['snapshot']:errors.append('posting_mismatch')
        arm=next((a for a in row['design_groups'] if a['id']==event['source_arm_id']),None)
        if not arm or category(arm['group_type'])!='EXPERIMENTAL':errors.append('experimental_arm_mismatch')
    return errors


def identity_check(program,arm_id,row,aliases,reverse):
    arm=next((a for a in row['design_groups'] if a['id']==arm_id),None)
    if not arm or category(arm['group_type'])!='EXPERIMENTAL':return ['arm_identity_or_role']
    linked={link['intervention_id'] for link in row['design_group_interventions'] if link['design_group_id']==arm_id}
    products=[d for d in row['interventions'] if d['id'] in linked and category(d['intervention_type']) in {'DRUG','BIOLOGICAL'}
        and not re.search(r'\b(placebo|sham|vehicle)\b',norm(d['name']))]
    if len(products)!=1:return ['active_product_count']
    drug=products[0];terms=[drug['name']]+[a['name'] for a in row['intervention_other_names'] if a['intervention_id']==drug['id']]
    ids=set().union(*(aliases.get(norm(term),set()) for term in terms))
    if ids!={program['drug_id']}:return ['exact_alias_identity']
    if not any(re.search(r'(?<!\w)'+re.escape(t)+r'(?!\w)',norm(arm['title'])) for t in reverse[program['drug_id']]):
        return ['explicit_title_identity']
    return []


def audit(frames_path, cohort_path, policy_path, output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    cohort_path=Path(cohort_path);frames=load(frames_path);policy=load(policy_path)
    if frames['protocol_sha256']!=sha256_file(policy_path):raise ValueError('Protocol mismatch')
    programs={p['program_id']:p for p in map(json.loads,(cohort_path/'cohort.jsonl').read_text(encoding='utf-8').splitlines())}
    events=load(cohort_path/'candidate-events.json');sample=load(cohort_path/'audit-sample.json')
    if len(programs)!=load(cohort_path/'summary.json')['cohort_programs']:raise ValueError('Duplicate/missing program')
    wanted=defaultdict(dict)
    def want(proof):
        path=str(Path(proof['source']).resolve());line=proof['line']
        if line in wanted[path] and wanted[path][line]!=proof['row_sha']:raise ValueError('Conflicting row proof')
        wanted[path][line]=proof['row_sha']
    for p in programs.values():
        for proof in p['source_proofs']:want(proof)
    for e in events:
        want(e['source_proof'])
        for v in e['source_versions']:want(v['source_proof'])
    aliases,_,_=mapping(policy);source_rows={};relaxed=defaultdict(dict);reverse=defaultdict(list)
    for term,ids in aliases.items():
        if len(ids)==1:reverse[next(iter(ids))].append(term)
    control_keys={(a['program']['drug_id'],a['program']['condition']):a['program'] for a in sample
        if a['program']['label_state']=='no_recorded_transition_by_cutoff'}
    scanned=0
    with (output/'retained-source-rows.jsonl').open('x',encoding='utf-8',newline='\n') as retained:
        for frame in frames['snapshots']:
            path=Path(frame['path']).resolve()
            if sha256_file(path)!=frame['sha256']:raise ValueError('Changed source frame')
            selected=wanted.get(str(path),{})
            with path.open('rb') as stream:
                for line,raw in enumerate(stream,1):
                    scanned+=1
                    if line in selected:
                        digest=hashlib.sha256(raw).hexdigest()
                        if digest!=selected[line]:raise ValueError('Changed original row')
                        row=json.loads(raw);source_rows[(str(path),line)]=row
                        retained.write(json.dumps({'source':str(path),'line':line,'row_sha':digest,'row':row},ensure_ascii=False)+'\n')
                    # Separate broad search includes comparator/unresolved roles, and
                    # mixed or skipped phases. Hits are audit leads, not transitions.
                    if frame['snapshot_date']==policy['origin']:continue
                    row=json.loads(raw);s=row['study'];conditions={norm(c['name']) for c in row['conditions']}
                    others=defaultdict(list)
                    for a in row['intervention_other_names']:others[a['intervention_id']].append(a['name'])
                    ids=set()
                    for d in row['interventions']:
                        for term in [d['name'],*others[d['id']]]:ids.update(aliases.get(norm(term),set()))
                    for drug in ids:
                        for condition in conditions:
                            p=control_keys.get((drug,condition))
                            if not p or s['nct_id'] in p['origin_trials']:continue
                            numeric=[int(n) for n in re.findall(r'[1-4]',category(s['phase']))]
                            if not numeric or max(numeric)<=p['origin_phase']:continue
                            lo,hi,precision=start_bounds(s.get('start_date'),s.get('start_month_year'))
                            if category(s.get('start_date_type'))=='ACTUAL' and hi and hi<=policy['origin']:continue
                            relaxed[p['program_id']][(s['nct_id'],frame['snapshot_date'])]={
                                'nct_id':s['nct_id'],'snapshot':frame['snapshot_date'],'phase':s['phase'],
                                'start':s.get('start_month_year'),'date_type':s.get('start_date_type'),
                                'source':str(path),'line':line,'row_sha':hashlib.sha256(raw).hexdigest(),
                                'meaning':'relaxed exact-alias/condition lead; regimen/role and phase-edge not qualified'}
    if sum(len(v) for v in wanted.values())!=len(source_rows):raise ValueError('Missing original row proofs')
    def original(proof):return source_rows[(str(Path(proof['source']).resolve()),proof['line'])]
    checked_events=[]
    for e in events:
        p=programs[e['program_id']];errors=source_check(p,e,original(e['source_proof']),policy['origin'],policy['occurrence_endpoint'])
        if e['status']=='recorded_next_phase_start':errors+=identity_check(p,e['source_arm_id'],original(e['source_proof']),aliases,reverse)
        if errors:raise ValueError('Source event contradiction: '+e['event_id']+' '+str(errors))
        checked_events.append({'program_id':p['program_id'],'event_id':e['event_id'],'source_fields':'passed','status':e['status']})
    for p in programs.values():
        if p['training_label'] is not None or p['individual_censoring_date'] is not None:raise ValueError('Unadjudicated training/censoring value')
        candidates=[]
        for proof in p['source_proofs']:
            raw_row=original(proof);s=raw_row['study']
            if proof['nct']!=s['nct_id'] or proof['phase_raw']!=s['phase']:raise ValueError('Origin proof projection differs')
            if identity_check(p,proof['arm_id'],raw_row,aliases,reverse):raise ValueError('Origin source identity/role mismatch')
            lo,hi,_=start_bounds(s.get('start_date'),s.get('start_month_year'))
            if (s['nct_id'] in p['origin_active_trials'] and category(s.get('overall_status')) in
                    {'RECRUITING','ACTIVENOTRECRUITING','ENROLLINGBYINVITATION'} and category(s.get('start_date_type'))=='ACTUAL'
                    and hi and hi<=policy['origin'] and category(s['phase'])=='PHASE'+str(p['origin_phase'])):candidates.append(s['nct_id'])
        if not candidates:raise ValueError('No source-supported active origin trial')
    annotations=[]
    for a in sample:
        p=a['program'];origin_rows=[]
        for proof in p['source_proofs']:
            if proof['nct'] not in p['origin_active_trials']:continue
            row=original(proof)
            origin_rows.append({'proof':proof,'study':row['study'],'arms':row['design_groups'],
                'interventions':row['interventions'],'links':row['design_group_interventions'],
                'other_names':row['intervention_other_names'],'summary':row['brief_summaries']})
        event_rows=[{'event':e,'original':original(e['source_proof'])} for e in a['candidate_events']]
        text=' '.join(json.dumps(r,ensure_ascii=False) for r in origin_rows+event_rows)
        annotations.append({'audit_id':a['audit_id'],'program_id':p['program_id'],'drug_name':p['drug_name'],
            'condition':p['condition'],'origin_phase':p['origin_phase'],'label_state':p['label_state'],
            'sampling_stratum':a['sampling_stratum'],'inclusion_probability':a['inclusion_probability'],
            'annotation_1':{'type':'deterministic_original_row_audit','byte_and_field_consistency':'passed',
                'regimen_and_population_equivalence':'not_adjudicated','therapeutic_success':None},
            'annotation_2':None,'independent_human_review':False,
            'narrative_flags':{'combination_words':bool(re.search(r'\b(combination|plus|chemotherapy|concomitant)\b',text,re.I)),
                'platform_or_subgroup_words':bool(re.search(r'\b(subprotocol|substudy|subgroup|basket|cohort)\b',text,re.I)),
                'dose_words':bool(re.search(r'\b(dose|dosing|mg|mcg)\b',text,re.I))},
            'relaxed_followup_leads':list(relaxed[p['program_id']].values()),
            'origin_rows':origin_rows,'event_rows':event_rows,'role':'evaluation_only'})
    write(output/'annotations.json',annotations);write(output/'event-checks.json',checked_events)
    positive={e['program_id'] for e in events if e['status']=='recorded_next_phase_start'}
    cluster={}
    for label,values in [('drug',lambda p:[p['drug_id']]),('target',lambda p:p['target_ids']),
                         ('lead_sponsor',lambda p:p['origin_lead_sponsors']),('dependency_component',lambda p:[p['dependency_component_id']])]:
        all_counts=Counter(v for p in programs.values() for v in values(p))
        positive_counts=Counter(v for p in programs.values() if p['program_id'] in positive for v in values(p))
        cluster[label]={'clusters':len(all_counts),'positive_program_clusters':len(positive_counts),
            'largest_cluster_programs':max(all_counts.values(),default=0),
            'memberships':dict(sorted(all_counts.items())),'positive_memberships':dict(sorted(positive_counts.items()))}
    write(output/'dependency-counts.json',{'role':'evaluation_only','clusters':cluster,
        'phase_edges':{str(phase)+'->'+str(phase+1):{'programs':sum(p['origin_phase']==phase for p in programs.values()),
            'programs_with_recorded_event':sum(p['origin_phase']==phase and p['program_id'] in positive for p in programs.values()),
            'unique_recorded_events':len({e['event_id'] for e in events if e['from_phase']==phase and e['status']=='recorded_next_phase_start'})} for phase in [1,2]},
        'warning':'Cluster counts are descriptive; no effective sample size, confidence interval or empirical power claim.'})
    report={'status':'technical_audit_passed_scientific_adjudication_incomplete','role':'evaluation_only',
        'protocol_sha256':sha256_file(policy_path),'cohort_sha256':sha256_file(cohort_path/'cohort.jsonl'),
        'sample_sha256':sha256_file(cohort_path/'audit-sample.json'),'programs_source_checked':len(programs),
        'event_links_source_checked':len(events),'original_rows_rehashed':len(source_rows),'physical_rows_scanned':scanned,
        'sample_annotations':len(annotations),'sample_groups':dict(Counter(a['sampling_stratum']['label_group'] for a in sample)),
        'controls_with_relaxed_followup_leads':sum(bool(v) for v in relaxed.values()),'relaxed_leads':sum(len(v) for v in relaxed.values()),
        'independent_human_annotations':0,'recall':None,'scientifically_validated_precision':None,
        'elapsed_seconds':time.monotonic()-started,'provider_spending_usd':0,
        'limitations':['Original-row checks establish consistency, not correct drug roles or equivalent eligibility.',
            'Relaxed follow-up search is not an independent exhaustive event search; no recall estimate.',
            'No observed transition remains a search result, not negative truth.',
            'Tier B experimental dosing and independent scientific validation remain unestablished.']}
    write(output/'technical-audit.json',report)
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--frames',type=Path,required=True);p.add_argument('--cohort',type=Path,required=True)
    p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();audit(a.frames,a.cohort,a.protocol,a.output)
