"""Finite ordinary-loopback transport controls; every opener is a local mock."""

import hashlib
import io
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from tether_engine.serde import ContractError, canonical, encode
from tether_engine.study.source_fact_transport import (
    TypedReportingClient,
    parse_netstat_listener,
    prepare_completion,
)


ENDPOINT = "http://127.0.0.1:55591"


def native(**updates):
    return dict(content='{"facts":[]}', tokens_evaluated=2,
                tokens_predicted=3, truncated=False, prompt="prompt", model="fictional-model",
                generation_settings=dict(seed=0, temperature=0.0, n_predict=2048,
                    stop=["<|im_end|>"], stream=False)) | updates


class Response(io.BytesIO):
    status = 200

    def geturl(self):
        return ENDPOINT + "/completion"


class Opener:
    def __init__(self, raw=None, error=None):
        self.raw = canonical(native()) if raw is None else raw
        self.error = error
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        if self.error is not None:
            raise self.error
        return Response(self.raw)


class NetstatListenerTests(unittest.TestCase):
    def test_single_canonical_owner_and_unrelated_connections(self):
        raw = (b"Active Connections\r\n Proto Local Address Foreign Address State PID\r\n"
               b" TCP 127.0.0.1:55591 0.0.0.0:0 LISTENING 1234\r\n"
               b" TCP 127.0.0.1:55591 127.0.0.1:9001 ESTABLISHED 999\r\n"
               b" TCP 0.0.0.0:80 0.0.0.0:0 LISTENING 7\r\n")
        self.assertEqual(parse_netstat_listener(raw, 55591), 1234)
        self.assertIsNone(parse_netstat_listener(raw, 55592))
        self.assertIsNone(parse_netstat_listener(b"", 55591))

    def test_duplicate_wildcard_ipv6_and_noncanonical_target_rows_rejected(self):
        row = b"TCP 127.0.0.1:55591 0.0.0.0:0 LISTENING 1234\n"
        for raw in (
            row + row,
            row + row.replace(b"1234", b"4321"),
            row.replace(b"127.0.0.1:55591", b"0.0.0.0:55591"),
            row.replace(b"127.0.0.1:55591", b"[::1]:55591"),
            row.replace(b"127.0.0.1:55591", b"[::]:55591"),
            row.replace(b"127.0.0.1:55591", b"127.000.0.1:55591"),
            row.replace(b":55591", b":055591"),
            row.replace(b"0.0.0.0:0", b"127.0.0.1:0"),
            row.replace(b"1234", b"0"), row.replace(b"1234", b"01234"),
            row.replace(b"1234", b"-1"), row.replace(b"1234", b"bad"),
            row.replace(b":55591", b":bad"),
            row.replace(b"TCP", b"UDP"), row + b"extra LISTENING\n",
            b"\xff",
        ):
            with self.subTest(raw=raw):
                with self.assertRaises(ContractError):
                    parse_netstat_listener(raw, 55591)

    def test_parser_configuration_and_capture_bounds(self):
        for port in (True, 0, -1, 65536, 55591.0, "55591"):
            with self.assertRaises(ContractError):
                parse_netstat_listener(b"", port)
        with self.assertRaises(ContractError):
            parse_netstat_listener("", 55591)
        with self.assertRaises(ContractError):
            parse_netstat_listener(b" " * (1024 * 1024 + 1), 55591)

    def test_unknown_target_state_cannot_hide_ambiguous_owner(self):
        row = b"TCP 127.0.0.1:55591 0.0.0.0:0 LISTENING 1234\n"
        for state in (b"UNKNOWN", "侦听".encode("utf-8"), b"LISTEN", b"listening"):
            with self.subTest(state=state):
                with self.assertRaises(ContractError):
                    parse_netstat_listener(row + row.replace(b"LISTENING", state), 55591)
                with self.assertRaises(ContractError):
                    parse_netstat_listener(row.replace(b"LISTENING", state), 55591)
        for state in (b"ESTABLISHED", b"TIME_WAIT", b"SYN_SENT", b"CLOSE_WAIT"):
            self.assertEqual(parse_netstat_listener(row + row.replace(b"LISTENING", state), 55591), 1234)


