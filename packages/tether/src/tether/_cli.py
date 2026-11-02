"""Canonical TETHER CLI; the compatibility engine remains unchanged."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from asof import cli as legacy
from asof.serde import ContractError, encode

from . import __version__, __core_version__
from . import _presentation as presentation


def _brand(parser):
    parser.prog = parser.prog.replace("asof", "tether", 1)
    parser.allow_abbrev = False
    if parser.description:
        parser.description = parser.description.replace("AsOf", "TETHER")
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for child in action.choices.values():
                _brand(child)
    return parser


def parser():
    result = _brand(legacy.parser())
    result.description = "TETHER auditable evidence workflow (frozen AsOf compatibility engine)"
    result.add_argument("--version", action="version", version=f"TETHER {__version__} (compatibility engine {__core_version__})")
    for action in result._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, child in action.choices.items():
                if name == "run":
                    child.add_argument("--catalog-policy", type=Path, help="Explicit schema-2 artifact policy; --catalog remains the schema-1 anchor")
                    child.add_argument("--policy-use", help="Exact allowed policy use ID")
                    child.add_argument("--policy-roots", type=Path, help="Schema-1 absolute root alias map")
                    child.add_argument("--policy-frame-sha256", help="Independently selected exact frame SHA-256")
                if name != "verify":
                    child.add_argument("--process-timeout-seconds", type=float, default=None,
                        help="Owned child absolute deadline, default 3600s; separate from workflow budget")
                    child.add_argument("--process-output-bytes", type=int, default=None,
                        help="Aggregate child stdout/stderr cap, default 16777216 bytes (maximum 67108864)")
    return result


def _print(value):
    print(json.dumps(encode(value), indent=2, allow_nan=False))


def _is_outer(path):
    return any((Path(path) / name).exists() for name in (presentation.RECEIPT, presentation.MANIFEST, presentation.FAILURE, "attempt"))


def _delegate(argv, limits):
    result = presentation.invoke_engine(argv, limits=limits)
    if result.stdout:
        sys.stdout.write(result.stdout.decode("utf-8", errors="replace"))
    if result.stderr:
        text = result.stderr.decode("utf-8", errors="replace")
        sys.stderr.write("\n".join("tether:" + line[5:] if line.startswith("asof:") else line for line in text.split("\n")))
    return result.returncode


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    args = parser().parse_args(argv)
    try:
        explicit = any(getattr(args, name, None) is not None for name in
                       ("process_timeout_seconds", "process_output_bytes"))
        defaults = presentation.ProcessLimits()
        limits = presentation.ProcessLimits(
            args.process_timeout_seconds if getattr(args, "process_timeout_seconds", None) is not None else defaults.timeout_seconds,
            args.process_output_bytes if getattr(args, "process_output_bytes", None) is not None else defaults.max_output_bytes)
        limits.validate()
        # Wrapper controls never enter the frozen parser or its workflow budget.
        engine_argv, index = [], 0
        while index < len(argv):
            token = argv[index]
            if token in ("--process-timeout-seconds", "--process-output-bytes"):
                index += 2
            elif token.startswith(("--process-timeout-seconds=", "--process-output-bytes=")):
                index += 1
            else:
                engine_argv.append(token)
                index += 1
        if args.command in ("demo", "run"):
            policy_request = None
            flags = ("catalog_policy", "policy_use", "policy_roots", "policy_frame_sha256")
            supplied = [getattr(args, name, None) is not None for name in flags]
            if any(supplied):
                if not all(supplied) or args.catalog is None:
                    raise ContractError("Artifact policy requires --catalog, --catalog-policy, --policy-use, --policy-roots and --policy-frame-sha256")
                if args.scorer is not None or args.replay is not None or args.local_model is not None:
                    raise ContractError("Artifact policy run currently supports offline extractive execution without scorer/replay/local-model")
                from ._catalog_binding import PolicyRequest
                policy_request = PolicyRequest(args.catalog_policy, args.policy_roots, args.case,
                    args.snapshot, args.catalog, args.policy_use, args.policy_frame_sha256)
                policy_request.validate()
            _print(presentation.create_outer(args.output, argv, limits=limits, policy_request=policy_request))
            return 0
        if args.command == "verify" and _is_outer(args.run_dir):
            if args.outputs_only:
                raise ContractError("TETHER outer verification requires source-inclusive engine verification")
            _print(presentation.verify_outer(args.run_dir, args.receipt_sha256))
            return 0
        if args.command == "inspect-run" and _is_outer(args.run_dir):
            if explicit:
                raise ContractError("Process limits do not apply to in-process outer inspection")
            _print(presentation.inspect_outer(args.run_dir))
            return 0
        if args.command == "verify":
            _print(presentation.verify_engine(args.run_dir, args.receipt_sha256, not args.outputs_only))
            return 0
        if args.command in ("verify", "inspect-run"):
            presentation.preflight_run_journals(args.run_dir, verify=args.command == "verify")
        return _delegate(engine_argv, limits)
    except KeyboardInterrupt as error:
        print("tether: interrupted; inspect any retained attempt before starting a new output", file=sys.stderr)
        captured = getattr(error, "tether_engine_result", None)
        if captured is not None and captured.supervision is not None:
            print(json.dumps({"tether_process_failure": captured.supervision}), file=sys.stderr)
        return 130
    except Exception as error:
        print(f"tether: {error}", file=sys.stderr)
        captured = getattr(error, "tether_engine_result", None)
        if captured is not None and captured.supervision is not None:
            print(json.dumps({"tether_process_failure": captured.supervision}), file=sys.stderr)
        return getattr(error, "exit_code", 2)
