"""Inspect pinned local OT Parquet partitions for an evaluator, without row reads.

This module has no collector or network entry point. Passing transport, checksum
and footer checks does not establish historical availability or scientific use.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import re
import stat
import time

from tether_engine.atomic import publish_bytes
from tether_engine.ingest import arrow, peak_memory_bytes
from tether_engine.journal import RunJournal
from tether_engine.serde import ContractError, canonical, fingerprint, parse_json, safe_child
from tether_engine.study.proofs import _identity, _no_links
from tools.science.historical_inputs import integrity_map


MAX_METADATA_BYTES = 16 * 1024 * 1024
MAX_RECEIPT_BYTES = 1024 * 1024
HASH_CHUNK_BYTES = 1024 * 1024
MAX_FILES = 10000
MANIFEST_KEYS = {"schema_version", "kind", "role", "agent_visible", "dataset_id", "release_id",
                 "approved_roots", "raw_root", "partition", "queue", "publisher_listing",
                 "publisher_listing_checksum", "files"}
FILE_KEYS = {"relative_path", "receipt_id", "receipt_path", "receipt_sha256", "bytes", "sha256"}
SOURCE_KEYS = {"path", "sha256", "receipt_path", "receipt_sha256"}


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _sha(value):
    _need(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
          "An exact lowercase SHA-256 pin is required")
    return value


def _relative(value):
    _need(type(value) is str, "Expected relative input path")
    value = value.replace("\\", "/")
    _need(value and not value.startswith("/") and ":" not in value and
          all(part not in ("", ".", "..") for part in value.split("/")), "Unsafe relative input path")
    return value


def _absolute(value):
    _need(type(value) is str and Path(value).is_absolute(), "Explicit absolute input paths are required")
    path = Path(value).absolute()
    _no_links(path)
    return path.resolve()


def _approved(value, roots):
    path = _absolute(str(value))
    _need(any(path.is_relative_to(root) for root in roots), "Input/output is outside every approved root")
    return path


def _child(root, value):
    relative = _relative(value)
    original = root.joinpath(*relative.split("/"))
    _no_links(original)
    return safe_child(root, relative)


def _read(path, expected, pins, *, limit=MAX_METADATA_BYTES):
    """Parse callers consume these exact pinned bytes, never a later path read."""
    _sha(expected)
    _no_links(path)
    before = path.stat()
    _need(stat.S_ISREG(before.st_mode) and before.st_size <= limit, "Metadata/receipt exceeds its size limit")
    with path.open("rb") as stream:
        _need(_identity(before) == _identity(os.fstat(stream.fileno())), "Metadata changed before read")
        payload = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    _no_links(path)
    _need(len(payload) <= limit and len(payload) == before.st_size, "Metadata/receipt exceeds its size limit or changed")
    _need(_identity(before) == _identity(after) == _identity(path.stat()), "Metadata changed during read")
    digest = hashlib.sha256(payload).hexdigest()
    _need(digest == expected, "Input metadata/receipt checksum mismatch")
    prior = pins.get(path)
    _need(prior is None or prior["identity"] == _identity(before), "Input changed between checked reads")
    pins[path] = {"sha256": digest, "bytes": len(payload), "identity": _identity(before)}
    return payload


def _utc(value):
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        _need(stamp.tzinfo is not None and stamp.utcoffset() == timedelta(0), "Receipt timestamp must use explicit UTC")
    except (AttributeError, TypeError, ValueError) as error:
        raise ContractError("Invalid receipt UTC timestamp") from error


def _capture(output, relative, payload):
    path = output / relative
    if path.exists():
        _need(path.read_bytes() == payload, "Conflicting captured metadata bytes")
    else:
        publish_bytes(path, payload)


def _publisher(reference, url, roots, pins, output, name):
    _need(type(reference) is dict and set(reference) == SOURCE_KEYS, "Invalid publisher metadata reference")
    path, receipt_path = (_approved(reference[key], roots) for key in ("path", "receipt_path"))
    payload = _read(path, reference["sha256"], pins)
    receipt_bytes = _read(receipt_path, reference["receipt_sha256"], pins, limit=MAX_RECEIPT_BYTES)
    receipt = parse_json(receipt_bytes)
    _need(type(receipt) is dict and receipt.get("role") == "evaluation_only" and
          receipt.get("status") == "retrieved_unreviewed" and type(receipt.get("http_status")) is int and
          receipt["http_status"] == 200 and receipt.get("url") == receipt.get("final_url") == url and
          type(receipt.get("bytes")) is int and receipt["bytes"] == len(payload) and
          receipt.get("sha256") == reference["sha256"], "Publisher transport receipt identity/status/size differs")
    _utc(receipt.get("retrieved_at_utc"))
    _capture(output, "inputs/" + name, payload)
    _capture(output, "inputs/receipts/" + reference["receipt_sha256"] + ".json", receipt_bytes)
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeError as error:
        raise ContractError("Publisher listing is not UTF-8") from error
    listing = integrity_map(text)
    _need(len(listing) == len(text.splitlines()), "Duplicate publisher listing paths")
    return payload, listing


def _schema_fields(schema):
    """Record names/types/nullability recursively, never metadata/statistics values."""
    count = 0
    def field(item, depth):
        nonlocal count
        count += 1
        _need(depth <= 32 and count <= 10000, "Parquet schema exceeds the structural limit")
        kind = item.type
        return {"name": item.name, "type": str(kind), "nullable": bool(item.nullable),
                "children": [field(kind.field(i), depth + 1) for i in range(kind.num_fields)]}
    return [field(item, 0) for item in schema]


def _disk_members(partition, raw):
    _no_links(partition)
    _need(partition.is_dir(), "Selected partition directory is missing")
    members = []
    for path in partition.iterdir():
        _need(len(members) < MAX_FILES, "Selected partition exceeds the file-count limit")
        _no_links(path)
        # Unexpected directories/partials remain in the reconciliation and fail.
        members.append(path.relative_to(raw).as_posix())
    return sorted(members)


def _inspect_file(path, entry, publisher_sha1, pq, pins, physical):
    _no_links(path)
    before = path.stat()
    _need(stat.S_ISREG(before.st_mode) and before.st_size == entry["bytes"], "Raw size differs from pinned receipt")
    key = (before.st_dev, before.st_ino)
    _need(key not in physical, "Duplicate physical raw-file identity")
    physical.add(key)
    sha256, sha1, total = hashlib.sha256(), hashlib.sha1(), 0
    with path.open("rb") as stream:
        _need(_identity(before) == _identity(os.fstat(stream.fileno())), "Raw input changed before hashing")
        while chunk := stream.read(HASH_CHUNK_BYTES):
            total += len(chunk)
            _need(total <= before.st_size, "Raw input grew during hashing")
            sha256.update(chunk)
            sha1.update(chunk)
        _need(total == before.st_size, "Raw input shortened during hashing")
        _need(sha256.hexdigest() == entry["sha256"], "Raw SHA-256 differs from pinned receipt")
        _need(sha1.hexdigest() == publisher_sha1, "Raw publisher SHA-1 mismatch")
        stream.seek(0)
        parquet = pq.ParquetFile(stream, pre_buffer=False,
                                 thrift_string_size_limit=MAX_METADATA_BYTES,
                                 thrift_container_size_limit=1000000)
        schema = _schema_fields(parquet.schema_arrow)
        rows, groups = parquet.metadata.num_rows, parquet.num_row_groups
        _need(type(rows) is int and rows >= 0 and type(groups) is int and groups >= 0,
              "Invalid Parquet footer counts")
        after = os.fstat(stream.fileno())
    _no_links(path)
    _need(_identity(before) == _identity(after) == _identity(path.stat()), "Raw input changed during hash/footer inspection")
    pins[path] = {"sha256": sha256.hexdigest(), "bytes": total, "identity": _identity(before)}
    return {"relative_path": entry["relative_path"], "sha256": sha256.hexdigest(),
            "publisher_sha1": sha1.hexdigest(), "bytes": total, "footer_rows": rows,
            "footer_row_groups": groups, "schema_sha256": fingerprint(schema),
            "receipt_sha256": entry["receipt_sha256"], "role": "evaluation_only", "agent_visible": False}, schema


def _preflight(manifest_path, expected_manifest_sha256, output_path):
    """Establish the output boundary before creating anything, even on failure."""
    output = Path(output_path).absolute()
    _need(".." not in output.parts, "Unsafe output path")
    for member in (*reversed(output.parents), output):
        try:
            info = member.lstat()
        except FileNotFoundError:
            continue
        _need(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
              "Output path has a symlink/reparse component")
    if output.exists():
        raise FileExistsError("Inspection output already exists: " + str(output))
    output = output.resolve()
    path, pins = Path(manifest_path).absolute(), {}
    payload = _read(path, expected_manifest_sha256, pins)
    manifest = parse_json(payload)
    _need(type(manifest) is dict and set(manifest) == MANIFEST_KEYS and
          type(manifest["schema_version"]) is int and manifest["schema_version"] == 1 and
          manifest["kind"] == "opentargets_evaluator_partition_inventory", "Invalid technical inventory manifest")
    _need(manifest["role"] == "evaluation_only" and manifest["agent_visible"] is False,
          "This inspection requires an explicit evaluator-only boundary")
    _need(type(manifest["approved_roots"]) is list and manifest["approved_roots"], "Approved roots are required")
    roots = tuple(_absolute(item) for item in manifest["approved_roots"])
    _need(len(set(roots)) == len(roots), "Duplicate approved roots")
    _approved(path, roots)
    _need(any(output.is_relative_to(root) for root in roots), "Output is outside every approved root")
    raw = _approved(manifest["raw_root"], roots)
    _need(raw.is_dir(), "Raw root is not a directory")
    release, dataset = manifest["release_id"], manifest["dataset_id"]
    _need(type(release) is str and re.fullmatch(r"\d{2}\.\d{2}", release) is not None and
          type(dataset) is str and bool(dataset.strip()), "Invalid dataset/release identity")
    relative_partition = _relative(manifest["partition"])
    release_prefix = "raw/open_targets_platform/" + release + "/"
    _need(relative_partition.startswith(release_prefix + "output/"), "Partition differs from pinned output release")
    partition = _child(raw, relative_partition)
    _need(not output.is_relative_to(partition), "Inspection output cannot be inside an original source partition")
    _need(not output.is_relative_to(raw / "raw") and not output.is_relative_to(raw / "manifests"),
          "Inspection output cannot be inside raw originals or transport receipt directories")
    return output, payload, manifest, roots, raw, partition, pins


def inspect_partition(manifest_path, expected_manifest_sha256, output_path):
    """Inspect bytes/footers only; unsafe preflight never reserves an output.

    After safe output reservation, failures retain their journal and failure.json.
    A complete result requires report.json plus its matching terminal journal hash.
    """
    started = time.monotonic()
    output, payload, manifest, roots, raw, partition, pins = _preflight(
        manifest_path, expected_manifest_sha256, output_path)
    journal = RunJournal(output, kind="build")
    stage, verified, membership = "manifest", [], None
    try:
        release, dataset = manifest["release_id"], manifest["dataset_id"]
        relative_partition = _relative(manifest["partition"])
        release_prefix = "raw/open_targets_platform/" + release + "/"
        publisher_prefix = relative_partition[len(release_prefix):] + "/"
        prefix = relative_partition + "/"
        base_url = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/" + release + "/"
        _need(type(manifest["files"]) is list and 0 < len(manifest["files"]) <= MAX_FILES,
              "Selected partition requires a bounded nonempty file inventory")
        entries, receipt_ids, receipt_paths = {}, set(), set()
        for original in manifest["files"]:
            _need(type(original) is dict and set(original) == FILE_KEYS, "Invalid selected file entry")
            entry = dict(original)
            entry["relative_path"] = _relative(entry["relative_path"])
            entry["receipt_path"] = _relative(entry["receipt_path"])
            name = entry["relative_path"]
            _need(name.startswith(prefix) and "/" not in name[len(prefix):] and name.endswith(".parquet"),
                  "Selected file is not a direct Parquet member of the pinned partition")
            _need(type(entry["receipt_id"]) is str and bool(entry["receipt_id"]) and
                  type(entry["bytes"]) is int and entry["bytes"] >= 0, "Invalid receipt identity/size pin")
            _need(name not in entries and entry["receipt_path"] not in receipt_paths and
                  entry["receipt_id"] not in receipt_ids, "Duplicate selected path or receipt identity")
            _sha(entry["sha256"])
            _sha(entry["receipt_sha256"])
            entries[name] = entry
            receipt_ids.add(entry["receipt_id"])
            receipt_paths.add(entry["receipt_path"])
        _capture(output, "inputs/manifest.json", payload)
        _capture(output, "executed-inspector.py", Path(__file__).read_bytes())

        stage = "membership"
        journal.append("inspection_stage", stage=stage)
        queue_ref = manifest["queue"]
        _need(type(queue_ref) is dict and set(queue_ref) == {"path", "sha256"}, "Invalid queue reference")
        queue_bytes = _read(_approved(queue_ref["path"], roots), queue_ref["sha256"], pins)
        queue = parse_json(queue_bytes)
        _need(type(queue) is dict and type(queue.get("files")) is list, "Invalid transport queue")
        selected_queue, queue_ids = {}, set()
        for row in queue["files"]:
            _need(type(row) is dict, "Invalid queue file entry")
            name = _relative(row.get("relative_path"))
            if not name.startswith(prefix):
                continue
            _need(type(row.get("receipt_id")) is str and bool(row["receipt_id"]), "Invalid queue receipt identity")
            _need(name not in selected_queue and row.get("receipt_id") not in queue_ids, "Duplicate selected queue identity")
            expected_url = base_url + name[len(release_prefix):]
            _need(row.get("dataset_id") == dataset and row.get("release_id") == release and
                  row.get("format") == "parquet" and row.get("url") == expected_url, "Queue identity/release/format/URL mismatch")
            selected_queue[name] = row
            queue_ids.add(row.get("receipt_id"))
        _capture(output, "inputs/queue.json", queue_bytes)
        listing_bytes, listing = _publisher(manifest["publisher_listing"], base_url + "release_data_integrity",
                                            roots, pins, output, "publisher-integrity.txt")
        _, checksum = _publisher(manifest["publisher_listing_checksum"], base_url + "release_data_integrity.sha1",
                                 roots, pins, output, "publisher-integrity.sha1")
        _need(set(checksum) == {"release_data_integrity"} and
              checksum["release_data_integrity"] == hashlib.sha1(listing_bytes).hexdigest(), "Publisher listing SHA-1 mismatch")
        selected_publisher = {release_prefix + name: digest for name, digest in listing.items() if name.startswith(publisher_prefix)}
        disk = _disk_members(partition, raw)
        expected = set(entries)
        membership = {"manifest": sorted(expected), "queue": sorted(selected_queue),
                      "publisher": sorted(selected_publisher), "disk": disk,
                      "missing": {key: sorted(expected - set(values)) for key, values in
                                  (("queue", selected_queue), ("publisher", selected_publisher), ("disk", disk))},
                      "unexpected": {key: sorted(set(values) - expected) for key, values in
                                     (("queue", selected_queue), ("publisher", selected_publisher), ("disk", disk))}}
        _need(expected == set(selected_queue) == set(selected_publisher) == set(disk), "Selected partition membership differs across manifest/queue/publisher/disk")

        stage = "receipt_hash_footer"
        journal.append("inspection_stage", stage=stage, selected_files=len(entries))
        pq, schemas, physical = arrow(), {}, set()
        for name, entry in sorted(entries.items()):
            queue_row = selected_queue[name]
            _need(queue_row.get("receipt_id") == entry["receipt_id"] and
                  (queue_row.get("expected_bytes") is None or type(queue_row["expected_bytes"]) is int and queue_row["expected_bytes"] == entry["bytes"]) and
                  (queue_row.get("expected_sha256") is None or queue_row["expected_sha256"] == entry["sha256"]), "Queue/manifest receipt or expected-byte identity mismatch")
            receipt_path = _child(raw, entry["receipt_path"])
            receipt_bytes = _read(receipt_path, entry["receipt_sha256"], pins, limit=MAX_RECEIPT_BYTES)
            receipt = parse_json(receipt_bytes)
            _need(type(receipt) is dict and receipt.get("status") == "completed" and
                  receipt.get("receipt_id") == entry["receipt_id"] and receipt.get("dataset_id") == dataset and
                  receipt.get("release_id") == release and _relative(receipt.get("relative_path")) == name and
                  receipt.get("url") == queue_row["url"] and type(receipt.get("bytes")) is int and
                  receipt["bytes"] == entry["bytes"] and receipt.get("sha256") == entry["sha256"],
                  "Receipt identity/status/size/checksum differs from selected pins")
            _utc(receipt.get("completed_at_utc"))
            _capture(output, "inputs/receipts/" + entry["receipt_sha256"] + ".json", receipt_bytes)
            row, fields = _inspect_file(_child(raw, name), entry, selected_publisher[name], pq, pins, physical)
            schemas[row["schema_sha256"]] = fields
            verified.append(row)
            journal.append("file_inspected", relative_path=name, verified_files=len(verified),
                           bytes=row["bytes"], sha256=row["sha256"], schema_sha256=row["schema_sha256"],
                           footer_rows=row["footer_rows"], footer_row_groups=row["footer_row_groups"])

        stage = "final_identity_check"
        for source, pin in pins.items():
            _no_links(source)
            _need(_identity(source.stat()) == pin["identity"], "Pinned input changed before finalization")
        _need(_disk_members(partition, raw) == disk, "Selected partition membership changed during inspection")
        by_hash = defaultdict(list)
        for row in verified:
            by_hash[row["sha256"]].append(row["relative_path"])
        try:
            arrow_version = version("pyarrow")
        except PackageNotFoundError:
            arrow_version = None
        report = {"schema_version": 1, "status": "technical_inventory_passed", "role": "evaluation_only",
                  "agent_visible": False, "manifest_sha256": expected_manifest_sha256,
                  "dataset_id": dataset, "release_id": release, "partition": relative_partition,
                  "file_count": len(verified), "bytes": sum(row["bytes"] for row in verified),
                  "footer_rows": sum(row["footer_rows"] for row in verified),
                  "footer_row_groups": sum(row["footer_row_groups"] for row in verified),
                  "row_payloads_decoded": 0, "scientific_eligibility": "unassessed", "labels_qualified": False,
                  "historical_availability": "unverified", "schema_compatibility": "unassessed",
                  "schema_consistency": "uniform" if len(schemas) == 1 else "heterogeneous",
                  "schemas": [{"sha256": digest, "fields": fields} for digest, fields in sorted(schemas.items())],
                  "duplicate_content_hashes": {digest: names for digest, names in sorted(by_hash.items()) if len(names) > 1},
                  "membership": membership, "files": verified,
                  "input_pins": [{"path": str(source), "sha256": pin["sha256"], "bytes": pin["bytes"]}
                                 for source, pin in sorted(pins.items(), key=lambda item: str(item[0]))],
                  "input_guard": "same_open_stream_hash_and_footer; stat_identity_checked_before_after_and_at_finalize; not_hostile_writer_attestation",
                  "publisher_scope": "retained_listing_checksum_and_transport_bytes_checked; publisher_authenticity_not_independently_attested",
                  "pyarrow_version": arrow_version, "elapsed_seconds": time.monotonic() - started,
                  "peak_memory_bytes": peak_memory_bytes()}
        stage = "publication"
        report_bytes = canonical(report) + b"\n"
        journal.append("build_completed", report_sha256=hashlib.sha256(report_bytes).hexdigest(), verified_files=len(verified))
        # Publish the success marker last. A journal write failure cannot leave a
        # passed report, and a publication failure appends a terminal failure.
        publish_bytes(output / "report.json", report_bytes)
        return report
    except BaseException as error:
        failure = {"schema_version": 1, "status": "technical_inventory_failed", "role": "evaluation_only",
                   "agent_visible": False, "stage": stage, "error_class": type(error).__name__, "error": str(error),
                   "verified_files": len(verified), "files": verified, "membership": membership,
                   "row_payloads_decoded": 0, "labels_qualified": False, "scientific_eligibility": "unassessed"}
        try:
            journal.fail(error, stage)
        except OSError:
            pass  # The original error remains primary if the output device also failed.
        try:
            publish_bytes(output / "failure.json", canonical(failure) + b"\n")
        except OSError:
            pass
        raise
    finally:
        journal.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    report = inspect_partition(args.manifest, args.manifest_sha256, args.output)
    print(json.dumps({key: report[key] for key in ("status", "file_count", "bytes", "footer_rows", "row_payloads_decoded")}))


if __name__ == "__main__":
    main()
