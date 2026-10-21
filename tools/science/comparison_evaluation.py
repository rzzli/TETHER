"""Post-seal descriptive source evaluation; no inference or clinical metrics."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
from itertools import combinations
from pathlib import Path
import time

from asof.contracts import Category, EvidenceStatus
from asof.journal import RunJournal, read_chain
from asof.serde import ContractError, encode, fingerprint, parse_json, safe_child, sha256_file, write_json
from tools.science.qualification import require_hash, validate_reference


def _freeze_evaluator_code(output):
    """Archive the exact local evaluation helpers and retain immutable digests."""
    root = Path(__file__).resolve().parents[2]
    inventory = []
    for name in ('tools/science/comparison_evaluation.py', 'tools/science/qualification.py',
                 'tools/science/reference_packets.py', 'tools/framework/run_pilot.py'):
        source = root/name
        payload = source.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        archive = output/'executed-code'/name
        archive.parent.mkdir(parents=True, exist_ok=True)
        with archive.open('xb') as stream:
            stream.write(payload)
        inventory.append({'source': {'path': str(source), 'sha256': digest, 'bytes': len(payload)},
                          'archive': {'path': str(archive), 'sha256': digest, 'bytes': len(payload)}})
    return inventory


def _read_pinned(path, expected, size=None):
    """Hash the exact bytes parsed; never open an unpinned answer file."""
    path = Path(path)
    require_hash(expected)
    if not path.is_file() or path.stat().st_size > 64 * 1024 * 1024:
        raise ContractError('Missing or oversized pinned evaluation input')
    raw = path.read_bytes()
    if (size is not None and len(raw) != size) or hashlib.sha256(raw).hexdigest() != expected:
        raise ContractError('Pinned evaluation bytes differ: ' + str(path))
    return parse_json(raw)


def _proof(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': sha256_file(path), 'bytes': path.stat().st_size}


def _expected_proof(path, digest):
    proof = _proof(path)
    if proof['sha256'] != digest:
        raise ContractError('Pinned input changed after its exact parsed read')
    return proof


def _source_input_proofs(store):
    """Retain admitted digests, including receipts, for the terminal recheck."""
    proofs = []
    for source in store.source_proofs:
        proofs.append({'path': source['path'], 'sha256': source['sha256'],
                       'bytes': Path(source['path']).stat().st_size})
        if source.get('receipt_path'):
            proofs.append({'path': source['receipt_path'], 'sha256': source['receipt_sha256'],
                           'bytes': Path(source['receipt_path']).stat().st_size})
    return proofs


def _unique_proofs(proofs):
    unique = {}
    for proof in proofs:
        path = str(Path(proof['path']).resolve())
        if path in unique and unique[path] != proof:
            raise ContractError('Evaluation input has inconsistent pinned proofs')
        unique[path] = proof
    return list(unique.values())


def _open_proof(proof):
    return _read_pinned(proof['path'], proof['sha256'], proof['bytes'])


def _sealed_inventory(folder, proof):
    """Expand immutable per-file pins and retain exact nested membership."""
    document = _open_proof(proof)
    rows, names = [], set()
    if document.get('schema_version') != 1:
        raise ContractError('Arm seal version differs')
    for row in document['files']:
        path = safe_child(folder, row['path'])
        if row['path'] in names or path == folder/'seal.json':
            raise ContractError('Arm seal duplicates or self-includes a file')
        names.add(row['path'])
        rows.append({'path': str(path), 'sha256': row['sha256'], 'bytes': row['bytes']})
    _check_inventory(folder, names)
    return rows, (folder, names)


def _check_inventory(folder, names):
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p != folder/'seal.json'}
    if actual != names:
        raise ContractError('Arm nested output inventory changed')


def _executed_code_proofs(plan):
    root = Path(__file__).resolve().parents[2]
    proofs = []
    for row in plan['code']:
        relative = Path(row['path']).resolve().relative_to(root)
        proofs.append({'path': str(Path(plan['root'])/'executed-code'/relative),
                       'sha256': row['sha256'], 'bytes': row['bytes']})
    return proofs


def _workflow_code_binding(folder, plan):
    matches = [proof for proof in plan['code'] if Path(proof['path']).resolve() == Path(__file__).with_name('comparison_workflow.py').resolve()]
    if len(matches) != 1 or sha256_file(folder/'executed-source.py') != matches[0]['sha256']:
        raise ContractError('Arm executed workflow source differs from frozen executing code')


def _launcher_boundary(seal, plan, config, *, verify_native=True):
    """Inspect trusted launcher records; these are not native attestation."""
    from tools.science.run_comparison import verify_model
    root = Path(plan['root']).resolve()
    expected = {'execution_journal': root/'execution/journal.jsonl', 'server_command': root/'server-command.json',
        'model_config': root/'model-config.json', 'native_stdout': root/'server.stdout.log',
        'native_stderr': root/'server.stderr.log', 'preparation_journal': root/'prepare/journal.jsonl'}
    provided = seal.get('execution_proofs', {})
    if set(provided) != set(expected):
        raise ContractError('Required trusted launcher proof inventory differs')
    proofs = []
    for name, path in expected.items():
        row = provided[name]
        if Path(row['path']).resolve() != path:
            raise ContractError('Trusted launcher proof path differs')
        proofs.append(_expected_proof(path, row['sha256']))
        if proofs[-1]['bytes'] != row['bytes']:
            raise ContractError('Trusted launcher proof size differs')
    if _open_proof(provided['model_config']) != config:
        raise ContractError('Trusted launcher model configuration differs')
    receipt = _open_proof(plan['model_receipt'])
    model_root = Path(receipt['root']).resolve()
    servers = [row for row in receipt['runtime_files'] if Path(row['path']).name == 'llama-server.exe']
    weights = [row for row in receipt['items'] if row['name'].endswith('.gguf')]
    if len(servers) != 1 or not weights:
        raise ContractError('Trusted launcher model/runtime identity is ambiguous')
    server, model = safe_child(model_root, servers[0]['path']), safe_child(model_root, weights[0]['name'])
    command = _open_proof(provided['server_command'])
    argv = [str(server), '--model', str(model), '--host', '127.0.0.1', '--port', '55581',
        '--ctx-size', '16384', '--parallel', '1', '--n-gpu-layers', '99', '--threads', '8',
        '--alias', 'asof-science7-qwen25-14b', '--no-webui', '--offline']
    if command != {'argv': argv, 'runtime_sha256': servers[0]['sha256']}:
        raise ContractError('Trusted launcher command differs from pinned offline loopback recipe')
    preparation = read_chain(expected['preparation_journal'])
    if (preparation[0]['event'] != 'build_reserved' or preparation[-1]['event'] != 'plan_frozen' or
            preparation[-1]['details'].get('plan_sha256') != seal['plan']['sha256'] or
            any(row['event'] in ('build_failed', 'build_interrupted') for row in preparation)):
        raise ContractError('Trusted preparation journal lacks its completed plan boundary')
    events = read_chain(expected['execution_journal'])
    names = [event['event'] for event in events]
    expected_names = ['build_reserved', 'model_verification_started', 'model_verification_passed', 'server_started', 'server_ready']
    for case in plan['execution_order']:
        expected_names.extend(name for _ in case['arms'] for name in ('arm_started', 'arm_verified'))
        expected_names.append('paired_case_source_reverified')
    expected_names.append('execution_terminal')
    if names != expected_names:
        raise ContractError('Trusted execution lifecycle stage/order inventory differs')
    required = ('model_verification_started', 'model_verification_passed', 'server_started', 'server_ready', 'execution_terminal')
    if (names[0] != 'build_reserved' or names[-1] != 'execution_terminal' or
            any(names.count(name) != 1 for name in required) or
            [names.index(name) for name in required] != sorted(names.index(name) for name in required) or
            any(name in ('build_failed', 'build_interrupted') for name in names)):
        raise ContractError('Trusted execution journal lifecycle differs')
    details = {name: events[names.index(name)]['details'] for name in required}
    pid = details['server_started'].get('pid')
    if (type(pid) is not int or pid <= 0 or details['server_ready'].get('pid') != pid or
            details['model_verification_passed'].get('server_sha256') != servers[0]['sha256'] or
            details['execution_terminal'].get('status') != 'all_paired_runs_verified' or
            details['execution_terminal'].get('server_stopped') is not True):
        raise ContractError('Trusted execution model, PID or terminal boundary differs')
    expected_arms = [(case['case_id'], arm['arm'], arm) for case in seal['cases'] for arm in case['arms']]
    if [(case['case_id'], [arm['arm'] for arm in case['arms']]) for case in seal['cases']] != [
            (case['case_id'], case['arms']) for case in plan['execution_order']]:
        raise ContractError('Trusted execution differs from frozen case/arm schedule')
    actual_arms = [event for event in events if event['event'] == 'arm_verified']
    starts = [event for event in events if event['event'] == 'arm_started']
    if len(actual_arms) != len(expected_arms) or len(starts) != len(expected_arms):
        raise ContractError('Trusted execution arm inventory differs')
    for (case_id, arm_id, arm), start, event in zip(expected_arms, starts, actual_arms):
        d = event['details']
        if (start['details'] != {'case_id': case_id, 'arm': arm_id} or start['sequence'] >= event['sequence'] or
                event['sequence'] <= names.index('server_ready') or
                d != {'case_id': case_id, 'arm': arm_id, 'status': arm['status'], 'result_sha256': arm['result']['sha256']}):
            raise ContractError('Trusted execution arm order or bound result differs')
    reverified = [event['details'].get('case_id') for event in events if event['event'] == 'paired_case_source_reverified']
    if reverified != [row['case_id'] for row in seal['cases']]:
        raise ContractError('Trusted execution source reverification inventory differs')
    signatures, files = [], []
    if verify_native:
        for row in receipt['items'] + receipt['runtime_files']:
            path = safe_child(model_root, row.get('name', row.get('path')))
            stat = path.stat()
            signatures.append((path, (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)))
            files.append({'path': str(path), 'sha256': row['sha256'], 'bytes': stat.st_size})
        actual_server, actual_model = verify_model(receipt)
        if actual_server.resolve() != server or actual_model.resolve() != model:
            raise ContractError('Verified model paths differ from launcher command')
        # The expensive byte verification runs once. Retain metadata signatures
        # to reject subsequent changes without hashing the weights a second time.
        _check_model_signatures(signatures)
    verification = {'status': 'actual_model_and_runtime_bytes_verified' if verify_native else 'previous_completed_evaluation_required',
        'receipt_sha256': plan['model_receipt']['sha256'], 'files': files,
        'trusted_launcher_pid': pid, 'native_attestation': False}
    return verification, proofs, signatures


def _check_model_signatures(signatures):
    for path, expected in signatures:
        stat = path.stat()
        if (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns) != expected:
            raise ContractError('Verified model/runtime changed during evaluation')


def _seal_scope(seal_path, seal, plan):
    """Validate the complete prediction boundary before opening any answers."""
    from tools.science.comparison_workflow import ARMS
    root = Path(plan['root']).resolve()
    if (seal.get('schema_version') != 1 or seal.get('role') != 'sealed_predictions_before_evaluator_join' or
            seal.get('evaluator_answers_opened_by_launcher') is not False or seal.get('clinical_probabilities') is not None):
        raise ContractError('Prediction seal boundary differs')
    if (seal_path != root/'predictions-seal.json' or
            Path(seal['plan']['path']).resolve() != root/'run-plan.json' or
            Path(seal['execution_report']['path']).resolve() != root/'execution-report.json' or
            len(plan['arms']) != len(ARMS) or set(plan['arms']) != set(ARMS)):
        raise ContractError('Prediction seal path or matched arm scope differs')
    execution = _open_proof(seal['execution_report'])
    if (execution.get('status') != 'all_paired_runs_verified' or execution.get('plan_sha256') != seal['plan']['sha256'] or
            execution.get('server_stopped') is not True or execution.get('owned_loopback_port_closed') is not True or
            execution.get('cases') != seal['cases']):
        raise ContractError('Prediction execution report or stopped-server boundary differs')
    expected = [row['case_id'] for row in plan['cases']]
    actual = [row['case_id'] for row in seal['cases']]
    if len(expected) != len(set(expected)) or len(actual) != len(set(actual)) or set(actual) != set(expected):
        raise ContractError('Prediction case membership differs')
    for paired in seal['cases']:
        arms = [row['arm'] for row in paired['arms']]
        if len(arms) != len(set(arms)) or set(arms) != set(plan['arms']):
            raise ContractError('Prediction paired-arm membership differs')
        for arm in paired['arms']:
            folder = safe_child(root, 'arms/'+paired['case_id']+'/'+arm['arm'])
            if Path(arm['path']).resolve() != folder:
                raise ContractError('Arm output path escapes its case/arm scope')
            for name, path in (('result', folder/'result.json'), ('seal', folder/'seal.json'),
                               ('verification', folder.parent/(arm['arm']+'-verification.json'))):
                if Path(arm[name]['path']).resolve() != path:
                    raise ContractError('Arm proof path differs')
    return execution


def _expected_config(plan):
    receipt = _open_proof(plan['model_receipt'])
    servers = [r for r in receipt['runtime_files'] if Path(r['path']).name == 'llama-server.exe']
    if len(servers) != 1:
        raise ContractError('Pinned native server is ambiguous')
    settings = plan['backend']
    return {'schema_version': 1, 'endpoint': 'http://127.0.0.1:55581',
        'model_id': 'Qwen/Qwen2.5-14B-Instruct-GGUF@' + receipt['revision'],
        'model_provenance': {'weights_sha256': {r['name']: r['sha256'] for r in receipt['items'] if r['name'].endswith('.gguf')},
            'runtime_sha256': servers[0]['sha256'], 'acquisition_receipt_sha256': plan['model_receipt']['sha256']},
        'retrieval': settings['retrieval'], 'max_output_tokens': settings['max_output_tokens'],
        'timeout_seconds': settings['timeout_seconds'], 'seed': settings['seed']}


def _configuration_binding(result, plan, config):
    """Baselines and zero-call arms retain the same planned upper ceilings."""
    from tools.science.role_backend import ROLE_SELECTION_POLICY
    actual = result.get('configuration', {})
    if (actual.get('budget') != plan['budget'] or actual.get('retrieval') != config['retrieval'] or
            actual.get('backend_id') != 'local-structured-selection-v1' or
            actual.get('backend_provenance', {}).get('config') != config or
            plan.get('backend', {}).get('selection_policy') != ROLE_SELECTION_POLICY or
            actual.get('backend_provenance', {}).get('selection_policy') != ROLE_SELECTION_POLICY):
        raise ContractError('Arm model/retrieval/budget configuration differs from the frozen plan')


def reference_bindings(case, store, references, source_build_sha256):
    """Validate exact Q1 joins, using the reference's documented build-ID field.

    Science2's version_applicability.snapshot_id names its *build report hash*,
    not the per-case Snapshot.snapshot_id. Both the frozen build and case world
    are verified upstream; comparing this field to a per-case ID would be wrong.
    """
    indexed = {}
    sources = {p['artifact_id']: p for p in store.source_proofs}
    source_urls = {n.source_id: n.source_url for n in store.snapshot.sources}
    for reference in references:
        if reference['case_id'] != case.case_id:
            continue
        validation = validate_reference(reference)
        if reference['hypothesis_sha256'] != case.hypothesis.key:
            raise ContractError('Q1 reference hypothesis differs')
        prefix = case.case_id + ':'
        identity = reference['reference_id']
        if not identity.startswith(prefix) or identity == prefix:
            raise ContractError('Q1 reference lacks an exact observation identity')
        observation_id = identity[len(prefix):]
        if observation_id in indexed:
            raise ContractError('Duplicate Q1 reference identity')
        record = store.lookup(observation_id)
        observation = encode(record.observation)
        if reference['version_applicability'].get('snapshot_id') != source_build_sha256:
            raise ContractError('Q1 reference source build differs')
        if (reference['source_row_sha256'] != observation['method']['parameters'].get('source_row_sha256') or
                reference['statement'] != observation['statement'] or
                reference['context'].get('observed') != observation['context'] or
                reference['context'].get('source_metrics') != observation['source_metrics'] or
                reference['context'].get('missingness') != observation['missingness']):
            raise ContractError('Q1 reference statement/context/original-row binding differs')
        locator = observation['source_locator']
        raw = sources.get(locator.get('source_id'))
        if raw is None or len(reference['source_evidence']) != 1:
            raise ContractError('Q1 reference original source identity is missing')
        source = reference['source_evidence'][0]
        if (source['artifact_sha256'] != raw['sha256'] or source['locator'] != locator or
                (locator['source_id'] in source_urls and source['url'] != source_urls[locator['source_id']])):
            raise ContractError('Q1 reference raw source fingerprint/locator differs')
        if reference['reference_level'] != 'ai_source_adjudicated' or reference['validation_claim'] != 'source_grounded_ai_reference':
            raise ContractError('This evaluation accepts only the qualified AI Q1 reference level')
        indexed[observation_id] = {'reference': reference, 'eligible': validation['eligible_for_source_grounded_comparison'],
                                  'category': observation['category']}
    return indexed


def evaluate_case(case, store, result, references, source_build_sha256):
    """Describe verified selected annotations; unreviewed is unknown, not wrong."""
    if (result.get('case_id') != case.case_id or result.get('case_sha256') != fingerprint(case) or
            result.get('hypothesis_sha256') != case.hypothesis.key or result.get('features') != {} or
            result.get('probability') is not None or result.get('provider_spend_usd') != 0):
        raise ContractError('Result case or withheld-prediction contract differs')
    categories = {c.value for c in Category}
    if set(result.get('coverage', {})) != categories or set(result.get('selections', {})) - categories:
        raise ContractError('Result category inventory differs')
    indexed = reference_bindings(case, store, references, source_build_sha256)
    metrics = {}
    for category in Category:
        coverage = result['coverage'][category.value]
        available = sum(r.observation.status == EvidenceStatus.OBSERVED for r in store.query(case, category))
        nonobserved = [{'observation_id': r.observation.observation_id, 'status': r.observation.status.value}
                       for r in store.query(case, category) if r.observation.status != EvidenceStatus.OBSERVED]
        if coverage.get('available_in_collected_case_world') != available or coverage.get('nonobserved') != nonobserved:
            raise ContractError('Reported source-world coverage differs from admission')
        selected = result.get('selections', {}).get(category.value, [])
        if coverage.get('selected') != len(selected):
            raise ContractError('Selected coverage count differs')
        retrieved = coverage.get('retrieval', {}).get('selected_ids', [])
        if len(retrieved) != len(set(retrieved)) or set(selected) - set(retrieved):
            raise ContractError('Selected claims escape bounded retrieval')
        refs = {identity for identity, row in indexed.items() if row['category'] == category.value and row['eligible']}
        metrics[category.value] = {'status': coverage['status'], 'reason': coverage.get('reason'),
            'available_in_collected_world': available, 'retrieved_candidates': len(retrieved),
            'selected_claims': len(selected), 'exact_normalized_copies': 0,
            'eligible_Q1_reference_universe': len(refs), 'Q1_references_in_retrieved_candidates': len(refs & set(retrieved)),
            'selected_Q1_overlap': 0, 'supported': 0, 'contradicted': 0, 'uncertain': 0, 'unavailable': 0,
            'unreviewed_unknown': 0, 'reference_not_applicable_unknown': 0,
            'source_nonobserved': nonobserved, 'missingness_fields': {}}
    claim_ids = set()
    claim_rows = []
    for claim in result['claims']:
        identity, category = claim['observation_id'], claim['category']
        if identity in claim_ids or category not in categories:
            raise ContractError('Duplicated or unknown selected claim')
        claim_ids.add(identity)
        record = store.lookup(identity)
        source = encode(record)
        if (claim['source_claim_sha256'] != fingerprint(record) or claim['evidence'] != source or
                category != record.observation.category.value or
                identity not in result['selections'].get(category, [])):
            raise ContractError('Selected ID/statement/context/source claim is not an exact admitted copy')
        row = metrics[category]
        row['exact_normalized_copies'] += 1
        for field in source['observation']['missingness']:
            row['missingness_fields'][field] = row['missingness_fields'].get(field, 0) + 1
        joined = indexed.get(identity)
        answer = 'unreviewed_unknown' if joined is None else 'reference_not_applicable_unknown' if not joined['eligible'] else joined['reference']['answer']
        row[answer] += 1
        if joined is not None and joined['eligible']:
            row['selected_Q1_overlap'] += 1
        claim_rows.append({'observation_id': identity, 'category': category, 'exact_normalized_copy': True,
            'source_claim_sha256': claim['source_claim_sha256'], 'Q1_annotation': answer,
            'source_row_sha256': source['observation']['method']['parameters'].get('source_row_sha256'),
            'missingness': source['observation']['missingness'], 'scientific_truth': 'not_established'})
    selected_ids = [identity for ids in result['selections'].values() for identity in ids]
    if len(selected_ids) != len(set(selected_ids)) or set(selected_ids) != claim_ids:
        raise ContractError('Committed claims and selected IDs differ')
    return {'case_id': case.case_id, 'case_sha256': fingerprint(case), 'hypothesis_sha256': case.hypothesis.key,
        'arm': result['arm'], 'status': result['status'], 'categories': metrics, 'claims': claim_rows,
        'calls': result['calls'], 'usage': result['usage'], 'measured_usage': result['measured_usage'],
        'estimated_usage': result['estimated_usage'], 'elapsed_seconds': result['elapsed_seconds'],
        'source_world_proofs_sha256': fingerprint(store.source_proofs),
        'interpretation': 'Copied resource annotations and conditional AI Q1 reference overlap; no therapeutic or clinical truth.'}


def evaluate(predictions_seal_path, expected_seal_sha256, references_path, expected_references_sha256, output):
    """Verify frozen predictions before opening evaluator answers; write fresh output."""
    from tools.science.run_comparison import validate_plan, _load_case
    from tools.science.comparison_workflow import verify_case
    output = Path(output).resolve()
    journal = RunJournal(output, kind='build')
    started = time.monotonic()
    proofs = []
    try:
        code_inventory = _freeze_evaluator_code(output)
        proofs.extend(proof for row in code_inventory for proof in row.values())
        seal_path = Path(predictions_seal_path).resolve()
        seal = _read_pinned(seal_path, expected_seal_sha256)
        if (seal.get('schema_version') != 1 or seal.get('role') != 'sealed_predictions_before_evaluator_join' or
                seal.get('evaluator_answers_opened_by_launcher') is not False or seal.get('clinical_probabilities') is not None):
            raise ContractError('Prediction seal boundary differs')
        proofs.append(_expected_proof(seal_path, expected_seal_sha256))
        plan = _open_proof(seal['plan'])
        validate_plan(plan)
        root = Path(plan['root']).resolve()
        execution = _seal_scope(seal_path, seal, plan)
        proofs.extend([seal['plan'], seal['execution_report']])
        for name in ('protocol', 'source_build', 'catalog', 'role_policy', 'model_receipt', 'original_model_receipt'):
            _open_proof(plan[name])
            proofs.append(plan[name])
        proofs.extend(plan['code'])
        proofs.extend(_executed_code_proofs(plan))
        expected_cases = {r['case_id']: r for r in plan['cases']}
        config = _expected_config(plan)
        model_verification, launcher_proofs, model_signatures = _launcher_boundary(seal, plan, config)
        proofs.extend(launcher_proofs)
        policy = _open_proof(plan['role_policy'])
        validated, stores, inventories = [], {}, []
        # Do not open reference answers until every arm's exact outputs verify.
        for paired in seal['cases']:
            case, store = _load_case(plan, expected_cases[paired['case_id']])
            stores[case.case_id] = (case, store)
            planned = expected_cases[case.case_id]
            proofs.extend([planned['case'], planned['snapshot'], *_source_input_proofs(store)])
            arms = [a['arm'] for a in paired['arms']]
            if len(arms) != len(set(arms)) or set(arms) != set(plan['arms']):
                raise ContractError('Prediction paired-arm membership differs')
            for arm in paired['arms']:
                folder = safe_child(root, 'arms/' + case.case_id + '/' + arm['arm'])
                if Path(arm['path']).resolve() != folder:
                    raise ContractError('Arm output path escapes its case/arm scope')
                for name, expected_path in (('result', folder/'result.json'), ('seal', folder/'seal.json'),
                        ('verification', folder.parent/(arm['arm']+'-verification.json'))):
                    if Path(arm[name]['path']).resolve() != expected_path:
                        raise ContractError('Arm proof path differs')
                    _open_proof(arm[name])
                    proofs.append(arm[name])
                validation = verify_case(folder, case, store, backend_config=config, role_policy=policy)
                _workflow_code_binding(folder, plan)
                nested, inventory = _sealed_inventory(folder, arm['seal'])
                proofs.extend(nested); inventories.append(inventory)
                if validation != _open_proof(arm['verification']):
                    raise ContractError('Saved verification differs from independent recomputation')
                result = _open_proof(arm['result'])
                _configuration_binding(result, plan, config)
                if (result['arm'] != arm['arm'] or result['status'] != arm['status'] or result['calls'] != arm['calls'] or result['usage'] != arm['usage']):
                    raise ContractError('Sealed arm summary differs')
                validated.append((case, store, result))
                journal.append('arm_independently_verified', case_id=case.case_id, arm=arm['arm'], result_sha256=arm['result']['sha256'])
        journal.append('all_predictions_verified_before_reference_join', seal_sha256=expected_seal_sha256)
        document = _read_pinned(references_path, expected_references_sha256)
        if document.get('schema_version') != 1 or document.get('role') != 'evaluation_only':
            raise ContractError('References must remain evaluator-only')
        references = document['references']
        if any(r['case_id'] not in expected_cases for r in references) or len({r['reference_id'] for r in references}) != len(references):
            raise ContractError('Reference membership or identity differs')
        proofs.append(_expected_proof(references_path, expected_references_sha256))
        rows = [evaluate_case(c, s, r, references, plan['source_build']['sha256']) for c, s, r in validated]
        aggregate = []
        for arm in plan['arms']:
            members = [r for r in rows if r['arm'] == arm]
            totals = Counter()
            for row in members:
                for category in row['categories'].values():
                    for name in ('selected_claims', 'exact_normalized_copies', 'eligible_Q1_reference_universe', 'selected_Q1_overlap',
                                 'supported', 'contradicted', 'uncertain', 'unavailable', 'unreviewed_unknown', 'reference_not_applicable_unknown'):
                        totals[name] += category[name]
            aggregate.append({'arm': arm, 'cases': len(members), 'statuses': dict(Counter(r['status'] for r in members)),
                'counts': dict(totals), 'calls': sum(r['calls'] for r in members),
                'elapsed_seconds': sum(r['elapsed_seconds'] for r in members),
                'measured_usage': {k: sum(r['measured_usage'][k] for r in members) for k in ('input_tokens', 'output_tokens', 'cost_usd')},
                'estimated_usage': {k: sum(r['estimated_usage'][k] for r in members) for k in ('input_tokens', 'output_tokens', 'cost_usd')}})
        overlaps = []
        for case_id in expected_cases:
            by_arm = {r['arm']: {c['observation_id'] for c in r['claims']} for r in rows if r['case_id'] == case_id}
            for left, right in combinations(plan['arms'], 2):
                union = by_arm[left] | by_arm[right]
                overlaps.append({'case_id': case_id, 'arms': [left, right], 'intersection': len(by_arm[left] & by_arm[right]),
                                 'union': len(union), 'jaccard': len(by_arm[left] & by_arm[right])/len(union) if union else None})
        # Recheck exact parsed input versions before emitting a completed report.
        proofs = _unique_proofs(proofs)
        for proof in proofs:
            if sha256_file(Path(proof['path'])) != proof['sha256'] or Path(proof['path']).stat().st_size != proof['bytes']:
                raise ContractError('Evaluation input changed during comparison')
        for folder, names in inventories:
            _check_inventory(folder, names)
        _check_model_signatures(model_signatures)
        report = {'schema_version': 1, 'role': 'evaluation_only', 'status': 'postseal_descriptive_source_evaluation_completed',
            'created_at_utc': datetime.now(timezone.utc).isoformat(), 'prediction_seal_sha256': expected_seal_sha256,
            'evaluator_code_sha256': sha256_file(Path(__file__)),
            'evaluation_code': code_inventory,
            'model_byte_verification': model_verification,
            'launcher_evidence': 'Hash-bound trusted Python launcher records; not independent native attestation.',
            'reference_sha256': expected_references_sha256, 'cases': len(expected_cases), 'arms': len(plan['arms']),
            'Q1_reference_records': len(references), 'per_case_arm': rows, 'per_arm': aggregate, 'paired_selection_overlap': overlaps,
            'execution_resources': {k: execution.get(k) for k in ('elapsed_seconds', 'peak_python_memory_bytes', 'peak_native_memory_bytes', 'native_memory_reason')},
            'elapsed_evaluation_seconds': time.monotonic()-started, 'proofs': proofs,
            'scientific_truth': 'not_established', 'clinical_evaluation': 'withheld', 'clinical_metrics': None,
            'probabilities': None, 'provider_spend_usd': 0,
            'limitations': ['ID-constrained copying can mechanically guarantee normalized-source fidelity.',
                'Sparse AI Q1 coverage is not selection accuracy; unreviewed statements remain unknown.',
                'Q2-Q4 external context is not a mandatory sourceworld fact.',
                'Purposive cases and source/model errors can be dependent; no P values, confidence intervals or clinical performance claims.',
                'Original-row fidelity is assessed separately from normalized copying and AI reference annotation.']}
        write_json(output/'report.json', report)
        journal.append('evaluation_completed', report_sha256=sha256_file(output/'report.json'))
        return report
    except BaseException as error:
        write_json(output/'failure.json', {'status': 'failed', 'error_class': type(error).__name__, 'reason': str(error),
            'created_at_utc': datetime.now(timezone.utc).isoformat(), 'clinical_metrics': None, 'probabilities': None})
        journal.fail(error, 'postseal_evaluation')
        raise
    finally:
        journal.close()
        write_json(output/'seal.json', {'schema_version': 1, 'files': [_proof(p) for p in sorted(output.rglob('*')) if p.is_file() and p != output/'seal.json']})


def select_original_audit_rows(claims, case_id, seen):
    """Choose at most two distinct physical rows from final asof claims only."""
    from tools.science.reference_packets import select_observations, _physical_key
    eligible, local = [], set()
    for claim in claims:
        observation = claim['evidence']['observation']
        key = _physical_key(observation)
        if key not in seen and key not in local:
            eligible.append(observation)
            local.add(key)
    selected = select_observations(eligible, case_id, maximum=2, seed='science7-postseal-original-row-audit')
    seen.update(_physical_key(observation) for observation in selected)
    return selected


def audit_selected_rows(predictions_seal_path, expected_seal_sha256, evaluation_report_path,
                        expected_evaluation_sha256, output):
    """Independently audit up to twenty final asof rows against original bytes.

    Requires the completed, independently hash-pinned post-seal evaluation. This
    technical source check neither creates Q1 answers nor upgrades scientific truth.
    """
    from asof.ingest import _load_case_pack
    from asof.provenance import InputGraph, catalog_index
    from tools.science.reference_packets import _mappings, audit_observation
    from tools.framework.run_pilot import SourceAudit
    from tools.science.run_comparison import validate_plan, _load_case
    from tools.science.comparison_workflow import verify_case
    output = Path(output).resolve()
    journal = RunJournal(output, kind='build')
    started = time.monotonic()
    try:
        code_inventory = _freeze_evaluator_code(output)
        evaluation = _read_pinned(evaluation_report_path, expected_evaluation_sha256)
        if (evaluation.get('status') != 'postseal_descriptive_source_evaluation_completed' or
                evaluation.get('role') != 'evaluation_only' or evaluation.get('prediction_seal_sha256') != expected_seal_sha256):
            raise ContractError('Original-row audit requires completed matching post-seal evaluation')
        seal_path = Path(predictions_seal_path).resolve()
        seal = _read_pinned(seal_path, expected_seal_sha256)
        if (seal.get('schema_version') != 1 or seal.get('role') != 'sealed_predictions_before_evaluator_join' or
                seal.get('evaluator_answers_opened_by_launcher') is not False or seal.get('clinical_probabilities') is not None):
            raise ContractError('Original-row audit prediction seal differs')
        plan = _open_proof(seal['plan'])
        validate_plan(plan)
        _seal_scope(seal_path, seal, plan)
        report_members = [(row['case_id'], row['arm']) for row in evaluation['per_case_arm']]
        expected_members = {(row['case_id'], arm) for row in plan['cases'] for arm in plan['arms']}
        if (len(report_members) != len(set(report_members)) or set(report_members) != expected_members or
                evaluation.get('cases') != len(plan['cases']) or evaluation.get('arms') != len(plan['arms'])):
            raise ContractError('Original-row audit evaluation membership differs')
        build = _open_proof(plan['source_build'])
        bundle = Path(plan['source_build']['path']).parent
        pack_path = bundle/'case-pack.json'
        definitions, _, digest = _load_case_pack(pack_path, build['case_pack']['sha256'])
        if digest != build['case_pack']['sha256']:
            raise ContractError('Original-row audit case pack differs')
        definitions = {definition.case_id: definition for definition in definitions}
        if set(definitions) != {row['case_id'] for row in plan['cases']}:
            raise ContractError('Original-row audit frozen case membership differs')
        # The build and execution can pin different catalog revisions. Execution
        # admission below enforces every source's role against the exact frozen
        # execution policy; whole-catalog metadata changes are not case changes.
        catalog_binding = {'source_build_policy_sha256': build['inspection']['catalog_sha256'],
            'execution_policy_sha256': plan['catalog']['sha256'],
            'admission_policy': 'Pinned execution catalog; all lineage nodes rechecked, including evaluator-only denial.'}
        policy = catalog_index(_open_proof(plan['catalog']))
        config, roles = _expected_config(plan), _open_proof(plan['role_policy'])
        if (evaluation.get('model_byte_verification', {}).get('status') != 'actual_model_and_runtime_bytes_verified' or
                evaluation['model_byte_verification'].get('receipt_sha256') != plan['model_receipt']['sha256']):
            raise ContractError('Original audit requires completed matching model byte verification')
        _, launcher_proofs, _ = _launcher_boundary(seal, plan, config, verify_native=False)
        source_audit, source_proofs, seen, rows, summaries = SourceAudit(), {}, set(), [], []
        input_proofs = [_expected_proof(evaluation_report_path, expected_evaluation_sha256),
                        _expected_proof(seal_path, expected_seal_sha256), seal['plan'], seal['execution_report'],
                        plan['source_build'], plan['catalog'], plan['role_policy'], _expected_proof(pack_path, digest),
                        *plan['code'], plan['model_receipt'], plan['original_model_receipt'], plan['protocol'],
                        *(proof for row in code_inventory for proof in row.values()),
                        *_executed_code_proofs(plan), *launcher_proofs]
        inventories = []
        reported = {r['case_id']: r for r in evaluation['per_case_arm'] if r['arm'] == 'asof'}
        paired = {r['case_id']: r for r in seal['cases']}
        for planned in plan['cases']:
            case, store = _load_case(plan, planned)
            input_proofs.extend(_source_input_proofs(store))
            case_arms = [arm for arm in paired[case.case_id]['arms'] if arm['arm'] == 'asof']
            if len(case_arms) != 1 or case.case_id not in reported:
                raise ContractError('Original-row audit lacks a unique final asof arm')
            arm = case_arms[0]
            folder = Path(arm['path']).resolve()
            if folder != safe_child(Path(plan['root']), 'arms/'+case.case_id+'/asof'):
                raise ContractError('Original-row audit asof path differs')
            result = _open_proof(arm['result'])
            _configuration_binding(result, plan, config)
            _open_proof(arm['seal'])
            validation = verify_case(folder, case, store, backend_config=config, role_policy=roles)
            _workflow_code_binding(folder, plan)
            nested, inventory = _sealed_inventory(folder, arm['seal'])
            input_proofs.extend(nested); inventories.append(inventory)
            if validation != _open_proof(arm['verification']):
                raise ContractError('Original-row audit verification differs')
            if (result['arm'] != 'asof' or result['status'] != arm['status'] or result['calls'] != arm['calls'] or
                    result['usage'] != arm['usage'] or reported[case.case_id]['case_sha256'] != fingerprint(case) or
                    reported[case.case_id]['hypothesis_sha256'] != case.hypothesis.key):
                raise ContractError('Original-row audit asof summary or case scope differs')
            actual_ids = {claim['observation_id'] for claim in result['claims']}
            if actual_ids != {claim['observation_id'] for claim in reported[case.case_id]['claims']}:
                raise ContractError('Original-row audit selected statements differ from evaluated asof claims')
            chosen = select_original_audit_rows(result['claims'], case.case_id, seen)
            case_folder = Path(planned['case']['path']).parent
            raw_case = _open_proof(planned['case'])
            raw_snapshot = _open_proof(planned['snapshot'])
            graph = InputGraph(store.snapshot, case_folder, policy)
            nodes, mapping_refs, disease_name = _mappings(source_audit, case_folder, raw_case, raw_snapshot,
                definitions[case.case_id], graph, source_proofs)
            audited = [audit_observation(source_audit, observation, case=case, nodes=nodes, graph=graph,
                mapping_refs=mapping_refs, symbol=definitions[case.case_id].symbol, disease_name=disease_name,
                proofs=source_proofs) for observation in chosen]
            rows.extend(audited)
            summaries.append({'case_id': case.case_id, 'final_asof_claims': len(result['claims']),
                'original_rows_audited': len(audited), 'requested': 2,
                'coverage': 'two_distinct_final_claims_audited' if len(audited) == 2 else 'fewer_distinct_final_claims_available_no_substitution',
                'observation_ids': [r['observation_id'] for r in audited]})
            input_proofs.extend([planned['case'], planned['snapshot'], arm['result'], arm['seal'], arm['verification'],
                                 _proof(case_folder/'identifier-validation.json')])
            journal.append('case_original_rows_audited', **summaries[-1])
        for proof in source_proofs.values():
            source_audit.source(proof, proof['raw_root'])
            if sha256_file(safe_child(Path(proof['raw_root']), proof['receipt_path'])) != proof['receipt_sha256']:
                raise ContractError('Original-row audit source receipt changed')
        input_proofs = _unique_proofs(input_proofs)
        for proof in input_proofs:
            if (sha256_file(Path(proof['path'])) != proof['sha256'] or
                    Path(proof['path']).stat().st_size != proof['bytes']):
                raise ContractError('Original-row audit input changed during inspection')
        for folder, names in inventories:
            _check_inventory(folder, names)
        write_json(output/'original-row-audits.json', rows)
        report = {'schema_version': 1, 'role': 'evaluation_only', 'status': 'postseal_original_row_audit_completed',
            'created_at_utc': datetime.now(timezone.utc).isoformat(), 'prediction_seal_sha256': expected_seal_sha256,
            'evaluator_code_sha256': sha256_file(Path(__file__)),
            'evaluation_code': code_inventory,
            'evaluation_report_sha256': expected_evaluation_sha256, 'requested_rows': 20, 'audited_rows': len(rows),
            'catalog_binding': catalog_binding,
            'model_byte_verification_scope': 'Requires matching completed evaluation model/runtime byte verification; launcher proofs revalidated, weights not rehashed by this audit.',
            'cases': summaries, 'selection': 'Up to two category/provider/study-spread distinct physical final asof statements per case; no substitution.',
            'source_proofs': list(source_proofs.values()), 'input_proofs': input_proofs,
            'rows_proof': _proof(output/'original-row-audits.json'), 'elapsed_seconds': time.monotonic()-started,
            'source_files_hashed': len(source_audit.hashes), 'provider_spend_usd': 0,
            'new_AI_reference_answers': 0, 'scientific_truth': 'not_established', 'clinical_metrics': None,
            'interpretation': 'Original-row identity/statement/metrics/context/missingness/lineage technical fidelity only.'}
        write_json(output/'report.json', report)
        journal.append('original_audit_completed', report_sha256=sha256_file(output/'report.json'))
        return report
    except BaseException as error:
        write_json(output/'failure.json', {'status': 'failed', 'error_class': type(error).__name__, 'reason': str(error)})
        journal.fail(error, 'postseal_original_row_audit')
        raise
    finally:
        journal.close()
        write_json(output/'seal.json', {'schema_version': 1, 'files': [_proof(p) for p in sorted(output.rglob('*')) if p.is_file() and p != output/'seal.json']})
