"""Reproduce the 24-case, explicitly unblinded development feasibility review.

Authored decisions below are scientific review inputs, not inferred gold labels.
Run with --output pointing to the newly reserved protocol directory.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import shutil
import traceback

from tools.feasibility.program_outcomes import (load, sha, verify_manifest,
    phase_screen, report_window, date_bounds, incident_supported, validate_bundle)

ROOT = Path(__file__).resolve().parents[2]
SESSION = ROOT / 'data/benchmark/cohorts/clinical-long-session-20261017T064802Z'
ORIGIN = ROOT / 'data/benchmark/cohorts/aact-origin-audit-20261017T021043Z'
ENDPOINT = ROOT / 'data/benchmark/cohorts/aact-followup-20250101-20261017T051834Z'
ANCHORS = [(SESSION, 'd2413f77400811069c5237150b565d2899aa7eeb0877409ea0e305a3adc62dcc'),
           (ORIGIN, '20c9f13c8b4b44c7e25f84fa26c7916f888081c5d11d3b52f4f23c1523f7ba65'),
           (ENDPOINT, '0c5ca850e61b922e379258072f79821e55aeed3e9fb2dc3be3ca8005568aaf9b')]

# Explicit target-arm selection from the origin dump. Null selects retained scope review.
ARMS = {'P01': [[21974621,21974622]], 'P02': [[22150217],[22150219,22150220,22150221],[22150223]],
    'P03': None, 'P04': [[22402200]], 'P05': [], 'P06': None, 'P07': [[22344950]],
    'P08': [[21981638,21981639,21981640,21981641,21981642],[21981643],[21981644],
            [21981645],[21981646],[21981647],[21981648]], 'P09': None,
    'P10': [[22089799]], 'P11': [[22168301]], 'P12': [[21919873],[21919874]],
    'P13': [], 'P14': [[22302750]], 'P15': None,
    'P17': [[21754374],[21754375],[21754376]], 'P16': [[22486805]],
    'P18': [[22013277]], 'P19': [[21817980,21817981]], 'P20': [],
    'P21': [[22185492]], 'P22': [], 'P23': [[22395481,22395482]],
    'P24': [[22273735],[22273736]]}
ROLES = {'P05':'rescue','P13':'comparator','P20':'background','P22':'closed_arm'}
NOTES = {
 'P01':'ES-SCLC monotherapy dose groups, not NSCLC. Phase 3 announcement links the drug family; exact line/population equivalence and incident timing remain qualified.',
 'P02':'Separate phase 2a, phase 2b double blind and extension scopes. Prior efficacy reporting is not phase advancement; arm-specific activity at origin remains unknown.',
 'P03':'MATCH J only. Arm narrative specifies pertuzumab/trastuzumab, but linked interventions include trastuzumab emtansine. Preserve conflict; platform recruitment cannot establish J activity.',
 'P04':'Phase 3 adolescent FH program; outside primary Phase 1/2 route.',
 'P05':'Tocilizumab is CRS rescue in a cevostamab study; exclude anchor program.',
 'P06':'Triple-combination safety extension, not ivacaftor monotherapy. Phase 3 excluded.',
 'P07':'Semaglutide treatment comparison; actual primary completion before origin does not itself establish phase progression. At-risk state and continuing program activity unresolved.',
 'P08':'Five dose-escalation arms grouped; tumor expansions and combination separated. Mixed-stage activity and shared development unresolved. Prostate cohort potentially overlaps TAMARACK.',
 'P09':'Only atezolizumab plus T-DM1 HER2 cohort. Mixed-phase platform stage/activity cannot be transferred to this arm.',
 'P10':'SPG5/27-hydroxycholesterol program, not familial hypercholesterolemia. Mixed-phase stage unresolved; UNKNOWN follow-up is not failure.',
 'P11':'Acute GVHD prophylaxis with transplant background regimen; underlying leukemia is not the target indication. Program progression ascertainment incomplete.',
 'P12':'Separate partial-function and N1303K CF populations; regimen is elexacaftor/tezacaftor/ivacaftor. Later N1303K primary sweat-chloride result cannot label the other arm or rewrite origin endpoint hierarchy.',
 'P13':'Dulaglutide active comparator to experimental tirzepatide; exclude anchor role.',
 'P14':'Origin already contains results. Prior fresh-efficacy exclusion retained as history, but next-phase risk is unresolved rather than automatically failed or excluded solely by publication.',
 'P15':'Phase I and II described within one structured arm; arm-level stage and multikinase selectivity remain unresolved.',
 'P16':'Phase 3 cardiovascular prevention; later results cannot enter January 2025 endpoint.',
 'P17':'Three tumor/regimen cohorts separated. Tocilizumab toxicity mitigation and antitumor endpoints remain distinct; inaccessible melanoma abstract is a lead only.',
 'P18':'Phase 3 cognition/dysglycemia program; exclude. Stale UNKNOWN is not individual censoring.',
 'P19':'Dose variants grouped for mCRPC. Phase 2/3 origin stage unresolved. Dosing cessation with safety/benefit-risk rationale differs from later business discontinuation.',
 'P20':'Pertuzumab is background therapy for WOKVAC vaccine evaluation; exclude anchor role.',
 'P21':'Evolocumab add-on immunotherapy in NSCLC. Intervention description says 14 mg; arm description says 140 mg. Preserve discrepancy. Safety/immune endpoints are not efficacy success.',
 'P22':'Tocilizumab arm closed before origin although RECOVERY platform recruits; exclude.',
 'P23':'Not yet recruiting and Phase 3 at origin. No delayed-entry rule in this protocol.',
 'P24':'Origin dose escalation/expansion separated, but tumor cohorts and active phase unresolved. Related I-DXd development with P01; not independent by NCT.'}


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def proof(path, pointer=None):
    path=Path(path).resolve()
    return {'path':str(path.relative_to(ROOT)), 'sha256':sha(path), 'json_pointer':pointer}


def derive():
    selected=load(ORIGIN/'selected.json'); context=load(ORIGIN/'origin-context.json')
    contexts={c['nct_id']:(i,c) for i,c in enumerate(context)}
    prior={c['candidate_id']:c for c in load(SESSION/'program-event-review.json')['cases']}
    mappings={c['candidate_id']:c for c in load(ORIGIN/'mapping-review.json')}
    scopes={c['candidate_id']:c for c in load(SESSION/'origin-scope-review/report.json')['cases']}
    contents={c['source_id']:c for c in load(SESSION/'source-content-review.json')['sources']}
    timeline={c['candidate_id']:c for c in load(SESSION/'timeline/timeline.json')}
    bundle={k:[] for k in ['programs','trial-arm-links','mapping-evidence','dispositions','reports','events','followup-assessments','ambiguities']}
    for index,c in enumerate(selected):
        cid=c['candidate_id'];r=c['origin_record'];nct=r['nct_id'];ci,ctx=contexts[nct]
        arms={a['id']:a for a in ctx['arms']}
        groups=ARMS[cid]
        if groups is None:groups=[scopes[cid]['selected_arm_ids']]
        baseproof=proof(ORIGIN/'selected.json',f'/{index}/origin_record')
        ctxproof=proof(ORIGIN/'origin-context.json',f'/{ci}')
        for ai,a in enumerate(ctx['arms']):
            bundle['trial-arm-links'].append({'arm_id':f'aact-20230101:{nct}:{a["id"]}',
                'candidate_id':cid,'trial_id':f'ctgov:{nct}','source_arm':a,
                'source':{**ctxproof,'json_pointer':f'/{ci}/arms/{ai}'},'role':'evaluation_only'})
        screen=phase_screen(r['phase'],r['overall_status'],ROLES.get(cid,'experimental'))
        if cid in {'P02','P03','P07','P14'} and screen=='provisional_origin_screen_pass':
            screen='unresolved_arm_activity_or_at_risk_state'
        programids=[]
        for gi,group in enumerate(groups,1):
            if not set(group)<=set(arms):raise ValueError('Selected arm absent from origin')
            pid=f'local-program-v1:{cid}:{gi}';programids.append(pid)
            sourcearms=[arms[a] for a in group]
            ids=set(i for a in sourcearms for i in a['intervention_ids'])
            interventions=[i for i in r['interventions'] if i['id'] in ids]
            bundle['programs'].append({'program_id':pid,'version':1,'candidate_id':cid,
                'trial_ids':[f'ctgov:{nct}'],'arm_ids':[f'aact-20230101:{nct}:{a}' for a in group],
                'related_program_cluster_id':'drug-anchor:'+c['drug_anchor'],
                'cluster_basis':'shared selected drug anchor; conservative dependence flag, not proven biological equivalence',
                'target_anchor':c['target_anchor'],'external_target_id':None,
                'external_drug_id':None,'external_indication_id':None,'namespace_versions':{'AACT':'2023-01-01'},
                'external_id_reason':'Origin-qualified canonical crosswalk not adjudicated; retain source identifiers.',
                'origin_interventions':interventions,'reported_arm_scopes':sourcearms,
                'study_conditions_context_only':r['conditions'],'indication_scope': 'Use selected arm text; study-wide conditions are contextual candidates only',
                'intended_action':None,'modality':None,
                'mechanism_reason':'Mechanism reference in prior review is not certified origin-available; no inferred mechanism label.',
                'retrospective_mapping_review':mappings[cid],
                'origin_phase':r['phase'],'origin_status':r['overall_status'],'origin_screen':screen,
                'historically_certified':False,'origin_mapping_proof':None,
                'identity_status':'source_qualified_candidate_not_independent_certified_program',
                'review_note':NOTES[cid],'origin_source':baseproof,'arm_source':ctxproof,
                'sponsor_history':{'origin_reported':r['sponsors'],'transfer_adjudicated':False},'role':'evaluation_only'})
            bundle['mapping-evidence'].append({'mapping_id':f'mapping:{cid}:{gi}','program_id':pid,
                'relation':'origin arm-to-intervention link plus explicitly qualified authored scope',
                'origin_evidence':[baseproof,ctxproof],'availability_basis':'versioned AACT January 1 2023 dump; retrospective retrieval',
                'confidence':'Source identity supported; canonical drug/target/indication and mechanism eligibility unadjudicated',
                'alternatives_or_conflicts':NOTES[cid], 'later_review_separate':proof(ORIGIN/'mapping-review.json'),
                'role':'evaluation_only'})
        bundle['dispositions'].append({'candidate_id':cid,'nct_id':nct,'program_ids':programids,
            'origin_screen':screen,'reason':NOTES[cid],'prior_disposition':prior[cid]['review_disposition'],
            'source':baseproof,'role':'evaluation_only'})
        for ei,e in enumerate(prior[cid]['events']):
            rid='report:'+e['source_id']; content=contents.get(e['source_id'],{})
            window=report_window(e['public_report_date'],'2023-01-01','2025-01-01')
            report={**e,'report_id':rid,'content_status':content.get('content_status','unreviewed'),
                'first_located_report_date':e['public_report_date'],'date_bounds':date_bounds(e['public_report_date']),
                'report_window':window,'parent':proof(SESSION/'program-event-review.json',f'/cases/{index}/events/{ei}'),
                'content_proof':proof(SESSION/'source-content-review.json'),'role':'evaluation_only'}
            bundle['reports'].append(report)
            domain=('phase_advancement' if 'phase3_initiation' in e['event_type'] else
                'safety_or_benefit_risk_dosing_stop' if e['source_id']=='P19-dosing-stop-official' else
                'administrative_development_decision' if e['source_id']=='P19-postendpoint-discontinuation' else 'efficacy_report')
            # P03's earlier abstract and later paper report the same candidate result.
            eventid='event:P03:subprotocol-J-result' if cid=='P03' else 'event:'+e['source_id']
            existing=next((x for x in bundle['events'] if x['event_id']==eventid),None)
            if existing:
                existing['report_ids'].append(rid)
                existing['deduplication_reason']='Same MATCH J regimen/population result; earlier abstract unavailable, so linkage remains provisional.'
                continue
            event={'event_id':eventid,'candidate_id':cid,'candidate_program_ids':programids,
                'qualified_program_ids':[], 'report_ids':[rid],'domain':domain,
                'analysis_scope':{'arm':e['arm'],'population':e['population'],'endpoint':e['endpoint']},
                'finding':e['finding'],'scope_match':'unresolved',
                'event_date':None,'event_interval':{'lower':None,'upper':e.get('event_occurred_on_or_before')},
                'date_reason':'Report date is not actual event date; no supported incident lower bound.',
                'first_located_report_date':e['public_report_date'],'first_public_date':None,
                'report_window':window,'content_status':report['content_status'],
                'adjudication':'candidate_report_not_qualified_incident_event','incident_supported':False,
                'clinical_label':None,'role':'evaluation_only'}
            if cid=='P12':
                event['candidate_program_ids']=[programids[1]]
                event['scope_match']='genotype_matches_but_endpoint_hierarchy_unresolved'
            if cid=='P17':event['candidate_program_ids']=[programids[0]]
            bundle['events'].append(event)
        obs=timeline[cid]['observations']
        bundle['followup-assessments'].append({'candidate_id':cid,'program_ids':programids,
            'observed_registry_dates':[o['snapshot_date'] for o in obs if o['record']],
            'observed_states':[{'date':o['snapshot_date'],'status':(o['record'] or {}).get('overall_status')} for o in obs],
            'administrative_endpoint':'2025-01-01','censoring_date':None,'clinical_label':None,
            'event_ascertainment':'incomplete; trial presence/status does not certify program follow-up',
            'status':'excluded_primary_route' if screen.startswith('excluded') else 'unresolved_program_followup',
            'source':proof(SESSION/'timeline/timeline.json',f'/{index}'),'role':'evaluation_only'})
        bundle['ambiguities'].append({'ambiguity_id':'review:'+cid,'candidate_id':cid,'program_ids':programids,
            'reason':NOTES[cid],'required_resolution':'Arm/program stage and risk set, historical mapping, event timing and complete follow-up as applicable.',
            'blocks_training':True,'role':'evaluation_only'})
    bundle['ambiguities'].append({'ambiguity_id':'canary:PMID41051123','candidate_id':'P02',
        'program_ids':[],'reason':'Unrelated retrospective rhinosinusitis article with matching NCT reference: exclude from PN outcome evidence.',
        'blocks_training':False,'role':'evaluation_only'})
    # Normalize tuple date bounds to the persisted JSON representation before
    # replay comparisons, so disk round-tripping cannot change semantic equality.
    return selected,json.loads(json.dumps(bundle,ensure_ascii=False))


def render(bundle, flow):
    esc=lambda x:html.escape(str(x))
    cards=[]
    for d in bundle['dispositions']:
        cid=d['candidate_id'];ps=[p for p in bundle['programs'] if p['candidate_id']==cid]
        es=[e for e in bundle['events'] if e['candidate_id']==cid]
        rs=[r for r in bundle['reports'] if r['candidate_id']==cid]
        source_links=''.join(f'<li><a href="{esc(r["source_url"])}">{esc(r["source_id"])}</a> — {esc(r["content_status"])}; {esc(r["first_located_report_date"])}</li>' for r in rs)
        followup=next(f for f in bundle['followup-assessments'] if f['candidate_id']==cid)
        chronology=''.join(f'<tr><td>{esc(o["date"])}</td><td>{esc(o["status"])}</td></tr>' for o in followup['observed_states'])
        findings=''.join(f'<li>{esc(e["first_located_report_date"])}: {esc(e["finding"])}</li>' for e in es)
        if not findings:findings='<li>No qualifying outcome report retained. This does not establish failure.</li>'
        body=json.dumps({'programs':ps,'events':es,'followup':followup},indent=2,ensure_ascii=False)
        display=d['origin_screen'].replace('_',' ').capitalize()
        cards.append(f'<article><h2>{esc(cid)} · {esc(d["nct_id"])}</h2><p><b>{esc(display)}</b></p><p>{esc(d["reason"])}</p><h3>Located reports</h3><ul>{findings}</ul><details><summary>Five-date registry chronology</summary><table><tr><th>Snapshot</th><th>Reported status</th></tr>{chronology}</table><p>Registry states are observations, not outcome or censoring labels.</p></details><details><summary>Source links and availability</summary><ul>{source_links}</ul></details><details><summary>Original arms and structured review</summary><pre>{esc(body)}</pre></details></article>')
    links=' '.join(f'<a href="{name}.json">{esc(name)}</a>' for name in bundle)
    summary=f"{flow['representatives']} trial representatives · {flow['program_candidates']} candidate program scopes · {flow['source_reports']} reports · {flow['candidate_events']} candidate events · 0 certified incident advancements"
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Program and outcome feasibility</title><style>body{font:17px system-ui;max-width:1100px;margin:35px auto;padding:0 18px;color:#183042;background:#f5f8fa}article{background:white;border:1px solid #ccd8df;border-radius:10px;padding:20px;margin:20px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}a{color:#005e82}summary{cursor:pointer;padding:8px 0}nav a{display:inline-block;margin:8px 12px 8px 0}td,th{text-align:left;padding:5px 16px 5px 0}</style><h1>Program and outcome feasibility</h1><p><b>Training: no-go. Targeted mapping and event-resolution work: proceed.</b></p><p>24 exposed development representatives. All outcomes and individual censoring remain unassigned. AI-assisted consistency review is not independent scientific adjudication.</p><p>'+esc(summary)+'</p><p>Start with P01/P24: verify the linked Phase 3 trial timing and population. Then resolve arm activity, historical mappings and follow-up before cohort expansion.</p><nav><a href="decision.md">Decision and next steps</a><a href="cohort-flow.json">Full counts</a>'+links+'</nav>'+''.join(cards)+'</html>'


def run(output):
    output=Path(output).resolve()
    protocol=load(output/'protocol.json')
    if protocol['protocol_id']!='program-outcome-development-v0.2':raise ValueError('Unexpected protocol')
    # Exclusive lock persists after failure: never overwrite or silently repeat a build.
    write(output/'build-reservation.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(output/'protocol.json')})
    previous=None
    def journal(stage,detail):
        nonlocal previous
        entry={'time':datetime.now(timezone.utc).isoformat(),'stage':stage,'detail':detail,'previous':previous}
        digest=hashlib.sha256(json.dumps(entry,sort_keys=True).encode()).hexdigest()
        with (output/'build-journal.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({**entry,'sha256':digest})+'\n');f.flush()
        previous=digest
    try:
        journal('started',{'provider_spend_usd':0})
        parents=[{'path':str(p.relative_to(ROOT)),'sha256':h,'files_verified':verify_manifest(p/'evidence-manifest.json',h)} for p,h in ANCHORS]
        journal('parents_verified',parents)
        selected,bundle=derive();checks=validate_bundle(bundle,selected)
        _,replay=derive()
        if bundle!=replay:raise ValueError('Non-deterministic replay')
        for name,value in bundle.items():write(output/(name+'.json'),value)
        screens=Counter(d['origin_screen'] for d in bundle['dispositions'])
        flow={'representatives':len(selected),'dispositions':dict(screens),'program_candidates':len(bundle['programs']),
            'selected_arm_links':sum(len(p['arm_ids']) for p in bundle['programs']),
            'unique_drug_anchors':len({c['drug_anchor'] for c in selected}),
            'unique_target_anchors':len({c['target_anchor'] for c in selected}),
            'adjudicated_indication_ids':0,'related_drug_clusters':len({p['related_program_cluster_id'] for p in bundle['programs']}),
            'source_reports':len(bundle['reports']),'candidate_events':len(bundle['events']),
            'candidate_advancement_reports':sum(e['domain']=='phase_advancement' for e in bundle['events']),
            'qualified_incident_advancements':0,'historically_certified_programs':0,
            'resolved_individual_censoring':0,'training_labels':0,
            'provisional_screen_pass_program_candidates':sum(p['origin_screen']=='provisional_origin_screen_pass' for p in bundle['programs']),
            'unresolved_origin_program_candidates':sum(p['origin_screen'].startswith('unresolved') for p in bundle['programs']),
            'excluded_origin_program_candidates':sum(p['origin_screen'].startswith('excluded') for p in bundle['programs']),
            'reports_by_content_status':dict(Counter(r['content_status'] for r in bundle['reports'])),
            'reports_by_window':dict(Counter(r['report_window'] for r in bundle['reports'])),
            'missingness':{'canonical_crosswalk_unadjudicated':len(bundle['programs']),'individual_followup_unresolved':len(selected)},
            'grouping_sensitivity':'Program candidates and related drug clusters are descriptive counts, not bounds on independent sample size. Indication/program deduplication remains unadjudicated.',
            'role':'evaluation_only'}
        write(output/'cohort-flow.json',flow)
        write(output/'validation.json',{**checks,'deterministic_replay':'identical','parents':parents,'protocol':proof(output/'protocol.json')})
        write(output/'second-pass-review.json',{'method':'same-assistant source inspection plus deterministic invariants; not independent review',
            'findings':['P03 linked T-DM1 conflicts with pertuzumab/trastuzumab arm narrative; retained unresolved.',
                'P21 14 mg intervention description conflicts with 140 mg arm text; retained without correction.',
                'P14 fresh-efficacy exclusion cannot automatically exclude a next-phase risk set; marked unresolved.',
                'P01 announcement provides an upper event bound only; cannot establish incident post-origin event.',
                'P01 retained page metadata modified in 2026; 2024 publication date does not prove archived content unchanged.',
                'P03 two source reports grouped as one provisional candidate event, earlier unavailable content retained.',
                'P12 N1303K report linked only to N1303K candidate, not partial-function arm.',
                'PMID41051123 mismatched population retained as rejection canary.'],
            'disagreements_with_parent':['P14 disposition revised for advancement estimand; earlier exclusion concerned fresh efficacy.'],
            'all_24_checked':True,'scientific_validation':'not_established','role':'evaluation_only'})
        decision=f'''# Program and outcome feasibility decision

**No-go for clinical scorer training or a locked T1 benchmark. Proceed with targeted resolution of the program unit and advancement evidence before expanding the cohort.**

All {len(selected)} frozen representatives are accounted for. There are {flow['program_candidates']} candidate program scopes across {flow['selected_arm_links']} selected arm links, {flow['source_reports']} source reports and {flow['candidate_events']} candidate events. These are not independent samples. The screens are: {dict(screens)}.

One retained report announces linked Phase 3 initiation (P01). It supplies an upper event bound, but not an established post-origin lower bound, and exact treatment-line/population equivalence remains qualified. Its retained web page has 2026 modification metadata. No incident advancement is certified under the amended protocol. Zero qualified events means unresolved certification, not zero real-world advancement.

Canonical origin drug/target/indication crosswalks remain unadjudicated. Local arm identities and original intervention text are retained; a missing ontology mapping is distinct from a missing clinical record. All 24 have five registry observations, but none has a defensible individual censoring assignment. No-event observations cannot become negative labels.

The prior efficacy-focused exclusions have been reconsidered for the next-phase estimand. In particular, prior primary completion or results do not alone prove a program is no longer at risk for advancement. Mixed phases, platform activity, background treatment and overlapping drug development require separate handling. P03 and P21 contain retained source inconsistencies; no source fields were silently repaired.

## Next permitted work

1. Resolve P01/P24 at the same drug/regimen and SCLC treatment-line scope. Extract the linked NCT06203210 record from the already restored January 2025 database, retaining actual start type/date and first-posted fields; inspect earlier dated records if needed. This can establish a defensible lower bound without treating announcement date as dosing date. Seek an archived 2024 announcement version only if needed to certify source availability.
2. Resolve active stage and prior advancement for the provisional and mixed-phase units; reconcile P03 regimen linkage and P21 dose discrepancy. Complete only the historical identifier/mechanism references necessary for these units.
3. Once one reproducible advancement route and explicit follow-up rules are demonstrated, freeze an origin-only expansion protocol before examining expansion outcomes. Exclude these 24 exposed cases from any untouched-test claim.
4. If resolution fails, continue contemporary T6 claim-support evaluation under its own protocol; do not substitute a generic efficacy or termination label for T1.

No arbitrary sample threshold, event-rate estimate, power calculation or model-training trigger follows from this purposive set. The clinical phase completes with an explicit gate decision, not scientific validation. Provider spending remained $0; no databases or downloader were restarted, and no model adapter or runtime evidence was changed.

## Verification and review

Parent manifests and their file hashes checked; deterministic replay identical; table references, selection accounting, phase/date rules and role isolation checked. See validation.json, second-pass-review.json and the hash-chained build journal. This was AI-assisted unblinded development review, not independent scientist gold. Original sealed parents remain unchanged.
'''
        (output/'decision.md').write_text(decision,encoding='utf-8',newline='\n')
        (output/'Review.html').write_text(render(bundle,flow),encoding='utf-8',newline='\n')
        for source in [Path(__file__),ROOT/'tools/feasibility/program_outcomes.py',
                       ROOT/'tools/feasibility/verify_program_feasibility.py', ROOT/'tests/test_program_outcomes.py']:
            shutil.copyfile(source,output/source.name)
        journal('completed',{'checks':checks,'flow':flow})
        files=[{'path':p.relative_to(output).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(output.rglob('*')) if p.is_file()]
        write(output/'evidence-manifest.json',{'schema_version':1,'role':'evaluation_only','parents':parents,'files':files})
        print(json.dumps({'output':str(output),'manifest_sha256':sha(output/'evidence-manifest.json'),'flow':flow}))
    except BaseException as exc:
        journal('failed',{'type':type(exc).__name__,'message':str(exc)})
        write(output/'failure.json',{'traceback':traceback.format_exc(),'automatic_retry':False})
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
