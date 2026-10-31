"""Finite design/control precheck retention; no reviewed module execution."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "INDEXED-ACCOUNTING-SUCCESSOR-PROPOSAL-v1.json": "7e2b1b5b71095863ab687a92f8152239c2922f0bd8ada9c875562ec15d6d9a5b",
    "INDEXED-ACCOUNTING-APPEND-ENVELOPE-CLARIFICATION-v1.json": "147dc12855fe6f9bbd5b1994bc1e389b938cb03bdc25ddb1cf4137c5fc48cfd6",
    "INDEXED-ACCOUNTING-PRECODE-PROTOCOL-DRAFT-v1.json": "c48962eecb3b43b6b185cc0be1a89ad4787ffec4c884e2f07b5dac60aab252d4",
    "INDEXED-ACCOUNTING-PRECODE-TEST-CONTRACT-v1.json": "a693c8f1529732e40792a1aefb00f3dae2997eb0998663665db6a1b684680115",
    "indexed_accounting_controls_v1.py": "bd7ea044253609c74396190658ddaadedd4d1bcc997e81391db7ded079e0d86e",
    "INDEXED-ACCOUNTING-PRECODE-CONTROL-FREEZE-v1.json": "888c7bec39a5b59861409c71bbd2cdfbb7b500a91755e82fc196fd886c478fed",
    "INDEXED-ACCOUNTING-ACTUAL-V2-BEFORE-PROOF-v1.json": "88dd26aa673997a99c53ce526b69e2d0286d6cc6f72999b180355d222213c1dc",
    "run_indexed_accounting_v2_before_v1.py": "1813ced6f43bb809fe726f6d0515399dabf2d0a7625704bab64a97900ac5c6ea",
}


def main():
    pins, raw = {}, {}
    for name, expected in EXPECTED.items():
        data = (ROOT / name).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        assert digest == expected, name
        raw[name] = data
        pins[name] = dict(path=str(ROOT / name), bytes=len(data), sha256=digest)
    before = json.loads(raw["INDEXED-ACCOUNTING-ACTUAL-V2-BEFORE-PROOF-v1.json"])
    assert before["methods"] == 6 and len(before["failures"]) == 4 and before["errors"] == []
    assert before["audit_denials"] == [] and all(before["source_unchanged"].values())
    assert before["prospective_source_executed"] is False
    hot = [row for row in before["observations"] if row["window"] == "clean_hot"]
    assert len(hot) == 4
    tree = ast.parse(raw["indexed_accounting_controls_v1.py"])
    locations = {node.name: node.lineno for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    blockers = [
        dict(id="T1", kind="harness_contract_coverage_only", line=locations["test_03_real_ref_guard_no_membership_scan"],
             issue="The manual test03 clean-hot assertions omit slice_copied_items==0 and len_calls<=32, although the common contract requires both.",
             consequence="A slice-only canonical copy or unbounded len calls could evade this one control's assertions; static source review remains required independently.",
             minimal_closure="Apply the same missing two metric assertions to this existing family; no threshold/case/source-policy change."),
        dict(id="T2", kind="harness_contract_coverage_only", line=locations["canonical_error_checks"],
             issue="The fresh-work assertion always calls acquire(specs[1]); CTRL5 has already opened/hashed that entry file, so healthy code also rejects this call.",
             consequence="This CTRL5 assertion alone does not isolate cache-fault quarantine or prove that an otherwise-admitted noncleanup operation is refused.",
             minimal_closure="In indexed mode test the otherwise-valid owner.check() at unchanged clock100 before/after canonical reports, with the same original fault and no extra binding/sink dispatch or state advance. Retain the already-open acquire check only as its honest prior no-dispatch invariant."),
    ]
    report = dict(
        schema_version=1, status="HOLD_PRECODE_CONTROL_CLOSURE_ONLY",
        recorded_at_utc="2026-10-29 17:45:52 UTC", reviewer="native_039_acceptance_audit",
        inputs=pins, material_blockers=blockers, finite_batch_complete=True,
        effective_design=dict(status="NO_REMAINING_SCOPED_DESIGN_BLOCKER",
                              base=pins["INDEXED-ACCOUNTING-SUCCESSOR-PROPOSAL-v1.json"],
                              append_envelope=pins["INDEXED-ACCOUNTING-APPEND-ENVELOPE-CLARIFICATION-v1.json"],
                              private_helpers=5,
                              review="Raw cells remain first deliberate facts. Registration begins its BaseException catch before append, folds are idempotent/quarantined, known ownership/raw lower bounds survive interrupted cache updates, canonical reports cannot repair/resume, and no cap/API/schema/oracle/production authority is added."),
        accepted_V2_before=dict(proof=pins["INDEXED-ACCOUNTING-ACTUAL-V2-BEFORE-PROOF-v1.json"],
                                methods=6, intended_hot_failures=4, functional_methods_passed=2,
                                errors=0, audit_denials=0, source_unchanged=True,
                                actual_hot_observations=hot,
                                meaning="Real acceptedV2 list scans, not absent-future-helper failures; source/pure operation counts only, no timing/production-fit qualification"),
        controls_review=[
            "CountingList is installed only into the actual empty canonical Registry before facts, preserving owner/list identity without copying authority.",
            "Actual iteration, membership, slice-copy, index/len and append counts are measured in explicit hot windows; cold cleanup/report windows are labeled and excluded, not hidden.",
            "Direct base-list calls are limited to instrumentation/measurement. Future source static review must still forbid global dict.values or alternative-ledger scans; metric passes alone cannot establish algorithm correctness.",
            "Reservation failure V2 adapter uses a real append-after-commit exception, and fold failure uses actual store_count after raw assignment. Canonical raw states, original exceptions, partial/zero distinctions and healthy identical replay have meaningful baseline evidence.",
            "Future before/after private-helper and dirty-work cases remain prospective until the later code exists; current raw-functional passes do not claim those future cache predicates were exercised.",
        ],
        authorization_boundary="Root's delivered message authorizes exactly these two harness closures in a new named version, preserving the firstfreeze/88dd. No implementation authorization follows from this precheck.",
        unchanged_scope="Same six families, N4/4KiB/16KiB/R68/C92/E224/gen68, DATA50ee, frozen48/e12, same8 and author16 remain; larger storage/output/firstentry/full-roster architecture is separate.",
        current_V2_acceptance_reopened=False,
        reviewed_source_executions_by_peer=0, test_repeats_by_peer=0,
        source_or_harness_or_fixture_edits_by_peer=0, actual_API_calls=0,
        old_original_or_payload_operations=0, implementation_authorized=False,
        production_owner_bound=False, profile_qualified=False, verification_complete=False,
    )
    path = ROOT / "INDEXED-ACCOUNTING-INDEPENDENT-PRECODE-HOLD-v1.json"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    note = """# Indexed-accounting pre-code peer

