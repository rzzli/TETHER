"""Prepare fictional Parquet fixtures and measure one complete build per fresh process."""
import argparse
import json
from pathlib import Path
import shutil
import sys

from tether_engine import ingest
from tether_engine.serde import fingerprint, read_json, sha256_file, write_json


def prepare(root, scenario):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tests.ingest_fixtures import IngestFixture

    root.mkdir()
    fixture = IngestFixture()
    fixture.setUp()
    try:
        cases = []
        if scenario == "sparse":
            # All distractors match individual requested IDs, but none match a requested pair.
            unique = {row["targetId"]: row for row in fixture.rows}
            candidates = list(unique.values())
            distractors = [dict(row, diseaseId=candidates[(i + 1) % len(candidates)]["diseaseId"])
                           for i, row in enumerate(candidates)]
            rows = distractors * 16384
            for i, row in enumerate(candidates):
                rows[i * 16001] = row
            rows[-2:] = [candidates[0], dict(candidates[1], datatypeId="unhandled")]
        else:
            symbol, disease, action, _ = ingest.PILOT[0]
            cases = [dict(symbol=symbol, disease_id=disease, intended_action=action,
                          modality=f"fixture_mode_{i}", tissue=None) for i in range(16)]
            rows = [dict(fixture.rows[0], id=f"fictional-{i}") for i in range(48)]
            rows.extend([rows[0], dict(rows[1], datatypeId="unhandled")])
        fixture.pq.write_table(fixture.pa.Table.from_pylist(rows), fixture.raw / "evidence.parquet",
                               row_group_size=70000)
        fixture.receipt(fixture.entries[2])
        shutil.copytree(fixture.raw, root / "raw")
        shutil.copyfile(fixture.catalog, root / "catalog.json")
        manifest = read_json(fixture.manifest)
        manifest["raw_root"] = str((root / "raw").resolve())
        write_json(root / "inputs.json", manifest)
        if cases:
            write_json(root / "cases.json", {"schema_version": 1, "cases": cases})
    finally:
        fixture.tearDown()


def measure(root, output):
    cases = root / "cases.json"
    report = ingest.build_snapshot(root / "inputs.json", root / "catalog.json", output,
                                   cases_path=cases if cases.is_file() else None, packet_layout="bounded")
    if report["status"] != "built":
        raise ValueError("Benchmark cases must all resolve")
    products = []
    for case in report["cases"]:
        directory = output / case["case_id"]
        products.append({
            "case": case["case_id"],
            "packets": [sha256_file(directory / packet["path"]) for packet in case["packets"]],
            "rejections": sha256_file(directory / "rejections.json"),
        })
    result = {
        "ingest_sha256": sha256_file(Path(ingest.__file__)),
        "manifest_sha256": report["inspection"]["manifest_sha256"],
        "evidence_sha256": sha256_file(root / "raw/evidence.parquet"),
        "cases": len(products), "ordered_products_sha256": fingerprint(products),
        "counters": report["counters"], "elapsed_seconds": report["elapsed_seconds"],
        "peak_memory_bytes": report["peak_memory_bytes"],
    }
    write_json(output / "measurement.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("root", type=Path)
    prep.add_argument("scenario", choices=("sparse", "repeated"))
    run = commands.add_parser("measure")
    run.add_argument("root", type=Path)
    run.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.root, args.scenario)
    else:
        measure(args.root, args.output)
