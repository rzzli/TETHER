"""B0 evaluator-only snapshot content contracts. No database or network dispatch.

These functions validate extraction proposals, not transport provenance. A source-
inclusive runner and sealed origin membership are required before real execution.
Existing twelve-member clinical extraction contracts are deliberately independent.
"""
from __future__ import annotations

import copy
from datetime import date
import re

from tether_engine.serde import ContractError, fingerprint
from tools.science.outcome_inputs import PRELUDE, _literal

ENDPOINT = 'registry_outcome_measurement_appearance_v1'
SNAPSHOTS = ('2025-01-01', '2026-01-01', '2026-04-01')
FIELDS = {
    'studies': ('nct_id', 'last_update_posted_date', 'last_update_posted_date_type',
                'results_first_posted_date', 'results_first_posted_date_type'),
    'outcomes': ('id', 'nct_id'),
    'result_groups': ('id', 'nct_id', 'outcome_id', 'ctgov_group_code'),
    'outcome_measurements': ('id', 'nct_id', 'outcome_id', 'result_group_id', 'ctgov_group_code'),
}
TABLES = tuple(t for t in FIELDS if t != 'studies')
STATES = ('present', 'absent_in_snapshot', 'unknown')


def require(condition, message):
    if not condition:
        raise ContractError(message)


def seal(value):
    result = copy.deepcopy(value)
    result['contract_sha256'] = fingerprint(result)
    return result


def content_query(nct_ids, snapshot_date, schema, *, max_rows_per_trial=100000):
    """Produce a bounded, unbound SQL contract; never authorize its execution.

    Follow-up contracts are templates until a separate source-inclusive runner
    verifies origin membership. No self-hash is an execution authorization.
    """
    require(snapshot_date in SNAPSHOTS, 'Unapproved B0 snapshot')
    bound = 128 if snapshot_date == SNAPSHOTS[0] else 32
    require(isinstance(nct_ids, (list, tuple)) and 0 < len(nct_ids) <= bound,
            'B0 membership exceeds stage cap or is empty')
    require(all(isinstance(n, str) and re.fullmatch(r'NCT[0-9]{8}', n) for n in nct_ids),
            'Invalid NCT identifier')
    require(len(set(nct_ids)) == len(nct_ids), 'Duplicate NCT identifier')
    require(type(max_rows_per_trial) is int and 1 <= max_rows_per_trial <= 100000,
            'Invalid row cap')
    require(isinstance(schema, dict), 'Schema must be a mapping')
    for columns in schema.values():
        require(isinstance(columns, list) and all(isinstance(c, str) for c in columns)
                and len(columns) == len(set(columns)), 'Malformed source columns')
    require('nct_id' in schema.get('studies', []), 'Study identity missing from schema')
    projection = {t: [c for c in cols if c in schema.get(t, [])] for t, cols in FIELDS.items()}
    missing = {t: [c for c in cols if c not in projection[t]] for t, cols in FIELDS.items()}
    usable = {t: not missing[t] for t in TABLES}

    def object_sql(columns, alias):
        return 'json_build_object(' + ','.join(_literal(c) + ',' + alias + '.' + c
                                               for c in columns) + ')'

    parts = ["'study'," + object_sql(projection['studies'], 's')]
    counts = []
    count_parts = []
    for table in TABLES:
        count = '(SELECT count(*) FROM ctgov.' + table + ' t WHERE t.nct_id=s.nct_id)'
        if usable[table]:
            counts.append(count)
            parts.append(_literal(table) + ',coalesce((SELECT json_agg(' +
                         object_sql(projection[table], 't') + ' ORDER BY t.id) FROM ctgov.' +
                         table + " t WHERE t.nct_id=s.nct_id),'[]'::json)")
            count_parts.extend([_literal(table), count])
        else:
            parts.append(_literal(table) + ",null")
            count_parts.extend([_literal(table), 'null'])
    parts.append("'table_counts',json_build_object(" + ','.join(count_parts) + ')')
    total = '(' + ('+'.join(counts) or '0') + ')'
    sql = (PRELUDE + 'SELECT CASE WHEN ' + total + '>' + str(max_rows_per_trial) +
           " THEN json_build_object('overflow',true,'nct_id',s.nct_id) ELSE json_build_object(" +
           ','.join(parts) + ') END FROM ctgov.studies s WHERE s.nct_id IN (' +
           ','.join(_literal(n) for n in sorted(nct_ids)) + ') ORDER BY s.nct_id;\nROLLBACK;')
    return seal({'schema_version': 1, 'kind': 'b0_content_query_template',
                 'endpoint_id': ENDPOINT, 'role': 'evaluation_only',
                 'snapshot_date': snapshot_date, 'nct_ids': sorted(nct_ids),
                 'source_schema': copy.deepcopy(schema), 'projection': projection,
                 'missing_required_columns': missing, 'usable_tables': usable,
                 'max_rows_per_trial': max_rows_per_trial, 'max_output_bytes': 128 * 1024 * 1024,
                 'sql': sql, 'execution_authorized': False,
                 'requires_source_inclusive_runner': True, 'clinical_activation': False})


