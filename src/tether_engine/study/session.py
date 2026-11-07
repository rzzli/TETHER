"""One-attempt study cells with durable accounting and explicit trusted verification.

Backend IDs are provenance. Capabilities and caller-supplied verifier objects define
behavior. Failed or unknown calls are never repeated, including during inspection.
This module establishes mechanics, not source entailment or scientific validity.
"""

from __future__ import annotations

import inspect
import hashlib
import math
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from tether_engine.agents import Usage
from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import (
    ContractError,
    canonical,
    decode,
    encode,
    fingerprint,
    freeze,
    parse_json,
)
from tether_engine.workflow import Budget, over_quote

from .proofs import capture_file, capture_package_proof, verify_package_proof


def need(condition, message):
    if not condition:
        raise ContractError(message)


@dataclass(frozen=True)
class BackendCapabilities:
    interface_version: str
    max_prompt_bytes: int = 14200
    max_payload_bytes: int = 65536
    max_response_bytes: int = 65536
    context_tokens: int = 16384
    max_output_tokens: int = 2048
    tokenizer_identity: str | None = None

    def validate(self):
        need(
            isinstance(self.interface_version, str)
            and bool(self.interface_version.strip()),
            "Missing interface",
        )
        for name in (
            "max_prompt_bytes",
            "max_payload_bytes",
            "max_response_bytes",
            "context_tokens",
            "max_output_tokens",
        ):
            value = getattr(self, name)
            need(type(value) is int and value > 0, "Invalid capability bound")
        need(self.max_response_bytes <= 1048576, "Response capture exceeds study limit")


@dataclass(frozen=True)
class GeneratedBytes:
    content: bytes
    usage: Usage | None


class StudyBackend(Protocol):
    backend_id: str
    capabilities: BackendCapabilities
    provenance: Mapping

    def quote(self, request, payload) -> Usage: ...

    def generate(
        self, request, payload, *, timeout_seconds: float
    ) -> GeneratedBytes: ...


class StudyVerifier(Protocol):
    """Trusted code passed explicitly; no symbols are imported from archived JSON."""

    required_resources: tuple[str, ...]

    def validate_payload(self, request, payload) -> None: ...

    def validate_response(self, request, content: bytes) -> Mapping: ...

    def verify_execution(
        self, request, payload, content: bytes, configuration, usage: Usage
    ) -> None: ...


def _identity(value):
    cls = value if inspect.isclass(value) else type(value)
    proof = capture_file(Path(inspect.getfile(cls)), logical_id="trusted-code.py")
    return dict(symbol=cls.__module__ + "." + cls.__qualname__, file=encode(proof))


def _usage(value):
    need(isinstance(value, Usage), "Usage must use the explicit adapter contract")
    value.validate()
    return value


def _capacity(payload, caps, quote, budget):
    """Shared execution/replay admission; token estimates stay distinct from bytes."""
    need(isinstance(caps, BackendCapabilities), "Missing explicit backend capabilities")
    caps.validate()
    budget.validate()
    quote = _usage(quote)
    prompt = payload.get("prompt")
    need(
        isinstance(prompt, str)
        and len(prompt.encode("utf-8")) <= caps.max_prompt_bytes,
        "Prompt exceeds capability",
    )
    need(
        len(canonical(payload)) <= caps.max_payload_bytes, "Payload exceeds capability"
    )
    output_tokens = payload.get("n_predict")
    need(
        type(output_tokens) is int and 0 < output_tokens <= caps.max_output_tokens,
        "Output exceeds capability",
    )
    need(
        quote.input_tokens >= len(prompt.encode("utf-8")) + 32,
        "Quote lacks conservative prompt reservation",
    )
    need(
        quote.output_tokens >= output_tokens
        and quote.input_tokens + quote.output_tokens <= caps.context_tokens,
        "Quote/context mismatch",
    )
    need(
        quote.cost_usd == budget.max_cost_usd == 0
        and budget.max_calls >= 1
        and quote.input_tokens <= budget.max_input_tokens
        and quote.output_tokens <= budget.max_output_tokens,
        "Cell exceeds budget",
    )


