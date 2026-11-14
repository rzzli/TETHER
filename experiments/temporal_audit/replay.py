"""Recompute the descriptive study tables from published aggregate counts."""
from __future__ import annotations

import argparse
import csv
import hashlib
from itertools import product
import json
from pathlib import Path
import re
import subprocess
import sys


SOURCE = Path(__file__).with_name("aggregates.json")
SHA256 = "81d3b6db2954bc5a4e072b391b8295dfe448a08cb32f68f9f4bfc61492e1734d"
SOURCES = ("gene_burden", "uniprot_literature", "expression_atlas")
CLOCKS = {"22.11": "2022-11-25", "24.09": "2024-09-19"}
FIELDS = ("evidenceDate", "publicationDate")
DATE_BINS = ("entirely_before", "at_or_after", "crossing", "missing_column", "null", "empty", "malformed", "unsupported")
SNAPSHOTS = ("2023-01-01", "2025-01-01", "2026-04-01")
UNITS = ("pair", "literal_drug_target_disease")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def exact(value, fields, label):
    need(type(value) is dict and set(value) == set(fields.split()), f"Invalid {label} fields")


def counts(values, label):
    need(all(type(value) is int and value >= 0 for value in values), f"Invalid {label} count")


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def _archive(document):
    need(type(document["archive"]) is list and len(document["archive"]) == 12, "Expected 12 archive comparison cells")
    exact(document["archive_inventory"], "bytes_verified files_selected physical_footer_rows", "archive inventory")
    counts(document["archive_inventory"].values(), "archive inventory")
    cells, physical = {}, {}
    for row in document["archive"]:
        exact(row, "source archive cutoff field archive_pairs modern_pairs shared date_counts modern_rows archive_rows", "archive cell")
        source, release, field = row["source"], row["archive"], row["field"]
        key = source, release, field
        need(source in SOURCES and release in CLOCKS and field in FIELDS and key not in cells, "Invalid or duplicate archive cell")
        need(row["cutoff"] == CLOCKS[release], "Incorrect exclusive release clock")
        a, f, s = (row[x] for x in ("archive_pairs", "modern_pairs", "shared"))
        counts((a, f, s, row["modern_rows"], row["archive_rows"]), "pair or row")
        bins = row["date_counts"]
        exact(bins, " ".join(DATE_BINS), "date dispositions")
        counts(bins.values(), "date disposition")
        need(sum(bins.values()) == row["modern_rows"] and f <= bins["entirely_before"] and a <= row["archive_rows"]
             and s <= min(a, f), "Archive pair/date conservation failure")
        for coordinate, value in (((source, release), row["archive_rows"]), ((source, "25.09"), row["modern_rows"])):
            need(physical.setdefault(coordinate, value) == value, "Archive physical-row denominator differs across cells")
        union = a + f - s
        cells[key] = dict(source=source, archive=release, cutoff=row["cutoff"], field=field,
                          archive_pairs=a, modern_pairs=f, shared=s, archive_only=a - s, modern_only=f - s,
                          union=union, jaccard=ratio(s, union), archive_retention=ratio(s, a),
                          selected_modern_unmatched=ratio(f - s, f), archive_rows=row["archive_rows"],
                          modern_rows=row["modern_rows"], **bins)
    need(len(physical) == 9 and sum(physical.values()) == document["archive_inventory"]["physical_footer_rows"],
         "Archive physical inventory differs from nine unique partitions")
    return [cells[key] for key in product(SOURCES, CLOCKS, FIELDS)]


def _endpoint(document, flow):
    need(type(document["endpoint"]) is list and len(document["endpoint"]) == 4, "Expected four endpoint cells")
    cells = {}
    for row in document["endpoint"]:
        exact(row, "unit months mature excluded candidate no_record unresolved", "endpoint cell")
        unit, months = row["unit"], row["months"]
        counts((row[k] for k in ("months", "mature", "excluded", "candidate", "no_record", "unresolved")), "endpoint")
        need(unit in UNITS and months in (36, 60) and (unit, months) not in cells, "Invalid or duplicate endpoint cell")
        mature, excluded, candidate, no_record, unresolved = (row[k] for k in ("mature", "excluded", "candidate", "no_record", "unresolved"))
        need(mature == excluded + candidate + no_record + unresolved and
             (unit != "pair" or mature == flow["development"]), "Endpoint disposition conservation failure")
        eligible = mature - excluded
        cells[(unit, months)] = row | dict(eligible=eligible, lower=ratio(candidate, eligible),
                                          upper=ratio(candidate + unresolved, eligible),
                                          unresolved_fraction=ratio(unresolved, eligible))
    return [cells[key] for key in product(UNITS, (36, 60))]


def _registry(document, flow):
    need(type(document["registry"]) is list and len(document["registry"]) == 3, "Expected three registry snapshots")
    cells = {}
    fields = ("snapshot found_ids coherent_actual_ids unknown_start_type found_links exact_phase mixed_phase "
              "different_phase unknown_phase equal_date overlap_date disjoint_date joint_start exact_names names_nonmatch names_missing")
    for row in document["registry"]:
        exact(row, fields, "registry snapshot")
        date = row["snapshot"]
        need(date in SNAPSHOTS and date not in cells, "Invalid or duplicate registry snapshot")
        counts((value for key, value in row.items() if key != "snapshot"), "registry")
        ids, links = flow["requested_ids"], flow["row_trial_links"]
        need(row["coherent_actual_ids"] + row["unknown_start_type"] <= row["found_ids"] <= ids,
             "Registry ID conservation failure")
        found = row["found_links"]
        need(row["found_ids"] <= found <= links and
             sum(row[k] for k in ("exact_phase", "mixed_phase", "different_phase", "unknown_phase")) == found and
             sum(row[k] for k in ("equal_date", "overlap_date", "disjoint_date")) == found and
             row["joint_start"] <= min(row["exact_phase"], row["equal_date"] + row["overlap_date"]) and
             row["exact_names"] + row["names_nonmatch"] + row["names_missing"] == links,
             "Registry link conservation failure")
        cells[date] = row | dict(requested_ids=ids, requested_links=links, missing_ids=ids - row["found_ids"],
                                 missing_links=links - found, joint_start_fraction=ratio(row["joint_start"], links),
                                 exact_name_fraction=ratio(row["exact_names"], links))
    return [cells[date] for date in SNAPSHOTS]


