"""Small independent peer controls: invented data, fake transport, no network.

Run only with the already qualified installed 0.5 environment; all outputs are
fresh, caller-named peer leaves. No old evidence or production code is edited.
"""
from __future__ import annotations
import copy
import hashlib
import importlib.metadata
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys

# Import installed packages before the repository fixture adds any source paths.
import asof.local_model as local_model
from asof.chrono import load_snapshot
from asof.contracts import Case
from asof.serde import canonical, decode, encode, fingerprint, read_json
from asof.workflow import Budget, run_workflow
from tether import _catalog_binding as binding, _catalog_policy as policy

ROOT = Path(__file__).resolve().parents[3]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else canonical(value) + b"\n")


def receipt_alias(parent):
    root = parent / "receipt-alias"
    root.mkdir()
    payload = b"fictional,value\n1,2\n"
    write(root / "raw/example.csv", payload)
    row = dict(receipt_id="fictional", dataset_id="fictional", release_id="v1",
               relative_path="raw/example.csv", url="https://example.invalid/data",
               expected_bytes=len(payload), planning_upper_bytes=100, format="csv")
    write(root / "queue.json", dict(batch_id="fictional", files=[row]))
    receipt = dict(**row, status="completed", bytes=len(payload),
                   sha256=hashlib.sha256(payload).hexdigest())
    path = root / "manifests/receipts/fictional.json"
    write(path, receipt)
    before = path.read_bytes()
    outputs = []
    for output in (path, root / "recheck-report.json"):
        run = subprocess.run(["pwsh", "-NoProfile", "-File", str(ROOT / "tools/data/Test-DownloadBatch.ps1"),
                              "-QueuePath", str(root / "queue.json"), "-DataRoot", str(root),
                              "-OutputPath", str(output)], capture_output=True, text=True, timeout=20)
        outputs.append(dict(exit_code=run.returncode, report=json.loads(output.read_text(encoding="utf-8-sig"))))
    write(root / "receipt-before.json", before)
    return dict(first=outputs[0], recheck=outputs[1], receipt_changed=path.read_bytes() != before,
                raw_unchanged=(root / "raw/example.csv").read_bytes() == payload)


def accounting(parent, tokens):
    root = parent / ("accounting-" + str(tokens))
    root.mkdir()
    config = dict(schema_version=1, endpoint="http://127.0.0.1:55580", model_id="peer-fake-only",
                  model_provenance=dict(weights_sha256={"fictional": "a"*64}, runtime_sha256="b"*64),
                  retrieval=dict(max_records=12, max_request_bytes=12000), max_output_tokens=256,
                  timeout_seconds=2, seed=1)
    write(root / "config.json", config)
    backend = local_model.LocalSelectionBackend(root / "config.json")
    class Fake:
        def open(self, request, timeout):
            payload = json.loads(request.data)
            schema = payload["json_schema"]["properties"]["observation_ids"]
            selected = schema["items"]["enum"][:min(1, schema["maxItems"])]
            return io.BytesIO(canonical(dict(content=json.dumps(dict(observation_ids=selected)),
                                            truncated=False, tokens_evaluated=tokens, tokens_predicted=1)))
    backend.opener = Fake()
    base = ROOT / "src/asof/demo/v2"
    case = decode(Case, read_json(base / "case.json"))
    run = run_workflow(case, load_snapshot(base / "snapshot.json", case), backend,
                       budget=Budget(max_input_tokens=100000, max_output_tokens=10000))
    document = dict(schema_version=1, attempts=encode(backend.records))
    local_model.verify_backend_execution(document, encode(run.trace), encode(run.configuration))
    write(root / "execution.json", document)
    write(root / "trace.json", run.trace)
    return dict(tokens_per_response=tokens, calls=run.calls, status=run.status, measured=encode(run.measured_usage),
                estimated=encode(run.estimated_usage), accounted=encode(run.usage),
                reported_input=sum(x["response"]["tokens_evaluated"] for x in backend.records),
                violated=sum(e["event"] == "backend_usage_contract_violated" for e in run.trace),
                archive_verification="accepted", network_calls=0)


