"""Read-only exact acquisition-manifest/transport/installer path-schema check."""
import ast
import hashlib
import json
from pathlib import Path
import runpy


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
ASSETS = HERE.parents[1]
TRANSPORT = ROOT / "experiments/scifact_multivers_transport/download.py"
INSTALLER = ASSETS / "install_sc02.py"
MANIFEST = ASSETS / "solver-feasibility/acquisition-manifest.json"
OUTPUT = HERE / "transport-join-review-attempt01"


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def assignment(path, name):
    nodes = ast.walk(ast.parse(path.read_text(encoding="utf-8")))
    matched = [node for node in nodes if isinstance(node, ast.Assign) and any(isinstance(x, ast.Name) and x.id == name for x in node.targets)]
    assert len(matched) == 1
    return ast.literal_eval(matched[0].value)


before = {name: pin(path) for name, path in (("transport", TRANSPORT), ("installer", INSTALLER), ("manifest", MANIFEST))}
transport = runpy.run_path(str(TRANSPORT), run_name="metadata_transport_review_only")
manifest = transport["validate_manifest"](json.loads(MANIFEST.read_text(encoding="utf-8")))
from_transport = assignment(TRANSPORT, "KIND_DIRECTORY")
from_installer = assignment(INSTALLER, "directories")
assert from_transport == from_installer == {"wheel": "wheel", "checkpoint": "checkpoint", "tokenizer_config": "tokenizer"}
expected = [from_transport[a["kind"]] + "/" + a["logical_id"] for a in manifest["assets"]]
assert len(expected) == len(set(expected)) == 30
assert sum(x.startswith("wheel/") for x in expected) == 25
assert sum(x.startswith("tokenizer/") for x in expected) == 4
assert sum(x.startswith("checkpoint/") for x in expected) == 1
assert before == {name: pin(path) for name, path in (("transport", TRANSPORT), ("installer", INSTALLER), ("manifest", MANIFEST))}
OUTPUT.mkdir(exist_ok=False)
report = {"status": "PASS_schema_join_only", "sources": before, "reviewer": pin(Path(__file__)), "directory_mapping": from_transport,
          "expected_relative_paths": expected, "payload_bytes": manifest["total_payload_bytes"],
          "scope": "Actual planned manifest validation and exact transport/installer identity join only. No endpoint opened, no payload read, no process launched, no installation or model inference.",
          "receipt_conventions": {"root_status": "PASS", "successful_asset_status": "completed", "tokenizer_asset_kind": "tokenizer_config", "tokenizer_relative_directory": "tokenizer"},
          "static_review": ["Fresh supervisor reservation protects owned attempt identity.", "Payload headers, stream byte caps and expected published digests/revisions are checked.", "Worker process has hard total/stall limits; parent local finalization is not hard-preempted.", "Installer uses a fresh workspace-cache descendant, explicit interpreter and offline hash-locked wheels."]}
(OUTPUT / "REVIEW.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"status": report["status"], "assets": len(expected), "record": pin(OUTPUT / "REVIEW.json")}))
