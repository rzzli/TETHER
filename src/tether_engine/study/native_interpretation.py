"""One-use token-quoted native v2 adapter; source authority belongs to its caller.

Reuse the owned transport and existing exact-token capacity. This module starts
no server and cannot admit source/history authority. Controller integration is
required before a complete case or scientific qualification can be claimed.
"""

from collections.abc import Mapping
import math
from pathlib import Path
from threading import Lock
import time

from tether_engine.agents import Usage
from tether_engine.serde import canonical, decode, encode, fingerprint, freeze, parse_json
from tether_engine.workflow import Budget
from . import native, tokenization
from .interpretation_interface import (
    INTERFACE,
    request_from_payload,
    validate_output,
)
from .session import BackendCapabilities, _identity, need
from .stable_read import deadline_check
from .token_capacity import require_policy

KIND = "token_quoted_owned_native_interpretation_v2"
_NO_REPORT = object()
_DURATION_TOLERANCE_SECONDS = 1e-6


def _binding(request, payload):
    need(isinstance(request, Mapping), "Missing native stage request")
    original = request.get("original_request", request)
    decoded = request_from_payload(payload)
    need(
        fingerprint(original) == fingerprint(decoded), "Native original request differs"
    )
    return decoded


def _capabilities(policy):
    return BackendCapabilities(
        interface_version=INTERFACE,
        max_prompt_bytes=32768,
        max_output_tokens=1024,
        max_response_bytes=native.MAX_WRAPPER_RESPONSE,
        tokenizer_identity=policy.spec_sha256,
    )


def _context(value):
    need(
        isinstance(value, Mapping)
        and set(value) == {"endpoint", "owner_pid", "model_alias", "model_provenance"},
        "Explicit native context differs",
    )
    endpoint, _ = native._endpoint(value["endpoint"])
    need(
        type(value["owner_pid"]) is int and value["owner_pid"] > 0,
        "Native owner PID differs",
    )
    return freeze(
        dict(
            endpoint=endpoint,
            owner_pid=value["owner_pid"],
            model_alias=native._alias(value["model_alias"]),
            model_provenance=native._model(value["model_provenance"]),
        )
    )


def _provenance(context, policy, case_deadline, request, payload):
    need(
        type(case_deadline) in (int, float) and math.isfinite(case_deadline),
        "Missing finite native parent deadline",
    )
    return freeze(
        dict(
            kind=KIND,
            native_protocol=native.PROTOCOL,
            interface=INTERFACE,
            **encode(_context(context)),
            max_original_response_bytes=native.MAX_ORIGINAL_RESPONSE,
            provider_cost_usd=0,
            capacity_policy=policy.describe(),
            parent_case_end_monotonic=case_deadline,
            stage_request_sha256=fingerprint(request),
            payload_sha256=fingerprint(payload),
        )
    )


def _weights(policy, model, deadline):
    """Bind model identity to the externally anchored quote's approved specification."""
    deadline_check(deadline)
    with (policy.path / "spec.json").open("rb") as stream:
        raw = stream.read(131073)
    need(len(raw) <= 131072, "Native tokenizer spec exceeds bound")
    spec = parse_json(raw)
    need(
        fingerprint(spec) == policy.spec_sha256,
        "Native tokenizer specification differs",
    )
    spec = tokenization._validate_spec(spec)
    expected = {
        Path(a["relative_path"]).name: a["sha256"]
        for a in spec["assets"]
        if a["relative_path"].endswith(".gguf")
    }
    need(
        expected and canonical(expected) == canonical(model["weights_sha256"]),
        "Native model differs from quoted tokenizer weights",
    )
    deadline_check(deadline)


class TokenQuotedNativeBackend(native.LocalBackend):
    """Reuse exactly one owned HTTP POST; never launch/discover a server."""

    backend_id = "token-quoted-owned-local-native-v2"

    def __init__(
        self,
        *,
        endpoint,
        model_provenance,
        model_alias,
        owner,
        failure_directory,
        request,
        payload,
        capacity_policy,
        case_deadline,
    ):
        self.capacity_policy = require_policy(capacity_policy)
        deadline_check(case_deadline)
        self.case_deadline = case_deadline
        self.request, self.payload = freeze(encode(request)), freeze(encode(payload))
        _binding(self.request, self.payload)
        self._call_lock = Lock()
        self._attempted = False
        self._caller_end = None
        super().__init__(
            endpoint,
            "simplified",
            model_provenance,
            model_alias,
            owner,
            failure_directory,
        )
        self.interface = INTERFACE
        self.capabilities = _capabilities(self.capacity_policy)
        self.native_context = _context(
            dict(
                endpoint=self.endpoint,
                owner_pid=self.pid,
                model_alias=self.alias,
                model_provenance=model_provenance,
            )
        )
        self.provenance = _provenance(
            self.native_context,
            self.capacity_policy,
            case_deadline,
            self.request,
            self.payload,
        )

    def quote(self, request, payload):
        need(not self._used, "Native v2 backend already consumed")
        end = (
            min(self.case_deadline, self._caller_end)
            if self._caller_end is not None
            else self.case_deadline
        )
        deadline_check(end)
        need(
            canonical(request) == canonical(self.request)
            and canonical(payload) == canonical(self.payload),
            "Native stage/payload binding differs",
        )
        _binding(request, payload)
        quote = self.capacity_policy.reservation(
            request, payload, self.capabilities, deadline=end
        )
        _weights(self.capacity_policy, self.native_context["model_provenance"], end)
        deadline_check(end)
        return quote

    def _execution_deadline(self, start, timeout_seconds):
        # The inherited transport starts its own clock after fallible quoting.
        # Keep the earlier caller deadline instead of granting that time twice.
        return min(self.case_deadline, self._caller_end, start + timeout_seconds)

    def generate(self, request, payload, *, timeout_seconds):
        need(
            type(timeout_seconds) in (int, float)
            and math.isfinite(timeout_seconds)
            and timeout_seconds > 0,
            "No finite native v2 time remains",
        )
        need(
            self._call_lock.acquire(blocking=False),
            "Native v2 attempt is already running",
        )
        try:
            need(not self._attempted, "Native v2 attempt cannot repeat")
            self._attempted = True
            self._caller_end = min(
                self.case_deadline, time.monotonic() + timeout_seconds
            )
            deadline_check(self._caller_end)
            return super().generate(request, payload, timeout_seconds=timeout_seconds)
        finally:
            self._call_lock.release()