def regenerate_query(request):
    require(isinstance(request, dict), 'Invalid B0 request')
    try:
        rebuilt = content_query(request['nct_ids'], request['snapshot_date'],
                                request['source_schema'],
                                max_rows_per_trial=request['max_rows_per_trial'])
    except KeyError as exc:
        raise ContractError('Incomplete B0 request') from exc
    require(rebuilt == request, 'B0 request differs from deterministic generator')
    return rebuilt


def _iso_day(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def classify_content(rows, request):
    """Validate a complete extraction envelope and propose source states.

    Structural/projection/count errors fail the batch. Source inconsistencies
    retain a record-level unknown. Missing returned NCTs are explicitly unknown.
    External receipt/byte/source proofs are intentionally not claimed here.
    """
    regenerate_query(request)
    require(isinstance(rows, list) and len(rows) <= len(request['nct_ids']), 'Envelope cap exceeded')
    by_id = {}
    seen_order = []
    for record in rows:
        require(isinstance(record, dict) and not record.get('overflow'), 'B0 overflow or invalid record')
        require(set(record) == {'study', 'table_counts', *TABLES}, 'Unexpected B0 envelope fields')
        study = record['study']
        require(isinstance(study, dict) and set(study) == set(request['projection']['studies']),
                'Study projection differs')
        nct = study['nct_id']
        require(nct in request['nct_ids'] and nct not in by_id, 'Unrequested or duplicate NCT envelope')
        require(isinstance(record['table_counts'], dict) and set(record['table_counts']) == set(TABLES),
                'Table count coverage differs')
        reasons = ['missing_required_columns:' + t for t, cols in
                   request['missing_required_columns'].items() if cols]
        total = 0
        keys = {}
        for table in TABLES:
            children, count = record[table], record['table_counts'][table]
            if not request['usable_tables'][table]:
                require(children is None and count is None, 'Unavailable table misrepresented as queried')
                keys[table] = {}
                continue
            require(isinstance(children, list) and type(count) is int and count == len(children),
                    'Result count mismatch or truncated rows')
            total += count
            ids = []
            for child in children:
                require(isinstance(child, dict) and set(child) == set(request['projection'][table]),
                        'Unprojected result fields')
                require(child['nct_id'] == nct and type(child['id']) is int and child['id'] > 0,
                        'Cross-trial or malformed child identity')
                ids.append(child['id'])
            require(ids == sorted(ids), 'Lost deterministic child order')
            if len(ids) != len(set(ids)):
                reasons.append('duplicate_source_key:' + table)
            keys[table] = {c['id']: c for c in children}
        require(total <= request['max_rows_per_trial'], 'B0 row cap exceeded')

        if all(request['usable_tables'].values()):
            for group in record['result_groups']:
                outcome = group['outcome_id']
                if outcome is not None and (type(outcome) is not int or outcome not in keys['outcomes']):
                    reasons.append('orphan_group_outcome')
            for child in record['outcome_measurements']:
                outcome, group_id = child['outcome_id'], child['result_group_id']
                if (type(outcome) is not int or outcome not in keys['outcomes'] or
                        type(group_id) is not int or group_id not in keys['result_groups']):
                    reasons.append('orphan_measurement')
                    continue
                group = keys['result_groups'][group_id]
                if group['outcome_id'] is not None and group['outcome_id'] != outcome:
                    reasons.append('measurement_group_outcome_conflict')
                if (child['ctgov_group_code'] is not None and group['ctgov_group_code'] is not None and
                        child['ctgov_group_code'] != group['ctgov_group_code']):
                    reasons.append('measurement_group_code_conflict')

        latest = study.get('last_update_posted_date')
        posted = study.get('results_first_posted_date')
        if not _iso_day(latest) or study.get('last_update_posted_date_type') != 'ACTUAL':
            reasons.append('unqualified_record_version_date')
        elif latest > request['snapshot_date']:
            reasons.append('record_version_after_snapshot')
        if posted is not None:
            if (not _iso_day(posted) or study.get('results_first_posted_date_type') != 'ACTUAL' or
                    posted > request['snapshot_date'] or (_iso_day(latest) and posted > latest)):
                reasons.append('unqualified_results_posting_date')
            if request['usable_tables']['outcome_measurements'] and not record['outcome_measurements']:
                reasons.append('posting_date_without_measurements')
        elif study.get('results_first_posted_date_type') is not None:
            reasons.append('posting_date_type_without_date')
        if request['usable_tables']['outcome_measurements'] and record['outcome_measurements'] and posted is None:
            reasons.append('measurements_without_posting_date')
        state = ('unknown' if reasons else
                 'present' if record['outcome_measurements'] else 'absent_in_snapshot')
        by_id[nct] = {'nct_id': nct, 'snapshot_date': request['snapshot_date'], 'state': state,
                      'reasons': sorted(set(reasons)), 'source_record_sha256': fingerprint(record),
                      'table_counts': copy.deepcopy(record['table_counts'])}
        seen_order.append(nct)
    require(seen_order == sorted(seen_order), 'Lost deterministic envelope order')
    for nct in request['nct_ids']:
        if nct not in by_id:
            by_id[nct] = {'nct_id': nct, 'snapshot_date': request['snapshot_date'], 'state': 'unknown',
                          'reasons': ['missing_nct_record'], 'source_record_sha256': None,
                          'table_counts': None}
    return seal({'endpoint_id': ENDPOINT, 'role': 'evaluation_only',
                 'snapshot_date': request['snapshot_date'], 'request_sha256': request['contract_sha256'],
                 'records': [by_id[n] for n in request['nct_ids']],
                 'transport_provenance_verified': False, 'clinical_activation': False,
                 'execution_authorized': False})


def appearance(origin_state, endpoint_state, *, endpoint_snapshot):
    """Compute only this registry-state contrast; no clinical efficacy label."""
    require(endpoint_snapshot in SNAPSHOTS[1:], 'Invalid endpoint snapshot')
    for state, snapshot in ((origin_state, SNAPSHOTS[0]), (endpoint_state, endpoint_snapshot)):
        require(isinstance(state, dict) and state.get('snapshot_date') == snapshot and
                state.get('state') in STATES, 'State snapshot or type differs')
    require(origin_state.get('nct_id') == endpoint_state.get('nct_id') and
            isinstance(origin_state.get('nct_id'), str) and
            re.fullmatch(r'NCT[0-9]{8}', origin_state['nct_id']), 'Transition NCT mismatch')
    eligible = origin_state['state'] == 'absent_in_snapshot'
    value = (int(endpoint_state['state'] == 'present') if eligible and
             endpoint_state['state'] != 'unknown' else None)
    return {'endpoint_id': ENDPOINT, 'nct_id': origin_state['nct_id'],
            'view': 'january_primary' if endpoint_snapshot == SNAPSHOTS[1] else 'april_sensitivity',
            'origin_eligible': eligible, 'operational_value': value,
            'clinical_label': None, 'probability': None, 'features': {},
            'interpretation': 'Snapshot-defined content appearance; not clinical efficacy or earliest public disclosure.',
            'transport_provenance_verified': False}
