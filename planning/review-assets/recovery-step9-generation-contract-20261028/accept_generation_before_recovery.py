"""DRAFT: qualify retained pure-generation evidence; do not run before root review.

This helper imports no project/runtime code and launches nothing.  It cannot
accept the failed original matching-verifier attempt. A separately approved
recovery/combined qualification would need an explicit prospective amendment to
this helper; an old failed report must never be relabeled to satisfy it.

Only after every check passes is a new, exclusive acceptance.json written.
"""

from datetime import datetime, timezone
from email.parser import Parser
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
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


def matching_verifiers():
    # Hard stop: the failed original attempt cannot become ten qualified results.
    require(not (FROZEN_CACHE / "failure.json").exists(),
            "Original verifier attempt failed; explicit prospective recovery qualification required")
    require(not (HERE / "FROZEN-VERIFIER-FINALIZATION-FAILURE.json").exists(),
            "Authoritative verifier finalization failure")
    summary = read(HERE / "FROZEN-VERIFIER-CHECKS.json")
    require(summary["status"] == "passed_all_ten_matching_installed_verifiers"
            and "failure" not in summary, "All ten matching verifiers are not qualified")
    require(summary["actual_native_execution_authorized"] is False
            and summary["restart_allowed"] is False, "Verifier scope changed")
    require([row["version"] for row in summary["records"]] == list(EXPECTED_STATUSES),
            "Matching verifier identities/order differ")
    check_pin(HERE / "verify_frozen_all.py", summary["helper_sha256"])
    require(summary["elapsed_seconds_before_report"] < summary["overall_timeout_seconds"],
            "Verifier aggregate budget exceeded")
    for row in summary["records"]:
        require(row["expected_version"] == "0.3." + row["version"][2:], "Installed version mapping differs")
        require(row["status"] == row["expected_status"] == EXPECTED_STATUSES[row["version"]],
                "Matching verifier status differs")
        require(row["version_check_exit_code"] == row["exit_code"] == 0, "Verifier exit differs")
        check_pin(row["helper"], row["helper_sha256"])
        check_pin(row["python"], row["python_sha256"])
        payload = read(row["report"], row["report_sha256"])
        require(payload["status"] == row["status"], "Matching report status differs")
        clean_guards(payload)
        for stage in ("metadata", "replay"):
            call = row[stage]
            require(call["returncode"] == 0 and call["reaped"] is True
                    and call["timed_out"] is False and type(call["pid"]) is int,
                    "Matching child was not cleanly owned/reaped")
            proof(call["stdout"])
            proof(call["stderr"])
        metadata = read(row["metadata"]["stdout"])
        require(metadata == dict(actual=row["expected_version"], expected=row["expected_version"], isolated=True),
                "Matching installed metadata differs")
    return summary


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
        dependencies = metadata.get_all("Requires-Dist", [])
        require(len(dependencies) == 1 and re.fullmatch(
            r'pyarrow\s*==\s*21\.0\.0\s*;\s*extra\s*==\s*[\x22\x27]ingestion[\x22\x27]', dependencies[0]),
            "Default dependency-free metadata differs")
    require(not (environments[0] / "pyarrow").exists(), "Default runtime contains PyArrow")
    require(len(package["copied_existing_arrow_files"]) == 760, "Optional Arrow closure differs")
    for item in package["copied_existing_arrow_files"]:
        check_pin(environments[1] / item["relative_path"], item)
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


def main():
    require(not (HERE / "acceptance.json").exists(), "Acceptance already exists; no replacement")
    # This currently refuses the failed original attempt. Do not bypass it.
    frozen = matching_verifiers()
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
    descriptor, temporary = tempfile.mkstemp(prefix="acceptance-pending-", suffix=".json", dir=HERE)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # Exclusive publication; os.link never replaces an existing acceptance.
        os.link(temporary, HERE / "acceptance.json")
    finally:
        Path(temporary).unlink(missing_ok=True)
    print(json.dumps(dict(status=report["status"], acceptance=str(HERE / "acceptance.json"),
                          sha256=hashlib.sha256(payload).hexdigest())))


if __name__ == "__main__":
    main()
