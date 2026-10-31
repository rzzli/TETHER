"""Independent static literal reconstruction; no transition or helper execution."""
from pathlib import Path
import hashlib
import json
import struct

PHASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inspect(fixture_name, schema_name):
    data = json.loads((PHASE / fixture_name).read_text(encoding="utf-8"))
    schema = json.loads((PHASE / schema_name).read_text(encoding="utf-8"))
    public = json.loads((PHASE / "SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json").read_text(encoding="utf-8"))
    cohort = json.loads((PHASE / "SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json").read_text(encoding="utf-8"))
    proposal = json.loads((PHASE / "SHARED-OWNER-CONTINUATION-PROPOSAL-v2.json").read_text(encoding="utf-8"))
    assert len(data["cases"]) == len({c["id"] for c in data["cases"]}) == 48
    assert {c["group"] for c in data["cases"]} == {g["id"] for g in proposal["pure_fixture_matrix"]}
    assert data["qualification"] == public["qualification_exact"]
    frames = {key: bytes.fromhex(value) for key, value in data["frames_hex"].items()}
    assert all(frames[key].hex() == value for key, value in data["frames_hex"].items())
    assert len(frames) == 27 and struct.unpack("<II", frames["attributes_normal"]) == (128, 0)
    expected_calls = []

    def add_call(api, blob_id, arguments, actions):
        expected_calls.append(dict(ordinal=len(expected_calls), api=api, file_id=blob_id,
                                   arguments=arguments, actions=actions, binding_return="normal_None"))

    scalar = lambda value: dict(hook="store_scalar", value=value)
    frame_action = lambda frame_id: dict(hook="buffer_write", frame_id=frame_id)
    for file_id, descriptor in enumerate(cohort["blobs"]):
        blob_id, size, label = descriptor["id"], descriptor["bytes"], descriptor["path"]
        payload = bytes.fromhex(descriptor["utf8_hex"])
        assert len(payload) == size and hashlib.sha256(payload).hexdigest() == descriptor["sha256"]
        assert frames[blob_id + "_read"] == payload
        path_bytes = label.encode("utf-16-le")
        assert frames[blob_id + "_final_path"] == path_bytes + bytes(8202 - len(path_bytes))
        assert struct.unpack("<q", frames[blob_id + "_size"])[0] == size
        handle = 101 + file_id
        add_call("CreateFileW", blob_id, dict(path=label, desired_access=2147483648, share_mode=1,
                 security=None, creation=3, flags=2097280, template=None), [scalar(handle)])
        add_call("GetFileType", blob_id, dict(handle=handle), [scalar(1)])
        add_call("GetFileInformationByHandleEx", blob_id, dict(handle=handle, info_class=9, buffer_bytes=8),
                 [frame_action("attributes_normal"), scalar(1)])
        add_call("GetFinalPathNameByHandleW", blob_id, dict(handle=handle, capacity=4101, flags=0),
                 [frame_action(blob_id + "_final_path"), scalar(len(path_bytes) // 2)])
        add_call("GetFileSizeEx", blob_id, dict(handle=handle), [frame_action(blob_id + "_size"), scalar(1)])
        add_call("ReadFile", blob_id, dict(handle=handle, requested=size, overlapped=None),
                 [frame_action(blob_id + "_read"), scalar(1), dict(hook="store_count", value=size)])
    for file_id in (2, 1, 0):
        add_call("CloseHandle", cohort["blobs"][file_id]["id"], dict(handle=101 + file_id), [scalar(1)])
    assert data["baseline_binding_inputs"] == expected_calls and len(expected_calls) == 21
    rows = []

    def row(event, *, file_id=None, module=None, stage=None, kind=None):
        rows.append(dict(sequence=len(rows), event=event, file_id=file_id, module=module,
                         stage=stage, kind=kind, elapsed=0))

    row("output_reserved")
    for file_id in (0, 1):
        for event in ("source_open_reserved", "source_open_returned", "source_identity_reserved",
                      "source_identity_returned", "source_hash_reserved", "source_hash_returned"):
            row(event, file_id=file_id)
    row("handoff_reserved"); row("handoff_claimed")
    for event, module in (("source_compile_reserved", "cohort_entry"), ("source_compile_reserved", "cohort_leaf"),
                          ("source_compile_returned", "cohort_leaf"), ("source_compile_returned", "cohort_entry")):
        row(event, module=module)
    for stage in ("authority_factory", "checker_factory", "admit_reconcile"):
        row("stage_reserved", stage=stage); row("stage_returned", stage=stage)
    row("stage_reserved", stage="hash_remaining")
    for event in ("file_open_reserved", "file_open_returned", "file_hash_reserved", "file_hash_returned"):
        row(event, file_id=2)
    row("stage_returned", stage="hash_remaining")
    for stage in ("archive", "journal", "resources", "core", "consistency"):
        row("stage_reserved", stage=stage); row("stage_returned", stage=stage)
    row("finalization_reserved")
    row("publication_reserved", kind="candidate"); row("publication_returned", kind="candidate")
    for file_id in (2, 1, 0):
        row("original_close_reserved", file_id=file_id); row("original_close_returned_or_unknown", file_id=file_id)
    row("publication_reserved", kind="cleanup"); row("publication_returned", kind="cleanup")
    row("journal_close_reserved")
    assert rows == data["expected_baseline_serialized_rows"] and len(rows) == 53
    encoded = [json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8") + b"\n" for r in rows]
    assert all(len(r) <= 1024 for r in encoded)
    assert all(set(r) == set(public["serialized_journal_row"]["exact_keys"]) for r in rows)
    assertions = 0
    for case in data["cases"]:
        assert set(case) == set(schema["case_exact_keys"])
        assert len(case["steps"]) <= 32 and len(case["checks"]) <= 180 and len(case["binding_overrides"]) <= 17
        for step in case["steps"]: assert set(step) == set(schema["step_exact_keys"][step["op"]])
        seen = {}
        for check in case["checks"]:
            assert set(check) == set(schema["check_exact_keys"]) and check["relation"] in schema["check_relations"]
            if check["relation"] == "eq":
                key = (check["at"], check["path"])
                typed = json.dumps(check["value"], sort_keys=True, separators=(",", ":"))
                assert key not in seen or seen[key] == typed
                seen[key] = typed
            assertions += 1
        for override in case["binding_overrides"]:
            assert set(override) == set(schema["binding_override_exact_keys"])
            assert override["api"] in proposal["active_original_API_subset"]
            assert type(override["file_id"]) is int and 0 <= override["file_id"] < 3
            for action in override["actions"]:
                assert set(action) == set(schema["binding_action_exact_shapes"][action["hook"]])
                if action["hook"] == "buffer_write": assert action["frame"] in frames
        assert any(c["path"] == "qualification" and c["value"] == public["qualification_exact"] for c in case["checks"])
    by_id = {c["id"]: c for c in data["cases"]}
    short = by_id["short_read_attempt_exhaustion"]
    assert [x["occurrence"] for x in short["binding_overrides"]] == list(range(1, 18))
    leaf_prefix = b"".join(frames["leaf_byte_" + str(i)] for i in range(17))
    leaf = bytes.fromhex(cohort["blobs"][0]["utf8_hex"])
    assert leaf_prefix == leaf[:17] and len(leaf) - len(leaf_prefix) == 41
    assert by_id["publication_attempt_or_size_cap"]["binding_overrides"] == []
    assert by_id["publication_attempt_or_size_cap"]["callback_rules"] == []
    assert "NOT exercised" in by_id["publication_attempt_or_size_cap"]["coverage"][0]
    return dict(fixture=pin(PHASE / fixture_name), schema=pin(PHASE / schema_name),
                histories=48, groups=14, literal_frames=27, authored_assertions=assertions,
                independently_reconstructed_baseline_calls=21, independently_reconstructed_rows=53,
                baseline_serialized_bytes=sum(map(len, encoded)), maximum_row_bytes=max(map(len, encoded)),
                baseline_serialized_sha256=hashlib.sha256(b"".join(encoded)).hexdigest(),
                short_read_literal_bytes=17, short_read_remaining_bytes=41,
                candidate_callback_rows_are_not_measurements=True,
                current_fake_dispatches=0, reviewed_components_imported_or_executed=0,
                actual_target_API_calls=0, old_original_payload_or_source_closure_operations=0)


if __name__ == "__main__":
    report = inspect("SHARED-OWNER-INTEGRATION-FIXTURES-v2.json", "SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v2.json")
    report.update(status="STATIC_INPUT_AND_BASELINE_CHECKS_PASS_TWO_PREPARATION_CLOSURES_PENDING",
                  checker=pin(Path(__file__).resolve()))
    out = PHASE / "SHARED-OWNER-LITERAL-INDEPENDENT-PROOF-v2.json"
    with out.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
    print(json.dumps(pin(out), sort_keys=True))
