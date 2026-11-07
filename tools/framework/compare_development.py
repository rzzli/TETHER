"""Offline, paired selection diagnostics on sealed development model requests.

No inference or outcome access. This is conditional on the candidates actually
shown to the model, not an end-to-end retrieval or scientific-quality benchmark.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import math
import re
import time

from tether_engine.agents import SpecialistRequest
from tether_engine.artifacts import verify_run
from tether_engine.local_model import parse_selection
from tether_engine.serde import ContractError, decode, fingerprint, read_json, safe_child, sha256_file, write_json
from tools.framework.summarize_local_pilot import summarize


def checked_request(value):
    request = decode(SpecialistRequest, value)
    ids = [x.observation_id for x in request.evidence]
    if len(ids) != len(set(ids)):
        raise ContractError('Duplicate comparison candidate ID')
    case = read_case(request)
    if case['task'] != 'T6':
        raise ContractError('This comparison accepts exposed T6 development requests only')
    for item in request.evidence:
        from tether_engine.serde import parse_json
        record = parse_json(item.scientific_record_json)
        if (record['observation_id'] != item.observation_id or record['statement'] != item.statement or
                record['category'] != request.category.value or record['target_id'] != case['hypothesis']['target_id'] or
                record['indication_id'] != case['hypothesis']['indication_id'] or record['features'] or
                record['status'] != 'observed'):
            raise ContractError('Comparison candidate identity/scope/status or empty-feature contract failed')
    return request


def read_case(request):
    from tether_engine.serde import parse_json
    return parse_json(request.case_json)


def select_baseline(request, method, k=3):
    """Descriptive selectors; scores never become weights, effects or probabilities.

    Provider-score top-k abstains when scores are missing or from different data
    sources. No normalization or silent ordering across incomparable scales.
    """
    if type(k) is not int or not 1 <= k <= 3:
        raise ContractError('Comparison top-k must be between one and three')
    evidence = request.evidence
    if method == 'extractive_all':
        selected = evidence
    elif method == 'lexical_top_k':
        tokens = set(re.findall(r'[a-z0-9_]{3,}', request.case_json.casefold()))
        selected = sorted(evidence, key=lambda x: (
            -len(tokens & set(re.findall(r'[a-z0-9_]{3,}', x.statement.casefold()))), x.observation_id))[:k]
    elif method == 'provider_score_top_k':
        from tether_engine.serde import parse_json
        records = [(x, parse_json(x.scientific_record_json)) for x in evidence]
        groups = {r.get('source_locator', {}).get('datasource_id') for _, r in records}
        scores = [r.get('source_metrics', {}).get('score') for _, r in records]
        if len(groups) > 1 or (records and None in groups):
            return {'status': 'inapplicable', 'reason': 'incomparable_or_unknown_datasource_scales', 'selected_ids': None}
        if any(type(s) not in (int, float) or not math.isfinite(s) for s in scores):
            return {'status': 'inapplicable', 'reason': 'missing_or_nonfinite_provider_score', 'selected_ids': None}
        selected = [x for x, _ in sorted(zip(evidence, scores), key=lambda x: (-x[1], x[0].observation_id))[:k]]
    else:
        raise ContractError('Unknown development baseline')
    return {'status': 'computed', 'selected_ids': [x.observation_id for x in selected],
            'probability': None, 'prediction_features': {},
            'output_cap_matches_model': method != 'extractive_all',
            'role': 'uncapped_candidate_reference' if method == 'extractive_all' else 'matched_top_k_baseline'}


def selection_comparison(candidate_ids, actual, baseline):
    if len(actual) != len(set(actual)) or set(actual) - set(candidate_ids) or len(actual) > 3:
        raise ContractError('Invalid archived model selection')
    if baseline['status'] != 'computed':
        return {'status': 'inapplicable', 'reason': baseline['reason']}
    expected = baseline['selected_ids']
    if len(expected) != len(set(expected)) or set(expected) - set(candidate_ids):
        raise ContractError('Baseline selected outside paired candidate set')
    a, b = set(actual), set(expected)
    return {'status': 'computed', 'same_selection_set': a == b,
            'same_selection_order': list(actual) == expected,
            'jaccard': len(a & b) / len(a | b) if a | b else None,
            'interpretation': 'selection_agreement_only_not_accuracy'}


def analyze_attempt(entry):
    if entry['status'] != 'completed':
        raise ContractError('Failed/incomplete attempts cannot be treated as successful comparisons')
    request = checked_request(entry['request'])
    if entry['request_sha256'] != fingerprint(request):
        raise ContractError('Comparison request fingerprint mismatch')
    if entry['response_sha256'] != fingerprint(entry['response']):
        raise ContractError('Comparison response fingerprint mismatch')
    actual, usage = parse_selection(entry['response'], [x.observation_id for x in request.evidence])
    if list(actual) != entry['selection'] or fingerprint(usage) != fingerprint(entry['measured_usage']):
        raise ContractError('Comparison model selection/usage mismatch')
    candidates = [x.observation_id for x in request.evidence]
    baselines = {}
    for method in ('extractive_all', 'lexical_top_k', 'provider_score_top_k'):
        selection = select_baseline(request, method)
        baselines[method] = {**selection, 'comparison': selection_comparison(candidates, actual, selection)}
    return {'case_id': read_case(request)['case_id'], 'category': request.category.value,
            'request_sha256': fingerprint(request), 'candidate_ids': candidates,
            'candidate_fingerprints': {x.observation_id: fingerprint(x) for x in request.evidence},
            'model_selected_ids': list(actual), 'model_selected_every_candidate': set(actual) == set(candidates),
            'candidate_count_exceeds_selection_cap': len(candidates) > 3,
            'baselines': baselines, 'archived_model_usage': entry['measured_usage'],
            'baseline_provider_spend_usd': 0, 'baseline_model_calls': 0}


def ablation_masks(rows):
    """Actually compute deterministic selection masks, not counterfactual model runs."""
    full = [(r['category'], i) for r in rows for i in r['model_selected_ids']]
    return {name: {'retained_ids': [i for category, i in full if category != excluded],
                   'removed_ids': [i for category, i in full if category == excluded],
                   'execution': 'deterministic_post_selection_mask_no_model_rerun',
                   'scientific_effect': None, 'probability': None}
            for name, excluded in [('no_literature', 'literature'), ('no_perturbation', 'perturbation')]}


def pilot_wire_format(report, configuration):
    """Older canonical pilot reports predate the optional wire-format field."""
    configured = configuration['backend_provenance']['config']['retrieval'].get('wire_format', 'canonical')
    if report.get('wire_format', configured) != configured:
        raise ContractError('Pilot report and archived request transport disagree')
    return configured


def validate_protocol(protocol):
    if (protocol.get('schema_version') != 1 or protocol.get('purpose') != 'exposed_t6_selection_diagnostics' or
            type(protocol.get('selection_cap')) is not int or protocol['selection_cap'] != 3 or
            protocol.get('baselines') != ['extractive_all', 'lexical_top_k', 'provider_score_top_k'] or
            protocol.get('new_model_calls') != 0 or protocol.get('provider_spend_usd') != 0 or
            protocol.get('clinical_labels_read') is not False):
        raise ContractError('Invalid development comparison protocol or unsupported method/budget')
    pilots = protocol.get('pilots')
    if not isinstance(pilots, list) or not pilots or len({p['id'] for p in pilots}) != len(pilots):
        raise ContractError('Missing or duplicate comparison pilot groups')
    for parent in pilots:
        if (not re.fullmatch('[a-z0-9_-]+', parent['id']) or type(parent['case_count']) is not int or
                not 1 <= parent['case_count'] <= 10 or not re.fullmatch('[a-f0-9]{64}', parent['seal_sha256'])):
            raise ContractError('Invalid comparison pilot identity/count/seal')


def compare(protocol_path, output):
    protocol = read_json(protocol_path)
    validate_protocol(protocol)
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    (output / 'executed-comparison.py').write_bytes(Path(__file__).read_bytes())
    (output / 'protocol.json').write_bytes(protocol_path.read_bytes())
    write_json(output / 'status.json', {'status': 'running', 'protocol_sha256': sha256_file(protocol_path)})
    try:
        groups, used = [], set()
        for parent in protocol['pilots']:
            root = Path(parent['path'])
            # Validate external seal, terminal event and inherited source-inclusive proof.
            parent_summary = summarize(root, parent['seal_sha256'], parent['case_count'])
            report = read_json(root / 'pilot-report.json')
            cases, formats = [], set()
            for case in report['cases']:
                run = safe_child(root, case['case_id'])
                verification = verify_run(run, case['receipt_sha256'], verify_sources=False)
                formats.add(pilot_wire_format(report, read_json(run / 'inputs.json')['configuration']))
                entries = read_json(run / 'backend-execution.json')['attempts']
                rows = [analyze_attempt(e) for e in entries]
                if any(r['case_id'] != case['case_id'] for r in rows):
                    raise ContractError('Model request belongs to a different parent case')
                if len({r['category'] for r in rows}) != len(rows):
                    raise ContractError('Repeated categories/retries need a separately frozen pairing policy')
                key = (parent['id'], case['case_id'])
                if key in used:
                    raise ContractError('Duplicate comparison case within a transport group')
                used.add(key)
                cases.append({'case_id': case['case_id'], 'parent_receipt_sha256': case['receipt_sha256'],
                    'verification': verification, 'attempts': rows, 'ablations': ablation_masks(rows),
                    'no_reviewer_retries': {'observed_retry_count': 0,
                        'status': 'not_informative_no_retries_in_parent',
                        'scientific_quality_effect': None}})
                partial = safe_child(output, f"cases/{parent['id']}/{case['case_id']}.json")
                partial.parent.mkdir(parents=True, exist_ok=True)
                write_json(partial, cases[-1])
                print(f"{parent['id']} {case['case_id']}: {len(rows)} paired requests", flush=True)
                write_json(output / 'status.json', {'status': 'running', 'completed_cases': len(used)})
            attempts = [a for c in cases for a in c['attempts']]
            counts = {}
            for method in ('extractive_all', 'lexical_top_k', 'provider_score_top_k'):
                computed = [a['baselines'][method]['comparison'] for a in attempts
                            if a['baselines'][method]['comparison']['status'] == 'computed']
                counts[method] = {'applicable_requests': len(computed),
                    'inapplicable_requests': len(attempts) - len(computed),
                    'identical_selection_sets': sum(x['same_selection_set'] for x in computed)}
            if len(formats) != 1:
                raise ContractError('A pilot mixes different transports')
            groups.append({'id': parent['id'], 'wire_format': formats.pop(),
                'parent_seal_sha256': parent['seal_sha256'], 'case_count': len(cases),
                'request_count': len(attempts), 'model_selected_all_candidates_requests': sum(
                    a['model_selected_every_candidate'] for a in attempts),
                'requests_with_more_than_three_candidates': sum(a['candidate_count_exceeds_selection_cap'] for a in attempts),
                'baseline_agreement_counts': counts, 'cases': cases,
                'inherited_resource_summary': {k: parent_summary[k] for k in
                    ('calls', 'input_tokens', 'output_tokens', 'native_prompt_and_generation_seconds_sum')}})
        result = {'schema_version': 1, 'status': 'technical_diagnostics_completed_scientific_comparison_blocked',
            'protocol_sha256': sha256_file(protocol_path), 'groups': groups,
            'source_verification': 'Archived runs/seals reverified; original raw bytes not rehashed in this diagnostic',
            'new_model_calls': 0, 'provider_spend_usd': 0, 'clinical_metrics': None, 'independent_quality_metrics': None,
            'virtual_biotech_performance': None, 'task6_complete': False,
            'elapsed_seconds': time.monotonic() - started,
            'limitations': protocol['limitations']}
        write_json(output / 'comparison.json', result)
        write_json(output / 'status.json', {'status': result['status'], 'completed_at_utc': datetime.now(timezone.utc).isoformat()})
        members = ['protocol.json', 'comparison.json', 'status.json', 'executed-comparison.py'] + sorted(
            p.relative_to(output).as_posix() for p in (output / 'cases').rglob('*.json'))
        write_json(output / 'evidence-manifest.json', {'schema_version': 1, 'files': [
            {'path': n, 'bytes': (output / n).stat().st_size, 'sha256': sha256_file(output / n)} for n in members],
            'code_sha256': sha256_file(Path(__file__))})
        return result
    except BaseException as exc:
        write_json(output / 'status.json', {'status': 'failed', 'error_type': type(exc).__name__, 'error': str(exc),
            'elapsed_seconds': time.monotonic() - started})
        raise


def verify_comparison(output, expected_seal):
    """Recheck sealed report and independently regenerate each paired/masked row."""
    seal = output / 'evidence-manifest.json'
    if sha256_file(seal) != expected_seal:
        raise ContractError('Comparison external seal anchor mismatch')
    seen = set()
    for item in read_json(seal)['files']:
        path = safe_child(output, item['path'])
        if (item['path'] in seen or not path.is_file() or path.stat().st_size != item['bytes'] or
                sha256_file(path) != item['sha256']):
            raise ContractError('Changed, duplicate or missing comparison output')
        seen.add(item['path'])
    if not {'protocol.json', 'comparison.json', 'status.json', 'executed-comparison.py'} <= seen:
        raise ContractError('Incomplete comparison proof inventory')
    if sha256_file(output / 'executed-comparison.py') != read_json(seal)['code_sha256']:
        raise ContractError('Archived comparison code fingerprint mismatch')
    protocol = read_json(output / 'protocol.json'); validate_protocol(protocol)
    report = read_json(output / 'comparison.json')
    if (report['protocol_sha256'] != sha256_file(output / 'protocol.json') or
            report['task6_complete'] is not False or report['new_model_calls'] != 0 or
            report['clinical_metrics'] is not None or report['independent_quality_metrics'] is not None or
            report['virtual_biotech_performance'] is not None or report['provider_spend_usd'] != 0 or
            report['status'] != read_json(output / 'status.json')['status']):
        raise ContractError('Comparison status, protocol or scientific-boundary mismatch')
    if len(report['groups']) != len(protocol['pilots']):
        raise ContractError('Comparison group count mismatch')
    checked = 0
    for parent, group in zip(protocol['pilots'], report['groups']):
        if parent['id'] != group['id'] or parent['seal_sha256'] != group['parent_seal_sha256']:
            raise ContractError('Comparison parent/group binding mismatch')
        root = Path(parent['path']); inherited = summarize(root, parent['seal_sha256'], parent['case_count'])
        pilot_report = read_json(root / 'pilot-report.json'); cases = pilot_report['cases']
        if len(cases) != len(group['cases']):
            raise ContractError('Comparison parent case inventory mismatch')
        for original, case in zip(cases, group['cases']):
            if original['case_id'] != case['case_id'] or original['receipt_sha256'] != case['parent_receipt_sha256']:
                raise ContractError('Comparison case receipt binding mismatch')
            run = safe_child(root, case['case_id'])
            verified = verify_run(run, case['parent_receipt_sha256'], verify_sources=False)
            stable = lambda value: {k: v for k, v in value.items() if k != 'code_matches_current'}
            if fingerprint(stable(verified)) != fingerprint(stable(case['verification'])):
                raise ContractError('Comparison verification description differs from parent check')
            config = read_json(run / 'inputs.json')['configuration']
            if group['wire_format'] != pilot_wire_format(pilot_report, config):
                raise ContractError('Comparison transport differs from parent')
            expected = [analyze_attempt(e) for e in read_json(run / 'backend-execution.json')['attempts']]
            if fingerprint(expected) != fingerprint(case['attempts']) or fingerprint(ablation_masks(expected)) != fingerprint(case['ablations']):
                raise ContractError('Comparison selection/baseline/mask semantic mismatch')
            member = f"cases/{parent['id']}/{case['case_id']}.json"
            if member not in seen or fingerprint(read_json(output / member)) != fingerprint(case):
                raise ContractError('Comparison case report differs from sealed partial record')
            checked += len(expected)
        attempts = [a for case in group['cases'] for a in case['attempts']]
        if (group['case_count'] != len(cases) or group['request_count'] != len(attempts) or
                group['model_selected_all_candidates_requests'] != sum(a['model_selected_every_candidate'] for a in attempts) or
                group['requests_with_more_than_three_candidates'] != sum(a['candidate_count_exceeds_selection_cap'] for a in attempts)):
            raise ContractError('Comparison aggregate case/request/selectivity accounting mismatch')
        if set(group['baseline_agreement_counts']) != set(protocol['baselines']):
            raise ContractError('Comparison baseline inventory mismatch')
        for method, counts in group['baseline_agreement_counts'].items():
            results = [a['baselines'][method]['comparison'] for a in attempts]
            computed = [r for r in results if r['status'] == 'computed']
            expected_counts = {'applicable_requests': len(computed),
                'inapplicable_requests': len(results) - len(computed),
                'identical_selection_sets': sum(r['same_selection_set'] for r in computed)}
            if counts != expected_counts:
                raise ContractError('Comparison baseline agreement accounting mismatch')
        if fingerprint(group['inherited_resource_summary']) != fingerprint({k: inherited[k] for k in
                ('calls', 'input_tokens', 'output_tokens', 'native_prompt_and_generation_seconds_sum')}):
            raise ContractError('Comparison inherited resource summary mismatch')
    return {'status': 'verified', 'seal_sha256': expected_seal, 'sealed_files': len(seen),
            'paired_requests_regenerated': checked, 'original_raw_bytes_rehashed': False,
            'scientific_validation': 'not_established'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify-seal-sha256')
    args = parser.parse_args()
    if args.verify_seal_sha256:
        if args.protocol:
            parser.error('--protocol is only for new execution')
        result = verify_comparison(args.output, args.verify_seal_sha256)
    else:
        if not args.protocol:
            parser.error('--protocol is required for new execution')
        result = compare(args.protocol, args.output)
    print(result['status'])
