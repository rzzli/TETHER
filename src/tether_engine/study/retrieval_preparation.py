"""Anchored bounded collected-corpus preparation; zero model or network calls."""

from __future__ import annotations
from collections.abc import Mapping
from dataclasses import replace
import hashlib
from importlib import resources
from pathlib import Path
import time
from tether_engine.agents import make_request
from tether_engine.atomic import publish_bytes
from tether_engine.contracts import (
    Case,
    Category,
    GroundedObservation,
    Observation,
    Citation,
    validate_observation,
)
from tether_engine.journal import RunJournal
from tether_engine.retrieval import RetrievalPolicy, bounded_request
from tether_engine.serde import canonical, decode, encode, fingerprint, freeze, parse_json
from tether_engine.wire import request_bytes
from .baseline_smoke import _prepare_parent
from .diagnostic import REQUIRED_RESOURCES as DIAGNOSTIC_RESOURCES
from .diagnostic_codec import bind_question, need, validate_request
from .proofs import capture_package_proof, verify_package_proof, _no_links
from .source_preparation import (
    verify_source_preparation,
    _bounded_chain,
    _source_path_guard,
)
from .stable_read import checked_path, deadline_check, read_file, stable_files

CORPUS = "resources/retrieval-corpus-v1.json"
POLICIES = "resources/retrieval-policy-v1.json"
RESOURCE_HASHES = {
    CORPUS: "ca522d8e543b2db0fb505a28a53f96026beab5c1563026360a3a06456dbb1a33",
    POLICIES: "312dc711ad897cc902f8397c4ac57a69d8b78a4ea6ae41c6397aebd9c232a8a1",
}
REQUIRED_RESOURCES = tuple(DIAGNOSTIC_RESOURCES) + (CORPUS, POLICIES)
MAX_BYTES = 64 * 1024 * 1024
TRACK = "bounded_collected_corpus_preparation"
ARMS = (
    "tether_interpretation",
    "adapted_virtual_biotech_interpretation",
    "extractive",
    "lexical",
)


def _resource(name):
    raw = resources.files("tether_engine.study").joinpath(name).read_bytes()
    need(
        hashlib.sha256(raw).hexdigest() == RESOURCE_HASHES[name],
        "Retrieval resource differs",
    )
    return parse_json(raw)


def fixture_authority(name="invented-six-v1"):
    pack = _resource(CORPUS)
    need(
        isinstance(name, str) and name in pack["fixtures"],
        "Unknown invented retrieval fixture",
    )
    return freeze(
        dict(
            schema_version=1,
            kind="invented_retrieval",
            fixture=name,
            corpus_sha256=RESOURCE_HASHES[CORPUS],
        )
    )


def authority_anchor(authority):
    return fingerprint(authority)


def policy_for(strategy):
    policy = _resource(POLICIES)
    need(strategy in policy["strategies"], "Unknown retrieval strategy")
    return freeze(
        dict(
            schema_version=1,
            strategy=strategy,
            max_records=policy["max_records"],
            max_request_bytes=policy["max_request_bytes"],
            wire_format=policy["wire_format"],
        )
    )


def _policy(policy):
    need(
        isinstance(policy, Mapping)
        and canonical(policy) == canonical(policy_for(policy.get("strategy"))),
        "Retrieval policy differs from versioned limits",
    )
    return RetrievalPolicy(
        policy["max_records"], policy["max_request_bytes"], policy["wire_format"]
    )


def _records(request):
    original = encode(request)
    case = decode(Case, original["source_request"]["case"])
    case.validate()
    records = []
    for row in original["source_request"]["evidence"]:
        obs = decode(Observation, row["scientific_record"])
        citation = decode(Citation, row["source_ref"])
        record = GroundedObservation(obs, citation)
        need(
            not obs.features
            and row["admitted_sha256"] == fingerprint(record)
            and row["observation_id"] == obs.observation_id
            and row["statement"] == obs.statement,
            "Original grounded record binding differs",
        )
        need(
            obs.target_id == case.hypothesis.target_id
            and obs.indication_id == case.hypothesis.indication_id,
            "Candidate case differs",
        )
        records.append(record)
    ids = [r.observation.observation_id for r in records]
    need(len(ids) == len(set(ids)) <= 16, "Duplicate or oversized declared universe")
    return case, tuple(records)


