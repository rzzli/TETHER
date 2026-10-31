"""Retain fixture encoding/count pins only; no archive graph implementation."""
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURES-v1.json"
FREEZE = HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURE-FREEZE-v1.json"
PROOF = HERE / "CAPTURED-NATIVE-ARCHIVE-FIXTURE-FRAMING-PROOF-v1.json"


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    started = time.monotonic()
    assert not PROOF.exists()
    frozen = json.loads(FREEZE.read_bytes())
    for key in ("contract", "contract_freeze", "framing", "author", "fixtures"):
        assert pin(Path(frozen[key]["path"])) == frozen[key]
    fixture = json.loads(FIXTURES.read_bytes())
    assert len(fixture["cases"]) == 32
    ids = [row["id"] for row in fixture["cases"]]
    assert len(set(ids)) == 32
    assert all("argv_" + str(index) in ids for index in range(9))
    maximum = 0
    run_file_count = 0
    for case in fixture["cases"]:
        assert set(case) == {"id", "purpose", "captured", "bindings", "expected_projection"}
        capture = case["captured"]
        assert set(capture) == {"protocol_hex", "authority_hex", "run_files"}
        protocol, authority = (bytes.fromhex(capture[name]) for name in ("protocol_hex", "authority_hex"))
        assert len(json.loads(protocol)) == 31 and len(json.loads(authority)) == 18
        total = len(protocol) + len(authority)
        for item in capture["run_files"]:
            assert set(item) == {"locator", "raw_hex"}
            raw = bytes.fromhex(item["raw_hex"])
            assert raw.hex() == item["raw_hex"]
            total += len(raw)
            run_file_count += 1
        assert total < 33554432
        maximum = max(maximum, total)
        for key in ("profile_qualified", "originals_authenticated", "actual_directory_complete", "source_qualified"):
            assert case["expected_projection"][key] is False
    elapsed = time.monotonic() - started
    assert elapsed < 20
    result = dict(schema_version=1, status="fixture_encoding_and_counts_retained_graph_checker_NOT_IMPLEMENTED",
        fixtures=pin(FIXTURES), freeze=pin(FREEZE), recorder=pin(Path(__file__).resolve()),
        cases=32, argv_derivations=9, encoded_run_file_instances=run_file_count,
        maximum_case_decoded_capture_bytes=maximum, elapsed_seconds=elapsed, maximum_seconds=20,
        expected_graph_results_are_authored_not_observed=True, archive_graph_cases_executed=0,
        actual_old_runs_replayed=0, source_closure_qualification=False, directory_scans=0,
        SDK_OS_native_calls=0, payload_path_operations=0, profile_qualified=False)
    with PROOF.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(result, out, indent=2); out.write("\n")
    print(json.dumps(dict(status=result["status"], cases=32, proof_sha256=pin(PROOF)["sha256"])))


if __name__ == "__main__":
    main()
