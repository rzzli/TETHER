"""Receipt-verified, bounded local ingestion; no network or clinical prediction."""
from __future__ import annotations

import csv
import hashlib
import math
import os
import re
import tempfile
import time
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import (Artifact, Availability, Case, Category, EvidencePacket, EvidenceStatus,
                        Hypothesis, Method, Observation, Polarity, Profile, QuantitativeResult,
                        ScientificContext, Snapshot, SourceNode, TemporalClass)
from .provenance import catalog_index, check_role
from .journal import RunJournal
from .serde import (ContractError, Frozen, canonical, decode, encode, fingerprint, read_json,
                    parse_json, safe_child, sha256_file, write_json, MAX_NORMALIZED_JSON_BYTES)


DATASETS = {"ot_target", "ot_disease", "ot_evidence", "hgnc_symbols"}
NORMALIZATION_VERSION = "2.2"
REVIEW_CONTEXT_COLUMNS = ("textMiningSentences", "pmcIds", "studyOverview", "clinicalSignificances")
TYPE_CATEGORIES = {"genetic_association": Category.GENETICS, "somatic_mutation": Category.GENETICS,
                   "rna_expression": Category.EXPRESSION, "animal_model": Category.PERTURBATION,
                   "affected_pathway": Category.PATHWAY, "literature": Category.LITERATURE}
EVIDENCE_COLUMNS = ("id", "targetId", "diseaseId", "datasourceId", "datatypeId", "score", "resourceScore",
                    "studyId", "cohortId", "ancestry", "ancestryId", "cellType", "studySampleSize", "beta",
                    "betaConfidenceIntervalLower", "betaConfidenceIntervalUpper", "oddsRatio",
                    "oddsRatioConfidenceIntervalLower", "oddsRatioConfidenceIntervalUpper", "literature",
                    "publicationYear", "publicationDate", "evidenceDate", "releaseDate", "releaseVersion",
                    "targetModulation", "pValueMantissa", "pValueExponent", "biosamplesFromSource",
                    "diseaseCellLines", "biologicalModelId", "biologicalModelAllelicComposition",
                    "biologicalModelGeneticBackground", "geneticBackground", "targetInModel",
                    "targetInModelEnsemblId", "targetInModelMgiId", "variantId", "variantRsId",
                    "variantHgvsId", "variantFromSourceId", "variantAminoacidDescriptions",
                    "variantFunctionalConsequenceId", "variantEffect", "directionOnTrait",
                    "alleleOrigins", "allelicRequirements", "sex", "contrast", "crisprScreenLibrary",
                    "diseaseModelAssociatedHumanPhenotypes", "diseaseModelAssociatedModelPhenotypes",
                    "cohortDescription", "cohortPhenotypes", "cohortShortName", "studyLocusId",
                    "studyCases", "studyCasesWithQualifyingVariants", "statisticalMethod",
                    "statisticalMethodOverview", "statisticalTestTail", "log2FoldChangeValue",
                    "log2FoldChangePercentileRank", "pathways", "reactionId", "reactionName") + REVIEW_CONTEXT_COLUMNS
PILOT = (
    ("CD276", "EFO_0003060", "delivery_antigen", "adc"),
    ("OSMR", "EFO_0000729", "inhibit", "antibody"),
    ("ERBB2", "EFO_0000305", "inhibit", "antibody"),
    ("ERBB2", "EFO_0000305", "delivery_antigen", "adc"),
    ("PCSK9", "EFO_0004911", "inhibit", "antibody"),
    ("PCSK9", "EFO_0004911", "reduce_expression", "sirna"),
    ("IL6R", "EFO_0000685", "inhibit", "antibody"),
    ("CFTR", "MONDO_0009061", "activate", "small_molecule"),
    ("GLP1R", "MONDO_0005148", "activate", "peptide"),
    ("SCN9A", "EFO_0005762", "inhibit", "small_molecule"),
)


@dataclass(frozen=True)
class CaseDefinition(Frozen):
    symbol: str
    disease_id: str
    intended_action: str
    modality: str
    tissue: str | None
    case_id: str
    target_id: str | None = None
    hgnc_id: str | None = None


