"""Close SC03 by joining independently retained gates and rechecking their bytes.

This is an acceptance aggregator, not a replacement semantic evaluator.
No inference or scientific threshold selection is performed here.
"""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
FRAME_SHA = '3c96f903256acf7fc7003cfa5c3abb7e24541741a7f1851e5b2dd48cd394458c'
RESULT_SHA = 'cec2984ec5d677c1867969ac916b97c2b7e8f1305eb3b527b327383adedbff8e'
ANALYSIS_SHA = 'ff8a0df3e6584d3891dd4e3a3a471c8ccaaeb5e9a497f596be1162002d244163'


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    checks = 0
    anchors = {}
    report = dict(status='FAIL', created_at=datetime.now(timezone.utc).isoformat())

    def check(value, reason):
        nonlocal checks
        checks += 1
        if not value:
            raise ValueError(reason)

    def anchored(path, expected=None):
        digest = sha(path)
        if expected:
            check(digest == expected, 'Changed anchor: '+str(path))
        anchors[str(Path(path).resolve())] = digest
        return read(path)

    def proof(p):
        check(Path(p['path']).stat().st_size == p['bytes'] and sha(p['path']) == p['sha256'],
              'Changed proof: '+p['path'])

    try:
        frame = anchored(HERE/'production-freeze-attempt01/EXPERIMENT.json', FRAME_SHA)
        results = anchored(HERE/'production-freeze-attempt01/execution/RESULT-ANCHORS.json', RESULT_SHA)
        analysis = Path(frame['analysis_output'])
        receipt = anchored(analysis/'RECEIPT.json', ANALYSIS_SHA)
        check(receipt['frame_sha256'] == results['frame_sha256'] == FRAME_SHA and
              receipt['result_anchors_sha256'] == RESULT_SHA and receipt['status'] == 'complete', 'Analysis/frame joins')
        for p in frame['pins']:
            proof(p)
        for name, p in receipt['files'].items():
            check(Path(p['path']).resolve() == (analysis/name).resolve(), 'Analysis path binding')
            proof(p)
        check({p.relative_to(analysis).as_posix() for p in analysis.rglob('*') if p.is_file()} ==
              set(receipt['files']) | {'RECEIPT.json'}, 'Exact analysis inventory')
        independent = anchored(HERE/'independent-analysis-attempt01/INDEPENDENT-REVIEW.json')
        check(independent['status'] == 'PASS' and independent['checks'] == 30220 and
              independent['frame_sha256'] == FRAME_SHA and independent['analysis_receipt_sha256'] == ANALYSIS_SHA and
              independent['production_modules_imported'] is False, 'Independent reconstruction')
        check(sha(HERE/'independent_analysis.py') == independent['reviewer_sha256'], 'Independent code')
        source = anchored(HERE/'independent-analysis-attempt01/raw-source-preflight/PREFLIGHT.json')
        check(source['status'] == 'PASS', 'Original source/baseline reconstruction')
        strict = anchored(HERE/'strict-event-review-attempt01/STRICT-EVENT-REVIEW.json')
        check(strict['status'] == 'PASS' and strict['tests'] == 5 and strict['errors'] == strict['failures'] == 0,
              'Supplemental contradictory-event regression')
        check(sha(HERE/'strict_events.py') == strict['source_sha256'], 'Supplemental code')
        for path, digest in strict['observed_file_hashes'].items():
            check(sha(path) == digest, 'Changed admitted worker/supervisor file: '+path)
        controls = anchored(HERE/'production-components-attempt02/QUALIFICATION.json')
        check(controls['status'] == 'PASS' and controls['tests'] == 62 and
              controls['errors'] == controls['failures'] == controls['skipped'] == 0, 'Component qualification')
        for p in controls['source_pins']:
            proof(p)
        for filename in ['input-review-attempt01/INPUT-REVIEW.json',
                         'worker-rehearsal-acceptance01/ACCEPTANCE.json',
                         'production-auditor-rehearsal01/VERIFIED.json']:
            gate = anchored(HERE/filename)
            check(gate['status'] in ('PASS', 'verified'), 'Qualification gate '+filename)
        measured = read(analysis/'REPORT.json')
        check(measured['primary_counts']['produced'] == measured['primary_counts']['accepted'] == 300 and
              measured['primary_counts']['correct_raw'] == measured['primary_counts']['correct_and_admitted'] == 127,
              'All-scheduled primary result')
        evaluation = read(analysis/'EVALUATION.json')
        check(evaluation['raw_metrics'] == evaluation['checked_metrics'], 'Raw/checked equality')
        boot = read(analysis/'PAIRED-BOOTSTRAP.json')
        check(boot['replicates'] == 10000 and boot['components'] == 247 and boot['claims'] == 300 and
              boot['seed'] == 20261106 and len(boot['metrics']) == 13, 'Declared paired uncertainty')
        prepared = read(frame['prepared']['path'])
        resources = {}
        check(results['condition_order'] == frame['condition_order'] and len(frame['condition_order']) == 5,
              'Complete condition schedule')
        for condition in frame['condition_order']:
            proof(frame['conditions'][condition])
            binding = results['conditions'][condition]
            for p in binding.values():
                if isinstance(p, dict) and {'path','sha256','bytes'} <= set(p):
                    proof(p)
            launch = read(frame['conditions'][condition]['path'])
            root = Path(launch['qualification_output'])
            outcome = read(binding['supervisor_outcome']['path'])
            check(outcome['status'] == 'completed' and outcome['all_frozen_pins_unchanged'], 'Supervised completion')
            actual_files = {str(p.resolve()) for tree in (root,Path(launch['launch_output']))
                            for p in tree.rglob('*') if p.is_file()}
            check(actual_files <= set(strict['observed_file_hashes']), 'Unreviewed output file')
            check(strict['conditions'][condition] == dict(claims=300,pairs=1500,journal_events=5102,supervisor_signals=604),
                  'Exact ordered event coverage')
            worker = read(root/'REPORT.json')
            counts = worker['counts']
            check(counts['completed_pairs'] == 1500 and counts['completed_claims'] == counts['complete_prediction_claims'] == 300
                  and counts['input_unavailable_pairs'] == counts['overlength_pairs'] == counts['unexpected_failed_pairs'] == 0,
                  'Complete condition accounting')
            pairs = [read(p) for p in (root/'pairs').glob('*.json')]
            check(len(pairs) == 1500 and all(p['status'] == 'completed' and p['model_dispatch'] for p in pairs), 'Actual forwards')
            obs = [p['observations'] for p in pairs]
            request_proof = prepared['conditions'][condition]['requests']
            proof(request_proof)
            resources[condition] = dict(worker=worker, request_jsonl_bytes=request_proof['bytes'],
                transformer_input_tokens=sum(p['token_count'] for p in obs),
                max_pair_input_tokens=max(p['token_count'] for p in obs),
                cuda_peak_allocated_bytes=max(p['cuda_peak_allocated_bytes'] for p in obs),
                cuda_peak_reserved_bytes=max(p['cuda_peak_reserved_bytes'] for p in obs),
                total_forward_seconds=sum(p['forward_seconds'] for p in obs),
                generated_output_tokens=0, actual_model_forwards=1500,
                all_output_files_bytes=sum(Path(p).stat().st_size for p in actual_files))
        report.update(status='PASS', scope='SC03 measurement complete; SC04–SC09 remain incomplete.',
            scientific_validation='Exposed SciFact development comparison; no independent biological validation.',
            required_gates=['frozen production audit','exact-event supplement','independent source/native/bootstrap reconstruction'],
            known_verifier_limit='Original standalone auditor permits extra terminal events; supplemental exact-event gate is mandatory.',
            primary_counts=measured['primary_counts'], primary_metrics=measured['primary_metrics'],
            baseline_metrics=measured['baseline_metrics'], bootstrap=boot, diagnostics=measured['diagnostics'],
            resources=resources, analysis_wall_seconds=measured['analysis_wall_seconds'],
            provider_cost_usd=0, original_analysis_report_preserved=True,
            original_analysis_pending_label='Superseded by this joined acceptance; original sealed report remains unchanged.')
    except BaseException as error:
        report.update(error_type=type(error).__name__, error=str(error))
    report.update(checks=checks, anchors=anchors, acceptance_code_sha256=sha(__file__))
    (args.output/'ROOT-ACCEPTANCE.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k in ('status','checks','error','error_type','scope')}))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
