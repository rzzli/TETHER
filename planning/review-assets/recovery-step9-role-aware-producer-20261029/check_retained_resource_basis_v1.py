"""Check retained descriptor extraction without touching any described target."""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASIS = HERE / "RETAINED-HISTORICAL-RESOURCE-VECTOR-v1.json"
EXPECTED = "3a7e00e9cc812f7fcf0676c70704c65ab35565cac4b6a652fe06fad42c890c75"
SOURCES = {
    "planning/review-assets/recovery-step9-native-recognition-20261028/RECOGNITION-FRESH-INPUT-PASS-v1.json": "04eff7fb2274a13130c8bc6ee639d57cb3362d7761f2ae96c1e084d97b06fb49",
    "planning/review-assets/recovery-step9-native-recognition-20261028/RECOGNITION-EXECUTION-PROTOCOL-v1.json": "b690c63bbcc576dab0ea02b4f6359ed31b24edc39a850bc945789563bf99bbf2",
    "planning/review-assets/recovery-step9-native-recognition-20261028/RECOGNITION-RUNTIME-PIN-DESCRIPTOR-v1.json": "e42cfda8a76c0784883c5d3dd1f695fd6e10c4d60b9c85685bfc2aba2a89922c",
}


def metadata(path, expected):
    # Only the explicitly listed planning metadata and new extraction are opened.
    assert path == BASIS or path in {ROOT / name for name in SOURCES}
    assert path.stat().st_size <= 2 * 1024 * 1024
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected, path.name
    return json.loads(raw), {"path": str(path), "bytes": len(raw), "sha256": expected}


def main():
    basis, basis_pin = metadata(BASIS, EXPECTED)
    loaded, pins = {}, {BASIS.name: basis_pin}
    for name, expected in SOURCES.items():
        loaded[name], pins[name] = metadata(ROOT / name, expected)
    records = loaded[next(iter(SOURCES))]["records"]
    rows = basis["files"]
    assert len(records) == len(rows) == 213
    assert len({row["path"] for row in rows}) == 213
    roles = defaultdict(lambda: {"files": 0, "bytes": 0})
    for ordinal, (original, row) in enumerate(zip(records, rows)):
        assert row["ordinal"] == ordinal
        assert (row["path"], row["bytes"], row["sha256"], row["historical_role"]) == (
            original["path"], original["expected_bytes"], original["expected_sha256"], original["role"])
        assert type(row["bytes"]) is int and row["bytes"] > 0
        roles[row["historical_role"]]["files"] += 1
        roles[row["historical_role"]]["bytes"] += row["bytes"]
    assert dict(roles) == basis["historical_roles"]
    assert basis["totals"] == {"files": 213, "positive_files": 213, "bytes": 9017363392}
    assert sum(row["bytes"] for row in rows) == 9017363392
    options = []
    assert [item["chunk_bytes"] for item in basis["chunk_options"]] == [65536, 1048576, 4194304]
    for item in basis["chunk_options"]:
        chunk = item["chunk_bytes"]
        q = sum(size // chunk + bool(size % chunk) for size in (row["bytes"] for row in rows))
        r, c = q + 16 * 213, q + 22 * 213
        expected = {"chunk_bytes": chunk, "Q": q, "R": r, "C": c, "positive_files": 213,
                    "query_frame_bytes": 8218 * 213,
                    "read_and_query_work_plus_retained_frames": chunk + 8202 + 8218 * 213}
        assert item == expected
        options.append(expected)
    assert all(value == 0 for value in basis["activity"].values())
    assert basis["missing_new84_roster"] is True
    result = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed_retained_metadata_extraction_and_arithmetic_only",
        "scope": "Four bounded planning JSON documents only. No referenced target was statted, opened, parsed or hashed; old run was not replayed or requalified.",
        "inputs": pins, "metadata_rows_matched": 213,
        "totals": basis["totals"], "historical_roles": dict(roles), "chunk_options": options,
        "fresh_source_eligibility": False, "new84_roster_complete": False,
        "actual_runtime_authorized": False, "physical_fit_established": False,
        "referenced_target_operations": 0,
        "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    output = HERE / "RETAINED-HISTORICAL-RESOURCE-VECTOR-ROOT-CHECK-v1.json"
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "rows": 213, "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
