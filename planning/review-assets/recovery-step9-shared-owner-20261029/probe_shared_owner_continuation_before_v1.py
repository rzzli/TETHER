"""Focused pure before witness: ordinary mutation of a source-issued continuation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
HELPER = HERE / "check_shared_owner_author_controls_v1.py"
raw = HELPER.read_bytes()
assert hashlib.sha256(raw).hexdigest() == "f8a65c46200937b9928eb5cdfb2ebf9cce1d37a8d97392e615af5bc26581e8a7"
env = {"__name__": "root_focused_before", "__file__": str(HELPER)}
exec(compile(raw, str(HELPER), "exec"), env)

owner_a, _, sink_a, binding_a = env["create"]()
owner_b, _, sink_b, binding_b = env["create"]()
continuation_a = env["early"](owner_a)
continuation_b = env["early"](owner_b)
assert continuation_a.owner is owner_a and continuation_b.owner is owner_b
owner_b.load_source("cohort_entry")
assignment_error = None
try:
    continuation_a.owner = owner_b
except BaseException as error:
    assignment_error = type(error).__name__
result = None
dispatch_error = None
if assignment_error is None:
    try:
        result = env["finish"](owner_b, continuation_a).to_dict()
    except BaseException as error:
        dispatch_error = type(error).__name__
if not owner_a.finalized:
    owner_a.finalize()
if not owner_b.finalized:
    owner_b.finalize()

reproduced = assignment_error is None and result is not None and result["pure_seam_complete"]
proof = {
    "schema_version": 1,
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "REPRODUCED_CONTINUATION_OWNER_REBINDING" if reproduced else "COUNTEREXAMPLE_NOT_REPRODUCED",
    "scope": "Two independent legitimate fictional owners and genuine claimed continuations. Only ordinary assignment to the public continuation.owner attribute; no private-state mutation, new source inputs or actual platform calls.",
    "source_pins": [{"name": name + ".py", "sha256": digest} for name, digest in zip(env["SOURCE_NAMES"], env["SOURCE_SHA"])],
    "helper": {"name": HELPER.name, "sha256": hashlib.sha256(raw).hexdigest()},
    "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "observation": {
        "initial_owners_distinct": owner_a is not owner_b,
        "initial_origins_distinct": owner_a.origin is not owner_b.origin,
        "assignment_rejected": assignment_error is not None,
        "assignment_error_class": assignment_error,
        "continuation_now_points_to_other_owner": continuation_a.owner is owner_b,
        "wrong_original_continuation_accepted_for_second_owner": reproduced,
        "second_owner_final_status": result["status"] if result else None,
        "dispatch_error_class": dispatch_error,
        "owner_a_fake_API_calls_including_cleanup": len(binding_a.calls),
        "owner_b_fake_API_calls_including_cleanup": len(binding_b.calls),
    },
    "required": "The original source-issued continuation must remain bound to its issuing owner. Reassignment must refuse without changing either owner or permit no execution through the foreign view.",
    "actual_API_calls": 0, "old_original_or_payload_operations": 0,
    "runtime_authorized": False, "production_owner_bound": False,
    "FFI_registration_proven": False, "profile_qualified": False,
}
destination = HERE / "SHARED-OWNER-CONTINUATION-OWNER-BEFORE-v1.json"
with destination.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(proof, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({"status": proof["status"], "observation": proof["observation"], "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}))
