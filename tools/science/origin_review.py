"""Freeze a bounded, deterministic origin-only scope-review pack before follow-up.

This creates review inputs, never clinical labels or an outcome-selected cohort.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from tools.science.origin_programs import cat, norm, read_bound_json, sha, start_bounds, validate, verify_pins, write

ORIGIN_SEAL_SHA256='8622c4896796489e0d34c9359ccdbc3a1ad0eb1778541e173e0ab34ff7cd26e8'
SALT='science3-origin-only-pilot-20250101-v1:20261018'
FIELDS=set(('active_product_names arm_id clinical_outcome clinical_ready condition_candidate_ids '
    'condition_mapping_status condition_verbatim_normalized dependence_keys design_source drug_ids exclusions '
    'historical_mapping_proofs historical_mapping_slots lead_sponsors mapping_inputs_qualified mapping_status '
    'nct_id origin_phase phase_raw population_source prior_higher_phase_verbatim_alerts program_id '
    'qualification_holds reconstructed_origin_information_eligible regimen_source_intervention_ids role '
    'scope_status source_arm source_products source_proof start_interval status_raw target_ids '
    'target_mapping_status unrecognized_historical_target_ids').split())


def rank(kind,value):
    return hashlib.sha256((SALT+'\0'+kind+'\0'+value).encode()).hexdigest()


def criteria(count):
    if type(count) is not int or count<=0:raise ValueError('Positive integer pilot size required')
    return {'schema_version':1,'protocol_id':'science3-origin-only-review-pilot-v1',
        'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'review_phase':'origin_only_before_followup',
        'sample_size_distinct_trials':count,'salt':SALT,
        'order':'SHA256(salt NUL trial NUL NCT), then SHA256(salt NUL program NUL program_id); one minimum-ranked eligible scope per trial',
        'criteria':{'origin_phase':2,'phase_raw_category':'PHASE2','exact_historical_drug_slots':1,
            'drug_ids':1,'nonempty_historical_target_annotation':True,'experimental_linked_products':1,
            'single_study_condition':True,'original_start_interval_lower_min':'2022-01-01',
            'original_start_interval_upper_max':'2024-12-31','start_type':'ACTUAL',
            'source_role':'evaluation_only','clinical_outcome_must_be_null':True},
        'no_relaxation_if_insufficient':True,'qualification_holds_preserved':True,
        'parent_membership_changed':False,'followup_sources_allowed':False,
        'max_prior_source_rows':2048,'max_total_packet_bytes':256*1024*1024,
        'interpretation':'Purposive source-eligibility subset with deterministic hash ordering; no representation, power, clinical equivalence or outcome claim'}


def eligibility(rec):
    """Only the explicit pre-origin fields below may affect selection."""
    if set(rec)-FIELDS:raise ValueError('Unapproved or future/label selection field')
    if rec.get('clinical_outcome') is not None or rec.get('clinical_ready') is not False:
        raise ValueError('Follow-up label or clinical activation present in origin source')
    reasons=[]
    if rec.get('role')!='evaluation_only' or rec.get('scope_status')!='conditional_origin_candidate' or rec.get('exclusions'):
        reasons.append('not_conditional_origin_candidate')
    if rec.get('origin_phase')!=2 or cat(rec.get('phase_raw'))!='PHASE2':reasons.append('not_unambiguous_phase2')
    slots=rec.get('historical_mapping_slots') or []
    if (rec.get('mapping_inputs_qualified') is not True or rec.get('mapping_status')!='unique_exact_historical_drug_aliases'
            or len(slots)!=1 or slots[0].get('status')!='unique_exact_historical_alias'
            or len(slots[0].get('candidate_drug_ids') or [])!=1 or len(rec.get('drug_ids') or [])!=1):
        reasons.append('historical_drug_identity_not_single_exact')
    if not rec.get('target_ids') or rec.get('unrecognized_historical_target_ids'):reasons.append('target_annotation_missing_or_unrecognized')
    products=rec.get('source_products') or []
    if (len(products)!=1 or cat(products[0].get('intervention_type')) not in {'DRUG','BIOLOGICAL'}
            or cat((rec.get('source_arm') or {}).get('group_type'))!='EXPERIMENTAL'):
        reasons.append('not_one_linked_experimental_product')
    if (not rec.get('condition_verbatim_normalized') or
            'multiple_conditions_arm_assignment_unqualified' in rec.get('qualification_holds',[])):
        reasons.append('not_single_condition_assignment')
    interval=rec.get('start_interval') or {};low=interval.get('lower_date');high=interval.get('upper_date')
    if (not low or not high or not '2022-01-01'<=low<=high<='2024-12-31'
            or interval.get('precision') not in {'day','month','year'}):
        reasons.append('start_not_wholly_2022_to_2024')
    return reasons


def select(path,count):
    best={};seen=set();reasons=Counter();eligible_scopes=0;digest=hashlib.sha256();offset=0
    with Path(path).open('rb') as f:
        for line,raw in enumerate(f,1):
            digest.update(raw);rec=json.loads(raw);pid=rec['program_id']
            if pid in seen:raise ValueError('Duplicate parent program ID')
            seen.add(pid);excluded=eligibility(rec)
            if excluded:reasons.update(excluded)
            else:
                eligible_scopes+=1;nct=rec['nct_id'];order=(rank('program',pid),pid)
                proof={'path':str(Path(path).resolve()),'line':line,'byte_offset':offset,'bytes':len(raw),
                    'sha256':hashlib.sha256(raw).hexdigest()}
                if nct not in best or order<best[nct][0]:best[nct]=(order,rec,proof)
            offset+=len(raw)
    ordered=sorted(best,key=lambda nct:(rank('trial',nct),nct))
    result={'parent_scopes_scanned':len(seen),'eligible_scopes':eligible_scopes,'eligible_distinct_trials':len(best),
        'rejection_reason_counts_overlapping':dict(reasons),'parent_program_bytes_sha256':digest.hexdigest()}
    if len(best)<count:raise InsufficientPool(result,count)
    return [(best[nct][1],best[nct][2]) for nct in ordered[:count]],result


class InsufficientPool(ValueError):
    def __init__(self,report,requested):
        self.report={**report,'requested_distinct_trials':requested,'criteria_relaxed':False}
        super().__init__('Insufficient distinct-trial pool; criteria were not relaxed')


def source_rows(frame,wanted,expected_hash):
    found={};offset=0;digest=hashlib.sha256()
    with Path(frame).open('rb') as f:
        for line,raw in enumerate(f,1):
            digest.update(raw);row=json.loads(raw);nct=row['study']['nct_id']
            if nct in wanted:
                if nct in found:raise ValueError('Duplicate origin source NCT')
                validate(row)
                found[nct]={'record':row,'proof':{'path':str(Path(frame).resolve()),'line':line,
                    'byte_offset':offset,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}}
            offset+=len(raw)
    if digest.hexdigest()!=expected_hash:raise ValueError('Origin source frame fingerprint changed')
    if set(found)!=wanted:raise ValueError('Missing retained original origin/prior-risk source row')
    return found


def verify_selected(rec,source):
    row=source['record'];s=row['study']
    low,high,precision=start_bounds(s.get('start_month_year'))
    expected_interval=(rec['start_interval']['lower_date'],rec['start_interval']['upper_date'],rec['start_interval']['precision'])
    if rec['source_proof']!=source['proof']:raise ValueError('Original source row/byte fingerprint mismatch')
    if (s['nct_id']!=rec['nct_id'] or s['phase']!=rec['phase_raw'] or cat(s['start_date_type'])!='ACTUAL'
            or (low,high,precision)!=expected_interval or s['overall_status']!=rec['status_raw']
            or len({norm(c['name']) for c in row['conditions'] if norm(c['name'])})!=1
            or rec['condition_verbatim_normalized'] not in {norm(c['name']) for c in row['conditions']}
            or rec['population_source']!=row['eligibilities'] or rec['design_source']!=row['designs']
            or rec['source_arm']!=next(a for a in row['design_groups'] if a['id']==rec['arm_id'])):
        raise ValueError('Origin-only selected scope/source projection mismatch')
    links=sorted({l['intervention_id'] for l in row['design_group_interventions'] if l['design_group_id']==rec['arm_id']})
    expected=[next(p for p in row['interventions'] if p['id']==iid) for iid in links]
    if links!=rec['regimen_source_intervention_ids'] or expected!=rec['source_products']:
        raise ValueError('Original regimen linkage fingerprint mismatch')


def build(origin_path,expected_sha256,output,count=12):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    contract=criteria(count)
    write(output/'criteria-freeze.json',contract)  # Before any source program/selection scan.
    (output/'executed-origin-review.py').write_bytes(Path(__file__).read_bytes())
    try:
        origin,origin_pin=read_bound_json(origin_path)
        if origin_pin['sha256']!=expected_sha256:raise ValueError('Wrong pinned origin seal')
        if (origin.get('status')!='sealed_mapping_qualified_reconstructed_exploratory'
                or origin.get('origin_at')!='2025-01-01T00:00:00Z' or origin.get('endpoint_rows_queried')!=0
                or origin.get('clinical_ready') is not False or origin.get('clinical_locked') is not False):
            raise ValueError('Origin-only reconstructed input seal required')
        from tools.science.endpoint_restore import verify_origin_closure
        _,closure=verify_origin_closure(origin_path,expected_sha256)
        pins=[{'path':str(p.resolve()),'sha256':h} for p,h in closure.items()]
        program_proof=next(p for p in origin['files'] if Path(p['path']).name=='origin-programs.jsonl')
        chosen,pool=select(program_proof['path'],count)
        if pool['parent_program_bytes_sha256']!=program_proof['sha256']:raise ValueError('Parent program fingerprint changed during selection')
        if pool['parent_scopes_scanned']!=origin['programs']:raise ValueError('Parent membership count differs')
        frames={Path(r['source_proof']['path']).resolve() for r,_ in chosen}
        if len(frames)!=1:raise ValueError('One consistent origin source frame required')
        frame=frames.pop()
        if frame not in closure:raise ValueError('Original source frame outside frozen ancestry')
        prior_ids={a['nct_id'] for r,_ in chosen for a in r['prior_higher_phase_verbatim_alerts']}
        if len(prior_ids)>contract['max_prior_source_rows']:raise ValueError('Prior-risk source-row bound exceeded; no truncation')
        wanted=prior_ids|{r['nct_id'] for r,_ in chosen};originals=source_rows(frame,wanted,closure[frame])
        (output/'packets').mkdir();selected=[];packet_pins=[];total=0
        for rec,program_row_proof in chosen:
            source=originals[rec['nct_id']];verify_selected(rec,source)
            prior=[originals[nct] for nct in sorted({a['nct_id'] for a in rec['prior_higher_phase_verbatim_alerts']})]
            packet={'schema_version':1,'role':'evaluation_only','review_phase':'origin_only_before_followup',
                'origin_seal':origin_pin,'historical_mapping_manifest':origin['historical_mapping_manifest'],
                'program_row_proof':program_row_proof,'origin_scope':rec,'original_origin_source':source,
                'original_prior_risk_sources':prior,'clinical_labels':[],
                'followup_sources_read':False,'qualification_holds_preserved':True,
                'review_questions':['Does the historical exact alias identify this experimental product/formulation?',
                    'Is the linked treatment experimental rather than background/comparator/rescue, with one interpretable regimen?',
                    'What indication/subtype, biomarker, treatment line, age and route are supported at origin, and which are unresolved?',
                    'Does source evidence qualify arm-level phase/activity and actual start without imputed precision?',
                    'Do prior-stage alerts establish same-program pre-origin higher phase, or remain unresolved?',
                    'Which origin-only eligibility holds can be source-supported, excluded or retained unresolved?'],
                'clinical_eligibility':'unresolved_pending_origin_only_review','outcome_adjudication_performed':False}
            dest=output/'packets'/(rec['nct_id']+'-'+str(rec['arm_id'])+'.json');write(dest,packet)
            total+=dest.stat().st_size
            if total>contract['max_total_packet_bytes']:raise ValueError('Pilot packet byte bound exceeded; no truncation')
            packet_pins.append({'path':str(dest),'sha256':sha(dest),'bytes':dest.stat().st_size})
            selected.append({'nct_id':rec['nct_id'],'arm_id':rec['arm_id'],'program_id':rec['program_id'],
                'drug_ids':rec['drug_ids'],'target_ids':rec['target_ids'],'trial_rank':rank('trial',rec['nct_id']),
                'program_rank':rank('program',rec['program_id']),'qualification_holds':rec['qualification_holds'],
                'packet':str(dest),'packet_sha256':packet_pins[-1]['sha256']})
        write(output/'selection.json',{'status':'frozen_origin_only_review_inputs','selection':selected,'pool':pool,
            'parent_membership_changed':False,'criteria_relaxed':False,'clinical_labels_assigned':0,
            'qualified_clinical_programs':0,'followup_sources_read':False,'prior_source_rows':len(prior_ids),
            'source_rows_retained':len(originals),'total_packet_bytes':total,'interpretation':contract['interpretation']})
        # Check all transitive original bytes again before committing the pack.
        verify_pins(pins)
        assets=[output/'criteria-freeze.json',output/'executed-origin-review.py',output/'selection.json']
        write(output/'pack-freeze.json',{'schema_version':1,'status':'sealed_origin_only_review_pack',
            'sealed_at_utc':datetime.now(timezone.utc).isoformat(),'origin_seal':origin_pin,
            'criteria_sha256':sha(output/'criteria-freeze.json'),'selected_distinct_trials':len(selected),
            'clinical_labels_assigned':0,'followup_sources_read':False,'parent_membership_changed':False,
            'clinical_ready':False,'clinical_locked':False,'files':packet_pins+[
                {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in assets],
            'ancestor_pins':pins,'provider_spend_usd':0})
        return {'status':'sealed_origin_only_review_pack','output':str(output),'seal_sha256':sha(output/'pack-freeze.json'),
            'trial_ids':[r['nct_id'] for r in selected],'pool':pool}
    except Exception as error:
        write(output/'failure.json',{'status':'failed','type':type(error).__name__,'error':str(error),
            'criteria_relaxed':False,'followup_sources_read':False,
            'pool':error.report if isinstance(error,InsufficientPool) else None})
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--origin-seal',type=Path,required=True)
    p.add_argument('--origin-sha256',default=ORIGIN_SEAL_SHA256);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(build(a.origin_seal,a.origin_sha256,a.output)),flush=True)
