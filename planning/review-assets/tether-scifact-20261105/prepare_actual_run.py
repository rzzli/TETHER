"""Freeze a reviewable actual-run command after qualified fictional execution.

This helper does not fit, predict, open reference rows or dispatch a worker.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
PREPARATION_SHA = 'cb32f1384c49b66b912a62120abd7137a8a19b303f3ad052f035f21779c131f8'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rehearsal-receipt-sha256', required=True)
    parser.add_argument('--bytecode-qualification', type=Path, required=True)
    parser.add_argument('--run-output', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    try:
        gate = read(BASE / 'integration-attempt01/VALIDATION.json')
        require(gate['status'] == 'PASS' and gate['tests'] == 148 and gate['sources_unchanged']
                and gate['failures'] == gate['errors'] == gate['skips'] == 0, 'Integration gate is incomplete')
        for name, expected in gate['source_pins'].items():
            require(sha(ROOT / name) == expected, 'Qualified source changed: ' + name)
        rehearsal = ROOT / 'data/cache/scifact-runner-fictional-attempt02'
        require(read(rehearsal / 'REHEARSAL-COMPLETED.json')['status'] == 'PASS', 'Full rehearsal unfinished')
        stage = rehearsal / 'stage'
        require(sha(stage / 'RECEIPT.json') == args.rehearsal_receipt_sha256, 'Rehearsal receipt anchor differs')
        receipt = read(stage / 'RECEIPT.json')
        actual_files = {path.relative_to(stage).as_posix() for path in stage.rglob('*') if path.is_file()}
        require(actual_files == set(receipt['outputs']) | {'RECEIPT.json'}, 'Rehearsal inventory differs')
        for name, expected in receipt['outputs'].items():
            require(sha(stage / name) == expected, 'Rehearsal output changed: ' + name)
        for name, proof in read(stage / 'FROZEN.json')['runtime']['task_code'].items():
            require(sha(name) == proof['sha256'], 'Executed rehearsal source changed: ' + name)
        bytecode = read(args.bytecode_qualification)
        require(bytecode['status'] == 'PASS', 'Import caches unqualified')
        for row in bytecode['cache_files']:
            require(sha(row['path']) == row['sha256'] and sha(row['source_path']) == row['source_sha256'],
                    'Qualified import cache/source changed')
        preparation = ROOT / 'data/benchmark/scifact/preparation-20261105-attempt03'
        require(sha(preparation / 'manifest.json') == PREPARATION_SHA, 'Actual preparation manifest changed')
        run_output = args.run_output.resolve()
        require(run_output.is_relative_to(ROOT / 'data/benchmark/scifact') and not run_output.exists(),
                'Actual output must be a fresh benchmark directory')
        python = ROOT / 'data/cache/tether-scifact-env-attempt02/environment/Scripts/python.exe'
        require(Path(sys.executable).resolve() == python.resolve(), 'Preflight must use qualified interpreter')
        command = [str(python), '-I', '-B', str(ROOT / 'experiments/scifact/run.py'),
                   '--preparation', str(preparation), '--preparation-sha256', PREPARATION_SHA,
                   '--output', str(run_output), '--python', str(python),
                   '--evaluator', str(ROOT / 'data/reference/scifact-evaluator-66feffc5/evaluator/eval.py'),
                   '--environment-qualification', str(BASE / 'ENVIRONMENT-QUALIFICATION-02.json')]
        report = {'schema_version': 1, 'status': 'READY_NOT_EXECUTED',
                  'created_at_utc': datetime.now(timezone.utc).isoformat(),
                  'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  'preparation_manifest_sha256': PREPARATION_SHA,
                  'rehearsal_receipt_sha256': args.rehearsal_receipt_sha256,
                  'rehearsal_outputs_verified': len(receipt['outputs']),
                  'integration_gate_sha256': sha(BASE / 'integration-attempt01/VALIDATION.json'),
                  'bytecode_qualification': {'path': str(args.bytecode_qualification.resolve()),
                                             'sha256': sha(args.bytecode_qualification)},
                  'protocol_sha256': sha(ROOT / 'planning/TETHER SciFact Execution Protocol 2026-11-05.md'),
                  'qualified_source_pins': gate['source_pins'], 'command': command,
                  'environment': {'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
                  'scheduled_dev_claims': 300, 'tuning_configurations': 9, 'provider_spend_usd': 0,
                  'rules': 'One fresh stage; no implicit retries or dev-selected parameter changes.',
                  'preflight_code_sha256': sha(__file__)}
        (output / 'READY.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
        print(json.dumps({'status': report['status'], 'run_output': str(run_output),
                          'ready_sha256': sha(output / 'READY.json')}))
    except BaseException as error:
        (output / 'FAILED.json').write_text(json.dumps({'status': 'failed_before_dispatch',
            'error_type': type(error).__name__, 'message': str(error)}, indent=2) + '\n', encoding='utf-8', newline='\n')
        raise


if __name__ == '__main__':
    main()
