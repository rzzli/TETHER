"""Native transport/replay tests use fake sockets and HTTP only, never a server."""

import base64
import hashlib
import http.client
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from asof.agents import Usage
from asof.serde import ContractError, canonical, encode, parse_json
from asof.study import native
from asof.study.diagnostic import load_synthetic_request, prepare_payload
from asof.study.session import _identity


class Response:
    def __init__(self, body, status=200):
        self.body = body
        self.status = status
        self.length = len(body)
        self.closed = False

    def read1(self, count):
        chunk = self.body[:count]
        self.body = self.body[count:]
        self.length -= len(chunk)
        return chunk

    def close(self):
        self.closed = True


class NativeStudyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.request = load_synthetic_request("synthetic-orientation")
        self.payload = prepare_payload(self.request, "simplified")
        self.owner = Mock()
        self.owner.assert_ready = Mock()
        self.owner.spec = SimpleNamespace(host="127.0.0.1", port=55581)
        self.owner.terminal_record = {"pid": 4567}
        self.model = {
            "weights_sha256": {"weights.gguf": "a" * 64},
            "runtime_sha256": "b" * 64,
        }
        self.document = dict(
            answer_status="abstained",
            claims=[],
            unresolved=[],
            abstention_reason="No supported inference.",
        )
        self.native = dict(
            prompt=self.payload["prompt"],
            model="test-alias",
            generation_settings={
                k: encode(self.payload[k])
                for k in ("seed", "temperature", "n_predict", "stop", "stream")
            },
            truncated=False,
            stop=True,
            stop_type="eos",
            stopped_limit=False,
            stopping_word="",
            tokens_evaluated=100,
            tokens_predicted=20,
            content=json.dumps(self.document),
        )
        self.connection = Mock()
        self.connection.sock = Mock()
        self.connection.getresponse.return_value = Response(canonical(self.native))
        self.factory = patch.object(
            native.http.client, "HTTPConnection", return_value=self.connection
        ).start()
        self.addCleanup(patch.stopall)
        self.timer = patch.object(native, "Timer").start()

    def backend(self, **changes):
        kwargs = dict(
            endpoint="http://127.0.0.1:55581",
            interface="simplified",
            model_provenance=self.model,
            model_alias="test-alias",
            owner=self.owner,
            failure_directory=self.directory,
        )
        kwargs.update(changes)
        return native.LocalBackend(**kwargs)

    def generated(self, body=None, status=200):
        if body is not None:
            self.connection.getresponse.return_value = Response(body, status)
        backend = self.backend()
        return backend, backend.generate(self.request, self.payload, timeout_seconds=10)

    def configuration(self, backend):
        return dict(
            adapter_code=_identity(native.LocalBackend),
            adapter_provenance=encode(backend.provenance),
            backend_capabilities=encode(backend.capabilities),
        )

    def test_success_exact_original_body_and_strict_replay(self):
        backend, result = self.generated()
        self.assertEqual(result.usage, Usage(100, 20, 0))
        wrapper = parse_json(result.content)
        self.assertEqual(
            base64.b64decode(wrapper["body_base64"]), canonical(self.native)
        )
        self.assertTrue(wrapper["complete"])
        self.assertIsNone(wrapper["error_class"])
        self.connection.request.assert_called_once_with(
            "POST",
            "/completion",
            body=canonical(self.payload),
            headers={"Content-Type": "application/json"},
        )
        self.assertGreaterEqual(self.owner.assert_ready.call_count, 3)
        verifier = native.NativeVerifier("simplified", "test-alias")
        verifier.validate_payload(self.request, self.payload)
        response = verifier.validate_response(self.request, result.content)
        self.assertEqual(response["response"]["answer_status"], "abstained")
        verifier.verify_execution(
            self.request,
            self.payload,
            result.content,
            self.configuration(backend),
            result.usage,
        )
        self.connection.close.assert_called_once()
        self.timer.return_value.cancel.assert_called_once()
        with self.assertRaises(ContractError):
            backend.generate(self.request, self.payload, timeout_seconds=10)

    def test_owner_denial_and_endpoint_before_any_http(self):
        self.owner.assert_ready.side_effect = ContractError("not owned")
        with self.assertRaises(ContractError):
            self.backend()
        self.factory.assert_not_called()
        self.owner.assert_ready.side_effect = None
        for endpoint in (
            "https://127.0.0.1:55581",
            "http://localhost:55581",
            "http://user@127.0.0.1:55581",
            "http://127.0.0.1:55581/foreign",
        ):
            with self.assertRaises(ContractError):
                self.backend(endpoint=endpoint)
        self.factory.assert_not_called()

    def test_owner_loss_before_dispatch_never_posts(self):
        backend = self.backend()
        self.owner.assert_ready.side_effect = ContractError("owner lost")
        with self.assertRaises(ContractError):
            backend.generate(self.request, self.payload, timeout_seconds=10)
        self.factory.assert_not_called()
        self.assertTrue((self.directory / "native-failure-wrapper.json").is_file())

    def test_non200_never_redirects_or_accepts(self):
        _, result = self.generated(canonical(self.native), 302)
        self.connection.request.assert_called_once()
        with self.assertRaises(ContractError):
            native.NativeVerifier("simplified", "test-alias").validate_response(
                self.request, result.content
            )

    def test_complete_bad_content_retains_measured_usage(self):
        self.native["content"] = "not JSON"
        _, result = self.generated(canonical(self.native))
        self.assertEqual(result.usage, Usage(100, 20, 0))
        with self.assertRaises(ContractError):
            native.NativeVerifier("simplified", "test-alias").validate_response(
                self.request, result.content
            )

    def test_unknown_usage_is_not_fabricated(self):
        for invalid in (None, True, -1, 1.5):
            self.native["tokens_evaluated"] = invalid
            _, result = self.generated(canonical(self.native))
            self.assertIsNone(result.usage)

    def test_positive_completion_and_echo_settings_required(self):
        variants = [
            {"truncated": True},
            {"model": "foreign"},
            {"prompt": "foreign"},
            {"stop_type": "limit"},
            {"stopped_limit": True},
            {"stop": False},
            {"stopped_word": True},
            {"stopping_word": "foreign"},
            {
                "generation_settings": dict(
                    self.native["generation_settings"], seed=True
                )
            },
        ]
        for changes in variants:
            value = dict(self.native, **changes)
            _, result = self.generated(canonical(value))
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                native.NativeVerifier("simplified", "test-alias").validate_response(
                    self.request, result.content
                )
        value = dict(self.native)
        value.pop("stop_type")
        value.update(stopped_eos=False, stopped_word=False)
        _, result = self.generated(canonical(value))
        with self.assertRaises(ContractError):
            native.NativeVerifier("simplified", "test-alias").validate_response(
                self.request, result.content
            )
        value["stopped_eos"] = True
        _, result = self.generated(canonical(value))
        native.NativeVerifier("simplified", "test-alias").validate_response(
            self.request, result.content
        )

    def test_native_wrapper_tampering_and_usage_provenance_rejected(self):
        backend, result = self.generated()
        verifier = native.NativeVerifier("simplified", "test-alias")
        for field, value in [
            ("body_sha256", "0" * 64),
            ("complete", False),
            ("request_sha256", "0" * 64),
            ("owner_pid", True),
            ("elapsed_seconds", -1),
        ]:
            wrapper = parse_json(result.content)
            wrapper[field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                verifier.validate_response(self.request, canonical(wrapper))
        config = self.configuration(backend)
        config["adapter_provenance"]["owner_pid"] = 999
        with self.assertRaises(ContractError):
            verifier.verify_execution(
                self.request, self.payload, result.content, config, result.usage
            )
        with self.assertRaises(ContractError):
            verifier.verify_execution(
                self.request,
                self.payload,
                result.content,
                self.configuration(backend),
                Usage(0, 0, 0),
            )

    def test_interruption_preserves_partial_capture_and_original(self):
        primary = KeyboardInterrupt("original")
        response = Response(b"")
        response.read1 = Mock(side_effect=[b"partial", primary])
        response.length = None
        self.connection.getresponse.return_value = response
        self.connection.close.side_effect = OSError("close failed")
        self.timer.return_value.cancel.side_effect = OSError("timer cancel failed")
        with self.assertRaises(KeyboardInterrupt) as caught:
            self.backend().generate(self.request, self.payload, timeout_seconds=10)
        self.assertIs(caught.exception, primary)
        wrapper = parse_json(
            (self.directory / "native-failure-wrapper.json").read_bytes()
        )
        self.assertFalse(wrapper["complete"])
        self.assertEqual(wrapper["error_class"], "KeyboardInterrupt")
        self.assertEqual(
            (self.directory / "native-failure-body.bin").read_bytes(), b"partial"
        )
        self.assertTrue(primary.__notes__)

    def test_incomplete_content_length_fails_and_captures(self):
        response = Response(b"")
        response.length = 10
        self.connection.getresponse.return_value = response
        with self.assertRaises(http.client.IncompleteRead):
            self.backend().generate(self.request, self.payload, timeout_seconds=10)
        self.assertFalse(
            parse_json((self.directory / "native-failure-wrapper.json").read_bytes())[
                "complete"
            ]
        )

    def test_overflow_explicit_prefix_never_success(self):
        self.connection.getresponse.return_value = Response(
            b"x" * (native.MAX_ORIGINAL_RESPONSE + 1)
        )
        with self.assertRaises(ContractError):
            self.backend().generate(self.request, self.payload, timeout_seconds=10)
        body = (self.directory / "native-failure-body.bin").read_bytes()
        self.assertEqual(len(body), native.MAX_ORIGINAL_RESPONSE)
        wrapper = parse_json(
            (self.directory / "native-failure-wrapper.json").read_bytes()
        )
        self.assertFalse(wrapper["complete"])
        self.assertEqual(wrapper["body_sha256"], hashlib.sha256(body).hexdigest())

    def test_absolute_deadline_not_reset_by_reads(self):
        response = Response(b"body")
        original = response.read1
        clock = [0.0]

        def read(count):
            clock[0] += 0.6
            return original(1)

        response.read1 = read
        self.connection.getresponse.return_value = response
        with patch.object(native.time, "monotonic", side_effect=lambda: clock[0]):
            with self.assertRaises(TimeoutError):
                self.backend().generate(self.request, self.payload, timeout_seconds=1)
        self.assertLessEqual(response.length, 2)
        timeouts = [
            call.args[0] for call in self.connection.sock.settimeout.call_args_list
        ]
        self.assertLess(min(timeouts), max(timeouts))

    def test_connection_close_detachment_uses_actual_response_socket(self):
        transport = self.connection.sock
        response = Response(canonical(self.native))
        response.fp = SimpleNamespace(raw=SimpleNamespace(_sock=transport))

        def detached():
            self.connection.sock = None
            return response

        self.connection.getresponse.side_effect = detached
        _, result = self.generated()
        self.assertTrue(parse_json(result.content)["complete"])
        self.assertGreater(transport.settimeout.call_count, 2)

    def test_unknown_detached_socket_fails_closed(self):
        response = Response(canonical(self.native))
        response.fp = SimpleNamespace(raw=SimpleNamespace(_sock=Mock()))

        def detached():
            self.connection.sock = None
            return response

        self.connection.getresponse.side_effect = detached
        with self.assertRaises(ContractError):
            self.backend().generate(self.request, self.payload, timeout_seconds=10)
        self.assertEqual((self.directory / "native-failure-body.bin").read_bytes(), b"")

    def test_incomplete_read_exception_retains_unreturned_partial_bytes(self):
        response = Response(b"")
        response.length = None
        response.read1 = Mock(
            side_effect=[b"prefix", http.client.IncompleteRead(b"tail", 3)]
        )
        self.connection.getresponse.return_value = response
        with self.assertRaises(http.client.IncompleteRead):
            self.backend().generate(self.request, self.payload, timeout_seconds=10)
        self.assertEqual(
            (self.directory / "native-failure-body.bin").read_bytes(), b"prefixtail"
        )

    def test_mocked_windows_listener_query_exact_owner_and_denied_access(self):
        import ctypes
        from ctypes import wintypes
        import os
        import socket
        import struct

        rows = [
            (
                2,
                struct.unpack("<I", socket.inet_aton("127.0.0.1"))[0],
                socket.htons(55581),
                0,
                0,
                4567,
            )
        ]

        def table(buffer, size, *args):
            raw = struct.pack("<I", len(rows)) + b"".join(
                struct.pack("<6I", *row) for row in rows
            )
            ctypes.cast(size, ctypes.POINTER(wintypes.DWORD)).contents.value = len(raw)
            if buffer is None:
                return 122
            ctypes.memmove(buffer, raw, len(raw))
            return 0

        function = Mock(side_effect=table)
        with (
            patch.object(
                ctypes,
                "WinDLL",
                create=True,
                return_value=SimpleNamespace(GetExtendedTcpTable=function),
            ),
            patch.object(os, "name", "nt"),
        ):
            self.assertTrue(native.windows_listener_owner(4567, "127.0.0.1", 55581))
            self.assertFalse(native.windows_listener_owner(4568, "127.0.0.1", 55581))
            rows.append(rows[0])
            self.assertFalse(native.windows_listener_owner(4567, "127.0.0.1", 55581))
            rows.clear()
            self.assertFalse(native.windows_listener_owner(4567, "127.0.0.1", 55581))
            function.side_effect = lambda *args: 5
            with self.assertRaises(OSError):
                native.windows_listener_owner(4567, "127.0.0.1", 55581)

    def test_success_close_failure_is_retained_not_accepted(self):
        self.connection.close.side_effect = OSError("close failed")
        with self.assertRaises(OSError):
            self.backend().generate(self.request, self.payload, timeout_seconds=10)
        wrapper = parse_json(
            (self.directory / "native-failure-wrapper.json").read_bytes()
        )
        self.assertEqual(wrapper["error_class"], "OSError")
        self.assertEqual(
            base64.b64decode(wrapper["body_base64"]), canonical(self.native)
        )

    def test_failure_capture_write_error_never_replaces_primary(self):
        primary = TimeoutError("original timeout")
        self.connection.getresponse.side_effect = primary
        with patch.object(
            native, "publish_bytes", side_effect=OSError("storage failure")
        ):
            with self.assertRaises(TimeoutError) as caught:
                self.backend().generate(self.request, self.payload, timeout_seconds=10)
        self.assertIs(caught.exception, primary)
        self.assertEqual(len(primary.__notes__), 2)

    def test_health_is_bounded_get_only(self):
        self.connection.getresponse.return_value = Response(b"")
        self.assertTrue(native.bounded_health_probe("127.0.0.1", 55581, 1))
        self.connection.request.assert_called_once_with("GET", "/health")
        self.connection.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
