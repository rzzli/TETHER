"""Selected original-row replay for the explicit Open Targets 25.09 recipe 2.2."""

from __future__ import annotations
import csv
from collections.abc import Mapping
from asof.contracts import (
    Observation,
    EvidenceStatus,
    Polarity,
    ScientificContext,
    QuantitativeResult,
    Method,
)
from asof.ingest import (
    EVIDENCE_COLUMNS,
    TYPE_CATEGORIES,
    NORMALIZATION_VERSION,
    _json_value,
    _publication,
    arrow,
)
from asof.serde import ContractError, canonical, encode, fingerprint, freeze
from .diagnostic_codec import need

FORBIDDEN = frozenset(
    (
        "clinicalPhase",
        "clinicalStatus",
        "trialPhase",
        "trialStatus",
        "studyStopReason",
        "studyStopReasonCategories",
        "trialOutcome",
        "outcome",
    )
)
IDENTITY = frozenset(("id", "targetId", "diseaseId", "datasourceId", "datatypeId"))


def reconstruct_observation(
    row, *, symbol, disease_name, locator, mapping_refs, availability, cutoff
):
    """Rebuild every Observation field; source scores remain descriptive only."""
    need(
        isinstance(row, Mapping) and not FORBIDDEN.intersection(row),
        "Forbidden clinical projection",
    )
    need(
        row.get("datasourceId") not in (None, "", "chembl")
        and row.get("datatypeId") in TYPE_CATEGORIES,
        "Unsupported evidence source/type",
    )
    need(
        all(
            isinstance(row.get(k), str) and row[k]
            for k in ("id", "targetId", "diseaseId")
        ),
        "Missing row identity",
    )
    need(
        set(locator) == {"source_id", "row_group", "row"}
        and isinstance(locator["source_id"], str)
        and locator["source_id"]
        and all(
            type(locator[k]) is int and locator[k] >= 0 for k in ("row_group", "row")
        ),
        "Invalid physical locator",
    )
    published, year, date_unknown, reason = _publication(row, cutoff)
    need(not reason, "Ineligible publication")
    row = _json_value(row)
    source = row["datasourceId"]
    datatype = row["datatypeId"]
    missing = {
        "species": "not_verified_from_source_model_context",
        "effect_scale": "unverified_source_scale",
        "scientific_interpretation": "unreviewed",
        "tissue": "not_canonically_resolved_from_source_context",
    }
    for name in ("study_id", "cohort"):
        if not row.get({"study_id": "studyId", "cohort": "cohortId"}[name]):
            missing[name] = "not_supplied_by_source"
    ancestry = (
        row.get("ancestry")
        if isinstance(row.get("ancestry"), str) and row.get("ancestry")
        else None
    )
    if ancestry is None:
        missing["ancestry"] = (
            "not_supplied_by_source"
            if not row.get("ancestry")
            else "unresolved_provider_value"
        )
    missing.update(date_unknown)
    study = str(row["studyId"]) if row.get("studyId") is not None else None
    cohort = str(row["cohortId"]) if row.get("cohortId") is not None else None
    statement = f"Open Targets 25.09 record {row['id']} from {source} links {symbol} ({row['targetId']}) to {disease_name} ({row['diseaseId']}); datatype {datatype}; provider evidence score {row.get('score')}. This is a resource annotation."
    return Observation(
        "ot25:" + source + ":" + row["id"],
        row["targetId"],
        row["diseaseId"],
        None,
        TYPE_CATEGORIES[datatype],
        "integrated",
        statement,
        EvidenceStatus.OBSERVED,
        Polarity.UNCERTAIN,
        "uncertain",
        source + ":" + study if study else None,
        source + ":cohort:" + cohort
        if cohort
        else source + ":study:" + study
        if study
        else None,
        ScientificContext(
            None,
            ancestry,
            None,
            None,
            None,
            None,
            (source + ":" + cohort,) if cohort else (),
        ),
        QuantitativeResult(None, None, None, None, None, None, None),
        Method(
            "asof.opentargets.normalize",
            NORMALIZATION_VERSION,
            {
                "projection": tuple(row),
                "source_row_sha256": fingerprint(row),
                "interpretation_scope": "resource_annotation_only",
                "scientific_validation": "not_run",
            },
            "passed",
            (
                "Contract/field normalization checked; scientific interpretation is unreviewed",
                "Provider score is descriptive and is not an effect size or prediction feature",
            ),
        ),
        availability,
        {},
        None,
        tuple(sorted(set(mapping_refs) | {locator["source_id"]})),
        None,
        {**locator, "evidence_id": row["id"], "datasource_id": source},
        {k: v for k, v in row.items() if k not in IDENTITY},
        missing,
        published,
        year,
    )


