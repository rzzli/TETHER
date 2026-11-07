"""Unscored native corpus preparation and explicit, auditable fault mutations.

No expected decision is computed here. Both validators receive the same final
bytes. Resealing intentionally removes simple byte-integrity shortcuts from
semantic counterexamples; it is not a valid repair of the semantic fault.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    Path(path).write_bytes(canonical(value) + b'\n')


def _chain(events):
    previous = None
    for index, event in enumerate(events):
        event.pop('sha256', None)
        event.update(sequence=index, previous_sha256=previous)
        event['sha256'] = previous = digest(event)
    return b''.join(canonical(event) + b'\n' for event in events)


def _reseal(run, receipt, *, trace=None):
    if trace is not None:
        payload = _chain(trace)
        (run / 'trace.jsonl').write_bytes(payload)
        (run / 'journal.jsonl').write_bytes(payload)
    for name in receipt['outputs']:
        receipt['outputs'][name] = file_hash(run / name)
    for name in receipt.get('auxiliary_outputs', {}):
        receipt['auxiliary_outputs'][name] = file_hash(run / name)
    save(run / 'receipt.json', receipt)


def mutate_core(root, descriptor, mutation):
    """Only modifies this freshly materialized fictional bundle."""
    run = root / descriptor['paths']['run_dir']
    if mutation == 'none':
        return
    if mutation == 'journal_chain':
        path = run / 'journal.jsonl'
        events = [json.loads(line) for line in path.read_bytes().splitlines()]
        events[-1]['details']['reserved']['input_tokens'] += 1
        # Deliberately preserve old event hashes.
        path.write_bytes(b''.join(canonical(event) + b'\n' for event in events))
        return
    if mutation == 'wrong_external_anchor':
        descriptor['anchors']['receipt_sha256'] = '0' * 64
        return
    if mutation == 'original_raw_bytes':
        (root / 'input/source.json').write_bytes(b'{"fictional":"altered original"}\n')
        return
    if mutation == 'auxiliary_request_bytes':
        path = run / 'request.json'
        value = load(path)
        value['review_enabled'] = not value['review_enabled']
        save(path, value)
        return
    receipt = load(run / 'receipt.json')
    trace = [json.loads(line) for line in (run / 'trace.jsonl').read_bytes().splitlines()]
    if mutation == 'omit_raw_parent_proof_reseal':
        receipt['sources'] = [p for p in receipt['sources'] if p['artifact_id'] != 'source-1']
    elif mutation == 'journal_claim_differs_reseal':
        event = next(event for event in trace if event['event'] == 'claim_committed')
        event['details']['claim']['evidence']['observation']['statement'] += ' Fictional contradiction.'
    elif mutation == 'run_call_count_reseal':
        value = load(run / 'run.json')
        value['calls'] += 1
        save(run / 'run.json', value)
    elif mutation == 'feature_value_reseal':
        value = load(run / 'features.json')
        value['values']['genetic_support']['value'] = 0.125
        save(run / 'features.json', value)
        trace[-1]['details']['feature_sha256'] = digest(value)
    elif mutation == 'prediction_contribution_reseal':
        value = load(run / 'prediction.json')
        value['contributions']['genetic_support']['log_odds'] += 0.25
        save(run / 'prediction.json', value)
        trace[-1]['details']['prediction_sha256'] = digest(value)
    elif mutation == 'trace_fingerprint_reseal':
        trace[-1]['details']['feature_sha256'] = 'f' * 64
    elif mutation == 'claim_fingerprint_reseal':
        value = load(run / 'ledger.json')
        value['claims'][0]['admitted_fingerprint'] = 'f' * 64
        save(run / 'ledger.json', value)
        next(event for event in trace if event['event'] == 'claim_committed')['details']['claim'] = value['claims'][0]
    elif mutation == 'replay_request_fingerprint_reseal':
        inputs = load(run / 'inputs.json')
        config = inputs['configuration']
        proof = config['backend_provenance']
        entries = next(iter(proof['document']['responses'].values()))
        entries[0]['request_sha256'] = 'f' * 64
        replay_path = Path(proof['path'])
        if not replay_path.resolve().is_relative_to(root.resolve()):
            raise RuntimeError('Fictional replay path escaped fresh bundle')
        save(replay_path, proof['document'])
        proof['sha256'] = file_hash(replay_path)
        save(run / 'inputs.json', inputs)
        receipt['input_fingerprint'] = digest(inputs)
        value = load(run / 'run.json')
        value['input_fingerprint'] = digest(inputs)
        save(run / 'run.json', value)
        next(event for event in trace if event['event'] == 'plan')['details']['configuration'] = config
        request = load(run / 'request.json')
        request['backend_provenance'] = proof
        save(run / 'request.json', request)
        next(event for event in trace if event['event'] == 'inputs_archived')['details']['request_sha256'] = digest(request)
    elif mutation in ('local_request_fingerprint_reseal', 'local_response_usage_reseal'):
        archive = load(run / 'backend-execution.json')
        entry = archive['attempts'][0]
        if mutation == 'local_request_fingerprint_reseal':
            entry['request_sha256'] = 'f' * 64
        else:
            entry['response']['tokens_evaluated'] += 1
            entry['response_sha256'] = digest(entry['response'])
        save(run / 'backend-execution.json', archive)
    else:
        raise ValueError('Unimplemented declared sealed mutation: ' + mutation)
    _reseal(run, receipt, trace=trace)
    descriptor.setdefault('anchors', {})['receipt_sha256'] = file_hash(run / 'receipt.json')


def mutate_outer(root, descriptor, mutation):
    if mutation in ('none', 'valid_outer'):
        return
    run = root / descriptor['paths']['run_dir']
    manifest = load(run / 'tether-manifest.json')
    receipt = load(run / 'tether-receipt.json')
    journal = [json.loads(line) for line in (run / 'attempt/journal.jsonl').read_bytes().splitlines()]
    if mutation == 'process_supervision_reseal':
        manifest['supervision']['process_reaped'] = False
        next(e for e in journal if e['event'] == 'engine_returned')['details']['supervision'] = manifest['supervision']
    elif mutation == 'outer_code_proof_reseal':
        proof = manifest['launcher']
        proof['code'][next(iter(proof['code']))]['sha256'] = 'f' * 64
        next(e for e in journal if e['event'] == 'tether_prepared')['details']['launcher_proof_sha256'] = digest(proof)
    elif mutation == 'dossier_reseal':
        with (run / 'dossier.md').open('ab') as stream:
            stream.write(b'\nFictional unauthorized extra assertion.\n')
    elif mutation in ('copied_control_reseal', 'projection_reseal'):
        key = 'case' if mutation == 'copied_control_reseal' else 'projection'
        binding = load(run / 'catalog-policy/binding.json')
        control = binding['controls'][key]
        path = run / control['path']
        value = load(path)
        if key == 'case':
            value['hypothesis']['target_id'] = 'FICTIONAL:ALTERED-TARGET'
        else:
            value['datasets'][0]['roles'] = ['evaluation_only']
        save(path, value)
        control.update(sha256=file_hash(path), bytes=path.stat().st_size)
        save(run / 'catalog-policy/binding.json', binding)
        binding_descriptor = manifest['artifact_policy']
        binding_descriptor.update(sha256=file_hash(run / binding_descriptor['path']),
                                  bytes=(run / binding_descriptor['path']).stat().st_size)
        next(e for e in journal if e['event'] == 'artifact_policy_prepared')['details']['binding'] = binding_descriptor
    else:
        raise ValueError('Unimplemented declared outer mutation: ' + mutation)
    for name, proof in manifest['artifacts'].items():
        proof.update(sha256=file_hash(run / name), bytes=(run / name).stat().st_size)
    save(run / 'tether-manifest.json', manifest)
    receipt['manifest_sha256'] = file_hash(run / 'tether-manifest.json')
    journal[-1]['details']['manifest_sha256'] = receipt['manifest_sha256']
    (run / 'attempt/journal.jsonl').write_bytes(_chain(journal))
    receipt['journal_sha256'] = file_hash(run / 'attempt/journal.jsonl')
    save(run / 'tether-receipt.json', receipt)
    descriptor['anchors']['receipt_sha256'] = file_hash(run / 'tether-receipt.json')


def prepare_sealed_case(bundle_dir, spec, descriptor, *, python):
    """Callback consumes the already mutated original inputs, never the oracle."""
    root = Path(bundle_dir).resolve()
    recipe = spec['preparation']['recipe']
    if 'policy_recipe' in recipe:
        from .policy_cases import prepare_policy_sources
        descriptor, pending = prepare_policy_sources(root, spec, descriptor)
        if descriptor['operation'] == 'prepare_run':
            return descriptor
        producer = 'valid_outer_policy'
        mutation = pending or recipe['policy_recipe']
    else:
        producer = recipe.get('sealed_producer', 'offline')
        mutation = recipe.get('sealed_mutation', 'none')
    instruction = root / 'producer-descriptor.json'
    save(instruction, descriptor)
    command = [str(python), '-I', '-B', str(Path(__file__).with_name('reference.py')),
               '--root', str(root), '--descriptor', str(instruction), '--materialize', producer]
    process = subprocess.run(command, capture_output=True, timeout=180, check=False)
    (root / 'producer-stdout.txt').write_bytes(process.stdout)
    (root / 'producer-stderr.txt').write_bytes(process.stderr)
    save(root / 'producer-execution.json', dict(argv=command, returncode=process.returncode,
        unscored=True, expected_decision_consumed=False))
    if process.returncode:
        raise RuntimeError('Native producer failed; retained stdout/stderr, exit ' + str(process.returncode))
    descriptor = json.loads(process.stdout)
    if producer in ('valid_outer_schema1', 'valid_outer_policy'):
        mutate_outer(root, descriptor, mutation)
    else:
        mutate_core(root, descriptor, mutation)
    return descriptor