def _case_definitions(document):
    """Validate authored contemporary hypothesis scopes without biological inference."""
    if (not isinstance(document, dict) or type(document.get("schema_version")) is not int or
            document["schema_version"] != 1 or not isinstance(document.get("cases"), list) or
            not document["cases"]):
        raise ContractError("Case pack requires schema_version 1 and a nonempty cases array")
    if document.get("task", "T6") != "T6" or document.get("profile", "contemporary") != "contemporary":
        raise ContractError("Case packs support contemporary T6 hypotheses only")
    definitions, scopes, identifiers = [], set(), set()
    required = ("symbol", "disease_id", "intended_action", "modality", "tissue")
    for row in document["cases"]:
        if not isinstance(row, dict) or any(key not in row for key in required):
            raise ContractError("Every case requires symbol, disease_id, intended_action, modality and explicit tissue")
        if (row.get("task", "T6") != "T6" or row.get("profile", "contemporary") != "contemporary" or
                row.get("program") is not None or row.get("endpoint") is not None):
            raise ContractError("Case packs cannot introduce clinical programs, endpoints or historical profiles")
        for key in required[:-1]:
            value = row[key]
            if not isinstance(value, str) or not value or value != value.strip():
                raise ContractError("Case pack scope strings must be explicit and nonempty")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", row["symbol"]):
            raise ContractError("Case pack requires an explicit HGNC symbol")
        if not re.fullmatch(r"[A-Z][A-Z0-9]*_[0-9]+", row["disease_id"]):
            raise ContractError("Case pack requires an explicit canonical disease ID")
        if any(not re.fullmatch(r"[a-z][a-z0-9_]*", row[key]) for key in ("intended_action", "modality")):
            raise ContractError("Case pack actions/modalities require normalized lowercase tokens")
        tissue = row["tissue"]
        if tissue is not None and (not isinstance(tissue, str) or not tissue or tissue != tissue.strip()):
            raise ContractError("Case tissue must be null or an explicit nonempty value")
        scope = tuple(row[key] for key in required)
        if scope in scopes:
            raise ContractError("Duplicate complete hypothesis scope in case pack")
        scopes.add(scope)
        slug = f"{row['symbol'].lower()}-{row['disease_id'].lower()}-{row['intended_action']}-{row['modality']}"
        if tissue is not None:
            slug += "-tissue-" + fingerprint(tissue)[:16]
        case_id = row.get("case_id", slug)
        if not isinstance(case_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,199}", case_id):
            raise ContractError("Case pack case_id must be a safe lowercase directory name")
        if case_id in identifiers:
            raise ContractError("Duplicate case_id in case pack")
        identifiers.add(case_id)
        for key in ("target_id", "hgnc_id"):
            if key in row and (not isinstance(row[key], str) or not row[key] or row[key] != row[key].strip()):
                raise ContractError("Declared canonical identifiers must be explicit nonempty strings")
        definitions.append(CaseDefinition(row["symbol"], row["disease_id"], row["intended_action"],
            row["modality"], tissue, case_id, row.get("target_id"), row.get("hgnc_id")))
    return tuple(definitions)


def _load_case_pack(path, expected_sha256=None):
    if expected_sha256 is not None and not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
        raise ContractError("Case-pack SHA-256 anchor must be 64 lowercase hexadecimal characters")
    with path.open("rb") as stream:
        payload = stream.read(MAX_NORMALIZED_JSON_BYTES + 1)
    if len(payload) > MAX_NORMALIZED_JSON_BYTES:
        raise ContractError("Case pack exceeds the 64 MiB JSON limit")
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ContractError("Case pack differs from its frozen SHA-256 anchor")
    return _case_definitions(parse_json(payload)), payload, digest


def hypothesis_qualification(symbol):
    """Unresolved design fields only; no evaluator answers or inferred subtypes."""
    fields = ["disease_subtype", "population", "regimen", "endpoint"]
    fields += {"ERBB2": ["her2_biomarker_status"],
               "PCSK9": ["familial_hypercholesterolemia_subtype", "ldlr_function"],
               "CFTR": ["genotype", "protein_production", "modulator_mechanism"],
               "SCN9A": ["neuropathy_subtype"]}.get(symbol, [])
    return {key: {"value": None, "reason": "not_specified_in_development_case"} for key in fields}


@dataclass(frozen=True)
class InputFile(Frozen):
    dataset_id: str
    release_id: str
    relative_path: str
    receipt_path: str


@dataclass(frozen=True)
class InputManifest(Frozen):
    schema_version: int
    raw_root: str
    files: tuple[InputFile, ...]
    expected_counts: Mapping[str, int]
    missing_inputs: tuple[str, ...] = ()


def arrow():
    try:
        import pyarrow.parquet as pq
        import pyarrow
    except ImportError as error:
        raise ContractError("Ingestion requires: uv sync --python 3.11 --extra ingest") from error
    if pyarrow.__version__ != "21.0.0":
        raise ContractError("This ingestion recipe requires pyarrow==21.0.0")
    return pq


def peak_memory_bytes():
    import sys
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (key, ctypes.c_size_t) for key in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return int(counters.PeakWorkingSetSize)
        return None
    import resource
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform == "darwin" else value * 1024


