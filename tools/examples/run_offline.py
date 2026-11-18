"""Run a prepared IL6R/RA example through the installed, policy-bound API.

No downloading, registration, model inference or source permission is implicit.
Use a prepared input directory with its explicit artifact policy and retain its
frame hash before execution. Outputs must be new sibling directories outside it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from tether.api import PolicyInputs, run_offline, export_run, verify_bundle


def run_example(inputs: Path, output: Path, bundle_output: Path, frame_sha256: str) -> dict[str, object]:
    started = time.monotonic()
    inputs = inputs.absolute()
    selection = PolicyInputs(inputs / "case.json", inputs / "snapshot/snapshot.json",
                             inputs / "data/catalog/sources.json", inputs / "policy.json",
                             inputs / "roots.json", "p10-il6r-example", frame_sha256)
    run = run_offline(selection, output, source_roots=(inputs,))
    bundle = export_run(run, bundle_output, source_roots=(inputs,))
    verification = verify_bundle(bundle)
    return dict(status="completed", run_directory=str(run.directory), dossier=str(run.dossier),
                receipt_sha256=run.receipt_sha256, engine_receipt_sha256=run.engine_receipt_sha256,
                bundle_directory=str(bundle.directory), manifest_sha256=bundle.manifest_sha256,
                verification=verification, elapsed_seconds=time.monotonic() - started,
                scientific_validation="not_established")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bundle-output", required=True, type=Path)
    parser.add_argument("--frame-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(run_example(args.inputs, args.output, args.bundle_output, args.frame_sha256), indent=2))


if __name__ == "__main__":
    main()