def _write(output, name, value):
    publish_bytes(output / name, canonical(value) + b"\n")


def _read(output, name, limit=1048576):
    path = output / name
    need(path.is_file() and not path.is_symlink(), "Missing or aliased study artifact")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    need(len(raw) <= limit, "Study artifact exceeds read bound")
    return raw


class StudySession:
    """Exclusive, single planned cell. A second call is rejected in all outcomes.

    A matched study must allocate and check its aggregate case budget before
    creating cells; this helper does not reset or enlarge a parent allocation.
    """

    def __init__(
        self, output, *, budget=None, configuration=None, resources, required_resources,
        capacity_policy=None,
    ):
        self.output = Path(output).resolve()
        self.budget = decode(Budget, encode(budget if budget is not None else Budget()))
        self.budget.validate()
        need(
            self.budget.max_cost_usd == 0, "This study route has zero provider spending"
        )
        self.resources = dict(resources)
        self.required_resources = tuple(required_resources)
        self.configuration = freeze(configuration or {})
        if capacity_policy is not None:
            from .token_capacity import require_policy
            require_policy(capacity_policy)
        self.capacity_policy = capacity_policy
        self.started = time.monotonic()
        self.journal = RunJournal(self.output, kind="build")
        self.run_id = self.journal.events[0]["details"]["run_id"]
        self.called = self.failed = self.sealed = self.closed = False
        self.accepted = None
        self.accounted = False
        self.outstanding = None
        self.usage = Usage(0, 0, 0.0)
        self.basis = None
        self.files = set()
        try:
            self.package_proof = capture_package_proof(
                resources=self.resources, required_resources=self.required_resources
            )
        except BaseException as primary:
            self._failure(primary, "package_proof")
            try:
                self.journal.close()
            except BaseException as secondary:
                primary.add_note("Journal close failed: " + type(secondary).__name__)
            raise

    def __enter__(self):
        return self

    def _put(self, name, value):
        _write(self.output, name, value)
        self.files.add(name)

    def _account(self, usage, basis):
        self.journal.append(
            "study_accounted", attempt_id="cell", usage=encode(usage), basis=basis
        )
        self.usage, self.basis = usage, basis
        self.accounted, self.outstanding = True, None

    def _failure(self, primary, stage):
        self.failed = True
        for operation, action in (
            ("terminal journal", lambda: self.journal.fail(primary, stage)),
            (
                "failure marker",
                lambda: _write(
                    self.output,
                    "failure.json",
                    dict(
                        schema_version=1,
                        run_id=self.run_id,
                        stage=stage,
                        error_class=type(primary).__name__,
                        successful_receipt=False,
                    ),
                ),
            ),
        ):
            try:
                action()
            except BaseException as secondary:
                primary.add_note(operation + " failed: " + type(secondary).__name__)

    def call_once(
        self, *, request, payload, backend: StudyBackend, verifier: StudyVerifier
    ):
        need(
            not self.called and not self.failed and not self.sealed and not self.closed,
            "Study cell cannot repeat",
        )
        self.called = True
        generated = None
        dispatched = False
        quote = None
        stage = "preflight"
        try:
            verify_package_proof(
                self.package_proof, required_resources=self.required_resources
            )
            request, payload = freeze(encode(request)), freeze(encode(payload))
            caps = backend.capabilities
            need(
                isinstance(caps, BackendCapabilities),
                "Missing explicit backend capabilities",
            )
            caps.validate()
            need(
                isinstance(backend.backend_id, str) and backend.backend_id.strip(),
                "Missing backend provenance ID",
            )
            need(
                set(verifier.required_resources) == set(self.required_resources),
                "Consumer resource set differs",
            )
            verifier.validate_payload(request, payload)
            prompt = payload.get("prompt")
            need(
                isinstance(prompt, str)
                and len(prompt.encode("utf-8")) <= caps.max_prompt_bytes,
                "Prompt exceeds capability",
            )
            need(
                len(canonical(payload)) <= caps.max_payload_bytes,
                "Payload exceeds capability",
            )
            output_tokens = payload.get("n_predict")
            need(
                type(output_tokens) is int
                and 0 < output_tokens <= caps.max_output_tokens,
                "Output exceeds capability",
            )
            config = dict(
                schema_version=1,
                kind="study_cell",
                run_id=self.run_id,
                caller_configuration=encode(self.configuration),
                budget=encode(self.budget),
                backend_id=backend.backend_id,
                backend_capabilities=encode(caps),
                adapter_provenance=encode(backend.provenance),
                adapter_code=_identity(backend),
                verifier_code=_identity(verifier),
                package_proof=encode(self.package_proof),
                required_resources=list(self.required_resources),
                request_sha256=fingerprint(request),
                payload_sha256=fingerprint(payload),
                automatic_retries=False,
                source_qualification="not_established_by_generic_study_session",
            )
            if self.capacity_policy is not None:
                # Inputs survive a failed quote. Configuration2 is published only
                # after the exact capacity authority has authenticated its quote.
                self._put("request.json", request)
                self._put("payload.json", payload)
                quote = _usage(backend.quote(request, payload))
                binding = self.capacity_policy.verify(
                    request, payload, caps, quote, self.budget,
                    deadline=self.started + self.budget.max_seconds,
                )
                config.update(schema_version=2,
                    capacity_policy=encode(self.capacity_policy.describe()),
                    capacity_binding=encode(binding))
            for name, value in (
                ("configuration.json", config),
                ("request.json", request),
                ("payload.json", payload),
            ):
                if name not in self.files:
                    self._put(name, value)
            self.journal.append(
                "study_prepared",
                run_id=self.run_id,
                configuration_sha256=fingerprint(config),
            )
            if self.capacity_policy is None:
                quote = _usage(backend.quote(request, payload))
                _capacity(payload, caps, quote, self.budget)
            remaining = self.budget.max_seconds - (time.monotonic() - self.started)
            need(
                self.budget.max_calls >= 1
                and quote.input_tokens <= self.budget.max_input_tokens
                and quote.output_tokens <= self.budget.max_output_tokens
                and remaining > 0,
                "Cell exceeds budget",
            )
            stage = "dispatch"
            self.journal.append(
                "study_dispatch",
                attempt_id="cell",
                request_sha256=fingerprint(request),
                payload_sha256=fingerprint(payload),
                reserved=encode(quote),
            )
            dispatched = True
            self.outstanding = quote
            generated = backend.generate(request, payload, timeout_seconds=remaining)
            stage = "response_capture"
            measured = None
            if isinstance(generated, GeneratedBytes):
                try:
                    measured = _usage(generated.usage)
                except (ContractError, TypeError, ValueError):
                    pass
            self._account(
                measured or quote,
                "adapter_reported" if measured is not None else "conservative_quote",
            )
            need(
                isinstance(generated, GeneratedBytes)
                and isinstance(generated.content, bytes),
                "Malformed generated envelope",
            )
            raw = generated.content
            publish_bytes(
                self.output / "raw-response.bin", raw[: caps.max_response_bytes]
            )
            self.files.add("raw-response.bin")
            self.journal.append(
                "study_response_captured",
                content_sha256=hashlib.sha256(raw).hexdigest(),
                content_bytes=len(raw),
                retained_bytes=min(len(raw), caps.max_response_bytes),
                complete=len(raw) <= caps.max_response_bytes,
            )
            need(
                len(raw) <= caps.max_response_bytes,
                "Response exceeds bound; explicit prefix retained",
            )
            need(not over_quote(self.usage, quote), "Actual usage exceeds quote")
            need(
                time.monotonic() - self.started < self.budget.max_seconds,
                "Cell exceeded shared wall budget",
            )
            stage = "response_validation"
            response = verifier.validate_response(request, raw)
            verifier.verify_execution(request, payload, raw, freeze(config), self.usage)
            self._put("response.json", response)
            self.journal.append(
                "study_response_accepted", response_sha256=fingerprint(response)
            )
            self.accepted = freeze(response)
            self._verifier, self._request, self._payload, self._config = (
                verifier,
                request,
                payload,
                freeze(config),
            )
            return self.accepted
        except BaseException as primary:
            if dispatched and not self.accounted:
                # A failed accounting write remains unresolved; do not fabricate a
                # second measured event or issue another generation.
                has_account = any(
                    e["event"] == "study_accounted" for e in self.journal.events
                )
                if stage == "dispatch" or generated is None:
                    try:
                        self._account(quote, "conservative_quote")
                    except BaseException as secondary:
                        primary.add_note(
                            "Accounting failed: " + type(secondary).__name__
                        )
                elif has_account:
                    self.accounted = True
            self._failure(primary, stage)
            raise

    def finish(self):
        need(
            self.accepted is not None
            and not self.failed
            and self.accounted
            and not self.sealed,
            "Incomplete study cell cannot finalize",
        )
        try:
            verify_package_proof(
                self.package_proof, required_resources=self.required_resources
            )
            for name, expected in (
                ("request.json", self._request),
                ("payload.json", self._payload),
                ("configuration.json", self._config),
                ("response.json", self.accepted),
            ):
                need(
                    fingerprint(parse_json(_read(self.output, name)))
                    == fingerprint(expected),
                    "Archived accepted state changed before finalization",
                )
            need(
                fingerprint(read_chain(self.output / "journal.jsonl"))
                == fingerprint(self.journal.events),
                "Durable journal differs from accepted execution",
            )
            need(
                time.monotonic() - self.started < self.budget.max_seconds,
                "Cell exceeded finalization wall budget",
            )
            need(
                _identity(self._verifier) == encode(self._config["verifier_code"]),
                "Trusted verifier changed",
            )
            self._verifier.verify_execution(
                self._request,
                self._payload,
                _read(self.output, "raw-response.bin"),
                self._config,
                self.usage,
            )
            if self.capacity_policy is not None:
                dispatch = next(e['details'] for e in self.journal.events
                                if e['event'] == 'study_dispatch')
                binding = self.capacity_policy.verify(
                    self._request, self._payload,
                    decode(BackendCapabilities, encode(self._config['backend_capabilities'])),
                    decode(Usage, encode(dispatch['reserved'])), self.budget,
                    deadline=self.started+self.budget.max_seconds,
                )
                need(canonical(binding) == canonical(self._config['capacity_binding'])
                     and canonical(self.capacity_policy.describe()) == canonical(self._config['capacity_policy']),
                     'Capacity authority changed before finalization')
            report = dict(
                schema_version=1,
                kind="study_cell_report",
                run_id=self.run_id,
                status="contract_completed_not_scientific_validation",
                calls=1,
                measured_usage=encode(
                    self.usage if self.basis == "adapter_reported" else Usage(0, 0, 0.0)
                ),
                estimated_usage=encode(
                    self.usage if self.basis != "adapter_reported" else Usage(0, 0, 0.0)
                ),
                request_sha256=fingerprint(self._request),
                payload_sha256=fingerprint(self._payload),
                response_sha256=fingerprint(self.accepted),
                elapsed_seconds=time.monotonic() - self.started,
                features={},
                clinical_probability=None,
                scientific_validation="not_performed",
            )
            self._put("report.json", report)
            self.journal.append("study_completed", report_sha256=fingerprint(report))
            self.journal.close()
            self.closed = True
            self.files.add("journal.jsonl")
            outputs = {
                name: encode(capture_file(self.output / name, logical_id=name))
                for name in sorted(self.files)
            }
            receipt = dict(schema_version=1, kind="study_cell_receipt",
                           run_id=self.run_id, outputs=outputs)
            if self.capacity_policy is not None:
                receipt.update(schema_version=2, capacity_sha256=fingerprint(dict(
                    capacity_policy=self._config['capacity_policy'],
                    capacity_binding=self._config['capacity_binding'])))
                from .stable_read import deadline_check
                deadline_check(self.started+self.budget.max_seconds)
            self._put("receipt.json", receipt)
            if self.capacity_policy is not None:
                deadline_check(self.started+self.budget.max_seconds)
            self.sealed = True
            return freeze(report)
        except BaseException as primary:
            if self.capacity_policy is not None and 'receipt.json' in self.files and not self.sealed:
                try:
                    need(_read(self.output,'receipt.json') == canonical(receipt)+b'\n',
                         'Published token receipt changed before withdrawal')
                    (self.output/'receipt.json').unlink()
                    self.files.remove('receipt.json')
                except BaseException as secondary:
                    primary.add_note('Token receipt withdrawal failed: '+type(secondary).__name__)
            self._failure(primary, "finalization")
            raise

    def __exit__(self, kind, primary, traceback):
        if primary is not None and not self.failed:
            self._failure(primary, "caller")
        if primary is None and not self.sealed:
            primary = ContractError("Study exited without finalization")
            self._failure(primary, "unfinalized")
        if not self.closed:
            try:
                self.journal.close()
                self.closed = True
            except BaseException as secondary:
                if primary is None:
                    self._failure(secondary, "journal_close")
                    raise
                primary.add_note("Journal close failed: " + type(secondary).__name__)
        if kind is None and primary is not None:
            raise primary
        return False