def _synthetic(authority):
    need(
        canonical(authority) == canonical(fixture_authority(authority.get("fixture"))),
        "Invented authority differs",
    )
    pack = _resource(CORPUS)
    case = decode(Case, pack["case"])
    case.validate()
    originals = tuple(decode(GroundedObservation, r) for r in pack["records"])
    ids = pack["fixtures"][authority["fixture"]]
    selected = tuple(r for r in originals if r.observation.observation_id in ids)
    need(len(selected) == len(ids), "Invented universe differs")
    for record in selected:
        obs = record.observation
        validate_observation(obs)
        need(
            obs.source_kind == "primary"
            and obs.method.code_id == "invented.source"
            and not obs.features
            and record.citation.dataset_id == "invented_retrieval_source"
            and record.citation.artifact_sha256 == fingerprint(obs),
            "Invented source authority differs",
        )
    source = dict(
        schema_version=1,
        role="agent_evidence",
        case=encode(case),
        hypothesis_key=case.hypothesis.key,
        snapshot_id="invented-retrieval-v1:" + authority["fixture"],
        evidence=[
            dict(
                observation_id=r.observation.observation_id,
                admitted_sha256=fingerprint(r),
                source_ref=encode(r.citation),
                statement=r.observation.statement,
                scientific_record=encode(r.observation),
            )
            for r in selected
        ],
        coverage=dict(
            pack["coverage"],
            observations_available=len(selected),
            observations_visible=len(selected),
            selection_scope="explicit_invented_universe_not_real_admission",
        ),
        bounds=dict(max_claims=3, max_text_bytes=8192, max_quotes_per_claim=8),
        instructions=pack["instructions"],
    )
    request = bind_question(source, pack["family"])
    return (
        request,
        pack["category"],
        dict(
            kind="invented_structural_authentication_only",
            corpus_sha256=RESOURCE_HASHES[CORPUS],
            raw_qualified_records=0,
            structurally_authenticated_records=len(selected),
        ),
    )


def _real(authority, roots, deadline):
    need(
        set(authority)
        == {
            "schema_version",
            "kind",
            "parent",
            "parent_receipt_sha256",
            "source_authority_sha256",
            "candidate_ids",
            "grounded_fingerprints",
            "category",
            "request_sha256",
        },
        "Invalid real retrieval authority",
    )
    parent = authority["parent"]
    need(
        isinstance(parent, Mapping)
        and set(parent) == {"root_id", "relative_path"}
        and parent["root_id"] in roots,
        "Invalid parent root",
    )
    folder = checked_path(Path(roots[parent["root_id"]]), parent["relative_path"])
    _source_path_guard(folder)
    verify_source_preparation(
        folder,
        authority["parent_receipt_sha256"],
        authority["source_authority_sha256"],
        roots,
        deadline=deadline,
    )
    with stable_files(
        (
            folder / "receipt.json",
            folder / "request.json",
            folder / "source-audit.json",
        ),
        deadline=deadline,
    ):
        receipt_raw = read_file(
            folder / "receipt.json", deadline=deadline, max_bytes=MAX_BYTES
        )
        need(
            hashlib.sha256(receipt_raw).hexdigest()
            == authority["parent_receipt_sha256"],
            "Source parent receipt changed",
        )
        receipt = parse_json(receipt_raw)
        buffers = {}
        for name in ("request.json", "source-audit.json"):
            raw = read_file(folder / name, deadline=deadline, max_bytes=MAX_BYTES)
            pin = receipt["files"][name]
            need(
                hashlib.sha256(raw).hexdigest() == pin["sha256"]
                and len(raw) == pin["bytes"],
                "Source parent buffer differs",
            )
            buffers[name] = parse_json(raw)
        request = validate_request(buffers["request.json"])
        case, records = _records(request)
        need(
            fingerprint(request) == authority["request_sha256"],
            "Parent request differs",
        )
        ids = [r.observation.observation_id for r in records]
        need(
            isinstance(authority["candidate_ids"], (list, tuple))
            and list(authority["candidate_ids"]) == sorted(set(ids))
            and len(ids) > 0,
            "Entire parent candidate universe required",
        )
        need(
            {r.observation.observation_id: fingerprint(r) for r in records}
            == dict(authority["grounded_fingerprints"]),
            "Candidate fingerprints differ",
        )
        audits = buffers["source-audit.json"]["selected_rows"]
        need(
            len(audits) == len(ids)
            and {a["observation_id"] for a in audits} == set(ids),
            "All candidates require raw replay",
        )
        for record in records:
            matches = [
                a
                for a in audits
                if a["observation_id"] == record.observation.observation_id
            ]
            need(
                len(matches) == 1
                and matches[0]["whole_record_equal"] is True
                and matches[0]["observation_sha256"] == fingerprint(record.observation),
                "Whole source audit differs",
            )
        need(
            hashlib.sha256(
                read_file(
                    folder / "receipt.json", deadline=deadline, max_bytes=MAX_BYTES
                )
            ).hexdigest()
            == authority["parent_receipt_sha256"],
            "Parent changed during recovery",
        )
    return (
        request,
        authority["category"],
        dict(
            kind="current_package_source_inclusive",
            parent_receipt_sha256=authority["parent_receipt_sha256"],
            source_authority_sha256=authority["source_authority_sha256"],
            raw_qualified_records=len(records),
            structurally_authenticated_records=0,
        ),
    )


