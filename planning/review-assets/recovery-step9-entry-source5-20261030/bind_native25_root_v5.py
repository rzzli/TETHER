"""Bind the reviewed Source5 source/synthetic diagnostic exactly once; no native call."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def write(path, value):
    with path.open("xb") as stream:
        stream.write((json.dumps(value, indent=2) + "\n").encode())
    return pin(path)


def main():
    freeze_path = BASE / "NATIVE25-COMPONENT-FREEZE-v5.json"
    peer_path = BASE / "SOURCE5-NATIVE25-INDEPENDENT-STATIC-REVIEW-v1.json"
    resume_path = BASE / "SOURCE5-RESUME-STATIC-PIN-CHECK-v2.json"
    docs_path = BASE.parent / "recovery-step9-real-route-closure-20261030/C-RETURN-CURRENT-DOCS-QA-v2.json"
    required = {
        freeze_path: "afe6658f6145eaf5a69e9fb5325fc1c1b003162a1ba1e512b48657289d61ee1a",
        peer_path: "6093db538cbcaae0a656c92de5be66039c4c334e8133ca15e1a4a6ef9bfc7ae3",
        resume_path: "ed43be652302c6640f006689db46b969792698633e0bb0628a886cdc955aeb5a",
        docs_path: "747464ba3c083500790ad0ba5503463d345dba580aae306091da104cd5029d7d",
    }
    for path, digest in required.items():
        if pin(path)["sha256"] != digest:
            raise ValueError("Changed selected prerequisite: " + str(path))
    freeze = json.loads(freeze_path.read_bytes())
    for selected in freeze["pins"].values():
        if pin(Path(selected["path"])) != selected:
            raise ValueError("Changed frozen input")
    peer = json.loads(peer_path.read_bytes())
    if peer["status"] != "CLEAR_STATIC_SOURCE5_NATIVE25_ONLY":
        raise ValueError("Source5 static peer not clear")
    docs = json.loads(docs_path.read_bytes())
    if docs["status"] != "PASS_TEN_CURRENT_DOCS_C_RETURN_CAPTURE" or docs["counts"]["failed"] != 0:
        raise ValueError("C-return current documentation not passed")
    for name, selected in docs["documents_final"].items():
        raw = (ROOT / name).read_bytes()
        if len(raw) != selected["bytes"] or hashlib.sha256(raw).hexdigest() != selected["sha256"]:
            raise ValueError("Current document differs: " + name)
    for name in ("NATIVE25-COMPONENT-ATTEMPT-v5.json", "NATIVE25-COMPONENT-PROOF-v5.json", "NATIVE25-COMPONENT-ARTIFACTS-v5"):
        if (BASE / name).exists():
            raise ValueError("One-shot output already exists")
    scope = dict(
        schema_version=5, at_utc=datetime.now(timezone.utc).isoformat(),
        status="ROOT_AUTHORIZED_SINGLE_NATIVE25_COMPONENT_EXECUTION",
        deadline_seconds=60, freeze=pin(freeze_path), independent_static_peer=pin(peer_path),
        resume_peer=pin(resume_path), current_document_qa=pin(docs_path),
        geometry=dict(normative_families=25, branches=48, executable=43, source_runtime=21,
                      data=22, static=1, deferred=4, genuine_worlds_max=20,
                      data_instances_max=32, synthetic_capacity_max=20, bulk_bytes=2097169),
        selected_subjects="Fresh exact Source5 kernel namespace; unchanged Ops4, FileView4, codec4 and native25 cases V3. No actual C image.",
        diagnostic="Only RawCallStore._call exact API/axis-kind guard changed. Retain all prior 31/12,38/5,41/2 controls and first failures. Predicates, raw bits, rights, progress and no-retry checks unchanged.",
        allowed="One bounded source/synthetic suite, source-issued objects and frozen fictional inputs. Retain partial raw banks, snapshots, accounting, original errors and audit denials.",
        excluded="No original target paths, C/SDK/FFI/compiler/native image/model, live native ticket/lease/child/path lifetime, physical14, cap/default/downloader/monitor changes or prior-suite replay.",
        limitations="43 executable controls cannot pass four native deferrals or one static declaration. No native25 completion, whole-project fit or scientific qualification.",
        provider_spend_usd=0)
    scope_pin = write(BASE / "NATIVE25-COMPONENT-EXECUTION-SCOPE-v5.json", scope)
    binding = dict(schema_version=5, status="ROOT_BOUND_NATIVE25_COMPONENT_ONE_SHOT",
                   run_authorized=True, deadline_seconds=60, freeze=pin(freeze_path),
                   execution_scope=scope_pin, independent_peer=pin(peer_path))
    binding_pin = write(BASE / "NATIVE25-COMPONENT-BINDING-v5.json", binding)
    print(json.dumps(dict(scope=scope_pin, binding=binding_pin, final_document_pins_checked=10)))


if __name__ == "__main__":
    main()
