"""Source-identical synthetic stage contracts; recorded transport only, no model."""

import copy
import hashlib
from importlib.resources import files
from pathlib import Path
import re
import math
import time

from asof.journal import read_chain
from asof.serde import ContractError, canonical, encode, fingerprint, freeze, parse_json
from asof.workflow import Budget

from .baseline_smoke import _read
from .baselines import _authenticated
from .diagnostic import (
    ACTIVE_SIMPLIFIED_SCHEMA,
    load_synthetic_request,
    validate_output,
)
from .diagnostic_resources import REQUIRED_RESOURCES as DIAGNOSTIC_RESOURCES
from .diagnostic_codec import need, quote_choices
from .proofs import _no_links, capture_file
from .recorded import RecordedBackend, RecordedVerifier, _document
from .session import GeneratedBytes, _identity, verify_study

PLAN_SHA256 = "33d2b7dff7a3f834132b005be650129f0378cf74a1f3083dc60f8db2688e3a52"
PLAN_RESOURCE = "resources/fixed-evidence-plan-v1.json"
REQUIRED_RESOURCES = DIAGNOSTIC_RESOURCES + (PLAN_RESOURCE,)
INTERFACE = "fixed-evidence-recorded-v1"
ARMS = ("asof_interpretation", "adapted_virtual_biotech_interpretation")


def load_plan():
    raw = files("asof.study").joinpath(PLAN_RESOURCE).read_bytes()
    need(
        hashlib.sha256(raw).hexdigest() == PLAN_SHA256,
        "Fixed-evidence plan resource differs",
    )
    plan = parse_json(raw)
    need(
        canonical(plan["aggregate_budget"]) == canonical(Budget()),
        "Fixed plan budget differs",
    )
    return freeze(plan)


def _context(fixture, arm, index):
    plan = load_plan()
    need(
        isinstance(fixture, str) and fixture in plan["fixture_names"],
        "Unknown synthetic fixture",
    )
    need(isinstance(arm, str) and arm in ARMS, "Unknown interpretation arm")
    stages = plan["asof_stages"] if arm == ARMS[0] else plan["stage_order"]
    need(type(index) is int and 0 <= index < len(stages), "Invalid stage index")
    req = _authenticated(load_synthetic_request(fixture))
    return plan, req, stages


def cell_path(fixture, arm, index):
    _, _, stages = _context(fixture, arm, index)
    return f"cells/{fixture}/{arm}/{index:02d}-{stages[index]}"


