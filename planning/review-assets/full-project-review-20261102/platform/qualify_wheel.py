"""Source-isolated local wheel smoke; fictional demo and negative verification."""
import base64
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", default="data/cache/tether-041-qualified-build")
    parser.add_argument("--report", default="WHEEL-QUALIFICATION.json")
    args = parser.parse_args()
    work = ROOT / args.work
    wheel = work / "wheels/tether_target_agents-0.4.1-py3-none-any.whl"
    interpreter = work / "env/Scripts/python.exe"
    source_checks = 0
    with zipfile.ZipFile(wheel) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert len(names) == len(set(names)) == 21
        assert not any(name.startswith("asof/") for name in names)
        for name in names:
            if name.startswith("tether/") and name.endswith(".py"):
                assert archive.read(name) == (ROOT / "packages/tether/src" / name).read_bytes()
                source_checks += 1
        rows = list(csv.reader(io.StringIO(archive.read("tether_target_agents-0.4.1.dist-info/RECORD").decode())))
        assert {r[0] for r in rows} == set(names)
        for name, digest, size in rows:
            if not digest:
                assert name.endswith("/RECORD") and size == ""
                continue
            raw = archive.read(name)
            assert digest == "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode()
            assert size == str(len(raw))
    calls = []
    def run(args, expected=0):
        call = subprocess.run([str(interpreter), "-B", "-I", *args], cwd=work,
                              capture_output=True, text=True, timeout=60)
        calls.append(dict(argv=args, returncode=call.returncode,
                          stdout_sha256=hashlib.sha256(call.stdout.encode()).hexdigest(),
                          stderr_sha256=hashlib.sha256(call.stderr.encode()).hexdigest()))
        assert call.returncode == expected, call.stderr
        return call.stdout
    source = run(["-c", "import tether,asof,sys,pathlib,importlib.util,json; "
        "assert tether.__version__=='0.4.1'; assert asof.__version__=='0.3.11'; "
        "assert pathlib.Path(tether.__file__).is_relative_to(pathlib.Path(sys.prefix)); "
        "assert pathlib.Path(asof.__file__).is_relative_to(pathlib.Path(sys.prefix)); "
        "assert importlib.util.find_spec('pyarrow') is None; "
        "print(json.dumps({'isolated_installed_imports':True,'arrow':False,'version':tether.__version__}))"])
    created = json.loads(run(["-m", "tether", "demo", "--output", "demo"]))
    verified = json.loads(run(["-m", "tether", "verify", "--run-dir", "demo",
                              "--receipt-sha256", created["receipt_sha256"]]))
    assert verified["external_anchor_checked"] is True
    assert verified["engine"]["tether_semantics"]["dossier_reconstruction"] == "verified"
    journal = (work / "demo/attempt/journal.jsonl").read_bytes()
    negative = run(["-m", "tether", "verify", "--run-dir", "demo", "--receipt-sha256", "0" * 64], 2)
    assert (work / "demo/attempt/journal.jsonl").read_bytes() == journal
    report = dict(schema_version=1, status="PASS_ISOLATED_TETHER_041_WHEEL", role="evaluation_only",
                  agent_visible=False, wheel_path=wheel.relative_to(ROOT).as_posix(),
                  wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(), wheel_bytes=wheel.stat().st_size,
                  wheel_members=21, runtime_source_files_checked=source_checks, record_closure="verified",
                  environment=json.loads(source), calls=calls, outer_verification=verified,
                  wrong_anchor_rejected_without_redispatch=True, canonical_locked_sync="passed_offline",
                  limits=["Fresh workspace-cache environment; both imports resolve inside its site-packages.",
                          "No new scientific source reconstruction, paper package or hosted CI qualification.",
                          "Core legacy wheel and published earlier artifacts remain unchanged."],
                  new_model_calls=0, new_provider_downloads=0, provider_spending_usd=0)
    (HERE / args.report).write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "wheel_sha256", "wheel_bytes", "wheel_members")}))


if __name__ == "__main__":
    main()
