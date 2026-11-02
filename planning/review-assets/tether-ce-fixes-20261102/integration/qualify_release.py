"""Offline, fresh-path installed qualification for CE01--CE03 releases.

Prepare/help is safe while another gate builds; execution requires the parent's
explicit --execute --core-gate-terminal confirmation. No retries or old outputs
are overwritten. This is fictional software qualification, not a study.
"""
from __future__ import annotations

import argparse
import base64
import csv
from datetime import datetime, timezone
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import tomllib
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[4]
EXPECTED = {"asof-target-agents": "0.3.12", "tether-target-agents": "0.5.1"}
CONSTRAINTS = ROOT / "paper/release/build-constraints.txt"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(canonical(value) + b"\n")


def package_sources():
    result = {}
    for namespace, directory in (("asof", ROOT / "src/asof"), ("tether", ROOT / "packages/tether/src/tether")):
        paths = {p for p in directory.rglob("*.py") if "__pycache__" not in p.parts}
        if namespace == "asof":
            for pattern in ("demo/*.json", "demo/v2/*.json", "archive/*.json", "study/resources/*.json"):
                paths.update(directory.glob(pattern))
        result[namespace] = {namespace + "/" + p.relative_to(directory).as_posix(): digest(p.read_bytes())
                             for p in sorted(paths)}
    return result


class Commands:
    def __init__(self, output, environment):
        self.output, self.environment = output, environment
        self.previous, self.sequence, self.commands = None, 0, []

    def event(self, event, details):
        record = dict(sequence=self.sequence, previous_sha256=self.previous,
                      utc=datetime.now(timezone.utc).isoformat(), event=event, details=details)
        record["sha256"] = digest(canonical(record))
        with (self.output / "journal.jsonl").open("ab") as stream:
            stream.write(canonical(record) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.previous, self.sequence = record["sha256"], self.sequence + 1

    def run(self, label, arguments, *, cwd=None, expected=0, timeout=180):
        stem = f"{len(self.commands) + 1:02d}-{label}"
        logdir = self.output / "commands"
        logdir.mkdir(exist_ok=True)
        stdout, stderr = logdir / (stem + ".stdout.txt"), logdir / (stem + ".stderr.txt")
        arguments = [str(x) for x in arguments]
        record = dict(label=label, argv=arguments, cwd=str(cwd or self.output), expected_exit=expected,
                      timeout_seconds=timeout, stdout=str(stdout), stderr=str(stderr))
        self.event("command_reserved", record)
        started = time.monotonic()
        try:
            with stdout.open("xb") as out, stderr.open("xb") as err:
                completed = subprocess.run(arguments, cwd=cwd or self.output, env=self.environment,
                    stdout=out, stderr=err, timeout=timeout)
            record.update(exit_code=completed.returncode, seconds=time.monotonic() - started,
                          stdout_sha256=digest(stdout.read_bytes()), stderr_sha256=digest(stderr.read_bytes()))
            self.commands.append(record)
            self.event("command_returned", record)
            if completed.returncode != expected:
                raise RuntimeError(f"{label} exited {completed.returncode}, expected {expected}; see {stderr}")
            return stdout
        except BaseException as error:
            self.event("command_failed", dict(label=label, error_class=type(error).__name__,
                message=str(error), seconds=time.monotonic() - started,
                recovery="Inspect retained logs/process state; never automatically repeat this output."))
            raise


def check_wheel(path, namespace, expected_source):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)), "Duplicate wheel members"
        assert all(not n.startswith("/") and ".." not in n.split("/") for n in names), "Unsafe wheel path"
        actual = {n: digest(archive.read(n)) for n in names if n.startswith(namespace + "/")}
        assert actual == expected_source, f"{namespace} wheel/source inventory or bytes differ"
        record_name = next(n for n in names if n.endswith(".dist-info/RECORD"))
        records = list(csv.reader(io.StringIO(archive.read(record_name).decode())))
        assert len(records) == len(names) and {r[0] for r in records} == set(names), "Wheel RECORD closure differs"
        for name, encoded, size in records:
            if name == record_name:
                assert encoded == size == ""
            else:
                raw = archive.read(name)
                wanted = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode()
                assert encoded == wanted and int(size) == len(raw), f"Wheel RECORD differs: {name}"
        metadata = BytesParser().parsebytes(archive.read(next(n for n in names if n.endswith(".dist-info/METADATA"))))
        assert EXPECTED[metadata["Name"]] == metadata["Version"], "Wheel metadata version differs"
        dependencies = metadata.get_all("Requires-Dist", [])
        if namespace == "tether":
            assert "asof-target-agents==0.3.12" in dependencies, "Unpinned compatibility dependency"
    return dict(path=str(path), sha256=digest(path.read_bytes()), bytes=path.stat().st_size,
                package_members=len(actual), source_sha256=actual, record_verified=True,
                distribution=metadata["Name"], version=metadata["Version"], requires_dist=dependencies)


