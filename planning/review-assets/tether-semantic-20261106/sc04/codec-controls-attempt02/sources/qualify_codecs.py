"""Retain invented-input SC04 codec checks without model or benchmark execution."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    source=ROOT/'experiments/litqa_comparison'
    pins={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*.py')}
    log=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(source/'tests'),pattern='test_*.py')
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    (args.output/'TEST-RESULTS.txt').write_text(log.getvalue(),encoding='utf-8',newline='\n')
    report=dict(status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,
                failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
                source_sha256=pins,scope='Invented codec/selection controls only; no real model or benchmark.')
    (args.output/'QUALIFICATION.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'}))
    if not result.wasSuccessful():print(log.getvalue())
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
