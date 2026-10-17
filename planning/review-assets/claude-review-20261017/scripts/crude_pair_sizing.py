"""Crude, contemporaneous sizing of target-indication phase transitions from the Virtual Biotech linkage.

PURPOSE: order-of-magnitude feasibility sizing for planning only. NOT a label set.
Known biases (see review document): (1) the linkage is a contemporary ChEMBL-curated mapping, so it lags
registration (few 2025+ trials) and under-counts 2024 events; (2) comparator/background arms are linked as
if they were program drugs (e.g., NCT06203210 is mapped to topotecan/amrubicin targets, not to I-DXd/CD276);
(3) 'trial_date' is a start date without date type; (4) mixed phases are collapsed by the source.
Run with the project's .venv Python (needs pyarrow).
"""
import collections
import json
import sys

import pyarrow.parquet as pq

LINK = r"E:\projects_data\drug_target_agents_data\reference\vbt_linkage\71f9da6\chembl_clinical_nct_data.parquet"
table = pq.read_table(LINK).to_pydict()
n = len(table["nct_id"])

pairs = collections.defaultdict(list)
for i in range(n):
    d = table["trial_date"][i]
    if not d:
        continue
    pairs[(table["targetId"][i], table["diseaseId"][i])].append(
        (d, float(table["phase"][i]), table["nct_id"][i], table["drugId"][i]))


def run(t0, t1, lookback_years=None, label=""):
    rows = []
    cutoff_recent = None
    if lookback_years:
        y, m, d = map(int, t0.split("-"))
        cutoff_recent = f"{y - lookback_years:04d}-{m:02d}-{d:02d}"
    for key, trials in pairs.items():
        before = [x for x in trials if x[0] <= t0]
        if not before:
            continue
        s0 = max(x[1] for x in before)
        if s0 > 2.0:
            continue
        if cutoff_recent and not [x for x in before if x[0] >= cutoff_recent and x[1] <= 2.0]:
            continue
        s0n = 1.0 if s0 <= 1.0 else 2.0
        adv = [x for x in trials if t0 < x[0] <= t1 and x[1] >= s0n + 1.0]
        rows.append((key, s0n, bool(adv)))
    events = [r for r in rows if r[2]]
    out = {"label": label, "origin": t0, "horizon_end": t1, "recent_activity_lookback_years": lookback_years,
           "at_risk_pairs": len(rows), "pair_level_transitions": len(events),
           "rate_percent": round(100 * len(events) / max(1, len(rows)), 2),
           "targets_with_events": len({r[0][0] for r in events}),
           "diseases_with_events": len({r[0][1] for r in events})}
    for s in (1.0, 2.0):
        sub = [r for r in rows if r[1] == s]
        out[f"origin_phase_{int(s)}"] = {"at_risk": len(sub), "transitions": sum(r[2] for r in sub)}
    return out


trial_dates = {}
for i in range(n):
    if table["trial_date"][i]:
        trial_dates[table["nct_id"][i]] = table["trial_date"][i]
by_year = collections.Counter(d[:4] for d in trial_dates.values())

example = [(table["drugId"][i], table["targetId"][i], table["diseaseId"][i], table["phase"][i], table["trial_date"][i])
           for i in range(n) if table["nct_id"][i] == "NCT06203210"]

result = {
    "linkage_rows": n,
    "unique_target_disease_pairs": len({(table['targetId'][i], table['diseaseId'][i]) for i in range(n)}),
    "distinct_trials_with_start_date": len(trial_dates),
    "trials_by_start_year": {y: by_year.get(str(y), 0) for y in range(2016, 2027)},
    "max_nct_number": "NCT%08d" % max(int(k[3:]) for k in trial_dates),
    "comparator_contamination_example_NCT06203210": example,
    "configs": [
        run("2023-01-01", "2025-01-01", None, "all pairs with Phase<=2 trial at origin (24 months)"),
        run("2023-01-01", "2025-01-01", 5, "recent-activity restricted (24 months)"),
        run("2023-01-01", "2024-01-01", 5, "recent-activity restricted (12 months)"),
        run("2025-08-01", "2026-08-01", 5, "post-2025-08 origin (12 months): linkage truncated"),
    ],
}
json.dump(result, sys.stdout, indent=1)
