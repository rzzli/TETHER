"""Import one explicitly named neutral metadata frame into additive TETHER policy.

No acquisition, biological-row parsing, database query or collection promotion.
Original payload hashes are inherited from retained receipts; normalized packet
bytes and the small metadata/receipt files are freshly checked. Outputs are new
workspace directories, including content-addressed metadata copies.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages/tether/src"))
from asof.contracts import Case
from asof.serde import ContractError, canonical, decode, fingerprint
from asof.study.stable_read import checked_path, read_file
from tether._catalog_policy import (artifact_record, authorize_snapshot, migrate_catalog,
                                    relative_path, strict_json, validate_policy)


def need(condition, message):
    if not condition:
        raise ContractError("Catalog frame import: " + message)


def checked_json(path, expected=None):
    raw = read_file(Path(path), time.monotonic() + 60, 16 * 1024 * 1024)
    digest = hashlib.sha256(raw).hexdigest()
    need(expected is None or digest == expected, "metadata hash differs: " + str(path))
    return strict_json(raw), raw, digest


def add_record(records, record):
    key = record["artifact_id"]
    need(key not in records or canonical(records[key]) == canonical(record),
         "conflicting artifact metadata for the same exact identity")
    records[key] = record


def receipt_archive_path(node):
    digest = node.get("receipt_sha256")
    need(type(digest) is str and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest),
         "receipt archive digest invalid")
    expected = "manifests/receipt-archive/" + digest + ".json"
    need(node.get("receipt_path") == expected, "selected frame requires exact content-addressed receipt path")
    return expected


def check_frame_case(row, case, snapshot, report):
    """Match current control metadata to fields bound by the retained build."""
    typed = decode(Case, case)
    cutoff = decode(datetime, report["origin_at_utc"])
    need(typed.schema_version == 2 and typed.task == "T6" and typed.case_id == row["case_id"]
         and typed.hypothesis.key == row["hypothesis_key"] and typed.program is None
         and typed.endpoint is None and typed.cutoff == cutoff and typed.origin == cutoff.date(),
         "case identity/hypothesis/origin differs from pinned canonical frame")
    need(snapshot.get("schema_version") == 2 and snapshot.get("profile") == "contemporary_assessment"
         and snapshot.get("allow_reconstructed") is False and snapshot.get("origin") == case["origin"]
         and decode(datetime, snapshot.get("origin_at")) == cutoff
         and snapshot.get("snapshot_id") == report["snapshot_id"] + ":" + row["case_id"],
         "snapshot identity/profile/origin differs from pinned canonical frame")
    need(len(snapshot["sources"]) == row["input_sources"], "source-node count differs from pinned build")
    expected = [p["path"] for p in row["packets"]]
    supplied = [p["path"] for p in snapshot["artifacts"]]
    need(len(expected) == len(set(expected)) and len(supplied) == len(set(supplied))
         and set(expected) == set(supplied), "packet inventory differs from pinned build")


class MetadataImport:
    def __init__(self, output, raw_root):
        self.output = output
        self.raw_root = raw_root
        self.pins = {}

    def load(self, path, expected=None):
        path = Path(path).absolute()
        resolved = path.resolve()
        need(resolved.is_relative_to(ROOT.resolve()) or resolved.is_relative_to(self.raw_root.resolve()),
             "metadata outside approved roots")
        for component in (*reversed(path.parents), path):
            info = component.lstat()
            need(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                 "metadata path contains a link or reparse point")
        document, raw, digest = checked_json(path, expected)
        destination = self.output / "metadata" / (digest + ".json")
        destination.parent.mkdir(exist_ok=True)
        if destination.exists():
            need(destination.read_bytes() == raw, "content-address collision")
        else:
            with destination.open("xb") as handle:
                handle.write(raw)
        if path.is_relative_to(ROOT):
            alias, relative = "project", path.relative_to(ROOT).as_posix()
        else:
            need(path.is_relative_to(self.raw_root), "metadata outside approved roots")
            alias, relative = "external_data", path.relative_to(self.raw_root).as_posix()
        proof = {"path": destination.relative_to(ROOT).as_posix(), "sha256": digest}
        self.pins[(alias, relative)] = dict(root_alias=alias, relative_path=relative,
            bytes=len(raw), sha256=digest, archived_copy=proof["path"])
        return document, proof


def raw_artifact(node, receipt, receipt_proof):
    """Bind a previously pinned receipt, without inventing an original queue ID."""
    need(node.get("computed_at") is None and not node.get("parents"),
         "this selected import expects raw-only source nodes")
    for field, expected in (("status", "completed"), ("dataset_id", node["dataset_id"]),
            ("release_id", node["release_id"]), ("sha256", node["sha256"]), ("url", node["source_url"])):
        need(receipt.get(field) == expected, "receipt/node mismatch: " + field)
    receipt_path = receipt.get("relative_path")
    need(type(receipt_path) is str and relative_path(receipt_path.replace("\\", "/")) == node["path"],
         "receipt/node mismatch: normalized relative_path")
    need(type(receipt.get("bytes")) is int and receipt["bytes"] > 0,
         "receipt byte count absent")
    need(type(receipt.get("receipt_id")) is str and receipt["receipt_id"],
         "retained transport receipt lacks identity")
    return artifact_record(dataset_id=node["dataset_id"], release_id=node["release_id"],
        root_alias="external_data", relative_path=node["path"], sha256=node["sha256"],
        bytes=receipt["bytes"], kind="raw", parents=[], availability=node["availability"],
        temporal_classification=node["temporal_classification"], source_url=node["source_url"],
        provenance=dict(kind="download_receipt", evidence=[receipt_proof], receipt=dict(
            root_alias="external_data", relative_path=node["receipt_path"],
            sha256=node["receipt_sha256"], receipt_id=receipt["receipt_id"], url=receipt["url"])),
        scope="Inherited original payload hash from pinned normalization receipt; receipt bytes freshly checked. No new queue-to-receipt reconciliation or raw payload hash check.",
        scientific_validation="not_established")


def add_aact(policy, importer, records):
    """Seven exact archive identities remain blocked for agent inference."""
    public = ROOT / "data/manifests/public"
    origin, op = importer.load(public / "2026-10-16-aact-restoration.json")
    followup, fp = importer.load(public / "2026-10-16-aact-followup.json")
    intermediate, ip = importer.load(public / "2026-10-17-aact-intermediate-restorations.json")
    endpoint, ep = importer.load(public / "2026-10-18-aact-endpoint-technical.json")
    ascertainment, ap = importer.load(public / "2026-10-18-aact-ascertainment-technical.json")
    rows = [("2023-01-01", origin["input"]["path"], origin["input"]["bytes"], origin["input"]["sha256"], op),
            ("2025-01-01", followup["archive"]["archive"], followup["archive"]["bytes"], followup["archive"]["sha256"], fp)]
    specs = [(r["actual_dump_date"], r["restore_root_relative_to_external_data"],
              r["archive_bytes"], r["archive_sha256"], ip) for r in intermediate["snapshots"]]
    specs += [("2026-01-01", "derived/aact_restore/science-endpoint-20260101-20261018T174448Z/restore/2026-01-01",
               endpoint["source_archive_bytes"], endpoint["source_archive_sha256"], ep),
              ("2026-04-01", "derived/aact_restore/science-ascertainment-20260401-20261018T205200Z/restore/2026-04-01",
               ascertainment["source_archive_bytes"], ascertainment["source_archive_sha256"], ap)]
    for date, folder, size, sha, proof in specs:
        inspection, _ = importer.load(importer.raw_root / folder / "archive-inspection.json")
        need(inspection["status"] == "archive_integrity_passed" and
             inspection["archive_bytes"] == size and inspection["archive_sha256"] == sha,
             "AACT retained archive metadata disagreement")
        rows.append((date, inspection["archive"], size, sha, proof))
    for date, path, size, sha, proof in sorted(rows):
        absolute = Path(path)
        need(absolute.is_relative_to(importer.raw_root), "AACT archive outside approved root")
        record = artifact_record(dataset_id="aact_snapshots", release_id=date,
            root_alias="external_data", relative_path=absolute.relative_to(importer.raw_root).as_posix(),
            sha256=sha, bytes=size, kind="raw", parents=[], availability=None,
            temporal_classification="unverified", source_url=None,
            provenance=dict(kind="manual_archive", evidence=[proof], receipt=None),
            scope="Inherited user-supplied archive identity and technical restoration metadata; original bytes not rehashed; first public availability unqualified.",
            scientific_validation="not_established")
        add_record(records, record)
        policy["uses"].append(dict(use_id="aact-2023-origin-program-" + date,
            kind="origin_context" if date == "2023-01-01" else
                 "ascertainment_evaluation" if date == "2026-04-01" else "endpoint_evaluation",
            status="blocked", profile="historical_benchmark", origin_at="2023-01-01T00:00:00Z",
            frame_sha256=None, case_fingerprint=None, snapshot_fingerprint=None,
            raw_root_alias="external_data", snapshot_root_alias="blocked_aact",
            grants=[dict(artifact_id=record["artifact_id"], role="agent_evidence" if date == "2023-01-01" else "evaluation_only")],
            blockers=["No qualified historical availability, case/manifest binding or clinical endpoint contract.",
                      "Later snapshots are evaluator use for the original 2023-origin programme; no agent-visible grant."]))


def build(args):
    output, raw_root = args.output.absolute(), args.raw_root.absolute()
    need(output.resolve().is_relative_to((ROOT / "data/derived").resolve()),
         "output must be a fresh data/derived workspace directory")
    output.mkdir(exist_ok=False)
    started = time.monotonic()
    stage = "catalog"
    try:
        importer = MetadataImport(output, raw_root)
        need(args.catalog.resolve().is_relative_to(ROOT.resolve()), "source catalog must be workspace-local")
        _, catalog_bytes, _ = checked_json(args.catalog, args.catalog_sha256)
        policy = migrate_catalog(catalog_bytes, source_path=args.catalog.absolute().relative_to(ROOT).as_posix(),
            policy_id="tether-canonical-ten-and-aact-v2", created_at_utc=args.created_at)
        normalization, _ = importer.load(ROOT / "data/manifests/public/2026-10-17-literature-normalization.json")
        build_ref = normalization["build_report"]
        build_root = (ROOT / build_ref["path"]).parent
        report, _ = importer.load(ROOT / build_ref["path"], build_ref["sha256"])
        need(report["status"] == "built" and not report["blocked_cases"] and len(report["cases"]) == 10,
             "canonical build frame is incomplete")
        records, roots, receipts = {}, {"external_data": str(raw_root), "metadata": str(ROOT)}, {}
        frames = []
        node_occurrences = packet_count = 0
        stage = "canonical_metadata"
        for row in report["cases"]:
            folder = build_root / row["case_id"]
            case, _ = importer.load(folder / "case.json")
            snapshot, snapshot_proof = importer.load(folder / "snapshot.json")
            check_frame_case(row, case, snapshot, report)
            need(Path(snapshot["raw_root"]) == raw_root, "snapshot raw root differs")
            alias = "case_" + row["case_id"].replace("-", "_")
            roots[alias] = str(folder)
            grants, node_ids = [], {}
            for node in snapshot["sources"]:
                receipt_relative = receipt_archive_path(node)
                key = node["receipt_sha256"]
                if key not in receipts:
                    receipts[key] = importer.load(raw_root / receipt_relative, key)
                record = raw_artifact(node, *receipts[key])
                add_record(records, record)
                need(node["source_id"] not in node_ids, "duplicate source node")
                node_ids[node["source_id"]] = record["artifact_id"]
                grants.append(dict(artifact_id=record["artifact_id"], role=node["role"]))
                node_occurrences += 1
            packet_by_path = {p["path"]: p for p in row["packets"]}
            for packet in snapshot["artifacts"]:
                expected = packet_by_path[packet["path"]]
                need(packet["sha256"] == expected["sha256"], "packet/build hash disagreement")
                packet_path = checked_path(folder, relative_path(packet["path"]))
                raw = read_file(packet_path, time.monotonic() + 60, 64 * 1024 * 1024)
                need(len(raw) == expected["bytes"] and hashlib.sha256(raw).hexdigest() == expected["sha256"],
                     "normalized packet bytes differ")
                record = artifact_record(dataset_id=packet["dataset_id"], release_id=packet["release_id"],
                    root_alias=alias, relative_path=packet["path"], sha256=packet["sha256"], bytes=len(raw),
                    kind="packet", parents=[node_ids[n] for n in packet["input_refs"]],
                    availability=packet["availability"], temporal_classification=packet["temporal_classification"],
                    source_url=packet["source_url"], provenance=dict(kind="generated", evidence=[snapshot_proof], receipt=None),
                    scope="Selected canonical T6 packet; bytes freshly hashed, no biological re-adjudication or case rerun.",
                    scientific_validation="not_established")
                add_record(records, record)
                grants.append(dict(artifact_id=record["artifact_id"], role=packet["role"]))
                packet_count += 1
            policy["uses"].append(dict(use_id="canonical-ten-" + row["case_id"], kind="contemporary_evidence",
                status="allowed", profile=snapshot["profile"], origin_at=snapshot["origin_at"],
                frame_sha256=build_ref["sha256"], case_fingerprint=fingerprint(case), snapshot_fingerprint=fingerprint(snapshot),
                raw_root_alias="external_data", snapshot_root_alias=alias, grants=grants, blockers=[]))
            frames.append((case, snapshot, policy["uses"][-1]["use_id"]))
        stage = "aact_metadata"
        add_aact(policy, importer, records)
        policy["artifacts"] = sorted(records.values(), key=lambda r: r["artifact_id"])
        for product in policy["products"]:
            if product["dataset_id"] in {"ot_target", "ot_disease", "ot_evidence", "hgnc_symbols", "asof_normalized_packets"}:
                product["dependency_review_status"] = "reviewed_for_selected_frame"
        stage = "policy_validation"
        validate_policy(policy)
        selections = []
        for case, snapshot, use_id in frames:
            selected = authorize_snapshot(policy, snapshot, case=case, use_id=use_id, root_aliases=roots)
            need(selected["binding"]["frame_sha256"] == build_ref["sha256"], "frame anchor differs")
            selections.append(dict(use_id=use_id, projection_fingerprint=fingerprint(selected["projection"])))
        payload = json.dumps(policy, indent=2, ensure_ascii=False, allow_nan=False).encode() + b"\n"
        with (output / "policy.json").open("xb") as f:
            f.write(payload)
        with (output / "roots.json").open("x", encoding="utf-8") as f:
            json.dump(dict(schema_version=1, roots=roots), f, indent=2); f.write("\n")
        result = dict(schema_version=1, status="metadata_imported_no_execution", role="evaluation_only", agent_visible=False,
            policy_sha256=hashlib.sha256(payload).hexdigest(), products=len(policy["products"]),
            artifacts=len(records), raw_lineage_artifacts=len(receipts), source_node_occurrences=node_occurrences,
            packets=packet_count, aact_archives=7, allowed_uses=10, blocked_uses=7,
            pure_policy_selections=selections,
            metadata=list(importer.pins.values()), elapsed_seconds=time.monotonic() - started,
            source_payload_hashes="inherited_retained_check; not freshly rehashed", normalized_packet_hashes="freshly_checked",
            scientific_validation="not_established", collection_status_promotions=0, provider_spend_usd=0)
        with (output / "report.json").open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2); f.write("\n")
        return result
    except BaseException as error:
        with (output / "failure.json").open("x", encoding="utf-8") as f:
            json.dump(dict(status="failed", stage=stage, error_class=type(error).__name__, message=str(error)), f, indent=2)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--catalog", type=Path, default=ROOT / "data/catalog/sources.json")
    parser.add_argument("--catalog-sha256", required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--created-at", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    result = build(args)
    print(json.dumps({k: v for k, v in result.items() if k != "metadata"}, indent=2))


if __name__ == "__main__":
    main()
