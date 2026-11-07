"""Stream frozen registry frames into an evaluator-only program/event register.

The automatic subset is conservative; ambiguity is retained, never a negative label.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import random
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
import calendar
import os
import time

from tether_engine.serde import sha256_file
from tools.feasibility.registry_extract import load,write,validate_row


def norm(text):
    return ' '.join(unicodedata.normalize('NFKC',text or '').casefold().split())


def category(text):
    return re.sub('[^A-Z0-9]','',(text or '').upper())


def stage(text):
    return {'PHASE1':1,'PHASE2':2,'PHASE3':3,'PHASE4':4}.get(category(text))


def start_bounds(value,raw):
    """Use the original precision; AACT can impute a day in start_date."""
    raw=(raw or '').strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',raw):return raw,raw,'day'
    if re.fullmatch(r'\d{4}-\d{2}',raw):
        y,m=map(int,raw.split('-'));return f'{y:04}-{m:02}-01',f'{y:04}-{m:02}-{calendar.monthrange(y,m)[1]}','month'
    if re.fullmatch(r'\d{4}',raw):return raw+'-01-01',raw+'-12-31','year'
    for fmt in ['%B %d, %Y','%b %d, %Y','%B %Y','%b %Y']:
        try:parsed=datetime.strptime(raw,fmt)
        except ValueError:continue
        if '%d' in fmt:return parsed.date().isoformat(),parsed.date().isoformat(),'day'
        return parsed.strftime('%Y-%m-01'),f'{parsed.year:04}-{parsed.month:02}-{calendar.monthrange(parsed.year,parsed.month)[1]}','month'
    return None,None,'unknown'


def program_id(drug,condition):
    return 'program:'+hashlib.sha256(json.dumps([drug,condition],ensure_ascii=False).encode()).hexdigest()[:24]


def stratified_sample(rows,key,limit,rng):
    groups=defaultdict(list)
    for row in rows:groups[key(row)].append(row)
    keys=sorted(groups);budget=min(limit,len(rows))
    if len(keys)>budget:raise ValueError('Audit budget cannot represent every stratum; amend sampling before proceeding')
    allocations={k:1 for k in keys};remaining=budget-len(keys)
    while remaining:
        k=max(keys,key=lambda k:((len(groups[k])-allocations[k])/len(groups[k]),len(groups[k])-allocations[k],k))
        if allocations[k]>=len(groups[k]):raise ValueError('Invalid sampling allocation')
        allocations[k]+=1;remaining-=1
    output=[]
    for k in keys:
        selected=rng.sample(sorted(groups[k],key=lambda x:x['program_id']),allocations[k])
        output.extend((p,k,len(groups[k]),allocations[k]) for p in selected)
    return output


def mapping(policy):
    import pyarrow.parquet as pq
    aliases=defaultdict(set);names={};targets=defaultdict(set)
    for item in policy['mapping_inputs']:
        path=Path(item['path'])
        if sha256_file(path)!=item['sha256']:raise ValueError('Oracle mapping input changed')
        if item['component']=='drug_molecule':
            for row in pq.read_table(path,columns=['id','name','synonyms','tradeNames']).to_pylist():
                names[row['id']]=row['name']
                for term in [row['id'],row['name'],*(row['synonyms'] or []),*(row['tradeNames'] or [])]:
                    if norm(term):aliases[norm(term)].add(row['id'])
        elif item['component']=='drug_mechanism_of_action':
            for row in pq.read_table(path,columns=['chemblIds','targets']).to_pylist():
                for did in row['chemblIds'] or []:targets[did].update(row['targets'] or [])
    return aliases,names,targets


ROLE_CUE=re.compile(r'\b(rescue|premedication|premedicate|background therapy|active comparator|reference treatment)\b',re.I)
COMPOSITION_CUE=re.compile(r'\b(in addition to|in combination(?: with)?|drug cocktail|co[ -]?administer(?:ed|ing|ation)?|concomitant (?:therapy|treatment|medication)|at the (?:same )?insulin injection site|at the same (?:site|time) as insulin)\b',re.I)
CLOSED=re.compile(r'\b(?:enrollment|enrolment|recruitment)\b.{0,45}\b(?:closed|stopped|discontinued)\b',re.I)


def arm_facts(row,aliases,reverse_aliases=None):
    """Return one record per source arm with positive identity evidence and holds."""
    interventions={d['id']:d for d in row['interventions']}
    other=defaultdict(list)
    for a in row['intervention_other_names']:other[a['intervention_id']].append(a['name'])
    links=defaultdict(list)
    for link in row['design_group_interventions']:links[link['design_group_id']].append(link['intervention_id'])
    facts=[]
    for arm in row['design_groups']:
        reasons=[];slots=[];ids=set();matched_terms=[]
        if category(arm['group_type'])!='EXPERIMENTAL':reasons.append('not_experimental_arm')
        for iid in links[arm['id']]:
            d=interventions[iid]
            if category(d['intervention_type']) not in {'DRUG','BIOLOGICAL'}:
                if category(d['intervention_type']) in {'GENETIC','COMBINATIONPRODUCT'}:reasons.append('unsupported_active_product_type')
                continue
            if re.search(r'\b(placebo|sham|vehicle)\b',norm(d['name'])):continue
            terms=[d['name'],*other[iid]];matches=set()
            for term in terms:matches.update(aliases.get(norm(term),set()))
            slots.append({'intervention_id':iid,'names':terms,'candidate_drug_ids':sorted(matches),'description':d.get('description')})
            ids.update(matches)
            if len(matches)==1:
                for term in terms:
                    if norm(term) and aliases.get(norm(term))==matches:
                        matched_terms.append(norm(term))
            if ROLE_CUE.search(d.get('description') or ''):reasons.append('drug_role_cue_requires_review')
            if COMPOSITION_CUE.search(d.get('description') or ''):reasons.append('drug_description_composition_requires_review')
        if not slots:reasons.append('no_active_drug_product')
        if len(slots)>1:reasons.append('multiple_active_products_or_roles_unresolved')
        if len(ids)!=1 or any(len(s['candidate_drug_ids'])!=1 for s in slots):reasons.append('drug_alias_unresolved_or_conflicting')
        if reverse_aliases and len(ids)==1:
            matched_terms.extend(reverse_aliases.get(next(iter(ids)),[]))
        title=norm(arm.get('title'));description=arm.get('description') or ''
        matched_title=any(re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',title) for term in matched_terms)
        if not matched_title:reasons.append('no_explicit_arm_title_alias')
        if ROLE_CUE.search(description):reasons.append('arm_role_cue_requires_review')
        if COMPOSITION_CUE.search(description):reasons.append('arm_description_composition_requires_review')
        if CLOSED.search(description):reasons.append('arm_explicitly_closed')
        if re.search(r'\b(plus|with|and)\b|\s\+\s',title):reasons.append('arm_composition_or_scope_text_requires_review')
        facts.append({'arm_id':arm['id'],'title':arm.get('title'),'description':description,
            'product_slots':slots,'candidate_drug_ids':sorted(ids),'resolved_drug_id':next(iter(ids)) if not reasons else None,
            'reasons':sorted(set(reasons)),'drug_role':'source_supported_experimental_product' if not reasons else 'unresolved_or_inapplicable',
            'source_link_ids':sorted(links[arm['id']])})
    experimental=[f for f in facts if 'not_experimental_arm' not in f['reasons'] and f['candidate_drug_ids']]
    product_scopes={tuple(f['candidate_drug_ids']) for f in experimental}
    if len({norm(c['name']) for c in row['conditions'] if norm(c['name'])})>1 and len(product_scopes)>1:
        for fact in experimental:
            fact['reasons']=sorted(set(fact['reasons']+['multi_program_study_condition_scope_unqualified']))
            fact['resolved_drug_id']=None;fact['drug_role']='unresolved_or_inapplicable'
    return facts


def ingest_frames(frames,db,policy,aliases):
    reverse_aliases=defaultdict(list)
    for term,ids in aliases.items():
        if len(ids)==1:reverse_aliases[next(iter(ids))].append(term)
    db.executescript('''CREATE TABLE observations(snapshot TEXT,nct TEXT,phase INTEGER,phase_raw TEXT,status TEXT,start TEXT,start_raw TEXT,start_kind TEXT,first_post TEXT,last_post TEXT,row_json TEXT,row_sha TEXT,line INTEGER,source TEXT,PRIMARY KEY(snapshot,nct));
        CREATE TABLE arms(snapshot TEXT,nct TEXT,arm_id INTEGER,drug TEXT,condition TEXT,phase INTEGER,active INTEGER,resolved INTEGER,fact TEXT,PRIMARY KEY(snapshot,nct,arm_id,condition));
        CREATE TABLE possible(snapshot TEXT,nct TEXT,arm_id INTEGER,drug TEXT,condition TEXT,resolved INTEGER,reason TEXT);
        CREATE INDEX possible_program ON possible(snapshot,drug,condition);
        CREATE INDEX arm_program ON arms(drug,condition,snapshot);CREATE INDEX observed_nct ON observations(nct,snapshot);''')
    counts={};reason_counts=Counter()
    for item in frames['snapshots']:
        path=Path(item['path']);snap=item['snapshot_date']
        if sha256_file(path)!=item['sha256']:raise ValueError('Frame bytes changed')
        count=0;arms_count=0
        with path.open('rb') as source:
            for line,raw in enumerate(source,1):
                row=json.loads(raw);nct=validate_row(row,snap);s=row['study'];count+=1
                db.execute('INSERT INTO observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (snap,nct,stage(s['phase']),s['phase'],category(s['overall_status']),s.get('start_date'),s.get('start_month_year'),category(s.get('start_date_type')),s.get('study_first_posted_date'),s.get('last_update_posted_date'),raw.decode().strip(),hashlib.sha256(raw).hexdigest(),line,str(path)))
                conditions=sorted({norm(c['name']) for c in row['conditions'] if norm(c['name'])}) or ['']
                for fact in arm_facts(row,aliases,reverse_aliases):
                    arms_count+=1;reason_counts.update(fact['reasons'])
                    for condition in conditions:
                        db.execute('INSERT INTO arms VALUES(?,?,?,?,?,?,?,?,?)',(snap,nct,fact['arm_id'],fact['resolved_drug_id'],condition,stage(s['phase']),int(category(s['overall_status']) in {'RECRUITING','ACTIVENOTRECRUITING','ENROLLINGBYINVITATION'}),int(fact['resolved_drug_id'] is not None),json.dumps(fact,ensure_ascii=False)))
                        if 'not_experimental_arm' not in fact['reasons']:
                            for did in fact['candidate_drug_ids']:
                                db.execute('INSERT INTO possible VALUES(?,?,?,?,?,?,?)',(snap,nct,fact['arm_id'],did,condition,int(fact['resolved_drug_id'] is not None),json.dumps(fact['reasons'])))
                if count%2000==0:db.commit()
        if count!=item['records']:raise ValueError('Frame count differs')
        db.commit();counts[snap]={'studies':count,'arms':arms_count}
        print(json.dumps({'stage':'frame_indexed','date':snap,**counts[snap]}),flush=True)
    return counts,dict(reason_counts)


def _build(frames_path,policy_path,output):
    policy=load(policy_path);frames=load(frames_path)
    if policy.get('protocol_id')!='registry-sizing-development-v0.4' or policy.get('role')!='evaluation_only':raise ValueError('Wrong evaluator protocol')
    if sha256_file(policy_path)!=frames['protocol_sha256']:raise ValueError('Different frozen protocol')
    if policy.get('snapshots') and [s['date'] for s in policy['snapshots']] != [s['snapshot_date'] for s in frames['snapshots']]:
        raise ValueError('Missing, duplicate or out-of-order snapshot frame')
    aliases,names,targets=mapping(policy)
    db=sqlite3.connect(output/'cohort.sqlite');db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=NORMAL')
    counts,reasons=ingest_frames(frames,db,policy,aliases)
    origin=policy['origin'];end=policy['occurrence_endpoint']
    # Aggregate origin candidates before seeing/joining any follow-up outcome.
    origin_keys=db.execute('SELECT DISTINCT drug,condition FROM arms WHERE snapshot=? AND resolved=1 ORDER BY drug,condition',(origin,)).fetchall()
    programs=[];lookup={};origin_routing=Counter()
    with (output/'origin-programs.jsonl').open('x',encoding='utf-8',newline='\n') as out:
        for key in origin_keys:
            did,condition=key
            observations=db.execute('SELECT a.nct,a.arm_id,a.phase,a.active,o.start,o.start_raw,o.start_kind,o.first_post,o.last_post,o.phase_raw,o.row_sha,o.line,o.source FROM arms a JOIN observations o USING(snapshot,nct) WHERE a.snapshot=? AND a.drug=? AND a.condition=? ORDER BY o.first_post,a.nct,a.arm_id',(origin,did,condition)).fetchall()
            known=[r for r in observations if r['start_kind']=='ACTUAL' and start_bounds(r['start'],r['start_raw'])[1] and start_bounds(r['start'],r['start_raw'])[1]<=origin and r['first_post'] and r['first_post']<=origin and r['last_post'] and r['last_post']<=origin]
            phases=[r['phase'] for r in known if r['phase']];highest=max(phases,default=None)
            mixed=[category(r['phase_raw']) for r in known if r['phase'] is None]
            active=[r for r in known if r['active'] and r['phase']==highest]
            holds=[];ambiguous_prior=[]
            if not condition:holds.append('missing_indication')
            if highest is None:holds.append('origin_stage_or_actual_start_unresolved')
            if highest and highest>=3:status='excluded_prior_higher_phase'
            elif highest and not any(r['active'] for r in observations):status='excluded_not_active_in_origin_snapshot'
            else:
                if not active:holds.append('highest_known_phase_not_active_at_origin')
                if ('PHASE2PHASE3' in mixed or highest==1 and 'PHASE1PHASE2' in mixed):holds.append('possible_higher_origin_stage_unresolved')
                prior=db.execute('SELECT p.nct,p.arm_id,p.reason,o.phase,o.phase_raw,o.status,o.start,o.start_raw,o.start_kind FROM possible p JOIN observations o USING(snapshot,nct) WHERE p.snapshot=? AND p.drug=? AND p.condition=? AND p.resolved=0',(origin,did,condition)).fetchall()
                ambiguous_prior=[dict(r) for r in prior if (r['phase'] and highest and r['phase']>highest or category(r['phase_raw'])=='PHASE2PHASE3') and (r['status'] in {'RECRUITING','ACTIVENOTRECRUITING','ENROLLINGBYINVITATION'} or r['start_kind']=='ACTUAL' and start_bounds(r['start'],r['start_raw'])[1] and start_bounds(r['start'],r['start_raw'])[1]<=origin)]
                if ambiguous_prior:holds.append('possible_higher_phase_with_unresolved_origin_role')
                status='unresolved_origin' if holds else 'resolved_origin_program'
            pid=program_id(did,condition)
            sponsor_names=set()
            for nct in {r['nct'] for r in active}:
                source_row=json.loads(db.execute('SELECT row_json FROM observations WHERE snapshot=? AND nct=?',(origin,nct)).fetchone()[0])
                sponsor_names.update(s['name'] for s in source_row['sponsors'] if s.get('name') and (s.get('lead_or_collaborator') or '').lower()=='lead')
            p={'program_id':pid,'drug_id':did,'drug_name':names.get(did),'condition':condition,'origin_phase':highest,
                'origin_status':status,'holds':holds,'target_ids':sorted(targets[did]),'target_mapping':'contemporary_oracle_evaluator_only',
                'ambiguous_prior_observations':ambiguous_prior,
                'origin_trials':sorted({r['nct'] for r in observations}),'origin_active_trials':sorted({r['nct'] for r in active}),
                'representative_origin_trial':active[0]['nct'] if active else None,
                'origin_lead_sponsors':sorted(sponsor_names),
                'source_proofs':[dict(r) for r in observations],'role':'evaluation_only'}
            programs.append(p);lookup[(did,condition)]=p;origin_routing[status]+=1
            out.write(json.dumps(p,ensure_ascii=False)+'\n')
    write(output/'origin-freeze.json',{'protocol_sha256':sha256_file(policy_path),'origin_programs_sha256':sha256_file(output/'origin-programs.jsonl'),
        'programs':len(programs),'selection':'origin fields only; follow-up not joined until this file was written','role':'evaluation_only'})
    # Actual start/phase changes across snapshots are unresolved, not silently merged.
    conflicts=set();db.create_function('phasekey',1,category)
    for r in db.execute('SELECT nct,COUNT(DISTINCT CASE WHEN start_kind="ACTUAL" THEN start END) dates,COUNT(DISTINCT phasekey(phase_raw)) phases,MAX(CASE WHEN status="WITHDRAWN" AND start_kind="ACTUAL" THEN 1 ELSE 0 END) contradiction FROM observations GROUP BY nct'):
        if r['dates']>1 or r['phases']>1 or r['contradiction']:conflicts.add(r['nct'])
    events={};candidate_events=[];late_preorigin=set()
    cursor=db.execute('SELECT a.drug,a.condition,a.arm_id,o.* FROM arms a JOIN observations o USING(snapshot,nct) WHERE a.snapshot>? AND a.resolved=1 ORDER BY a.snapshot,a.nct,a.arm_id,a.condition',(origin,))
    for row in cursor:
        p=lookup.get((row['drug'],row['condition']))
        if not p or p['origin_status']!='resolved_origin_program':continue
        if row['phase']!=p['origin_phase']+1:continue
        if row['nct'] in p['origin_trials']:continue
        lower,upper,precision=start_bounds(row['start'],row['start_raw'])
        if row['start_kind']=='ACTUAL' and upper and upper<=origin:
            late_preorigin.add(p['program_id']);continue
        holds=[]
        if row['start_kind']!='ACTUAL' or not row['start']:holds.append('start_not_actual_or_missing')
        if not lower or not upper or not origin<lower<=upper<=end:holds.append('start_precision_or_window_unresolved')
        if row['nct'] in conflicts:holds.append('study_phase_or_actual_date_changed')
        if row['status']=='WITHDRAWN':holds.append('withdrawn_study_actual_start_contradiction')
        if row['start_kind']=='ACTUAL' and lower and row['last_post'] and lower>row['last_post']:
            holds.append('actual_start_after_source_update')
        if not row['first_post'] or not row['last_post'] or row['last_post']>row['snapshot']:holds.append('posting_bounds_unresolved')
        event_id='event:'+row['nct']+':'+row['drug']+':registry-start'
        record={'event_id':event_id,'program_id':p['program_id'],'nct_id':row['nct'],'drug_id':row['drug'],'condition':row['condition'],
            'from_phase':p['origin_phase'],'to_phase':row['phase'],'registry_start_date':row['start'],'date_type':row['start_kind'],
            'registry_start_interval':{'lower':lower,'upper':upper,'precision':precision},
            'first_observed_snapshot':row['snapshot'],'source_arm_id':row['arm_id'],'holds':holds,
            'tier':'A_registry_enrollment_surrogate','clinical_success':None,'role':'evaluation_only',
            'scope_qualification':{'product_composition':'single_source_supported_active_product',
                'indication':'exact_normalized_registry_condition','dose_route_line_genotype_equivalence':'not_adjudicated',
                'experimental_dosing':'not_established_by_registry_start'},
            'source_proof':{k:row[k] for k in ['snapshot','nct','row_sha','line','source']}}
        edge=(p['program_id'],event_id)
        version={'snapshot':row['snapshot'],'date':row['start'],'date_type':row['start_kind'],'holds':list(holds),'source_proof':record['source_proof']}
        if edge not in events:
            events[edge]={**record,'source_versions':[version],'candidate_first_seen_snapshot':row['snapshot']}
        else:
            existing=events[edge];versions=existing['source_versions']+[version]
            if existing['holds'] and not holds:
                events[edge]={**record,'source_versions':versions,'candidate_first_seen_snapshot':existing['candidate_first_seen_snapshot']}
            else:
                existing['source_versions']=versions
                if existing['holds']:existing['holds']=sorted(set(existing['holds']+holds))
    # Unresolved source roles/aliases in a plausible next-phase record are not
    # silently treated as a program with no transition.
    cursor=db.execute('SELECT p.drug,p.condition,p.arm_id,p.reason,o.* FROM possible p JOIN observations o USING(snapshot,nct) WHERE p.snapshot>? AND p.resolved=0 ORDER BY p.snapshot,p.nct,p.arm_id,p.condition',(origin,))
    for row in cursor:
        p=lookup.get((row['drug'],row['condition']))
        if not p or p['origin_status']!='resolved_origin_program' or row['phase']!=p['origin_phase']+1 or row['nct'] in p['origin_trials']:continue
        lower,upper,precision=start_bounds(row['start'],row['start_raw'])
        if row['start_kind']=='ACTUAL' and upper and upper<=origin:
            late_preorigin.add(p['program_id']);continue
        event_id='event:'+row['nct']+':'+row['drug']+':registry-start';edge=(p['program_id'],event_id)
        if edge in events:
            events[edge]['holds']=sorted(set(events[edge]['holds']+['next_phase_role_or_alias_unresolved',*json.loads(row['reason'])]))
            events[edge]['source_versions'].append({'snapshot':row['snapshot'],'date':row['start'],'date_type':row['start_kind'],
                'holds':['next_phase_role_or_alias_unresolved',*json.loads(row['reason'])],
                'source_proof':{k:row[k] for k in ['snapshot','nct','row_sha','line','source']}})
            continue
        events[edge]={'event_id':event_id,'program_id':p['program_id'],'nct_id':row['nct'],'drug_id':row['drug'],
            'condition':row['condition'],'from_phase':p['origin_phase'],'to_phase':row['phase'],
            'registry_start_date':row['start'],'date_type':row['start_kind'],
            'registry_start_interval':{'lower':lower,'upper':upper,'precision':precision},
            'first_observed_snapshot':row['snapshot'],'candidate_first_seen_snapshot':row['snapshot'],'source_arm_id':row['arm_id'],
            'holds':['next_phase_role_or_alias_unresolved',*json.loads(row['reason'])],
            'tier':'A_registry_enrollment_surrogate','clinical_success':None,'role':'evaluation_only',
            'source_proof':{k:row[k] for k in ['snapshot','nct','row_sha','line','source']},'source_versions':[]}
    # A late-disclosed pre-origin transition leaves the origin risk assessment unresolved.
    for event in events.values():
        if event['program_id'] in late_preorigin:event['holds'].append('late_disclosed_preorigin_advancement')
        event['status']='candidate_unresolved' if event['holds'] else 'recorded_next_phase_start'
        candidate_events.append(event)
    write(output/'candidate-events.json',candidate_events)
    event_by_program=defaultdict(list)
    for e in candidate_events:event_by_program[e['program_id']].append(e)
    cohort=[]
    for p in programs:
        if p['origin_status']!='resolved_origin_program':continue
        es=event_by_program[p['program_id']];positive=any(e['status']=='recorded_next_phase_start' for e in es)
        state='recorded_next_phase_start' if positive else 'unresolved_transition' if es or p['program_id'] in late_preorigin else 'no_recorded_transition_by_cutoff'
        cohort.append({**p,'label_state':state,'event_ids':sorted({e['event_id'] for e in es}),
            'individual_censoring_date':None,'training_label':None,'label_use':'development_sizing_only_not_adjudicated_gold'})
    # Conservative split components preserve shared product, source trial and event.
    parent={p['program_id']:p['program_id'] for p in cohort};owners={}
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    for p in cohort:
        keys=['drug:'+p['drug_id']]+['origin-trial:'+n for n in p['origin_trials']]+p['event_ids']
        for key in keys:
            if key in owners:
                a,b=find(p['program_id']),find(owners[key]);parent[max(a,b)]=min(a,b)
            else:owners[key]=p['program_id']
    for p in cohort:p['dependency_component_id']='component:'+find(p['program_id']).split(':',1)[1]
    with (output/'cohort.jsonl').open('x',encoding='utf-8',newline='\n') as out:
        for row in cohort:out.write(json.dumps(row,ensure_ascii=False)+'\n')
    # Pair rollups and representative programs are selected from origin ordering.
    pair_programs=defaultdict(list)
    for p in cohort:
        for target in p['target_ids']:pair_programs[(target,p['condition'])].append(p)
    pairs=[]
    for (target,condition),ps in sorted(pair_programs.items()):
        ps=sorted(ps,key=lambda p:(next((s['first_post'] or '9999' for s in p['source_proofs'] if s['nct']==p['representative_origin_trial']),'9999'),p['representative_origin_trial'] or '',p['program_id']))
        pairs.append({'target_id':target,'condition':condition,'program_ids':[p['program_id'] for p in ps],
            'any_program_recorded_transition':any(p['label_state']=='recorded_next_phase_start' for p in ps),
            'origin_representative_program':ps[0]['program_id'],'representative_label_state':ps[0]['label_state'],
            'mapping':'contemporary_oracle_sizing_only','role':'evaluation_only'})
    write(output/'target-indication-rollups.json',pairs)
    # Fixed seed; phase-stratified sample with explicit stratum inclusion probabilities.
    rng=random.Random(20261017);audit=[]
    for label,n in [('candidate_transitions',120),('no_recorded_transition_by_cutoff',120)]:
        pool=[p for p in cohort if (bool(event_by_program[p['program_id']]) if label=='candidate_transitions' else p['label_state']==label)]
        def stratum(p):
            es=event_by_program[p['program_id']]
            ambiguity='candidate_has_holds' if any(e['holds'] for e in es) else 'resolved_alias_and_role_subset'
            interval=min((e['first_observed_snapshot'] for e in es),default='no_recorded_event')
            return (p['origin_phase'],ambiguity,'single_resolved_active_product',interval)
        selected=stratified_sample(pool,stratum,n,rng)
        for p,k,population,take in selected:
            audit.append({'audit_id':f'A{len(audit)+1:03d}','program':p,'candidate_events':event_by_program[p['program_id']],
                'sampling_stratum':{'phase':k[0],'ambiguity':k[1],'regimen_complexity':k[2],'first_observed_snapshot':k[3],
                    'label_group':label,'population':population,'sample':take},
                'inclusion_probability':take/population,'review_status':'awaiting_source_and_semantic_audit',
                'independent_human_review':False,'scientific_validation':'not_established','role':'evaluation_only'})
    write(output/'audit-sample.json',audit)
    resolved_events={e['event_id'] for e in candidate_events if e['status']=='recorded_next_phase_start'}
    summary={'protocol_sha256':sha256_file(policy_path),'frames':counts,'arm_resolution_reasons':reasons,
        'origin_program_status':dict(origin_routing),'cohort_programs':len(cohort),'label_states':dict(Counter(p['label_state'] for p in cohort)),
        'candidate_event_links':len(candidate_events),'resolved_unique_development_events':len(resolved_events),
        'resolved_event_ncts':len({e['nct_id'] for e in candidate_events if e['status']=='recorded_next_phase_start'}),
        'unique_drugs':len({p['drug_id'] for p in cohort}),'mapped_targets':len({t for p in cohort for t in p['target_ids']}),
        'programs_with_target_mapping':sum(bool(p['target_ids']) for p in cohort),
        'programs_without_target_mapping':sum(not p['target_ids'] for p in cohort),
        'target_indication_pairs':len(pairs),'audit_sample':len(audit),'training_labels':0,'scientific_validation':'not_established',
        'dependency_components':len({p['dependency_component_id'] for p in cohort}),
        'origin_lead_sponsors':len({s for p in cohort for s in p['origin_lead_sponsors']}),
        'limitations':['Conservative automatically resolved subset; unresolved arm roles/combinations/aliases are retained separately',
            'Exact normalized condition baseline can miss synonyms/subtypes; no unsupported family merge',
            'Registry enrollment at observed phase is a surrogate, not experimental dosing or therapeutic success',
            'Contemporary target mapping is oracle information for sizing; no predictor admission',
            'No recorded transition is not a verified negative or censoring assignment']}
    write(output/'summary.json',summary)
    db.execute('PRAGMA wal_checkpoint(TRUNCATE)');db.close()
    print(json.dumps({'stage':'cohort_built',**{k:v for k,v in summary.items() if k not in ['arm_resolution_reasons','limitations','frames']}}),flush=True)


def peak_memory_bytes():
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(key,ctypes.c_size_t) for key in
                ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
                 'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
        counters=Counters();counters.cb=ctypes.sizeof(counters)
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.GetCurrentProcess.restype=wintypes.HANDLE
        info=ctypes.WinDLL('psapi',use_last_error=True).GetProcessMemoryInfo
        info.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD];info.restype=wintypes.BOOL
        if not info(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return counters.PeakWorkingSetSize
    import resource
    import sys
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024)


def build(frames_path,policy_path,output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    write(output/'execution.json',{'started_at_utc':datetime.now(timezone.utc).isoformat(),
        'frames_sha256':sha256_file(frames_path),'protocol_sha256':sha256_file(policy_path),'role':'evaluation_only',
        'code_sha256':{name:sha256_file(Path(__file__).with_name(name)) for name in ['registry_cohort.py','registry_extract.py']}})
    try:
        _build(frames_path,policy_path,output)
    except BaseException as exc:
        write(output/'failure.json',{'error_type':type(exc).__name__,'error':str(exc),'automatic_retry':False})
        raise
    finally:
        write(output/'resources.json',{'elapsed_seconds':time.monotonic()-started,'peak_process_memory_bytes':peak_memory_bytes(),
            'finished_at_utc':datetime.now(timezone.utc).isoformat(),'provider_spending_usd':0})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--frames',type=Path,required=True);p.add_argument('--protocol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.frames,a.protocol,a.output)
