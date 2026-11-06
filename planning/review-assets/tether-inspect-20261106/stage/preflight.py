"""Independent read-only check of the inherited corpus; no validator executes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import time
from datetime import datetime, timezone

FROZEN_SHA = "3ec7625fa601a517d8e2dd302228f9f465f35e877f79cd1a587a3a63b394a4fc"


def fingerprint(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
            raise ValueError("Linked input: " + str(part))
    before = path.stat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("Nonregular input")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        if identity(os.fstat(stream.fileno())) != identity(before):
            raise ValueError("Changed before open")
        size = 0
        while block := stream.read(1024 * 1024):
            size += len(block)
            h.update(block)
        if identity(os.fstat(stream.fileno())) != identity(before):
            raise ValueError("Changed during read")
    if size != before.st_size or identity(path.stat()) != identity(before):
        raise ValueError("Changed after read")
    return {"bytes": size, "sha256": h.hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    corpus = root / "data/benchmark/tether-equal-policy-v2-patched-20261105-attempt01"
    if args.output.exists():
        raise FileExistsError(args.output)
    started = time.perf_counter()
    frozen_pin = fingerprint(corpus / "FROZEN.json")
    if frozen_pin["sha256"] != FROZEN_SHA:
        raise ValueError("Inherited freeze differs")
    frozen = json.loads((corpus / "FROZEN.json").read_text(encoding="utf-8"))
    checked = {}
    def check(path, expected):
        got = fingerprint(path)
        if got != expected:
            raise ValueError("Proof mismatch: " + str(path))
        checked[str(Path(path).resolve())] = got
    check(corpus / "oracle.json", frozen["oracle_pin"])
    check(corpus / "trusted-runtime.json", frozen["trusted_runtime_pin"])
    bundles = corpus / "bundles"
    actual_files = {p.relative_to(bundles).as_posix() for p in bundles.rglob("*") if p.is_file()}
    actual_dirs = {p.relative_to(bundles).as_posix() for p in bundles.rglob("*") if p.is_dir()}
    if actual_files != set(frozen["bundles"]) or actual_dirs != set(frozen["bundle_directories"]):
        raise ValueError("Whole bundle inventory differs")
    for name, pin in frozen["bundles"].items():
        check(bundles / name, pin)
    for name, pin in frozen["sources"].items():
        check(root / name, pin)
    for name, pin in frozen["runtime_proofs"].items():
        check(Path(name), pin)
    for package in frozen["installed_runtime"].values():
        base = Path(package["root"])
        for name, pin in package["files"].items():
            check(base / name, pin)
    ids = [row["control_id"] for row in frozen["cases"]]
    if len(ids) != 109 or len(set(ids)) != 109:
        raise ValueError("Inherited schedule differs")
    result = {"schema_version": 1, "status": "pass", "at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "read_only_input_byte_inventory_no_case_validation_or_dispatch",
              "frozen": frozen_pin, "helper": fingerprint(__file__), "cases": len(ids),
              "bundle_files": len(actual_files), "bundle_directories": len(actual_dirs),
              "unique_files_hashed": len(checked), "logical_bytes_hashed": sum(p["bytes"] for p in checked.values()),
              "checking_wall_seconds": time.perf_counter() - started,
              "runtime_calls": 0, "scientific_validation": "not_established", "files": checked}
    raw = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    with args.output.open("xb") as out:
        out.write(raw)
    print(json.dumps({key: value for key, value in result.items() if key != "files"}, indent=2))


if __name__ == "__main__":
    main()
