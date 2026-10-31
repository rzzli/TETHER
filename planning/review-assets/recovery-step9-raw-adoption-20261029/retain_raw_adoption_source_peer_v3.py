"""Publish the bounded final source peer from exact NEW metadata and proofs."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

PHASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def load(name):
    return json.loads((PHASE / name).read_text(encoding="utf-8"))


freeze_path = PHASE / "RAW-ADOPTION-CORE-SOURCE-FREEZE-v3.json"
assert pin(freeze_path)["sha256"] == "15c07bc04d40f224d977a00f19cbab926590fb7d514872e83250960053e5782c"
freeze = load(freeze_path.name)
source = freeze["source"]
assert source == pin(PHASE / "raw_adoption_core_v3.py")
assert source["sha256"] == "f4fcae07926927f509f455b1b8e243cec2be8fdbc91fa710aacf14618e9b5bea"
verified = []


def bind(value):
    if type(value) is dict:
        if set(value) == {"path", "bytes", "sha256"}:
            path = Path(value["path"])
            # Every bound input here is NEW phase-local source/proof metadata.
            assert path.resolve().is_relative_to(PHASE.resolve())
            assert pin(path) == value
            verified.append(value)
        else:
            for child in value.values(): bind(child)
    elif type(value) is list:
        for child in value: bind(child)


bind(freeze)
driver_name = "RAW-ADOPTION-CORE-DRIVER-PURE-PROOF-v3.json"
owner_name = "RAW-ADOPTION-OWNER-CONTROLS-PROOF-v3.json"
after_name = "RAW-ADOPTION-SOURCE-INDEPENDENT-AFTER-v3.json"
driver, owner, after = load(driver_name), load(owner_name), load(after_name)
assert pin(PHASE / driver_name)["sha256"] == "1c05165b626aade0db9ff2cfb6399e015ffc7a07b3618f41af5d9c4b41d47a81"
assert pin(PHASE / owner_name)["sha256"] == "2aae75bd78d0ff05d0c93c259231cb5646f698cd1f2ab80028e0600c17ea9305"
assert pin(PHASE / after_name)["sha256"] == "4a2b30bf78a352806e8c81e3b822ec67de198c9c4a464c34d2d1b55ac4057042"
assert driver["status"] == "passed" and driver["methods"] == 19
assert driver["errors"] == driver["failures"] == driver["audit_denials"] == []
assert owner["status"] == "PASS" and owner["methods"] == 21
assert owner["errors"] == owner["failures"] == []
assert driver["core"] == owner["source"] == after["source"] == source
assert after["status"] == "passed" and after["audit_denials"] == []
assert after["AST_changed_methods"] == ["Owner._component", "Owner.handoff", "Owner.raise_exception"]
assert after["AST_unchanged_methods"] == 66 and after["all_other_AST_except_module_docstring_equal"] is True
fixtures = load("RAW-ADOPTION-FIXTURES-v3.json")
assert len(fixtures["cases"]) == len(driver["runs"]) == 32
steps, retained_snapshots, issued_snapshots, checkpoints = 0, 0, 0, 0


def projection(data, path):
    pieces = path.split(".")
    if pieces[0].startswith("record"):
        ordinal = int(pieces.pop(0)[6:])
        data = next(row for row in data["records"] if row["ordinal"] == ordinal)
    elif pieces[0] == "slot":
        pieces.pop(0)
        slot_id = pieces.pop(0)
        data = next(row for row in data["slots"] if row["id"] == slot_id)
    for piece in pieces: data = data[piece]
    return data


for case, run in zip(fixtures["cases"], driver["runs"]):
    assert case["id"] == run["id"] and run["matched"] is True and run["differences"] == []
    assert run["actual"] == case["expected"]
    assert [s["after_step"] for s in run["snapshots"]] == [-1] + list(range(len(case["steps"])))
    assert run["snapshot_count"] == len(run["snapshots"]) + 1
    snapshots = {s["after_step"]: s["data"] for s in run["snapshots"]}
    for point in case["checkpoints"]:
        for path, expected in point["projection"].items():
            assert projection(snapshots[point["after_step"]], path) == expected
    assert len(run["checkpoints"]) == len(case["checkpoints"])
    assert all(c["matched"] is True and c["differences"] == [] for c in run["checkpoints"])
    steps += len(case["steps"])
    retained_snapshots += len(run["snapshots"])
    issued_snapshots += run["snapshot_count"]
    checkpoints += len(case["checkpoints"])
assert (steps, retained_snapshots, issued_snapshots, checkpoints) == (256, 288, 320, 9)
assert driver["actual_snapshots"] == issued_snapshots and driver["all32_matched"] == 32
assert driver["checkpoint_count"] == checkpoints

record = {
    "schema_version": 3, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "CLEAR_SOURCE_PURE_INJECTED_CORE_ONLY",
    "reviewer": "/root/native_039_acceptance_audit", "author": "/root/os_accounting_peer",
    "independent_driver_author": "/root/grammar_toolchain_requirements",
    "scope": "Exact finite three-method correction review of the portable injected adoption model, plus focused same-counterexample probes and static retained-proof consistency. No actual native C/ctypes/wrapper return capture, file port or production continuation was exercised.",
    "source": source, "freeze": pin(freeze_path),
    "source_authorization": freeze["inputs"]["RAW-ADOPTION-PREPARATION-AND-SOURCE-SCOPE-v2.json"],
    "implementation_scope": freeze["inputs"]["RAW-ADOPTION-CORE-IMPLEMENTATION-SCOPE-v1.json"],
    "prior_hold": freeze["inputs"]["RAW-ADOPTION-CORE-SOURCE-INDEPENDENT-PEER-v2.json"],
    "prior_independent_before": after["before"], "author_wrapper_before": after["author_wrapper_before"],
    "independent_after": pin(PHASE / after_name),
    "independent_after_checker": after["checker"],
    "independent_driver_proof": pin(PHASE / driver_name),
    "owner_controls_proof": pin(PHASE / owner_name),
    "literal_schema": driver["schema"], "literal_fixtures": driver["fixture"],
    "literal_correction_peer": freeze["inputs"]["RAW-ADOPTION-FIXTURE-INDEPENDENT-PEER-v3.json"],
    "source_AST": {"changed_methods": after["AST_changed_methods"], "unchanged_methods": 66,
                   "all_other_AST_except_module_docstring_equal": True},
    "resolved_findings": [
        {"id": "closed_early_source_handoff", "finding": "Current early slots must be owned_live with available close rights before claim/event increment.",
         "evidence": "The same closed-source counterexample now rejects early_context_not_live, claims0/event7; it carries the original context/Origin, namespace/readiness, five known/hash/capture bytes and one already consumed close."},
        {"id": "injected_core_error_class", "finding": "The component catch checks whether the exact error is already primary/secondary, instead of classifying all AdoptionError instances as already handled.",
         "evidence": "The same fresh hook error is now the exact original primary with no secondary duplication; known bytes remain3, copy/hash remain0 and the retained wrapper return remains1. Retained independent regressions cover both copy/hash and the source-created count guard without duplication."},
        {"id": "wrapper_return_monotonicity", "finding": "Later stop retains wrapper_state returned and adds stopped/error without erasing the known return fact.",
         "evidence": "The focused later-publication-stop probe keeps all prior counters and3known bytes; repeated reconcile remains idempotent and one legal cleanup close brings wrapper returns to2 while preserving the original primary."},
    ],
    "retained_proof_consistency": {"verified_freeze_pin_records": len(verified),
        "driver_methods": 19, "owner_control_methods": 21, "histories": 32,
        "all_final_projections_equal_frozen_expected": True, "literal_steps": 256,
        "stored_initial_and_step_snapshots": 288, "separately_issued_final_snapshots": 32,
        "issued_snapshots": 320, "independently_reconstructed_checkpoints": 9,
        "test_suites_rerun_by_this_metadata_review": 0},
    "focused_peer_probes": {"probes": 3, "synthetic_owners": 3, "audit_denials": 0,
                            "fixture_histories_replayed": 0},
    "material_blockers": [],
    "scope_drift": "No new serialized fields, fixture changes, APIs, factories or methods in this successor. Preparation e20b47ff scope remains the injected HARNESS_ONLY model. Core still consumes no fixture/case/expected data or filesystem inputs.",
    "remaining_gates": [
        "Actual native-to-Python/ctypes conversion and first-store registration are not proved by these methods or Python-object fixtures.",
        "A real first-clock entry and exact shared bootstrap/controller/registry/output/source-loader continuation remain separately unimplemented or unqualified boundaries.",
        "Actual14-export binding behavior, full roster/call/event/buffer/time/resource fit and new Unicode checker/archive integration remain separate.",
        "No originals, source closure, live leases, runtime/profile or scientific acceptance follows from this pure component review.",
    ],
    "reviewed_core_versions_edited": False, "existing_fixtures_or_prior_artifacts_edited": False,
    "actual_target_API_calls": 0, "old_payload_pack_or_source_closure_operations": 0,
    "FFI_registration_proven": False, "production_owner_bound": False,
    "originals_authenticated": False, "profile_qualified": False, "runtime_authorized": False,
    "retention_source": pin(Path(__file__).resolve()),
}
out = PHASE / "RAW-ADOPTION-CORE-SOURCE-INDEPENDENT-PEER-v3.json"
with out.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(json.dumps(record, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
md = """# Raw-adoption core v3: independent source peer

