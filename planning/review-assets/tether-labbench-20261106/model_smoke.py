"""One explicitly dispatched fictional MCQ smoke, under a Windows process job.

No benchmark data, old launchers, active pointers or model retries. The default
command only prints the proposed fixture/limits. --execute requires externally
supplied code hashes and a new output directory. The parent bounds the entire
worker; KILL_ON_JOB_CLOSE contains its descendants if normal cleanup fails.
"""
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from asof.atomic import publish_bytes
from asof.journal import RunJournal, read_chain
from asof.serde import ContractError, canonical, encode, fingerprint, parse_json
from asof.study.session import StudySession, verify_study
from asof.workflow import Budget
from tether._process import ProcessLimits, supervise_command, validate_success_report
from experiments.labbench import model

RECEIPT = Path(r"E:\projects_data\drug_target_agents_data\models\qwen25-14b-q4km-20261018T032528Z\acquisition.json")
RECEIPT_SHA256 = "cc95c56ce1f497b36d6b9ed62b22721d8af7eaccc0a8c50da91439c5b076acbf"
LIMITS = dict(total_seconds=900, startup_seconds=180,
              query_seconds=120, output_bytes=4*1024**2, port=55606,
              threads=8, gpu_layers=99, context_tokens=16384)
ALIAS = "tether-litqa2-fictional-qwen14b-v1"


def need(condition, message):
    if not condition:
        raise ContractError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    publish_bytes(Path(path), canonical(value) + b"\n")


def fixture():
    text = "In this invented laboratory, the Lumen-7 orb is cobalt. The amber item is a different object."
    query = dict(id="00000000-0000-0000-0000-000000000106",
                 question="In the invented laboratory, what color is the Lumen-7 orb?",
                 choices=["(A) Amber", "(B) Insufficient information to answer the question", "(C) Cobalt"])
    sources = [dict(source_id="fiction-lumen7:p0001", sha256=sha(text.encode()), text=text)]
    # This deterministic expected answer never enters the model request as a key.
    expected = dict(answer_index=2, evidence_ids=["fiction-lumen7:p0001"])
    return query, sources, expected


def code_pins():
    files = [Path(__file__).resolve(), ROOT/"experiments/labbench/model.py",
             ROOT/"experiments/labbench/native_contract.py"]
    return {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p.read_bytes()) for p in files}


def empty_import_cache(expected=None):
    """Fresh prefix + -B avoids loading old adjacent timestamp-valid bytecode."""
    need(sys.dont_write_bytecode and sys.flags.isolated == 1 and isinstance(sys.pycache_prefix,str)
         and sys.pycache_prefix, "Smoke requires -I -B -X pycache_prefix=<fresh empty path>")
    path=Path(sys.pycache_prefix).resolve()
    need(path.is_relative_to((ROOT/"data/cache").resolve()), "Import cache prefix outside isolated cache root")
    if expected is not None:
        need(path == Path(expected).resolve(), "Worker import cache prefix differs")
    path.mkdir(parents=True,exist_ok=True)
    need(not any(path.iterdir()), "Import cache prefix is not empty")
    return path


