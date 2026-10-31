"""Retain the completed finite harness-validator peer; no reviewed code runs."""
from pathlib import Path
import ast
import hashlib
import json


PHASE = Path(__file__).resolve().parent
EXPECTED = {
    "shared_owner_snapshot_validator_v1.py": "afa71df1ebba3eb7da83890b6e86675597894600cd593578b34f5f1a12cefefc",
    "SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json": "50ee2d7a9285370e6a3f0d18801c43e441b327f7ceac9eb46ebdf0463eff28d6",
    "SHARED-OWNER-CONTINUATION-PROPOSAL-v2.json": "90fc021a044bba34953a8f8f8e42b05f5d61f49da945044e1e108f92bb1fc3cd",
    "SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json": "eb5147d200bcc0108b71968d69f6b251c29b56dd52d926a8606504682134d9b8",
    "SHARED-OWNER-ROOT-SOURCE-SCOPE-v1.json": "4db8622f185edb1488a0066205b6248f0eb37b539e0806d04d748f277ea8e6ee",
    "check_shared_owner_snapshot_validator_v1.py": "e5df657200087764994eefc064361a555bf11a4a5f8a65fb420601884e2e14ba",
    "SHARED-OWNER-SNAPSHOT-VALIDATOR-PURE-PROBES-FIRST-v1.json": "43799e0cd5aa704cb3477657936a04795426927f9341fc14c45621066b05d13f",
    "check_shared_owner_snapshot_validator_peer_v1.py": "565f84832133633c4da744a1821f326b94525af6eb4036f5a1d377e82ed164dd",
    "SHARED-OWNER-SNAPSHOT-VALIDATOR-INDEPENDENT-PROOF-v1.json": "1f0124055a237dcc8ecc409a62d3575783a72c180bfabb63409bbba2fbfa4d75",
}


