"""Independent native-boundary regressions: fake HTTP only, no inference/network."""

import base64
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from asof.agents import Usage
from asof.serde import ContractError, canonical, encode, parse_json
from asof.study import native
from asof.study.diagnostic import REQUIRED_RESOURCES
from asof.study.session import StudySession, inspect_study
from tests import test_study_native as native_tests
from tests.test_study_native import Response


class NativePeerTests(unittest.TestCase):
    # Reuse only fake setup/helpers, not the other author's test methods.
    setUp = native_tests.NativeStudyTests.setUp
    backend = native_tests.NativeStudyTests.backend
    generated = native_tests.NativeStudyTests.generated
    configuration = native_tests.NativeStudyTests.configuration

    def bind_owner(self):
        self.owner.spec = SimpleNamespace(host="127.0.0.1", port=55581)

    def test_endpoint_must_match_the_actual_owned_server(self):
        self.bind_owner()
        with self.assertRaises(ContractError):
            self.backend(endpoint="http://127.0.0.1:55582")
        self.factory.assert_not_called()

    def test_owner_endpoint_change_before_dispatch_is_rejected(self):
        self.bind_owner()
        backend = self.backend()
        self.owner.spec = SimpleNamespace(host="127.0.0.1", port=55582)
        with self.assertRaises(ContractError):
            backend.generate(self.request, self.payload, timeout_seconds=10)
        self.connection.request.assert_not_called()

    def test_health_cleanup_preserves_primary_interruption(self):
        primary = KeyboardInterrupt("health header interrupted")
        self.connection.getresponse.side_effect = primary
        self.connection.close.side_effect = OSError("health close failed")
        with self.assertRaises(KeyboardInterrupt) as caught:
            native.bounded_health_probe("127.0.0.1", 55581, 1)
        self.assertIs(caught.exception, primary)
        self.connection.close.assert_called_once()
        self.assertTrue(primary.__notes__)

    def test_health_response_close_failure_still_closes_connection(self):
        response = Response(b"")
        response.close = Mock(side_effect=OSError("health response close failed"))
        self.connection.getresponse.return_value = response
        with self.assertRaises(OSError):
            native.bounded_health_probe("127.0.0.1", 55581, 1)
        self.connection.close.assert_called_once()

    def test_total_deadline_includes_response_headers(self):
        self.bind_owner()
        clock = [0.0]
        response = Response(canonical(self.native))
        response.read1 = Mock(wraps=response.read1)

        def slow_headers():
            clock[0] = 2.0
            return response

        self.connection.getresponse.side_effect = slow_headers
        with patch.object(native.time, "monotonic", side_effect=lambda: clock[0]):
            with self.assertRaises(TimeoutError):
                self.backend().generate(self.request, self.payload, timeout_seconds=1)
        response.read1.assert_not_called()
        wrapper = parse_json(
            (self.directory / "native-failure-wrapper.json").read_bytes()
        )
        self.assertFalse(wrapper["complete"])
        self.assertEqual(wrapper["error_class"], "TimeoutError")
        self.connection.request.assert_called_once()

    def test_watchdog_targets_only_retained_transport_socket(self):
        transport = Mock()
        with patch.object(native, "_remaining", return_value=0.25):
            native._watchdog(transport, 123)
        interval, expire = self.timer.call_args.args
        self.assertEqual(interval, 0.25)
        expire()
        transport.shutdown.assert_called_once_with(native.socket.SHUT_RDWR)
        transport.close.assert_called_once()
        self.connection.close.assert_not_called()

    def test_wrapper_type_and_completion_inconsistencies_are_rejected(self):
        self.bind_owner()
        _, result = self.generated()
        verifier = native.NativeVerifier("simplified", "test-alias")
        for changes in (
            {"schema_version": True},
            {"http_status": True},
            {"complete": 1},
            {"error_class": "TimeoutError"},
            {"elapsed_seconds": True},
            {"body_base64": base64.b64encode(b"different original bytes").decode()},
            {"body_base64": "not valid base64!"},
            {"owner_pid": 0},
        ):
            wrapper = parse_json(result.content)
            wrapper.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                verifier.validate_response(self.request, canonical(wrapper))

    def test_offline_verification_uses_explicit_verifier_not_backend_id(self):
        self.bind_owner()
        backend, result = self.generated()
        self.factory.reset_mock()
        config = self.configuration(backend)
        config["backend_id"] = "different-metadata-label-same-explicit-native-contract"
        verifier = native.NativeVerifier("simplified", "test-alias")
        verifier.verify_execution(
            self.request, self.payload, result.content, config, result.usage
        )
        self.factory.assert_not_called()

    def test_full_session_keeps_known_usage_when_native_content_is_invalid(self):
        self.bind_owner()
        self.native["content"] = "not valid answer JSON"
        self.connection.getresponse.return_value = Response(canonical(self.native))
        resources = {name: "study/" + name for name in REQUIRED_RESOURCES}
        cell = StudySession(
            self.directory / "cell",
            resources=resources,
            required_resources=REQUIRED_RESOURCES,
        )
        backend = self.backend(failure_directory=cell.output)
        with self.assertRaises(ContractError):
            with cell:
                cell.call_once(
                    request=self.request,
                    payload=self.payload,
                    backend=backend,
                    verifier=native.NativeVerifier("simplified", "test-alias"),
                )
        inspected = inspect_study(cell.output)
        self.assertEqual(inspected["calls"], 1)
        self.assertEqual(inspected["measured_usage"], encode(Usage(100, 20, 0.0)))
        self.assertEqual(inspected["estimated_usage"], encode(Usage(0, 0, 0.0)))
        self.assertFalse((cell.output / "receipt.json").exists())
        self.assertTrue((cell.output / "raw-response.bin").is_file())
        self.connection.request.assert_called_once()

    def test_failure_capture_and_transport_close_do_not_mask_original(self):
        self.bind_owner()
        primary = KeyboardInterrupt("original interrupted header")
        self.connection.getresponse.side_effect = primary
        self.connection.close.side_effect = OSError("close storage failed")
        with patch.object(
            native, "publish_bytes", side_effect=PermissionError("capture denied")
        ):
            with self.assertRaises(KeyboardInterrupt) as caught:
                self.backend().generate(self.request, self.payload, timeout_seconds=10)
        self.assertIs(caught.exception, primary)
        self.assertEqual(sum("capture failed" in note for note in primary.__notes__), 2)
        self.assertTrue(
            any("transport close failed" in note for note in primary.__notes__)
        )
        self.connection.request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
