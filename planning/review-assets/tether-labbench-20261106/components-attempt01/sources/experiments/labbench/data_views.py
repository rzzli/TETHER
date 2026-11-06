"""Trusted LitQA2 preparation. Never import this module in the answering worker.

The mixed original contains answers and retrieval hints. Only queries.json is an
answerer input; a content hash does not turn a mixed container into public input.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import random
import re
import string
from uuid import UUID

from asof.atomic import publish_bytes
from asof.journal import RunJournal, read_chain
from asof.serde import ContractError, canonical, freeze, parse_json, safe_child

REFUSE_CHOICE = "Insufficient information to answer the question"
SEED = 20261106
MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 1000
ORIGINAL = "github/LitQA2/litqa-v2-public.jsonl"
REQUIRED_FIELDS = {"id", "question", "ideal", "distractors", "canary", "tag", "version", "sources"}
OPTIONAL_FIELDS = {"key-passage", "is_opensource", "source", "subtask"}


def need(condition, message):
    if not condition:
        raise ContractError(message)


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def bounded_bytes(path, limit=MAX_BYTES):
    path = Path(path)
    need(path.is_file() and not path.is_symlink(), "Missing or symlinked input")
    with path.open("rb") as stream:
        payload = stream.read(limit + 1)
    need(len(payload) <= limit, "Input byte bound exceeded")
    return payload


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _proof(root, relative, payload):
    return {"path": relative, "sha256": digest(payload), "bytes": len(payload)}


def verify_originals(root, expected_receipt_sha256):
    root = Path(root).resolve()
    receipt_bytes = bounded_bytes(safe_child(root, "ACQUISITION.json"))
    need(_sha(expected_receipt_sha256) and digest(receipt_bytes) == expected_receipt_sha256,
         "Acquisition receipt hash mismatch")
    receipt = parse_json(receipt_bytes)
    need(receipt.get("schema_version") == 1 and isinstance(receipt.get("files"), list), "Invalid acquisition receipt")
    proofs, native_payload = {}, None
    for record in receipt["files"]:
        relative = record.get("path")
        need(isinstance(relative, str) and relative not in proofs, "Duplicate acquisition path")
        payload = bounded_bytes(safe_child(root, relative))
        need(record.get("status") == 200 and record.get("bytes") == len(payload)
             and record.get("sha256") == digest(payload), "Original proof mismatch")
        if record.get("git_blob_sha1") is not None:
            blob = hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
            need(blob == record["git_blob_sha1"], "Git blob mismatch")
        if record.get("expected_sha256") is not None:
            need(record["expected_sha256"] == digest(payload), "Provider digest mismatch")
        proofs[relative] = record
        if relative == ORIGINAL:
            native_payload = payload
    need(ORIGINAL in proofs, "Native JSONL absent from acquisition")
    return freeze(receipt), freeze(proofs), native_payload


def project_rows(payload, *, seed=SEED, expected_count=199):
    """Pure trusted projection with native all-option shuffle and no skipped rows."""
    need(type(seed) is int and type(expected_count) is int and 0 < expected_count <= MAX_ROWS, "Invalid projection settings")
    need(len(payload) <= MAX_BYTES, "Original exceeds byte bound")
    queries, references, provenance, seen = [], [], [], set()
    rng = random.Random(seed)
    fields = Counter()
    for ordinal, raw_line in enumerate(payload.splitlines(keepends=True)):
        need(ordinal < MAX_ROWS and raw_line.strip(), "Empty or excess native row")
        row = parse_json(raw_line)
        need(isinstance(row, dict) and REQUIRED_FIELDS <= set(row)
             and not set(row) - REQUIRED_FIELDS - OPTIONAL_FIELDS, "Unexpected original schema")
        need(isinstance(row["id"], str), "Native ID must be a string")
        try:
            need(str(UUID(row["id"])) == row["id"], "Noncanonical native UUID")
        except (ValueError, AttributeError) as exc:
            raise ContractError("Invalid native UUID") from exc
        need(row["id"] not in seen, "Duplicate native ID")
        seen.add(row["id"])
        for name in ("question", "ideal", "canary", "tag", "version"):
            need(isinstance(row[name], str) and bool(row[name].strip()) and len(row[name]) <= 64000,
                 "Invalid original string")
        need(isinstance(row["distractors"], list) and 1 <= len(row["distractors"]) <= 24
             and all(isinstance(v, str) and v.strip() for v in row["distractors"]), "Invalid distractors")
        need(isinstance(row["sources"], list) and all(isinstance(v, str) for v in row["sources"]), "Invalid source hints")
        need(row.get("is_opensource") is None or type(row["is_opensource"]) is bool, "Invalid openness metadata")
        passage = row.get("key-passage")
        need(passage is None or isinstance(passage, str) or
             (isinstance(passage, list) and all(isinstance(v, str) for v in passage)), "Invalid hidden key passage")
        values = [row["ideal"], REFUSE_CHOICE, *row["distractors"]]
        need(len(set(values)) == len(values), "Ambiguous duplicate choices")
        permutation = list(range(len(values)))
        rng.shuffle(permutation)
        choices = [f"({letter}) {values[index]}" for letter, index in zip(string.ascii_uppercase, permutation)]
        queries.append({"id": row["id"], "question": row["question"], "choices": choices})
        references.append({"id": row["id"], "answer_index": permutation.index(0), "unsure_index": permutation.index(1)})
        provenance.append({"id": row["id"], "row_1based": ordinal + 1,
                           "raw_line_sha256": digest(raw_line), "original_fields": row,
                           "query_sha256": digest(canonical(queries[-1])),
                           "reference_sha256": digest(canonical(references[-1]))})
        fields.update(row.keys())
    need(len(queries) == expected_count, "Native schedule count mismatch")
    return freeze({"queries": queries, "references": references, "provenance": provenance,
                   "diagnostics": {"count": len(queries), "field_presence": dict(fields),
                                   "unknown_fields": [], "skipped_rows": 0}})


def prepare_views(original_root, output, *, expected_receipt_sha256, seed=SEED, expected_count=199):
    journal = RunJournal(Path(output), kind="build")
    root = journal.output
    try:
        receipt, proofs, native_payload = verify_originals(original_root, expected_receipt_sha256)
        original_root = Path(original_root).resolve()
        projected = project_rows(native_payload, seed=seed, expected_count=expected_count)
        products = {}
        for name in ("queries", "references", "provenance"):
            payload = canonical(projected[name]) + b"\n"
            relative = name + ".json"
            publish_bytes(safe_child(root, relative), payload)
            products[name] = _proof(root, relative, payload) | {
                "purpose": "answerer_input" if name == "queries" else "evaluation_only",
                "physical_parent": {"path": ORIGINAL, "sha256": proofs[ORIGINAL]["sha256"], "bytes": proofs[ORIGINAL]["bytes"]},
                "logical_fields": ["id", "question", "displayed_choices"] if name == "queries" else ["original_reference_fields"],
            }
            journal.append("product_written", product_id=name, sha256=products[name]["sha256"], bytes=len(payload))
        manifest = {"schema_version": 1, "kind": "labbench_projected_views", "created_at": datetime.now(timezone.utc).isoformat(),
                    "original_root": str(original_root), "acquisition_receipt_sha256": expected_receipt_sha256,
                    "hf_revision": receipt.get("hf_revision"), "github_revision": receipt.get("github_revision"),
                    "seed": seed, "expected_count": expected_count, "shuffle": "native_all_option_random_Random_in_original_order",
                    "products": products, "diagnostics": projected["diagnostics"],
                    "physical_container_role": "mixed_reference_only", "predictor_allowed_product_ids": ["queries"],
                    "projector_sha256": digest(bounded_bytes(Path(__file__)))}
        payload = canonical(manifest) + b"\n"
        publish_bytes(root / "manifest.json", payload)
        journal.append("build_completed", manifest_sha256=digest(payload), count=expected_count)
        publish_bytes(root / "COMPLETE.json", canonical({"manifest_sha256": digest(payload), "journal_sha256": digest(bounded_bytes(journal.path))}) + b"\n")
        return freeze(manifest)
    except BaseException as exc:
        journal.fail(exc, "projection")
        publish_bytes(root / "FAILED.json", canonical({"error_type": type(exc).__name__, "stage": "projection"}) + b"\n")
        raise
    finally:
        journal.close()


def verify_views(root, expected_manifest_sha256):
    root = Path(root).resolve()
    payload = bounded_bytes(safe_child(root, "manifest.json"))
    need(digest(payload) == expected_manifest_sha256, "Projection manifest hash mismatch")
    manifest = parse_json(payload)
    need(manifest.get("schema_version") == 1 and manifest.get("kind") == "labbench_projected_views", "Unknown projection")
    need(manifest.get("projector_sha256") == digest(bounded_bytes(Path(__file__))), "Projector source changed")
    complete = parse_json(bounded_bytes(safe_child(root, "COMPLETE.json")))
    journal_bytes = bounded_bytes(safe_child(root, "journal.jsonl"))
    need(complete == {"manifest_sha256": expected_manifest_sha256, "journal_sha256": digest(journal_bytes)}, "Projection completion mismatch")
    events = read_chain(root / "journal.jsonl")
    need(events[-1]["event"] == "build_completed" and events[-1]["details"]["manifest_sha256"] == expected_manifest_sha256,
         "Projection journal incomplete")
    receipt, proofs, native_payload = verify_originals(manifest["original_root"], manifest["acquisition_receipt_sha256"])
    need(manifest["hf_revision"] == receipt.get("hf_revision") and manifest["github_revision"] == receipt.get("github_revision"), "Acquisition revision mismatch")
    need(manifest["shuffle"] == "native_all_option_random_Random_in_original_order", "Shuffle method mismatch")
    projected = project_rows(native_payload, seed=manifest["seed"], expected_count=manifest["expected_count"])
    need(set(manifest["products"]) == {"queries", "references", "provenance"}
         and manifest["physical_container_role"] == "mixed_reference_only"
         and manifest["predictor_allowed_product_ids"] == ["queries"], "Projection purpose mismatch")
    for name, record in manifest["products"].items():
        actual = bounded_bytes(safe_child(root, record["path"]))
        need(record["path"] == name + ".json" and record["sha256"] == digest(actual) and record["bytes"] == len(actual), "Projection product proof mismatch")
        need(actual == canonical(projected[name]) + b"\n", "Projection semantic mismatch")
        need(record["purpose"] == ("answerer_input" if name == "queries" else "evaluation_only"), "Reference purpose laundering")
        need(record["physical_parent"] == {"path": ORIGINAL, "sha256": proofs[ORIGINAL]["sha256"], "bytes": proofs[ORIGINAL]["bytes"]}, "Projection parent mismatch")
        need(record["logical_fields"] == (["id", "question", "displayed_choices"] if name == "queries" else ["original_reference_fields"]), "Projection fields mismatch")
    need(canonical(manifest["diagnostics"]) == canonical(projected["diagnostics"]), "Projection diagnostics mismatch")
    return freeze(manifest)


def load_queries(path, expected_sha256):
    """Small answerer-safe loader: no original, reference or preparation-manifest read."""
    payload = bounded_bytes(path)
    need(digest(payload) == expected_sha256, "Query product hash mismatch")
    queries = parse_json(payload)
    need(isinstance(queries, list) and 0 < len(queries) <= MAX_ROWS, "Invalid query schedule")
    seen = set()
    for query in queries:
        need(isinstance(query, dict) and set(query) == {"id", "question", "choices"}, "Non-query fields in answering view")
        need(isinstance(query["id"], str) and query["id"] not in seen and isinstance(query["question"], str), "Invalid query identity")
        seen.add(query["id"])
        choices = query["choices"]
        need(isinstance(choices, list) and 3 <= len(choices) <= 26 and all(isinstance(x, str) and x.startswith(f"({string.ascii_uppercase[i]}) ") for i, x in enumerate(choices)), "Invalid displayed choices")
        need(sum(x[4:] == REFUSE_CHOICE for x in choices) == 1, "Refusal option missing or duplicated")
    return freeze(queries)
