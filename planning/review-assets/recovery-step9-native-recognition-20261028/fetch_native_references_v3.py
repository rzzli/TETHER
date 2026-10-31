"""Fixed twelve public references only; preparation never makes a request.

Use the accepted default 0.3.11 interpreter with -I -B. Actual acquisition needs
the separately reviewed protocol hash. Fetched bytes are data, never imports,
build inputs or executable code in this helper. No automatic retry or crawl.
"""

from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
from importlib import metadata, util
import json
import math
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from threading import Event, Thread
import time
from zipfile import ZipFile

from asof.journal import RunJournal, read_chain
from asof.serde import canonical, encode
from asof.study.stable_read import deadline_check, hash_file, stable_files

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROTOCOL = HERE / "SOURCE-TEXT-PROTOCOL-v3.json"
INVENTORY = HERE / "LOCAL-SOURCE-INVENTORY.json"
INVENTORY_SHA = "595973441abacc48b9e340f5d4df1a15f3abfb000d1409d0f47fa5672398633c"
ADDENDUM = HERE / "SOURCE-SCOPE-ADDENDUM.md"
ADDENDUM_SHA = "e44b1f94a05c230635d03135dbdbdf1023224bf099d603796fbd17568a97d2cb"
FAULT_CHECK = HERE / "INTERRUPTED-READ-FAULT-CHECK-v3.json"
PARENTAGE = HERE / "PYTHON-PARENTAGE-PROBE.json"
PARENTAGE_SHA = "261e96221be0898cd29f982c7c8b339574bc9c9926c5d93cc97be86a9f3df69a"
TIMEOUT_CHECK = HERE / "PYTHON-DIRECT-WORKER-TIMEOUT.json"
TIMEOUT_CHECK_SHA = "63a39f568d531c29e1327a00422ee6e7bddd86df41167597ed4c2a287ec67017"
BASE_EXE = Path(r"C:\Users\zzric\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe")
BASE_EXE_SHA = "d2ec5b9401b6471874373fe3e4329da1da85014d98f8abedd4e0f02ffdaa21a1"
DEFAULT_ENV = ROOT / "data/cache/recovery-step9-generation-wheel-20261028/environment"
DEFAULT_PYTHON = DEFAULT_ENV / "Scripts/python.exe"
FAILED_V2 = ROOT / "data/cache/r09-native-recognition-source-20261028T160234Z"
FAILED_V2_RECEIPT_SHA = "da608eb10930d1ce7374d11ee7165300ed5edcc4613ce386e7f29e20614d92a4"
PREVIOUS = HERE.parent / "recovery-step9-generation-contract-20261028"
ACCEPTANCE = PREVIOUS / "acceptance.json"
ACCEPTANCE_SHA = "491feb0f5fbeefb9df841de46d104b160e3ad4832241b449115037b79961070b"
COMMIT = "848bbda9041decd87904f7eb5a2990863ecce03b"
PATHS = (
    "ggml/include/ggml.h", "ggml/include/ggml-cpu.h", "ggml/include/ggml-backend.h",
    "ggml/include/ggml-opt.h", "ggml/include/gguf.h", "src/llama.cpp",
    "src/llama-model.cpp", "src/llama-model-loader.cpp", "src/llama-model.h",
    "tools/tokenize/tokenize.cpp", "ggml/src/ggml-backend-reg.cpp",
    "src/llama-vocab.cpp",
)
LIMITS = dict(file_body_bytes=1048576, aggregate_retained_body_bytes=4194304,
    whole_child_seconds=20, aggregate_seconds=300, finalization_reserve_seconds=30,
    stdout_bytes=65536, stderr_bytes=65536, maximum_children=12,
    maximum_concurrent_requests=1, attempts_per_url=1)


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pin(path):
    path = Path(path).absolute()
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)


