"""Exact two-closure final DESIGN/pre-code peer; metadata/AST only."""
import ast
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASIS = ROOT.parent / "recovery-step9-shared-owner-20261029"
EXPECTED = {
    "INDEXED-ACCOUNTING-SUCCESSOR-PROPOSAL-v1.json": "7e2b1b5b71095863ab687a92f8152239c2922f0bd8ada9c875562ec15d6d9a5b",
    "INDEXED-ACCOUNTING-APPEND-ENVELOPE-CLARIFICATION-v1.json": "147dc12855fe6f9bbd5b1994bc1e389b938cb03bdc25ddb1cf4137c5fc48cfd6",
    "INDEXED-ACCOUNTING-INDEPENDENT-PRECODE-HOLD-v1.json": "50eff232619227c3beeae736e9fac35910a29baf81d205f4e059e6b3bd50ea3a",
    "indexed_accounting_controls_v1.py": "bd7ea044253609c74396190658ddaadedd4d1bcc997e81391db7ded079e0d86e",
    "INDEXED-ACCOUNTING-PRECODE-TEST-CONTRACT-v1.json": "a693c8f1529732e40792a1aefb00f3dae2997eb0998663665db6a1b684680115",
    "INDEXED-ACCOUNTING-PRECODE-CONTROL-FREEZE-v1.json": "888c7bec39a5b59861409c71bbd2cdfbb7b500a91755e82fc196fd886c478fed",
    "INDEXED-ACCOUNTING-ACTUAL-V2-BEFORE-PROOF-v1.json": "88dd26aa673997a99c53ce526b69e2d0286d6cc6f72999b180355d222213c1dc",
    "indexed_accounting_controls_v2.py": "d76e1a2d7c70a9a42fa70c5f4989f08f2e291e79f12fa53b454250998c74bf5b",
    "INDEXED-ACCOUNTING-PRECODE-TEST-CONTRACT-v2.json": "cccf8a1f4f6219ff51ade0279e82f587cfbe76c969e1be69125c0cc72ff2a3bd",
    "INDEXED-ACCOUNTING-PRECODE-CONTROL-DELTA-v2.json": "f98ed86bb84484c3afb0a6d59ec5b46c95f2b8de7279edcd39aa46984c0e4bcc",
    "INDEXED-ACCOUNTING-PRECODE-CONTROL-FREEZE-v2.json": "52da9451c215d50f4b3e559a47eb4c286dd7e33fc884b8bf67430d9e6ac9703d",
    "INDEXED-ACCOUNTING-ACTUAL-V2-BEFORE-PROOF-v2.json": "24da94c6576a7d94ef1c88467e28a179ae4f57b7da6e0a6a885f1e836101ef7d",
    "run_indexed_accounting_v2_before_v2.py": "7047d1b35d86381063169a15d2097d6eb04594b43fbba9410d6a526d44c3ee75",
}


