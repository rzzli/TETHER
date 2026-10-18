"""Recheck applicability of exposed legacy T6 reviews without promoting their ratings."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from pathlib import Path

from asof.serde import ContractError, fingerprint, read_json, sha256_file, write_json


HYPOTHESIS_FIELDS = ("target_id", "indication_id", "target_namespace_version",
    "indication_namespace_version", "intended_action", "modality", "tissue")
SCIENCE_FIELDS = ("target_id", "indication_id", "program_id", "category", "source_kind",
    "input_refs", "context", "quantitative", "method", "source_metrics", "missingness",
    "status", "polarity", "mechanism_direction", "study_id", "dependency_group",
    "features", "feature_scope", "publication_date", "publication_year")
LEGACY_PROVENANCE = "data/manifests/public/2026-10-15-ai-assisted-review.json"
LEGACY_COMBINED = "data/benchmark/gold_evidence/ai-assisted-review-20261013/reports/combined-assessments-20261015.json"
LEGACY_FORMS = "data/benchmark/gold_evidence/t6-development-review-20261012/manifest.json"


def hypothesis_key(hypothesis: dict) -> str:
    if not isinstance(hypothesis, dict) or any(k not in hypothesis for k in HYPOTHESIS_FIELDS):
        raise ContractError("Incomplete hypothesis scope")
    return fingerprint({k: hypothesis[k] for k in HYPOTHESIS_FIELDS})


def pinned(root: Path, relative: str, expected: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ContractError("Pinned input escapes project root")
    if not isinstance(expected, str) or len(expected) != 64 or sha256_file(path) != expected:
        raise ContractError(f"Pinned hash mismatch: {relative}")
    return path


def source_identity(observation: dict, source: dict) -> dict:
    locator = observation["source_locator"]
    for field in ("source_id", "row_group", "row", "evidence_id", "datasource_id"):
        if locator.get(field) is None:
            raise ContractError(f"Missing original source locator: {field}")
    if locator["source_id"] != source.get("source_id"):
        raise ContractError("Source locator does not resolve")
    for field in ("dataset_id", "release_id", "sha256", "path"):
        if not source.get(field):
            raise ContractError(f"Missing parent source identity: {field}")
    return {k: source[k] for k in ("dataset_id", "release_id", "sha256", "path")} | {
        k: locator[k] for k in ("row_group", "row", "evidence_id", "datasource_id")}


def compare(old_hypothesis: dict, current_hypothesis: dict, old: dict,
            current: dict | None, old_source: dict, current_source: dict | None) -> dict:
    """Classify exact provenance and scientific applicability, not review correctness."""
    old_key, current_key = hypothesis_key(old_hypothesis), hypothesis_key(current_hypothesis)
    old_identity = source_identity(old, old_source)
    current_identity = source_identity(current, current_source) if current is not None else None
    if current is not None and current["observation_id"] != old["observation_id"]:
        raise ContractError("Comparison joins different observation IDs")
    changed_fields = [] if current is None else [k for k in SCIENCE_FIELDS
        if fingerprint(old.get(k)) != fingerprint(current.get(k))]
    statement_changed = current is not None and old["statement"] != current["statement"]
    if old_key != current_key:
        status, reason = "hypothesis_changed", "Target/disease namespace, identifier, action, modality or tissue changed"
    elif current is None:
        status, reason = "unmatched", "Observation ID absent from current canonical source packets"
    elif old_identity != current_identity:
        status, reason = "source_version_changed", "Raw source dataset/release/hash/path/physical row identity changed"
    elif statement_changed:
        status, reason = "same_source_changed_statement", "Same original source row; normalized assertion wording changed"
    elif changed_fields:
        status, reason = "same_statement_changed_context", "Same source and assertion; scientific context or normalization changed"
    else:
        status, reason = "exact_match", "Same hypothesis, original source row, assertion and scientific normalization"
    return {"applicability": status, "reason": reason,
        "old_hypothesis_fingerprint": old_key, "current_hypothesis_fingerprint": current_key,
        "old_source_identity": old_identity, "current_source_identity": current_identity,
        "old_source_row_sha256": old["method"]["parameters"].get("source_row_sha256"),
        "current_source_row_sha256": current["method"]["parameters"].get("source_row_sha256") if current else None,
        "old_observation_fingerprint": fingerprint(old),
        "current_observation_fingerprint": fingerprint(current) if current else None,
        "old_statement_sha256": hashlib.sha256(old["statement"].encode("utf-8")).hexdigest(),
        "current_statement_sha256": hashlib.sha256(current["statement"].encode("utf-8")).hexdigest() if current else None,
        "statement_changed": statement_changed, "changed_scientific_fields": changed_fields,
        "new_assessment_required": True, "copied_ratings": False,
        "reuse_scope": "exposed_development_feedback_only",
        "independent_gold": False}


def crosswalk(root: Path) -> tuple[dict, dict]:
    """Verify retained pins and compare the legacy 20 claims to canonical packets."""
    root = root.resolve()
    registry_path = root / "planning/run-registry.json"
    registry = read_json(registry_path)
    entries = [e for e in registry["entries"] if e["id"] == registry["canonical_pilot_id"]]
    if len(entries) != 1 or entries[0]["state"] != "canonical":
        raise ContractError("Canonical pilot is not uniquely selected")
    canonical = entries[0]
    build_entries = [e for e in registry["entries"] if e["id"] == canonical["build_id"]]
    if len(build_entries) != 1 or build_entries[0]["state"] != "canonical":
        raise ContractError("Canonical build is not uniquely selected")
    build = build_entries[0]
    pins = []
    for entry in (canonical, build):
        for item in entry["reports"]:
            pinned(root, item["path"], item["sha256"]); pins.append(item)
    provenance = read_json(root / LEGACY_PROVENANCE)
    legacy_pins = {v["path"]: v["sha256"] for v in provenance["inputs_and_retained_artifacts"]}
    combined = read_json(pinned(root, LEGACY_COMBINED, legacy_pins[LEGACY_COMBINED]))
    pins.append({"path": LEGACY_COMBINED, "sha256": legacy_pins[LEGACY_COMBINED]})
    if combined["role"] != "evaluation_only" or combined["review_status"] != "ai_reviewed_unadjudicated":
        raise ContractError("Unexpected legacy review qualification")
    form_manifest = read_json(pinned(root, LEGACY_FORMS, legacy_pins[LEGACY_FORMS]))
    pins.append({"path": LEGACY_FORMS, "sha256": legacy_pins[LEGACY_FORMS]})
    form_dir = (root / LEGACY_FORMS).parent
    blank_forms = {}
    for item in form_manifest["files"]:
        path = (form_dir / item["path"]).relative_to(root).as_posix()
        blank_forms[item["case_id"]] = read_json(pinned(root, path, item["sha256"]))
        pins.append({"path": path, "sha256": item["sha256"]})
    case_entries = {item["case_id"]: item for item in canonical["cases"]}
    if len(case_entries) != len(canonical["cases"]):
        raise ContractError("Duplicate canonical case ID")
    records, visited = [], set()
    for form in combined["forms"]:
        case_id = form["case"]["case_id"]
        if case_id in visited or case_id not in case_entries:
            raise ContractError("Duplicate or missing legacy/current case")
        visited.add(case_id)
        blank = blank_forms[case_id]
        if hypothesis_key(form["case"]["hypothesis"]) != form["hypothesis_fingerprint"]:
            raise ContractError("Legacy hypothesis fingerprint mismatch")
        if fingerprint(blank["case"]) != fingerprint(form["case"]):
            raise ContractError("Reviewed form case differs from frozen original")
        old_claims = {c["claim"]["claim_id"]: c["claim"] for c in blank["claims"]}
        old_run = root / "runs" / form_manifest["canonical_pilot_id"] / case_id
        old_receipt = read_json(pinned(root, (old_run / "receipt.json").relative_to(root).as_posix(), form["run_receipt_sha256"]))
        old_inputs = read_json(pinned(root, (old_run / "inputs.json").relative_to(root).as_posix(), old_receipt["outputs"]["inputs.json"]))
        pins.extend([{"path": (old_run / "receipt.json").relative_to(root).as_posix(), "sha256": form["run_receipt_sha256"]},
            {"path": (old_run / "inputs.json").relative_to(root).as_posix(), "sha256": old_receipt["outputs"]["inputs.json"]}])
        old_sources = {s["source_id"]: s for s in old_inputs["snapshot"]["sources"]}
        case_entry = case_entries[case_id]
        run = root / case_entry["path"]
        receipt_path = pinned(root, (run / "receipt.json").relative_to(root).as_posix(), case_entry["receipt_sha256"])
        receipt = read_json(receipt_path)
        for name, digest in (receipt["outputs"] | receipt.get("auxiliary_outputs", {})).items():
            pinned(root, (run / name).relative_to(root).as_posix(), digest)
            pins.append({"path": (run / name).relative_to(root).as_posix(), "sha256": digest})
        inputs = read_json(run / "inputs.json")
        current_sources = {s["source_id"]: s for s in inputs["snapshot"]["sources"]}
        needed = {c["claim"]["evidence"]["observation"]["observation_id"] for c in form["claims"]}
        matches, packet_pins, seen = {}, [], set()
        for artifact in inputs["snapshot"]["artifacts"]:
            packet_relative = (Path(build["path"]) / case_id / artifact["path"]).as_posix()
            packet = read_json(pinned(root, packet_relative, artifact["sha256"]))
            packet_pins.append({"path": packet_relative, "sha256": artifact["sha256"]})
            for obs in packet["observations"]:
                oid = obs["observation_id"]
                if oid in seen:
                    raise ContractError("Duplicate observation ID across current packets")
                seen.add(oid)
                if oid in needed:
                    matches[oid] = obs
            del packet
        for wrapper in form["claims"]:
            claim = wrapper["claim"]; cid = claim["claim_id"]
            if cid not in old_claims or fingerprint(claim) != fingerprint(old_claims[cid]):
                raise ContractError("Reviewed legacy claim differs from pinned original form")
            old = claim["evidence"]["observation"]; current = matches.get(old["observation_id"])
            old_source = old_sources[old["source_locator"]["source_id"]]
            current_source = current_sources[current["source_locator"]["source_id"]] if current else None
            row = compare(form["case"]["hypothesis"], inputs["case"]["hypothesis"], old, current, old_source, current_source)
            records.append({"legacy_claim_id": cid, "case_id": case_id,
                "observation_id": old["observation_id"], "old_hypothesis": form["case"]["hypothesis"],
                "current_hypothesis": inputs["case"]["hypothesis"], **row,
                "legacy_receipt_sha256": form["run_receipt_sha256"],
                "current_receipt_sha256": case_entry["receipt_sha256"], "current_packet_pins": packet_pins})
        pins.extend(packet_pins)
        pins.append({"path": receipt_path.relative_to(root).as_posix(), "sha256": case_entry["receipt_sha256"]})
    if len(records) != 20 or len(visited) != 10:
        raise ContractError("Expected all 20 original claims across ten cases")
    limitations = ["Current receipts, all receipt outputs, packet bytes, old original forms and legacy review bundle were rehashed.",
        "Raw biological files and receipt ancestor closure were NOT freshly rehashed; source-file identities inherit earlier source-inclusive verification.",
        "Projected row hashes can change when the normalization projection expands; raw-file hash plus physical row locator establishes inherited row identity.",
        "This crosswalk performs no scientific re-review and copies no legacy rating or answer.",
        "All ten cases are exposed development cases; exact applicability is not independent gold."]
    report = {"schema_version": 1, "kind": "legacy_t6_review_crosswalk", "role": "evaluation_only",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "canonical_pilot_id": canonical["id"],
        "legacy_run_id": form_manifest["canonical_pilot_id"], "legacy_bundle_sha256": legacy_pins[LEGACY_COMBINED],
        "registry_sha256": sha256_file(registry_path), "tool_sha256": sha256_file(Path(__file__)),
        "cases": len(visited), "claims": len(records), "counts": dict(Counter(r["applicability"] for r in records)),
        "records": records, "verified_pins": pins, "limitations": limitations,
        "scientific_validation": "not_performed", "copied_ratings": False, "independent_gold": False}
    summary = {k: v for k, v in report.items() if k not in ("records", "verified_pins")}
    summary["verified_pin_count"] = len(pins)
    summary["changed_fields_counts"] = dict(Counter(f for r in records for f in r["changed_scientific_fields"]))
    return report, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.summary.exists():
        raise ContractError("Refusing to overwrite retained crosswalk outputs")
    report, summary = crosswalk(args.root)
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "crosswalk.json", report)
    summary["report_path"] = args.output.as_posix()
    summary["report_sha256"] = sha256_file(args.output / "crosswalk.json")
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.summary, summary)
    print(f"Crosswalk retained: {report['cases']} cases / {report['claims']} claims; {report['counts']}")


if __name__ == "__main__":
    main()
