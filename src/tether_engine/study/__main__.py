"""Installed offline smoke study. This command has no native inference mode."""

import argparse
import hashlib
from pathlib import Path

from tether_engine.agents import Usage
from tether_engine.serde import canonical, encode, fingerprint
from tether_engine.workflow import Budget

from .diagnostic import REQUIRED_RESOURCES, load_synthetic_request, prepare_payload
from .recorded import RecordedBackend, RecordedVerifier
from .session import StudySession, inspect_study, verify_study


def fixture(request, payload, *, malformed=False, timeout=False):
    """Evaluator fixture construction is separate from source/prompt rendering."""
    literal = request["source_request"]["evidence"][0]["statement"]
    response = dict(
        answer_status="answered",
        claims=[
            dict(
                kind="source_report",
                text=literal,
                source_ids=["E0"],
                quote_pointers=["/statement"],
                limitations=[],
            )
        ],
        unresolved=[],
        abstention_reason=None,
    )
    return dict(
        schema_version=1,
        role="evaluation_only_fixture",
        request_sha256=fingerprint(request),
        payload_sha256=fingerprint(payload),
        content_utf8="{}" if malformed else canonical(response).decode("utf-8"),
        usage=encode(Usage(0, 0, 0.0)),
        outcome="timeout" if timeout else "return",
    )


def smoke(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    request = load_synthetic_request("synthetic-orientation")
    payload = prepare_payload(request, "simplified")
    verifier = RecordedVerifier()
    resources = {name: "study/" + name for name in REQUIRED_RESOURCES}
    config = dict(
        study_id="r05-diagnostic-recorded-smoke.v1",
        source_kind="synthetic_not_admitted",
        qualification="mechanical_fixture_only",
        features={},
        clinical_probability=None,
    )
    with StudySession(
        output / "success",
        budget=Budget(max_calls=1),
        configuration=config,
        resources=resources,
        required_resources=REQUIRED_RESOURCES,
    ) as cell:
        cell.call_once(
            request=request,
            payload=payload,
            backend=RecordedBackend(fixture(request, payload)),
            verifier=verifier,
        )
        cell.finish()
    receipt_hash = hashlib.sha256(
        (output / "success/receipt.json").read_bytes()
    ).hexdigest()
    success = verify_study(
        output / "success", expected_receipt_sha256=receipt_hash, verifier=verifier
    )
    try:
        with StudySession(
            output / "failure",
            budget=Budget(max_calls=1),
            configuration=config,
            resources=resources,
            required_resources=REQUIRED_RESOURCES,
        ) as cell:
            cell.call_once(
                request=request,
                payload=payload,
                backend=RecordedBackend(fixture(request, payload, malformed=True)),
                verifier=verifier,
            )
    except Exception as error:
        from tether_engine.serde import ContractError

        if not isinstance(error, ContractError):
            raise
    failure = inspect_study(output / "failure")
    assert failure["calls"] == 1 and not (output / "failure/receipt.json").exists()
    summary = dict(
        status="recorded_smoke_passed",
        success=encode(success),
        failure=encode(failure),
        native_model_calls=0,
        provider_spend_usd=0,
        scientific_validation="not_established",
    )
    (output / "smoke-report.json").write_bytes(canonical(summary) + b"\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("smoke",))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(canonical(smoke(args.output)).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
