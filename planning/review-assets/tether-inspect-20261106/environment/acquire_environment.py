"""Bounded public-wheel acquisition into a new isolated Inspect environment."""
from datetime import datetime, timezone
import email
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT/"data/cache/tether-inspect-env-attempt01"
EVIDENCE = Path(__file__).resolve().parent
CAP = 512*1024**2


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def publish(path, value):
    with Path(path).open("xb") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True).encode()+b"\n")


def size_tree(path):
    total = 0
    for file in path.rglob("*"):
        try:
            if file.is_file():
                total += file.stat().st_size
        except FileNotFoundError:
            pass
    return total


def run(name, command, environment, timeout=900, acquisition=False):
    start = time.monotonic()
    log = EVIDENCE/(name+".log")
    status = {"command": command, "started_at": datetime.now(timezone.utc).isoformat(),
              "timeout_seconds": timeout, "acquisition_storage_cap_bytes": CAP if acquisition else None,
              "proxy_environment": "not inherited", "pip_config_file": os.devnull}
    with log.open("xb") as output:
        process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT, cwd=ROOT, env=environment)
        try:
            while process.poll() is None:
                if time.monotonic()-start > timeout:
                    raise TimeoutError("Environment command deadline")
                # Pip uses binary wheels only: no source builders/subprocesses.
                observed = size_tree(TARGET/"wheels")+size_tree(TARGET/"tmp")
                if acquisition and observed > CAP:
                    raise RuntimeError("Acquisition working storage exceeded 512 MiB cap")
                time.sleep(0.1)
            status["exit_code"] = process.returncode
            if process.returncode:
                raise RuntimeError("Environment command failed: "+name)
        except BaseException as exc:
            process.kill()
            process.wait(timeout=15)
            status.update(error_class=type(exc).__name__, error=str(exc), exit_code=process.returncode)
            raise
        finally:
            status["elapsed_seconds"] = time.monotonic()-start
            status["log_sha256"] = digest(log.read_bytes())
            publish(EVIDENCE/(name+".json"), status)


def main():
    TARGET.mkdir(parents=True, exist_ok=False)
    for name in ("wheels", "tmp", "metadata"):
        (TARGET/name).mkdir()
    env = {k: v for k, v in os.environ.items() if k.upper() in
           {"SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "PATH", "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS"}}
    env.update(TEMP=str(TARGET/"tmp"), TMP=str(TARGET/"tmp"), PIP_CONFIG_FILE=os.devnull,
               PIP_DISABLE_PIP_VERSION_CHECK="1", PYTHONNOUSERSITE="1")
    publish(EVIDENCE/"ACQUISITION-START.json", {"started_at": datetime.now(timezone.utc).isoformat(),
        "base_python": sys.executable, "base_python_version": sys.version, "target": str(TARGET),
        "inspect_version": "0.3.287", "package_index": "https://pypi.org/simple", "retries": 0,
        "acquisition_cap_bytes": CAP, "cap_basis": "Sampled retained wheel plus pip temporary-file logical bytes; wire transfer unknown",
        "environment_keys": sorted(env), "provider_calls": 0, "model_weight_downloads": 0})
    try:
        run("01-create-venv", [sys.executable, "-I", "-B", "-m", "venv", str(TARGET/"environment")], env, 120)
        python = str(TARGET/"environment/Scripts/python.exe")
        run("02-download-wheels", [python, "-I", "-B", "-m", "pip", "--isolated", "--disable-pip-version-check",
            "--no-input", "--no-cache-dir", "download", "--index-url", "https://pypi.org/simple",
            "--only-binary=:all:", "--retries", "0", "--timeout", "30", "--dest", str(TARGET/"wheels"),
            "inspect-ai==0.3.287"], env, 1200, True)
        wheels = []
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for path in sorted((TARGET/"wheels").glob("*.whl")):
            raw = path.read_bytes()
            with zipfile.ZipFile(path) as archive:
                metadata = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
                if len(metadata) != 1:
                    raise ValueError("Ambiguous wheel metadata")
                parsed = email.message_from_bytes(archive.read(metadata[0]))
                name, version = parsed["Name"], parsed["Version"]
            url = "https://pypi.org/pypi/"+name+"/"+version+"/json"
            with opener.open(url, timeout=30) as response:
                body = response.read(2*1024**2+1)
            if len(body) > 2*1024**2:
                raise ValueError("PyPI metadata body limit")
            catalog = json.loads(body)
            matching = [record for record in catalog["urls"] if record["filename"] == path.name]
            if len(matching) != 1 or matching[0]["digests"]["sha256"] != digest(raw) or matching[0]["size"] != len(raw):
                raise ValueError("Wheel differs from official PyPI record")
            metadata_path = TARGET/"metadata"/(name+"-"+version+".json")
            with metadata_path.open("xb") as stream:
                stream.write(body)
            wheels.append({"name": name, "version": version, "filename": path.name, "bytes": len(raw),
                "sha256": digest(raw), "url": matching[0]["url"], "upload_time": matching[0]["upload_time_iso_8601"],
                "metadata_sha256": digest(body), "metadata_path": str(metadata_path.relative_to(TARGET)).replace("\\", "/"),
                "requires_python": parsed["Requires-Python"], "requires_dist": parsed.get_all("Requires-Dist", [])})
        lock = "\n".join(item["name"]+"=="+item["version"]+" --hash=sha256:"+item["sha256"] for item in wheels)+"\n"
        (EVIDENCE/"requirements-lock.txt").write_text(lock, encoding="utf-8")
        publish(EVIDENCE/"WHEELS.json", {"kind": "official_pypi_wheel_inventory", "wheels": wheels,
            "wheel_count": len(wheels), "total_wheel_bytes": sum(i["bytes"] for i in wheels),
            "verified_at": datetime.now(timezone.utc).isoformat(), "wire_transfer_bytes": None,
            "wire_transfer_reason": "Pip metadata/resolver traffic and transport overhead were not instrumented"})
        run("03-offline-install", [python, "-I", "-B", "-m", "pip", "--isolated", "--disable-pip-version-check",
            "--no-input", "--no-cache-dir", "install", "--no-index", "--find-links", str(TARGET/"wheels"),
            "--require-hashes", "--no-compile", "-r", str(EVIDENCE/"requirements-lock.txt")], env, 600)
        run("04-pip-check", [python, "-I", "-B", "-m", "pip", "--isolated", "check"], env, 60)
        publish(EVIDENCE/"ACQUISITION-COMPLETE.json", {"status": "complete", "python": python,
            "inspect_version": "0.3.287", "wheel_count": len(wheels), "total_wheel_bytes": sum(i["bytes"] for i in wheels),
            "finished_at": datetime.now(timezone.utc).isoformat(), "mock_eval_qualification": "pending"})
        print(json.dumps({"status": "complete", "python": python, "wheels": len(wheels)}))
    except BaseException as exc:
        publish(EVIDENCE/"FAILED.json", {"status": "failed", "error_class": type(exc).__name__, "message": str(exc),
            "at": datetime.now(timezone.utc).isoformat(), "automatic_retry": False})
        raise


if __name__ == "__main__":
    main()
