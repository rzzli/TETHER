"""Deterministic origin-only maturity screening, with no outcome inference."""
from __future__ import annotations

from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path

from tether_engine.serde import ContractError,read_json,sha256_file
from tools.science.origin_review import eligibility
from tools.science.origin_programs import start_bounds
from tools.science.outcome_inputs import study_query,regenerate_request,schema_from_audit,ORIGIN_COLUMNS,CHILD_COLUMNS
from tools.science.ascertainment_policy import version_eligibility

ROOT=Path(__file__).resolve().parents[2]
PARENT_SHA='8622c4896796489e0d34c9359ccdbc3a1ad0eb1778541e173e0ab34ff7cd26e8'
OLD_PACK_SHA='5a4842f9b1751d3e0b2e50c166c5bf1786e3639741072b38b8ad264b4b8da56d'
POLICY=ROOT/'planning/protocols/endpoint-origin-feasibility-v0.1.json'


def require(condition,message):
    if not condition:raise ContractError(message)


def rank(salt,kind,value):
    return hashlib.sha256((salt+'\0'+kind+'\0'+value).encode()).hexdigest()


def select_candidates(path,excluded,*,salt,maximum=128):
    require(type(maximum) is int and 1<=maximum<=128,'Invalid origin screening bound')
    require(isinstance(excluded,(list,tuple)) and len(excluded)==len(set(excluded)),'Duplicate old member exclusion')
    best={};seen=set();reasons=Counter();digest=hashlib.sha256();offset=0;scopes=0
    with Path(path).open('rb') as stream:
        for line,raw in enumerate(stream,1):
            digest.update(raw);record=json.loads(raw);pid=record['program_id']
            require(pid not in seen,'Duplicate source origin program');seen.add(pid)
            rejected=eligibility(record)
            if record['nct_id'] in excluded:rejected.append('original_twelve_excluded')
            if rejected:reasons.update(rejected)
            else:
                scopes+=1;nct=record['nct_id'];key=(rank(salt,'program',pid),pid)
                proof={'path':str(Path(path).resolve()),'line':line,'byte_offset':offset,'bytes':len(raw),
                    'sha256':hashlib.sha256(raw).hexdigest()}
                candidate={'nct_id':nct,'program_id':pid,'program':record,'program_row':proof,
                    'trial_rank':rank(salt,'trial',nct),'program_rank':key[0]}
                if nct not in best or key<best[nct][0]:best[nct]=(key,candidate)
            offset+=len(raw)
    ordered=sorted(best,key=lambda n:(rank(salt,'trial',n),n))
    require(len(ordered)>=maximum,'Insufficient origin screening pool; no relaxation')
    return [best[n][1] for n in ordered[:maximum]],{
        'parent_scopes_scanned':len(seen),'eligible_scopes_after_exclusion':scopes,
        'eligible_trials_after_exclusion':len(ordered),'candidate_trials':maximum,
        'parent_program_sha256':digest.hexdigest(),'rejection_counts_overlapping':dict(reasons),
        'followup_used_for_selection':False,'clinical_labels_assigned':0}


def maturity_reasons(record):
    require('study' in record,'Origin study envelope required')
    study=record['study']
    require(set(study)<=set(ORIGIN_COLUMNS) and set(record)<=({'study'}|set(CHILD_COLUMNS)),
        'Unapproved or follow-up field in origin metadata')
    for table,children in record.items():
        if table=='study':continue
        require(isinstance(children,list) and all(isinstance(c,dict) and set(c)<=set(CHILD_COLUMNS[table]) for c in children),
            'Unapproved or follow-up child field in origin metadata')
    require(not any(key.startswith('results_') or key in ('why_stopped','clinical_outcome') for key in study),
        'Follow-up fields cannot affect origin maturity')
    require(not ({'outcomes','outcome_measurements','outcome_analyses'}&set(record)),
        'Reported results cannot affect origin maturity')
    reasons=[]
    kind=str(study.get('primary_completion_date_type','')).strip().upper()
    if kind not in ('ESTIMATED','ANTICIPATED'):reasons.append('primary_completion_not_planned_at_origin')
    low,high,precision=start_bounds(study.get('primary_completion_month_year'))
    if low is None or high is None or not '2025-01-01'<=low<=high<='2025-12-31':
        reasons.append('planned_primary_completion_not_wholly_calendar2025')
    outcomes=record.get('design_outcomes',[])
    if not any(str(x.get('outcome_type','')).upper()=='PRIMARY' and isinstance(x.get('measure'),str) and x['measure'].strip() for x in outcomes):
        reasons.append('no_recorded_planned_primary_outcome')
    return reasons,{'lower_date':low,'upper_date':high,'precision':precision,'source_type':study.get('primary_completion_date_type'),
        'event_inferred':False}


