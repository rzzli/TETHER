"""Retain an exact metadata/source-text peer review; never import a reviewed helper."""
from pathlib import Path
import ast
import hashlib
import json
from datetime import datetime, timezone

PHASE = Path(__file__).resolve().parent
ROOT = PHASE.parents[2]


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def bound(item):
    actual = pin(Path(item["path"]))
    assert actual == item, (actual, item)
    return actual


design_path = PHASE / "FILE-PORTS-ADOPTION-SEAM-DESIGN-v1.json"
freeze_path = PHASE / "FILE-PORTS-ADOPTION-SEAM-FREEZE-v1.json"
design_pin, freeze_pin = pin(design_path), pin(freeze_path)
assert design_pin["sha256"] == "055db993a35f173d19a01c52c3b88515d97d3752d7dd409e1273b55f63c15cd6"
assert freeze_pin["sha256"] == "f2d57dee6454c04dc2d3416e411b9c2a6bc69aab79db0ad131ec5be7fe769046"
design, freeze = load(design_path), load(freeze_path)
assert freeze["design"] == design_pin
sources = [bound(item) for item in design["sources"]]
assert sources == [bound(item) for item in freeze["sources"]]
gap = bound(design["prior_gap"])
assert gap == freeze["gap"]
author = bound(design["author"])
assert author == freeze["author"]
freeze_author = bound(freeze["freeze_author"])
acceptance = bound(freeze["portable_scoped_acceptance"])
prior_peer = pin(PHASE / "PORTABLE-FILE-PORTS-SOURCE-INDEPENDENT-PEER-v2.json")
assert prior_peer["sha256"] == "56b57f3ce0f08770b8bbf16698adc64d6560e19d14e04239a976d0d09694132d"
expected_exports = (
    "CreateFileW", "GetFileType", "GetFileInformationByHandleEx",
    "GetFinalPathNameByHandleW", "GetFileSizeEx", "ReadFile", "CloseHandle",
    "GetFileAttributesExW", "FindFirstFileExW", "FindNextFileW", "FindClose",
    "CreateDirectoryW", "WriteFile", "FlushFileBuffers",
)
assert tuple(item["name"] for item in design["minimal_exports"]) == expected_exports
assert len(design["method_successor_map"]) == 10
assert len(design["fixture_expectations_to_freeze_before_code"]) == 14
assert len({item["id"] for item in design["fixture_expectations_to_freeze_before_code"]}) == 14
for flag in ("FFI_registration_proven", "implementation_authorized", "originals_authenticated",
             "production_owner_bound", "profile_qualified", "runtime_authorized"):
    assert design[flag] is False

source_ast_inventory = []
for item in sources:
    tree = ast.parse(Path(item["path"]).read_text(encoding="utf-8"))
    source_ast_inventory.append({
        "source": item,
        "classes": [node.name for node in tree.body if isinstance(node, ast.ClassDef)],
        "top_level_functions": [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))],
    })

groups = [
    {"id": "raw_return_axes", "verdict": "consistent",
     "finding": "Logical reservation/entry, FFI invocation reservation, scalar return, count definedness, and portable-wrapper return remain separate. Unknown C entry or return is not converted into a measured zero, while a retained native scalar is not erased by a wrapper exception."},
    {"id": "ownership_and_counts", "verdict": "consistent",
     "finding": "Preallocated owner/Origin/nonce/slot/ordinal records precede invocation. Usable handle/search/namespace effects and function-specific known read/write counts are adopted before error copying, RawReturn allocation, callbacks, clocks, hashing or immutable copying. Partial fields and original buffer lifetime are retained; return counters reconcile once by ordinal."},
    {"id": "sentinels_and_closers", "verdict": "consistent",
     "finding": "CreateFile/FindFirst INVALID remains the documented known-no-handle case; unexpected NULL is unknown and creates no guessed close right. File/search closers stay distinct, with one reservation and no retry after false, unknown, late or wrapper-failed close."},
    {"id": "identity_and_namespace", "verdict": "consistent",
     "finding": "Real identity requires all four same-handle owner-bound query records and current-clock admission. Harness seeds, copied flags and caught identity failures grant no content authority. Namespace ownership is retained separately from readiness, including partial output slots before acknowledgment failure."},
    {"id": "continuation", "verdict": "consistent",
     "finding": "Ten mappings cover portable slots, early-source captures, immutable source context, source-bound port, loader, engine entry, events and finalization. Exact Origin/nonce/registry/output ownership survives a one-use handoff; numeric old t0, run_once, a new _Owner, source recapture and duplicated cleanup rights are expressly rejected."},
    {"id": "deadlines_and_primary", "verdict": "consistent",
     "finding": "The same original 295-second work/300-second hard clock continues. Known late raw facts remain retained without renewed work; cleanup stops at the hard boundary. Existing primary object/phase persists and raw API facts stay distinct from later Python exception precedence."},
    {"id": "finite_scope_and_next_gate", "verdict": "consistent",
     "finding": "The design keeps the existing 14 exports and caps, 14 proposed fault expectations, and no new discovery or loader fallback. Joint roster/event fit, literal record schemas/fixtures, actual FFI conversion/adoption, first-entry provenance, complete checker/sink integration and profile qualification remain pending; no assumed 256/2048 fit is asserted."},
]

