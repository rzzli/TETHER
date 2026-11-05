"""Bounded preparation-only SciFact archive projection with explicit consumer purposes.

The physical tarball is a mixed-role container. Predictor views never contain gold
or citation hints. This trusted projector is not an OS sandbox or a semantic judge.
"""
from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import math
from pathlib import Path, PurePosixPath
import re
import tarfile
import time

from asof.atomic import publish_bytes
from asof.journal import RunJournal, read_chain
from asof.serde import ContractError, canonical, encode, freeze, parse_json, safe_child
from .split import build_split, pair_rows

MAX_ARCHIVE = 64 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024
MAX_MEMBER = 16 * 1024 * 1024
MAX_LINE = 1024 * 1024
REQUIRED = ("data/corpus.jsonl", "data/claims_train.jsonl", "data/claims_dev.jsonl", "data/claims_test.jsonl")


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def need(condition, message):
    if not condition:
        raise ContractError(message)


def bounded_bytes(path, limit=MAX_ARCHIVE):
    path = Path(path)
    need(path.is_file() and not path.is_symlink(), "Missing or symlinked input")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    need(len(data) <= limit, "Input exceeds byte bound")
    return data


def jsonl_bytes(rows):
    return b"".join(canonical(row) + b"\n" for row in rows)


def _rows(payload, name):
    rows = []
    for index, line in enumerate(payload.splitlines(keepends=True), 1):
        need(index <= 20000 and len(line) <= MAX_LINE, f"JSONL bound exceeded: {name}")
        need(line.strip(), f"Blank JSONL record: {name}:{index}")
        row = parse_json(line)
        need(isinstance(row, dict), f"JSONL object required: {name}:{index}")
        rows.append((row, {"member": name, "line_1based": index, "raw_line_sha256": digest(line)}))
    need(rows, f"Empty JSONL member: {name}")
    return rows


def _integer(value):
    return type(value) is int and value >= 0


@dataclass(frozen=True)
class LoadedRelease:
    corpus: Mapping
    claims: Mapping
    bindings: Mapping
    members: Mapping
    inventory: tuple
    schema_exclusions: Mapping
    diagnostics: tuple
    archive_sha256: str
    archive_bytes: int