def main():
    captured = {name: (PHASE / name).read_bytes() for name in EXPECTED}
    pins = {}
    for name, raw in captured.items():
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == EXPECTED[name], name
        pins[name] = dict(path=str(PHASE / name), bytes=len(raw), sha256=digest)
    prior = json.loads(captured["SHARED-OWNER-SNAPSHOT-VALIDATOR-PURE-PROBES-FIRST-v1.json"])
    independent = json.loads(captured["SHARED-OWNER-SNAPSHOT-VALIDATOR-INDEPENDENT-PROOF-v1.json"])
    assert prior["probe_count"] == 675 and prior["passed"] is True and prior["failures"] == []
    assert independent["probe_count"] == 54 and independent["status"] == "passed"
    assert independent["failures"] == [] and independent["denied_operation_attempts"] == []
    tree = ast.parse(captured["shared_owner_snapshot_validator_v1.py"])
    imports = [ast.unparse(node) for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert imports == ["from math import isfinite"]
    assert not any(isinstance(node, (ast.Try, ast.TryStar)) for node in ast.walk(tree))
    record = dict(
        schema_version=1,
        status="CLEAR_HARNESS_VALIDATOR_SOURCE_PURE_ONLY",
        material_blockers=[],
        recorded_at_utc="2026-10-29 16:34:16 UTC",
        reviewer="native_039_acceptance_audit",
        source=pins["shared_owner_snapshot_validator_v1.py"],
        helper_sha256=EXPECTED["shared_owner_snapshot_validator_v1.py"],
        authority=pins["SHARED-OWNER-ROOT-SOURCE-SCOPE-v1.json"],
        closed_DATA=pins["SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json"],
        inputs=pins,
        provenance=dict(
            author="Grammar-delegated independent harness helper, reported paused before this review",
            author_probes=675,
            author_proof_status="passed",
            author_expected_fixture_cases_read=False,
            author_subject_modules_imported=False,
            author_subject_outputs_read=False,
            independent_probes=54,
            independent_proof_status="passed",
            independent_specimens="Authored directly from DATA shape; not source states, frozen expected cases, or actual subject outputs",
            independent_source_execution="Pinned validator only, executed from the exact captured source bytes; no import-path fallback",
            independent_denied_operation_attempts=0),
        finite_review=[
            "All Snapshot and nested record key sets read against DATA50ee; exact dict/list and closed enum checks are present.",
            "Flags use exact bool; counters/IDs/sizes/capacities use exact nonbool int and integer comparisons. Huge integer time stays integer; finite-float checks do not coerce integers.",
            "Signed32 BOOL accepts nonzero +2/-1 and endpoints; DWORD/COUNT32/handle tagged domains distinguish UNOBSERVED, NULL and scalar values.",
            "File/query/call/event/module/stage bounds and applicable frame caps are explicit. UTF16 path-unit limits reject lone surrogates without filesystem access.",
            "Prepared-undispatched payloads and nullable close_success retain allowed DATA shapes; 8193 publication bytes and truthy integer flags reject.",
            "Diagnostic identity requires exact True from the external token callback. No try/catch exists in the helper, so callback ValueError, OverflowError, MemoryError, KeyboardInterrupt, SystemExit and its own validation error propagate as the exact original object.",
            "The only import is math.isfinite. No filesystem, source loader, fixture lookup, subject component or SDK dependency exists in this validator.",
        ],
        explicit_limits=[
            "This is harness format validation, not qualification of a hypothetical or actual subject Snapshot.",
            "Actual opaque source identity remains an external owner token resolver/is check. Passing this callback in a synthetic probe grants no production provenance.",
            "It does not independently prove the lifecycle, gate truth, actual raw accounting, captured payload/digest correspondence, original file identity, canonical admission or all cross-record semantic equations. Independent literal comparisons, binding spies and source peer remain required.",
            "No numeric cap was invented where DATA supplies none (secondary diagnostic count, loader cache-hit count, or per-args_repr string length). DATA's existing <=8 repr entries is enforced.",
            "675 author probes and 54 peer probes are separate retained evidence sets, not a 48-history subject run or a whole-component acceptance.",
        ],
        source_changes_by_reviewer=0,
        frozen_expected_cases_read=0,
        subject_modules_imported=0,
        subject_outputs_read=0,
        actual_API_calls=0,
        original_or_payload_operations=0,
        FFI_registration_proven=False,
        production_owner_bound=False,
        runtime_authorized=False,
        profile_qualified=False,
        verification_complete=False,
    )
    json_path = PHASE / "SHARED-OWNER-SNAPSHOT-VALIDATOR-INDEPENDENT-PEER-v1.json"
    with json_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    text = """# Shared-owner snapshot validator peer

**CLEAR_HARNESS_VALIDATOR_SOURCE_PURE_ONLY.** No material blocker in the finite review of `shared_owner_snapshot_validator_v1.py` (`afa71df1…`) against closed DATA v2 (`50ee2d7a…`). The helper was unchanged.

All nested closed record keys, strict flag/integer domains, enum and declared bounds were read against DATA. Scalar facts retain signed32 BOOL/nonzero semantics and tagged UNOBSERVED/NULL distinctions. Nullable close outcomes and prepared-undispatched callbacks remain representable. The validator has no data catch and imports only `math.isfinite`.

The independent [54-probe proof](SHARED-OWNER-SNAPSHOT-VALIDATOR-INDEPENDENT-PROOF-v1.json) passed with no I/O attempts under denial hooks. Probes used independently authored format specimens, including signed BOOL boundaries, UTF16 path units, oversized integer time, unknown keys, bool counters, and exact original callback exception propagation. Only the pinned validator source was executed; no subject implementation, frozen expected case, helper source cohort or subject output was loaded. The separately retained author [675-probe record](SHARED-OWNER-SNAPSHOT-VALIDATOR-PURE-PROBES-FIRST-v1.json) also binds the same helper and reports no fixture/subject reads.

This clearance concerns harness format checking. It does not establish lifecycle or gate truth, actual accounting, file identity, captured-byte/digest correspondence, source token provenance, or subject Snapshot correctness. External identity checks, literal comparisons, binding spies and the separate three-source peer are still required. Where DATA provides no numeric length cap, this review introduces none.

No real FFI/API, SDK, original-source closure, model/CPU/pack access or runtime operation occurred. All production, profile and verification qualification flags remain false. Exact pins and provenance are in the [peer JSON](SHARED-OWNER-SNAPSHOT-VALIDATOR-INDEPENDENT-PEER-v1.json).
"""
    md_path = PHASE / "SHARED-OWNER-SNAPSHOT-VALIDATOR-INDEPENDENT-PEER-v1.md"
    with md_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    for path in (json_path, md_path):
        raw = path.read_bytes()
        print(json.dumps(dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())))


if __name__ == "__main__":
    main()
