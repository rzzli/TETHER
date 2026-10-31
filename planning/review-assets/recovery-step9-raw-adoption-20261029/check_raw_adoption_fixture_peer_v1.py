"""Independent structural/projection inspection of NEW literal data, no adopter."""
import hashlib
import json
from pathlib import Path

PHASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inspect(schema_name, fixture_name):
    schema_path, fixture_path = PHASE / schema_name, PHASE / fixture_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    cases = fixture["cases"]
    assert len(cases) == 32 and len({c["id"] for c in cases}) == 32
    assert set(c["family"] for c in cases) == set(schema["families"])
    totals = {"cases": 32, "steps": 0, "checkpoints": 0, "records": 0}
    for case in cases:
        assert set(case) == set(schema["case_exact_keys"]), case["id"]
        initial, expected = case["initial"], case["expected"]
        assert set(initial) == set(schema["initial_exact_keys"]), case["id"]
        assert set(expected) == set(schema["expected_exact_keys"]), case["id"]
        assert len(case["steps"]) <= schema["bounds"]["steps_per_case"]
        assert len(initial["slots"]) <= schema["bounds"]["slots_per_case"]
        assert len(initial["buffers"]) <= schema["bounds"]["buffers_per_case"]
        assert sum(b["capacity"] for b in initial["buffers"]) <= schema["bounds"]["aggregate_buffer_bytes_per_case"]
        assert expected["qualification"] == schema["qualification_exact_value"]
        for step in case["steps"]:
            assert set(step) == set(schema["closed_steps"][step["op"]]), (case["id"], step)
        records = expected["records"]
        assert len(records) <= schema["bounds"]["calls_per_case"]
        assert len({r["ordinal"] for r in records}) == len(records)
        for row in records:
            assert set(row) == set(schema["expected_record_exact_keys"])
        counts = expected["counters"]
        assert set(counts) == set(schema["counter_exact_keys"])
        assert all(type(v) is int and v >= 0 for v in counts.values())
        current = initial["current"]["owner"]
        record_ordinals = {r["ordinal"] for r in records}
        folded = {
            "logical_call_reservations": len(records),
            "FFI_invocations_reserved": sum(r["invocation_reserved"] is True for r in records),
            "known_scalar_returns": sum(r["raw_scalar"]["tag"] != "UNOBSERVED" for r in records),
            "known_count_values": sum(r["raw_count"]["tag"] != "UNOBSERVED" for r in records),
            "portable_wrapper_returns": sum(r["wrapper_state"] == "returned" for r in records),
            "unique_reconciled_ordinals": len({s["ordinal"] for s in case["steps"] if s["op"] == "reconcile" and s["owner_ref"] == current and s["ordinal"] in record_ordinals}),
        }
        assert folded == counts, (case["id"], folded, counts)
        by_ordinal = {r["ordinal"]: r for r in records}
        reservations = {}
        for step in case["steps"]:
            if step["op"] == "reserve" and step["ordinal"] in by_ordinal:
                reservations.setdefault(step["ordinal"], step)
        known_read = initial["early_context"]["known_read_bytes"] if initial["early_context"] is not None else 0
        known_write = 0
        for row in records:
            if row["api"] not in ("ReadFile", "WriteFile"):
                assert row["count_state"] == "not_applicable" and row["count_defined"] is False
                continue
            scalar, count = row["raw_scalar"], row["raw_count"]
            defined = scalar["tag"] == "BOOL32" and scalar["value"] != 0 and count["tag"] == "COUNT32" and count["value"] <= reservations[row["ordinal"]]["requested"]
            assert row["count_defined"] is defined
            if defined:
                assert row["count_state"] == "known_defined"
                if row["api"] == "ReadFile": known_read += count["value"]
                else: known_write += count["value"]
        assert known_read == expected["known_read_bytes"] and known_write == expected["known_write_bytes"], case["id"]
        for slot in expected["slots"]:
            assert set(slot) == set(schema["expected_slot_exact_keys"])
            assert type(slot["close_invocations"]) is int and slot["close_invocations"] in (0, 1)
            if slot["liveness"] == "closed_known": assert slot["close_success"] is True
            elif slot["liveness"] == "close_failed_known": assert slot["close_success"] is False
            else: assert slot["close_success"] is None
        early = initial["early_context"]
        if early is not None:
            raw = bytes.fromhex(early["blob_hex"])
            assert hashlib.sha256(raw).hexdigest() == early["digest"]
            assert early["known_read_bytes"] == early["hashed_bytes"] == early["captured_bytes"] == len(raw)
            assert expected["handoff"]["new_origins"] == expected["handoff"]["new_output_reservations"] == expected["handoff"]["early_source_reopens"] == 0
        totals["steps"] += len(case["steps"])
        totals["checkpoints"] += len(case["checkpoints"])
        totals["records"] += len(records)
    return {"schema": pin(schema_path), "fixtures": pin(fixture_path), "structural_projection_checks": "passed", "totals": totals,
            "adopter_implementation_imports_or_executions": 0, "actual_API_calls": 0, "profile_qualified": False}


if __name__ == "__main__":
    print(json.dumps(inspect("ADOPTION-FIXTURE-SCHEMA-v1.json", "RAW-ADOPTION-FIXTURES-v1.json"), sort_keys=True))
