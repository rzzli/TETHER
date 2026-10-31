"""Independent three-regression BEFORE proof on preserved a687 source."""
import json
from pathlib import Path
import sys
import time
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import check_raw_adoption_core_v2 as BASE
import raw_adoption_regressions_v3 as R

REPORT=HERE/'RAW-ADOPTION-INDEPENDENT-THREE-REGRESSIONS-BEFORE-v3.json'
class BeforeTests(unittest.TestCase):pass
R.add_tests(BeforeTests,BASE.D,BASE.CORE,BASE.fresh)

if __name__=='__main__':
    assert not REPORT.exists()
    started=time.monotonic()
    before=BASE.D.pin(BASE.SOURCE)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BeforeTests))
    report=dict(schema_version=1,status='expected_before_failures' if result.failures and not result.errors else 'unexpected_result',methods=result.testsRun,failures=[dict(test=str(t),detail=s) for t,s in result.failures],errors=[dict(test=str(t),detail=s) for t,s in result.errors],source=before,source_unchanged=BASE.D.pin(BASE.SOURCE)==before,regressions=BASE.D.pin(HERE/'raw_adoption_regressions_v3.py'),checker=BASE.D.pin(Path(__file__).resolve()),preserved_full=BASE.D.pin(HERE/'RAW-ADOPTION-CORE-DRIVER-PURE-PROOF-v2.json'),audit_denials=BASE.D.AUDIT_DENIALS,elapsed_seconds=time.monotonic()-started,actual_API_calls=0,FFI_registration_proven=False,production_owner_bound=False,runtime_authorized=False,scope='Exact independent three-boundary before regressions only; no FFI/old sources or payloads.')
    with REPORT.open('xb') as out:out.write(BASE.D.canonical(report)+b'\n')
    print(json.dumps(dict(proof=BASE.D.pin(REPORT),status=report['status'],methods=result.testsRun,failures=len(result.failures),errors=len(result.errors))))
