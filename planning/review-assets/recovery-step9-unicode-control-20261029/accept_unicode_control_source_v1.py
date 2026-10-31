"""Close the source fixture gate using only this new fixture directory.

Does not run a validator, open a payload, load native code or qualify runtime.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PINS = {
    "UNICODE-CONTROL-FIXTURE-FREEZE-v1.json": "e6e8419c0ad37db007263de0a57e0ce66a20f7481f35686427076ea36c7106b3",
    "UNICODE-CONTROL-CORPUS-v1.json": "13e2c2f2900802729c0d39fa9b7851c56ab3db6afdc45c4b15c2f7f80bd6523c",
    "UNICODE-CONTROL-STAGES-v1.json": "ad688168a366d5e95413ec69731d030c54431663e6574fb93445ced2b580413a",
    "UNICODE-CONTROL-CONTRACT-v2.json": "65a34539dd1bdecb20ed85724c58f80e362113cb4db969f5edf60b48af9a111d",
    "UNICODE-CONTROL-PROFILE-v2.md": "f6512f48ffd58756e96ea1655df05824e4ccb2588cbe19264cd21e8b1bd27dbf",
    "UNICODE-CONTROL-STRUCTURAL-CHECKS-v1.json": "6e62f04b8f701e9a358c9bc8ab2c3872723a59d2218cc4bedfd23a0c06c0b3da",
    "UNICODE-CONTROL-CORPUS-MANUAL-PRECHECK-v1.json": "77b7f3f9ec2d069ae6b4357ff16ea2f4ced9e520ee3b2230995c7aa9038dc04a",
    "UNICODE-CONTROL-INDEPENDENT-SEMANTIC-PROOF-v1.json": "739d83dff80490175a6b18e0a4e40b209d752e6eef9bcc39a762fd098333e057",
    "check_unicode_control_semantics_v1.py": "4ba76c9b2d0fb59aa200bd98a5f97eb7d20e7828a003d92629e8d55b94e25bd7",
}


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    blobs, pins = {}, {}
    for name, expected in PINS.items():
        data = (ROOT / name).read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        require(actual == expected, "Source fixture pin mismatch: " + name)
        blobs[name] = data
        pins[name] = {"bytes": len(data), "sha256": actual}
    freeze = json.loads(blobs["UNICODE-CONTROL-FIXTURE-FREEZE-v1.json"])
    structural = json.loads(blobs["UNICODE-CONTROL-STRUCTURAL-CHECKS-v1.json"])
    independent = json.loads(blobs["UNICODE-CONTROL-INDEPENDENT-SEMANTIC-PROOF-v1.json"])
    corpus = json.loads(blobs["UNICODE-CONTROL-CORPUS-v1.json"])
    require(freeze["execution_authorized"] is False, "Freeze cannot grant execution")
    require(structural["status"] == "passed" and structural["methods"] == 7, "Structural gate")
    require(structural["errors"] == [] and structural["failures"] == [], "Structural failures")
    require(independent["status"] == "passed" and independent["errors"] == [], "Independent gate")
    require(independent["audit_denials"] == [], "Independent activity denial")
    require(independent["freeze_sha256"] == PINS["UNICODE-CONTROL-FIXTURE-FREEZE-v1.json"], "Frozen reference")
    require(len(independent["case_checks"]) == len(corpus["cases"]) == 84, "Case completeness")
    for case, observation in zip(corpus["cases"], independent["case_checks"]):
        require(case["id"] == observation["id"] and observation["matched"] is True, "Case mismatch")
        require(observation["native_observation"] is None and observation["mismatches"] == [], "No native observations")
    require(len(independent["stage_checks"]) == 4, "Stage completeness")
    require(all(row["full_actual_v3_preparation_equal"] is True for row in independent["stage_checks"]), "Stage mismatch")
    for key in ("tokenizer_calls", "target_native_calls", "SDK_constructions", "CPU_GGUF_oldpack_operations", "bridge_pack_runtime_implementations"):
        require(independent[key] == 0, "Unexpected activity: " + key)
    expected = {"cases": 84, "coverage_population": 68, "native_byte_eligible": 78,
                "expected_native_members": 69, "expected_native_nonmembers": 9,
                "null_native_membership": 6, "v3_semantic_true": 71,
                "ASCII_pairs": 14, "max_document_bytes": 420}
    require(all(independent["counts"][key] == value for key, value in expected.items()), "Count mismatch")
    report = {
        "schema_version": 1,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACCEPTED_SOURCE_ONLY_FROZEN_FULL_RESPONSE_FIXTURES",
        "scope": "Frozen exact bytes, actual v3 preparation/post-validation and structural expectations; not native membership or tokenizer coverage.",
        "inputs": pins,
        "structural_methods": 7,
        "independent_counts": independent["counts"],
        "independent_seconds": independent["elapsed_seconds"],
        "execution_authorized": False,
        "native_conformance": "unverified",
        "scientific_validation": "not_established",
        "old_profile": "FAILED, unchanged",
        "old_external_verification": "INCOMPLETE_TIMEOUT, unchanged",
        "next": ["Frozen synthetic ledger vectors and pure analyzer", "Trusted-origin handoff and real captured-byte checkers", "Exact wire/platform/source/budget review before any runtime decision"],
    }
    destination = ROOT / "UNICODE-CONTROL-SCOPED-ACCEPTANCE-v1.json"
    with destination.open("xb") as stream:
        stream.write((json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": report["status"], "path": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