def qualify_universe(authority, authority_sha256, *, roots=None, deadline):
    deadline_check(deadline)
    need(isinstance(authority, Mapping), "Missing universe authority")
    authority = freeze(encode(authority))
    roots = {key: Path(value) for key, value in (roots or {}).items()}
    need(
        isinstance(authority, Mapping)
        and fingerprint(authority) == authority_sha256
        and type(authority.get("schema_version")) is int
        and authority["schema_version"] == 1,
        "External universe authority differs",
    )
    if authority.get("kind") == "invented_retrieval":
        request, category, qualification = _synthetic(authority)
    else:
        need(
            authority.get("kind") == "real_source_preparation",
            "Unsupported universe authority kind",
        )
        request, category, qualification = _real(authority, roots or {}, deadline)
    case, records = _records(request)
    category = decode(Category, category)
    need(
        category != Category.CLINICAL
        and all(r.observation.category == category for r in records),
        "Mixed/clinical candidate categories unsupported",
    )
    deadline_check(deadline)
    return freeze(
        dict(
            schema_version=1,
            authority=authority,
            authority_sha256=authority_sha256,
            request=request,
            category=category.value,
            qualification=qualification,
            grounded_fingerprints={
                r.observation.observation_id: fingerprint(r) for r in records
            },
        )
    )


def _authenticate(universe, anchor, roots, deadline):
    need(
        isinstance(universe, Mapping) and "authority" in universe,
        "Missing qualified universe",
    )
    universe = freeze(encode(universe))
    expected = qualify_universe(
        universe["authority"], anchor, roots=roots, deadline=deadline
    )
    need(canonical(expected) == canonical(universe), "Forged or changed universe")
    return expected


def _select(request, policy):
    bound = _policy(policy)
    if policy["strategy"] == "literal_case_overlap_then_id_v1":
        return bounded_request(request, bound)
    empty = replace(request, evidence=())
    need(
        len(request_bytes(empty, bound.wire_format)) <= bound.max_request_bytes,
        "Case/instructions exceed bounded request size",
    )
    ids = [x.observation_id for x in request.evidence]
    need(len(ids) == len(set(ids)), "Duplicate retrieval observation IDs")
    kept = []
    excluded = []
    for row in sorted(request.evidence, key=lambda r: r.observation_id):
        if len(kept) == bound.max_records:
            reason = "record_count_cap"
        elif (
            len(
                request_bytes(
                    replace(request, evidence=tuple(kept + [row])), bound.wire_format
                )
            )
            > bound.max_request_bytes
        ):
            reason = "whole_record_exceeds_byte_cap"
        else:
            kept.append(row)
            continue
        excluded.append(dict(observation_id=row.observation_id, reason=reason))
    prepared = replace(request, evidence=tuple(kept))
    return prepared, dict(
        policy=dict(
            max_records=bound.max_records, max_request_bytes=bound.max_request_bytes
        ),
        input_request_sha256=fingerprint(request),
        request_sha256=fingerprint(prepared),
        available_records=len(request.evidence),
        selected_ids=tuple(r.observation_id for r in kept),
        excluded=excluded,
        request_bytes=len(request_bytes(prepared, bound.wire_format)),
        ranking="id_order_v1",
        interpretation="selected subset only; excluded records are not biological absence",
    )


def retrieve(universe, policy, authority_sha256, *, roots=None, deadline):
    policy = freeze(encode(policy))
    checked = _authenticate(universe, authority_sha256, roots, deadline)
    case, records = _records(checked["request"])
    request = make_request(case, decode(Category, checked["category"]), records)
    selected, audit = _select(request, policy)
    deadline_check(deadline)
    return freeze(
        dict(
            schema_version=1,
            track=TRACK,
            universe_sha256=fingerprint(checked),
            authority_sha256=authority_sha256,
            policy=policy,
            retrieval_audit=audit,
            selected_ids=[x.observation_id for x in selected.evidence],
            source_request_sha256=fingerprint(checked["request"]),
            model_calls=0,
            scientific_answer_status="not_attempted",
        )
    )


