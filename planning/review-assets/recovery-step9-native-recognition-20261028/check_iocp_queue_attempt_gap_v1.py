"""Own-source AST/fake counterexample only; no SDK, worker or runtime rerun."""
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import time

HERE=Path(__file__).resolve().parent
SOURCE=HERE/"diagnose_native_job_iocp_v1.py"
EXPECTED="3e31e7281aa41900b5331312f2133b7672c2eb3965eaa37f5e33428128ce6cc1"
require=lambda ok,message: None if ok else (_ for _ in ()).throw(RuntimeError(message))
require(hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED,"Consumed source changed")
denied=[]
def guard(event,args):
    if event in ("ctypes.dlopen","subprocess.Popen","os.system","socket.__new__","socket.connect","socket.getaddrinfo"):
        denied.append(event);raise RuntimeError("No real operations in source-only gap proof")
sys.addaudithook(guard)
tree=ast.parse(SOURCE.read_bytes())
node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="Observer")
class Stop(RuntimeError):pass
class Journal:
    def __init__(self):self.rows=[]
    def append(self,name,**details):self.rows.append((name,details))
class Api:
    def __init__(self):self.invocations=0
    def queue_call(self,port):
        self.invocations+=1
        if self.invocations==1:raise KeyboardInterrupt("Synthetic unknown-return boundary")
        return dict(started_monotonic_ns=1,finished_monotonic_ns=2,ok=False,error=258,
                    raw_number_of_bytes=0,raw_completion_key=0,raw_overlapped_value=0)
namespace=dict(sdk=SimpleNamespace(finite_deadline=lambda value:None),time=time,require=require,
    ObservationStop=Stop,COMPLETION_KEY=0x52303949,MESSAGES={},PID_MESSAGES=set())
exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE)+"::Observer_fake_only","exec"),namespace)
api,journal=Api(),Journal();observer=namespace["Observer"](api,journal,1);observer.port=40
observer.calls=[dict(synthetic_prior_returned_call=True)]*1023
first=None
try:observer.drain("synthetic_unknown_call")
except KeyboardInterrupt as error:first=type(error).__name__
require(first=="KeyboardInterrupt" and api.invocations==1 and len(observer.calls)==1023,
        "Expected uncounted fake call counterexample did not occur")
first_rows=len(journal.rows)
second=None
try:observer.drain("synthetic_cleanup_call")
except Stop as error:second=str(error)
require(api.invocations==2 and len(observer.calls)==1024 and second=="Queue call budget reached",
        "Expected recorded-vs-invoked boundary difference did not occur")
report=dict(schema_version=1,status="demonstrated_with_own_source_AST_and_fake_calls_only",
    source_sha256=EXPECTED,checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    synthetic_prior_recorded_calls=1023,fake_queue_invocations=api.invocations,
    first_exception=first,recorded_calls_after_first=1023,durable_call_rows_after_first=first_rows,
    recorded_calls_after_second=len(observer.calls),second_exception=second,
    potential_conservative_total_if_first_native_outcome_unknown=1025,
    actual_SDK_or_native_or_worker_calls=0,consumed_v1_reruns=0,denied_real_operations=denied,
    consumed_attempt_limitation="Root reports nine normal returns and no API exception/interruption; this latent path was not observed there.",
    disposition="Future reuse requires a new reviewed version with pre-dispatch attempt reservation and retained unknown outcomes. No new runtime protocol or rerun is authorized.")
with (HERE/"IOCP-QUEUE-ATTEMPT-GAP-v1.json").open("x",encoding="utf-8") as stream:
    json.dump(report,stream,indent=2);stream.write("\n")
print(json.dumps(dict(status=report["status"],fake_invocations=2,actual_native_calls=0)))
