"""Fresh bracketed qualification of native components; runner is a later gate."""
import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
MODULES=('baseline','data_views','evaluate','native_contract','runtime','split','tether_adapter','worker')
TESTS=('baseline','data_views','policy','runtime','scoring','split','worker')
SCOPE='fictional native component tests; excludes runner integration, real fitting and benchmark results'
EXTRA_SOURCES=()


def pins(paths):
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    output=Path(sys.argv[1]).resolve();output.mkdir(parents=True,exist_ok=False)
    temp=output/'temporary';temp.mkdir()
    os.environ['TEMP']=str(temp);os.environ['TMP']=str(temp);tempfile.tempdir=str(temp)
    paths=[ROOT/'experiments/scifact'/f'{n}.py' for n in MODULES]
    paths += [ROOT/'experiments/scifact/tests'/f'test_scifact_{n}.py' for n in TESTS]
    paths += [Path(path) for path in EXTRA_SOURCES]
    before=pins(paths)
    snapshots=output/'sources';snapshots.mkdir()
    for p in paths:
        dest=snapshots/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    (output/'BEFORE.json').write_text(json.dumps(before,indent=2)+'\n',encoding='utf-8',newline='\n')
    sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'experiments/scifact/tests'))
    suite=unittest.TestLoader().loadTestsFromNames([f'test_scifact_{n}' for n in TESTS])
    started=time.perf_counter()
    with (output/'tests.log').open('x',encoding='utf-8',newline='\n') as stream:
        with contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):
            result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    after=pins(paths)
    report={'schema_version':1,'checked_at_utc':datetime.now(timezone.utc).isoformat(),
            'status':'PASS' if result.wasSuccessful() and not result.skipped and before==after else 'FAIL',
            'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),
            'elapsed_seconds':time.perf_counter()-started,'sources_unchanged':before==after,
            'source_pins':after,'tests_log_sha256':hashlib.sha256((output/'tests.log').read_bytes()).hexdigest(),
            'scope':SCOPE}
    (output/'VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k!='source_pins'}))
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