def compile_retrieved(universe, result, authority_sha256, *, roots=None, deadline):
    need(isinstance(result, Mapping), "Missing retrieval result")
    universe = freeze(encode(universe))
    result = freeze(encode(result))
    expected = retrieve(
        universe, result.get("policy"), authority_sha256, roots=roots, deadline=deadline
    )
    need(canonical(expected) == canonical(result), "Retrieval result differs")
    parent = encode(universe["request"])
    selected = set(result["selected_ids"])
    source = parent["source_request"]
    rows = [row for row in source["evidence"] if row["observation_id"] in selected]
    count = len(source["evidence"])
    source["evidence"] = rows
    source["coverage"]["observations_visible"] = len(rows)
    request = bind_question(source, parent["question"]["question_id"]) if rows else None
    coverage = dict(
        status="selected_subset"
        if rows
        else "empty_declared_universe"
        if count == 0
        else "all_whole_records_excluded",
        declared_candidates=count,
        raw_qualified_candidates=universe["qualification"]["raw_qualified_records"],
        structurally_authenticated_candidates=universe["qualification"][
            "structurally_authenticated_records"
        ],
        selected_count=len(rows),
        selected_rank_ids=result["selected_ids"],
        compiled_source_ids=[r["observation_id"] for r in rows],
        excluded=result["retrieval_audit"]["excluded"],
        parent_observations_available=source["coverage"].get("observations_available"),
        missing_input_count=source["coverage"].get("missing_input_count"),
        missing_count_basis=source["coverage"].get("missing_count_basis"),
        absence_claim=False,
        scientific_answer_status="not_attempted",
    )
    return freeze(dict(request=request, coverage=coverage))


def _package_check(proof):
    need(
        isinstance(proof, Mapping)
        and isinstance(proof.get("resources"), Mapping)
        and {
            k: v.get("relative_path")
            for k, v in proof["resources"].items()
            if isinstance(v, Mapping)
        }
        == {name: "study/" + name for name in REQUIRED_RESOURCES},
        "Retrieval resource paths differ",
    )
    verify_package_proof(proof, required_resources=REQUIRED_RESOURCES)


def _read(path, name, deadline):
    raw = read_file(path / name, deadline=deadline, max_bytes=MAX_BYTES)
    return raw, dict(
        logical_id=name, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)
    )


def _write(path, name, value):
    publish_bytes(path / name, canonical(value))


def prepare_retrieval(
    authority, authority_sha256, policy, output, *, roots=None, deadline
):
    now = time.monotonic()
    need(
        type(deadline) in (int, float) and now < deadline <= now + 300,
        "Invalid shared preparation deadline",
    )
    root = Path(output).absolute()
    _prepare_parent(root.parent)
    journal = RunJournal(root, kind="build")
    try:
        journal.append(
            "retrieval_preparing",
            authority_sha256=authority_sha256,
            policy_sha256=fingerprint(policy),
        )
        proof = capture_package_proof(
            {n: "study/" + n for n in REQUIRED_RESOURCES}, REQUIRED_RESOURCES
        )
        _package_check(proof)
        universe = qualify_universe(
            authority, authority_sha256, roots=roots, deadline=deadline
        )
        result = retrieve(
            universe, policy, authority_sha256, roots=roots, deadline=deadline
        )
        compiled = compile_retrieved(
            universe, result, authority_sha256, roots=roots, deadline=deadline
        )
        access = {
            arm: dict(
                authority_sha256=authority_sha256,
                universe_sha256=fingerprint(universe),
                policy_sha256=fingerprint(policy),
                request_sha256=fingerprint(compiled["request"])
                if compiled["request"] is not None
                else None,
                execution="preparation_only_no_arm_output",
            )
            for arm in ARMS
        }
        docs = {
            "authority.json": authority,
            "policy.json": policy,
            "package-proof.json": proof,
            "universe.json": universe,
            "retrieval.json": result,
            "request.json": compiled["request"],
            "coverage.json": compiled["coverage"],
            "access-manifest.json": access,
        }
        for name, doc in docs.items():
            deadline_check(deadline)
            _write(root, name, doc)
        journal.append(
            "retrieval_prepared",
            universe_sha256=fingerprint(universe),
            result_sha256=fingerprint(result),
            model_calls=0,
            scientific_answer_status="not_attempted",
        )
        journal.close()
        _package_check(proof)
        deadline_check(deadline)
        files = {
            name: _read(root, name, deadline)[1] for name in (*docs, "journal.jsonl")
        }
        deadline_check(deadline)
        receipt = dict(
            schema_version=1, kind=TRACK, authority_sha256=authority_sha256, files=files
        )
        _write(root, "receipt.json", receipt)
        return freeze(
            dict(
                receipt_sha256=fingerprint(receipt),
                authority_sha256=authority_sha256,
                request_sha256=access[ARMS[0]]["request_sha256"],
                coverage=compiled["coverage"],
                model_calls=0,
            )
        )
    except BaseException as error:
        try:
            journal.fail(error, "retrieval_preparation")
        except BaseException as extra:
            error.add_note("Journal failure: " + type(extra).__name__)
        try:
            _write(
                root,
                "failure.json",
                dict(
                    error_class=type(error).__name__,
                    message=str(error),
                    model_calls=0,
                    retry=False,
                ),
            )
        except BaseException as extra:
            error.add_note("Failure marker: " + type(extra).__name__)
        raise
    finally:
        journal.close()