def inspect_study(output):
    """Read-only accounting, including potentially billed unresolved reservations."""
    output = Path(output)
    events = read_chain(output / "journal.jsonl", allow_incomplete_tail=True)
    dispatches = [e for e in events if e["event"] == "study_dispatch"]
    accounts = [e for e in events if e["event"] == "study_accounted"]
    need(
        len(dispatches) <= 1 and len(accounts) <= len(dispatches),
        "Contradictory study accounting",
    )
    if accounts:
        need(
            accounts[0]["sequence"] > dispatches[0]["sequence"],
            "Accounting precedes dispatch",
        )
    measured, estimated = Usage(0, 0, 0.0), Usage(0, 0, 0.0)
    if accounts:
        detail = accounts[0]["details"]
        need(
            detail["attempt_id"] == dispatches[0]["details"]["attempt_id"] == "cell",
            "Account identity differs",
        )
        usage = decode(Usage, encode(detail["usage"]))
        usage.validate()
        need(
            detail["basis"] in ("adapter_reported", "conservative_quote"),
            "Unknown accounting basis",
        )
        if detail["basis"] == "adapter_reported":
            measured = usage
        else:
            need(
                usage == decode(Usage, encode(dispatches[0]["details"]["reserved"])),
                "Conservative usage differs from full reservation",
            )
            estimated = usage
    elif dispatches:
        estimated = decode(Usage, encode(dispatches[0]["details"]["reserved"]))
        estimated.validate()
    failure = (output / "failure.json").is_file()
    failure_events = any(
        e["event"] in ("build_failed", "build_interrupted") for e in events
    )
    complete = (
        events[-1]["event"] == "study_completed"
        and (output / "receipt.json").is_file()
        and not failure
        and not failure_events
    )
    return freeze(
        dict(
            schema_version=1,
            status="sealed_unverified" if complete else "failed_or_incomplete",
            calls=len(dispatches),
            unresolved_attempts=["cell"] if dispatches and not accounts else [],
            measured_usage=encode(measured),
            estimated_usage=encode(estimated),
            durable_events=len(events),
            failure_marker_present=failure,
            recovery_action="inspect only; never automatically repeat any cell",
        )
    )


