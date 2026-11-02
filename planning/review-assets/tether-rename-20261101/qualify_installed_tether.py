"""Qualify local two-wheel installation outside checkout/original data roots.

Only the packaged synthetic demo executes. No provider/model/source acquisition.
"""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    location = json.loads((HERE / "ISOLATED-INSTALL-LOCATION.json").read_text(encoding="utf-8-sig"))
    work, python = Path(location["root"]), location["python"]
    calls = []
    def run(args, *, parse=False):
        answer = subprocess.run([python, "-B", "-I", *args], cwd=work, capture_output=True, timeout=120)
        calls.append({"argv": args, "returncode": answer.returncode,
            "stdout_sha256": sha(answer.stdout), "stderr_sha256": sha(answer.stderr)})
        if answer.returncode:
            raise AssertionError(answer.stderr.decode(errors="replace"))
        return json.loads(answer.stdout) if parse else answer.stdout.decode()
    probe = r'''
import importlib.metadata as metadata, importlib.util, json, pathlib, sys
import asof, tether
from asof import contracts as original
from tether import contracts as renamed
import asof.study.source_fact_sources as old_sources
import tether.study.source_fact_sources as new_sources
assert original is renamed and original.Case is renamed.Case
assert old_sources is new_sources and old_sources._TOKEN is new_sources._TOKEN
assert renamed.__spec__.name == 'asof.contracts'
assert metadata.version('asof-target-agents') == '0.3.11'
assert metadata.version('tether-target-agents') == '0.4.0'
assert importlib.util.find_spec('pyarrow') is None
base=pathlib.Path(sys.executable).resolve().parent.parent
assert pathlib.Path(asof.__file__).resolve().is_relative_to(base)
assert pathlib.Path(tether.__file__).resolve().is_relative_to(base)
assert not any(pathlib.Path(p).drive.upper() in ('D:', 'E:') for p in sys.path if p)
print(json.dumps(dict(core_version=asof.__version__,tether_version=tether.__version__,
 core_file=asof.__file__,tether_file=tether.__file__,source_checkout_imports=False,
 pyarrow_present=False,shared_contract_and_reference_authority=True)))
'''
    imports = run(["-c", probe], parse=True)
    version = run(["-m", "tether", "--version"]).strip()
    assert version == "TETHER 0.4.0 (compatibility engine 0.3.11)"
    assert "TETHER" in run(["-m", "tether", "--help"])
    run(["-m", "tether.study", "--help"])
    run(["-m", "tether.archive", "--help"])
    demo = work / "synthetic-demo"
    assert not demo.exists()
    executed = run(["-m", "tether", "demo", "--output", str(demo)], parse=True)
    assert executed["status"] == "completed"
    verified = run(["-m", "tether", "verify", "--run-dir", str(demo),
                    "--receipt-sha256", executed["receipt_sha256"]], parse=True)
    assert verified["status"] == "integrity_verified" and verified["external_anchor_checked"] is True
    assert verified["launcher_code_verified"] is True
    assert verified["engine"]["semantic_consistency"] == "verified"
    assert verified["engine"]["source_binding"] == "current_originals"
    inspected = run(["-m", "tether", "inspect-run", "--run-dir", str(demo)], parse=True)
    assert inspected["brand"] == "TETHER" and inspected["last_event"] == "tether_completed"
    legacy = run(["-m", "asof", "verify", "--run-dir", str(demo / "engine"),
                  "--receipt-sha256", executed["engine_receipt_sha256"]], parse=True)
    assert legacy["semantic_consistency"] == "verified" and legacy["code_matches_current"] is True
    outer, inner = (demo / "dossier.md").read_bytes(), (demo / "engine/dossier.md").read_bytes()
    assert outer.startswith(b"# TETHER dossier:") and inner.startswith(b"# AsOf dossier:")
    assert outer == b"# TETHER dossier:" + inner[len(b"# AsOf dossier:"):]
    manifest = json.loads((demo / "tether-manifest.json").read_bytes())
    assert manifest["launcher"]["installed_distributions"] == {"tether-target-agents": "0.4.0", "asof-target-agents": "0.3.11"}
    result = {"schema_version": 1, "method": "tether.isolated_wheel_qualification.v1",
        "status": "PASS_ISOLATED_INSTALLED_TETHER", "role": "evaluation_only", "agent_visible": False,
        "environment": imports, "version_display": version, "fixture": "packaged_synthetic_demo_only",
        "calls": calls, "outer_receipt_sha256": executed["receipt_sha256"],
        "engine_receipt_sha256": executed["engine_receipt_sha256"],
        "outer_verification": verified, "legacy_engine_verification": legacy,
        "source_checkout_imports": False, "optional_arrow_present": False,
        "new_model_calls": 0, "new_provider_downloads": 0, "provider_spending_usd": 0,
        "scientific_validation": "not_established", "publication_authorized": False,
        "scope": "Windows x64 CPython3.11.15; native-source/Linux/hosted qualification not extended"}
    with (HERE / "ISOLATED-INSTALLED-QUALIFICATION.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "subprocesses": len(calls),
        "source_checkout_imports": False, "optional_arrow_present": False,
        "outer_receipt_sha256": executed["receipt_sha256"]}))


if __name__ == "__main__":
    main()
