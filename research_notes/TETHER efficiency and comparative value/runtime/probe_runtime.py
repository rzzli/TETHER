"""Fictional current-source audit. Writes only fresh audit/cache output leaves."""
from __future__ import annotations
import collections
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "packages/tether/src")]
spec = importlib.util.spec_from_file_location("audit_fixture", ROOT / "packages/tether/tests/test_catalog_binding.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
from asof import provenance
from asof.serde import canonical, fingerprint
from tether import _catalog_binding as binding, _catalog_policy as policy


def fresh(parent, name):
    result = parent / name
    result.mkdir()
    return result


def unused_future_receipt(parent, referenced=False):
    root = fresh(parent, "referenced-future-receipt" if referenced else "unused-future-receipt")
    f = fixture.make_fixture(root)
    extra = copy.deepcopy(f["snapshot"]["sources"][0])
    payload = b'{"fictional_unused_raw":true}\n'
    extra.update(source_id="unused-future", path="originals/unused.json", sha256=hashlib.sha256(payload).hexdigest(),
                 receipt_path="receipt-archive/unused.json")
    fixture.write(f["raw_root"] / extra["path"], payload)
    receipt = dict(receipt_id="fictional-unused", dataset_id=extra["dataset_id"], release_id=extra["release_id"],
                   relative_path=extra["path"], sha256=extra["sha256"], bytes=len(payload), url=extra["source_url"],
                   status="completed", completed_at_utc="2024-01-01T00:00:00+00:00")
    fixture.write(f["raw_root"] / extra["receipt_path"], receipt)
    extra["receipt_sha256"] = hashlib.sha256((f["raw_root"] / extra["receipt_path"]).read_bytes()).hexdigest()
    extra["availability"] = dict(first_public_at=None, release_public_at=None, record_public_at=None,
        annotation_public_at=None, retrieved_at="2026-01-01", basis="public_download_receipt",
        uncertainty="fictional counterexample", known_public_by="2022-01-01T00:00:00+00:00",
        evidence_ref=extra["receipt_sha256"])
    f["snapshot"]["sources"].append(extra)
    record = policy.artifact_record(dataset_id=extra["dataset_id"], release_id=extra["release_id"],
        root_alias="raw", relative_path=extra["path"], sha256=extra["sha256"], bytes=len(payload), kind="raw",
        parents=[], availability=extra["availability"], temporal_classification=extra["temporal_classification"],
        source_url=extra["source_url"], scope="fictional counterexample", scientific_validation="not_established",
        provenance=dict(kind="download_receipt", evidence=copy.deepcopy(f["policy"]["artifacts"][0]["provenance"]["evidence"]),
            receipt=dict(root_alias="raw", relative_path=extra["receipt_path"], sha256=extra["receipt_sha256"],
                         receipt_id=receipt["receipt_id"], url=extra["source_url"])))
    f["policy"]["artifacts"].append(record)
    f["policy"]["uses"][0]["grants"].append(dict(artifact_id=record["artifact_id"], role=extra["role"]))
    if referenced:
        f["snapshot"]["sources"][1]["parents"].append(extra["source_id"])
        f["policy"]["artifacts"][1]["parents"].append(record["artifact_id"])
    f["policy"]["uses"][0]["snapshot_fingerprint"] = fingerprint(f["snapshot"])
    fixture.write(f["paths"]["policy"], f["policy"])
    fixture.write(f["paths"]["snapshot"], f["snapshot"])
    output = fresh(root, "preparation")
    result = dict(referenced=referenced, case_origin=f["case"]["origin_at"], receipt_completed=receipt["completed_at_utc"],
                  claimed_known_public_by=extra["availability"]["known_public_by"], output=str(output))
    try:
        descriptor = binding.prepare_policy_run(output, f["request"])
        result.update(preparation="accepted", verify=binding.verify_policy_run(output, descriptor, check_engine=False))
    except BaseException as error:
        result.update(preparation="rejected", exception=type(error).__name__, message=str(error))
    fixture.write(root / "result.json", result)
    return result


def count_hashes(parent):
    root = fresh(parent, "hash-count")
    f = fixture.make_fixture(root)
    output = fresh(root, "preparation")
    target = (f["raw_root"] / f["snapshot"]["sources"][0]["path"]).absolute()
    counts = collections.Counter()
    real_hash, real_legacy = binding.hash_file, provenance.sha256_file
    def counted_hash(path, deadline):
        if Path(path).absolute() == target:
            counts["stable_hash"] += 1
        return real_hash(path, deadline)
    def counted_legacy(path):
        if Path(path).absolute() == target:
            counts["engine_hash"] += 1
        return real_legacy(path)
    with patch.object(binding, "hash_file", counted_hash), patch.object(provenance, "sha256_file", counted_legacy):
        started = time.perf_counter()
        descriptor = binding.prepare_policy_run(output, f["request"])
        preparation = dict(counts)
        binding.verify_policy_run(output, descriptor, check_engine=False)
        predispatch = dict(counts)
    result = dict(raw_bytes=target.stat().st_size, prepare=preparation, total_before_dispatch=predispatch,
                  elapsed_seconds=time.perf_counter()-started,
                  note="Real policy preparation plus exact second outer preflight verification; zero child dispatches")
    fixture.write(root / "result.json", result)
    return result


def main():
    parent = Path(sys.argv[1]).absolute()
    parent.mkdir(parents=True, exist_ok=False)
    result = dict(schema_version=1, source_head="b8d107059c781bb96ab27807f857f1127ed09608",
                  unused_future_receipt=unused_future_receipt(parent),
                  referenced_control=unused_future_receipt(parent, referenced=True),
                  hash_counts=count_hashes(parent))
    fixture.write(parent / "results.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
