"""Separate installed-runtime witnesses, not independent-validator cases.

Run with the qualified installed interpreter and -I -B. All fixtures are fresh,
fictional and local. No backend transport, model or provider is invoked.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import operator
from pathlib import Path
import sys
from unittest.mock import patch


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_hashes(root):
    return {path.relative_to(root).as_posix(): file_hash(path) for path in sorted(root.rglob("*")) if path.is_file()}


def _cases_module():
    path = Path(__file__).with_name("cases.py")
    spec = importlib.util.spec_from_file_location("runtime_witness_fictional_cases", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def execute(output, expected_runtime_root):
    import asof
    import tether
    from asof.agents import ExtractiveBackend, Usage
    from asof.artifacts import write_run
    from asof.chrono import load_snapshot
    from asof.cli import main as cli_main
    from asof.contracts import Case, Category
    from asof.journal import RunJournal
    from asof.ledger import EvidenceLedger
    from asof.scorer import ScorerArtifact
    from asof.serde import decode, encode, fingerprint, read_json, write_json
    from asof.workflow import Budget, run_workflow
    from tether._presentation import verify_engine

    output, expected_runtime_root = Path(output).resolve(), Path(expected_runtime_root).resolve()
    output.mkdir(parents=True, exist_ok=False)
    runtime = dict(python=sys.executable, isolated=sys.flags.isolated, asof_version=asof.__version__,
        tether_version=tether.__version__, asof_file=str(Path(asof.__file__).resolve()), tether_file=str(Path(tether.__file__).resolve()))
    if runtime["isolated"] != 1 or (asof.__version__, tether.__version__) != ("0.3.12", "0.5.1"):
        raise RuntimeError("Require isolated qualified installed candidate")
    for module in (asof, tether):
        path = Path(module.__file__).resolve()
        if not path.is_relative_to(expected_runtime_root) or "site-packages" not in path.parts:
            raise RuntimeError("Runtime import did not come from expected installed environment")
    runtime_pins = {str(path): file_hash(path) for module in (asof, tether)
                    for path in Path(module.__file__).parent.rglob("*.py")}
    cases = _cases_module()
    fixture = output / "fixture"
    descriptor, pending = cases.write_source_bundle(fixture, cases.case_specs()[0])
    if pending:
        raise RuntimeError("Runtime witness must use the ordinary preflight source fixture")
    # Add nested containers before admission, with ordinary input pins resealed.
    docs = cases.prepare_documents(cases.case_specs()[0])
    docs["evidence"]["observations"][0]["method"]["parameters"]["nested"] = {"items": [{"value": 7}]}
    docs["snapshot"]["coverage"]["nested"] = {"flags": [True]}
    cases.seal_sources(docs)
    for name, value in docs.items():
        (fixture / "input" / (name + ".json")).write_bytes(cases.file_bytes(value))
    case = decode(Case, read_json(fixture / descriptor["paths"]["case"]))
    store = load_snapshot(fixture / descriptor["paths"]["snapshot"], case,
                          fixture / descriptor["paths"]["catalog"])
    model = decode(ScorerArtifact, read_json(fixture / descriptor["paths"]["scorer"]))
    controls = []

    def immutable(name, value, action):
        before = fingerprint(value)
        caught = None
        try:
            action()
        except (TypeError, AttributeError) as error:
            caught = type(error).__name__
        after = fingerprint(value)
        passed = caught is not None and before == after
        controls.append(dict(name=name, passed=passed, rejected_mutation=caught,
                             before_sha256=before, after_sha256=after))
        if not passed:
            raise AssertionError(name)

    record = store.query(case, Category.GENETICS)[0]
    immutable("query_nested_mapping", record, lambda: operator.setitem(
        record.observation.method.parameters["nested"]["items"][0], "value", 8))
    immutable("query_nested_sequence", record, lambda: record.observation.method.parameters["nested"]["items"].append({"value": 8}))
    immutable("query_feature_mapping", record, lambda: operator.setitem(record.observation.features, "genetic_support", 0.1))
    ledger = EvidenceLedger(case, store)
    claim = ledger.append(Category.GENETICS, "obs-1")
    immutable("committed_claim_nested_mapping", ledger.claims, lambda: operator.setitem(
        claim.evidence.observation.method.parameters["nested"]["items"][0], "value", 9))

    finalized = output / "finalized"
    journal = RunJournal(finalized)
    budget = Budget(max_retries=0)
    try:
        request = dict(case=case, snapshot=store.snapshot, scorer=model, budget=budget, disabled=(), review_enabled=True,
                       catalog_policy=store.catalog_policy, backend_provenance=None)
        write_json(finalized / "request.json", request)
        journal.append("inputs_archived", request_sha256=fingerprint(read_json(finalized / "request.json")))
        result = run_workflow(case, store, ExtractiveBackend(), model, budget, journal=journal)
        anchor = write_run(finalized, result, store, model, journal)
    finally:
        journal.close()
    finalized_hashes = tree_hashes(finalized)
    immutable("finalized_nested_coverage", result, lambda: operator.setitem(
        result.coverage["genetics"]["source_coverage"]["nested"]["flags"], 0, False))
    plan = next(event for event in result.trace if event["event"] == "plan")
    immutable("finalized_trace_configuration", result, lambda: operator.setitem(
        plan["details"]["configuration"], "backend_id", "changed"))
    immutable("finalized_configuration_budget", result, lambda: setattr(result.configuration["budget"], "max_calls", 99))
    verified = verify_engine(finalized, anchor, True)
    controls.append(dict(name="finalized_bytes_and_semantics_after_mutations", passed=tree_hashes(finalized) == finalized_hashes
                         and verified["semantic_consistency"] == "verified", verification=verified))

    stdout, stderr = io.StringIO(), io.StringIO()
    with patch.object(ExtractiveBackend, "quote", side_effect=AssertionError("Forbidden quote during output collision")) as quote, \
         patch.object(ExtractiveBackend, "select", side_effect=AssertionError("Forbidden select during output collision")) as select, \
         redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = cli_main(["run", "--output", str(finalized), "--case", str(fixture / descriptor["paths"]["case"]),
                              "--snapshot", str(fixture / descriptor["paths"]["snapshot"])])
    controls.append(dict(name="existing_output_collision_preserves_bytes_and_dispatches_nothing",
        passed=exit_code == 2 and quote.call_count == select.call_count == 0 and tree_hashes(finalized) == finalized_hashes,
        exit_code=exit_code, quote_calls=quote.call_count, selection_calls=select.call_count, diagnostic=stderr.getvalue()))

    interrupted = output / "interrupted"
    journal = RunJournal(interrupted)
    try:
        journal.append("dispatch", category="genetics", attempt=1, attempt_id="genetics:1",
                       request_sha256="f" * 64, reserved=Usage(2, 3, 0))
    finally:
        journal.close()
    # Simulated crash after a durable dispatch and during the next event write;
    # no actual paid, remote or model call occurred.
    with (interrupted / "journal.jsonl").open("ab") as stream:
        stream.write(b'{"sequence":2,"event":')
    before = tree_hashes(interrupted)
    stdout, stderr = io.StringIO(), io.StringIO()
    with patch.object(ExtractiveBackend, "quote", side_effect=AssertionError("Recovery must not quote")) as quote, \
         patch.object(ExtractiveBackend, "select", side_effect=AssertionError("Recovery must not select")) as select, \
         redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = cli_main(["inspect-run", "--run-dir", str(interrupted)])
    recovery = json.loads(stdout.getvalue())
    controls.append(dict(name="interrupted_inspection_keeps_unresolved_usage_without_redispatch",
        passed=exit_code == 0 and quote.call_count == select.call_count == 0 and tree_hashes(interrupted) == before
               and recovery["unresolved_attempts"] == ["genetics:1"]
               and recovery["estimated_upper_usage"] == dict(input_tokens=2, output_tokens=3, cost_usd=0)
               and recovery["receipt_present"] is False
               and recovery["recovery_action"] == "inspect only; never automatically repeat unresolved calls",
        quote_calls=quote.call_count, selection_calls=select.call_count, recovery=recovery,
        simulation="Fictional durable dispatch plus incomplete final journal bytes; no actual process kill or inference"))
    stable = all(file_hash(path) == pin for path, pin in runtime_pins.items())
    report = dict(schema_version=1, status="PASS" if stable and all(row["passed"] for row in controls) else "FAILED",
        completed_at_utc=datetime.now(timezone.utc).isoformat(), runtime=runtime, installed_runtime_unchanged=stable,
        control_count=len(controls), controls=controls, runtime_source_sha256=runtime_pins,
        witness_code_sha256=file_hash(Path(__file__)), case_constructor_sha256=file_hash(Path(cases.__file__)),
        provider_spending_usd=0, actual_model_calls=0,
        scope="Separate installed-runtime witnesses; not independent-validator performance or paired corpus denominators")
    with (output / "RUNTIME-WITNESSES.json").open("x", encoding="utf-8") as stream:
        json.dump(encode(report), stream, indent=2, sort_keys=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-runtime-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = execute(args.output, args.expected_runtime_root)
    except BaseException as error:
        failure = dict(status="FAILED", error_class=type(error).__name__, message=str(error))
        # The caller retains stderr. Do not publish into a directory whose
        # ownership may not have been acquired (notably an output collision).
        print(json.dumps(failure), file=sys.stderr)
        raise
    print(json.dumps(dict(status=report["status"], controls=report["control_count"], output=str(args.output.resolve())), indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
