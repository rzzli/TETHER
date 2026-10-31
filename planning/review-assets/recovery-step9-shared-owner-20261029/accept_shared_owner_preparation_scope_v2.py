"""Retain root design acceptance and literal-preparation scope; no component runs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PINS = {
    "SHARED-OWNER-CONTINUATION-PROPOSAL-v1.json": "ed72dbb98842f3daa61e4bc89e5619335bed6e3226546016acd87ffd6146f953",
    "SHARED-OWNER-PROPOSAL-INDEPENDENT-PEER-v1.json": "68ed430031b8f6c6aeccca23dda480b42c43e51950cde8b684f963f4c14fcece",
    "SHARED-OWNER-CONTINUATION-PROPOSAL-v2.json": "90fc021a044bba34953a8f8f8e42b05f5d61f49da945044e1e108f92bb1fc3cd",
    "SHARED-OWNER-PROPOSAL-INDEPENDENT-PEER-v2.json": "ba12adb90ab423cbd233ad868c2fd746f8f430fa6e6a59bd92726547ebfb0379",
    "SHARED-OWNER-CONTINUATION-INTERFACE-REVIEW-v1.json": "e7754c5a82c306aedadd336b55840c134b8d34f909fef30e35d1c88687c03179",
    "SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json": "eb5147d200bcc0108b71968d69f6b251c29b56dd52d926a8606504682134d9b8",
    "SHARED-OWNER-SYNTHETIC-INPUT-PREPARATION-PROOF-v1.json": "2b7f3c88f3affa6aefca8f664ee49e7e1b612ede1bc4539336ba66e4e8db8d5b",
    "SHARED-OWNER-SYNTHETIC-INPUT-FREEZE-v1.json": "9f1fbd21bd11b06e969c01a15a773fa6f60e54d685ae62ed7ddd6bc24f76482e",
    "SHARED-OWNER-COHORT-INDEPENDENT-PEER-v1.json": "40adfa21e53f2d67dba648ed069f4d577c48afb5df10f86df8e0bc4ee4fee481",
}


def pin(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def read(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def main():
    inputs = {}
    for name, expected in PINS.items():
        inputs[name] = pin(HERE / name)
        assert inputs[name]["sha256"] == expected, name
    proposal = read("SHARED-OWNER-CONTINUATION-PROPOSAL-v2.json")
    peer = read("SHARED-OWNER-PROPOSAL-INDEPENDENT-PEER-v2.json")
    assert peer["status"] == "CLEAR_SOURCE_DESIGN_FOR_LITERAL_FIXTURE_PREPARATION_ONLY"
    assert peer["material_blockers"] == []
    assert all(value is False for value in proposal["qualification"].values())
    assert proposal["active_original_API_subset"] == [
        "CreateFileW", "GetFileType", "GetFileInformationByHandleEx",
        "GetFinalPathNameByHandleW", "GetFileSizeEx", "ReadFile", "CloseHandle",
    ]
    assert set(proposal["publication_protocol"]["kinds"]) == {"candidate", "cleanup", "failure", "receipt", "seal"}
    assert set(proposal["proposed_files"]) == {"shared_owner_v1.py", "shared_file_ports_v1.py", "continue_verification_v1.py"}
    assert len(proposal["pure_fixture_matrix"]) == 14
    caps = proposal["joint_caps"]["first_batch"]
    assert (caps["N_max"], caps["B_max"], caps["M_max"], caps["S"]) == (4, 2, 2, 0)
    assert caps["file_bytes_max"] == 4096 and caps["captured_bytes_max"] == 16384
    r_max = 4 * (1 + 16)
    assert (r_max, 6 * 4 + r_max, 6 * 4 + 2 * 2 + 2 * 2 + 64 + 128) == (68, 92, 224)
    raw_storage = 65536 + 8202 + 4 * (8 + 8202 + 8) + 16384
    assert raw_storage == 122994 and raw_storage <= 131072
    cohort = read("SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json")
    assert len(cohort["blobs"]) == 3
    assert sorted(row["bytes"] for row in cohort["blobs"]) == [58, 68, 83]
    for row in cohort["blobs"]:
        blob = bytes.fromhex(row["utf8_hex"])
        assert len(blob) == row["bytes"] and hashlib.sha256(blob).hexdigest() == row["sha256"]
    assert cohort["totals"]["total_bytes"] == 209
    raw_acceptance = ROOT / "planning/review-assets/recovery-step9-raw-adoption-20261029/RAW-ADOPTION-CORE-SCOPED-ACCEPTANCE-v3.json"
    accepted = pin(raw_acceptance)
    assert accepted["sha256"] == "5afb82f048dd05e65be5223ead9410c40e4670c429c3b5b762ee49d8c7db87a7"
    inputs[str(raw_acceptance.relative_to(ROOT))] = accepted
    inputs[Path(__file__).name] = pin(Path(__file__))
    result = {
        "schema_version": 1,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACCEPTED_DESIGN_AND_INPUTS_LITERAL_PREPARATION_ONLY",
        "inputs": inputs,
        "scope": "Exactly one canonical bootstrap-successor owner from the cohort start, two non-owning views and one continuation-only controller; seven injected original-file APIs plus fictional sink, over the unchanged209B invented input cohort.",
        "authorized_now": [
            "Agree and freeze exact public observation/refusal/snapshot signatures needed by independent fixture author and source author before implementation.",
            "Author a closed literal operation/fault/expected-observation schema and finite schedules for the14 declared causal groups; target at most48 histories with bounded variations, preserving the209B cohort.",
            "Author and run only data/AST/shape/closed-script interchange checks. Toy helper execution and under-test component implementation are not part of preparation.",
            "Obtain independent literal/schema peer review, then retain a separate root source/pure implementation decision for exactly the three proposed files and independent tests."
        ],
        "required_fixture_controls": [
            "Use at least one nonzero original start100/work395/hard400 and preserve all already spent setup/bootstrap time.",
            "Reference identity invariants are tested with actual source-issued objects, never serialized ready flags or copied ownership.",
            "Expected projections and injected fake actions belong only to the independent harness; no case ID/fault label/expected selector enters under-test source.",
            "Cover all14 groups, including the three preserved raw-core regressions, current early liveness, once-only closure, late first facts and stopped buffer retention.",
            "State complete/negative/refused/incomplete pure-seam outcomes separately from all real/native/source/scientific qualifications.",
            "First-cohort authority/checker callbacks are explicitly fixture-only branded injections; captured marker-chain loading is a separate same-owner observation. No real source-qualified factories are claimed.",
            "Only seven original operations and ReadFile byte accounting are active. Physical write/flush/close observations and remaining exports stay outside this batch."
        ],
        "bounds": {"N_max": 4, "B_max": 2, "M_max": 2, "R_max": 68, "C_max": 92, "E_max": 224,
                   "raw_payload_storage_max": raw_storage, "raw_payload_ceiling": 131072,
                   "immutable_capture_bytes_max": 16384, "input_blob_bytes": 209,
                   "output_kinds": ["candidate", "cleanup", "failure", "receipt", "seal"]},
        "preserved": "Original ed72 proposal and68ed five-finding HOLD, all accepted source baselines and negative/timeout experiments remain unchanged.",
        "interpretation": "Explicit fixture-only factory policy governs inherited source-bound wording. Payload bounds are source-derived, not measured process memory or production fit.",
        "under_test_implementation_authorized_now": False,
        "actual_API_calls": 0, "original_or_payload_operations": 0,
        "runtime_authorized": False, "FFI_registration_proven": False,
        "production_owner_bound": False, "real_checkers_bound": False,
        "originals_authenticated": False, "profile_qualified": False,
        "verification_complete": False, "scientific_validation": "not_established",
    }
    destination = HERE / "SHARED-OWNER-ROOT-PREPARATION-SCOPE-v2.json"
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "sha256": pin(destination)["sha256"], "inputs": len(inputs)}))


if __name__ == "__main__":
    main()