def load_archive(path, expected_sha256, expected_bytes=None):
    raw = bounded_bytes(path)
    need(digest(raw) == expected_sha256, "Archive SHA-256 mismatch")
    need(expected_bytes is None or len(raw) == expected_bytes, "Archive byte count mismatch")
    payloads, members, inventory, names = {}, {}, [], set()
    total = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        for index, item in enumerate(archive):
            need(index < 100, "Archive member-count bound exceeded")
            name = item.name
            parts = PurePosixPath(name).parts
            need(name and "\\" not in name and ":" not in name and not name.startswith("/")
                 and all(p not in ("..", ".", "") for p in parts), "Unsafe archive member path")
            need(name not in names, "Duplicate archive member")
            names.add(name)
            need(item.isfile() or item.isdir(), "Archive link or unsupported member")
            need(0 <= item.size <= MAX_MEMBER, "Archive member size exceeds bound")
            total += item.size
            need(total <= MAX_EXPANDED, "Archive expanded size exceeds bound")
            is_crossval = bool(re.fullmatch(r"data/cross_validation/fold_[1-5]/claims_(?:train|dev)_[1-5]\.jsonl", name))
            is_dir = name in {"data", "data/cross_validation", *(f"data/cross_validation/fold_{i}" for i in range(1, 6))}
            is_apple = parts[-1].startswith("._") and (name == "._data" or name.startswith("data/cross_validation/"))
            need(name in REQUIRED or is_crossval or (item.isdir() and is_dir) or (item.isfile() and is_apple), "Unapproved archive member")
            need((name not in REQUIRED and not is_crossval) or item.isfile(), "Task member must be regular file")
            reason = "native_task_input" if name in REQUIRED else "unused_cross_validation" if is_crossval else "directory" if item.isdir() else "apple_metadata"
            inventory.append({"name": name, "bytes": item.size, "kind": "file" if item.isfile() else "directory", "disposition": reason})
            if name in REQUIRED:
                stream = archive.extractfile(item)
                need(stream is not None, "Task archive member unavailable")
                content = stream.read(MAX_MEMBER + 1)
                need(len(content) == item.size, "Truncated task archive member")
                payloads[name] = content
                members[name] = {"sha256": digest(content), "bytes": len(content)}
    need(set(payloads) == set(REQUIRED), "Missing required native task member")
    corpus, corpus_bindings, excluded = {}, {}, Counter()
    for row, binding in _rows(payloads[REQUIRED[0]], REQUIRED[0]):
        need({"doc_id", "title", "abstract"} <= row.keys(), "Missing corpus fields")
        key = row["doc_id"]
        need(_integer(key) and key not in corpus, "Duplicate or invalid corpus document ID")
        need(isinstance(row["title"], str) and isinstance(row["abstract"], list) and row["abstract"]
             and all(isinstance(s, str) for s in row["abstract"]), "Invalid corpus text")
        need("structured" not in row or type(row["structured"]) is bool, "Invalid structured flag")
        view = {field: row[field] for field in ("doc_id", "title", "abstract")}
        corpus[key] = view
        binding.update(projected_sha256=digest(canonical(view)), field_sha256={field: digest(canonical(row[field])) for field in view})
        corpus_bindings[str(key)] = binding
        excluded.update(set(row) - set(view))
    claims, claim_bindings, claim_exclusions, all_claim_ids, diagnostics = {}, {}, {}, set(), []
    for split in ("train", "dev", "test"):
        name = f"data/claims_{split}.jsonl"
        parsed, bindings, extras = [], {}, Counter()
        for row, binding in _rows(payloads[name], name):
            need({"id", "claim"} <= row.keys(), "Missing claim fields")
            key = row["id"]
            need(_integer(key) and key not in all_claim_ids, "Duplicate or invalid native claim ID")
            all_claim_ids.add(key)
            need(isinstance(row["claim"], str) and row["claim"].strip(), "Empty/invalid claim text")
            if split != "test":
                need({"evidence", "cited_doc_ids"} <= row.keys(), "Missing supervised claim fields")
            evidence = row.get("evidence", {})
            cited = row.get("cited_doc_ids", [])
            need(isinstance(evidence, dict) and isinstance(cited, list), "Invalid evidence/citation containers")
            need(all(_integer(k) and k in corpus for k in cited), "Invalid cited document")
            if len(set(cited)) != len(cited):
                diagnostics.append({"kind": "duplicate_cited_document_preserved", "split": split, "claim_id": key,
                                    "original_count": len(cited), "unique_count": len(set(cited)),
                                    "handling": "References preserve original array; source-component edges and pair identities are sets."})
            for doc, rationales in evidence.items():
                need(isinstance(doc, str) and doc.isdigit() and str(int(doc)) == doc and int(doc) in corpus,
                     "Unknown or noncanonical evidence document")
                need(isinstance(rationales, list) and rationales, "Empty/invalid rationale list")
                labels, sentence_seen = set(), set()
                for rationale in rationales:
                    need(isinstance(rationale, dict) and set(rationale) == {"label", "sentences"}, "Invalid rationale fields")
                    need(rationale["label"] in ("SUPPORT", "CONTRADICT"), "Invalid evidence label")
                    sentence_ids = rationale["sentences"]
                    need(isinstance(sentence_ids, list) and sentence_ids and all(_integer(s) and s < len(corpus[int(doc)]["abstract"]) for s in sentence_ids)
                         and len(set(sentence_ids)) == len(sentence_ids), "Invalid rationale sentence IDs")
                    need(not sentence_seen.intersection(sentence_ids), "Overlapping rationale sets unsupported by native scorer")
                    sentence_seen.update(sentence_ids)
                    labels.add(rationale["label"])
                need(len(labels) == 1, "Conflicting labels within one evidence document")
            view = {"id": key, "claim": row["claim"], "evidence": evidence, "cited_doc_ids": cited}
            parsed.append(view)
            query = {"id": key, "claim": row["claim"]}
            binding.update(query_sha256=digest(canonical(query)), reference_sha256=digest(canonical(view)),
                           field_sha256={field: digest(canonical(value)) for field, value in view.items()})
            bindings[str(key)] = binding
            extras.update(set(row) - set(view))
        claims[split], claim_bindings[split], claim_exclusions[split] = parsed, bindings, dict(extras)
    return LoadedRelease(freeze(corpus), freeze(claims), freeze({"corpus": corpus_bindings, "claims": claim_bindings}),
                         freeze(members), tuple(freeze(item) for item in inventory),
                         freeze({"corpus": dict(excluded), "claims": claim_exclusions}), freeze(diagnostics), expected_sha256, len(raw))