def receipt_policy(parent, referenced):
    spec = importlib.util.spec_from_file_location("peer_fixture", ROOT / "packages/tether/tests/test_catalog_binding.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = parent / ("policy-ancestor" if referenced else "policy-unused")
    root.mkdir()
    f = module.make_fixture(root)
    extra = copy.deepcopy(f["snapshot"]["sources"][0])
    payload = b'{"fictional_peer":true}\n'
    extra.update(source_id="peer-extra", path="originals/peer.json", sha256=hashlib.sha256(payload).hexdigest(),
                 receipt_path="receipt-archive/peer.json")
    write(f["raw_root"] / extra["path"], payload)
    receipt = dict(receipt_id="peer-extra", dataset_id=extra["dataset_id"], release_id=extra["release_id"],
                   relative_path=extra["path"], sha256=extra["sha256"], bytes=len(payload), url=extra["source_url"],
                   status="completed", completed_at_utc="2024-01-01T00:00:00+00:00")
    write(f["raw_root"] / extra["receipt_path"], receipt)
    extra["receipt_sha256"] = hashlib.sha256((f["raw_root"] / extra["receipt_path"]).read_bytes()).hexdigest()
    extra["availability"] = dict(first_public_at=None, release_public_at=None, record_public_at=None,
        annotation_public_at=None, retrieved_at="2026-01-01", basis="public_download_receipt",
        uncertainty="peer fictional contradiction", known_public_by="2022-01-01T00:00:00+00:00",
        evidence_ref=extra["receipt_sha256"])
    f["snapshot"]["sources"].append(extra)
    record = policy.artifact_record(dataset_id=extra["dataset_id"], release_id=extra["release_id"], root_alias="raw",
        relative_path=extra["path"], sha256=extra["sha256"], bytes=len(payload), kind="raw", parents=[],
        availability=extra["availability"], temporal_classification=extra["temporal_classification"],
        source_url=extra["source_url"], scope="peer fictional", scientific_validation="not_established",
        provenance=dict(kind="download_receipt", evidence=copy.deepcopy(f["policy"]["artifacts"][0]["provenance"]["evidence"]),
                        receipt=dict(root_alias="raw", relative_path=extra["receipt_path"], sha256=extra["receipt_sha256"],
                                     receipt_id=receipt["receipt_id"], url=extra["source_url"])))
    f["policy"]["artifacts"].append(record)
    f["policy"]["uses"][0]["grants"].append(dict(artifact_id=record["artifact_id"], role=extra["role"]))
    if referenced:
        f["snapshot"]["sources"][1]["parents"].append(extra["source_id"])
        f["policy"]["artifacts"][1]["parents"].append(record["artifact_id"])
    f["policy"]["uses"][0]["snapshot_fingerprint"] = fingerprint(f["snapshot"])
    write(f["paths"]["policy"], f["policy"])
    write(f["paths"]["snapshot"], f["snapshot"])
    output = root / "preparation"
    output.mkdir()
    try:
        descriptor = binding.prepare_policy_run(output, f["request"])
        outcome = dict(preparation="accepted", verification=binding.verify_policy_run(output, descriptor, check_engine=False))
    except Exception as exc:
        outcome = dict(preparation="rejected", error_type=type(exc).__name__, message=str(exc))
    return dict(referenced=referenced, origin=f["case"]["origin_at"], completed=receipt["completed_at_utc"],
                known_public_by=extra["availability"]["known_public_by"], **outcome)


def main():
    parent = Path(sys.argv[1]).absolute()
    parent.mkdir(parents=True, exist_ok=False)
    modules = {"local_model": Path(local_model.__file__), "catalog_binding": Path(binding.__file__)}
    record = dict(tether_version=importlib.metadata.version("tether-target-agents"),
                  asof_version=importlib.metadata.version("asof-target-agents"),
                  modules={key: dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                           for key, path in modules.items()},
                  scope="Fictional controls, no model/network/real study run")
    assert record["tether_version"] == "0.5.0"
    assert all("site-packages" in str(path) for path in modules.values())
    write(parent / "START.json", record)
    record.update(receipt_alias=receipt_alias(parent), accounting=[accounting(parent, n) for n in (50,1000000)],
                  policy=[receipt_policy(parent, flag) for flag in (False, True)])
    write(parent / "results.json", record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
