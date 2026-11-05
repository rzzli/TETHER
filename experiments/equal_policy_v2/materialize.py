"""Versioned corpus preparation with a clean recorded-request counterexample.

All unchanged mutation recipes and byte encodings use the immutable original.
The EP075 correction refreshes only deterministic prose after its deliberate
semantic mutation, then reseals; it never repairs the invalid request hash.
"""
from pathlib import Path
import json
import subprocess

from equal_policy import materialize as original
from equal_policy.materialize import canonical, digest, file_hash, load, save, mutate_outer


def mutate_core(root, descriptor, mutation, *, python):
    original.mutate_core(root, descriptor, mutation)
    if mutation != 'replay_request_fingerprint_reseal':
        return
    run = Path(root) / descriptor['paths']['run_dir']
    command = [str(python), '-I', '-B', str(Path(__file__).with_name('reference.py')),
               '--rerender-dossier', str(run)]
    result = subprocess.run(command, capture_output=True, check=False, timeout=180)
    for name, payload in (('rerender-stdout.json', result.stdout), ('rerender-stderr.txt', result.stderr)):
        with (Path(root) / name).open('xb') as stream:
            stream.write(payload)
    with (Path(root) / 'rerender-execution.json').open('xb') as stream:
        stream.write(canonical(dict(argv=command, returncode=result.returncode,
            unscored=True, expected_decision_consumed=False)) + b'\n')
    if result.returncode:
        raise RuntimeError('Native prose refresh failed; retained unscored attempt')
    observed = json.loads(result.stdout)
    if (observed.get('operation') != 'rerender_dossier' or observed.get('unscored') is not True
            or observed.get('sha256') != file_hash(run / 'dossier.md')
            or observed.get('bytes') != (run / 'dossier.md').stat().st_size):
        raise ValueError('Native prose refresh returned inconsistent output proof')
    receipt = load(run / 'receipt.json')
    receipt['outputs']['dossier.md'] = file_hash(run / 'dossier.md')
    save(run / 'receipt.json', receipt)
    descriptor['anchors']['receipt_sha256'] = file_hash(run / 'receipt.json')


def prepare_sealed_case(bundle_dir, spec, descriptor, *, python):
    """Callback consumes the already mutated original inputs, never the oracle."""
    root = Path(bundle_dir).resolve()
    recipe = spec['preparation']['recipe']
    if 'policy_recipe' in recipe:
        from equal_policy.policy_cases import prepare_policy_sources
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
        mutate_core(root, descriptor, mutation, python=python)
    return descriptor
