"""Root-authorized trusted-helper regression; no C import/build/process/native call.

Execute only the exact nested build-driver run function against fixed fake
process/time/emit objects. This does not execute main() or its Root binding.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import types

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
SOURCE=BASE/"build_native_carrier_component_v3.py"
RAW=SOURCE.read_bytes()
if hashlib.sha256(RAW).hexdigest()!="2d0b0ad29ab13ea9a82b01d28238a87c3e4c4eefbacf1a1eff5f0916cb92d3db":
    raise ValueError("Exact trusted driverV2")
OUT=ROOT/"data/cache/r09-native-carrier-driver-cleanup-fakes-v2"
OUT.mkdir(exist_ok=False)
tree=ast.parse(RAW)
main=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=="main")
run=next(n for n in main.body if isinstance(n,ast.FunctionDef)and n.name=="run")
factory=ast.parse("def factory():\n    primary_dispatch_error=None\n    return None\n").body[0]
factory.body[1:]=[run,ast.parse("return run, lambda: primary_dispatch_error").body[0]]
module=ast.fix_missing_locations(ast.Module(body=[factory],type_ignores=[]))
code=compile(module,str(SOURCE)+":EXACT_RUN_FUNCTION_ONLY","exec")


def require(value, message):
    if not value:raise AssertionError(message)


class FakeProcess:
    pid=111
    def __init__(self, outcomes, kill_error=None):
        self.outcomes=list(outcomes);self.kill_error=kill_error
        self.returncode=None;self.timeouts=[];self.kill_calls=0
    def communicate(self,timeout):
        self.timeouts.append(timeout)
        value=self.outcomes.pop(0)
        if isinstance(value,BaseException):raise value
        self.returncode=0;return value
    def poll(self):return self.returncode
    def kill(self):
        self.kill_calls+=1
        if self.kill_error:raise self.kill_error


primary_timeout=subprocess.TimeoutExpired(["fake-compiler"],58,output=b"abc",stderr=b"e")
secondary_timeout=subprocess.TimeoutExpired(["fake-compiler"],2,output=b"abcdef",stderr=b"ef")
primary_interrupt=KeyboardInterrupt("fixed interruption")
cases=[
    ("timeout_kill_and_reap_fail",FakeProcess([primary_timeout,secondary_timeout],OSError("fixed kill failure")),primary_timeout),
    ("interrupt_cleanup_exit0_not_healed",FakeProcess([primary_interrupt,(b"all",b"")]),primary_interrupt),
    ("ordinary_success",FakeProcess([(b"ok",b"")]),None),
    ("slow_spawn_preserves_original_deadline",FakeProcess([(b"late",b"")]),"DEADLINE_AFTER_SPAWN"),
]
records=[]
for name,process,expected_error in cases:
    case_out=OUT/name;case_out.mkdir()
    rows=[];events=[];spawns=[]
    clock=[0.0]
    def spawn(*args,**kwargs):
        spawns.append((args,kwargs))
        if name=="slow_spawn_preserves_original_deadline":clock[0]=58.5
        return process
    namespace=dict(start=0,time=types.SimpleNamespace(monotonic=lambda:clock[0]),
        subprocess=types.SimpleNamespace(Popen=spawn,DEVNULL="fake-devnull",PIPE="fake-pipe"),
        environment={},out=case_out,results=rows,
        emit=lambda kind,**fields:events.append(dict(kind=kind,**fields)))
    exec(code,namespace)
    run_function,primary=namespace["factory"]()
    caught=None;failure=None
    try:
        try:run_function(name,["fake-compiler"])
        except BaseException as error:caught=error
        if expected_error=="DEADLINE_AFTER_SPAWN":
            require(isinstance(caught,TimeoutError),"Same-clock timeout after slow spawn")
        else:
            require(caught is expected_error,"Exact original error identity")
        require(len(spawns)==1 and len(rows)==1,"One fake dispatch and retained result")
        row=rows[0]
        if expected_error is None:
            require(process.timeouts==[58] and process.kill_calls==0,"Ordinary one completion")
            require(primary() is None and row["output_complete"] and row["main_exit_observed"],"Ordinary facts")
        elif expected_error=="DEADLINE_AFTER_SPAWN":
            require(process.timeouts==[1.5] and process.kill_calls==1,"Only remaining1.5 cleanup seconds, no new58-second work wait")
            require(primary()["type"]=="TimeoutError"and row["returncode"]==0,"Cleanup exit0 cannot heal original work deadline")
        else:
            require(process.timeouts==[58,2.0] and process.kill_calls==1,"Bounded cleanup inside60")
            require(primary()["type"]==type(expected_error).__name__,"Primary descriptor not replaced")
        if name=="timeout_kill_and_reap_fail":
            require([e["stage"]for e in row["cleanup_errors"]]==["kill","bounded_reap"],"Both cleanup errors retained")
            require(not row["output_complete"]and not row["main_exit_observed"],"Unknown EOF/exit not success")
            require((case_out/(name+".first-error.stdout")).read_bytes()==b"abc","First output prefix")
            require((case_out/(name+".stdout")).read_bytes()==b"abcdef","Later partial output separate")
        if name=="interrupt_cleanup_exit0_not_healed":
            require(row["returncode"]==0 and caught is primary_interrupt,"Later exit0 does not heal original interruption")
            require(row["kill_acknowledged"]and row["output_complete"],"Known cleanup facts retained separately")
    except BaseException as error:
        failure=dict(type=type(error).__name__,message=str(error))
    records.append(dict(id=name,outcome="FAIL"if failure else"PASS",failure=failure,
        fake_spawn_count=len(spawns),communicate_timeouts=process.timeouts,
        kill_calls=process.kill_calls,primary_error=primary(),results=rows,events=events))
report=dict(schema_version=1,status="PASS"if all(r["outcome"]=="PASS"for r in records)else"FAIL",
    source=dict(path=str(SOURCE),bytes=len(RAW),sha256=hashlib.sha256(RAW).hexdigest()),
    authorization="Root finite trusted-helper fake regression only; original user-authorized correctness work. No C subject or driver main/build binding is executed.",
    cases=records,scope="Four fixed fake process controls, real ordinary harness evidence writes; no OS process/SDK/compiler/native behavior or physical profile is qualified.",
    actual_process_spawns=0,C_builds=0,C_subject_runs=0,original_target_reads=0)
path=BASE/"NATIVE-CARRIER-BUILD-DRIVER-FAKE-REGRESSIONS-v2.json"
with path.open("x",encoding="utf-8")as stream:json.dump(report,stream,indent=2);stream.write("\n")
print(json.dumps(dict(status=report["status"],cases=len(records),path=str(path))))
if report["status"]!="PASS":raise SystemExit(1)
