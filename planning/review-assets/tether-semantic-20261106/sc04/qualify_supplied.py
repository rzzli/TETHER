"""Retain supplied-source fixture results; does not dispatch HTTP or a model."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    temporary=ROOT/'data/cache/sc04-supplied-tests';temporary.mkdir(parents=True,exist_ok=True);tempfile.tempdir=str(temporary)
    root=ROOT/'experiments/litqa_supplied'
    pins={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*.py')}
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.discover(str(root),pattern='test_*.py'))
    (args.output/'TEST-RESULTS.txt').write_text(log.getvalue(),encoding='utf-8',newline='\n')
    report=dict(status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                skipped=len(result.skipped),source_sha256=pins,scope='Invented supplied DOI resolution only; no network, model or clinical claims.')
    (args.output/'QUALIFICATION.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'}))
    if not result.wasSuccessful():print(log.getvalue());raise SystemExit(1)


if __name__=='__main__':main()
