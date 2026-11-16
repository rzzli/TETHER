"""Reconcile a complete isolated census against explicit component test scopes.

This classifies tests; it neither executes them nor changes the existing gate.
An absent classification or a changed source invalidates the report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.test_inventory import source_inventory, write_new


def classify(root, census, policy):
    if census.get('status') != 'collection_complete_not_execution':
        raise ValueError('A complete isolated census is required')
    if policy.get('schema_version') != 1:
        raise ValueError('Unsupported test-scope policy')
    sources = source_inventory(root)
    current = {row['path']: row['sha256'] for row in sources}
    recorded = {row['path']: row['sha256'] for row in census['sources']}
    if len(recorded) != len(census['sources']) or current != recorded:
        raise ValueError('Census source inventory is stale or duplicated')
    files, profiles = policy['files'], policy['profiles']
    if set(current) != set(files):
        raise ValueError('Every test file requires exactly one scope classification')
    if not profiles or any(value not in profiles for value in files.values()):
        raise ValueError('Unknown test profile')
    cases = {}
    for module in census['modules']:
        for case in module['cases']:
            identifier = case['id']
            if identifier in cases and cases[identifier] != case:
                raise ValueError('Conflicting collected test identity')
            cases[identifier] = case
    if not cases:
        raise ValueError('Census contains no cases')
    declared = {(row['path'], method['owner'], method['method'])
                for row in sources for method in row['declared']}
    collected = {(case['path'], case['owner'], case['method']) for case in cases.values()}
    if declared - collected:
        raise ValueError('Census omits declared test methods')
    overrides = policy.get('overrides', {})
    used = set()
    result = []
    for identifier, case in sorted(cases.items()):
        path = case['path']
        if path not in files:
            raise ValueError('Collected method has an unclassified source')
        key = path + '::' + case['owner'] + '.' + case['method']
        profile = overrides.get(key, files[path])
        if profile not in profiles:
            raise ValueError('Unknown method override profile')
        if key in overrides:
            used.add(key)
        result.append(dict(case, profile=profile, execution_status='not_established_by_census'))
    if used != set(overrides):
        raise ValueError('Stale method scope override')
    groups = {name: [case['id'] for case in result if case['profile'] == name]
              for name in profiles}
    return dict(schema_version=1, status='scope_reconciled_not_execution',
                authority=policy['authority'], profiles=profiles,
                counts={name: len(ids) for name, ids in groups.items()},
                source_files=len(sources), unique_cases=len(result),
                methods=result, test_ids=groups)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--policy', type=Path, default=ROOT / 'tools/test-profiles.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError(args.output)
    raw = args.inventory.read_bytes()
    policy = args.policy.read_bytes()
    result = classify(args.root, json.loads(raw), json.loads(policy))
    result.update(census_sha256=hashlib.sha256(raw).hexdigest(),
                  policy_sha256=hashlib.sha256(policy).hexdigest())
    write_new(args.output, result)
    print(json.dumps({'status': result['status'], 'counts': result['counts']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
