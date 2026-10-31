"""Own-source future launcher fixture; no target library, model or network.

Do not run without its separately frozen qualification protocol. The parent
must create this worker suspended and verify its Job before the only resume.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(r"C:\Users\zzric\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe")
MODES = ("resources", "overflow", "sleep", "suspended_abort")


def need(value, message):
    if not value:
        raise RuntimeError(message)


def safe(path):
    path = Path(path).absolute()
    cache = ROOT / "data/cache"
    need(path.is_relative_to(cache) and path.resolve().is_relative_to(cache.resolve()), "Fixture path outside cache")
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        need(not part.is_symlink() and not getattr(info, "st_file_attributes", 0) & 0x400,
             "Fixture reparse ancestry")
    return path


def publish(path, value):
    path = safe(path)
    pending = path.with_name(path.name + ".pending")
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii") + b"\n"
    need(len(raw) <= 4096, "Fixture marker cap")
    with pending.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.rename(pending, path)


def main():
    need(os.name == "nt" and sys.flags.isolated and sys.dont_write_bytecode, "Windows -I -B fixture only")
    need(len(sys.argv) == 5, "MODE OUTPUT PROTOCOL SHA256 required")
    mode, out_arg, protocol_arg, expected = sys.argv[1:]
    need(mode in MODES and len(expected) == 64 and all(c in "0123456789abcdef" for c in expected), "Fixture arguments")
    protocol_path = safe(protocol_arg)
    need(protocol_path.stat().st_size <= 1024 * 1024, "Fixture protocol cap")
    raw = protocol_path.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == expected, "Fixture protocol identity")
    protocol = json.loads(raw)
    need(protocol["kind"] == "harmless_sdk_launch_qualification_v1", "Fixture protocol role")
    need(protocol["worker_sha256"] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "Fixture source differs")
    need(Path(sys.executable).resolve() == BASE and Path(sys._base_executable).resolve() == BASE,
         "Fixture executable differs")
    output = safe(out_arg)
    parent_output = safe(protocol["output"])
    need(output.is_relative_to(parent_output) and output.resolve().is_relative_to(parent_output.resolve())
         and output.is_dir(), "Fixture output differs")
    rows = [row for row in protocol["cases"] if row["worker_mode"] == mode and safe(row["child_output"]) == output]
    need(len(rows) == 1, "Fixture case not uniquely protocol-bound")
    identity = dict(pid=os.getpid(), executable=str(Path(sys.executable).resolve()),
                    protocol_sha256=expected, mode=mode, parent_pid=None,
                    parent_pid_reason="Not queried by fixture; parent owns CreateProcess handles")
    publish(output / "worker-started.json", identity)
    if mode == "suspended_abort":
        # This case must be killed while still suspended; reaching here is a failure.
        raise RuntimeError("Qualification unexpectedly resumed the abort worker")
    if mode == "overflow":
        remaining = b"x" * (65536 + 8192)
        while remaining:
            written = os.write(sys.stdout.fileno(), remaining)
            need(0 < written <= len(remaining), "Fixture pipe write made no progress")
            remaining = remaining[written:]
        time.sleep(120)
        raise RuntimeError("Capture-overflow cleanup did not stop worker")
    if mode == "sleep":
        time.sleep(120)
        raise RuntimeError("Timeout cleanup did not stop worker")

    memory_rejected = False
    try:
        buffer = bytearray(384 * 1024 * 1024)
        del buffer
    except MemoryError:
        memory_rejected = True
    extra = None
    try:
        extra = subprocess.Popen([str(BASE), "-I", "-B", "-c", "raise SystemExit(0)"],
            shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW,
            env={"SystemRoot": os.environ["SystemRoot"]})
    except OSError as error:
        spawn = dict(rejected=True, error_class=type(error).__name__, winerror=error.winerror)
    else:
        try:
            extra.wait(timeout=2)
            spawn = dict(rejected=False, pid=extra.pid, exit_code=extra.returncode)
        finally:
            if extra.poll() is None:
                extra.kill()
                extra.wait(timeout=2)
    result = dict(memory_rejected=memory_rejected, descendant_spawn_attempts=1,
                  spawn=spawn, target_library_calls=0, model_calls=0, network_requests=0)
    publish(output / "worker-result.json", result)
    print(json.dumps(result, sort_keys=True), flush=True)
    need(memory_rejected and spawn["rejected"] and spawn.get("winerror") == 1816,
         "Fixture resource limits did not produce the selected quota result")


if __name__ == "__main__":
    main()
