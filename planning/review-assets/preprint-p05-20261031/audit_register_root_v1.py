"""Root's separate read-only register check; no producer helper or answer oracle."""
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from asof.study.stable_read import checked_path, stable_files
import pyarrow.parquet as pq

ASSETS = Path(__file__).resolve().parent
TASKS = ROOT / "data/derived/preprint-p05-neutral-tasks-20261101T075541Z"
RAW = Path(r"E:\projects_data\drug_target_agents_data")
RUN = ROOT / "data/benchmark/cohorts/preprint-p05-register-20261101T083548Z"
CHECKS = 0


def need(ok, message):
    global CHECKS
    CHECKS += 1
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def wire(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def classify(row, field, family):
    if field not in row:
        return "absent"
    v = row[field]
    if v is None:
        return "null"
    if v == "" or type(v) in (list, dict, tuple) and len(v) == 0:
        return "empty"
    if family == "reported_measurement":
        if type(v) not in (int, float) or not math.isfinite(v) or field == "pValueExponent" and type(v) is not int:
            return "invalid"
    return "answerable"


def main():
    started = time.monotonic()
    public = json.loads((ASSETS / "REGISTER-MANIFEST-v1.json").read_bytes())
    need(sha((ASSETS / "REGISTER-MANIFEST-v1.json").read_bytes()) == "2c363c14a03b94ed39e285f9fac502fd8eff9bd3f3c81dc7faebe0309897c414", "external register manifest")
    raw = (RUN / "register.json").read_bytes()
    need(sha(raw) == public["register_sha256"] == "9108838b4611f356111807c6bfbfe5c319a11bdebbf6366233852e840d6463ec", "register bytes")
    d = json.loads(raw)
    need(d["case_ids"] == [f"p05-{i:02d}" for i in range(1, 13)] and d["status"] == "FROZEN", "fixed cases/status")
    need(d["role"] == "evaluation_only" and d["agent_visible"] is False and d["other_exposure"] == "UNKNOWN" and d["independent_studies_established"] is False and d["study_ready"] is False, "claim/role boundary")
    nodes = {n["source_id"]: n for n in json.loads((TASKS / "source-snapshot.json").read_bytes())["sources"]}
    paths = {checked_path(RAW, nodes[r["source"]["source_id"]]["path"]) for c in d["cases"] for r in c["native_records"]}
    totals, histogram, equal = defaultdict(Counter), Counter(), defaultdict(list)
    rows_checked = 0
    reasons = {"answerable": None, "absent": "field_not_in_schema", "null": "null_source_value", "empty": "empty_source_value", "invalid": "native_type_invalid"}
    with stable_files(sorted(paths), deadline=time.monotonic() + 120):
        for path in paths:
            node = next(n for n in nodes.values() if checked_path(RAW, n["path"]) == path)
            need(sha(path.read_bytes()) == node["sha256"], "original bytes")
        for c in d["cases"]:
            task_bytes = (TASKS / (c["case_id"] + ".task.json")).read_bytes()
            task = json.loads(task_bytes)
            need(sha(wire(task)) == c["task_sha256"] and c["exposure"]["status"] == "UNKNOWN", "neutral task/exposure")
            rows = {}
            for r in c["native_records"]:
                src = r["source"]; node = nodes[src["source_id"]]
                request = next(x for x in task["records"] if x["record_key"] == r["record_key"])
                need(src["sha256"] == node["sha256"] and src["relative_path"] == node["path"] and src["release_id"] == node["release_id"] and src["locator"] == request["locator"], "physical source binding")
                file = pq.ParquetFile(checked_path(RAW, node["path"]))
                loc = src["locator"]
                wanted = set(r["native_identity"]) | {f["field"] for f in task["fields"] if f["record_key"] == r["record_key"]}
                columns = sorted(wanted & set(file.schema_arrow.names))
                row = file.read_row_group(loc["row_group"], columns=columns).slice(loc["row"], 1).to_pylist()[0]
                rows[r["record_key"]] = row
                need(src["physical_row_0based"] == sum(file.metadata.row_group(i).num_rows for i in range(loc["row_group"])) + loc["row"], "global physical index")
                for field, observed in r["native_identity"].items():
                    status = classify(row, field, "identity_linkage")
                    expected = dict(present=field in row, value=row.get(field), status=status, unknown_reason=reasons[status])
                    need(wire(observed) == wire(expected), "native literal identity")
                    if status == "answerable" and type(row[field]) is str:
                        equal[(field, row[field])].append(dict(case_id=c["case_id"], record_key=r["record_key"], table_family=r["table_family"], source_id=src["source_id"], locator=loc))
                rows_checked += 1
            groups = defaultdict(list)
            per_family = defaultdict(Counter)
            expected_fields = []
            for f in task["fields"]:
                status = classify(rows[f["record_key"]], f["field"], f["family"])
                per_family[f["family"]]["requested"] += 1
                per_family[f["family"]][status] += 1
                groups[(f["family"], f["group"])].append(status)
                expected_fields.append({k: f[k] for k in ("record_key", "field", "family", "group")} | {"status": status})
            need(expected_fields == c["denominators"]["field_statuses"], "all original field statuses")
            for (family, _), statuses in groups.items():
                per_family[family]["groups"] += 1
                if family == "reported_measurement":
                    histogram[str(statuses.count("answerable"))] += 1
            for family, declared in c["denominators"]["families"].items():
                need(all(per_family[family][key] == value for key, value in declared.items()), "per-case original denominator")
                totals[family].update(per_family[family])
    expected_equal = {(field, value): members for (field, value), members in equal.items() if len(members) > 1}
    observed_equal = {(g["field"], g["native_string"]): g["members"] for g in d["literal_equal_string_groups"]}
    need(observed_equal == expected_equal, "complete literal equal-string membership")
    for family, declared in d["summary"]["families"].items():
        need(all(totals[family][k] == v for k, v in declared.items()), "aggregate denominator")
    need(dict(histogram) == d["summary"]["measurement_group_answerable_component_histogram"] and rows_checked == 24, "group histogram/all rows")
    seal_bytes = (RUN / "seal.json").read_bytes(); seal = json.loads(seal_bytes)
    need(sha(seal_bytes) == public["seal_sha256"] and not (RUN / "failure-seal.json").exists(), "seal/absence of failure")
    for artifact in seal["artifacts"]:
        payload = checked_path(RUN, artifact["path"]).read_bytes()
        need(len(payload) == artifact["bytes"] and sha(payload) == artifact["sha256"], "retained artifact bytes")
    result = dict(schema_version=1, status="PASS_ROOT_ORIGINAL_ROW_REGISTER_CHECK", checks=CHECKS, physical_rows=rows_checked, unique_original_files=len(paths), summary=d["summary"], register_sha256=sha(raw), wall_seconds=time.monotonic()-started, scientific_validation="not_established", outputs_modified=False)
    out = ASSETS / "REGISTER-ROOT-AUDIT-v1.json"
    with out.open("xb") as stream:
        stream.write(wire(result) + b"\n")
    print(json.dumps({k:result[k] for k in ("status", "checks", "physical_rows", "wall_seconds")}))


if __name__ == "__main__":
    main()
