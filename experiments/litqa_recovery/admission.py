"""Admit recovered sources without turning an interrupted request into evidence.

``prepare`` and ``revalidate`` perform whole-collection replay at operation
boundaries. ``capture`` rechecks only its question's original source/provenance
files. The caller must revalidate before publishing a successful answer operation.
This is trusted local Python, not an operating-system security boundary.
"""
from collections.abc import Mapping
from datetime import datetime, timezone
import math
from pathlib import Path
import time

from tether_engine.serde import canonical, encode, fingerprint, freeze, parse_json
from tether_engine.study.stable_read import read_file, stable_files
from experiments.labbench.native_contract import validate_query
from experiments.litqa_comparison import codecs, selection, transport
from experiments.litqa_comparison.admission import CapturedContext, check
from experiments.litqa_supplied import admission as supplied, resolver
from experiments.litqa_recovery import collection, plan

_ISSUED = object()
_ROW_FIELDS = {"ordinal", "id", "branch", "disposition", "resolution", "parent_proofs", "coverage", "accounting"}
_RESOLVED = ("adopt_completed", "newly_completed")
_UNCERTAIN = "inherited_uncertain_metadata"


class PreparedCollection:
    """Copied immutable state issued only after an anchored collection replay."""
    __slots__ = ("_state", "_queries", "_hints", "_rows", "_fingerprint", "_issued")

    def __init__(self, *args, **kwargs):
        raise TypeError("Use prepare() with an externally anchored collection")

    def __setattr__(self, name, value):
        raise AttributeError("Prepared collection is immutable")

    @property
    def manifest(self): return self._state["manifest"]
    @property
    def queries(self): return self.manifest["answer_queries"]
    @property
    def hints(self): return self.manifest["hints"]
    @property
    def receipt(self): return self._state["receipt"]
    @property
    def root(self): return self._state["root"]
    @property
    def common_root(self): return self._state["common_root"]
    @property
    def collection_identity(self):
        return freeze(dict(receipt=self.receipt, manifest_sha256=fingerprint(self.manifest),
                           parent_identity=self.manifest["parent_identity"], prepared_sha256=self._fingerprint))


def _deadline(value, seconds):
    end = time.monotonic() + seconds if value is None else value
    codecs.need(type(end) in (int, float) and math.isfinite(end) and time.monotonic() < end,
                "Finite unexpired admission deadline required")
    return end


def _bound(proof, root, end):
    codecs.need(isinstance(proof, Mapping) and set(proof) == {"path", "bytes", "sha256"}
                and type(proof["bytes"]) is int and 0 <= proof["bytes"] <= plan.MAX_FILE_BYTES,
                "Exact recovered provenance proof required")
    plan._sha(proof["sha256"])
    path = plan._absolute(proof["path"])
    codecs.need(path.is_relative_to(root) and path != root, "Operational/source proof outside common study root")
    raw = read_file(path, end, plan.MAX_FILE_BYTES)
    codecs.need(len(raw) == proof["bytes"] and codecs.digest(raw) == proof["sha256"],
                "Recovered provenance bytes changed")
    return raw


def _state(result, output, common_root):
    codecs.need(isinstance(result, Mapping) and result.get("status") == "independently_reconstructed"
                and result.get("scientific_support_verified") is False
                and result.get("model_or_http_execution_performed") is False,
                "Source-inclusive collection reconstruction required")
    manifest = result["manifest"]
    codecs.need(isinstance(manifest, Mapping) and manifest.get("schema_version") == 2
                and manifest.get("kind") == "sc04_recovered_collection_v2" and manifest.get("status") == "complete"
                and manifest.get("ordinary_retrieval") is False and manifest.get("automatic_retry") is False
                and manifest.get("scientific_support_verified") is False,
                "Recovered collection role/version mismatch")
    original = plan._absolute(manifest["original_root"])
    codecs.need(original.is_relative_to(common_root) and original != common_root
                and output.is_relative_to(common_root) and output != common_root,
                "Original and recovered collections require a common study root")
    dois, queries, hints, rows = (manifest[k] for k in ("doi_schedule", "answer_queries", "hints", "records"))
    codecs.need(0 < len(dois) <= 190 and len(set(dois)) == len(dois) and len(rows) == len(dois),
                "Complete unique recovered DOI schedule required")
    for doi in dois: resolver.identity(doi)
    codecs.need(0 < len(queries) <= 199 and len(queries) == len(hints), "Complete recovered question/hint schedule required")
    by_query, by_hint = {}, {}
    for query, hint in zip(queries, hints):
        query = validate_query(query)
        codecs.need(query["id"] not in by_query and isinstance(hint, Mapping)
                    and set(hint) == {"id", "question", "dois"} and hint["id"] == query["id"]
                    and hint["question"] == query["question"] and 1 <= len(hint["dois"]) <= 2
                    and len(set(hint["dois"])) == len(hint["dois"]), "Recovered hint identity/role mismatch")
        by_query[query["id"]], by_hint[query["id"]] = query, hint
    codecs.need({d for h in hints for d in h["dois"]} == set(dois), "Question/hint and DOI cohorts differ")
    execution = parse_json(collection.bound(encode(manifest["execution_frame"])))
    codecs.need(execution.get("purpose") in ("production", "fictional_qualification"), "Explicit recovered collection purpose")
    if execution["purpose"] == "production":
        codecs.need((len(dois), len(queries), sum(len(h["dois"]) for h in hints)) == (190, 199, 205),
                    "Complete production 190/199/205 cohort required")
    by_doi = {}
    for index, (doi, row) in enumerate(zip(dois, rows)):
        codecs.need(isinstance(row, Mapping) and set(row) == _ROW_FIELDS and row["ordinal"] == index
                    and type(row["ordinal"]) is int and row["id"] == doi and row["branch"] == "shared",
                    "Exact recovered row identity/role required")
        if row["disposition"] in _RESOLVED:
            resolution = row["resolution"]
            codecs.need(isinstance(resolution, Mapping) and set(resolution) == {"root", "receipt_sha256", "plan"}
                        and resolution["plan"]["doi"] == doi, "Resolved original source descriptor required")
            location = plan._absolute(resolution["root"])
            codecs.need(location.is_relative_to(common_root) and location != common_root, "Resolved source outside common study root")
        else:
            codecs.need(row["disposition"] == _UNCERTAIN and row["resolution"] is None
                        and row["coverage"].get("article_retained") is None
                        and row["coverage"].get("exact_doi_resolved") is None
                        and row["coverage"].get("source_availability") == "unknown",
                        "Inherited uncertainty cannot become a completed or absent source")
        by_doi[doi] = row
    codecs.need(canonical(by_doi) == canonical(result["by_doi"]), "Replayed collection row index differs")
    receipt = result["receipt"]
    codecs.need(Path(receipt["path"]) == output / "RECEIPT.json", "Collection receipt locator differs")
    return freeze(dict(root=str(output), common_root=str(common_root), receipt=receipt, manifest=manifest))


