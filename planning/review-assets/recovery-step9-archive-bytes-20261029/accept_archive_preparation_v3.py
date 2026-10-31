"""Root source-format/fixture preparation acceptance, never archive execution."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {
    "CAPTURED-NATIVE-ARCHIVE-CONTRACT-v3.json": "ce077d5bfd2e12bd5de7a84d17094572a15286e0cb44bdc224513206f305e3d2",
    "CAPTURED-NATIVE-ARCHIVE-CONTRACT-FREEZE-v3.json": "0251171e43f655fc211e865c5458fc76fc508501664b0a5bf12fb32216503641",
    "CAPTURED-NATIVE-ARCHIVE-FIXTURES-v3.json": "3e75447d4d3a01c56833d089bf23dab52e5e53bc49a9ea33e9de689eef9b5dcd",
    "CAPTURED-NATIVE-ARCHIVE-FIXTURE-FREEZE-v3.json": "7663f2edfff3d0c4365bbe9d4336895b56f2e5b5001bb69717eeeab06bfd96b9",
    "CAPTURED-NATIVE-ARCHIVE-FIXTURE-FRAMING-PROOF-v3.json": "1f1ba32f2cb13fbffa9056c07431a4e5076b758e6be04bb12c427ae621922b7e",
    "CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-DESIGN-REVIEW-v3.json": "0f411d7ef3749bc8dd38e5eede604d64169babcbde5c72e704ccbd23c8b3d43b",
}


def main():
    blobs, checked = {}, {}
    for name, expected in PINS.items():
        raw = (HERE / name).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != expected:
            raise ValueError("Archive preparation pin mismatch: " + name)
        blobs[name] = raw
        checked[name] = {"bytes": len(raw), "sha256": digest}
    author = json.loads(blobs["CAPTURED-NATIVE-ARCHIVE-FIXTURE-FRAMING-PROOF-v3.json"])
    peer = json.loads(blobs["CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-DESIGN-REVIEW-v3.json"])
    assert author["status"] == "fixture_framing_and_narrow_source_delta_passed" and author["methods"] == 5
    assert type(author["failures"]) is int and type(author["errors"]) is int
    assert author["failures"] == author["errors"] == 0
    assert peer["status"] == "CLEAR_CORRECTED_DESIGN_AND_LITERAL_SOURCE_FIXTURES_ONLY"
    assert peer["material_findings"] == []
    assert len(peer["checks"]) == 6 and all(item["status"] == "passed" for item in peer["checks"])
    assert peer["profile_qualified"] is False and peer["originals_authenticated"] is False
    assert peer["actual_directory_complete"] is False and peer["source_qualified"] is False
    result = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACCEPTED_ARCHIVE_V3_DESIGN_AND_LITERAL_FIXTURE_PREPARATION_ONLY",
        "inputs": checked, "literal_captures": 32, "author_framing_methods": 5,
        "independent_inspection_groups": 6,
        "scope": "Corrected source-format schemas, locators, conditional maps and authored literal graph expectations. No checker has yet validated these graph outcomes.",
        "profile_qualified": False, "source_qualified": False,
        "originals_authenticated": False, "actual_directory_complete": False,
        "runtime_or_execution_authority": False, "old_negative_and_timeout_unchanged": True,
        "next_scope": "Separate root source/pure checker implementation decision; actual source/owner/directory/resource/profile binding stays pending.",
    }
    output = HERE / "CAPTURED-NATIVE-ARCHIVE-PREPARATION-ACCEPTANCE-v3.json"
    with output.open("xb") as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": result["status"], "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
