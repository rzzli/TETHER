"""TETHER admission for a declared source-backed LitQA2 task policy.

This is not therapeutic schema-2 or all BG02 obligations. It reuses TETHER's
actual input DAG/role/temporal checks, public-download receipt validation,
stable original-path locks, immutable capture and hash-chained journal. It
does not use the correct answer or assert that a cited passage entails it.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
from pathlib import Path
import re
import time
from types import SimpleNamespace

from tether_engine.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from tether_engine.provenance import InputGraph, catalog_index
from tether_engine.serde import ContractError, Frozen, canonical, decode, encode, fingerprint, freeze, parse_json, safe_child
from tether_engine.study.stable_read import read_file, stable_files
from .model import make_request
from .native_contract import validate_prediction, validate_query, visible_unsure_index
from .retrieval import select_passages, verify_retrieval

POLICY_KIND = "labbench_native_source_backed_v1"
DEFAULT_CATALOG = freeze({"schema_version":1,"datasets":[
    {"dataset_id":"labbench_retrieved_literature","roles":["agent_evidence"],
     "provider":"Europe PMC","source_products":["europepmc_metadata","europepmc_fulltext"],
     "scope":"original bounded public HTTP search/XML responses; transport success is not scientific validation"},
    {"dataset_id":"labbench_retrieved_passages","roles":["agent_evidence"],
     "provider":"project","source_products":["labbench_retrieved_literature"],
     "scope":"versioned source extraction and deterministic bounded passage view"}]})


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class CapturedContext(Frozen):
    """Trusted in-memory result of ``capture_context``, not a deserializer.

    Its fingerprints protect consistency, not a caller's claim that admission
    ran. Archived verification must recapture original roots using external
    manifest anchors and compare the rebuilt sources, requests, roles and
    eligibility. Never construct this class from untrusted serialized reports.
    The supervisor/producer transport separately proves the query projection,
    model files, request and returned bytes through its sealed StudySession.
    """
    query: Mapping
    sources: tuple
    bindings: tuple
    request: Mapping
    report: Mapping

    @property
    def sha256(self):
        return fingerprint(self.report)


def capture_context(query, retrieval_root, expected_manifest_sha256, cutoff, model_provenance,
                    configuration=None, catalog=None, *, deadline=None):
    """Capture verified source bytes once, then admit candidates without rereads.

    The supervisor supplies a trusted task-only projection plus frozen model
    provenance and cutoff. It must separately bind those to the stage's query
    file/model receipts. No full benchmark answer container is an agent input.
    ``cutoff`` is after source acquisition and before model dispatch. The
    serialized report permits an independent original-source replay later.
    """
    query = validate_query(query)
    if isinstance(cutoff, str):
        cutoff = decode(datetime, cutoff)
    _need(isinstance(cutoff, datetime) and cutoff.tzinfo is not None, "Exact aware source cutoff required")
    cutoff = cutoff.astimezone(timezone.utc)
    _need(isinstance(expected_manifest_sha256, str) and re.fullmatch("[0-9a-f]{64}",expected_manifest_sha256),
          "Pinned retrieval manifest hash required")
    root = Path(retrieval_root).absolute()
    deadline = time.monotonic()+120 if deadline is None else deadline
    manifest_path = safe_child(root, "manifest.json")
    effective_catalog = freeze(DEFAULT_CATALOG if catalog is None else catalog)
    products = catalog_index(effective_catalog)
    # The initial manifest is held while its inventory is interpreted, and
    # every original path/receipt remains locked through all verification.
    with stable_files((manifest_path,), deadline=deadline):
        raw_manifest = read_file(manifest_path, deadline, 32*1024*1024)
        _need(_sha(raw_manifest) == expected_manifest_sha256, "Retrieval manifest checksum mismatch")
        preliminary = parse_json(raw_manifest)
        paths = [manifest_path, safe_child(root,"COMPLETE.json"), safe_child(root,"journal.jsonl")]
        for entry in preliminary["requests"]:
            if entry["status"] == "completed":
                paths += [safe_child(root,entry["body_path"]),safe_child(root,entry["receipt_path"])]
        with stable_files(paths, deadline=deadline):
            manifest = verify_retrieval(root, expected_manifest_sha256, query["question"])
            view = select_passages(manifest,query["question"])
            _need(len({row["source_id"] for row in view["sources"]}) == len(view["sources"]), "Duplicate granted passage ID")
            by_request = {row["request_id"]:row for row in manifest["requests"]}
            used_requests = set()
            publication_dates = {}
            for source in manifest["sources"]:
                publication = source["publication_date"]
                if publication is not None:
                    publication = decode(date,publication)
                    _need(publication <= cutoff.date(), "Source publication is after source cutoff")
                matches = [row for row in manifest["requests"] if row.get("body_path") == source["original"]["path"]]
                _need(len(matches) == 1,"Ambiguous source original request")
                used_requests.update((source["discovery_request_id"],matches[0]["request_id"]))
                publication_dates[source["source_id"]] = {"reported_date":source["publication_date"],
                    "unknown_reason":"not reported in retrieved metadata" if publication is None else None}
            captured_at = datetime.now(timezone.utc)
            nodes = []
            for key in sorted(used_requests):
                row = by_request[key]
                _need(row["status"] == "completed" and 200 <= row["http_status"] < 300,"Unsuccessful original cannot enter evidence DAG")
                receipt = parse_json(read_file(safe_child(root,row["receipt_path"]),deadline,65536))
                observed_at = decode(datetime,receipt.get("completed_at_utc"))
                availability = Availability(None,None,None,None,observed_at.date(),"public_download_receipt",
                    "Present-day download bound; does not prove historical availability",observed_at,row["receipt_sha256"])
                nodes.append(SourceNode("request:"+key,"labbench_retrieved_literature",row["body_sha256"],
                    row["body_path"],row["body_sha256"],"agent_evidence",availability,TemporalClass.CONTEMPORARY,
                    row["url"],receipt_path=row["receipt_path"],receipt_sha256=row["receipt_sha256"]))
            if nodes:
                nodes.append(SourceNode("parsed-manifest","labbench_retrieved_passages",expected_manifest_sha256,
                    "manifest.json",expected_manifest_sha256,"agent_evidence",
                    Availability(None,None,None,None,captured_at.date(),"computed_from_verified_originals",None),
                    TemporalClass.CONTEMPORARY,"local:deterministic-europepmc-extraction",
                    parents=tuple(node.source_id for node in nodes),computed_at=captured_at,
                    method_id="labbench_question_only_extraction_and_selection",method_version=manifest["retriever_sha256"]))
            snapshot = Snapshot(2,"litqa2-"+query["id"],Profile.CONTEMPORARY,cutoff.date(),False,(),
                tuple(nodes),str(root),view["coverage"],cutoff)
            proofs = ()
            if nodes:
                graph = InputGraph(snapshot,root,products)
                # Validate every granted original, not only the citations the
                # answer later chooses. Derived computation time is separate.
                refs = tuple(node.source_id for node in nodes)
                exclusion = graph.exclusion(refs,SimpleNamespace(cutoff=cutoff))
                _need(exclusion is None,"Input lineage is ineligible: "+str(exclusion))
                proofs = graph.verify(refs,{})
            request,_ = make_request(query,view["sources"],model_provenance,configuration)
            report = {"schema_version":1,"policy_kind":POLICY_KIND,"task_id":query["id"],
                "query_sha256":fingerprint(query),"request_sha256":fingerprint(request),
                "sources_sha256":fingerprint(view["sources"]),"bindings":view["bindings"],
                "retrieval_root":str(root),"retrieval_manifest_sha256":expected_manifest_sha256,
                "cutoff_utc":cutoff.isoformat(),"captured_at_utc":captured_at.isoformat(),
                "snapshot":encode(snapshot),"effective_catalog":effective_catalog,"input_proofs":proofs,
                "publication_dates":publication_dates,"coverage":view["coverage"],
                "source_count":len(view["sources"]),"no_sources":not bool(view["sources"]),
                "query_boundary":"Trusted field projection; answer-containing original is supervisor-only and is not relabeled as agent evidence",
                "semantic_support":"unevaluated",
                "obligations":["native_schema","request_binding","offered_source_identity","source_text_and_locator",
                    "all_granted_input_lineage","catalog_roles","contemporary_availability","source_backed_substantive_answer"],
                "not_established":["semantic_entailment","native_answer_correctness","clinical_validity","full_BG02_parity"]}
            return CapturedContext(query,tuple(view["sources"]),tuple(view["bindings"]),request,report)


def verify_candidate(context, supplied_request, prediction, *, journal=None):
    """Check one already-produced candidate against an immutable source capture.

    Wrong native answers can pass provenance. A substantive source-free answer
    is rejected here while remaining a raw native answer for scoring. A valid
    unsure answer can pass with no citation; it is not an operational failure.
    """
    _need(isinstance(context,CapturedContext),"Expected captured native policy context")
    _need(context.report["request_sha256"] == fingerprint(context.request) and
          context.report["query_sha256"] == fingerprint(context.query) and
          context.report["sources_sha256"] == fingerprint(context.sources),"Captured policy context is inconsistent")
    accepted, reason, validated = False, None, None
    try:
        _need(canonical(supplied_request) == canonical(context.request),"request_binding_mismatch")
        validated = validate_prediction(prediction,context.query,[row["source_id"] for row in context.sources])
        _need(validated["answer_index"] == visible_unsure_index(context.query) or bool(validated["evidence_ids"]),
              "substantive_answer_requires_captured_evidence")
        accepted = True
    except (ContractError,TypeError,ValueError) as error:
        reason = str(error)
    decision = freeze({"accepted":accepted,"reason":reason,"prediction":validated,
        "request_sha256":fingerprint(context.request),"context_sha256":context.sha256,
        "policy_kind":POLICY_KIND,"semantic_support":"unevaluated"})
    if journal is not None:
        journal.append("labbench_candidate_checked",task_id=context.query["id"],decision=decision)
    return decision
