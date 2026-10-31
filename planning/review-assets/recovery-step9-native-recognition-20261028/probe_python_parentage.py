"""Harmless stdlib worker identity probe; no HTTP, AsOf import or native target."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTPUT = ROOT / "data/cache/r09-native-python-parentage-20261028"


def main():
    assert not OUTPUT.exists() and OUTPUT.resolve().is_relative_to(ROOT)
    OUTPUT.mkdir()
    system = Path(os.environ["SystemRoot"])
    environment = dict(SystemRoot=str(system), WINDIR=str(system), SystemDrive=system.drive,
                       PATH=str(system / "System32"))
    code = """import os,sys,json
from importlib.metadata import version,PackageNotFoundError
try: package=version('asof-target-agents')
except PackageNotFoundError: package=None
print(json.dumps(dict(pid=os.getpid(),ppid=os.getppid(),executable=sys.executable,
base_executable=sys._base_executable,prefix=sys.prefix,base_prefix=sys.base_prefix,
asof_distribution_version=package,isolated=bool(sys.flags.isolated),
dont_write_bytecode=bool(sys.dont_write_bytecode))))
"""
    rows = []
    cases = [
        ("venv_launcher", sys.executable, dict(environment)),
        ("base_interpreter", sys._base_executable, dict(environment)),
        ("base_with_pinned_venv_launcher_context", sys._base_executable,
         dict(environment, __PYVENV_LAUNCHER__=sys.executable)),
    ]
    for label, executable, child_environment in cases:
        command = [executable, "-I", "-B", "-c", code]
        process = subprocess.Popen(command, cwd=ROOT, env=child_environment, shell=False,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            stdout, stderr = process.communicate(input=b"", timeout=10)
        except BaseException:
            process.kill()
            process.wait(timeout=3)
            raise
        (OUTPUT / (label + ".stdout.json")).write_bytes(stdout)
        (OUTPUT / (label + ".stderr.txt")).write_bytes(stderr)
        assert process.returncode == 0 and not stderr and len(stdout) < 4096
        child = json.loads(stdout)
        rows.append(dict(case=label, parent_pid=os.getpid(), launched_pid=process.pid,
                         worker=child, launched_pid_equals_worker=process.pid == child["pid"],
                         worker_parent_equals_owner=child["ppid"] == os.getpid(),
                         exit_code=process.returncode, launched_handle_reaped=process.poll() is not None,
                         executable_sha256=hashlib.sha256(Path(executable).read_bytes()).hexdigest()))
    record = dict(schema_version=1, at_utc=datetime.now(timezone.utc).isoformat(),
                  status="completed_parentage_observations_not_process_tree_guarantee",
                  helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  records=rows, http_requests=0, asof_code_imports=0,
                  native_target_or_model_calls=0,
                  limitation="Normal-exit identity observations do not prove forced-timeout or descendant cleanup")
    with (HERE / "PYTHON-PARENTAGE-PROBE.json").open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