**HOLD_PRECODE_CONTROL_CLOSURE_ONLY.** Effective design `7e2b1b5b…` plus append-envelope clarification `147dc128…` has no remaining scoped design blocker. Raw facts precede derived state; registration/fold interruptions retain originals and quarantine work; canonical reports cannot heal or grant authority. N4/caps/public DATA/oracle remain unchanged.

Two harness-only closures are required before code: test03 must assert the missing zero-slice and bounded-len metrics; and CTRL5's already-open `acquire(specs[1])` cannot establish fresh-work quarantine. The indexed-only otherwise-valid `owner.check()` at clock100 should refuse before/after reports without dispatch or state advance. These stay within the same six families and add no source API or policy.

The retained accepted-v2 BEFORE proof `88dd26aa…` records four intended scan failures and two raw-functional passes, no errors/audit denials and unchanged source. Hot visits are18 for handle,18 for known bytes,18 membership for the actual ref, and17 iteration plus54 membership/one append for Read admission. These are real list-access observations, not missing-future-helper failures or timing evidence. Future private cache modes remain prospective.

Preserve the original protocol/test/freeze/BEFORE bytes and issue one narrow successor. This peer executed no subject or test, changed no reviewed artifact and inspected no originals. Full48/same8/author16 and separate future source review remain required. [Exact precheck JSON](INDEXED-ACCOUNTING-INDEPENDENT-PRECODE-HOLD-v1.json).
"""
    md = ROOT / "INDEXED-ACCOUNTING-INDEPENDENT-PRECODE-HOLD-v1.md"
    with md.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(note)
    for output in (path, md):
        b = output.read_bytes()
        print(json.dumps(dict(path=str(output), bytes=len(b), sha256=hashlib.sha256(b).hexdigest())))


if __name__ == "__main__":
    main()
