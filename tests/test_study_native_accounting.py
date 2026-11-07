"""Journal/wrapper reconciliation; fixture bytes never represent a real call."""

import base64
import hashlib
from pathlib import Path
import tempfile
import unittest
from contextlib import closing

from tether_engine.journal import RunJournal
from tether_engine.serde import canonical, fingerprint
from tether_engine.study.native_accounting import accounting
from tether_engine.study.native import PROTOCOL


class NativeAccountingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(
            dir=Path(__file__).resolve().parents[1] / "data/cache"
        )
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "run"
        self.context = dict(
            endpoint="http://127.0.0.1:55581",
            owner_pid=4242,
            model_alias="fixture",
            model_provenance={},
        )
        with closing(RunJournal(self.root, kind="build")) as journal:
            journal.append("native_context_qualified", context=self.context)
        self.path = self.root / "cells/00"
        self.path.parent.mkdir()
        self.request = dict(fixture="only")
        self.payload = dict(
            prompt="invented prompt",
            seed=42,
            temperature=0,
            n_predict=1024,
            stop=["end"],
            stream=False,
        )
        with closing(RunJournal(self.path, kind="build")) as journal:
            journal.append(
                "study_dispatch",
                request_sha256=fingerprint(self.request),
                payload_sha256=fingerprint(self.payload),
            )
            journal.append(
                "study_accounted",
                usage=dict(input_tokens=20, output_tokens=5, cost_usd=0.0),
                basis="adapter_reported",
            )
        (self.path / "request.json").write_bytes(canonical(self.request))
        (self.path / "payload.json").write_bytes(canonical(self.payload))
        self.body = dict(
            prompt=self.payload["prompt"],
            model="fixture",
            generation_settings={
                k: self.payload[k]
                for k in ("seed", "temperature", "n_predict", "stop", "stream")
            },
            tokens_evaluated=20,
            tokens_predicted=5,
        )
        self.wrapper = dict(
            kind=PROTOCOL,
            http_status=200,
            owner_pid=4242,
            endpoint=self.context["endpoint"],
            request_sha256=fingerprint(self.request),
            payload_sha256=fingerprint(self.payload),
        )

    def write(self, body=None, **changes):
        raw = canonical(body or self.body)
        wrapper = dict(
            self.wrapper,
            body_base64=base64.b64encode(raw).decode(),
            body_sha256=hashlib.sha256(raw).hexdigest(),
            **changes,
        )
        (self.path / "raw-response.bin").write_bytes(canonical(wrapper))

    def test_measured_usage_and_bound_model_count(self):
        self.write()
        result = accounting(self.root, "owned_native")
        self.assertEqual(result["actual_model_calls"], 1)
        self.assertEqual(result["observed_model_usage"]["input_tokens"], 20)

    def test_foreign_request_owner_and_prompt_cannot_be_counted_known(self):
        for change in (
            dict(request_sha256="a" * 64),
            dict(owner_pid=999),
            dict(endpoint="http://127.0.0.1:55582"),
        ):
            self.write(**change)
            result = accounting(self.root, "owned_native")
            self.assertIsNone(result["actual_model_calls"])
            self.assertEqual(result["unknown_model_calls"], 1)
        self.write(body=dict(self.body, prompt="foreign"))
        self.assertIsNone(accounting(self.root, "owned_native")["actual_model_calls"])

    def test_wrong_echoed_model_or_settings_are_unknown(self):
        for body in (
            dict(self.body, model="foreign"),
            dict(self.body, generation_settings={}),
        ):
            self.write(body=body)
            self.assertIsNone(
                accounting(self.root, "owned_native")["actual_model_calls"]
            )

    def test_simulated_transport_never_claims_model_or_network_usage(self):
        self.write()
        result = accounting(self.root, "simulated_native_transport")
        self.assertEqual(result["actual_model_calls"], 0)
        self.assertEqual(result["known_model_calls"], 0)
        self.assertEqual(result["known_http_attempts"], 0)
        self.assertEqual(result["known_simulated_model_calls"], 1)
        self.assertEqual(result["simulated_transport_usage"]["input_tokens"], 20)

    def test_missing_wrapper_is_unknown_not_zero(self):
        result = accounting(self.root, "owned_native")
        self.assertIsNone(result["actual_model_calls"])
        self.assertEqual(result["unknown_http_attempts"], 1)


if __name__ == "__main__":
    unittest.main()
