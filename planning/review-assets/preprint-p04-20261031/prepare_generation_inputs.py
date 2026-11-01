"""One finite original-source preparation; no model or reference generation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

WORKSPACE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKSPACE / "src"))
from asof.serde import canonical, parse_json
from asof.journal import RunJournal
from asof.study.source_fact_inputs import prepare_generation_inputs

PLAN = WORKSPACE / "planning/review-assets/preprint-p04-20261031/DEVELOPMENT-INPUT-PLAN-v4.json"
PLAN_SHA256 = "815f23b10f15bb6e68967aaed05e532c35b286160c5f89f65b9105a98b10b761"
RAW_ROOT = Path(r"E:\projects_data\drug_target_agents_data")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def peak_memory():
    try:
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        if not kernel.K32GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return None
        return counters.PeakWorkingSetSize
    except (AttributeError, OSError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-source-preparation", action="store_true", required=True)
    args = parser.parse_args()
    target = WORKSPACE / "planning/review-assets/preprint-p04-20261031/GENERATION-INPUTS-v1.json"
    if target.exists():
        raise FileExistsError("Sanitized generation-input summary already exists; do not repeat original-source preparation")
    plan = parse_json(PLAN.read_bytes())
    if digest(PLAN) != PLAN_SHA256:
        raise ValueError("Frozen neutral plan hash differs")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = WORKSPACE / "data/derived" / ("preprint-p04-inputs-" + stamp)
    probe = subprocess.run(["git", "check-ignore", "--quiet", str(output.relative_to(WORKSPACE) / "probe.json")], cwd=WORKSPACE)
    if probe.returncode != 0:
        raise ValueError("Private original-value output directory must already be ignored")
    journal = RunJournal(output, kind="build")
    started = time.monotonic()
    retained = {}
    def save(name, document):
        payload = canonical(document)
        with (output / name).open("xb") as stream:
            stream.write(payload)
        retained[name] = dict(sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload))
    code_paths = [WORKSPACE / "src/asof/study/source_fact_inputs.py", Path(__file__).resolve(),
                  WORKSPACE / "tests/test_study_source_fact_inputs.py"]
    code_hashes = {str(path.relative_to(WORKSPACE)).replace("\\", "/"): digest(path) for path in code_paths}
    try:
        journal.append("build_stage", stage="source_input_preparation")
        prepared = prepare_generation_inputs(PLAN, WORKSPACE / plan["source_policy"]["inspection_manifest"],
                       WORKSPACE / "data/catalog/sources.json", expected_plan_sha256=PLAN_SHA256,
                       workspace_root=WORKSPACE, approved_raw_root=RAW_ROOT,
                       cutoff=plan["created_at_utc"], deadline=started + plan["source_policy"]["selection_wall_seconds"],
                       progress=lambda event, **details: journal.append(event, **details))
        journal.append("build_stage", stage="seal_generation_inputs")
        save("source-inventory.json", dict(schema_version=1, role="agent_evidence", agent_visible=True,
             source_snapshot=prepared["source_snapshot"], inventory_proofs=prepared["inventory_proofs"],
             reference_inputs=[], plan_sha256=PLAN_SHA256))
        condition_details = {}
        for key, packet in prepared["packets"].items():
            save(key + ".packet.json", packet)
            save(key + ".task.json", packet["neutral_task"])
            condition_details[key] = dict(packet_path=key + ".packet.json", task_path=key + ".task.json",
                                          task_sha256=packet["task_sha256"], records=len(packet["source_records"]),
                                          fact_slots=len(packet["fact_skeleton"]), collection_status=packet["neutral_task"]["collection"]["status"],
                                          synthetic=packet["condition"]["synthetic"])
        summary = dict(schema_version=1, status="sealed_source_inputs" if not prepared["blocked_cases"] else "blocked_source_inputs",
                       cutoff=plan["created_at_utc"], plan_sha256=PLAN_SHA256,
                       inspection_sha256=prepared["inspection_sha256"], catalog_sha256=prepared["catalog_sha256"],
                       inventory=prepared["inventory_summary"], selection=prepared["selection"], blocked_cases=prepared["blocked_cases"],
                       conditions=condition_details, source_scan_elapsed_seconds=prepared["elapsed_seconds"],
                       preparation_elapsed_seconds=time.monotonic() - started,
                       peak_working_set_bytes=peak_memory(), implementation_hashes=code_hashes,
                       original_value_output=str(output.relative_to(WORKSPACE)).replace("\\", "/"),
                       input_interface="source-fact-generation-input-v1", application_evidence_packet=False,
                       role="agent_evidence", agent_visible=True, content_parents="allowlisted pinned originals and neutral frozen input plan only",
                       reference_inputs=[], evaluator_artifacts_read=False,
                       public_compiler_code_exposure="Read public source_fact_sources.py algorithm during API/schema inspection; no compiler invocation or retained reference/expected artifacts read.",
                       model_calls=0, generation_authority=False, scientific_interpretation="not_performed",
                       controlled_missing="Synthetic evidence withholding within the CD276 context; incomplete collection, no biological-absence claim, not a third independent case")
        save("preparation-summary.json", summary)
        seal = dict(schema_version=1, sealed_at_utc=datetime.now(timezone.utc).isoformat(),
                    phase="generation_inputs_sealed_before_evaluator_reference_creation",
                    files=retained, implementation_hashes=code_hashes, plan_sha256=PLAN_SHA256,
                    reference_inputs=[], model_calls=0, generation_authority=False)
        save("SEAL.json", seal)
        summary["seal"] = retained["SEAL.json"]
        with target.open("x", encoding="utf-8") as stream:
            json.dump(summary, stream, indent=2, allow_nan=False)
            stream.write("\n")
        journal.append("build_completed", seal_sha256=retained["SEAL.json"]["sha256"],
                       condition_packets=len(condition_details), original_sources=prepared["inventory_summary"]["files"],
                       elapsed_seconds=time.monotonic() - started, model_calls=0)
        print(json.dumps(summary, indent=2))
    except BaseException as error:
        try:
            journal.fail(error, "source_input_preparation")
        except BaseException as journal_error:
            error.add_note("Terminal journal write also failed: " + str(journal_error))
        if not (output / "FAILURE.json").exists():
            save("FAILURE.json", dict(schema_version=1, status="preparation_failed", exception_type=type(error).__name__,
                                     error=str(error), elapsed_seconds=time.monotonic() - started,
                                     plan_sha256=PLAN_SHA256, implementation_hashes=code_hashes,
                                     reference_inputs=[], model_calls=0, generation_authority=False))
        raise
    finally:
        journal.close()


if __name__ == "__main__":
    main()
