"""Read-only installed-file qualification and a canned, network-denied Inspect eval."""
import base64
import csv
from datetime import datetime, timezone
import ensurepip
import hashlib
import importlib.metadata as metadata
import inspect
import io
import json
import os
from pathlib import Path
import shutil
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT/"data/cache/tether-inspect-env-attempt02"
EVIDENCE = Path(__file__).parent/"attempt02"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    with Path(path).open("xb") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2).encode()+b"\n")


def main():
    started = time.monotonic()
    assert Path(sys.prefix).resolve() == (TARGET/"environment").resolve()
    assert metadata.version("inspect-ai") == "0.3.287"
    assert metadata.version("asof-target-agents") == "0.3.13"
    assert metadata.version("tether-target-agents") == "0.5.2"
    record_root = TARGET/"installed-metadata"
    record_root.mkdir(exist_ok=False)
    all_files, distributions, unchecked = [], [], []
    for dist in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
        name, version = dist.metadata["Name"], dist.version
        destination = record_root/(name+"-"+version)
        destination.mkdir()
        record = dist.read_text("RECORD")
        assert record is not None, "Missing installed RECORD"
        record_bytes = record.encode("utf-8")
        (destination/"RECORD").write_bytes(record_bytes)
        package_metadata = dist.read_text("METADATA")
        (destination/"METADATA").write_text(package_metadata, encoding="utf-8")
        checked = 0
        for relative, expected, expected_size in csv.reader(io.StringIO(record)):
            path = Path(dist.locate_file(relative)).resolve()
            assert path.is_relative_to(Path(sys.prefix).resolve()), "Installed path escapes environment"
            raw = path.read_bytes()
            if expected:
                algorithm, encoded = expected.split("=", 1)
                calculated = base64.urlsafe_b64encode(hashlib.new(algorithm, raw).digest()).decode().rstrip("=")
                assert calculated == encoded and (not expected_size or len(raw) == int(expected_size)), "RECORD mismatch"
                checked += 1
            else:
                unchecked.append({"distribution": name, "path": path.relative_to(Path(sys.prefix)).as_posix(),
                                  "reason": "Installed RECORD has no expected content digest"})
            all_files.append({"distribution": name, "version": version,
                "path": path.relative_to(Path(sys.prefix)).as_posix(), "sha256": sha(raw), "bytes": len(raw),
                "record_expected_digest": expected or None})
        distributions.append({"name": name, "version": version, "record_sha256": sha(record_bytes),
                              "record_verified_files": checked, "metadata_sha256": sha(package_metadata.encode())})
    write(TARGET/"INSTALLED-FILES.json", {"files": all_files, "unchecked_RECORD_entries": unchecked})
    write(EVIDENCE/"DISTRIBUTIONS.json", {"distributions": distributions, "count": len(distributions),
        "record_verified_files": sum(d["record_verified_files"] for d in distributions),
        "unchecked_record_count": len(unchecked), "inventory_sha256": sha((TARGET/"INSTALLED-FILES.json").read_bytes())})
    # Retain original CPython bootstrap wheels separately from PyPI dependencies.
    bootstrap = TARGET/"bootstrap-wheels"
    bootstrap.mkdir()
    bootstrap_proofs = []
    for path in sorted((Path(ensurepip.__file__).parent/"_bundled").glob("*.whl")):
        raw = path.read_bytes()
        (bootstrap/path.name).write_bytes(raw)
        bootstrap_proofs.append({"filename": path.name, "bytes": len(raw), "sha256": sha(raw),
                                 "source": str(path), "basis": "CPython ensurepip bundled original"})
    write(EVIDENCE/"BOOTSTRAP-WHEELS.json", {"wheels": bootstrap_proofs})
    # Compare project source payloads to both exact wheels and old qualified env.
    project_sources = []
    old = ROOT/"data/cache/tether-scifact-env-attempt02/environment/Lib/site-packages"
    installed = Path(sys.prefix)/"Lib/site-packages"
    for wheel in sorted((TARGET/"project-wheels").glob("*.whl")):
        with zipfile.ZipFile(wheel) as archive:
            for name in archive.namelist():
                if name.endswith(".py") and name.startswith(("asof/", "tether/")):
                    raw = archive.read(name)
                    assert raw == (installed/name).read_bytes() == (old/name).read_bytes(), "Project source changed"
                    project_sources.append({"path": name, "sha256": sha(raw), "bytes": len(raw)})
    assert len(project_sources) == 85
    write(EVIDENCE/"PROJECT-SOURCE-COMPARISON.json", {"status": "pass", "source_count": 85, "sources": project_sources,
        "comparison": "Exact authorized wheels == new Inspect environment == existing qualified SciFact environment"})
    work = TARGET/"mock-eval-attempt01"
    work.mkdir()
    os.chdir(work)
    os.environ.update(INSPECT_CACHE_DIR=str(work/"cache"), INSPECT_LOG_DIR=str(work/"logs"),
                      TIKTOKEN_CACHE_DIR=str(work/"tiktoken-cache"))
    attempts = []
    def block_network(event, args):
        if event in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
            attempts.append({"event": event})
            raise PermissionError("Network denied during mock environment qualification")
    sys.addaudithook(block_network)
    from inspect_ai import Task, eval
    from inspect_ai.dataset import Sample
    from inspect_ai.model import ModelAPI, ModelOutput, ModelUsage, GenerateConfig
    from inspect_ai.solver import TaskState, generate
    from inspect_ai.scorer import match
    outputs = []
    for value in ("fictional-blue", "fictional-wrong"):
        output = ModelOutput.from_content(model="mockllm", content=value)
        output.usage = ModelUsage(input_tokens=7, output_tokens=2, total_tokens=9)
        outputs.append(output)
    task = Task(name="inspect_environment_mock", dataset=[
        Sample(id="fictional-1", input="Invented color?", target="fictional-blue"),
        Sample(id="fictional-2", input="Another invented color?", target="fictional-green")],
        solver=generate(), scorer=match(location="exact"))
    logs = eval(task, model="mockllm/model", model_args={"custom_outputs": outputs}, display="none",
        log_dir=str(work/"logs"), log_format="json", fail_on_error=True, retry_on_error=0, score_on_error=False,
        max_retries=0, max_samples=1, max_tasks=1, time_limit=30, log_shared=False, notification=False,
        log_samples=True, log_model_api=True)
    assert len(logs) == 1 and logs[0].status == "success", "Mock evaluation did not complete"
    log = logs[0]
    assert log.samples is not None and len(log.samples) == 2
    values = [sample.scores["match"].value for sample in log.samples]
    assert values == ["C", "I"] and not attempts, "Mock score or network isolation differs"
    write(EVIDENCE/"MOCK-EVAL.json", {"status": "pass", "sample_count": 2, "scores": values,
        "model": "mockllm/model", "mock_generation_count": 2, "real_model_calls": 0, "external_provider_calls": 0,
        "network_attempts": attempts, "provider_cost_usd": 0, "usage_basis": "Explicit synthetic fixture usage; not measured model tokens",
        "retry_on_error": 0, "max_retries": 0, "log_location": str(log.location),
        "results": log.results.model_dump(mode="json"), "stats": log.stats.model_dump(mode="json")})
    api = {"ModelAPI.__init__": str(inspect.signature(ModelAPI.__init__)),
           "ModelAPI.generate": str(inspect.signature(ModelAPI.generate)), "TaskState": str(inspect.signature(TaskState)),
           "GenerateConfig": str(inspect.signature(GenerateConfig)), "eval": str(inspect.signature(eval))}
    write(EVIDENCE/"OBSERVED-API.json", {"inspect_ai_version": "0.3.287", "signatures": api})
    write(EVIDENCE/"ENVIRONMENT-QUALIFICATION.json", {"status": "pass", "python": sys.executable,
        "python_version": sys.version, "inspect_ai_version": metadata.version("inspect-ai"),
        "distributions": len(distributions), "record_verified_files": sum(d["record_verified_files"] for d in distributions),
        "record_unhashed_entries": len(unchecked), "project_sources_identical": 85, "mock_samples": 2,
        "real_model_calls": 0, "external_provider_calls": 0, "network_attempts_in_mock": 0,
        "elapsed_seconds": time.monotonic()-started, "finished_at": datetime.now(timezone.utc).isoformat(),
        "qualification_code_sha256": sha(Path(__file__).read_bytes())})
    print(json.dumps({"status": "pass", "distributions": len(distributions), "project_sources": 85, "mock_samples": 2}))


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        write(EVIDENCE/"QUALIFICATION-FAILED.json", {"error_class": type(exc).__name__, "message": str(exc),
              "at": datetime.now(timezone.utc).isoformat(), "automatic_retry": False})
        raise