def verify_observation(observation, row, **kwargs):
    expected = reconstruct_observation(row, **kwargs)
    need(
        canonical(encode(observation)) == canonical(encode(expected)),
        "Whole normalized Observation differs from original row recipe",
    )
    return freeze(
        {
            "observation_id": expected.observation_id,
            "source_row_sha256": fingerprint(_json_value(row)),
            "observation_sha256": fingerprint(expected),
            "whole_record_equal": True,
        }
    )


def parquet_row(path, locator, columns, *, deadline_check):
    """Caller holds approved source lock; convert exactly one projected row."""
    pq = arrow()
    deadline_check()
    parquet = pq.ParquetFile(path)
    group, offset = locator.get("row_group"), locator.get("row")
    need(
        type(group) is int
        and type(offset) is int
        and 0 <= group < parquet.num_row_groups
        and offset >= 0,
        "Invalid row locator",
    )
    need(
        len(columns) == len(set(columns))
        and all(c in parquet.schema_arrow.names for c in columns),
        "Missing/duplicate projected column",
    )
    consumed = 0
    for batch in parquet.iter_batches(
        row_groups=[group], columns=list(columns), batch_size=4096
    ):
        deadline_check()
        if consumed + batch.num_rows > offset:
            return _json_value(batch.slice(offset - consumed, 1).to_pylist()[0])
        consumed += batch.num_rows
    raise ContractError("Row locator outside row group")


def audit_selected(store, case, identifiers, selected, paths, *, deadline_check):
    """Replay exact mapping and selected rows using already locked approved paths."""
    nodes = {n.source_id: n for n in store.snapshot.sources}
    values = {}
    refs = []

    def source(locator, product, release):
        node = nodes.get(locator.get("source_id"))
        need(
            node is not None
            and node.dataset_id == product
            and node.release_id == release,
            "Mapping/source product mismatch",
        )
        need(node.source_id in paths, "Source not approved")
        return node, paths[node.source_id]

    for kind in ("target", "disease"):
        expected, locator = identifiers[kind]
        node, path = source(locator, "ot_" + kind, "25.09")
        actual = parquet_row(
            path, locator, tuple(expected), deadline_check=deadline_check
        )
        need(actual == expected, "Identifier mapping row differs")
        namespace = (
            case.hypothesis.target_namespace_version
            if kind == "target"
            else case.hypothesis.indication_namespace_version
        )
        need(
            namespace == "OpenTargets-25.09:" + kind + ":" + node.sha256,
            "Identifier namespace differs",
        )
        values[kind] = actual
        refs.append(node.source_id)
    expected, locator = identifiers["hgnc"]
    node, path = source(locator, "hgnc_symbols", "snapshot_2026-10-10")
    need(type(locator.get("row")) is int and locator["row"] >= 0, "Invalid HGNC row")
    actual = None
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for i, row in enumerate(csv.DictReader(stream, delimiter="\t")):
            deadline_check()
            if i == locator["row"]:
                actual = row
                break
    need(
        actual == expected and actual is not None and actual["status"] == "Approved",
        "HGNC mapping differs",
    )
    symbol = identifiers["symbol"]
    need(
        actual["symbol"] == symbol == values["target"]["approvedSymbol"]
        and actual["ensembl_gene_id"]
        == values["target"]["id"]
        == case.hypothesis.target_id
        and values["disease"]["id"] == case.hypothesis.indication_id,
        "Canonical identifiers disagree",
    )
    refs.append(node.source_id)
    audits = []
    for record in selected:
        deadline_check()
        obs = encode(record.observation)
        locator = obs["source_locator"]
        node, path = source(locator, "ot_evidence", "25.09")
        pq = arrow()
        columns = pq.ParquetFile(path).schema_arrow.names
        projection = tuple(c for c in EVIDENCE_COLUMNS if c in columns)
        need(
            obs["method"]["parameters"].get("projection") == list(projection),
            "Normalization projection differs",
        )
        raw = parquet_row(path, locator, projection, deadline_check=deadline_check)
        need(
            raw.get("targetId") == case.hypothesis.target_id
            and raw.get("diseaseId") == case.hypothesis.indication_id,
            "Raw row case differs",
        )
        audits.append(
            verify_observation(
                obs,
                raw,
                symbol=symbol,
                disease_name=values["disease"]["name"],
                locator={k: locator[k] for k in ("source_id", "row_group", "row")},
                mapping_refs=refs,
                availability=node.availability,
                cutoff=case.cutoff,
            )
        )
    return freeze(
        {
            "mapping_refs": sorted(refs),
            "selected_rows": audits,
            "scientific_validation": "not_performed",
        }
    )
