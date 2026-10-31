"""Inspect invented captured bytes and ASTs without importing/executing them."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import re

PHASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


fixture_path = PHASE / "SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json"
fixture_pin = pin(fixture_path)
assert fixture_pin["sha256"] == "eb5147d200bcc0108b71968d69f6b251c29b56dd52d926a8606504682134d9b8"
cohort = json.loads(fixture_path.read_text(encoding="utf-8"))
freeze_path = PHASE / "SHARED-OWNER-SYNTHETIC-INPUT-FREEZE-v1.json"
assert pin(freeze_path)["sha256"] == "9f1fbd21bd11b06e969c01a15a773fa6f60e54d685ae62ed7ddd6bc24f76482e"
freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
verified = []
for key in ("author", "checker", "fixture", "preparation_proof"):
    item = freeze[key]
    actual_path = Path(item["path"])
    assert actual_path.parent.resolve() == PHASE
    assert pin(actual_path) == item
    verified.append(item)
proof = json.loads((PHASE / "SHARED-OWNER-SYNTHETIC-INPUT-PREPARATION-PROOF-v1.json").read_text(encoding="utf-8"))
assert proof["status"] == "passed" and proof["methods"] == 4
assert proof["failures"] == proof["errors"] == []
assert len(cohort["blobs"]) == 3
blobs, trees = {}, {}
for descriptor in cohort["blobs"]:
    assert descriptor["id"] not in blobs and descriptor["capture"] is True
    assert descriptor["encoding"] == "utf-8" and re.fullmatch(r"[0-9a-f]*", descriptor["utf8_hex"])
    raw = bytes.fromhex(descriptor["utf8_hex"])
    assert type(descriptor["bytes"]) is int and len(raw) == descriptor["bytes"]
    assert hashlib.sha256(raw).hexdigest() == descriptor["sha256"]
    text = raw.decode("utf-8", "strict")
    assert text.endswith("\n") and "\r" not in text and "\0" not in text
    assert descriptor["path"].startswith(cohort["path_namespace"] + "\\")
    # Embedded path labels are never passed to Path/open/import/compile/exec.
    blobs[descriptor["id"]] = raw
    if descriptor["content_kind"] == "toy_python_helper":
        assert descriptor["phase"] == "early_source" and descriptor["role"] == "software"
        trees[descriptor["id"]] = ast.parse(text)
    else:
        assert descriptor["content_kind"] == "toy_metadata_json"
        assert descriptor["phase"] == "remaining_captured_input" and descriptor["role"] == "owner_metadata"
assert [len(blobs[name]) for name in ("cohort_leaf", "cohort_entry", "metadata")] == [58, 83, 68]
assert cohort["totals"] == {"early_bytes": 141, "early_sources": 2, "remaining_bytes": 68,
                            "remaining_captured_inputs": 1, "total_blobs": 3, "total_bytes": 209}

# Static symbol/body inspection only; no reviewed function is called.
leaf = trees["cohort_leaf"]
assert len(leaf.body) == 2 and isinstance(leaf.body[0], ast.Assign)
assignment, marker_function = leaf.body
assert len(assignment.targets) == 1 and isinstance(assignment.targets[0], ast.Name) and assignment.targets[0].id == "MARKER"
assert isinstance(assignment.value, ast.Constant) and type(assignment.value.value) is str
leaf_marker = assignment.value.value
assert isinstance(marker_function, ast.FunctionDef) and marker_function.name == "marker"
assert ast.dump(marker_function.args) == ast.dump(ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]))
assert marker_function.decorator_list == [] and len(marker_function.body) == 1
assert isinstance(marker_function.body[0], ast.Return) and isinstance(marker_function.body[0].value, ast.Name)
assert marker_function.body[0].value.id == "MARKER"

entry = trees["cohort_entry"]
assert len(entry.body) == 2
import_node, run_function = entry.body
assert isinstance(import_node, ast.ImportFrom) and import_node.level == 0 and import_node.module == "cohort_leaf"
assert [(a.name, a.asname) for a in import_node.names] == [("marker", None)]
assert isinstance(run_function, ast.FunctionDef) and run_function.name == "run"
assert ast.dump(run_function.args) == ast.dump(marker_function.args)
assert run_function.decorator_list == [] and len(run_function.body) == 1
returned = run_function.body[0]
assert isinstance(returned, ast.Return) and isinstance(returned.value, ast.Tuple) and len(returned.value.elts) == 2
label, call = returned.value.elts
assert isinstance(label, ast.Constant) and type(label.value) is str
assert isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "marker"
assert call.args == call.keywords == []
static_tuple = [label.value, leaf_marker]
assert leaf_marker == cohort["expected_toy_values"]["leaf_marker"]
assert static_tuple == cohort["expected_toy_values"]["entry_run_result_tuple"]
metadata = json.loads(blobs["metadata"].decode("utf-8"))
assert metadata == cohort["expected_toy_values"]["metadata_object"]
assert type(metadata["value"]) is int and metadata["value"] == 7

modules = cohort["closed_modules"]
assert modules == [{"blob_id": "cohort_leaf", "dependencies": [], "fullname": "cohort_leaf", "package": False},
                   {"blob_id": "cohort_entry", "dependencies": ["cohort_leaf"], "fullname": "cohort_entry", "package": False}]
assert cohort["stdlib_dependencies"] == []
assert {node.module for tree in trees.values() for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} == {"cohort_leaf"}
assert not any(isinstance(node, ast.Import) for tree in trees.values() for node in ast.walk(tree))
assert [row["blob_id"] for row in cohort["successful_lifecycle_input_history"]] == ["cohort_leaf", "cohort_entry", "metadata"]
for row in cohort["successful_lifecycle_input_history"]:
    size = len(blobs[row["blob_id"]])
    assert all(type(v) is int for k, v in row.items() if k != "blob_id")
    assert row["original_acquisition_histories"] == row["whole_blob_hash_histories"] == row["capture_histories"] == 1
    assert row["known_read_bytes"] == row["hashed_bytes"] == row["captured_bytes"] == size
    assert row["continuation_reopens"] == row["continuation_rehashes"] == 0
for name in ("FFI_registration_proven", "fixture_behavior_qualified", "original_sources_authenticated",
             "production_owner_bound", "profile_qualified", "runtime_authorized"):
    assert cohort[name] is False
assert cohort["actual_API_calls"] == 0 and cohort["no_real_checker_implementation"] is True
assert "successful-lifecycle" in cohort["history_scope"] and "every failure" in cohort["history_scope"]
assert "separately frozen integration fixtures" in cohort["future_fault_purpose"] and "unchanged valid helper bytes" in cohort["future_fault_purpose"]

record = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "CLEAR_SYNTHETIC_COHORT_PREPARATION_ONLY",
    "reviewer": "/root/native_039_acceptance_audit",
    "scope": "Independent literal byte/hash, closed AST/symbol graph, toy-value and successful-history framing review only. Embedded labels were not opened and reviewed helpers were not imported, compiled to executable code or executed.",
    "fixture": fixture_pin, "freeze": pin(freeze_path), "preparation_proof": freeze["preparation_proof"],
    "checker": pin(Path(__file__).resolve()), "verified_metadata_pins": len(verified),
    "byte_totals": {"leaf": 58, "entry": 83, "metadata": 68, "early": 141, "total": 209},
    "closed_module_graph": {"cohort_leaf": [], "cohort_entry": ["cohort_leaf"]},
    "static_toy_values": {"leaf_marker": leaf_marker, "entry_run_result_tuple": static_tuple, "metadata_object": metadata},
    "successful_history_expectations": "One acquisition, whole-blob hash and capture per three inputs; early bytes retained into continuation with zero reopens/rehashes. These are authored success expectations, not API/event counts or a guarantee for fault histories.",
    "fault_nonclaims": "A later frozen compile-callback failure must use unchanged valid helper bytes and preserve once/unknown/no-retry behavior. This cohort supplies no operation schedule, loader, fault implementation, real checker or authority.",
    "material_blockers": [], "reviewed_helpers_imported_or_executed": 0,
    "embedded_path_labels_opened": False, "blobs_written_as_files": False,
    "actual_API_calls": 0, "old_payload_or_source_closure_operations": 0,
    "FFI_registration_proven": False, "production_owner_bound": False,
    "fixture_behavior_qualified": False, "original_sources_authenticated": False,
    "profile_qualified": False, "runtime_authorized": False,
    "next_gate": "Exact shared-owner canonical integration proposal review and closed fictional operation/fault fixtures before separately authorized source implementation.",
}
out = PHASE / "SHARED-OWNER-COHORT-INDEPENDENT-PEER-v1.json"
with out.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(json.dumps(record, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": record["status"], "record": pin(out)}, sort_keys=True))