def projected_products(loaded):
    split = build_split(loaded.claims["train"], loaded.claims["dev"])
    claims = {row["id"]: row for name in ("train", "dev") for row in loaded.claims[name]}
    products = {}
    def add(key, path, value, format, kind, purposes, fields, parents):
        raw = jsonl_bytes(value) if format == "jsonl" else canonical(value) + b"\n"
        products[key] = {"bytes_value": raw, "metadata": {"path": path, "sha256": digest(raw), "bytes": len(raw), "format": format,
                         "kind": kind, "purposes": sorted(set(purposes) | {"preparation_audit"}), "fields": fields,
                         "rows": len(value) if format == "jsonl" else None, "logical_parents": parents}}
    add("corpus", "views/corpus.jsonl", [loaded.corpus[k] for k in sorted(loaded.corpus)], "jsonl", "public_corpus",
        ["fit", "tune", "calibrate", "predict", "evaluate"], ["doc_id", "title", "abstract"], ["member:data/corpus.jsonl:doc_id,title,abstract"])
    for part in ("fit", "tune", "calibration", "dev"):
        rows = [claims[k] for k in split["partitions"][part]]
        purpose = {"fit": "fit", "tune": "tune", "calibration": "calibrate", "dev": "predict"}[part]
        member = "dev" if part == "dev" else "train"
        add(f"queries_{part}", f"views/queries_{part}.jsonl", [{"id": row["id"], "claim": row["claim"]} for row in rows], "jsonl", "query_only",
            [purpose], ["id", "claim"], [f"member:data/claims_{member}.jsonl:id,claim", "split:membership"])
        add(f"references_{part}", f"restricted/references_{part}.jsonl", rows, "jsonl", "fit_supervision" if part == "fit" else "evaluation_reference",
            ["evaluate" if part == "dev" else purpose], ["id", "claim", "evidence", "cited_doc_ids"], [f"member:data/claims_{member}.jsonl:id,claim,evidence,cited_doc_ids", "split:membership"])
    add("fit_pairs", "restricted/fit_pairs.jsonl", pair_rows([claims[k] for k in split["partitions"]["fit"]]), "jsonl", "fit_supervision",
        ["fit"], ["claim_id", "doc_id", "label", "rationale_sentences", "rationale_sets", "negative_basis"], ["references_fit"])
    add("split", "restricted/split.json", split, "json", "preparation_split", [], [], ["member:data/claims_train.jsonl:source_and_text_links", "member:data/claims_dev.jsonl:source_and_text_links"])
    add("source_bindings", "restricted/source_bindings.json", loaded.bindings, "json", "preparation_locator_proof", [], [], ["archive:physical_members"])
    return products, split


def _acquisition(path):
    path = Path(path).resolve()
    record = parse_json(bounded_bytes(path))
    entries = [row for row in record["originals"] if Path(row["file"]).name == "scifact-data.tar.gz"]
    need(len(entries) == 1, "Exactly one pinned data archive required")
    entry = entries[0]
    archive, receipt = Path(entry["file"]).resolve(), Path(entry["receipt_file"]).resolve()
    receipt_bytes = bounded_bytes(receipt)
    need(digest(receipt_bytes) == entry["receipt_sha256"], "Original receipt hash mismatch")
    value = parse_json(receipt_bytes)
    need(value.get("status") == "downloaded_not_parsed" and value.get("sha256") == entry["sha256"]
         and value.get("bytes") == entry["bytes"] and Path(value["path"]).resolve() == archive
         and value.get("url") == entry["source_url"], "Original receipt identity mismatch")
    metadata = {"path": str(archive), "sha256": entry["sha256"], "bytes": entry["bytes"], "receipt_path": str(receipt),
                "receipt_sha256": entry["receipt_sha256"], "url": value["url"], "downloaded_at": value["finished_at_utc"],
                "physical_role": "mixed_role_preparation_container", "allowed_purposes": ["prepare", "preparation_audit"]}
    return metadata, {"path": str(path), "sha256": digest(bounded_bytes(path))}


