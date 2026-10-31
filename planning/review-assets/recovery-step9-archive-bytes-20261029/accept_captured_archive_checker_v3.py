"""Accept exact new source/pure evidence, without executing any archive checker."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = {
    "captured_archive_v3.py": "90ba49a96713b6178320f04e68affee084abfb77588551b22140330309cd7d9b",
    "check_captured_archive_v3.py": "e6df7bd2272e56b5c7278d5b2901ad7f4d7d34f44a74ee4c28fe40e6b917e599",
    "CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v3.json": "cfde0f81ae458c9d76a4cd29cb68ef8ba532e8f4be01c71d3ce96a67c552b8c9",
    "CAPTURED-ARCHIVE-CHECKER-FREEZE-v3.json": "43041bffa8058a25ca16fe79e4bce375e29c5d1b17ea236d89ffdc25a0b3ac29",
    "CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-PEER-v3.json": "d562bcfd0a20d691ef8e022a9c6aed86f65c5687374258a042910021a9874f5d",
    "CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-AFTER-PROBES-v3.json": "6f730defe059db4635d04ea4851f422fd0e6b62af09ca6f2df27123a68c76f96",
    "CAPTURED-NATIVE-ARCHIVE-CONTRACT-v3.json": "ce077d5bfd2e12bd5de7a84d17094572a15286e0cb44bdc224513206f305e3d2",
    "CAPTURED-NATIVE-ARCHIVE-FIXTURES-v3.json": "3e75447d4d3a01c56833d089bf23dab52e5e53bc49a9ea33e9de689eef9b5dcd",
    "CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-PEER-v2.json": "1a48b0e0e19ed873fb99c19f3a7d865f3243168cdc8831a8a598844b38f513de",
    "CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-PROBES-v3.json": "05b44dab09818ef89894c8483c0f05e2ec7ba7619465ac7f82d0a27ca7eec549",
}
inputs, docs = {}, {}
for name, expected in EXPECTED.items():
    raw = (HERE / name).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    assert actual == expected, (name, actual)
    inputs[name] = {"bytes": len(raw), "sha256": actual}
    if name.endswith(".json"):
        docs[name] = json.loads(raw)
peer = docs["CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-PEER-v3.json"]
assert peer["status"] == "CLEAR_SOURCE_PURE_NARROW_V3_SUCCESSOR"
assert peer["author_evidence"] == {
    "all32_frozen_projection_cases": True, "methods": 13,
    "source_and_input_pins_current": True, "status": "passed",
}
assert peer["independent_after"]["methods"] == 7
assert peer["independent_after"]["status"] == "passed"
assert peer["unchanged_top_level_ASTs"] == 57
assert peer["changed_ASTs"] == ["Expr", "_number", "_run_graph"]
proof = docs["CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v3.json"]
assert proof["methods"] == 13 and not proof["errors"] and not proof["failures"]
for data in (peer, proof):
    assert data["actual_directory_complete"] is False
    assert data["originals_authenticated"] is False
    assert data["source_qualified"] is False and data["profile_qualified"] is False
record = {
    "schema_version": 1,
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "ACCEPTED_V3_SOURCE_PURE_CAPTURED_GRAPH_CHECKER_ONLY",
    "scope": "Bounded caller-captured metadata, locator/hash/DAG/source-map consistency and negative/incomplete disposition. No original source authentication, filesystem capture or owner/resource/profile qualification.",
    "inputs": inputs,
    "author_methods": 13, "independent_methods": 7,
    "frozen_projection_cases": 32, "fully_rebound_before_after_cases": 2,
    "resolved_v2_hold": [
        "Source-shaped already-closed unattempted lease retains null close_success",
        "Out-of-range huge integer is data rejection without floating conversion overflow",
    ],
    "earlier_callback_and_LF_regressions_preserved": True,
    "prior_sources_proofs_failures_preserved": True,
    "originals_authenticated": False, "actual_directory_complete": False,
    "source_qualified": False, "resource_qualified": False,
    "owner_context_provenance_established": False,
    "profile_qualified": False, "runtime_authorized": False,
    "actual_old_archive_capture_or_replay": False,
    "new_SDK_OS_native_model_operations": 0,
    "original_negative_and_timeout_unchanged": True,
    "remaining": [
        "Complete future Unicode observation schema and trace fixtures/validator",
        "File-port fake vectors, typed source and separate real qualification",
        "Original-clock entry, fresh leases, source loader and production-engine integration",
        "Full parent/resource/profile binding and separate native qualification",
    ],
}
output = HERE / "CAPTURED-ARCHIVE-CHECKER-SCOPED-ACCEPTANCE-v3.json"
with output.open("x", encoding="utf-8", newline="\n") as handle:
    json.dump(record, handle, sort_keys=True, ensure_ascii=False, indent=2)
    handle.write("\n")
raw = output.read_bytes()
print(json.dumps({"status": record["status"], "bytes": len(raw),
                  "sha256": hashlib.sha256(raw).hexdigest()}))
