"""Root's finite source-component acceptance, not a runtime verifier."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {
    "UNICODE-PIECE-ANALYZER-CONTRACT-v1.json": "05c214f42e9214691b5675cca58e67a6265dd069d2e7829f604df23c7ccca3e6",
    "UNICODE-PIECE-ANALYZER-VECTORS-v1.json": "150a6f0597c226f9aaddcb3f6a3506e9a0513a5cdd2f7da839b25cf56c0f9a79",
    "UNICODE-PIECE-ANALYZER-FREEZE-v1.json": "125d1474ed8498e7dd5bf00f7209fa36660d1326634e0e257b0b2c82f9578a10",
    "unicode_piece_analyzer_v1.py": "537a780a3d2d3b95d5fe4976cd8a073cf528db908badf3edf3e861e729ff8f9d",
    "check_unicode_piece_analyzer_v1.py": "908e9be5d299e59dc4eb811c927cd8487815d4bc54a93388db963da2e042018b",
    "UNICODE-PIECE-ANALYZER-PURE-PROOF-v1.json": "34c7886a52b81f15c81df971222677682cbe0054d45f5e15f5e0b553e451ca54",
    "UNICODE-PIECE-ANALYZER-INDEPENDENT-PEER-v1.json": "e3a45f48c7f8217f632e36acfcb1b60612667c76c809e42e95f7e182cc6bcf8b",
}


def main():
    blobs, checked = {}, {}
    for name, expected in PINS.items():
        data = (HERE / name).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected:
            raise ValueError("Component pin mismatch: " + name)
        blobs[name] = data
        checked[name] = {"bytes": len(data), "sha256": digest}
    author = json.loads(blobs["UNICODE-PIECE-ANALYZER-PURE-PROOF-v1.json"])
    peer = json.loads(blobs["UNICODE-PIECE-ANALYZER-INDEPENDENT-PEER-v1.json"])
    assert author["status"] == "passed" and author["methods"] == 8
    assert author["failures"] == author["errors"] == []
    assert peer["status"] == "CLEAR_SOURCE_PURE_COMPONENT_ONLY_NOT_TOKENIZER_OR_RUNTIME_QUALIFICATION"
    assert peer["methods"] == 8 and peer["material_blockers"] == []
    assert peer["failures"] == peer["errors"] == []
    result = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACCEPTED_SOURCE_PURE_SUPPLIED_PIECE_ANALYZER_ONLY",
        "inputs": checked, "author_methods": 8, "independent_peer_methods": 8,
        "independent_literal_scenarios": 15, "peer_partition_cases": 272,
        "peer_matrix_cells": 12,
        "scope": "Ordinary immutable supplied-piece QC/geometry/count/population/selector component, from independently frozen expectations. No tokenizer or source authentication.",
        "native_wire_or_runtime_qualification": False, "execution_authorized": False,
        "old_profile": "FAILED, unchanged", "old_external_gate": "INCOMPLETE_TIMEOUT, unchanged",
        "remaining": ["Verifier origin/ownership corrections", "Real captured-byte checkers", "Exact native wire/pack/parent/platform/source/budget binding before runtime decision"],
    }
    output = HERE / "UNICODE-PIECE-ANALYZER-SCOPED-ACCEPTANCE-v1.json"
    with output.open("xb") as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": result["status"], "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
