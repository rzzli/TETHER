"""Reproduce the Virtual Biotech label/linkage counts quoted in the October 8 plan (catalog blocker:
'row/pair counts from the old review were not independently reproduced').

Run with the project .venv Python (needs pyarrow). Prints JSON.
"""
import collections
import csv
import hashlib
import json

import pyarrow.parquet as pq

LABELS = r"E:\projects_data\drug_target_agents_data\benchmark\labels\vbt_labels\71f9da6\clinical_trial_labels_reconciled.csv"
LINK = r"E:\projects_data\drug_target_agents_data\reference\vbt_linkage\71f9da6\chembl_clinical_nct_data.parquet"

with open(LABELS, newline="", encoding="utf-8-sig") as handle:
    rows = list(csv.DictReader(handle))
primary = collections.Counter(r["primary_endpoint_result"] for r in rows)
link = pq.read_table(LINK).to_pydict()
n = len(link["nct_id"])
report = {
    "label_rows": len(rows),
    "label_unique_nct_ids": len({r["nct_id"] for r in rows}),
    "primary_endpoint_result": dict(primary),
    "decisive_primary_endpoints": primary["POSITIVE"] + primary["NEGATIVE"],
    "linkage_rows": n,
    "linkage_unique_trials": len(set(link["nct_id"])),
    "linkage_unique_targets": len(set(link["targetId"])),
    "linkage_unique_diseases": len(set(link["diseaseId"])),
    "linkage_unique_target_disease_pairs": len({(link["targetId"][i], link["diseaseId"][i]) for i in range(n)}),
    "labels_sha256": hashlib.sha256(open(LABELS, "rb").read()).hexdigest(),
    "linkage_sha256": hashlib.sha256(open(LINK, "rb").read()).hexdigest(),
}
print(json.dumps(report, indent=1))
