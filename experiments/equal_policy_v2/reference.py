"""Versioned installed-product adapter; immutable v1 validators stay unchanged.

Native production and validation use the same explicitly qualified interpreter.
Only trusted-runtime metadata capture differs from the original adapter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

# Script execution with -I admits only the experiment tree, never repo src.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from equal_policy.reference import (materialize_core, materialize_outer,
                                    runtime_identity, validate_bundle)

SUPPORTED_VERSION_PAIRS = {('0.5.1', '0.3.12'), ('0.5.2', '0.3.13')}


def trusted_runtime(qualification_root):
    import asof
    import tether
    from tether._presentation import code_proof
    versions = dict(tether=tether.__version__, asof=asof.__version__)
    if (versions['tether'], versions['asof']) not in SUPPORTED_VERSION_PAIRS:
        raise ValueError('Unsupported corrected-BG02 package version pair')
    qualified = Path(qualification_root).resolve()
    environment = qualified / 'environment'
    for value in (sys.executable, asof.__file__, tether.__file__):
        if not Path(value).resolve().is_relative_to(environment):
            raise ValueError('Product/interpreter is outside the requested qualified installation')
    qualification = qualified / 'QUALIFICATION.json'
    document = json.loads(qualification.read_bytes())
    if document.get('status') != 'PASS':
        raise ValueError('Installed qualification did not complete successfully')
    if document.get('versions') != {'tether-target-agents': versions['tether'],
                                    'asof-target-agents': versions['asof']}:
        raise ValueError('Qualified package versions differ from actual installation')
    hash_file = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    core = Path(asof.__file__).parent
    wheels = sorted((qualified / 'wheels').glob('*.whl'))
    if len(wheels) != 2:
        raise ValueError('Expected exactly one core and one facade wheel')
    wheel_proofs = document.get('wheel_proofs', [])
    if len(wheel_proofs) != 2 or {Path(item['path']).resolve() for item in wheel_proofs} != {p.resolve() for p in wheels}:
        raise ValueError('Qualified wheel inventory differs from actual wheels')
    for package, entry in (('asof', asof.__file__), ('tether', tether.__file__)):
        matching = [item for item in wheel_proofs if item['distribution'] == package + '-target-agents']
        if len(matching) != 1 or matching[0].get('record_verified') is not True:
            raise ValueError('Missing verified distribution wheel proof')
        proof = matching[0]
        wheel = Path(proof['path'])
        if hash_file(wheel) != proof['sha256'] or wheel.stat().st_size != proof['bytes']:
            raise ValueError('Qualified wheel bytes changed')
        package_root = Path(entry).parent
        observed = {package + '/' + p.relative_to(package_root).as_posix(): hash_file(p)
                    for p in package_root.rglob('*.py')}
        expected = {name: sha for name, sha in proof['source_sha256'].items()
                    if name.startswith(package + '/') and name.endswith('.py')}
        if observed != expected:
            raise ValueError('Actual installed Python payload differs from qualified wheel')
    return dict(schema_version=1, versions=versions,
        launcher_proof=code_proof(),
        core_code_sha256={p.relative_to(core).as_posix(): hash_file(p)
                          for p in sorted(core.rglob('*.py'))},
        qualification=dict(path=str(qualification), sha256=hash_file(qualification)),
        wheels=[dict(filename=p.name, sha256=hash_file(p), bytes=p.stat().st_size) for p in wheels],
        runtime_paths=runtime_identity())


def rerender_dossier(root):
    """Native prose refresh after an explicit unscored mutation, before reseal."""
    from types import SimpleNamespace
    from asof.artifacts import dossier
    from asof.agents import Usage
    from asof.contracts import Case, Claim, Snapshot
    from asof.chrono import Exclusion
    from asof.features import FeatureVector
    from asof.journal import read_chain
    from asof.scorer import Prediction
    from asof.serde import decode, read_json, read_ledger_json, encode
    from asof.workflow import Budget, PlanStep, RunResult
    root = Path(root)
    run, inputs = read_json(root / 'run.json'), read_json(root / 'inputs.json')
    fields = {key: run[key] for key in ('snapshot_id', 'profile', 'backend_id', 'status',
        'budget', 'calls', 'usage', 'plan', 'coverage', 'measured_usage', 'estimated_usage')}
    fields.update(case=inputs['case'], claims=read_ledger_json(root / 'ledger.json')['claims'],
        features=read_json(root / 'features.json'), prediction=read_json(root / 'prediction.json'),
        trace=encode(read_chain(root / 'trace.jsonl')), configuration=inputs['configuration'])
    for key, kind in (('case', Case), ('claims', tuple[Claim, ...]), ('features', FeatureVector),
                     ('prediction', Prediction), ('budget', Budget), ('plan', tuple[PlanStep, ...]),
                     ('usage', Usage), ('measured_usage', Usage), ('estimated_usage', Usage)):
        fields[key] = decode(kind, fields[key])
    store = SimpleNamespace(snapshot=decode(Snapshot, inputs['snapshot']),
                            exclusions=decode(tuple[Exclusion, ...], run['exclusions']))
    payload = dossier(RunResult(**fields), store).encode('utf-8')
    (root / 'dossier.md').write_bytes(payload)
    return dict(unscored=True, operation='rerender_dossier', bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--descriptor', type=Path)
    parser.add_argument('--materialize')
    parser.add_argument('--identity', action='store_true')
    parser.add_argument('--trusted-runtime', type=Path)
    parser.add_argument('--rerender-dossier', type=Path)
    args = parser.parse_args()
    if args.trusted_runtime:
        answer = trusted_runtime(args.trusted_runtime)
    elif args.rerender_dossier:
        answer = rerender_dossier(args.rerender_dossier)
    elif args.identity:
        answer = runtime_identity()
    else:
        descriptor = json.loads(args.descriptor.read_bytes())
        answer = (materialize_outer(args.root, descriptor)
                  if args.materialize in ('valid_outer_schema1', 'valid_outer_policy')
                  else materialize_core(args.root, descriptor, args.materialize)
                  if args.materialize else validate_bundle(args.root, descriptor))
    print(json.dumps(answer, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
