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
    result = argparse.ArgumentParser(prog="tether-engine", description="TETHER local evidence workflow")
    commands = result.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Execute an approved normalized evidence snapshot")
    run.add_argument("--case", type=Path, required=True)
    run.add_argument("--snapshot", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--catalog", type=Path)
    run.add_argument("--scorer", type=Path)
    run.add_argument("--replay", type=Path)
    run.add_argument("--local-model", type=Path, help="Explicit loopback model configuration; never the default")
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
    bundle_export = commands.add_parser("bundle-export", help="Copy a sealed offline run into a fresh portable bundle")
    bundle_export.add_argument("--run-dir", type=Path, required=True)
    bundle_export.add_argument("--output", type=Path, help="Fresh output directory; default is a UTC-named directory")
    bundle_export.add_argument("--source-root", type=Path, action="append", required=True)
    bundle_export.add_argument("--receipt-sha256")
    bundle_export.add_argument("--omit-originals", action="store_true", help="Exclude raw originals and skip source replay")
    for name in ("bundle-inspect", "bundle-verify"):
        bundle_reader = commands.add_parser(name, help="Inspect the manifest or verify a relocated bundle")
        bundle_reader.add_argument("--bundle-dir", type=Path, required=True)
        bundle_reader.add_argument("--manifest-sha256")
        if name == "bundle-verify":
            bundle_reader.add_argument("--bytes-only", action="store_true", help="Verify content hashes without semantic replay")
    source = commands.add_parser("inspect-source", help="Validate explicit receipt-verified source inputs")
    source.add_argument("--manifest", type=Path, required=True)
    source.add_argument("--catalog", type=Path, required=True)
    source.add_argument("--report", type=Path)
    build = commands.add_parser("build-snapshot", help="Build v2 contemporary T6 packets from approved local files")
    build.add_argument("--manifest", type=Path, required=True)
    build.add_argument("--catalog", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--cases", type=Path, help="Explicit frozen schema-version-1 contemporary T6 case pack")
    build.add_argument("--cases-sha256", help="Optional SHA-256 anchor for the frozen case-pack bytes")
    build.add_argument("--packet-layout", choices=("single", "bounded"), default="single",
                       help="Explicitly permit multiple complete packets per case; each stays within 64 MiB")
    for name, help_text in (("evaluate", "Receipt-bound fixed-horizon T1 evaluation"),
                            ("evaluate-baseline", "Declared external-baseline fixed-horizon evaluation")):
        evaluation = commands.add_parser(name, help=help_text)
        for source_name in ("cohort", "producer", "labels"):
            evaluation.add_argument("--" + source_name, type=Path, required=True)
            evaluation.add_argument("--" + source_name + "-sha256", required=True)
        evaluation.add_argument("--output", type=Path, required=True)
        evaluation.add_argument("--allow-synthetic", action="store_true")
    raw = commands.add_parser("evaluate-raw", help="Unverified prediction diagnostics; no producer checks")
    raw.add_argument("--predictions", type=Path, nargs="+", required=True)
    raw.add_argument("--labels", type=Path, required=True)
    raw.add_argument("--policy", type=Path, help="Explicit fixed-horizon policy; otherwise infer one horizon with zero lag")
    raw.add_argument("--output", type=Path, required=True)
    raw.add_argument("--allow-synthetic", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    journal, stage = None, "configuration"
    try:
        if args.command == "verify":
            answer = verify_run(args.run_dir, args.receipt_sha256, not args.outputs_only)
        elif args.command == "inspect-run":
            answer = inspect_run(args.run_dir)
        elif args.command in ("bundle-export", "bundle-inspect", "bundle-verify"):
            from .bundle import automatic_output, export_bundle, inspect_bundle, verify_bundle
            if args.command == "bundle-export":
                answer = export_bundle(args.run_dir, args.output or automatic_output(), source_roots=args.source_root,
                                       receipt_sha256=args.receipt_sha256, include_originals=not args.omit_originals)
            elif args.command == "bundle-inspect":
                answer = inspect_bundle(args.bundle_dir, args.manifest_sha256)
            else:
                answer = verify_bundle(args.bundle_dir, args.manifest_sha256, replay=not args.bytes_only)
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
                answer = build_snapshot(args.manifest, args.catalog, args.output, packet_layout=args.packet_layout,
                                        cases_path=args.cases, cases_sha256=args.cases_sha256)
        elif args.command in ("evaluate", "evaluate-baseline", "evaluate-raw"):
            # Deliberately imported only in the separate evaluator command.
            from .maintenance import write_new_json
            if args.output.exists() or args.output.is_symlink():
                raise ContractError("Refusing to overwrite an evaluation result")
            if args.command == "evaluate-raw":
                from .evaluation import EvaluationPolicy, Outcomes, evaluate
                labels = decode(Outcomes, read_json(args.labels), "outcomes")
                predictions = tuple(decode(Prediction, read_json(path), "prediction")
                                    for path in args.predictions)
                policy = decode(EvaluationPolicy, read_json(args.policy), "policy") if args.policy else None
                answer = evaluate(predictions, labels, args.allow_synthetic, policy=policy)
            else:
                from .evaluation_binding import evaluate_bound
                answer = evaluate_bound(args.cohort, args.cohort_sha256,
                                        args.producer, args.producer_sha256,
                                        args.labels, args.labels_sha256,
                                        allow_synthetic=args.allow_synthetic,
                                        expected_producer_kind=("tether_run_predictions" if args.command == "evaluate"
                                                                else "external_baseline_predictions"))
            write_new_json(args.output, answer)
        else:
            journal = RunJournal(args.output)
            if args.command == "demo":
                base = Path(__file__).parent / "demo" / "v2"
                case_path, snapshot_path, model_path = base / "case.json", base / "snapshot.json", base / "scorer.json"
                catalog, backend, budget, disabled, review = None, ExtractiveBackend(), Budget(), (), True
            else:
                case_path, snapshot_path, model_path = args.case, args.snapshot, args.scorer
                catalog = args.catalog
                if args.replay and args.local_model:
                    raise ContractError('Choose replay or explicit local inference')
                if args.local_model:
                    from .local_model import LocalSelectionBackend
                    backend = LocalSelectionBackend(args.local_model)
                else:
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
            if hasattr(backend, 'records'):
                write_json(args.output / 'backend-execution.json', {'schema_version': 1, 'attempts': backend.records})
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
        print("tether-engine: interrupted; inspect the durable journal before retrying", file=sys.stderr)
        return 130
    except Exception as error:
        if journal:
            try:
                journal.fail(error, stage)
            except OSError:
                pass
        print(f"tether-engine: {error}", file=sys.stderr)
        return 2
    finally:
        if journal:
            journal.close()

