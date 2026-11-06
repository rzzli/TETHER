"""Bounded fictional worker/control qualification; no actual model loading."""
import argparse
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from experiments.scifact_comparison.prepare import pin, write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    temp = args.output/'temp'
    temp.mkdir()
    os.environ['TEMP'] = os.environ['TMP'] = str(temp)
    tempfile.tempdir = str(temp)
    sources = sorted(Path(__file__).parent.rglob('*.py'))
    before = [pin(p) for p in sources]
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent/'tests'))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    with (args.output/'TEST-RESULTS.txt').open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(stream.getvalue())
    preserved = before == [pin(p) for p in sources]
    report = dict(status='PASS' if result.wasSuccessful() and preserved else 'FAIL', tests=result.testsRun,
        failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        source_pins=before, source_preserved=preserved, model_or_benchmark_execution=False)
    write(args.output/'QUALIFICATION.json', report)
    print(json.dumps({k:v for k,v in report.items() if k != 'source_pins'}))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
