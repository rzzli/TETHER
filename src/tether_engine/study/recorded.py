"""Explicit fingerprint-bound fixtures; never a live model or scientific reference."""

from tether_engine.agents import Usage
from tether_engine.serde import canonical, decode, encode, fingerprint, freeze, parse_json

from .diagnostic import REQUIRED_RESOURCES, prepare_payload, validate_output
from .session import BackendCapabilities, GeneratedBytes, _identity, need


def _document(value, request, payload):
    doc = encode(value)
    need(
        isinstance(doc, dict)
        and set(doc)
        == {
            "schema_version",
            "role",
            "request_sha256",
            "payload_sha256",
            "content_utf8",
            "usage",
            "outcome",
        },
        "Invalid recorded fixture",
    )
    need(
        type(doc["schema_version"]) is int
        and doc["schema_version"] == 1
        and doc["role"] == "evaluation_only_fixture",
        "Wrong recorded fixture role/version",
    )
    need(
        doc["request_sha256"] == fingerprint(request)
        and doc["payload_sha256"] == fingerprint(payload),
        "Fixture request/payload differs",
    )
    need(
        doc["outcome"] in ("return", "timeout")
        and isinstance(doc["content_utf8"], str),
        "Invalid fixture outcome",
    )
    usage = decode(Usage, doc["usage"])
    usage.validate()
    need(usage.cost_usd == 0, "Fixture provider cost must be zero")
    return freeze(doc), usage


class RecordedBackend:
    """Consume one explicitly supplied evaluator fixture. IDs do not select behavior."""

    def __init__(
        self,
        document,
        *,
        interface="simplified",
        backend_id="recorded-study-fixture-v1",
    ):
        self.provenance = freeze(
            dict(kind="recorded_study_fixture", document=encode(document))
        )
        self.capabilities = BackendCapabilities(interface_version=interface)
        self.backend_id = backend_id
        self.used = False

    def quote(self, request, payload):
        need(not self.used, "Fixture already consumed")
        _, usage = _document(self.provenance["document"], request, payload)
        quote = Usage(
            len(payload["prompt"].encode("utf-8")) + 32, payload["n_predict"], 0.0
        )
        need(
            usage.input_tokens <= quote.input_tokens
            and usage.output_tokens <= quote.output_tokens,
            "Fixture exceeds quote",
        )
        return quote

    def generate(self, request, payload, *, timeout_seconds):
        need(timeout_seconds > 0, "No fixture time remains")
        self.quote(request, payload)
        self.used = True
        doc, usage = _document(self.provenance["document"], request, payload)
        if doc["outcome"] == "timeout":
            raise TimeoutError("Recorded timeout fixture; no model call")
        return GeneratedBytes(doc["content_utf8"].encode("utf-8"), usage)


class RecordedVerifier:
    """Explicit trusted consumer/replay verifier, independent of backend ID."""

    required_resources = REQUIRED_RESOURCES

    def __init__(self, interface="simplified"):
        self.interface = interface

    def validate_payload(self, request, payload):
        need(
            canonical(prepare_payload(request, self.interface)) == canonical(payload),
            "Frozen payload differs",
        )

    def validate_response(self, request, content):
        return validate_output(request, self.interface, parse_json(content))

    def verify_execution(self, request, payload, content, configuration, usage):
        need(
            encode(configuration["adapter_code"]) == _identity(RecordedBackend),
            "Recorded adapter code identity differs",
        )
        provenance = configuration["adapter_provenance"]
        need(
            set(provenance) == {"kind", "document"}
            and provenance["kind"] == "recorded_study_fixture",
            "Wrong fixture provenance",
        )
        doc, expected_usage = _document(provenance["document"], request, payload)
        need(
            doc["outcome"] == "return"
            and doc["content_utf8"].encode("utf-8") == content,
            "Fixture response differs",
        )
        need(usage == expected_usage, "Fixture measured usage differs")
        need(
            configuration["backend_capabilities"]["interface_version"]
            == self.interface,
            "Verifier interface differs",
        )
