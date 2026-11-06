"""Retain a fictional counterexample and qualify the supplemental event gate."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
HERE=Path(__file__).parent
OUTPUT=HERE/'extra-event-regression-attempt01'


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    OUTPUT.mkdir(parents=True,exist_ok=False)
    temporary=OUTPUT/'fictional'
    temporary.mkdir()
    tempfile.tempdir=str(temporary)
    fixtures=module('sc03_audit_fixtures',ROOT/'experiments/scifact_comparison/tests/test_audit.py')
    strict=module('sc03_strict_events',HERE/'strict_events.py')
    from experiments.scifact_comparison.inputs import encoded,digest
    fixture=fixtures.AuditTests('test_complete_fixture')
    fixture.setUp()
    # Detach TemporaryDirectory cleanup: the entire fictional counterexample is
    # retained as evidence rather than removed at interpreter shutdown.
    fixture.temp._finalizer.detach()
    root=fixture.root
    journal=[json.loads(line) for line in (root/'journal.jsonl').read_bytes().splitlines()]
    failed=dict(event='pair_failed',monotonic_seconds=journal[3]['monotonic_seconds'],
                details=dict(claim_id=1,abstract_id=2,error='Invented contradictory terminal'))
    journal.insert(4,failed)
    previous='0'*64
    for index,row in enumerate(journal):
        row.pop('sha256',None)
        row.update(sequence=index,previous_sha256=previous)
        previous=digest(row)
        row['sha256']=previous
    (root/'journal.jsonl').write_bytes(b''.join(encoded(row)+b'\n' for row in journal))
    receipt=json.loads((root/'RECEIPT.json').read_bytes())
    receipt.update(journal_last_sha256=previous,journal_records=len(journal))
    (root/'RECEIPT.json').write_bytes(encoded(receipt)+b'\n')
    old=fixture.audit()
    rejection=None
    try:
        strict.verify_order(journal,fixture.requests,{(1,2):json.loads((root/'pairs/1-2.json').read_bytes())})
    except ValueError as error:
        rejection=str(error)
    stream=io.StringIO()
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(strict.EventControls))
    report=dict(status='PASS' if old['status']=='verified' and rejection and tests.wasSuccessful() else 'FAIL',
        fictional_only=True,old_auditor_accepts_counterexample=old['status']=='verified',
        supplemental_gate_rejects=rejection,controls=tests.testsRun,failures=len(tests.failures),errors=len(tests.errors),
        fixture_root=str(root),requirement='No contradictory or unscheduled terminal event may survive final acceptance.',
        disposition='Retain frozen producer/auditor; require separately qualified supplemental gate for final SC03 acceptance.',
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        supplemental_source_sha256=hashlib.sha256((HERE/'strict_events.py').read_bytes()).hexdigest())
    (OUTPUT/'TEST-RESULTS.txt').write_text(stream.getvalue(),encoding='utf-8',newline='\n')
    (OUTPUT/'REGRESSION.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
