"""Root-supervised one-shot entry point; requires a separately frozen input pin."""
import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.inspect_policy.records import parse, proof, read_bytes
from experiments.inspect_policy.process_witnesses import interruption, concurrent_reservation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preparation", type=Path, required=True)
    parser.add_argument("--preparation-sha256", required=True)
    parser.add_argument("--which", choices=("IX06", "IX08"), required=True)
    args = parser.parse_args()
    raw = read_bytes(args.preparation, 2 * 1024 * 1024)
    if hashlib.sha256(raw).hexdigest() != args.preparation_sha256:
        raise ValueError("Frozen witness preparation differs")
    manifest = parse(raw)
    base = args.preparation.parent.resolve()
    for relative, expected in manifest["input_inventory"].items():
        path = (base / relative).resolve()
        if not path.is_relative_to(base) or proof(path) != expected:
            raise ValueError("Frozen witness input differs: " + relative)
    rows = parse(read_bytes(manifest["process_rows"]["path"]))
    oracle = manifest["process_oracle"]
    oracle_proof = {key: oracle[key] for key in ("sha256", "bytes")}
    if args.which == "IX06":
        result = interruption(base / "IX06-interruption", rows["IX06"], oracle["path"], oracle_proof)
    else:
        result = concurrent_reservation(base / "IX08-concurrency", rows["IX08"], oracle["path"], oracle_proof)
    print({"witness": args.which, "status": result["status"], "provider_dispatches": result["provider_dispatches"]})


if __name__ == "__main__":
    main()
