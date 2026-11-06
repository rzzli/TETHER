"""Bounded final reporting check; no production imports, models or references.

This independently recounts the post hoc contingency from already scored cases
and a separately anchored source audit. It is not another answer-key scoring run.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[4]
STAGE = Path(__file__).resolve().parent
EVAL = ROOT / "data/benchmark/labbench/evaluation-20261106T011303Z-attempt01"
ASSETS = ROOT / "planning/review-assets/tether-labbench-20261106"
PROOFS = []


def read(path, expected=None):
    path = Path(path)
    size = path.stat().st_size
    assert 0 < size <= 2 * 1024 * 1024, (path, size)
    with path.open("rb") as stream:
        raw = stream.read(size + 1)
    assert len(raw) == size, str(path)
    sha = hashlib.sha256(raw).hexdigest()
    if expected is not None:
        assert sha == expected, str(path)
    PROOFS.append({"path": str(path.relative_to(ROOT)), "sha256": sha, "bytes": size})
    return raw


def obj(path, expected=None):
    return json.loads(read(path, expected))


def main(output):
    sealed = obj(EVAL / "SEALED.json", "118711b7e7552750e441380b7abf8f60b68096ae98ef3163cf96754e7423fa6f")
    assert sealed["status"] == "completed"
    generation_sha = "46acaabedd04b0f9a2410f8620f13f19f9927e5e6fc1d0437d8b29bc63cd8447"
    assert sealed["input_anchors"]["external_sealed_sha256"] == generation_sha
    evaluation = obj(EVAL / "evaluation.json", sealed["outputs"]["evaluation.json"]["sha256"])
    reconstruction = obj(ROOT / "data/benchmark/labbench/reconstruction-20261106-attempt01/RECONSTRUCTION.json", "e184cbaefa4ca767d0dcf0c55286b96ea768f624fd512d9585ec4aefe41f4fa0")
    comparison = obj(ROOT / "data/benchmark/labbench/reconstruction-comparison-20261106-attempt01/COMPARISON.json", "0374f21ca3b7b49ba6810adc7cb316f960b2050c6e76630ce611986066e429a6")
    assert comparison["status"] == "pass" and comparison["primary_evaluation_comparison"] is True
    assert comparison["generation_sealed_sha256"] == generation_sha
    doi = obj(ASSETS / "operational-audit/SOURCE-DOI-02.json", "d8bba9effebaf5d1292ea61a57b61501f8f67ed43e1bccd4d9e371a42fcf11d7")
    doi_comparison = obj(ASSETS / "operational-audit/SOURCE-DOI-COMPARISON-01.json", "8b1bf151426afe91525b8783249f28cbe421ba8fa09b82206f15a2e550ffa764")
    assert doi_comparison["status"] == "PASS"
    resources = obj(STAGE / "RESOURCE-SCOPE-02.json", "8c39c654b6711e4c03c3ab4b1a476f65ede8f7277f46a0d19b3df665122c5218")
    operational = obj(ASSETS / "operational-audit/GENERATION-FINAL-03.json", "abcd5878cb83f1e7e481239e347952c9ae207ef47cf373d59977af3f69810576")
    assert operational["generation"]["status"] == operational["collection"]["status"] == "PASS"

    rows = evaluation["case_results"]
    by_id = {row["id"]: row for row in doi["cases"]}
    assert len(rows) == len({row["id"] for row in rows}) == len(by_id) == len(doi["cases"]) == 199
    assert {row["id"] for row in rows} == set(by_id)
    totals = Counter()
    cells = {name: Counter() for name in ("annotated_doi_hit", "no_annotated_doi_hit")}
    for row in rows:
        assert row["producer_status"] == "produced" and row["check_status"] == "accepted"
        assert row["raw_answered"] == row["checked_answered"] == (not row["native_unsure"])
        assert row["raw_correct"] == row["correct_and_admitted"]
        assert not row["raw_correct"] or row["raw_answered"]
        cell = cells["annotated_doi_hit" if by_id[row["id"]]["selected_nonconflicting_hit_count"] else "no_annotated_doi_hit"]
        for counter in (totals, cell):
            counter["scheduled"] += 1
            counter["correct"] += int(row["raw_correct"])
            counter["substantive"] += int(row["raw_answered"])
            counter["incorrect_substantive"] += int(row["raw_answered"] and not row["raw_correct"])
            counter["unsure"] += int(row["native_unsure"])
            counter["operational_failure"] += int(row["producer_status"] != "produced")
    assert dict(totals) == {"scheduled": 199, "correct": 12, "substantive": 21, "incorrect_substantive": 9, "unsure": 178, "operational_failure": 0}
    for arm in ("raw_metrics", "checked_metrics"):
        assert evaluation[arm] == reconstruction[arm] == {"accuracy": 12/199, "coverage": 21/199, "precision": 12/21}
    expected_cells = {
        "annotated_doi_hit": {"scheduled": 10, "correct": 6, "substantive": 8, "incorrect_substantive": 2, "unsure": 2, "operational_failure": 0},
        "no_annotated_doi_hit": {"scheduled": 189, "correct": 6, "substantive": 13, "incorrect_substantive": 7, "unsure": 176, "operational_failure": 0},
    }
    assert cells == expected_cells
    retained_join = obj(STAGE / "SOURCE-ANSWER-CONTINGENCY-01.json")
    assert retained_join["cells"] == cells
    assert retained_join["evaluation_seal_sha256"] == PROOFS[0]["sha256"]
    assert retained_join["source_audit_sha256"] == "d8bba9effebaf5d1292ea61a57b61501f8f67ed43e1bccd4d9e371a42fcf11d7"
    assert retained_join["new_model_calls"] == retained_join["new_network_requests"] == 0
    assert retained_join["reopened_original_references"] is False

    source_counts = {
        "annotated_doi_pairs": sum(row["annotated_doi_count"] for row in by_id.values()),
        "selected_doi_pair_hits": sum(row["selected_nonconflicting_hit_count"] for row in by_id.values()),
        "retained_doi_pair_hits": sum(row["retained_nonconflicting_hit_count"] for row in by_id.values()),
        "selected_article_instances": sum(row["selected_article_count"] for row in by_id.values()),
        "retained_article_instances": sum(row["retained_article_count"] for row in by_id.values()),
        "metadata_missing_article_instances": sum(row["metadata_missing_article_count"] for row in by_id.values()),
    }
    assert source_counts == {"annotated_doi_pairs": 205, "selected_doi_pair_hits": 10, "retained_doi_pair_hits": 10, "selected_article_instances": 406, "retained_article_instances": 538, "metadata_missing_article_instances": 42}
    assert reconstruction["observed_dependence"]["observed_component_count"] == 186
    assert sum(reconstruction["observed_dependence"]["observed_component_sizes"]) == 199
    assert resources["generation"]["totals"]["measured_usage"] == {"cost_usd": 0.0, "input_tokens": 443470, "output_tokens": 34279}
    assert round(resources["scoring"]["outer_elapsed_seconds"], 3) == 882.172
    assert resources["scoring"]["outer_controller_cpu_seconds"] == 817.953125
    assert resources["generation"]["end_to_end_wall_seconds"] is None
    assert resources["generation"]["measured_marginal_admission_seconds"] is None

    report_path = ROOT / "planning/TETHER LitQA2 Native Evaluation Results 2026-11-06.md"
    report = read(report_path).decode("utf-8")
    local_links = []
    for target in re.findall(r"\]\(([^)]+)\)", report):
        target = target.strip("<>")
        if "://" in target or target.startswith("#"):
            continue
        path = (report_path.parent / target.split("#", 1)[0]).resolve()
        assert path.is_file(), str(path)
        local_links.append(str(path.relative_to(ROOT)))
    wording_findings = []
    if "broader identifier-alias\ndiagnostics agree with the independent audit" in report:
        wording_findings.append("Alias-graph independence is overstated: only DOI-pair/question-hit counts were independently reproduced.")
    if "The decisive passage and its interpretation remain separate bottlenecks." in report:
        wording_findings.append("Decisive-passage and interpretation bottlenecks are hypotheses, not identified causes from this unadjudicated join.")
    assert "RESOURCE-SCOPE-02.json" in report
    result = {
        "schema_version": 1, "status": "PASS" if not wording_findings else "PASS_NUMBERS_WORDING_CORRECTIONS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "Anchored aggregate/case-outcome recount and report consistency; not a new full source/model replay or answer-key reconstruction",
        "input_proofs": PROOFS, "counts": dict(totals), "contingency": cells,
        "source_counts": source_counts, "metrics": evaluation["raw_metrics"],
        "local_links_checked": local_links, "wording_findings": wording_findings,
        "reference_answer_files_opened": False, "new_model_calls": 0, "new_network_calls": 0,
        "production_sources_changed": False,
        "limitations": [
            "Same-candidate admission cannot increase all-scheduled correct yield; every actual candidate passed.",
            "The independently reproduced source counts do not revalidate the primary alias graph or semantic entailment.",
            "The contingency is post hoc, unadjusted and noncausal; 186 observed groups are not an independent sample count.",
            "Generation end-to-end monotonic time, marginal admission cost, GPU memory and total economic cost remain unmeasured.",
            "Scientific qualification is not established by completed measurement and reproducible counting.",
        ],
    }
    with Path(output).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "output": str(output), "sha256": hashlib.sha256(Path(output).read_bytes()).hexdigest()}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output)
