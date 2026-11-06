"""One externally anchored, supervised collection dispatch; no automatic retry."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time

from asof.atomic import publish_bytes
from asof.journal import RunJournal
from asof.serde import canonical, parse_json
from tether._process import ProcessLimits, supervise_command, validate_success_report

ROOT = Path(__file__).resolve().parents[3]


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def execute(recipe_path, expected_hash, output):
    need(sys.flags.isolated and sys.dont_write_bytecode and sys.pycache_prefix,
         "Use isolated Python, no bytecode writes and a fresh cache prefix")
    cache = Path(sys.pycache_prefix).resolve()
    need(cache.is_relative_to(ROOT / "data/cache"), "Wrong cache root")
    cache.mkdir(parents=True, exist_ok=True)
    need(not any(cache.iterdir()), "Cache must start empty")
    raw = Path(recipe_path).read_bytes()
    need(len(raw) < 1024**2 and hashlib.sha256(raw).hexdigest() == expected_hash,
         "Collection recipe anchor differs")
    recipe = parse_json(raw)
    need(recipe["kind"] == "labbench_collection_dispatch", "Wrong recipe")
    for name, expected in recipe["code_pins"].items():
        path = (ROOT / name).resolve()
        need(path.is_relative_to(ROOT) and sha(path) == expected, "Source freeze differs")
    command = recipe["command"]
    need(command[0] == sys.executable and "--stage-seconds" in command,
         "Use the qualified interpreter and explicit source budget")
    limits = ProcessLimits(timeout_seconds=recipe["parent_seconds"], max_output_bytes=8*1024**2)
    output = Path(output).resolve()
    need(output.is_relative_to(ROOT / "data"), "Control output must be a fresh data path")
    journal = RunJournal(output, kind="build")
    result = None
    started = time.monotonic()
    try:
        publish_bytes(output / "recipe.json", raw)
        journal.append("collection_child_dispatch", recipe_sha256=expected_hash,
                       command=command, limits=limits.payload(), retries=0)
        try:
            result = supervise_command(command, limits=limits)
        except BaseException as error:
            result = getattr(error, "tether_engine_result", None)
            raise
        finally:
            if result is not None:
                publish_bytes(output / "child.stdout", result.stdout)
                publish_bytes(output / "child.stderr", result.stderr)
                publish_bytes(output / "SUPERVISION.json", canonical(dict(
                    returncode=result.returncode, supervision=result.supervision)) + b"\n")
        need(result.returncode == 0, "Source collection returned a partial or failed outcome")
        validate_success_report(result.supervision, limits, len(result.stdout), len(result.stderr))
        need(not any(cache.iterdir()), "Import cache changed")
        for name, expected in recipe["code_pins"].items():
            need(sha(ROOT / name) == expected, "Source code changed during collection")
        manifest = Path(recipe["collection_output"]) / "manifest.json"
        status = parse_json(manifest.read_bytes())["status"]
        need(status == "completed", "Collection manifest is not complete")
        record = dict(status=status, manifest_sha256=sha(manifest),
                      wall_seconds=time.monotonic()-started, retries=0,
                      source_inclusive_reverification="pending")
        journal.append("collection_child_completed", **record)
        publish_bytes(output / "COMPLETE.json", canonical(record) + b"\n")
        print(json.dumps(record))
    except BaseException as error:
        journal.fail(error, "supervised_collection")
        publish_bytes(output / "FAILED.json", canonical(dict(
            error_class=type(error).__name__, message=str(error),
            automatic_retry=False, recovery="inspect retained child; never repeat dispatch")) + b"\n")
        raise
    finally:
        journal.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--recipe-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    execute(args.recipe, args.recipe_sha256, args.output)
