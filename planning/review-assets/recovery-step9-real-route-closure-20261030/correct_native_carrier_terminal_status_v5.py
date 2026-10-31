"""Close the retained build failure/status paths without changing commands."""
import ast
import hashlib
import json
from pathlib import Path

base=Path(__file__).resolve().parent
prior=base/"build_native_carrier_component_v4.py";old=prior.read_bytes()
if hashlib.sha256(old).hexdigest()!="a0641dc6cff79514a0d641290e30b15e8be5dc2b06411d561396c1b9b9c9e291":raise ValueError("UnchangedV4")
text=old.decode().replace('    results = []\n','    results = []\n    secondary_errors = []\n',1)
before='''    except BaseException as caught:
        failure = dict(type=type(caught).__name__, message=str(caught), original_dispatch_error=primary_dispatch_error)
'''
after='''    except BaseException as caught:
        terminal = "BUILD_FAILED"
        failure = dict(type=type(caught).__name__, message=str(caught), original_dispatch_error=primary_dispatch_error)
'''
if text.count(before)!=1:raise ValueError("Unique main catch")
text=text.replace(before,after)
before='''    artifacts = []
    for path in sorted(out.iterdir()):
        if path.is_file():
            raw = path.read_bytes()
            artifacts.append(dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=digest(raw)))
'''
after='''    artifacts = []
    inventory_complete = False
    try:
        for path in sorted(out.iterdir()):
            if path.is_file():
                raw = path.read_bytes()
                artifacts.append(dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=digest(raw)))
        inventory_complete = True
    except BaseException as inventory_error:
        terminal = "BUILD_FAILED"
        observed = dict(stage="artifact_inventory", type=type(inventory_error).__name__, message=str(inventory_error))
        secondary_errors.append(observed)
        if failure is None:
            failure = dict(type=type(inventory_error).__name__, message=str(inventory_error), original_dispatch_error=primary_dispatch_error)
        try:
            emit("build_failure", stage="artifact_inventory", error=observed)
            journal_raw = (out / "build-journal.jsonl").read_bytes()
            for artifact in artifacts:
                if artifact["path"] == str((out / "build-journal.jsonl").relative_to(ROOT)):
                    artifact.update(bytes=len(journal_raw), sha256=digest(journal_raw))
        except BaseException as inventory_journal_error:
            secondary_errors.append(dict(stage="inventory_failure_journal", type=type(inventory_journal_error).__name__))
'''
if text.count(before)!=1:raise ValueError("Unique inventory")
text=text.replace(before,after)
text=text.replace('                  failure=failure, executable_dispatches=0, original_payload_reads=0,',
                  '                  failure=failure, secondary_errors=secondary_errors, artifact_inventory_complete=inventory_complete,\n                  executable_dispatches=0, original_payload_reads=0,',1)
before='''    (out / "build-result.json").write_text(json.dumps(report, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(dict(status=terminal, result=str(out / "build-result.json"), failure=failure)))
'''
after='''    try:
        (out / "build-result.json").write_text(json.dumps(report, indent=2) + "\\n", encoding="utf-8")
    except BaseException as report_error:
        reporting_failure = dict(type=type(report_error).__name__, message=str(report_error))
        try:
            emit("build_report_write_failure", status="BUILD_FAILED", error=reporting_failure)
        except BaseException as report_journal_error:
            reporting_failure["journal_error"] = type(report_journal_error).__name__
        print(json.dumps(dict(status="BUILD_FAILED", result=None, failure=failure, reporting_failure=reporting_failure)))
        return 1
    print(json.dumps(dict(status=terminal, result=str(out / "build-result.json"), failure=failure)))
'''
if text.count(before)!=1:raise ValueError("Unique final reporting")
text=text.replace(before,after)
output=base/"build_native_carrier_component_v5.py";raw=text.encode()
with output.open("xb")as stream:stream.write(raw)
def run_node(payload):
    main=next(n for n in ast.parse(payload).body if isinstance(n,ast.FunctionDef)and n.name=="main")
    return next(n for n in main.body if isinstance(n,ast.FunctionDef)and n.name=="run")
same=ast.dump(run_node(old),include_attributes=False)==ast.dump(run_node(raw),include_attributes=False)
if not same:raise ValueError("Subprocess function unchanged")
record=dict(schema_version=1,status="NAMED_TERMINAL_PERSISTENCE_CORRECTION_NOT_EXECUTED",
    before=dict(path=str(prior),bytes=len(old),sha256=hashlib.sha256(old).hexdigest()),
    after=dict(path=str(output),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),
    findings=["Independent same-D1 batch: prepared-success emit failure could retain terminal BUILT and return0 despite caught failure.",
              "Root final control-flow review: inventory/read failures and final report-write failures also need explicit failed disposition, partial retention and no false zero exit."],
    correction="Main catch always setsBUILD_FAILED; inventory is protected with first failure preserved and partial-inventory flag; final report-write failure emits readable failure when possible and returns1. Subprocess function/three commands/source/header/oracles unchanged.",
    subprocess_function_AST_unchanged=same,
    qualification="Trusted-helper source correction only; no C build/native/image/original action.")
with(base/"NATIVE-CARRIER-BUILD-TERMINAL-CORRECTION-v5.json").open("x",encoding="utf-8")as stream:
    json.dump(record,stream,indent=2);stream.write("\n")
print(json.dumps(record["after"]))