def select_mature(candidates,validation,*,requested=12):
    require(type(requested) is int and 1<=requested<=128,'Invalid final sample bound')
    require(validation.get('status')=='study_rows_validated','Validated origin-only source rows required')
    by_id={c['nct_id']:c for c in candidates}
    require(len(by_id)==len(candidates),'Duplicate screening members')
    dispositions={x['nct_id']:x for x in validation['version_dispositions']}
    require(len(dispositions)==len(validation['version_dispositions']) and set(dispositions)<=set(by_id),'Origin version membership differs')
    eligible={r['study']['nct_id']:r for r in validation['eligible_reconstructed_rows']}
    require(len(eligible)==len(validation['eligible_reconstructed_rows']) and set(eligible)<=set(by_id),'Eligible origin membership differs')
    expected={nct for nct,d in dispositions.items() if d['version_eligibility']['status']=='eligible_reconstructed_date_bound'}
    require(set(eligible)==expected,'Eligible origin payload/disposition membership differs')
    for record in eligible.values():
        study=record['study']
        actual=version_eligibility(last_update_posted_date=study.get('last_update_posted_date'),
            first_posted_date=study.get('study_first_posted_date'),cutoff_at='2025-01-01T00:00:00Z')
        require(actual['status']=='eligible_reconstructed_date_bound' and
            str(study.get('last_update_posted_date_type','')).strip().upper()=='ACTUAL',
            'Origin eligible declaration contradicts source posting fields')
    selected=[];screen=[]
    for candidate in candidates:
        nct=candidate['nct_id'];reasons=[];interval=None
        if nct not in dispositions:reasons=['origin_trial_missing']
        elif dispositions[nct]['version_eligibility']['status']!='eligible_reconstructed_date_bound':reasons=['origin_version_held']
        elif nct not in eligible:raise ContractError('Eligible source disposition and payload differ')
        else:reasons,interval=maturity_reasons(eligible[nct])
        screen.append({'nct_id':nct,'program_id':candidate['program_id'],'reasons':reasons,'planned_primary_completion':interval,
            'selection_eligible':not reasons,'clinical_eligibility':'unreviewed','clinical_label':None})
        if not reasons and len(selected)<requested:
            selected.append({'candidate':candidate,'origin_design':eligible[nct],
                'planned_primary_completion':interval,'clinical_label':None,'scientific_qualification':False})
    require(len(selected)==requested,'Insufficient maturity-qualified pool; no relaxation or replacement')
    return selected,screen


