"""Post hoc audit: code metadata, public aggregate tables, fictional probes only.

Never reads benchmark answers, human responses, source data or candidate outputs.
Writes only a fresh comparative-audit cache directory. Not a study rerun.
"""
from __future__ import annotations
import ast
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data/cache/comparative-audit-20261102/pipeline-attempt-01"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def write(name, value):
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")

def inventory():
    paths = subprocess.check_output(["git", "ls-files", "tools"], cwd=ROOT, text=True).splitlines()
    records, groups = [], defaultdict(list)
    for name in paths:
        path = ROOT / name
        if path.suffix not in (".py", ".ps1"):
            continue
        raw = path.read_bytes()
        source = raw.decode("utf-8-sig")
        row = dict(path=name, bytes=len(raw), lines=len(source.splitlines()), sha256=sha(raw), language=path.suffix)
        if path.suffix == ".py":
            tree = ast.parse(source, filename=name)
            functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
            row.update(functions=len(functions), ast_parsed=True, imports=sorted({node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}))
            for node in functions:
                if node.end_lineno - node.lineno < 8:
                    continue
                groups[sha(ast.dump(node, include_attributes=False).encode())].append(dict(path=name, name=node.name, line=node.lineno, lines=node.end_lineno-node.lineno+1))
        records.append(row)
    summary = {suffix: dict(files=sum(r["language"] == suffix for r in records), lines=sum(r["lines"] for r in records if r["language"] == suffix)) for suffix in (".py", ".ps1")}
    duplicates = [rows for rows in groups.values() if len({r["path"] for r in rows}) > 1]
    write("tool-inventory.json", dict(summary=summary, files=records, exact_ast_function_duplicate_groups=duplicates,
        caveat="Exact AST matches are inventory leads, not proof of removable redundancy. Frozen/versioned copies and independent checkers must retain identity."))
    return summary

def descriptive():
    pinned = {}
    def table(name):
        path = ROOT / "paper/results/tables" / (name + ".csv")
        raw = path.read_bytes()
        pinned[path.relative_to(ROOT).as_posix()] = dict(sha256=sha(raw), bytes=len(raw))
        return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    missing, native = table("native_missingness"), table("native_case_results")
    controls, resources = table("constructed_control_verdicts"), table("resource_phases")
    schedule, operation = table("output_schedule"), table("native_operation_resources")
    stages = Counter(r["first_failure_stage"] for r in controls if r["truth"] == "INVALID" and r["policy"] == "FULL")
    policy = {p: {r["scenario_id"]: r for r in controls if r["policy"] == p} for p in ("FULL", "WITHOUT_WRAPPER", "WIRE_ONLY")}
    null_hist = Counter(int(r["measurement_null"]) for r in missing)
    total_slots = sum(int(r["measurement_requested"]) for r in missing)
    answerable = sum(int(r["measurement_answerable"]) for r in missing)
    phases = {r["phase"]: r for r in resources}
    prod = float(phases["producer_total"]["wall_seconds"])
    verification = float(phases["amortized_source_verification"]["wall_seconds"])
    generation = float(phases["native_generation_pairs"]["wall_seconds"])
    scoring = float(phases["native_scoring"]["wall_seconds"])
    new = dict(
        status="POST_HOC_DESCRIPTIVE_AUDIT_NOT_NEW_EXPERIMENT", input_pins=pinned,
        measurement_availability=dict(units=len(missing), requested=total_slots, answerable=answerable,
            available_fraction=answerable/total_slots, nulls=total_slots-answerable,
            units_by_null_count=dict(sorted(null_hist.items())), complete_units=null_hist[0], incomplete_units=len(missing)-null_hist[0],
            independent_studies="not_established", broader_exposure=Counter(r["other_exposure"] for r in missing)),
        threshold_geometry={str(n): {str(t): next(k for k in range(n+1) if k/n >= t) for t in (.6,.8,1.)} for n in (2,3,4)},
        guard_attribution=dict(full_first_rejection=dict(stages),
            admitted_when_only_G2_is_removed=[k for k in policy["FULL"] if policy["FULL"][k]["verdict"]=="rejected" and policy["WITHOUT_WRAPPER"][k]["verdict"]=="admitted"],
            additionally_admitted_when_G1_G3_and_exactness_are_removed=[k for k in policy["FULL"] if policy["WITHOUT_WRAPPER"][k]["verdict"]=="rejected" and policy["WIRE_ONLY"][k]["verdict"]=="admitted"],
            invalid_schema_passing=sum(r["truth"]=="INVALID" and r["schema_status"]=="pass" for r in policy["FULL"].values()),
            warning="Nested policies identify G2 incremental contribution on two exposed fixtures; the remaining five joint changes do not independently estimate each guard's causal value or prevalence."),
        coverage_error_contrasts=[{k:r[k] for k in ("scenario_id", "measurement_coverage", "core_exact_report", "full_source_admitted", "full_verified_exact", "measurement_completion")} for r in policy["FULL"].values() if r["scenario_id"] in ("C04","F03","F04","F05","F06","F07")],
        resource_decomposition=dict(producer_wall_seconds=prod, verification_wall_seconds=verification,
            verification_fraction=verification/prod, shared_generation_seconds=generation, native_scoring_seconds=scoring,
            remaining_producer_seconds=prod-verification-generation-scoring,
            ideal_ceiling_speedup_if_generation_and_scoring_cost_zero=prod/(prod-generation-scoring),
            ideal_ceiling_speedup_if_source_verification_cost_zero=prod/(prod-verification),
            logical_hash_bytes_per_frozen_unique_source_byte=int(phases["producer_total"]["logical_completed_hash_bytes"])/2866248239,
            original_byte_denominator_source="paper/revisions/20261102/manuscript.md line 59; frozen 137-source frame",
            independent_audit_wall_seconds=float(phases["independent_source_audit"]["wall_seconds"]),
            physical_io_bytes="unknown", hash_amplification_warning="Logical rehash byte ratio; not physical disk I/O, a cache benchmark, or measured attainable speedup.",
            zero_literal_scoring_times=sum(float(r["literal_scoring_wall_seconds"])==0 for r in operation),
            zero_abstain_scoring_times=sum(float(r["abstain_scoring_wall_seconds"])==0 for r in operation)),
        output_accounting=dict(outputs=len(schedule), terminal_counts=dict(Counter(r["terminal"] for r in schedule)),
            native_output_count=len(native), warning="38 outputs and 90 repeated policy decisions are not 90 independent experimental units."),
        inference="No confidence intervals, tests, resampling or independent-study claims. Inputs already exposed; computed quantities are post hoc descriptive only.")
    write("descriptive-analysis.json", new)
    return new

