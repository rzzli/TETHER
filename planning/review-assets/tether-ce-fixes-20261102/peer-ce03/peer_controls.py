"""Independent tiny CE03 controls; no model, network or production source use."""
from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "packages/tether/tests"))
from test_catalog_binding import make_fixture, write
from asof import provenance
from asof.serde import ContractError, fingerprint
from tether import _catalog_binding as binding, _catalog_policy as policy


def fixture(root, *, used, known="2022-02-02T12:00:00Z",
            completed="2022-02-02T12:00:00+00:00", bad_ref=False,
            bad_url=False, alternate=False):
    root.mkdir()
    frame = make_fixture(root)
    node = copy.deepcopy(frame["snapshot"]["sources"][0])
    raw = b'{"peer_only":"no_science"}\n'
    node.update(source_id="peer-ce03", path="originals/peer.json",
                sha256=hashlib.sha256(raw).hexdigest(), receipt_path="receipt-archive/peer.json")
    write(frame["raw_root"] / node["path"], raw)
    receipt = dict(receipt_id="peer-ce03", dataset_id=node["dataset_id"],
        release_id=node["release_id"], relative_path=node["path"], bytes=len(raw),
        sha256=node["sha256"], status="completed", completed_at_utc=completed,
        url="https://example.invalid/other" if bad_url else node["source_url"])
    write(frame["raw_root"] / node["receipt_path"], receipt)
    node["receipt_sha256"] = hashlib.sha256((frame["raw_root"] / node["receipt_path"]).read_bytes()).hexdigest()
    node["availability"] = dict(first_public_at="2020-01-01", release_public_at="2020-01-01",
        record_public_at="2020-01-01", annotation_public_at="2020-01-01", retrieved_at="2026-01-01",
        basis="Fictional original release metadata" if alternate else "public_download_receipt",
        uncertainty="Invented peer input; not publisher authentication", known_public_by=known,
        evidence_ref="wrong-receipt-reference" if bad_ref else node["receipt_sha256"])
    frame["snapshot"]["sources"].append(node)
    item = policy.artifact_record(dataset_id=node["dataset_id"], release_id=node["release_id"],
        root_alias="raw", relative_path=node["path"], sha256=node["sha256"], bytes=len(raw),
        kind="raw", parents=[], availability=node["availability"],
        temporal_classification=node["temporal_classification"], source_url=node["source_url"],
        scope="Fictional peer check", scientific_validation="not_established",
        provenance=dict(kind="download_receipt",
            evidence=copy.deepcopy(frame["policy"]["artifacts"][0]["provenance"]["evidence"]),
            receipt=dict(root_alias="raw", relative_path=node["receipt_path"],
                sha256=node["receipt_sha256"], receipt_id=receipt["receipt_id"], url=node["source_url"])))
    frame["policy"]["artifacts"].append(item)
    frame["policy"]["uses"][0]["grants"].append(dict(artifact_id=item["artifact_id"], role=node["role"]))
    if used:
        frame["snapshot"]["sources"][1]["parents"].append(node["source_id"])
        frame["policy"]["artifacts"][1]["parents"].append(item["artifact_id"])
    frame["policy"]["uses"][0]["snapshot_fingerprint"] = fingerprint(frame["snapshot"])
    write(frame["paths"]["policy"], frame["policy"])
    write(frame["paths"]["snapshot"], frame["snapshot"])
    return frame


def execute(frame, *, disable_outer_relation=False):
    output = frame["paths"]["policy"].parent / "preparation"
    output.mkdir()
    calls = {"outer_hash": [], "engine_hash": [], "outer_receipt_relation": []}
    outer_hash, engine_hash = binding.hash_file, provenance.sha256_file
    actual_relation = binding.check_receipt_availability
    def observed_outer(path, *args, **kwargs):
        calls["outer_hash"].append(Path(path).name)
        return outer_hash(path, *args, **kwargs)
    def observed_engine(path, *args, **kwargs):
        calls["engine_hash"].append(Path(path).name)
        return engine_hash(path, *args, **kwargs)
    def relation(node, receipt):
        calls["outer_receipt_relation"].append(node.source_id)
        if not disable_outer_relation:
            return actual_relation(node, receipt)
    with patch.object(binding, "hash_file", observed_outer), \
            patch.object(provenance, "sha256_file", observed_engine), \
            patch.object(binding, "check_receipt_availability", relation):
        try:
            descriptor = binding.prepare_policy_run(output, frame["request"])
            verified = binding.verify_policy_run(output, descriptor, check_engine=False)
            return dict(status="accepted", checked_inputs=verified["checked_inputs"], calls=calls)
        except ContractError as error:
            return dict(status="rejected", message=str(error), calls=calls)


def main():
    root = Path(sys.argv[1]).absolute()
    root.mkdir(parents=True, exist_ok=False)
    cases = []
    # Four independent control families, expanded across both ancestry roles.
    variants = [
        ("exact_utc_alias", {}, "accepted", None),
        ("one_microsecond_early", {"known": "2022-02-02T11:59:59.999999Z"}, "rejected", "availability bound"),
        ("bad_evidence_ref", {"bad_ref": True}, "rejected", "availability bound"),
        ("bad_receipt_url", {"bad_url": True}, "rejected", "receipt url differs"),
        ("naive_completion", {"completed": "2022-02-02T12:00:00"}, "rejected", "UTC"),
        ("separate_release_basis", {"known": None, "alternate": True,
                                     "completed": "2024-01-01T00:00:00Z"}, "accepted", None),
    ]
    for used in (False, True):
        for name, options, expected, message in variants:
            frame = fixture(root / (name + ("-used" if used else "-unused")), used=used, **options)
            result = execute(frame)
            assert result["status"] == expected, (name, used, result)
            if message:
                assert message in result["message"], (name, used, result)
            else:
                assert result["checked_inputs"] == 4
                assert result["calls"]["outer_receipt_relation"].count("peer-ce03") == 3
            cases.append(dict(name=name, used=used, **result))
    observed = []
    for disabled in (False, True):
        frame = fixture(root / ("hash-control-disabled" if disabled else "hash-control-enabled"), used=False)
        observed.append(execute(frame, disable_outer_relation=disabled))
    for family in ("outer_hash", "engine_hash"):
        assert observed[0]["calls"][family] == observed[1]["calls"][family], family
    modules = {"provenance": Path(provenance.__file__), "catalog_binding": Path(binding.__file__)}
    result = dict(status="PASS", cases=cases, hash_control=observed,
        versions={p: importlib.metadata.version(p) for p in ("tether-target-agents", "asof-target-agents")},
        modules={name: dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                 for name, path in modules.items()},
        scope="12 invented used/unused relationship cases plus valid helper-enabled/disabled hash instrumentation; no backend dispatch",
        limitations="Helper-disabled arm is a fictional instrumentation control, not an old release or a valid scientific run.")
    (root / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