def validate_origin_binding(plan):
    """Exact source/policy/membership binding for the new origin-only runner phase."""
    from tools.science.reference_panel import read_bound_json
    from tools.science.outcome_extract import APPROVED_BASE,APPROVED_RESTORES,check_pins
    policy_pin=plan['origin_policy']
    require(Path(policy_pin['path']).resolve()==POLICY.resolve(),'Wrong origin-maturity policy path')
    policy,_=read_bound_json(POLICY,policy_pin['sha256'])
    require(policy['protocol_id']=='endpoint-origin-feasibility-v0.1' and policy['role']=='evaluation_only' and
        policy['clinical_activation'] is False and policy['automatic_labels'] is False and policy['max_output_bytes']==128*1024*1024,
        'Unapproved origin-maturity policy')
    require(policy['selection']['candidate_trials']==128 and policy['selection']['final_trials']==12 and
        policy['selection']['salt']=='endpoint-origin-feasibility-v0.1:20261021' and
        policy['selection']['exclude_original_twelve'] is True,'Origin selection policy differs')
    require(all(plan[k]==policy[k] for k in ('origin_at','horizon_at','ascertainment_at')),'Origin chronology differs')
    parent_pin=plan['origin_parent'];old_pin=plan['excluded_old_pack'];selection_pin=plan['selection']
    require(parent_pin['sha256']==PARENT_SHA==policy['parent_origin_sha256'],'Wrong origin parent')
    require(old_pin['sha256']==OLD_PACK_SHA==policy['excluded_old_pack_sha256'],'Wrong old-member pack')
    parent,_=read_bound_json(Path(parent_pin['path']),PARENT_SHA)
    old,_=read_bound_json(Path(old_pin['path']),OLD_PACK_SHA)
    check_pins(old['files'])
    excluded=[]
    for p in old['files']:
        if Path(p['path']).parent.name=='packets':
            packet,_=read_bound_json(Path(p['path']),p['sha256']);excluded.append(packet['origin_scope']['nct_id'])
    require(len(excluded)==len(set(excluded))==12,'Old member exclusion differs')
    for pin in (policy_pin,parent_pin,old_pin,selection_pin):
        require(any(Path(p['path']).resolve()==Path(pin['path']).resolve() and p['sha256']==pin['sha256'] for p in plan['parents']),
            'Missing complete origin-selection parent proof')
    programs=next(p for p in parent['files'] if Path(p['path']).name=='origin-programs.jsonl')
    require(any(Path(p['path']).resolve()==Path(programs['path']).resolve() and p['sha256']==programs['sha256'] for p in plan['parents']),
        'Missing full origin program commitment')
    candidates,pool=select_candidates(programs['path'],sorted(excluded),salt=policy['selection']['salt'])
    require(pool['parent_program_sha256']==programs['sha256'],'Origin program bytes differ')
    selection,_=read_bound_json(Path(selection_pin['path']),selection_pin['sha256'])
    require(selection['role']=='evaluation_only' and selection['candidates']==candidates and selection['pool']==pool and
        selection['clinical_labels_assigned']==0 and selection['followup_used_for_selection'] is False,
        'Candidate selection differs from origin-only regeneration')
    members=sorted(c['nct_id'] for c in candidates)
    require(plan['nct_ids']==members,'Request differs from exact frozen screening membership')
    require(len(plan['jobs'])==1,'Origin-only phase cannot open a follow-up source')
    job=plan['jobs'][0];root=Path(job['restore_root']).resolve()
    require(job['snapshot_date']=='2025-01-01' and root==(APPROVED_BASE/APPROVED_RESTORES['2025-01-01']).resolve(),
        'Wrong origin source identity')
    check_pins(job['pins']);pins={Path(p['path']).resolve():p for p in job['pins']}
    for name in ('extracted/postgres.dmp','archive-inspection.json','dump-toc-pg17.txt','technical-audit.json','setup.py','schema-pg17.sql'):
        require(root/name in pins,'Missing original restored-source commitment')
    inspection,_=read_bound_json(root/'archive-inspection.json',pins[root/'archive-inspection.json']['sha256'])
    require(next(m for m in inspection['members'] if m['name']=='postgres.dmp')['sha256']==pins[root/'extracted/postgres.dmp']['sha256'],
        'Origin dump contradicts archive inspection')
    audit,_=read_bound_json(root/'technical-audit.json',pins[root/'technical-audit.json']['sha256'])
    require(audit['status']=='completed' and audit['study_id_check']['rows']==520688,'Wrong origin inventory')
    require(len(job['queries'])==1 and job['queries'][0]['name']=='studies','Origin screening accepts metadata only')
    query=job['queries'][0];request=query['request']
    regenerate_request(request)
    require(request==study_query(members,'2025-01-01',schema_from_audit(audit),max_ids=128) and
        Path(query['path']).read_text(encoding='utf-8')==request['sql'],'Origin projection/membership differs')
    return policy
