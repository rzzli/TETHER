"""DRAFT v4: exact Amendment-3 optional-cache derivation; all other gates retained.

No project/runtime import or child dispatch. Requires explicit external hashes
for the reviewed combined result and corrected completion protocol; preserves the
original failed attempt and all original acceptance gates. Never execute before
root authorization. Only all passing checks permit exclusive acceptance.json.
"""

from datetime import datetime, timezone
from email.parser import Parser
import argparse
import hashlib
import math
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import tomllib
import zipfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FULL = ROOT / "data/cache/recovery-step9-generation-validation-20261028"
INSTALLED = ROOT / "data/cache/r09-generation-installed-20261028"
FROZEN_CACHE = ROOT / "data/cache/r09-generation-frozen-20261028"
CORPUS = ROOT / "data/cache/r09-generation-corpus-extension-v1-20261028"
GRAMMAR_PHASE = HERE.parent / "recovery-step9-native-grammar-20261028"
OLD = HERE.parent / "recovery-step9-native-duration-20261028"
ACCEPTED_0310 = "27f33a36fd01d48b79e1492ad6b4b185a60e4bd662bb1ee0d955e5a284079cdc"
WHEEL_SHA = "b0d7573be994e3f44e3d942a1944cddb2e43e1306a64cfd6480dd05e3415a276"
ORIGINAL_CORPUS_SHA = "01286d35689c7005ea67fa817c4b4098cecd05c4233c3949e7ec744bc5f5d97a"
REFERENCE_RECEIPT_SHA = "18764b64c8829d2905ab14d1605d6b34d16673d52e6bdb3f92c3bb79bca7fd5e"
REFERENCE_RESULT_SHA = "1fa0be7bb260e95e200902311af3c0d18ae31014dd904609ba35ff7ca948e164"
PROTECTED = {
    "data/benchmark/cohorts/science4-outcomes-20261019T024500Z/adjudication/normalized-outcomes.json":
        "9392df7cec11704f3f0abaddc12e4196349ace1aba55b4da0af0f14d41bb26f2",
    "data/benchmark/labels/endpoint-followup-feasibility-20261021/adjudication-v1/normalized-outcomes.json":
        "c3195a27565debe2c0b891f8aecffbae8a63988dfe2fd62b9e5aed37f0353398",
}
EXPECTED_STATUSES = {
    "031": "passed_frozen_installed_verifier_without_live_source",
    "032": "passed_synthetic_bundle_relocation",
    "033": "passed_recorded_comparison_relocation",
    "034": "passed_installed_source_and_token_replay",
    "035": "passed",
    "036": "passed_authority_four_arm_relocation",
    "037": "installed_collected_source_relocation_verified",
    "038": "passed",
    "039": "installed_native_simulation_relocation_verified",
    "0310": "installed_native_simulation_relocation_verified",
}
METADATA_DELTA = {
    "src/asof/__init__.py", "src/asof/archive/semantic_dependencies.json",
    "pyproject.toml", "uv.lock",
}
ADDED_FILES = {
    "src/asof/study/interpretation_grammar.py",
    "src/asof/study/interpretation_generation.py",
    "tests/test_study_interpretation_generation.py",
}
EVIDENCE = {}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def fingerprint(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def path_key(path):
    path = Path(path).resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def proof(path, *, protected_hash_only=False):
    path = Path(path).resolve()
    require(path.suffix.lower() != ".gguf", "No model-file access in acceptance")
    if "data/benchmark/" in path_key(path).replace("\\", "/").lower():
        require(protected_hash_only and path_key(path) in PROTECTED,
                "Protected payload may be checked only by its explicit hash")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    value = dict(sha256=digest, bytes=path.stat().st_size)
    EVIDENCE[path_key(path)] = value
    return value


def read(path, expected=None):
    path = Path(path).resolve()
    require("data/benchmark/" not in path_key(path).lower(), "No outcome decoding")
    pin = proof(path)
    require(pin["bytes"] <= 16 * 1024 * 1024, "Metadata JSON exceeds 16 MiB")
    require(expected is None or pin["sha256"] == expected, "Metadata anchor differs: " + str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def check_pin(path, expected):
    value = proof(path)
    if isinstance(expected, str):
        require(value["sha256"] == expected, "File hash differs: " + str(path))
    else:
        require(value["sha256"] == expected["sha256"], "File hash differs: " + str(path))
        require("bytes" not in expected or value["bytes"] == expected["bytes"],
                "File size differs: " + str(path))
    return value


def read_chain(path):
    proof(path)
    events = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]
    previous = None
    for index, event in enumerate(events):
        body = dict(event)
        digest = body.pop("sha256")
        require(body["sequence"] == index and body["previous_sha256"] == previous
                and fingerprint(body) == digest, "Journal chain differs")
        previous = digest
    require(bool(events), "Empty journal")
    return events


def inventory(directory, expected_receipt=None):
    directory = Path(directory).resolve()
    receipt = read(directory / "receipt.json", expected_receipt)
    for name, expected in receipt["outputs"].items():
        relative = PurePosixPath(name)
        require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe receipt member")
        path = (directory / name).resolve()
        require(path.is_relative_to(directory), "Receipt path escapes owner directory")
        if isinstance(expected, dict) and "path" in expected:
            require(Path(expected["path"]).resolve() == path, "Receipt member path differs")
        check_pin(path, expected)
    return receipt


def clean_guards(payload):
    for key, value in payload.items():
        if key == "guards" or key.endswith("attempts"):
            values = value.values() if isinstance(value, dict) else (value,)
            require(all(item == [] for item in values), "Nonempty replay guard: " + key)
    for obj in (payload, payload.get("result", {})):
        if isinstance(obj, dict):
            for key in ("actual_model_calls", "native_processes", "model_calls", "tokenizer_calls", "network_calls"):
                require(key not in obj or obj[key] == 0, "Unexpected actual execution: " + key)


def matching_verifiers(combined_sha256, completion_protocol_sha256):
    """Amendment 2: preserve failed primary; verify seven retained plus three new."""
    require(re.fullmatch(r"[0-9a-f]{64}", combined_sha256)
            and re.fullmatch(r"[0-9a-f]{64}", completion_protocol_sha256),
            "Explicit root-reviewed combined/protocol SHA256 anchors required")
    primary_sha = "c780b0643756aa3006c25cb3a01a0066bcc38cc3d603f9285c53754786848e50"
    failure_sha = "f1824a909e74a94a28de5562fbf40b4175e1e337890f0eaa3e792ab021805229"
    checkpoint_sha = "de5b773c4d2e6ff093b87e8ba1d16e10911f188147d08d17d0823b9c228bfc57"
    amendment_sha = "1bf138d7209bc88b2d4eb7e8e6d6daec89c9a9c332b742d5cecff6f6fe4de74c"
    decision_sha = "1c39b715310bae31926403b5b2a723ba4564ec71472eee58f479d31d93db0af6"
    reused, remaining = list(EXPECTED_STATUSES)[:7], list(EXPECTED_STATUSES)[7:]
    output = ROOT / "data/cache/r09-generation-frozen-completion-20261028"
    marker = output / "failure.json"
    require(not marker.exists(), "Authoritative completion failure overrides combined qualification")
    primary = read(HERE / "FROZEN-VERIFIER-CHECKS.json", primary_sha)
    original_failure = read(FROZEN_CACHE / "failure.json", failure_sha)
    require(primary["status"] == "failed_or_incomplete"
            and primary["failure"]["error_class"] == "TimeoutExpired"
            and primary["failure"]["completed_versions"] == reused
            and original_failure["status"] == "failed_no_automatic_restart",
            "Original primary failure must remain unchanged and failed")
    require([row["version"] for row in primary["records"]] == list(EXPECTED_STATUSES),
            "Original matching-version set differs")
    require(primary["records"][7]["replay"]["timed_out"] is True
            and primary["records"][7]["replay"]["reaped"] is True
            and all("replay" not in row and "status" not in row for row in primary["records"][8:]),
            "Original timeout/unattempted versions were relabeled")
    check_pin(HERE / "AMENDMENT-2-FROZEN-VERIFICATION-RECOVERY.md", amendment_sha)
    decision = read(HERE / "AMENDMENT-2-ROOT-DECISION.json", decision_sha)
    require(decision["reused_success_versions"] == reused
            and decision["remaining_versions"] == remaining
            and decision["whole_process_seconds_each"] == 360
            and decision["aggregate_verification_seconds"] == 1200
            and decision["scientific_case_budget_seconds_unchanged"] == 300
            and decision["original_attempt_must_remain_failed"] is True,
            "Recovery authority scope differs")
    combined = read(HERE / "FROZEN-VERIFIER-COMBINED.json", combined_sha256)
    require(combined["status"] == "verified_all_ten_matching_installed_versions_across_retained_attempts"
            and combined["verification_only"] is True
            and combined["current_source_version_under_test"] == "0.3.11"
            and combined["scientific_case_budget_seconds_unchanged"] == 300
            and combined["automatic_restart"] is False
            and combined["model_calls"] == combined["native_target_calls"] == 0,
            "Combined qualification scope differs")
    primary_pin = combined["primary_attempt"]
    require(Path(primary_pin["path"]).resolve() == (HERE / "FROZEN-VERIFIER-CHECKS.json").resolve()
            and primary_pin["sha256"] == primary_sha and primary_pin["status"] == "failed_or_incomplete"
            and primary_pin["failed_at_version"] == "038" and primary_pin["outcome_preserved"] is True,
            "Combined record must preserve original failed attempt")
    check_pin(primary_pin["path"], primary_pin)
    require(Path(primary_pin["failure"]["path"]).resolve() == (FROZEN_CACHE / "failure.json").resolve()
            and primary_pin["failure"]["sha256"] == failure_sha, "Original failure anchor differs")
    check_pin(primary_pin["failure"]["path"], primary_pin["failure"])
    require(combined["record_origins"] == {
        version: "failed_primary_retained_success" if version in reused else "declared_remaining_three_completion"
        for version in EXPECTED_STATUSES}, "Combined record origins differ")
    require([row["version"] for row in combined["records"]] == list(EXPECTED_STATUSES)
            and len({row["version"] for row in combined["records"]}) == 10
            and combined["records"][:7] == primary["records"][:7],
            "Exactly seven unchanged retained plus three new records required")
    for key, name, digest in (("amendment", "AMENDMENT-2-FROZEN-VERIFICATION-RECOVERY.md", amendment_sha),
                              ("root_decision", "AMENDMENT-2-ROOT-DECISION.json", decision_sha)):
        pin = combined[key]
        require(Path(pin["path"]).resolve() == (HERE / name).resolve() and pin["sha256"] == digest,
                "Combined amendment authority differs")
        check_pin(pin["path"], pin)
    source_pin = combined["source_checkpoint"]
    require(Path(source_pin["path"]).resolve() == (FULL / "code-validation.json").resolve()
            and source_pin["sha256"] == checkpoint_sha
            and source_pin["source_pins"] == 327 and source_pin["unchanged"] is True,
            "Combined source checkpoint differs")
    check_pin(source_pin["path"], source_pin)
    completion = combined["completion_attempt"]
    require(Path(completion["failure_marker"]).resolve() == marker.resolve()
            and completion["status"] == "verified_remaining_three_matching_installed_versions",
            "Completion authority marker/status differs")
    protocol_pin = completion["protocol"]
    require(Path(protocol_pin["path"]).resolve() == (HERE / "FROZEN-COMPLETION-PROTOCOL-v3.json").resolve()
            and protocol_pin["sha256"] == completion_protocol_sha256,
            "Only the separately root-reviewed corrected completion v3 protocol is accepted")
    protocol = read(protocol_pin["path"], completion_protocol_sha256)
    expected_limits = dict(per_replay_seconds=360, metadata_seconds=10, aggregate_seconds=1200,
        finalization_reserve_seconds=30, max_stdout_bytes=1048576, max_stderr_bytes=1048576,
        maximum_metadata_children=3, maximum_replay_children=3, scientific_case_seconds_unchanged=300)
    require(protocol["kind"] == "remaining_three_matching_installed_verifiers_v1"
            and protocol["preparation_revision"] == 3 and protocol["limits"] == expected_limits
            and protocol["reused_versions"] == reused and protocol["remaining_versions"] == remaining
            and protocol["reused_records"] == primary["records"][:7]
            and protocol["reused_reports_never_rerun"] is True and protocol["restart_allowed"] is False
            and Path(protocol["output"]).resolve() == output.resolve()
            and Path(protocol["combined_report"]).resolve() == (HERE / "FROZEN-VERIFIER-COMBINED.json").resolve(),
            "Completion protocol scope differs")
    require(Path(protocol["helper"]["path"]).resolve() == (HERE / "verify_frozen_completion_v3.py").resolve(),
            "Unexpected completion helper")
    check_pin(protocol["helper"]["path"], protocol["helper"])
    require(len(protocol["pinned_files"]) <= 500
            and sum(item["bytes"] for item in protocol["pinned_files"]) <= 32 * 1024 * 1024,
            "Completion pin inventory exceeds reviewed scope")
    for item in protocol["pinned_files"]:
        check_pin(item["path"], item)
    require(Path(completion["report"]["path"]).resolve() == (output / "completion-report.json").resolve(),
            "Completion report path differs")
    finished = read(completion["report"]["path"], completion["report"]["sha256"])
    require(finished["status"] == completion["status"] and "failure" not in finished
            and finished["protocol_sha256"] == completion_protocol_sha256
            and finished["primary_attempt_sha256"] == primary_sha
            and finished["original_primary_status"] == "failed_or_incomplete"
            and finished["records"] == combined["records"][7:]
            and finished["source_pins_unchanged"] == 327
            and finished["retained_success_reports_rechecked"] == 7
            and finished["limits"] == expected_limits
            and finished["automatic_restart"] is False
            and finished["model_calls"] == finished["native_target_calls"] == 0
            and 0 <= finished["elapsed_seconds_before_finalization"] < 1200,
            "Completion report is not a clean bounded success")
    journal_pin = completion["journal"]
    require(Path(journal_pin["path"]).resolve() == (output / "journal.jsonl").resolve(), "Completion journal path differs")
    check_pin(journal_pin["path"], journal_pin)
    events = read_chain(journal_pin["path"])
    require(events[-1]["event"] == "completion_attempt_terminal"
            and events[-1]["details"]["status"] == completion["status"]
            and sum(e["event"] == "completion_child_started" for e in events) == 6
            and sum(e["event"] == "completion_child_terminal" for e in events) == 6
            and sum(e["event"] == "completion_version_verified" for e in events) == 3
            and not any(e["event"] == "build_failed" for e in events), "Completion journal differs")
    require([row["version"] for row in protocol["records"]] == remaining, "Completion record set differs")
    for index, row in enumerate(combined["records"]):
        require(row["expected_version"] == "0.3." + row["version"][2:]
                and row["status"] == row["expected_status"] == EXPECTED_STATUSES[row["version"]]
                and row["version_check_exit_code"] == row["exit_code"] == 0,
                "Matching installed identity/status differs")
        check_pin(row["helper"], row["helper_sha256"])
        check_pin(row["python"], row["python_sha256"])
        payload = read(row["report"], row["report_sha256"])
        require(payload["status"] == row["status"], "Matching report status differs")
        clean_guards(payload)
        if index >= 7:
            planned, original = protocol["records"][index-7], primary["records"][index]
            require(all(row[key] == value for key, value in planned.items()), "Completed record differs from approved plan")
            require(all(row[key] == original[key] for key in ("version", "python", "python_sha256", "helper", "helper_sha256", "expected_status"))
                    and row["primary_args"] == original["args"], "Remaining verifier original identity/inputs differ")
            args = list(original["args"])
            if row["version"] == "038":
                expected_report = output / "038/guarded-installed-verification.json"
                args[-1] = str(expected_report)
            else:
                expected_report = output / (row["version"] + "-report.json")
                args[0], args[1] = str(expected_report), str(output / row["version"])
            require(row["args"] == args and Path(row["report"]).resolve() == expected_report.resolve(),
                    "Only approved fresh report/relocation paths may differ")
        for stage in ("metadata", "replay"):
            call = row[stage]
            require(call["returncode"] == 0 and call["reaped"] is True
                    and call["timed_out"] is False and type(call["pid"]) is int and call["pid"] > 0,
                    "Matching child was not cleanly owned/reaped")
            if index < 7:
                stdout, stderr = call["stdout"], call["stderr"]
            else:
                declared = 10 if stage == "metadata" else 360
                elapsed, effective = call["full_process_elapsed_seconds"], call["effective_seconds"]
                require(type(elapsed) in (int, float) and math.isfinite(elapsed)
                        and type(effective) in (int, float) and math.isfinite(effective)
                        and 0 <= elapsed <= effective <= declared and call["declared_seconds"] == declared
                        and call["spawned"] is True and call["capture_overflow"] is False
                        and call["cleanup_errors"] == [], "Whole-process deadline/capture/cleanup differs")
                expected_argv = ([row["python"], "-I", row["helper"], *row["args"]] if stage == "replay" else None)
                require(expected_argv is None or call["argv"] == expected_argv, "Replay argv differs")
                stdout, stderr = call["stdout"]["path"], call["stderr"]["path"]
                for name in ("stdout", "stderr"):
                    check_pin(call[name]["path"], call[name])
                    stream = call["streams"][name]
                    require(stream["error_class"] is None and stream["truncated"] is False
                            and stream["retained_bytes"] == stream["observed_bytes_at_least"]
                            == proof(call[name]["path"])["bytes"] <= 1048576,
                            "Completion stream is incomplete or exceeds cap")
                terminal = [e for e in events if e["event"] == "completion_child_terminal"
                            and e["details"]["version"] == row["version"] and e["details"]["stage"] == stage]
                require(len(terminal) == 1 and terminal[0]["details"] == call, "Child journal/record differs")
            proof(stdout)
            proof(stderr)
        metadata_stdout = row["metadata"]["stdout"]
        metadata = read(metadata_stdout["path"] if isinstance(metadata_stdout, dict) else metadata_stdout)
        require(metadata == dict(actual=row["expected_version"], expected=row["expected_version"], isolated=True),
                "Matching installed metadata differs")
    require(not marker.exists(), "Late completion failure overrides combined qualification")
    return combined


def full_and_source():
    require(not (FULL / "failure.json").exists(), "Full validation failure marker")
    full = read(FULL / "full-validation.json")
    require(full["status"] == "passed" and full["mode"] == "full"
            and full["tests"] == dict(run=1774, failures=0, errors=0, skipped=[])
            and full["required_probes_exit_code"] == 0 and full["powershell_syntax"] is True
            and full["packaging"]["dependency_free_demo"] == "passed", "Full qualification incomplete")
    code = read(FULL / "code-validation.json")
    require(code["status"] == "passed" and code["exit_code"] == 0
            and code["unchanged_code"] is True and code["protected_unchanged"] is True,
            "Source/protected validation incomplete")
    require(len(code["source_pins"]) == 327
            and read(FULL / "before-source-pins.json") == code["source_pins"], "Source test pins differ")
    for name, digest in code["source_pins"].items():
        check_pin(ROOT / name, digest)
    require(code["protected_hashes"] == PROTECTED, "Protected hash metadata differs")
    for name, digest in PROTECTED.items():
        require(proof(ROOT / name, protected_hash_only=True)["sha256"] == digest,
                "Protected hash changed; content was not decoded")
    before = read(HERE / "BEFORE-IMPLEMENTATION.json")
    require(before["accepted_version"] == "0.3.10" and before["old_v2_cell_count"] == 12,
            "Previous checkpoint differs")
    require(len(before["source_pins"]) == 324, "Previous source scope differs")
    old_pins, current = before["source_pins"], code["source_pins"]
    require(set(current) - set(old_pins) == ADDED_FILES and not set(old_pins) - set(current),
            "Unexpected source additions/removals")
    require({name for name in old_pins if old_pins[name] != current[name]} == METADATA_DELTA,
            "Legacy runtime changed outside approved metadata files")
    require(read(OLD / "acceptance.json", ACCEPTED_0310)["status"]
            == "accepted_native_duration_consistency_engineering_only", "Old acceptance differs")
    profile = read(ROOT / "src/asof/archive/semantic_dependencies.json")
    old_profile_path = ROOT / "data/cache/recovery-step9-duration-wheel-20261028/environment/Lib/site-packages/asof/archive/semantic_dependencies.json"
    old_profile = read(old_profile_path)
    require(profile["previous_resource_sha256"] == proof(old_profile_path)["sha256"], "Profile lineage differs")
    require({name for name in old_profile["modules"] if old_profile["modules"][name] != profile["modules"][name]}
            == {"__init__.py"} and set(old_profile["modules"]) == set(profile["modules"]),
            "Legacy helper profile changed beyond initializer")
    targeted = read(HERE / "TARGETED-COMPLETION.json")
    require(targeted["status"] == "passed" and targeted["tests"] == 58
            and targeted["failures"] == targeted["errors"] == targeted["skips"] == 0,
            "Targeted qualification incomplete")
    for name, digest in targeted["source_pins"].items():
        check_pin(ROOT / name, digest)
    for name in ("REGRESSION-BEFORE.log", "REGRESSION-INPUT-BOUND-BEFORE.log", "REGRESSION-AFTER-37.log", "FULL-VALIDATION.log"):
        proof(HERE / name)
    return full, code, before


def preparations():
    report = read(HERE / "PREPARATION-QUALIFICATION.json")
    require(report["status"] == "passed_retained_preparation_only"
            and report["preparations"] == 18 and report["synthetic_preparations"] == 12
            and report["real_preparations"] == 6 and report["original_v2_fingerprints_unchanged"] == 12,
            "Preparation coverage differs")
    require(report["guards"] == [] and report["native_conformance"] == "unverified"
            and report["native_calls"] == report["model_calls"] == report["tokenizer_children"]
            == report["provider_spend_usd"] == 0, "Preparation authority/execution differs")
    output = Path(report["output"])
    require(not (output / "failure.json").exists(), "Preparation failed")
    receipt = inventory(output, report["receipt_sha256"])
    require(read_chain(output / "journal.jsonl")[-1]["sha256"] == receipt["journal_tip_sha256"],
            "Preparation journal differs")
    require(len(report["records"]) == 18
            and sum(row["development_exposed"] for row in report["records"]) == 6,
            "Exposed preparation count differs")
    for row in report["records"]:
        path = Path(row["preparation_file"]).resolve()
        require(path.is_relative_to(output.resolve()), "Preparation escapes output")
        prepared = read(path)
        require(prepared["interface"] == "source-quote-interpretation-v3-gbnf"
                and prepared["execution_authorized"] is False
                and prepared["native_conformance"] == "unverified", "Preparation contract differs")
        payload, grammar = prepared["payload"], prepared["generation_grammar"]
        require("json_schema" not in payload and payload["grammar"] == grammar["grammar"], "Grammar payload differs")
        require(fingerprint(payload) == row["payload_sha256"] == prepared["payload_sha256"], "Payload binding differs")
        require(fingerprint(grammar) == prepared["generation_contract_sha256"], "Generation binding differs")
        require(fingerprint(prepared["semantic_data"]["original_request"]) == prepared["request_sha256"]
                == row["request_sha256"], "Original request binding differs")
        require(fingerprint(prepared["acceptance_schema"]) == prepared["acceptance_schema_sha256"],
                "Acceptance schema binding differs")
        require(hashlib.sha256(grammar["grammar"].encode("utf-8")).hexdigest()
                == grammar["grammar_sha256"] == row["grammar_sha256"], "Grammar hash differs")
        require(len(payload["prompt"].encode("utf-8")) == row["prompt_bytes"] <= 32768
                and len(canonical(payload)) == row["payload_bytes"] <= 65536,
                "Complete payload byte caps differ")
        require(len(grammar["grammar"].encode("utf-8")) == row["grammar_bytes"] <= 65536,
                "Grammar byte cap differs")
    require(max(row["prompt_bytes"] for row in report["records"]) == 14187
            and max(row["payload_bytes"] for row in report["records"]) == 21872,
            "Measured preparation maxima differ")
    require(report["coverage"] == dict(absence_claim=False, available=9, basis="snapshot_declaration", missing=65, selected=1),
            "Archived source coverage differs")
    return report


def pure_corpus_and_reference():
    pure = read(HERE / "PRODUCTION-PURE-CHECKS-v4.json")
    check_pin(ROOT / "src/asof/study/interpretation_grammar.py", pure["generator_source_sha256"])
    check_pin(HERE / "pure_grammar_probe.py", pure["helper_sha256"])
    require(pure["role"] == "pure_subset_oracle_not_native_qualification" and len(pure["checks"]) == 6,
            "Pure-production evidence differs")
    require([row.get("assertions") for row in pure["checks"] if "assertions" in row] == [262144, 4064],
            "Pure exhaustive scope differs")
    require(all(row.get("passed", True) for row in pure["checks"]), "Pure-production check failed")
    require(all(pure[key] == 0 for key in ("native_calls", "vocabulary_loads", "model_loads", "inference_calls", "servers")),
            "Pure-production execution scope differs")
    artifact_inventory = read(HERE / "CORPUS-EXTENSION-ARTIFACTS.json")
    for name, digest in artifact_inventory["files"].items():
        check_pin(ROOT / name, digest)
    frozen = read(CORPUS / "FROZEN-INPUTS.json", "1b80e365e42b28fe237c22fc35e215d1a0410729203a77255fc628309a9da414")
    for name, digest in frozen["files"].items():
        check_pin(ROOT / name, digest)
    originals = read(ROOT / "data/cache/r09-native-grammar-corpus-20261028/cases.json", ORIGINAL_CORPUS_SHA)
    future = read(CORPUS / "FUTURE-NATIVE-CORPUS-MANIFEST.json", "43aa4b18d3d9c7393198d0eaa93095999d1ef54f0d2757ffe6265c7d95a26e4a")
    results = read(CORPUS / "COMPARISON-RESULTS.json", "95c2c30fa8ef69dca5122e22ce32fe3b636e812d3a8f8f05c685b366e323316a")
    require(len(originals) == 109 and len(results) == len(future["cases"]) == 167
            and frozen["extension_cases"] == 58 and future["execution_authorized"] is False,
            "Frozen corpus coverage/authority differs")
    for row in results:
        require(row["observations"]["strict_accepted"] == row["authored_expectations"]["strict_accepted"],
                "Strict corpus expectation differs")
        expected = row["authored_expectations"]["generation_membership"]
        require(type(expected) is not bool or row["observations"]["pure_grammar_membership"] == expected,
                "Pure corpus authored expectation differs")
    disposition = read(HERE / "SCHEMA-ORACLE-DISPOSITION.json")
    require(disposition["status"] == "qualified_alternative_reference_for_frozen_typed_scope"
            and disposition["reference"]["all167_schema_agreement"] is False
            and disposition["parse_edge_policy"]["graded_with_typed_cases"] is False,
            "Schema/reference scope overstated")
    old_ps = read(CORPUS / "CORPUS-COMPARISON.json", "1e812ea6c82a3e85e1def4fba6b0d5d5c095d3b02c7d7060767f50297affde59")
    require(old_ps["status"] == "expectation_mismatch_stop"
            and read(CORPUS / "COMPARISON-TERMINAL.json")["status"] == "failed"
            and disposition["prior_powershell"]["rerun"] is False
            and disposition["prior_powershell"]["relabelled"] is False, "Original PowerShell failure altered")
    reference_parent = ROOT / "data/cache/r09-jsonschema-reference-parent-20261028"
    inventory(reference_parent, REFERENCE_RECEIPT_SHA)
    require(not (reference_parent / "failure.json").exists(), "Reference parent failed")
    reference = read(ROOT / "data/cache/r09-jsonschema-reference-batch-20261028/REFERENCE-BATCH-RESULT.json", REFERENCE_RESULT_SHA)
    require(reference["status"] == "passed_reference_schema_expectations"
            and reference["typed_schema_cases"] == 162 and reference["unicode_controls"] == 16
            and reference["explicit_parse_edge_cases"] == 5 and reference["guard_attempts"] == [],
            "Reference coverage differs")
    typed = [row for row in reference["cases"] if row["typed_expectation"]]
    edges = [row for row in reference["cases"] if not row["typed_expectation"]]
    require(len(typed) == 162 and all(row["matches_expected"] is True for row in typed)
            and len(edges) == 5 and all(row["matches_expected"] is None for row in edges)
            and len(reference["controls"]) == 16
            and all(row["matches_expected"] is True for row in reference["controls"]),
            "Reference expectations or ungraded edges differ")
    require(all(reference[key] == 0 for key in ("target_native_calls", "model_calls", "tokenizer_calls", "provider_cost_usd")),
            "Reference execution scope differs")
    review = read(HERE / "REFERENCE-RESULT-VERIFICATION.json", "3303dbd2c7b0b43f1bfc2226e6b817b7e49433cc32bc0fb6276453c25d872636")
    require(review["status"] == "verified_once_only_reference_batch_pass_with_unscored_parser_edges"
            and review["protocol_input_and_code_pins_verified"] == 296
            and review["package_files_verified"] == 139, "Independent reference audit differs")
    return pure, disposition, edges


def check_dependency_metadata(metadata, project):
    """Pure packaging assertion; not a wheel build or acceptance execution."""
    optional = project["project"]["optional-dependencies"]
    require(project["project"].get("dependencies", []) == []
            and optional == {"ingest": ["pyarrow==21.0.0"]},
            "Project default/optional dependency metadata differs")
    require(metadata.get_all("Provides-Extra", []) == list(optional),
            "Wheel Provides-Extra differs from project ingest extra")
    dependencies = metadata.get_all("Requires-Dist", [])
    require(len(dependencies) == 1 and re.fullmatch(
        r'pyarrow\s*==\s*21\.0\.0\s*;\s*extra\s*==\s*[\x22\x27]ingest[\x22\x27]', dependencies[0]),
        "Default dependency-free metadata differs")


def check_optional_arrow_copy(package, target):
    """Amendment 3: 755 exact old bytes plus only five approved derived caches."""
    derivation_sha = "22462459f61495c2107a495eb64c9871f6e2f9015d2a6c24d6b1441b4b4406fd"
    peer_sha = "53f96fc28eec3296ca9183dcda8f7c1e8b54739faa4e4eab71f9a85c11e93e85"
    decision_sha = "8b7f1b3fababf691bacf86d7dc33a73562b0a7b8aa9ed47e26be72316cbbc24a"
    amendment_sha = "369c8e019535114a7304bca11a9550ca10127b5d195cd4d40b56daaaa25ba92f"
    probe_sha = "621dbfa08a498f8fca475b0c5af2e238aa010a47f5431b14d8ad93081002d90a"
    note_sha = "459a22a3f6524aeec6f3dbcd37381fa0d178b3a742aea268e885021b57693752"
    decision = read(HERE / "OPTIONAL-ARROW-ROOT-DECISION.json", decision_sha)
    require(decision["decision"] == "approve_exact_five_optional_cache_derivations_and_prepare_narrow_acceptance_v4"
            and decision["derivation_sha256"] == derivation_sha
            and decision["independent_review_sha256"] == peer_sha
            and decision["amendment_sha256"] == amendment_sha
            and decision["representation_probe_sha256"] == probe_sha
            and decision["serialization_note_sha256"] == note_sha
            and decision["blanket_cache_exception"] is False
            and decision["source_runtime_wheel_or_environment_changes_authorized"] is False
            and decision["all_other_acceptance_gates_unchanged"] is True,
            "Exact optional-cache approval differs")
    check_pin(HERE / "AMENDMENT-3-OPTIONAL-ENVIRONMENT-CACHES.md", amendment_sha)
    check_pin(HERE / "BYTECODE-SERIALIZATION-NOTE.md", note_sha)
    probe = read(HERE / "OPTIONAL-ARROW-MARSHAL-REPRESENTATION-PROBE.json", probe_sha)
    require(probe["status"] == "resolved_observed_marshal_reference_flag_representation_difference"
            and probe["author_record_sha256"] == derivation_sha
            and probe["source_code_objects_executed"] == probe["arrow_imports"] == probe["model_calls"] == 0,
            "Bytecode representation qualification differs")
    record = read(HERE / "OPTIONAL-ARROW-DIAGNOSIS.json", derivation_sha)
    peer = read(HERE / "OPTIONAL-ARROW-PEER-REVIEW-v3.json", peer_sha)
    require(record["status"] == "verified_five_source_equivalent_recompiled_caches_not_760_byte_identity"
            and record["copied_files_checked"] == record["original_source_files_still_match_copy_pins"] == 760
            and record["byte_identical_to_copy_pins"] == 755 and record["changed_files"] == 5
            and record["missing_files"] == record["unlisted_files"] == [], "Derivation scope differs")
    require(peer["status"] == "passed_independent_exact_five_cache_derivation_review"
            and peer["author_record_expected_sha256"] == derivation_sha
            and peer["original_source_files_still_match"] == peer["target_files_rehashed"] == 760
            and peer["unchanged_target_files"] == 755 and peer["individually_qualified_changed_caches"] == 5
            and peer["record_hashed_rows_verified"] == 751
            and peer["reparse_and_link_checks"]["violations"] == [] and peer["guard_attempts"] == []
            and peer["source_code_objects_executed"] == peer["actual_package_imports"]
            == peer["environment_files_modified_or_repaired"] == 0,
            "Independent cache qualification differs")
    check_pin(HERE / "diagnose_optional_arrow.py", record["helper_sha256"])
    require(record["copy_manifest"] == proof(HERE / "WHEEL-ENVIRONMENTS.json"), "Copy manifest differs")
    source = ROOT / "data/cache/recovery-step9-token-aware-wheel-20261026/environment-v2/Lib/site-packages"
    require(Path(record["source_site"]).resolve() == source.resolve()
            and Path(record["target_site"]).resolve() == Path(target).resolve(), "Approved optional sites differ")
    modules = {"__init__", "_generated_version", "ipc", "types", "util"}
    allowed = {f"pyarrow/__pycache__/{name}.cpython-311.pyc" for name in modules}
    require(set(decision["exact_qualified_cache_modules"]) == modules
            and decision["original_copy_files"] == 760 and decision["unchanged_files_required"] == 755,
            "No additional cache exceptions permitted")
    entries = {item["relative_path"]: item for item in package["copied_existing_arrow_files"]}
    recorded = {item["relative_path"]: item for item in record["all_files"]}
    caches = {item["cache_relative_path"]: item for item in record["bytecode_derivations"]}
    peer_caches = {item["cache"]: item for item in peer["caches"]}
    require(len(entries) == len(recorded) == 760 and set(entries) == set(recorded)
            and len(caches) == len(peer_caches) == 5 and set(caches) == set(peer_caches) == allowed,
            "Optional-file/cache universe differs")
    def file_universe(site):
        files = set()
        checked = set()
        def inspect(path):
            path = Path(path).absolute()
            if path in checked:
                return path.lstat()
            value = path.lstat()
            require(not path.is_symlink() and not (getattr(value, "st_file_attributes", 0) & 0x400),
                    "Optional package contains symlink/reparse path: " + str(path))
            checked.add(path)
            return value
        # Check approved-root ancestors too; never traverse a linked package root.
        for path in (Path(site).absolute(), *Path(site).absolute().parents):
            if path == ROOT.parent:
                break
            inspect(path)
        def walk(path):
            inspect(path)
            if path.is_dir():
                for child in path.iterdir():
                    walk(child)
            else:
                require(path.is_file(), "Optional package entry is not a regular file")
                files.add(path.relative_to(site).as_posix())
        for folder in ("pyarrow", "pyarrow.libs", "pyarrow-21.0.0.dist-info"):
            walk(Path(site) / folder)
        require(files == set(entries), "Missing or additional optional package file")
    file_universe(source)
    file_universe(Path(target))
    changed = set()
    for relative, original in entries.items():
        value = PurePosixPath(relative)
        require(not value.is_absolute() and ".." not in value.parts, "Unsafe optional member")
        old_pin = {key: original[key] for key in ("sha256", "bytes")}
        require(recorded[relative]["copy_time"] == old_pin
                and recorded[relative]["source_still_matches_copy_pin"] is True,
                "Original optional-copy binding differs")
        check_pin(source / relative, old_pin)
        if relative not in allowed:
            require(recorded[relative]["changed"] is False and recorded[relative]["current"] == old_pin,
                    "Unapproved optional file changed")
            check_pin(Path(target) / relative, old_pin)
            continue
        item, independent = caches[relative], peer_caches[relative]
        require(recorded[relative]["changed"] is True and item["original_cache"] == old_pin
                and item["current_cache"] == recorded[relative]["current"]
                and independent["original_sha256"] == old_pin["sha256"]
                and independent["current_sha256"] == item["current_cache"]["sha256"],
                "Qualified cache hash binding differs")
        check_pin(Path(target) / relative, item["current_cache"])
        module = Path(relative).name.split(".cpython-")[0]
        source_relative = f"pyarrow/{module}.py"
        require(item["source_relative_path"] == independent["source"] == source_relative
                and item["source"]["sha256"] == independent["source_sha256"]
                and item["source_unchanged"] is True
                and item["current_compiler_filename"] == str(Path(target) / source_relative)
                and item["original_compiler_filename"] == str(source / source_relative),
                "Qualified cache/source/filename binding differs")
        check_pin(source / source_relative, item["source"])
        check_pin(Path(target) / source_relative, item["source"])
        require(item["current_marshaled_payload_exactly_matches_source_compile"] is True
                and item["original_marshaled_payload_exactly_matches_source_compile"] is True
                and item["all_recursive_code_fields_except_filename_match"] is True
                and independent["old_and_current_complete_marshaled_payloads_match_nonexecuted_compile"] is True
                and independent["only_recursive_field_difference"] == "co_filename"
                and independent["all_expected_paths_verified"] is True
                and independent["source_headers_match"] is True, "Qualified compilation proof differs")
        contents = (Path(target) / relative).read_bytes()
        source_stat = (Path(target) / source_relative).stat()
        require(contents[:4].hex() == item["current_header"]["magic_hex"] == independent["magic_hex"]
                and int.from_bytes(contents[4:8], "little") == item["current_header"]["flags"] == independent["flags"] == 0
                and int.from_bytes(contents[8:12], "little") == int(source_stat.st_mtime) & 0xFFFFFFFF
                and int.from_bytes(contents[12:16], "little") == source_stat.st_size & 0xFFFFFFFF,
                "Current qualified cache/source header differs")
        changed.add(relative)
    require(changed == allowed and len(entries) - len(changed) == 755,
            "Expected exactly five derived caches and 755 unchanged files")


def wheel_and_installed():
    package = read(HERE / "WHEEL-ENVIRONMENTS.json")
    require(package["status"] == "offline_wheel_and_two_installed_environments_verified"
            and package["version"] == "0.3.11" and package["wheel_sha256"] == WHEEL_SHA
            and package["wheel_runtime_resources_checked"] == 85
            and package["default_runtime_dependencies"] == []
            and package["optional_pyarrow_version"] == "21.0.0" and package["new_downloads"] == 0,
            "Wheel/environment qualification differs")
    require(all(command["exit_code"] == 0 for command in package["commands"]), "Package command failed")
    check_pin(package["wheel"], WHEEL_SHA)
    environments = [Path(package[key]).parents[1] / "Lib/site-packages"
                    for key in ("default_python", "ingestion_python")]
    with zipfile.ZipFile(package["wheel"]) as archive:
        names = [name for name in archive.namelist() if name.startswith("asof/") and not name.endswith("/")]
        require(len(names) == len(set(names)) == 85, "Wheel runtime member count differs")
        for name in names:
            relative = PurePosixPath(name)
            require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe wheel member")
            value = archive.read(name)
            digest = hashlib.sha256(value).hexdigest()
            check_pin(ROOT / "src" / name, dict(sha256=digest, bytes=len(value)))
            for site in environments:
                check_pin(site / name, dict(sha256=digest, bytes=len(value)))
        metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        metadata = Parser().parsestr(archive.read(metadata_name).decode("utf-8"))
        require(metadata["Version"] == "0.3.11", "Wheel version differs")
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        check_dependency_metadata(metadata, project)
    require(not (environments[0] / "pyarrow").exists(), "Default runtime contains PyArrow")
    check_optional_arrow_copy(package, environments[1])
    preserved = read(HERE / "WHEEL-PRESERVATION.json")
    require(preserved["status"] == "preserved_build_pending_full_milestone_acceptance"
            and preserved["version"] == "0.3.11" and len(preserved["files"]) == 3,
            "Wheel preservation evidence differs")
    for item in preserved["files"]:
        check_pin(item["source"], item)
        check_pin(item["preserved"], item)
    installed = read(INSTALLED / "guarded-installed-verification.json")
    require(installed["status"] == "passed" and installed["isolated_mode"] is True
            and installed["receipt_bytes_rewritten"] is False, "Installed validation failed")
    for key in ("original_root_access_attempts", "archived_execution_attempts", "repository_tools_import_attempts", "network_or_child_attempts"):
        require(installed[key] == [], "Installed guard violation")
    require(len(installed["results"]) == 7 and all(row["status"] == "passed" for row in installed["results"]),
            "Seven installed legacy families incomplete")
    generated = installed["installed_generation_v3"]
    require(generated["stage_count"] == len(generated["stages"]) == 12
            and generated["state_validations"] == 36
            and generated["negative_case_count"] == len(set(generated["rejected"])) == 74
            and generated["execution_authorized"] is False
            and generated["native_conformance"] == "unverified", "Installed v3 scope differs")
    require(all(generated[key] == 0 for key in ("actual_model_calls", "tokenizer_calls", "native_processes", "network_calls")),
            "Installed v3 execution scope differs")
    for row in generated["stages"]:
        require(row["deeply_immutable"] is True and {state["state"] for state in row["states"]}
                == {"answered", "partial", "abstained"}, "Installed states/immutability differ")
    relocation = generated["relocation"]
    require(relocation["kind"] == "plain_json_pure_artifact_relocation_only"
            and relocation["original_json_reads_denied"] is True
            and relocation["archived_code_executed"] is False
            and relocation["new_native_or_dossier_family"] is False, "Relocation scope differs")
    anchor = read(relocation["external_anchor"], relocation["external_anchor_sha256"])
    require(anchor["receipt_sha256"] == relocation["external_expected_receipt_sha256"], "Relocation anchor differs")
    for directory in (Path(relocation["original"]), Path(relocation["copied"])):
        receipt = read(directory / "receipt.json", anchor["receipt_sha256"])
        for name, digest in receipt["files"].items():
            check_pin(directory / name, digest)
        fixture = read(directory / "fixture.json", anchor["fixture_sha256"])
        require(fingerprint(fixture["preparation"]) == receipt["preparation_sha256"]
                and fingerprint(fixture["validated_response"]) == receipt["validated_response_sha256"],
                "Relocated plain JSON binding differs")
    return package, installed


def preserved_negative():
    old = read(GRAMMAR_PHASE / "FINAL-CHECK.json")
    require(old["status"] == "passed" and old["native_gate"] == "sealed_negative"
            and old["entire_R09_complete"] is False, "Original native negative differs")
    run = ROOT / "data/cache/r09-finite-converter-execution-20261028T043655Z"
    receipt = inventory(run, "73c3f2bede92d2f51238831dea8012e3e4d20a0dd9655002d9f51432bdefcaa4")
    seal = read(run / "seal-state.json", "2d1d4eff84ec786907fba754eb46c5db610463384708b2a5ba23869708866ffe")
    require(not (run / "failure.json").exists()
            and seal["receipt"] == proof(run / "receipt.json")
            and receipt["disposition"] == seal["disposition"] == "closed_negative_conversion_incomplete_warning",
            "Original negative converter seal differs")
    require(read_chain(run / "journal.jsonl")[-1]["sha256"] == receipt["journal_tip_sha256"],
            "Original negative converter journal differs")
    return old


def publish_acceptance(payload):
    """Windows same-directory publication: existing destination always fails."""
    require(os.name == "nt", "Windows non-overwriting rename publication only")
    directory = HERE.resolve(strict=True)
    descriptor, temporary = tempfile.mkstemp(prefix="acceptance-pending-", suffix=".json", dir=directory)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # On Windows os.rename refuses any existing destination; never use replace.
        os.rename(temporary, directory / "acceptance.json")
    finally:
        Path(temporary).unlink(missing_ok=True)


def main():
    require(not (HERE / "acceptance.json").exists(), "Acceptance already exists; no replacement")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--combined-sha256", required=True)
    parser.add_argument("--completion-protocol-sha256", required=True)
    arguments = parser.parse_args()
    frozen = matching_verifiers(arguments.combined_sha256, arguments.completion_protocol_sha256)
    full, code, before = full_and_source()
    preparation = preparations()
    pure, schema_disposition, edges = pure_corpus_and_reference()
    package, installed = wheel_and_installed()
    preserved_negative()
    proof(__file__)
    # Detect any change during aggregation. This rehashes bytes only; it does not
    # rerun tests, reference tools, archived verifiers or protected decoders.
    for name, expected in list(EVIDENCE.items()):
        path = Path(name) if Path(name).is_absolute() else ROOT / name
        require(proof(path, protected_hash_only=name in PROTECTED) == expected,
                "Evidence changed during aggregation: " + name)
    require(not Path(frozen["completion_attempt"]["failure_marker"]).exists(),
            "Late completion failure vetoes acceptance")
    report = dict(
        schema_version=1, status="accepted_pure_generation_contract_engineering_only",
        accepted_at_utc=datetime.now(timezone.utc).isoformat(), version="0.3.11",
        previous_accepted_version="0.3.10", previous_acceptance_sha256=ACCEPTED_0310,
        helper_sha256=proof(__file__)["sha256"], tests=full["tests"],
        full_validation_seconds=full["elapsed_seconds"], source_pins=code["source_pins"],
        protected_hash_only_checks=PROTECTED, protected_payloads_decoded=False,
        source_metadata_only_delta=sorted(METADATA_DELTA), new_files=sorted(ADDED_FILES),
        old_v2_payload_fingerprints_retained=before["old_v2_cell_count"],
        matching_verifiers=len(frozen["records"]), matching_verifier_status=frozen["status"],
        matching_verifier_qualification=dict(primary_attempt="failed_at_038_preserved",
            retained_successes=7, declared_completion_successes=3,
            combined_sha256=arguments.combined_sha256, completion_protocol_sha256=arguments.completion_protocol_sha256,
            original_attempt_relabelled=False, scientific_case_budget_seconds_unchanged=300),
        preparations=dict(total=18, synthetic=12, development_exposed=6,
                          max_prompt_bytes=14187, max_http_payload_bytes=21872,
                          archived_source_coverage=preparation["coverage"]),
        reference=dict(typed_expectations_matched=162, unicode_controls_matched=16,
                       parser_dependent_ungraded=edges, all167_agreement_claim=False),
        original_powershell_failure="preserved_not_relabelled_or_rerun",
        original_converter_gate="preserved_sealed_negative_before_vocabulary",
        corpus=dict(original=109, extension=58, native_execution=False),
        installed=dict(legacy_families=7, v3_stages=12, state_validations=36,
                       negative_cases=74, relocation="plain_json_pure_artifact_only"),
        wheel=dict(sha256=WHEEL_SHA, runtime_members=85, installed_environments=2,
                   default_runtime_dependencies=[], optional_pyarrow="21.0.0"),
        optional_arrow_cache_derivation=dict(original_copy_files=760, byte_identical_copy_files=755,
            exact_qualified_changed_caches=5, blanket_exception=False, environment_or_receipts_rewritten=False,
            derivation_sha256="22462459f61495c2107a495eb64c9871f6e2f9015d2a6c24d6b1441b4b4406fd",
            independent_review_sha256="53f96fc28eec3296ca9183dcda8f7c1e8b54739faa4e4eab71f9a85c11e93e85",
            root_decision_sha256="8b7f1b3fababf691bacf86d7dc33a73562b0a7b8aa9ed47e26be72316cbbc24a",
            amendment_sha256="369c8e019535114a7304bca11a9550ca10127b5d195cd4d40b56daaaa25ba92f",
            serialization_note_sha256="459a22a3f6524aeec6f3dbcd37381fa0d178b3a742aea268e885021b57693752",
            caches=["pyarrow/__pycache__/" + name + ".cpython-311.pyc"
                    for name in ("__init__", "_generated_version", "ipc", "types", "util")]),
        new_v3_execution_authorized=False, existing_default_route="unchanged_v2",
        actual_0311_native_target_calls=0, actual_model_calls=0, vocabulary_loads=0,
        provider_spend_usd=0, native_conformance="unverified", scientific_validation="not_established",
        clinical_probability=None, entire_R09_complete=False, entire_project_complete=False,
        remaining=["actual pinned-DLL grammar/document/EOG qualification under a separately approved protocol",
                   "full-case resource feasibility including actual startup/inference; preserve 295.922/300-second simulation",
                   "independent human scientific reviews and sufficient/fresh source-qualified cases",
                   "later R10-R16 scientific/evaluation milestones and conditional branches"],
        evidence_files=dict(sorted(EVIDENCE.items())),
        reviewer_execution="stdlib metadata/hash/ZIP inspection only; no archive/runtime code execution or source downloads",
    )
    payload = json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False).encode("utf-8") + b"\n"
    publish_acceptance(payload)
    print(json.dumps(dict(status=report["status"], acceptance=str(HERE / "acceptance.json"),
                          sha256=hashlib.sha256(payload).hexdigest())))


if __name__ == "__main__":
    main()