def _inspect(manifest_path, catalog_path, progress=None):
    started = time.monotonic()
    manifest = decode(InputManifest, read_json(manifest_path))
    if manifest.schema_version != 2 or not Path(manifest.raw_root).is_absolute():
        raise ContractError("Input manifest requires v2 and an explicit absolute raw_root")
    policy = catalog_index(read_json(catalog_path))
    root = Path(manifest.raw_root).resolve()
    pq = arrow()
    verified, excluded, missing, seen = [], [], list(manifest.missing_inputs), set()
    for number, item in enumerate(manifest.files, 1):
        if progress and (number == 1 or number % 64 == 0):
            progress("inspection", checked_files=number - 1, total_files=len(manifest.files),
                     verified_files=len(verified))
        if item.dataset_id not in DATASETS:
            raise ContractError("Pilot accepts only pinned Open Targets and HGNC products")
        if item.dataset_id.startswith("ot_") and item.release_id != "25.09" or (
                item.dataset_id == "hgnc_symbols" and item.release_id != "snapshot_2026-10-10"):
            raise ContractError("Pilot source version mismatch; newer/older substitution is forbidden")
        check_role(item.dataset_id, "reference" if item.dataset_id == "hgnc_symbols" else "agent_evidence", policy)
        path, receipt_path = safe_child(root, item.relative_path), safe_child(root, item.receipt_path)
        if str(path) in seen:
            raise ContractError("Duplicate raw input path")
        seen.add(str(path))
        if "sourceId=chembl" in item.relative_path.replace("\\", "/").split("/"):
            excluded.append({"path": item.relative_path, "reason": "excluded_clinical_partition"})
            continue
        if path.name.endswith(".partial") or not path.is_file() or not receipt_path.is_file():
            missing.append(item.relative_path)
            continue
        if receipt_path.stat().st_size > 64 * 1024 * 1024:
            raise ContractError("Download receipt exceeds the JSON size limit")
        receipt_bytes = receipt_path.read_bytes()
        receipt = parse_json(receipt_bytes)
        if (receipt.get("status") != "completed" or receipt.get("dataset_id") != item.dataset_id or
                receipt.get("release_id") != item.release_id or
                safe_child(root, receipt.get("relative_path", "")) != path or
                receipt.get("bytes") != path.stat().st_size):
            raise ContractError("Receipt identity/status/size mismatch")
        digest = sha256_file(path)
        if digest != receipt.get("sha256"):
            raise ContractError("Raw input receipt checksum mismatch")
        completed = decode(datetime, receipt.get("completed_at_utc"))
        url = receipt.get("url", "")
        if not url.startswith(("https://ftp.ebi.ac.uk/", "https://storage.googleapis.com/public-download-files/hgnc/")):
            raise ContractError("Receipt is not an approved public-source download")
        if item.dataset_id == "hgnc_symbols":
            with path.open(encoding="utf-8-sig", newline="") as stream:
                columns = next(csv.reader(stream, delimiter="\t"))
            required = {"hgnc_id", "symbol", "status", "ensembl_gene_id"}
            rows = None
        else:
            parquet = pq.ParquetFile(path)
            columns, rows = parquet.schema_arrow.names, parquet.metadata.num_rows
            required = ({"id", "approvedSymbol"} if item.dataset_id == "ot_target" else
                        {"id", "name"} if item.dataset_id == "ot_disease" else
                        {"id", "targetId", "diseaseId", "datasourceId", "datatypeId", "score"})
            import pyarrow as pa
            for name in required - {"score"}:
                if name in columns and not (pa.types.is_string(parquet.schema_arrow.field(name).type) or
                                            pa.types.is_large_string(parquet.schema_arrow.field(name).type)):
                    raise ContractError(f"Unexpected raw identifier type: {name}")
            if "score" in required and "score" in columns:
                score_type = parquet.schema_arrow.field("score").type
                if not (pa.types.is_floating(score_type) or pa.types.is_integer(score_type)):
                    raise ContractError("Provider evidence score must be numeric")
        if required - set(columns):
            raise ContractError(f"Required raw columns missing in {item.dataset_id}: {sorted(required - set(columns))}")
        receipt_sha = hashlib.sha256(receipt_bytes).hexdigest()
        node = SourceNode("raw-" + fingerprint({"dataset": item.dataset_id, "release": item.release_id,
                                               "sha256": digest, "path": item.relative_path})[:24],
            item.dataset_id, item.release_id, item.relative_path.replace("\\", "/"), digest,
            "reference" if item.dataset_id == "hgnc_symbols" else "agent_evidence",
            Availability(None, None, None, None, completed.date(), "public_download_receipt",
                         "Known public by download observation; earliest publisher availability remains unknown",
                         completed, receipt_sha), TemporalClass.CONTEMPORARY, url,
            receipt_path=item.receipt_path.replace("\\", "/"), receipt_sha256=receipt_sha)
        verified.append({"node": node, "path": path, "columns": tuple(columns), "rows": rows,
                         "bytes": path.stat().st_size, "schema_sha256": fingerprint(tuple(columns)),
                         "receipt_bytes": receipt_bytes})
    counts = Counter(row["node"].dataset_id for row in verified)
    if any(type(value) is not int or value < counts[key] for key, value in manifest.expected_counts.items()):
        raise ContractError("Invalid expected source counts")
    complete = bool(manifest.expected_counts) and not missing and all(
        counts[key] == value for key, value in manifest.expected_counts.items())
    report = {"schema_version": 2, "status": "inspected", "manifest_sha256": sha256_file(manifest_path),
              "catalog_sha256": sha256_file(catalog_path), "selected_files": len(verified),
              "selected_bytes": sum(row["bytes"] for row in verified), "dataset_counts": dict(counts),
              "source_completeness": "complete" if complete else "selected_subset",
              "missing_inputs": sorted(set(missing)), "excluded_files": excluded,
              "files": [{"source": row["node"], "columns": row["columns"], "rows": row["rows"],
                         "bytes": row["bytes"], "schema_sha256": row["schema_sha256"]} for row in verified],
              "elapsed_seconds": time.monotonic() - started, "peak_memory_bytes": peak_memory_bytes(),
              "scientific_validation": "not_run"}
    if progress:
        progress("inspection", checked_files=len(manifest.files), total_files=len(manifest.files),
                 verified_files=len(verified))
    return manifest, verified, report


