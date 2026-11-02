"""Independent CLI/process declaration probes over a genuine fictional demo."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "packages/tether/src"))
from tether import _cli as cli, _presentation as layer, _process as process
from asof.serde import ContractError, canonical, fingerprint


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run = HERE / ("boundary-" + stamp)
    run.mkdir()
    checks = []
    details = []
    def check(name, value):
        checks.append(dict(name=name, passed=bool(value)))
        if not value:
            raise AssertionError(name)
    def read(path):
        return json.loads(path.read_text())
    def save(path, value):
        path.write_bytes(canonical(value) + b"\n")
    try:
        for flag in ("--process-timeout-s=10", "--process-output-b=100"):
            target = run / ("abbreviation-" + str(len(checks)))
            with patch.object(layer, "create_outer", side_effect=AssertionError("must not reserve")) as create, \
                    patch.object(layer, "invoke_engine", side_effect=AssertionError("must not launch")) as invoke, \
                    redirect_stderr(io.StringIO()):
                try:
                    cli.main(["demo", "--output", str(target), flag])
                except SystemExit as error:
                    check(flag + ": parser rejects", error.code == 2)
                else:
                    raise AssertionError("abbreviation accepted")
                check(flag + ": zero reservation/dispatch", create.call_count == invoke.call_count == 0 and not target.exists())

        target = run / "demo"
        stream = io.StringIO()
        raw_argv = ["demo", "--output", str(target), "--process-timeout-seconds=30", "--process-output-bytes", "32768"]
        with redirect_stdout(stream):
            status = cli.main(raw_argv)
        check("genuine demo succeeds", status == 0)
        summary = json.loads(stream.getvalue())
        manifest = read(target / layer.MANIFEST)
        check("raw accepted invocation retained", manifest["invocation_sha256"] == hashlib.sha256(canonical(raw_argv)).hexdigest())
        check("effective process policy retained", manifest["process_limits"] == dict(timeout_seconds=30.0, max_output_bytes=32768))
        check("genuine process supervised", manifest["supervision"]["process_reaped"] is True and manifest["supervision"]["termination_reason"] == "exited")
        verified = layer.verify_outer(target, summary["receipt_sha256"])
        check("genuine source-inclusive verification", verified["engine"]["source_binding"] == "current_originals")
        check("stronger semantics still checked", verified["engine"]["tether_semantics"]["dossier_reconstruction"] == "verified")
        details.append(dict(genuine_summary=summary, verification=verified))

        for command in ("verify", "inspect-run"):
            with patch.object(layer, "invoke_engine", side_effect=AssertionError("no dispatch")) as invoke, \
                    redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                try:
                    status = cli.main([command, "--run-dir", str(target), "--process-timeout-seconds=1"])
                except SystemExit as error:
                    status = error.code
                check(command + ": explicit in-process limits rejected", status == 2)
                check(command + ": no dispatch", invoke.call_count == 0)

        changes = {
            "past_deadline": lambda doc: doc["supervision"].update(execution_elapsed_seconds=31, total_elapsed_seconds=32),
            "bytes_mismatch": lambda doc: doc["supervision"].update(retained_stdout_bytes=123456),
            "typed_eof": lambda doc: doc["supervision"]["pipe_eof"].update(stdout=1),
            "unreaped": lambda doc: doc["supervision"].update(process_reaped=False),
            "wrong_policy": lambda doc: doc["supervision"]["limits"].update(max_output_bytes=32769),
        }
        for name, alter in changes.items():
            changed = run / name
            shutil.copytree(target, changed)
            doc = read(changed / layer.MANIFEST)
            alter(doc)
            save(changed / layer.MANIFEST, doc)
            mh = hashlib.sha256((changed / layer.MANIFEST).read_bytes()).hexdigest()
            events = [json.loads(line) for line in (changed / layer.JOURNAL).read_text().splitlines()]
            events[3]["details"]["supervision"] = deepcopy(doc["supervision"])
            events[-1]["details"]["manifest_sha256"] = mh
            previous = None
            for event in events:
                event.pop("sha256", None)
                event["previous_sha256"] = previous
                event["sha256"] = previous = fingerprint(event)
            (changed / layer.JOURNAL).write_bytes(b"".join(canonical(event) + b"\n" for event in events))
            receipt = read(changed / layer.RECEIPT)
            receipt.update(manifest_sha256=mh, journal_sha256=hashlib.sha256((changed / layer.JOURNAL).read_bytes()).hexdigest())
            save(changed / layer.RECEIPT, receipt)
            anchor = hashlib.sha256((changed / layer.RECEIPT).read_bytes()).hexdigest()
            try:
                layer.verify_outer(changed, anchor)
            except ContractError as error:
                details.append(dict(mutation=name, error_class=type(error).__name__, error=str(error)))
            else:
                raise AssertionError(name + " resealed inconsistency accepted")
            check(name + ": resealed process inconsistency rejected", True)
        status = "passed"
    except BaseException as error:
        status = "failed"
        details.append(dict(error_class=type(error).__name__, error=str(error)))
        raise
    finally:
        files = ["packages/tether/src/tether/_process.py", "packages/tether/src/tether/_presentation.py", "packages/tether/src/tether/_cli.py"]
        report = dict(schema_version=1, status=locals().get("status", "failed"), recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                      checks=checks, details=details, code_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files})
        (run / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(dict(status=report["status"], checks=len(checks), report=str(run / "report.json"))))


if __name__ == "__main__":
    main()
