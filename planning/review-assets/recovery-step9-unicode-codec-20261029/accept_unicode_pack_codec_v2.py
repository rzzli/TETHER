"""Root source/pure codec acceptance; never persists or dispatches a pack."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {
    "unicode_pack_codec_v2.py": "8ff0d6228fbec2900d52125f2e94e311cc22762d2d0b8b52c3eaadf0e59be91a",
    "UNICODE-PACK-CODEC-CORRECTION-BINDING-v2.json": "172a5e60b666da4ad276f21bef0cff4a4ec69ebf9adde5bea258fa5f8b9dbf15",
    "UNICODE-PACK-CODEC-FREEZE-v2.json": "3ba5a910169cd2c3d55baeb9bcc0e7a43ebc89a29bf4bb30455146b433efab09",
    "UNICODE-PACK-CODEC-PURE-PROOF-v2.json": "a3dd915fd78d3ffed4701a7b1655ba1904813240363385cb372a0a0af3c96177",
    "UNICODE-PACK-CODEC-REGRESSION-AFTER-v2.json": "1e611a122d13769873683e779e8f77e9a1a688dc992453880994d90abdbdcacf",
    "UNICODE-PACK-CODEC-INDEPENDENT-PEER-REVIEW-v2.json": "199157f7940e8cfcdd80f3d8e2fc28e7c443c9b532341cb77d17da7df75b047c",
    "UNICODE-PACK-CODEC-INDEPENDENT-PURE-PROOF-v2.json": "50a31edf1dc75de62996aaa3f501d4f02d61117d9f34450a9cbb1c9cd56d3645",
    "UNICODE-PACK-CODEC-CALLBACK-BEFORE-v2.json": "f0d6be2b4038502916fcca45a2f1385dab3332d6cb4ce1f59f76c9e095ee3dd8",
}


def main():
    blobs, pins = {}, {}
    for name, expected in PINS.items():
        data = (HERE / name).read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise ValueError("Codec component pin mismatch: " + name)
        blobs[name] = data
        pins[name] = {"bytes": len(data), "sha256": actual}
    author = json.loads(blobs["UNICODE-PACK-CODEC-PURE-PROOF-v2.json"])
    after = json.loads(blobs["UNICODE-PACK-CODEC-REGRESSION-AFTER-v2.json"])
    peer = json.loads(blobs["UNICODE-PACK-CODEC-INDEPENDENT-PEER-REVIEW-v2.json"])
    independent = json.loads(blobs["UNICODE-PACK-CODEC-INDEPENDENT-PURE-PROOF-v2.json"])
    assert author["status"] == "passed" and author["methods"] == 11
    assert author["failures"] == author["errors"] == []
    assert after["status"] == "passed" and after["methods"] == 3
    assert after["failures"] == after["errors"] == []
    assert peer["status"] == "CLEAR_SOURCE_PURE_CALLBACK_CORRECTION_AND_CAPTURED_BYTE_CODEC_ONLY"
    assert peer["findings"] == []
    assert peer["profile_qualified"] is peer["originals_authenticated"] is peer["runtime_authorized"] is False
    assert independent["status"] == "passed" and independent["methods"] == 11
    assert type(independent["failures"]) is int and type(independent["errors"]) is int
    assert independent["failures"] == independent["errors"] == 0
    assert peer["independent_counts"]["UnicodeError_ID_probes"] == 720
    result = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACCEPTED_V2_SOURCE_PURE_IN_MEMORY_UNICODE_PACK_CODEC_ONLY",
        "inputs": pins, "author_methods": 11, "author_regression_methods": 3,
        "independent_methods": 11, "independent_callback_identity_probes": 720,
        "complete_pack_bytes_in_test_memory": 37766,
        "in_memory_pack_sha256": "d2537df43e7e6e8113c4e08f0536c2e3a698bd274963ab71a4efced4fa32c8ab",
        "scope": "Factory-issued immutable profile from exact new captured metadata, bounded in-memory encode/decode and independent byte/field checks. No fresh original provenance or runtime behavior.",
        "pack_file_persisted": False, "runtime_authorized": False,
        "profile_qualified": False, "originals_authenticated": False,
        "old_negative_and_timeout_unchanged": True,
        "remaining": ["Full observation trace validator and source/native/parent implementation", "Actual file/source/owner/archive/resource graph integration", "Separate build/runtime/masking/integrated-case/scientific gates"],
    }
    output = HERE / "UNICODE-PACK-CODEC-SCOPED-ACCEPTANCE-v2.json"
    with output.open("xb") as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": result["status"], "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