def prepare_release(acquisition_record, output):
    """Reserve, inspect, project and seal; a failure always preserves the attempt."""
    output = Path(output).resolve()
    journal = RunJournal(output, kind="build")
    started = time.perf_counter()
    stage = "acquisition"
    try:
        source_pins = {str(p.resolve()): digest(p.read_bytes()) for p in (Path(__file__), Path(__file__).with_name("split.py"))}
        journal.append("build_stage", stage=stage)
        archive, acquisition = _acquisition(acquisition_record)
        stage = "parse"
        journal.append("build_stage", stage=stage)
        loaded = load_archive(archive["path"], archive["sha256"], archive["bytes"])
        stage = "projection_and_split"
        journal.append("build_stage", stage=stage)
        products, split = projected_products(loaded)
        for key, product in products.items():
            publish_bytes(output / product["metadata"]["path"], product["bytes_value"])
            journal.append("build_progress", product=key, bytes=product["metadata"]["bytes"], rows=product["metadata"]["rows"])
        need(all(digest(bounded_bytes(path)) == pin for path, pin in source_pins.items()), "Projector source changed during preparation")
        manifest = {"schema_version": 1, "kind": "scifact_preparation", "authority_version": "purpose_field_projection_v1",
                    "prepared_at_utc": datetime.now(timezone.utc).isoformat(), "archive": archive, "acquisition": acquisition,
                    "members": loaded.members, "inventory": loaded.inventory, "schema_exclusions": loaded.schema_exclusions, "diagnostics": loaded.diagnostics,
                    "source_pins": source_pins, "products": {key: row["metadata"] for key, row in products.items()},
                    "counts": {"corpus": len(loaded.corpus), **{name: len(rows) for name, rows in loaded.claims.items()}},
                    "split_counts": split["counts"], "pair_label_counts": split["pair_label_counts"],
                    "feasibility_issues": split["feasibility_issues"], "reference_isolation": "qualified_projector_and_consumer_allowlists_not_os_sandbox",
                    "normalization": "Predictor text preserved; only grouping uses NFKC/casefold/whitespace. Product order native ID ascending.",
                    "negative_pair_basis": "Pinned SciFact doc/data.md: cited documents outside evidence were annotated without evidence; corpus remainder stays unlabeled."}
        manifest_raw = canonical(manifest) + b"\n"
        publish_bytes(output / "manifest.json", manifest_raw)
        report = {"schema_version": 1, "status": "prepared", "manifest_sha256": digest(manifest_raw), "elapsed_seconds": time.perf_counter()-started,
                  "counts": manifest["counts"], "split_counts": split["counts"], "pair_label_counts": split["pair_label_counts"],
                  "feasibility_issues": split["feasibility_issues"], "diagnostics": loaded.diagnostics, "candidate_generation": False, "native_scoring": False}
        publish_bytes(output / "build-report.json", canonical(report) + b"\n")
        journal.append("build_completed", manifest_sha256=digest(manifest_raw), counts=report["counts"], elapsed_seconds=report["elapsed_seconds"])
        return freeze(report)
    except BaseException as error:
        journal.fail(error, stage)
        raise
    finally:
        journal.close()


