"""Authorize the three reproduced source fixes after pre-fix controls."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {
    "admission_envelope_v1.py": "4c86530b2cab406d2a78bb707a9efdfab5533432d64ee34312c2ad6287124242",
    "ADMISSION-ENVELOPE-ROOT-SOURCE-SCOPE-v1.json": "30644e8c0b59356b7dda2f9fde30f366fec80638945d051dc4c5baed1e8f74c3",
    "ADMISSION-ENVELOPE-SOURCE-INDEPENDENT-HOLD-v1.json": "da3b47e59aca5d28971d55c1fe9cfc5157e487e18940f12c93b9ac6d02615b7b",
    "ADMISSION-ENVELOPE-REGRESSION-FREEZE-v1.json": "c82d411a50359e2dfba7c0f491c64d56db4caac1b824ae73a7bcebd2ca2262ae",
    "admission_envelope_regressions_v1.py": "5644882f8d67c0121b4967538d3af9eedf200266792bdb0d07b08e0392171e34",
    "ADMISSION-ENVELOPE-INDEPENDENT-REGRESSION-BEFORE-v1.json": "8a02fb18aed5469637e11ff990dacad35e5e4472b3d7ae217c45756ab286be05",
    "ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v2.json": "0cf04ddbe83d147ce33b48b8b70e104430d841093a5999ddd9307a3062fa15a1",
    "ADMISSION-ENVELOPE-AUTHOR-FIRST-PROOF-v1.json": "c3f79da767d1270d437692e5e05c5378f9aea0736b307b4fec1168cd468f5113",
    "check_admission_envelope_author_v1.py": "845dda7329c7bcb79264a9619a528acbd777ce4fefec2b9412a2094b85dc247f",
    "ADMISSION-ENVELOPE-PRECODE-VECTORS-v1.json": "cb4c6dd46cd8e02bc45c9bbec69a52f0a6ee1baea633eefaed85eeb018f57cc7",
    "admission_envelope_independent_tests_v1.py": "e670199a7c4c50dc7eb540f8e5a021919464e67a891ef00fa48902d21b783bcc",
}


def pin(path):
    assert path.resolve().parent == HERE
    data = path.read_bytes()
    return {"path": str(path.resolve()), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def read(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def main():
    inputs = {}
    for name, expected in PINS.items():
        record = pin(HERE / name)
        assert record["sha256"] == expected, name
        inputs[name] = record
    hold = read("ADMISSION-ENVELOPE-SOURCE-INDEPENDENT-HOLD-v1.json")
    assert hold["status"] == "HOLD_FINITE_THREE_SOURCE_BOUNDARIES" and len(hold["material_blockers"]) == 3
    before = read("ADMISSION-ENVELOPE-INDEPENDENT-REGRESSION-BEFORE-v1.json")
    assert before["methods"] == 4 and len(before["failures"]) == 4 and not before["errors"]
    assert not before["audit_denials"] and not before["closed_import_denials"]
    assert all(value is True for value in before["bytes_unchanged"].values())
    baseline = read("ADMISSION-ENVELOPE-INDEPENDENT-ACTUAL-PROOF-v2.json")
    assert not baseline["failures"] and not baseline["errors"]
    author = read("ADMISSION-ENVELOPE-AUTHOR-FIRST-PROOF-v1.json")
    assert author["methods"] == 8 and author["analyze_invocations"] == 50
    target = HERE / "admission_envelope_v2.py"
    assert not target.exists()
    inputs[Path(__file__).name] = pin(Path(__file__))
    result = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "AUTHORIZED_DISTINCT_V2_SOURCE_FOR_EXACT_THREE_REPRODUCED_FIXES",
        "inputs": inputs, "verified_inputs": len(inputs), "target": str(target),
        "allowed_fixes": [
            "_object: refuse an incorrect exact-built-in dictionary cardinality before key traversal/set construction; preserve bounded key-type/key-set checks for correctly sized objects.",
            "_integer: reject int subclasses as TYPE_DOMAIN without custom numeric/coercion/comparison hooks; preserve bool and other pinned numeric codes/domains.",
            "_steps: finish declared graph/binding validation before aggregate mismatch and overflowing total summation can preempt it. Preserve formulas, checked integer arithmetic and unknown propagation."
        ],
        "constraints": [
            "Keep V1 source, first author7/8, initial codec failure, corrected30 pass, finite HOLD and four before failures immutable.",
            "Use a separately named coherent V2. Freeze source before import/test; record exact AST delta, preserving unrelated helpers/constants/API/serialization and callback boundaries.",
            "Run unchanged original30/e670 plus four regression methods5644 and unchanged eight author assertion bodies. Preserve first V2 results. No oracle edits, fourth family or relaxed guard.",
            "Retain codec preload9719 in trusted bootstrap and the active no-I/O/import audit. Profiling observes actual code without source-global replacement or timing guesses.",
            "No actual runtime/cap/hash-only streaming/source discovery/physical output/application/native/model/data download or paid-query change."
        ],
        "source_correction_authorized": True, "pure_subject_tests_authorized": True,
        "qualification": dict(before["qualification"]), "application_changed": False,
        "provider_spending": 0, "actual_target_API_calls": 0,
    }
    destination = HERE / "ADMISSION-ENVELOPE-ROOT-CORRECTION-SCOPE-v2.json"
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "sha256": pin(destination)["sha256"], "verified_inputs": len(inputs)}))


if __name__ == "__main__":
    main()
