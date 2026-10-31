"""Keep final success eligibility after the measured build artifact inventory."""
import ast
import hashlib
import json
from pathlib import Path

base=Path(__file__).resolve().parent
prior=base/"build_native_carrier_component_v3.py"
old=prior.read_bytes()
if hashlib.sha256(old).hexdigest()!="2d0b0ad29ab13ea9a82b01d28238a87c3e4c4eefbacf1a1eff5f0916cb92d3db":raise ValueError("UnchangedV3")
text=old.decode().replace('emit("build_complete_no_execution")','emit("build_commands_prepared_no_execution")',1)
marker='    report = dict(schema_version=1, status=terminal, elapsed_seconds=time.monotonic() - start,\n'
replacement='''    eligibility_elapsed = time.monotonic() - start
    if terminal == "BUILT_NOT_EXECUTED" and eligibility_elapsed >= 60:
        terminal = "BUILD_FAILED"
        failure = dict(type="TimeoutError", message="Final build deadline after artifact inventory",
                       original_dispatch_error=primary_dispatch_error)
        try:
            emit("build_failure", error=failure)
            journal_raw = (out / "build-journal.jsonl").read_bytes()
            for artifact in artifacts:
                if artifact["path"] == str((out / "build-journal.jsonl").relative_to(ROOT)):
                    artifact.update(bytes=len(journal_raw), sha256=digest(journal_raw))
        except BaseException as journal_error:
            failure["journal_error"] = type(journal_error).__name__
    report = dict(schema_version=1, status=terminal, elapsed_seconds=eligibility_elapsed,
'''
if text.count(marker)!=1:raise ValueError("Unique final eligibility")
text=text.replace(marker,replacement)
text=text.replace('clock_scope="The60-second timer starts after input pin checks and exclusive output reservation; interpreter startup/preflight and final report write are excluded",',
                  'clock_scope="The60-second timer starts after input pin checks/reservation and ends at post-inventory eligibility; final report construction/write and any failure-only diagnostic tail are excluded. No new command follows the veto.",',1)
text=text.replace('persistence_scope="Ordinary harness writes, not flush/crash durability; report write outside measured elapsed")',
                  'persistence_scope="Ordinary harness writes, not flush/crash durability; final report construction/write and failure-only diagnostic tail outside measured elapsed")',1)
output=base/"build_native_carrier_component_v4.py";raw=text.encode()
with output.open("xb")as stream:stream.write(raw)
def run_node(payload):
    main=next(n for n in ast.parse(payload).body if isinstance(n,ast.FunctionDef)and n.name=="main")
    return next(n for n in main.body if isinstance(n,ast.FunctionDef)and n.name=="run")
same=ast.dump(run_node(old),include_attributes=False)==ast.dump(run_node(raw),include_attributes=False)
if not same:raise ValueError("Subprocess function must stay unchanged")
record=dict(schema_version=1,status="NAMED_FINAL_ELIGIBILITY_CORRECTION_NOT_EXECUTED",
    before=dict(path=str(prior),bytes=len(old),sha256=hashlib.sha256(old).hexdigest()),
    after=dict(path=str(output),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),
    finding="Same independentD1 batch: final deadline check preceded measured artifact inventory, allowing a late inventory to retain success.",
    correction="Final eligibility sample after inventory. Prepared commands are not final success; late sample yields failed result and failure-only journal tail with refreshed hash. Report construction/write explicitly outside measured sample; no cap reset/increase.",
    subprocess_function_AST_unchanged=same,
    fake_regression_boundary="V3's four fixed subprocess fake controls apply to the identical extracted V4 function; no new fake/native execution is claimed.",
    activity=dict(C_builds=0,native_runs=0,original_target_reads=0))
with(base/"NATIVE-CARRIER-BUILD-FINAL-VETO-CORRECTION-v4.json").open("x",encoding="utf-8")as stream:
    json.dump(record,stream,indent=2);stream.write("\n")
print(json.dumps(record["after"]))
