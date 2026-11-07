"""Deliberately weaker diagnostic and reject-all comparison controls.

Neither control claims equal-policy semantics. The hash/schema arm can admit
scientifically ineligible or contradictory but consistently rehashed records.
"""
from __future__ import annotations

from pathlib import Path

from .independent import (LEDGER_LIMIT, RUN_FILES, PolicyError, child, file_digest,
                          object_fields, read_chain, read_json)
from .independent_schema import decode, require


def _result(descriptor, decision, **extras):
    return dict(schema_version=1, control_id=descriptor.get('control_id'), decision=decision,
        stage=descriptor.get('operation', 'descriptor'), violated_obligations=[],
        checked_scope=['diagnostic_control'], observables={}, **extras)


def reject_all(root, descriptor, *, scratch_dir=None):
    return _result(descriptor, 'reject', reason='Reject-all sanity control; no policy validation performed')


def _hashed(path, expected):
    require(file_digest(path) == expected, 'EP-VERIFY-01', 'Declared checksum mismatch')


def _prepare(root, descriptor):
    paths = descriptor['paths']
    decode('Case', read_json(child(root, paths['case'])))
    snapshot_path = child(root, paths['snapshot'])
    snapshot = decode('Snapshot', read_json(snapshot_path))
    require(snapshot['schema_version'] == 2, 'EP-WIRE-01', 'Unsupported snapshot schema')
    for artifact in snapshot['artifacts']:
        path = child(snapshot_path.parent, artifact['path'])
        _hashed(path, artifact['sha256'])
        packet = decode('Packet', read_json(path))
        require(packet['schema_version'] == 2, 'EP-WIRE-01', 'Unsupported packet schema')
    raw = Path(snapshot['raw_root'] or snapshot_path.parent)
    for source in snapshot['sources']:
        base = snapshot_path.parent if source['computed_at'] is not None else raw
        _hashed(child(base, source['path']), source['sha256'])
        if source['receipt_path']:
            _hashed(child(raw, source['receipt_path']), source['receipt_sha256'])
            read_json(child(raw, source['receipt_path']))
    for key, schema in (('scorer', 'Scorer'), ('replay', 'ReplayDocument')):
        if paths.get(key):
            decode(schema, read_json(child(root, paths[key])))
    for key in ('catalog', 'local_model'):
        if paths.get(key):
            require(type(read_json(child(root, paths[key]))) is dict, 'EP-WIRE-01', 'Metadata object required')
    if paths.get('catalog_policy'):
        policy = read_json(child(root, paths['catalog_policy']))
        object_fields(policy, ('schema_version', 'products', 'artifacts', 'uses'), 'EP-WIRE-01', 'Artifact policy')
        require(policy['schema_version'] == 2 and all(type(policy[key]) is list for key in ('products', 'artifacts', 'uses')),
                'EP-WIRE-01', 'Artifact policy top-level shape invalid')
        roots = read_json(child(root, paths['policy_roots']))['roots']
        for artifact in policy['artifacts']:
            _hashed(child(Path(roots[artifact['root_alias']]), artifact['relative_path']), artifact['sha256'])


def _verify_engine(root):
    receipt = read_json(root / 'receipt.json')
    require(receipt.get('schema_version') == 2 and set(receipt.get('outputs', {})) == set(RUN_FILES),
            'EP-WIRE-01', 'Unsupported/incomplete receipt schema')
    for name, checksum in receipt['outputs'].items():
        _hashed(child(root, name), checksum)
    for name, checksum in receipt.get('auxiliary_outputs', {}).items():
        _hashed(child(root, name), checksum)
    inputs = read_json(root / 'inputs.json')
    decode('Case', inputs['case'])
    decode('Snapshot', inputs['snapshot'])
    if inputs['scorer'] is not None:
        decode('Scorer', inputs['scorer'])
    decode('[Claim]', read_json(root / 'ledger.json', LEDGER_LIMIT)['claims'])
    decode('FeatureVector', read_json(root / 'features.json'))
    decode('Prediction', read_json(root / 'prediction.json'))
    # Only chain bytes/shape, not lifecycle, claims, reservations or accounting.
    read_chain(root / 'journal.jsonl')
    read_chain(root / 'trace.jsonl')


def _verify(root, descriptor):
    run = child(root, descriptor['paths']['run_dir'])
    outer = (run / 'tether-receipt.json').exists()
    if outer:
        receipt = read_json(run / 'tether-receipt.json')
        _hashed(run / 'tether-manifest.json', receipt['manifest_sha256'])
        _hashed(run / 'attempt/journal.jsonl', receipt['journal_sha256'])
        manifest = read_json(run / 'tether-manifest.json')
        for relative, proof in manifest['artifacts'].items():
            _hashed(child(run, relative), proof['sha256'])
        _verify_engine(run / 'engine')
    else:
        _verify_engine(run)
    anchor = (descriptor.get('anchors') or {}).get('receipt_sha256')
    if anchor:
        _hashed(run / ('tether-receipt.json' if outer else 'receipt.json'), anchor)


def hash_schema(root, descriptor, *, scratch_dir=None):
    try:
        require(type(descriptor) is dict and descriptor.get('schema_version') == 1, 'EP-WIRE-01', 'Invalid descriptor')
        operation = descriptor['operation']
        if operation == 'prepare_run':
            _prepare(Path(root), descriptor)
        elif operation == 'verify_run':
            _verify(Path(root), descriptor)
        elif operation == 'inspect_run':
            run = child(root, descriptor['paths']['run_dir'])
            journal = run / 'attempt/journal.jsonl' if (run / 'attempt').is_dir() else run / 'journal.jsonl'
            read_chain(journal, partial=True)
        else:
            raise PolicyError('EP-WIRE-01', 'Unknown operation')
        return _result(descriptor, 'inspect_only' if operation == 'inspect_run' else 'accept',
            reason='Hash/schema diagnostic only; temporal, lineage, hypothesis, scientific and execution semantics unchecked')
    except PolicyError as error:
        result = _result(descriptor, 'reject', reason=str(error))
        result['violated_obligations'] = [error.obligation]
        return result
    except Exception as error:
        return _result(descriptor, 'error', reason=str(error), error_class=type(error).__name__)
