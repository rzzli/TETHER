"""Retain exact terminal gates and emit a public, value-free qualification record.

Post-result release metadata only. No provider originals or answer records read.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PROTOCOL = "e28461a5681bcaaae89752f0cf7e1ac6fb644c4eebdf501a1f2c2ec7c26dd529"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def proof(path):
    raw = path.read_bytes()
    return {"sha256": sha(raw), "bytes": len(raw)}


def main():
    lanes = {}
    for mode, stamp, expected, skips in (
        ("core", "20261101T224500Z", "e42fd680941a24f9783cddeea5c41e66dcdba6a3ac406e7226530fcff04be85d", 94),
        ("full", "20261101T224000Z", "369466b5739f7cb4658f40a066027b90d615914f507353e771c62dc8c584c98b", 0),
    ):
        raw = (ROOT / f"data/cache/p09-{mode}-validation-v3-{stamp}.json").read_bytes()
        report = json.loads(raw)
        assert sha(raw) == expected
        assert report["status"] == "passed" and report["mode"] == mode
        assert report["tests"]["run"] == 1973
        assert report["tests"]["failures"] == report["tests"]["errors"] == 0
        assert len(report["tests"]["skipped"]) == skips
        assert report["required_probes_exit_code"] == 0 and report["powershell_syntax"] is True
        assert report["packaging"]["package_network_policy"] == "offline"
        assert report["packaging"]["dependency_free_demo"] == "passed"
        target = HERE / f"{mode.upper()}-VALIDATION-v3.json"
        if target.exists():
            assert target.read_bytes() == raw
        else:
            with target.open("xb") as stream:
                stream.write(raw)
        lanes[mode] = {
            "report_sha256": expected, "tests_collected": 1973,
            "tests_executed": 1973 - skips, "approved_optional_skips": skips,
            "failures": 0, "errors": 0, "required_probes_exit_code": 0,
            "elapsed_seconds": report["elapsed_seconds"],
            "packaging": report["packaging"],
            "skip_reasons": sorted({x["reason"] for x in report["tests"]["skipped"]}),
        }
    suites = {}
    for name, filename, count in (
        ("p05_separate", "P05-COMPLETE-REGRESSIONS-v1.txt", 199),
        ("installed_fictional_no_bytecode", "INSTALLED-NO-BYTECODE-TESTS-v2.txt", 82),
        ("release_preparation", "ROOT-PREPARATION-AND-PACKAGE-TESTS-final-v3.txt", 40),
    ):
        path = HERE / filename
        text = path.read_text(encoding="utf-8-sig")
        assert re.search(rf"Ran {count} tests in [0-9.]+s\s+OK(?:\s|$)", text)
        suites[name] = {"tests": count, "status": "passed", "log": proof(path)}
    metadata_path = HERE / "ACTUAL-QUALIFICATION-PEER-REVIEW-v2.json"
    metadata = json.loads(metadata_path.read_bytes())
    assert metadata["check_count"] == 3481 and metadata["unresolved_findings"] == []
    assert metadata["external_READY_sha256"] == PROTOCOL
    record = {
        "schema_version": 1, "method": "p09.public_release_qualification.v1",
        "status": "PASS_LOCAL_WINDOWS_RESEARCH_ARTIFACT", "role": "evaluation_only",
        "agent_visible": False, "scientific_validation": "not_established",
        "study_independence": "not_established", "publication_authorized": False,
        "owner_declarations": "deferred", "protocol_sha256": PROTOCOL,
        "qualified_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_commit_for_framework_gates": "3629337cda1e033228df67cb9c0046d6d9cc9049",
        "environment": {"platform": "Windows x64", "python": "3.11.15", "pyarrow": "21.0.0",
            "core_gate_pyarrow": "absent", "core_runtime": "0.3.11", "replay_distribution": "0.1.0"},
        "native_reconstruction": {
            "complete_originals": 137, "receipt_files": 137,
            "original_bytes": 2866248239, "receipt_bytes": 116051,
            "native_units": 12, "constructed_controls": 14,
            "reproduced_output_hashes": 38, "recomputed_policy_decisions": 90,
            "wall_seconds": 289.938, "cpu_seconds": 269.390625,
            "process_peak_bytes": 481636352,
            "report_sha256": "a0f4e0e76ad5dfd746664c69023549cb0bf23fd74316b02a40ef85c54bfd8acb",
            "receipt_sha256": "b184839bdedea102e022786de51bd7fcec062e2eb232c45699b6d55444814b8e",
        },
        "separate_source_audit": {
            "status": "passed", "checks": 6862, "unresolved_findings": [],
            "wall_seconds": 15.187, "cpu_seconds": 14.578125, "process_peak_bytes": 298418176,
            "report_sha256": "b7e8bdd49fe0a29a78277a65ba627e405b652b6aa5e060f930796421958f62ca",
            "receipt_sha256": "c981dfe9d5964b8be6d2fd49ccdfc5300be3eeb60628c2ae8f998c1fbbbe1977",
            "shares_core_dependencies": True, "independent_scientific_adjudication": False,
        },
        "sealed_metadata_peer_review": {"checks": 3481, **proof(metadata_path), "provider_sources_reopened": False},
        "framework_gates": lanes, "additional_test_suites": suites,
        "scope_notes": [
            "Post-result technical qualification; original P06 results and costs remain unchanged.",
            "Source generation precedes evaluator-bridge comparison; no native answer values in this record.",
            "Historical reference equivalence removes only method.catalog_sha256; genuine public references have new fingerprints.",
            "New G0 checks declared byte bindings under external authority; provider authenticity and old private-archive integrity are not established.",
            "All complete originals are mandatory; selected-row extracts are insufficient.",
            "136 Open Targets originals remain external; fresh exact-byte reacquisition is untested.",
            "Exact CC0 HGNC original and project receipt metadata are included under explicit allowlists.",
            "Original model branch remains closed; no clinical, causal, study-independence or model-superiority result follows.",
            "Earlier failed validation runs and initial reconstruction revision remain retained.",
            "Framework lanes, separate suites and source checks overlap; counts are not additive independent samples.",
        ],
        "unsupported_or_unmeasured": {"native_linux_replay": "not_qualified", "current_hosted_ci": "not_executed",
            "fresh_external_reacquisition": "untested", "total_physical_io_bytes": None,
            "total_platform_cost_usd": None, "public_deposit": None},
        "provider_spending_usd": 0, "new_model_calls": 0, "new_provider_downloads": 0,
    }
    target = ROOT / "paper/release/qualification.json"
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": record["status"], "qualification": proof(target), "retained_terminal_reports": 2}))


if __name__ == "__main__":
    main()
