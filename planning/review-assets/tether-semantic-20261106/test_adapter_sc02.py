"""Retain one bounded run of the adapter's fictional component tests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]


def write(path, data):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write('\n')


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    temp = output / 'temp'
    temp.mkdir()
    sources = sorted((ROOT / 'experiments/scifact_multivers').rglob('*.py'))
    before = [pin(p) for p in sources]
    code = (
        'import sys,json,unittest;from pathlib import Path;'
        f'sys.path.insert(0,{str(ROOT)!r});'
        'import torch;torch.set_num_threads(2);'
        f'suite=unittest.defaultTestLoader.discover({str(ROOT / "experiments/scifact_multivers/tests")!r});'
        'result=unittest.TextTestRunner(verbosity=2).run(suite);'
        "summary=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),passed=result.wasSuccessful());"
        f'Path({str(output / "TEST-SUMMARY.json")!r}).write_bytes((json.dumps(summary,indent=2)+"\\n").encode("utf-8"));'
        'sys.exit(0 if result.wasSuccessful() else 1)'
    )
    argv = [str(args.python.resolve()), '-I', '-B', '-X', f'pycache_prefix={output / "fresh-pycache"}', '-c', code]
    env = dict(os.environ, TEMP=str(temp), TMP=str(temp), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', PYTHONUTF8='1')
    write(output / 'FROZEN.json', dict(command=argv, timeout_seconds=300, sources=before,
          interpreter=pin(args.python.resolve()), controller=pin(Path(__file__).resolve()),
          scope='Fictional component/reference tests only; no released model or benchmark inference.'))
    started = time.perf_counter()
    result = dict(status='FAIL')
    with (output / 'stdout.txt').open('xb') as stdout, (output / 'stderr.txt').open('xb') as stderr:
        try:
            process = subprocess.run(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, timeout=300)
            result.update(returncode=process.returncode, status='PASS' if process.returncode == 0 else 'FAIL')
        except BaseException as error:
            result.update(error_type=type(error).__name__, error=str(error))
        finally:
            preserved = before == [pin(p) for p in sources]
            result.update(source_preserved=preserved, elapsed_seconds=time.perf_counter()-started)
            if not preserved:
                result['status'] = 'FAIL'
            write(output / 'RESULT.json', result)
    print(json.dumps(result))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
