"""Independent read-only aggregate checks for the stable final SciFact report."""
from pathlib import Path
import ast
from datetime import datetime, timezone
import hashlib
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[4]
REPORT = ROOT / 'planning/TETHER SciFact Native Evaluation Results 2026-11-05.md'
EXPECTED_REPORT = '7bd7b9a55d5bdad4b72b37d346f7ed63a6f68f934ec77b03131d371790da2c3b'
STAGE = ROOT / 'data/benchmark/scifact/native-20261105T234805Z-attempt01'
REBUILD = ROOT / 'data/benchmark/scifact/reconstruction-20261105-attempt01'
ACCEPTANCE = ROOT / 'planning/review-assets/tether-scifact-20261105/actual-attempt01/ROOT-ACCEPTANCE.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def main():
    before = digest(REPORT)
    assert before == EXPECTED_REPORT
    text = REPORT.read_text(encoding='utf-8')
    rows = {}
    for line in text.splitlines():
        if line.startswith('|'):
            cells = [value.strip() for value in line.strip('|').split('|')]
            rows[cells[0]] = cells[1:]
    acceptance, reconstructed, stage = read(ACCEPTANCE), read(REBUILD / 'RECONSTRUCTION.json'), read(STAGE / 'REPORT.json')
    assert acceptance['status'] == 'PASS_actual_execution_and_independent_reconstruction'
    assert reconstructed['status'] == 'PASS' and reconstructed['all_primary_aggregates_match'] is True
    for key in ('counts', 'rates', 'raw_metrics', 'checked_metrics', 'configuration', 'resource_panels',
                'by_native_reference_status', 'dev_source_component_count', 'retrieval_coverage', 'original_source_bindings_checked'):
        assert acceptance[key] == reconstructed[key], key
    for path, expected in ((STAGE / 'RECEIPT.json', acceptance['stage_receipt_sha256']),
                           (REBUILD / 'RECEIPT.json', acceptance['reconstruction_receipt_sha256'])):
        assert digest(path) == expected
    assert acceptance['stage_receipt_sha256'] in text
    assert digest(ACCEPTANCE) in text and digest(REBUILD / 'RECONSTRUCTION.json') in text
    metric_families = {'Abstract label only': 'abstract_label_only', 'Abstract rationalized': 'abstract_rationalized',
                       'Sentence selection': 'sentence_selection', 'Sentence label': 'sentence_label'}
    for label, key in metric_families.items():
        expected = [f'{100 * reconstructed[arm][key + "_" + metric]:.2f}%'
                    for arm in ('raw_metrics', 'checked_metrics') for metric in ('precision', 'recall', 'f1')]
        assert rows[label] == expected, label
    assert sum(value['scheduled'] for value in reconstructed['by_native_reference_status'].values()) == 300
    for label, value in reconstructed['by_native_reference_status'].items():
        expected = [str(value['scheduled']), str(value['accepted']), str(value['strict_raw_correct']),
                    f'{100 * value["strict_raw_correct"] / value["scheduled"]:.2f}%']
        assert rows[label] == expected, label
    assert reconstructed['counts']['accepted'] - reconstructed['counts']['correct_raw'] == 273
    assert acceptance['posthoc_constant_nei_context']['strict_correct'] == 112
    assert acceptance['posthoc_constant_nei_context']['strict_correct_rate'] == 112 / 300
    assert 'post hoc arithmetic reference, not an executed competing run' in text
    assert 'no retained predictor session' in text and 'no semantic accuracy gain' in text
    assert all(token in text for token in ('159/209 (76.08%)', '147/188 (78.19%)', '27/300 (9.00%)', '112/300 NEI claims (37.33%)'))
    assert reconstructed['dev_source_component_count'] == 247
    assert reconstructed['original_source_bindings_checked'] == {'retrieved_documents': 10110, 'returned_sentences': 12777}

    panels = acceptance['resource_panels']
    known_input = sum(value['logical_input_bytes'] for value in panels.values())
    known_output = sum(value['primary_product_output_bytes'] for value in panels.values())
    assert f'{known_input:,}' in text and f'{known_output:,}' in text
    assert panels['check_verification']['unknown_measurements']['input_bytes'] == 1
    assert panels['check_verification']['unknown_measurements']['output_bytes'] == 1
    assert 'Input/output byte counts for final checker verification are unknown' in text
    transports = {path.stem: read(path)['supervision'] for path in (STAGE / 'transport').glob('*.json')}
    assert len(transports) == 22 and all(row['termination_reason'] == 'exited' and not row['cleanup_errors'] for row in transports.values())
    parent_seconds = sum(value['execution_elapsed_seconds'] for value in transports.values())
    brackets = [item for item in stage['controller_costs'] if item['operation'] == 'runtime_reverification']
    controller_seconds = sum(item['wall_seconds'] for item in stage['controller_costs'])
    check_brackets = sum(item['wall_seconds'] for item in brackets if item['phase'] == 'check')
    calculations = {'stage_wall_seconds': stage['elapsed_seconds'], 'controller_wall_seconds': controller_seconds,
                    'runtime_bracket_wall_seconds': sum(item['wall_seconds'] for item in brackets),
                    'parent_process_seconds': parent_seconds, 'checking_phase_brackets_seconds': check_brackets,
                    'checking_branch_measured_subtotal': check_brackets + transports['check']['execution_elapsed_seconds'],
                    'unallocated_wall_remainder': stage['elapsed_seconds'] - controller_seconds - parent_seconds,
                    'prediction_ms_per_case': panels['dev_inference']['wall_seconds_sum'] / 300 * 1000,
                    'direct_check_ms_per_case': panels['dev_checks']['wall_seconds_sum'] / 300 * 1000}
    assert len(brackets) == 47 and len(stage['controller_costs']) == 49
    for key, value in calculations.items():
        assert f'{value:.3f}' in text, key
    complete = [read(path) for path in STAGE.rglob('COMPLETE.json')]
    sampled = max(item['peak_sampled_working_set_bytes'] or 0 for item in complete)
    assert sampled == 282071040 and f'{sampled:,}' in text
    assert sum(item['memory_observations'] == 0 for item in complete) == 10
    assert max(item['peak_memory_bytes_max'] for item in panels.values()) == 304451584

    model = read(STAGE / 'jobs/fit/model/model-manifest.json')
    metadata = model['training_metadata']
    assert len(metadata['fit_claim_ids']) == 380 and len(metadata['fit_document_ids']) == 261
    assert (metadata['fit_pairs'], metadata['sentence_fit_rows'], metadata['label_iterations'], metadata['rationale_iterations']) == (427, 2503, 16, 10)
    assert metadata['pair_features'] * 4 == 195940 and sum(item['bytes'] for item in model['files']) == 22456342
    assert digest(STAGE / 'jobs/fit/model/model-manifest.json') in text
    with zipfile.ZipFile(STAGE / 'jobs/fit/model/arrays.npz') as archive:
        with archive.open('index_data.npy') as source:
            assert source.read(6) == b'\x93NUMPY'
            version = source.read(2)
            length = int.from_bytes(source.read(2 if version[0] == 1 else 4), 'little')
            header = ast.literal_eval(source.read(length).decode('latin1'))
            assert header['shape'] == (1177207,)
    links = re.findall(r'\]\(([^)]+)\)', text)
    assert all((REPORT.parent / target.strip('<>')).exists() for target in links)
    assert digest(REPORT) == before
    result = {'schema_version': 1, 'status': 'PASS_independent_final_report_review',
              'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'report_sha256': before,
              'root_acceptance_sha256': digest(ACCEPTANCE), 'reconstruction_sha256': digest(REBUILD / 'RECONSTRUCTION.json'),
              'official_metric_cells': 24, 'native_strata': 3, 'local_links': len(links),
              'denominators_and_posthoc_nei_context': 'consistent; arithmetic reference is not an executed arm',
              'cost_calculations': calculations, 'known_logical_input_bytes': known_input,
              'known_primary_output_bytes': known_output, 'measurement_unknowns_preserved': True,
              'scientific_claim_review': 'weak baseline; no semantic gain; clean-producer admission is not invalid-source detection prevalence',
              'fixes_required': [], 'native_run_or_report_edits': False,
              'validator_scope_note': 'The initial validator overrequired both receipt hashes inline; reconstruction receipt is correctly bound by the linked, hash-pinned root acceptance record.',
              'scope': 'report arithmetic, source aggregate joins and claim limits; does not rerun producer or remeasure past resources',
              'review_script_sha256': digest(Path(__file__))}
    destination = Path(__file__).with_name('FINAL-REPORT-REVIEW-20261105.json')
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
