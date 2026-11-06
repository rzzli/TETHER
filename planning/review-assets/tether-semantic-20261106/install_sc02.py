"""Create an isolated, offline runtime from the completed bounded acquisition.

The invocation never changes an existing environment and never downloads wheels.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "planning/review-assets/tether-semantic-20261106"
UV = Path("C:/Users/zzric/.local/bin/uv.exe")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pin(path):
    path = Path(path).resolve(strict=True)
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            count += len(chunk)
    return {"path": str(path), "sha256": digest.hexdigest(), "bytes": count}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def command(output, name, argv, env, timeout):
    record = {"argv": argv, "cwd": str(ROOT), "timeout_seconds": timeout,
              "started_at_utc": datetime.now(timezone.utc).isoformat()}
    write(output / (name + "-COMMAND.json"), record)
    started = time.perf_counter()
    result = {"status": "FAIL"}
    with (output / (name + "-stdout.txt")).open("xb") as stdout, (output / (name + "-stderr.txt")).open("xb") as stderr:
        try:
            process = subprocess.run(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, timeout=timeout)
            result.update(returncode=process.returncode, status="PASS" if process.returncode == 0 else "FAIL")
        except BaseException as error:
            result.update(error_type=type(error).__name__, error=str(error))
        finally:
            result.update(elapsed_seconds=time.perf_counter() - started, completed_at_utc=datetime.now(timezone.utc).isoformat())
            write(output / (name + "-RESULT.json"), result)
    need(result["status"] == "PASS", f"{name} failed; retained logs; no retry")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--acquisition", type=Path, required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    acquisition = args.acquisition.resolve(strict=True)
    receipt_path = acquisition / "RECEIPT.json"
    need(pin(receipt_path)["sha256"] == args.receipt_sha256, "Acquisition receipt identity")
    receipt = read(receipt_path)
    manifest_path = ASSETS / "solver-feasibility/acquisition-manifest.json"
    manifest_pin = pin(manifest_path)
    need(receipt["status"] == "PASS" and receipt["manifest_sha256"] == manifest_pin["sha256"], "Complete acquisition")
    manifest = read(manifest_path)
    observed = {entry["relative_path"]: entry for entry in receipt["files"]}
    directories = {"wheel": "wheel", "checkpoint": "checkpoint", "tokenizer_config": "tokenizer"}
    expected = {f"{directories[entry['kind']]}/{entry['logical_id']}": entry for entry in manifest["assets"]}
    need(len(observed) == len(receipt["files"]) == len(expected) == 30 and set(observed) == set(expected), "Exact assets")
    verified = []
    for name, specification in expected.items():
        actual = pin(acquisition / name)
        declared = observed[name]
        need(Path(actual["path"]) == Path(declared["path"]).resolve(), "Receipt path")
        need(actual["sha256"] == declared["sha256"], "Receipt content identity")
        need(actual["bytes"] == declared["bytes"] == specification["expected_bytes"], "Asset byte count")
        if specification.get("expected_sha256"):
            need(actual["sha256"] == specification["expected_sha256"], "Published content identity")
        verified.append(actual)
    output = args.output.resolve()
    need(ROOT / "data/cache" in output.parents and not output.exists(), "New workspace runtime path required")
    output.mkdir(parents=True, exist_ok=False)
    temp = output / "temp"
    temp.mkdir()
    environment = output / "environment"
    env = dict(os.environ, TEMP=str(temp), TMP=str(temp), UV_OFFLINE="1", UV_NO_CONFIG="1",
               UV_PYTHON_DOWNLOADS="never", UV_NO_PROGRESS="1", UV_CACHE_DIR=str(output / "cache"),
               PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1", HF_HUB_OFFLINE="1",
               TRANSFORMERS_OFFLINE="1", HF_DATASETS_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")
    requirements = ASSETS / "solver-feasibility/requirements.lock.txt"
    dependency_lock = ASSETS / "solver-feasibility/dependency-lock.json"
    locked_packages = read(dependency_lock)["packages"]
    freeze = {"status": "FROZEN", "acquisition_receipt": pin(receipt_path), "manifest": manifest_pin,
              "verified_assets": verified, "requirements": pin(requirements), "uv": pin(UV),
              "dependency_lock": pin(dependency_lock),
              "parent_interpreter": pin(sys.executable), "installer": pin(__file__),
              "environment": str(environment), "provider_spend_usd": 0}
    write(output / "FROZEN.json", freeze)
    try:
        command(output, "CREATE", [str(UV), "venv", "--python", sys.executable, "--offline", "--no-config",
                "--no-python-downloads", "--no-project", str(environment)], env, 180)
        interpreter = environment / "Scripts/python.exe"
        command(output, "INSTALL", [str(UV), "pip", "install", "--python", str(interpreter), "--offline",
                "--no-config", "--no-python-downloads", "--no-index", "--require-hashes", "--no-build",
                "--strict", "--link-mode", "copy", "--find-links", str(acquisition / "wheel"),
                "-r", str(requirements)], env, 1800)
        command(output, "CHECK", [str(UV), "pip", "check", "--python", str(interpreter),
                "--offline", "--no-config", "--no-python-downloads"], env, 120)
        command(output, "INVENTORY", [str(UV), "pip", "list", "--python", str(interpreter),
                "--format", "json", "--offline", "--no-config", "--no-python-downloads"], env, 120)
        inventory = read(output / "INVENTORY-stdout.txt")
        normalize = lambda name: re.sub(r"[-_.]+", "-", name).lower()
        installed_versions = {normalize(row["name"]): row["version"] for row in inventory}
        expected_versions = {normalize(row["name"]): row["version"] for row in locked_packages}
        need(len(inventory) == len(installed_versions) == len(locked_packages) == len(expected_versions) == 25,
             "Installed package count and uniqueness")
        need(installed_versions == expected_versions, "Exact installed name/version inventory")
        need(pin(requirements) == freeze["requirements"] and pin(manifest_path) == manifest_pin, "Stable lock")
        need(pin(dependency_lock) == freeze["dependency_lock"], "Stable dependency metadata")
        write(output / "INSTALL-RECEIPT.json", {"status": "PASS", "scope": "Offline dependency installation only; inference remains unqualified.",
              "interpreter": pin(interpreter), "inventory": inventory, "freeze": pin(output / "FROZEN.json"),
              "completed_at_utc": datetime.now(timezone.utc).isoformat(), "provider_spend_usd": 0})
        print(json.dumps({"status": "PASS", "installation_receipt": pin(output / "INSTALL-RECEIPT.json")}))
    except BaseException as error:
        write(output / "FAILED.json", {"status": "FAIL", "error_type": type(error).__name__, "error": str(error),
                                      "completed_at_utc": datetime.now(timezone.utc).isoformat(), "automatic_retry": False})
        raise


if __name__ == "__main__":
    main()
