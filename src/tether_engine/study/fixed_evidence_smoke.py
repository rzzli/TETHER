"""Four fixed synthetic arms with shared budgets; recorded transport, never models."""

import argparse
from dataclasses import replace
import json
import math
import os
from pathlib import Path
import re
import time

from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import canonical, decode, encode, fingerprint, freeze
from tether_engine.workflow import Budget

from .baseline_smoke import _prepare_parent, _read, _write
from .baselines import run_baseline, reviewer_view
from .diagnostic import load_synthetic_request
from .diagnostic_codec import need
from .fixed_evidence import (
    ARMS,
    PLAN_SHA256,
    REQUIRED_RESOURCES,
    DeadlineRecordedBackend,
    RoleRecordedVerifier,
    cell_path,
    load_plan,
    preflight,
    prepare_payload,
    recorded_document,
)
from .proofs import _no_links, capture_file, capture_package_proof, verify_package_proof
from .session import StudySession, verify_study

CELL_FILES = {
    "request.json",
    "payload.json",
    "configuration.json",
    "raw-response.bin",
    "response.json",
    "report.json",
    "journal.jsonl",
    "receipt.json",
}


def _schedule(fixture):
    plan = load_plan()
    return [
        (arm, index)
        for arm in ARMS
        for index in range(
            len(plan["tether_stages"] if arm == ARMS[0] else plan["stage_order"])
        )
    ]


def _members():
    names = {"journal.jsonl", "package-proof.json", "summary.json", "assignment.json"}
    for fixture in load_plan()["fixture_names"]:
        names.add(f"{fixture}-preflight.json")
        for method in ("extractive", "lexical"):
            names.update(
                f"{fixture}-{method}-{kind}.json"
                for kind in ("policy", "result", "reviewer")
            )
        for arm, index in _schedule(fixture):
            names.update(
                cell_path(fixture, arm, index) + "/" + name for name in CELL_FILES
            )
        for arm in ARMS:
            names.add(f"{fixture}-{arm}-reviewer.json")
    return names


def _inventory(root):
    _no_links(root)
    found = set()
    directories = set()
    for directory, children, names in os.walk(root, followlinks=False):
        for child in children:
            path = Path(directory) / child
            _no_links(path)
            directories.add(path.relative_to(root).as_posix())
        for name in names:
            path = Path(directory) / name
            _no_links(path)
            need(path.is_file(), "Unexpected artifact type")
            found.add(path.relative_to(root).as_posix())
    expected_dirs = {
        parent.as_posix()
        for name in _members()
        for parent in Path(name).parents
        if parent != Path(".")
    }
    need(directories == expected_dirs, "Unexpected comparison directories")
    return found


def _resources():
    return {name: "study/" + name for name in REQUIRED_RESOURCES}


def _baseline_policy(request, method):
    return dict(
        schema_version=1,
        method=method,
        query=request["question"]["text"] if method == "lexical" else None,
        max_excerpts=3,
        max_quote_bytes=8192,
        max_request_bytes=65536,
        max_result_bytes=65536,
    )


def _assignment():
    return dict(
        role="evaluation_only",
        assignment="fixed_not_randomized_not_blinded",
        arms={
            ARMS[0]: "Candidate A",
            ARMS[1]: "Candidate B",
            "extractive": "Candidate C",
            "lexical": "Candidate D",
        },
    )


def _recorded_document(request, payload):
    return recorded_document(request, payload)


def _interpretation_view(stage, response, label):
    # Keep authored text unchanged; copied quotations are separate literal fields.
    from .diagnostic_codec import quote_choices

    choices = quote_choices(stage["original_request"])
    claims = []
    for claim in response["response"]["claims"]:
        claims.append(
            dict(
                authored_claim=encode(claim),
                literal_quotes=[
                    dict(source_id=alias, pointer=pointer, text=choices[alias][pointer])
                    for alias, pointer in zip(
                        claim["source_ids"], claim["quote_pointers"]
                    )
                ],
            )
        )
    return dict(
        schema_version=1,
        role="evaluation_only",
        label=label,
        scope="synthetic_recorded_transport_not_model_or_human_reference",
        answer_status=response["response"]["answer_status"],
        claims=claims,
        unresolved=encode(response["response"]["unresolved"]),
        abstention_reason=response["response"]["abstention_reason"],
        coverage=encode(stage["original_request"]["source_request"]["coverage"]),
        features={},
        clinical_probability=None,
        scientific_validation="not_attempted",
    )


