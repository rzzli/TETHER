"""Root trusted-helper emitter regressions; no build/native/original I/O."""
import ast
import hashlib
import json
from pathlib import Path
import types

BASE=Path(__file__).resolve().parent
SOURCE=BASE/"build_native_carrier_component_v6.py";raw=SOURCE.read_bytes()
if hashlib.sha256(raw).hexdigest()!="e182ff2503103a7b77ca888f0f2c572600859def6d501476e661784f55a8c16b":raise ValueError("ExactV6")
main=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)and n.name=="main")
emit=next(n for n in main.body if isinstance(n,ast.FunctionDef)and n.name=="emit")
factory=ast.parse('''def factory():
    previous="0"*64
    journal_complete=True
    journal_acknowledged_events=0
    events=[]
    return None
''').body[0]
factory.body[-1:]=[emit,ast.parse("return emit, lambda: dict(previous=previous,complete=journal_complete,acked=journal_acknowledged_events,events=events)").body[0]]
code=compile(ast.fix_missing_locations(ast.Module(body=[factory],type_ignores=[])),str(SOURCE)+":EXACT_EMIT_ONLY","exec")


class FakeStream:
    def __init__(self,mode):self.mode=mode;self.data=bytearray();self.opens=0;self.closes=0
    def __truediv__(self,other):return self
    def open(self,mode):
        if mode!="ab":raise AssertionError("Append only")
        self.opens+=1;return self
    def __enter__(self):return self
    def write(self,value):
        if self.mode=="partial_write":self.data.extend(value[:7]);return 7
        self.data.extend(value);return len(value)
    def __exit__(self,*args):
        self.closes+=1
        if self.mode=="close_failure":raise OSError("fixed close failure")


records=[]
for mode in("normal","partial_write","close_failure"):
    stream=FakeStream(mode)
    namespace=dict(start=0,time=types.SimpleNamespace(monotonic=lambda:0),
                   out=stream,json=json,digest=lambda value:hashlib.sha256(value).hexdigest())
    exec(code,namespace);function,state=namespace["factory"]();caught=None;failure=None
    try:
        try:function("first",number=1)
        except BaseException as error:caught=error
        first_state=state()
        if mode=="normal":
            if caught:raise AssertionError("Normal emitter failed")
            function("second",number=2);now=state();lines=bytes(stream.data).splitlines()
            if now["acked"]!=2 or len(now["events"])!=2 or not now["complete"]:raise AssertionError("Acknowledged ordinary rows")
            if json.loads(lines[1])["previous_sha256"]!=hashlib.sha256(lines[0]).hexdigest():raise AssertionError("Actual byte chain")
            if now["previous"]!=hashlib.sha256(lines[1]).hexdigest():raise AssertionError("Acknowledged final tip")
        else:
            if not isinstance(caught,OSError):raise AssertionError("Original append/close failure retained")
            if first_state["complete"]or first_state["acked"]!=0 or first_state["previous"]!="0"*64:raise AssertionError("Unacknowledged row cannot advance tip/count")
            blocked=None
            try:function("would_repair_tail")
            except BaseException as error:blocked=error
            if not isinstance(blocked,RuntimeError)or stream.opens!=1:raise AssertionError("No append/repaired chain after unknown tail")
    except BaseException as error:failure=dict(type=type(error).__name__,message=str(error))
    records.append(dict(id=mode,outcome="FAIL"if failure else"PASS",failure=failure,
                        state=state(),open_attempts=stream.opens,close_attempts=stream.closes,
                        raw_fake_bytes_hex=bytes(stream.data).hex()))
report=dict(schema_version=1,status="PASS"if all(r["outcome"]=="PASS"for r in records)else"FAIL",
    source=dict(path=str(SOURCE),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),
    cases=records,scope="Root-author fixed fake emitter controls, exact source fragment only; fake bytes are not filesystem flush/durability. No C subject/driver main/compiler/native/original call.",
    actual_process_spawns=0,C_builds=0,native_runs=0)
path=BASE/"NATIVE-CARRIER-BUILD-JOURNAL-FAKE-REGRESSIONS-v1.json"
with path.open("x",encoding="utf-8")as stream:json.dump(report,stream,indent=2);stream.write("\n")
print(json.dumps(dict(status=report["status"],cases=len(records),path=str(path))))
if report["status"]!="PASS":raise SystemExit(1)
