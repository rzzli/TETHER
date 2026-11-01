"""P04b fictional literal-extraction qualification: DRAFT denies execution.

READY requires an independently supplied exact protocol hash and --execute.
Importing, validating and dry qualifying this module never dispatch.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
import hashlib
import importlib.util
import math
from pathlib import Path
import time
import subprocess
import urllib.request

from asof.journal import RunJournal
from asof.serde import ContractError, canonical, encode, fingerprint, parse_json
from asof.study.process import OwnedServer
from asof.study.source_fact_adapters import adapt_output
from asof.study.source_fact_reporting import _GUIDE
from asof.study.source_fact_transport import TypedReportingClient, prepare_completion
from asof.study.stable_read import checked_path, stable_files

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
LEGACY = ROOT / "planning/review-assets/preprint-p04-20261031/EXECUTION-PROTOCOL-READY-v1.json"
CONTROLLER = ROOT / "tools/science/run_source_fact_pilot.py"
MODEL_PIN = "dfba9f924a01d7ff8b7ab7845b481af482e29d0dbed9eb280bc3bb142598342e"
SERVER_PIN = "2143076f29b6af862d138ea1a605919ab0eefb91c39f9b8d4f282ce76662b8e3"
CONTROLLER_PIN = "8d144f96a1b0ce4c1b6e9b19ee1eb82e312b78d3c5f0a771e0feecc655e5b6c0"
JOURNAL_MAX_EVENTS, JOURNAL_MAX_BYTES = 8256, 8 * 1024 * 1024
ZERO = dict(input_tokens=0, output_tokens=0, cost_usd=0.0)
BUDGET = dict(max_calls=1, max_input_tokens=32000, max_output_tokens=8000,
              max_seconds=300, max_cost_usd=0)
SCHEDULE = [dict(cell_id="fictional-two-plain", control_id="fictional-two", stage="plain"),
            dict(cell_id="fictional-eight-plain", control_id="fictional-eight", stage="plain")]
REFINEMENT = (
    " The source member is an OBJECT, never a source_id string. Copy exactly "
    "fact_skeleton[i].source with its five keys: source_id:string, sha256:64 "
    "lowercase hexadecimal characters, release_id:string, locator:object, "
    "field:string. locator has exactly format:string='json',pointer:string "
    "(RFC6901), or format:string='parquet',row_group:nonnegative integer,"
    "row:nonnegative integer. No source lookup or binding reconstruction. "
    "Status invariant: answered => facts nonempty and reason=null; partial => "
    "facts nonempty and reason nonblank string; abstained or insufficient_input "
    "=> facts=[] and reason nonblank string. Never emit partial with facts=[]."
)


def need(condition, message):
    if not condition:
        raise ContractError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def helpers():
    """Import existing guards only; importing this controller performs no IO."""
    need(digest(CONTROLLER.read_bytes()) == CONTROLLER_PIN, "P04 controller pin differs")
    spec = importlib.util.spec_from_file_location("p04b_p04_guards", CONTROLLER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def controls():
    """Exactly two declared artificial originals; no external facts or references."""
    originals = [
        ("fictional-two", {"toy_label": "violet-gear", "toy_count": 7}),
        ("fictional-eight", {"toy_label": "amber-cube", "toy_count": 11,
         "toy_ratio": 1.25, "toy_flag": False, "toy_order": ["b", "a"],
         "toy_object": {"mark": "q"}, "toy_null": None, "toy_empty": ""}),
    ]
    result = []
    for identifier, row in originals:
        original = dict(artificial=True, purpose="fictional literal copying only", rows=[row])
        source_hash = fingerprint(original)
        task = dict(task_id=identifier, collection=dict(status="selected_records"),
                    fields=[dict(record_key="toy-row", field=field, empty_policy="unknown")
                            for field in row])
        skeleton = [dict(fact_id=f"{identifier}:{field}", record_key="toy-row", field=field,
                    source=dict(source_id=identifier + "-original", sha256=source_hash,
                     release_id="fictional-v1", locator=dict(format="json", pointer="/rows/0"),
                     field=field)) for field in row]
        view = dict(interface="source-fact-reporting-view-v1", artificial=True, task=task,
                    task_sha256=fingerprint(task), source_records=[dict(record_key="toy-row", row=row)],
                    fact_skeleton=skeleton)
        facts = []
        for slot in skeleton:
            value = row[slot["field"]]
            reason = "null_source_value" if value is None else "empty_source_value" if value == "" else None
            facts.append(dict(fact_id=slot["fact_id"], value=None if reason else encode(value),
                              unit=None, source=encode(slot["source"]), unknown_reason=reason))
        expected = dict(schema_version=1, task_id=identifier, task_sha256=view["task_sha256"],
                        status="answered", facts=facts, collection_status="selected_records", reason=None)
        result.append(dict(control_id=identifier, original_input=original,
                           original_sha256=source_hash, view=view, expected=expected))
    return result


def prompt(control):
    data = dict(source_input=control["view"], stage="plain")
    text = canonical(data).decode("utf-8").replace("<|", "<\\u007c")
    rendered = ("<|im_start|>system\n" + _GUIDE + REFINEMENT + "<|im_end|>\n"
                "<|im_start|>user\n" + text + "<|im_end|>\n<|im_start|>assistant\n")
    prepare_completion(rendered, 2048, 0)  # Byte upper bound, not measured token use.
    return rendered


def validate(protocol, *, executable=False):
    need(type(protocol.get("schema_version")) is int and protocol["schema_version"] == 1
         and protocol.get("status") in ("DRAFT", "READY")
         and protocol.get("execution_allowed") is (protocol["status"] == "READY"), "DRAFT denies execution")
    need(not executable or protocol["status"] == "READY", "DRAFT denies execution")
    need(protocol.get("qualification_id") == "p04b-fictional-literal-v1", "Unknown qualification")
    need(canonical(protocol.get("controls")) == canonical(controls()), "Frozen fictional fixtures differ")
    need(canonical(protocol.get("scheduled_cells")) == canonical(SCHEDULE), "Exact two-cell plain schedule required")
    need(canonical(protocol.get("budgets_per_cell")) == canonical(BUDGET) and protocol.get("seed") == 0
         and type(protocol["seed"]) is int and type(protocol.get("maximum_output_tokens_per_call")) is int
         and protocol["maximum_output_tokens_per_call"] == 2048
         and type(protocol.get("setup_seconds")) is int and protocol["setup_seconds"] == 900
         and type(protocol.get("startup_seconds")) is int and protocol["startup_seconds"] == 180,
         "Literal caps differ")
    need(fingerprint(protocol.get("model")) == MODEL_PIN
         and fingerprint(protocol.get("server")) == SERVER_PIN, "Existing model/runtime/host pins differ")
    need(protocol.get("prompt_sha256") == {c["control_id"]: digest(prompt(c).encode()) for c in controls()},
         "Frozen prompt differs")
    need(protocol.get("retry_policy") == "none" and protocol.get("fallback_policy") == "none"
         and protocol.get("wire_format") == "typed_facts_v1", "No retry/fallback or wire revision")
    need(protocol.get("journal_limits") == dict(events=JOURNAL_MAX_EVENTS, bytes=JOURNAL_MAX_BYTES,
                                                details_bytes=65536), "Journal caps differ")
    return protocol


def dry_qualification(protocol):
    validate(protocol)
    spec, bindings = helpers()._server_spec(protocol)
    return dict(status="dry_qualified", execution_allowed=False, model_calls=0,
                cells=[dict(cell_id=cell["cell_id"], prompt_bytes=len(prompt(c).encode()),
                            expected_bytes=len(canonical(c["expected"])))
                       for cell, c in zip(SCHEDULE, controls())],
                server_host=spec.host, server_port=spec.port, pinned_assets=len(bindings),
                output_token_feasibility="unmeasured; byte counts are not token counts",
                scientific_validation="not_established")


class BoundedJournal(RunJournal):
    """Finite exact two-cell harness, retaining existing durable hash chaining."""
    def append(self, event, **details):
        size = len(canonical(details))
        need(len(self.events) < JOURNAL_MAX_EVENTS and size <= 65536
             and self._durable_size + size + 2048 <= JOURNAL_MAX_BYTES,
             "Qualification journal bound exceeded")
        return super().append(event, **details)


def grade(control, raw):
    """Strict existing adapter plus exact native JSON equality; never repairs."""
    adapted = adapt_output(raw, wire_format="typed_facts_v1", task_id=control["control_id"],
                           task_sha256=control["view"]["task_sha256"])
    if adapted["status"] != "scorable":
        return dict(terminal="malformed", passed=False, error=adapted["error"])
    exact = canonical(adapted["output"]) == canonical(control["expected"])
    return dict(terminal="returned", passed=exact, error=None if exact else "Exact fictional fixture mismatch")


class DeadlineOpener:
    def __init__(self, opener, deadline, monotonic):
        self.opener, self.deadline, self.monotonic = opener, deadline, monotonic

    def open(self, request, *, timeout):
        remaining = self.deadline - self.monotonic()
        need(remaining > 0, "Cell deadline before HTTP dispatch")
        return self.opener.open(request, timeout=min(timeout, remaining))


@contextmanager
def _owned_runtime(protocol, output, journal, holder):
    """Existing P04 exact asset/host ownership guards; no native bridge."""
    guard = helpers()
    setup_deadline = time.monotonic() + 900
    code = protocol.get("code_bundle")
    names = set(guard.code_inventory()) | {Path(__file__).resolve().relative_to(ROOT).as_posix()}
    need(isinstance(code, dict) and set(code) == names, "Complete frozen executing code inventory required")
    need(guard.capture_environment() == protocol.get("environment"), "Frozen execution environment differs")
    spec, bindings = guard._server_spec(protocol)
    with ExitStack() as stack:
        stack.enter_context(stable_files(tuple(checked_path(ROOT, name) for name in code),
                                        deadline=setup_deadline + 640))
        archive = output / "code"
        archive.mkdir()
        for name, pin in code.items():
            raw = guard._verified_bytes(checked_path(ROOT, name), pin, setup_deadline, 2 * 1024 * 1024)
            destination = archive / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            guard.write_bytes(destination, raw)
        acquisition = protocol["model"]["acquisition"]
        raw = guard._verified_bytes(checked_path(ROOT, acquisition["path"].replace("\\", "/")), acquisition, setup_deadline)
        guard.write_bytes(output / "model-acquisition.json", raw)
        stack.enter_context(stable_files(tuple(bindings.values()), deadline=setup_deadline + 640))
        evidence = guard.ListenerEvidence(output / "ownership", journal, setup_deadline)

        def spawn(argv, **kwargs):
            evidence._setup_bound()
            process = subprocess.Popen(argv, **kwargs)
            evidence.process = process
            return process

        server = OwnedServer(spec, bindings=bindings, output=output, journal=journal,
            listener_owner=evidence.owner, health_probe=evidence.health, process_factory=spawn,
            parent_deadline=setup_deadline + 640)
        holder["server"] = server
        stack.enter_context(server)
        evidence._setup_bound()
        evidence.ready = True
        holder.update(pid=evidence.process.pid, owner=evidence.owner)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), guard._RejectRedirect())
        yield server, lambda control: opener


def _exercise(protocol, output, *, runtime, holder, mock_only, monotonic=time.monotonic, protocol_raw=None):
    validate(protocol)
    clock, previous = monotonic, None

    def checked_clock():
        nonlocal previous
        now = clock()
        need(type(now) in (int, float) and math.isfinite(now)
             and (previous is None or now >= previous), "Invalid/reversing qualification clock")
        previous = now
        return now

    monotonic = checked_clock
    started = monotonic()
    guard = helpers()
    journal = BoundedJournal(Path(output))
    cells = [dict(**cell, terminal="unexecuted", dispatches=0, passed=False,
                  measured_usage=None, estimated_upper_usage=dict(ZERO), usage_unknown=False,
                  files={}, raw_content_sha256=None, elapsed_seconds=None, error=None) for cell in SCHEDULE]
    raw_contents, errors, cleanup = {}, [], None
    try:
        protocol_raw = canonical(protocol) if protocol_raw is None else protocol_raw
        journal.append("schedule_reserved", cells=SCHEDULE, retry_policy="none", mock_only=mock_only,
                       protocol_sha256=digest(protocol_raw))
        guard.write_bytes(journal.output / "protocol.json", protocol_raw)
        with runtime(protocol, journal.output, journal, holder) as (server, opener_factory):
            need(monotonic() - started < 900, "Setup budget exhausted")
            for record, control in zip(cells, controls()):
                cell_start = monotonic()
                text = prompt(control)
                quote = dict(input_tokens=len(text.encode()) + 32, output_tokens=2048, cost_usd=0.0)
                need(quote["input_tokens"] <= 32000 and quote["output_tokens"] <= 8000, "Cell reservation exceeds cap")
                folder = journal.output / record["cell_id"]
                folder.mkdir()
                attempt = dict(attempt=False, terminal=False)

                def retain(event):
                    if event["event"] == "attempt":
                        need(not attempt["attempt"] and not attempt["terminal"], "Duplicate attempt; no retry")
                        record["files"]["request"] = guard.write_bytes(folder / "raw-request.bin", event["raw_request"])
                        journal.append("attempt", cell_id=record["cell_id"], reserved=quote,
                                       request_sha256=event["request_sha256"], dispatched=False)
                        attempt["attempt"] = True
                        need(monotonic() - cell_start < 300, "Cell deadline before dispatch")
                        return
                    need(event["event"] == "terminal" and not attempt["terminal"], "Duplicate terminal")
                    attempt["terminal"] = True
                    result = event["result"]
                    record.update(terminal=result.status, dispatches=int(result.dispatched), error=result.error,
                                  measured_usage=encode(result.measured_usage),
                                  response_sha256=result.response_sha256, content_sha256=result.content_sha256,
                                  envelope_complete=result.envelope_complete,
                                  usage_unknown=result.dispatched and result.measured_usage is None,
                                  estimated_upper_usage=quote if result.dispatched and result.measured_usage is None else dict(ZERO))
                    if result.dispatched or result.raw_envelope:
                        record["files"]["envelope"] = guard.write_bytes(folder / "raw-envelope.bin", result.raw_envelope)
                    if result.content is not None:
                        record["files"]["content"] = guard.write_bytes(folder / "content.bin", result.content)
                        raw_contents[record["cell_id"]] = result.content
                        record["raw_content_sha256"] = digest(result.content)
                    journal.append("transport_terminal", **record)

                server.assert_ready()
                opener = opener_factory(control)
                need(not mock_only or getattr(opener, "p04b_mock_only", None) is True,
                     "Explicit non-network mock opener required")
                client = TypedReportingClient("http://127.0.0.1:55591", expected_pid=holder["pid"],
                    ownership_check=holder["owner"], opener=DeadlineOpener(opener, cell_start + 300, monotonic), retain=retain)
                remaining = 300 - (monotonic() - cell_start)
                need(remaining > 0, "Cell deadline before call")
                client.execute(text, maximum=2048, seed=0, timeout_seconds=min(300, remaining))
                record["elapsed_seconds"] = monotonic() - cell_start
                need(monotonic() - cell_start < 300, "Cell deadline after call")
                if record["terminal"] != "returned":
                    break
    except BaseException as error:
        errors.append(type(error).__name__ + ": " + str(error)[:240])
        try:
            journal.append("qualification_failed", error=errors[-1])
        except BaseException as secondary:
            errors.append("Failure journal: " + type(secondary).__name__)
    finally:
        owned = holder.get("server")
        cleanup = dict(started=None, server_stopped=None)
        try:
            cleanup = encode(owned.terminal_record) if owned is not None else dict(started=False, server_stopped=None)
            journal.append("generation_ceased", cleanup=cleanup)
        except BaseException as secondary:
            errors.append("Generation terminal: " + type(secondary).__name__)
    cleanup_affirmed = cleanup.get("server_stopped") is True
    if cleanup_affirmed and not errors:
        try:
            for record, control in zip(cells, controls()):
                if record["terminal"] == "returned":
                    record.update(grade(control, raw_contents[record["cell_id"]]))
                    journal.append("graded", cell_id=record["cell_id"], passed=record["passed"], terminal=record["terminal"])
        except BaseException as error:
            errors.append("Post-cleanup grading: " + type(error).__name__)
    passed = cleanup_affirmed and not errors and all(c["passed"] for c in cells)
    report = dict(status=("mock_passed" if mock_only else "qualified") if passed else "failed_branch_closed", mock_only=mock_only,
                  cells=cells, actual_calls=sum(c["dispatches"] for c in cells), cleanup=cleanup,
                  grading_allowed=cleanup_affirmed and not errors, errors=errors,
                  measured_usage={key: sum((c["measured_usage"] or ZERO)[key] for c in cells) for key in ZERO},
                  estimated_upper_usage={key: sum(c["estimated_upper_usage"][key] for c in cells) for key in ZERO},
                  unknown_usage_calls=sum(c["usage_unknown"] for c in cells),
                  call_count_basis="transport dispatched or potentially dispatched; not server-confirmed inference count",
                  elapsed_seconds=None, physical_io_bytes=None, peak_native_rss_bytes=None,
                  resource_unknown_reason="Physical IO and peak native memory not instrumented",
                  scientific_validation="not_established", model_scale_allowed=False)
    try:
        report["elapsed_seconds"] = monotonic() - started
        proof = guard.write_bytes(journal.output / "report.json", canonical(report))
        journal.append("qualification_terminal", report=proof, passed=passed)
        guard.write_bytes(journal.output / "receipt.json", canonical(dict(report=proof,
            status=report["status"], protocol_sha256=digest(protocol_raw), actual_calls=report["actual_calls"],
            journal_sha256=digest(journal.path.read_bytes()),
            journal_terminal_sha256=journal.events[-1]["sha256"])))
    except BaseException as error:
        report.update(status="failed_branch_closed")
        errors.append("Final publication: " + type(error).__name__)
        try:
            journal.append("qualification_publication_failed", passed=False, error=errors[-1])
        except BaseException:
            pass
        try:
            guard.write_bytes(journal.output / "failure-receipt.json", canonical(dict(
                status="failed_branch_closed", invalidates_report_success=True, errors=errors,
                actual_calls=report["actual_calls"], journal_terminal_sha256=journal.events[-1]["sha256"])))
        except BaseException:
            pass  # Absence of a complete success receipt also forbids success.
    finally:
        journal.close()
    return report


def exercise_mock(protocol, output, *, server, opener_factory, monotonic=time.monotonic):
    """Offline harness; trusted injected mocks never select a production opener."""
    validate(protocol)
    need(getattr(server, "p04b_mock_only", None) is True, "Explicit offline mock server required")
    holder = dict(server=server, pid=server.pid, owner=server.owner)

    @contextmanager
    def runtime(*args):
        with server:
            yield server, opener_factory

    return _exercise(protocol, output, runtime=runtime, holder=holder, mock_only=True, monotonic=monotonic)


def run_qualification(protocol_path, protocol_sha256, output, *, execute=False):
    raw = Path(protocol_path).read_bytes()
    need(type(protocol_sha256) is str and len(protocol_sha256) == 64 and digest(raw) == protocol_sha256,
         "Independent exact protocol SHA-256 required")
    protocol = validate(parse_json(raw), executable=True)
    need(execute is True, "Explicit --execute required")
    output = Path(output).absolute()
    need(output.parent.resolve() == (ROOT / "runs").resolve()
         and output.name.startswith("preprint-p04b-"), "Fresh P04b direct child of runs required")
    return _exercise(protocol, output, runtime=_owned_runtime, holder={}, mock_only=False, protocol_raw=raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=HERE / "PROTOCOL-DRAFT-v1.json")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--protocol-sha256")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.execute:
        need(args.output is not None, "Explicit fresh output required")
        result = run_qualification(args.protocol, args.protocol_sha256, args.output, execute=True)
        print(canonical(result).decode())
        return 0 if result["status"] == "qualified" else 1
    print(canonical(dry_qualification(parse_json(args.protocol.read_bytes()))).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
