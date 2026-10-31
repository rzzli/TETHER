"""Apply the reviewed failure/status rule to the never-run runtime helper."""
from pathlib import Path
import hashlib
import json

base=Path(__file__).resolve().parent
prior=base/"run_native_carrier_fake_tests_v1.py";old=prior.read_bytes();text=old.decode()
text=text.replace('emit("run_terminal",status=outcome,failure=failure,grade_error=grade_error)',
                  'emit("run_prepared_status",status=outcome,failure=failure,grade_error=grade_error)',1)
before='''    except BaseException as error:
        failure=failure or dict(type=type(error).__name__,message=str(error))
'''
after='''    except BaseException as error:
        outcome="FAILED"
        failure=failure or dict(type=type(error).__name__,message=str(error))
'''
if text.count(before)!=1:raise ValueError("Unique runtime main catch")
text=text.replace(before,after)
before='''    files=[]
    for path in sorted(output.iterdir()):
        if path.is_file():
            raw=path.read_bytes();files.append(dict(path=str(path.relative_to(ROOT)),bytes=len(raw),sha256=sha(raw)))
'''
after='''    files=[];inventory_complete=False
    try:
        for path in sorted(output.iterdir()):
            if path.is_file():
                raw=path.read_bytes();files.append(dict(path=str(path.relative_to(ROOT)),bytes=len(raw),sha256=sha(raw)))
        inventory_complete=True
    except BaseException as error:
        outcome="FAILED"
        failure=failure or dict(type=type(error).__name__,message=str(error),stage="artifact_inventory")
    eligibility_elapsed=time.monotonic()-started
    if outcome=="ALL_79_FAKE_TARGET_CONTROLS_PASSED"and eligibility_elapsed>=60:
        outcome="FAILED"
        failure=dict(type="TimeoutError",message="Final post-inventory runtime deadline")
'''
if text.count(before)!=1:raise ValueError("Unique runtime inventory")
text=text.replace(before,after)
text=text.replace('elapsed_seconds=time.monotonic()-started,commands=commands,failure=failure,',
                  'elapsed_seconds=eligibility_elapsed,commands=commands,failure=failure,artifact_inventory_complete=inventory_complete,',1)
text=text.replace('clock_scope="Input checks/reservation precede timer; final report write/startup excluded. No whole-process resource fit or durability claim.")',
                  'clock_scope="Input checks/reservation precede timer through post-inventory eligibility; final report construction/write/startup excluded. No whole-process resource fit or durability claim.")',1)
before='''    report_path.write_text(json.dumps(report,indent=2)+"\\n",encoding="utf-8")
    print(json.dumps(dict(status=outcome,path=str(report_path),failure=failure,grade_error=grade_error)))
'''
after='''    try:
        report_path.write_text(json.dumps(report,indent=2)+"\\n",encoding="utf-8")
    except BaseException as error:
        reporting_failure=dict(type=type(error).__name__,message=str(error))
        try:emit("run_report_write_failure",status="FAILED",error=reporting_failure)
        except BaseException as journal_error:reporting_failure["journal_error"]=type(journal_error).__name__
        print(json.dumps(dict(status="FAILED",path=None,failure=failure,reporting_failure=reporting_failure)))
        return 1
    print(json.dumps(dict(status=outcome,path=str(report_path),failure=failure,grade_error=grade_error)))
'''
if text.count(before)!=1:raise ValueError("Unique runtime report")
text=text.replace(before,after)
output=base/"run_native_carrier_fake_tests_v2.py";raw=text.encode()
with output.open("xb")as stream:stream.write(raw)
record=dict(schema_version=1,status="ROOT_PREFREEZE_RUNTIME_STATUS_CORRECTION_NO_IMAGE_EXECUTION",
    before=dict(path=str(prior),bytes=len(old),sha256=hashlib.sha256(old).hexdigest()),
    after=dict(path=str(output),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),
    correction="Prepared status cannot survive outer exception/inventory/final deadline/report-write failure as success. Exact expected79 bytes/counters and extracted reviewed subprocess function remain unchanged. Runtime peer and separate Root image binding are still required.",
    actual_processes=0,C_builds=0,C_subject_runs=0)
with(base/"NATIVE-CARRIER-RUNTIME-STATUS-CORRECTION-v2.json").open("x",encoding="utf-8")as stream:
    json.dump(record,stream,indent=2);stream.write("\n")
print(json.dumps(record["after"]))
