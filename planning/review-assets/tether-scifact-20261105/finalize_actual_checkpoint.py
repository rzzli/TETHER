"""Root acceptance of sealed native results and independent reconstruction.

No fitting, prediction or re-scoring occurs here; all source artifacts stay intact.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
STAGE = ROOT / 'data/benchmark/scifact/native-20261105T234805Z-attempt01'
AUDIT = ROOT / 'data/benchmark/scifact/reconstruction-20261105-attempt01'
STAGE_SHA = '3a997165aac2f0a85a93890f5e10a66d8117563e380e98f892dd3cb8a93f8968'
AUDIT_SHA = '07e9d33fa0d8d989c458edd1a956b3a9e7b4701f5665e10e3fcdc0cf5fa30bed'


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_inventory(root, expected):
    require(sha(root / 'RECEIPT.json') == expected, 'External receipt anchor changed')
    outputs = read(root / 'RECEIPT.json')['outputs']
    observed = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    require(observed == set(outputs) | {'RECEIPT.json'}, 'Receipt inventory differs')
    for name, digest in outputs.items():
        path = root / name
        require(path.resolve().is_relative_to(root.resolve()) and not path.is_symlink(), 'Invalid receipt path')
        require(sha(path) == digest, 'Changed retained output: ' + name)
    return {'outputs': len(outputs), 'retained_bytes': sum((root / name).stat().st_size for name in observed)}


def main():
    inventories = {'stage': verify_inventory(STAGE, STAGE_SHA), 'reconstruction': verify_inventory(AUDIT, AUDIT_SHA)}
    gate = read(BASE / 'integration-attempt01/VALIDATION.json')
    require(gate['status'] == 'PASS' and gate['tests'] == 148 and
            gate['failures'] == gate['errors'] == gate['skips'] == 0, 'Integration qualification failed')
    for name, digest in gate['source_pins'].items():
        require(sha(ROOT / name) == digest, 'Qualified implementation changed: ' + name)
    core = read(ROOT / 'research_notes/TETHER benchmark priorities and methods/implementation-scope.json')['source_files']
    for name, digest in core.items():
        require(sha(ROOT / name) == digest, 'Maintained core/facade source changed: ' + name)
    before = read(BASE / 'BYTECODE-BEFORE-ACTUAL-01.json')
    after = read(BASE / 'BYTECODE-AFTER-ACTUAL-01.json')
    require(before['status'] == after['status'] == 'PASS' and before['cache_files'] == after['cache_files'],
            'Import-cache qualification or continuity failed')
    independent = read(AUDIT / 'RECONSTRUCTION.json')
    require(independent['status'] == 'PASS' and independent['all_primary_aggregates_match'], 'Independent analysis failed')
    require(independent['stage_receipt_sha256'] == STAGE_SHA and independent['scheduled'] == 300,
            'Independent stage/schedule differs')
    helper = BASE / 'reconstruction/reconstruct.py'
    require(sha(helper) == independent['helper_sha256'], 'Independent helper changed')
    qualification = read(BASE / 'reconstruction/qualification-attempt02/QUALIFICATION.json')
    require(qualification['status'] == 'PASS' and qualification['sources_before'] == qualification['sources_after'],
            'Independent helper qualification failed')
    require(qualification['sources_after']['reconstruct.py']['sha256'] == sha(helper), 'Unqualified analysis helper')
    report = read(STAGE / 'REPORT.json')
    for key in ('counts', 'rates', 'raw_metrics', 'checked_metrics', 'provider_spend_usd'):
        require(report[key] == independent[key], 'Primary aggregate differs: ' + key)
    require(report['raw_metrics'] == report['checked_metrics'], 'Unexpected paired metric mismatch')
    require(independent['paired_candidate_count'] == 300, 'Paired candidate inventory incomplete')
    selected = ('counts', 'rates', 'raw_metrics', 'checked_metrics', 'configuration', 'resource_panels',
                'by_native_reference_status', 'dev_source_component_count', 'retrieval_coverage',
                'original_source_bindings_checked', 'limitations')
    result = {key: independent[key] for key in selected}
    result.update({'schema_version': 1, 'status': 'PASS_actual_execution_and_independent_reconstruction',
                   'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'stage_receipt_sha256': STAGE_SHA,
                   'reconstruction_receipt_sha256': AUDIT_SHA, 'inventories': inventories,
                   'elapsed_seconds': report['elapsed_seconds'], 'controller_costs': independent['controller_costs'],
                   'maintained_core_facade_sources_unchanged': len(core), 'qualified_tests': 148,
                   'import_caches_unchanged': len(after['cache_files']), 'provider_spend_usd': 0,
                   'posthoc_constant_nei_context': {'status': 'analytical_reference_not_executed_arm',
                       'strict_correct': independent['retrieval_coverage']['nei_claims'], 'scheduled': 300,
                       'strict_correct_rate': independent['retrieval_coverage']['nei_claims']/300,
                       'evidence_f1': 0, 'reason': 'Empty evidence matches NEI references but retrieves no gold evidence.'},
                   'scientific_conclusion': 'Weak public-development task performance; provenance preserved answers without semantic accuracy gain.',
                   'root_checker_sha256': sha(__file__)})
    target = BASE / 'actual-attempt01/ROOT-ACCEPTANCE.json'
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'sha256': sha(target), 'inventories': inventories,
                      'strict_correct': result['counts']['correct_raw'], 'scheduled': 300}))


if __name__ == '__main__':
    main()
