"""Export source-only configuration and evaluator-only hash anchors for P09.

Preparation only: no new source parsing, references, reports, model calls or
experimental execution. Historical references are read solely to hash the
declared catalog-only comparison projection. Outputs are new derived artifacts.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools/science"))
import prepare_source_validation_set as stage1
import prepare_source_validation_inputs as inputs
from asof.atomic import publish_bytes
from asof.journal import RunJournal
from asof.serde import canonical, encode, fingerprint, parse_json

ASSETS = ROOT / "planning/review-assets/preprint-p05-20261031"
NEUTRAL = ROOT / "data/derived/preprint-p05-neutral-tasks-20261101T075541Z"
REFS = ROOT / "data/benchmark/gold_evidence/preprint-p05-references-20261101T081933Z/references.json"
LEDGER = ROOT / "data/derived/preprint-p05-experiment-20261101T091345Z/ledger.json"
ANALYSIS = ROOT / "data/derived/preprint-p05-analysis-20261101T092110Z/analysis.json"
PINS = {
    "ready": (ASSETS / "EXPERIMENT-READY-v1.json", "49c2ce672356bfcfd572a7b6c963c56bd5c96e3d042a9972f2c36434ebb8de3f"),
    "ledger": (LEDGER, "b2a9727ca9ce89865b80ffe80b21a325ea6d91d8844247740ac2c2ecc9a4faa0"),
    "audit": (ASSETS / "EXPERIMENT-AUDIT-v1.json", "f10f15959f8497821115f65268808c98ae345079c7361722390a479b15506922"),
    "references": (REFS, "d6260cfaf86363a8bf7a82b8088f1a84968cc1e18dc4c9806f53b0bd3d88cd9a"),
    "analysis": (ANALYSIS, "ee9f02ea3c3692bbd8b7d63d2d2cd545cfd769ccee9ee7454b4ed00c7ac87312"),
    "neutral_seal": (NEUTRAL / "SEAL.json", "5bf827df9921a01712d9739d7d04f59e8b0aa3554a9ebc9eaf87d6e240aadace"),
}


def need(value, message):
    if not value:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def projection(reference):
    result = deepcopy(encode(reference))
    need("catalog_sha256" in result["method"], "Historical reference catalog binding is absent")
    del result["method"]["catalog_sha256"]
    return result


def historical_reference(case, case_id):
    disposition = case.get("disposition")
    need(isinstance(disposition, dict) and disposition.get("status") == "compiled" and
         disposition.get("case_id") == case_id and disposition.get("blocked_reason") is None and
         disposition.get("role") == "evaluation_only" and disposition.get("agent_visible") is False and
         disposition.get("adjudicated_gold") is False,
         "Historical reference disposition is not compiled evaluator-only evidence")
    reference = case.get("reference")
    need(isinstance(reference, dict) and fingerprint(reference) == disposition.get("reference_sha256"),
         "Historical reference differs from its compiled disposition")
    return reference


def safe_public(value):
    """Reject machine paths/secrets; source URLs and neutral identifiers are data."""
    if isinstance(value, dict):
        for key, item in value.items():
            need(not re.search(r"(?i)^(password|authorization|access_token|secret|api_key)$", key), "Secret-like public field")
            safe_public(item)
    elif isinstance(value, list):
        for item in value:
            safe_public(item)
    elif isinstance(value, str):
        need(not re.search(r"(?:(?<![A-Za-z0-9_])[A-Za-z]:[\\/]|/Users/|/home/)", value), "Machine path in public metadata")
        need(not re.search(r"(?i)(?:[?&](?:token|signature|key|x-amz-credential)=|bearer\s+[A-Za-z0-9])", value), "Credential-like public value")


def load_inputs():
    documents, proofs = {}, {}
    expected = {name: sha for name, (_, sha) in PINS.items()}
    for name, (path, sha) in PINS.items():
        need(re.fullmatch("[0-9a-f]{64}", sha) is not None, "Malformed independent byte anchor")
        raw = path.read_bytes()
        need(digest(raw) == expected[name], "Historical byte anchor differs: " + name)
        documents[name] = parse_json(raw)
        proofs[name] = dict(sha256=expected[name], bytes=len(raw), role="historical_evaluation_anchor")
    for group in ("code_sha256", "extra_code_sha256"):
        for name, sha in documents["ready"][group].items():
            need(digest((ROOT / name).read_bytes()) == sha, "Frozen P05 code changed: " + name)
    audit = documents["audit"]
    need(audit["status"] == "PASS_INDEPENDENT_EXPERIMENT_AUDIT" and not audit["unresolved_findings"] and
         audit["subject"]["ledger_sha256"] == expected["ledger"], "Historical source audit is not accepted")
    docs = stage1.pinned_documents(__import__("time").monotonic() + 60)
    routing = parse_json((NEUTRAL / "selected-case-plan.json").read_bytes())
    for item in documents["neutral_seal"]["items"]:
        raw = (NEUTRAL / item["path"]).read_bytes()
        need(digest(raw) == item["sha256"] and len(raw) == item["bytes"], "Neutral source configuration differs")
    return documents, docs, routing, proofs


def export(output):
    journal = RunJournal(output, kind="build")
    stage = "historical_anchor_validation"
    try:
        documents, docs, routing, historical = load_inputs()
        journal.append("build_stage", stage=stage, source_values_read=False)
        inventory = stage1.inventory_from_metadata(docs["frame"], docs["acquisition"])
        public_inventory = []
        for number, item in enumerate(inventory):
            receipt = item["receipt"]
            public_inventory.append(dict(
                source_id=f"original-{number:03d}", family=item["family"], dataset_id=item["dataset_id"],
                release_id=item["release_id"], relative_path=item["relative_path"], sha256=item["sha256"],
                bytes=item["bytes"], fields=item["fields"], rows=item["rows"], source_url=item["source_url"],
                role=stage1.original_role(item), receipt=dict(relative_path=Path(receipt["path"]).relative_to(stage1.RAW_ROOT).as_posix(),
                    sha256=receipt["sha256"], bytes=receipt["bytes"])))
        dataset_ids = {i["dataset_id"] for i in public_inventory}
        catalog = dict(schema_version=1, datasets=[dict(dataset_id=i["dataset_id"], roles=i["roles"])
            for i in docs["catalog"]["datasets"] if i["dataset_id"] in dataset_ids])
        need(len(catalog["datasets"]) == len(dataset_ids), "Required catalog role is absent")
        snapshot = parse_json((NEUTRAL / "source-snapshot.json").read_bytes())
        snapshot["raw_root"] = None
        cases = [{key: c[key] for key in ("case_id", "targetId", "diseaseId", "studyLocusId", "release_id", "unit_hash")}
                 for c in routing["cases"]]
        tasks = {c["case_id"]: parse_json((NEUTRAL / (c["case_id"] + ".task.json")).read_bytes()) for c in cases}
        policy = dict(schema_version=1, method="p09.source_policy.v1", cutoff=inputs.CUTOFF,
            inventory=public_inventory, expected_frame=stage1.EXPECTED, catalog=catalog, snapshot=snapshot,
            cases=cases, tasks=tasks, exposed_symbols=sorted(stage1.EXPOSED), limits=inputs.LIMITS)
        safe_public(policy)
        policy_raw = canonical(policy) + b"\n"
        journal.append("build_stage", stage="public_role_projection", files=len(public_inventory),
                       source_data_payloads_read=0, numerical_values_exported=0)
        stage = "historical_comparison_export"
        native = {}
        ledger = documents["ledger"]
        for case in cases:
            key = case["case_id"]
            old = documents["references"]["cases"][key]
            reference = historical_reference(old, key)
            need(fingerprint(reference) == ledger["subject_bindings"][key]["reference_sha256"], "Historical reference binding differs")
            native[key] = dict(task_sha256=reference["task_sha256"], historical_reference_sha256=fingerprint(reference),
                reference_projection_sha256=fingerprint(projection(reference)),
                projection_method="remove_only_method_catalog_sha256.v1", counts=ledger["native_qualification"][key])
        outputs = []
        for old in ledger["output_cells"]:
            # No raw output bytes or typed values are opened/exported. Score and
            # accounting objects hold only evaluator metadata and field counts.
            copied = {k: old[k] for k in ("cell_id", "case_id", "arm", "stratum", "terminal", "received_terminal",
                "raw_bytes", "raw_sha256", "core_score", "fact_accounting", "full_source_admitted", "full_verified_exact", "strict_exact_report")}
            if copied["core_score"] is not None:
                copied["core_score"] = deepcopy(copied["core_score"])
                del copied["core_score"]["reference_sha256"]
            outputs.append(copied)
        guards = {key: {stage: {k: v for k, v in item.items() if k in ("status", "schema_status")}
                        for stage, item in value.items()} for key, value in ledger["guards"].items()}
        decisions = [{key: old[key] for key in ("decision_id", "policy", "verdict", "first_failure_stage", "terminal", "required_stages")}
                     for old in ledger["decision_cells"]]
        bridge = dict(schema_version=1, method="p09.p05_comparison_bridge.v1", role="evaluation_only", agent_visible=False,
            source_policy_sha256=digest(policy_raw), historical_artifacts=historical,
            native=native, outputs=outputs, guards=guards, decisions=decisions,
            historical_analysis=documents["analysis"], scientific_validation="not_established",
            original_private_archive_byte_verification="not_provided_by_public_reconstruction",
            generation_parent_policy="never a generation input; compare only after output sealing")
        # Analysis execution has historical absolute paths. Export only the
        # substantive descriptive result families and pin the full old analysis.
        bridge["historical_analysis"] = {k: v for k, v in documents["analysis"].items() if k != "execution"}
        safe_public(bridge)
        publish_bytes(output / "source-policy.json", policy_raw)
        publish_bytes(output / "comparison.json", canonical(bridge) + b"\n")
        report = dict(schema_version=1, method="p09.public_bridge_export.v1", status="PREPARED_PENDING_INDEPENDENT_REVIEW",
            source_policy_sha256=digest(policy_raw), comparison_sha256=digest(canonical(bridge) + b"\n"),
            native_cases=len(native), outputs=len(outputs), decisions=len(decisions), original_files=len(public_inventory),
            original_bytes=sum(i["bytes"] for i in public_inventory), source_payloads_opened=0,
            reference_values_exported=0, raw_output_payloads_opened=0, frozen_code_unchanged=True,
            exporter_sha256=digest(Path(__file__).read_bytes()), historical_artifacts=historical,
            model_calls=0, network_calls=0, new_downloads=0, source_admission_roles=Counter(i["role"] for i in public_inventory))
        publish_bytes(output / "export-report.json", canonical(report) + b"\n")
        journal.append("build_completed", report_sha256=fingerprint(report), actual_reconstruction=False)
        return report
    except BaseException as error:
        journal.fail(error, stage)
        raise
    finally:
        journal.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.output.absolute()
    need(output.is_relative_to(ROOT / "data/cache"), "Preparation stays in ignored workspace cache")
    print(json.dumps(export(output), indent=2))


if __name__ == "__main__":
    main()