def probes():
    results = []
    fixture = OUT / "fictional-transport"
    (fixture / "raw").mkdir(parents=True)
    (fixture / "manifests/receipts").mkdir(parents=True)
    payload=b"PAR1fictionalPAR1"
    (fixture / "raw/example.parquet").write_bytes(payload)
    queue=dict(receipt_id="receipt-example", dataset_id="ot_target", release_id="25.09", relative_path="raw/example.parquet",
        url="https://example.invalid/fictional.parquet", expected_bytes=len(payload), planning_upper_bytes=100, format="parquet")
    (fixture / "queue.json").write_text(json.dumps(dict(batch_id="fictional",files=[queue])), encoding="utf-8")
    receipt={**queue, "status":"completed", "bytes":len(payload), "sha256":sha(payload)}
    receipt_path=fixture / "manifests/receipts/receipt-example.json"
    receipt_path.write_text(json.dumps(receipt),encoding="utf-8")
    for name, wrong, sentinel in (("valid",False,False),("wrong-dataset",True,False),("existing-report",False,True),("receipt-output-alias",False,False)):
        report=receipt_path if name=="receipt-output-alias" else fixture/(name+".json")
        receipt_path.write_text(json.dumps({**receipt, "dataset_id":"wrong"} if wrong else receipt),encoding="utf-8")
        receipt_before=receipt_path.read_bytes()
        (fixture/(name+".receipt-before.json")).write_bytes(receipt_before)
        if sentinel: report.write_bytes(b"preserve-this-prior-report\n")
        before=sha(report.read_bytes()) if sentinel else None
        run=subprocess.run(["pwsh","-NoProfile","-File",str(ROOT/"tools/data/Test-DownloadBatch.ps1"),"-QueuePath",str(fixture/"queue.json"),"-DataRoot",str(fixture),"-OutputPath",str(report)],capture_output=True,text=True,timeout=30)
        (fixture/(name+".stdout.txt")).write_text(run.stdout,encoding="utf-8")
        (fixture/(name+".stderr.txt")).write_text(run.stderr,encoding="utf-8")
        result=json.loads(report.read_text(encoding="utf-8-sig"))
        results.append(dict(probe=name, exit_code=run.returncode, reported_complete=result["complete"], sentinel_before_sha256=before,
            final_report_sha256=sha(report.read_bytes()), sentinel_overwritten=bool(sentinel and before != sha(report.read_bytes())),
            receipt_overwritten=receipt_path.read_bytes()!=receipt_before, raw_unchanged=(fixture/"raw/example.parquet").read_bytes()==payload))
    from tools import validate
    collision = OUT / "validation-sentinel.json"
    collision.write_text("preserve-validation-report",encoding="utf-8")
    with patch.object(validate,"structural_checks") as fake:
        try: validate.main(["--mode","core","--report",str(collision)])
        except FileExistsError: rejected=True
        else: rejected=False
        results.append(dict(probe="validator-existing-report",rejected=rejected, structural_calls=fake.call_count, sentinel_preserved=collision.read_text()=="preserve-validation-report"))
    failure=OUT/"validator-fictional-failure.json"
    buffer=io.StringIO()
    with patch.object(validate,"structural_checks",side_effect=RuntimeError("fictional structural fault")), redirect_stdout(buffer), redirect_stderr(buffer):
        code=validate.main(["--mode","core","--report",str(failure)])
    (OUT/"validator-fictional-failure.log").write_text(buffer.getvalue(),encoding="utf-8")
    results.append(dict(probe="validator-failure-retention",exit_code=code,record=json.loads(failure.read_text())))
    from tools.presentation import package_tether_review_v2 as packet
    existing=OUT/"existing.zip"
    existing.write_bytes(b"fictional-existing-archive")
    try: packet._output(ROOT,existing)
    except Exception as error: record=dict(rejected=True,exception=type(error).__name__)
    else: record=dict(rejected=False)
    results.append(dict(probe="packet-existing-output",**record,sentinel_preserved=existing.read_bytes()==b"fictional-existing-archive"))
    write("fictional-probes.json",results)
    return results

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    write("START.json",dict(started_at=datetime.now(timezone.utc).isoformat(),script_sha256=sha(Path(__file__).read_bytes()),
        head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(), scope="Public aggregate CSVs, tool code, fictional probes only"))
    summary=inventory()
    descriptive()
    results=probes()
    write("COMPLETE.json",dict(status="completed",tool_summary=summary,probe_count=len(results),failures_reproduced=[r["probe"] for r in results if r.get("sentinel_overwritten") or r.get("receipt_overwritten")]))
    print(json.dumps(dict(output=str(OUT),tool_summary=summary,probes=results),indent=2))

if __name__ == "__main__":
    main()
