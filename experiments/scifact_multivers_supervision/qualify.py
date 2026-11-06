"""Retain one fresh standard-library-only supervisor qualification attempt."""
from pathlib import Path
import argparse
import io
import json
import os
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.scifact_multivers_supervision.supervise import fresh_path, pin, write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = fresh_path(str(args.output))
    output.mkdir(parents=True, exist_ok=False)
    (output/'temp').mkdir()
    os.environ.update(TEMP=str(output/'temp'), TMP=str(output/'temp'),
                      SUPERVISION_TEST_ROOT=str(output/'children'))
    sources = [pin(path) for path in sorted(Path(__file__).parent.rglob('*.py'))]
    write(output/'COMMAND.json', {'argv':sys.argv, 'interpreter':pin(sys.executable),
                                'cwd':str(Path.cwd()), 'sources':sources,
                                'scope':'Invented tiny child processes only; no model or benchmark imports.'})
    started = time.monotonic()
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent/'tests'), pattern='test_*.py')
    with (output/'tests.txt').open('x', encoding='utf-8', newline='\n') as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    unchanged = all(pin(item['path']) == item for item in sources)
    record = {'status':'PASS' if result.wasSuccessful() and unchanged else 'FAIL',
              'tests_run':result.testsRun, 'failures':len(result.failures), 'errors':len(result.errors),
              'sources_unchanged':unchanged, 'elapsed_seconds':time.monotonic()-started,
              'sources':sources, 'interpreter':pin(sys.executable),
              'models_loaded':False, 'benchmark_rows_read':False, 'automatic_retry':False}
    write(output/'QUALIFICATION.json', record)
    print(json.dumps(record, sort_keys=True))
    return 0 if record['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