def verify_study(output, *, expected_receipt_sha256, verifier: StudyVerifier,
                 capacity_policy=None, deadline=None):
    """Byte/accounting/consumer consistency; no archived executable import."""
    output = Path(output)
    def check_deadline():
        if deadline is not None:
            from .stable_read import deadline_check
            deadline_check(deadline)
    check_deadline()
    raw_receipt = _read(output, "receipt.json")
    need(
        hashlib.sha256(raw_receipt).hexdigest() == expected_receipt_sha256,
        "Wrong external receipt anchor",
    )
    receipt = parse_json(raw_receipt)
    required = {
        "request.json",
        "payload.json",
        "configuration.json",
        "raw-response.bin",
        "response.json",
        "report.json",
        "journal.jsonl",
    }
    need(
        receipt.get("kind") == "study_cell_receipt"
        and set(receipt.get("outputs", {})) == required,
        "Incomplete study output set",
    )
    for name, proof in receipt["outputs"].items():
        check_deadline()
        need(
            encode(capture_file(output / name, logical_id=name)) == proof,
            "Study output fingerprint differs",
        )
    config = parse_json(_read(output, "configuration.json"))
    request = parse_json(_read(output, "request.json"))
    payload = parse_json(_read(output, "payload.json"))
    response = parse_json(_read(output, "response.json"))
    report = parse_json(_read(output, "report.json"))
    raw = _read(output, "raw-response.bin")
    need(
        _identity(verifier) == config["verifier_code"],
        "Explicit trusted verifier identity differs",
    )
    need(
        type(config.get("schema_version")) is int
        and config["schema_version"] in (1, 2)
        and config.get("kind") == "study_cell"
        and type(receipt.get("schema_version")) is int
        and receipt["schema_version"] == config["schema_version"],
        "Unsupported study schema",
    )
    if config['schema_version'] == 2:
        from .token_capacity import require_policy
        from .stable_read import deadline_check
        require_policy(capacity_policy)
        deadline_check(deadline)
        base_fields = {
            'schema_version','kind','run_id','caller_configuration','budget','backend_id',
            'backend_capabilities','adapter_provenance','adapter_code','verifier_code',
            'package_proof','required_resources','request_sha256','payload_sha256',
            'automatic_retries','source_qualification','capacity_policy','capacity_binding',
        }
        need(set(config) == base_fields
             and set(receipt) == {'schema_version','kind','run_id','outputs','capacity_sha256'},
             'Token study fields differ')
        need(canonical(config['capacity_policy']) == canonical(capacity_policy.describe())
             and receipt['capacity_sha256'] == fingerprint(dict(
                 capacity_policy=config['capacity_policy'],capacity_binding=config['capacity_binding'])),
             'Token capacity descriptor/receipt differs')
    else:
        need(capacity_policy is None and not {'capacity_policy','capacity_binding'} & set(config)
             and 'capacity_sha256' not in receipt,'Legacy study cannot select token semantics')
    need(
        type(report.get("schema_version")) is int
        and report["schema_version"] == 1
        and report.get("kind") == "study_cell_report"
        and type(report.get("calls")) is int,
        "Unsupported report schema",
    )
    need(
        set(verifier.required_resources) == set(config["required_resources"]),
        "Consumer resource set differs",
    )
    verify_package_proof(
        config["package_proof"], required_resources=tuple(verifier.required_resources)
    )
    check_deadline()
    need(
        config["automatic_retries"] is False and config["budget"]["max_cost_usd"] == 0,
        "Study policy differs",
    )
    verifier.validate_payload(freeze(request), freeze(payload))
    need(
        fingerprint(verifier.validate_response(freeze(request), raw))
        == fingerprint(response),
        "Response reconstruction differs",
    )
    inspected = inspect_study(output)
    need(
        inspected["status"] == "sealed_unverified"
        and inspected["calls"] == 1
        and not inspected["unresolved_attempts"],
        "Incomplete accounting",
    )
    usage = Usage(
        **{
            key: inspected["measured_usage"][key] + inspected["estimated_usage"][key]
            for key in ("input_tokens", "output_tokens", "cost_usd")
        }
    )
    verifier.verify_execution(
        freeze(request), freeze(payload), raw, freeze(config), usage
    )
    check_deadline()
    events = read_chain(output / "journal.jsonl")
    need(
        [e["event"] for e in events]
        == [
            "build_reserved",
            "study_prepared",
            "study_dispatch",
            "study_accounted",
            "study_response_captured",
            "study_response_accepted",
            "study_completed",
        ],
        "Study event order differs",
    )
    need(
        events[1]["event"] == "study_prepared"
        and events[1]["details"]["configuration_sha256"] == fingerprint(config),
        "Configuration journal binding differs",
    )
    dispatch = next(e["details"] for e in events if e["event"] == "study_dispatch")
    capacity_args = (payload,decode(BackendCapabilities, config['backend_capabilities']),
                     decode(Usage,encode(dispatch['reserved'])),decode(Budget,config['budget']))
    if capacity_policy is None:
        _capacity(*capacity_args)
    else:
        binding = capacity_policy.verify(request,*capacity_args,deadline=deadline)
        need(canonical(binding) == canonical(config['capacity_binding']),
             'Token capacity binding differs from authenticated recomputation')
    need(
        len(raw) <= config["backend_capabilities"]["max_response_bytes"],
        "Raw response exceeds capability",
    )
    need(
        type(report.get("elapsed_seconds")) in (int, float)
        and math.isfinite(report["elapsed_seconds"])
        and 0 <= report["elapsed_seconds"] < config["budget"]["max_seconds"],
        "Completed report exceeds wall budget",
    )
    need(
        not over_quote(usage, decode(Usage, encode(dispatch["reserved"]))),
        "Usage exceeds reservation",
    )
    run_id = events[0]["details"]["run_id"]
    need(
        receipt["run_id"] == config["run_id"] == report["run_id"] == run_id,
        "Run identity differs",
    )
    need(
        events[1]["details"]["run_id"] == run_id
        and report.get("status") == "contract_completed_not_scientific_validation",
        "Run status/identity differs",
    )
    need(
        config["request_sha256"]
        == report["request_sha256"]
        == dispatch["request_sha256"]
        == fingerprint(request)
        and config["payload_sha256"]
        == report["payload_sha256"]
        == dispatch["payload_sha256"]
        == fingerprint(payload),
        "Request/payload binding differs",
    )
    need(
        report["response_sha256"] == fingerprint(response)
        and report["calls"] == 1
        and report["measured_usage"] == encode(inspected["measured_usage"])
        and report["estimated_usage"] == encode(inspected["estimated_usage"]),
        "Run accounting/response differs",
    )
    need(
        events[-1]["details"]["report_sha256"] == fingerprint(report)
        and report["features"] == {}
        and report["clinical_probability"] is None
        and report["scientific_validation"] == "not_performed",
        "Report policy/journal differs",
    )
    accepted = [e for e in events if e["event"] == "study_response_accepted"]
    captured = [e for e in events if e["event"] == "study_response_captured"]
    need(
        len(accepted) == len(captured) == 1
        and accepted[0]["details"]["response_sha256"] == fingerprint(response),
        "Accepted response differs",
    )
    need(
        captured[0]["details"]["complete"] is True
        and captured[0]["details"]["content_bytes"] == len(raw)
        and captured[0]["details"]["retained_bytes"] == len(raw)
        and captured[0]["details"]["content_sha256"] == hashlib.sha256(raw).hexdigest(),
        "Raw response differs",
    )
    check_deadline()
    return freeze(
        dict(
            status="verified_study_cell",
            byte_integrity="verified",
            mechanical_consistency="verified",
            consumer_contract="verified",
            scientific_validation="not_established",
            run_id=run_id,
        )
    )
