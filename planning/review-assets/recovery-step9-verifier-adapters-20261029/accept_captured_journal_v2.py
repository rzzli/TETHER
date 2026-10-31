"""Root acceptance for captured bytes and the exact v7 source policy only."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {
    "captured_journal_v2.py": "d6c2f8ef61ffda069f7cbb41c5c06417d2e0fd530ce490e9488442131e385d91",
    "check_captured_journal_v2.py": "3bd8261596694995c40fc67d07f7cdeefd805b33ed5ea6522b7b723700f60609",
    "CAPTURED-JOURNAL-FIXTURE-FREEZE-v1.json": "cd4f6b3f381a837d790dfcad84e92231111456e3eb6648a0ebd7617c84980140",
    "CAPTURED-JOURNAL-SOURCE-PURE-PROOF-v2.json": "3be62ccf191f57714c61760d44bb43928b23a692f528f8550bd348755c16a7a6",
    "CAPTURED-JOURNAL-INDEPENDENT-PEER-v1.json": "d7b6c1d13e96ed6236b0a5acb9e3a37ef35ee9d36e4d87974f0ca26a53d5ae97",
    "CAPTURED-JOURNAL-INDEPENDENT-PEER-v2.json": "36d149366aa6687654bbf41daca961f685339afb28c786eb4d888ba0292cb0b3",
    "CAPTURED-JOURNAL-INDEPENDENT-AFTER-PROOF-v2.json": "3be918806ea84853c1802d41cd375c7d7882f68d1d91fa005007461efe96c49c",
}


def main():
    blobs, inputs = {}, {}
    for name, expected in PINS.items():
        data = (HERE / name).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected:
            raise ValueError("Journal component pin mismatch: " + name)
        blobs[name] = data
        inputs[name] = {"bytes": len(data), "sha256": digest}
    author = json.loads(blobs["CAPTURED-JOURNAL-SOURCE-PURE-PROOF-v2.json"])
    peer = json.loads(blobs["CAPTURED-JOURNAL-INDEPENDENT-PEER-v2.json"])
    after = json.loads(blobs["CAPTURED-JOURNAL-INDEPENDENT-AFTER-PROOF-v2.json"])
    assert author["status"] == "passed" and author["methods"] == 10
    assert author["failures"] == author["errors"] == []
    assert peer["status"] == "CLEAR_SOURCE_PURE_JOURNAL_COMPONENT_ONLY_NO_LIVE_AUTHORITY"
    assert peer["material_blockers"] == []
    assert after["status"] == "ALL_PRESERVED_BOUNDED_PEER_PROBES_PASS_V2"
    assert after["methods"] == 7
    assert type(after["failures"]) is int and type(after["errors"]) is int
    assert after["failures"] == after["errors"] == 0
    report = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACCEPTED_SOURCE_PURE_CAPTURED_JOURNAL_V2_ONLY",
        "inputs": inputs, "frozen_fixture_cases": 30,
        "author_methods": 10, "added_terminal_regressions": 13, "peer_methods": 7,
        "former_false_positives_now_rejected": 5,
        "scope": "Captured canonical chain integrity plus exact known-launched v7 event/reference completeness; source-negative terminals may be complete without profile acceptance. No actual old run is replayed or qualified.",
        "resource_qualified": False, "profile_qualified": False,
        "execution_authorized": False, "old_negative_and_timeout_unchanged": True,
        "remaining": ["New Unicode source/event policy", "Actual raw-resource/archive/receipt/seal/profile checker binding", "Real first-clock/platform/output/production engine and exact authority/budgets"],
    }
    output = HERE / "CAPTURED-JOURNAL-SCOPED-ACCEPTANCE-v2.json"
    with output.open("xb") as stream:
        stream.write((json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": report["status"], "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
