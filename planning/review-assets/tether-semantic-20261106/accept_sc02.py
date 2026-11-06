"""Source-inclusive, artifact-only acceptance of the SC02 qualification.

No model inference, checkpoint deserialization, acquisition or retry occurs.
Run with a fresh --output directory. Every retained assertion must pass.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / 'planning/review-assets/tether-semantic-20261106'
QUAL = ASSETS / 'solver-qualification'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def pin(path):
    path = Path(path)
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
            size += len(block)
    return dict(path=str(path.resolve()), bytes=size, sha256=digest.hexdigest())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    checks, observed = [], {}
    started = time.perf_counter()

    def require(condition, name):
        checks.append(dict(check=name, passed=bool(condition)))
        if not condition:
            raise ValueError(name)

    def verify(proof):
        actual = pin(proof['path'])
        require(actual['sha256'] == proof['sha256'], 'sha256: ' + proof['path'])
        if 'bytes' in proof:
            require(actual['bytes'] == proof['bytes'], 'bytes: ' + proof['path'])
        observed[actual['path']] = actual
        return actual

    result = dict(status='FAIL', checks=checks)
    try:
        anchors = {
            ROOT/'data/cache/tether-multivers-acquisition-20261106-attempt01/RECEIPT.json':
                'a76d300564d0a5a4477a31cf167748e2e5b8540696b1c836d0fb8fab537b1610',
            ROOT/'data/cache/tether-multivers-env-20261106-attempt01/INSTALL-RECEIPT.json':
                '9291f74f724d8490c2eb0720c0baa341c1e4edea3b3c56910f5ebb826f496961',
            QUAL/'full-freeze-attempt02/MANIFEST.json':
                'fbcff0a79e7054fdb3e128a3ad038ff03b6dc1ced9411e2ee7ed1a83becf64e6',
            ROOT/'data/benchmark/scifact_multivers/qualification-20261106-attempt02/QUALIFICATION.json':
                'e54fd34919a6c965cbc54397d1b7c44ecadf837e1123cb226ecdc44ff1292374',
            ASSETS/'methods/sc02/actual-parity-review-attempt01/PARITY-REVIEW.json':
                '62c47415d51b818ac30219df7164a6a251d2f6ed341b79f595a8eac01ef522ea',
        }
        for path, digest in anchors.items():
            verify(dict(path=str(path), sha256=digest))
        acquired, installed, frozen, qualification, parity = [read(p) for p in anchors]
        require(acquired['status'] == 'PASS' and len(acquired['files']) == 30, 'All 30 acquired assets complete')
        require(sum(row['bytes'] for row in acquired['files']) == 8571393927, 'Acquisition byte count')
        require(len({row['path'] for row in acquired['files']}) == 30, 'Unique acquisition paths')
        for row in acquired['files']:
            require(row['status'] == 'completed', 'Completed acquisition: ' + row['logical_id'])
            verify(row)
            receipt = read(row['receipt_path'])
            require(all(receipt[k] == row[k] for k in ('sha256', 'bytes', 'status', 'source_url')),
                    'Individual receipt binding: ' + row['logical_id'])
            observed[row['receipt_path']] = pin(row['receipt_path'])
        require(installed['status'] == 'PASS' and len(installed['inventory']) == 25, 'Offline installed inventory')
        verify(installed['freeze'])
        verify(installed['interpreter'])
        for proof in frozen['pins']:
            verify(proof)
        tests = QUAL/'metadata-regression-green01'
        require(read(tests/'RESULT.json')['status'] == 'PASS', 'Component controller passed')
        summary = read(tests/'TEST-SUMMARY.json')
        require(summary['tests'] == 24 and summary['passed'] and
                not any(summary[k] for k in ('failures', 'errors', 'skips')), '24 component tests, none skipped')
        for proof in read(tests/'FROZEN.json')['sources']:
            verify(proof)
        outcome = read(QUAL/'actual-launch-attempt02/OUTCOME.json')
        require(outcome['status'] == 'completed' and outcome['exit_code'] == 0 and
                outcome['all_frozen_pins_unchanged'] and not outcome['automatic_retry'], 'Owned process completed without retry')
        require(outcome['manifest_sha256'] == anchors[QUAL/'full-freeze-attempt02/MANIFEST.json'], 'Launch uses accepted freeze')
        require([row['case_id'] for row in outcome['cases']] == frozen['schedule'] and
                all(row['status'] == 'completed' for row in outcome['cases']), 'Complete nine-case supervisor accounting')
        require(qualification['status'] == 'passed' and not qualification['dev_or_calibration_data_used'], 'Fictional-only qualification')
        require([row['case_id'] for row in qualification['cases']] == frozen['schedule'], 'Qualification schedule equality')
        require(parity['status'] == 'PASS_captured_source_parity_reconstruction' and
                parity['scheduled_cases'] == 9 and parity['overflow_controls'] == 1, 'Independent nine-case parity reconstruction')
        for proof in parity['input_pins'].values():
            verify(proof)
        verify(parity['reviewer'])
        actual = Path(frozen['qualification_output'])
        events = [json.loads(line) for line in (actual/'events.jsonl').read_text(encoding='utf-8').splitlines()]
        require(events[-1]['event'] == 'completed' and events[-1]['status'] == 'passed', 'Terminal child event')
        require([row['case_id'] for row in events if row['event'] == 'case_completed'] == frozen['schedule'],
                'Events cover each scheduled case exactly once')
        prior = read(QUAL/'actual-launch-attempt01/OUTCOME.json')
        require(prior['status'] != 'completed' and all(row['status'] == 'unexecuted' for row in prior['cases']),
                'Initial checkpoint failure retained with no invented predictions')
        for row in read(QUAL/'pre-legacy-metadata-fix/SOURCE-ARCHIVE.json'):
            verify(dict(path=row['archive'], sha256=row['sha256']))
        supervisor = read(ASSETS/'methods/sc02/SUPERVISOR-REVIEW.json')
        proof = dict(supervisor['qualification'])
        proof['path'] = str(ROOT/proof['path'])
        verify(proof)
        require(proof['tests_run'] == 13 and not proof['errors'] and not proof['failures'], '13 supervisor controls')
        # Seal the complete local qualification tree, failed attempt and audit evidence.
        trees = [actual, QUAL, ASSETS/'methods/sc02/actual-parity-review-attempt01']
        for tree in trees:
            for path in sorted(tree.rglob('*')):
                if path.is_file():
                    observed[str(path.resolve())] = pin(path)
        rows = [r for r in qualification['cases'] if not r.get('rejected')]
        result.update(status='PASS', stage='SC02', source_frozen_pins=len(frozen['pins']),
            fictional_inference_pairs=len(rows), overflow_rejections=1,
            fictional_label_matches=sum(r['semantic_diagnostic_match'] for r in rows),
            resource_measurements=dict(child_wall_seconds=qualification['wall_seconds'],
                supervisor_child_phase_seconds=outcome['observed_child_phase_seconds'],
                model_load_seconds=qualification['model_load_seconds'],
                peak_process_working_set_bytes=qualification['memory']['peak_working_set_bytes'],
                maximum_cuda_allocated_bytes=max(r['cuda_peak_allocated_bytes'] for r in rows),
                maximum_cuda_reserved_bytes=max(r['cuda_peak_reserved_bytes'] for r in rows)),
            scope='Fictional source-level parity on modern runtime; not historical binary parity or SciFact accuracy.',
            next_stage='SC03 remains incomplete; no development predictions made in this qualification.',
            provider_spend_usd=0)
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error))
    result.update(completed_utc=datetime.now(timezone.utc).isoformat(),
                  elapsed_seconds=time.perf_counter()-started, verified_files=list(observed.values()),
                  validator=pin(Path(__file__)))
    with (args.output/'ROOT-ACCEPTANCE.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(dict(status=result['status'], checks=len(checks), files=len(observed),
                         error=result.get('error'), receipt=pin(args.output/'ROOT-ACCEPTANCE.json'))))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
