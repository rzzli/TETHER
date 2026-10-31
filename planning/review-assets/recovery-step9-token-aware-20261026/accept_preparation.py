"""Accept this bounded engineering slice only after its retained checks pass."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
CACHE = ROOT/'data/cache/recovery-step9-token-aware-validation-v2-20261026'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def pin(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size)


full, code = load(CACHE/'full-validation.json'), load(CACHE/'code-validation.json')
assert full['status'] == code['status'] == 'passed'
assert not full['tests']['failures'] and not full['tests']['errors'] and not full['tests']['skipped']
assert full['tests']['run'] >= 1582 and full['required_probes_exit_code'] == 0
assert code['unchanged_code'] and code['protected_unchanged']
for name, digest in code['source_pins'].items():
    assert sha(ROOT/name) == digest, name
for name, digest in code['protected_hashes'].items():
    assert sha(ROOT/name) == digest  # Hash only; never parse protected outcomes.
peer = load(HERE/'IMPLEMENTATION-PEER-REVIEW-final.json')
assert peer['tests']['count'] == 8 and peer['tests']['failures'] == peer['tests']['errors'] == peer['tests']['skipped'] == 0
for item in peer['pins']:
    raw = (ROOT/item['path']).read_bytes()
    if item['path'] == 'tests/test_study_preparation_peer.py':
        raw = raw.replace(b'from tests import test_study_source_preparation as source_fixtures',
                          b'import test_study_source_preparation as source_fixtures').replace(
                          b'from tests import test_study_tokenization as token_fixtures',
                          b'import test_study_tokenization as token_fixtures')
    assert hashlib.sha256(raw).hexdigest() == item['sha256'], item['path']
installed_path = ROOT/'data/cache/r09prep-installed-20261026/guarded-installed-verification.json'
installed = load(installed_path)
assert installed['status'] == 'passed' and len(installed['results']) == 7
assert all(item['status'] == 'passed' for item in installed['results'])
for key in ('original_root_access_attempts','archived_execution_attempts','repository_tools_import_attempts','network_or_child_attempts'):
    assert installed[key] == []
real = load(HERE/'REAL-PREPARATION.json')
assert real['status'] == 'source_and_token_preparation_verified'
assert real['generation_calls'] == real['provider_spend_usd'] == 0
assert len(real['records']) == len(real['children']) == 6
assert real['input_reservation'] == 28241 and real['output_reservation'] == 6144
assert real['elapsed_preparation_seconds'] <= 300
assert not real['protected_read_attempts'] and not real['network_attempts']
assert sha(Path(real['output'])/'receipt.json') == real['receipt_sha256']
real_installed = load(HERE/'installed-preparation-verification.json')
assert real_installed['status'] == 'passed_installed_source_and_token_replay'
assert real_installed['quote_count'] == 6 and not any(real_installed['guards'].values())
for name in ('frozen-r07-after.json','frozen-baseline-after.json','frozen-comparison-after.json'):
    result = load(HERE/name)
    assert result['status'].startswith('passed_') and not any(result['guards'].values())
wheel = ROOT/'data/cache/recovery-step9-token-aware-wheel-20261026/dist/asof_target_agents-0.3.4-py3-none-any.whl'
with ZipFile(wheel) as archive:
    members = {name for name in archive.namelist() if name.startswith('asof/') and name.endswith(('.py','.json'))}
    current = {p.relative_to(ROOT/'src').as_posix() for p in (ROOT/'src/asof').rglob('*')
               if p.is_file() and p.suffix in ('.py','.json') and '__pycache__' not in p.parts}
    assert members == current
    for name in members:
        assert archive.read(name) == (ROOT/'src'/name).read_bytes(), name
preserved = ROOT/'data/reference/recovery-r09-preparation-verifier-034-20261026'
preserved.mkdir(exist_ok=False)
for path in (wheel, ROOT/'src/asof/archive/semantic_dependencies.json', ROOT/'src/asof/__init__.py'):
    with (preserved/path.name).open('xb') as stream:
        stream.write(path.read_bytes())
reports = [installed_path]
failed = ROOT/'data/cache/recovery-step9-token-aware-validation-20261026'
for source_name, retained_name in (('full-validation.json','first-full-validation-failure.json'),
                                   ('code-validation.json','first-code-validation.json')):
    with (HERE/retained_name).open('xb') as stream:
        stream.write((failed/source_name).read_bytes())
    reports.append(HERE/retained_name)
for name in ('full-validation.json','code-validation.json'):
    source = CACHE/name
    with (HERE/name).open('xb') as stream:
        stream.write(source.read_bytes())
    reports.append(HERE/name)
reports += [HERE/name for name in ('CONTRACT-v2.md','CONTRACT-v2.json','INDEPENDENT-CONTRACT-REVIEW-v2.json',
    'IMPLEMENTATION-PEER-REVIEW-final.json','LOCK-PROBE-RESULT.json','SOURCE-AUTHORITY-v1.json',
    'SOURCE-AUTHORITY-PREPARATION.json','REAL-PREPARATION.json','REAL-PREPARATION-FAILURE.json',
    'REAL-PREPARATION-PROTOCOL-v2.json','installed-preparation-verification.json',
    'frozen-r07-after.json','frozen-baseline-after.json','frozen-comparison-after.json','WORKING-VERSION.json')]
result = dict(schema_version=1, recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    status='accepted_source_and_token_preparation_engineering_only', version='0.3.4',
    full_tests=full['tests'], peer_tests=peer['tests'], source_pins_rechecked=len(code['source_pins']),
    protected_hashes_only=len(code['protected_hashes']), installed_legacy_families=7,
    approved_input_inventory_files=27, approved_input_inventory_bytes=363192274, selected_whole_rows_replayed=1,
    identifier_mapping_rows_replayed=3, real_request_sha256=real['request_sha256'],
    real_preparation_receipt_sha256=real['receipt_sha256'], input_reservation=28241,
    output_reservation=6144, elapsed_preparation_seconds=real['elapsed_preparation_seconds'],
    tokenizer_children=6, actual_generation_calls=0, provider_spending_usd=0,
    lock_probe_tokenizer_children=1,
    first_full_validation='one test-discovery import error; runtime code unchanged; original report preserved',
    discovery_correction='two peer fixture imports made package-qualified; test assertions unchanged',
    verified_history_scope='exact_hypothetical_only_not_a_token_maximum',
    admission_scope='one_exposed_case_supported_OT25.09_recipe2.2_contemporary_profile',
    runtime_execution_policy_changed=False, human_scientific_review='pending',
    scientific_validation='not_established', entire_R09_complete=False,
    remaining=['Token-aware execution-policy integration and end-to-end retrieval track',
               'Fresh-case/source qualification and independent human references',
               'Prospectively gated native comparison and scientific evaluation'],
    limits=['Cooperative kernel/filesystem deadlines; tokenizer child separately bounded',
            'OS/loader/sharing trust boundaries; no hostile same-user sandbox or CPU attestation',
            'No newly acquired data, new model, clinical probability or independent biological validation'],
    wheel=pin(wheel), preserved_wheel=pin(preserved/wheel.name), evidence=[pin(p) for p in reports])
with (HERE/'acceptance.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(dict(status=result['status'], tests=full['tests']['run'], source_pins=len(code['source_pins']),
                      acceptance_sha256=sha(HERE/'acceptance.json'))))
