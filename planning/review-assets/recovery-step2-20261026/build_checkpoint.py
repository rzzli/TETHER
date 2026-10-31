"""Copy the current repository and representative dependencies without editing originals."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INVENTORY = ROOT / 'data/cache/recovery-checkpoint-inventory-20261026'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = ROOT / 'data/reference' / ('recovery-checkpoint-' + stamp)
    output.mkdir(parents=True, exist_ok=False)
    objects = output / 'objects/sha256'
    objects.mkdir(parents=True)
    entries, index = [], {}

    def put(logical, expected, *, source=None, payload=None, role='dependency', run=None):
        if source is not None:
            actual, size = digest(source), source.stat().st_size
        else:
            actual, size = hashlib.sha256(payload).hexdigest(), len(payload)
        if expected is not None and actual != expected:
            raise ValueError('Pinned checkpoint source differs: ' + str(logical))
        target = objects / actual[:2] / actual
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            if source is not None:
                shutil.copyfile(source, target)
            else:
                target.write_bytes(payload)
            if digest(target) != actual:
                raise ValueError('Checkpoint copy differs')
        key = (str(logical), actual, role, run)
        if key not in index:
            row = dict(logical_path=str(logical), sha256=actual, bytes=size,
                       object=target.relative_to(output).as_posix(), role=role, run=run)
            index[key] = row
            entries.append(row)
        return index[key]

    names = subprocess.check_output(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT
    ).decode('utf-8').split('\0')
    repository = []
    for name in sorted(set(n for n in names if n)):
        path = ROOT / name
        if not path.is_file() or not path.resolve().is_relative_to(ROOT):
            raise ValueError('Non-file/escaped repository member')
        if name.startswith(('data/raw/', 'data/derived/', 'data/benchmark/', 'data/cache/', 'runs/')):
            if path.name != '.gitkeep':
                raise ValueError('Bulk/evaluator payload in repository file scope')
        row = put(str(path), None, source=path, role='repository')
        destination = output / 'repository' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        repository.append(dict(path=name, sha256=row['sha256'], bytes=row['bytes']))

    representatives = json.loads((INVENTORY / 'representatives.json').read_text(encoding='utf-8'))
    runs = []
    for representative in representatives:
        run = representative['kind']
        run_path = Path(representative['path'])
        for path in sorted(run_path.rglob('*')):
            if path.is_file():
                put(str(path), None, source=path, role='run', run=run)
        for proof in representative['proofs']:
            if not proof.get('exists'):
                continue  # Excluded future fixture members are explicitly recorded below.
            expected = proof.get('expected_sha256') or proof['observed_sha256']
            path = Path(proof['path'])
            if digest(path) == expected:
                put(str(path), expected, source=path, run=run)
            else:
                old = representative.get('recoverable_old_code')
                if not old or old['sha256'] != expected or (ROOT / old['path']).resolve() != path.resolve():
                    raise ValueError('Unrecoverable code/dependency: ' + str(path))
                payload = subprocess.check_output(['git', 'show', old['git_commit'] + ':' + old['path']], cwd=ROOT)
                put(str(path), expected, payload=payload, role='historical_code', run=run)
        runs.append(dict(kind=run, logical_root=str(run_path),
                         receipt_sha256=representative['observed_receipt_sha256'],
                         observed_verification=representative['verification'],
                         unresolved_members=representative['unresolved_relative_members']))

    current_pins = json.loads((ROOT / 'data/cache/question-pilot-controller-v2-code-validation-20261025.json').read_text(encoding='utf-8'))['code_pins']
    if any(digest(ROOT / name) != pin for name, pin in current_pins.items()):
        raise ValueError('Current tested code changed before checkpoint')
    full = ROOT / 'planning/review-assets/opus-response-20261026/full-validation.json'
    validation = json.loads(full.read_text(encoding='utf-8'))
    if validation['status'] != 'passed' or validation['tests'] != dict(run=1262, failures=0, errors=0, skipped=[]):
        raise ValueError('Passing validation unavailable')
    manifest = dict(schema_version=1, kind='recovery_checkpoint', created_at_utc=datetime.now(timezone.utc).isoformat(),
                    repository_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
                    repository_logical_root=str(ROOT), raw_logical_root='E:\\projects_data\\drug_target_agents_data',
                    repository=repository, entries=entries, runs=runs,
                    tested_code_pins=current_pins,
                    validation=dict(path=str(full), sha256=digest(full), result=validation),
                    environment=dict(python=sys.version, executable=sys.executable,
                                     dependency_versions=json.loads((INVENTORY/'environment.json').read_text(encoding='utf-8'))),
                    verification_scope='Copied bytes and anchored identities; relocation is a separate gate',
                    off_machine_copy=False, original_receipts_modified=False,
                    historical_code_execution=False, model_weights_copied=False,
                    clinical_outcome_payloads_read=False,
                    excluded_future_fixture_policy='Preserved repository fixtures, not admitted dependency failures')
    manifest_path = output / 'checkpoint.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    # Rehash every stored object after all writes; a copied manifest is not proof of copied bytes.
    unique = {row['object']: row for row in entries}
    for relative, row in unique.items():
        path = output / relative
        if path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
            raise ValueError('Checkpoint final object verification failed')
    result = dict(status='passed_checkpoint_bytes_not_relocation', checkpoint=str(output),
                  checkpoint_sha256=digest(manifest_path), repository_members=len(repository),
                  logical_entries=len(entries), unique_objects=len(unique),
                  unique_object_bytes=sum(row['bytes'] for row in unique.values()),
                  representative_runs=len(runs), unchanged_tested_code_pins=len(current_pins),
                  original_receipts_modified=False, historical_code_recovered=True,
                  old_bounded_run_current_verification='fails_live_code_pin; restoration verification pending',
                  current_head_hosted_ci='unverified_invalid_github_auth',
                  off_machine_backup='not_established', whole_project_complete=False)
    result_path = Path(__file__).with_name('checkpoint-acceptance.json')
    result_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
