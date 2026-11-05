"""Retain fresh runner QA without hashing a receipt into its own inputs.

Run once under the original qualified Python. This checks invented inputs only;
it does not prepare, execute or score the corrected benchmark corpus.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[4]
PYTHON = PROJECT / 'data/cache/tether-051-installed-qualification-attempt02/environment/Scripts/python.exe'
QUALIFIED = PYTHON.parents[2]
RAW = PROJECT / 'data/cache/tether-equal-policy-v2-runner-qualification-20261105-attempt03'
DESTINATION = Path(__file__).with_name('QUALIFICATION-CLOSURE-20261105.json')
SOURCES = [PROJECT / 'experiments/equal_policy_v2' / name for name in (
    'run_comparison.py', 'worker.py', 'reference.py', 'test_runner.py', 'test_reference_worker.py')]
SOURCES.append(Path(__file__).resolve())


def pin(path):
    return dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)


def publish(path, value):
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')


def run(label, arguments, *, parse=True):
    command = [str(PYTHON), *arguments]
    result = subprocess.run(command, cwd=PROJECT, capture_output=True, timeout=120, check=False)
    (RAW / (label + '.stdout')).write_bytes(result.stdout)
    (RAW / (label + '.stderr')).write_bytes(result.stderr)
    publish(RAW / (label + '.command.json'), dict(argv=command, exit_code=result.returncode))
    if result.returncode:
        raise RuntimeError(label + ' failed; inspect retained logs')
    return json.loads(result.stdout) if parse else result


def main():
    if DESTINATION.exists():
        raise FileExistsError('Never replace a retained qualification')
    RAW.mkdir(parents=True, exist_ok=False)
    before = {str(path.relative_to(PROJECT)).replace('\\', '/'): pin(path) for path in SOURCES}
    try:
        tests = run('unit', ['-B', '-m', 'unittest', 'experiments.equal_policy_v2.test_runner',
                    'experiments.equal_policy_v2.test_reference_worker', '-v'], parse=False)
        count = int(re.search(rb'Ran (\d+) tests', tests.stderr).group(1))
        if count != 42:
            raise RuntimeError('Unexpected runner test inventory')
        trusted = run('trusted-runtime', ['-I', '-B', str(PROJECT / 'experiments/equal_policy_v2/reference.py'),
                                         '--trusted-runtime', str(QUALIFIED)])
        if trusted['versions'] != dict(tether='0.5.1', asof='0.3.12'):
            raise RuntimeError('Unexpected native qualification runtime')
        original = QUALIFIED / 'asof-demo'
        copy = RAW / 'native-prose-copy'
        original_pin = pin(original / 'dossier.md')
        shutil.copytree(original, copy)
        expected = (copy / 'dossier.md').read_bytes().replace(b'\r\n', b'\n')
        prose = run('native-prose', ['-I', '-B', str(PROJECT / 'experiments/equal_policy_v2/reference.py'),
                                   '--rerender-dossier', str(copy)])
        if ((copy / 'dossier.md').read_bytes() != expected or prose['unscored'] is not True
                or pin(copy / 'dossier.md') != {key: prose[key] for key in ('sha256', 'bytes')}
                or pin(original / 'dossier.md') != original_pin):
            raise RuntimeError('Native prose qualification differs')
        bundle = RAW / 'invented-worker-bundle'
        bundle.mkdir()
        publish(bundle / 'descriptor.json', dict(schema_version=1, control_id='QA-ONLY',
            operation='invented_invalid', variant='core_v2_catalog1', paths={}, options={}, anchors={}))
        workers = {}
        for arm in ('tether', 'independent', 'hash_schema', 'reject_all'):
            answer = run('worker-' + arm, ['-I', '-B', str(PROJECT / 'experiments/equal_policy_v2/worker.py'),
                '--implementation', arm, '--root', str(bundle), '--descriptor', 'descriptor.json',
                '--scratch', str(RAW / ('scratch-' + arm))])
            runtime = answer['runtime']
            if (answer['result']['decision'] != 'reject' or runtime['isolated'] is not True
                    or runtime['repository_product_source_on_path']
                    or (arm != 'tether' and runtime['loaded_product_modules'])):
                raise RuntimeError('Worker isolation/dispatch smoke differs: ' + arm)
            workers[arm] = dict(decision=answer['result']['decision'], runtime=runtime)
        after = {str(path.relative_to(PROJECT)).replace('\\', '/'): pin(path) for path in SOURCES}
        if after != before:
            raise RuntimeError('Qualified source changed during tests')
        sys.path.insert(0, str(PROJECT / 'experiments'))
        from equal_policy import run_comparison as original_runner
        old = PROJECT / 'data/benchmark/tether-equal-policy-20261102-attempt03'
        unchanged = original_runner.check_frozen(old, json.loads((old / 'FROZEN.json').read_bytes()))
        if not all(unchanged.values()):
            raise RuntimeError('Original frozen experiment changed')
        inputs = sorted(set(SOURCES) | {path for path in RAW.rglob('*') if path.is_file()})
        rows = [dict(path=path.relative_to(PROJECT).as_posix(), **pin(path)) for path in inputs]
        report = dict(schema_version=1, status='PASS_RUNNER_QUALIFICATION', tests=count,
            scope='Invented terminal/input records and original installed native helper smoke only; no corpus scoring',
            source_before=before, source_after=after, pins=rows, versions=trusted['versions'],
            native_prose=dict(normalized_prose_identical=True, original_unchanged=True),
            workers=workers, original_frozen_checks=unchanged,
            recursion='Receipt pins source bytes and preexisting logs; it never pins itself. FROZEN later pins receipt plus sources.',
            previous_qualification='runner/QUALIFICATION-20261105.json is historical; this receipt qualifies current execution sources')
        publish(RAW / 'QUALIFICATION.json', report)
        tracked = dict(report)
        tracked['pins'] = [*rows, dict(path=(RAW / 'QUALIFICATION.json').relative_to(PROJECT).as_posix(),
                                    **pin(RAW / 'QUALIFICATION.json'))]
        publish(DESTINATION, tracked)
        from equal_policy_v2 import run_comparison as current_runner
        closure = current_runner.source_pins()
        publish(RAW / 'CLOSURE-CHECK.json', dict(status='PASS', source_files=len(closure),
            qualification_files=len(current_runner.qualification_evidence()),
            original_source_files=len(original_runner.source_pins()),
            current_receipt_pin=pin(DESTINATION)))
        print(json.dumps(dict(status='PASS', tests=count, frozen_source_files=len(closure),
                              receipt=str(DESTINATION))))
    except BaseException as error:
        publish(RAW / 'FAILURE.json', dict(status='FAILED', error_class=type(error).__name__, reason=str(error)))
        raise


if __name__ == '__main__':
    main()
