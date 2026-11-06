"""Independent, stdlib-only reconstruction of a terminal SciFact stage.

This deliberately imports no project implementation. The only executed scorer is
the unchanged, SHA-pinned upstream CLI. References are opened only after an
externally anchored completed stage and its candidate journals are checked.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import unicodedata

EVALUATOR_SHA256 = "2554fed44c3f5592bdeed59ab0d3918a412b452ba1c77da73ba0f62e74c9987f"
EVALUATOR_COMMIT = "66feffc5b2cc9e28e3ce3b8c9e824c3c642981eb"
ARCHIVE_SHA256 = "11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be"
GRID = [{"k": k, "rationale_threshold": t} for k in (5, 10, 20) for t in (.25, .5, .75)]
SUM_FIELDS = ("wall_seconds", "cpu_seconds", "input_bytes", "output_bytes", "examples")


class AuditError(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise AuditError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(canonical(value))


def same(expected, actual, message):
    need(canonical(expected) == canonical(actual), "Mismatch: " + message)


def parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, "Duplicate JSON key: " + key)
            result[key] = value
        return result
    def bad(value):
        raise AuditError("Non-finite JSON constant: " + value)
    return json.loads(raw, object_pairs_hook=unique, parse_constant=bad)


def read_bytes(path, expected=None, maximum=256 * 1024**2):
    path = Path(path)
    need(path.is_file() and not path.is_symlink(), "Missing or symlinked file: " + str(path))
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    need(len(raw) <= maximum, "Read bound exceeded: " + str(path))
    if expected is not None:
        need(sha(raw) == expected, "Checksum mismatch: " + str(path))
    return raw


def read(path, expected=None):
    return parse(read_bytes(path, expected))


def file_hash(path):
    path = Path(path)
    need(path.is_file() and not path.is_symlink(), "Missing or symlinked proof file: " + str(path))
    result, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024**2), b""):
            result.update(chunk); size += len(chunk)
    return {"path": str(path.absolute()), "sha256": result.hexdigest(), "bytes": size}


def proof(item):
    actual = file_hash(item["path"])
    need(actual["sha256"] == item["sha256"] and actual["bytes"] == item["bytes"],
         "File proof mismatch: " + item["path"])
    return actual


def child(root, relative):
    need(isinstance(relative, str) and relative and "\\" not in relative and ":" not in relative,
         "Unsafe relative path")
    parts = relative.split("/")
    need(not relative.startswith("/") and all(x not in ("", ".", "..") for x in parts), "Unsafe relative path")
    result = Path(root).joinpath(*PurePosixPath(relative).parts)
    need(result.resolve().is_relative_to(Path(root).resolve()), "Escaping relative path")
    current = result
    while current != Path(root):
        need(not current.is_symlink(), "Symlink in artifact path")
        current = current.parent
    return result


def inventory(root, receipt_name, expected):
    root = Path(root)
    receipt = read(root / receipt_name, expected)
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p != root / receipt_name}
    need(actual == set(receipt["outputs"]), "Receipt inventory mismatch: " + str(root))
    for name, expected_hash in receipt["outputs"].items():
        need(file_hash(child(root, name))["sha256"] == expected_hash, "Receipt output mismatch: " + name)
    return receipt


def jsonl(raw):
    return [parse(line) for line in raw.splitlines() if line.strip()]


def chain(path):
    raw = read_bytes(path)
    need(raw.endswith(b"\n"), "Incomplete journal tail")
    events, previous = [], None
    for event in jsonl(raw):
        need(set(event) == {"sequence", "event", "details", "previous_sha256", "sha256"}, "Journal schema differs")
        body = {k: v for k, v in event.items() if k != "sha256"}
        need(event["sequence"] == len(events) and event["previous_sha256"] == previous and digest(body) == event["sha256"],
             "Journal chain mismatch")
        events.append(event); previous = event["sha256"]
    need(events, "Empty journal")
    return events


def schedule_ids(values):
    need(isinstance(values, list) and values and all(type(x) is int and x >= 0 for x in values), "Invalid native schedule")
    need(len(values) == len(set(values)), "Duplicate native schedule")
    return values


def native_prediction(value, corpus, claim_id):
    need(isinstance(value, dict) and set(value) == {"id", "evidence"}, "Native prediction fields differ")
    need(type(value["id"]) is int and value["id"] == claim_id and isinstance(value["evidence"], dict), "Native identity differs")
    for doc, item in value["evidence"].items():
        need(isinstance(doc, str) and doc.isascii() and doc.isdecimal() and str(int(doc)) == doc and int(doc) in corpus,
             "Unknown or noncanonical document")
        need(isinstance(item, dict) and set(item) == {"label", "sentences"} and item["label"] in {"SUPPORT", "CONTRADICT"},
             "Native label fields differ")
        sentences = item["sentences"]
        need(isinstance(sentences, list) and all(type(i) is int and 0 <= i < len(corpus[int(doc)]["abstract"]) for i in sentences),
             "Invalid sentence locator")
        need(len(sentences) == len(set(sentences)), "Duplicate sentence locator")
    return value


def strict_correct(gold, prediction):
    """Exact evidence documents and labels; one complete native-capped rationale."""
    expected, predicted = gold["evidence"], prediction["evidence"]
    if set(expected) != set(predicted):
        return False
    for doc, rationales in expected.items():
        labels = {item["label"] for item in rationales}
        need(len(labels) == 1 and rationales and all(item["sentences"] for item in rationales), "Invalid gold rationale")
        if predicted[doc]["label"] not in labels:
            return False
        cap = max(3, min(len(item["sentences"]) for item in rationales))
        available = set(predicted[doc]["sentences"][:cap])
        if not any(set(item["sentences"]).issubset(available) for item in rationales):
            return False
    return True


def aggregate(schedule, golds, dispositions, corpus):
    schedule_ids(schedule)
    need([g["id"] for g in golds] == schedule and [d["id"] for d in dispositions] == schedule, "All-scheduled identity/order mismatch")
    names = ("produced", "accepted", "correct_raw", "correct_and_admitted", "correct_but_policy_rejected",
             "correct_but_not_admitted", "successful_native_nei", "correct_native_nei", "raw_failure_placeholders",
             "checked_failure_or_rejection_placeholders")
    counts = dict.fromkeys(names, 0)
    producers, checks, cases, raw, checked = Counter(), Counter(), [], [], []
    for gold, row in zip(golds, dispositions):
        need(set(row) == {"id", "producer_status", "check_status", "prediction", "reason"}, "Disposition fields differ")
        p, c = row["producer_status"], row["check_status"]
        need(p in {"produced", "parse_failure", "timeout", "error", "unexecuted", "input_unavailable"}, "Unknown producer status")
        need(c in {"accepted", "rejected", "error", "not_run"}, "Unknown check status")
        produced, accepted = p == "produced", p == "produced" and c == "accepted"
        if produced:
            native_prediction(row["prediction"], corpus, row["id"])
        else:
            need(row["prediction"] is None and c == "not_run", "Failure cannot produce a native prediction")
        if (not produced and p != "unexecuted") or c in {"rejected", "error"}:
            need(isinstance(row["reason"], str) and row["reason"].strip(), "Failure reason absent")
        candidate = row["prediction"] if produced else {"id": row["id"], "evidence": {}}
        correct = strict_correct(gold, candidate) if produced else None
        useful, nei = bool(accepted and correct), bool(produced and not candidate["evidence"])
        values = (produced, accepted, bool(correct), useful, bool(correct and c == "rejected"),
                  bool(correct and not accepted), nei, bool(nei and correct), not produced, not accepted)
        for name, value in zip(names, values): counts[name] += int(value)
        producers[p] += 1; checks[c] += 1
        raw.append(candidate); checked.append(candidate if accepted else {"id": row["id"], "evidence": {}})
        cases.append(dict(id=row["id"], producer_status=p, check_status=c, reason=row["reason"],
                          prediction_produced=produced, native_nei_prediction=nei, raw_strict_correct=correct,
                          checked_strict_correct=useful, raw_is_placeholder=not produced, checked_is_placeholder=not accepted))
    return {"scheduled_count": len(schedule), "counts": counts, "producer_status_counts": dict(producers),
            "check_status_counts": dict(checks), "case_results": cases, "raw_predictions": raw, "checked_predictions": checked,
            "rates": {key + "_per_scheduled": counts[key] / len(schedule)
                      for key in ("produced", "accepted", "correct_raw", "correct_and_admitted")}}


def source_bindings(result, corpus, claim_id):
    native_prediction(result["prediction"], corpus, claim_id)
    seen = set()
    for rank, item in enumerate(result["retrieved"], 1):
        need(set(item) == {"doc_id", "rank", "score", "document_sha256"}, "Retrieved fields differ")
        doc = item["doc_id"]
        need(type(doc) is int and doc in corpus and doc not in seen and type(item["rank"]) is int and item["rank"] == rank,
             "Retrieved identity/order differs")
        need(type(item["score"]) in (int, float) and math.isfinite(item["score"]), "Invalid retrieval score")
        need(item["document_sha256"] == digest(corpus[doc]), "Original document binding differs")
        seen.add(doc)
    wanted = {(int(doc), sid) for doc, item in result["prediction"]["evidence"].items() for sid in item["sentences"]}
    need({int(doc) for doc in result["prediction"]["evidence"]}.issubset(seen), "Prediction uses unretrieved document")
    actual = set()
    for item in result["source_bindings"]:
        need(set(item) == {"doc_id", "sentence_id", "text_sha256"}, "Sentence binding fields differ")
        doc, sid = item["doc_id"], item["sentence_id"]
        need(type(doc) is int and type(sid) is int and doc in corpus and 0 <= sid < len(corpus[doc]["abstract"]), "Unknown original sentence")
        need((doc, sid) not in actual and item["text_sha256"] == sha(corpus[doc]["abstract"][sid].encode("utf-8")),
             "Duplicate or mismatched original sentence binding")
        actual.add((doc, sid))
    same(sorted(wanted), sorted(actual), "exact selected sentence coverage")
    return {"retrieved_documents": len(seen), "returned_sentences": len(actual)}


def resource_totals(records):
    totals = dict.fromkeys(SUM_FIELDS, 0)
    missing = dict.fromkeys(SUM_FIELDS, 0)
    for row in records:
        value = row["resources"]
        for name in SUM_FIELDS:
            number = value[name]
            need(number is None or type(number) in (int, float) and math.isfinite(number) and number >= 0, "Invalid resource measurement")
            if name in {"input_bytes", "output_bytes", "examples"}:
                need(number is None or type(number) is int, "Noninteger resource count")
            if number is None: missing[name] += 1
            else: totals[name] += number
        need(value["provider_cost_usd"] == 0 and value["token_usage_reason"] == "not_applicable_non_llm" and
             all(value[key] is None for key in ("model_input_tokens", "model_output_tokens", "tokenizer_identity", "provider_usage")),
             "Nonzero provider cost or invented non-LLM token use")
    return {**totals, "unknown_measurements": missing, "provider_cost_usd": 0, "model_input_tokens": None, "model_output_tokens": None}


def resource_panel(records):
    totals = resource_totals(records)
    peaks = [row["resources"]["peak_memory_bytes"] for row in records if row["resources"]["peak_memory_bytes"] is not None]
    need(all(type(x) is int and x >= 0 for x in peaks), "Invalid peak memory measurement")
    return {"cells": len(records), "wall_seconds_sum": totals["wall_seconds"], "cpu_seconds_sum": totals["cpu_seconds"],
            "logical_input_bytes": totals["input_bytes"], "primary_product_output_bytes": totals["output_bytes"],
            "examples": totals["examples"], "unknown_measurements": totals["unknown_measurements"],
            "peak_memory_bytes_max": max(peaks, default=None), "unknown_peak_cells": len(records) - len(peaks),
            "memory_methods": sorted({row["resources"]["memory_method"] for row in records}), "provider_cost_usd": 0}


def session(root, expected_receipt, expected_schedule, configuration):
    root = Path(root)
    need(expected_schedule and len(set(expected_schedule)) == len(expected_schedule), "Empty or duplicate session schedule")
    receipt = inventory(root, "receipt.json", expected_receipt)
    same(receipt["schedule"], expected_schedule, "session schedule")
    same(receipt["configuration"], configuration, "session configuration")
    events = chain(root / "journal.jsonl")
    need(events[0]["event"] == "run_reserved" and events[1]["event"] == "native_configured" and
         events[-1]["event"] == "native_finalized", "Incomplete native session")
    header = events[1]["details"]
    same(header["schedule"], expected_schedule, "journal schedule")
    same(header["configuration"], configuration, "journal configuration")
    records, requests, active, bytes_so_far = {}, {}, None, 0
    for event in events[2:-1]:
        detail = event["details"]
        if event["event"] == "native_dispatch":
            key = detail["cell_id"]
            need(active is None and key in expected_schedule and key not in requests, "Duplicated or overlapping dispatch")
            need(detail["request_sha256"] == digest(detail["request"]), "Request hash differs")
            requests[key] = detail["request"]; active = key
        elif event["event"] in {"native_terminal", "native_unexecuted"}:
            key = detail["cell_id"]
            need(key in expected_schedule and key not in records, "Duplicate or unknown terminal cell")
            need(detail["path"] == "cells/" + sha(key.encode()) + ".json", "Cell path identity differs")
            row = read(child(root, detail["path"]), detail["record_sha256"])
            need(row["cell_id"] == key and digest(row) == detail["record_fingerprint"], "Cell fingerprint differs")
            same(row["resources"], detail["resources"], "journal resources")
            if event["event"] == "native_terminal":
                need(active == key and row["status"] == detail["status"], "Terminal lacks matching dispatch")
                active = None
            else:
                need(key not in requests and row["status"] == "unexecuted", "False unexecuted cell")
            resource_totals([row])
            bytes_so_far += row["resources"]["output_bytes"] or 0
            breach = row["session_elapsed_seconds"] > header["budgets"]["max_wall_seconds"] or bytes_so_far > header["budgets"]["max_output_bytes"]
            need((row["status"] == "budget_exceeded") == breach, "Budget/status disagreement")
            records[key] = row
        else:
            raise AuditError("Unexpected event in finalized session: " + event["event"])
    need(active is None and list(records) == expected_schedule and len(requests) <= header["budgets"]["max_calls"], "Session accounting/schedule incomplete")
    totals = resource_totals(list(records.values()))
    same(totals, receipt["totals"], "receipt resource totals")
    same(totals, events[-1]["details"]["totals"], "journal resource totals")
    need(receipt["terminal_cells"] == len(records) == events[-1]["details"]["terminal_cells"], "Terminal denominator differs")
    return records, requests


def select(rows):
    need(len(rows) == 9 and {digest(row["configuration"]) for row in rows} == {digest(x) for x in GRID}, "Tuning grid differs")
    need(all(row["status"] == "completed" for row in rows), "Failed tuning configuration excluded")
    return sorted(rows, key=lambda row: (-row["metrics"]["abstract_rationalized_f1"], -row["metrics"]["sentence_label_f1"],
                                        row["configuration"]["k"], -row["configuration"]["rationale_threshold"]))[0]


def official(golds, predictions, evaluator_raw, output):
    need(sha(evaluator_raw) == EVALUATOR_SHA256, "Official evaluator pin differs")
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    (output / "eval.py").write_bytes(evaluator_raw)
    for name, rows in (("labels.jsonl", golds), ("predictions.jsonl", predictions)):
        (output / name).write_bytes(b"".join(canonical(row) + b"\n" for row in rows))
    result = subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", str(output / "eval.py"),
                             "--labels_file", str(output / "labels.jsonl"), "--preds_file", str(output / "predictions.jsonl"),
                             "--metrics_output_file", str(output / "metrics.json"), "--verbose"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False)
    (output / "stdout.txt").write_bytes(result.stdout); (output / "stderr.txt").write_bytes(result.stderr)
    need(result.returncode == 0, "Pinned official evaluator failed")
    return read(output / "metrics.json")


def original_fields(manifest):
    """Only called after stage completion/candidate freeze, never during fitting."""
    archive = manifest["archive"]
    need(archive["sha256"] == ARCHIVE_SHA256, "Original SciFact release pin differs")
    raw = read_bytes(archive["path"], archive["sha256"])
    originals = {}
    wanted = {"data/corpus.jsonl", "data/claims_train.jsonl", "data/claims_dev.jsonl"}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
        for member in tar:
            if member.name not in wanted: continue
            need(member.name not in originals and member.isfile() and member.size <= 32 * 1024**2, "Invalid original member")
            content = tar.extractfile(member).read(member.size + 1)
            same({"sha256": sha(content), "bytes": len(content)}, manifest["members"][member.name], "original member proof")
            originals[member.name] = jsonl(content)
    need(set(originals) == wanted, "Original member missing")
    corpus_rows = [{key: row[key] for key in ("doc_id", "title", "abstract")} for row in originals["data/corpus.jsonl"]]
    corpus = {row["doc_id"]: row for row in corpus_rows}
    need(len(corpus) == len(corpus_rows), "Duplicate original corpus ID")
    claims = {}
    for split in ("train", "dev"):
        rows = originals["data/claims_" + split + ".jsonl"]
        claims[split] = {row["id"]: row for row in rows}
        need(len(rows) == len(claims[split]), "Duplicate original claim ID")
    return corpus, claims


def runtime_proofs(runtime):
    proof(runtime["qualification"])
    qualification = read(runtime["qualification"]["path"], runtime["qualification"]["sha256"])
    need(qualification["status"] == "PASS", "Runtime qualification failed")
    for name, value in runtime["executables"].items():
        proof(value)
        need(value["sha256"] == qualification["python"][name + "_sha256"], "Qualified executable identity differs")
    for value in runtime["task_code"].values(): proof(value)
    site = Path(runtime["executables"]["executable"]["path"]).parent.parent / "Lib/site-packages"
    checked = 0
    for name, item in runtime["packages"].items():
        same(item["version"], qualification["installed"][name]["version"], "qualified package version")
        same(item["metadata_sha256"], qualification["installed"][name]["metadata_sha256"], "qualified metadata identity")
        for relative, spec in item["files"].items():
            proof({"path": str((site / relative).resolve()), **spec}); checked += 1
        need(len(item["files"]) == qualification["installed"][name]["record_payloads_verified"], "Runtime payload denominator differs")
    return {"qualified_package_payloads": checked, "task_source_files": len(runtime["task_code"]), "scope": runtime["scope"]}


def component_strata(claims, references, case_results, declared_split):
    """Independent graph traversal from original sources and normalized exact text."""
    combined = {**claims["train"], **claims["dev"]}
    need(len(combined) == len(claims["train"]) + len(claims["dev"]), "Train/dev identity overlap")
    links, adjacency = {}, {key: set() for key in combined}
    for key, row in combined.items():
        normalized = " ".join(unicodedata.normalize("NFKC", row["claim"]).casefold().split())
        tokens = [("source", int(doc)) for doc in set(row["cited_doc_ids"]) | {int(x) for x in row["evidence"]}]
        tokens.append(("exact_text", normalized))
        for token in tokens:
            if token in links:
                other = links[token]; adjacency[key].add(other); adjacency[other].add(key)
            else:
                links[token] = key
    component_by_claim, components = {}, {}
    remaining = set(combined)
    while remaining:
        todo, group = [min(remaining)], set()
        while todo:
            key = todo.pop()
            if key in group: continue
            group.add(key); todo.extend(adjacency[key] - group)
        remaining.difference_update(group)
        ids = sorted(group); identity = digest(ids)
        components[identity] = ids
        for key in ids: component_by_claim[str(key)] = identity
    same(component_by_claim, declared_split["group_by_claim"], "independent original-source components")
    groups = {row["group_id"]: row for row in declared_split["groups"]}
    same(sorted(components), sorted(groups), "declared component inventory")
    for identity, ids in components.items(): same(ids, groups[identity]["claim_ids"], "component claim membership")
    by_status, by_group, per_case = {}, {}, []
    for gold, case in zip(references, case_results):
        labels = {item["label"] for values in gold["evidence"].values() for item in values}
        status = "NEI" if not labels else next(iter(labels)) if len(labels) == 1 else "mixed"
        identity = component_by_claim[str(gold["id"])]
        row = {"id": gold["id"], "source_component_id": identity, "native_reference_status": status,
               "component_all_claims": len(components[identity]),
               "component_dev_claims": sum(i in claims["dev"] for i in components[identity]),
               "cited_document_ids": gold["cited_doc_ids"], "gold_evidence_document_ids": sorted(map(int, gold["evidence"])),
               "produced": case["prediction_produced"], "accepted": case["check_status"] == "accepted",
               "strict_raw_correct": case["raw_strict_correct"], "strict_correct_and_admitted": case["checked_strict_correct"]}
        per_case.append(row)
        for table, group_key in ((by_status, status), (by_group, identity)):
            summary = table.setdefault(group_key, {"scheduled": 0, "produced": 0, "accepted": 0, "strict_raw_correct": 0,
                                                   "strict_correct_and_admitted": 0, "source_component_ids": set()})
            summary["scheduled"] += 1
            for name in ("produced", "accepted", "strict_raw_correct", "strict_correct_and_admitted"): summary[name] += int(bool(row[name]))
            summary["source_component_ids"].add(identity)
    for table in (by_status, by_group):
        for summary in table.values():
            summary["source_component_ids"] = sorted(summary["source_component_ids"])
            summary["source_component_count"] = len(summary["source_component_ids"])
            summary["strict_correct_and_admitted_per_scheduled"] = summary["strict_correct_and_admitted"] / summary["scheduled"]
    return {"per_case": per_case, "by_native_reference_status": by_status, "by_source_component": by_group,
            "grouping": "source_or_NFKC_casefold_whitespace_exact_claim_connected_components; no inferential confidence intervals"}


def retrieval_coverage(references, retrieved_by_claim):
    """Annotation-relative retrieval, measured separately from label/rationale quality."""
    schedule = schedule_ids([row["id"] for row in references])
    need(set(schedule) == set(retrieved_by_claim), "Retrieval coverage schedule differs")
    relevant_pairs, found_pairs, annotated_claims, complete_claims, per_case = 0, 0, 0, 0, []
    for row in references:
        retrieved = retrieved_by_claim[row["id"]]
        need(isinstance(retrieved, list) and all(type(doc) is int and doc >= 0 for doc in retrieved) and
             len(retrieved) == len(set(retrieved)), "Retrieval coverage requires unique native document IDs")
        gold = {int(doc) for doc in row["evidence"]}
        found = gold.intersection(retrieved)
        relevant_pairs += len(gold); found_pairs += len(found)
        if gold:
            annotated_claims += 1; complete_claims += int(found == gold)
        per_case.append({"id": row["id"], "gold_evidence_document_ids": sorted(gold),
                         "retrieved_document_ids": retrieved, "annotated_claim_document_pairs": len(gold),
                         "retrieved_annotated_pairs": len(found),
                         "annotated_pair_recall": len(found) / len(gold) if gold else None,
                         "complete_gold_set_retrieved": found == gold if gold else None})
    return {"scheduled_claims": len(schedule), "annotated_claim_document_pairs": relevant_pairs,
            "retrieved_annotated_claim_document_pairs": found_pairs, "nonempty_gold_claims": annotated_claims,
            "claims_with_complete_gold_set_retrieved": complete_claims, "nei_claims": len(schedule) - annotated_claims,
            "annotated_pair_recall": found_pairs / relevant_pairs if relevant_pairs else None,
            "complete_gold_claim_recall": complete_claims / annotated_claims if annotated_claims else None,
            "per_case": per_case,
            "scope": "annotated_gold_document_retrieval_only; excludes_NEI_from_recall_denominators; no_inferential_confidence_interval"}


def reconstruct(stage, expected_receipt_sha256, output, *, expected_scheduled=300):
    stage, output = Path(stage).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc)
    def write(name, value):
        (output / name).write_bytes(canonical(value) + b"\n")
    write("STARTED.json", {"stage": str(stage), "expected_receipt_sha256": expected_receipt_sha256,
                           "started_at_utc": started.isoformat(), "helper_sha256": file_hash(__file__)["sha256"]})
    try:
        result = _reconstruct(stage, expected_receipt_sha256, output, expected_scheduled)
        result.update(status="PASS", helper_sha256=file_hash(__file__)["sha256"], completed_at_utc=datetime.now(timezone.utc).isoformat())
        write("RECONSTRUCTION.json", result)
        write("RECEIPT.json", {"outputs": {p.relative_to(output).as_posix(): file_hash(p)["sha256"]
                                             for p in sorted(output.rglob("*")) if p.is_file()}})
        return result
    except BaseException as error:
        write("FAILED.json", {"status": "FAILED", "error_type": type(error).__name__, "message": str(error),
                              "recovery": "Inspect; do not edit or exclude scheduled records."})
        raise


def _reconstruct(stage, expected_receipt, output, expected_scheduled):
    receipt = inventory(stage, "RECEIPT.json", expected_receipt)
    need(receipt.get("kind") == "scifact_native_stage", "Wrong stage receipt")
    report, frozen, devfreeze = read(stage / "REPORT.json"), read(stage / "FROZEN.json"), read(stage / "DEV-FROZEN.json")
    events = chain(stage / "journal.jsonl")
    need(report["status"] == "completed" and events[-1]["event"] == "build_completed" and not (stage / "FAILED.json").exists(),
         "Independent scoring requires a completed, frozen candidate stage")
    schedule = schedule_ids(frozen["dev_schedule"])
    need(len(schedule) == expected_scheduled == report["scheduled"], "Complete scheduled denominator differs")
    same(frozen["grid"], GRID, "preregistered grid")
    need(frozen["selection_criterion"] == "abstract_rationalized_f1_then_sentence_label_f1_then_smaller_k_then_higher_threshold", "Frozen selection criterion differs")
    proof(frozen["protocol"])
    same(devfreeze["dev_schedule"], schedule, "dev freeze schedule")
    same(receipt["runtime_fingerprint"], digest(frozen["runtime"]), "runtime receipt fingerprint")
    same(devfreeze["runtime_fingerprint"], receipt["runtime_fingerprint"], "frozen runtime")
    need(devfreeze["reference_answers_opened_for_prediction"] is False and frozen["provider_spend_usd"] == report["provider_spend_usd"] == 0,
         "Prediction reference-use declaration or zero-spend differs")
    dispatches = [e for e in events if e["event"] == "build_worker_dispatch"]
    returns = [e for e in events if e["event"] == "build_worker_returned"]
    names = ["fit", *[f"tune-{i:02d}" for i in range(1, 10)], "dev"]
    need([e["details"]["name"] for e in dispatches] == names == [e["details"]["name"] for e in returns], "Attempt inventory/retry/order differs")
    freeze_events = [e for e in events if e["event"] == "build_dev_frozen"]
    need(len(freeze_events) == 1 and freeze_events[0]["sequence"] < dispatches[-1]["sequence"], "Candidate prediction preceded model freeze")
    same(freeze_events[0]["details"]["sha256"], file_hash(stage / "DEV-FROZEN.json")["sha256"], "dev freeze journal")
    initial_events = [e for e in events if e["event"] == "build_stage" and e["details"].get("stage") == "initialized"]
    need(len(initial_events) == 1 and initial_events[0]["details"]["freeze_sha256"] == file_hash(stage / "FROZEN.json")["sha256"], "Initial freeze journal differs")
    same(events[-1]["details"]["evaluation_sha256"], file_hash(stage / "evaluation.json")["sha256"], "outcome journal hash")
    same(devfreeze["evaluator"], frozen["evaluator"], "evaluator freeze")
    evaluator = read_bytes(frozen["evaluator"]["path"], EVALUATOR_SHA256)
    proof(frozen["evaluator"])
    runtime = runtime_proofs(frozen["runtime"])
    prep = Path(frozen["preparation_root"])
    manifest = read(prep / "MANIFEST.json", frozen["preparation_manifest_sha256"])
    need(manifest["kind"] == "scifact_preparation" and not manifest["feasibility_issues"], "Preparation feasibility failed")
    product_proofs = {name: {"path": str(child(prep, item["path"])), **{k: item[k] for k in ("sha256", "bytes")}}
                      for name, item in manifest["products"].items()}
    for item in product_proofs.values(): proof(item)
    archive = manifest["archive"]
    proof(archive); transport_receipt = read(archive["receipt_path"], archive["receipt_sha256"])
    proof(manifest["acquisition"] | {"bytes": Path(manifest["acquisition"]["path"]).stat().st_size})
    for source, expected in manifest["source_pins"].items(): need(file_hash(source)["sha256"] == expected, "Preparation source changed")
    need(datetime.fromisoformat(archive["downloaded_at"]) <= datetime.fromisoformat(frozen["cutoff"]), "Future source availability")
    need(transport_receipt.get("sha256") == archive["sha256"] and transport_receipt.get("bytes") == archive["bytes"] and
         transport_receipt.get("status") == "downloaded_not_parsed" and transport_receipt.get("http_status") == 200 and
         Path(transport_receipt["path"]).resolve() == Path(archive["path"]).resolve(), "Original receipt/archive mismatch")
    model_path = stage / "jobs/fit/model/model-manifest.json"
    model = read(model_path, devfreeze["model_manifest_sha256"])
    same(report["model_manifest_sha256"], devfreeze["model_manifest_sha256"], "reported model")
    same(model["configuration"], devfreeze["configuration"], "selected configuration")
    same(model["preparation_manifest_sha256"], frozen["preparation_manifest_sha256"], "model parent preparation")
    same(model["fit_product_ids"], ["corpus", "queries_fit", "fit_pairs"], "fit input roles")
    proof(model["producer_code"])
    same(model["producer_code"], frozen["runtime"]["task_code"][model["producer_code"]["path"]], "frozen producer code")
    for item in model["files"]: proof({**item, "path": str(child(model_path.parent, item["path"]))})
    for name, spec in model["input_product_proofs"].items(): same(spec, {k: manifest["products"][name][k] for k in ("sha256", "bytes")}, "model input proof")
    need(model["fit_execution"]["path"] == str(stage / "jobs/fit/session"), "Fit execution path differs")
    jobs, recipes, primary_panels, reported_jobs = {}, {}, {}, []
    for index, name in enumerate(names):
        job = stage / "jobs" / name
        recipe_path = stage / "recipes" / (name + ".json")
        recipe = read(recipe_path, dispatches[index]["details"]["recipe_sha256"])
        same(recipe, read(job / "recipe.json"), "worker copied recipe")
        expected_names = {"corpus", "queries_fit", "fit_pairs"} if name == "fit" else {"model_json", "model_arrays", "queries"}
        need(set(recipe["inputs"]) == expected_names, "Worker input role inventory differs")
        for value in recipe["inputs"].values(): proof(value)
        wanted_inputs = {key: product_proofs[key] for key in expected_names} if name == "fit" else {
            "model_json": file_hash(model_path.parent / "model.json"), "model_arrays": file_hash(model_path.parent / "arrays.npz"),
            "queries": product_proofs["queries_dev" if name == "dev" else "queries_tune"]}
        same(recipe["inputs"], wanted_inputs, "purpose-eligible producer inputs")
        complete = read(job / "COMPLETE.json")
        need(complete["status"] == "completed", "Worker incomplete")
        cell_schedule = ["fit"] if name == "fit" else ["setup", *map(str, recipe["schedule"])]
        records, requests = session(job / "session", complete["session_receipt_sha256"], cell_schedule, recipe["configuration"])
        need(all(x["status"] == "completed" for x in records.values()), "Non-completed cell in completed worker")
        setup = "fit" if name == "fit" else "setup"
        same(requests[setup], {"mode": recipe["mode"], "inputs": recipe["inputs"]}, "worker setup request")
        need(records[setup]["resources"]["input_bytes"] == sum(p["bytes"] for p in recipe["inputs"].values()), "Setup logical bytes differ")
        transport = read(stage / "transport" / (name + ".json"))
        need(transport["returncode"] == returns[index]["details"]["returncode"] == 0, "Worker transport failed")
        same(transport["supervision"], returns[index]["details"]["supervision"], "transport supervision")
        need(transport["recipe_sha256"] == file_hash(recipe_path)["sha256"], "Transport recipe differs")
        audit = jsonl(read_bytes(job / "io-audit.jsonl"))
        need(audit and all(row["allowed"] is True for row in audit), "Worker access denied or audit absent")
        observed = {str(Path(row["path"]).resolve()).casefold() for row in audit if row.get("path")}
        allowed = {str(Path(value["path"]).resolve()).casefold() for value in recipe["inputs"].values()}
        need(allowed <= observed, "Input absent from managed-open audit")
        forbidden = {str(child(prep, item["path"]).resolve()).casefold() for key, item in manifest["products"].items()
                     if key not in ({"corpus", "queries_fit", "fit_pairs"} if name == "fit" else {"queries_dev" if name == "dev" else "queries_tune"})}
        forbidden.add(str(Path(archive["path"]).resolve()).casefold())
        need(not observed.intersection(forbidden), "Worker observed prohibited reference/container product")
        jobs[name], recipes[name] = (records, requests), recipe
        reported_jobs.append({"name": name, "path": str(job), "recipe": str(recipe_path), "schedule": recipe["schedule"], "mode": recipe["mode"]})
    same(report["jobs"], reported_jobs, "reported job inventory")
    same(recipes["dev"]["schedule"], schedule, "dev worker schedule")
    same(recipes["dev"]["configuration"], model["configuration"], "dev worker configuration")
    auxiliary_dispatches = [e for e in events if e["event"] == "build_auxiliary_dispatch"]
    auxiliary_returns = [e for e in events if e["event"] == "build_auxiliary_returned"]
    auxiliary_names = [*[f"score-tune-{i:02d}" for i in range(1, 10)], "check", "score-dev"]
    need([e["details"]["name"] for e in auxiliary_dispatches] == auxiliary_names ==
         [e["details"]["name"] for e in auxiliary_returns], "Auxiliary attempt inventory differs")
    auxiliary_rows, score_records, score_recipes = [], {}, {}
    for number, name in enumerate(auxiliary_names):
        is_check = name == "check"
        job = stage / "checks" if is_check else stage / "evaluation-jobs" / name.removeprefix("score-")
        recipe_path = stage / "auxiliary-recipes" / (name + ".json")
        recipe = read(recipe_path, auxiliary_dispatches[number]["details"]["recipe_sha256"])
        same(recipe, read(job / "recipe.json"), "auxiliary copied recipe")
        complete = read(job / "COMPLETE.json")
        need(complete["status"] == "completed", "Incomplete auxiliary process")
        transport = read(stage / "transport" / (name + ".json"))
        need(transport["returncode"] == auxiliary_returns[number]["details"]["returncode"] == 0, "Failed auxiliary transport")
        same(transport["supervision"], auxiliary_returns[number]["details"]["supervision"], "auxiliary supervision")
        need(transport["recipe_sha256"] == file_hash(recipe_path)["sha256"], "Auxiliary recipe transport differs")
        auxiliary_rows.append({"name": name, "path": str(job), "recipe": str(recipe_path),
                               "script": "check_worker.py" if is_check else "score_worker.py"})
        if is_check:
            check_recipe, check_complete = recipe, complete
            same(recipe["schedule"], schedule, "checker full schedule")
            same(recipe["configuration"], model["configuration"], "checker configuration")
            same(recipe["model_manifest_sha256"], devfreeze["model_manifest_sha256"], "checker model parent")
            same(recipe["preparation_manifest_sha256"], frozen["preparation_manifest_sha256"], "checker preparation parent")
            same(recipe["policy_sha256"], devfreeze["policy_sha256"], "checker policy")
            same(recipe["producer_session"], {"path": str(stage / "jobs/dev/session"),
                                              "receipt_sha256": read(stage / "jobs/dev/COMPLETE.json")["session_receipt_sha256"]},
                 "checker immutable producer receipt anchor")
            admission = recipe["container_admission"]
            same(admission["archive_sha256"], archive["sha256"], "admitted archive parent")
            same(admission["original_receipt_sha256"], archive["receipt_sha256"], "admitted transport parent")
            need(admission["allowed_purpose"] == "preparation", "Mixed container purpose differs")
            normalized_path = child(Path(recipe["workspace_root"]), admission["normalized_receipt_path"])
            normalized = read(normalized_path, admission["core"]["normalized_receipt_sha256"])
            need(normalized["sha256"] == archive["sha256"] and normalized["bytes"] == archive["bytes"] and
                 normalized["original_transport_receipt_sha256"] == archive["receipt_sha256"] and
                 normalized["allowed_purpose"] == "preparation" and normalized["completed_at_utc"] == transport_receipt["finished_at_utc"],
                 "Normalized original transport proof differs")
            policy = {"schema_version": 1, "policy": "scifact_native_purpose_policy_v1",
                      "preparation_manifest_sha256": frozen["preparation_manifest_sha256"],
                      "model_manifest_sha256": devfreeze["model_manifest_sha256"], "cutoff": datetime.fromisoformat(frozen["cutoff"]).isoformat(),
                      "container_admission_sha256": digest(admission),
                      "adapter_code_sha256": next(p["sha256"] for path, p in frozen["runtime"]["task_code"].items() if Path(path).name == "tether_adapter.py")}
            need(digest(policy) == devfreeze["policy_sha256"] == report["policy_sha256"], "Policy identity reconstruction differs")
            proof(recipe["candidates"])
            same(read(recipe["candidates"]["path"], recipe["candidates"]["sha256"]),
                 [jobs["dev"][0][str(i)] for i in schedule], "checker exact producer record array")
            need(complete["candidate_input_sha256"] == recipe["candidates"]["sha256"], "Checker candidate receipt differs")
            need(auxiliary_dispatches[number]["sequence"] > returns[-1]["sequence"], "Check preceded candidate production")
        else:
            need(set(recipe["inputs"]) == {"corpus", "references", "candidates"}, "Scorer input roles differ")
            for value in recipe["inputs"].values(): proof(value)
            same(recipe["inputs"]["corpus"], product_proofs["corpus"], "scorer corpus input")
            same(recipe["inputs"]["references"], product_proofs["references_dev" if name == "score-dev" else "references_tune"], "scorer reference input")
            need(recipe["mode"] == ("evaluate" if name == "score-dev" else "tune"), "Scorer mode differs")
            same(recipe["evaluator"], frozen["evaluator"], "scorer evaluator pin")
            records, requests = session(job / "session", complete["session_receipt_sha256"], ["score"], {"mode": recipe["mode"]})
            need(records["score"]["status"] == "completed", "Scorer cell incomplete")
            same(requests["score"], {key: recipe[key] for key in ("mode", "inputs", "schedule", "evaluator")}, "scorer request identity")
            same(records["score"]["result"], read(job / "RESULT.json", complete["result_sha256"]), "scorer result identity")
            need(records["score"]["resources"]["input_bytes"] == sum(x["bytes"] for x in recipe["inputs"].values()) + recipe["evaluator"]["bytes"] and
                 records["score"]["resources"]["output_bytes"] == file_hash(job / "RESULT.json")["bytes"] and
                 records["score"]["resources"]["examples"] == len(recipe["schedule"]), "Scorer product accounting differs")
            audit = jsonl(read_bytes(job / "io-audit.jsonl"))
            need(audit and all(row["allowed"] is True for row in audit), "Scorer managed access failed")
            observed = {str(Path(row["path"]).resolve()).casefold() for row in audit if row.get("path")}
            need({str(Path(x["path"]).resolve()).casefold() for x in [*recipe["inputs"].values(), recipe["evaluator"]]} <= observed,
                 "Scorer input missing from managed access audit")
            score_records[name], score_recipes[name] = records["score"], recipe
            predecessor = returns[-1] if name == "score-dev" else returns[number + 1]
            need(auxiliary_dispatches[number]["sequence"] > predecessor["sequence"], "Scoring preceded candidate production")
    same(report["auxiliary_jobs"], auxiliary_rows, "reported auxiliary attempts")
    checks, check_requests = session(stage / "checks/session", check_complete["session_receipt_sha256"], list(map(str, schedule)), model["configuration"])
    need(all(row["status"] in {"accepted", "rejected"} for row in checks.values()), "Check stage incomplete")
    need(check_complete["setup_resources"]["input_bytes"] == check_recipe["candidates"]["bytes"] and
         check_complete["setup_resources"]["output_bytes"] == 0 and check_complete["setup_resources"]["examples"] == 0,
         "Checker setup product byte accounting differs")
    # Candidate/receipt finalization is established above. Only now read references.
    corpus, claims = original_fields(manifest)
    def product(name):
        item = manifest["products"][name]
        return jsonl(read_bytes(child(prep, item["path"]), item["sha256"]))
    same(product("corpus"), sorted(corpus.values(), key=lambda row: row["doc_id"]), "corpus projection from original fields")
    for partition in ("fit", "tune", "dev"):
        queries, references = product("queries_" + partition), product("references_" + partition)
        original = claims["dev" if partition == "dev" else "train"]
        ids = [row["id"] for row in queries]
        same(queries, [{key: original[i][key] for key in ("id", "claim")} for i in ids], "original query projection")
        same(references, [{key: original[i][key] for key in ("id", "claim", "evidence", "cited_doc_ids")} for i in ids], "original reference projection")
    same(model["fit_claim_ids"], [r["id"] for r in product("queries_fit")], "model fit claim membership")
    query_lookup = {row["id"]: row for row in product("queries_dev")}
    same(sorted(query_lookup), schedule, "original development schedule")
    tune_queries = {row["id"]: row for row in product("queries_tune")}
    fit_records = jobs["fit"][0]
    need(fit_records["fit"]["resources"]["output_bytes"] == sum(x["bytes"] for x in model["files"]), "Fit product bytes differ")
    same(fit_records["fit"]["result"]["files"], model["files"], "model assets from fit cell")
    same(model["fit_execution"]["receipt_sha256"], read(stage / "jobs/fit/COMPLETE.json")["session_receipt_sha256"], "fit receipt model parent")
    tuning, source_counts = [], Counter()
    for number, configuration in enumerate(GRID, 1):
        name = f"tune-{number:02d}"; records, requests = jobs[name]
        same(recipes[name]["configuration"], configuration, "tuning recipe configuration")
        same(recipes[name]["schedule"], sorted(tune_queries), "tuning full schedule")
        predictions = []
        for key in recipes[name]["schedule"]:
            row = records[str(key)]; source_counts.update(source_bindings(row["result"], corpus, key))
            same(requests[str(key)], {"query": tune_queries[key], "configuration": configuration}, "tune query request")
            need(row["resources"]["input_bytes"] == len(canonical(tune_queries[key])) and
                 row["resources"]["output_bytes"] == len(canonical(row["result"])) and row["resources"]["examples"] == 1,
                 "Tuning logical byte/example accounting differs")
            predictions.append(row["result"]["prediction"])
        metrics = official(product("references_tune"), predictions, evaluator, output / "official" / name)
        scoring_recipe = score_recipes["score-" + name]
        same(scoring_recipe["schedule"], recipes[name]["schedule"], "scorer tune schedule")
        same(read(scoring_recipe["inputs"]["candidates"]["path"], scoring_recipe["inputs"]["candidates"]["sha256"]),
             predictions, "scorer exact tune candidates")
        same(metrics, score_records["score-" + name]["result"], "bounded scoring worker metrics")
        retained = read(stage / "tuning" / f"config-{number:02d}.json")
        rebuilt = {"configuration": configuration, "status": "completed", "metrics": metrics, "worker": str(stage / "jobs" / name),
                   "candidate_session_receipt_sha256": read(stage / "jobs" / name / "COMPLETE.json")["session_receipt_sha256"]}
        same(retained, rebuilt, "all tuning metrics and candidate identity")
        tuning.append(rebuilt)
    selection = read(stage / "tuning/selection.json")
    same(selection, {"criterion": "abstract_rationalized_f1_then_sentence_label_f1_then_smaller_k_then_higher_threshold",
                     "selected": select(tuning), "configurations": tuning}, "selection reconstruction")
    same(select(tuning)["configuration"], model["configuration"], "selected frozen configuration")
    dispositions, paired, expected_rejections = [], [], []
    for claim_id in schedule:
        row = jobs["dev"][0][str(claim_id)]; value = row["result"]; checked = checks[str(claim_id)]
        source_error = None
        try:
            source_counts.update(source_bindings(value, corpus, claim_id))
        except AuditError as error:
            source_error = str(error)
        same(jobs["dev"][1][str(claim_id)], {"query": query_lookup[claim_id], "configuration": model["configuration"]}, "dev query request")
        request = {"schema_version": 1, "benchmark_id": "scifact", "release_sha256": archive["sha256"], "claim_id": claim_id,
                   "claim_sha256": digest(query_lookup[claim_id]), "corpus_sha256": manifest["products"]["corpus"]["sha256"],
                   "model_sha256": devfreeze["model_manifest_sha256"], "configuration_sha256": digest(model["configuration"])}
        same(check_requests[str(claim_id)], request, "check dispatch request")
        result = checked["result"]
        same(result["request"], request, "checked native request")
        same(result["prediction"], value["prediction"], "paired candidate identity")
        envelope = {"request_sha256": digest(request), "prediction_sha256": digest(value["prediction"]),
                    "retrieved": value["retrieved"], "source_bindings": value["source_bindings"],
                    "producer_code_sha256": model["producer_code"]["sha256"], "resources": row["resources"]}
        same(result["envelope"], envelope, "check envelope / producer accounting identity")
        if checked["status"] == "accepted":
            need(source_error is None, "Policy admitted invalid original source binding: " + str(source_error))
            need(result["kind"] == "accepted_candidate" and result["scientific_validation"] == "not_performed" and
                 result["policy_sha256"] == devfreeze["policy_sha256"], "Accepted policy identity differs")
            reason = None
        else:
            need(result["kind"] == "rejected_candidate", "Rejected disposition identity differs")
            reason = result["message"]
            need(source_error is not None, "Native bindings passed but policy rejected claim " + str(claim_id))
            expected_rejections.append({"id": claim_id, "independent_binding_error": source_error, "retained_policy_reason": reason})
        need(row["resources"]["input_bytes"] == len(canonical(query_lookup[claim_id])) and
             row["resources"]["output_bytes"] == len(canonical(value)) and row["resources"]["examples"] == 1, "Dev product accounting differs")
        need(checked["resources"]["input_bytes"] == len(canonical(value)) and checked["resources"]["output_bytes"] == len(canonical(result)) and
             checked["resources"]["examples"] == 1, "Check product accounting differs")
        dispositions.append({"id": claim_id, "producer_status": "produced", "check_status": checked["status"], "prediction": value["prediction"], "reason": reason})
        paired.append({"id": claim_id, "prediction_sha256": digest(value["prediction"]), "check_status": checked["status"],
                       "worker_record_sha256": digest(row), "check_record_sha256": digest(checked)})
    same(read(stage / "dispositions.json"), dispositions, "all scheduled dispositions")
    same(read(stage / "checks/dispositions.json"), dispositions, "checker retained dispositions")
    same(read(stage / "checks/verification.json"), read(stage / "check-verification.json"), "retained checker verification")
    need(read(stage / "check-verification.json")["status"] == "verified", "Retained checker verification failed")
    same(read(score_recipes["score-dev"]["inputs"]["candidates"]["path"], score_recipes["score-dev"]["inputs"]["candidates"]["sha256"]),
         dispositions, "scorer exact dev dispositions")
    aggregate_result = aggregate(schedule, product("references_dev"), dispositions, corpus)
    raw = aggregate_result.pop("raw_predictions"); checked = aggregate_result.pop("checked_predictions")
    aggregate_result.update(schema_version=1, projection_policy="failure_as_empty_for_native_metrics_only",
                            strict_case_rule="exact_evidence_documents_and_labels_with_complete_native_capped_rationale",
                            official_evaluator={"commit": EVALUATOR_COMMIT, "sha256": EVALUATOR_SHA256},
                            raw_metrics=official(product("references_dev"), raw, evaluator, output / "official/dev-raw"),
                            checked_metrics=official(product("references_dev"), checked, evaluator, output / "official/dev-checked"))
    same(read(stage / "evaluation.json"), aggregate_result, "complete primary evaluation reconstruction")
    same(score_records["score-dev"]["result"], aggregate_result, "bounded final scoring reconstruction")
    strata = component_strata(claims, product("references_dev"), aggregate_result["case_results"],
                              read(product_proofs["split"]["path"], product_proofs["split"]["sha256"]))
    retrieval = retrieval_coverage(product("references_dev"), {
        claim_id: [item["doc_id"] for item in jobs["dev"][0][str(claim_id)]["result"]["retrieved"]]
        for claim_id in schedule})
    for field in ("counts", "rates", "raw_metrics", "checked_metrics"): same(report[field], aggregate_result[field], "report primary " + field)
    primary_panels["fit_setup"] = resource_panel(list(jobs["fit"][0].values()))
    primary_panels["tuning_setup"] = resource_panel([jobs[name][0]["setup"] for name in names[1:-1]])
    primary_panels["tuning_inference"] = resource_panel([record for name in names[1:-1] for key, record in jobs[name][0].items() if key != "setup"])
    primary_panels["dev_setup"] = resource_panel([jobs["dev"][0]["setup"]])
    primary_panels["dev_inference"] = resource_panel([row for key, row in jobs["dev"][0].items() if key != "setup"])
    primary_panels["dev_checks"] = resource_panel(list(checks.values()))
    primary_panels["check_setup"] = resource_panel([{"resources": check_complete["setup_resources"]}])
    primary_panels["check_verification"] = resource_panel([{"resources": check_complete["verification_resources"]}])
    primary_panels["tuning_scoring"] = resource_panel([row for name, row in score_records.items() if name != "score-dev"])
    primary_panels["dev_scoring"] = resource_panel([score_records["score-dev"]])
    controller = report["controller_costs"]
    need(all(type(row[k]) in (int, float) and math.isfinite(row[k]) and row[k] >= 0 for row in controller for k in ("wall_seconds", "cpu_seconds")),
         "Invalid controller measurements")
    need(report["elapsed_seconds"] >= events[-1]["details"]["elapsed_seconds"] > 0, "Overall elapsed timing differs")
    (output / "paired-candidates.json").write_bytes(canonical(paired) + b"\n")
    (output / "rebuilt-evaluation.json").write_bytes(canonical(aggregate_result) + b"\n")
    (output / "source-class-strata.json").write_bytes(canonical(strata) + b"\n")
    (output / "retrieval-coverage.json").write_bytes(canonical(retrieval) + b"\n")
    return {"stage": str(stage), "stage_receipt_sha256": expected_receipt, "scheduled": len(schedule),
            "all_primary_aggregates_match": True, "counts": aggregate_result["counts"], "rates": aggregate_result["rates"],
            "raw_metrics": aggregate_result["raw_metrics"], "checked_metrics": aggregate_result["checked_metrics"],
            "configuration": model["configuration"], "resource_panels": primary_panels,
            "by_native_reference_status": strata["by_native_reference_status"],
            "dev_source_component_count": len(strata["by_source_component"]),
            "retrieval_coverage": {key: value for key, value in retrieval.items() if key != "per_case"},
            "resource_scope": "measured_cell_time_and_logical_primary_product_bytes_not_physical_disk_IO; process_lifetime_peaks_are_maxima_not_sums",
            "controller_costs": {"operations": len(controller), "wall_seconds_sum": sum(x["wall_seconds"] for x in controller),
                                 "cpu_seconds_sum": sum(x["cpu_seconds"] for x in controller)},
            "runtime_proofs": runtime, "original_source_bindings_checked": dict(source_counts),
            "independently_explained_rejections": expected_rejections,
            "paired_candidate_count": len(paired), "outcome_sha256": file_hash(stage / "evaluation.json")["sha256"],
            "provider_spend_usd": 0, "limitations": ["No independent biological adjudication or private-test claim.",
            "Managed Python IO audit is not an OS sandbox; frozen hashes do not attest every host component.",
            "Controller time fields are retained measurements; rebuilding sums cannot independently measure past execution.",
            "Source-invalid rejected candidates remain in all scheduled denominators; unexplained policy disagreement fails reconstruction."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--expected-receipt-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    result = reconstruct(arguments.stage, arguments.expected_receipt_sha256, arguments.output)
    print(json.dumps({"status": result["status"], "scheduled": result["scheduled"], "output": str(arguments.output)}))
