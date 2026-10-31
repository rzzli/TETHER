"""Explicitly use the reviewed installed0.3.1 verifier; never import run code."""
import importlib.abc
from importlib import metadata
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(sys.argv[1]).resolve()
REPORT = Path(sys.argv[2]).resolve()
RUN = ROOT / "runs/r07-native-diagnostic-20261026T165505Z"
ENVIRONMENT = Path(sys.prefix).resolve()
REPORT.parent.mkdir(parents=True, exist_ok=True)
attempts = {"source_reads": [], "archived_execution": [], "repository_imports": [], "dispatch": []}


def normalized(value):
    return os.path.normcase(os.path.abspath(os.fsdecode(value)))


def under(path, root):
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


denied_reads = [normalized(ROOT / "src"), normalized(ROOT / ".venv")]
denied_execution = [normalized(RUN), normalized(ROOT / "data/reference")]


def audit(event, args):
    if event in ("open", "os.listdir", "os.scandir") and args and isinstance(args[0], (str, bytes, os.PathLike)):
        path = normalized(args[0])
        if any(under(path, root) for root in denied_reads):
            attempts["source_reads"].append(path)
            raise PermissionError("Project source/editable environment unavailable")
    if event == "exec" and args:
        filename = args[0].co_filename
        if filename and not filename.startswith("<") and any(under(normalized(filename), root) for root in denied_execution):
            attempts["archived_execution"].append(filename)
            raise PermissionError("Run/reference code execution forbidden")
    if event in ("socket.connect", "subprocess.Popen"):
        attempts["dispatch"].append(event)
        raise PermissionError("No network/child dispatch during verification")


class NoRepositoryModules(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in ("tools", "planning"):
            attempts["repository_imports"].append(fullname)
            raise ImportError("Repository-only module unavailable")


sys.meta_path.insert(0, NoRepositoryModules())
sys.addaudithook(audit)
started = time.monotonic()
report = {"schema_version": 1, "status": "running", "verification_only": True,
          "isolated_mode": bool(sys.flags.isolated), "environment": str(ENVIRONMENT),
          "new_native_calls": 0, "scientific_validation": "not_established"}
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
try:
    from asof.study.native_diagnostic import verify
    from asof.serde import encode
    import asof.study.native_diagnostic as consumer
    assert sys.flags.isolated and Path(consumer.__file__).resolve().is_relative_to(ENVIRONMENT)
    assert metadata.version("asof-target-agents") == "0.3.1"
    result = verify(RUN, "863bf2a9cfb8d4fd01a5223b993d87fbe2ac06992e7206d3d32ef4c712cf2d41",
                    [ROOT, Path("E:/projects_data/drug_target_agents_data")])
    assert result["status"] == "verified_r07_technical_terminal"
    assert not any(attempts.values())
    report.update(status="passed_frozen_installed_verifier_without_live_source", result=encode(result),
                  installed_consumer=str(consumer.__file__))
except BaseException as error:
    report.update(status="failed", error_class=type(error).__name__, message=str(error))
    raise
finally:
    report.update(elapsed_seconds=time.monotonic() - started, guards=attempts,
                  archived_code_imported=False, original_run_rewritten=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