def calculate(document):
    exact(document, "schema_version kind source_report_sha256 archive_inventory archive flow endpoint registry qualification dependence expression_full_modern", "aggregate document")
    need(type(document["schema_version"]) is int and document["schema_version"] == 1 and
         document["kind"] == "tether_descriptive_audit_aggregates_v1", "Unsupported aggregate format")
    pins = document["source_report_sha256"]
    exact(pins, "designation archive expression_full registry endpoint literal_drug dependence", "source report pins")
    need(all(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) for value in pins.values()), "Invalid source report digest")
    flow = document["flow"]
    exact(flow, "sizing development reserve selected_trails withheld_trails linked_trails requested_ids row_trial_links", "cohort flow")
    counts(flow.values(), "cohort flow")
    need(flow["development"] + flow["reserve"] == flow["sizing"] and
         flow["withheld_trails"] + flow["linked_trails"] == flow["selected_trails"] <= flow["development"] and
         flow["requested_ids"] <= flow["row_trial_links"], "Cohort flow conservation failure")
    qualification = document["qualification"]
    exact(qualification, "clinical_labels independent_test_pool historical_actor_inputs", "qualification")
    need(type(qualification["clinical_labels"]) is int and qualification["clinical_labels"] == 0 and
         qualification["independent_test_pool"] is False and qualification["historical_actor_inputs"] is False,
         "Aggregate release does not qualify clinical inputs, labels or test sets")
    dependence = document["dependence"]
    exact(dependence, "bridge_quarantined linked_components entry_components largest_entry_component max_pairs_per_trial_36 max_pairs_per_trial_60", "dependence")
    counts(dependence.values(), "dependence")
    need(dependence["bridge_quarantined"] <= flow["development"] and
         dependence["largest_entry_component"] <= flow["sizing"] and dependence["linked_components"] <= dependence["entry_components"],
         "Dependence denominator failure")
    archive, endpoint, registry = _archive(document), _endpoint(document, flow), _registry(document, flow)
    context = document["expression_full_modern"]
    need(type(context) is list and len(context) == 2, "Invalid expression overlap context")
    expression = []
    for row, release in zip(context, CLOCKS):
        exact(row, "archive archive_pairs modern_pairs shared", "full expression cell")
        a, m, s = (row[key] for key in ("archive_pairs", "modern_pairs", "shared"))
        counts((a, m, s), "full expression")
        primary = next(c for c in archive if (c["source"], c["archive"], c["field"]) == ("expression_atlas", release, FIELDS[0]))
        need(row["archive"] == release and s <= min(a, m) and a == primary["archive_pairs"] and
             m >= primary["modern_pairs"] and s >= primary["shared"], "Full expression context does not reconcile")
        expression.append(row | dict(union=a + m - s, jaccard=ratio(s, a + m - s)))
    maxima = [dependence[f"max_pairs_per_trial_{months}"] for months in (36, 60)]
    need(all(n <= row["candidate"] for n, row in zip(maxima, endpoint[:2])), "Candidate link maximum exceeds its denominator")
    return dict(archive=archive, endpoint=endpoint, registry=registry,
                flow=[dict(id=key, count=value) for key, value in flow.items()],
                dependence=dependence | {f"max_pair_fraction_{row['months']}": ratio(n, row["candidate"])
                                         for n, row in zip(maxima, endpoint[:2])},
                expression_full_modern=expression)


def replay(output):
    payload = SOURCE.read_bytes()
    need(hashlib.sha256(payload).hexdigest() == SHA256, "Released aggregate digest mismatch")
    document = json.loads(payload)
    result = calculate(document)
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {}
    for name in ("archive", "endpoint", "registry", "flow"):
        rows = result[name]
        path = output / (name + ".csv")
        with path.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        artifacts[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    summary = dict(schema_version=1, scope="released_aggregate_arithmetic_only", input_sha256=SHA256,
                   source_report_sha256=document["source_report_sha256"], archive_inventory=document["archive_inventory"],
                   artifacts=artifacts, dependence=result["dependence"],
                   expression_full_modern=result["expression_full_modern"],
                   qualification=document["qualification"])
    with (output / "summary.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(summary, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Fresh directory for CSV tables and summary")
    parser.add_argument("--figures", action="store_true", help="Also render both figures with optional matplotlib")
    args = parser.parse_args(argv)
    try:
        summary = replay(args.output)
        if args.figures:
            plot_script = Path(__file__).with_name("plot.py")
            figure_dir = args.output / "figures"
            subprocess.run([sys.executable, "-I", "-B", str(plot_script), "--input", str(args.output),
                            "--output", str(figure_dir)], check=True, stdout=subprocess.DEVNULL)
            summary["figure_manifest"] = str(figure_dir / "plot-manifest.json")
        print(json.dumps(summary, indent=2, allow_nan=False))
    except subprocess.CalledProcessError as error:
        print(f"temporal audit: tables written; figure generation exited with status {error.returncode}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as error:
        print(f"temporal audit: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
