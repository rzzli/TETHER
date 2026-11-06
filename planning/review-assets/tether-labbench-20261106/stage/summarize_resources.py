"""Resource-only extraction from externally anchored BG04 operational records.

No production imports, reference keys, native scores or model/retrieval calls.
Reads allocate the observed bounded file size, not the maximum allowed cap.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
STAGE = Path(__file__).resolve().parent
GENERATION_SHA = "46acaabedd04b0f9a2410f8620f13f19f9927e5e6fc1d0437d8b29bc63cd8447"
COLLECTION_SHA = "b75558de8fca5382729e42d7bd6adc9efabdb072791b0d75201aaff2280c47de"
COLLECTION_SEAL_SHA = "37555f392f1712a7510a49448e59b84fcc1798862414db8285cb93dcd9b46fbc"
FREEZE_SHA = "4359d589205caec39085872cc72cd5799323e2285e0993b58405e7e70ccd2fe5"
proofs = []


def read(path, expected=None, *, cap=16*1024**2):
    path = Path(path)
    before = path.stat()
    if not path.is_file() or path.is_symlink() or before.st_size > cap:
        raise ValueError("Not a bounded ordinary operational record")
    with path.open("rb") as stream:
        raw = stream.read(before.st_size+1)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino) or len(raw) != before.st_size:
        raise ValueError("Operational record changed during capture")
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError("External or parent-bound resource anchor differs: " + str(path))
    proofs.append({"path": str(path), "sha256": digest, "bytes": len(raw)})
    return raw


def load(path, expected=None):
    return json.loads(read(path, expected))


def values(samples, key):
    return [row["value"][key] for row in samples
            if row.get("value") is not None and row["value"].get(key) is not None]


freeze = load(STAGE/"generation-freeze-attempt02/GENERATION-FREEZE.json", FREEZE_SHA)
generation_root = Path(freeze["generation_output"])
collection_root = Path(freeze["collection"]["path"])
seal = load(generation_root/"SEALED.json", GENERATION_SHA)
generation = load(generation_root/"manifest.json", seal["manifest_sha256"])
collection_seal = load(collection_root/"SEALED.json", COLLECTION_SEAL_SHA)
collection = load(collection_root/"manifest.json", COLLECTION_SHA)
assert collection_seal["manifest_sha256"] == freeze["collection"]["manifest_sha256"] == COLLECTION_SHA
assert freeze["collection"]["seal_sha256"] == COLLECTION_SEAL_SHA
assert generation["collection"] == {"path": str(collection_root), "manifest_sha256": COLLECTION_SHA}
terminal_ref = generation["worker_terminal"]
assert terminal_ref["sha256"] == seal["outputs"][terminal_ref["path"]]["sha256"]
terminal = load(generation_root/terminal_ref["path"], terminal_ref["sha256"])
worker_events = [json.loads(line) for line in read(generation_root/"worker/journal.jsonl", seal["outputs"]["worker/journal.jsonl"]["sha256"]).splitlines()]
parent_events = [json.loads(line) for line in read(generation_root/"journal.jsonl", seal["outputs"]["journal.jsonl"]["sha256"]).splitlines()]
ready = [row["details"] for row in worker_events if row["event"] == "worker_model_ready"]
assert len(ready) == 1
samples = terminal["model_samples"]
cpu = values(samples, "cpu_seconds")
working = values(samples, "working_set_bytes")
process_peak = values(samples, "process_peak_working_set_bytes")
first_reserved = parent_events[0]["details"]["created_at_utc"]
seal_mtime = datetime.fromtimestamp((generation_root/"SEALED.json").stat().st_mtime, timezone.utc)
scoring_control = STAGE/"SCORE-CONTROL-01.json"
control_size = scoring_control.stat().st_size if scoring_control.exists() else None
result = {
    "schema_version": 1,
    "kind": "labbench_resource_scope",
    "captured_at_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "Selected anchored operational records only; not a complete output-byte or semantic verification",
    "external_anchors": {"generation_seal_sha256": GENERATION_SHA, "collection_manifest_sha256": COLLECTION_SHA,
                         "collection_seal_sha256": COLLECTION_SEAL_SHA, "generation_freeze_sha256": FREEZE_SHA},
    "generation_status": generation["status"],
    "cleanup": generation["cleanup"],
    "collection": {"status": collection["status"], "totals": collection["totals"], "resources": collection["resources"],
                   "inventory_product_files": len(collection["outputs"]),
                   "inventory_product_bytes": sum(row["bytes"] for row in collection["outputs"].values()),
                   "timing_scope": "Collector resource field captured before final manifest/journal/seal publication; HTTP-child CPU and peak RAM are uninstrumented",
                   "byte_scope": "Known response-body bytes and conservative unknown-body allowance exclude protocol/transfer overhead; selected text and retained products are separate quantities"},
    "generation": {"totals": generation["totals"], "parent_pre_seal_resources": generation["parent_resources"],
                   "parent_pre_seal_scope": "Captured before _seal; excludes recover_cases, final publication/inventory/hash/seal work; not total workflow latency",
                   "supervised_worker": generation["supervision"],
                   "worker_wall_seconds": terminal["worker_wall_seconds"], "worker_cpu_seconds": terminal["worker_cpu_seconds"],
                   "setup_including_asset_verification_seconds": ready[0]["setup_including_asset_verification_seconds"],
                   "setup_scope": "Owned server context entry including declared asset verification and startup; excludes prior source collection verification",
                   "inventory_files": len(seal["outputs"]), "inventory_bytes": sum(row["bytes"] for row in seal["outputs"].values()),
                   "inventory_scope": "All generation seal-declared outputs excluding SEALED.json itself; not physical I/O",
                   "measured_marginal_admission_seconds": None,
                   "marginal_admission_reason": "verify_candidate is not separately timed; source capture, generation and checking share case wall records",
                   "finalization_wall_seconds": None, "end_to_end_wall_seconds": None,
                   "finalization_reason": "No retained outer monotonic timer; finalization follows parent_resources capture and is not covered by worker deadline",
                   "filesystem_timing": {"parent_reserved_at_utc": first_reserved, "seal_last_write_at_utc": seal_mtime.isoformat(),
                       "interval_seconds": (seal_mtime-datetime.fromisoformat(first_reserved)).total_seconds(),
                       "basis": "Declared UTC start plus filesystem modification time; descriptive chronology, not attested monotonic stopwatch"}},
    "native_process": {"sample_records": len(samples), "sample_errors": sum(row.get("error_class") is not None for row in samples),
                       "interval_seconds": terminal["model_sampling_seconds"], "sample_window": "After owned-server readiness through case loop; excludes cleanup",
                       "first_cumulative_cpu_seconds": cpu[0] if cpu else None,
                       "last_cumulative_cpu_seconds": cpu[-1] if cpu else None,
                       "observed_cpu_delta_seconds": cpu[-1]-cpu[0] if len(cpu)>1 else None,
                       "maximum_sampled_working_set_bytes": max(working) if working else None,
                       "maximum_reported_process_lifetime_peak_working_set_bytes": max(process_peak) if process_peak else None,
                       "memory_scope": "Sampled current working set can miss short peaks; sampled OS process-lifetime peak may include startup before sampling; neither includes GPU memory",
                       "gpu_memory_bytes": None, "energy": None},
    "scoring": {"control_path": str(scoring_control), "observed_control_bytes": control_size,
                "outer_elapsed_seconds": None, "controller_cpu_seconds": None,
                "status": "not_read_pending_explicit_aggregate_authorization",
                "reason": "Control was running or awaiting authorized resource extraction; no scorer/native result opened"},
    "cost": {"provider_cost_usd": generation["provider_cost_usd"], "collection_provider_usd": collection["resources"]["provider_usd"],
             "electricity_hardware_depreciation_labour_usd": None,
             "basis": "Zero external-provider charges do not establish zero total cost; fictional controls/development are separate"},
    "input_proofs": proofs,
    "producer_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "reference_access": False, "native_correctness_access": False,
    "production_changes": False, "new_model_calls": 0, "new_retrieval_calls": 0,
}
output = STAGE/"RESOURCE-SCOPE-01.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(result, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({key:result[key] for key in ("generation_status","cleanup","collection","generation","native_process","scoring","cost")}))
