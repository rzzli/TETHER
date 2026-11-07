"""Versioned runtime routing for the corrected equal-policy comparison.

Core, schema, lineage, replay and policy checks reuse the immutable original
implementation. Only outer runtime version selection and entrypoint routing
are restated here. Both supported version pairs retain actual per-call code
and metadata checks; matching a historical manifest alone is insufficient.
"""
from pathlib import Path
import hashlib
import time

from equal_policy.independent import (
    descriptor_contract, require, child, read_json, prepare_core, verify_core,
    inspect_core, PolicyError, UnsupportedPolicy,
)
from equal_policy.independent_policy import (
    no_links, need, json_file, NORMAL, LARGE, pin, outer_envelope,
    validate_process_limits, canonical, file_inventory, stable, secure_path,
    chain, digest, supervision, verify_binding, prepare_policy, inspect_outer,
)
from .independent_runtime import approved_versions


def verify_outer(output, anchor, trusted_runtime, *, expected_policy=None):
    output = no_links(output); deadline = time.monotonic() + 300
    check = lambda value, message: need(value, message, 'EP-VERIFY-03')
    check(not (output / 'tether-failure.json').exists(), 'Retained failure cannot be success')
    receipt, raw = json_file(output / 'tether-receipt.json', deadline, NORMAL)
    receipt_sha = hashlib.sha256(raw).hexdigest()
    if anchor is not None: check(pin(anchor) == receipt_sha, 'External outer receipt anchor differs')
    outer_envelope(receipt, {'manifest_sha256', 'journal_sha256', 'engine_receipt_sha256'})
    manifest, raw = json_file(output / 'tether-manifest.json', deadline, NORMAL)
    check(hashlib.sha256(raw).hexdigest() == receipt['manifest_sha256'], 'Manifest bytes differ')
    outer_envelope(manifest, {'command', 'invocation_sha256', 'engine', 'projection', 'launcher', 'artifacts', 'process_limits', 'supervision', 'artifact_policy'})
    if expected_policy is not None:
        need((manifest['artifact_policy'] is not None) == expected_policy,
             'Requested policy variant differs from actual sealed surface', 'EP-WIRE-01')
    check(type(manifest['process_limits']) is dict and set(manifest['process_limits']) == {'timeout_seconds', 'max_output_bytes'}, 'Process limits fields')
    limits = validate_process_limits(manifest['process_limits'])
    check(manifest['command'] in ('run', 'demo') and manifest['engine'] == dict(path='engine', receipt_sha256=receipt['engine_receipt_sha256']), 'Engine identity binding')
    check(type(trusted_runtime) is dict and type(trusted_runtime.get('schema_version')) is int and trusted_runtime['schema_version'] == 1 and
          approved_versions(trusted_runtime.get('versions')), 'Trusted current runtime required')
    from .independent_runtime import launcher_proof
    check(canonical(manifest['launcher']) == canonical(launcher_proof(trusted_runtime)), 'Launcher identity differs from current installed runtime')
    pin(manifest['invocation_sha256'])
    check(manifest['projection'] == dict(source='engine/dossier.md', target='dossier.md', transform='identity_dossier_v2'), 'Projection declaration')
    check(type(manifest['artifacts']) is dict, 'Outer artifact inventory')
    expected = set(manifest['artifacts']) | {'tether-manifest.json', 'tether-receipt.json', 'attempt/journal.jsonl'}
    files, directories = file_inventory(output)
    expected_dirs = {p.as_posix() for name in expected for p in Path(name).parents if p.as_posix() != '.'}
    check(files == expected and directories == expected_dirs, 'Whole outer inventory differs')
    for name, proof in manifest['artifacts'].items():
        # Inventory hashing is streamed without imposing metadata's size cap on
        # ledgers or arbitrary retained assets; individual parsers apply theirs.
        observed = stable(secure_path(output, name), deadline, collect=False)
        check(canonical(dict(path=name, **observed)) == canonical(proof), 'Outer artifact bytes/size/path differ')
    payload = stable(output / 'attempt/journal.jsonl', deadline, NORMAL)
    check(hashlib.sha256(payload).hexdigest() == receipt['journal_sha256'], 'Outer journal hash differs')
    events = chain(payload); binding = manifest['artifact_policy']
    schedule = ['run_reserved', 'tether_prepared'] + (['artifact_policy_prepared'] if binding is not None else []) + ['engine_dispatch', 'engine_returned', 'tether_completed']
    check([e['event'] for e in events] == schedule and all(type(e['sequence']) is int for e in events), 'Outer journal schedule')
    check(events[-1]['details'] == dict(manifest_sha256=receipt['manifest_sha256'], engine_receipt_sha256=receipt['engine_receipt_sha256']), 'Outer final event')
    prepared = dict(command=manifest['command'], launcher_proof_sha256=digest(manifest['launcher']), process_limits=limits, artifact_policy_requested=binding is not None)
    dispatched = dict(argv_sha256=manifest['invocation_sha256'], output='engine', process_limits=limits)
    returned = dict(returncode=0, supervision=manifest['supervision'])
    check(canonical(events[1]['details']) == canonical(prepared) and canonical(events[-3]['details']) == canonical(dispatched) and
          canonical(events[-2]['details']) == canonical(returned), 'Outer journal proof/dispatch differs')
    stdout = stable(output / 'engine-stdout.txt', deadline, NORMAL)
    stderr = stable(output / 'engine-stderr.txt', deadline, NORMAL)
    supervision(manifest['supervision'], limits, len(stdout), len(stderr))
    source = stable(output / 'engine/dossier.md', deadline, LARGE)
    projected = stable(output / 'dossier.md', deadline, LARGE)
    check(source.startswith(b'# TETHER dossier:') and projected == source, 'Dossier presentation differs')
    for name in ('journal.jsonl', 'trace.jsonl'): stable(output / 'engine' / name, deadline, NORMAL)
    engine = verify_core(output / 'engine', receipt['engine_receipt_sha256'], trusted_runtime=trusted_runtime)
    check(engine['semantic_consistency'] == 'verified' and engine.get('code_matches_current') is True and engine['status'] == 'completed', 'Inner source/current-code/completion qualification')
    if binding is None:
        check(not (output / 'catalog-policy').exists(), 'Unbound policy directory')
        policy = dict(status='unavailable_schema1_compatibility', scientific_validation='not_established')
    else:
        check(canonical(events[2]['details']) == canonical(dict(binding=binding)), 'Policy preparation event differs')
        policy = verify_binding(output, binding, deadline)
    return {**engine, 'verification': dict(status='integrity_verified', receipt_sha256=receipt_sha,
        external_anchor_checked=anchor is not None, launcher_code_verified=True, source_binding='current_originals',
        semantic_consistency='verified', artifact_policy=policy, scientific_validation='not_established')}