def inspect_sources(manifest_path: Path, catalog_path: Path):
    return _inspect(manifest_path, catalog_path)[2]


def _archive_receipts(root, files):
    """Preserve the exact inspected bytes, independent of mutable transport receipts."""
    for item in files:
        payload, node = item["receipt_bytes"], item["node"]
        relative = "manifests/receipt-archive/" + node.receipt_sha256 + ".json"
        destination = safe_child(root, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            descriptor, temporary_name = tempfile.mkstemp(prefix=".receipt-", dir=destination.parent)
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                try:
                    # Publish complete bytes atomically without replacing an existing archive.
                    os.link(temporary, destination)
                except FileExistsError:
                    pass
            finally:
                temporary.unlink(missing_ok=True)
        if destination.read_bytes() != payload:
            raise ContractError("Content-addressed receipt archive has conflicting bytes")
        item["node"] = replace(node, receipt_path=relative)


def _rows(item, columns, *, pairs=None, counters=None, progress=None):
    pq = arrow()
    parquet = pq.ParquetFile(item["path"])
    projection = [name for name in columns if name in item["columns"]]
    if pairs is not None:
        import pyarrow as pa
        import pyarrow.compute as pc
        targets = pa.array(sorted({pair[0] for pair in pairs}), type=pa.string())
        diseases = pa.array(sorted({pair[1] for pair in pairs}), type=pa.string())
    for group in range(parquet.num_row_groups):
        offset = 0
        for batch in parquet.iter_batches(row_groups=[group], columns=projection, batch_size=65536):
            count = batch.num_rows
            if counters is not None:
                counters["physical_rows_scanned"] += count
                counters["scanned_rows"] += count  # Retained report alias.
            if pairs is None:
                indices, selected = range(count), batch
            else:
                mask = pc.and_(pc.is_in(batch.column("targetId"), value_set=targets),
                               pc.is_in(batch.column("diseaseId"), value_set=diseases))
                indices = pc.indices_nonzero(mask)
                selected = batch.take(indices)
                indices = indices.to_pylist()
            for index, row in zip(indices, selected.to_pylist()):
                if pairs is not None and (row.get("targetId"), row.get("diseaseId")) not in pairs:
                    continue
                if counters is not None:
                    counters["selected_rows"] += 1
                yield row, {"source_id": item["node"].source_id, "row_group": group, "row": offset + index}
            offset += count
            if progress:
                progress()


def _json_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if type(value) is float and not math.isfinite(value):
        raise ContractError("nonfinite_provider_metric")
    return value


def _publication(row, cutoff):
    published, year, unknown = None, None, {}
    raw_year = row.get("publicationYear")
    if raw_year is not None:
        if type(raw_year) is int or isinstance(raw_year, str) and raw_year.isdigit():
            year = int(raw_year)
            if year > cutoff.year:
                return None, year, unknown, "publication_after_origin"
        else:
            unknown["publication_year"] = "unparseable_provider_value"
    for name in ("publicationDate", "evidenceDate", "releaseDate"):
        raw = row.get(name)
        if raw is None:
            continue
        try:
            if isinstance(raw, datetime):
                if raw.tzinfo is not None and raw > cutoff:
                    return None, year, unknown, "publication_after_origin"
                value = raw.date()
            elif isinstance(raw, date):
                value = raw
            else:
                value = date.fromisoformat(str(raw)[:10])
                if "T" in str(raw):
                    exact = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                    if exact.tzinfo and exact > cutoff:
                        return None, year, unknown, "publication_after_origin"
            if value > cutoff.date():
                return value, year, unknown, "publication_after_origin"
            if name == "publicationDate":
                published = value
        except ValueError:
            unknown[name] = "unparseable_provider_value"
    return published, year, unknown, None


def _packet_groups(observations, layout):
    """Preserve order and whole records; account for commas, envelope and newline."""
    if layout == "single":
        if len(canonical(EvidencePacket(2, observations))) + 1 > MAX_NORMALIZED_JSON_BYTES:
            raise ContractError("Oversized evidence packet; no silent truncation is permitted")
        return [observations]
    envelope = len(canonical(EvidencePacket(2, ()))) + 1
    groups, current, size = [], [], envelope
    for observation in observations:
        encoded_size = len(canonical(observation))
        if envelope + encoded_size > MAX_NORMALIZED_JSON_BYTES:
            raise ContractError("Oversized single observation; no splitting or truncation is permitted")
        increment = encoded_size + bool(current)
        if size + increment > MAX_NORMALIZED_JSON_BYTES:
            groups.append(tuple(current))
            current, size = [], envelope
            increment = encoded_size
        current.append(observation)
        size += increment
    if current or not groups:
        groups.append(tuple(current))
    return groups


def build_snapshot(manifest_path: Path, catalog_path: Path, output: Path, *, packet_layout="single",
                   cases_path: Path | None = None, cases_sha256: str | None = None):
    """Reserve first; every later stage leaves inspectable, non-retrying records."""
    journal = RunJournal(output, kind="build")
    started = time.monotonic()
    cutoff = datetime.now(timezone.utc)
    state = {"stage": "reservation", "counters": Counter()}
    try:
        custom = {"cases_path": str(cases_path.resolve()), "cases_sha256": cases_sha256} if cases_path else {}
        journal.append("build_request", manifest_path=str(manifest_path.resolve()),
                       catalog_path=str(catalog_path.resolve()), origin_at_utc=cutoff, packet_layout=packet_layout, **custom)
        if packet_layout not in ("single", "bounded"):
            raise ContractError("Unknown evidence packet layout")
        if cases_sha256 is not None and cases_path is None:
            raise ContractError("A case-pack SHA-256 anchor requires an explicit case pack")
        return _build_snapshot(manifest_path, catalog_path, output, journal, state, started, cutoff,
                               packet_layout, cases_path, cases_sha256)
    except BaseException as error:
        failure = {"schema_version": 2, "status": "interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
                   "stage": state["stage"], "error_class": type(error).__name__, "message": str(error),
                   "elapsed_seconds": time.monotonic() - started, "counters": dict(state["counters"]),
                   "recovery_action": "inspect only; replacement builds require a new output directory"}
        try:
            journal.fail(error, state["stage"])
        except OSError:
            pass  # A readable durable journal prefix remains if the device stopped accepting writes.
        try:
            write_json(output / "build-failure.json", failure)
        except OSError:
            pass
        raise
    finally:
        journal.close()


def _build_snapshot(manifest_path, catalog_path, output, journal, state, started, cutoff, packet_layout,
                    cases_path=None, cases_sha256=None):
    def stage(name):
        state["stage"] = name
        journal.append("build_stage", stage=name, elapsed_seconds=time.monotonic() - started)

    last_progress = time.monotonic()

    def progress(phase, **values):
        nonlocal last_progress
        journal.append("build_progress", stage=phase, elapsed_seconds=time.monotonic() - started,
                       counters=dict(state["counters"]), **values)
        last_progress = time.monotonic()

    case_pack = None
    if cases_path is not None:
        stage("case_pack_validation")
        definitions, payload, digest = _load_case_pack(cases_path, cases_sha256)
        with (output / "case-pack.json").open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        case_pack = {"path": "case-pack.json", "sha256": digest,
                     "scopes_sha256": fingerprint(definitions), "cases": len(definitions)}
        journal.append("build_case_pack_frozen", source_path=str(cases_path.resolve()), **case_pack)
    else:
        definitions = _case_definitions({"schema_version": 1, "cases": [
            {"symbol": symbol, "disease_id": disease, "intended_action": action,
             "modality": modality, "tissue": None} for symbol, disease, action, modality in PILOT]})
    stage("inspection")
    manifest, files, inspection = _inspect(manifest_path, catalog_path, progress)
    stage("receipt_archival")
    _archive_receipts(Path(manifest.raw_root).resolve(), files)
    for item, inspected in zip(files, inspection["files"]):
        inspected["source"] = item["node"]
    write_json(output / "inspection.json", inspection)
    journal.append("build_inspected", manifest_sha256=inspection["manifest_sha256"],
                   catalog_sha256=inspection["catalog_sha256"], inspection_sha256=sha256_file(output / "inspection.json"),
                   selected_files=len(files), selected_bytes=inspection["selected_bytes"])
    stage("identifier_resolution")
    policy = catalog_index(read_json(catalog_path))
    check_role("asof_normalized_packets", "agent_evidence", policy)
    wanted_symbols = {item.symbol for item in definitions}
    wanted_diseases = {item.disease_id for item in definitions}
    hgnc, targets, diseases = {}, {}, {}
    hg_item = None
    for item in files:
        if item["node"].availability.exclusion(cutoff):
            raise ContractError("Selected raw input was not available at the frozen cutoff")
        if item["node"].dataset_id == "hgnc_symbols":
            if hg_item is not None:
                raise ContractError("Pilot requires one pinned HGNC snapshot")
            hg_item = item
            with item["path"].open(encoding="utf-8-sig", newline="") as stream:
                for number, row in enumerate(csv.DictReader(stream, delimiter="\t")):
                    if row["symbol"] in wanted_symbols and row["status"] == "Approved":
                        if row["symbol"] in hgnc:
                            raise ContractError("Ambiguous approved HGNC symbol")
                        hgnc[row["symbol"]] = (row, {"source_id": item["node"].source_id, "row": number})
    ids = {row[0]["ensembl_gene_id"] for row in hgnc.values()}
    for item in files:
        kind = item["node"].dataset_id
        if kind == "ot_target":
            for row, locator in _rows(item, ("id", "approvedSymbol", "approvedName", "biotype")):
                if row["id"] in ids:
                    if row["id"] in targets and targets[row["id"]][0] != row:
                        raise ContractError("Conflicting target identifier records")
                    targets[row["id"]] = (row, locator)
        if kind == "ot_disease":
            for row, locator in _rows(item, ("id", "name")):
                if row["id"] in wanted_diseases:
                    if row["id"] in diseases and diseases[row["id"]][0] != row:
                        raise ContractError("Conflicting disease identifier records")
                    diseases[row["id"]] = (row, locator)
    jobs, blocked = [], []
    nodes = {item["node"].source_id: item["node"] for item in files}
    for definition in definitions:
        symbol, disease_id, action, modality = (definition.symbol, definition.disease_id,
            definition.intended_action, definition.modality)
        slug = definition.case_id
        row = hgnc.get(symbol)
        target_id = row[0]["ensembl_gene_id"] if row else None
        if (not target_id or target_id not in targets or disease_id not in diseases or
                targets[target_id][0]["approvedSymbol"] != symbol or
                definition.target_id is not None and definition.target_id != target_id or
                definition.hgnc_id is not None and (not row or definition.hgnc_id != row[0]["hgnc_id"])):
            blocked.append({"case_id": slug, "reason": "canonical_identifier_missing_or_conflicting"})
            continue
        mapping_refs = tuple(sorted({row[1]["source_id"], targets[target_id][1]["source_id"], diseases[disease_id][1]["source_id"]}))
        public_by = max(nodes[key].availability.known_public_by for key in mapping_refs)
        availability = Availability(None, None, None, None, cutoff.date(), "verified_mapping_inputs",
            "Contemporary mapping only", public_by, fingerprint(tuple(nodes[key] for key in mapping_refs)))
        target_version = "OpenTargets-25.09:target:" + nodes[targets[target_id][1]["source_id"]].sha256
        disease_version = "OpenTargets-25.09:disease:" + nodes[diseases[disease_id][1]["source_id"]].sha256
        case = Case(2, slug, "T6", cutoff.date(), Hypothesis(target_id, disease_id, target_version,
                    disease_version, action, modality, definition.tissue, availability), None, None, cutoff)
        case.validate()
        jobs.append({"case": case, "symbol": symbol, "disease_name": diseases[disease_id][0]["name"],
                     "mapping_refs": mapping_refs, "observations": [], "rejections": [], "seen": {}})
    pairs = {(job["case"].hypothesis.target_id, job["case"].hypothesis.indication_id) for job in jobs}
    jobs_by_pair = {pair: [job for job in jobs if (job["case"].hypothesis.target_id,
                    job["case"].hypothesis.indication_id) == pair] for pair in pairs}
    counters = state["counters"]
    unsupported_types = Counter()
    counters.update({key: 0 for key in ("physical_rows_scanned", "scanned_rows", "selected_rows", "matched_rows",
                    "accepted_source_rows", "normalized_case_records", "evidence_files_scanned")})
    stage("evidence_normalization")

    def batch_progress():
        if time.monotonic() - last_progress >= 5:
            progress("evidence_normalization", total_evidence_files=inspection["dataset_counts"].get("ot_evidence", 0))

    for item in files:
        if item["node"].dataset_id != "ot_evidence":
            continue
        for raw, locator in _rows(item, EVIDENCE_COLUMNS, pairs=pairs, counters=counters, progress=batch_progress):
            pair = (raw.get("targetId"), raw.get("diseaseId"))
            counters["matched_rows"] += 1
            matching = jobs_by_pair[pair]
            source, datatype = raw.get("datasourceId"), raw.get("datatypeId")
            reason = ("excluded_clinical_evidence" if source == "chembl" or datatype == "known_drug" else
                      "unsupported_datatype" if datatype not in TYPE_CATEGORIES else None)
            published, year, date_unknown, date_reason = _publication(raw, cutoff)
            reason = reason or date_reason
            if not raw.get("id") or not source:
                reason = reason or "missing_evidence_identity"
            try:
                row = _json_value(raw)
            except ContractError as error:
                row, reason = {}, str(error)
            if reason:
                counters[reason] += 1
                if reason == "unsupported_datatype":
                    unsupported_types[str(datatype)] += 1
                for job in matching:
                    job["rejections"].append({"source_locator": locator, "evidence_id": raw.get("id"),
                                              "datasource_id": source, "datatype_id": datatype, "reason": reason})
                continue
            accepted = False
            for job in matching:
                raw_id = str(raw["id"])
                observation_id = "ot25:" + str(source) + ":" + raw_id
                payload_hash = fingerprint(row)
                if observation_id in job["seen"]:
                    if job["seen"][observation_id] != payload_hash:
                        raise ContractError("Conflicting duplicate provider evidence ID")
                    counters["identical_duplicates_coalesced"] += 1
                    continue
                job["seen"][observation_id] = payload_hash
                missing = {"species": "not_verified_from_source_model_context", "effect_scale": "unverified_source_scale",
                           "scientific_interpretation": "unreviewed", "tissue": "not_canonically_resolved_from_source_context"}
                for name in ("study_id", "cohort"):
                    if not raw.get({"study_id": "studyId", "cohort": "cohortId"}.get(name, name)):
                        missing[name] = "not_supplied_by_source"
                ancestry = raw.get("ancestry") if isinstance(raw.get("ancestry"), str) and raw.get("ancestry") else None
                if ancestry is None:
                    missing["ancestry"] = "not_supplied_by_source" if not raw.get("ancestry") else "unresolved_provider_value"
                missing.update(date_unknown)
                study = str(raw["studyId"]) if raw.get("studyId") is not None else None
                cohort = str(raw["cohortId"]) if raw.get("cohortId") is not None else None
                statement = (f"Open Targets 25.09 record {raw_id} from {source} links {job['symbol']} "
                             f"({pair[0]}) to {job['disease_name']} ({pair[1]}); datatype {datatype}; "
                             f"provider evidence score {raw.get('score')}. This is a resource annotation.")
                metrics = {key: value for key, value in row.items() if key not in (
                    "id", "targetId", "diseaseId", "datasourceId", "datatypeId")}
                observation = Observation(observation_id, pair[0], pair[1], None, TYPE_CATEGORIES[datatype],
                    "integrated", statement, EvidenceStatus.OBSERVED, Polarity.UNCERTAIN, "uncertain",
                    (str(source) + ":" + study) if study else None,
                    (str(source) + ":cohort:" + cohort) if cohort else (str(source) + ":study:" + study) if study else None,
                    ScientificContext(None, ancestry, None, None, None, None,
                                      (str(source) + ":" + cohort,) if cohort else ()),
                    QuantitativeResult(None, None, None, None, None, None, None),
                    Method("asof.opentargets.normalize", NORMALIZATION_VERSION, {"projection": tuple(row), "source_row_sha256": payload_hash,
                           "interpretation_scope": "resource_annotation_only", "scientific_validation": "not_run"}, "passed", (
                        "Contract/field normalization checked; scientific interpretation is unreviewed",
                        "Provider score is descriptive and is not an effect size or prediction feature")),
                    item["node"].availability, {}, None,
                    tuple(sorted(set(job["mapping_refs"]) | {item["node"].source_id})), None,
                    {**locator, "evidence_id": raw_id, "datasource_id": source}, metrics, missing, published, year)
                job["observations"].append(observation)
                counters["normalized_case_records"] += 1
                accepted = True
            if accepted:
                counters["accepted_source_rows"] += 1
        counters["evidence_files_scanned"] += 1
        if counters["evidence_files_scanned"] % 64 == 0:
            progress("evidence_normalization", total_evidence_files=inspection["dataset_counts"].get("ot_evidence", 0))
    progress("evidence_normalization", total_evidence_files=inspection["dataset_counts"].get("ot_evidence", 0))
    recipe = {"method": "asof.opentargets.normalize", "version": NORMALIZATION_VERSION,
              "projection": EVIDENCE_COLUMNS, "code_sha256": sha256_file(Path(__file__)),
              "packet_encoding": "canonical_json", "packet_layout": packet_layout,
              "packet_limit_bytes": MAX_NORMALIZED_JSON_BYTES}
    if case_pack is not None:
        recipe["case_pack"] = case_pack
    bundle_id = "contemporary-" + fingerprint({"cutoff": cutoff, "manifest": inspection["manifest_sha256"],
                                              "recipe": recipe})[:16]
    cases_report = []
    stage("packet_finalization")
    for job in jobs:
        case, observations = job["case"], tuple(job["observations"])
        case_dir = output / case.case_id
        case_dir.mkdir()
        groups = _packet_groups(observations, packet_layout)
        packets, artifacts = [], []
        for number, group in enumerate(groups, 1):
            suffix = "" if len(groups) == 1 else f"-{number:04d}"
            packet_path = case_dir / f"evidence{suffix}.json"
            write_json(packet_path, EvidencePacket(2, group), compact=True)
            if packet_path.stat().st_size > MAX_NORMALIZED_JSON_BYTES:
                raise ContractError("Evidence packet exceeds 64 MiB")
            digest = sha256_file(packet_path)
            packet_refs = tuple(sorted(set(job["mapping_refs"]) | {ref for obs in group for ref in obs.input_refs}))
            artifacts.append(Artifact("packet-" + case.case_id + suffix, "asof_normalized_packets", bundle_id,
                packet_path.name, digest, "agent_evidence", True, TemporalClass.CONTEMPORARY,
                case.hypothesis.availability, "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/25.09/", packet_refs))
            packets.append({"path": packet_path.name, "sha256": digest, "bytes": packet_path.stat().st_size,
                            "observations": len(group)})
        refs = tuple(sorted(set(job["mapping_refs"]) | {ref for observation in observations for ref in observation.input_refs}))
        coverage = {"source_completeness": inspection["source_completeness"],
                    "expected_counts": manifest.expected_counts, "selected_counts": inspection["dataset_counts"],
                    "missing_input_count": len(inspection["missing_inputs"]), "rejected_records": len(job["rejections"]),
                    "matching_observations": len(observations), "absence_claim": False,
                    "evidence_categories": dict(Counter(observation.category.value for observation in observations)),
                    "rejection_reasons": dict(Counter(record["reason"] for record in job["rejections"])),
                    "unknown_context": {field: sum(getattr(observation.context, field) is None for observation in observations)
                                        for field in ("species", "ancestry", "tissue")},
                    "scientific_interpretation": "unreviewed",
                    "interpretation_scope": "resource_annotation_only",
                    "therapeutic_relevance": "not_assessed", "hypothesis_refined": False,
                    "hypothesis_qualification": hypothesis_qualification(job["symbol"]),
                    "review_context_nonempty": {field: sum(observation.source_metrics.get(field) not in (None, (), "")
                        for observation in observations) for field in REVIEW_CONTEXT_COLUMNS}}
        if case_pack is not None:
            coverage["case_pack"] = case_pack
        snapshot = Snapshot(2, bundle_id + ":" + case.case_id, Profile.CONTEMPORARY, case.origin, False,
            tuple(artifacts),
            tuple(nodes[ref] for ref in refs), manifest.raw_root, coverage, case.origin_at)
        write_json(case_dir / "case.json", case)
        write_json(case_dir / "snapshot.json", snapshot)
        write_json(case_dir / "rejections.json", job["rejections"])
        write_json(case_dir / "identifier-validation.json", {
            "symbol": job["symbol"], "hgnc": hgnc[job["symbol"]],
            "target": targets[case.hypothesis.target_id], "disease": diseases[case.hypothesis.indication_id]})
        cases_report.append({"case_id": case.case_id, "hypothesis_key": case.hypothesis.key,
                             "observations": len(observations), "packet_bytes": sum(p["bytes"] for p in packets),
                             "packet_sha256": packets[0]["sha256"] if len(packets) == 1 else None,
                             "packets": packets, "input_sources": len(refs)})
        journal.append("build_case_written", **cases_report[-1])
    # Inputs are independently rechecked after scanning so concurrent source changes fail closed.
    stage("source_recheck")
    if case_pack is not None:
        if (sha256_file(cases_path) != case_pack["sha256"] or
                sha256_file(output / case_pack["path"]) != case_pack["sha256"]):
            raise ContractError("Case pack changed during snapshot build")
    for number, item in enumerate(files, 1):
        if sha256_file(item["path"]) != item["node"].sha256:
            raise ContractError("Raw input changed during snapshot build")
        archived = safe_child(Path(manifest.raw_root).resolve(), item["node"].receipt_path)
        if sha256_file(archived) != item["node"].receipt_sha256:
            raise ContractError("Archived receipt changed during snapshot build")
        if number % 64 == 0 or number == len(files):
            progress("source_recheck", checked_files=number, total_files=len(files))
    stage("report_finalization")
    report = {"schema_version": 2, "snapshot_id": bundle_id, "origin_at_utc": cutoff,
              "status": "built" if not blocked else "built_with_blocked_cases", "cases": cases_report,
              "blocked_cases": blocked, "counters": dict(counters), "inspection": {
                  key: value for key, value in inspection.items() if key != "files"},
              "unsupported_datatypes": dict(unsupported_types),
              "elapsed_seconds": time.monotonic() - started, "peak_memory_bytes": peak_memory_bytes(),
              "output_bytes": sum(path.stat().st_size for path in output.rglob("*.json")),
              "normalization_recipe": recipe,
              "scientific_validation": "not_run", "probabilities": "withheld"}
    if case_pack is not None:
        report["case_pack"] = case_pack
    write_json(output / "build-report.json", report)
    journal.append("build_completed", report_sha256=sha256_file(output / "build-report.json"),
                   cases=len(cases_report), blocked_cases=len(blocked), counters=dict(counters),
                   elapsed_seconds=time.monotonic() - started)
    return report
