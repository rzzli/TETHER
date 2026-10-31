"""Regression-first rejection-summary probe; no native/tokenizer/model access."""
import copy
import hashlib
from importlib import util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
CHECKER=HERE/'check_recognition_validation_v1.py'
REPORT=HERE/'RECOGNITION-COVERAGE-REGRESSION-BEFORE-v2.json'
spec=util.spec_from_file_location('synthetic_wire_coverage_before',CHECKER)
m=util.module_from_spec(spec);spec.loader.exec_module(m)
OBSERVED=[]
class Checks(unittest.TestCase):
    def check_bad(self,kind):
        rows=copy.deepcopy(m.BASE);row=rows[m.first('case_result')]
        if kind=='missing_snapshot':del row['native_state']
        elif kind=='pending_snapshot':row['native_call_counters']['llama_tokenize']['attempted']+=1
        else:row['event']='wrong_event_with_tokens'
        try:m.validate(rows)
        except m.h.RecognitionValidationError as error:
            OBSERVED.append(dict(kind=kind,error=str(error),coverage=error.coverage))
            self.assertEqual(error.coverage['case_results_validated'],0)
            self.assertEqual(error.coverage['cases_computed_claims_validated'],0,
                'No valid result accounting frame was consumed; last durable before_case computed claim is0')
        else:self.fail('Malformed case unexpectedly accepted')
    def test_missing_snapshot_cannot_validate_expected_computation(self):self.check_bad('missing_snapshot')
    def test_pending_snapshot_cannot_validate_expected_computation(self):self.check_bad('pending_snapshot')
    def test_wrong_event_cannot_validate_expected_computation(self):self.check_bad('wrong_event')
def pin(path):
    raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
if __name__=='__main__':
    assert not REPORT.exists();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    value=dict(schema_version=1,status='failed_expected_before_last_observed_coverage_fix' if not result.wasSuccessful() else 'unexpected_pass',
        tests=result.testsRun,failures=[str(c) for c,_ in result.failures],errors=[str(c) for c,_ in result.errors],source=pin(m.SOURCE),
        synthetic_fixture=pin(CHECKER),checker=pin(Path(__file__)),observed=OBSERVED,
        activity=dict(CPU_binary_reads=0,GGUF_reads=0,SDK_constructors=0,native_calls=0,children=0))
    with REPORT.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(REPORT))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
