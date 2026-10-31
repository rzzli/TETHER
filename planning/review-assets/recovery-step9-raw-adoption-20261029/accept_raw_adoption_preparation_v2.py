"""Accept closed fictional preparation and authorize a portable record core."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = {
    "ADOPTION-FIXTURE-SCHEMA-v2.json": "b4b6670c71d08133670af0af357088447c452f0e973f179c07e69702f900ade5",
    "RAW-ADOPTION-FIXTURES-v2.json": "09f79b6a5f7bca50a3da63f3d95a6041e8bc2acf84ec85f1db5d96a4e7c1d5f6",
    "RAW-ADOPTION-FIXTURE-FREEZE-v2.json": "bb83204db84c64941cad82c760396ce3bc8b91f1d7fd692c29c05a746b3c84ff",
    "RAW-ADOPTION-LITERAL-SHAPE-PROOF-v2.json": "d26efab8f119e5ebd7243513ac3796b875cdc45a94c24d8532f78012ff694ee2",
    "RAW-ADOPTION-FIXTURE-INDEPENDENT-PEER-v2.json": "9dd25010c0e248fd249ef9a6607b6d5ed3bac0a36a8768568ba46775e67976d4",
    "RAW-ADOPTION-FIXTURE-INDEPENDENT-PROOF-v2.json": "e53a5ba708e800c5cb6a4cc52390394f1b481887657fe00b3230b29a1872eeee",
    "RAW-ADOPTION-RAWVALUE-COUNTER-SUBSET-REVIEW-v3.json": "be3d0634639592f7ddb62e5ba18ee0c572454ac1810e869aeec60f520e2df0af",
}
inputs, docs = {}, {}
for name, digest in EXPECTED.items():
    assert len(digest) == 64
    raw = (HERE / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, name
    inputs[name] = {"bytes": len(raw), "sha256": digest}
    docs[name] = json.loads(raw)
peer = docs["RAW-ADOPTION-FIXTURE-INDEPENDENT-PEER-v2.json"]
assert peer["status"] == "CLEAR_LITERAL_PREPARATION_SCOPE_ONLY"
assert peer["population"] == {"cases": 32, "checkpoints": 9, "expected_records": 45, "families_including_success": 15, "steps": 256}
assert not peer["material_blockers"]
proof = docs["RAW-ADOPTION-LITERAL-SHAPE-PROOF-v2.json"]
assert proof["status"] == "passed" and proof["methods"] == 6
assert not proof["errors"] and not proof["failures"]
assert proof["successor_implementation_executed"] is False
record = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "LITERAL_PREPARATION_ACCEPTED_PORTABLE_ADOPTION_CORE_SOURCE_AUTHORIZED",
    "inputs": inputs,
    "accepted_scope": "32 independently reviewed fictional histories across14 fault families plus success,256 steps/45 records/9 checkpoints. Shape/formula review is not adopter behavior or real FFI evidence.",
    "source_scope": "Implement actual generic portable call-record adoption/reconciliation, buffer lifetime/count accounting, once-only rights and same-object typed handoff logic. A test harness drives the frozen steps through those methods; the implementation cannot read expected results, fixture files, case IDs or fault labels to choose outputs.",
    "requirements": [
        "Expose preallocated first-fact storage with UNOBSERVED distinct from zero/NULL. Reconcile preserved stored values before relying on auxiliary acknowledgments or later wrapper objects",
        "Preserve partial raw facts and legal close rights across wrapper faults; keep conservative invocation, observed scalar/count and portable-return axes distinct without a measured C-entry claim",
        "Support incremental scalar-then-count folding at one ordinal: pending may resolve, final undefined/unknown stays distinct, and no axis or known byte is counted twice",
        "Raw defined zero is a valid observation; full-file/hash/write-progress completeness remains a separate caller policy",
        "Maintain owner/Origin/nonce/registry/port/slot/buffer identity, exact generations and same output/early-context/loader/journal continuity; no new owner/start/reservation or duplicated closer",
        "Perform real pure copy/hash operations only when requested/eligible, preserve raw buffer lifetimes and known late observations without inventing capture/hash completion",
        "Preserve original exception objects, bounded secondary diagnostics and immutable detached snapshots; test type/capability/transition/counter/lifetime and interruption faults meaningfully",
        "Keep all harness preconditions and object references fictional; no producer dictionary or test seed can grant production/source/identity authority",
    ],
    "validation": "Exercise all32 histories/checkpoints against independently authored expected states, add meaningful adversarial/state/immutability tests, preserve every failing source/proof in a named successor and obtain exact independent review before acceptance.",
    "explicit_limits": "This authorizes a portable record core, not a real ctypes/FFI wrapper, production first-entry/engine integration or proof of the native-to-Python conversion window. Actual binding, real source/roster/resource/profile qualification remain separate.",
    "portable_source_implementation_authorized": True,
    "real_ctypes_or_binding_construction_authorized": False,
    "real_file_or_native_operations_authorized": False,
    "old_source_closure_or_payload_operations_authorized": False,
    "production_activation_authorized": False,
    "profile_qualified": False, "runtime_authorized": False,
    "originals_authenticated": False,
    "prior_versions_and_two_preparation_findings_preserved": True,
}
output = HERE / "RAW-ADOPTION-PREPARATION-AND-SOURCE-SCOPE-v2.json"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(record, stream, sort_keys=True, indent=2)
    stream.write("\n")
print(json.dumps({"status": record["status"], "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
