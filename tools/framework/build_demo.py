"""Regenerate small, deliberately fictional packaged fixtures. No network access."""

from __future__ import annotations

import hashlib
import argparse
import json
from pathlib import Path


def write(path: Path, document: object) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    root = parser.parse_args().output
    root.mkdir(parents=True, exist_ok=False)
    availability = {"first_public_at": "2018-01-01", "release_public_at": "2019-01-01",
                    "record_public_at": "2019-01-01", "annotation_public_at": "2019-01-01",
                    "retrieved_at": "2026-10-10", "basis": "Fictional fixture availability dates",
                    "uncertainty": "Synthetic; no historical availability is claimed"}
    case = {"schema_version": 1, "case_id": "demo-program-001", "task": "T1", "origin": "2023-01-01",
            "hypothesis": {"target_id": "DEMO:TARGET1", "indication_id": "DEMO:DISEASE1",
                           "target_namespace_version": "demo-v1", "indication_namespace_version": "demo-v1",
                           "intended_action": "inhibit", "modality": "small_molecule", "tissue": "fictional tissue",
                           "availability": dict(availability)},
            "program": {"program_id": "DEMO:PROGRAM1", "molecule_id": "DEMO:MOLECULE1",
                        "sponsor": "Fictional sponsor", "phase_at_origin": 2, "status_at_origin": "active",
                        "eligible_since": "2022-01-01", "mapping_confidence": 1.0, "trial_ids": ["DEMO:TRIAL1"],
                        "availability": {**availability, "first_public_at": "2022-01-01",
                                         "release_public_at": "2022-01-01", "record_public_at": "2022-01-01",
                                         "annotation_public_at": "2022-01-01"}},
            "endpoint": {"name": "phase_2_to_3", "horizon_months": 24}}
    observations = []
    feature_maps = {
        "genetics": {"genetic_support": 0.8, "direction_alignment": 0.6},
        "perturbation": {"perturbation_support": 0.4},
        "expression": {"expression_relevance": 0.7},
        "modality": {"modality_feasibility": 0.5},
        "literature": {"literature_support": 0.6},
        "clinical": {}, "safety": {"safety_liability": 0.2}, "pathway": {"pathway_support": 0.3}}
    for category, features in feature_maps.items():
        observations.append({
            "observation_id": f"demo-{category}-1", "target_id": "DEMO:TARGET1", "indication_id": "DEMO:DISEASE1",
            "program_id": "DEMO:PROGRAM1" if category == "clinical" else None,
            "category": category, "source_kind": "clinical" if category == "clinical" else "primary",
            "statement": f"Fictional {category} observation for workflow testing; no biological finding is asserted.",
            "status": "observed", "polarity": "uncertain", "mechanism_direction": "uncertain",
            "study_id": f"DEMO:STUDY-{category}", "dependency_group": f"demo-cohort-{category}",
            "context": {"species": "synthetic", "ancestry": "fictional", "tissue": "fictional tissue",
                        "disease_state": "fictional", "intervention": "fictional inhibition",
                        "comparator": "fictional control", "cohort_ids": [f"DEMO:COHORT-{category}"]},
            "quantitative": {"effect": 0.1, "scale": "synthetic", "standard_error": 0.05,
                             "ci_lower": 0.002, "ci_upper": 0.198, "sample_size": 100,
                             "adjusted_p_value": 0.04},
            "method": {"code_id": "synthetic-fixture", "version": "1", "parameters": {},
                       "qc_status": "passed", "limitations": ["Invented fixture; not a scientific calculation"]},
            "availability": dict(availability), "features": features})
    duplicate = json.loads(json.dumps(observations[4]))
    duplicate["observation_id"] = "demo-literature-duplicate"
    duplicate["source_kind"] = "integrated"
    observations.append(duplicate)
    missing = json.loads(json.dumps(observations[1]))
    missing.update(observation_id="demo-perturbation-unmeasured", status="not_measured", features={},
                   statement="The fictional primary-cell perturbation was not measured.")
    missing["method"]["qc_status"] = "not_run"
    observations.append(missing)
    canary = json.loads(json.dumps(observations[4]))
    canary["observation_id"] = "demo-future-record"
    canary["statement"] = "FUTURE_CANARY_SECRET_MUST_NEVER_REACH_A_SPECIALIST"
    canary["availability"]["record_public_at"] = "2024-01-01"
    observations.append(canary)
    write(root / "case.json", case)
    write(root / "evidence.json", {"schema_version": 1, "observations": observations})
    write(root / "future.json", {"future_fact": "FUTURE_ARTIFACT_SECRET_MUST_NEVER_BE_OPENED"})
    artifacts = []
    for name in ("evidence", "future"):
        dates = dict(availability)
        if name == "future":
            dates.update(release_public_at="2025-01-01", record_public_at="2025-01-01",
                         annotation_public_at="2025-01-01")
        artifacts.append({"artifact_id": f"demo-{name}", "dataset_id": "synthetic_fixture",
                          "release_id": "fixture-v1", "path": f"{name}.json",
                          "sha256": hashlib.sha256((root / f"{name}.json").read_bytes()).hexdigest(),
                          "role": "agent_evidence", "access_approved": True,
                          "temporal_classification": "verified_historical", "availability": dates,
                          "source_url": "https://example.invalid/synthetic-fixture"})
    write(root / "snapshot.json", {"schema_version": 1, "snapshot_id": "synthetic-v1",
                                  "profile": "synthetic_demo", "origin": "2023-01-01",
                                  "allow_reconstructed": False, "artifacts": artifacts})
    write(root / "scorer.json", {
        "schema_version": 1, "model_id": "synthetic-logistic-v1", "kind": "synthetic_demo",
        "feature_schema": "asof-features-v1", "aggregation": "mean_of_unique_dependency_groups_v1",
        "endpoint": "phase_2_to_3", "horizon_months": 24, "phases": [2], "modalities": ["small_molecule"],
        "intended_actions": ["inhibit"], "target_namespace_versions": ["demo-v1"],
        "indication_namespace_versions": ["demo-v1"], "training_origin_max": "2020-01-01",
        "training_label_available_max": "2022-01-01", "calibration_label_available_max": None,
        "training_manifest_sha256": hashlib.sha256(b"fictional-training-fixture").hexdigest(),
        "calibration": "none", "intercept": -1.4,
        "coefficients": {"genetic_support": 0.8, "direction_alignment": 0.4, "perturbation_support": 0.3,
                         "expression_relevance": 0.2, "modality_feasibility": 0.2,
                         "literature_support": 0.3, "safety_liability": -0.6, "pathway_support": 0.1},
        "required_features": ["genetic_support", "direction_alignment"], "missing_values": {},
        "minimum_coverage": 0.75})
    responses = {}
    for category in feature_maps:
        selected = [item["observation_id"] for item in observations if item["category"] == category
                    and item["status"] == "observed" and item["observation_id"] != "demo-future-record"]
        response = {"observation_ids": selected, "usage": {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0}}
        responses[category] = [response]
    write(root / "replay.json", {"schema_version": 1, "responses": responses})
    print(f"Wrote synthetic fixtures under {root}")


if __name__ == "__main__":
    main()

