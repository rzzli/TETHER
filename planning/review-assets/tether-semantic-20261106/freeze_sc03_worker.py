"""Freeze a SC03 resident-worker execution; fictional rehearsal precedes production."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from experiments.scifact_comparison.prepare import pin, read, write, write_rows
from experiments.scifact_comparison.inputs import CONDITIONS, need, validate_requests

ASSETS = ROOT/'planning/review-assets/tether-semantic-20261106'
ACQUISITION = ROOT/'data/cache/tether-multivers-acquisition-20261106-attempt01'
ENVIRONMENT = ROOT/'data/cache/tether-multivers-env-20261106-attempt01/environment'
SC02_ACCEPTANCE = 'bb21dfe9c08f01796457dcf634dcc9a9bc9082c9aec711e765d1b71b5a974ef4'
ACQUISITION_SHA = 'a76d300564d0a5a4477a31cf167748e2e5b8540696b1c836d0fb8fab537b1610'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['fictional','production'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--worker-output', type=Path, required=True)
    parser.add_argument('--tests', type=Path, required=True)
    parser.add_argument('--tests-sha256', required=True)
    parser.add_argument('--prepared', type=Path)
    parser.add_argument('--prepared-sha256')
    parser.add_argument('--condition', choices=CONDITIONS, default='primary')
    parser.add_argument('--rehearsal-acceptance', type=Path)
    parser.add_argument('--rehearsal-sha256')
    args = parser.parse_args()
    output = args.output.resolve()
    child = args.worker_output.resolve()
    need(not output.exists() and not child.exists(), 'Fresh freeze and child outputs required')
    need(output.is_relative_to(ROOT) and child.is_relative_to(ROOT), 'Workspace paths required')
    gate = ASSETS/'sc02-acceptance-attempt01/ROOT-ACCEPTANCE.json'
    need(pin(gate)['sha256'] == SC02_ACCEPTANCE and read(gate)['status'] == 'PASS', 'SC02 acceptance differs')
    need(pin(args.tests)['sha256'] == args.tests_sha256, 'Tests external anchor differs')
    tests = read(args.tests)
    need(tests['status'] == 'PASS' and tests['tests'] >= 31 and not tests['skipped'], 'Worker tests incomplete')
    for proof in tests['source_pins']:
        need(pin(proof['path']) == proof, 'Tested source changed')
    accepted = read(ASSETS/'solver-qualification/full-freeze-attempt02/MANIFEST.json')
    pins = {p['path']:p for p in accepted['pins']}
    for proof in pins.values():
        need(pin(proof['path']) == proof, 'Qualified runtime/source changed')
    output.mkdir(parents=True, exist_ok=False)
    extra = [gate, args.tests, Path(__file__), ROOT/'planning/TETHER SciFact Full Context Protocol 2026-11-06.md']
    if args.mode == 'fictional':
        need(not args.prepared and not args.prepared_sha256 and args.condition == 'primary', 'Fictional mode excludes actual inputs')
        controls_path = ROOT/'experiments/scifact_multivers/fictional-controls.json'
        controls = read(controls_path)
        source = controls['cases'][0]
        requests = [dict(id=90001, claim=source['claim'], documents=[
            dict(doc_id=91001+i, title=source['title'], abstract=list(source['sentences'])) for i in range(5)])]
        write_rows(output/'fictional-requests.jsonl', requests)
        request_pin = pin(output/'fictional-requests.jsonl')
        schedule = validate_requests(requests)
        extra.append(controls_path)
    else:
        need(args.prepared is not None and args.rehearsal_acceptance is not None, 'Actual inputs and accepted rehearsal required')
        need(pin(args.prepared)['sha256'] == args.prepared_sha256, 'Prepared manifest anchor differs')
        need(pin(args.rehearsal_acceptance)['sha256'] == args.rehearsal_sha256 and
             read(args.rehearsal_acceptance)['status'] == 'PASS', 'Actual worker rehearsal not accepted')
        prepared = read(args.prepared)
        need(prepared['status'] == 'prepared' and len(prepared['schedule']) == 300, 'Full prepared denominator required')
        request_pin = prepared['conditions'][args.condition]['requests']
        schedule = prepared['schedule']
        for proof in prepared['source_pins'] + prepared['source_parents']:
            need(pin(proof['path']) == proof, 'Preparation source/parent changed')
            pins[proof['path']] = proof
        extra += [args.prepared, args.rehearsal_acceptance,
                  Path(prepared['conditions'][args.condition]['lineage']['path'])]
    need(pin(request_pin['path']) == request_pin, 'Prepared requests changed')
    recipe = dict(schema_version=1, kind='sc03_condition_worker', condition=args.condition,
        requests=request_pin, schedule=schedule, acquisition_root=str(ACQUISITION),
        acquisition_receipt_sha256=ACQUISITION_SHA, device='cuda:0', pair_seconds=120, output_bytes=2*1024**3)
    write(output/'RECIPE.json', recipe)
    entrypoint = ROOT/'experiments/scifact_comparison/worker.py'
    extra += [output/'RECIPE.json', Path(request_pin['path'])]
    extra += sorted((ROOT/'experiments/scifact_comparison').rglob('*.py'))
    for path in extra:
        proof = pin(path)
        pins[proof['path']] = proof
    manifest = dict(schema_version=1, kind='multivers_qualification_supervision',
        purpose='SC03 ' + args.mode + '; legacy supervisor schema reused without changing its checked process/event protocol.',
        cwd=str(ROOT), launch_output=str(output/'launch'), qualification_output=str(child),
        schedule=[str(x) for x in schedule], limits=dict(process_seconds=1800, case_seconds=120, poll_seconds=.05),
        command=[str(ENVIRONMENT/'Scripts/python.exe'), '-I', '-B', '-X',
                 f'pycache_prefix={output / "fresh-pycache"}', str(entrypoint),
                 '--recipe', str(output/'RECIPE.json'), '--recipe-sha256', pin(output/'RECIPE.json')['sha256'],
                 '--output', str(child)], pins=list(pins.values()),
        benchmark_inference=args.mode == 'production', condition=args.condition)
    write(output/'MANIFEST.json', manifest)
    write(output/'RECEIPT.json', dict(status='FROZEN', manifest=pin(output/'MANIFEST.json')))
    print(json.dumps(dict(manifest=pin(output/'MANIFEST.json'), mode=args.mode, claims=len(schedule))))


if __name__ == '__main__':
    main()