class CompletionPreparationTests(unittest.TestCase):
    def test_plain_payload_preserves_exact_utf8_and_has_no_native_constraints(self):
        prompt = " exact α😀 <|source|>\n"
        result = prepare_completion(prompt, 2048, 0)
        self.assertEqual(encode(result), dict(prompt=prompt, n_predict=2048,
            temperature=0.0, seed=0, cache_prompt=False, stream=False,
            stop=["<|im_end|>"]))
        self.assertNotIn("json_schema", result)
        self.assertNotIn("grammar", result)
        with self.assertRaises(TypeError):
            result["temperature"] = 1

    def test_complete_byte_reservation_and_strict_configuration(self):
        self.assertEqual(prepare_completion("x" * (16384 - 2048 - 32), 2048, 0)["n_predict"], 2048)
        for prompt, maximum, seed in (
            ("x" * (16384 - 2048 - 31), 2048, 0),
            ("😀" * 4000, 2048, 0), ("\ud800", 10, 0),
            (b"prompt", 10, 0), ("x", True, 0), ("x", 2049, 0),
            ("x", 0, 0), ("x", 10, True),
        ):
            with self.assertRaises(ContractError):
                prepare_completion(prompt, maximum, seed)


class TypedReportingTransportTests(unittest.TestCase):
    def client(self, opener=None, owner=None, retain=None):
        return TypedReportingClient(ENDPOINT, expected_pid=1234,
            ownership_check=(lambda pid, host, port: True) if owner is None else owner,
            opener=Opener() if opener is None else opener, retain=retain)

    def test_exact_request_response_content_and_usage_retention(self):
        raw = b" \n" + canonical(native(content=' {"facts":[]}\n', prompt="source prompt",
            generation_settings=dict(seed=0, temperature=0.0, n_predict=20,
                                     stop=["<|im_end|>"], stream=False)))
        opener = Opener(raw)
        events = []
        owners = []
        def own(pid, host, port):
            owners.append((pid, host, port))
            return True
        result = self.client(opener, own, events.append).execute("source prompt", maximum=20)
        self.assertEqual(result.status, "returned")
        self.assertTrue(result.dispatched)
        self.assertTrue(result.envelope_complete)
        self.assertEqual(result.raw_request, canonical(prepare_completion("source prompt", 20, 0)))
        self.assertEqual(result.raw_envelope, raw)
        self.assertEqual(result.content, b' {"facts":[]}\n')
        self.assertEqual(result.request_sha256, hashlib.sha256(result.raw_request).hexdigest())
        self.assertEqual(result.response_sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(result.content_sha256, hashlib.sha256(result.content).hexdigest())
        self.assertEqual(encode(result.measured_usage), dict(input_tokens=2, output_tokens=3, cost_usd=0.0))
        self.assertEqual(encode(result.estimated_usage), dict(input_tokens=45, output_tokens=20, cost_usd=0.0))
        self.assertEqual(owners, [(1234, "127.0.0.1", 55591)])
        self.assertEqual([e["event"] for e in events], ["attempt", "terminal"])
        self.assertFalse(events[0]["dispatched"])
        self.assertEqual(events[-1]["result"], result)
        req, timeout = opener.calls[0]
        self.assertEqual(req.full_url, ENDPOINT + "/completion")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.data, result.raw_request)
        self.assertEqual(timeout, 300)
        with self.assertRaises(TypeError):
            result.measured_usage["input_tokens"] = 999

    def test_ownership_denial_never_opens_and_consumes_one_attempt(self):
        for owner_result in (False, None, 1, "true"):
            opener = Opener()
            events = []
            client = self.client(opener, lambda *args: owner_result, events.append)
            result = client.execute("prompt")
            self.assertEqual(result.status, "failed")
            self.assertFalse(result.dispatched)
            self.assertIsNone(result.measured_usage)
            self.assertEqual(opener.calls, [])
            self.assertEqual(events[-1]["event"], "terminal")
            with self.assertRaises(ContractError):
                client.execute("prompt")
            self.assertEqual(opener.calls, [])

    def test_endpoint_validation_and_default_no_proxy_no_redirect_opener(self):
        for endpoint in ("https://127.0.0.1:55591", "http://localhost:55591",
                         "http://[::1]:55591", "http://127.0.0.1", "http://127.0.0.1:0",
                         "http://user@127.0.0.1:55591", "http://127.0.0.1:55591/path",
                         "http://127.0.0.1:55591?x=1", "http://127.0.0.1:55591#x",
                         "http://127.0.0.1:055591"):
            with self.assertRaises(ContractError):
                TypedReportingClient(endpoint, expected_pid=1234, ownership_check=lambda *a: True)
        client = TypedReportingClient(ENDPOINT, expected_pid=1234, ownership_check=lambda *a: True)
        proxies = [h for h in client.opener.handlers if isinstance(h, urllib.request.ProxyHandler)]
        self.assertTrue(not proxies or all(h.proxies == {} for h in proxies))
        redirects = [h for h in client.opener.handlers if isinstance(h, urllib.request.HTTPRedirectHandler)]
        self.assertEqual(len(redirects), 1)
        with self.assertRaises(ContractError):
            redirects[0].redirect_request(None, None, 302, "Found", {}, "http://example.invalid")

    def test_invalid_execute_configuration_is_retained_without_dispatch(self):
        for kwargs in (dict(timeout_seconds=True), dict(timeout_seconds=0),
                       dict(timeout_seconds=301), dict(timeout_seconds=float("nan")),
                       dict(maximum=True), dict(seed=True)):
            events = []
            opener = Opener()
            with self.assertRaises(ContractError):
                self.client(opener, retain=events.append).execute("prompt", **kwargs)
            self.assertEqual(opener.calls, [])
            self.assertEqual(events[-1]["event"], "terminal")
            self.assertFalse(events[-1]["result"].dispatched)

    def test_malformed_native_usage_and_json_retain_raw_without_invented_usage(self):
        payloads = [b"{", b"\xff", b'{"content":"x","content":"y"}',
                    canonical([]), canonical(native(tokens_evaluated=True)),
                    canonical(native(tokens_predicted=-1)),
                    canonical(native(tokens_predicted=1.0)),
                    canonical(native(tokens_evaluated=None))]
        for raw in payloads:
            result = self.client(Opener(raw)).execute("prompt")
            self.assertEqual(result.status, "failed")
            self.assertTrue(result.dispatched)
            self.assertEqual(result.raw_envelope, raw)
            self.assertIsNone(result.measured_usage)
            self.assertIsNone(result.content)

    def test_invalid_content_completeness_and_over_quote_keep_valid_measured_usage(self):
        for changes in (dict(content=7), dict(content="\ud800"),
                        dict(truncated=True), dict(truncated=0),
                        dict(stopped_limit=True), dict(stop=False),
                        dict(stop_type="limit", stop=True),
                        dict(stopped_word=True, stopped_eos=True),
                        dict(tokens_predicted=2049), dict(tokens_evaluated=999999)):
            if changes.get("content") == "\ud800":
                raw = canonical(native()).replace(b'{\\"facts\\":[]}', b'\\ud800')
            else:
                raw = canonical(native(**changes))
            result = self.client(Opener(raw)).execute("prompt")
            self.assertEqual(result.status, "failed", changes)
            self.assertIsNotNone(result.measured_usage, changes)
            self.assertEqual(result.measured_usage["output_tokens"], changes.get("tokens_predicted", 3))

    def test_optional_stop_metadata_absent_and_valid_explicit_stops(self):
        for changes in ({}, dict(stop=True, stop_type="eos", stopped_eos=True,
                                stopped_word=False, stopped_limit=False),
                        dict(stop=True, stop_type="word", stopping_word="<|im_end|>")):
            result = self.client(Opener(canonical(native(**changes)))).execute("prompt")
            self.assertEqual(result.status, "returned")

    def test_explicit_word_cause_always_requires_exact_requested_stopping_word(self):
        for changes in (dict(stopped_word=True), dict(stopped_word=True, stopping_word=None),
                        dict(stopped_word=True, stopping_word=""),
                        dict(stopped_word=True, stopping_word="different word")):
            result = self.client(Opener(canonical(native(**changes)))).execute("prompt")
            self.assertEqual(result.status, "failed", changes)
            self.assertEqual(result.measured_usage["output_tokens"], 3)
        result = self.client(Opener(canonical(native(stopped_word=True,
            stopping_word="<|im_end|>")))).execute("prompt")
        self.assertEqual(result.status, "returned")

    def test_native_prompt_model_and_settings_must_bind_to_exact_payload(self):
        malformed = [native(prompt="another prompt"), native(prompt=None),
                     native(model=" "), native(model=2), native(generation_settings={})]
        for key in ("prompt", "model", "generation_settings"):
            doc = native()
            del doc[key]
            malformed.append(doc)
        for field, value in (("seed", False), ("seed", 1), ("temperature", 0),
                             ("n_predict", True), ("n_predict", 2),
                             ("stream", 0), ("stream", True), ("stop", [])):
            doc = native()
            doc["generation_settings"][field] = value
            malformed.append(doc)
        for doc in malformed:
            result = self.client(Opener(canonical(doc))).execute("prompt")
            self.assertEqual(result.status, "failed")
            self.assertEqual(result.measured_usage["output_tokens"], 3)
        doc = native()
        doc["generation_settings"]["unrelated_native_setting"] = "preserved metadata"
        self.assertEqual(self.client(Opener(canonical(doc))).execute("prompt").status, "returned")

    def test_oversized_envelope_keeps_bounded_prefix_without_partial_rescue(self):
        raw = canonical(native()) + b" " * (2 * 1024 * 1024)
        result = self.client(Opener(raw)).execute("prompt")
        self.assertEqual(result.status, "failed")
        self.assertFalse(result.envelope_complete)
        self.assertEqual(len(result.raw_envelope), 2 * 1024 * 1024 + 1)
        self.assertEqual(result.response_sha256, hashlib.sha256(result.raw_envelope).hexdigest())
        self.assertIsNone(result.content)
        self.assertIsNone(result.measured_usage)

        class NonconformingResponse(Response):
            def read(self, maximum):
                return raw
        class NonconformingOpener(Opener):
            def open(self, request, timeout):
                return NonconformingResponse(b"")
        result = self.client(NonconformingOpener()).execute("prompt")
        self.assertEqual(result.status, "failed")
        self.assertFalse(result.envelope_complete)
        self.assertEqual(len(result.raw_envelope), 2 * 1024 * 1024 + 1)

    def test_injected_redirect_or_non200_response_is_rejected_before_read(self):
        class WrongResponse(Response):
            def read(self, maximum):
                raise AssertionError("Rejected response must not be read")
        class WrongOpener(Opener):
            def open(self, request, timeout):
                response = WrongResponse(b"")
                response.geturl = lambda: "http://example.invalid/completion"
                return response
        result = self.client(WrongOpener()).execute("prompt")
        self.assertEqual(result.status, "failed")
        self.assertIn("URL differs", result.error)
        self.assertEqual(result.raw_envelope, b"")
        class StatusOpener(Opener):
            def open(self, request, timeout):
                response = WrongResponse(b"")
                response.status = 500
                return response
        result = self.client(StatusOpener()).execute("prompt")
        self.assertEqual(result.status, "failed")
        self.assertIn("HTTP status", result.error)

    def test_timeout_http_and_connection_failures_dispatch_once(self):
        for error, status in ((TimeoutError("mock timeout"), "timeout"),
                              (urllib.error.URLError("mock connection"), "failed"),
                              (urllib.error.HTTPError(ENDPOINT, 302, "redirect", {}, None), "failed")):
            events = []
            opener = Opener(error=error)
            client = self.client(opener, retain=events.append)
            result = client.execute("prompt")
            self.assertEqual(result.status, status)
            self.assertTrue(result.dispatched)
            self.assertIsNone(result.measured_usage)
            self.assertEqual(len(opener.calls), 1)
            self.assertEqual(events[-1]["result"], result)
            with self.assertRaises(ContractError):
                client.execute("prompt")
            self.assertEqual(len(opener.calls), 1)

    def test_interruption_and_trusted_callback_failures_retain_then_propagate(self):
        for error in (KeyboardInterrupt(), SystemExit(2)):
            events = []
            opener = Opener(error=error)
            with self.assertRaises(type(error)):
                self.client(opener, retain=events.append).execute("prompt")
            self.assertEqual(events[-1]["result"].status, "interrupted")
            self.assertTrue(events[-1]["result"].dispatched)
        def bad_owner(*args):
            raise OSError("mock owner table denied")
        events = []
        opener = Opener()
        with self.assertRaises(OSError):
            self.client(opener, bad_owner, events.append).execute("prompt")
        self.assertEqual(opener.calls, [])
        self.assertFalse(events[-1]["result"].dispatched)
        events = []
        def bad_retain(event):
            events.append(event)
            if event["event"] == "attempt":
                raise OSError("mock journal unavailable")
        with self.assertRaises(OSError):
            self.client(opener, retain=bad_retain).execute("prompt")
        self.assertEqual(opener.calls, [])
        self.assertEqual(events[-1]["event"], "terminal")

    def test_response_read_interruption_retains_partial_bytes(self):
        class PartialResponse(Response):
            def read(self, maximum):
                error = KeyboardInterrupt()
                error.partial = b'{"content":"partial'
                raise error
        class PartialOpener(Opener):
            def open(self, request, timeout):
                self.calls.append((request, timeout))
                return PartialResponse(b"")
        events = []
        opener = PartialOpener()
        with self.assertRaises(KeyboardInterrupt):
            self.client(opener, retain=events.append).execute("prompt")
        result = events[-1]["result"]
        self.assertEqual(result.raw_envelope, b'{"content":"partial')
        self.assertFalse(result.envelope_complete)
        self.assertIsNone(result.measured_usage)

    def test_secondary_close_and_terminal_retention_do_not_replace_interruption(self):
        class InterruptedResponse(Response):
            def read(self, maximum):
                raise KeyboardInterrupt("primary read interruption")
            def __exit__(self, *args):
                raise RuntimeError("secondary close failure")
        class InterruptedOpener(Opener):
            def open(self, request, timeout):
                return InterruptedResponse(b"")
        events = []
        def retain(event):
            events.append(event)
            if event["event"] == "terminal":
                raise RuntimeError("secondary retention failure")
        with self.assertRaises(KeyboardInterrupt) as caught:
            self.client(InterruptedOpener(), retain=retain).execute("prompt")
        self.assertEqual(str(caught.exception), "primary read interruption")
        self.assertEqual(len(caught.exception.__notes__), 2)
        self.assertEqual(events[-1]["result"].status, "interrupted")

    def test_client_construction_and_preparation_never_open_socket_or_files(self):
        with patch("socket.socket", side_effect=AssertionError("No network")), \
             patch("builtins.open", side_effect=AssertionError("No writes")), \
             patch("subprocess.Popen", side_effect=AssertionError("No server")):
            TypedReportingClient(ENDPOINT, expected_pid=1234, ownership_check=lambda *a: True)
            prepare_completion("prompt", 100, 0)


if __name__ == "__main__":
    unittest.main()
