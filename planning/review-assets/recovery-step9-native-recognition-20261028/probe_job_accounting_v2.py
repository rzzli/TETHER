"""Version-two OS-only accounting diagnostic; --prepare dispatches nothing.

No target libraries, models, network, global process enumeration or private
process APIs. Only PIDs returned by this newly owned job receive read-only
image/creation queries. Worker PPID comes from its own strict identity marker.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from threading import Event, Thread

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROTOCOL = HERE / "JOB-ACCOUNTING-DIAGNOSTIC-PROTOCOL-v2.json"
FAULTS = HERE / "JOB-ACCOUNTING-V2-FAULT-CHECKS.json"
V1_HOLD = HERE / "JOB-ACCOUNTING-DIAGNOSTIC-PEER-REVIEW-v1.json"
BASE = Path(r"C:\Users\zzric\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe")
BASE_SHA = "d2ec5b9401b6471874373fe3e4329da1da85014d98f8abedd4e0f02ffdaa21a1"
PRIOR = ROOT / "data/cache/r09-windows-job-probe-20261028T171342Z"
PRIOR_REPORT_SHA = "2b35761da99681ffb84995590c8199f58d45289167665905557df01ba1ce0f38"
SDK = Path(r"C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\um")
LIMITS = dict(children=1, whole_child_seconds=8, aggregate_seconds=45,
              finalization_reserve_seconds=5, steady_seconds=1, maximum_job_pids=16,
              maximum_total_unique_pids=16, image_characters=32768,
              stdout_bytes=65536, stderr_bytes=65536,
              process_commit_bytes=67108864, active_process_limit=1)
STAGES = ("configured_empty", "assigned_before_authorization", "child_ready",
          "steady_one_second", "after_wait_and_process_handle_close")


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def check(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError("Declared diagnostic deadline exceeded")


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def safe(path):
    path = Path(path).absolute()
    cache = ROOT / "data/cache"
    need(path.is_relative_to(cache) and path.resolve().is_relative_to(cache.resolve()),
         "Diagnostic output outside project cache")
    for part in (path, *path.parents):
        try:
            status = part.lstat()
        except FileNotFoundError:
            continue
        need(not part.is_symlink() and not getattr(status, "st_file_attributes", 0) & 0x400,
             "Diagnostic output reparse ancestry")
    return path


def write_new(path, value):
    with safe(path).open("xb") as stream:
        stream.write(canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def publish_marker(path, value):
    path = safe(path)
    need(path.name in ("started.json", "ready.json"), "Only fixed worker markers")
    pending = path.with_name(path.name + ".pending")
    write_new(pending, value)
    need(not path.exists(), "Worker marker already published")
    os.rename(pending, path)  # Windows refuses an existing destination.


def drain_capture(pipe, sink, record, stop, cap=65536):
    try:
        while True:
            block = pipe.read1(65536)
            if not block:
                break
            record["observed_bytes_at_least"] += len(block)
            remaining = cap - record["retained_bytes"]
            if remaining:
                sink.write(block[:remaining])
                record["retained_bytes"] += min(remaining, len(block))
            if len(block) > remaining:
                record["truncated"] = True
                stop.set()
                break
    except BaseException as error:
        record.update(error_class=type(error).__name__, error=str(error)[:512])
        stop.set()
    finally:
        try:
            sink.flush()
            os.fsync(sink.fileno())
        except BaseException as error:
            record.update(error_class=type(error).__name__, error=str(error)[:512])
            stop.set()


def pin(path):
    path = Path(path).absolute()
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)


def environment():
    system = Path(os.environ["SystemRoot"])
    return dict(SystemRoot=str(system), WINDIR=str(system), SystemDrive=system.drive,
                PATH=str(system / "System32"))


def guard(state, *, preparing=False, worker=False):
    kernel = os.path.normcase(str(Path(os.environ["SystemRoot"]) / "System32/kernel32.dll"))
    def audit(event, args):
        if event in ("socket.__new__", "socket.getaddrinfo", "socket.connect", "os.system"):
            state["denied"].append(event)
            raise RuntimeError("No network/system shell in diagnostic")
        if event == "ctypes.dlopen":
            allowed = (not preparing and not worker and
                       (args[0] is None or os.path.normcase(str(args[0])) == kernel))
            need(allowed, "Only current-process and exact system kernel32 loads")
        if event == "subprocess.Popen":
            argv = state.get("active_argv")
            allowed = (not preparing and not worker and state["dispatches"] == 0
                       and argv is not None and args[0] in (None, str(BASE))
                       and args[1] == subprocess.list2cmdline(argv)
                       and args[2] is not None and Path(args[2]).resolve() == ROOT
                       and args[3] == environment())
            need(allowed, "Only one exact owned diagnostic worker")
            state["dispatches"] += 1
        if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0])).absolute()
            need(path.drive.casefold() != "e:" and path.suffix.casefold() != ".gguf"
                 and "\\data\\benchmark\\" not in str(path).casefold(),
                 "No protected model/evaluation payload")
    sys.addaudithook(audit)


def prepare():
    state = dict(denied=[], dispatches=0, active_argv=None)
    guard(state, preparing=True)
    need(sys.flags.isolated and sys.dont_write_bytecode and os.name == "nt", "Use Windows -I -B")
    need(sha(BASE) == BASE_SHA and sha(PRIOR / "report.json") == PRIOR_REPORT_SHA,
         "Pinned base or original report changed")
    need(not PROTOCOL.exists(), "Protocol already exists; do not overwrite")
    files = [Path(__file__).resolve(), BASE, SDK / "winnt.h", SDK / "processthreadsapi.h",
             SDK / "winbase.h", BASE.parent / "Lib/ctypes/wintypes.py",
             HERE / "probe_windows_job.py", HERE / "OS-PROBE-ROOT-DECISION.json",
             HERE / "OS-PROBE-CORRECTION-REVIEW.md",
             HERE / "OS-PROBE-RESULT-VERIFICATION.json", HERE / "OS-PROBE-RESULT-VERIFICATION.md"]
    fault = json.loads(FAULTS.read_bytes())
    need(fault["status"] == "passed_atomic_markers_and_capped_capture_pure_fixtures"
         and fault["helper_sha256"] == sha(__file__)
         and fault["actual_children"] == fault["network_requests"] == fault["windows_api_calls"] == 0,
         "Fresh pure regression evidence required")
    hold = json.loads(V1_HOLD.read_bytes())
    need(hold["helper_sha256"] == "ca36c94c8cffb3d0ec0b93990bb934b17994fa75101cd5f1b80696f8870608d1",
         "Preserved v1 hold differs")
    files += [HERE / "probe_job_accounting.py", HERE / "JOB-ACCOUNTING-DIAGNOSTIC-PROTOCOL.json",
              HERE / "JOB-ACCOUNTING-DIAGNOSTIC-PREPARATION.md", V1_HOLD,
              HERE / "JOB-ACCOUNTING-DIAGNOSTIC-PEER-REVIEW-v1.md",
              HERE / "check_job_accounting_v2.py", FAULTS]
    files += sorted(path for path in PRIOR.rglob("*") if path.is_file())
    need(len([p for p in PRIOR.rglob("*") if p.is_file()]) == 16, "Original artifact universe changed")
    pins = [pin(path) for path in files]
    for item in pins:
        path = Path(item["path"])
        need(path.resolve(strict=True) == path, "Input is not canonical")
        for part in (path, *path.parents):
            status = part.lstat()
            need(not part.is_symlink() and not getattr(status, "st_file_attributes", 0) & 0x400,
                 "Input reparse ancestry")
    winnt = (SDK / "winnt.h").read_text(encoding="utf-8").split("\n")
    need(winnt[13791].startswith("typedef struct _IO_COUNTERS")
         and winnt[14133].startswith("typedef struct _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION")
         and winnt[14604].startswith("typedef enum _JOBOBJECTINFOCLASS"),
         "SDK physical-line landmarks differ")
    excerpts = [dict(path=str(SDK / "winnt.h"), start_line=a, end_line=b,
                     text="\n".join(winnt[a-1:b]))
                for a, b in ((13792,13800),(14134,14179),(14605,14615))]
    output = safe(ROOT / "data/cache" / ("r09-job-accounting-diagnostic-v2-" +
                 datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")))
    need(not output.exists(), "New diagnostic output already exists")
    value = dict(schema_version=1, kind="one_worker_job_accounting_diagnostic_v2",
                 helper=pin(__file__), base=pin(BASE), output=str(output), limits=LIMITS,
                 stages=list(STAGES), pinned_files=pins, sdk_excerpts=excerpts,
                 superseded_unexecuted=dict(helper=pin(HERE / "probe_job_accounting.py"),
                     protocol=pin(HERE / "JOB-ACCOUNTING-DIAGNOSTIC-PROTOCOL.json"), hold=pin(V1_HOLD)),
                 pure_regressions=pin(FAULTS),
                 marker_publication="Fsynced pending file then Windows non-overwriting same-directory rename",
                 capture_policy="Two read1 pipe drainers retain64KiB each; overflow/error signals parent checkpoints and owned cleanup; observed/retained/truncated/error fields sealed",
                 sdk_excerpt_correction="Physical LF lines after universal-newline normalization, not splitlines formfeed boundaries",
                 prior_artifact_names=sorted(path.relative_to(PRIOR).as_posix() for path in PRIOR.rglob("*") if path.is_file()),
                 expected_sizes=dict(BasicLimit=64, ExtendedLimit=144, Accounting=48, PidList=136),
                 expected_accounting_offsets=dict(TotalPageFaultCount=32, TotalProcesses=36,
                     ActiveProcesses=40, TotalTerminatedProcesses=44),
                 metadata_rights=4096, metadata_scope="Only PIDs returned by this owned job; image and creation via read-only OpenProcess. Own PPID from strict marker; other PPIDs null.",
                 global_process_enumeration=False, private_process_apis=False,
                 network=False, native_target=False, model_or_gguf=False,
                 automatic_retry=False, execution_authorized=False,
                 preparation_activity=dict(child_dispatches=0, windows_api_calls=0))
    with PROTOCOL.open("xb") as stream:
        stream.write(canonical(value) + b"\n"); stream.flush(); os.fsync(stream.fileno())
    need(state["dispatches"] == 0 and not state["denied"], "Preparation performed an action")
    print(json.dumps(dict(status="prepared_no_dispatch_or_windows_api", helper_sha256=sha(__file__),
                         protocol_sha256=sha(PROTOCOL), pins=len(pins), output=str(output))))


def authority(expected):
    need(len(expected) == 64 and sha(PROTOCOL) == expected, "Exact protocol hash required")
    value = json.loads(PROTOCOL.read_bytes())
    need(value["kind"] == "one_worker_job_accounting_diagnostic_v2"
         and value["helper"]["sha256"] == sha(__file__) and value["base"]["sha256"] == BASE_SHA
         and value["base"]["path"] == str(BASE) and value["limits"] == LIMITS
         and value["stages"] == list(STAGES), "Diagnostic authority mismatch")
    return value, safe(value["output"])


def worker(expected):
    state = dict(denied=[], dispatches=0, active_argv=None)
    guard(state, worker=True)
    p, output = authority(expected); leaf = safe(output / "worker")
    need(sys.flags.isolated and sys.dont_write_bytecode and
         Path(sys.executable).resolve() == BASE and Path(sys._base_executable).resolve() == BASE,
         "Direct worker interpreter differs")
    identity = dict(pid=os.getpid(), parent_pid=os.getppid(), protocol_sha256=expected,
                    executable=str(Path(sys.executable).resolve()), base_executable=str(Path(sys._base_executable).resolve()),
                    prefix=str(Path(sys.prefix).resolve()), isolated=True, dont_write_bytecode=True)
    publish_marker(leaf / "started.json", identity)
    deadline = time.monotonic() + 3
    while not (leaf / "assigned.json").exists():
        check(deadline); time.sleep(.01)
    owner = json.loads((leaf / "assigned.json").read_bytes())
    need(owner["pid"] == os.getpid() and owner["parent_pid"] == os.getppid()
         and owner["protocol_sha256"] == expected, "Worker assignment identity mismatch")
    check(owner["deadline_monotonic"])
    publish_marker(leaf / "ready.json", identity)
    time.sleep(30)
    raise RuntimeError("Owned job was not terminated within diagnostic budget")


def api():
    import ctypes as c
    from ctypes.wintypes import BOOL, DWORD, HANDLE, LARGE_INTEGER, LPVOID, LPWSTR, FILETIME
    class BasicLimit(c.Structure):
        _fields_ = [("PerProcessUserTimeLimit",LARGE_INTEGER),("PerJobUserTimeLimit",LARGE_INTEGER),
            ("LimitFlags",DWORD),("MinimumWorkingSetSize",c.c_size_t),("MaximumWorkingSetSize",c.c_size_t),
            ("ActiveProcessLimit",DWORD),("Affinity",c.c_size_t),("PriorityClass",DWORD),("SchedulingClass",DWORD)]
    class IoCounters(c.Structure):
        _fields_ = [(name,c.c_ulonglong) for name in ("ReadOperationCount","WriteOperationCount",
            "OtherOperationCount","ReadTransferCount","WriteTransferCount","OtherTransferCount")]
    class ExtendedLimit(c.Structure):
        _fields_ = [("BasicLimitInformation",BasicLimit),("IoInfo",IoCounters),
            ("ProcessMemoryLimit",c.c_size_t),("JobMemoryLimit",c.c_size_t),
            ("PeakProcessMemoryUsed",c.c_size_t),("PeakJobMemoryUsed",c.c_size_t)]
    class Accounting(c.Structure):
        _fields_ = [(name,LARGE_INTEGER) for name in ("TotalUserTime","TotalKernelTime",
            "ThisPeriodTotalUserTime","ThisPeriodTotalKernelTime")]
        _fields_ += [(name,DWORD) for name in ("TotalPageFaultCount","TotalProcesses",
            "ActiveProcesses","TotalTerminatedProcesses")]
    class PidList(c.Structure):
        _fields_ = [("NumberOfAssignedProcesses",DWORD),("NumberOfProcessIdsInList",DWORD),
                    ("ProcessIdList",c.c_size_t * 16)]
    structures = dict(BasicLimit=BasicLimit, ExtendedLimit=ExtendedLimit, Accounting=Accounting, PidList=PidList)
    need(c.sizeof(c.c_size_t) == 8 and {n:c.sizeof(t) for n,t in structures.items()} ==
         dict(BasicLimit=64,ExtendedLimit=144,Accounting=48,PidList=136), "Unexpected x64 layouts")
    need({n:getattr(Accounting,n).offset for n in ("TotalPageFaultCount","TotalProcesses",
         "ActiveProcesses","TotalTerminatedProcesses")} == dict(TotalPageFaultCount=32,
         TotalProcesses=36,ActiveProcesses=40,TotalTerminatedProcesses=44)
         and PidList.ProcessIdList.offset == 8, "Unexpected accounting/PID offsets")
    k = c.WinDLL(str(Path(os.environ["SystemRoot"]) / "System32/kernel32.dll"),use_last_error=True)
    specs = {"CreateJobObjectW":([LPVOID,LPVOID],HANDLE),
        "SetInformationJobObject":([HANDLE,DWORD,LPVOID,DWORD],BOOL),
        "QueryInformationJobObject":([HANDLE,DWORD,LPVOID,DWORD,c.POINTER(DWORD)],BOOL),
        "AssignProcessToJobObject":([HANDLE,HANDLE],BOOL),"TerminateJobObject":([HANDLE,DWORD],BOOL),
        "CloseHandle":([HANDLE],BOOL),"OpenProcess":([DWORD,BOOL,DWORD],HANDLE),
        "GetProcessId":([HANDLE],DWORD),"QueryFullProcessImageNameW":([HANDLE,DWORD,LPWSTR,c.POINTER(DWORD)],BOOL),
        "GetProcessTimes":([HANDLE,c.POINTER(FILETIME),c.POINTER(FILETIME),c.POINTER(FILETIME),c.POINTER(FILETIME)],BOOL)}
    for n,(args,result) in specs.items():getattr(k,n).argtypes,getattr(k,n).restype=args,result
    return c,k,structures,FILETIME


def execute(expected):
    need(os.name == "nt" and sys.flags.isolated and sys.dont_write_bytecode, "Use Windows -I -B")
    p, output = authority(expected); need(not output.exists(), "Attempt consumed; never restart")
    output.mkdir(); leaf=safe(output/"worker");leaf.mkdir()
    state=dict(denied=[],dispatches=0,active_argv=None);guard(state)
    capture_stop=Event();capture_threads=[];capture_files=ExitStack()
    capture_records={name:dict(observed_bytes_at_least=0,retained_bytes=0,truncated=False,error_class=None)
                     for name in ("stdout","stderr")}
    child_started=None
    started=time.monotonic(); end=started+45; child_end=None; k=None;job=None;process=None
    report=dict(schema_version=1,status="failed",protocol_sha256=expected,output=str(output),
                snapshots=[],cleanup_errors=[],network_requests=0,target_native_calls=0,gguf_reads=0,captures=capture_records)
    journal=(output/"journal.jsonl").open("xb"); tip=None; sequence=0
    def event(name,**details):
        nonlocal tip,sequence
        e=dict(sequence=sequence,event=name,details=details,previous_sha256=tip)
        tip=hashlib.sha256(canonical(e)).hexdigest();e["sha256"]=tip
        journal.write(canonical(e)+b"\n");journal.flush();os.fsync(journal.fileno());sequence+=1
    def ensure(deadline):
        check(deadline)
        need(not capture_stop.is_set(), "Capture overflow or drain failure; stop owned worker")
    def win(ok,what):
        need(ok,what+"; winerror="+str(c.get_last_error()))
    def metadata(pid,deadline):
        ensure(deadline); result=dict(pid=pid,parent_pid=None,parent_pid_reason="No documented narrow PPID API used")
        if not 0<pid<=0xFFFFFFFF:return dict(result,error="PID outside public DWORD namespace")
        handle=k.OpenProcess(0x1000,False,pid)
        if not handle:return dict(result,open_process_error=c.get_last_error())
        try:
            result["opened_pid"]=k.GetProcessId(handle);ensure(deadline)
            image=c.create_unicode_buffer(32768);length=c.wintypes.DWORD(len(image))
            if k.QueryFullProcessImageNameW(handle,0,image,c.byref(length)):
                result.update(image=image.value,image_characters=length.value)
            else:result["image_error"]=c.get_last_error()
            ensure(deadline);creation,exit_time,kernel,user=(FileTime() for _ in range(4))
            if k.GetProcessTimes(handle,c.byref(creation),c.byref(exit_time),c.byref(kernel),c.byref(user)):
                result["creation_time_100ns_since_1601"]=(creation.dwHighDateTime<<32)|creation.dwLowDateTime
            else:result["creation_time_error"]=c.get_last_error()
            if process is not None and pid==process.pid and (leaf/"started.json").exists():
                own=json.loads((leaf/"started.json").read_bytes());result.update(parent_pid=own["parent_pid"],parent_pid_reason="Strict owned-worker marker")
        finally:
            result["metadata_handle_closed"]=bool(k.CloseHandle(handle))
            need(result["metadata_handle_closed"], "Read-only metadata handle close failed")
        ensure(deadline);return result
    seen=set()
    def snapshot(name,deadline):
        ensure(deadline);begin=time.monotonic();a=types["Accounting"]();ids=types["PidList"]();returned=c.wintypes.DWORD()
        win(k.QueryInformationJobObject(job,1,c.byref(a),c.sizeof(a),c.byref(returned)),"Query accounting")
        accounting_length=returned.value;need(accounting_length==48,"Accounting returned length differs from SDK48");ensure(deadline)
        win(k.QueryInformationJobObject(job,3,c.byref(ids),c.sizeof(ids),c.byref(returned)),"Query bounded PID list")
        ensure(deadline);need(ids.NumberOfAssignedProcesses<=16 and ids.NumberOfProcessIdsInList<=16,"Owned job exceeds fixed16-PID diagnostic bound")
        need(8+8*ids.NumberOfProcessIdsInList<=returned.value<=136,"PID-list returned length does not cover its bounded entries")
        pid_values=list(ids.ProcessIdList[:ids.NumberOfProcessIdsInList]);seen.update(pid_values)
        need(len(seen)<=16,"More than16 distinct job PIDs; stop without expansion")
        value=dict(stage=name,monotonic_begin=begin,accounting_returned_bytes=accounting_length,
            accounting={n:getattr(a,n) for n,_ in a._fields_},accounting_raw_hex=c.string_at(c.byref(a),c.sizeof(a)).hex(),
            pid_list_returned_bytes=returned.value,number_assigned=ids.NumberOfAssignedProcesses,
            number_listed=ids.NumberOfProcessIdsInList,pids=pid_values,
            pid_list_raw_hex=c.string_at(c.byref(ids),c.sizeof(ids)).hex(),
            process_metadata=[metadata(pid,deadline) for pid in dict.fromkeys(pid_values)])
        ensure(deadline);value["monotonic_end"]=time.monotonic()
        write_new(output/(name+".json"),value);report["snapshots"].append(value);event("snapshot",stage=name,sha256=sha(output/(name+".json")))
    try:
        event("diagnostic_reserved",owner_pid=os.getpid(),protocol_sha256=expected)
        write_new(output/"effective-protocol.json",p)
        need(sorted(path.relative_to(PRIOR).as_posix() for path in PRIOR.rglob("*") if path.is_file())==p["prior_artifact_names"], "Original artifact universe changed")
        for item in p["pinned_files"]:
            ensure(end-5);need(pin(item["path"])==item,"Input pin changed")
        c,k,types,FileTime=api();report["layouts"]={n:dict(size=c.sizeof(t),offsets={f:getattr(t,f).offset for f,_ in t._fields_}) for n,t in types.items()}
        job=k.CreateJobObjectW(None,None);win(job,"Create newly owned unnamed job")
        limits=types["ExtendedLimit"]();limits.BasicLimitInformation.LimitFlags=0x2108
        limits.BasicLimitInformation.ActiveProcessLimit=1;limits.ProcessMemoryLimit=67108864
        win(k.SetInformationJobObject(job,9,c.byref(limits),c.sizeof(limits)),"Set finite owned job")
        configured=types["ExtendedLimit"]();win(k.QueryInformationJobObject(job,9,c.byref(configured),c.sizeof(configured),None),"Verify configured limits")
        need(configured.BasicLimitInformation.LimitFlags==0x2108 and configured.BasicLimitInformation.ActiveProcessLimit==1 and configured.ProcessMemoryLimit==67108864,"Queried configuration differs")
        report["configured"]=dict(flags=0x2108,active_limit=1,process_commit_bytes=67108864)
        snapshot(STAGES[0],end-5)
        child_started=time.monotonic();child_end=min(child_started+8,end-5)
        argv=[str(BASE),"-I","-B",str(Path(__file__).resolve()),"--worker",expected]
        sinks={name:capture_files.enter_context((leaf/(name+".bin")).open("xb"))
               for name in ("stdout","stderr")}
        state["active_argv"]=argv
        process=subprocess.Popen(argv,cwd=ROOT,env=environment(),shell=False,stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True,creationflags=subprocess.CREATE_NO_WINDOW)
        state["active_argv"]=None;process.stdin.close();report["worker_pid"]=process.pid
        for name,pipe in (("stdout",process.stdout),("stderr",process.stderr)):
            thread=Thread(target=drain_capture,args=(pipe,sinks[name],capture_records[name],capture_stop),daemon=True)
            thread.start();capture_threads.append(thread)
        event("worker_spawned",pid=process.pid,argv=argv,deadline_monotonic=child_end)
        ready_end=min(child_end,time.monotonic()+2)
        while not (leaf/"started.json").exists():ensure(ready_end);need(process.poll() is None,"Worker exited before identity");time.sleep(.01)
        identity=json.loads((leaf/"started.json").read_bytes())
        need(identity==dict(pid=process.pid,parent_pid=os.getpid(),protocol_sha256=expected,
            executable=str(BASE),base_executable=str(BASE),prefix=str(BASE.parent),isolated=True,dont_write_bytecode=True),"Worker identity differs")
        report["worker_identity"]=identity
        win(k.AssignProcessToJobObject(job,c.wintypes.HANDLE(int(process._handle))),"Assign owned direct worker")
        snapshot(STAGES[1],child_end)
        pending=leaf/"assigned.pending.json";write_new(pending,dict(pid=process.pid,parent_pid=os.getpid(),protocol_sha256=expected,deadline_monotonic=child_end))
        os.rename(pending,leaf/"assigned.json")
        while not (leaf/"ready.json").exists():ensure(child_end);need(process.poll() is None,"Worker exited before ready");time.sleep(.01)
        need(json.loads((leaf/"ready.json").read_bytes())==identity,"Ready identity differs")
        snapshot(STAGES[2],child_end)
        steady_end=time.monotonic()+1;ensure(child_end)
        while time.monotonic()<steady_end:ensure(child_end);need(process.poll() is None,"Worker exited during steady observation");time.sleep(.01)
        snapshot(STAGES[3],child_end)
        win(k.TerminateJobObject(job,87),"Terminate only this owned job")
        process.wait(timeout=max(.05,min(2,child_end-time.monotonic())))
        report.update(worker_reaped=True,worker_exit_code=process.returncode)
        need(process.returncode==87,"Unexpected explicit termination result")
        process._handle.Close();report["worker_process_handle_closed"]=True
        snapshot(STAGES[4],child_end)
        ensure(child_end)
        need(state["dispatches"]==1 and not state["denied"],"Unexpected dispatch/guard activity")
        report["status"]="diagnostic_completed_raw_observations_only"
    except BaseException as error:
        report.update(status="failed",failure=dict(error_class=type(error).__name__,error=str(error)[:2048]))
    finally:
        state["active_argv"]=None
        try:
            if process is not None and process.poll() is None:
                if job is not None:report["cleanup_job_termination_requested"]=bool(k.TerminateJobObject(job,88))
                try:process.wait(timeout=.25)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=2)
                report["cleanup_worker_reaped"]=True
        except BaseException as error:report["cleanup_errors"].append(dict(stage="worker",error_class=type(error).__name__,error=str(error)[:512]))
        finally:
            try:
                if job is not None:win(k.CloseHandle(job),"Close owned job");report["owned_job_handle_closed"]=True
            except BaseException as error:report["cleanup_errors"].append(dict(stage="job_close",error_class=type(error).__name__,error=str(error)[:512]))
            finally:
                if process is not None and process.poll() is not None and not report.get("worker_process_handle_closed"):
                    try:process._handle.Close();report["worker_process_handle_closed"]=True
                    except BaseException as error:report["cleanup_errors"].append(dict(stage="process_handle",error_class=type(error).__name__))
        try:
            try:
                for thread in capture_threads:
                    thread.join(timeout=max(.05,min(1,(child_end or end)-time.monotonic())))
                if any(thread.is_alive() for thread in capture_threads):
                    report["cleanup_errors"].append(dict(stage="capture_threads",error_class="UnresolvedCaptureThread"))
                elif process is not None:
                    for pipe in (process.stdout,process.stderr):
                        if pipe is not None:pipe.close()
            finally:
                capture_files.close()
            for name,record in capture_records.items():
                path=leaf/(name+".bin")
                if path.exists():
                    record["actual_retained_bytes"]=path.stat().st_size
                    record["sha256"]=sha(path)
                    need(path.stat().st_size==record["retained_bytes"]<=65536,"Capture retained-byte accounting differs")
            need(not capture_stop.is_set() and all(not r["truncated"] and r["error_class"] is None
                 for r in capture_records.values()),"Capture overflow/error vetoes diagnostic")
            need(all(r["retained_bytes"]==0 for r in capture_records.values()),"Unexpected worker diagnostics")
            if child_started is not None:
                report["whole_child_seconds"]=time.monotonic()-child_started
                need(report["whole_child_seconds"]<=8,"Whole child including capture cleanup exceeded8s")
            check(end)
            for item in p["pinned_files"]:check(end);need(pin(item["path"])==item,"Final input pin changed")
            need(sha(PROTOCOL)==expected, "Final protocol changed")
            need(sorted(path.relative_to(PRIOR).as_posix() for path in PRIOR.rglob("*") if path.is_file())==p["prior_artifact_names"], "Final original artifact universe changed")
            if report["cleanup_errors"]:raise RuntimeError("Cleanup failed")
        except BaseException as error:report.update(status="failed",failure=dict(stage="cleanup_or_final_pins",error_class=type(error).__name__,error=str(error)[:2048]))
        report["guards"]={k:v for k,v in state.items() if k!="active_argv"};report["elapsed_seconds_before_seal"]=time.monotonic()-started
        try:
            event("diagnostic_terminal",status=report["status"]);journal.close()
            write_new(output/"report.json",report);check(end)
            inventory={}
            for f in sorted(output.rglob("*")):
                check(end)
                if f.is_file():inventory[f.relative_to(output).as_posix()]={k:pin(f)[k] for k in ("sha256","bytes")}
            write_new(output/"receipt.json",dict(protocol_sha256=expected,status=report["status"],outputs=inventory,journal_tip_sha256=tip,
                authority_rule="failure.json vetoes a completed diagnostic record"));check(end)
        except BaseException as error:report.update(status="failed",failure=dict(stage="seal",error_class=type(error).__name__,error=str(error)[:2048]))
        finally:
            if not journal.closed:
                try:journal.close()
                except BaseException as error:report.update(status="failed",failure=dict(stage="journal_close",error_class=type(error).__name__,error=str(error)[:512]))
        if report["status"]=="failed":write_new(output/"failure.json",dict(authoritative=True,failure=report.get("failure"),cleanup_errors=report["cleanup_errors"]))
    print(json.dumps(dict(status=report["status"],output=str(output),elapsed_seconds=time.monotonic()-started)))
    return 0 if report["status"]=="diagnostic_completed_raw_observations_only" and not (output/"failure.json").exists() else 1


if __name__ == "__main__":
    if sys.argv[1:]==["--prepare"]:prepare()
    elif len(sys.argv)==3 and sys.argv[1]=="--execute":raise SystemExit(execute(sys.argv[2]))
    elif len(sys.argv)==3 and sys.argv[1]=="--worker":worker(sys.argv[2])
    else:raise SystemExit("Prepare first; execution requires separately reviewed protocol SHA256")
