"""Apply frozen v0.3 rules to retained development evidence, without acquisition."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import shutil

from tools.feasibility.program_outcomes import load, sha, verify_manifest
from tools.feasibility.advancement_rules import evaluate, group_shared_events, validate_policy

ROOT=Path(__file__).resolve().parents[2]
PARENT=ROOT/'data/benchmark/cohorts/program-outcome-feasibility-20261017T143507Z'
LINK=ROOT/'data/benchmark/cohorts/phase3-linkage-20261017T144828Z'


def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2,ensure_ascii=False);f.write('\n')


def proof(path,pointer):
    return {'path':str(path),'sha256':sha(path),'json_pointer':pointer}


def authored_facts():
    timing=load(LINK/'timing-assessment.json')
    # Facts are explicit authored interpretations of retained, exposed sources.
    # Null origin arm activity/risk is deliberate: a study screen is not a proof.
    shared={'next_stage':3,'origin_active':None,'origin_at_risk':None,
        'event_kind':'trial_any_arm_first_dose','event_interval':timing['conditional_trial_dosing_interval'],
        'bounds_quality':'conditional','report_date':'2024-08-01','historical_content':'conditional',
        'canonical_event_id':'ctgov:NCT06203210:trial-initiation','event_linkage':'reviewed',
        'canonical_link_note':'Same retained announcement and next trial; this identifies the observed report/event, not qualified predecessor program equivalence.',
        'role':'evaluation_only','scientific_validation':'not_established',
        'evidence':[proof(LINK/'timing-assessment.json','/conditional_trial_dosing_interval'),
                    proof(LINK/'assessment.json','/remaining_gates'),
                    proof(LINK/'extraction/records.json','/records/2')]}
    a={**shared,'candidate_id':'P01','origin_stage':2,'product_relation':'documented_alias',
       'regimen_relation':'same_composition_route_schedule','dose_relation':'selection_from_origin_options',
       'population_relation':'origin_documented_nested_stratum',
       'scope_rationale':'Source alias, ES-SCLC second-line origin strata and the 12 mg/kg IV Q3W option support a narrowed program link. Other dose/population members are not labeled.',
       'evidence':shared['evidence']+[proof(LINK/'scope-comparison.json','/0'),
          proof(LINK/'scope-comparison.json','/1'),proof(LINK/'scope-comparison.json','/2'),proof(LINK/'scope-comparison.json','/3'),
          proof(PARENT/'dispositions.json','/0')]}
    b={**shared,'candidate_id':'P24','origin_stage':None,'product_relation':'documented_alias',
       'regimen_relation':'unknown','dose_relation':'unknown','population_relation':'unknown',
       'scope_rationale':'Shared drug lineage only. Exact origin SCLC cohort, dose/schedule and active stage are unresolved; later expansion status cannot fill origin gaps.',
       'evidence':shared['evidence']+[proof(LINK/'scope-comparison.json','/4'),proof(PARENT/'dispositions.json','/23')]}
    return [a,b]


def derive(policy):
    facts=authored_facts();results=[evaluate(f,policy) for f in facts]
    groups=group_shared_events(facts,results)
    applications=[];indexed={r['candidate_id']:r for r in results}
    for i,old in enumerate(load(PARENT/'dispositions.json')):
        cid=old['candidate_id'];excluded=old['origin_screen'].startswith('excluded')
        status=('excluded_origin_route' if excluded else 'candidate_transition_rule_applied' if cid in indexed else 'no_qualifying_next_phase_lead_retained')
        applications.append({'candidate_id':cid,'nct_id':old['nct_id'],'origin_screen':old['origin_screen'],
            'application_status':status,'program_ids':old['program_ids'],'rule_result':indexed.get(cid),
            'next_evidence_needed':('Keep exclusion; no replacement based on outcomes' if excluded else
                'Resolve experimental-arm dosing, origin arm activity/risk and historical content' if cid=='P01' else
                'Resolve origin SCLC cohort, regimen and active phase before transition linkage' if cid=='P24' else
                'Resolve origin program/stage and perform dated next-phase ascertainment; retained efficacy reports are not transition events'),
            'retained_ambiguity':old['reason'],'origin_source':proof(PARENT/'dispositions.json',f'/{i}'),
            'clinical_label':None,'censoring_date':None,'role':'evaluation_only'})
    classifications=[]
    for i,event in enumerate(load(PARENT/'events.json')):
        classifications.append({'event_id':event['event_id'],'candidate_id':event['candidate_id'],
            'retained_domain':event['domain'],'classification':('candidate_trial_initiation_not_experimental_first_dose'
                if event['domain']=='phase_advancement' else 'separate_descriptive_domain_not_primary_advancement'),
            'source':proof(PARENT/'events.json',f'/{i}'),'report_ids':event['report_ids'],'role':'evaluation_only'})
    flow={'cases':len(applications),'applications':dict(Counter(a['application_status'] for a in applications)),
        'retained_candidate_events':len(classifications),'phase_advancement_leads':1,
        'source_shared_event_groups':len(groups),'qualified_unique_primary_events':sum(g['qualified_unique_event_count'] for g in groups),
        'candidate_scope_relations':{r['candidate_id']:r['scope_relation'] for r in results},
        'clinical_training_labels_added':0,'censoring_dates_added':0,'new_cohort_members':0,
        'role':'evaluation_only','scientific_validation':'not_established'}
    if {x['candidate_id'] for x in applications}!={f'P{i:02}' for i in range(1,25)} or len(applications)!=24:
        raise ValueError('Frozen case membership changed')
    return {'authored-facts':facts,'transition-results':results,'shared-events':groups,
            'case-applications':applications,'event-classifications':classifications,'cohort-flow':flow}


def apply(output):
    output=Path(output).resolve();policy=load(output/'protocol.json');validate_policy(policy)
    if sha(output/'protocol.json')!=load(output/'protocol-freeze.json')['protocol_sha256']:
        raise ValueError('Frozen protocol changed')
    write(output/'application-reservation.json',{'started_at_utc':datetime.now(timezone.utc).isoformat(),
        'protocol_sha256':sha(output/'protocol.json'),'role':'evaluation_only'})
    try:
        for parent in policy['parents']:verify_manifest(Path(parent['path']),parent['sha256'])
        outputs=derive(policy)
        if outputs!=derive(policy):raise ValueError('Non-deterministic application')
        for name,value in outputs.items():write(output/(name+'.json'),value)
        evidence=[]
        for fact in outputs['authored-facts']:
            for p in fact['evidence']:
                value=load(p['path'])
                for key in p['json_pointer'].strip('/').split('/'):
                    value=value[int(key)] if isinstance(value,list) else value[key]
                evidence.append({'candidate_id':fact['candidate_id'],'proof':p,'value':value})
        write(output/'review-inputs.json',evidence)
        write(output/'verification.json',{'status':'passed','deterministic_replay':'identical',
            'cases_accounted':24,'source_pointers_resolved':len(evidence),'scientific_validation':'not_established'})
        esc=html.escape
        cards=[]
        for row in outputs['case-applications']:
            result=row['rule_result'];notes=('; '.join(result['blocking_reasons']) if result else row['next_evidence_needed'])
            cards.append('<article><h2>'+esc(row['candidate_id']+' · '+row['nct_id'])+'</h2><p><b>'+esc(row['application_status'].replace('_',' '))+'</b></p><p>'+esc(row['retained_ambiguity'])+'</p><details><summary>Rule result and remaining evidence</summary><p>'+esc(notes)+'</p><pre>'+esc(json.dumps(row,indent=2))+'</pre></details></article>')
        page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Program advancement rules v0.3</title><style>body{font:17px/1.5 system-ui;max-width:1100px;margin:35px auto;padding:20px;background:#f5f8fa;color:#183042}article{background:white;padding:20px;border:1px solid #ccd8df;border-radius:8px;margin:18px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}summary{cursor:pointer}a{color:#005e82}</style><h1>Program advancement rules v0.3</h1><p><b>Rules frozen for development. No new training labels or cohort expansion.</b></p><ul><li>Primary event: first participant receiving the qualifying experimental regimen in the next numerical phase.</li><li>Known origin dose selection and documented nested populations may qualify with narrower coverage.</li><li>Any-arm first dosing stays a separate trial-level observation.</li><li>A shared event counts once and joins predecessor cases for data splitting.</li></ul><p>P01 has an admissible narrowed scope link but insufficient primary-event evidence. P24 still needs origin cohort/stage qualification. Neither receives a label.</p><p><a href="protocol.json">Frozen protocol</a> · <a href="decision.md">Decision and next action</a> · <a href="cohort-flow.json">Counts</a> · <a href="shared-events.json">Shared-event accounting</a></p>'+''.join(cards)+'</html>'
        with (output/'Review.html').open('x',encoding='utf-8',newline='\n') as f:f.write(page)
        for path in [Path(__file__),ROOT/'tools/feasibility/advancement_rules.py',ROOT/'tests/test_advancement_rules.py']:
            shutil.copyfile(path,output/path.name)
        write(output/'application-completed.json',{'completed_at_utc':datetime.now(timezone.utc).isoformat(),
            'flow':outputs['cohort-flow'],'provider_spend_usd':0,'new_downloads':0,'database_restarts':0})
        print(json.dumps(outputs['cohort-flow']))
    except BaseException as exc:
        write(output/'application-failure.json',{'type':type(exc).__name__,'message':str(exc),'automatic_retry':False})
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    apply(parser.parse_args().output)
