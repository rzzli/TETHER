"""Read-only historical pins plus one new isolated old-version offline demo."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).parent
BASELINE = "114fecf"
OLD_ENV = ROOT / "data/cache/tether-050-qualified-build/env"
PYTHON = OLD_ENV / "Scripts/python.exe"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "data/cache" / ("ce02-legacy-preservation-" + stamp)
    output.mkdir(exist_ok=False)
    (output / "tmp").mkdir()
    report_path = HERE / ("PRESERVATION-" + stamp + ".json")
    checks = []
    calls = []

    def check(name, passed, **detail):
        checks.append(dict(name=name, passed=bool(passed), **detail))
        if not passed:
            write_new(output / "FAILED.json", dict(checks=checks, calls=calls))
            raise AssertionError(name)

    def pinned(path, expected, origin):
        actual = digest(path)
        check("retained_hash", actual == expected, path=str(path.relative_to(ROOT)),
              expected_sha256=expected, actual_sha256=actual, authority=origin)

    q02 = read("planning/review-assets/tether-q02-20261102/VALIDATION.json")
    q02_wheel = ROOT / q02["wheel"]["wheel_path"]
    pinned(q02_wheel, q02["wheel"]["wheel_sha256"], "Q02 VALIDATION.json wheel")
    inventories = read("research_notes/TETHER efficiency and comparative value/runtime/pins-v1/runtime_inventory.json")
    site = OLD_ENV / "Lib/site-packages"
    for item in inventories["files"]:
        if item["path"].startswith("src/asof/"):
            installed = site / item["path"][4:]
            check("old_engine_source_pin", digest(installed) == item["sha256"],
                  module=item["path"], sha256=digest(installed))

    old_record = read("paper/release/RELEASE-RECORD.json")
    old_archive = ROOT / old_record["archive"]["workspace_path"]
    pinned(old_archive, old_record["archive"]["sha256"], "P09 RELEASE-RECORD.json")
    core_wheel = ROOT / "data/cache/p09-runtime-bundle-20261101T213500Z/wheels/asof_target_agents-0.3.11-py3-none-any.whl"
    with zipfile.ZipFile(old_archive) as archive:
        core_members = [name for name in archive.namelist() if name.endswith("/asof_target_agents-0.3.11-py3-none-any.whl")]
        check("exact_core_wheel_member", len(core_members) == 1)
        packaged_core_hash = hashlib.sha256(archive.read(core_members[0])).hexdigest()
    pinned(core_wheel, packaged_core_hash, "exact wheel inside unchanged P09 archive")
    for wheel, prefix in ((q02_wheel, "tether/"), (core_wheel, "asof/")):
        with zipfile.ZipFile(wheel) as archive:
            members = [name for name in archive.namelist() if name.startswith(prefix) and not name.endswith("/")]
            for name in members:
                expected = hashlib.sha256(archive.read(name)).hexdigest()
                check("installed_wheel_payload", digest(site / name) == expected,
                      module=name, sha256=expected)

    tether040 = read("paper/release/tether/RELEASE-RECORD.json")
    pinned(ROOT / tether040["archive"]["workspace_path"], tether040["archive"]["sha256"], "TETHER0.4.0 RELEASE-RECORD.json")
    pinned(ROOT / "paper/tether-source-reporting-preprint.pdf", tether040["current_pdf_sha256"], "TETHER0.4.0 PDF record")
    tether050 = read("paper/release/tether-v2/RELEASE-RECORD.json")
    pinned(ROOT / tether050["archive_path"], tether050["archive_sha256"], "corrected working packet RELEASE-RECORD.json")
    pinned(ROOT / tether050["pdf_path"], tether050["pdf_sha256"], "corrected working PDF RELEASE-RECORD.json")
    pinned(ROOT / tether050["qualification_path"], tether050["qualification_sha256"], "corrected qualification record")

    preserved = ["tools/data/Start-DownloadBatch.ps1", "tools/data/Watch-DownloadBatch.ps1",
                 "tools/data/Get-DownloadStatus.ps1", "tools/data/Sync-DownloadCatalog.ps1"]
    for name in preserved:
        expected = hashlib.sha256(git("show", BASELINE + ":" + name)).hexdigest()
        pinned(ROOT / name, expected, BASELINE + " tracked downloader/monitor code")
    changes = git("diff", "--name-only", BASELINE, "--", "paper", *preserved).decode().splitlines()
    check("tracked_paper_worker_monitor_unchanged", changes == [], changed_files=changes)
    storage = read("data/manifests/private/storage-config.json")
    check("monitor_configuration_disabled", storage["monitor_enabled"] is False,
          monitor_enabled=storage["monitor_enabled"], monitor_process_id=storage["monitor_process_id"],
          monitor_session_id=storage["monitor_session_id"],
          scope="Current configuration only; no historical state hash or live process survey asserted")

    env = dict(os.environ, TEMP=str(output / "tmp"), TMP=str(output / "tmp"))

    def invoke(name, *args):
        completed = subprocess.run([str(PYTHON), "-I", "-B", *args], cwd=output,
                                   env=env, capture_output=True, timeout=90)
        (output / (name + ".stdout.txt")).write_bytes(completed.stdout)
        (output / (name + ".stderr.txt")).write_bytes(completed.stderr)
        calls.append(dict(name=name, argv=["-I", "-B", *args], returncode=completed.returncode,
                          stdout_sha256=hashlib.sha256(completed.stdout).hexdigest(),
                          stderr_sha256=hashlib.sha256(completed.stderr).hexdigest()))
        check(name + "_exit", completed.returncode == 0)
        return json.loads(completed.stdout)

    identity = invoke("old-identity", "-c", "import tether,asof,sys,json,pathlib; print(json.dumps(dict(tether=tether.__version__,asof=asof.__version__,tether_file=tether.__file__,asof_file=asof.__file__,prefix=sys.prefix)))")
    check("old_environment_identity", identity["tether"] == "0.5.0" and identity["asof"] == "0.3.11" and
          all(Path(identity[key]).is_relative_to(OLD_ENV) for key in ("tether_file", "asof_file")), **identity)
    demo = invoke("old-offline-demo", "-m", "tether", "demo", "--output", str(output / "demo"))
    receipt = digest(output / "demo/tether-receipt.json")
    verified = invoke("old-offline-verify", "-m", "tether", "verify", "--run-dir", str(output / "demo"), "--receipt-sha256", receipt)
    check("old_demo_finalized", (output / "demo/tether-receipt.json").is_file(), receipt_sha256=receipt)
    report = dict(status="PASS", checked_at_utc=datetime.now(timezone.utc).isoformat(), baseline=BASELINE,
                  output=str(output), checks=checks, calls=calls, demo=demo, verified=verified,
                  scope="Historical software payload/hash preservation plus a fresh fictional offline demo; no scientific requalification",
                  limitations=["Tracked monitor/worker bytes and current disabled configuration checked; no historical process-state attestation",
                               "The expected CE01 Test-DownloadBatch verifier correction is outside the preserved downloader-worker list",
                               "Protected human returns and clinical adjudicated outcomes were not accessed"],
                  no_network=True, no_models=True, provider_spending_usd=0)
    write_new(report_path, report)
    print(json.dumps(dict(status=report["status"], checks=len(checks), record=str(report_path), output=str(output)), indent=2))


if __name__ == "__main__":
    main()
