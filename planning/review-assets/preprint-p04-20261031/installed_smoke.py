"""Isolated installed-package qualification with FICTIONAL data and MOCK transport.

This script never launches a model/server, opens HTTP, reads scientific source
files or constructs evaluator references. Wheel/code reads verify installation;
all created journals and byte artifacts contain explicitly fictional controls.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def retain_json(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                      allow_nan=False) + "\n").encode("utf-8")
    with Path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--expected-pins", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    report = dict(schema_version=1, status="failed", qualification="FICTIONAL_MOCK_ONLY",
                  created_at_utc=datetime.now(timezone.utc).isoformat(),
                  actual_model_calls=0, actual_http_calls=0, server_launches=0,
                  scientific_source_reads=0, evaluator_reference_inputs=0,
                  scientific_validation="not_performed", mock_dispatches=0)
    try:
        import asof
        from asof.journal import RunJournal, read_chain
        from asof.serde import canonical, parse_json
        from asof.study.source_fact_cell import run_reporting_cell
        from asof.study.source_fact_inputs import make_packet
        from asof.study.source_fact_reporting import literal_report, reporting_view, render_reporting_prompt
        from asof.study.source_fact_transport import TypedReportingClient

        prefix = Path(sys.prefix).resolve()
        package = Path(asof.__file__).resolve().parent
        assert package.is_relative_to(prefix), "Package escaped fresh installed prefix"
        assert sys.flags.isolated == 1 and sys.flags.dont_write_bytecode == 1
        assert importlib.util.find_spec("pyarrow") is None, "Optional Arrow must be absent"
        expected = json.loads(args.expected_pins.read_text(encoding="utf-8"))
        pins = {}
        for relative, wanted in expected["source_code_pins"].items():
            parts = Path(relative).parts
            assert parts[0] == "asof" and ".." not in parts
            installed = package.joinpath(*parts[1:]).resolve()
            assert installed.is_relative_to(package)
            actual = digest(installed)
            assert actual == wanted, "Installed code differs: " + relative
            pins[relative] = actual

        nodes = {key: dict(source_id=key, sha256=str(i) * 64,
                          release_id="FICTIONAL_RELEASE", role="agent_evidence")
                 for i, key in enumerate(("FICTIONAL_EVIDENCE", "FICTIONAL_HGNC", "FICTIONAL_TARGETS"), 1)}
        mappings = [dict(source_id=key, locator=dict(format="json", pointer=""), row={})
                    for key in ("FICTIONAL_HGNC", "FICTIONAL_TARGETS")]
        source = make_packet(
            dict(case_id="FICTIONAL_CASE", target_symbol="FICTIONAL_SYMBOL",
                 indication_id="FICTIONAL_INDICATION", action=None, modality=None, tissue=None),
            dict(id="FICTIONAL_CLEAN", kind="real_selected_sources", records_available=1,
                 collection_status="selected_records", biological_absence=False),
            dict(target_id="FICTIONAL_TARGET", mappings=mappings),
            [dict(source_id="FICTIONAL_EVIDENCE", locator=dict(format="parquet", row_group=0, row=0),
                  row=dict(id="FICTIONAL_RECORD", targetId="FICTIONAL_TARGET",
                           diseaseId="FICTIONAL_INDICATION", datasourceId="europepmc",
                           datatypeId="literature", publicationDate="2000-01-01", cellType=None))],
            nodes, [], cutoff="2001-01-01T00:00:00+00:00", plan_sha256="4" * 64)
        calls, factory_stages = [], []
        journal = None

        class Response:
            status = 200
            def __init__(self, raw):
                self.raw = raw
            def __enter__(self):
                return self
            def __exit__(self, *arguments):
                return False
            def geturl(self):
                return "http://127.0.0.1:55591/completion"
            def read(self, maximum):
                return self.raw[:maximum]

        class Opener:
            def __init__(self, stage, fixture_content):
                self.stage, self.fixture_content = stage, fixture_content
            def open(self, request, timeout):
                assert journal.events[-1]["event"] == "dispatch", "Dispatch journal must precede MOCK open"
                payload = parse_json(request.data)
                assert "grammar" not in payload and "json_schema" not in payload
                assert payload["seed"] == 0 and payload["cache_prompt"] is False
                calls.append(self.stage)
                return Response(canonical(dict(
                    prompt=payload["prompt"], model="FICTIONAL_MOCK_MODEL",
                    generation_settings={key: payload[key] for key in (
                        "seed", "temperature", "n_predict", "stop", "stream")},
                    content=self.fixture_content.decode("utf-8"), truncated=False,
                    tokens_evaluated=11, tokens_predicted=7)))

        with patch("socket.socket", side_effect=AssertionError("Real sockets forbidden")), \
             patch("urllib.request.urlopen", side_effect=AssertionError("Real HTTP forbidden")), \
             patch("urllib.request.build_opener", side_effect=AssertionError("Use injected MOCK opener")), \
             patch("subprocess.Popen", side_effect=AssertionError("No model/server/netstat process")):
            view = reporting_view(source)
            assert not source["lineage"]["reference_inputs"]
            assert not view["task"]["joins"]
            content = literal_report(source)
            assert parse_json(content)["facts"][0]["value"] == "FICTIONAL_RECORD"
            prompt = render_reporting_prompt(source, max_prompt_bytes=14304)
            assert "FICTIONAL_RECORD" in prompt and "expected_answers" not in prompt

            def factory(stage, retain):
                factory_stages.append(stage)
                return TypedReportingClient("http://127.0.0.1:55591", expected_pid=1234,
                    ownership_check=lambda pid, host, port: (
                        pid == 1234 and host == "127.0.0.1" and port == 55591),
                    opener=Opener(stage, content), retain=retain)

            journal = RunJournal(args.output / "FICTIONAL_MOCK_RUN")
            try:
                plain = run_reporting_cell(source, "plain_same_model_typed_report",
                    cell_id="FICTIONAL_PLAIN", output=journal.output / "FICTIONAL_PLAIN",
                    journal=journal, client_factory=factory)
                two_stage = run_reporting_cell(source, "asof_declared_two_stage_typed_report",
                    cell_id="FICTIONAL_TWO_STAGE", output=journal.output / "FICTIONAL_TWO_STAGE",
                    journal=journal, client_factory=factory)
                assert plain["terminal"] == two_stage["terminal"] == "returned"
                assert plain["raw_final"] == two_stage["raw_final"] == content
                assert plain["dispatches"] == 1 and two_stage["dispatches"] == 2
                assert plain["measured_usage"]["input_tokens"] == 11
                assert two_stage["measured_usage"]["input_tokens"] == 22
                assert plain["measured_usage"]["output_tokens"] == 7
                assert two_stage["measured_usage"]["output_tokens"] == 14
                assert plain["estimated_usage"]["input_tokens"] == two_stage["estimated_usage"]["input_tokens"] == 0
            finally:
                journal.close()
            chain = read_chain(journal.path)
            assert [stage for stage in calls] == ["plain", "proposal", "audit"]
            assert factory_stages == calls
            accounted = [row["details"] for row in chain if row["event"] == "attempt_accounted"]
            assert len(accounted) == 3 and all(row["basis"] == "adapter_reported" for row in accounted)
            assert sum(row["usage"]["input_tokens"] for row in accounted) == 33
            assert sum(row["usage"]["output_tokens"] for row in accounted) == 21
            assert all(row["dispatched"] is True and row["retention_complete"] is True for row in accounted)
            assert len([row for row in chain if row["event"] == "cell_terminal"]) == 2

        report.update(status="passed_installed_dependency_free_fictional_mock_only",
            wheel=dict(name=args.wheel.name, bytes=args.wheel.stat().st_size, sha256=digest(args.wheel)),
            environment=dict(python=sys.executable, prefix=sys.prefix, package_path=str(package),
                python_version=sys.version, cwd=str(Path.cwd()), isolated=True, dont_write_bytecode=True,
                arrow_present=False, package_version=asof.__version__),
            source_code_pins=pins, installed_code_matches_source=True,
            expected_pin_manifest_sha256=digest(args.expected_pins),
            mock_dispatches=len(calls), mock_stages=calls,
            mock_measured_usage=dict(input_tokens=33, output_tokens=21, cost_usd=0.0),
            mock_estimated_usage=dict(input_tokens=0, output_tokens=0, cost_usd=0.0),
            per_cell_caps=dict(max_calls=16, max_input_tokens=32000, max_output_tokens=8000,
                               max_cost_usd=0, max_seconds=300, retries=0),
            journal=dict(events=len(chain), sha256=digest(journal.path)),
            checks=dict(fictional_packet_only=True, reference_values_never_supplied=True,
                        exact_literal_output=True, lossless_prompt_render=True,
                        actual_client_with_mock_opener=True, guarded_real_sockets_http_processes=True,
                        fsynced_exact_transport_retention=True, measured_not_double_charged=True,
                        plain_and_two_stage_completed=True),
            limits=["Finite fictional controls only", "No real local model/server/HTTP/native qualification",
                    "No source admission or scientific validation", "No full controller or actual source preparation replay"])
    except BaseException as error:
        report.update(error_class=type(error).__name__,
            error=str(error).encode("utf-8", "backslashreplace").decode("utf-8")[:240])
        retain_json(args.output / "smoke-result.json", report)
        raise
    retain_json(args.output / "smoke-result.json", report)
    print(json.dumps({key: report[key] for key in ("status", "mock_dispatches", "actual_model_calls")}, sort_keys=True))


if __name__ == "__main__":
    main()
