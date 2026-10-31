"""Pure raw-consistent terminated-count matrix; no SDK constructor/child."""
from importlib import util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
SOURCE=HERE/"qualify_detached_native_worker_v1.py"
spec=util.spec_from_file_location("detached_resource_matrix",SOURCE)
q=util.module_from_spec(spec);spec.loader.exec_module(q);sdk=q.load_sdk()
def guard(event,args):
    if event in ("ctypes.dlopen","subprocess.Popen","os.system","socket.__new__","socket.connect","socket.getaddrinfo"):
        raise RuntimeError("Pure matrix cannot perform real operations")
sys.addaudithook(guard)
rows=[]
for total in (1,2):
    for terminated in (0,1,7,0xffffffff):
        a,p=sdk.ACCOUNTING(),sdk.PID_LIST();a.TotalProcesses=total;a.TotalTerminatedProcesses=terminated
        raw=dict(accounting=dict(ok=True,error=0,returned_bytes=48,raw_hex=bytes(a).hex(),
            decoded={name:int(getattr(a,name)) for name,_ in a._fields_}),
            pid_list=dict(ok=True,error=0,returned_bytes=136,raw_hex=bytes(p).hex(),assigned_count=0,listed_count=0,pids=[]))
        error=q.resource_finished_problem(sdk,raw)
        assert (error is None)==(terminated==0)
        rows.append(dict(total=total,terminated=terminated,accepted=error is None))
report=dict(schema_version=1,status="passed",helper_sha256=q.pin(SOURCE)["sha256"],checker_sha256=q.pin(__file__)["sha256"],
    rows=rows,actual_children=0,real_sdk_constructions=0,scope="Raw and decoded fields agree; final resources predicate only")
with (HERE/"DETACHED-RESOURCE-MATRIX-v1.json").open("x",encoding="utf-8") as stream:json.dump(report,stream,indent=2);stream.write("\n")
print(json.dumps(dict(status="passed",conditions=len(rows),actual_children=0)))
