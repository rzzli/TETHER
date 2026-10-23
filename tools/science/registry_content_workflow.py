"""Source-bound B0 preparation/execution; origin membership precedes follow-up.

This is a separate entry point. It never relaxes the legacy twelve-member runner.
Only frozen local source identities and deterministic SQL contracts are accepted.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from asof.journal import RunJournal, read_chain
from asof.serde import ContractError, fingerprint, sha256_file, write_json
from tools.science.outcome_extract import (APPROVED_BASE, APPROVED_RESTORES,
                                           check_pins)
from tools.science.outcome_inputs import parse_jsonl, schema_from_audit
from tools.science.reference_panel import read_bound_json
from tools.science.registry_content import classify_content, content_query

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / 'planning/protocols/registry-content-feasibility-v0.1.json'
POLICY_SHA = 'a610586389c92f139bfa9714e0789c562f87a5d4012fdc1b409fbc7299dc75a6'
MANIFEST = ROOT / 'data/benchmark/labels/registry-content-20261022/contracts-v1/source-manifest.json'
MANIFEST_SHA = 'ba1833116d4306ebeac5fd796e81b22943c1e72285f055d27c24b14f21d2c2b9'
APPROVED_RAW = Path('E:/projects_data/drug_target_agents_data/raw/aact_snapshots')
CODE = ('tools/science/registry_content_workflow.py', 'tools/science/registry_content_transport.py',
        'tools/science/registry_content.py', 'tools/science/outcome_extract.py',
        'tools/science/outcome_inputs.py', 'tools/science/origin_maturity.py',
        'tools/science/origin_review.py', 'tools/science/origin_programs.py',
        'tools/science/ascertainment_policy.py', 'tools/science/reference_panel.py',
        'src/asof/serde.py', 'src/asof/journal.py')


def require(condition, message):
    if not condition:
        raise ContractError(message)


def pin(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': sha256_file(path), 'bytes': path.stat().st_size}


def peak_parent_memory():
    """Measure this Python process only; PostgreSQL subprocess memory is separate."""
    import os
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
                (key, ctypes.c_size_t) for key in ('PeakWorkingSetSize', 'WorkingSetSize',
                'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        info = ctypes.WinDLL('psapi', use_last_error=True).GetProcessMemoryInfo
        info.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        info.restype = wintypes.BOOL
        if not info(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(counters.PeakWorkingSetSize)
    import resource
    import sys
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024))


def load_pin(proof):
    value, _ = read_bound_json(Path(proof['path']), proof['sha256'])
    require(Path(proof['path']).stat().st_size == proof['bytes'], 'Source size differs')
    return value


def origin_context():
    """Rebuild the old origin-only candidate lineage, not follow-up outcomes."""
    policy, _ = read_bound_json(POLICY, POLICY_SHA)
    manifest, _ = read_bound_json(MANIFEST, MANIFEST_SHA)
    require(manifest['policy'] == pin(POLICY), 'Schema manifest policy differs')
    candidate = load_pin(manifest['candidate_freeze'])
    require(manifest['candidate_freeze']['sha256'] ==
            policy['selection']['candidate_source_expected_sha256'], 'Candidate source differs')
    prior = load_pin(manifest['prior_request_plans'][0])
    # Reuse the complete original-source and deterministic candidate admission,
    # without using its twelve-case maturity rule for the new B0 endpoint.
    from tools.science.origin_maturity import validate_origin_binding
    check_pins(prior['parents'])
    validate_origin_binding(prior)
    require(candidate['candidates'] and len(candidate['candidates']) == 128 and
            candidate['followup_used_for_selection'] is False, 'Wrong candidate frame')
    ids = [c['nct_id'] for c in candidate['candidates']]
    require(len(set(ids)) == 128 and sorted(ids) == prior['nct_ids'], 'Candidate order/frame differs')
    excluded = set()
    for proof in manifest['excluded_pack_pins']:
        pack = load_pin(proof)
        check_pins(pack['files'] + pack.get('direct_parents', []) + pack.get('ancestor_pins', []))
        members = []
        for packet in pack['files']:
            if Path(packet['path']).parent.name == 'packets':
                members.append(load_pin(packet)['origin_scope']['nct_id'])
        require(len(members) == len(set(members)) == 12, 'Exclusion pack membership differs')
        excluded.update(members)
    return policy, manifest, prior, candidate, excluded


def source_job(manifest, snapshot, nct_ids, query_path):
    """Verify original archive/dump/TOC/schema and approved local source identity."""
    index = 0 if snapshot == '2025-01-01' else 1
    prior = load_pin(manifest['prior_request_plans'][index])
    job = next(j for j in prior['jobs'] if j['snapshot_date'] == snapshot)
    root = Path(job['restore_root']).resolve()
    require(root == (APPROVED_BASE / APPROVED_RESTORES[snapshot]).resolve(), 'Unapproved restore root')
    expected = {'2025-01-01': 520688, '2026-01-01': 563840, '2026-04-01': 578527}[snapshot]
    require(job['expected_studies'] == expected and type(job['port']) is int and
            1024 <= job['port'] <= 65535, 'Wrong source inventory/port')
    check_pins(job['pins'])
    proofs = {Path(p['path']).resolve(): p for p in job['pins']}
    for name in ('archive-inspection.json', 'dump-toc-pg17.txt', 'extracted/postgres.dmp',
                 'technical-audit.json', 'setup.py'):
        require(root / name in proofs, 'Missing restored-source ancestor: ' + name)
    archive = load_pin(proofs[root / 'archive-inspection.json'])
    raw = Path(archive['archive']).resolve()
    require(raw.is_relative_to(APPROVED_RAW.resolve()),
            'Archive outside approved raw root')
    raw_pin = {'path': str(raw), 'sha256': archive['sha256'], 'bytes': archive['bytes']}
    check_pins([raw_pin])
    dump = next(m for m in archive['members'] if m['name'] == 'postgres.dmp')
    require(dump['sha256'] == proofs[root / 'extracted/postgres.dmp']['sha256'],
            'Original dump contradicts qualified archive member')
    require('; Archive created at ' + snapshot + ' ' in
            (root / 'dump-toc-pg17.txt').read_text(encoding='utf-8'), 'Wrong actual dump date')
    audit = load_pin(proofs[root / 'technical-audit.json'])
    require(audit['status'] == 'completed' and audit['study_id_check']['rows'] == expected,
            'Wrong restored audit identity')
    request = content_query(nct_ids, snapshot, schema_from_audit(audit))
    path = Path(query_path).resolve()
    # Build deterministic query proof even before its exclusive write at preparation.
    raw_sql = request['sql'].encode('utf-8')
    import hashlib
    query = {'path': str(path), 'sha256': hashlib.sha256(raw_sql).hexdigest(),
             'bytes': len(raw_sql), 'request': request}
    return {'snapshot_date': snapshot, 'restore_root': str(root), 'port': job['port'],
            'expected_studies': expected, 'pins': job['pins'] + [raw_pin], 'query': query}


def build_plan(folder, mode, membership=None):
    require(mode in ('origin', 'followup'), 'Unknown B0 execution stage')
    policy, manifest, prior, candidate, excluded = origin_context()
    if mode == 'origin':
        require(membership is None, 'Origin cannot consume a follow-up membership')
        ids = sorted(c['nct_id'] for c in candidate['candidates'] if c['nct_id'] not in excluded)
        snapshots = ['2025-01-01']
    else:
        require(membership is not None, 'Follow-up needs sealed source-bound origin membership')
        selected = verify_membership(membership)
        ids = sorted(selected['nct_ids'])
        require(bool(ids), 'No eligible members: follow-up prohibited')
        snapshots = ['2026-01-01', '2026-04-01']
    require(bool(ids), 'No origin screening members')
    jobs = [source_job(manifest, when, ids, Path(folder) / (when + '.sql')) for when in snapshots]
    pg = Path(prior['pg_bin']).resolve()
    require(pg == Path('E:/projects_data/drug_target_agents_data/cache/postgresql-17.11-portable/pgsql/bin').resolve(),
            'Unapproved PostgreSQL runtime')
    return {'schema_version': 1, 'protocol_id': 'registry-content-execution-v0.1',
            'role': 'evaluation_only', 'mode': mode, 'policy': pin(POLICY),
            'source_manifest': pin(MANIFEST), 'membership': membership,
            'nct_ids': ids, 'jobs': jobs, 'pg_bin': str(pg),
            'runtime_pins': [pin(pg / name) for name in ('pg_ctl.exe', 'psql.exe', 'postgres.exe')],
            'code': [pin(ROOT / name) for name in CODE],
            'clinical_activation': False, 'scoring_activation': False,
            'provider_spend_usd': 0, 'model_calls': 0, 'automatic_retries': 0}


def prepare(output, mode, membership=None):
    output = Path(output).resolve()
    journal = RunJournal(output, kind='build')
    try:
        journal.append('build_stage', stage='source_inclusive_plan_binding')
        plan = build_plan(output, mode, membership)
        for job in plan['jobs']:
            with Path(job['query']['path']).open('xb') as stream:
                stream.write(job['query']['request']['sql'].encode('utf-8'))
        write_json(output / 'plan.json', plan)
        journal.append('build_completed', plan=pin(output / 'plan.json'))
        return pin(output / 'plan.json')
    except BaseException as exc:
        journal.fail(exc, 'source_inclusive_plan_binding')
        raise
    finally:
        journal.close()


def validate_plan(plan, plan_path):
    require(isinstance(plan, dict) and plan.get('protocol_id') == 'registry-content-execution-v0.1',
            'Wrong B0 execution protocol')
    expected = build_plan(Path(plan_path).parent, plan.get('mode'), plan.get('membership'))
    require(plan == expected, 'B0 execution plan differs from source-inclusive regeneration')
    check_pins(plan['runtime_pins'] + plan['code'])
    for job in plan['jobs']:
        check_pins([job['query']])
        require(Path(job['query']['path']).read_bytes() == job['query']['request']['sql'].encode('utf-8'),
                'Query bytes differ from regenerated allowlist')


def run(plan_proof, output):
    from tools.science.registry_content_transport import run_source
    output = Path(output).resolve()
    journal = RunJournal(output, kind='build')
    stage = 'source_binding'
    started = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        plan = load_pin(plan_proof)
        validate_plan(plan, Path(plan_proof['path']))
        write_json(output / 'effective-plan.json', plan)
        code_proofs = []
        for proof in plan['code']:
            source = Path(proof['path'])
            target = output / 'executed-code' / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(source.read_bytes())
            require(pin(target)['sha256'] == proof['sha256'], 'Code changed while archiving')
            code_proofs.append({'source': proof, 'copy': pin(target)})
        write_json(output / 'executed-code-proofs.json', code_proofs)
        results = []
        for job in plan['jobs']:
            stage = job['snapshot_date']
            journal.append('build_stage', stage=stage)
            source_started = time.monotonic()
            result = run_source(job, plan['pg_bin'], output / stage, journal)
            result['source_elapsed_seconds'] = time.monotonic() - source_started
            check_pins([result['first'], result['repeat']])
            require(Path(result['first']['path']).read_bytes() == Path(result['repeat']['path']).read_bytes(),
                    'Repeated B0 result bytes differ')
            rows = parse_jsonl(Path(result['first']['path']).read_text(encoding='utf-8'))
            states = classify_content(rows, job['query']['request'])
            # Classification alone never attests transport. Only this source-bound
            # receipt associates that proposal with verified original/repeated bytes.
            state_path = output / stage / 'state-proposals.json'
            write_json(state_path, states)
            result['state_proposals'] = pin(state_path)
            result['request_sha256'] = job['query']['request']['contract_sha256']
            results.append(result)
        check_pins(plan['runtime_pins'] + plan['code'])
        for job in plan['jobs']:
            check_pins(job['pins'] + [job['query']])
        report = {'schema_version': 1, 'status': 'source_bound_snapshot_reads_completed',
                  'role': 'evaluation_only', 'mode': plan['mode'], 'plan': plan_proof,
                  'effective_plan': pin(output / 'effective-plan.json'), 'results': results,
                  'executed_code_proofs': pin(output / 'executed-code-proofs.json'),
                  'started_at_utc': started_at, 'finished_at_utc': datetime.now(timezone.utc).isoformat(),
                  'elapsed_seconds': time.monotonic() - started,
                  'peak_parent_memory_bytes': peak_parent_memory(),
                  'peak_postgres_memory_bytes': None,
                  'peak_postgres_memory_reason': 'Database subprocess peak not instrumented; parent measurement is not whole-system memory.',
                  'clinical_labels_assigned': 0, 'clinical_activation': False,
                  'provider_spend_usd': 0, 'model_calls': 0}
        write_json(output / 'report.json', report)
        journal.append('build_completed', report=pin(output / 'report.json'))
        return report
    except BaseException as exc:
        journal.fail(exc, stage)
        write_json(output / 'failure.json', {'stage': stage, 'error_class': type(exc).__name__,
                   'message': str(exc), 'automatic_retry': False})
        raise
    finally:
        journal.close()


def verify_origin_run(origin_run):
    root = Path(origin_run).resolve()
    report_proof = pin(root / 'report.json')
    report = load_pin(report_proof)
    events = read_chain(root / 'journal.jsonl')
    require(events[-1]['event'] == 'build_completed' and
            dict(events[-1]['details']['report']) == report_proof, 'Origin journal does not bind report')
    require(report['status'] == 'source_bound_snapshot_reads_completed' and report['mode'] == 'origin',
            'Uncompleted or wrong origin extraction')
    require(report.get('role') == 'evaluation_only' and report.get('clinical_labels_assigned') == 0 and
            report.get('clinical_activation') is False and report.get('provider_spend_usd') == 0 and
            report.get('model_calls') == 0, 'Origin report scope/accounting differs')
    plan = load_pin(report['plan'])
    require(plan.get('mode') == 'origin' and len(plan['jobs']) == 1 and
            plan['jobs'][0]['snapshot_date'] == '2025-01-01', 'Follow-up plan cannot be an origin receipt')
    require(Path(report['effective_plan']['path']).resolve() == root / 'effective-plan.json',
            'Effective origin plan locator differs')
    require(load_pin(report['effective_plan']) == plan, 'Effective origin plan differs')
    validate_plan(plan, Path(report['plan']['path']))
    code_proof = report.get('executed_code_proofs')
    require(isinstance(code_proof, dict) and Path(code_proof['path']).resolve() ==
            root / 'executed-code-proofs.json', 'Missing owned executing-code receipt')
    archived = load_pin(code_proof)
    require(len(archived) == len(plan['code']), 'Incomplete archived execution code')
    for record, expected in zip(archived, plan['code']):
        require(record['source'] == expected, 'Archived execution source differs')
        source = Path(expected['path']).resolve()
        require(source.is_relative_to(ROOT), 'Execution code outside project')
        require(Path(record['copy']['path']).resolve() == root / 'executed-code' / source.relative_to(ROOT),
                'Executing-code archive locator differs')
        check_pins([record['copy']])
        require(record['copy']['sha256'] == expected['sha256'] and record['copy']['bytes'] == expected['bytes'],
                'Archived execution bytes differ')
    require(len(report['results']) == 1, 'Origin may contain only one source snapshot')
    result = report['results'][0]
    require(result['snapshot_date'] == '2025-01-01' and result['repeat_identical'] is True,
            'Wrong origin observation source')
    require(result.get('request_sha256') == plan['jobs'][0]['query']['request']['contract_sha256'],
            'Origin result request fingerprint differs')
    for name, suffix in [('first', 'first.stdout.log'), ('repeat', 'repeat.stdout.log')]:
        require(Path(result[name]['path']).resolve() == root / '2025-01-01' / suffix,
                'Origin result locator differs from owned output')
    for name, suffix in [('lifecycle', 'lifecycle.json'), ('state_proposals', 'state-proposals.json'),
                         ('metadata_file', 'metadata.stdout.log')]:
        require(Path(result[name]['path']).resolve() == root / '2025-01-01' / suffix,
                'Origin owned result locator differs: ' + name)
    check_pins([result[k] for k in ('first', 'repeat', 'lifecycle', 'state_proposals', 'metadata_file')])
    lifecycle = load_pin(result['lifecycle'])
    require(lifecycle.get('server_stopped') is True and lifecycle.get('port_closed') is True and
            lifecycle.get('primary_error_class') is None and lifecycle.get('cleanup_error_class') is None and
            lifecycle.get('startup_attempted') is True and lifecycle.get('automatic_retry') is False and
            lifecycle.get('port') == plan['jobs'][0]['port'], 'Origin source lifecycle incomplete')
    meta = load_pin(result['metadata_file'])
    job = plan['jobs'][0]
    require(meta == result['metadata'] and meta.get('database') == 'aact_snapshot' and
            type(meta.get('studies')) is int and meta['studies'] == job['expected_studies'] and
            Path(meta.get('directory', '')).resolve() == Path(job['restore_root']) / 'pgdata' and
            meta.get('port') == str(job['port']) and meta.get('read_only') == 'on',
            'Origin source connection receipt differs')
    from tools.science.registry_content_transport import METADATA_SQL, startup_command
    pg, restore = Path(plan['pg_bin']), Path(job['restore_root'])
    stage_folder = root / '2025-01-01'
    expected_args = {
        'status-before': [str(pg / 'pg_ctl.exe'), '-D', str(restore / 'pgdata'), 'status'],
        'start': startup_command(pg, restore, stage_folder, job['port']),
        'metadata': [str(pg / 'psql.exe'), '-XAtq', '-v', 'ON_ERROR_STOP=1', '-c', METADATA_SQL],
        'first': [str(pg / 'psql.exe'), '-XAtq', '-v', 'ON_ERROR_STOP=1', '-f', job['query']['path']],
        'repeat': [str(pg / 'psql.exe'), '-XAtq', '-v', 'ON_ERROR_STOP=1', '-f', job['query']['path']],
        'stop': [str(pg / 'pg_ctl.exe'), '-D', str(restore / 'pgdata'), '-m', 'fast', '-w', '-t', '45', 'stop'],
        'status-after': [str(pg / 'pg_ctl.exe'), '-D', str(restore / 'pgdata'), 'status'],
    }
    all_commands = [e['details'] for e in events if e['event'] == 'build_progress' and
                    e['details'].get('command') is not None]
    require([(c.get('command'), c.get('status')) for c in all_commands] ==
            [(name, status) for name in expected_args for status in ('started', 'finished')],
            'Origin command order/attempt count differs')
    for command, arguments in expected_args.items():
        commands = [e['details'] for e in events if e['event'] == 'build_progress' and
                    e['details'].get('stage') == '2025-01-01' and
                    e['details'].get('command') == command]
        require(len(commands) == 2 and commands[0].get('status') == 'started' and
                commands[1].get('status') == 'finished' and
                commands[1].get('returncode') == (3 if command.startswith('status-') else 0) and
                list(commands[0].get('arguments', [])) == arguments and
                commands[0].get('timeout_seconds') == (330 if command in ('first', 'repeat') else 90),
                'Origin command accounting contradicts successful extraction: ' + command)
        for channel in ('stdout', 'stderr'):
            observed = stage_folder / (command + '.' + channel + '.log')
            require(observed.is_file() and type(commands[1].get(channel + '_bytes')) is int and
                    commands[1][channel + '_bytes'] == observed.stat().st_size,
                    'Origin command byte accounting differs: ' + command + '.' + channel)
    require(Path(result['first']['path']).read_bytes() == Path(result['repeat']['path']).read_bytes(),
            'Origin repeated bytes differ')
    rows = parse_jsonl(Path(result['first']['path']).read_text(encoding='utf-8'))
    states = classify_content(rows, plan['jobs'][0]['query']['request'])
    require(load_pin(result['state_proposals']) == states, 'Origin state proposals differ from original rows')
    return report_proof, plan, states


def membership_record(origin_run):
    report_proof, plan, states = verify_origin_run(origin_run)
    _, manifest, _, candidate, excluded = origin_context()
    by_nct = {r['nct_id']: r for r in states['records']}
    selected, screen = [], []
    for candidate_row in candidate['candidates']:
        nct = candidate_row['nct_id']
        state = by_nct.get(nct)
        reason = ('excluded_prior_pilot' if nct in excluded else
                  'origin_unknown' if state is None or state['state'] == 'unknown' else
                  'origin_results_prevalent' if state['state'] == 'present' else
                  'selected' if len(selected) < 32 else 'eligible_beyond_cap')
        if reason == 'selected':
            selected.append(nct)
        screen.append({'nct_id': nct, 'disposition': reason, 'origin_state': state})
    return {'schema_version': 1, 'status': 'source_bound_origin_membership',
            'role': 'evaluation_only', 'endpoint_id': 'registry_outcome_measurement_appearance_v1',
            'policy': pin(POLICY), 'candidate_freeze': manifest['candidate_freeze'],
            'exclusion_packs': manifest['excluded_pack_pins'], 'origin_run': str(Path(origin_run).resolve()),
            'origin_report': report_proof, 'nct_ids': selected, 'screen': screen,
            'selected_members': len(selected), 'screened_candidates': len(screen),
            'followup_used_for_selection': False, 'clinical_activation': False,
            'clinical_labels_assigned': 0, 'protected_holdout': False}


def seal_membership(origin_run, output):
    output = Path(output).resolve()
    journal = RunJournal(output, kind='build')
    try:
        record = membership_record(origin_run)
        write_json(output / 'membership.json', record)
        journal.append('build_completed', membership=pin(output / 'membership.json'))
        return pin(output / 'membership.json')
    except BaseException as exc:
        journal.fail(exc, 'origin_membership_seal')
        raise
    finally:
        journal.close()


def verify_membership(proof):
    value = load_pin(proof)
    require(value.get('status') == 'source_bound_origin_membership', 'Wrong membership type')
    require(value == membership_record(value['origin_run']),
            'Membership differs from source-inclusive deterministic origin reconstruction')
    events = read_chain(Path(proof['path']).parent / 'journal.jsonl')
    require(events[-1]['event'] == 'build_completed' and
            dict(events[-1]['details']['membership']) == proof, 'Membership journal binding differs')
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare-origin', 'prepare-followup', 'run', 'seal-origin'))
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--expected-sha256')
    args = parser.parse_args(argv)
    if args.action == 'prepare-origin':
        result = prepare(args.output, 'origin')
    elif args.action == 'seal-origin':
        require(args.input is not None, 'Origin run directory required')
        result = seal_membership(args.input, args.output)
    else:
        require(args.input is not None and args.expected_sha256 is not None, 'Byte-bound input required')
        proof = pin(args.input)
        require(proof['sha256'] == args.expected_sha256, 'Supplied input hash differs')
        result = (prepare(args.output, 'followup', proof) if args.action == 'prepare-followup'
                  else run(proof, args.output))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
