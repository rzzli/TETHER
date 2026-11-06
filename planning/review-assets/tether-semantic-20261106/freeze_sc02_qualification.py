"""Freeze one full-checkpoint fictional qualification after component tests."""
import hashlib
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from experiments.scifact_multivers_supervision.supervise import pin, write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', type=int, default=1)
    parser.add_argument('--component-tests', default='component-tests-attempt01')
    args = parser.parse_args()
    if not 1 <= args.attempt <= 99:
        raise ValueError('Invalid attempt number')
    suffix = f'{args.attempt:02d}'
    assets = ROOT / 'planning/review-assets/tether-semantic-20261106'
    acquisition = ROOT / 'data/cache/tether-multivers-acquisition-20261106-attempt01'
    environment = ROOT / 'data/cache/tether-multivers-env-20261106-attempt01'
    receipt = acquisition / 'RECEIPT.json'
    expected = 'a76d300564d0a5a4477a31cf167748e2e5b8540696b1c836d0fb8fab537b1610'
    if pin(receipt)['sha256'] != expected:
        raise ValueError('Original acquisition receipt differs')
    installed = environment / 'INSTALL-RECEIPT.json'
    if pin(installed)['sha256'] != '9291f74f724d8490c2eb0720c0baa341c1e4edea3b3c56910f5ebb826f496961':
        raise ValueError('Installation authority differs')
    tests = assets / 'solver-qualification' / args.component_tests
    if json.loads((tests/'RESULT.json').read_text(encoding='utf-8'))['status'] != 'PASS':
        raise ValueError('Component tests did not pass')
    summary = json.loads((tests/'TEST-SUMMARY.json').read_text(encoding='utf-8'))
    if not summary['passed'] or summary['tests'] < 20 or summary['skips']:
        raise ValueError('Incomplete component qualification')
    output = assets / f'solver-qualification/full-freeze-attempt{suffix}'
    output.mkdir(parents=True, exist_ok=False)
    package = ROOT / 'experiments/scifact_multivers'
    supervisor = ROOT / 'experiments/scifact_multivers_supervision/supervise.py'
    python = environment / 'environment/Scripts/python.exe'
    bundle = assets / 'solver-feasibility'
    controls = package / 'fictional-controls.json'
    schedule = [row['id'] for row in json.loads(controls.read_text(encoding='utf-8'))['cases']]
    child_output = ROOT / f'data/benchmark/scifact_multivers/qualification-20261106-attempt{suffix}'
    paths = [python, supervisor, Path(__file__).resolve(), receipt, installed,
             environment/'FROZEN.json', tests/'RESULT.json', tests/'TEST-SUMMARY.json', controls,
             bundle/'source-receipt.json', bundle/'source-reference-addendum.json',
             bundle/'requirements.lock.txt', bundle/'dependency-lock.json']
    paths += sorted(package.glob('*.py'))
    paths += sorted(p for p in (bundle/'source').rglob('*') if p.is_file())
    site = environment/'environment/Lib/site-packages'
    paths += sorted(site.glob('*.dist-info/RECORD'))
    paths += sorted((site/'transformers/models/longformer').glob('*.py'))
    paths += [site/'transformers/modeling_utils.py', site/'torch/serialization.py', site/'torch/__init__.py']
    paths += sorted((site/'torch').glob('_C*.pyd'))
    paths += sorted((site/'tokenizers').glob('*.pyd'))
    paths += [site/'torch/lib/torch_cpu.dll', site/'torch/lib/torch_cuda.dll', site/'torch/lib/c10.dll']
    pins = [pin(p) for p in dict.fromkeys(paths)]
    manifest = dict(schema_version=1, kind='multivers_qualification_supervision', cwd=str(ROOT),
        launch_output=str(assets/f'solver-qualification/actual-launch-attempt{suffix}'),
        qualification_output=str(child_output), schedule=schedule,
        limits=dict(process_seconds=1800, case_seconds=120, poll_seconds=.05),
        command=[str(python), '-I', '-B', '-X', f'pycache_prefix={ROOT / ("data/cache/sc02-full-qual-pycache"+suffix)}',
                 str(package/'qualify.py'), '--acquisition-root', str(acquisition), '--receipt-sha256', expected,
                 '--reference-bundle', str(bundle), '--output', str(child_output), '--device', 'cuda:0'],
        pins=pins,
        runtime_fingerprint_scope='Installed inventory and wheel authorities plus selected runtime source/binaries; not exhaustive host attestation.',
        purpose='Nine fictional controls only; no SciFact development inference or threshold selection.')
    path = output/'MANIFEST.json'
    write(path, manifest)
    write(output/'RECEIPT.json', dict(status='FROZEN', manifest=pin(path)))
    print(json.dumps(dict(manifest=pin(path), pinned_files=len(pins), scheduled_cases=len(schedule))))


if __name__ == '__main__':
    main()
