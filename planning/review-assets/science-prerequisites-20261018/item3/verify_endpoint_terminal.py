"""Independent terminal acceptance for the single authorized technical restore."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import sys
import time

PROJECT = Path('D:/Projects/drug_target_agents')
sys.path.insert(0, str(PROJECT))
from asof.serde import read_json, sha256_file, write_json
from tools.science.endpoint_restore import verify_origin_closure, validate_gate
from tools.feasibility.restore_intermediate_aact import technical_checks

OUT = Path('E:/projects_data/drug_target_agents_data/derived/aact_restore/science-endpoint-20260101-20261018T174448Z')
TRACKED = PROJECT/'planning/review-assets/science-prerequisites-20261018/item3'


def journal(path):
    previous = None
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        digest = row.pop('sha256')
        assert row['previous_sha256'] == previous
        actual = hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        assert actual == digest, (path, row)
        previous = digest
        rows.append(row)
    return rows, previous


def main():
    start = time.monotonic()
    result = read_json(OUT/'restore/result.json')
    assert result['status'] == 'completed'
    outer = read_json(OUT/'report.json')
    assert outer['status'] == 'technical_restore_completed'
    assert outer['endpoint_cohort_rows_queried'] == 0 and outer['clinical_activation'] is False
    assert outer['ascertainment_qualified'] is False
    assert len(result['snapshots']) == 1
    row = result['snapshots'][0]
    root = Path(row['root'])
    assert row['status'] == 'completed' and row['server_stopped'] is True
    assert row['requested_date'] == row['actual_snapshot_date'] == '2026-01-01'
    assert row['cohort_records'] == 0
    retained_row = read_json(root/'restore-result.json')
    assert all(retained_row[k] == row[k] for k in retained_row)
    assert not (root/'pgdata/postmaster.pid').exists()
    with socket.socket() as connection:
        connection.settimeout(2)
        assert connection.connect_ex(('127.0.0.1', 55437)) != 0, 'Owned port is still listening'
    assert read_json(root/'cohort-records.json') == []
    assert (root/'cohort-query.sql').read_text(encoding='utf-8') == "SELECT '[]'::text;\n"
    checks = technical_checks(root, '2026-01-01')
    assert checks == row['technical_checks']
    assert checks['identifier_exceptions'] == []
    manifest = read_json(root/'evidence-manifest.json')
    assert sha256_file(root/'evidence-manifest.json') == row['evidence_manifest_sha256']
    for proof in manifest['files']:
        path = root/proof['path']
        assert path.stat().st_size == proof['bytes'] and sha256_file(path) == proof['sha256'], str(path)
    plan = read_json(OUT/'plan.json')
    archive = read_json(root/'archive-inspection.json')
    # Prior qualification and independent launch-time proof pin the same original.
    original = Path(archive['archive'])
    digest = sha256_file(original)
    assert digest == '7fb923dacecae1dfec864c3e21fbed669add8a64b6bd1664ce973c24a514035c'
    assert digest == archive['archive_sha256']
    assert original.stat().st_size == archive['archive_bytes'] == 2344676979
    for member in archive['members']:
        assert member['crc_check'] == 'passed_full_read'
        path = root/'extracted'/member['name']
        assert path.stat().st_size == member['bytes'] and sha256_file(path) == member['sha256']
    stages, child_head = journal(OUT/'restore/journal.jsonl')
    assert stages[-1]['stage'] == 'batch_terminal' and stages[-1]['status'] == 'completed'
    assert not any(x.get('status') == 'failed' or x['stage'] == 'batch_failed' for x in stages)
    for stage in ('archive_check','toc','setup','import','analyze','audit','cohort','stop'):
        assert any(x['stage'] == stage and x.get('status') == 'completed' for x in stages), stage
    # RunJournal uses the framework's canonical fingerprint; validate with its reader.
    from asof.journal import read_chain
    outer_journal = read_chain(OUT/'journal.jsonl')
    assert outer_journal[-1]['event'] == 'build_completed'
    assert outer_journal[-1]['details']['report_sha256'] == sha256_file(OUT/'report.json')
    decision_path = TRACKED/'origin-route-decision.json'
    decision = read_json(decision_path)
    origin_path = PROJECT/'data/benchmark/cohorts/science-origin-20250101-20261018T173340Z/mapping-r1/origin-freeze.json'
    origin, pins = verify_origin_closure(origin_path, outer['origin_seal_sha256'])
    validate_gate(origin, decision)
    assert sha256_file(decision_path) == outer['decision_sha256']
    report = {
        'schema_version': 1, 'status': 'independent_terminal_acceptance_passed',
        'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'role': 'evaluation_only',
        'restore_root': str(OUT), 'endpoint_cohort_rows_queried': 0,
        'clinical_activation': False, 'ascertainment_qualified': False,
        'technical_checks': checks, 'server_stopped': True, 'owned_port_listening': False,
        'source_archive_sha256': digest, 'source_archive_bytes': archive['archive_bytes'],
        'source_members_verified': len(archive['members']),
        'evidence_files_verified': len(manifest['files']), 'child_journal_head_sha256': child_head,
        'ancestor_pins_reverified': len(pins),
        'restore_elapsed_seconds': result['elapsed_seconds'],
        'import_elapsed_seconds': row['import_elapsed_seconds'],
        'retained_bytes': row['retained_bytes'],
        'peak_memory_bytes': result['peak_memory_bytes'], 'peak_memory_reason': result['peak_memory_reason'],
        'acceptance_elapsed_seconds': time.monotonic()-start, 'provider_spend_usd': 0,
        'live_wrapper_note': 'Original dispatched gate archived; current corrected source ancestry and archive guards independently applied after completion. No duplicate dispatch.',
        'proofs': [{'path': str(path), 'sha256': sha256_file(path)} for path in
            (OUT/'report.json', OUT/'restore/result.json', root/'evidence-manifest.json',
             root/'technical-audit.json', OUT/'gate-code-provenance.json', decision_path)]
    }
    write_json(TRACKED/'endpoint-terminal-validation.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