def write_new(path, value):
    with Path(path).open("xb") as stream:
        stream.write(canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def safe_path(path, *, within=ROOT):
    path = Path(path).absolute()
    need(path.is_relative_to(Path(within).absolute()), "Path outside approved root")
    for item in (path, *path.parents):
        if item == ROOT.parent:
            break
        try:
            stat = item.lstat()
        except FileNotFoundError:
            continue
        need(not item.is_symlink() and not (getattr(stat, "st_file_attributes", 0) & 0x400),
             "Symlink/reparse ancestry rejected: " + str(item))
    need(path.resolve().is_relative_to(Path(within).resolve()), "Resolved path escapes approved root")
    return path


def files():
    return [dict(index=i, path=value,
        url=f"https://raw.githubusercontent.com/ggml-org/llama.cpp/{COMMIT}/{value}")
        for i, value in enumerate(PATHS)]


def safe_input(path):
    path = Path(path).absolute()
    if path == BASE_EXE:
        return safe_path(path, within=BASE_EXE.parent)
    return safe_path(path)


def worker_identity():
    need(Path(sys.executable).resolve() == DEFAULT_PYTHON.resolve()
         and Path(sys.prefix).resolve() == DEFAULT_ENV.resolve()
         and Path(sys._base_executable).resolve() == BASE_EXE.resolve()
         and sha(BASE_EXE) == BASE_EXE_SHA
         and metadata.version("asof-target-agents") == "0.3.11"
         and util.find_spec("pyarrow") is None,
         "Pinned direct base worker/default environment identity differs")


def accepted():
    need(os.name == "nt" and sys.flags.isolated and sys.dont_write_bytecode,
         "Use Windows accepted Python with -I -B")
    worker_identity()
    need(metadata.version("asof-target-agents") == "0.3.11"
         and util.find_spec("pyarrow") is None, "Accepted dependency-free 0.3.11 required")
    need(sha(ACCEPTANCE) == ACCEPTANCE_SHA and sha(INVENTORY) == INVENTORY_SHA
         and sha(ADDENDUM) == ADDENDUM_SHA,
         "Accepted version/inventory anchor changed")
    wheel_report = json.loads((PREVIOUS / "WHEEL-ENVIRONMENTS.json").read_bytes())
    acceptance = json.loads(ACCEPTANCE.read_bytes())
    wheel_key = (PREVIOUS / "WHEEL-ENVIRONMENTS.json").relative_to(ROOT).as_posix()
    need({k: pin(PREVIOUS / "WHEEL-ENVIRONMENTS.json")[k] for k in ("sha256","bytes")}
         == acceptance["evidence_files"][wheel_key]
         and sha(wheel_report["wheel"]) == wheel_report["wheel_sha256"] == acceptance["wheel"]["sha256"],
         "Accepted installed-environment/wheel provenance differs")
    need(Path(sys.executable).resolve() == Path(wheel_report["default_python"]).resolve(),
         "Wrong accepted interpreter")
    inventory = json.loads(INVENTORY.read_bytes())
    need(inventory["source_commit"] == COMMIT
         and [item["repository_path"] for item in inventory["proposed_new_references"]] == list(PATHS[:-1]),
         "Fixed source list differs")
    pins = [pin(ACCEPTANCE), pin(INVENTORY), pin(ADDENDUM), pin(PREVIOUS / "WHEEL-ENVIRONMENTS.json"),
            pin(__file__), pin(sys.executable), pin(BASE_EXE), pin(Path(sys.prefix) / "pyvenv.cfg")]
    with ZipFile(wheel_report["wheel"]) as archive:
        members = [name for name in archive.namelist() if name.startswith("asof/") and not name.endswith("/")]
        need(len(members) == 85, "Installed source closure differs")
        for name in members:
            path = Path(sys.prefix) / "Lib/site-packages" / name
            need(sha(path) == hashlib.sha256(archive.read(name)).hexdigest(), "Installed accepted resource changed")
            pins.append(pin(path))
    pins.append(pin(wheel_report["wheel"]))
    for item in inventory["retained_source_references"]:
        path = Path(item["local"]["path"])
        need(pin(path) == item["local"], "Retained reference changed")
        pins.append(pin(path))
    need(len(inventory["retained_source_references"]) == 13, "Retained reference count differs")
    pins.extend(inventory["source_acquisition_manifests"])
    pins.append(inventory["identity_evidence"])
    for item in pins:
        safe_input(item["path"])
    return list({os.path.normcase(item["path"]): item for item in pins}.values())


def checked_protocol(expected):
    need(len(expected) == 64 and all(c in "0123456789abcdef" for c in expected), "Explicit protocol SHA256 required")
    need(sha(PROTOCOL) == expected, "Protocol SHA256 differs")
    value = json.loads(PROTOCOL.read_bytes())
    need(value["kind"] == "fixed_twelve_native_reference_acquisition_v3"
         and value["files"] == files() and value["limits"] == LIMITS
         and value["commit"] == COMMIT and value["helper"]["sha256"] == sha(__file__)
         and value["accepted_acceptance_sha256"] == ACCEPTANCE_SHA
         and value["inventory_sha256"] == INVENTORY_SHA
         and value["scope_addendum"]["sha256"] == ADDENDUM_SHA
         and Path(value["interpreter"]).resolve() == Path(sys.executable).resolve()
         and value["direct_worker"]["path"] == str(BASE_EXE)
         and value["direct_worker"]["sha256"] == BASE_EXE_SHA
         and value["controlled_environment"] == {"__PYVENV_LAUNCHER__":str(DEFAULT_PYTHON)},
         "Protocol identity differs")
    cache = safe_path(value["output"], within=ROOT / "data/cache")
    return value, cache


def sanitized_environment():
    system = Path(os.environ["SystemRoot"])
    return dict(SystemRoot=str(system), WINDIR=str(system), SystemDrive=system.drive,
                PATH=str(system / "System32"), __PYVENV_LAUNCHER__=str(DEFAULT_PYTHON))


def parent_guards(state, *, preparing=False):
    def audit(event, args):
        if event in ("socket.__new__", "socket.connect", "socket.getaddrinfo", "os.system"):
            state["denied"].append(event)
            raise RuntimeError("Parent cannot perform network/system execution")
        if event == "subprocess.Popen":
            active = state.get("active_argv")
            valid = (not preparing and active is not None and state["dispatch_attempts"] < 12
                 and args[1] == subprocess.list2cmdline(active)
                 and args[0] in (None, str(BASE_EXE))
                 and args[2] is not None and Path(args[2]).resolve() == ROOT
                 and args[3] == sanitized_environment())
            if not valid:
                state["denied"].append(event)
                raise RuntimeError("Only one exact fixed fetch child per file")
            state["dispatch_attempts"] += 1
    sys.addaudithook(audit)


def prepare():
    state = dict(dispatch_attempts=0, spawned_children=0, denied=[], active_argv=None)
    parent_guards(state, preparing=True)
    pins = accepted()
    fault = json.loads(FAULT_CHECK.read_bytes())
    need(fault["status"] == "passed_unknown_receipt_parent_interrupt_and_worker_identity_stops"
         and fault["helper_sha256"] == sha(__file__) and fault["actual_children"] == 0
         and fault["actual_network_requests"] == 0, "No-network accounting check missing or stale")
    pins.extend([pin(FAULT_CHECK), pin(HERE / "check_interrupted_read_accounting_v3.py")])
    pins.extend(pin(HERE / name) for name in ("fetch_native_references.py", "SOURCE-TEXT-PROTOCOL.json", "INTERRUPTED-READ-FAULT-CHECK.json",
        "SOURCE-FETCH-PEER-PRECHECK-v1.json", "SOURCE-FETCH-PEER-PRECHECK-v1.md"))
    need(sha(PARENTAGE) == PARENTAGE_SHA and sha(TIMEOUT_CHECK) == TIMEOUT_CHECK_SHA
         and sha(FAILED_V2 / "receipt.json") == FAILED_V2_RECEIPT_SHA,
         "Process-identity or failed-attempt anchor differs")
    parentage = json.loads(PARENTAGE.read_bytes())
    timeout = json.loads(TIMEOUT_CHECK.read_bytes())
    need(parentage["helper_sha256"] == sha(HERE / "probe_python_parentage.py")
         and timeout["helper_sha256"] == sha(HERE / "probe_direct_worker_timeout.py")
         and timeout["status"] == "passed_direct_worker_identity_and_forced_timeout"
         and timeout["base_executable"] == str(BASE_EXE)
         and timeout["base_executable_sha256"] == BASE_EXE_SHA
         and timeout["controlled_venv_launcher"] == str(DEFAULT_PYTHON)
         and timeout["worker"]["pid"] == timeout["launched_pid"]
         and timeout["worker"]["ppid"] == timeout["parent_pid"]
         and Path(timeout["worker"]["prefix"]).resolve() == DEFAULT_ENV.resolve()
         and timeout["worker"]["version"] == "0.3.11"
         and timeout["worker"]["isolated"] is True and timeout["worker"]["dont_write_bytecode"] is True
         and timeout["timed_out"] is True and timeout["killed_owned_actual_worker"] is True
         and timeout["actual_worker_equals_launched_pid"] is True and timeout["handle_reaped"] is True
         and timeout["http_requests"] == timeout["native_target_or_model_calls"] == 0,
         "Direct-worker identity/timeout proof differs")
    pins.extend(pin(HERE / name) for name in ("PYTHON-PARENTAGE-PROBE.json", "probe_python_parentage.py",
        "PYTHON-DIRECT-WORKER-TIMEOUT.json", "probe_direct_worker_timeout.py",
        "fetch_native_references_v2.py", "SOURCE-TEXT-PROTOCOL-v2.json", "INTERRUPTED-READ-FAULT-CHECK-v2.json",
        "check_interrupted_read_accounting_v2.py", "SOURCE-FETCH-ROOT-DECISION-v2.json",
        "SOURCE-FETCH-PEER-PRECHECK-v2.json", "SOURCE-FETCH-PEER-PRECHECK-v2.md",
        "SOURCE-PREPARATION-v2.json", "SOURCE-ACQUISITION-v2-FAILURE-DIAGNOSIS.json"))
    failed_receipt = json.loads((FAILED_V2 / "receipt.json").read_bytes())
    need(failed_receipt["status"] == "failed_or_incomplete" and (FAILED_V2 / "failure.json").is_file(),
         "Prior failed attempt must remain failed")
    for name, expected in failed_receipt["outputs"].items():
        path = safe_path(FAILED_V2 / name, within=FAILED_V2)
        need({key:pin(path)[key] for key in ("sha256","bytes")} == expected,
             "Prior failure evidence differs")
        pins.append(pin(path))
    pins.append(pin(FAILED_V2 / "receipt.json"))
    pins = list({os.path.normcase(item["path"]):item for item in pins}.values())
    for item in pins:
        safe_input(item["path"])
    need(not PROTOCOL.exists(), "Protocol already exists; do not replace")
    output = safe_path(ROOT / "data/cache" / ("r09-native-recognition-source-" +
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")), within=ROOT / "data/cache")
    need(not output.exists(), "Output already exists")
    deadline = time.monotonic() + 60
    with stable_files([Path(item["path"]) for item in pins], deadline=deadline):
        for item in pins:
            need(encode(hash_file(item["path"], deadline)) == {k: item[k] for k in ("sha256", "bytes")},
                 "Preparation pin changed")
        value = dict(schema_version=1, kind="fixed_twelve_native_reference_acquisition_v3",
            recorded_at_utc=datetime.now(timezone.utc).isoformat(), commit=COMMIT, files=files(),
            helper=pin(__file__), accepted_acceptance_sha256=ACCEPTANCE_SHA,
            inventory_sha256=INVENTORY_SHA, scope_addendum=pin(ADDENDUM),
            no_network_accounting_check=pin(FAULT_CHECK),
            superseded_unexecuted=dict(helper=pin(HERE / "fetch_native_references.py"),
                protocol=pin(HERE / "SOURCE-TEXT-PROTOCOL.json"),
                reason="Parent error/interruption must disqualify an otherwise completed child"),
            prior_failed_attempt=dict(receipt=pin(FAILED_V2 / "receipt.json"),
                disposition="preserved_failed_before_HTTP_at_strict_parent_check_not_relabelled",
                protocol=pin(HERE / "SOURCE-TEXT-PROTOCOL-v2.json")),
            process_parentage_probe=pin(PARENTAGE), direct_worker_timeout_check=pin(TIMEOUT_CHECK),
            direct_worker=pin(BASE_EXE), controlled_environment={"__PYVENV_LAUNCHER__":str(DEFAULT_PYTHON)},
            base_read_allowance=dict(root=str(BASE_EXE.parent),read_only=True,writes=False,
                note="Canonical base executable plus Python runtime reads resolving within that base only"),
            ownership_rule="Before HTTP, child PID must equal atomically published Popen PID and PPID must equal reservation owner; same deadline includes at most2s handshake wait. No process-tree guarantee.",
            pinned_files=pins, output=str(output), limits=LIMITS,
            interpreter=str(Path(sys.executable).resolve()), child_flags=["-I", "-B"],
            credentials=False, proxies=False, redirects=False, automatic_retry=False, include_crawl=False,
            protocol_hash_required_by_parent_and_child=True,
            reservation_policy="Reserve1MiB before each sequential child against remaining4MiB retained-body budget; actual retained body replaces reservation only after a qualified complete read. Incomplete receipt stays unknown and stops all remaining requests.",
            retained_body_budget_scope="Successful source bytes plus retained unqualified partial body bytes; excludes separately capped diagnostic captures.",
            conservative_reservation_is_not_measured_transfer=True,
            executable_external_material=False, external_source_import=False, builds=False,
            native_target_calls=0, gguf_file_reads=0, tokenizer_calls=0, model_calls=0, servers=0,
            execution_authorized=False, preparation_activity=dict(children=0, network_requests=0))
        write_new(PROTOCOL, value)
    need(state["dispatch_attempts"] == 0 and state["denied"] == [], "Preparation performed an action")
    print(json.dumps(dict(status="prepared_no_children_or_requests", protocol=str(PROTOCOL),
        protocol_sha256=sha(PROTOCOL), helper_sha256=sha(__file__), pinned_files=len(pins))))


def child_one(index, expected, child_end):
    protocol, cache = checked_protocol(expected)
    need(sys.flags.isolated and sys.dont_write_bytecode and math.isfinite(child_end)
         and 0 <= index < len(PATHS), "Invalid isolated child/index")
    entry = protocol["files"][index]
    directory = safe_path(cache / "attempts" / f"{index:02d}", within=cache)
    reservation = json.loads((directory / "reservation.json").read_bytes())
    need(reservation["parent_pid"] == os.getppid() and reservation["protocol_sha256"] == expected
         and reservation["deadline_monotonic"] == child_end, "Child reservation differs")
    # This parent-published marker binds the actual worker to its Popen handle.
    # Publication is atomic; the bounded wait consumes the same child deadline.
    launch = directory / "spawned-worker.json"
    identity_end = min(child_end - 2, time.monotonic() + 2)
    while not launch.exists():
        deadline_check(identity_end)
        time.sleep(0.01)
    owner = json.loads(launch.read_bytes())
    need(owner == dict(pid=os.getpid(), parent_pid=os.getppid(), protocol_sha256=expected,
                       deadline_monotonic=child_end), "Actual worker differs from launched PID")
    worker_identity()
    write_new(directory / "child-started.json", dict(**owner,
        base_executable=str(Path(sys._base_executable).resolve()),
        executable=str(Path(sys.executable).resolve()), prefix=str(Path(sys.prefix).resolve()),
        isolated=bool(sys.flags.isolated), dont_write_bytecode=bool(sys.dont_write_bytecode),
        asof_distribution_version=metadata.version("asof-target-agents")))
    deadline_check(child_end)
    # The parent's read leases protect these same inputs throughout all requests.
    for item in protocol["pinned_files"]:
        need(encode(hash_file(item["path"], child_end)) == {k: item[k] for k in ("sha256", "bytes")}, "Child input pin differs")
    import urllib.error
    import urllib.request
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    def audit(event, args):
        if event in ("subprocess.Popen", "os.system", "ctypes.dlopen"):
            raise RuntimeError("Fetch child cannot dispatch or load target libraries")
        if event == "socket.getaddrinfo":
            need(args[0] == "raw.githubusercontent.com" and args[1] == 443, "Only raw GitHub HTTPS resolution")
        if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0])).absolute()
            need(path.suffix.lower() != ".gguf" and path.drive.lower() != "e:"
                 and "\\data\\benchmark\\" not in str(path).lower(), "No model/evaluation input")
            mode = args[1] if len(args) > 1 else None
            flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
            writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)) or (isinstance(mode, str) and any(c in mode for c in "wax+"))
            need(not writing or path.is_relative_to(cache), "Child writes only reserved source output")
            if path.drive.casefold() == BASE_EXE.drive.casefold():
                need(not writing and path.resolve().is_relative_to(BASE_EXE.parent.resolve()),
                     "C: access is read-only pinned Python base context")
    sys.addaudithook(audit)
    partial = directory / "body.partial.bin"
    report = dict(schema_version=1, **entry, status="failed_or_incomplete", unknown_received=True,
        observed_body_bytes_at_least=0, retained_body_bytes=0, source_bytes=None, source_sha256=None,
        http_status=None, role="unqualified_reference_until_parent_checks", protocol_sha256=expected)
    try:
        deadline_check(child_end - 2)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        request = urllib.request.Request(entry["url"], headers={"User-Agent":"AsOf-fixed-reference/1.0",
            "Accept":"text/plain", "Accept-Encoding":"identity"})
        timeout = min(15, child_end-time.monotonic()-2)
        need(timeout > 0, "No network time remains")
        with opener.open(request, timeout=timeout) as response:
            report.update(http_status=response.status, final_url=response.geturl(),
                          content_type=response.headers.get("Content-Type"))
            need(response.status == 200 and response.geturl() == entry["url"]
                 and response.headers.get_content_type() == "text/plain", "Unqualified HTTP response")
            length = response.headers.get("Content-Length")
            length = int(length) if length is not None else None
            need(length is None or 0 < length <= LIMITS["file_body_bytes"], "Declared response length exceeds cap or is empty")
            with partial.open("xb") as body, (directory / "read-progress.jsonl").open("xb") as progress:
                complete = False
                while report["retained_body_bytes"] < LIMITS["file_body_bytes"]:
                    deadline_check(child_end - 2)
                    remaining = LIMITS["file_body_bytes"] - report["retained_body_bytes"]
                    if length is not None:
                        remaining = min(remaining, length-report["retained_body_bytes"])
                    if remaining == 0:
                        complete = True
                        break
                    block = response.read(min(65536, remaining))
                    if not block:
                        complete = True
                        break
                    report["observed_body_bytes_at_least"] += len(block)
                    body.write(block); body.flush(); os.fsync(body.fileno())
                    report["retained_body_bytes"] += len(block)
                    progress.write(canonical(dict(observed_body_bytes_at_least=report["observed_body_bytes_at_least"],
                        retained_body_bytes=report["retained_body_bytes"])) + b"\n")
                    progress.flush(); os.fsync(progress.fileno())
                if length is not None and report["retained_body_bytes"] == length:
                    complete = True
                need(complete and (length is None or report["retained_body_bytes"] == length),
                     "Incomplete read or unknown-length response reached limit")
        raw = partial.read_bytes()
        need(bool(raw) and b"\0" not in raw, "Empty/NUL reference text")
        raw.decode("utf-8")
        deadline_check(child_end - 1)
        need(sha(PROTOCOL) == expected and sha(__file__) == protocol["helper"]["sha256"], "Child authority changed")
        target = safe_path(cache / "sources" / entry["path"], within=cache)
        need(not target.exists(), "Source already exists")
        os.rename(partial, target)  # Windows exclusive destination; owned paths only.
        report.update(status="retained_utf8_text", unknown_received=False, source_bytes=len(raw),
            source_sha256=hashlib.sha256(raw).hexdigest(), source_path=str(target), role="source_reference_only")
    except BaseException as error:
        report.update(status="failed_or_incomplete", unknown_received=True,
                      error_class=type(error).__name__, error=str(error)[:2048])
    write_new(directory / "child-result.json", report)
    print(canonical(report).decode("utf-8"), flush=True)
    return 0 if report["status"] == "retained_utf8_text" else 1


