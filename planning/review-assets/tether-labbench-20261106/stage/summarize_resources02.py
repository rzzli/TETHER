"""Append completed evaluator resources to snapshot 01 without rewriting it."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
STAGE = Path(__file__).resolve().parent
EVALUATION_SHA = "118711b7e7552750e441380b7abf8f60b68096ae98ef3163cf96754e7423fa6f"
SNAPSHOT01_SHA = "320dd59dc6b7b583e80b1096473431a0af82067adfbda74f3ae47dba5d7d476c"
proofs = []


def load(path, expected=None):
    path = Path(path)
    before = path.stat()
    if not path.is_file() or path.is_symlink() or before.st_size > 4*1024**2:
        raise ValueError("Not a bounded ordinary resource record")
    with path.open("rb") as stream:
        raw = stream.read(before.st_size+1)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino) or len(raw) != before.st_size:
        raise ValueError("Resource record changed during capture")
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError("Resource anchor mismatch")
    proofs.append({"path": str(path), "sha256": digest, "bytes": len(raw)})
    return json.loads(raw)


prior = load(STAGE/"RESOURCE-SCOPE-01.json", SNAPSHOT01_SHA)
evaluation_root = ROOT/"data/benchmark/labbench/evaluation-20261106T011303Z-attempt01"
seal = load(evaluation_root/"SEALED.json", EVALUATION_SHA)
assert seal["status"] == "completed"
assert seal["input_anchors"]["external_sealed_sha256"] == prior["external_anchors"]["generation_seal_sha256"]
resources = load(evaluation_root/"resources.json", seal["outputs"]["resources.json"]["sha256"])
report = load(evaluation_root/"REPORT.json", seal["outputs"]["REPORT.json"]["sha256"])
control = load(STAGE/"SCORE-CONTROL-01.json")
assert control["generation_sealed_sha256"] == prior["external_anchors"]["generation_seal_sha256"]
assert control["status"] == report["status"] == "completed"
assert control["scheduled_count"] == report["scheduled_count"] == 199
assert control["raw_metrics"] == report["raw_metrics"] and control["checked_metrics"] == report["checked_metrics"]
assert resources["generation_totals"] == prior["generation"]["totals"]
assert resources["collection_totals"] == prior["collection"]["totals"]
assert resources["provider_cost_usd"] == resources["new_model_calls"] == resources["new_retrieval_calls"] == 0
assert control["new_model_calls"] == control["new_retrieval_calls"] == 0
assert control["elapsed_seconds"] >= resources["evaluation_wall_seconds"]
assert control["controller_cpu_seconds"] >= resources["evaluation_cpu_seconds"]
result = dict(prior)
result.update(captured_at_utc=datetime.now(timezone.utc).isoformat(), snapshot=2,
    previous_snapshot={"path": str(STAGE/"RESOURCE-SCOPE-01.json"), "sha256": SNAPSHOT01_SHA},
    scope="Selected anchored operational/evaluator records; not a new full output rehash or independent metric reconstruction",
    native_correctness_access=True,
    native_correctness_scope="Authorized aggregate report only; no reference-answer file opened",
    producer_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
result["external_anchors"] = dict(prior["external_anchors"], evaluation_seal_sha256=EVALUATION_SHA)
result["input_proofs"] = prior["input_proofs"] + proofs
result["scoring"] = {
    "status": "completed", "control_path": str(STAGE/"SCORE-CONTROL-01.json"),
    "control_sha256": proofs[-1]["sha256"],
    "control_anchor_scope": "Captured completed outer-control bytes; evaluator seal is externally anchored; control settings/aggregate identity were reconciled",
    "outer_elapsed_seconds": control["elapsed_seconds"], "outer_controller_cpu_seconds": control["controller_cpu_seconds"],
    "outer_timing_scope": "Wrapper timer surrounds full evaluator return; excludes earlier imports and final controller-record serialization",
    "internal_elapsed_seconds": resources["evaluation_wall_seconds"],
    "internal_cpu_seconds": resources["evaluation_cpu_seconds"],
    "internal_timing_scope": "Evaluator resource fields captured before its final product/journal/seal writes",
    "process_sample": resources["evaluation_process_sample"],
    "memory_basis": resources["evaluation_memory_basis"],
    "model_asset_unique_bytes_verified": resources["model_asset_unique_bytes_verified"],
    "model_asset_byte_basis": resources["model_asset_byte_basis"],
    "new_model_calls": 0, "new_retrieval_calls": 0, "provider_cost_usd": 0,
    "verification_scope": "Full source-inclusive generation/model/session replay plus reference reconstruction, native scoring and reporting; not marginal admission-check cost",
    "independent_audit_reconstruction_cost": None,
    "independent_audit_reconstruction_reason": "Separate independent audit/reconstruction timings are outside this evaluator control; no invented aggregate cost",
    "finalization_and_total_generation_timing": "Remain unknown as monotonic measurements; snapshot01's limitations are unchanged",
}
with (STAGE/"RESOURCE-SCOPE-02.json").open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(result, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps(result["scoring"], sort_keys=True))
