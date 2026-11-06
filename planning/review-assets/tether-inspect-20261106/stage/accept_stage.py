"""Root closure checks over already sealed BG05 results; no execution or retry."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[4]
STAGE = ROOT / "planning/review-assets/tether-inspect-20261106"
ARMS = ("bare_independent", "bare_tether", "inspect")
RUNTIME_FREEZE_SHA = "532b396ae05de2cdb07531898e1c0b72c3d38a557cee5c6fa5f6c70bb342a7b5"
RUNTIME_SEAL_SHA = "92d8f5754a2e119844df01964103c7f1f09d71e5bee5e70d6cec3ab1b344158f"
RUNTIME_PREPARATION_SHA = "b17fdfba429a913cb5a12bd1d1c5e0388031066ed45d7e93fca6c931fa55077c"
PRIMARY_SEAL_SHA = "d0ea739f5e4cf004cb37802df3ffe25dcf97e1756c0ca0a1c52293a147bf1f9c"
PRIMARY_RECONSTRUCTION_SHA = "33720734fb1132fdd91a215f4bc6497d540c0e2ec56b382f859bb6c9e6683ce6"


def read(path: Path, expected_sha256=None):
    def unique(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise ValueError(f"duplicate JSON key: {key}")
            obj[key] = value
        return obj
    size = path.stat().st_size
    if size > 16 * 1024 * 1024:
        raise ValueError(f"unexpected report size: {path}")
    with path.open("rb") as stream:
        payload = stream.read(size + 1)
    if len(payload) != size:
        raise ValueError(f"report changed while reading: {path}")
    if expected_sha256 is not None and hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError(f"consumed report hash differs: {path}")
    return json.loads(payload, object_pairs_hook=unique)


def proof(path: Path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {"path": str(path), "bytes": size, "sha256": digest.hexdigest()}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_runtime_review(review, runtime, freeze_sha, seal_sha, preparation_sha):
    require(review["status"] == "PASS", "Runtime reconstruction did not pass")
    require(review["freeze_sha256"] == freeze_sha and review["stage_seal_sha256"] == seal_sha
            and review["preparation_sha256"] == preparation_sha, "Runtime reconstruction anchors differ")
    require(review["automatic_redispatch"] is False and review["provider_cost_usd"] == 0,
            "Runtime retry/spending boundary differs")
    rows = review["logical_dispositions"]
    require(len(rows) == len({row["id"] for row in rows}) == 19, "Runtime reconstruction denominator differs")
    require({row["id"]: row["status"] for row in rows} ==
            {row["id"]: row["status"] for row in runtime["case_dispositions"]}, "Runtime dispositions contradict sealed result")
    require(review["status_counts"] == dict(Counter(row["status"] for row in rows)), "Runtime status totals contradict rows")
    ordinary = review["ordinary"]
    require(ordinary["status"] == "PASS" and ordinary["scheduled"] == ordinary["expected_fields_matched"] == 16,
            "Ordinary witness reconstruction incomplete")
    require(review["IX06"]["status"] == "PASS" and review["IX06"]["provider_dispatches"] ==
            review["IX06"]["unresolved_calls"] == 1, "Interruption reconstruction differs")
    require(review["IX08"]["status"] == "PASS" and review["IX08"]["owners"] ==
            review["IX08"]["provider_dispatches"] == 1 and review["IX08"]["native_workers"] == 2,
            "Ownership reconstruction differs")


def validate_coverage(coverage, matrix, primary_sha, runtime_sha, primary_seal, runtime_seal, runtime_statuses):
    require(coverage["schema_version"] == 1 and coverage["status"] == "complete_with_declared_gaps",
            "Coverage still pending or failed")
    require(coverage["full_production_runtime_equivalence"] is False and coverage["scientific_validation"] is False
            and bool(coverage["remaining_gaps"]), "Coverage overstates qualified scope")
    original = {row["id"]: row for row in matrix["obligations"]}
    rows = coverage["obligations"]
    require(len(rows) == len(original) == 27 and {row["id"] for row in rows} == set(original),
            "Coverage obligation denominator differs")
    evidence = coverage["evidence"]
    require(evidence["primary_reconstruction"]["sha256"] == primary_sha
            and evidence["runtime_reconstruction"]["sha256"] == runtime_sha
            and evidence["primary_stage_seal_sha256"] == primary_seal
            and evidence["runtime_stage_seal_sha256"] == runtime_seal, "Coverage evidence anchors differ")
    runtime_rows = coverage["runtime_cases"]
    require(len(runtime_rows) == len({row["id"] for row in runtime_rows}) == len(runtime_statuses),
            "Coverage runtime denominator differs")
    require({row["id"]: row["actual_status"] for row in runtime_rows} == runtime_statuses
            and all(row["independent_check"] == "PASS" for row in runtime_rows),
            "Coverage runtime statuses contradict independent reconstruction")
    require(coverage["runtime_status_counts"] == dict(Counter(runtime_statuses.values())), "Coverage runtime totals differ")
    for row in rows:
        require(row["archive_result_status"] == "finite_archive_conformance_pass", "Unfinished archive obligation")
        expected_per_arm = len(original[row["id"]]["frozen_case_ids"])*3
        actual = row["archive_results"]
        require(actual["scheduled_cells"] == actual["full_conformance"] == expected_per_arm*3,
                "Obligation archive totals differ")
        require(set(actual["by_arm"]) == set(ARMS) and all(v["scheduled_cells"] == v["full_conformance"] == expected_per_arm
                for v in actual["by_arm"].values()), "Obligation arm totals differ")
        controls = row["runtime_control_ids"]
        require(len(controls) == len(set(controls)) and set(controls) <= set(runtime_statuses), "Unknown runtime obligation controls")
        expected_status = "bounded_witness_reconstruction_pass" if controls else "archive_only_no_live_schema_equivalence_claim"
        require(row["runtime_result_status"] == expected_status, "Runtime obligation status differs")
        source_hashes = {item["sha256"] for item in row["actual_result_evidence"]}
        require(primary_sha in source_hashes and (not controls or runtime_sha in source_hashes), "Obligation lacks result evidence")
        if controls:
            outcomes = row["runtime_control_outcomes"]
            require(len(outcomes) == len(controls) and {item["id"]: item["actual_status"] for item in outcomes} ==
                    {ident: runtime_statuses[ident] for ident in controls}
                    and all(item["independent_check"] == "PASS" for item in outcomes), "Obligation runtime outcomes differ")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runtime-review", type=Path, required=True)
    parser.add_argument("--runtime-review-sha256", required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--coverage-sha256", required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    assertions = []

    def check(condition, name):
        if not condition:
            raise AssertionError(name)
        assertions.append(name)

    pinned = {
        ROOT / "data/benchmark/tether-inspect-20261106-attempt01/run/SEALED.json": "d0ea739f5e4cf004cb37802df3ffe25dcf97e1756c0ca0a1c52293a147bf1f9c",
        ROOT / "data/benchmark/tether-inspect-20261106-attempt01/freeze/FROZEN.json": "dd2e5e3d07cac7e966a02bff34b9b2e2fb1ea30507d6d861630d76b57244e6b4",
        ROOT / "data/cache/tether-inspect-runtime-witnesses-20261106-attempt01/runtime-stage/SEALED.json": "92d8f5754a2e119844df01964103c7f1f09d71e5bee5e70d6cec3ab1b344158f",
        ROOT / "data/cache/tether-inspect-runtime-witnesses-20261106-attempt01/freeze/FROZEN.json": "532b396ae05de2cdb07531898e1c0b72c3d38a557cee5c6fa5f6c70bb342a7b5",
        STAGE / "reconstruction/actual01/RECONSTRUCTION.json": "33720734fb1132fdd91a215f4bc6497d540c0e2ec56b382f859bb6c9e6683ce6",
        STAGE / "reconstruction/actual01/SUMMARY-02.json": "dfe30cea88aeeb0c92656862ca1767617089d7011e840a9fb4da799051b23e97",
        STAGE / "stage/POSTFLIGHT-EXACT-INVENTORY-01.json": "45dd026586ef7eeb305c8e1ab4999eaaec73cfde48343976b7206684134a8d8b",
    }
    pins = []
    for path, sha in pinned.items():
        p = proof(path)
        check(p["sha256"] == sha, f"external hash: {path.name} {path.parent.name}")
        pins.append(p)
    summary_path = STAGE / "reconstruction/actual01/SUMMARY-02.json"
    summary = read(summary_path, expected_sha256=pinned[summary_path])
    check(summary["status"] == "PASS" and summary["scheduled_cells"] == 981,
          "independent primary PASS / 981 scheduled")
    check(set(summary["operational_counts_by_arm"]) == set(ARMS), "All three primary arms represented")
    for arm, values in summary["operational_counts_by_arm"].items():
        check(values["scheduled"] == values["full_conformance"] == 327,
              f"{arm}: 327 complete conforming")
        check(all(values[k] == 0 for k in ("false_admission", "false_rejection", "unscored")),
              f"{arm}: no false decisions or unscored")
    runtime_root = ROOT / "data/cache/tether-inspect-runtime-witnesses-20261106-attempt01/runtime-stage"
    runtime_seal = read(runtime_root/"SEALED.json", expected_sha256=RUNTIME_SEAL_SHA)
    check(runtime_seal["freeze_sha256"] == RUNTIME_FREEZE_SHA, "Runtime seal binds frozen execution")
    runtime = read(runtime_root/"result.json", expected_sha256=runtime_seal["files"]["result.json"]["sha256"])
    check(runtime["status"] == "completed" and runtime["automatic_retry"] is False,
          "runtime completed without retries")
    cases = runtime["case_dispositions"]
    check(len(cases) == len({c["id"] for c in cases}) == 19,
          "runtime complete unique 19 logical-case denominator")
    counts = Counter(c["status"] for c in cases)
    check(counts == Counter(completed=4, budget_exhausted=3, error=9, timeout=1,
                            interrupted_unresolved=1, unexecuted=1),
          "runtime expected terminal disposition counts")
    postflight_path = STAGE / "stage/POSTFLIGHT-EXACT-INVENTORY-01.json"
    check(read(postflight_path, expected_sha256=pinned[postflight_path])["status"] == "pass",
          "independent exact postflight passed")
    runtime_review = read(args.runtime_review, expected_sha256=args.runtime_review_sha256)
    validate_runtime_review(runtime_review, runtime, RUNTIME_FREEZE_SHA, RUNTIME_SEAL_SHA, RUNTIME_PREPARATION_SHA)
    check(True, "Runtime independent PASS with all 19 dispositions, ordinary 16 and process witnesses")
    coverage = read(args.coverage, expected_sha256=args.coverage_sha256)
    primary_freeze_path = ROOT/"data/benchmark/tether-inspect-20261106-attempt01/freeze/FROZEN.json"
    primary_freeze = read(primary_freeze_path, expected_sha256=pinned[primary_freeze_path])
    matrix_path = STAGE/"policy/OBLIGATION-MATRIX.json"
    matrix = read(matrix_path, expected_sha256=primary_freeze["input_pins"][str(matrix_path)]["sha256"])
    validate_coverage(coverage, matrix, PRIMARY_RECONSTRUCTION_SHA, args.runtime_review_sha256,
                      PRIMARY_SEAL_SHA, RUNTIME_SEAL_SHA, {row["id"]: row["status"] for row in runtime_review["logical_dispositions"]})
    check(True, "All 27 obligations have anchored results and explicit production/scientific gaps")
    evidence = {item["path"]: item for row in coverage["obligations"] for item in row["actual_result_evidence"]}
    evidence.update({item["path"]: item for key, item in coverage["evidence"].items() if isinstance(item, dict) and "path" in item})
    for name, expected in evidence.items():
        path = (ROOT/name).resolve()
        check(path.is_relative_to(ROOT), "Coverage evidence remains in project")
        actual = proof(path)
        check(all(actual[k] == expected[k] for k in ("sha256", "bytes")), "Coverage evidence proof: "+path.name)
    pins.extend([proof(args.runtime_review), proof(args.coverage)])
    docs = [ROOT / "planning/TETHER Inspect Comparison Results 2026-11-06.md",
            ROOT / "reports/TETHER benchmark comparison update 2026-11-06.md"]
    links = []
    for doc in docs:
        body = doc.read_text(encoding="utf-8")
        for match in re.finditer(r"\[[^\]]*\]\((?:<([^>]+)>|([^\)]+))\)", body):
            target = match.group(1) or match.group(2)
            if target.startswith(("https://", "http://", "#")):
                continue
            target = re.sub(r":\d+$", "", target.split("#", 1)[0])
            path = (doc.parent / target).resolve()
            check(path.exists(), f"local link: {doc.name} -> {target}")
            links.append(str(path))
        pins.append(proof(doc))
    result = {"schema_version": 1, "status": "pass", "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
              "checks": assertions, "count": len(assertions), "local_links": len(links),
              "pins": pins, "runtime_dispositions": dict(counts),
              "scope": "Root acceptance of independently reconstructed finite primary comparison and retained runtime review; no new inference, full production-runtime equivalence or scientific validation."}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": "pass", "checks": len(assertions), "local_links": len(links)}))


if __name__ == "__main__":
    main()
