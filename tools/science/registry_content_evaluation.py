"""Source-inclusive B0 follow-up verification and finite feasibility audit.

Registry-content observations never become clinical efficacy labels or predictors.
This evaluator opens follow-up only after reconstructing sealed origin membership.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from asof.journal import RunJournal, read_chain
from asof.serde import fingerprint, write_json
from tools.science.outcome_extract import check_pins
from tools.science.outcome_inputs import parse_jsonl
from tools.science.registry_content import appearance, classify_content
from tools.science.registry_content_transport import METADATA_SQL, startup_command
from tools.science.registry_content_workflow import (
    CODE, ROOT, load_pin, pin, require, validate_plan, verify_membership, verify_origin_run,
)


def commands(job, pg, folder):
    pg, restore = Path(pg), Path(job['restore_root'])
    return {
        'status-before': [str(pg / 'pg_ctl.exe'), '-D', str(restore / 'pgdata'), 'status'],
        'start': startup_command(pg, restore, folder, job['port']),
        'metadata': [str(pg / 'psql.exe'), '-XAtq', '-v', 'ON_ERROR_STOP=1', '-c', METADATA_SQL],
        'first': [str(pg / 'psql.exe'), '-XAtq', '-v', 'ON_ERROR_STOP=1', '-f', job['query']['path']],
        'repeat': [str(pg / 'psql.exe'), '-XAtq', '-v', 'ON_ERROR_STOP=1', '-f', job['query']['path']],
        'stop': [str(pg / 'pg_ctl.exe'), '-D', str(restore / 'pgdata'), '-m', 'fast', '-w', '-t', '45', 'stop'],
        'status-after': [str(pg / 'pg_ctl.exe'), '-D', str(restore / 'pgdata'), 'status'],
    }


def verify_followup(report_proof, membership_proof):
    membership = verify_membership(membership_proof)
    require(Path(report_proof['path']).name == 'report.json', 'Unexpected follow-up report name')
    root = Path(report_proof['path']).resolve().parent
    report = load_pin(report_proof)
    events = read_chain(root / 'journal.jsonl')
    require(events[-1]['event'] == 'build_completed' and
            dict(events[-1]['details']['report']) == report_proof, 'Follow-up terminal receipt differs')
    require(report.get('status') == 'source_bound_snapshot_reads_completed' and
            report.get('mode') == 'followup' and report.get('role') == 'evaluation_only' and
            report.get('clinical_activation') is False and report.get('clinical_labels_assigned') == 0 and
            report.get('provider_spend_usd') == 0 and report.get('model_calls') == 0,
            'Wrong follow-up status/scope/accounting')
    plan = load_pin(report['plan'])
    require(plan.get('mode') == 'followup' and plan.get('membership') == membership_proof and
            plan.get('nct_ids') == sorted(membership['nct_ids']) and
            [j['snapshot_date'] for j in plan['jobs']] == ['2026-01-01', '2026-04-01'],
            'Follow-up source/membership differs')
    validate_plan(plan, Path(report['plan']['path']))
    for key, name in [('effective_plan', 'effective-plan.json'), ('executed_code_proofs', 'executed-code-proofs.json')]:
        require(Path(report[key]['path']).resolve() == root / name, 'Foreign follow-up receipt: ' + key)
    require(load_pin(report['effective_plan']) == plan, 'Effective follow-up plan differs')
    archives = load_pin(report['executed_code_proofs'])
    require(len(archives) == len(plan['code']), 'Incomplete follow-up code archives')
    for archived, original in zip(archives, plan['code']):
        source = Path(original['path']).resolve()
        require(source.is_relative_to(ROOT) and archived['source'] == original and
                Path(archived['copy']['path']).resolve() == root / 'executed-code' / source.relative_to(ROOT),
                'Follow-up code archive identity differs')
        check_pins([archived['copy']])
        require(archived['copy']['sha256'] == original['sha256'] and
                archived['copy']['bytes'] == original['bytes'], 'Follow-up code bytes differ')
    require(len(report['results']) == len(plan['jobs']), 'Follow-up result coverage differs')
    expected_command_order = []
    frames = {}
    for result, job in zip(report['results'], plan['jobs']):
        when = job['snapshot_date']
        folder = root / when
        require(result['snapshot_date'] == when and result.get('repeat_identical') is True and
                result.get('request_sha256') == job['query']['request']['contract_sha256'],
                'Follow-up result request differs')
        for key, name in [('first', 'first.stdout.log'), ('repeat', 'repeat.stdout.log'),
                          ('state_proposals', 'state-proposals.json'), ('lifecycle', 'lifecycle.json'),
                          ('metadata_file', 'metadata.stdout.log')]:
            require(Path(result[key]['path']).resolve() == folder / name, 'Foreign follow-up output: ' + key)
            check_pins([result[key]])
        require(Path(result['first']['path']).read_bytes() == Path(result['repeat']['path']).read_bytes(),
                'Follow-up repeated source bytes differ')
        require(result['first']['bytes'] <= job['query']['request']['max_output_bytes'], 'Oversized follow-up source')
        lifecycle = load_pin(result['lifecycle'])
        require(all(lifecycle.get(k) is True for k in ('startup_attempted', 'server_stopped', 'port_closed')) and
                lifecycle.get('port') == job['port'] and lifecycle.get('automatic_retry') is False and
                lifecycle.get('primary_error_class') is None and lifecycle.get('cleanup_error_class') is None,
                'Incomplete follow-up server lifecycle')
        meta = load_pin(result['metadata_file'])
        require(meta == result['metadata'] and meta.get('database') == 'aact_snapshot' and
                type(meta.get('studies')) is int and meta['studies'] == job['expected_studies'] and
                Path(meta.get('directory', '')).resolve() == Path(job['restore_root']) / 'pgdata' and
                meta.get('port') == str(job['port']) and meta.get('read_only') == 'on', 'Follow-up metadata differs')
        for name, arguments in commands(job, plan['pg_bin'], folder).items():
            expected_command_order.extend([(when, name, 'started'), (when, name, 'finished')])
            logged = [e['details'] for e in events if e['event'] == 'build_progress' and
                      e['details'].get('stage') == when and e['details'].get('command') == name]
            require(len(logged) == 2 and logged[0].get('status') == 'started' and
                    logged[1].get('status') == 'finished' and list(logged[0].get('arguments', [])) == arguments and
                    logged[0].get('timeout_seconds') == (330 if name in ('first', 'repeat') else 90) and
                    logged[1].get('returncode') == (3 if name.startswith('status-') else 0),
                    'Follow-up command differs: ' + when + '/' + name)
            for channel in ('stdout', 'stderr'):
                path = folder / (name + '.' + channel + '.log')
                require(path.is_file() and type(logged[1].get(channel + '_bytes')) is int and
                        logged[1][channel + '_bytes'] == path.stat().st_size, 'Follow-up command byte count differs')
        rows = parse_jsonl(Path(result['first']['path']).read_text(encoding='utf-8'))
        states = classify_content(rows, job['query']['request'])
        require(load_pin(result['state_proposals']) == states, 'Follow-up states differ from source rows')
        frames[when] = {'states': states, 'source': result['first'], 'result': result, 'rows': rows}
    actual_order = [(e['details'].get('stage'), e['details'].get('command'), e['details'].get('status'))
                    for e in events if e['event'] == 'build_progress' and e['details'].get('command') is not None]
    require(actual_order == expected_command_order, 'Follow-up attempt count/order differs')
    return frames, report


def compare_states(members, origin_states, by_snapshot):
    require(isinstance(members, list) and 0 < len(members) <= 32 and len(set(members)) == len(members),
            'Invalid selected-member denominator')
    require(set(by_snapshot) == {'2026-01-01', '2026-04-01'}, 'Missing or substituted follow-up snapshot')
    origin = {r['nct_id']: r for r in origin_states['records']}
    require(len(origin) == len(origin_states['records']), 'Duplicate origin state')
    views = {}
    rows = []
    for when in ('2026-01-01', '2026-04-01'):
        records = by_snapshot[when]['records']
        current = {r['nct_id']: r for r in records}
        require(len(current) == len(records) and set(current) == set(members), 'Follow-up member coverage differs')
        counts = Counter()
        reasons = Counter()
        for nct in members:
            require(nct in origin and origin[nct]['state'] == 'absent_in_snapshot', 'Selected member not origin-absent')
            contrast = appearance(origin[nct], current[nct], endpoint_snapshot=when)
            counts[{1: 'appearance', 0: 'absent', None: 'unknown'}[contrast['operational_value']]] += 1
            reasons.update(current[nct]['reasons'])
            rows.append({'nct_id': nct, 'snapshot_date': when, 'origin_state': origin[nct],
                         'endpoint_state': current[nct], 'contrast': contrast})
        known = counts['appearance'] + counts['absent']
        views[when] = {'selected_denominator': len(members), **{k: counts[k] for k in ('appearance', 'absent', 'unknown')},
                       'observable_fraction': known / len(members), 'unknown_reasons': dict(reasons)}
    primary = views['2026-01-01']
    coverage_pass = primary['observable_fraction'] >= 0.9
    both_classes = primary['appearance'] > 0 and primary['absent'] > 0
    decision = ('larger_feasibility_design_only' if coverage_pass and both_classes
                else 'stop_operational_prediction_expansion')
    return {'views': views, 'contrasts': rows, 'decision': decision,
            'coverage_threshold': 0.9, 'coverage_pass': coverage_pass, 'both_classes_observed': both_classes,
            'clinical_activation': False, 'training_allowed': False, 'probabilities': None,
            'interpretation': 'Purposive exposed snapshot-content audit; no clinical outcome or population incidence inference.'}


def audit_native_rows(members, frames):
    audit = []
    for when, frame in frames.items():
        source = frame['source']
        check_pins([source])
        indexed = {}
        offset = 0
        with Path(source['path']).open('rb') as stream:
            for line_number, raw in enumerate(stream, 1):
                record = json.loads(raw)
                nct = record['study']['nct_id']
                require(nct not in indexed, 'Duplicate native source envelope')
                indexed[nct] = (line_number, offset, len(raw), record)
                offset += len(raw)
        states = {r['nct_id']: r for r in frame['states']['records']}
        for nct in members:
            state = states[nct]
            located = indexed.get(nct)
            if located is None:
                require(state['state'] == 'unknown' and 'missing_nct_record' in state['reasons'],
                        'Missing source row cannot support a binary state')
                audit.append({'snapshot_date': when, 'nct_id': nct, 'state': state['state'],
                              'source': source, 'native_locator': None, 'reason': 'missing_nct_record'})
                continue
            line, offset, length, record = located
            require(fingerprint(record) == state['source_record_sha256'], 'State/source fingerprint differs')
            audit.append({'snapshot_date': when, 'nct_id': nct, 'state': state['state'], 'source': source,
                          'native_locator': {'line_1based': line, 'byte_offset': offset, 'byte_length': length},
                          'record_sha256': state['source_record_sha256'], 'table_counts': record['table_counts'],
                          'native_row_ids': {t: [r['id'] for r in record[t]] if record[t] is not None else None
                                             for t in ('outcomes', 'result_groups', 'outcome_measurements')},
                          'unknown_reasons': state['reasons']})
    return audit


def dependence_diagnostics(members, candidates):
    """Describe exact origin-key overlap; never estimate independent sample size."""
    indexed = {c['nct_id']: c for c in candidates}
    require(len(indexed) == len(candidates) and set(members) <= set(indexed),
            'Dependency context must resolve selected origin members')
    parent = {m: m for m in members}
    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value
    dimensions = {}
    for kind in ('historical_drug', 'target', 'sponsor_verbatim', 'product_verbatim'):
        keys = {}
        missing = 0
        for member in members:
            values = indexed[member]['program']['dependence_keys'].get(kind, [])
            require(isinstance(values, list) and all(isinstance(v, str) for v in values),
                    'Malformed origin dependency keys')
            if not values:
                missing += 1
            for value in set(values):
                keys.setdefault(value, []).append(member)
        for group in keys.values():
            for member in group[1:]:
                parent[find(member)] = find(group[0])
        dimensions[kind] = {'distinct_recorded_keys': len(keys),
                            'keys_shared_by_multiple_trials': sum(len(v) > 1 for v in keys.values()),
                            'members_with_missing_keys': missing}
    return {'selected_trials': len(members), 'dimensions': dimensions,
            'observed_joint_key_components': len({find(m) for m in members}),
            'effective_sample_size': None,
            'interpretation': 'Exact origin annotations flag possible dependence; aliases, shared biology and unrecorded links may be missed. Not independent events, population sampling or validated effective sample size.'}


def evaluate(membership_proof, followup_proof, output):
    output = Path(output).resolve()
    journal = RunJournal(output, kind='build')
    try:
        executing = [pin(ROOT / name) for name in (*CODE, 'tools/science/registry_content_evaluation.py')]
        copies = []
        for proof in executing:
            source = Path(proof['path'])
            target = output / 'executed-code' / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(source.read_bytes())
            require(pin(target)['sha256'] == proof['sha256'], 'Evaluator code changed during archival')
            copies.append({'source': proof, 'copy': pin(target)})
        write_json(output / 'executed-code-proofs.json', copies)
        membership = verify_membership(membership_proof)
        _, origin_plan, origin_states = verify_origin_run(membership['origin_run'])
        origin_report = load_pin(membership['origin_report'])
        frames, followup_report = verify_followup(followup_proof, membership_proof)
        compared = compare_states(membership['nct_ids'], origin_states,
                                  {when: frame['states'] for when, frame in frames.items()})
        origin_result = origin_report['results'][0]
        frames['2025-01-01'] = {'source': origin_result['first'], 'states': origin_states}
        audit = audit_native_rows(membership['nct_ids'], frames)
        candidate_frame = load_pin(membership['candidate_freeze'])
        dependence = dependence_diagnostics(membership['nct_ids'], candidate_frame['candidates'])
        write_json(output / 'dependence-diagnostics.json', dependence)
        write_json(output / 'native-row-audit.json', audit)
        write_json(output / 'contrasts.json', compared)
        results = origin_report['results'] + followup_report['results']
        resources = {'extract_elapsed_seconds_including_source_checks': origin_report['elapsed_seconds'] + followup_report['elapsed_seconds'],
                     'source_elapsed_seconds': {r['snapshot_date']: r['source_elapsed_seconds'] for r in results},
                     'first_read_bytes': sum(r['first']['bytes'] for r in results),
                     'repeat_read_bytes': sum(r['repeat']['bytes'] for r in results),
                     'peak_python_parent_bytes': max(origin_report['peak_parent_memory_bytes'], followup_report['peak_parent_memory_bytes']),
                     'postgres_peak_bytes': None, 'postgres_peak_reason': 'Not instrumented; parent is not total system memory.',
                     'provider_spend_usd': 0}
        phase = Path(membership['origin_run']).parent
        resources['phase_workspace_bytes_before_final_report'] = sum(p.stat().st_size for p in phase.rglob('*') if p.is_file())
        resources['workspace_scope'] = str(phase)
        resources['workspace_reservation_bytes'] = 5 * 1024 ** 3
        require(resources['phase_workspace_bytes_before_final_report'] < resources['workspace_reservation_bytes'],
                'B0 phase workspace exceeds reservation')
        write_json(output / 'resources.json', resources)
        check_pins(executing + [record['copy'] for record in copies])
        report = {'schema_version': 1, 'status': 'source_inclusive_B0_feasibility_audit_complete',
                  'created_at_utc': datetime.now(timezone.utc).isoformat(), 'membership': membership_proof,
                  'followup_report': followup_proof, 'selected_members': len(membership['nct_ids']),
                  'source_state_audits': len(audit), 'located_native_envelopes': sum(a['native_locator'] is not None for a in audit),
                  'contrasts': pin(output / 'contrasts.json'), 'native_row_audit': pin(output / 'native-row-audit.json'),
                  'resources': pin(output / 'resources.json'), 'decision': compared['decision'],
                  'dependence_diagnostics': pin(output / 'dependence-diagnostics.json'),
                  'executed_code_proofs': pin(output / 'executed-code-proofs.json'),
                  'views': compared['views'], 'clinical_activation': False, 'training_allowed': False,
                  'all_project_tasks_complete': False}
        write_json(output / 'report.json', report)
        journal.append('build_completed', report=pin(output / 'report.json'))
        return report
    except BaseException as exc:
        journal.fail(exc, 'source_inclusive_B0_audit')
        raise
    finally:
        journal.close()