The exact three-method successor is clear for its injected source/pure scope. The previous HOLD's three findings are resolved; no material blocker remains in this finite batch. All other 66 function/method ASTs and the remaining module AST match v2 apart from the module docstring.

Handoff now rejects an early source whose close right was consumed, before changing the claim or event sequence. A fresh injected AdoptionError becomes the original primary by identity, while an already latched source guard is not duplicated. A later stop preserves an observed wrapper return and its count, with stopped/error state retained separately.

Three independent focused after probes pass under I/O denial with no denied operations. They preserve the original owner objects, known bytes, primary identity and once-only cleanup. The retained independent suite passes 19 methods and all 32 frozen histories/nine checkpoints; the author's separate controls pass 21 methods. This review independently compared all final projections and reconstructed the nine checkpoints from captured data. The 320 issued snapshots comprise 288 stored initial/step snapshots plus 32 final snapshots. Neither full suite was replayed here.

This is a portable Python-object adoption model using typed HARNESS_ONLY preconditions. It does not prove capture between native return and Python conversion, an actual Win32 wrapper, original first-clock entry, production continuation, full roster/resource fit, originals, runtime or profile qualification. No existing source, fixture or prior artifact was edited, and no actual target API or old payload/source-closure operation occurred.

- [Exact peer](RAW-ADOPTION-CORE-SOURCE-INDEPENDENT-PEER-v3.json)
- [Focused independent after proof](RAW-ADOPTION-SOURCE-INDEPENDENT-AFTER-v3.json)
- [Prior HOLD](RAW-ADOPTION-CORE-SOURCE-INDEPENDENT-PEER-v2.json)
- [Frozen source/proof index](RAW-ADOPTION-CORE-SOURCE-FREEZE-v3.json)
"""
md_path = PHASE / "RAW-ADOPTION-CORE-SOURCE-INDEPENDENT-PEER-v3.md"
with md_path.open("x", encoding="utf-8", newline="\n") as stream: stream.write(md)
print(json.dumps({"status": record["status"], "json": pin(out), "md": pin(md_path)}, sort_keys=True))
