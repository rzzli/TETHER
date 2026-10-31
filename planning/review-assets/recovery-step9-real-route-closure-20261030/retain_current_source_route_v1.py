"""Metadata-only staged-design delta. Never follows original resource paths."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def pin(relative):
    raw = (ROOT / relative).read_bytes()
    return dict(path=relative, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    staged_path = "planning/review-assets/recovery-step9-production-preflight-20261029/STAGED-NEW84-SELECTION-MANIFEST-v1.json"
    staged = json.loads((ROOT / staged_path).read_text(encoding="utf-8"))
    resources = staged["resources"]
    states = {}
    for row in resources:
        states[row["state"]] = states.get(row["state"], 0) + 1
    if len(resources) != 48 or len({row["resource_id"] for row in resources}) != 48:
        raise ValueError("Expected frozen48 distinct staged nodes")
    source_base = "planning/review-assets/recovery-step9-entry-source4-20261030/"
    selected = [
        ("PLANNED_ENTRY_KERNEL", source_base + "preflight_entry_kernel_v4.py", "accepted_source_pure_preentry_TCB"),
        ("PLANNED_OWNER_OPS", source_base + "preflight_owner_ops_v4.py", "accepted_source_pure_captured_software"),
        ("PLANNED_FILE_VIEW", source_base + "preflight_file_view_v4.py", "accepted_source_pure_captured_software"),
    ]
    deltas = []
    for node, path, status in selected:
        original = next(row for row in resources if row["resource_id"] == node)
        tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
        imports = []
        for statement in tree.body:
            if isinstance(statement, ast.Import):
                imports.extend(alias.name for alias in statement.names)
            elif isinstance(statement, ast.ImportFrom):
                imports.append(statement.module)
        deltas.append(dict(staged_id=node, preserved_staged_state=original["state"],
                           source=pin(path), current_source_status=status,
                           top_level_imports=imports, execution_admission=False))
    candidate_base = "planning/review-assets/recovery-step9-real-route-closure-20261030/"
    result = dict(
        schema_version=1, status="STAGED_SOURCE_DELTA_NOT_AN_EXECUTION_MANIFEST",
        frozen_staged_manifest=pin(staged_path), resource_count=48, preserved_state_counts=states,
        source_replacements=deltas,
        acceptance=pin(source_base + "ENTRY-E08-SUITE-ROOT-ACCEPTANCE-v1.json"),
        native_candidate=dict(
            staged_id="PLANNED_RAW_SHIM", status="SOURCE_TEXT_EXISTS_REVIEW_PENDING_NOT_BUILT",
            files=[pin(candidate_base + name) for name in
                   ("preflight_file14_raw_v1.h", "preflight_file14_raw_v1.c")],
            source_scope=pin(candidate_base + "NATIVE-CARRIER-SOURCE-AUTHORING-SCOPE-v1.json"),
            native_or_kernel_binding=False),
        dependency_gaps=[
            dict(module="bisect", consumer="unicode_piece_analyzer_v1",
                 disposition="Required captured-consumer dependency is outside Kernel4's seven trusted standard-library names; versioned explicit selection/admission required."),
            dict(module="datetime", consumer="Old archive/journal references if selected",
                 disposition="Not automatically selected. Distinct84 policy successors still required; their exact imports must be closed prospectively.")],
        gap_review=pin(candidate_base + "NEXT-REAL-ROUTE-GAP-REVIEW-v1.json"),
        unresolved=dict(full_runtime_roster=None, full_runtime_module_rules=None,
                        genuine_native_ticket_bridge=None, held_path_lifetime=None,
                        full14_physical_profile=None, joint_actor_census=None,
                        new84_parent_child_build_pack=None, resource_fit=None),
        qualification=dict(metadata_only=True, source_imports=0, original_target_reads=0,
                           C_SDK_or_native_calls=0, execution_admission=False,
                           roster_complete=False, physical=False, scientific=False),
        preservation="The48-node manifest and accepted Source4 bytes are unchanged. This delta records current source existence and retained scoped acceptance; no planned node is promoted to a live input or inferred authentic from its state label."
    )
    output = HERE / "STAGED-NEW84-CURRENT-SOURCE-DELTA-v1.json"
    raw = (json.dumps(result, indent=2) + "\n").encode()
    with output.open("xb") as stream:
        stream.write(raw)
    print(json.dumps(dict(path=str(output), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                          resource_count=48, source_replacements=3, execution_admission=False)))


if __name__ == "__main__":
    main()
