"""Reconcile native/simulated attempts from durable child journals and wrappers."""

import base64
import hashlib
from asof.agents import Usage
from asof.journal import read_chain
from asof.serde import ContractError, canonical, encode, fingerprint, parse_json
from .native import PROTOCOL
from .diagnostic_codec import need


def accounting(root, scope):
    measured = dict(input_tokens=0, output_tokens=0, cost_usd=0.0)
    conservative = dict(measured)
    recovered = dict(measured)
    attempts = known_http = known_model = 0
    ready = [
        e["details"]["context"]
        for e in read_chain(root / "journal.jsonl")
        if e["event"] == "native_context_qualified"
    ]
    need(len(ready) <= 1, "Duplicate native accounting context")
    context = ready[0] if ready else None
    for cell in range(6):
        path = root / "cells" / f"{cell:02d}"
        if not (path / "journal.jsonl").is_file():
            continue
        events = read_chain(path / "journal.jsonl")
        dispatch = [e for e in events if e["event"] == "study_dispatch"]
        accounts = [e["details"] for e in events if e["event"] == "study_accounted"]
        need(
            len(dispatch) <= 1 and len(accounts) <= 1,
            "Duplicate native child accounting",
        )
        if accounts:
            a = accounts[0]
            usage = Usage(**a["usage"])
            usage.validate()
            dest = measured if a["basis"] == "adapter_reported" else conservative
            need(
                a["basis"] in ("adapter_reported", "conservative_quote"),
                "Unknown native accounting basis",
            )
            for key, value in encode(usage).items():
                dest[key] += value
        if not dispatch:
            continue
        attempts += 1
        names = [
            n
            for n in ("raw-response.bin", "native-failure-wrapper.json")
            if (path / n).is_file()
        ]
        if not names:
            continue
        try:
            with (path / names[0]).open("rb") as stream:
                raw = stream.read(1048577)
            need(len(raw) <= 1048576, "Native accounting wrapper exceeds bound")
            wrapper = parse_json(raw)
            request = parse_json((path / "request.json").read_bytes())
            payload = parse_json((path / "payload.json").read_bytes())
            need(
                context is not None
                and wrapper["kind"] == PROTOCOL
                and wrapper["request_sha256"]
                == fingerprint(request)
                == dispatch[0]["details"]["request_sha256"]
                and wrapper["payload_sha256"]
                == fingerprint(payload)
                == dispatch[0]["details"]["payload_sha256"]
                and wrapper["owner_pid"] == context["owner_pid"]
                and wrapper["endpoint"] == context["endpoint"],
                "Accounting wrapper belongs to another request/owner",
            )
            status = wrapper.get("http_status")
            if type(status) is int and 100 <= status <= 599:
                known_http += 1
            if status != 200:
                continue
            decoded = base64.b64decode(wrapper["body_base64"], validate=True)
            need(
                len(decoded) <= 524288
                and hashlib.sha256(decoded).hexdigest() == wrapper["body_sha256"],
                "Native accounting body differs",
            )
            body = parse_json(decoded)
            usage = Usage(
                body.get("tokens_evaluated"), body.get("tokens_predicted"), 0.0
            )
            usage.validate()
            need(
                body.get("model") == context["model_alias"]
                and body.get("prompt") == payload["prompt"]
                and isinstance(body.get("generation_settings"), dict)
                and canonical(
                    {
                        k: body["generation_settings"][k]
                        for k in ("seed", "temperature", "n_predict", "stop", "stream")
                    }
                )
                == canonical(
                    {
                        k: payload[k]
                        for k in ("seed", "temperature", "n_predict", "stop", "stream")
                    }
                ),
                "Native accounting echoed model/settings differ",
            )
            known_model += 1
            if not accounts or accounts[0]["basis"] != "adapter_reported":
                # A complete retained body can preserve reported usage even when
                # transport cleanup raised before GeneratedBytes was returned.
                # Keep the conservative journal reservation rather than rewriting it.
                for key, value in encode(usage).items():
                    recovered[key] += value
                    measured[key] += value
        except (ContractError, ValueError, TypeError, KeyError, OSError):
            pass
    simulated = scope == "simulated_native_transport"
    zero = dict(input_tokens=0, output_tokens=0, cost_usd=0.0)
    return dict(
        native_dispatch_attempts=attempts,
        known_http_attempts=0 if simulated else known_http,
        unknown_http_attempts=0 if simulated else attempts - known_http,
        known_model_calls=0 if simulated else known_model,
        unknown_model_calls=0 if simulated else attempts - known_model,
        known_simulated_model_calls=known_model if simulated else 0,
        unknown_simulated_model_calls=attempts - known_model if simulated else 0,
        known_simulated_http_attempts=known_http if simulated else 0,
        actual_model_calls=0
        if simulated
        else (known_model if known_model == attempts else None),
        observed_model_usage=zero if simulated else measured,
        simulated_transport_usage=measured if simulated else zero,
        conservative_unresolved_usage=conservative,
        recovered_transport_usage=recovered,
    )
