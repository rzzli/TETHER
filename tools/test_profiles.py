"""Reconcile a complete isolated census against explicit component test scopes.

This classifies tests; it neither executes them nor changes the existing gate.
An absent classification or a changed source invalidates the report.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.test_inventory import flatten, source_inventory, write_new


def select_suite(root, policy, *, profile='maintained', reverse=False):
    """Select an explicit current scope without importing historical suites.

    This is independent of census execution. It does not certify unselected
    profiles, and it leaves the existing all-current validation gate unchanged.
    """
    root = Path(root).resolve()
    sources = source_inventory(root)
    files, profiles = policy['files'], policy['profiles']
    if policy.get('schema_version') != 1 or profile not in profiles:
        raise ValueError('Unknown test profile')
    if {row['path'] for row in sources} != set(files):
        raise ValueError('Every test file requires exactly one scope classification')
    declarations = {row['path'] + '::' + method['owner'] + '.' + method['method']
                    for row in sources for method in row['declared']}
    overrides = policy.get('overrides', {})
    if set(overrides) - declarations:
        raise ValueError('Stale method scope override')
    if any(name not in profiles for name in (*files.values(), *overrides.values())):
        raise ValueError('Unknown test profile')
    loader = unittest.TestLoader()
    selected, excluded = {}, []
    for source in sources:
        path = source['path']
        if files[path] != profile and not any(key.startswith(path + '::') and value == profile
                                              for key, value in overrides.items()):
            continue
        tests = loader.loadTestsFromName(source['module'])
        if loader.errors:
            raise ValueError('Profile collection failed: ' + '\n'.join(loader.errors))
        for test in flatten(tests):
            method = getattr(test, test._testMethodName)
            actual_path = Path(inspect.getsourcefile(method)).resolve().relative_to(root).as_posix()
            key = actual_path + '::' + method.__qualname__
            assigned = overrides.get(key, files.get(actual_path))
            if assigned is None:
                raise ValueError('Collected method has an unclassified source')
            if assigned == profile:
                selected.setdefault(test.id(), test)
            else:
                excluded.append(dict(id=test.id(), profile=assigned))
    if not selected:
        raise ValueError('Selected profile contains no tests')
    ids = sorted(selected, reverse=reverse)
    return unittest.TestSuite(selected[name] for name in ids), dict(
        profile=profile, selected=len(ids), test_ids=ids, excluded_from_mixed_modules=excluded,
        reverse=reverse, unselected_profiles_executed=False)


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
