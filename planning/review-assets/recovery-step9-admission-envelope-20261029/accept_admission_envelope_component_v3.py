"""Root metadata acceptance of the final standalone calculator evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ALLOWED = {HERE, HERE.parent / "recovery-step9-production-preflight-20261029"}
PINS = {
    "admission_envelope_v3.py": "24889920f1f0d4e6f26130c053adde9cdf7f9e006a250f9f9bae274e61ac0501",
    "ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v4.json": "5ba8af6c77ddf3f7e23bb377589abcc348a7fb91a59a5766c409672a640d94cf",
    "ADMISSION-ENVELOPE-AUTHOR-PROOF-v3.json": "e05425e0679d64adaa3c420bb3fc9d83987b44a0d99a40486933bae45b03ead3",
    "ADMISSION-ENVELOPE-INDEPENDENT-REGRESSION-BEFORE-v1.json": "8a02fb18aed5469637e11ff990dacad35e5e4472b3d7ae217c45756ab286be05",
    "ADMISSION-ENVELOPE-F2-METACLASS-BEFORE-v1.json": "c4c84c6a5b17fae8a0509dcbaf89d83e3e8ef972687636bb3ef460cefa9e8dee",
    "ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json": "cb4c6dd46cd8e02bc45c9bbec69a52f0a6ee1baea633eefaed85eeb018f57cc7",
    "admission_envelope_independent_tests_v1.py": "e670199a7c4c50dc7eb540f8e5a021919464e67a891ef00fa48902d21b783bcc",
    "admission_envelope_regressions_v1.py": "5644882f8d67c0121b4967538d3af9eedf200266792bdb0d07b08e0392171e34",
    "admission_envelope_f2_metaclass_regression_v1.py": "d158e3db6f2ebc4aedcfc168d2dcd9ffb383047c850e10c842c8855ca4990f93",
}


def pin(path):
    assert path.resolve().parent in ALLOWED, str(path)
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    for item in ("freeze-name", "freeze-sha256", "peer-name", "peer-sha256"):
        parser.add_argument("--" + item, required=True)
    args = parser.parse_args()
    assert Path(args.freeze_name).name == args.freeze_name and Path(args.peer_name).name == args.peer_name
    inputs = {}
    for name, expected in {**PINS, args.freeze_name: args.freeze_sha256, args.peer_name: args.peer_sha256}.items():
        record = pin(HERE / name)
        assert record["sha256"] == expected, name
        inputs[name] = record
    freeze = read(args.freeze_name)
    records = freeze["inputs"]
    for record in records.values():
        assert pin(Path(record["path"])) == record
    run = read("ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v4.json")
    assert run["status"] == "passed" and run["methods"] == 9
    assert run["unique_original_metadata_vectors"] == run["original_vectors_matched"] == 30
    assert run["focused_methods"] == 4 and run["metaclass_methods"] == 1
    assert not run["failures"] and not run["errors"] and not run["audit_denials"] and not run["closed_import_denials"]
    assert not run["original_check_exception_identity_failures"]
    assert all(value is True for value in run["input_bytes_unchanged"].values())
    assert all(value is False for value in run["qualification"].values())
    assert run["actual_analysis_invocations"] == 59 and run["actual_analysis_returns"] == 38 and run["actual_analysis_exceptions"] == 21
    assert run["actual_check_invocations"] == 488 and run["actual_check_returns"] == 470 and run["actual_check_exceptions"] == 18
    assert len(run["getter_invocations"]) == 113
    assert run["actual_target_API_calls"] == run["original_payload_operations"] == 0
    observations = run["focused_regression_observations"]
    assert len(observations) == 4
    assert observations[0]["metrics"] == {"object_calls": 1, "generator_resumptions": 0, "key_yields": 0}
    assert observations[0]["profile_restored"] and observations[0]["source_object_code_unchanged"]
    assert observations[1]["actual_code"] == "TYPE_DOMAIN" and observations[1]["hook_calls"] == []
    assert all(row["actual_code"] == "MODULE_GRAPH" for row in observations[2:])
    meta = run["metaclass_regression_observations"]
    assert len(meta) == 1 and meta[0]["actual_code"] == "TYPE_DOMAIN" and meta[0]["metaclass_equality_calls"] == []
    author = read("ADMISSION-ENVELOPE-AUTHOR-PROOF-v3.json")
    assert author["status"] == "PASS" and author["methods"] == 8 and author["analyze_invocations"] == 50
    assert len(author["results"]) == 8 and all(row["passed"] is True for row in author["results"])
    assert not author["audit_denials"]
    peer = read(args.peer_name)
    assert peer["status"].startswith("CLEAR") and peer["material_blockers"] == []
    peer_text = json.dumps(peer, sort_keys=True)
    for expected in (PINS["admission_envelope_v3.py"], PINS["ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v4.json"], args.freeze_sha256):
        assert expected in peer_text
    inputs[Path(__file__).name] = pin(Path(__file__))
    result = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACCEPTED_STANDALONE_V3_METADATA_ENVELOPE_CALCULATOR_SOURCE_PURE_ONLY",
        "inputs": inputs, "verified_evidence_freeze_pins": len(records),
        "validation": {"original_metadata_vectors": 30, "independent_methods": 9,
                       "independent_limit_boundaries": 12, "focused_methods": 4,
                       "additional_F2_methods": 1, "author_methods": 8,
                       "independent_analyze_calls": 59, "independent_check_calls": 488,
                       "original_check_exception_stops": 18, "getter_calls": 113,
                       "author_analyze_calls": 50, "pure_seconds": run["elapsed_seconds"]},
        "fixed": ["Bounded dictionary cardinality before key traversal/copy.",
                  "Exact numeric types reject subclasses as TYPE_DOMAIN without producer equality/coercion hooks; bool and other numeric codes preserved.",
                  "Declared graph/binding precedes aggregate consistency and sum overflow."],
        "chronology": "Original30 and strict tests predate V1. Four focused controls predate V2; the F2 metaclass control predates V3. Initial UTF16 bootstrap failure, corrected original30 pass, author7/8, four V1 failures, V2 eight-method pass, metaclass failure and all source versions remain preserved. Final source/test expectations unchanged during final replay.",
        "scope": "Deterministic seven-key metadata API,32 derived fields,four nonauthorizing statuses,12 declared limits and11 logical coefficients. Explicit nulls remain unresolved. Pure source arithmetic/immutability/cancellation only.",
        "limits": ["WITHIN_DECLARED_BOUNDS_ONLY is conditional arithmetic, not actual source authenticity, operational admission, implemented storage/streaming/output, measured RSS/time or full-roster fit.",
                   "The mixed-role baseline R69/C93 exceeds unchanged runtime R68/C92. No existing runtime cap or role support changes.",
                   "Paths retain bounded C/D lexical identity; metadata digest syntax is not actual hash verification. No original filesystem discovery or payload pass occurred.",
                   "No application/default change, original experiment replay, model/native/compiler invocation, new data download or provider spending."],
        "qualification": dict(run["qualification"]), "application_changed": False,
        "application_tests_rerun": False, "provider_spending": 0,
        "actual_target_API_calls": 0, "original_payload_operations": 0,
        "scientific_validation": "not_established",
        "next": "Select and qualify the actual role-aware producer/storage/serialization representation and exact future roster before using any declared envelope to propose runtime admission.",
    }
    destination = HERE / "ADMISSION-ENVELOPE-SCOPED-ACCEPTANCE-v3.json"
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "sha256": pin(destination)["sha256"], "freeze_pins": len(records)}))


if __name__ == "__main__":
    main()
