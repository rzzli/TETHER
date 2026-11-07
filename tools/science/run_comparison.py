"""Freeze source-only paired inputs, then own a local zero-provider-cost comparison.

Preparation never opens evaluator answers. Execution is explicit and single-use;
failure outputs are retained and cannot be automatically resumed or overwritten.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from importlib import metadata
import json
import os
import platform
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

from tether_engine.chrono import EvidenceStore, load_snapshot
from tether_engine.contracts import Case, Category, EvidenceStatus
from tether_engine.ingest import peak_memory_bytes
from tether_engine.journal import RunJournal, read_chain
from tether_engine.local_model import NoRedirect
from tools.science.role_backend import ROLE_SELECTION_POLICY, RoleSelectionBackend
from tether_engine.serde import ContractError, decode, encode, fingerprint, read_json, safe_child, sha256_file, write_json
from tether_engine.workflow import Budget


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT/'planning/protocols/science7-matched-t6-v0.2.json'
PORT = 55581
CODE_FILES = ('tools/science/run_comparison.py', 'tools/science/comparison_workflow.py', 'tools/science/role_backend.py') + tuple(
        p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'src/tether_engine').glob('*.py')))
EXECUTION_PROOF_FILES = {
    'execution_journal': 'execution/journal.jsonl',
    'server_command': 'server-command.json',
    'model_config': 'model-config.json',
    'native_stdout': 'server.stdout.log',
    'native_stderr': 'server.stderr.log',
    'preparation_journal': 'prepare/journal.jsonl',
}


def pin(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': sha256_file(path), 'bytes': path.stat().st_size}


def check_pin(proof):
    path = Path(proof['path'])
    if (not path.is_file() or path.stat().st_size != proof['bytes'] or
            sha256_file(path) != proof['sha256']):
        raise ContractError('Comparison pinned bytes changed: ' + str(path))
    return path


def selected_store(case, full, maximum=None, seed=None):
    observed = tuple(r for category in Category for r in full.query(case, category)
                     if r.observation.status == EvidenceStatus.OBSERVED)
    if any(r.observation.features for r in observed):
        raise ContractError('Real comparison prediction features must remain empty')
    if maximum is not None or seed is not None:
        raise ContractError('Frozen comparison requires the complete admitted case world, not a reference-selected subset')
    ids = sorted(r.observation.observation_id for r in observed)
    rows = tuple(full.lookup(identity) for identity in ids)
    nonobserved = tuple(r for category in Category for r in full.query(case, category)
                       if r.observation.status != EvidenceStatus.OBSERVED)
    restricted = EvidenceStore(full.snapshot, rows + nonobserved, full.exclusions,
                               full.source_proofs, full.catalog_policy)
    restricted.snapshot_base = full.snapshot_base
    selection = {'candidate_ids': ids, 'candidate_sha256s': {r.observation.observation_id: fingerprint(r) for r in rows},
                 'full_admitted_observed': len(observed), 'selected_observed': len(rows),
                 'policy': {'maximum': None, 'seed': None, 'selection': 'complete_admitted_case_world_without_answers'},
                 'source_proofs_sha256': fingerprint(full.source_proofs)}
    return restricted, selection


def _load_case(plan, row):
    for name in ('case', 'snapshot'):
        check_pin(row[name])
    case = decode(Case, read_json(Path(row['case']['path'])))
    if case.case_id != row['case_id']:
        raise ContractError('Comparison case identity changed')
    full = load_snapshot(Path(row['snapshot']['path']), case, Path(plan['catalog']['path']))
    if fingerprint(full.source_proofs) != fingerprint(row['source_proofs']):
        raise ContractError('Comparison complete source proof inventory differs')
    world = plan['candidate_world']
    restricted, selected = selected_store(case, full, world['maximum_total_observations_per_case'], world['seed'])
    if fingerprint(selected) != fingerprint(row['selection']):
        raise ContractError('Comparison source-only candidate world changed')
    return case, restricted


def validate_plan(plan):
    """Validate the complete fixed recipe, never accept arbitrary planned paths."""
    output = Path(plan['root']).resolve()
    if not any(output.is_relative_to(ROOT/name) for name in ('runs', 'data/derived')):
        raise ContractError('Comparison plan output escapes the ignored project trees')
    protocol = read_json(check_pin(plan['protocol']))
    if (protocol.get('protocol_id') != 'science7-matched-source-bounded-t6-v0.2' or
            plan.get('schema_version') != 1 or plan.get('provider_spend_usd') != 0 or
            plan.get('evaluator_inputs_opened') is not False):
        raise ContractError('Comparison plan boundary or protocol differs')
    for field, expected in (('arms', protocol['arms']), ('budget', protocol['budget_per_case_per_arm']),
                            ('backend', protocol['local_backend']), ('candidate_world', protocol['candidate_world'])):
        if fingerprint(plan.get(field)) != fingerprint(expected):
            raise ContractError('Comparison recipe differs from frozen protocol: ' + field)
    for field, name in (('catalog', 'catalog-policy.json'), ('role_policy', 'role-policy.json'),
                         ('model_receipt', 'model-acquisition.json')):
        if check_pin(plan[field]).resolve() != output/name:
            raise ContractError('Comparison local manifest path differs')
    expected_policy = protocol['role_policy']
    policy_source = safe_child(ROOT, expected_policy['path'])
    policy = read_json(check_pin(plan['role_policy']))
    if (sha256_file(policy_source) != expected_policy['sha256'] or
            plan['role_policy']['sha256'] != expected_policy['sha256'] or
            policy.get('output_constraint_policy') != RoleSelectionBackend.output_scope_policy or
            protocol['local_backend'].get('selection_policy') != ROLE_SELECTION_POLICY):
        raise ContractError('Comparison frozen role-policy output constraint differs')
    if (plan['model_receipt']['sha256'] != protocol['local_backend']['acquisition_receipt_sha256'] or
            plan['original_model_receipt']['sha256'] != plan['model_receipt']['sha256']):
        raise ContractError('Comparison model receipt is not the pinned acquisition')
    check_pin(plan['original_model_receipt'])
    source_build = check_pin(plan['source_build'])
    bundle = safe_child(ROOT, protocol['source_bundle'])
    if (source_build != bundle/'build-report.json' or
            plan['source_build']['sha256'] != protocol['source_build_report_sha256']):
        raise ContractError('Comparison source build path or bytes differ')
    expected_ids = [r['case_id'] for r in read_json(source_build)['cases']]
    actual_ids = [r['case_id'] for r in plan['cases']]
    if len(expected_ids) != 10 or actual_ids != expected_ids or len(set(actual_ids)) != 10:
        raise ContractError('Comparison case membership differs from the fixed ten-case build')
    for row in plan['cases']:
        for field, name in (('case', 'case.json'), ('snapshot', 'snapshot.json')):
            if check_pin(row[field]) != safe_child(bundle, row['case_id'])/name:
                raise ContractError('Comparison case source path differs')
    schedule = plan['execution_order']
    if [r['case_id'] for r in schedule] != expected_ids:
        raise ContractError('Comparison execution membership/order differs')
    for i, row in enumerate(schedule):
        arms = plan['arms']
        if row['arms'] != arms[i % len(arms):] + arms[:i % len(arms)]:
            raise ContractError('Comparison fixed arm rotation differs')
    if (len(plan['code']) != len(CODE_FILES) or {str(Path(p['path']).resolve()) for p in plan['code']} !=
            {str((ROOT/name).resolve()) for name in CODE_FILES}):
        raise ContractError('Comparison executing code inventory differs')
    for proof in plan['code']:
        check_pin(proof)
        name = Path(proof['path']).resolve().relative_to(ROOT)
        archived = output/'executed-code'/name
        if not archived.is_file() or sha256_file(archived) != proof['sha256']:
            raise ContractError('Comparison executing code archive differs')
    Budget(**plan['budget']).validate()
    return {'status': 'plan_valid', 'cases': 10, 'arms': len(plan['arms'])}


def prepare(output, protocol_path=PROTOCOL):
    output = Path(output).resolve()
    if not any(output.is_relative_to(ROOT/name) for name in ('runs', 'data/derived')):
        raise ContractError('Comparison output must be under ignored project runs or data/derived')
    output.mkdir(parents=True, exist_ok=False)
    journal = RunJournal(output/'prepare', kind='build')
    started = time.monotonic()
    try:
        from tools.science.comparison_workflow import default_role_policy
        protocol = read_json(Path(protocol_path))
        if protocol['protocol_id'] != 'science7-matched-source-bounded-t6-v0.2':
            raise ContractError('Unexpected comparison protocol')
        bundle = safe_child(ROOT, protocol['source_bundle'])
        if sha256_file(bundle/'build-report.json') != protocol['source_build_report_sha256']:
            raise ContractError('Source build differs from frozen Science2 input')
        build = read_json(bundle/'build-report.json')
        if build['status'] != 'built' or len(build['cases']) != 10:
            raise ContractError('Expected ten complete source-bound development cases')
        catalog = output/'catalog-policy.json'
        catalog.write_bytes((ROOT/'data/catalog/sources.json').read_bytes())
        role_policy = default_role_policy()
        write_json(output/'role-policy.json', role_policy)
        pointer = read_json(ROOT/'data/derived/active-local-model-acquisition.json')
        receipt_path = Path(pointer['path'])
        if (sha256_file(receipt_path) != pointer['sha256'] or
                pointer['sha256'] != protocol['local_backend']['acquisition_receipt_sha256']):
            raise ContractError('Model receipt pointer changed')
        receipt = read_json(receipt_path)
        if receipt['status'] != 'downloaded_hash_verified_not_inference_validated':
            raise ContractError('Incomplete model acquisition receipt')
        receipt_copy = output/'model-acquisition.json'
        receipt_copy.write_bytes(receipt_path.read_bytes())
        world = protocol['candidate_world']
        plan = {'schema_version': 1, 'root': str(output), 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'scope': protocol['scope'], 'protocol': pin(protocol_path), 'source_build': pin(bundle/'build-report.json'),
                'catalog': pin(catalog), 'role_policy': pin(output/'role-policy.json'),
                'model_receipt': pin(receipt_copy), 'original_model_receipt': pin(receipt_path),
                'candidate_world': world, 'budget': protocol['budget_per_case_per_arm'],
                'backend': protocol['local_backend'], 'cases': [], 'arms': protocol['arms'],
                'evaluator_inputs_opened': False, 'provider_spend_usd': 0,
                'code': [pin(ROOT/name) for name in CODE_FILES],
                'environment': {'python': sys.version, 'platform': platform.platform(),
                    'installed_dependencies': dict(sorted((d.metadata['Name'], d.version) for d in metadata.distributions() if d.metadata['Name']))}}
        for name in CODE_FILES:
            source = ROOT/name
            copy = output/'executed-code'/name
            copy.parent.mkdir(parents=True, exist_ok=True)
            copy.write_bytes(source.read_bytes())
            if sha256_file(copy) != sha256_file(source):
                raise ContractError('Code changed while archiving preparation')
        for entry in build['cases']:
            case_id = entry['case_id']
            folder = safe_child(bundle, case_id)
            case = decode(Case, read_json(folder/'case.json'))
            if case.task != 'T6' or case_id != case.case_id:
                raise ContractError('Comparison only accepts the frozen T6 case pack')
            full = load_snapshot(folder/'snapshot.json', case, catalog)
            _, selection = selected_store(case, full, world['maximum_total_observations_per_case'], world['seed'])
            row = {'case_id': case_id, 'case': pin(folder/'case.json'), 'snapshot': pin(folder/'snapshot.json'),
                   'selection': selection, 'source_proofs': encode(full.source_proofs)}
            plan['cases'].append(row)
            journal.append('source_world_prepared', case_id=case_id, selected=selection['selected_observed'],
                           full_observed=selection['full_admitted_observed'], source_proofs=len(full.source_proofs))
        # Rotate the fixed arm list by case position, before any inference.
        plan['execution_order'] = [{'case_id': row['case_id'],
            'arms': plan['arms'][i % len(plan['arms']):] + plan['arms'][:i % len(plan['arms'])]}
            for i, row in enumerate(plan['cases'])]
        plan['preparation_seconds'] = time.monotonic()-started
        plan['preparation_peak_python_memory_bytes'] = peak_memory_bytes()
        validate_plan(plan)
        write_json(output/'run-plan.json', plan)
        journal.append('plan_frozen', plan_sha256=sha256_file(output/'run-plan.json'),
                       cases=len(plan['cases']), selected=sum(r['selection']['selected_observed'] for r in plan['cases']))
        return {'plan': str(output/'run-plan.json'), 'sha256': sha256_file(output/'run-plan.json'),
                'cases': len(plan['cases']), 'status': 'prepared_no_inference_no_answers'}
    except BaseException as error:
        journal.fail(error, 'preparation')
        raise
    finally:
        journal.close()


def port_closed(port):
    with socket.socket() as client:
        client.settimeout(0.5)
        return client.connect_ex(('127.0.0.1', port)) != 0


def _owned_listener(pid, port):
    if os.name != 'nt':
        raise ContractError('This native launcher is explicitly Windows-only')
    command = f"(Get-NetTCPConnection -State Listen -LocalPort {int(port)} -ErrorAction Stop).OwningProcess"
    result = subprocess.run(['pwsh', '-NoProfile', '-Command', command], check=True,
                            capture_output=True, timeout=15, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return {int(p) for p in result.stdout.decode('utf-8-sig').split()} == {pid}


def verify_model(receipt):
    model_root = Path(receipt['root']).resolve()
    for entry in receipt['items']:
        path = safe_child(model_root, entry['name'])
        if path.stat().st_size != entry['bytes'] or sha256_file(path) != entry['sha256']:
            raise ContractError('Model/native archive changed')
    for entry in receipt['runtime_files']:
        if sha256_file(safe_child(model_root, entry['path'])) != entry['sha256']:
            raise ContractError('Extracted native runtime changed')
    servers = list((model_root/'runtime').rglob('llama-server.exe'))
    if len(servers) != 1:
        raise ContractError('Native server identity is ambiguous')
    weights = [entry for entry in receipt['items'] if entry['name'].endswith('.gguf')]
    if not weights:
        raise ContractError('No pinned model weights')
    return servers[0], safe_child(model_root, weights[0]['name'])


def _dossier(case, result):
    lines = [f'# Source-bounded T6 comparison: {case.case_id}', '',
             f'Action: {case.hypothesis.intended_action}; modality: {case.hypothesis.modality}; tissue: {case.hypothesis.tissue or "unspecified"}.',
             f'Arm: {result.get("arm")}; status: {result.get("status")}.', '',
             'Probability withheld. Numerical prediction features are empty. These are selected resource annotations, not evidence of intervention benefit.', '',
             'Original source contexts, unknown fields and coverage are retained in result.json.', '']
    for claim in result.get('claims', []):
        lines += ['```json', json.dumps(claim, ensure_ascii=False, indent=2), '```', '']
    return '\n'.join(lines)


def _write_predictions_seal(output, plan_path, report):
    """Bind closed execution/preparation journals and final native logs before evaluation."""
    if report['status'] != 'all_paired_runs_verified' or not report['server_stopped']:
        raise ContractError('Only a completed, stopped comparison can seal predictions')
    output = Path(output).resolve()
    seal = {'schema_version': 1, 'role': 'sealed_predictions_before_evaluator_join',
        'sealed_at_utc': datetime.now(timezone.utc).isoformat(), 'plan': pin(plan_path),
        'execution_report': pin(output/'execution-report.json'),
        'execution_proofs': {name: pin(output/path) for name, path in EXECUTION_PROOF_FILES.items()},
        'cases': report['cases'], 'clinical_probabilities': None,
        'evaluator_answers_opened_by_launcher': False}
    write_json(output/'predictions-seal.json', seal)
    return seal


def execute(plan_path, expected_sha256):
    plan_path = Path(plan_path).resolve()
    if sha256_file(plan_path) != expected_sha256:
        raise ContractError('Comparison plan fingerprint differs')
    plan = read_json(plan_path)
    output = Path(plan['root']).resolve()
    if plan_path != output/'run-plan.json':
        raise ContractError('Plan moved outside its reserved output')
    # This exclusive reservation is never removed or reused, even on startup failure.
    journal = RunJournal(output/'execution', kind='build')
    process = None
    started = time.monotonic()
    report = {'schema_version': 1, 'status': 'running', 'plan_sha256': expected_sha256,
              'started_at_utc': datetime.now(timezone.utc).isoformat(), 'cases': [], 'provider_spend_usd': 0}
    try:
        from tools.science.comparison_workflow import run_case, verify_case
        validate_plan(plan)
        for proof in plan['code'] + [plan['protocol'], plan['source_build'], plan['catalog'],
                                      plan['role_policy'], plan['model_receipt'], plan['original_model_receipt']]:
            check_pin(proof)
        if plan.get('evaluator_inputs_opened') is not False or plan['provider_spend_usd'] != 0:
            raise ContractError('Comparison boundary contradiction')
        receipt = read_json(check_pin(plan['model_receipt']))
        journal.append('model_verification_started')
        server, model = verify_model(receipt)
        journal.append('model_verification_passed', server_sha256=sha256_file(server))
        with socket.socket() as check:
            check.bind(('127.0.0.1', PORT))
        argv = [str(server), '--model', str(model), '--host', '127.0.0.1', '--port', str(PORT),
                '--ctx-size', '16384', '--parallel', '1', '--n-gpu-layers', '99', '--threads', '8',
                '--alias', 'tether-science7-qwen25-14b', '--no-webui', '--offline']
        write_json(output/'server-command.json', {'argv': argv, 'runtime_sha256': sha256_file(server)})
        with (output/'server.stdout.log').open('xb') as stdout, (output/'server.stderr.log').open('xb') as stderr:
            process = subprocess.Popen(argv, stdout=stdout, stderr=stderr,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        journal.append('server_started', pid=process.pid)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        deadline = time.monotonic()+180
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('Owned native server exited; inspect retained logs')
            try:
                with opener.open(f'http://127.0.0.1:{PORT}/health', timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(1)
        else:
            raise TimeoutError('Native startup timed out; no automatic repeat')
        if not _owned_listener(process.pid, PORT):
            raise ContractError('Loopback listener ownership not established')
        journal.append('server_ready', pid=process.pid)
        settings = plan['backend']
        config = {'schema_version': 1, 'endpoint': f'http://127.0.0.1:{PORT}',
                  'model_id': 'Qwen/Qwen2.5-14B-Instruct-GGUF@'+receipt['revision'],
                  'model_provenance': {'weights_sha256': {r['name']: r['sha256'] for r in receipt['items'] if r['name'].endswith('.gguf')},
                                       'runtime_sha256': sha256_file(server), 'acquisition_receipt_sha256': plan['model_receipt']['sha256']},
                  'retrieval': settings['retrieval'], 'max_output_tokens': settings['max_output_tokens'],
                  'timeout_seconds': settings['timeout_seconds'], 'seed': settings['seed']}
        config_path = output/'model-config.json'
        write_json(config_path, config)
        policy = read_json(Path(plan['role_policy']['path']))
        rows = {r['case_id']: r for r in plan['cases']}
        for scheduled in plan['execution_order']:
            row = rows[scheduled['case_id']]
            case, store = _load_case(plan, row)
            case_result = {'case_id': case.case_id, 'arms': []}
            report['cases'].append(case_result)
            for arm in scheduled['arms']:
                for proof in plan['code']:
                    check_pin(proof)
                backend = RoleSelectionBackend(config_path)
                folder = output/'arms'/case.case_id/arm
                journal.append('arm_started', case_id=case.case_id, arm=arm)
                result = run_case(case, store, backend, Budget(**plan['budget']), arm, folder, role_policy=policy)
                if 'probability' not in result or result['probability'] is not None or result.get('features') != {}:
                    raise ContractError('Unqualified real prediction emitted')
                validation = verify_case(folder, case, store, backend_config=config, role_policy=policy)
                write_json(folder.parent/(arm+'-verification.json'), validation)
                # Dossier is an auxiliary view; the engine seals the authoritative JSON.
                (folder.parent/(arm+'-dossier.md')).write_text(_dossier(case, result), encoding='utf-8', newline='\n')
                case_result['arms'].append({'arm': arm, 'path': str(folder), 'result': pin(folder/'result.json'),
                    'seal': pin(folder/'seal.json'), 'verification': pin(folder.parent/(arm+'-verification.json')),
                    'status': result['status'], 'calls': result.get('calls'), 'usage': result.get('usage')})
                journal.append('arm_verified', case_id=case.case_id, arm=arm, status=result['status'],
                               result_sha256=sha256_file(folder/'result.json'))
                print(json.dumps({'case_id': case.case_id, 'arm': arm, 'status': result['status'], 'calls': result.get('calls')}), flush=True)
                if result['status'] in ('failed', 'interrupted'):
                    journal.append('arm_terminal_failure', case_id=case.case_id, arm=arm,
                                   status=result['status'], result_sha256=sha256_file(folder/'result.json'))
                    raise ContractError('Comparison arm '+result['status']+'; retained outputs require inspection before any new run')
                if result['status'] not in ('completed', 'budget_exhausted'):
                    raise ContractError('Comparison arm has an unsupported terminal status')
            # Fresh source-inclusive admission after the complete paired case, not just output hashes.
            _load_case(plan, row)
            journal.append('paired_case_source_reverified', case_id=case.case_id)
        for proof in plan['code']:
            check_pin(proof)
        for name in ('protocol', 'source_build', 'catalog', 'role_policy', 'model_receipt', 'original_model_receipt'):
            check_pin(plan[name])
        report['status'] = 'all_paired_runs_verified'
    except BaseException as error:
        report.update(status='failed', error_class=type(error).__name__, error=str(error))
        journal.fail(error, 'execution')
        raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        report.update(finished_at_utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic()-started,
                      server_stopped=process is None or process.poll() is not None,
                      owned_loopback_port_closed=port_closed(PORT), peak_python_memory_bytes=peak_memory_bytes(),
                      peak_native_memory_bytes=None, native_memory_reason='Not instrumented; no estimate inferred')
        write_json(output/'execution-report.json', report)
        journal.append('execution_terminal', status=report['status'], server_stopped=report['server_stopped'])
        journal.close()
        if report['status'] == 'all_paired_runs_verified':
            _write_predictions_seal(output, plan_path, report)
        write_json(output/'seal.json', {'schema_version': 1, 'files': [
            {'path': p.relative_to(output).as_posix(), 'sha256': sha256_file(p), 'bytes': p.stat().st_size}
            for p in sorted(output.rglob('*')) if p.is_file() and p != output/'seal.json']})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    preparation = commands.add_parser('prepare')
    preparation.add_argument('--output', type=Path, required=True)
    preparation.add_argument('--protocol', type=Path, default=PROTOCOL)
    execution = commands.add_parser('execute')
    execution.add_argument('--plan', type=Path, required=True)
    execution.add_argument('--expected-sha256', required=True)
    args = parser.parse_args(argv)
    result = prepare(args.output, args.protocol) if args.command == 'prepare' else execute(args.plan, args.expected_sha256)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
