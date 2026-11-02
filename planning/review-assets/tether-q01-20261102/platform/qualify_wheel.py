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
    parser.add_argument("--work", default="data/cache/tether-042-qualified-build")
    parser.add_argument("--report", default="WHEEL-QUALIFICATION.json")
    args = parser.parse_args()
    work = ROOT / args.work
    wheel = work / "wheels/tether_target_agents-0.4.2-py3-none-any.whl"
    interpreter = work / "env/Scripts/python.exe"
    source_checks = 0
    with zipfile.ZipFile(wheel) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert len(names) == len(set(names)) == 22
        assert not any(name.startswith("asof/") for name in names)
        for name in names:
            if name.startswith("tether/") and name.endswith(".py"):
                assert archive.read(name) == (ROOT / "packages/tether/src" / name).read_bytes()
                source_checks += 1
        rows = list(csv.reader(io.StringIO(archive.read("tether_target_agents-0.4.2.dist-info/RECORD").decode())))
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
        "assert tether.__version__=='0.4.2'; assert asof.__version__=='0.3.11'; "
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
    failures = []
    for name, option, value, expected_reason in (
        ("timeout", "--process-timeout-seconds", "0.000001", "deadline_exceeded"),
        ("overflow", "--process-output-bytes", "1", "output_limit_exceeded")):
        run(["-m", "tether", "demo", "--output", name, option, value], 2)
        target = work / name
        assert not (target / "tether-receipt.json").exists()
        failure = json.loads((target / "tether-failure.json").read_text())
        supervision = failure["supervision"]
        assert supervision["termination_reason"] == expected_reason
        assert supervision["process_reaped"] is True
        retained = sum((target / ("engine-"+stream+".txt")).stat().st_size for stream in ("stdout","stderr"))
        assert retained <= supervision["limits"]["max_output_bytes"]
        journal_bytes = (target / "attempt/journal.jsonl").read_bytes()
        events = [json.loads(line) for line in journal_bytes.splitlines()]
        assert sum(event["event"] == "engine_dispatch" for event in events) == 1
        inspected = json.loads(run(["-m", "tether", "inspect-run", "--run-dir", name]))
        assert inspected["failure"]["supervision"] == supervision
        assert (target / "attempt/journal.jsonl").read_bytes() == journal_bytes
        failures.append(dict(name=name, termination_reason=expected_reason, retained_stream_bytes=retained,
                             process_reaped=True, dispatches=1, inspection_without_redispatch=True))
    report = dict(schema_version=1, status="PASS_ISOLATED_TETHER_042_WHEEL", role="evaluation_only",
                  agent_visible=False, wheel_path=wheel.relative_to(ROOT).as_posix(),
                  wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(), wheel_bytes=wheel.stat().st_size,
                  wheel_members=22, runtime_source_files_checked=source_checks, record_closure="verified",
                  environment=json.loads(source), calls=calls, outer_verification=verified,
                  failure_qualification=failures, execution_platform="Windows", posix_branch_executed=False,
                  wrong_anchor_rejected_without_redispatch=True, canonical_locked_sync="passed_offline",
                  limits=["Fresh workspace-cache environment; both imports resolve inside its site-packages.",
                          "Windows-only execution; POSIX select branch has not been executed here.",
                          "No new scientific source reconstruction, paper package or hosted CI qualification.",
                          "Core legacy wheel and published earlier artifacts remain unchanged."],
                  new_model_calls=0, new_provider_downloads=0, provider_spending_usd=0)
    (HERE / args.report).write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("status", "wheel_sha256", "wheel_bytes", "wheel_members")}))


if __name__ == "__main__":
    main()
