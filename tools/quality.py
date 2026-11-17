"""Pinned source quality checks; explicit staged typing, no scientific qualification."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.portable_validate import reserve_output

VERSIONS = {"ruff": "0.15.22", "mypy": "2.4.1", "coverage": "7.17.3"}
TYPED = tuple(
    "src/tether_engine/" + name + ".py" for name in ("money", "temporal", "verification_policy")
) + ("packages/tether/src/tether/api.py",)
FORMATTED = (*TYPED, "tools/quality.py", "tools/coverage_gate.py", "tests/test_quality.py")


def runtime_sources(root=ROOT):
    """Match the slim wheel's source layout, including mapped compatibility shims."""
    result = {}
    for directory, namespace in (
        ("src/tether_engine", "tether_engine"),
        ("packages/tether/src/tether", "tether"),
    ):
        for path in (root / directory).rglob("*.py"):
            relative = path.relative_to(root / directory)
            if relative.parts[0] != "study":
                result[namespace + "/" + relative.as_posix()] = path
    for path in (root / "src/_tether_study_compat").glob("*.py"):
        result["tether_engine/study/" + path.name] = path
    if not result or any(not path.is_file() for path in result.values()):
        raise ValueError("Missing maintained runtime sources")
    return result


def check_lock_versions(root=ROOT):
    """Catch version bumps that leave either documented locked install stale."""
    projects = {}
    for folder in (".", "packages/tether"):
        project = tomllib.loads((root / folder / "pyproject.toml").read_text("utf-8"))["project"]
        projects[project["name"]] = project
    for folder, required in ((".", {"tether-target-engine"}), ("packages/tether", set(projects))):
        locked = tomllib.loads((root / folder / "uv.lock").read_text("utf-8"))["package"]
        for name in required:
            rows = [row for row in locked if row["name"] == name]
            if len(rows) != 1 or rows[0]["version"] != projects[name]["version"]:
                raise ValueError("Stale or duplicate lock entry: " + name)
    pin = "tether-target-engine==" + projects["tether-target-engine"]["version"]
    if pin not in projects["tether-target-agents"]["dependencies"]:
        raise ValueError("Wrapper must pin the matching engine")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Fresh report directory")
    args = parser.parse_args(argv)
    output = reserve_output(args.output)
    report = {
        "status": "failed",
        "stages": [],
        "typing_scope": TYPED,
        "formatting_scope": FORMATTED,
        "scientific_validation": "not_established",
    }
    try:
        versions = {name: importlib.metadata.version(name) for name in VERSIONS}
        report["versions"] = versions
        if versions != VERSIONS:
            raise ValueError("Install tools/quality-requirements.txt in an isolated environment")
        check_lock_versions()
        sources = runtime_sources()
        report["source_sha256"] = {
            name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in sources.items()
        }
        commands = (
            (
                "lint",
                [
                    "ruff",
                    "check",
                    "--no-cache",
                    "--config",
                    "tools/ruff.toml",
                    *(str(path) for path in sources.values()),
                    *FORMATTED,
                ],
            ),
            ("format", ["ruff", "format", "--check", "--config", "tools/ruff.toml", *FORMATTED]),
            (
                "types",
                [
                    "mypy",
                    "--config-file",
                    "tools/mypy.ini",
                    "--cache-dir",
                    str(output / "mypy-cache"),
                ],
            ),
        )
        for name, command in commands:
            with (output / (name + ".log")).open("xb") as log:
                result = subprocess.run(
                    [sys.executable, "-I", "-B", "-m", *command],
                    cwd=ROOT,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=180,
                    check=False,
                )
            report["stages"].append({"name": name, "returncode": result.returncode})
            if result.returncode:
                raise ValueError(name + " failed; inspect the retained log")
        report["status"] = "passed"
    except (Exception, KeyboardInterrupt) as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    with (output / "report.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({"status": report["status"], "report": str(output / "report.json")}))
    return int(report["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
