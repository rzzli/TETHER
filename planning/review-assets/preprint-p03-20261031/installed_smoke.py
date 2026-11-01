"""Installed JSON-only fictional smoke; no model, acquisition or biomedical data."""

import argparse
from datetime import date, datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

import asof
from asof.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from asof.serde import canonical, encode
from asof.study.source_fact_sources import compile_reference, verify_reference
from asof.study.source_fact_evaluation import score_cell, aggregate_cells


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.output.absolute()
    root.mkdir(parents=True, exist_ok=False)
    assert Path(asof.__file__).is_relative_to(Path(sys.prefix)), "Checkout import instead of installed package"
    assert importlib.util.find_spec("pyarrow") is None, "Expected dependency-free installed environment"
    row = dict(id="fiction", targetId="CONTROL", diseaseId="CONTROL_DISEASE", beta=-0.0)
    raw = canonical(row)
    (root / "raw.json").write_bytes(raw)
    day = date(2000, 1, 1)
    cutoff = datetime(2001, 1, 1, tzinfo=timezone.utc)
    availability = Availability(day, day, day, day, day, "fictional_control", None)
    source = SourceNode("control", "fictional", "fiction-v1", "raw.json", hashlib.sha256(raw).hexdigest(),
                        "agent_evidence", availability, TemporalClass.HISTORICAL, "https://example.invalid/control")
    snapshot = Snapshot(2, "fictional", Profile.DEMO, cutoff.date(), False, (), (source,), str(root),
                        origin_at=cutoff)
    task = dict(schema_version=1, task_id="installed-fictional-control",
                scope=dict(target_id="CONTROL", indication_id="CONTROL_DISEASE", target_namespace_version="fiction-v1",
                           indication_namespace_version="fiction-v1", action=None, modality=None, tissue=None),
                cutoff=cutoff.isoformat(), profile="synthetic_demo", primary_families=["reported_measurement"],
                records=[dict(record_key="r", source_id="control", locator=dict(format="json", pointer=""),
                              identity=dict(id="fiction", targetId="CONTROL", diseaseId="CONTROL_DISEASE"))],
                fields=[dict(record_key="r", field="beta", family="reported_measurement", group="r-estimate",
                             unit_field=None, empty_policy="unknown")], joins=[],
                collection=dict(status="selected_records", reason="One fictional installed smoke record."))
    catalog = {"fictional": {"roles": ["agent_evidence"]}}
    reference = compile_reference(task, snapshot, root, catalog, deadline=time.monotonic() + 30)
    replay = verify_reference(reference.document, reference.fingerprint, task, snapshot, root, catalog,
                              deadline=time.monotonic() + 30)
    facts = [{key: encode(f[key]) for key in ("fact_id", "value", "unit", "source", "unknown_reason")}
             for f in replay.document["facts"]]
    output = dict(schema_version=1, task_id=task["task_id"], task_sha256=replay.document["task_sha256"],
                  status="answered", facts=facts, collection_status="selected_records", reason=None)
    good = score_cell(replay, canonical(output), cell_id="good")
    output["facts"][0]["value"] = 0.0
    bad = score_cell(replay, canonical(output), cell_id="signed-zero-control")
    unexecuted = score_cell(replay, None, cell_id="unexecuted", terminal="unexecuted")
    plan = [dict(cell_id=result["cell_id"], task_id=task["task_id"], task_sha256=replay.document["task_sha256"],
                 reference_sha256=replay.fingerprint) for result in (good, bad, unexecuted)]
    aggregate = aggregate_cells(plan, [good, bad, unexecuted])
    assert good["completion"] and not bad["completion"] and bad["critical_errors"]
    assert aggregate["completion_count"] == 1 and aggregate["planned_cells"] == 3
    report = dict(schema_version=1, status="PASS_INSTALLED_FICTIONAL_JSON_ONLY", installed_module=str(asof.__file__),
                  interpreter=str(sys.executable), interpreter_prefix=sys.prefix, arrow_installed=False,
                  reference_sha256=replay.fingerprint, fictional_cells=3, completed_cells=1,
                  signed_zero_rejected=True, unexecuted_retained=True, source_replay_passed=True,
                  model_calls=0, scientific_validation="not_established", real_measurement_features_added=0)
    (root / "smoke-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
