"""New fictional native inputs, constructed without reading archived outcomes."""
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
from equal_policy.cases import source_documents, seal_sources, file_bytes
from experiments.inspect_policy.records import proof, publish


def source(root, ident="IX-fictional", *, mutate=None):
    root = Path(root)
    root.mkdir()
    folder = root / "input"
    folder.mkdir()
    documents = source_documents()
    documents["case"]["case_id"] = "FICTIONAL:INSPECT:" + ident
    second = deepcopy(documents["evidence"]["observations"][0])
    second["observation_id"] = "obs-2"
    second["statement"] = "A second invented observation for bounded claim commits."
    second["source_locator"] = {"row": 1}
    documents["evidence"]["observations"].append(second)
    if mutate is not None:
        mutate(documents)
    seal_sources(documents)
    for name, value in documents.items():
        (folder / (name + ".json")).write_bytes(file_bytes(value))
    descriptor = {"schema_version": 1, "control_id": ident, "operation": "prepare_run",
        "variant": "core_v2_catalog1", "paths": {name: "input/" + name + ".json" for name in ("case", "snapshot", "catalog", "scorer")},
        "options": {"review_enabled": True, "budget": {"max_retries": 0}}, "anchors": {}}
    publish(root / "descriptor.json", descriptor)
    return {"control_id": ident, "bundle_root": str(root),
            "descriptor": {"path": "descriptor.json", **proof(root / "descriptor.json")}}


def runtime_row(source_row, **changes):
    result = {"id": source_row["control_id"], "input": source_row,
        "budget": {"max_calls": 2, "max_input_tokens": 200, "max_output_tokens": 200,
                   "max_cost_usd": 0.0, "max_seconds": 30.0},
        "steps": [{"category": "genetics", "quote": {"input_tokens": 20, "output_tokens": 40, "cost_usd": 0.0},
                   "script": {"behavior": "success", "content": '{"observation_ids":["obs-1","obs-2"]}',
                              "usage": {"input_tokens": 10, "output_tokens": 8, "cost_usd": 0.0}, "delay_seconds": 0.0}}],
        "call_seconds": 3.0, "hook_fault": False, "hook_skip": False, "hook_mutate_request": False,
        "mutate_task_state": False, "commit_clock": None}
    result.update(changes)
    return result
