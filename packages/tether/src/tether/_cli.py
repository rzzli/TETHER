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
    return result


def _print(value):
    print(json.dumps(encode(value), indent=2, allow_nan=False))


def _is_outer(path):
    return any((Path(path) / name).exists() for name in (presentation.RECEIPT, presentation.MANIFEST, presentation.FAILURE, "attempt"))


def _delegate(argv):
    result = presentation.invoke_engine(argv)
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
        if args.command in ("demo", "run"):
            _print(presentation.create_outer(args.output, argv))
            return 0
        if args.command == "verify" and _is_outer(args.run_dir):
            if args.outputs_only:
                raise ContractError("TETHER outer verification requires source-inclusive engine verification")
            _print(presentation.verify_outer(args.run_dir, args.receipt_sha256))
            return 0
        if args.command == "inspect-run" and _is_outer(args.run_dir):
            _print(presentation.inspect_outer(args.run_dir))
            return 0
        if args.command in ("verify", "inspect-run"):
            presentation.preflight_run_journals(args.run_dir, verify=args.command == "verify")
        return _delegate(argv)
    except KeyboardInterrupt:
        print("tether: interrupted; inspect retained attempts before starting a new output", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"tether: {error}", file=sys.stderr)
        return getattr(error, "exit_code", 2)
