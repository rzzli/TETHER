"""Bounded harmless direct-worker timeout; no fetch or AsOf module execution."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTPUT = ROOT / "data/cache/r09-native-direct-worker-timeout-20261028"
BASE_SHA = "d2ec5b9401b6471874373fe3e4329da1da85014d98f8abedd4e0f02ffdaa21a1"


def main():
    base = Path(sys._base_executable).resolve(strict=True)
    assert hashlib.sha256(base.read_bytes()).hexdigest() == BASE_SHA
    assert not OUTPUT.exists() and OUTPUT.resolve().is_relative_to(ROOT)
    OUTPUT.mkdir()
    system = Path(os.environ["SystemRoot"])
    environment = dict(SystemRoot=str(system), WINDIR=str(system), SystemDrive=system.drive,
                       PATH=str(system / "System32"), __PYVENV_LAUNCHER__=sys.executable)
    code = """import os,sys,json,time
from importlib.metadata import version
print(json.dumps(dict(pid=os.getpid(),ppid=os.getppid(),executable=sys.executable,
base_executable=sys._base_executable,prefix=sys.prefix,version=version('asof-target-agents'),
isolated=bool(sys.flags.isolated),dont_write_bytecode=bool(sys.dont_write_bytecode))),flush=True)
time.sleep(30)
"""
    command = [str(base), "-I", "-B", "-c", code]
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=ROOT, env=environment, shell=False,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    timed_out = False
    try:
        stdout, stderr = process.communicate(input=b"", timeout=1)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        stdout, stderr = process.communicate(timeout=3)
    except BaseException:
        process.kill()
        process.wait(timeout=3)
        raise
    elapsed = time.monotonic() - started
    (OUTPUT / "stdout.json").write_bytes(stdout)
    (OUTPUT / "stderr.txt").write_bytes(stderr)
    assert timed_out and process.returncode != 0 and process.poll() is not None
    assert len(stdout) < 4096 and not stderr and elapsed < 5
    worker = json.loads(stdout)
    assert worker["pid"] == process.pid and worker["ppid"] == os.getpid()
    assert Path(worker["executable"]).resolve() == Path(sys.executable).resolve()
    assert Path(worker["base_executable"]).resolve() == base
    assert Path(worker["prefix"]).resolve() == Path(sys.prefix).resolve()
    assert worker["version"] == "0.3.11" and worker["isolated"] and worker["dont_write_bytecode"]
    report = dict(schema_version=1, at_utc=datetime.now(timezone.utc).isoformat(),
                  status="passed_direct_worker_identity_and_forced_timeout",
                  helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  parent_pid=os.getpid(), launched_pid=process.pid, worker=worker,
                  base_executable=str(base), base_executable_sha256=BASE_SHA,
                  controlled_venv_launcher=sys.executable, child_flags=["-I", "-B"],
                  timed_out=True, killed_owned_actual_worker=True,
                  actual_worker_equals_launched_pid=True, handle_reaped=True,
                  returncode=process.returncode, elapsed_seconds=elapsed,
                  http_requests=0, asof_code_imports=0, native_target_or_model_calls=0,
                  scope="One print-and-sleep worker using the proposed exact interpreter transport",
                  limitation="Not a general process-tree/job containment or HTTP/loader conformance proof")
    with (HERE / "PYTHON-DIRECT-WORKER-TIMEOUT.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