def _envelope(run_id, fixture, arm, index, proofs, history):
    plan, request, stages = _context(fixture, arm, index)
    need(
        isinstance(run_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", run_id),
        "Invalid comparison identity",
    )
    table = [
        dict(
            source_id=alias,
            observation_id=request["source_request"]["evidence"][i]["observation_id"],
            pointers=list(pointers),
        )
        for i, (alias, pointers) in enumerate(quote_choices(request).items())
    ]
    return freeze(
        dict(
            schema_version=1,
            kind="fixed_evidence_stage_request",
            comparison_run_id=run_id,
            fixture_id=fixture,
            arm=arm,
            stage_index=index,
            stage_name=stages[index],
            original_request=encode(request),
            original_request_sha256=fingerprint(request),
            source_scope_sha256=fingerprint(request["source_scope"]),
            question_key=request["question_key"],
            hypothesis_key=request["hypothesis_key"],
            policy_sha256=PLAN_SHA256,
            budget_policy_sha256=fingerprint(plan["aggregate_budget"]),
            prior_stage_proofs=proofs,
            history_projection=history,
            history_projection_sha256=fingerprint(history),
            history_authority="untrusted_generated_selection_not_evidence",
            original_source_table=table,
            original_source_table_sha256=fingerprint(table),
        )
    )


def _structural(stage):
    doc = encode(stage)
    need(isinstance(doc, dict), "Missing fixed stage request")
    try:
        plan, req, stages = _context(doc["fixture_id"], doc["arm"], doc["stage_index"])
        history = doc["history_projection"]
        proofs = doc["prior_stage_proofs"]
        need(
            isinstance(history, list)
            and isinstance(proofs, list)
            and len(history) == len(proofs) == doc["stage_index"],
            "Invalid predecessor prefix",
        )
        aliases = set(quote_choices(req))
        for i, row in enumerate(history):
            need(
                isinstance(row, dict)
                and set(row) == {"stage", "source_ids"}
                and row["stage"] == stages[i]
                and isinstance(row["source_ids"], list)
                and all(isinstance(x, str) for x in row["source_ids"])
                and row["source_ids"] == sorted(set(row["source_ids"]))
                and not set(row["source_ids"]) - aliases
                and len(row["source_ids"]) <= 3,
                "Invalid source-only history projection",
            )
        need(
            len(canonical(history)) <= plan["history"]["max_projection_bytes"],
            "History exceeds bound",
        )
        expected = _envelope(
            doc["comparison_run_id"],
            doc["fixture_id"],
            doc["arm"],
            doc["stage_index"],
            proofs,
            history,
        )
        need(
            canonical(doc) == canonical(expected),
            "Stage request/source/policy fields differ",
        )
        return freeze(doc)
    except (KeyError, TypeError, IndexError) as exc:
        raise ContractError("Malformed fixed stage request") from exc


def prepare_payload(stage_request):
    """Render only the frozen semantic projection; provenance never enters prompt."""
    stage = _structural(stage_request)
    plan = load_plan()
    request = encode(stage["original_request"])
    aliases = quote_choices(request)
    schema = copy.deepcopy(encode(ACTIVE_SIMPLIFIED_SCHEMA))
    schema.pop("$comment", None)
    schema["properties"]["claims"]["maxItems"] = request["source_request"]["bounds"][
        "max_claims"
    ]
    claim = schema["properties"]["claims"]["items"]["properties"]
    claim["source_ids"]["items"] = {"type": "string", "enum": list(aliases)}
    claim["quote_pointers"]["items"] = {
        "type": "string",
        "enum": sorted({p for choices in aliases.values() for p in choices}),
    }
    data = dict(
        original_request=request,
        original_source_table=encode(stage["original_source_table"]),
        stage=stage["stage_name"],
        prior_source_id_feedback=encode(stage["history_projection"]),
        feedback_authority="untrusted_generated_selection_not_evidence",
    )
    prompt = (
        "<|im_start|>system\n"
        + plan["guide"]
        + "\n"
        + plan["role_guides"][stage["stage_name"]]
        + "<|im_end|>\n<|im_start|>user\n"
        + canonical(data).decode().replace("<|", "<\\u007c")
        + "<|im_end|>\n<|im_start|>assistant\n"
    )
    payload = dict(
        prompt=prompt,
        n_predict=1024,
        temperature=0.0,
        seed=42,
        cache_prompt=False,
        json_schema=schema,
        stop=["<|im_end|>"],
        stream=False,
    )
    need(
        len(prompt.encode()) <= 6368 and len(canonical(payload)) <= 65536,
        "Complete fixed payload exceeds bound",
    )
    return freeze(payload)


def preflight(fixture):
    """Conservative complete six-stage schedule, including maximal ID feedback."""
    inputs = outputs = 0
    cells = []
    for arm in ARMS:
        _, req, stages = _context(fixture, arm, 0)
        for index, stage in enumerate(stages):
            history = [
                dict(stage=prior, source_ids=list(quote_choices(req)))
                for prior in stages[:index]
            ]
            envelope = _envelope(
                "preflight", fixture, arm, index, [{}] * index, history
            )
            payload = prepare_payload(envelope)
            size = len(payload["prompt"].encode()) + 32
            inputs += size
            outputs += payload["n_predict"]
            cells.append(
                dict(
                    arm=arm,
                    stage_index=index,
                    input_reservation=size,
                    output_reservation=1024,
                )
            )
    budget = Budget()
    need(
        inputs <= budget.max_input_tokens
        and outputs <= budget.max_output_tokens
        and len(cells) <= budget.max_calls,
        "Aggregate fixed schedule exceeds unchanged budget",
    )
    return freeze(
        dict(
            fixture=fixture,
            input_reservation=inputs,
            output_reservation=outputs,
            cells=cells,
            budget=encode(budget),
        )
    )


def recorded_document(request, payload):
    """Fixed evaluator-only transport stimulus; never a scientific reference."""
    stage = _structural(request)
    choices = quote_choices(stage["original_request"])
    alias = next(iter(choices))
    pointer = next(iter(choices[alias]))
    response = dict(
        answer_status="partial",
        claims=[
            dict(
                kind="source_report",
                text=choices[alias][pointer],
                source_ids=[alias],
                quote_pointers=[pointer],
                limitations=[],
            ),
            dict(
                kind="caution",
                text="This is an invented source-only transport fixture; no real-world scientific conclusion is attempted.",
                source_ids=[alias],
                quote_pointers=[pointer],
                limitations=[
                    "Synthetic fixture only; not a human reference or model prediction."
                ],
            ),
        ],
        unresolved=[
            "Independent scientific interpretation is not tested by this recorded fixture."
        ],
        abstention_reason="Recorded fixture exercises the interface only.",
    )
    return freeze(
        dict(
            schema_version=1,
            role="evaluation_only_fixture",
            request_sha256=fingerprint(stage),
            payload_sha256=fingerprint(payload),
            content_utf8=canonical(response).decode(),
            usage=dict(input_tokens=64, output_tokens=64, cost_usd=0.0),
            outcome="return",
        )
    )


class DeadlineRecordedBackend(RecordedBackend):
    """RecordedBackend's fixture semantics with a parent deadline at consumption."""

    def __init__(self, document, *, case_end):
        need(
            type(case_end) in (int, float) and math.isfinite(case_end),
            "Invalid parent monotonic deadline",
        )
        super().__init__(document, interface=INTERFACE)
        self.provenance = freeze(
            dict(encode(self.provenance), parent_case_end_monotonic=case_end)
        )

    def generate(self, request, payload, *, timeout_seconds):
        need(timeout_seconds > 0, "No fixture time remains")
        self.quote(request, payload)
        doc, usage = _document(self.provenance["document"], request, payload)
        need(
            time.monotonic() < self.provenance["parent_case_end_monotonic"],
            "Shared fixture deadline exceeded before recorded consumption",
        )
        self.used = True
        if doc["outcome"] == "timeout":
            raise TimeoutError("Recorded timeout fixture; no model call")
        return GeneratedBytes(doc["content_utf8"].encode("utf-8"), usage)


class RoleRecordedVerifier(RecordedVerifier):
    """Only verified same-root predecessors can supply non-evidence ID proposals."""

    required_resources = REQUIRED_RESOURCES

    def __init__(self, root, run_id):
        super().__init__(INTERFACE)
        self.root = Path(root).absolute()
        self.run_id = run_id
        self._verified = {}

    def _identity_check(self):
        _no_links(self.root)
        _no_links(self.root / "journal.jsonl")
        event = read_chain(self.root / "journal.jsonl")[0]
        need(
            event["event"] == "build_reserved"
            and event["details"]["run_id"] == self.run_id,
            "Comparison root identity differs",
        )

    def verify_stage(self, fixture, arm, index, anchor):
        self._identity_check()
        relative = cell_path(fixture, arm, index)
        folder = self.root / relative
        receipt, proof = _read(folder, "receipt.json")
        need(proof["sha256"] == anchor, "Predecessor receipt anchor differs")
        expected_names = {
            "request.json",
            "payload.json",
            "configuration.json",
            "raw-response.bin",
            "response.json",
            "report.json",
            "journal.jsonl",
            "receipt.json",
        }
        need(
            {p.name for p in folder.iterdir()} == expected_names,
            "Unexpected predecessor members",
        )
        req, _ = _read(folder, "request.json")
        need(
            isinstance(req, dict)
            and req.get("fixture_id") == fixture
            and req.get("arm") == arm
            and type(req.get("stage_index")) is int
            and req["stage_index"] == index
            and req.get("comparison_run_id") == self.run_id,
            "Predecessor is cross-case/arm/run",
        )
        key = (relative, anchor)
        if key not in self._verified:
            verify_study(folder, expected_receipt_sha256=anchor, verifier=self)
            self._verified[key] = encode(receipt)
        for name, expected in receipt["outputs"].items():
            need(
                canonical(capture_file(folder / name, name)) == canonical(expected),
                "Predecessor changed",
            )
        return freeze(receipt)

    def _history(self, fixture, arm, index):
        _, _, stages = _context(fixture, arm, index)
        proofs = []
        history = []
        for previous in range(index):
            relative = cell_path(fixture, arm, previous)
            folder = self.root / relative
            _, receipt_proof = _read(folder, "receipt.json")
            accepted = [
                event["details"]
                for event in read_chain(self.root / "journal.jsonl")
                if event["event"] == "stage_accepted"
                and event["details"].get("cell_id") == relative
            ]
            need(
                len(accepted) == 1
                and accepted[0].get("receipt_sha256") == receipt_proof["sha256"],
                "Predecessor was not accepted in this comparison run",
            )
            receipt = self.verify_stage(fixture, arm, previous, receipt_proof["sha256"])
            response, _ = _read(folder, "response.json")
            aliases = sorted(
                {
                    alias
                    for claim in response["response"]["claims"]
                    for alias in claim["source_ids"]
                }
            )
            history.append(dict(stage=stages[previous], source_ids=aliases))
            proofs.append(
                dict(
                    cell_id=relative,
                    receipt_sha256=receipt_proof["sha256"],
                    request_sha256=receipt["outputs"]["request.json"]["sha256"],
                    raw_response_sha256=receipt["outputs"]["raw-response.bin"][
                        "sha256"
                    ],
                    validated_response_sha256=receipt["outputs"]["response.json"][
                        "sha256"
                    ],
                )
            )
        return proofs, history

    def prepare_stage(self, fixture, arm, index):
        self._identity_check()
        _context(fixture, arm, index)
        proofs, history = self._history(fixture, arm, index)
        return _envelope(self.run_id, fixture, arm, index, proofs, history)

    def validate_payload(self, request, payload):
        stage = _structural(request)
        need(stage["comparison_run_id"] == self.run_id, "Wrong comparison run")
        expected = self.prepare_stage(
            stage["fixture_id"], stage["arm"], stage["stage_index"]
        )
        need(
            canonical(stage) == canonical(expected),
            "Unverified/cross-run generated history",
        )
        need(
            canonical(payload) == canonical(prepare_payload(expected)),
            "Fixed renderer/schema/source differs",
        )

    def validate_response(self, request, content):
        stage = _structural(request)
        need(len(content) <= 65536, "Fixed response exceeds bound")
        return validate_output(
            stage["original_request"], "simplified", parse_json(content)
        )

    def verify_execution(self, request, payload, content, configuration, usage):
        need(
            encode(configuration["adapter_code"]) == _identity(DeadlineRecordedBackend),
            "Wrong deadline-recorded adapter code",
        )
        provenance = encode(configuration["adapter_provenance"])
        need(
            set(provenance) == {"kind", "document", "parent_case_end_monotonic"},
            "Invalid deadline fixture provenance",
        )
        starts = [
            e["details"]
            for e in read_chain(self.root / "journal.jsonl")
            if e["event"] == "fixture_started"
            and e["details"].get("fixture") == request["fixture_id"]
        ]
        need(
            len(starts) == 1
            and provenance["parent_case_end_monotonic"]
            == starts[0]["case_end_monotonic"],
            "Adapter parent deadline differs",
        )
        # Authenticate the actual subclass first, then reuse the original recorded
        # consumer's unchanged document/usage checks with its expected base identity.
        delegated = encode(configuration)
        delegated["adapter_code"] = _identity(RecordedBackend)
        delegated["adapter_provenance"] = {
            k: v for k, v in provenance.items() if k != "parent_case_end_monotonic"
        }
        super().verify_execution(request, payload, content, freeze(delegated), usage)
        need(
            canonical(configuration["adapter_provenance"]["document"])
            == canonical(recorded_document(request, payload)),
            "Recorded stage differs from fixed synthetic transport fixture",
        )


def prepare_stage(root, run_id, fixture, arm, stage_index):
    return RoleRecordedVerifier(root, run_id).prepare_stage(fixture, arm, stage_index)


def verify_stage(root, run_id, fixture, arm, stage_index, receipt_sha256):
    return RoleRecordedVerifier(root, run_id).verify_stage(
        fixture, arm, stage_index, receipt_sha256
    )
