"""Retain commands, results and source preservation for the authorized SC01 review."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback


METHODS = Path(__file__).resolve().parent
ROOT = METHODS.parents[3]
LAUNCH = METHODS / "actual-launch-attempt01"
RECON = METHODS / "actual-reconstruction-attempt01"
COMPARE = METHODS / "actual-comparison-attempt01"
MANIFEST = ROOT / "planning/review-assets/tether-semantic-20261106/decomposition/actual-freeze-attempt01/INPUT-MANIFEST.json"
BASELINE = ROOT / "data/benchmark/scifact/native-20261105T234805Z-attempt01"
EXPECTED_MANIFEST = "f465f1579dd6f71d82d261c0a1230acfc258935c557025f0f0197fe670659203"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def proof(path):
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2)
        stream.write("\n")


def launch(name, argv):
    write(LAUNCH / (name + "-COMMAND.json"), {"argv": argv, "cwd": str(ROOT), "started_at_utc": datetime.now(timezone.utc).isoformat()})
    started = time.perf_counter()
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=300, check=False)
    (LAUNCH / (name + "-STDOUT.txt")).write_text(result.stdout, encoding="utf-8", newline="\n")
    (LAUNCH / (name + "-STDERR.txt")).write_text(result.stderr, encoding="utf-8", newline="\n")
    outcome = {"returncode": result.returncode, "elapsed_seconds": time.perf_counter() - started}
    write(LAUNCH / (name + "-RESULT.json"), outcome)
    assert result.returncode == 0, (name, result.stderr)
    return outcome


def main():
    assert proof(MANIFEST)["sha256"] == EXPECTED_MANIFEST
    helpers = {"independent_native_check.py": "68703fe9713580223e0ed918758ab7f87e9bd00205375aa3a753b9ef1bfd83d8",
               "compare_primary.py": "f4196156da4cb9a4c7703924d5b308b27928794102ad730fac89146a850c663e"}
    for name, expected in helpers.items():
        assert proof(METHODS / name)["sha256"] == expected
    manifest = read(MANIFEST)
    assert not RECON.exists() and not COMPARE.exists()
    interpreter = ROOT / "data/cache/tether-scifact-env-attempt02/environment/Scripts/python.exe"
    flags = [str(interpreter), "-I", "-B", "-X", "utf8"]
    commands = {}
    commands["reconstruct"] = launch("RECONSTRUCT", flags + [str(METHODS / "independent_native_check.py"),
        "--output", str(RECON), "--evaluator", str(ROOT / "data/benchmark/scifact/reconstruction-20261105-attempt01/official/dev-raw/eval.py"),
        "--freeze", str(MANIFEST), "--baseline", str(BASELINE),
        "--references", str(ROOT / "data/benchmark/scifact/preparation-20261105-attempt03/restricted/references_dev.jsonl")])
    COMPARE.mkdir()
    commands["compare"] = launch("COMPARE", flags + [str(METHODS / "compare_primary.py"),
        "--primary", str(ROOT / "data/benchmark/scifact_diagnostics/20261106-attempt01/DECOMPOSITION.json"),
        "--independent", str(RECON / "INDEPENDENT-RECONSTRUCTION.json"), "--output", str(COMPARE / "COMPARISON.json")])
    prior = read(METHODS / "source-preflight-attempt02/PREFLIGHT.json")
    original = read(METHODS / "source-preflight-attempt02/VERIFIED-BASELINE-INVENTORY.json")["outputs"]
    actual_files = {p.relative_to(BASELINE).as_posix() for p in BASELINE.rglob("*") if p.is_file()}
    assert actual_files == set(original) | {"RECEIPT.json"}
    for item in original.values():
        assert proof(Path(item["path"])) == item
    for items in (prior["anchors"], prior["prepared_products_verified"]):
        for item in items.values():
            assert proof(Path(item["path"])) == item
    pins = list(manifest["inputs"].values()) + manifest["source_pins"] + manifest.get("authority_pins", [])
    for item in pins:
        assert proof(Path(item["path"])) == item
    assert proof(MANIFEST)["sha256"] == EXPECTED_MANIFEST
    for name, expected in helpers.items():
        assert proof(METHODS / name)["sha256"] == expected
    record = {"status": "PASS", "completed_at_utc": datetime.now(timezone.utc).isoformat(),
              "commands": commands, "manifest": proof(MANIFEST), "script": proof(Path(__file__)),
              "comparison": proof(COMPARE / "COMPARISON.json"), "reconstruction": proof(RECON / "INDEPENDENT-RECONSTRUCTION.json"),
              "original_stage_outputs_rechecked": len(original), "original_stage_exact_fileset_unchanged": True,
              "original_authorities_and_prepared_products_rechecked": True, "all_frozen_pins_rechecked": len(pins),
              "reader_and_comparator_unchanged": True}
    write(LAUNCH / "ACCEPTANCE.json", record)
    print(json.dumps({"status": "PASS", "acceptance": proof(LAUNCH / "ACCEPTANCE.json"), "comparison": record["comparison"]}))


if __name__ == "__main__":
    LAUNCH.mkdir(parents=True, exist_ok=False)
    try:
        main()
    except Exception as exc:
        write(LAUNCH / "FAILED.json", {"status": "FAIL", "type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc()})
        raise
