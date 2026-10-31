"""Finite root source-interface acceptance; no live verification or test replay."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {
    "verifier_bootstrap_interfaces_v2.py": "d937599212133ee7c036ee863b8c751885ffe60f7d657ec1ed5e506bf90c74eb",
    "check_verifier_bootstrap_interfaces_v2.py": "d516efd3dad05e1895dba1f520a4087b6bef35ef00cc81110c306a9c9913dcb8",
    "VERIFIER-BOOTSTRAP-INTERFACES-PURE-PROOF-v2.json": "e15aefdd042b704abe8d1fd6e02e1b6bd61d544a2723085251a555e50b63a3d3",
    "VERIFIER-BOOTSTRAP-INTERFACES-PEER-REVIEW-v2.json": "d9e006e61da63266b5c4e5fb8e5edb86a04d09e85b00eb2198436a73a826075d",
    "VERIFIER-BOOTSTRAP-PEER-FAULTS-AFTER-v2.json": "f5dd9b2a89f3539b132300a08cc53a61cbc8bbd2cd0b4e6e8ae2e11ac69ebeca",
    "VERIFIER-BOOTSTRAP-INTERFACES-PEER-REVIEW-v1.json": "c54a9439cb8968a26ca73a3cae87ad812de9f1c72415dfab7e0a237833a6296d",
    "VERIFIER-BOOTSTRAP-PEER-FAULTS-BEFORE-v1.json": "030ade7137ac35f68ed5966d2ec1de04507ac290c4b16c0db8ecb69f48e6c05c",
}


def main():
    blobs, records = {}, {}
    for name, expected in PINS.items():
        data = (HERE / name).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected:
            raise ValueError("Source-interface pin mismatch: " + name)
        blobs[name] = data
        records[name] = {"sha256": digest, "bytes": len(data)}
    author = json.loads(blobs["VERIFIER-BOOTSTRAP-INTERFACES-PURE-PROOF-v2.json"])
    peer = json.loads(blobs["VERIFIER-BOOTSTRAP-INTERFACES-PEER-REVIEW-v2.json"])
    assert author["status"] == "V2_PURE_INTERFACE_CORRECTION_PASS_INDEPENDENT_REVIEW_PENDING"
    assert author["methods"] == 22
    assert type(author["failures"]) is int and type(author["errors"]) is int
    assert author["failures"] == author["errors"] == 0
    assert peer["status"] == "CLEAR_v2_pure_injected_interface_corrections_no_live_qualification"
    assert peer["review_complete"] is True and peer["findings"] == []
    result = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACCEPTED_V2_PURE_INJECTED_BOOTSTRAP_INTERFACES_ONLY",
        "inputs": records, "author_methods": 22,
        "independently_reproduced_then_fixed_findings": ["foreign source read port", "nested returned diagnostic aliases"],
        "independent_after_probes": 2,
        "scope": "Same-owner original-clock handoff, source-bound read interface, ordinary detached diagnostic snapshots and closed injected-loader interfaces. No real first-entry or production engine integration.",
        "verification_complete": False, "real_profile_qualified": False,
        "execution_authorized": False, "old_negative_and_timeout_unchanged": True,
        "remaining": ["Real platform/entry/engine/sink and exact authority/caps", "Captured-byte journal, archive, resource and new-profile checkers", "New native wire/protocol/source review before runtime decision"],
    }
    output = HERE / "VERIFIER-BOOTSTRAP-INTERFACES-SCOPED-ACCEPTANCE-v2.json"
    with output.open("xb") as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": result["status"], "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