def verify_retrieval_preparation(
    path, receipt_sha256, authority_sha256, *, roots=None, deadline
):
    root = Path(path)
    _no_links(root)
    raw, _ = _read(root, "receipt.json", deadline)
    need(
        hashlib.sha256(raw).hexdigest() == receipt_sha256,
        "Retrieval receipt anchor differs",
    )
    receipt = parse_json(raw)
    names = {
        "authority.json",
        "policy.json",
        "package-proof.json",
        "universe.json",
        "retrieval.json",
        "request.json",
        "coverage.json",
        "access-manifest.json",
        "journal.jsonl",
    }
    need(
        set(receipt) == {"schema_version", "kind", "authority_sha256", "files"}
        and receipt["schema_version"] == 1
        and receipt["kind"] == TRACK
        and receipt["authority_sha256"] == authority_sha256
        and set(receipt["files"]) == names
        and {p.name for p in root.iterdir()} == names | {"receipt.json"},
        "Retrieval inventory/identity differs",
    )
    docs = {}
    for name, pin in receipt["files"].items():
        payload, actual = _read(root, name, deadline)
        need(actual == pin, "Retrieval member changed")
        docs[name] = payload if name == "journal.jsonl" else parse_json(payload)
    _package_check(docs["package-proof.json"])
    universe = qualify_universe(
        docs["authority.json"], authority_sha256, roots=roots, deadline=deadline
    )
    need(
        canonical(universe) == canonical(docs["universe.json"]),
        "Universe replay differs",
    )
    result = retrieve(
        universe, docs["policy.json"], authority_sha256, roots=roots, deadline=deadline
    )
    need(
        canonical(result) == canonical(docs["retrieval.json"]),
        "Retrieval replay differs",
    )
    compiled = compile_retrieved(
        universe, result, authority_sha256, roots=roots, deadline=deadline
    )
    for name, value in [
        ("request.json", compiled["request"]),
        ("coverage.json", compiled["coverage"]),
    ]:
        need(
            canonical(docs[name]) == canonical(value),
            "Compiled subset/coverage differs",
        )
    access = {
        arm: dict(
            authority_sha256=authority_sha256,
            universe_sha256=fingerprint(universe),
            policy_sha256=fingerprint(docs["policy.json"]),
            request_sha256=fingerprint(compiled["request"])
            if compiled["request"] is not None
            else None,
            execution="preparation_only_no_arm_output",
        )
        for arm in ARMS
    }
    need(
        canonical(docs["access-manifest.json"]) == canonical(access),
        "Unequal/forged arm access",
    )
    events = _bounded_chain(docs["journal.jsonl"])
    need(
        [e["event"] for e in events]
        == ["build_reserved", "retrieval_preparing", "retrieval_prepared"]
        and events[1]["details"]
        == dict(
            authority_sha256=authority_sha256,
            policy_sha256=fingerprint(docs["policy.json"]),
        )
        and events[2]["details"]
        == dict(
            universe_sha256=fingerprint(universe),
            result_sha256=fingerprint(result),
            model_calls=0,
            scientific_answer_status="not_attempted",
        ),
        "Retrieval journal differs",
    )
    for name, pin in receipt["files"].items():
        need(_read(root, name, deadline)[1] == pin, "Retrieval changed during replay")
    need(
        _read(root, "receipt.json", deadline)[1]["sha256"] == receipt_sha256,
        "Retrieval receipt changed",
    )
    return freeze(
        dict(
            status="verified",
            request_sha256=access[ARMS[0]]["request_sha256"],
            coverage=compiled["coverage"],
            model_calls=0,
            scientific_answer_status="not_attempted",
        )
    )