def _trusted(prepared):
    codecs.need(type(prepared) is PreparedCollection and getattr(prepared, "_issued", None) is _ISSUED,
                "Prepared collection capability required; raw replay dictionaries are not admitted")
    codecs.need(fingerprint(prepared._state) == prepared._fingerprint, "Prepared collection state changed")
    return prepared


def prepare(output, receipt_sha, common_root, *, deadline=None):
    """Replay the entire collection once and copy its immutable solver state."""
    end = _deadline(deadline, 1800)
    output, common_root = plan._absolute(output), plan._absolute(common_root)
    result = collection.replay(output, receipt_sha)
    state = _state(result, output, common_root)
    codecs.need(state["receipt"]["sha256"] == receipt_sha, "Prepared external receipt anchor differs")
    _deadline(end, 0)
    prepared = object.__new__(PreparedCollection)
    object.__setattr__(prepared, "_state", state)
    object.__setattr__(prepared, "_queries", freeze({q["id"]: q for q in state["manifest"]["answer_queries"]}))
    object.__setattr__(prepared, "_hints", freeze({h["id"]: h for h in state["manifest"]["hints"]}))
    object.__setattr__(prepared, "_rows", freeze({r["id"]: r for r in state["manifest"]["records"]}))
    object.__setattr__(prepared, "_fingerprint", fingerprint(state))
    object.__setattr__(prepared, "_issued", _ISSUED)
    return prepared


def revalidate(prepared, *, deadline=None):
    """Mandatory operation-end replay; this never restarts a request."""
    prepared = _trusted(prepared)
    end = _deadline(deadline, 1800)
    observed = collection.replay(prepared.root, prepared.receipt["sha256"])
    state = _state(observed, Path(prepared.root), Path(prepared.common_root))
    codecs.need(canonical(state) == canonical(prepared._state), "Collection changed during the answer operation")
    _deadline(end, 0)
    return freeze(dict(status="independently_revalidated", collection_identity=prepared.collection_identity,
                       model_or_http_execution_performed=False))


def _operational(row, common_root, end):
    parents = row["parent_proofs"]
    if row["disposition"] in _RESOLVED:
        expected = {"receipt", "manifest"} | ({"original_slot"} if row["disposition"] == "adopt_completed" else set())
        codecs.need(set(parents) == expected, "Resolved operational parent proofs differ")
        for proof in parents.values(): _bound(proof, common_root, end)
    else:
        codecs.need(set(parents) == {"plan", "journal", "reservation", "response_proof", "terminal_proof"}
                    and parents["response_proof"] is None and parents["terminal_proof"] is None,
                    "Uncertain source has an invented response or terminal proof")
        value = parse_json(_bound(parents["plan"], common_root, end))
        resolver.validate_plan(value)
        codecs.need(value["doi"] == row["id"], "Uncertain plan DOI differs")
        events = collection._chain(_bound(parents["journal"], common_root, end))
        expected = dict(request_id="000", kind="metadata", url=value["metadata_url"],
                        byte_reservation=value["policy"]["metadata_bytes"], transport_status="started")
        codecs.need(len(events) == 3 and events[0]["event"] == "build_reserved"
                    and events[1]["event"] == "plan_bound"
                    and events[1]["details"] == dict(plan_sha256=parents["plan"]["sha256"])
                    and events[2]["event"] == "http_attempt" and events[2]["details"] == expected
                    and canonical(parents["reservation"]) == canonical(expected), "Uncertain request prefix differs")
        codecs.need(row["accounting"]["measured_response_bytes"] is None
                    and row["accounting"]["safety_accounted_bytes"] == expected["byte_reservation"]
                    and row["accounting"]["unknown_transfer_upper_bytes"] == expected["byte_reservation"],
                    "Uncertain metadata reservation differs")
    return freeze(dict(doi=row["id"], ordinal=row["ordinal"], disposition=row["disposition"],
                       parent_proofs=parents, accounting=row["accounting"], citable=False))


