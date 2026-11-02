"""Independently reconstruct the retained original-source rows at physical locators."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
WORK = Path(__file__).resolve().parents[4]
STORE = Path(r"E:\projects_data\drug_target_agents_data")
policy = json.loads((HERE / "SOURCE-SELECTION-POLICY.json").read_text())
assert hashlib.sha256((HERE / "SOURCE-INVENTORY.json").read_bytes()).hexdigest() == policy["universe_inventory_sha256"]
assert hashlib.sha256(Path(policy["task_spec_path"]).read_bytes()).hexdigest() == policy["task_spec_sha256"]
groups = defaultdict(list)
for name in ["source-slice-evidence.json", "source-slice-credible-set.json", "source-slice-labels.json"]:
    path = WORK / "data/cache/tether-q03" / name
    for row in json.loads(path.read_text(encoding="utf-8")):
        loc = row["_locator"]
        source = (STORE / loc["relative_path"]).resolve()
        assert source.is_relative_to(STORE / "raw/open_targets_platform/25.09")
        projection = {k: v for k, v in row.items() if not k.startswith("_")}
        groups[source, loc["row_group"]].append((loc["row_in_group"], projection))
verified = 0
decoded = 0
logical_bytes = 0
for (path, rg), rows in groups.items():
    columns = sorted({key for _, row in rows for key in row})
    table = pq.ParquetFile(path).read_row_group(rg, columns=columns, use_threads=False)
    decoded += table.num_rows
    logical_bytes += table.nbytes
    source_rows = table.take(pa.array([i for i, _ in rows])).to_pylist()
    for (_, expected), actual in zip(rows, source_rows):
        assert expected == actual, (path, rg, expected, actual)
        verified += 1
result = {"passed": True, "source_rows_reconstructed": verified, "physical_row_groups_read": len(groups), "row_group_rows_decoded": decoded, "decoded_arrow_logical_bytes": logical_bytes, "frozen_spec_hash_verified": True, "frozen_universe_hash_verified": True}
(HERE / "SOURCE-LOCATOR-VERIFICATION.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
