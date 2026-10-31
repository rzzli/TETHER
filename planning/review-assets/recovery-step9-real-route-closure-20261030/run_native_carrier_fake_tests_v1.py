"""One separately bound model-free fake-target run; no automatic build/retry.

Use the exact reviewed build-helper subprocess function with its60-second
budget/2-second cleanup reserve. This helper never invokes build main().
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
BINDING=BASE/"NATIVE-CARRIER-FAKE-RUN-BINDING-v1.json"


def sha(raw):return hashlib.sha256(raw).hexdigest()


def require(ok,message):
    if not ok:raise ValueError(message)


def read_pin(pin):
    path=Path(pin["path"])
    if not path.is_absolute():path=ROOT/path
    raw=path.read_bytes()
    require(len(raw)==pin["bytes"]and sha(raw)==pin["sha256"],"Exact runtime input: "+str(path))
    return path.resolve(),raw


def main():
    binding=json.loads(BINDING.read_text(encoding="utf-8"))
    require(binding["status"]=="ROOT_BOUND_ONE_FAKE_TARGET_RUN"and binding["budget_seconds"]==60,
            "No exact once-only runtime scope")
    checked={name:read_pin(pin)for name,pin in binding["inputs"].items()}
    require(checked["driver"][0]==Path(__file__).resolve(),"Actual executing runtime helper")
    output=(ROOT/binding["output_relative"]).resolve()
    require(output.parent==(ROOT/"data/cache").resolve()and output.name.startswith("r09-native-carrier-component-run-"),
            "Approved fresh runtime output")
    output.mkdir(exist_ok=False)
    started=time.monotonic();events=[];previous="0"*64;commands=[]
    def emit(kind,**fields):
        nonlocal previous
        value=dict(sequence=len(events),previous_sha256=previous,kind=kind,
                   elapsed_seconds=time.monotonic()-started,**fields)
        raw=json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        with(output/"run-journal.jsonl").open("ab")as stream:stream.write(raw+b"\n")
        previous=sha(raw);events.append(value)
    outcome="FAILED";failure=None;grade_error=None;actual_cases=[];summary=None
    try:
        emit("run_reserved",binding_sha256=sha(BINDING.read_bytes()),model_execution=False)
        # Extract unchanged trusted subprocess logic; no compiler or subject import.
        tree=ast.parse(checked["command_executor"][1])
        build_main=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=="main")
        run_node=next(n for n in build_main.body if isinstance(n,ast.FunctionDef)and n.name=="run")
        factory=ast.parse("def factory():\n    primary_dispatch_error=None\n    return None\n").body[0]
        factory.body[1:]=[run_node,ast.parse("return run, lambda: primary_dispatch_error").body[0]]
        module=ast.fix_missing_locations(ast.Module(body=[factory],type_ignores=[]))
        environment={key:os.environ[key]for key in("SystemRoot","WINDIR","TEMP","TMP")if key in os.environ}
        environment["PATH"]=str(Path(environment.get("SystemRoot",r"C:\Windows"))/"System32")
        namespace=dict(start=started,time=time,subprocess=subprocess,environment=environment,
                       out=output,results=commands,emit=emit)
        exec(compile(module,str(checked["command_executor"][0])+":EXACT_RUN_FUNCTION_ONLY","exec"),namespace)
        run,primary=namespace["factory"]()
        try:run("native-fake-tests",[str(checked["image"][0])])
        except BaseException as error:
            failure=dict(type=type(error).__name__,message=str(error),original_dispatch_error=primary())
        stdout_path=output/"native-fake-tests.stdout"
        if stdout_path.exists():
            try:
                records=[json.loads(line)for line in stdout_path.read_text(encoding="utf-8").splitlines()]
                actual_cases=[row for row in records if "case"in row]
                summaries=[row["summary"]for row in records if "summary"in row]
                require(len(records)==80 and len(actual_cases)==79 and len(summaries)==1,"79case rows plus1summary")
                summary=summaries[0]
                expected=json.loads(checked["expectations"][1])
                comparisons=[]
                for row in expected["semantic_vectors"]:
                    comparisons.append((row["id"],row["normal_copy256_hex"],row["error_boundary_copy256_hex"]))
                for row in expected["malformed_wrapper_vectors"]:
                    comparisons.append((row["id"],row["cell_copy256_hex"],None))
                for row in expected["initializer_negative_vectors"]:
                    comparisons.append((row["id"],row["expected_cell_copy256_hex"],None))
                partial=expected["interrupted_error_vector"]
                comparisons.append((partial["id"],partial["escaped_copy256_hex"],partial["escaped_copy256_hex"]))
                require(len(comparisons)==79,"Exact frozen oracle count")
                for actual,(case_id,cell,partial_cell)in zip(actual_cases,comparisons):
                    require(set(actual)=={"case","outcome","cell_copy256_hex","error_boundary_copy256_hex"},"Exact case shape")
                    require(actual["case"]==case_id and actual["outcome"]=="PASS","Frozen case identity/outcome: "+case_id)
                    require(actual["cell_copy256_hex"]==cell and actual["error_boundary_copy256_hex"]==partial_cell,
                            "Complete256B golden bytes: "+case_id)
                expected_summary=dict(cases=79,failures=0,initializer_attempts=79,wrapper_attempts=116,
                                      fake_targets=47,error_entries=17,error_returns=16,partial_copies=17)
                require(set(summary)==set(expected_summary)|{"checks"},"Exact summary shape")
                require(all(type(summary[k])is int and summary[k]==v for k,v in expected_summary.items()),"Exact frozen counters")
                require(type(summary["checks"])is int and summary["checks"]>0,"Measured assertion count")
            except BaseException as error:
                grade_error=dict(type=type(error).__name__,message=str(error))
        else:
            grade_error=dict(type="MISSING_STDOUT",message="No C result bytes retained")
        require(sha(checked["image"][0].read_bytes())==binding["inputs"]["image"]["sha256"],"Image bytes unchanged after run")
        require(time.monotonic()-started<60,"Final unchanged runtime deadline")
        if failure is None and grade_error is None:
            outcome="ALL_79_FAKE_TARGET_CONTROLS_PASSED"
        emit("run_terminal",status=outcome,failure=failure,grade_error=grade_error)
    except BaseException as error:
        failure=failure or dict(type=type(error).__name__,message=str(error))
        try:emit("run_failure",error=failure)
        except BaseException as journal_error:failure["journal_error"]=type(journal_error).__name__
    files=[]
    for path in sorted(output.iterdir()):
        if path.is_file():
            raw=path.read_bytes();files.append(dict(path=str(path.relative_to(ROOT)),bytes=len(raw),sha256=sha(raw)))
    report=dict(schema_version=1,status=outcome,binding_sha256=sha(BINDING.read_bytes()),
                elapsed_seconds=time.monotonic()-started,commands=commands,failure=failure,
                grade_error=grade_error,summary=summary,cases=actual_cases,artifacts=files,
                journal_events=len(events),journal_final_hash=previous,
                boundary="One own-source x64 fake-target image; no real fourteen-port target qualification, same-Core ticket/lease/path lifetime, physical14, new84, inference or scientific result",
                clock_scope="Input checks/reservation precede timer; final report write/startup excluded. No whole-process resource fit or durability claim.")
    report_path=output/"run-result.json"
    report_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(status=outcome,path=str(report_path),failure=failure,grade_error=grade_error)))
    return 0 if outcome=="ALL_79_FAKE_TARGET_CONTROLS_PASSED"else 1


if __name__=="__main__":sys.exit(main())