def verify_preparation(output, expected_manifest_sha256, acquisition_record=None):
    output = Path(output).resolve()
    raw = bounded_bytes(output / "manifest.json")
    need(digest(raw) == expected_manifest_sha256, "Preparation manifest anchor mismatch")
    manifest = parse_json(raw)
    need(manifest.get("schema_version") == 1 and manifest.get("kind") == "scifact_preparation"
         and manifest.get("authority_version") == "purpose_field_projection_v1", "Unsupported projection authority")
    actual_source_pins = {str(p.resolve()): digest(bounded_bytes(p)) for p in (Path(__file__), Path(__file__).with_name("split.py"))}
    need(manifest["source_pins"] == actual_source_pins, "Projector code changed or incomplete code proof")
    acquisition_path = acquisition_record or manifest["acquisition"]["path"]
    archive, acquisition = _acquisition(acquisition_path)
    need(archive == manifest["archive"] and acquisition == manifest["acquisition"], "Acquisition anchor mismatch")
    loaded = load_archive(archive["path"], archive["sha256"], archive["bytes"])
    products, split = projected_products(loaded)
    need(set(products) == set(manifest["products"]), "Projection product set mismatch")
    need(canonical(loaded.members) == canonical(manifest["members"]), "Archive member proof mismatch")
    need(canonical(loaded.inventory) == canonical(manifest["inventory"]) and canonical(loaded.schema_exclusions) == canonical(manifest["schema_exclusions"]), "Archive inventory/schema report mismatch")
    need(canonical(loaded.diagnostics) == canonical(manifest["diagnostics"]), "Archive diagnostics mismatch")
    for key, product in products.items():
        need(canonical(product["metadata"]) == canonical(manifest["products"][key]), "Product purpose or field authority mismatch")
        path = safe_child(output, product["metadata"]["path"])
        need(bounded_bytes(path) == product["bytes_value"], "Source-reconstructed product mismatch")
    expected_counts = {"corpus": len(loaded.corpus), **{name: len(rows) for name, rows in loaded.claims.items()}}
    need(manifest["counts"] == expected_counts and canonical(manifest["split_counts"]) == canonical(split["counts"])
         and canonical(manifest["pair_label_counts"]) == canonical(split["pair_label_counts"])
         and canonical(manifest["feasibility_issues"]) == canonical(split["feasibility_issues"]), "Preparation accounting mismatch")
    events = read_chain(output / "journal.jsonl")
    need(events[0]["event"] == "build_reserved" and events[-1]["event"] == "build_completed"
         and events[-1]["details"]["manifest_sha256"] == expected_manifest_sha256, "Incomplete or mismatched preparation journal")
    report = parse_json(bounded_bytes(output / "build-report.json"))
    elapsed = events[-1]["details"].get("elapsed_seconds")
    need(type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0
         and canonical(events[-1]["details"].get("counts")) == canonical(expected_counts), "Preparation terminal accounting mismatch")
    expected_report = {"schema_version": 1, "status": "prepared", "manifest_sha256": expected_manifest_sha256,
                       "elapsed_seconds": elapsed, "counts": expected_counts, "split_counts": split["counts"],
                       "pair_label_counts": split["pair_label_counts"], "feasibility_issues": split["feasibility_issues"],
                       "diagnostics": loaded.diagnostics, "candidate_generation": False, "native_scoring": False}
    need(canonical(report) == canonical(expected_report), "Preparation report mismatch")
    return freeze(manifest)


def load_product(output, manifest, product_id, purpose):
    need(canonical(parse_json(bounded_bytes(Path(output) / "manifest.json"))) == canonical(manifest), "Consumer manifest differs from retained preparation")
    need(product_id in manifest["products"], "Unknown logical product")
    product = manifest["products"][product_id]
    need(purpose in product["purposes"], "Logical product denied for consumer purpose")
    raw = bounded_bytes(safe_child(Path(output).resolve(), product["path"]))
    need(len(raw) == product["bytes"] and digest(raw) == product["sha256"], "Logical product changed")
    if product["format"] == "jsonl":
        rows = [parse_json(line) for line in raw.splitlines()]
        need(len(rows) == product["rows"] and all(isinstance(row, dict) and set(row) == set(product["fields"]) for row in rows), "Logical product schema mismatch")
        return freeze(rows)
    need(product["format"] == "json", "Unknown product format")
    return freeze(parse_json(raw))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--acquisition", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(canonical(prepare_release(args.acquisition, args.output)).decode())


if __name__ == "__main__":
    main()