def normalize(tree):
    tree = copy.deepcopy(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in (
                "canonical_error_checks", "test_03_real_ref_guard_no_membership_scan"):
            node.body = [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def pin_nodes(value):
    if isinstance(value, dict):
        if set(("path", "bytes", "sha256")) <= set(value):
            yield value
        else:
            for child in value.values():
                yield from pin_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from pin_nodes(child)


def main():
    pins, raw = {}, {}
    def capture(path, digest=None, size=None):
        assert path.parent in (ROOT, BASIS), str(path)
        key = str(path)
        if key not in pins:
            data = path.read_bytes()
            actual = hashlib.sha256(data).hexdigest()
            pins[key] = dict(path=str(path), bytes=len(data), sha256=actual)
            raw[path.name] = data
        actual = pins[key]
        if digest is not None:
            assert actual["sha256"] == digest, path.name
        if size is not None:
            assert actual["bytes"] == size, path.name
        return actual
    for name, digest in EXPECTED.items():
        capture(ROOT / name, digest)
    old = json.loads(raw["INDEXED-ACCOUNTING-PRECODE-TEST-CONTRACT-v1.json"])
    new = json.loads(raw["INDEXED-ACCOUNTING-PRECODE-TEST-CONTRACT-v2.json"])
    before = json.loads(raw["INDEXED-ACCOUNTING-ACTUAL-V2-BEFORE-PROOF-v2.json"])
    freeze = json.loads(raw["INDEXED-ACCOUNTING-PRECODE-CONTROL-FREEZE-v2.json"])
    delta = json.loads(raw["INDEXED-ACCOUNTING-PRECODE-CONTROL-DELTA-v2.json"])
    for item in (new, before, freeze, delta):
        for pin in pin_nodes(item):
            capture(Path(pin["path"]), pin["sha256"], pin["bytes"])
    assert normalize(ast.parse(raw["indexed_accounting_controls_v1.py"])) == normalize(
        ast.parse(raw["indexed_accounting_controls_v2.py"]))
    assert old["tests"] == new["tests"] and len(new["tests"]) == 6
    assert [c["id"] for c in old["controls"]] == [c["id"] for c in new["controls"]]
    for key in ("accepted_pins", "instrumentation", "functional_failure_rules", "invariants",
                "future_private_seams", "counter_and_authority_limits", "design"):
        assert old[key] == new[key], key
    assert before["methods"] == 6 and len(before["failures"]) == 4 and before["errors"] == []
    assert before["audit_denials"] == [] and all(before["source_unchanged"].values())
    assert before["prospective_source_executed"] is False
    hot = [row for row in before["observations"] if row["window"] == "clean_hot"]
    assert [row["name"] for row in hot] == ["handle", "read_known", "ref_membership", "read_admission"]
    assert [row["metrics"]["iterated_items"] for row in hot] == [18, 18, 0, 17]
    assert [row["metrics"]["membership_items"] for row in hot] == [0, 0, 18, 54]
    assert hot[-1]["metrics"]["append_calls"] == 1
    assert new["implementation_authorized"] is False and freeze["implementation_authorized"] is False
    report = dict(
        schema_version=2, status="CLEAR_DESIGN_AND_PRECODE_CONTROLS_ONLY",
        material_blockers=[], recorded_at_utc="2026-10-29 17:48:10 UTC",
        reviewer="native_039_acceptance_audit", inputs=pins,
        effective_design=[pins[str(ROOT / name)] for name in (
            "INDEXED-ACCOUNTING-SUCCESSOR-PROPOSAL-v1.json",
            "INDEXED-ACCOUNTING-APPEND-ENVELOPE-CLARIFICATION-v1.json")],
        current_test_source=pins[str(ROOT / "indexed_accounting_controls_v2.py")],
        current_protocol=pins[str(ROOT / "INDEXED-ACCOUNTING-PRECODE-TEST-CONTRACT-v2.json")],
        freeze=pins[str(ROOT / "INDEXED-ACCOUNTING-PRECODE-CONTROL-FREEZE-v2.json")],
        preserved_hold=pins[str(ROOT / "INDEXED-ACCOUNTING-INDEPENDENT-PRECODE-HOLD-v1.json")],
        closed_findings=[
            dict(id="T1", resolved=True, closure="CTRL3 now asserts zero slice-copied items and len_calls<=32, completing the unchanged common clean-hot metric contract."),
            dict(id="T2", resolved=True, closure="Indexed-only owner.check() is otherwise valid at clock100, now required to refuse with the same primary/accounting fault and no binding/sink increment. Canonical reports before/after compare the declared raw/accounting/origin/journal/output/stage/gate/context progress fields. Already-open acquire is honestly labeled only an additional guard."),
        ],
        finite_delta_review=dict(
            only_two_test_function_bodies_changed=True,
            all_other_test_AST_equal=True,
            six_method_names_and_families_unchanged=True,
            accepted_source_pins_design_and_bounds_unchanged=True,
            raw_fact_expectations_public_API_schema_oracle_unchanged=True,
            reviewer_did_not_execute_subject_or_tests=True),
        design_review=[
            "Canonical raw scalar/count assignments stay first. Derived private counters/indices cannot replace raw authority or become serialized readiness.",
            "The append/index BaseException envelope starts before append and ends before invocation. It preserves an actually committed record or its absence, the original error and quarantine without delete/retry/scan/imagined native entry.",
            "Per-call fold watermarks distinguish pending from defined0, contribute identical known cells once, and never assume multiassignment atomicity. Failure including after-helper return stops new work.",
            "Direct canonical open/close pointers preserve ownership/known closure independently of cache/aux outcome. Named canonical report/consistency windows derive raw truth without healing quarantine or resuming work.",
            "Hot handle/read-known/ref/quota operations are prospectively constant in prior call count; hidden base-list/global dict-values scans remain forbidden by separate source review. A named canonical report remains allowed O(N+r).",
        ],
        before_evidence=dict(
            proof=pins[str(ROOT / "INDEXED-ACCOUNTING-ACTUAL-V2-BEFORE-PROOF-v2.json")],
            methods=6, intended_hot_scan_failures=4, functional_raw_passes=2,
            errors=0, audit_denials=0, source_hashes_unchanged=True,
            hot_observations=hot,
            meaning="Actual acceptedV2 call-list visits, not missing future helpers or a sourceV2 acceptance regression; the optimized predicates are not yet implemented"),
        chronology=[
            "Original v1 protocol/test/freeze preceded the first acceptedV2 probe and prospective indexed code; 88dd first result and its HOLD remain unchanged.",
            "The two harness closures produced v2 after that historical v1 run. V2 freeze's zero subject_runs means zero NEW v2-control invocations before its own freeze, not zero historical acceptedV2 runs.",
            "The retained24da v2-control replay follows the v2 freeze and still precedes indexed implementation. Future helper/quarantine modes are explicitly prospective and not claimed exercised on acceptedV2.",
        ],
        scope_limits=[
            "Preparation clearance only. It grants no indexed-source implementation or runtime authority; root's separate decision is required.",
            "Keep unchanged N4/4KiB/16KiB/R68/C92/E224/gen68, DATA50ee/e12, all48/same8/author16. Later source must pass the six controls in indexed mode plus compatibility and separate exact source peer.",
            "Measured access counters cover declared hot windows only; cleanup/report/warmup are cold. They are not timing, real native calls, full lifecycle complexity, full-roster scalability, physical memory fit or300s fit.",
            "Source must not evade CountingList via base-list calls, copied ledger or global dictionary traversal. Counter passes alone are insufficient source correctness evidence.",
            "No broad storage/output/first-entry/14-export/real-checker/physical-sink/full-roster/native/scientific gate is closed by this preparation.",
        ],
        reviewed_artifact_edits_by_peer=0, reviewer_subject_runs=0, reviewer_test_repeats=0,
        actual_API_calls=0, old_original_or_payload_operations=0,
        current_V2_acceptance_reopened=False, implementation_authorized=False,
        production_owner_bound=False, FFI_registration_proven=False,
        runtime_authorized=False, profile_qualified=False, verification_complete=False,
    )
    path = ROOT / "INDEXED-ACCOUNTING-INDEPENDENT-PRECODE-PEER-v2.json"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    note = """# Indexed-accounting design and pre-code peer

**CLEAR_DESIGN_AND_PRECODE_CONTROLS_ONLY.** Effective design `7e2b1b5b…` plus append-envelope clarification `147dc128…`, corrected controls `d76e1a2d…`/contract `cccf8a1f…` and freeze `52da9451…` close the two finite harness findings from preserved HOLD `50eff232…`. No material blocker remains in this preparation review.

CTRL3 now checks the entire declared common metric bound. The indexed-only otherwise-valid `owner.check()` at clock100 must refuse with the same original fault and no dispatch/progress; the already-open acquire is no longer presented as isolated quarantine evidence. Only those two test bodies changed. All other ASTs, six families, bounds, raw expectations, public API/schema and frozen oracle remain unchanged.

The accepted-v2 re-BEFORE proof `24da94c6…` retains exactly four intended hot-scan failures, two raw-functional passes and no errors/audit denials, with source hashes unchanged. Recorded visits are18/18 iteration for handle/known bytes,18 membership for the ref, and17 iteration+54 membership/one append for Read admission. No missing future helper caused a baseline failure. Original `88dd26aa…` and v1 artifacts remain.

The design keeps raw first facts authoritative, catches append/index interruptions before invocation, makes known contributions idempotent, quarantines failed folds and derives canonical reporting/cleanup facts without repair or resumed work. Full indexed source correctness remains unproved. Later source review must reject scan-hiding through base-list calls or alternate global traversals and retain all48/same8/author16 compatibility.

Chronology is explicit: v1 controls froze before the first probe; v2 controls froze before their own re-BEFORE and prospective code, after the preserved v1 run. Zero v2-control invocations at its freeze does not mean no historical accepted-v2 tests. Future private cache modes have not run yet.

This reviewer executed no subject/test and changed no reviewed artifact. List-access evidence is not timing, full-roster or real first-entry/FFI/physical-output qualification. No cap growth or implementation authority follows; root decides the next source-only stage separately. [Exact peer JSON](INDEXED-ACCOUNTING-INDEPENDENT-PRECODE-PEER-v2.json).
"""
    md = ROOT / "INDEXED-ACCOUNTING-INDEPENDENT-PRECODE-PEER-v2.md"
    with md.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(note)
    for output in (path, md):
        data = output.read_bytes()
        print(json.dumps(dict(path=str(output), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())))


if __name__ == "__main__":
    main()
