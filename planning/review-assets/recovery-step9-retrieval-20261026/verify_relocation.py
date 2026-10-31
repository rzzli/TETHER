"""Restore the recorded comparison bundle; deny its original folder during replay."""
import hashlib
import importlib.abc
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(sys.argv[1]).resolve()
ORIGINAL = Path(sys.argv[2]).resolve()
RESTORED = Path(sys.argv[3]).absolute()
EXPECTED = sys.argv[4]
REPORT = Path(sys.argv[5]).resolve()
ENVIRONMENT = Path(sys.prefix).resolve()
assert sys.flags.isolated
from asof.serde import encode
from asof.study.retrieval_smoke import verify

verify(ORIGINAL, EXPECTED)
RESTORED.mkdir(parents=True, exist_ok=False)
for source in ORIGINAL.rglob('*'):
    assert not source.is_symlink()
    destination = RESTORED / source.relative_to(ORIGINAL)
    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        continue
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
assert hashlib.sha256((RESTORED / "receipt.json").read_bytes()).hexdigest() == EXPECTED

attempts = {"forbidden_reads": [], "imports": [], "dispatch": []}


def normalized(path):
    return os.path.normcase(os.path.abspath(os.fsdecode(path)))


def under(path, root):
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


denied = [normalized(ORIGINAL), normalized(ROOT / "src"), normalized(ROOT / ".venv")]


def audit(event, args):
    if event in ("open", "os.listdir", "os.scandir") and args and isinstance(args[0], (str, bytes, os.PathLike)):
        path = normalized(args[0])
        if any(under(path, value) for value in denied):
            attempts["forbidden_reads"].append(path)
            raise PermissionError("Original bundle or project source unavailable")
    if event in ("socket.connect", "subprocess.Popen"):
        attempts["dispatch"].append(event)
        raise PermissionError("Verification cannot dispatch")


class NoRepositoryModules(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in ("tools", "planning"):
            attempts["imports"].append(fullname)
            raise ImportError("Repository runtime module unavailable")


sys.meta_path.insert(0, NoRepositoryModules())
sys.addaudithook(audit)
started = time.monotonic()
result = verify(RESTORED, EXPECTED)
assert not any(attempts.values())
report = {"schema_version": 1, "status": "passed_recorded_retrieval_relocation",
          "result": encode(result), "original_bundle_reads_denied": str(ORIGINAL),
          "restored": str(RESTORED), "trusted_installed_environment": str(ENVIRONMENT),
          "guards": attempts, "elapsed_seconds": time.monotonic() - started,
          "native_calls": 0, "real_source_admission": False,
          "native_R07_relocation_claimed": False, "archived_code_executed": False}
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