def capture(query, hint, prepared, cutoff, model_provenance, *, catalog=None, deadline=None):
    """Revalidate one question's raw sources and retain unresolved operational context."""
    prepared = _trusted(prepared)
    query = validate_query(query)
    codecs.need(query["id"] in prepared._queries and canonical(query) == canonical(prepared._queries[query["id"]]),
                "Actual query/choices differ from the complete frozen collection")
    codecs.need(isinstance(hint, Mapping) and canonical(hint) == canonical(prepared._hints[query["id"]]),
                "Actual hint identity/role differs from the frozen collection")
    hint = prepared._hints[query["id"]]
    model_provenance = freeze(model_provenance)
    end = _deadline(deadline, 120)
    cutoff = datetime.fromisoformat(cutoff) if isinstance(cutoff, str) else cutoff
    codecs.need(isinstance(cutoff, datetime) and cutoff.tzinfo is not None, "Aware recovered evidence cutoff required")
    cutoff = cutoff.astimezone(timezone.utc)
    availability = datetime.fromisoformat(prepared.manifest["availability_cutoff"])
    codecs.need(availability.tzinfo is not None and cutoff >= availability, "Answer cutoff precedes recovered source availability")
    common_root = Path(prepared.common_root)
    effective = freeze(supplied.DEFAULT_CATALOG if catalog is None else catalog)
    rows = [prepared._rows[doi] for doi in hint["dois"]]
    proofs = [prepared.receipt]
    for row in rows:
        proofs.extend(p for p in row["parent_proofs"].values() if isinstance(p, Mapping) and set(p) == {"path", "bytes", "sha256"})
    with stable_files(tuple(plan._absolute(p["path"]) for p in proofs), deadline=end):
        _bound(prepared.receipt, common_root, end)
        operational = [_operational(row, common_root, end) for row in rows]
        resolved = {row["id"]: row["resolution"] for row in rows if row["disposition"] in _RESOLVED}
        if resolved:
            subset = dict(id=query["id"], question=query["question"], dois=[d for d in hint["dois"] if d in resolved])
            context = supplied.capture(query, subset, resolved, common_root, cutoff, model_provenance,
                                       catalog=effective, deadline=end)
            sources, request, inner = context.sources, context.request, context.report
            known = {item["doi"]: item for item in inner["coverage"]["sources"]}
            pool, source_proofs, publications = inner["pool"], inner["source_proofs"], inner["publications"]
        else:
            sources = ()
            request, _ = transport.make_answer_request(query, sources, model_provenance)
            pool = selection.build_pool(dict(id=query["id"], question=query["question"]), ())
            known, source_proofs, publications = {}, (), {}
        coverage_rows = []
        for row in rows:
            if row["id"] in known: coverage_rows.append(known[row["id"]])
            else: coverage_rows.append(dict(doi=row["id"], coverage=row["coverage"], decisions=(),
                inherited_uncertainty=True, source_availability="unknown", source=None))
        coverage = dict(annotated_dois=len(hint["dois"]), retained_articles=len({s["source_id"].split(':')[0] for s in sources}),
                        sources=coverage_rows, selection_role="supplied_source_diagnostic", ordinary_retrieval=False,
                        unknown_or_unavailable_inputs=[r["doi"] for r in coverage_rows if r["coverage"]["article_retained"] is not True],
                        inherited_uncertain_inputs=[r["id"] for r in rows if r["disposition"] == _UNCERTAIN])
        if resolved: coverage["retained_articles"] = inner["coverage"]["retained_articles"]
        report = freeze(dict(policy_kind="sc04_recovered_supplied_source_v2", diagnostic_only=True, ordinary_retrieval=False,
            query_sha256=fingerprint(query), hint_sha256=fingerprint(hint), full_hint=hint,
            selection_uses_reference_paper_identity=True, collection_identity=prepared.collection_identity,
            resolved_source_descriptors=resolved, operational_provenance=operational, cutoff=cutoff.isoformat(),
            catalog_sha256=fingerprint(effective), publications=publications, source_proofs=source_proofs,
            coverage=coverage, pool=pool, sources_sha256=fingerprint(sources), request_sha256=fingerprint(request),
            uncertainty_answer_policy="single_generation_empty_evidence_with_inherited_uncertainty_coverage",
            scientific_support_verified=False))
        _deadline(end, 0)
        return CapturedContext(query, tuple(sources), request, report)