def validate_native_response(request, payload, content, *, model_alias):
    """Validate retained native bytes and authored assertions without repair."""
    original = _binding(request, payload)
    _, result, _ = native._native(content, request, payload, model_alias)
    return validate_output(original, payload, result["content"])


def verify_native_duration(wrapper, configuration, *, report=_NO_REPORT):
    """Reconcile relative transport duration; never infer absolute execution times."""
    need(
        isinstance(configuration, Mapping)
        and isinstance(configuration.get("budget"), Mapping)
        and set(configuration["budget"]) == set(encode(Budget())),
        "Native duration requires complete configured budget",
    )
    budget = decode(
        Budget, encode(configuration["budget"]), "native configuration.budget"
    )
    budget.validate()
    elapsed = wrapper.get("elapsed_seconds") if isinstance(wrapper, Mapping) else None
    need(
        type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0,
        "Native duration must be finite and nonnegative",
    )
    # Match successful StudySession reports and real deadline checks: reaching
    # the allocated cap is already expired, with no budget-extension tolerance.
    need(
        elapsed < budget.max_seconds,
        "Native duration reaches or exceeds configured budget",
    )
    if report is _NO_REPORT:
        return
    reported = report.get("elapsed_seconds") if isinstance(report, Mapping) else None
    need(
        type(reported) in (int, float)
        and math.isfinite(reported)
        and 0 <= reported < budget.max_seconds,
        "Native child report duration is invalid",
    )
    # Reuse the controller's absolute one-microsecond clock-rounding allowance.
    # It applies only to the enclosing-report comparison, never to the cap above.
    need(
        elapsed <= reported + _DURATION_TOLERANCE_SECONDS,
        "Native duration exceeds child report",
    )


def verify_native_execution(
    request,
    payload,
    content,
    configuration,
    usage,
    *,
    capacity_policy,
    case_deadline,
    expected_native,
    deadline=None,
):
    """Pure transport replay; original source/history/launch proof is caller-owned."""
    end = time.monotonic() + 299 if deadline is None else deadline
    deadline_check(end)
    policy = require_policy(capacity_policy)
    _binding(request, payload)
    context = _context(expected_native)
    binding = configuration.get("capacity_binding")
    need(
        type(configuration.get("schema_version")) is int
        and configuration["schema_version"] == 2
        and configuration.get("backend_id") == TokenQuotedNativeBackend.backend_id
        and canonical(configuration.get("capacity_policy"))
        == canonical(policy.describe())
        and isinstance(binding, Mapping)
        and binding.get("request_sha256") == fingerprint(request)
        and binding.get("payload_sha256") == fingerprint(payload)
        and binding.get("descriptor_sha256") == fingerprint(policy.describe()),
        "Native v2 requires exact version-two token authority",
    )
    need(
        canonical(configuration["adapter_code"])
        == canonical(_identity(TokenQuotedNativeBackend)),
        "Native v2 adapter identity differs",
    )
    need(
        canonical(configuration["adapter_provenance"])
        == canonical(_provenance(context, policy, case_deadline, request, payload)),
        "Native v2 provenance differs",
    )
    caps = _capabilities(policy)
    need(
        canonical(configuration["backend_capabilities"]) == canonical(caps),
        "Native v2 capabilities differ",
    )
    wrapper, _, expected_usage = native._native(
        content, request, payload, context["model_alias"]
    )
    verify_native_duration(wrapper, configuration)
    need(
        wrapper["endpoint"] == context["endpoint"]
        and wrapper["owner_pid"] == context["owner_pid"],
        "Native v2 wrapper ownership differs",
    )
    need(
        isinstance(usage, Usage) and canonical(usage) == canonical(expected_usage),
        "Native v2 measured usage differs",
    )
    quote = policy.reservation(request, payload, caps, deadline=end)
    need(
        usage.input_tokens <= quote.input_tokens
        and usage.output_tokens <= quote.output_tokens
        and usage.cost_usd == 0,
        "Native v2 usage exceeds authenticated quote",
    )
    _weights(policy, context["model_provenance"], end)
    validate_native_response(
        request, payload, content, model_alias=context["model_alias"]
    )
    deadline_check(end)
