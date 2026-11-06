"""Fresh attempt02; preserve attempt01 and fix disappearing temp-tree races."""
import importlib.util
import os
from pathlib import Path
import subprocess
import time

SOURCE = Path(__file__).with_name("acquire_environment.py")
spec = importlib.util.spec_from_file_location("inspect_acquisition_base", SOURCE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def walk_error(error):
    if not isinstance(error, FileNotFoundError):
        raise error


def size_tree(path):
    total = 0
    for directory, _, names in os.walk(path, onerror=walk_error):
        for name in names:
            try:
                total += (Path(directory)/name).stat().st_size
            except FileNotFoundError:
                pass
    return total


def run(name, command, environment, timeout=900, acquisition=False):
    start = time.monotonic()
    log = base.EVIDENCE/(name+".log")
    status = {"command": command, "started_at": base.datetime.now(base.timezone.utc).isoformat(),
              "timeout_seconds": timeout, "acquisition_storage_cap_bytes": base.CAP,
              "expanded_environment_cap_bytes": 1024**3, "proxy_environment": "not inherited",
              "pip_config_file": os.devnull, "guard_sampling_seconds": 0.1}
    with log.open("xb") as output:
        process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                                   cwd=base.ROOT, env=environment)
        try:
            while True:
                observed = size_tree(base.TARGET/"wheels")+size_tree(base.TARGET/"tmp")
                expanded = size_tree(base.TARGET/"environment")
                if observed > base.CAP or expanded > 1024**3:
                    raise RuntimeError("Explicit wheel/tmp or expanded environment cap exceeded")
                if time.monotonic()-start > timeout:
                    raise TimeoutError("Environment command deadline")
                if process.poll() is not None:
                    break
                time.sleep(0.1)
            status.update(exit_code=process.returncode, final_wheel_tmp_bytes=observed,
                          final_expanded_environment_bytes=expanded)
            if process.returncode:
                raise RuntimeError("Environment command failed: "+name)
        except BaseException as exc:
            process.kill()
            process.wait(timeout=15)
            status.update(error_class=type(exc).__name__, error=str(exc), exit_code=process.returncode)
            raise
        finally:
            status["elapsed_seconds"] = time.monotonic()-start
            status["log_sha256"] = base.digest(log.read_bytes())
            base.publish(base.EVIDENCE/(name+".json"), status)


if __name__ == "__main__":
    base.TARGET = base.ROOT/"data/cache/tether-inspect-env-attempt02"
    base.EVIDENCE = Path(__file__).parent/"attempt02"
    base.EVIDENCE.mkdir(exist_ok=False)
    base.size_tree = size_tree
    base.run = run
    base.main()
