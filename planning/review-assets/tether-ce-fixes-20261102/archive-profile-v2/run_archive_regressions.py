"""Qualify the second unpublished candidate profile and fictional old-run controls.

This is a fresh attempt after the bounded Windows atomic-replace correction.
Prior profile records and qualifications remain unchanged.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def profile():
    prepared = json.loads((HERE / "PREPARED.json").read_bytes())
    active = ROOT / prepared["active_resource"]
    assert active.read_bytes() == (ROOT / prepared["candidate"]).read_bytes(), "Reviewed second candidate is not active"
    assert sha(active) == prepared["new_resource_sha256"]
    document = json.loads(active.read_bytes())
    previous = ROOT / prepared["old_copy"]
    assert sha(previous) == prepared["old_resource_sha256"]
    assert document["previous_resource_sha256"] == prepared["old_resource_sha256"]
    prior = json.loads(previous.read_bytes())
    assert set(prior["modules"]) == set(document["modules"])
    assert {name for name in prior["modules"] if prior["modules"][name] != document["modules"][name]} == {"serde.py"}
    assert document["policy"] == prior["policy"]
    for name, expected in document["modules"].items():
        assert sha(ROOT / "src/asof" / name) == expected, name
    return prepared, document


def produce_old(work):
    import asof
    from asof.artifacts import verify_run, write_run
    from asof.chrono import load_snapshot
    from asof.contracts import Case
    from asof.journal import RunJournal
    from asof.local_model import LocalSelectionBackend
    from asof.serde import canonical, decode, encode, read_json, write_json
    from asof.workflow import Budget, run_workflow
    assert asof.__version__ == "0.3.11"
    work.mkdir(parents=True, exist_ok=False)
    fixture = ROOT / "src/asof/demo/v2"
    entries = []
    class Fake:
        def __init__(self, kind):
            self.kind, self.calls = kind, 0
        def open(self, request, timeout):
            self.calls += 1
            if self.kind == "unknown-timeout":
                raise TimeoutError("Fictional old archive control")
            shape = json.loads(request.data)["json_schema"]["properties"]["observation_ids"]
            return io.BytesIO(canonical(dict(truncated=False,
                content=json.dumps(dict(observation_ids=shape["items"]["enum"][:1])),
                tokens_evaluated=1_000_000 if self.kind == "invalid-overquote" else 50, tokens_predicted=1)))
    for kind in ("normal", "unknown-timeout", "invalid-overquote"):
        folder = work / kind
        folder.mkdir()
        config = folder / "config.json"
        write_json(config, dict(schema_version=1, endpoint="http://127.0.0.1:55580", model_id="fictional-profile-control",
            model_provenance=dict(weights_sha256={"fictional": "a" * 64}, runtime_sha256="b" * 64),
            retrieval=dict(max_records=12, max_request_bytes=12000), max_output_tokens=256, timeout_seconds=1, seed=42))
        backend = LocalSelectionBackend(config); backend.opener = Fake(kind)
        case = decode(Case, read_json(fixture / "case.json"))
        store = load_snapshot(fixture / "snapshot.json", case)
        output = folder / "run"
        journal = RunJournal(output)
        try:
            result = run_workflow(case, store, backend, budget=Budget(max_input_tokens=200000, max_retries=3), journal=journal)
            write_json(output / "backend-execution.json", dict(schema_version=1, attempts=backend.records))
            anchor = write_run(output, result, store, None, journal)
        finally:
            journal.close()
        old_verified = verify_run(output, anchor)
        assert old_verified["semantic_consistency"] == "verified"
        entries.append(dict(kind=kind, output=str(output), receipt_sha256=anchor, calls=result.calls,
                            measured=encode(result.measured_usage), estimated=encode(result.estimated_usage), old_verification=old_verified))
    save(work / "manifest.json", dict(engine_version=asof.__version__, code_root=str(Path(asof.__file__).parent),
                                      fixture=str(fixture), runs=entries))
    print(json.dumps(dict(status="created", cases=len(entries), engine=asof.__version__)))


def relocated_controls(work, manifest):
    from asof.archive.core import verify_core_archive
    from asof.archive.paths import ArchiveResolver
    from asof.serde import ContractError
    results = []
    for run in manifest["runs"]:
        original = Path(run["output"])
        receipt = json.loads((original / "receipt.json").read_bytes())
        code_root = Path(manifest["code_root"])
        inputs = set(original.glob("*"))
        inputs.update(Path(manifest["fixture"]).glob("*.json"))
        inputs.update(code_root / relative for relative in receipt["code"])
        restored = work / ("relocated-" + run["kind"])
        restored.mkdir()
        files = []
        for path in sorted(inputs):
            if not path.is_file():
                continue
            assert path.is_relative_to(ROOT)
            relative = path.relative_to(ROOT)
            destination = restored / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            files.append(dict(logical_path=str(path), root_id="project", relative_path=relative.as_posix(),
                              sha256=sha(destination), bytes=destination.stat().st_size))
        resolver = ArchiveResolver([dict(root_id="project", logical_root=str(ROOT), physical_root=str(restored))], files)
        expected = "rejected" if run["kind"] == "invalid-overquote" else "verified"
        try:
            verified = verify_core_archive(str(original), resolver, run["receipt_sha256"], code_root=str(code_root))
            assert verified["semantic_consistency"] == "verified" and verified["archived_code_executed"] is False
            actual = dict(disposition="verified", verification=verified)
        except ContractError as error:
            actual = dict(disposition="rejected", error=str(error))
        assert actual["disposition"] == expected, (run["kind"], actual)
        if expected == "rejected":
            assert "lost its validated usage" in actual["error"], actual
        results.append(dict(kind=run["kind"], expected=expected, **actual))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--produce-old", action="store_true")
    parser.add_argument("--old-python", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    work = args.work.absolute()
    if args.produce_old:
        produce_old(work)
        return 0
    if not args.old_python or not args.output:
        parser.error("--old-python and --output are required for qualification")
    if args.output.exists():
        parser.error("Choose a fresh output file")
    prepared, document = profile()  # Fail before importing the guarded archive modules.
    work.mkdir(parents=True, exist_ok=False)
    temporary = work / "temp"; temporary.mkdir()
    os.environ["TEMP"] = os.environ["TMP"] = str(temporary)
    tempfile.tempdir = str(temporary)
    sys.path.insert(0, str(ROOT))
    record = dict(status="FAILED", scope="Archive regression and relocated fictional old-run verification; no model/network/benchmark execution",
                  profile_sha256=prepared["new_resource_sha256"], modules=document["modules"],
                  script_sha256=sha(__file__), work=str(work))
    try:
        import asof
        assert asof.__version__ == "0.3.12"
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_archive*.py", top_level_dir=str(ROOT))
        with (work / "tests.log").open("x", encoding="utf-8") as stream:
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        record["tests"] = dict(run=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped))
        record["tests_log_sha256"] = sha(work / "tests.log")
        assert result.testsRun > 0 and result.wasSuccessful() and not result.skipped, record["tests"]
        command = [str(args.old_python.resolve()), "-I", str(Path(__file__)), "--produce-old", "--work", str(work / "old")]
        with (work / "old.stdout.log").open("xb") as out, (work / "old.stderr.log").open("xb") as err:
            process = subprocess.run(command, stdout=out, stderr=err, timeout=120, cwd=work)
        record["old_producer"] = dict(argv=command, exit_code=process.returncode,
            stdout_sha256=sha(work / "old.stdout.log"), stderr_sha256=sha(work / "old.stderr.log"))
        assert process.returncode == 0, "Old producer failed; inspect retained logs"
        manifest = json.loads((work / "old/manifest.json").read_bytes())
        record["old_manifest_sha256"] = sha(work / "old/manifest.json")
        record["relocated_controls"] = relocated_controls(work, manifest)
        profile()
        record["status"] = "PASS"
    except Exception as error:
        record["error"] = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc())
    record["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    save(args.output, record)
    print(json.dumps(record, indent=2))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
