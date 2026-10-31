"""Independent retained-artifact checker. Never imports or executes a subject."""
from pathlib import Path
import hashlib
import json
import math


ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
RUN = ROOT / "data/cache/r09-native-carrier-component-run-20261030T061649Z"
REPORT = BASE / "NATIVE-CARRIER-FAKE-RUN-INDEPENDENT-ACTUAL-REVIEW-v1.json"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(raw), "sha256": digest(raw)}


def load(path):
    return json.loads(Path(path).read_bytes())


def main():
    checks = 0
    failures = []

    def require(condition, label):
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(label)

    scope_path = BASE / "NATIVE-CARRIER-FAKE-RUN-SCOPE-v1.json"
    binding_path = BASE / "NATIVE-CARRIER-FAKE-RUN-BINDING-v1.json"
    result_path = RUN / "run-result.json"
    scope = load(scope_path)
    binding = load(binding_path)
    result = load(result_path)
    pins = {"scope": pin(scope_path), "binding": pin(binding_path), "actual_result": pin(result_path),
            "independent_checker": pin(__file__)}
    require(pins["scope"]["sha256"] == "8899d56436e44890cbee30be0d7e487c24db8b87794bad27ae3b3af58d108fa4", "original scope anchor")
    require(pins["binding"]["sha256"] == "b2e6d7ca65a9b2aa6dcf1fda3c33c0f99713f472fd7d21af2a90323f8cb7123f", "original binding anchor")
    require(result["binding_sha256"] == pins["binding"]["sha256"], "result binding")
    require(binding["budget_seconds"] == scope["budget_seconds"] == 60, "original budget")
    require(Path(binding["output_relative"]).resolve() == RUN == Path(scope["output_relative"]).resolve(), "exact output reservation")
    for label, expected in binding["inputs"].items():
        actual = pin(ROOT / expected["path"])
        pins[label] = actual
        require(actual["bytes"] == expected["bytes"] and actual["sha256"] == expected["sha256"], "bound unchanged " + label)
        if label != "root_scope":
            require(expected == scope["inputs"][label], "scope/binding input " + label)

    build_binding_path = BASE / "NATIVE-CARRIER-COMPONENT-BUILD-BINDING-v1.json"
    build_binding = load(build_binding_path)
    build = load(ROOT / binding["inputs"]["build_result"]["path"])
    pins["build_binding"] = pin(build_binding_path)
    require(pins["build_binding"]["sha256"] == build["binding_sha256"], "actual build binding")
    for label in ("source", "header", "tests"):
        expected = build_binding["inputs"][label]
        actual = pin(ROOT / expected["path"])
        pins["built_" + label] = actual
        require(actual["bytes"] == expected["bytes"] and actual["sha256"] == expected["sha256"], "built source unchanged " + label)
    image_pin = pins["image"]
    build_image = [row for row in build["artifacts"] if Path(row["path"]).name == "native-carrier-fake-tests.exe"]
    require(len(build_image) == 1, "one built image")
    require(image_pin["sha256"] == build_image[0]["sha256"] and image_pin["bytes"] == build_image[0]["bytes"], "post-run image equals built image")

    oracle = load(ROOT / binding["inputs"]["expectations"]["path"])
    groups = [oracle["semantic_vectors"], oracle["malformed_wrapper_vectors"], oracle["initializer_negative_vectors"], [oracle["interrupted_error_vector"]]]
    expected_rows = []
    for row in groups[0]:
        expected_rows.append((row["id"], row["normal_copy256_hex"], row["error_boundary_copy256_hex"]))
    for row in groups[1]:
        expected_rows.append((row["id"], row["cell_copy256_hex"], None))
    for row in groups[2]:
        expected_rows.append((row["id"], row["expected_cell_copy256_hex"], None))
    escaped = groups[3][0]
    expected_rows.append((escaped["id"], escaped["escaped_copy256_hex"], escaped["escaped_copy256_hex"]))
    require([len(group) for group in groups] == [46, 22, 10, 1], "frozen four groups")
    require(len(expected_rows) == len({row[0] for row in expected_rows}) == 79, "79 unique ordered oracle controls")

    stdout_path = RUN / "native-fake-tests.stdout"
    stdout = stdout_path.read_bytes()
    records = [json.loads(line) for line in stdout.splitlines()]
    require(stdout.endswith(b"\n") and len(records) == 80, "80 complete stdout JSON lines")
    rows = records[:-1]
    require(len(rows) == 79 and rows == result["cases"], "all actual rows retained exactly")
    require(set(records[-1]) == {"summary"}, "single final summary shape")
    require(records[-1]["summary"] == result["summary"], "stdout/report summary identity")
    normal_matches = boundary_matches = boundary_absent = 0
    actual_cells = bytearray()
    expected_cells = bytearray()
    for index, (actual, expected) in enumerate(zip(rows, expected_rows)):
        case_id, normal_hex, boundary_hex = expected
        require(set(actual) == {"case", "outcome", "cell_copy256_hex", "error_boundary_copy256_hex"}, "exact row keys " + str(index))
        require(actual["case"] == case_id and actual["outcome"] == "PASS", "ordered PASS " + case_id)
        normal = bytes.fromhex(actual["cell_copy256_hex"])
        expected_normal = bytes.fromhex(normal_hex)
        match = len(normal) == len(expected_normal) == 256 and normal == expected_normal and actual["cell_copy256_hex"] == normal_hex
        require(match, "all 256 normal/escaped bytes " + case_id)
        normal_matches += int(match)
        actual_cells.extend(normal)
        expected_cells.extend(expected_normal)
        if boundary_hex is None:
            require(actual["error_boundary_copy256_hex"] is None, "explicit absent boundary " + case_id)
            boundary_absent += int(actual["error_boundary_copy256_hex"] is None)
        else:
            boundary = bytes.fromhex(actual["error_boundary_copy256_hex"])
            expected_boundary = bytes.fromhex(boundary_hex)
            match = len(boundary) == len(expected_boundary) == 256 and boundary == expected_boundary and actual["error_boundary_copy256_hex"] == boundary_hex
            require(match, "all 256 error boundary bytes " + case_id)
            boundary_matches += int(match)
            actual_cells.extend(boundary)
            expected_cells.extend(expected_boundary)
    require((normal_matches, boundary_matches, boundary_absent) == (79, 17, 62), "complete cell comparison census")
    require(len(actual_cells) == 24576 and actual_cells == expected_cells, "combined 24576 raw payload bytes")

    target_count = sum(row["expected_fake_target_calls"] for group in (groups[0], groups[1], groups[2], groups[3]) for row in group)
    entries = sum(row.get("expected_error_entries", 0) for group in groups for row in group)
    returns = sum(row.get("expected_error_returns", 0) for group in groups for row in group)
    expected_counters = {"cases": 79, "failures": 0, "initializer_attempts": 79,
                         "wrapper_attempts": 2 * 46 + 22 + 2, "fake_targets": target_count,
                         "error_entries": entries, "error_returns": returns, "partial_copies": boundary_matches}
    require((target_count, entries, returns) == (47, 17, 16), "independent oracle counter sums")
    summary = result["summary"]
    require(set(summary) == set(expected_counters) | {"checks"}, "exact summary keys")
    for key, expected in expected_counters.items():
        require(type(summary[key]) is int and summary[key] == expected, "actual counter " + key)
    require(type(summary["checks"]) is int and summary["checks"] > 0, "measured positive C check count, not predeclared oracle total")
    require(result["status"] == "ALL_79_FAKE_TARGET_CONTROLS_PASSED" and result["failure"] is None and result["grade_error"] is None, "actual successful first outcome")

    require(len(result["commands"]) == 1, "one retained dispatch, no retry")
    command = result["commands"][0]
    expected_argv = [str((ROOT / binding["inputs"]["image"]["path"]).resolve())]
    require(command["label"] == "native-fake-tests" and command["argv"] == expected_argv, "exact single fake-image command")
    require(command["returncode"] == 0 and type(command["returncode"]) is int and command["output_complete"] is True and command["main_exit_observed"] is True, "known successful main exit and output")
    require(command["primary_error"] is None and command["cleanup_errors"] == [] and command["kill_attempted"] is False and command["kill_acknowledged"] is False, "no dispatch/cleanup/kill error")
    require(command["stdout_bytes"] == len(stdout) and command["stderr_bytes"] == 0 and (RUN / "native-fake-tests.stderr").read_bytes() == b"", "actual stdout/stderr lengths")

    journal_path = RUN / "run-journal.jsonl"
    journal = journal_path.read_bytes()
    previous = "0" * 64
    events = []
    prior_elapsed = 0.0
    for index, raw in enumerate(journal.splitlines()):
        event = json.loads(raw)
        require(raw == json.dumps(event, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"), "canonical journal bytes " + str(index))
        require(event["sequence"] == index and event["previous_sha256"] == previous, "journal sequence/link " + str(index))
        elapsed = event["elapsed_seconds"]
        require(type(elapsed) in (int, float) and math.isfinite(elapsed) and prior_elapsed <= elapsed <= result["elapsed_seconds"] < 60, "journal original-timer bounds " + str(index))
        prior_elapsed = elapsed
        previous = digest(raw)
        events.append(event)
    require(journal.endswith(b"\n") and len(events) == 4, "four complete journal rows")
    require([event["kind"] for event in events] == ["run_reserved", "dispatch_reserved", "dispatch_returned_or_failed", "run_prepared_status"], "one dispatch/return, no failure/retry journal")
    require(events[0]["binding_sha256"] == pins["binding"]["sha256"] and events[0]["model_execution"] is False, "original journal binding and model scope")
    require(events[1]["argv"] == expected_argv, "journal dispatch image")
    require(all(events[2][key] == value for key, value in command.items()), "actual return journal equals command facts")
    require(events[3]["status"] == result["status"] and events[3]["failure"] is None and events[3]["grade_error"] is None, "last journal prepared status")
    require(result["journal_complete"] is True and result["journal_events"] == result["journal_acknowledged_events"] == len(events) and result["journal_final_hash"] == previous, "complete acknowledged journal tip/count")
    require(type(result["elapsed_seconds"]) in (int, float) and 0 <= result["elapsed_seconds"] < scope["budget_seconds"], "final original helper deadline")

    actual_artifacts = []
    for expected in result["artifacts"]:
        actual = pin(ROOT / expected["path"])
        require(actual["bytes"] == expected["bytes"] and actual["sha256"] == expected["sha256"], "saved artifact hash " + actual["path"])
        actual_artifacts.append(actual)
    require(result["artifact_inventory_complete"] is True and len(actual_artifacts) == 3, "complete three-artifact inventory")
    require({Path(row["path"]).name for row in actual_artifacts} == {"native-fake-tests.stdout", "native-fake-tests.stderr", "run-journal.jsonl"}, "exact expected three artifacts")
    require({path.name for path in RUN.iterdir()} == {"native-fake-tests.stdout", "native-fake-tests.stderr", "run-journal.jsonl", "run-result.json"}, "exact four run files")
    artifact_bytes = sum(row["bytes"] for row in actual_artifacts)
    all_run_bytes = artifact_bytes + pins["actual_result"]["bytes"]
    review = {
        "schema_version": 1,
        "status": "CLEAR_ACTUAL_79_FAKE_TARGET_COMPONENT_ONLY" if not failures else "HOLD_RETAINED_ARTIFACT_MISMATCH",
        "scope": "Independent retained-byte/counter/journal/image-integrity review; no subject import, replay, build or native dispatch by reviewer.",
        "inputs": pins,
        "checks": {"performed": checks, "failed": len(failures), "failures": failures},
        "actual": {
            "frozen_group_counts": [46, 22, 10, 1], "ordered_PASS_controls": normal_matches,
            "matched_full256B_primary_copies": normal_matches, "matched_full256B_error_boundary_copies": boundary_matches,
            "explicit_absent_boundary_copies": boundary_absent, "compared_raw_payload_bytes": len(actual_cells),
            "interleaved_compared_payload_sha256": digest(actual_cells), "summary": summary,
            "counter_meaning": "29,310 is the image's measured CHECK invocation count, copied exactly in stdout/report; exact data bytes and operation counters independently match the pre-run oracle. Wrapper attempts include rejected repeats/malformed wrappers; 47 targets are own-source fakes. Error entries17 versus returns16 includes one controlled setjmp/longjmp escape.",
            "command": command, "elapsed_seconds": result["elapsed_seconds"],
            "one_image_no_retry_evidence": "One retained command and one dispatch/return journal pair under an exclusive one-use output reservation. No build command or second image dispatch is present in this attempt; not OS-wide process attestation.",
            "journal": {"events": len(events), "complete": result["journal_complete"], "acknowledged_events": result["journal_acknowledged_events"], "tip_sha256": previous, "kinds": [row["kind"] for row in events]},
        },
        "accounting": {
            "artifact_inventory": actual_artifacts,
            "inventory_files": len(actual_artifacts), "inventory_content_bytes": artifact_bytes,
            "result_bytes": pins["actual_result"]["bytes"], "run_files_including_result": 4, "run_content_bytes_including_result": all_run_bytes,
            "raw_copy_payload_primary_bytes": 79 * 256, "raw_copy_payload_boundary_bytes": 17 * 256,
            "copies": "Primary/boundary snapshots are 24,576 logical bytes serialized as hex inside stdout and duplicated as case values in run-result JSON. This is not 79 live Core rows, retained original file reads, Source4 generated ledgers or process memory.",
            "excluded": "Build files, pre-run bindings/scopes, checker/review files and prior evidence; no additive RAM/RSS/commit/working-set estimate.",
        },
        "timing_and_persistence": {
            "budget_seconds": 60, "known_main_cleanup_reserve_seconds": 2,
            "included": "Helper timer after pinned-input checks and exclusive output reservation through image/pipe work, known-main cleanup, grading, artifact inventory and final eligibility check.",
            "excluded": "Python/CRT/startup before timer, final report construction/write and failure-only diagnostic tail. Final result write elapsed is unmeasured; not production first-entry, whole-process, child120/work117/owner300 proof.",
            "writes": "Ordinary retained harness filesystem writes; no FlushFileBuffers, crash durability or physical producer output qualification.",
        },
        "qualification": {
            "compiled_C_fake_target_component": not failures,
            "actual_Win32_file_target_conformance": False, "same_Core_ticket_and_native_bank_integration": False,
            "native_input_child_image_path_lease": False, "physical14_profile": False,
            "native25_component_upgrade": False, "full_new84_roster": False, "inference_or_scientific_result": False,
            "RSS_or_resource_fit": False,
            "boundary": "Fixed fake14 function targets and trusted own-source error callback on one compiled x64 image. Volatile/store ordering and actual ABI artifact evidence remain the separately pinned build peer; no atomic OS-return, asynchronous interruption, real LastError, live lease or native model-consumption guarantee follows.",
        },
        "activity": {"subject_imports": 0, "image_runs": 0, "build_replays": 0, "original_or_model_payload_reads": 0,
                     "allowed_activity": "Trusted Python retained JSON/text/hash comparisons only; image read only for unchanged SHA256."},
    }
    with REPORT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(review, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"review": pin(REPORT), "checks": review["checks"], "actual_summary": summary,
                      "all_run_bytes": all_run_bytes, "status": review["status"]}, indent=2))


if __name__ == "__main__":
    main()
