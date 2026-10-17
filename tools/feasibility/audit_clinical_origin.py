"""Extract a reproducible evaluator-only origin sample from an isolated AACT restore.

No success/failure labels are derived. Follow-up information never enters selection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone


def key(value):
    return re.sub(r'[^a-z0-9]', '', value.lower())


def select(rows, protocol):
    aliases = {key(term): (target, term) for target, terms in
               protocol['seed_targets_and_drug_terms'].items() for term in terms}
    groups = {target: [] for target in protocol['seed_targets_and_drug_terms']}
    excluded = []
    for row in rows:
        status = re.sub(r'[^A-Z0-9]+', '_', (row['overall_status'] or '').upper()).strip('_')
        reasons = []
        if (row['study_type'] or '').lower() != 'interventional':
            reasons.append('not_interventional')
        if row['phase'] not in protocol['eligible_phases']:
            reasons.append('phase_outside_protocol')
        if status not in protocol['eligible_origin_states']:
            reasons.append('not_active_at_origin')
        if not row['study_first_posted_date'] or row['study_first_posted_date'] > protocol['origin_date']:
            reasons.append('missing_or_late_first_posted')
        if row.get('last_update_posted_date') and row['last_update_posted_date'] > protocol['origin_date']:
            reasons.append('future_origin_record_update')
        if not row['conditions']:
            reasons.append('missing_indication')
        if reasons:
            excluded.append({'nct_id': row['nct_id'], 'reasons': reasons})
            continue
        matches = set()
        for intervention in row['interventions']:
            for name in [intervention['name'], *(intervention.get('aliases') or [])]:
                if key(name) in aliases:
                    matches.add(aliases[key(name)])
        for target, anchor in sorted(matches):
            groups[target].append({'target_anchor': target, 'drug_anchor': anchor,
                'origin_record': row, 'selection_hash': hashlib.sha256(row['nct_id'].encode()).hexdigest()})
    for values in groups.values():
        values.sort(key=lambda r: (r['selection_hash'], r['drug_anchor']))
    chosen, programs, ncts = [], set(), set()
    while len(chosen) < protocol['requested_programs']:
        progressed = False
        for target, values in groups.items():
            while values:
                candidate = values.pop(0)
                row = candidate['origin_record']
                program = (candidate['drug_anchor'], tuple(sorted(row['conditions'])))
                if program in programs or row['nct_id'] in ncts:
                    continue
                programs.add(program)
                ncts.add(row['nct_id'])
                candidate.update(candidate_id=f"P{len(chosen)+1:02d}",
                    program_identity_status='provisional_trial_representative',
                    target_mapping_status='provisional_anchor',
                    indication_mapping_status='verbatim_registry_conditions_not_ontology_adjudicated',
                    therapeutic_success=None, clinical_failure=None, event_date=None,
                    event_publication_date=None, censoring_date=None,
                    label_status='unresolved_requires_dated_followup_and_adjudication')
                chosen.append(candidate)
                progressed = True
                break
            if len(chosen) == protocol['requested_programs']:
                break
        if not progressed:
            break
    return chosen, excluded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--restore-root', type=Path, required=True)
    parser.add_argument('--pg-bin', type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    protocol = json.loads((root/'protocol.json').read_text())
    # Refuse a second extraction into an existing run.
    with (root/'extraction-reservation.json').open('x', encoding='utf-8') as stream:
        json.dump({'started_at_utc': datetime.now(timezone.utc).isoformat()}, stream)
    terms = sorted({key(v) for values in protocol['seed_targets_and_drug_terms'].values() for v in values})
    assert all(re.fullmatch('[a-z0-9]+', term) for term in terms)
    names = ','.join("'"+term+"'" for term in terms)
    sql = f"""SELECT coalesce(json_agg(row_to_json(q)), '[]'::json) FROM (
SELECT s.nct_id,s.brief_title,s.study_type,s.phase,s.overall_status,
s.study_first_posted_date,s.last_update_posted_date,s.start_date,s.start_date_type,
s.primary_completion_date,s.primary_completion_date_type,s.completion_date,s.completion_date_type,
(SELECT json_agg(c.name ORDER BY c.name) FROM ctgov.conditions c WHERE c.nct_id=s.nct_id) AS conditions,
(SELECT json_agg(json_build_object('id',i.id,'type',i.intervention_type,'name',i.name,
'description',i.description,'aliases',(SELECT json_agg(o.name ORDER BY o.name)
FROM ctgov.intervention_other_names o WHERE o.intervention_id=i.id)) ORDER BY i.id)
FROM ctgov.interventions i WHERE i.nct_id=s.nct_id) AS interventions,
(SELECT json_agg(json_build_object('name',p.name,'lead_or_collaborator',p.lead_or_collaborator)
ORDER BY p.id) FROM ctgov.sponsors p WHERE p.nct_id=s.nct_id) AS sponsors,
(SELECT json_agg(json_build_object('type',d.outcome_type,'measure',d.measure,'time_frame',d.time_frame)
ORDER BY d.id) FROM ctgov.design_outcomes d WHERE d.nct_id=s.nct_id) AS planned_endpoints
FROM ctgov.studies s WHERE EXISTS (SELECT 1 FROM ctgov.interventions i
WHERE i.nct_id=s.nct_id AND (regexp_replace(lower(i.name),'[^a-z0-9]','','g') IN ({names})
OR EXISTS (SELECT 1 FROM ctgov.intervention_other_names o WHERE o.intervention_id=i.id
AND regexp_replace(lower(o.name),'[^a-z0-9]','','g') IN ({names})))) ORDER BY s.nct_id) q;"""
    (root/'origin-query.sql').write_text(sql, encoding='utf-8')
    env = os.environ.copy()
    env.update(PGHOST='127.0.0.1', PGPORT='55432', PGUSER='aact_restore_admin',
        PGDATABASE='aact_snapshot', PGPASSWORD=(args.restore_root/'.local-postgres-secrets/password.txt').read_text(),
        PGOPTIONS='-c default_transaction_read_only=on')
    with (root/'origin-records.json').open('xb') as out, (root/'query.stderr.log').open('xb') as err:
        result = subprocess.run([str(args.pg_bin/'psql.exe'), '-XAtq', '-v', 'ON_ERROR_STOP=1',
            '-f', str(root/'origin-query.sql')], env=env, stdout=out, stderr=err,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:
        raise RuntimeError('Origin query failed; retained stderr and partial output')
    rows = json.loads((root/'origin-records.json').read_text(encoding='utf-8'))
    chosen, excluded = select(rows, protocol)
    for name, value in [('selected.json',chosen),('excluded.json',excluded)]:
        (root/name).write_bytes((json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode())
    report = {'matched_source_trials':len(rows),'selected_trial_representatives':len(chosen),
        'excluded_trials':len(excluded),'source_sha256':hashlib.sha256((root/'origin-records.json').read_bytes()).hexdigest(),
        'protocol_sha256':hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest(),
        'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'role':'evaluation_only','clinical_labels_assigned':0}
    (root/'extraction-report.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps(report))


if __name__ == '__main__':
    main()
