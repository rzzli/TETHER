"""Read-only repository audit; does not open clinical outcome payloads or dispatch models."""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def digest(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def main():
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    paths = [p for p in paths if p]
    inventory = {}
    for prefix in ('src/', 'tools/', 'tests/', 'planning/', 'docs/', 'memory/', 'data/'):
        members = [p for p in paths if p.startswith(prefix)]
        python = [p for p in members if p.endswith('.py')]
        functions = classes = lines = 0
        for name in python:
            source = (ROOT / name).read_text(encoding='utf-8-sig')
            tree = ast.parse(source, filename=name)
            lines += len(source.splitlines())
            functions += sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree))
            classes += sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
        inventory[prefix] = dict(tracked_files=len(members), python_files=len(python),
                                 python_lines=lines, functions=functions, classes=classes)
    guard_path = ROOT / 'data/cache/question-pilot-controller-v2-code-validation-20261025.json'
    guard = json.loads(guard_path.read_text())
    mismatch = [name for name, pin in guard['code_pins'].items()
                if not (ROOT / name).is_file() or digest(ROOT / name) != pin]
    catalog = json.loads((ROOT / 'data/catalog/sources.json').read_text())
    registry = json.loads((ROOT / 'planning/run-registry.json').read_text())
    canonical = next(r for r in registry['entries'] if r['id'] == registry['canonical_pilot_id'])
    pins = [{'path': r['path'], 'matches': digest(ROOT / r['path']) == r['sha256']}
            for r in canonical['reports']]
    for r in canonical['cases']:
        pins.append({'path': r['path'] + '/receipt.json',
                     'matches': digest(ROOT / r['path'] / 'receipt.json') == r['receipt_sha256']})
    protected = {
        'data/benchmark/cohorts/science4-outcomes-20261019T024500Z/adjudication/normalized-outcomes.json':
            '9392df7cec11704f3f0abaddc12e4196349ace1aba55b4da0af0f14d41bb26f2',
        'data/benchmark/labels/endpoint-followup-feasibility-20261021/adjudication-v1/normalized-outcomes.json':
            'c3195a27565debe2c0b891f8aecffbae8a63988dfe2fd62b9e5aed37f0353398',
    }
    report = dict(
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
        tracked_inventory=inventory,
        unchanged_tested_code=dict(pins_checked=len(guard['code_pins']), mismatches=mismatch,
                                  prior_guard_sha256=digest(guard_path)),
        catalog=dict(providers=len(catalog['providers']), datasets=len(catalog['datasets']),
                     review_date=catalog['review_date']),
        canonical_registry_pins=pins,
        protected_payload_hashes_only={p: digest(ROOT / p) == pin for p, pin in protected.items()},
        limitations=['AST inventory is coverage of structure, not line-by-line correctness proof',
                     'Clinical payloads hashed only; no label contents inspected',
                     'Canonical receipt hashes checked here; source-inclusive verification is separate',
                     'No bulk original re-download or full data-inventory rehash'],
        provider_spend_usd=0, model_calls=0,
    )
    output = Path(__file__).with_name('audit-evidence.json')
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
