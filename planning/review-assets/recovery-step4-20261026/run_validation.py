"""Validate frozen R04 sources offline, retaining code identity and protected hashes."""
import hashlib
import json
import os
import runpy
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "data/cache/recovery-step4-validation-20261026"
CACHE.mkdir(exist_ok=True)
tempfile.tempdir = str(CACHE)
os.environ["TMP"] = os.environ["TEMP"] = str(CACHE)
os.environ["UV_OFFLINE"] = "1"
os.environ["PATH"] = str(ROOT / "data/cache/powershell-7.4.6-portable") + os.pathsep + os.environ["PATH"]
sys.path.insert(0, str(ROOT))


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pins():
    paths = [p for folder in ("src", "tools", "tests") for p in (ROOT / folder).rglob("*.py")
             if "__pycache__" not in p.parts]
    paths += [ROOT / "pyproject.toml", ROOT / "uv.lock", ROOT / "data/.gitignore",
              ROOT / "src/asof/archive/semantic_dependencies.json"]
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(paths)}


protected = {
    "data/benchmark/cohorts/science4-outcomes-20261019T024500Z/adjudication/normalized-outcomes.json":
        "9392df7cec11704f3f0abaddc12e4196349ace1aba55b4da0af0f14d41bb26f2",
    "data/benchmark/labels/endpoint-followup-feasibility-20261021/adjudication-v1/normalized-outcomes.json":
        "c3195a27565debe2c0b891f8aecffbae8a63988dfe2fd62b9e5aed37f0353398",
}
before = pins()
protected_before = {name: digest(ROOT / name) for name in protected}
assert protected_before == protected
sys.argv = ["tools/validate.py", "--mode", "full", "--package", "--report",
            str(CACHE / "full-validation.json")]
exit_code = 0
try:
    runpy.run_path(str(ROOT / "tools/validate.py"), run_name="__main__")
except SystemExit as error:
    exit_code = error.code
except BaseException as error:
    exit_code = 1
    (CACHE / "failure.json").write_text(json.dumps({"status": "failed", "error_class": type(error).__name__,
        "message": str(error)}, indent=2) + "\n", encoding="utf-8")
    raise
finally:
    after = pins()
    protected_after = {name: digest(ROOT / name) for name in protected}
    result = dict(exit_code=exit_code, unchanged_code=before == after, source_pins=after,
                  protected_hashes=protected_after, protected_unchanged=protected_after == protected,
                  status="passed" if exit_code == 0 and before == after and protected_after == protected else "failed")
    (CACHE / "code-validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
raise SystemExit(exit_code if result["status"] == "passed" else 1)