INSTALLED_PROBE = '''import hashlib, importlib.metadata, json, pathlib, sys
import asof, tether
manifest = json.loads(pathlib.Path(sys.argv[1]).read_bytes())
environment = pathlib.Path(sys.argv[2]).resolve()
assert sys.flags.isolated == 1
assert pathlib.Path(sys.executable).resolve().is_relative_to(environment)
result = {"python": sys.version, "executable": sys.executable, "isolated": sys.flags.isolated,
          "sys_path": sys.path, "packages": {}}
for name, module, distribution in (("asof", asof, "asof-target-agents"), ("tether", tether, "tether-target-agents")):
    root = pathlib.Path(module.__file__).resolve().parent
    assert root.is_relative_to(environment) and "site-packages" in root.parts
    observed = {name+"/"+p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.rglob("*") if p.is_file() and p.suffix in (".py", ".json") and "__pycache__" not in p.parts}
    assert observed == manifest["sources"][name], (name, "installed inventory/bytes differ")
    version = importlib.metadata.version(distribution)
    assert version == manifest["versions"][distribution] == module.__version__
    result["packages"][name] = {"root": str(root), "version": version, "source_sha256": observed}
print(json.dumps(result, indent=2))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--core-gate-terminal", action="store_true")
    args = parser.parse_args()
    if not args.execute or not args.core_gate_terminal:
        parser.error("Build is gated: explicitly supply --execute --core-gate-terminal after parent confirmation")
    output = args.output.absolute().resolve()
    cache = (ROOT / "data/cache").resolve()
    if not output.is_relative_to(cache) or output == cache:
        parser.error("Choose a new qualification leaf under project data/cache")
    output.mkdir(parents=True, exist_ok=False)
    temporary = output / "temp"
    temporary.mkdir()
    environment = dict(os.environ, TMP=str(temporary), TEMP=str(temporary), PYTHONDONTWRITEBYTECODE="1",
                       UV_OFFLINE="true", UV_PYTHON_DOWNLOADS="never", UV_NO_PROGRESS="1")
    commands = Commands(output, environment)
    try:
        sources = package_sources()
        build_inputs = {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p.read_bytes()) for p in
                        (ROOT / "pyproject.toml", ROOT / "packages/tether/pyproject.toml", CONSTRAINTS)}
        for path in (ROOT / "pyproject.toml", ROOT / "packages/tether/pyproject.toml"):
            project = tomllib.loads(path.read_text(encoding="utf-8"))["project"]
            assert EXPECTED[project["name"]] == project["version"]
        manifest = dict(versions=EXPECTED, sources=sources, build_inputs=build_inputs,
                        qualifier_sha256=digest(Path(__file__).read_bytes()))
        save(output / "source-manifest.json", manifest)
        commands.event("qualification_started", dict(manifest_sha256=digest((output / "source-manifest.json").read_bytes()),
            parent_core_gate_terminal_confirmed=True, scope="Offline installed software qualification; fictional inputs only"))
        uv = shutil.which("uv")
        assert uv, "uv is unavailable"
        commands.run("uv-version", [uv, "--version"], timeout=15)
        wheels = output / "wheels"
        wheels.mkdir()
        for name, directory in (("core", ROOT), ("facade", ROOT / "packages/tether")):
            commands.run("build-" + name, [uv, "build", "--offline", "--build-constraints", CONSTRAINTS,
                "--python", sys.executable, "--wheel", "--out-dir", wheels], cwd=directory, timeout=300)
        core = wheels / "asof_target_agents-0.3.12-py3-none-any.whl"
        facade = wheels / "tether_target_agents-0.5.1-py3-none-any.whl"
        wheel_proofs = [check_wheel(path, namespace, sources[namespace])
                        for path, namespace in ((core, "asof"), (facade, "tether"))]
        save(output / "wheel-proofs.json", wheel_proofs)
        installed = output / "environment"
        commands.run("create-environment", [uv, "venv", "--offline", "--python", sys.executable, installed])
        python = installed / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        commands.run("install-wheels", [uv, "pip", "install", "--offline", "--no-index", "--no-deps",
                                       "--python", python, core, facade])
        probe = output / "inspect-installed.py"
        with probe.open("x", encoding="utf-8") as stream:
            stream.write(INSTALLED_PROBE)
        installed_proof = commands.run("installed-source-proof", [python, "-I", "-B", probe,
                                       output / "source-manifest.json", installed])
        inspection = json.loads(installed_proof.read_bytes())
        version = commands.run("tether-version", [python, "-I", "-B", "-m", "tether", "--version"], timeout=15)
        assert version.read_text().strip() == "TETHER 0.5.1 (compatibility engine 0.3.12)"
        results = {}
        for module in ("asof", "tether"):
            run = output / (module + "-demo")
            arguments = [python, "-I", "-B", "-m", module, "demo", "--output", run]
            if module == "tether":
                arguments += ["--process-timeout-seconds", "60", "--process-output-bytes", "1048576"]
            commands.run(module + "-demo", arguments)
            receipt = run / ("tether-receipt.json" if module == "tether" else "receipt.json")
            anchor = digest(receipt.read_bytes())
            verified = commands.run(module + "-verify", [python, "-I", "-B", "-m", module,
                "verify", "--run-dir", run, "--receipt-sha256", anchor])
            result = json.loads(verified.read_bytes())
            engine = result["engine"] if module == "tether" else result
            assert result["status"] == "integrity_verified" and result["external_anchor_checked"]
            assert engine["semantic_consistency"] == "verified" and engine["code_matches_current"]
            assert engine["source_binding"] == "current_originals"
            results[module + "_demo"] = result

        # Fixture production may import checkout code. Every task/verification
        # CHILD above and below uses fresh installed Python in isolated mode.
        sys.path[:0] = [str(ROOT / "src"), str(ROOT / "packages/tether/src"), str(ROOT / "packages/tether/tests")]
        import test_catalog_binding as fixtures
        import test_ce03_receipt_time as receipt_fixtures
        producer = {str(Path(m.__file__).relative_to(ROOT)).replace("\\", "/"): digest(Path(m.__file__).read_bytes())
                    for m in (fixtures, receipt_fixtures)}
        save(output / "fixture-producer-pins.json", producer)
        for bad in (False, True):
            leaf = output / ("policy-invalid-unused" if bad else "policy-valid")
            leaf.mkdir()
            fixture = fixtures.make_fixture(leaf)
            receipt_fixtures.add_raw(fixture, used=False,
                completed="2024-01-01T00:00:00+00:00" if bad else "2022-01-01T00:00:00+00:00")
            run = leaf / "outer"
            commands.run("policy-invalid" if bad else "policy-valid", [python, "-I", "-B", "-m", "tether",
                *fixtures.argv(fixture, run), "--process-timeout-seconds", "60", "--process-output-bytes", "1048576"],
                expected=2 if bad else 0)
            if bad:
                diagnostic = Path(commands.commands[-1]["stderr"]).read_text(encoding="utf-8")
                assert "Contemporary availability bound does not match public-download receipt" in diagnostic
                failed = json.loads((run / "tether-failure.json").read_bytes())
                events = [json.loads(line) for line in (run / "attempt/journal.jsonl").read_bytes().splitlines()]
                assert failed["stage"] == "artifact_policy_preflight" and failed["status"] == "failed"
                assert not any(e["event"] == "engine_dispatch" for e in events)
                assert not (run / "engine").exists() and not (run / "tether-receipt.json").exists()
                results["invalid_unused"] = dict(failure=failed, events=[e["event"] for e in events],
                                                  backend_dispatches=0, expected_rejection=True)
            else:
                anchor = digest((run / "tether-receipt.json").read_bytes())
                verified = commands.run("policy-source-verify", [python, "-I", "-B", "-m", "tether", "verify",
                    "--run-dir", run, "--receipt-sha256", anchor])
                result = json.loads(verified.read_bytes())
                assert result["external_anchor_checked"] and result["engine"]["semantic_consistency"] == "verified"
                assert result["engine"]["code_matches_current"] and result["engine"]["source_binding"] == "current_originals"
                assert result["artifact_policy"]["checked_inputs"] == 4
                assert result["artifact_policy"]["status"] == "artifact_policy_consistency_verified"
                results["valid_policy"] = result
        assert sources == package_sources(), "Checkout package sources changed during qualification"
        assert digest(Path(__file__).read_bytes()) == manifest["qualifier_sha256"], "Qualifier changed during execution"
        for relative, pin in build_inputs.items():
            assert digest((ROOT / relative).read_bytes()) == pin, "Build input changed during qualification"
        commands.event("qualification_completed", dict(versions=EXPECTED, scientific_validation="not_established"))
        save(output / "QUALIFICATION.json", dict(status="PASS", versions=EXPECTED, wheel_proofs=wheel_proofs,
            installed=inspection, results=results, commands=commands.commands, source_manifest=manifest,
            journal_sha256=digest((output / "journal.jsonl").read_bytes()),
            limits="Windows/local offline software qualification; no benchmark, model, clinical or biological validation."))
        print(json.dumps(dict(status="PASS", output=str(output),
                             qualification_sha256=digest((output / "QUALIFICATION.json").read_bytes())), indent=2))
        return 0
    except BaseException as error:
        commands.event("qualification_failed", dict(error_class=type(error).__name__, message=str(error)))
        save(output / "FAILURE.json", dict(status="FAILED", error_class=type(error).__name__, message=str(error),
            traceback=traceback.format_exc(), commands=commands.commands,
            recovery="Inspect this retained attempt and any process state; no automatic retry or output reuse."))
        raise


if __name__ == "__main__":
    sys.exit(main())
