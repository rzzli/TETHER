"""Aggregate only a sealed, ten-case local development pilot; do not infer science."""
from collections import Counter
from pathlib import Path
from statistics import median
import argparse
import json

from tether_engine.serde import ContractError, fingerprint, read_json, safe_child, sha256_file, write_json


def verify_seal(root, expected):
    path = root / 'evidence-manifest.json'
    if sha256_file(path) != expected:
        raise ContractError('Pilot seal differs from expected anchor')
    seen = set()
    for item in read_json(path)['files']:
        relative = item['path'].replace('\\', '/'); child = safe_child(root, relative)
        if relative in seen or not child.is_file() or child.stat().st_size != item['bytes'] or sha256_file(child) != item['sha256']:
            raise ContractError('Changed, duplicate or missing pilot output')
        seen.add(relative)
    if 'pilot-report.json' not in seen or 'pilot-journal.jsonl' not in seen:
        raise ContractError('Missing pilot terminal evidence')
    return seen


def summarize(root, expected, expected_cases=10):
    root = root.resolve()
    if type(expected_cases) is not int or not 1 <= expected_cases <= 10:
        raise ContractError('Explicit pilot case count must be between one and ten')
    files = verify_seal(root, expected)
    report = read_json(root / 'pilot-report.json')
    wanted_status = 'ten_development_cases_verified' if expected_cases == 10 else 'selected_development_cases_verified'
    if report['status'] != wanted_status or not report['server_stopped'] or len(report['cases']) != expected_cases:
        raise ContractError('Pilot is incomplete or its owned server is not stopped')
    previous = None; events = []
    for line in (root / 'pilot-journal.jsonl').read_text(encoding='utf-8').splitlines():
        event = json.loads(line)
        if event['previous_sha256'] != previous or fingerprint({k: v for k, v in event.items() if k != 'sha256'}) != event['sha256']:
            raise ContractError('Pilot journal chain differs')
        previous = event['sha256']; events.append(event)
    if not events or events[-1]['stage'] != 'terminal' or events[-1]['status'] != report['status']:
        raise ContractError('Pilot terminal event differs')
    completed = [e['case_id'] for e in events if e['stage'] == 'case_verified']
    if len(completed) != expected_cases or set(completed) != {x['case_id'] for x in report['cases']}:
        raise ContractError('Pilot journal/report case inventory differs')
    cases = []; omitted = Counter(); known_raw = {}; tokens_in = tokens_out = calls = 0
    native_ms = 0; native_timings_missing = 0
    for item in report['cases']:
        run = safe_child(root, item['case_id'])
        if any((run / name).relative_to(root).as_posix() not in files for name in
               ('receipt.json', 'inputs.json', 'backend-execution.json', 'prediction.json', 'features.json')):
            raise ContractError('Unsealed case inputs or derived outputs')
        if sha256_file(run / 'receipt.json') != item['receipt_sha256']:
            raise ContractError('Case receipt differs from pilot anchor')
        if (item['status'] != 'completed' or item['verification']['semantic_consistency'] != 'verified' or
                item['verification']['source_binding'] != 'current_originals'):
            raise ContractError('Case lacks successful source-inclusive semantic verification')
        inputs = read_json(run / 'inputs.json'); execution = read_json(run / 'backend-execution.json')
        if read_json(run / 'prediction.json')['probability'] is not None or any(
                f['value'] is not None for f in read_json(run / 'features.json')['values'].values()):
            raise ContractError('Unexpected real probability or numerical prediction feature')
        for node in inputs['snapshot']['sources']:
            if node['computed_at'] is None:
                p = safe_child(Path(inputs['snapshot']['raw_root']), node['path'])
                known_raw[str(p)] = p.stat().st_size
        available = bounded = selected = 0
        for value in item['coverage'].values():
            available += value['available_observations']; selected += value['selected_observations']
            if 'retrieval' in value:
                bounded += len(value['retrieval']['selected_ids'])
                omitted.update(x['reason'] for x in value['retrieval']['excluded'])
        for attempt in execution['attempts']:
            timings = attempt['response'].get('timings')
            if timings and all(k in timings for k in ('prompt_ms', 'predicted_ms')):
                native_ms += timings['prompt_ms'] + timings['predicted_ms']
            else: native_timings_missing += 1
        tokens_in += item['usage']['input_tokens']; tokens_out += item['usage']['output_tokens']; calls += item['calls']
        cases.append({'case_id': item['case_id'], 'available_annotations': available,
            'bounded_candidates_across_categories': bounded, 'selected_source_statements': selected,
            'calls': item['calls'], 'elapsed_seconds_including_source_verification': item['elapsed_seconds_including_source_verification'],
            'receipt_sha256': item['receipt_sha256']})
    if len({x['case_id'] for x in cases}) != expected_cases:
        raise ContractError('Duplicate case IDs')
    return {'status': 'ten_local_development_dossiers_verified' if expected_cases == 10 else 'focused_local_development_dossiers_verified',
        'case_count': expected_cases, 'root': str(root),
        'evidence_manifest_sha256': expected, 'sealed_files_verified': len(files), 'cases': cases,
        'calls': calls, 'input_tokens': tokens_in, 'output_tokens': tokens_out, 'provider_spend_usd': 0,
        'native_prompt_and_generation_seconds_sum': native_ms / 1000,
        'native_timings_missing_attempts': native_timings_missing,
        'elapsed_seconds_end_to_end': report['elapsed_seconds'],
        'median_case_seconds_including_source_verification': median(x['elapsed_seconds_including_source_verification'] for x in cases),
        'unique_original_paths': len(known_raw), 'unique_original_bytes': sum(known_raw.values()),
        'omitted_records_by_reason': dict(omitted), 'server_stopped': True,
        'scientific_validation': 'not_established', 'independent_human_reviews': 0,
        'probabilities_withheld': True, 'non_null_numerical_prediction_features': 0,
        'limitations': ['Exposed, dependent development hypotheses; not an independent sample of targets',
            'Whole-record caps can leave only one candidate; selection quality is not independently adjudicated',
            'Native timing sum excludes admission, verification, startup, scheduling and I/O; not end-to-end latency',
            'Byte and semantic consistency do not validate therapeutic relevance or clinical performance']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot', type=Path, required=True)
    parser.add_argument('--seal-sha256', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--expected-cases', type=int, default=10)
    args = parser.parse_args()
    if args.report.exists():
        raise ContractError('Refusing to overwrite a pilot summary')
    write_json(args.report, summarize(args.pilot, args.seal_sha256, args.expected_cases))