report = {
    "schema_version": 1,
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "CLEAR_DESIGN_FOR_LITERAL_FIXTURE_PREPARATION_ONLY",
    "reviewer": "/root/native_039_acceptance_audit",
    "design_author": "/root/grammar_toolchain_requirements",
    "review_scope": "Independent finite source-text/design review against three accepted NEW pure components and the retained continuation gap. No reviewed helper or author script imported/executed, no source closure qualification, no old archive replay.",
    "authorization_basis": "Root assigned design-only independent peer after portable source-scoped acceptance 16d65f572019a86b466d684f5c67b330140de85362829abad7a19330ee4d318a; no implementation or live binding authority.",
    "design": design_pin, "freeze": freeze_pin, "author": author,
    "freeze_author": freeze_author, "sources": sources, "prior_gap": gap,
    "portable_scoped_acceptance": acceptance, "prior_portable_source_peer": prior_peer,
    "source_ast_inventory": source_ast_inventory,
    "inspection_groups": groups,
    "material_blockers": [],
    "next_required_gates": [
        "Freeze literal typed adoption-record and fault fixtures before source implementation; include scalar-return/wrapper-failure and partial-count/buffer cases without copying expected authority flags.",
        "Root must separately authorize any source successors; same-owner integration must retain the original clock, registry, live early sources, captured loader, event sequence and exactly-once cleanup.",
        "Derive the actual joint roster, buffers, call/event/output reservations before originals; existing prototype ceilings alone are not a fit certificate.",
        "Actual FFI binding and native-to-Python conversion/interruption behavior remain separate unqualified boundaries. Python object adoption cannot establish atomic native-return registration.",
        "New Unicode journal/archive policy and complete production checker/owner/sink integration remain separate; old v7 policies are not retargeted by this design.",
    ],
    "metadata_assertions_and_AST_parses_only": True,
    "semantic_test_replays": 0, "reviewed_helper_imports_or_executions": 0,
    "actual_FFI_API_calls": 0, "old_payload_operations": 0, "old_source_closure_operations": 0,
    "FFI_registration_proven": False, "production_owner_bound": False,
    "originals_authenticated": False, "profile_qualified": False,
    "implementation_authorized_by_review": False, "runtime_authorized": False,
    "retention_source": pin(Path(__file__).resolve()),
}
json_path = PHASE / "FILE-PORTS-ADOPTION-SEAM-INDEPENDENT-PEER-v1.json"
md_path = PHASE / "FILE-PORTS-ADOPTION-SEAM-INDEPENDENT-PEER-v1.md"
md = """# File-port adoption seam: independent design peer

The frozen design is clear for literal fixture preparation only. Seven finite inspection groups found no material contradiction with the three accepted NEW pure sources or the retained continuation gap. This review imported or executed no reviewed helper and made no actual API, old-payload or original-source-closure operations.

The design separates native scalar/count observations from portable-wrapper return. Raw handle, namespace, known byte and close facts remain in the same owner record before throwable wrapper work. A wrapper exception cannot clear a known effect or create a second close right. Unknown conversion/entry remains unknown, including unexpected NULL. Existing primary exceptions and the original 295/300-second clock persist.

The continuation keeps the exact Origin, nonce, registry, live early sources, captured loader, output namespace and event history. It rejects a fresh run_once owner, numeric clock restart, duplicated source capture or cleanup ownership. Four same-handle identity queries remain mandatory; harness assumptions grant no production authority.

Next come frozen literal adoption-record/fault fixtures, separately authorized source successors, and an actual joint roster/buffer/event fit calculation. Real FFI registration, native-to-Python conversion/interruption, first-entry provenance and complete checker/sink integration remain unqualified. Old v7 journal/archive policy cannot qualify a future Unicode parent through a changed binding.

The JSON record pins the exact design, freeze, accepted source basis and prior gap. This is design review, not implementation, runtime or profile approval.

- [Frozen design](FILE-PORTS-ADOPTION-SEAM-DESIGN-v1.json)
- [Freeze](FILE-PORTS-ADOPTION-SEAM-FREEZE-v1.json)
- [Exact peer record](FILE-PORTS-ADOPTION-SEAM-INDEPENDENT-PEER-v1.json)
"""
for path, raw in ((json_path, (json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")),
                  (md_path, md.encode("utf-8"))):
    with path.open("xb") as stream:
        stream.write(raw)
    path.read_text(encoding="utf-8")
print(json.dumps({"status": report["status"], "inspection_groups": len(groups),
                  "json": pin(json_path), "md": pin(md_path)}, sort_keys=True))
