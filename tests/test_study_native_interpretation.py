"""Regression-first native v2 adapter; fake HTTP only, never a model/server."""

import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock, patch

from tether_engine.agents import Usage
from tether_engine.serde import ContractError, canonical, encode, fingerprint, parse_json
from tether_engine.study import native
from tether_engine.study import tokenization as tok
from tether_engine.study.diagnostic_codec import bind_question
from tether_engine.study.diagnostic import load_synthetic_request
from tether_engine.study.interpretation_interface import prepare_payload
from tether_engine.study.native_interpretation import (
    TokenQuotedNativeBackend,
    verify_native_duration,
    validate_native_response,
    verify_native_execution,
)
from tether_engine.study.session import StudySession, _identity, verify_study
from tether_engine.study.token_capacity import TrustedTokenCapacity
from tether_engine.workflow import Budget
from tests import test_study_native as transport
from tests import test_study_tokenization as tokens


class NativeV2Verifier:
    from tether_engine.study.interpretation_interface import (
        REQUIRED_RESOURCES as required_resources,
    )

    def __init__(self, case):
        self.case = case

    def validate_payload(self, request, payload):
        if fingerprint(request) != fingerprint(self.case.request) or fingerprint(
            payload
        ) != fingerprint(self.case.payload):
            raise ContractError("Wrong test fixture binding")

    def validate_response(self, request, content):
        return validate_native_response(
            request, self.case.payload, content, model_alias="test-alias"
        )

    def verify_execution(self, request, payload, content, configuration, usage):
        verify_native_execution(
            request,
            payload,
            content,
            configuration,
            usage,
            capacity_policy=self.case.policy,
            case_deadline=self.case.deadline,
            expected_native=self.case.expected,
        )


class NativeDurationContractTests(unittest.TestCase):
    def setUp(self):
        self.configuration = dict(budget=encode(Budget(max_seconds=1.0)))

    def test_report_equality_zero_and_rounding_tolerance_are_valid(self):
        for elapsed, reported in ((0.0, 0.0), (0.5, 0.5), (0.5, 0.5 - 0.5e-6)):
            with self.subTest(elapsed=elapsed, reported=reported):
                verify_native_duration(
                    dict(elapsed_seconds=elapsed),
                    self.configuration,
                    report=dict(elapsed_seconds=reported),
                )

    def test_report_gap_above_absolute_tolerance_is_rejected(self):
        with self.assertRaisesRegex(
            ContractError, "Native duration exceeds child report"
        ):
            verify_native_duration(
                dict(elapsed_seconds=0.5),
                self.configuration,
                report=dict(elapsed_seconds=0.5 - 2e-6),
            )

    def test_supplied_missing_malformed_or_expired_report_is_rejected(self):
        reports = [
            None,
            {},
            [],
            *(
                dict(elapsed_seconds=v)
                for v in (None, True, "0", float("nan"), float("inf"), -1, 1.0, 2.0)
            ),
        ]
        for report in reports:
            with self.subTest(report=report):
                with self.assertRaises(ContractError):
                    verify_native_duration(
                        dict(elapsed_seconds=0.0), self.configuration, report=report
                    )

    def test_missing_or_malformed_wrapper_duration_is_rejected(self):
        wrappers = [
            None,
            {},
            [],
            *(
                dict(elapsed_seconds=v)
                for v in (None, True, "0", float("nan"), float("inf"), -1)
            ),
        ]
        for wrapper in wrappers:
            with self.subTest(wrapper=wrapper):
                with self.assertRaises(ContractError):
                    verify_native_duration(wrapper, self.configuration)

    def test_missing_or_malformed_configuration_is_rejected(self):
        for configuration in (
            None,
            {},
            [],
            dict(budget=None),
            dict(budget={"max_seconds": 1.0}),
        ):
            with self.subTest(configuration=configuration):
                with self.assertRaises(ContractError):
                    verify_native_duration(dict(elapsed_seconds=0.0), configuration)

    def test_report_tolerance_does_not_scale_with_duration(self):
        configuration = dict(budget=encode(Budget(max_seconds=300)))
        verify_native_duration(
            dict(elapsed_seconds=299.9),
            configuration,
            report=dict(elapsed_seconds=299.9),
        )
        with self.assertRaisesRegex(
            ContractError, "Native duration exceeds child report"
        ):
            verify_native_duration(
                dict(elapsed_seconds=299.9),
                configuration,
                report=dict(elapsed_seconds=299.9 - 2e-6),
            )
        with self.assertRaisesRegex(ContractError, "Native duration"):
            verify_native_duration(
                dict(elapsed_seconds=300),
                configuration,
                report=dict(elapsed_seconds=299.9999995),
            )


class NativeInterpretationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tokens.TokenizationArtifactTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        tokens.TokenizationArtifactTests.tearDownClass()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=tokens.TEMP_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture = SimpleNamespace()
        self.fixture.request = load_synthetic_request("synthetic-orientation")
        self.fixture.owner = Mock()
        self.fixture.owner.assert_ready = Mock()
        self.fixture.owner.spec = SimpleNamespace(host="127.0.0.1", port=55581)
        self.fixture.owner.terminal_record = {"pid": 4567}
        self.fixture.model = dict(
            weights_sha256={"weights.gguf": "a" * 64}, runtime_sha256="b" * 64
        )
        self.fixture.native = dict(
            model="test-alias",
            truncated=False,
            stop=True,
            stop_type="eos",
            stopped_limit=False,
            stopping_word="",
        )
        self.fixture.connection = Mock()
        self.fixture.connection.sock = Mock()
        factory = patch.object(
            native.http.client, "HTTPConnection", return_value=self.fixture.connection
        )
        self.fixture.factory = factory.start()
        self.addCleanup(factory.stop)
        timer = patch.object(native, "Timer")
        timer.start()
        self.addCleanup(timer.stop)
        original = self.fixture.request
        self.request = dict(
            original_request=encode(original), cell=0, kind="invented_native_test_stage"
        )
        self.payload = prepare_payload(original, "tether_interpretation", 0, [])[
            "payload"
        ]
        spec = tokens.TokenizationArtifactTests.spec
        real_run = tok._run_child
        with patch.object(
            tok,
            "_run_child",
            side_effect=lambda *a: real_run(*a, process_factory=tokens.FakeChild),
        ):
            quoted = tok.tokenize_prompt(
                self.payload["prompt"],
                spec,
                time.monotonic() + 60,
                self.root / "quote",
                payload_sha256=fingerprint(self.payload),
            )
        self.policy = TrustedTokenCapacity(
            self.root / "quote",
            quoted["receipt_sha256"],
            hashlib.sha256(self.payload["prompt"].encode()).hexdigest(),
            fingerprint(spec),
            fingerprint(self.payload),
        )
        self.deadline = time.monotonic() + 60
        self.model = dict(
            self.fixture.model,
            weights_sha256={
                Path(a["relative_path"]).name: a["sha256"]
                for a in spec["assets"]
                if a["relative_path"].endswith(".gguf")
            },
        )
        self.expected = dict(
            endpoint="http://127.0.0.1:55581",
            owner_pid=4567,
            model_alias="test-alias",
            model_provenance=self.model,
        )
        self.document = dict(
            answer_status="abstained",
            claims=[],
            unresolved=[],
            abstention_reason="Invented context only.",
        )
        self.body = dict(
            self.fixture.native,
            prompt=self.payload["prompt"],
            content=canonical(self.document).decode(),
            generation_settings={
                k: encode(self.payload[k])
                for k in ("seed", "temperature", "n_predict", "stop", "stream")
            },
            tokens_evaluated=20,
            tokens_predicted=5,
        )
        self.fixture.connection.getresponse.return_value = transport.Response(
            canonical(self.body)
        )

    def backend(self, **changes):
        args = dict(
            endpoint=self.expected["endpoint"],
            model_alias="test-alias",
            model_provenance=self.model,
            owner=self.fixture.owner,
            failure_directory=self.root,
            request=self.request,
            payload=self.payload,
            capacity_policy=self.policy,
            case_deadline=self.deadline,
        )
        args.update(changes)
        return TokenQuotedNativeBackend(**args)

    def configuration(self, backend):
        quote = backend.quote(self.request, self.payload)
        binding = self.policy.verify(
            self.request,
            self.payload,
            backend.capabilities,
            quote,
            Budget(),
            deadline=self.deadline,
        )
        return dict(
            schema_version=2,
            backend_id=backend.backend_id,
            adapter_code=_identity(TokenQuotedNativeBackend),
            adapter_provenance=encode(backend.provenance),
            backend_capabilities=encode(backend.capabilities),
            capacity_policy=encode(self.policy.describe()),
            capacity_binding=encode(binding),
            budget=encode(Budget()),
        )

    def verify_duration_fixture(self, result, config, elapsed):
        wrapper = parse_json(result.content)
        wrapper["elapsed_seconds"] = elapsed
        # Nonfinite cases must reach the parser, which rejects them; canonical()
        # itself intentionally refuses to encode such malformed evidence.
        raw = json.dumps(wrapper, allow_nan=True).encode()
        return verify_native_execution(
            self.request,
            self.payload,
            raw,
            config,
            result.usage,
            capacity_policy=self.policy,
            case_deadline=self.deadline,
            expected_native=self.expected,
        )

    def test_native_duration_exceeding_budget_rejected(self):
        backend = self.backend()
        config = self.configuration(backend)
        result = backend.generate(self.request, self.payload, timeout_seconds=20)
        with self.assertRaisesRegex(ContractError, "Native duration"):
            self.verify_duration_fixture(result, config, 9999.0)

    def test_native_duration_equal_to_budget_rejected(self):
        backend = self.backend()
        config = self.configuration(backend)
        config["budget"]["max_seconds"] = 1.0
        result = backend.generate(self.request, self.payload, timeout_seconds=20)
        with self.assertRaisesRegex(ContractError, "Native duration"):
            self.verify_duration_fixture(result, config, 1.0)

    def test_native_duration_zero_and_inside_budget_accepted(self):
        backend = self.backend()
        config = self.configuration(backend)
        config["budget"]["max_seconds"] = 1.0
        result = backend.generate(self.request, self.payload, timeout_seconds=20)
        for elapsed in (0, 0.0, 0.5):
            with self.subTest(elapsed=elapsed):
                self.verify_duration_fixture(result, config, elapsed)

    def test_native_duration_requires_complete_budget(self):
        backend = self.backend()
        config = self.configuration(backend)
        result = backend.generate(self.request, self.payload, timeout_seconds=20)
        alternatives = [None, {}, {"max_seconds": 1.0}, dict(config["budget"], extra=1)]
        missing = dict(config)
        del missing["budget"]
        for changed in [
            missing,
            *(dict(config, budget=value) for value in alternatives),
        ]:
            with self.subTest(budget=changed.get("budget")):
                with self.assertRaises(ContractError):
                    self.verify_duration_fixture(result, changed, 0.0)

    def test_native_duration_rejects_malformed_budget_bounds(self):
        backend = self.backend()
        config = self.configuration(backend)
        result = backend.generate(self.request, self.payload, timeout_seconds=20)
        alternatives = [
            dict(config["budget"], max_seconds=value)
            for value in (None, True, "1", float("nan"), float("inf"), 0, -1)
        ]
        alternatives += [
            dict(config["budget"], max_calls=True),
            dict(config["budget"], max_cost_usd=-1),
        ]
        for budget in alternatives:
            with self.subTest(budget=budget):
                with self.assertRaises(ContractError):
                    self.verify_duration_fixture(
                        result, dict(config, budget=budget), 0.0
                    )

    def test_native_duration_rejects_invalid_duration_types(self):
        backend = self.backend()
        config = self.configuration(backend)
        result = backend.generate(self.request, self.payload, timeout_seconds=20)
        for elapsed in (None, True, "0", float("nan"), float("inf"), -1):
            with self.subTest(elapsed=elapsed):
                with self.assertRaises(ContractError):
                    self.verify_duration_fixture(result, config, elapsed)

    def test_success_reuses_transport_and_binds_native_bytes_and_usage(self):
        backend = self.backend()
        config = self.configuration(backend)
        result = backend.generate(self.request, self.payload, timeout_seconds=20)
        self.assertEqual(result.usage, Usage(20, 5, 0))
        response = validate_native_response(
            self.request, self.payload, result.content, model_alias="test-alias"
        )
        self.assertEqual(response["response"]["answer_status"], "abstained")
        self.assertEqual(response["features"], {})
        verify_native_execution(
            self.request,
            self.payload,
            result.content,
            config,
            result.usage,
            capacity_policy=self.policy,
            case_deadline=self.deadline,
            expected_native=self.expected,
        )
        self.fixture.connection.request.assert_called_once()

    def test_wrong_payload_and_stage_are_rejected_before_http(self):
        bad = encode(self.payload)
        bad["seed"] = 99
        with self.assertRaises(ContractError):
            self.backend(payload=bad)
        backend = self.backend()
        with self.assertRaises(ContractError):
            backend.generate(
                dict(self.request, cell=1), self.payload, timeout_seconds=20
            )
        self.fixture.factory.assert_not_called()

    def test_wrong_token_model_is_rejected_before_http(self):
        model = dict(self.model, weights_sha256={"other.gguf": "a" * 64})
        backend = self.backend(model_provenance=model)
        with self.assertRaises(ContractError):
            backend.generate(self.request, self.payload, timeout_seconds=20)
        self.fixture.factory.assert_not_called()

    def test_expired_parent_and_invalid_owner_have_zero_http_calls(self):
        with self.assertRaises(TimeoutError):
            self.backend(case_deadline=time.monotonic() - 1)
        self.fixture.owner.assert_ready.side_effect = ContractError("Owner lost")
        with self.assertRaises(ContractError):
            self.backend()
        self.fixture.factory.assert_not_called()

    def test_quote_work_cannot_reset_caller_deadline(self):
        backend = self.backend()
        now = [time.monotonic()]
        original = backend.quote

        def slow(request, payload):
            result = original(request, payload)
            now[0] += 0.75
            return result

        with (
            patch.object(time, "monotonic", side_effect=lambda: now[0]),
            patch.object(backend, "quote", side_effect=slow),
        ):
            backend.generate(self.request, self.payload, timeout_seconds=1)
        self.assertLessEqual(self.fixture.factory.call_args.kwargs["timeout"], 0.251)

    def test_quote_exhaustion_has_zero_http_and_no_second_attempt(self):
        backend = self.backend()
        now = [time.monotonic()]
        original = self.policy.reservation

        def slow(*args, **kwargs):
            result = original(*args, **kwargs)
            now[0] += 2
            return result

        with (
            patch.object(time, "monotonic", side_effect=lambda: now[0]),
            patch.object(TrustedTokenCapacity, "reservation", side_effect=slow),
        ):
            with self.assertRaises(TimeoutError):
                backend.generate(self.request, self.payload, timeout_seconds=1)
        self.fixture.factory.assert_not_called()
        with self.assertRaises(ContractError):
            backend.generate(self.request, self.payload, timeout_seconds=20)

    def test_concurrent_generate_is_consumed_once(self):
        backend = self.backend()

        def call():
            try:
                return backend.generate(self.request, self.payload, timeout_seconds=20)
            except ContractError:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: call(), range(2)))
        self.assertEqual(sum(r is not None for r in results), 1)
        self.fixture.connection.request.assert_called_once()

    def test_native_model_echo_and_semantic_state_cannot_be_repaired(self):
        for change in (
            dict(model="other"),
            dict(
                content=canonical(
                    dict(self.document, answer_status="answered")
                ).decode()
            ),
        ):
            self.fixture.connection.getresponse.return_value = transport.Response(
                canonical(dict(self.body, **change))
            )
            result = self.backend().generate(
                self.request, self.payload, timeout_seconds=20
            )
            self.assertEqual(result.usage, Usage(20, 5, 0))
            with self.assertRaises(ContractError):
                validate_native_response(
                    self.request, self.payload, result.content, model_alias="test-alias"
                )

    def test_configuration_downgrade_and_wrong_provenance_rejected(self):
        backend = self.backend()
        config = self.configuration(backend)
        result = backend.generate(self.request, self.payload, timeout_seconds=20)
        for change in (
            dict(schema_version=1),
            dict(adapter_code=_identity(native.LocalBackend)),
            dict(adapter_provenance={}),
        ):
            with self.assertRaises(ContractError):
                verify_native_execution(
                    self.request,
                    self.payload,
                    result.content,
                    dict(config, **change),
                    result.usage,
                    capacity_policy=self.policy,
                    case_deadline=self.deadline,
                    expected_native=self.expected,
                )

    def test_partial_transport_bytes_and_interruption_are_retained(self):
        self.fixture.connection.getresponse.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.backend().generate(self.request, self.payload, timeout_seconds=20)
        wrapper = parse_json((self.root / "native-failure-wrapper.json").read_bytes())
        self.assertEqual(wrapper["error_class"], "KeyboardInterrupt")
        self.assertFalse(wrapper["complete"])

    def test_study_session_accounting_and_readonly_replay(self):
        backend = self.backend()
        verifier = NativeV2Verifier(self)
        resources = {n: "study/" + n for n in verifier.required_resources}
        with StudySession(
            self.root / "cell",
            resources=resources,
            required_resources=verifier.required_resources,
            capacity_policy=self.policy,
        ) as session:
            session.call_once(
                request=self.request,
                payload=self.payload,
                backend=backend,
                verifier=verifier,
            )
            session.finish()
        anchor = hashlib.sha256(
            (session.output / "receipt.json").read_bytes()
        ).hexdigest()
        with patch.object(
            native.http.client,
            "HTTPConnection",
            side_effect=AssertionError("Replay cannot connect"),
        ):
            result = verify_study(
                session.output,
                expected_receipt_sha256=anchor,
                verifier=verifier,
                capacity_policy=self.policy,
                deadline=time.monotonic() + 60,
            )
        self.assertEqual(result["status"], "verified_study_cell")

    def test_over_quote_usage_is_retained_as_failure(self):
        body = dict(self.body, tokens_evaluated=999)
        self.fixture.connection.getresponse.return_value = transport.Response(
            canonical(body)
        )
        verifier = NativeV2Verifier(self)
        resources = {n: "study/" + n for n in verifier.required_resources}
        with (
            self.assertRaises(ContractError),
            StudySession(
                self.root / "over",
                resources=resources,
                required_resources=verifier.required_resources,
                capacity_policy=self.policy,
            ) as session,
        ):
            session.call_once(
                request=self.request,
                payload=self.payload,
                backend=self.backend(),
                verifier=verifier,
            )
        self.assertTrue((session.output / "raw-response.bin").is_file())
        self.assertFalse((session.output / "receipt.json").exists())

    def test_no_quotable_strings_fail_before_schema_or_dispatch(self):
        request = encode(self.request["original_request"])
        for row in request["source_request"]["evidence"]:
            row["statement"] = row["scientific_record"]["statement"] = ""
            row["scientific_record"]["source_metrics"] = {}
        request = bind_question(
            request["source_request"], request["question"]["question_id"]
        )
        with self.assertRaisesRegex(ContractError, "quotable"):
            prepare_payload(request, "tether_interpretation", 0, [])


if __name__ == "__main__":
    unittest.main()