def _remaining(start):
    remaining = Budget().max_seconds - (time.monotonic() - start)
    need(
        math.isfinite(remaining) and 0 < remaining <= Budget().max_seconds,
        "Shared fixture deadline exceeded",
    )
    return remaining


def smoke(output):
    root = Path(output).absolute()
    _prepare_parent(root.parent)
    journal = RunJournal(root, kind="build")
    run_id = journal.events[0]["details"]["run_id"]
    accepted = []
    reserved = []
    summaries = []
    try:
        _no_links(root)
        plan = load_plan()
        package = capture_package_proof(_resources(), REQUIRED_RESOURCES)
        _write(root, "package-proof.json", package)
        _write(root, "assignment.json", _assignment())
        journal.append(
            "comparison_prepared",
            plan_sha256=PLAN_SHA256,
            budget=encode(Budget()),
            package_proof_sha256=fingerprint(package),
        )
        verifier = RoleRecordedVerifier(root, run_id)
        for fixture in plan["fixture_names"]:
            start = time.monotonic()
            case_end = start + Budget().max_seconds
            journal.append(
                "fixture_started",
                fixture=fixture,
                budget=encode(Budget()),
                start_monotonic=start,
                case_end_monotonic=case_end,
            )
            check = preflight(fixture)
            _write(root, f"{fixture}-preflight.json", check)
            _remaining(start)
            request = load_synthetic_request(fixture)
            input_reserved = output_reserved = calls = 0
            for method in ("extractive", "lexical"):
                _remaining(start)
                policy = _baseline_policy(request, method)
                result = run_baseline(request, policy)
                view = reviewer_view(result, _assignment()["arms"][method])
                for kind, value in [
                    ("policy", policy),
                    ("result", result),
                    ("reviewer", view),
                ]:
                    _write(root, f"{fixture}-{method}-{kind}.json", value)
                _remaining(start)
                journal.append(
                    "pure_completed",
                    fixture=fixture,
                    arm=method,
                    result_sha256=fingerprint(result),
                    actual_model_calls=0,
                )
            for arm, index in _schedule(fixture):
                _remaining(start)
                stage = verifier.prepare_stage(fixture, arm, index)
                payload = prepare_payload(stage)
                in_quote = len(payload["prompt"].encode()) + 32
                out_quote = payload["n_predict"]
                need(
                    input_reserved + in_quote <= Budget().max_input_tokens
                    and output_reserved + out_quote <= Budget().max_output_tokens
                    and calls < Budget().max_calls,
                    "Shared aggregate reservation exceeded",
                )
                remaining = _remaining(start)
                budget = replace(
                    Budget(),
                    max_calls=Budget().max_calls - calls,
                    max_input_tokens=Budget().max_input_tokens - input_reserved,
                    max_output_tokens=Budget().max_output_tokens - output_reserved,
                    max_seconds=remaining,
                )
                logical = cell_path(fixture, arm, index)
                journal.append(
                    "stage_preparing",
                    cell_id=logical,
                    request_sha256=fingerprint(stage),
                    payload_sha256=fingerprint(payload),
                )
                reserved.append(logical)
                document = _recorded_document(stage, payload)
                _remaining(start)
                path = root / logical
                _prepare_parent(path.parent)
                with StudySession(
                    path,
                    budget=budget,
                    configuration=dict(
                        comparison_run_id=run_id,
                        cell_id=logical,
                        usage_scope="declared_fixture_usage_not_observed_model_tokens",
                    ),
                    resources=_resources(),
                    required_resources=REQUIRED_RESOURCES,
                ) as session:
                    # Keep the child's deadline equal to the parent's, including
                    # time spent constructing the child and capturing its package.
                    _remaining(start)
                    budget = replace(budget, max_seconds=case_end - session.started)
                    need(
                        0 < budget.max_seconds <= Budget().max_seconds,
                        "Invalid child shared deadline",
                    )
                    session.budget = decode(Budget, encode(budget))
                    journal.append(
                        "stage_reserved",
                        fixture=fixture,
                        arm=arm,
                        stage_index=index,
                        cell_id=logical,
                        input_reservation=in_quote,
                        output_reservation=out_quote,
                        allocated_budget=encode(budget),
                        request_sha256=fingerprint(stage),
                        payload_sha256=fingerprint(payload),
                    )
                    input_reserved += in_quote
                    output_reserved += out_quote
                    calls += 1
                    _remaining(start)
                    response = session.call_once(
                        request=stage,
                        payload=payload,
                        backend=DeadlineRecordedBackend(document, case_end=case_end),
                        verifier=verifier,
                    )
                    session.finish()
                receipt_sha = capture_file(path / "receipt.json", "receipt.json")[
                    "sha256"
                ]
                verify_study(
                    path, expected_receipt_sha256=receipt_sha, verifier=verifier
                )
                _remaining(start)
                journal.append(
                    "stage_accepted",
                    cell_id=logical,
                    receipt_sha256=receipt_sha,
                    fixture_declared_usage=dict(
                        input_tokens=64, output_tokens=64, cost_usd=0.0
                    ),
                    actual_model_calls=0,
                )
                accepted.append(logical)
                if (
                    index
                    == len(
                        plan["tether_stages"] if arm == ARMS[0] else plan["stage_order"]
                    )
                    - 1
                ):
                    _write(
                        root,
                        f"{fixture}-{arm}-reviewer.json",
                        _interpretation_view(
                            stage, response, _assignment()["arms"][arm]
                        ),
                    )
            elapsed = Budget().max_seconds - _remaining(start)
            record = dict(
                fixture=fixture,
                recorded_adapter_cells=calls,
                input_reserved=input_reserved,
                output_reserved=output_reserved,
                fixture_declared_usage=dict(
                    input_tokens=calls * 64, output_tokens=calls * 64, cost_usd=0.0
                ),
                actual_model_calls=0,
                elapsed_seconds=elapsed,
            )
            summaries.append(record)
            journal.append("fixture_completed", **record)
        summary = dict(
            schema_version=1,
            role="evaluation_only",
            run_id=run_id,
            status="recorded_contract_completed_not_scientific_validation",
            plan_sha256=PLAN_SHA256,
            fixtures=summaries,
            recorded_adapter_cells=12,
            pure_baseline_results=4,
            actual_model_calls=0,
            observed_model_usage=dict(input_tokens=0, output_tokens=0, cost_usd=0.0),
            scientific_validation="not_attempted",
            cpu_time_and_energy="not_measured",
            automatic_retries=False,
        )
        _write(root, "summary.json", summary)
        journal.append("comparison_completed", summary_sha256=fingerprint(summary))
        journal.close()
        verify_package_proof(package, required_resources=REQUIRED_RESOURCES)
        need(
            _inventory(root) == _members(),
            "Comparison inventory differs before sealing",
        )
        artifacts = {
            name: encode(capture_file(root / name, name)) for name in sorted(_members())
        }
        receipt = dict(
            schema_version=1,
            kind="fixed_evidence_recorded_comparison",
            role="evaluation_only",
            run_id=run_id,
            artifacts=artifacts,
        )
        _write(root, "receipt.json", receipt)
        return verify(root, fingerprint(receipt))
    except BaseException as primary:
        try:
            journal.fail(primary, "fixed_evidence_comparison")
        except BaseException as secondary:
            primary.add_note("Parent journal failure: " + type(secondary).__name__)
        try:
            dispositions = {
                cell_path(f, a, i): "accepted"
                if cell_path(f, a, i) in accepted
                else "attempted_or_reserved_inspect_cell"
                if cell_path(f, a, i) in reserved
                else "undispatched"
                for f in load_plan()["fixture_names"]
                for a, i in _schedule(f)
            }
            _write(
                root,
                "failure.json",
                dict(
                    schema_version=1,
                    role="evaluation_only",
                    run_id=run_id,
                    error_class=type(primary).__name__,
                    message=str(primary),
                    stage_dispositions=dispositions,
                    failed_cell_usage="unknown_until_cell_inspection",
                    actual_model_calls=0,
                    automatic_retry=False,
                ),
            )
        except BaseException as secondary:
            primary.add_note("Failure marker unavailable: " + type(secondary).__name__)
        try:
            journal.close()
        except BaseException as secondary:
            primary.add_note("Journal close failed: " + type(secondary).__name__)
        raise


