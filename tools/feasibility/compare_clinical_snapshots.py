"""Compare frozen trial representatives in two AACT snapshots, without outcome labels."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess


def normalized(value):
    return re.sub(r'[^A-Z0-9]+', '_', (value or '').upper()).strip('_')


def compare(selected, followup, reviews, origin_date, followup_date):
    """Registry state comparison only; dates of program events remain unadjudicated."""
    ids = [c['origin_record']['nct_id'] for c in selected]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate selected trial')
    index = {}
    for row in followup:
        if row['nct_id'] in index or row['nct_id'] not in ids:
            raise ValueError('Duplicate or unselected follow-up trial')
        for field in ('study_first_posted_date', 'last_update_posted_date', 'results_first_posted_date'):
            if row.get(field) and row[field] > followup_date:
                raise ValueError('Post-cutoff follow-up information: '+field)
        index[row['nct_id']] = row
    review_index = {r['nct_id']:r for r in reviews}
    result = []
    for case in selected:
        old = case['origin_record']
        new = index.get(old['nct_id'])
        review = review_index[old['nct_id']]
        observations = []
        if new is None:
            observations.append('missing_followup_record_not_failure_or_censoring')
        else:
            if normalized(old['overall_status']) != normalized(new['overall_status']):
                observations.append('registry_status_changed_not_program_outcome')
            if normalized(old['phase']).replace('_','') != normalized(new['phase']).replace('_',''):
                observations.append('phase_field_changed_not_proven_transition')
            if sorted(old['conditions'] or []) != sorted(new['conditions'] or []):
                observations.append('verbatim_conditions_changed_requires_mapping_review')
            posted = new.get('results_first_posted_date')
            if posted:
                observations.append('results_posted_before_origin' if posted <= origin_date
                                    else 'results_first_posted_within_followup_window')
            else:
                observations.append('no_results_posting_date_in_snapshot_not_absence_of_external_results')
            if not new.get('last_update_posted_date'):
                observations.append('record_publication_bound_missing')
            if new.get('why_stopped'):
                observations.append('registry_stop_reason_available_requires_program_adjudication')
            for field in ('primary_completion_date', 'completion_date'):
                value, kind = new.get(field), normalized(new.get(field+'_type'))
                if value and kind == 'ACTUAL':
                    observations.append(field+('_reported_actual_by_endpoint' if value <= followup_date
                                               else '_actual_after_endpoint_requires_review'))
        result.append({'candidate_id':case['candidate_id'],'nct_id':old['nct_id'],
            'target_anchor':case['target_anchor'],'drug_anchor':case['drug_anchor'],
            'origin_mapping_decision':review['decision'],'origin_mapping_note':review['review_note'],
            'origin_status':old['overall_status'],'followup_status':new.get('overall_status') if new else None,
            'origin_phase':old['phase'],'followup_phase':new.get('phase') if new else None,
            'followup_registry_record':new,'observations':observations,
            'origin_date':origin_date,'administrative_observation_endpoint':followup_date,
            'therapeutic_success':None,'clinical_failure':None,'event_date':None,
            'event_publication_date':None,'censoring_date':None,
            'label_status':'unadjudicated_registry_states_do_not_define_program_events',
            'evaluator_only':True})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin-root',type=Path,required=True)
    parser.add_argument('--followup-root',type=Path,required=True)
    parser.add_argument('--pg-bin',type=Path,required=True)
    parser.add_argument('--port',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    out = args.output
    out.mkdir(exist_ok=False)
    def load(path): return json.loads(path.read_text(encoding='utf-8'))
    def write(name, value): (out/name).write_bytes((json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode())
    protocol = load(args.origin_root/'protocol.json')
    selected = load(args.origin_root/'selected.json')
    ids = [c['origin_record']['nct_id'] for c in selected]
    if not all(re.fullmatch('NCT[0-9]{8}',value) for value in ids):
        raise ValueError('Invalid NCT identifier')
    provenance = {'schema_version':1,'started_at_utc':datetime.now(timezone.utc).isoformat(),
        'origin_root':str(args.origin_root),'followup_root':str(args.followup_root),
        'origin_date':protocol['origin_date'],'followup_date':protocol['followup_date'],
        'selected_sha256':hashlib.sha256((args.origin_root/'selected.json').read_bytes()).hexdigest(),
        'protocol_sha256':hashlib.sha256((args.origin_root/'protocol.json').read_bytes()).hexdigest(),
        'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'selection_changed':False,'clinical_event_rule':'No clinical labels derived from registry status',
        'status':'started'}
    write('comparison-protocol.json',provenance)
    sql = """SELECT coalesce(json_agg(row_to_json(q)),'[]'::json) FROM (
SELECT s.nct_id,s.brief_title,s.study_type,s.phase,s.overall_status,s.why_stopped,
s.study_first_posted_date,s.last_update_posted_date,s.results_first_posted_date,
s.start_date,s.start_date_type,s.primary_completion_date,s.primary_completion_date_type,
s.completion_date,s.completion_date_type,
(SELECT json_agg(c.name ORDER BY c.name) FROM ctgov.conditions c WHERE c.nct_id=s.nct_id) AS conditions,
(SELECT json_agg(json_build_object('id',i.id,'name',i.name,'type',i.intervention_type,
'description',i.description) ORDER BY i.id) FROM ctgov.interventions i WHERE i.nct_id=s.nct_id) AS interventions,
(SELECT json_agg(json_build_object('id',d.id,'type',d.group_type,'title',d.title,'description',d.description)
ORDER BY d.id) FROM ctgov.design_groups d WHERE d.nct_id=s.nct_id) AS arms,
(SELECT json_agg(row_to_json(d) ORDER BY d.id) FROM ctgov.design_group_interventions d WHERE d.nct_id=s.nct_id) AS arm_intervention_links,
(SELECT json_agg(json_build_object('type',d.outcome_type,'measure',d.measure,'time_frame',d.time_frame)
ORDER BY d.id) FROM ctgov.design_outcomes d WHERE d.nct_id=s.nct_id) AS planned_endpoints
FROM ctgov.studies s WHERE s.nct_id IN ("""+','.join("'"+x+"'" for x in ids)+') ORDER BY s.nct_id) q;'
    (out/'followup-query.sql').write_bytes(sql.encode())
    env = os.environ.copy()
    env.update(PGHOST='127.0.0.1',PGPORT=args.port,PGUSER='aact_restore_admin',PGDATABASE='aact_snapshot',
        PGPASSWORD=(args.followup_root/'.local-postgres-secrets/password.txt').read_text(),
        PGOPTIONS='-c default_transaction_read_only=on')
    try:
        with (out/'followup-records.json').open('xb') as stdout,(out/'query.stderr.log').open('xb') as stderr:
            subprocess.run([str(args.pg_bin/'psql.exe'),'-XAtq','-v','ON_ERROR_STOP=1','-f',str(out/'followup-query.sql')],
                env=env,stdout=stdout,stderr=stderr,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        rows = compare(selected,load(out/'followup-records.json'),load(args.origin_root/'mapping-review.json'),
                       protocol['origin_date'],protocol['followup_date'])
        write('comparison.json',rows)
        summary = {'status':'registry_comparison_completed_program_labels_unadjudicated',
            'selected_trials':len(rows),'found_followup':sum(r['followup_registry_record'] is not None for r in rows),
            'followup_status_counts':dict(Counter(normalized(r['followup_status']) or 'MISSING' for r in rows)),
            'observations':dict(Counter(flag for r in rows for flag in r['observations'])),
            'clinical_labels_assigned':0,'independent_program_count':None,'power_estimate':None}
        write('summary.json',summary)
        esc=html.escape
        cards=[]
        for row in rows:
            new=row['followup_registry_record'] or {}
            cards.append('<article><h2>'+esc(row['candidate_id']+' · '+row['drug_anchor'])+'</h2><p>'+esc(row['nct_id'])+
                '</p><p><b>'+esc(row['origin_status'] or 'unknown')+' → '+esc(row['followup_status'] or 'missing')+
                '</b></p><p>'+esc(row['origin_mapping_note'])+'</p><p>Stop reason: '+esc(new.get('why_stopped') or 'not reported')+
                '</p><details><summary>Dated registry fields and qualifications</summary><pre>'+esc(json.dumps(new,indent=2,ensure_ascii=False))+
                '</pre><ul>'+''.join('<li>'+esc(x.replace('_',' '))+'</li>' for x in row['observations'])+'</ul></details></article>')
        page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>January 2023–2025 clinical follow-up</title><style>body{font:17px/1.5 system-ui;max-width:1000px;margin:35px auto;padding:20px;background:#f4f6f8;color:#182534}article{background:white;padding:20px;margin:16px 0;border:1px solid #ccd6df;border-radius:8px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}summary{cursor:pointer}h2{font-size:22px}</style><h1>Frozen trial follow-up: January 2023 → January 2025</h1><p>Registry observations only. Completed does not mean successful; stopped does not mean biological failure. All clinical event and censoring labels remain unadjudicated. Original mapping exclusions remain in force.</p>'+''.join(cards)+'</html>'
        (out/'Review.html').write_bytes(page.encode())
        provenance['status']='completed'
        provenance['source_sha256']=hashlib.sha256((out/'followup-records.json').read_bytes()).hexdigest()
        print(json.dumps(summary))
    except BaseException as exc:
        provenance.update(status='failed',error=repr(exc))
        raise
    finally:
        write('execution.json',provenance)


if __name__ == '__main__':
    main()
