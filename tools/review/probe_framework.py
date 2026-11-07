"""Exercise current v2 contracts using temporary fictional inputs.

The preserved planning/review-assets/framework-review-2026-10-10.json records the
old v1 findings. This utility does not rerun v1 execution or rewrite that report.
Passing probes establish software behavior, not biomedical validity.
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
from tools.history import materialize_checkpoint

from tether_engine.agents import ExtractiveBackend
from tether_engine.artifacts import verify_run, write_run
from tether_engine.chrono import load_snapshot
from tether_engine.contracts import Case, Category
from tether_engine.journal import RunJournal, inspect_run
from tether_engine.scorer import ScorerArtifact
from tether_engine.serde import ContractError, decode, fingerprint, read_json, sha256_file, write_json
from tether_engine.workflow import run_workflow


PROJECT = Path(__file__).resolve().parents[2]
FIXTURES = PROJECT / "src/tether_engine/demo/v2"
LEGACY_REPORT = PROJECT / "planning/review-assets/framework-review-2026-10-10.json"


class CaptureBackend(ExtractiveBackend):
    def __init__(self, error=None):
        self.calls = 0
        self.error = error

    def select(self, request):
        self.calls += 1
        if self.error is not None:
            raise self.error("Fictional provider failure")
        return super().select(request)


def inputs(root):
    fixture = root / "fixture"
    shutil.copytree(FIXTURES, fixture)
    case = decode(Case, read_json(fixture / "case.json"))
    model = decode(ScorerArtifact, read_json(fixture / "scorer.json"))
    store = load_snapshot(fixture / "snapshot.json", case)
    return fixture, case, model, store


def rejection(operation):
    try:
        operation()
    except ContractError as error:
        return str(error)
    return None


def report(expected, passed, **observed):
    return {"expected": expected, "passed": passed, "observed": observed}


def t6_future_program(root):
    _, case, _, store = inputs(root)
    future = replace(case.program, availability=replace(
        case.program.availability, record_public_at=date(2024, 1, 1)))
    case = replace(case, task="T6", endpoint=None, program=future)
    backend = CaptureBackend()
    error = rejection(lambda: run_workflow(case, store, backend))
    return report("Reject future T6 program information before dispatch",
                  error is not None and backend.calls == 0, calls=backend.calls, error=error)


def immutable_evidence(root):
    _, case, model, store = inputs(root)
    result = run_workflow(case, store, CaptureBackend(), model)
    values = (store.lookup("demo-genetics-1").observation.features,
              store.lookup("demo-genetics-1").observation.method.parameters,
              result.claims[0].evidence.observation.features,
              result.coverage["genetics"], result.trace[-1]["details"], result.features.values)
    rejected = 0
    for value in values:
        try:
            value["unapproved_change"] = 1
        except TypeError:
            rejected += 1
    output = root / "run"
    anchor = write_run(output, result, store, model)
    checked = verify_run(output, anchor)
    return report("Nested store, claim and finalized state remain immutable",
                  rejected == len(values) and checked["semantic_consistency"] == "verified",
                  mutation_attempts=len(values), mutations_rejected=rejected,
                  semantic_consistency=checked["semantic_consistency"])


def hypothesis_binding(root):
    _, case, _, store = inputs(root)
    original = run_workflow(case, store, CaptureBackend())
    results = []
    for changes in ({"intended_action": "activate"}, {"modality": "antibody"},
                    {"tissue": "different tissue"}):
        changed = replace(case, hypothesis=replace(case.hypothesis, **changes))
        result = run_workflow(changed, store, CaptureBackend())
        value = result.features.values["direction_alignment"]
        results.append({"changes": changes, "value": value.value,
                        "missing_reasons": value.missing_reasons,
                        "context_claims_visible": len(result.claims)})
    return report("Changed action, modality or tissue cannot reuse hypothesis features",
                  original.features.values["direction_alignment"].value is not None and
                  all(item["value"] is None and "outside_applicability" in item["missing_reasons"]
                      for item in results), cases=results)


def provider_failures(root):
    _, case, model, store = inputs(root)
    results = []
    for kind in (TimeoutError, ValueError, RuntimeError, KeyboardInterrupt):
        output = root / kind.__name__
        journal = RunJournal(output)
        backend = CaptureBackend(kind)
        try:
            result = run_workflow(case, store, backend, model, journal=journal)
            write_run(output, result, store, model, journal)
        finally:
            journal.close()
        inspection = inspect_run(output)
        checked = verify_run(output)
        results.append({"exception": kind.__name__, "calls": result.calls,
                        "status": result.status, "probability": result.prediction.probability,
                        "durable_events": inspection["durable_events"],
                        "semantic_consistency": checked["semantic_consistency"]})
    return report("Provider failures retain accounted attempts, readable journals and abstention",
                  all(item["calls"] >= 1 and item["status"] != "completed" and
                      item["probability"] is None and item["semantic_consistency"] == "verified"
                      for item in results), cases=results)


def scorer_preflight(root):
    _, case, model, store = inputs(root)
    invalid = replace(model, training_label_available_max=date(2024, 1, 1))
    backend = CaptureBackend()
    error = rejection(lambda: run_workflow(case, store, backend, invalid))
    return report("Reject invalid scorer cutoffs before dispatch",
                  error is not None and backend.calls == 0, calls=backend.calls, error=error)


def semantic_output_binding(root):
    _, case, model, store = inputs(root)
    output = root / "run"
    result = run_workflow(case, store, CaptureBackend(), model)
    write_run(output, result, store, model)
    features = read_json(output / "features.json")
    features["values"]["genetic_support"]["value"] = 0.1
    write_json(output / "features.json", features)
    receipt = read_json(output / "receipt.json")
    receipt["outputs"]["features.json"] = sha256_file(output / "features.json")
    write_json(output / "receipt.json", receipt)
    error = rejection(lambda: verify_run(output))
    return report("Reject feature/ledger inconsistency despite matching local byte hashes",
                  error is not None, error=error)


def archived_catalog_policy(root):
    fixture, case, _, _ = inputs(root)
    # Exercise the historical contract with explicitly fictional local receipts.
    # This tests policy persistence, not actual historical source availability.
    snapshot = read_json(fixture / "snapshot.json")
    snapshot["profile"] = "historical_benchmark"
    for node in snapshot["sources"]:
        path = fixture / node["path"]
        receipt_path = fixture / (node["source_id"] + ".receipt.json")
        write_json(receipt_path, {"status": "completed", "sha256": node["sha256"],
            "dataset_id": node["dataset_id"], "release_id": node["release_id"],
            "relative_path": node["path"], "bytes": path.stat().st_size,
            "fixture": "Fictional policy persistence probe; no provider acquisition"})
        node.update(receipt_path=receipt_path.name, receipt_sha256=sha256_file(receipt_path))
    write_json(fixture / "snapshot.json", snapshot)
    catalog = fixture / "catalog.json"
    policy = {"schema_version": 1, "datasets": [
        {"dataset_id": "synthetic_fixture", "roles": ["agent_evidence"]}]}
    write_json(catalog, policy)
    store = load_snapshot(fixture / "snapshot.json", case, catalog)
    result = run_workflow(case, store, CaptureBackend())
    output = root / "run"
    anchor = write_run(output, result, store, None)
    write_json(catalog, {"schema_version": 1, "datasets": [
        {"dataset_id": "synthetic_fixture", "roles": ["evaluation_only"]}]})
    checked = verify_run(output, anchor)
    archived = read_json(output / "inputs.json")["catalog_policy"]
    return report("Verify against the effective archived admission policy",
                  fingerprint(archived) == fingerprint(policy) and
                  checked["semantic_consistency"] == "verified",
                  archived_policy_matches=fingerprint(archived) == fingerprint(policy),
                  changed_external_catalog_does_not_rewrite_history=True)


def missingness_feature_contract(root):
    fixture, case, _, _ = inputs(root)
    original = read_json(fixture / "evidence.json")
    results = {}
    for status in ("absent", "access_denied"):
        packet = read_json(fixture / "evidence.json")
        packet["observations"][0] = dict(original["observations"][0], status=status, features={})
        packet["observations"][0]["method"] = dict(
            original["observations"][0]["method"], qc_status="not_run")
        write_json(fixture / "evidence.json", packet)
        snapshot = read_json(fixture / "snapshot.json")
        snapshot["artifacts"][0]["sha256"] = sha256_file(fixture / "evidence.json")
        write_json(fixture / "snapshot.json", snapshot)
        store = load_snapshot(fixture / "snapshot.json", case)
        result = run_workflow(case, store, CaptureBackend())
        feature = result.features.values["genetic_support"]
        results[status] = {"value": feature.value, "missing_reasons": feature.missing_reasons}
    return report("Preserve distinct reasons for absent versus inaccessible evidence",
                  all(item["value"] is None and status in item["missing_reasons"]
                      for status, item in results.items()), cases=results)


def new_computation_old_inputs(root):
    fixture, case, _, _ = inputs(root)
    packet = read_json(fixture / "evidence.json")
    observation = packet["observations"][0]
    observation["source_kind"] = "computed"
    observation["computed_at"] = "2026-10-10T00:00:00+00:00"
    observation["availability"]["record_public_at"] = "2026-10-10"
    write_json(fixture / "evidence.json", packet)
    snapshot = read_json(fixture / "snapshot.json")
    snapshot["artifacts"][0]["sha256"] = sha256_file(fixture / "evidence.json")
    write_json(fixture / "snapshot.json", snapshot)
    store = load_snapshot(fixture / "snapshot.json", case)
    result = run_workflow(case, store, CaptureBackend())
    value = result.features.values["genetic_support"].value
    return report("Permit later computation on completely referenced eligible old information",
                  value == 0.8, computed_at=observation["computed_at"],
                  origin_at=case.origin_at, eligible_records=len(store.query(case, Category.GENETICS)),
                  feature_value=value)


def legacy_verification(root):
    archived = root / "legacy-v1"
    materialize_checkpoint('tests/fixtures/legacy-v1', archived)
    checked = verify_run(archived, (archived / "receipt.sha256").read_text().strip())
    return report("Keep legacy byte verification without claiming v2 semantics",
                  checked["semantic_consistency"] == "unavailable_legacy_v1",
                  semantic_consistency=checked["semantic_consistency"],
                  scientific_validity=checked["scientific_validity"])


def required_probes_passed(results):
    return bool(results) and all(result.get("passed") is True for result in results.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite a retained review; choose a new output path")
    probes = {"F01_t6_future_program": t6_future_program,
              "F02_immutable_evidence": immutable_evidence,
              "F03_hypothesis_binding": hypothesis_binding,
              "F04_provider_failures": provider_failures,
              "F05_scorer_preflight": scorer_preflight,
              "semantic_output_binding": semantic_output_binding,
              "catalog_policy_archived": archived_catalog_policy,
              "missingness_preserved": missingness_feature_contract,
              "computed_input_eligibility": new_computation_old_inputs,
              "legacy_verification": legacy_verification}
    results = {}
    for name, probe in probes.items():
        with tempfile.TemporaryDirectory(prefix="tether-review-v2-") as directory:
            try:
                results[name] = probe(Path(directory))
            except Exception as error:
                results[name] = {"passed": False, "probe_error": type(error).__name__,
                                 "message": str(error)}
            results[name]["status"] = "passed" if results[name].get("passed") is True else "failed"
    report_value = {"schema_version": 2, "reviewed_at_utc": datetime.now(timezone.utc),
              "scope": "Current v2 fictional probes; no downloads, models or scientific conclusions",
              "fixture_schema_version": 2,
              "legacy_review": {"path": str(LEGACY_REPORT.relative_to(PROJECT)),
                                "sha256": sha256_file(LEGACY_REPORT) if LEGACY_REPORT.is_file() else None,
                                "meaning": "Preserved v1 historical findings; not current runtime status"},
              "source_hashes": {path.relative_to(PROJECT).as_posix(): sha256_file(path)
                                for path in sorted((PROJECT / "src/tether_engine").glob("*.py"))},
              "probes": results,
              "known_limitations": [{"area": "evaluation",
                  "status": "descriptive_only", "detail":
                  "Standalone evaluator inputs do not establish a locked, anchored benchmark cohort"}],
              "scientific_validity": "not_established"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, report_value)
    for name, result in results.items():
        print(f"{name}: passed={result.get('passed')}; error={result.get('probe_error')}")
    return 0 if required_probes_passed(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