def create_kill_job():
    """Assign this worker to a non-inheritable kill-on-close Windows job.

    The handle intentionally stays open until process exit. Closing it here
    would terminate this worker too. Failure occurs before any model spawn.
    """
    need(os.name == "nt", "This smoke helper requires Windows job containment")
    from ctypes import wintypes as w
    class Basic(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", w.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", w.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", w.DWORD), ("SchedulingClass", w.DWORD)]
    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in ("ReadOperationCount", "WriteOperationCount",
                    "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]
    class Extended(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", Basic), ("IoInfo", IO),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
    api.CreateJobObjectW.restype = w.HANDLE
    api.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
    api.SetInformationJobObject.restype = w.BOOL
    api.GetCurrentProcess.restype = w.HANDLE
    api.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    api.AssignProcessToJobObject.restype = w.BOOL
    api.SetHandleInformation.argtypes = [w.HANDLE, w.DWORD, w.DWORD]
    api.SetHandleInformation.restype = w.BOOL
    api.CloseHandle.argtypes = [w.HANDLE]
    api.CloseHandle.restype = w.BOOL
    handle = api.CreateJobObjectW(None, None)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    value = Extended()
    value.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    assigned = False
    try:
        if not api.SetHandleInformation(handle, 1, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        if not api.SetInformationJobObject(handle, 9, ctypes.byref(value), ctypes.sizeof(value)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not api.AssignProcessToJobObject(handle, api.GetCurrentProcess()):
            raise ctypes.WinError(ctypes.get_last_error())
        assigned = True
    finally:
        if not assigned:
            api.CloseHandle(handle)
    return handle  # DO NOT close while self is a member; the OS closes it on exit.


def process_sample(pid):
    if os.name != "nt":
        return None
    from ctypes import wintypes as w
    class Memory(ctypes.Structure):
        _fields_ = [("cb", w.DWORD), ("PageFaultCount", w.DWORD)] + [(name, ctypes.c_size_t)
            for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage",
                         "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]; api.OpenProcess.restype = w.HANDLE
    api.CloseHandle.argtypes = [w.HANDLE]
    api.GetProcessTimes.argtypes = [w.HANDLE, *([ctypes.POINTER(w.FILETIME)]*4)]
    api.GetProcessTimes.restype = w.BOOL
    memapi = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
    memapi.argtypes = [w.HANDLE, ctypes.POINTER(Memory), w.DWORD]; memapi.restype = w.BOOL
    handle = api.OpenProcess(0x0410, False, pid)
    if not handle:
        return None
    try:
        value = Memory(); value.cb = ctypes.sizeof(value)
        memory_ok = memapi(handle, ctypes.byref(value), value.cb)
        created, ended, kernel, user = (w.FILETIME() for _ in range(4))
        time_ok = api.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(ended), ctypes.byref(kernel), ctypes.byref(user))
        ticks = lambda f: (f.dwHighDateTime << 32) + f.dwLowDateTime
        return dict(working_set_bytes=int(value.WorkingSetSize) if memory_ok else None,
                    process_peak_working_set_bytes=int(value.PeakWorkingSetSize) if memory_ok else None,
                    cpu_seconds=(ticks(kernel)+ticks(user))/10**7 if time_ok else None)
    finally:
        api.CloseHandle(handle)


class Samples:
    def __init__(self, pid):
        self.pid, self.values = pid, []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.poll, daemon=True)
    def poll(self):
        while not self.stop.wait(.5):
            self.capture()
    def capture(self):
        self.values.append(dict(monotonic=time.monotonic(), value=process_sample(self.pid)))
    def __enter__(self):
        self.capture(); self.thread.start(); return self
    def __exit__(self, *unused):
        self.capture(); self.stop.set(); self.thread.join(2)


def worker(recipe_path, expected_sha, output):
    with Path(recipe_path).open("rb") as stream:
        raw = stream.read(65537)
    need(len(raw) <= 65536 and sha(raw) == expected_sha, "Smoke recipe anchor differs")
    recipe = parse_json(raw)
    need(recipe["code_pins"] == code_pins(), "Smoke worker code changed")
    need(recipe["limits"] == LIMITS, "Smoke worker limits changed")
    need(recipe["receipt"] == str(RECEIPT) and recipe["receipt_sha256"] == RECEIPT_SHA256,
         "Smoke model authority changed")
    prefix=empty_import_cache(recipe["worker_import_cache"])
    journal = RunJournal(Path(output), kind="build")
    started, cpu = time.monotonic(), time.process_time()
    deadline = started + LIMITS["total_seconds"] - 10
    stage, owner, sampler, result = "job_containment", None, None, None
    handle = None
    timings = {}
    try:
        handle = create_kill_job()
        journal.append("smoke_job_contained", kill_on_job_close=True, inherited_handle=False)
        stage = "asset_manifest_preparation"
        spec, bindings, provenance = model.make_server_spec(RECEIPT, RECEIPT_SHA256,
            port=LIMITS["port"], alias=ALIAS, startup_seconds=LIMITS["startup_seconds"],
            context_tokens=LIMITS["context_tokens"], threads=LIMITS["threads"], gpu_layers=LIMITS["gpu_layers"])
        proofs=[spec.executable,*spec.required_inputs]
        journal.append("smoke_assets_declared",proofs=proofs,total_asset_bytes=sum(p["bytes"] for p in proofs))
        server_output = Path(output)/"server"; server_output.mkdir()
        owner = model.owned_server(spec, bindings, output=server_output, journal=journal, parent_deadline=deadline)
        stage = "owned_startup"
        mark = time.monotonic()
        with owner:
            timings["owned_startup_including_asset_verification_seconds"] = time.monotonic()-mark
            timings["asset_verification_seconds"] = None
            journal.append("smoke_assets_verified_by_owned_server",proof_count=len(proofs),
                           total_asset_bytes=sum(p["bytes"] for p in proofs),
                           separate_hash_timing="not instrumented; included in owned startup")
            stage = "fictional_query"
            with Samples(owner.terminal_record["pid"]) as sampler:
                query, sources, expected = fixture()
                request, payload = model.make_request(query, sources, provenance)
                query_started = time.monotonic()
                query_deadline = min(deadline-40, query_started+LIMITS["query_seconds"])
                query_out = Path(output)/"query"; query_out.mkdir()
                journal.append("smoke_query_reserved", task_id=query["id"], request_sha256=fingerprint(request),
                               query_seconds=LIMITS["query_seconds"], max_generation_attempts=1)
                quote = model.tokenize_once(owner,payload,output=query_out/"tokenization",journal=journal,deadline=query_deadline)
                capture = query_out/"transport"; capture.mkdir()
                backend = model.LocalMCQBackend(owner=owner,request=request,payload=payload,tokenization=quote,
                    output=capture,deadline=query_deadline,model_alias=ALIAS)
                verifier = model.MCQVerifier(model_alias=ALIAS)
                with StudySession(query_out/"session",resources={},required_resources=(),
                        configuration=dict(purpose="fictional_native_mcq_qualification", absolute_query_budget_seconds=120),
                        budget=Budget(max_calls=1,max_retries=0,max_input_tokens=16384,max_output_tokens=256,
                                      max_seconds=max(.001,query_deadline-time.monotonic()))) as session:
                    prediction = session.call_once(request=request,payload=payload,backend=backend,verifier=verifier)
                    session.finish()
                need(time.monotonic() < query_deadline, "Fictional query exceeded original shared deadline")
                timings["tokenization_generation_and_cell_seal_seconds"] = time.monotonic()-query_started
                receipt = query_out/"session/receipt.json"
                verification = verify_study(query_out/"session",expected_receipt_sha256=sha(receipt.read_bytes()),
                                             verifier=verifier,deadline=deadline)
                need(canonical(prediction) == canonical(expected), "Fictional expected answer/source differs; no retry")
                result = dict(prediction=prediction,expected=expected,session_receipt_sha256=sha(receipt.read_bytes()),
                              replay=verification,exact_prompt_tokens=quote["token_count"],
                              reservation=encode(backend.reservation),measured_usage=encode(session.usage),
                              provider_cost_usd=0,query_count=1,tokenizer_requests=1,generation_attempts=1)
                stage = "owned_cleanup"
                mark = time.monotonic()
        timings["normal_owned_cleanup_seconds"] = time.monotonic()-mark
        need(owner.terminal_record["server_stopped"] is True,"Owned server cleanup remains unverified")
        need(code_pins() == recipe["code_pins"],"Smoke code changed during execution")
        empty_import_cache(prefix)
        need(time.monotonic() < deadline,"Smoke finalization exceeded worker budget")
        stage = "finalization"
        journal.append("smoke_verified", result=result, server_terminal=owner.terminal_record)
        report = dict(schema_version=1,status="qualified_fictional_only",result=result,timings=timings,
                      server_terminal=owner.terminal_record,model_samples=sampler.values if sampler else [],
                      sampling_seconds=.5,model_gpu_memory_bytes=None,gpu_memory_reason="not instrumented",
                      worker_peak=process_sample(os.getpid()),worker_cpu_seconds=time.process_time()-cpu,
                      worker_wall_seconds=time.monotonic()-started,job_containment="kill_on_last_handle_close",
                      cleanup="normal_owned_server_cleanup_verified",code_pins=recipe["code_pins"],
                      import_cache=dict(prefix=str(prefix),empty_before_and_after=True,
                                        isolated=sys.flags.isolated,dont_write_bytecode=sys.dont_write_bytecode),
                      limitations=["Fictional question only; no native benchmark accuracy", "Sampled model CPU/RAM after readiness omits startup peaks",
                                   "Asset verification and owned startup timing are combined", "No GPU memory or energy measurement"])
        write(Path(output)/"report.json",report)
        write(Path(output)/"COMPLETE.json",dict(status=report["status"],report_sha256=sha((Path(output)/"report.json").read_bytes()),
              journal_terminal_sha256=journal.events[-1]["sha256"],cleanup=report["cleanup"]))
    except BaseException as error:
        try:
            journal.fail(error,stage)
            write(Path(output)/"FAILURE.json",dict(status="failed",stage=stage,error_class=type(error).__name__,
                message=str(error),server_terminal=owner.terminal_record if owner else None,
                cleanup="normal_cleanup_verified" if owner and owner.terminal_record.get("server_stopped") is True
                else "forced_job_cleanup_pending_or_server_not_started",automatic_retry=False))
        except BaseException as secondary:
            error.add_note("Smoke failure capture: "+type(secondary).__name__)
        raise
    finally:
        journal.close()
        # Keep the job handle open through receipt writes. Process exit closes it.
        _ = handle


def execute(output, expected_pins):
    need(code_pins() == expected_pins,"Supplied smoke code pins differ")
    parent_prefix=empty_import_cache()
    output = Path(output).resolve()
    need(output.is_relative_to((ROOT/"data/cache").resolve()),"Smoke output must be a fresh data/cache path")
    journal = RunJournal(output,kind="build")
    started = time.monotonic()
    result = None
    try:
        versions = {name:metadata.version(name) for name in ("asof-target-agents","tether-target-agents")}
        need(versions == {"asof-target-agents":"0.3.13","tether-target-agents":"0.5.2"},"Use the qualified isolated Python environment")
        worker_prefix=output/"worker-import-cache"
        worker_prefix.mkdir()
        recipe = dict(schema_version=1,kind="labbench_fictional_model_smoke",code_pins=expected_pins,
                      limits=LIMITS,receipt=str(RECEIPT),receipt_sha256=RECEIPT_SHA256,
                      worker_import_cache=str(worker_prefix),parent_import_cache=str(parent_prefix),
                      versions=versions,created_at_utc=datetime.now(timezone.utc).isoformat())
        write(output/"recipe.json",recipe)
        limits = ProcessLimits(timeout_seconds=LIMITS["total_seconds"],max_output_bytes=LIMITS["output_bytes"])
        command = [sys.executable,"-I","-B","-X","pycache_prefix="+str(worker_prefix),str(Path(__file__).resolve()),"--worker","--recipe",str(output/"recipe.json"),
                   "--recipe-sha256",sha((output/"recipe.json").read_bytes()),"--output",str(output/"worker")]
        journal.append("smoke_worker_dispatch",command=command,limits=limits.payload(),recipe_sha256=sha((output/"recipe.json").read_bytes()))
        try:
            result = supervise_command(command,limits=limits)
        except BaseException as error:
            result = getattr(error,"tether_engine_result",None)
            raise
        finally:
            if result is not None:
                publish_bytes(output/"worker.stdout",result.stdout)
                publish_bytes(output/"worker.stderr",result.stderr)
                write(output/"SUPERVISION.json",dict(returncode=result.returncode,supervision=result.supervision))
        need(result is not None and result.returncode == 0,"Smoke worker did not complete successfully")
        validate_success_report(result.supervision,limits,len(result.stdout),len(result.stderr))
        complete = parse_json((output/"worker/COMPLETE.json").read_bytes())
        need(complete["status"] == "qualified_fictional_only" and complete["cleanup"] == "normal_owned_server_cleanup_verified"
             and complete["report_sha256"] == sha((output/"worker/report.json").read_bytes())
             and complete["journal_terminal_sha256"] == read_chain(output/"worker/journal.jsonl")[-1]["sha256"],
             "Smoke final artifacts do not reconcile")
        need(code_pins() == expected_pins,"Smoke source changed during parent supervision")
        empty_import_cache(parent_prefix)
        need(not any(worker_prefix.iterdir()),"Worker import cache is no longer empty")
        journal.append("smoke_parent_verified",worker_complete_sha256=sha((output/"worker/COMPLETE.json").read_bytes()))
        write(output/"COMPLETE.json",dict(status="qualified_fictional_only",wall_seconds=time.monotonic()-started,
              worker_complete_sha256=sha((output/"worker/COMPLETE.json").read_bytes()),journal_terminal_sha256=journal.events[-1]["sha256"],
              import_cache=dict(parent_prefix=str(parent_prefix),worker_prefix=str(worker_prefix),
                                empty_before_and_after=True,isolated=sys.flags.isolated,dont_write_bytecode=sys.dont_write_bytecode),
              provider_cost_usd=0,benchmark_questions=0))
    except BaseException as error:
        try:
            journal.fail(error,"parent_supervision_or_verification")
            write(output/"FAILURE.json",dict(status="failed",error_class=type(error).__name__,message=str(error),
                  wall_seconds=time.monotonic()-started,worker_returncode=result.returncode if result else None,
                  cleanup="forced_job_cleanup_or_unverified; inspect worker proof",automatic_retry=False))
        except BaseException as secondary:
            error.add_note("Parent failure capture: "+type(secondary).__name__)
        raise
    finally:
        journal.close()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--worker",action="store_true")
    parser.add_argument("--recipe");parser.add_argument("--recipe-sha256");parser.add_argument("--output")
    parser.add_argument("--expected-helper-sha256");parser.add_argument("--expected-model-sha256");parser.add_argument("--expected-contract-sha256")
    parser.add_argument("--containment-fixture")
    args=parser.parse_args()
    if args.containment_fixture:
        # Tiny non-model child used solely to qualify parent deadline/job cleanup.
        handle=create_kill_job()
        child=subprocess.Popen([sys.executable,"-I","-c","import time; time.sleep(60)"],
                               creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0),close_fds=True)
        write(Path(args.containment_fixture),dict(worker_pid=os.getpid(),child_pid=child.pid,contained=True))
        time.sleep(60)
        _=handle
    elif args.worker:
        need(args.recipe and args.recipe_sha256 and args.output,"Worker requires exact recipe/output")
        worker(args.recipe,args.recipe_sha256,args.output)
    elif args.execute:
        need(args.output and args.expected_helper_sha256 and args.expected_model_sha256 and args.expected_contract_sha256,
             "Execution requires fresh output and three external code hash pins")
        pins={str(Path(__file__).resolve().relative_to(ROOT)).replace("\\","/"):args.expected_helper_sha256,
              "experiments/labbench/model.py":args.expected_model_sha256,
              "experiments/labbench/native_contract.py":args.expected_contract_sha256}
        execute(args.output,pins)
    else:
        query,sources,expected=fixture()
        print(json.dumps(dict(status="not_dispatched",query=query,sources=sources,expected=expected,
                              limits=LIMITS,code_pins=code_pins(),receipt=str(RECEIPT),receipt_sha256=RECEIPT_SHA256),indent=2))


if __name__ == "__main__":
    main()