def run_child(entry, cache, expected, journal, state, deadline):
    started = time.monotonic()
    end = min(started + 20, deadline - 30)
    deadline_check(end)
    directory = safe_path(cache / "attempts" / f"{entry['index']:02d}", within=cache)
    directory.mkdir()
    write_new(directory / "reservation.json", dict(parent_pid=os.getpid(), protocol_sha256=expected,
        deadline_monotonic=end, conservative_body_reservation_bytes=1048576))
    argv = [str(BASE_EXE), "-I", "-B", str(Path(__file__).resolve()), "--one", str(entry["index"]), expected, repr(end)]
    record = dict(index=entry["index"], argv=argv, pid=None, spawned=False, reaped=False,
        timed_out=False, cleanup_errors=[], streams={}, conservative_body_reservation_bytes=1048576)
    process, threads, stop, captures = None, [], Event(), ExitStack()
    journal.append("source_child_reserved", **record)
    def drain(name, pipe, sink):
        item = record["streams"][name]
        try:
            while True:
                block = pipe.read(65536)
                if not block: break
                item["observed_bytes_at_least"] += len(block)
                remaining = 65536-item["retained_bytes"]
                if remaining:
                    sink.write(block[:remaining]); item["retained_bytes"] += min(remaining,len(block))
                if len(block) > remaining:
                    item["truncated"] = True; stop.set(); break
        except BaseException as error:
            item["error_class"] = type(error).__name__; stop.set()
        finally:
            try: sink.flush(); os.fsync(sink.fileno())
            except BaseException as error: item["error_class"] = type(error).__name__; stop.set()
    try:
        sinks = {name: captures.enter_context((directory/(name+".bin")).open("xb")) for name in ("stdout","stderr")}
        state["active_argv"] = argv
        process = subprocess.Popen(argv, cwd=ROOT, env=sanitized_environment(), shell=False,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True,
            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        record.update(pid=process.pid, spawned=True); state["spawned_children"] += 1
        process.stdin.close()
        pending = directory / "spawned-worker.pending.json"
        write_new(pending, dict(pid=process.pid, parent_pid=os.getpid(), protocol_sha256=expected,
                               deadline_monotonic=end))
        os.rename(pending, directory / "spawned-worker.json")
        journal.append("source_child_started", index=entry["index"], pid=process.pid)
        for name, pipe in (("stdout",process.stdout),("stderr",process.stderr)):
            record["streams"][name] = dict(retained_bytes=0, observed_bytes_at_least=0, truncated=False,error_class=None)
            thread = Thread(target=drain,args=(name,pipe,sinks[name]),daemon=True); thread.start(); threads.append(thread)
        while process.poll() is None:
            if stop.is_set() or time.monotonic() >= end:
                record["timed_out"] = time.monotonic() >= end; process.kill(); break
            time.sleep(0.02)
    except BaseException as error:
        record.update(error_class=type(error).__name__,error=str(error)[:2048])
        if isinstance(error,KeyboardInterrupt): record["interrupted"] = True
    finally:
        state["active_argv"] = None
        if process is not None:
            try:
                if process.poll() is None: process.kill()
                process.wait(timeout=max(0.1,min(3,deadline-time.monotonic())))
                record.update(reaped=True, returncode=process.poll())
            except BaseException as error: record["cleanup_errors"].append(type(error).__name__)
            for thread in threads: thread.join(timeout=max(0.1,min(2,deadline-time.monotonic())))
            if any(thread.is_alive() for thread in threads): record["cleanup_errors"].append("CaptureThreadUnresolved")
            if not any(thread.is_alive() for thread in threads):
                for pipe in (process.stdout,process.stderr):
                    if pipe is not None: pipe.close()
        try: captures.close()
        except BaseException as error: record["cleanup_errors"].append(type(error).__name__)
        record.update(full_process_elapsed_seconds=time.monotonic()-started,effective_seconds=end-started)
        for name in ("stdout","stderr"):
            path=directory/(name+".bin")
            if path.exists(): record[name]=pin(path)
        write_new(directory/"parent-attempt.json",record)
        journal.append("source_child_terminal",**record)
    return record


def collect(protocol, cache, expected, journal, state, deadline, runner=run_child, records=None):
    """Fixed sequential acquisition; failure never releases unknown reservation."""
    if records is None:
        records=[dict(**entry,status="not_attempted",unknown_received=False) for entry in files()]
    retained=0
    for entry in files():
        index=entry["index"]
        if 4194304-retained < 1048576:
            records[index].update(status="not_attempted_budget_reservation")
            break
        deadline_check(deadline-30)
        records[index].update(status="attempt_reserved",conservative_body_reservation_bytes=1048576,
            reservation_disposition="pending_not_measured_transfer")
        try:
            attempt=runner(entry,cache,expected,journal,state,deadline)
            need(attempt["spawned"] and attempt["reaped"] and attempt.get("returncode")==0
                and "error_class" not in attempt and "interrupted" not in attempt
                and not attempt["timed_out"] and not attempt["cleanup_errors"]
                and attempt["full_process_elapsed_seconds"] <= attempt["effective_seconds"] <= 20
                and all(not s["truncated"] and s["error_class"] is None for s in attempt["streams"].values()),
                "Owned child/capture/deadline failed")
            directory=cache/"attempts"/f"{index:02d}"
            owner=json.loads((directory/"spawned-worker.json").read_bytes())
            started=json.loads((directory/"child-started.json").read_bytes())
            reservation=json.loads((directory/"reservation.json").read_bytes())
            need(owner == dict(pid=attempt["pid"],parent_pid=os.getpid(),protocol_sha256=expected,
                               deadline_monotonic=reservation["deadline_monotonic"])
                 and all(started[key]==value for key,value in owner.items())
                 and reservation["parent_pid"]==os.getpid()
                 and started["base_executable"]==str(BASE_EXE.resolve())
                 and started["executable"]==str(DEFAULT_PYTHON.resolve())
                 and started["prefix"]==str(DEFAULT_ENV.resolve())
                 and started["isolated"] is True and started["dont_write_bytecode"] is True
                 and started["asof_distribution_version"]=="0.3.11", "Actual worker identity differs")
            child=json.loads((directory/"child-result.json").read_bytes())
            need(json.loads((directory/"stdout.bin").read_bytes())==child and (directory/"stderr.bin").stat().st_size==0,
                 "Child result/captures differ")
            need(child["status"]=="retained_utf8_text" and child["unknown_received"] is False
                and child["protocol_sha256"]==expected and child["url"]==entry["url"]
                and child["path"]==entry["path"], "Incomplete/unbound source receipt")
            target=safe_path(cache/"sources"/entry["path"],within=cache)
            need(Path(child["source_path"]).resolve()==target.resolve()
                and target.stat().st_size==child["source_bytes"]<=1048576
                and sha(target)==child["source_sha256"], "Retained source differs")
            raw=target.read_bytes(); need(bool(raw) and b"\0" not in raw,"Invalid reference bytes"); raw.decode("utf-8")
            retained += len(raw)
            records[index]=dict(child,attempt=attempt,conservative_body_reservation_bytes=1048576,
                reservation_disposition="replaced_by_known_retained_body")
            journal.append("source_reference_qualified",index=index,bytes=len(raw),sha256=child["source_sha256"])
        except BaseException as error:
            records[index]=dict(**entry,status="failed_or_incomplete_unknown_receipt",unknown_received=True,
                source_bytes=None,source_sha256=None,conservative_body_reservation_bytes=1048576,
                reservation_disposition="retained_unknown_not_zero_measured_transfer",
                error_class=type(error).__name__,error=str(error)[:2048])
            journal.append("source_receipt_unknown_stop",**records[index])
            for later in records[index+1:]: later["status"]="not_attempted_after_unknown_receipt"
            break
    return records,retained


def fetch(expected):
    accepted()
    protocol,cache=checked_protocol(expected)
    need(not cache.exists(),"Attempt already reserved; never restart")
    journal=RunJournal(cache,kind="build")
    state=dict(dispatch_attempts=0,spawned_children=0,denied=[],active_argv=None)
    parent_guards(state)
    started=time.monotonic(); deadline=started+300; leases=ExitStack(); failure=None
    records=[dict(**entry,status="not_attempted",unknown_received=False) for entry in files()]
    summary=dict(schema_version=1,status="failed_or_incomplete",protocol_sha256=expected,
        commit=COMMIT,records=records,unknown_received=False,known_qualified_source_bytes=0,
        role="public_reference_data_only",native_target_calls=0,gguf_file_reads=0,model_calls=0,
        tokenizer_calls=0,servers=0,external_code_imported=False,external_code_executed=False,builds=0,
        automatic_retry=False,remaining_requests_stopped_on_unknown_receipt=True,
        known_retained_body_bytes_including_unqualified_partials=None,
        retained_body_measurement_reason="not_completed")
    def fail(error,phase):
        nonlocal failure
        failure=dict(error_class=type(error).__name__,error=str(error)[:2048],phase=phase)
        summary.update(status="failed_or_incomplete",failure=failure)
        marker=cache/"failure.json"
        if not marker.exists(): write_new(marker,dict(authoritative=True,**failure,automatic_retry=False))
    try:
        (cache/"attempts").mkdir(); (cache/"sources").mkdir()
        for entry in files(): safe_path(cache/"sources"/entry["path"],within=cache).parent.mkdir(parents=True,exist_ok=True)
        write_new(cache/"effective-protocol.json",protocol)
        pins=protocol["pinned_files"]+[pin(PROTOCOL)]
        leases.enter_context(stable_files([Path(item["path"]) for item in pins],deadline=deadline))
        for item in pins: need(encode(hash_file(item["path"],deadline))=={k:item[k] for k in ("sha256","bytes")},"Fetch pin changed")
        journal.append("source_protocol_reserved",protocol_sha256=expected,files=12,limits=LIMITS)
        records,retained=collect(protocol,cache,expected,journal,state,deadline,records=records)
        summary.update(records=records,known_qualified_source_bytes=retained,
            unknown_received=any(row["unknown_received"] for row in records),
            conservative_reservation_sum_bytes=sum(row.get("conservative_body_reservation_bytes",0) for row in records),
            attempted_children=state["dispatch_attempts"],spawned_children=state["spawned_children"])
        bodies=list((cache/"sources").rglob("*"))+list((cache/"attempts").glob("*/body.partial.bin"))
        body_bytes=sum(path.stat().st_size for path in bodies if path.is_file())
        summary["known_retained_body_bytes_including_unqualified_partials"]=body_bytes
        need(body_bytes<=4194304 and not state["denied"],"Retained-body budget/parent guard failed")
        for item in pins: need(encode(hash_file(item["path"],deadline))=={k:item[k] for k in ("sha256","bytes")},"Final input pin changed")
        need(all(row["status"]=="retained_utf8_text" for row in records) and not summary["unknown_received"],
             "Incomplete acquisition; remaining files were not retried")
        summary["status"]="source_references_retained"
    except BaseException as error:
        fail(error,"acquisition")
    finally:
        try:
            for row in records:
                if row["status"] == "attempt_reserved":
                    row.update(status="unresolved_attempt_unknown_receipt",unknown_received=True,
                        source_bytes=None,source_sha256=None,
                        reservation_disposition="retained_unknown_not_zero_measured_transfer")
            summary.update(records=records,
                known_qualified_source_bytes=sum(row.get("source_bytes") or 0 for row in records if row["status"]=="retained_utf8_text"),
                unknown_received=any(row["unknown_received"] for row in records),
                conservative_reservation_sum_bytes=sum(row.get("conservative_body_reservation_bytes",0) for row in records),
                unresolved_conservative_body_reservation_bytes=sum(row.get("conservative_body_reservation_bytes",0) for row in records if row["unknown_received"]),
                attempted_children=state["dispatch_attempts"],spawned_children=state["spawned_children"])
            bodies=list((cache/"sources").rglob("*"))+list((cache/"attempts").glob("*/body.partial.bin"))
            summary["known_retained_body_bytes_including_unqualified_partials"]=sum(path.stat().st_size for path in bodies if path.is_file())
            summary["retained_body_measurement_reason"]="actual retained files, not measured network transfer"
            need(summary["known_retained_body_bytes_including_unqualified_partials"]<=4194304,
                 "Final retained-body limit exceeded")
            summary["elapsed_seconds_before_finalization"]=time.monotonic()-started
            summary["guards"]={k:v for k,v in state.items() if not k.startswith("active_")}
            try: journal.append("source_acquisition_terminal",status=summary["status"],unknown_received=summary["unknown_received"])
            finally: journal.close()
            write_new(cache/"terminal-report.json",summary)
            deadline_check(deadline)
            chain=read_chain(cache/"journal.jsonl")
            outputs={}
            for path in sorted(cache.rglob("*")):
                deadline_check(deadline)
                if path.is_file(): outputs[path.relative_to(cache).as_posix()]=encode(hash_file(path,deadline))
            write_new(cache/"receipt.json",dict(schema_version=1,kind="source_reference_terminal_inventory_v1",
                protocol_sha256=expected,status=summary["status"],outputs=outputs,journal_tip_sha256=chain[-1]["sha256"],
                authority_rule="failure.json vetoes source qualification even if a terminal report/receipt exists"))
            deadline_check(deadline)
        except BaseException as error:
            fail(error,"finalization")
        finally:
            try: leases.close(); deadline_check(deadline)
            except BaseException as error: fail(error,"lease_cleanup_or_global_deadline")
    print(json.dumps(dict(status=summary["status"],output=str(cache),authoritative_failure=(cache/"failure.json").exists(),
        terminal_report_sha256=sha(cache/"terminal-report.json") if (cache/"terminal-report.json").exists() else None,
        elapsed_seconds=time.monotonic()-started)),flush=True)
    return 0 if failure is None and not (cache/"failure.json").exists() and summary["status"]=="source_references_retained" else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--prepare"]:
        prepare()
    elif len(sys.argv)==3 and sys.argv[1]=="--fetch":
        raise SystemExit(fetch(sys.argv[2]))
    elif len(sys.argv)==5 and sys.argv[1]=="--one":
        raise SystemExit(child_one(int(sys.argv[2]),sys.argv[3],float(sys.argv[4])))
    else:
        raise SystemExit("Use --prepare only until reviewed; acquisition requires --fetch PROTOCOL_SHA256")
