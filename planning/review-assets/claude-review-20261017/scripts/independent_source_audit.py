"""Independent source audit (review script; does not import project code).

1. Recount (targetId, diseaseId)-matched evidence rows by scanning every selected evidence Parquet file.
2. Trace random observations back to their raw Parquet row and compare projected fields.
"""
import json
import math
import random
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq

ROOT = Path(r"D:\Projects\drug_target_agents")
RAW = Path(r"E:\projects_data\drug_target_agents_data")
BUILD = ROOT / "data/derived/literature-coverage-20261017T082208Z"
inspection = json.loads((BUILD / "inspection.json").read_bytes().decode("utf-8-sig"))
sources = {f["source"]["source_id"]: f for f in inspection["files"]}
evidence_files = [f for f in inspection["files"] if f["source"]["dataset_id"] == "ot_evidence"]
report = json.loads((BUILD / "build-report.json").read_bytes().decode("utf-8-sig"))

# Case pairs from case.json
cases = {}
for c in report["cases"]:
    case = json.loads((BUILD / c["case_id"] / "case.json").read_text(encoding="utf-8"))
    hyp = case["hypothesis"]
    cases[c["case_id"]] = (hyp["target_id"], hyp["indication_id"], c["observations"])
pairs = {(t, d) for t, d, _ in cases.values()}
print("pairs:", len(pairs), "cases:", len(cases), file=sys.stderr)


def scan(entry):
    path = RAW / entry["source"]["path"].replace("/", "\\")
    pf = pq.ParquetFile(path)
    found = []
    physical = 0
    for batch in pf.iter_batches(columns=["id", "targetId", "diseaseId", "datasourceId"], batch_size=262144):
        physical += batch.num_rows
        tbl_t = batch.column("targetId")
        mask = None
        for t in {p[0] for p in pairs}:
            m = pc.equal(tbl_t, t)
            mask = m if mask is None else pc.or_(mask, m)
        sub = batch.filter(mask)
        if sub.num_rows:
            ids = sub.column("id").to_pylist()
            ts = sub.column("targetId").to_pylist()
            ds = sub.column("diseaseId").to_pylist()
            dss = sub.column("datasourceId").to_pylist()
            for i, t, d, s in zip(ids, ts, ds, dss):
                if (t, d) in pairs:
                    found.append((t, d, i, s))
    return physical, found


started = time.monotonic()
total_physical = 0
matches = []
with ThreadPoolExecutor(max_workers=4) as pool:
    for physical, found in pool.map(scan, evidence_files):
        total_physical += physical
        matches.extend(found)
print(f"scan done in {time.monotonic()-started:.0f}s", file=sys.stderr)

by_pair = defaultdict(list)
for t, d, i, s in matches:
    by_pair[(t, d)].append(i)
recount = {}
for pair, ids in by_pair.items():
    recount[f"{pair[0]}|{pair[1]}"] = {"rows": len(ids), "distinct_ids": len(set(ids))}

comparison = []
for case_id, (t, d, n_obs) in cases.items():
    got = recount.get(f"{t}|{d}", {"rows": 0, "distinct_ids": 0})
    comparison.append({"case": case_id, "observations": n_obs, "raw_rows": got["rows"],
                       "raw_distinct_ids": got["distinct_ids"], "equal": n_obs == got["distinct_ids"]})

# ---- trace sample ----
random.seed(20261017)
trace_results = {"checked": 0, "mismatches": [], "fields_compared": 0}


def norm(v):
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def close(a, b):
    a, b = norm(a), norm(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-12)
    return a == b


def to_py(v):
    return v  # pyarrow to_pylist already yields python objects


unique_cases = {}
for case_id in cases:
    unique_cases.setdefault(cases[case_id][:2], case_id)  # one case per pair (shared evidence repeats)
for (t, d), case_id in unique_cases.items():
    paths = sorted((BUILD / case_id).glob("evidence*.json"))
    obs = []
    for p in paths:
        obs.extend(json.loads(p.read_text(encoding="utf-8"))["observations"])
    sample = random.sample(obs, min(30, len(obs)))
    for o in sample:
        loc = o["source_locator"]
        entry = sources[loc["source_id"]]
        path = RAW / entry["source"]["path"].replace("/", "\\")
        pf = pq.ParquetFile(path)
        cols = list(o["source_metrics"].keys())
        available = [c for c in cols if c in pf.schema_arrow.names]
        table = pf.read_row_group(loc["row_group"], columns=list(set(available + ["id", "targetId", "diseaseId", "datasourceId"])))
        row = {name: table.column(name)[loc["row"]].as_py() for name in table.column_names}
        trace_results["checked"] += 1
        if row["id"] != loc["evidence_id"] or row["targetId"] != o["target_id"] or row["diseaseId"] != o["indication_id"] \
                or row["datasourceId"] != loc["datasource_id"]:
            trace_results["mismatches"].append({"obs": o["observation_id"], "kind": "identity"})
            continue
        for c in available:
            trace_results["fields_compared"] += 1
            if not close(row[c], o["source_metrics"][c]):
                # struct/list values may differ in representation; compare json forms
                if json.dumps(row[c], sort_keys=True, default=str) != json.dumps(o["source_metrics"][c], sort_keys=True, default=str):
                    trace_results["mismatches"].append({"obs": o["observation_id"], "kind": "field", "field": c})
        score = row.get("score")
        if score is not None and f"provider evidence score {score}" not in o["statement"]:
            # statement may format scores differently; record but classify separately
            trace_results.setdefault("statement_score_format_differs", 0)
            trace_results["statement_score_format_differs"] += 1

print(json.dumps({"physical_rows_scanned": total_physical, "evidence_files": len(evidence_files),
                  "matched_rows_total": len(matches), "distinct_ids_total": len({m[2] for m in matches}),
                  "comparison": comparison, "trace": trace_results}, indent=1))