def verify(path, sha256):
    root = Path(path).absolute()
    need(
        isinstance(sha256, str) and re.fullmatch(r"[0-9a-f]{64}", sha256),
        "External comparison receipt anchor required",
    )
    need(
        _inventory(root) == _members() | {"receipt.json"},
        "Comparison member inventory differs",
    )
    receipt, rproof = _read(root, "receipt.json")
    need(rproof["sha256"] == sha256, "External comparison anchor differs")
    need(
        isinstance(receipt, dict)
        and set(receipt) == {"schema_version", "kind", "role", "run_id", "artifacts"}
        and type(receipt["schema_version"]) is int
        and receipt["schema_version"] == 1
        and receipt["kind"] == "fixed_evidence_recorded_comparison"
        and receipt["role"] == "evaluation_only"
        and isinstance(receipt["artifacts"], dict)
        and set(receipt["artifacts"]) == _members(),
        "Invalid comparison receipt",
    )
    for name, proof in receipt["artifacts"].items():
        need(
            canonical(capture_file(root / name, name)) == canonical(proof),
            "Comparison artifact differs",
        )
    package, _ = _read(root, "package-proof.json")
    need(
        set(package.get("resources", {})) == set(REQUIRED_RESOURCES)
        and all(
            package["resources"][n]["relative_path"] == _resources()[n]
            for n in REQUIRED_RESOURCES
        ),
        "Comparison resource map differs",
    )
    verify_package_proof(package, required_resources=REQUIRED_RESOURCES)
    assignment, _ = _read(root, "assignment.json")
    need(canonical(assignment) == canonical(_assignment()), "Assignment differs")
    events = read_chain(root / "journal.jsonl")
    run_id = events[0]["details"]["run_id"]
    need(receipt["run_id"] == run_id, "Comparison run identity differs")
    expected_events = ["build_reserved", "comparison_prepared"]
    need(
        events[1]["details"]
        == freeze(
            dict(
                plan_sha256=PLAN_SHA256,
                budget=encode(Budget()),
                package_proof_sha256=fingerprint(package),
            )
        ),
        "Comparison preparation differs",
    )
    verifier = RoleRecordedVerifier(root, run_id)
    fixture_summaries = []
    for fixture in load_plan()["fixture_names"]:
        expected_events.extend(["fixture_started", "pure_completed", "pure_completed"])
        starts = [
            e["details"]
            for e in events
            if e["event"] == "fixture_started"
            and e["details"].get("fixture") == fixture
        ]
        need(
            len(starts) == 1
            and set(starts[0])
            == {"fixture", "budget", "start_monotonic", "case_end_monotonic"}
            and canonical(starts[0]["budget"]) == canonical(Budget())
            and type(starts[0]["start_monotonic"]) in (int, float)
            and math.isfinite(starts[0]["start_monotonic"])
            and type(starts[0]["case_end_monotonic"]) in (int, float)
            and math.isfinite(starts[0]["case_end_monotonic"])
            and starts[0]["case_end_monotonic"]
            == starts[0]["start_monotonic"] + Budget().max_seconds,
            "Fixture budget reset/difference",
        )
        check, _ = _read(root, f"{fixture}-preflight.json")
        need(
            canonical(check) == canonical(preflight(fixture)),
            "Aggregate preflight differs",
        )
        request = load_synthetic_request(fixture)
        for method in ("extractive", "lexical"):
            policy = _baseline_policy(request, method)
            result = run_baseline(request, policy)
            view = reviewer_view(result, _assignment()["arms"][method])
            for kind, value in [
                ("policy", policy),
                ("result", result),
                ("reviewer", view),
            ]:
                doc, _ = _read(root, f"{fixture}-{method}-{kind}.json")
                need(canonical(doc) == canonical(value), "Pure baseline differs")
            pe = [
                e["details"]
                for e in events
                if e["event"] == "pure_completed"
                and e["details"].get("fixture") == fixture
                and e["details"].get("arm") == method
            ]
            need(
                len(pe) == 1
                and canonical(pe[0])
                == canonical(
                    dict(
                        fixture=fixture,
                        arm=method,
                        result_sha256=fingerprint(result),
                        actual_model_calls=0,
                    )
                ),
                "Pure accounting differs",
            )
        input_reserved = output_reserved = calls = 0
        last_remaining = Budget().max_seconds
        cell_elapsed = 0.0
        for arm, index in _schedule(fixture):
            expected_events.extend(
                ["stage_preparing", "stage_reserved", "stage_accepted"]
            )
            logical = cell_path(fixture, arm, index)
            folder = root / logical
            reservations = [
                e["details"]
                for e in events
                if e["event"] == "stage_reserved"
                and e["details"].get("cell_id") == logical
            ]
            accepted = [
                e["details"]
                for e in events
                if e["event"] == "stage_accepted"
                and e["details"].get("cell_id") == logical
            ]
            need(
                len(reservations) == len(accepted) == 1,
                "Missing/duplicate stage accounting",
            )
            res = reservations[0]
            acc = accepted[0]
            stage = verifier.prepare_stage(fixture, arm, index)
            payload = prepare_payload(stage)
            preparing = [
                e["details"]
                for e in events
                if e["event"] == "stage_preparing"
                and e["details"].get("cell_id") == logical
            ]
            need(
                len(preparing) == 1
                and canonical(preparing[0])
                == canonical(
                    dict(
                        cell_id=logical,
                        request_sha256=fingerprint(stage),
                        payload_sha256=fingerprint(payload),
                    )
                ),
                "Stage preparation binding differs",
            )
            in_quote = len(payload["prompt"].encode()) + 32
            out_quote = payload["n_predict"]
            seconds = res["allocated_budget"]["max_seconds"]
            need(
                type(seconds) in (int, float)
                and math.isfinite(seconds)
                and 0 < seconds <= last_remaining + 1e-6,
                "Shared deadline reset/invalid",
            )
            budget = replace(
                Budget(),
                max_calls=16 - calls,
                max_input_tokens=32000 - input_reserved,
                max_output_tokens=8000 - output_reserved,
                max_seconds=seconds,
            )
            expected = dict(
                fixture=fixture,
                arm=arm,
                stage_index=index,
                cell_id=logical,
                input_reservation=in_quote,
                output_reservation=out_quote,
                allocated_budget=encode(budget),
                request_sha256=fingerprint(stage),
                payload_sha256=fingerprint(payload),
            )
            need(canonical(res) == canonical(expected), "Aggregate reservation differs")
            need(
                input_reserved + in_quote <= 32000
                and output_reserved + out_quote <= 8000
                and calls < 16,
                "Aggregate budget exceeded",
            )
            verifier.verify_stage(fixture, arm, index, acc["receipt_sha256"])
            need(
                canonical(acc)
                == canonical(
                    dict(
                        cell_id=logical,
                        receipt_sha256=acc["receipt_sha256"],
                        fixture_declared_usage=dict(
                            input_tokens=64, output_tokens=64, cost_usd=0.0
                        ),
                        actual_model_calls=0,
                    )
                ),
                "Declared fixture accounting differs",
            )
            config, _ = _read(folder, "configuration.json")
            need(
                canonical(config["budget"]) == canonical(decode(Budget, encode(budget)))
                and canonical(config["caller_configuration"])
                == canonical(
                    dict(
                        comparison_run_id=run_id,
                        cell_id=logical,
                        usage_scope="declared_fixture_usage_not_observed_model_tokens",
                    )
                ),
                "Cell parent allocation differs",
            )
            report, _ = _read(folder, "report.json")
            cell_elapsed += report["elapsed_seconds"]
            input_reserved += in_quote
            output_reserved += out_quote
            calls += 1
            last_remaining = seconds - report["elapsed_seconds"]
            if (
                index
                == len(
                    load_plan()["tether_stages"]
                    if arm == ARMS[0]
                    else load_plan()["stage_order"]
                )
                - 1
            ):
                response, _ = _read(folder, "response.json")
                view, _ = _read(root, f"{fixture}-{arm}-reviewer.json")
                need(
                    canonical(view)
                    == canonical(
                        _interpretation_view(
                            stage, response, _assignment()["arms"][arm]
                        )
                    ),
                    "Interpretation projection differs",
                )
        expected_events.append("fixture_completed")
        ends = [
            e["details"]
            for e in events
            if e["event"] == "fixture_completed"
            and e["details"].get("fixture") == fixture
        ]
        need(len(ends) == 1, "Missing fixture completion")
        elapsed = ends[0]["elapsed_seconds"]
        need(
            type(elapsed) in (int, float)
            and math.isfinite(elapsed)
            and 0 <= elapsed < 300
            and elapsed + 1e-6 >= cell_elapsed
            and elapsed + 1e-6 >= 300 - last_remaining,
            "Fixture elapsed accounting differs",
        )
        record = dict(
            fixture=fixture,
            recorded_adapter_cells=calls,
            input_reserved=input_reserved,
            output_reserved=output_reserved,
            fixture_declared_usage=dict(
                input_tokens=calls * 64, output_tokens=calls * 64, cost_usd=0.0
            ),
            actual_model_calls=0,
            elapsed_seconds=elapsed,
        )
        need(
            canonical(ends[0]) == canonical(record),
            "Fixture accounting summary differs",
        )
        fixture_summaries.append(record)
    expected_events.append("comparison_completed")
    need(
        [e["event"] for e in events] == expected_events,
        "Comparison journal order differs",
    )
    summary, _ = _read(root, "summary.json")
    expected = dict(
        schema_version=1,
        role="evaluation_only",
        run_id=run_id,
        status="recorded_contract_completed_not_scientific_validation",
        plan_sha256=PLAN_SHA256,
        fixtures=fixture_summaries,
        recorded_adapter_cells=12,
        pure_baseline_results=4,
        actual_model_calls=0,
        observed_model_usage=dict(input_tokens=0, output_tokens=0, cost_usd=0.0),
        scientific_validation="not_attempted",
        cpu_time_and_energy="not_measured",
        automatic_retries=False,
    )
    need(
        canonical(summary) == canonical(expected)
        and events[-1]["details"] == freeze(dict(summary_sha256=fingerprint(summary))),
        "Comparison summary differs",
    )
    need(
        _inventory(root) == _members() | {"receipt.json"},
        "Comparison inventory changed",
    )
    for name, proof in receipt["artifacts"].items():
        need(
            canonical(capture_file(root / name, name)) == canonical(proof),
            "Comparison member changed during verification",
        )
    need(
        capture_file(root / "receipt.json", "receipt.json")["sha256"] == sha256,
        "Comparison receipt changed",
    )
    return freeze(
        dict(
            status="verified",
            run_id=run_id,
            receipt_sha256=sha256,
            recorded_adapter_cells=12,
            pure_baseline_results=4,
            actual_model_calls=0,
            scientific_validation="not_attempted",
            scope="synthetic_recorded_contract_only",
        )
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("smoke")
    s.add_argument("--output", type=Path, required=True)
    v = sub.add_parser("verify")
    v.add_argument("--path", type=Path, required=True)
    v.add_argument("--sha256", required=True)
    args = parser.parse_args(argv)
    result = (
        smoke(args.output)
        if args.command == "smoke"
        else verify(args.path, args.sha256)
    )
    print(json.dumps(encode(result), sort_keys=True))


if __name__ == "__main__":
    main()
