"""Local execution, demo, verification and separate evaluator commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agents import ExtractiveBackend, ReplayBackend
from .artifacts import verify_run, write_run
from .chrono import load_snapshot
from .contracts import Case, Category
from .scorer import Prediction, ScorerArtifact
from .serde import ContractError, decode, encode, fingerprint, read_json, write_json
from .workflow import Budget, run_workflow
from .journal import RunJournal, inspect_run


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="asof", description="AsOf local evidence workflow")
    commands = result.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Execute an approved normalized evidence snapshot")
    run.add_argument("--case", type=Path, required=True)
    run.add_argument("--snapshot", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--catalog", type=Path)
    run.add_argument("--scorer", type=Path)
    run.add_argument("--replay", type=Path)
    run.add_argument("--disable", action="append", choices=[item.value for item in Category], default=[])
    run.add_argument("--no-review-retries", action="store_true")
    run.add_argument("--max-calls", type=int, default=16)
    run.add_argument("--max-cost-usd", type=float, default=0)
    run.add_argument("--max-input-tokens", type=int, default=32000)
    run.add_argument("--max-output-tokens", type=int, default=8000)
    run.add_argument("--max-seconds", type=float, default=300)
    run.add_argument("--max-retries", type=int, default=1)
    demo = commands.add_parser("demo", help="Run the bundled synthetic offline example")
    demo.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify", help="Verify output/trace/source integrity")
    verify.add_argument("--run-dir", type=Path, required=True)
    verify.add_argument("--receipt-sha256")
    verify.add_argument("--outputs-only", action="store_true")
    inspect = commands.add_parser("inspect-run", help="Read durable run attempts or build stages; never restart work")
    inspect.add_argument("--run-dir", type=Path, required=True)
    source = commands.add_parser("inspect-source", help="Validate explicit receipt-verified source inputs")
    source.add_argument("--manifest", type=Path, required=True)
    source.add_argument("--catalog", type=Path, required=True)
    source.add_argument("--report", type=Path)
    build = commands.add_parser("build-snapshot", help="Build v2 contemporary T6 packets from approved local files")
    build.add_argument("--manifest", type=Path, required=True)
    build.add_argument("--catalog", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    evaluation = commands.add_parser("evaluate", help="Evaluator-only descriptive T1 metrics")
    evaluation.add_argument("--predictions", type=Path, nargs="+", required=True)
    evaluation.add_argument("--labels", type=Path, required=True)
    evaluation.add_argument("--output", type=Path, required=True)
    evaluation.add_argument("--allow-synthetic", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    journal, stage = None, "configuration"
    try:
        if args.command == "verify":
            answer = verify_run(args.run_dir, args.receipt_sha256, not args.outputs_only)
        elif args.command == "inspect-run":
            answer = inspect_run(args.run_dir)
        elif args.command in ("inspect-source", "build-snapshot"):
            from .ingest import inspect_sources, build_snapshot
            if args.command == "inspect-source":
                answer = inspect_sources(args.manifest, args.catalog)
                if args.report:
                    if args.report.exists():
                        raise ContractError("Refusing to overwrite an inspection report")
                    args.report.parent.mkdir(parents=True, exist_ok=True)
                    write_json(args.report, answer)
            else:
                answer = build_snapshot(args.manifest, args.catalog, args.output)
        elif args.command == "evaluate":
            # Deliberately imported only in the separate evaluator command.
            from .evaluation import Outcomes, evaluate
            labels = decode(Outcomes, read_json(args.labels), "outcomes")
            predictions = tuple(decode(Prediction, read_json(path), "prediction")
                                for path in args.predictions)
            answer = evaluate(predictions, labels, args.allow_synthetic)
            if args.output.exists():
                raise ContractError("Refusing to overwrite an evaluation result")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            write_json(args.output, answer)
        else:
            journal = RunJournal(args.output)
            if args.command == "demo":
                base = Path(__file__).parent / "demo" / "v2"
                case_path, snapshot_path, model_path = base / "case.json", base / "snapshot.json", base / "scorer.json"
                catalog, backend, budget, disabled, review = None, ExtractiveBackend(), Budget(), (), True
            else:
                case_path, snapshot_path, model_path = args.case, args.snapshot, args.scorer
                catalog = args.catalog
                backend = ReplayBackend(args.replay) if args.replay else ExtractiveBackend()
                budget = Budget(args.max_calls, args.max_input_tokens, args.max_output_tokens,
                                args.max_cost_usd, args.max_seconds, args.max_retries)
                disabled = tuple(Category(item) for item in args.disable)
                review = not args.no_review_retries
            case = decode(Case, read_json(case_path), "case")
            case.validate()
            model = decode(ScorerArtifact, read_json(model_path), "scorer") if model_path else None
            if model is not None:
                model.validate()
            stage = "source_validation"
            write_json(args.output / "request.json", {"case": case, "snapshot": read_json(snapshot_path),
                       "scorer": model, "budget": budget, "disabled": disabled, "review_enabled": review,
                       "catalog_policy": read_json(catalog) if catalog else None,
                       "backend_provenance": getattr(backend, "provenance", None)})
            journal.append("inputs_archived", request_sha256=fingerprint(read_json(args.output / "request.json")))
            store = load_snapshot(snapshot_path, case, catalog)
            stage = "execution"
            result = run_workflow(case, store, backend, model, budget, disabled, review, journal)
            stage = "artifact_finalization"
            digest = write_run(args.output, result, store, model, journal)
            answer = {"status": result.status, "output": str(args.output.resolve()),
                      "claims": len(result.claims), "prediction": result.prediction,
                      "receipt_sha256": digest}
            print(json.dumps(encode(answer), indent=2, allow_nan=False))
            return 0 if result.status == "completed" else 130 if result.status == "interrupted" else 3
        print(json.dumps(encode(answer), indent=2, allow_nan=False))
        return 0
    except KeyboardInterrupt as error:
        if journal:
            try:
                journal.fail(error, stage)
            except OSError:
                pass
        print("asof: interrupted; inspect the durable journal before retrying", file=sys.stderr)
        return 130
    except Exception as error:
        if journal:
            try:
                journal.fail(error, stage)
            except OSError:
                pass
        print(f"asof: {error}", file=sys.stderr)
        return 2
    finally:
        if journal:
            journal.close()

