"""Build v2 fictional fixtures from copies of archived v1 inputs; never rewrite v1."""
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

from tether_engine.agents import Selection, Usage, make_request
from tether_engine.chrono import load_snapshot
from tether_engine.contracts import Case, Category, EvidenceStatus
from tether_engine.serde import decode, encode, fingerprint, read_json, sha256_file, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path(__file__).resolve().parents[2] / 'src/tether_engine/demo')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    legacy, root = args.input, args.output
    required = ('case.json','evidence.json','future.json','snapshot.json','scorer.json')
    missing = [name for name in required if not (legacy/name).is_file()]
    if missing:
        parser.error('Missing preserved v1 inputs: '+', '.join(missing))
    for name in required:
        read_json(legacy/name)
    root.mkdir(parents=True, exist_ok=False)
    case_doc = read_json(legacy / "case.json")
    case_doc.update(schema_version=2, origin_at="2023-01-01T23:59:59.999999+00:00")
    case = decode(Case, case_doc)
    packet = read_json(legacy / "evidence.json")
    write_json(root / "raw-inputs.json", packet)
    packet = json.loads(json.dumps(packet))
    packet["schema_version"] = 2
    for record in packet["observations"]:
        record["input_refs"] = ["demo-original-input"]
        record["feature_scope"] = case.hypothesis.key if record["features"] else None
        record["source_locator"] = {"source_id": "demo-original-input", "legacy_observation_id": record["observation_id"]}
    write_json(root / "case.json", case)
    write_json(root / "evidence.json", packet)
    write_json(root / "future.json", read_json(legacy / "future.json"))
    snapshot = read_json(legacy / "snapshot.json")
    sources = []
    for artifact in snapshot["artifacts"]:
        is_future = artifact["artifact_id"] == "demo-future"
        key = "demo-future-input" if is_future else "demo-original-input"
        filename = "future.json" if is_future else "raw-inputs.json"
        sources.append({"source_id": key, "dataset_id": "synthetic_fixture", "release_id": "fixture-v1",
                        "path": filename, "sha256": sha256_file(root / filename), "role": "agent_evidence",
                        "availability": artifact["availability"], "temporal_classification": "verified_historical",
                        "source_url": artifact["source_url"]})
        artifact["sha256"] = sha256_file(root / artifact["path"])
        artifact["input_refs"] = [key]
    snapshot.update(schema_version=2, snapshot_id="synthetic-v2", origin_at=case_doc["origin_at"],
                    sources=sources, coverage={"source_completeness": "complete"})
    write_json(root / "snapshot.json", snapshot)
    model = read_json(legacy / "scorer.json")
    model.update(schema_version=2, model_id="synthetic-logistic-v2", feature_schema="tether-features-v2",
                 aggregation="mean_of_unique_dependency_groups_v2")
    write_json(root / "scorer.json", model)
    store = load_snapshot(root / "snapshot.json", case)
    responses = {}
    for category in Category:
        records = tuple(record for record in store.query(case, category)
                        if record.observation.status == EvidenceStatus.OBSERVED)
        if records:
            request = make_request(case, category, records)
            responses[category.value] = [{"request_sha256": fingerprint(request),
                "selection": Selection(tuple(record.observation.observation_id for record in records), Usage(0, 0, 0))}]
    write_json(root / "replay.json", {"schema_version": 2, "responses": responses})
    print(f"Built fictional v2 fixtures: {root}")


if __name__ == "__main__":
    main()
