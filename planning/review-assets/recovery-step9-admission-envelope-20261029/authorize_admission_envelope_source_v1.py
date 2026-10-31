"""Root source/pure scope after exact pre-code review; no subject import."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREFLIGHT = HERE.parent / "recovery-step9-production-preflight-20261029"
ALLOWED = {HERE, PREFLIGHT}
EXPECTED = {
    HERE / "ADMISSION-ENVELOPE-PRECODE-FIXTURE-FREEZE-v1.json": "5478b0144c737ff8876c9273fe5281790f3fe97aa5b7cfac2bae4b1d4d222bc6",
    PREFLIGHT / "ADMISSION-ENVELOPE-CALCULATOR-PROPOSAL-v1.json": "038611daa69c5749def12d64dedc0b9afebdbfba2aff7d0e93981551e08d2cb8",
    PREFLIGHT / "ADMISSION-ENVELOPE-FINITE-CLARIFICATIONS-v2.json": "57ff21a8955de95f61fa059543e33c1ace52726efbc36b286a52310af5addf97",
}


def pin(path):
    assert path.resolve().parent in ALLOWED
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--peer-name", required=True)
    parser.add_argument("--peer-sha256", required=True)
    args = parser.parse_args()
    assert Path(args.peer_name).name == args.peer_name
    expected = {**EXPECTED, HERE / args.peer_name: args.peer_sha256}
    inputs = {}
    for path, checksum in expected.items():
        record = pin(path)
        assert record["sha256"] == checksum, path.name
        inputs[path.name] = record
    freeze = json.loads((HERE / "ADMISSION-ENVELOPE-PRECODE-FIXTURE-FREEZE-v1.json").read_text(encoding="utf-8"))
    assert freeze["metadata_vectors"] == 30 and not freeze["subject_source_present"]
    assert freeze["subject_imports"] == freeze["subject_tests"] == 0
    for record in [*freeze["inputs"].values(), freeze["provenance"], freeze["freezer"]]:
        assert pin(Path(record["path"])) == record
        inputs[Path(record["path"]).name] = record
    peer = json.loads((HERE / args.peer_name).read_text(encoding="utf-8"))
    assert peer["status"].startswith("CLEAR") and peer["material_blockers"] == []
    peer_text = json.dumps(peer, sort_keys=True)
    for checksum in EXPECTED.values():
        assert checksum in peer_text
    subject = HERE / "admission_envelope_v1.py"
    assert not subject.exists(), "Source must follow this exact scope and pre-code freeze"
    inputs[Path(__file__).name] = pin(Path(__file__))
    result = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "AUTHORIZED_SINGLE_PURE_METADATA_CALCULATOR_AND_FROZEN_TESTS_ONLY",
        "inputs": inputs, "subject_path": str(subject),
        "allowed": ["One standard-library admission_envelope_v1.py implementing the exact seven-key API/32 derived fields/four statuses under the pinned effective contract.",
                    "Freeze the coherent source before import/test, then run the unchanged 30 literal vectors and four frozen interface test methods with honest invocation/check/exception counts.",
                    "At most eight bounded author methods for ordinary-container refusal, immutable report fields, numeric domains and callback boundaries; report inputs/counts honestly.",
                    "Independent exact source review and root retained-evidence decision after tests. Preserve the first source, first results and any failures; a correction needs a distinct successor and unchanged oracle."],
        "limits": ["Metadata-only arithmetic and bounded serialization; never allocate derived byte pools or iterate C/R represented call counts.",
                   "Use exact built-in structural snapshots; cancellation callback exceptions retain identity. No inherited clock/owner/native authority is created.",
                   "Logical representation coefficients are declarations, not proven producer layouts or measured RSS/time. WITHIN_DECLARED_BOUNDS_ONLY is never executable admission.",
                   "No application source/default changes, current runtime cap lift or actual hash-only/streaming/output implementation.",
                   "No original/payload/source-closure pass, old-run replay, Win32/ctypes/SDK/C++/native/model/tokenizer operation, new download, account access or paid query."],
        "source_implementation_authorized": True, "pure_subject_tests_authorized": True,
        "actual_runtime_authorized": False, "application_changed": False,
        "provider_spending": 0, "actual_target_API_calls": 0,
        "qualification": dict(freeze["qualification"]),
    }
    destination = HERE / "ADMISSION-ENVELOPE-ROOT-SOURCE-SCOPE-v1.json"
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "sha256": pin(destination)["sha256"], "verified_inputs": len(inputs)}))


if __name__ == "__main__":
    main()