def validate_policy_bundle(root, request, *, scratch_dir=None):
    operation = request['operation']
    if operation == 'prepare_run': return prepare_policy(root, request, scratch_dir)
    output = child(root, request['paths']['run_dir'])
    if operation == 'inspect_run': return dict(recovery=inspect_outer(output))
    trusted_path = request['paths'].get('trusted_runtime')
    need(trusted_path, 'Pinned runtime manifest required for outer verification', 'EP-VERIFY-03')
    trusted, _ = json_file(child(root, trusted_path), time.monotonic() + 300, NORMAL)
    return verify_outer(output, request.get('anchors', {}).get('receipt_sha256'), trusted,
                        expected_policy=request['variant'] == 'artifact_policy_v2')


def validate_bundle(root, descriptor, *, scratch_dir=None):
    """Validate existing files. Unsupported parity is explicit, never accepted."""
    stage = 'descriptor'
    checked = []
    identity = dict(schema_version=1, control_id=descriptor.get('control_id') if type(descriptor) is dict else None)
    try:
        descriptor = descriptor_contract(descriptor)
        variant = descriptor.get('variant')
        operation = descriptor.get('operation')
        require(variant in ('core_v2_catalog1', 'artifact_policy_v2')
            and operation in ('prepare_run', 'verify_run', 'inspect_run'), 'EP-WIRE-01', 'Unknown variant/operation')
        checked.append('descriptor')
        stage = operation
        run_dir = child(root, descriptor['paths']['run_dir']) if operation != 'prepare_run' else None
        outer = run_dir is not None and any((run_dir / name).exists() for name in (
            'tether-manifest.json', 'tether-receipt.json', 'tether-failure.json', 'attempt'))
        if variant == 'artifact_policy_v2' or outer:
            observed = validate_policy_bundle(Path(root), descriptor, scratch_dir=scratch_dir)
        elif operation == 'prepare_run':
            observed = prepare_core(Path(root), descriptor)
        elif operation == 'verify_run':
            trusted = read_json(child(root, descriptor['paths']['trusted_runtime'])) if descriptor['paths'].get('trusted_runtime') else None
            observed = verify_core(run_dir, (descriptor.get('anchors') or {}).get('receipt_sha256'),
                                   trusted_runtime=trusted)
        else:
            observed = dict(recovery=inspect_core(run_dir))
        checked.append(operation)
        return dict(**identity, decision='inspect_only' if operation == 'inspect_run' else 'accept', stage=stage,
                    violated_obligations=[], checked_scope=checked, observables=observed)
    except PolicyError as error:
        return dict(**identity, decision='reject', stage=stage, violated_obligations=[error.obligation],
                    checked_scope=checked, observables={}, error=str(error))
    except (ModuleNotFoundError, UnsupportedPolicy) as error:
        return dict(**identity, decision='unsupported', stage=stage, violated_obligations=[], checked_scope=checked,
                    observables={}, error=str(error))
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError) as error:
        return dict(**identity, decision='reject', stage=stage, violated_obligations=['EP-IO-01'],
                    checked_scope=checked, observables={}, error=type(error).__name__ + ': ' + str(error))
    except (OSError, KeyError, TypeError, ValueError, RecursionError) as error:
        return dict(**identity, decision='error', stage=stage, violated_obligations=[],
                    checked_scope=checked, observables={}, error=type(error).__name__ + ': ' + str(error))
