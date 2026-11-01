"""Independent finite transport regressions; all requests use in-memory mocks."""

import hashlib
import io
import threading
import unittest

from asof.serde import ContractError, canonical
from asof.study.source_fact_transport import (
    MAX_ENVELOPE_BYTES,
    TypedReportingClient,
    parse_netstat_listener,
    prepare_completion,
)


ENDPOINT = "http://127.0.0.1:55591"
PROMPT = "fictional prompt"
OWNER_ROW = b"TCP 127.0.0.1:55591 0.0.0.0:0 LISTENING 1234\n"


def envelope(**changes):
    return dict(content=' {"fictional":true}\n', prompt=PROMPT,
                model="fictional-model", truncated=False,
                tokens_evaluated=2, tokens_predicted=3,
                generation_settings=dict(seed=0, temperature=0.0, n_predict=7,
                    stream=False, stop=["<|im_end|>"])) | changes


class MemoryResponse(io.BytesIO):
    status = 200

    def geturl(self):
        return ENDPOINT + "/completion"


class MemoryOpener:
    def __init__(self, raw=None, *, response_factory=MemoryResponse, error=None):
        self.raw = canonical(envelope()) if raw is None else raw
        self.response_factory, self.error = response_factory, error
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        if self.error is not None:
            raise self.error
        return self.response_factory(self.raw)


def client(opener, *, owner=lambda *args: True, retain=None):
    return TypedReportingClient(ENDPOINT, expected_pid=1234,
        ownership_check=owner, opener=opener, retain=retain)


class IndependentListenerControls(unittest.TestCase):
    def test_unknown_target_states_cannot_hide_listener_ambiguity(self):
        for ambiguous in (
            b"TCP 127.0.0.1:55591 0.0.0.0:0 ECOUTE 1234\n",
            b"TCP 0.0.0.0:55591 0.0.0.0:0 LISTEN 9999\n",
            b"TCP [::]:55591 [::]:0 ABHOREN 9999\n",
            b"TCP [::1]:55591 [::]:0 UNKNOWN 9999\n",
        ):
            for raw in (ambiguous, OWNER_ROW + ambiguous, ambiguous + OWNER_ROW):
                with self.subTest(raw=raw), self.assertRaises(ContractError):
                    parse_netstat_listener(raw, 55591)

    def test_known_nonlisteners_and_unrelated_unknown_states_do_not_add_owners(self):
        raw = (b"\xef\xbb\xbfActive Connections\r\n"
               b"TCP [::1]:55590 [::]:0 UNKNOWN 9999\r\n"
               b"TCP 127.0.0.1:55591 127.0.0.1:1 ESTABLISHED 9999\r\n"
               b"TCP 127.0.0.1:55591 127.0.0.1:1 TIME_WAIT 0\r\n") + OWNER_ROW
        self.assertEqual(parse_netstat_listener(raw, 55591), 1234)

    def test_pid_is_canonical_ascii_positive_windows_uint32(self):
        self.assertEqual(parse_netstat_listener(OWNER_ROW.replace(b"1234", b"4294967295"), 55591),
                         4294967295)
        for pid in (b"4294967296", b"0001", b"+1", b"1.0", b"1e3", b"0",
                    "１２３４".encode("utf-8"), b"1_234"):
            with self.subTest(pid=pid), self.assertRaises(ContractError):
                parse_netstat_listener(OWNER_ROW.replace(b"1234", pid), 55591)

    def test_noncanonical_target_listeners_fail_even_after_the_expected_owner(self):
        for replacement in (b"0.0.0.0:55591", b"[::]:55591", b"[::1]:55591",
                            b"127.0.0.1:055591", b"127.0.0.2:55591"):
            row = OWNER_ROW.replace(b"127.0.0.1:55591", replacement)
            with self.subTest(replacement=replacement), self.assertRaises(ContractError):
                parse_netstat_listener(OWNER_ROW + row, 55591)


class IndependentDispatchControls(unittest.TestCase):
    def test_concurrent_calls_cannot_share_one_owned_attempt(self):
        entered, release = threading.Event(), threading.Event()
        ownership_calls, events, results, failures = [], [], [], []

        def owner(*args):
            ownership_calls.append(args)
            entered.set()
            if not release.wait(5):
                raise AssertionError("test did not release mocked ownership")
            return True

        opener = MemoryOpener()
        transport = client(opener, owner=owner, retain=events.append)

        def execute():
            try:
                results.append(transport.execute(PROMPT, maximum=7))
            except BaseException as error:
                failures.append(error)

        thread = threading.Thread(target=execute, daemon=True)
        thread.start()
        try:
            self.assertTrue(entered.wait(5))
            with self.assertRaises(ContractError):
                transport.execute(PROMPT, maximum=7)
            self.assertEqual(opener.calls, [])
            self.assertEqual(len(ownership_calls), 1)
        finally:
            release.set()
            thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failures, [])
        self.assertEqual([result.status for result in results], ["returned"])
        self.assertEqual(len(opener.calls), 1)
        self.assertEqual([event["event"] for event in events], ["attempt", "terminal"])

    def test_reentrant_attempt_callback_cannot_dispatch_a_second_request(self):
        events = []
        opener = MemoryOpener()
        transport = None

        def retain(event):
            events.append(event)
            if event["event"] == "attempt":
                with self.assertRaises(ContractError):
                    transport.execute(PROMPT, maximum=7)
                with self.assertRaises(TypeError):
                    event["estimated_usage"]["output_tokens"] = 100

        transport = client(opener, retain=retain)
        self.assertEqual(transport.execute(PROMPT, maximum=7).status, "returned")
        self.assertEqual(len(opener.calls), 1)
        self.assertEqual([event["event"] for event in events], ["attempt", "terminal"])

    def test_truthy_ownership_is_denied_without_boolean_coercion_or_dispatch(self):
        class TruthTrap:
            def __bool__(self):
                raise AssertionError("ownership requires literal True")

        opener, events = MemoryOpener(), []
        transport = client(opener, owner=lambda *args: TruthTrap(), retain=events.append)
        result = transport.execute(PROMPT, maximum=7)
        self.assertEqual(result.status, "failed")
        self.assertFalse(result.dispatched)
        self.assertEqual(opener.calls, [])
        self.assertEqual([event["event"] for event in events], ["terminal"])
        with self.assertRaises(ContractError):
            transport.execute(PROMPT, maximum=7)

    def test_attempt_journal_failure_remains_primary_and_never_dispatches(self):
        original = OSError("fictional attempt journal failure")
        opener, events = MemoryOpener(), []

        def retain(event):
            events.append(event)
            if event["event"] == "attempt":
                raise original
            raise RuntimeError("fictional terminal journal failure")

        transport = client(opener, retain=retain)
        with self.assertRaises(OSError) as caught:
            transport.execute(PROMPT, maximum=7)
        self.assertIs(caught.exception, original)
        self.assertEqual(opener.calls, [])
        self.assertEqual([event["event"] for event in events], ["attempt", "terminal"])
        self.assertFalse(events[-1]["result"].dispatched)
        self.assertEqual(len(original.__notes__), 1)
        with self.assertRaises(ContractError):
            transport.execute(PROMPT, maximum=7)

    def test_terminal_journal_failure_propagates_after_exactly_one_dispatch(self):
        original = OSError("fictional terminal journal failure")
        opener, events = MemoryOpener(), []

        def retain(event):
            events.append(event)
            if event["event"] == "terminal":
                raise original

        transport = client(opener, retain=retain)
        with self.assertRaises(OSError) as caught:
            transport.execute(PROMPT, maximum=7)
        self.assertIs(caught.exception, original)
        self.assertEqual(events[-1]["result"].status, "returned")
        self.assertEqual(len(opener.calls), 1)
        with self.assertRaises(ContractError):
            transport.execute(PROMPT, maximum=7)
        self.assertEqual(len(opener.calls), 1)

    def test_ownership_interruption_survives_terminal_journal_failure(self):
        interruption = KeyboardInterrupt("fictional ownership interruption")
        opener, events = MemoryOpener(), []

        def owner(*args):
            raise interruption

        def retain(event):
            events.append(event)
            raise OSError("fictional terminal journal failure")

        with self.assertRaises(KeyboardInterrupt) as caught:
            client(opener, owner=owner, retain=retain).execute(PROMPT, maximum=7)
        self.assertIs(caught.exception, interruption)
        self.assertEqual(opener.calls, [])
        self.assertEqual([event["event"] for event in events], ["terminal"])
        self.assertEqual(events[-1]["result"].status, "interrupted")
        self.assertFalse(events[-1]["result"].dispatched)

    def test_response_context_cannot_suppress_a_read_interruption(self):
        interruption = KeyboardInterrupt("fictional read interruption")
        exits = []

        class SuppressingResponse(MemoryResponse):
            def read(self, maximum):
                raise interruption

            def __exit__(self, *args):
                exits.append(args)
                super().__exit__(*args)
                return True

        events, opener = [], MemoryOpener(response_factory=SuppressingResponse)
        with self.assertRaises(KeyboardInterrupt) as caught:
            client(opener, retain=events.append).execute(PROMPT, maximum=7)
        self.assertIs(caught.exception, interruption)
        self.assertEqual(len(exits), 1)
        self.assertIs(exits[0][1], interruption)
        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(events[-1]["result"].status, "interrupted")


class IndependentEnvelopeControls(unittest.TestCase):
    def execute(self, document=None, *, raw=None):
        if raw is None:
            raw = canonical(envelope() if document is None else document)
        return client(MemoryOpener(raw)).execute(PROMPT, maximum=7)

    def test_exact_envelope_limit_is_accepted_and_over_limit_is_not_rescued(self):
        prefix = canonical(envelope())
        raw = prefix + b" " * (MAX_ENVELOPE_BYTES - len(prefix))
        accepted = self.execute(raw=raw)
        self.assertEqual(accepted.status, "returned")
        self.assertTrue(accepted.envelope_complete)
        self.assertEqual(accepted.raw_envelope, raw)
        rejected = self.execute(raw=raw + b" ")
        self.assertEqual(rejected.status, "failed")
        self.assertFalse(rejected.envelope_complete)
        self.assertEqual(rejected.raw_envelope, raw + b" ")
        self.assertIsNone(rejected.measured_usage)
        self.assertIsNone(rejected.content)
        self.assertEqual(rejected.response_sha256, hashlib.sha256(raw + b" ").hexdigest())

    def test_non200_status_never_parses_even_a_valid_envelope(self):
        class Non200Response(MemoryResponse):
            status = 201

            def read(self, maximum):
                raise AssertionError("non200 body must not be read")

        result = client(MemoryOpener(response_factory=Non200Response)).execute(PROMPT, maximum=7)
        self.assertEqual(result.status, "failed")
        self.assertTrue(result.dispatched)
        self.assertEqual(result.raw_envelope, b"")
        self.assertIsNone(result.measured_usage)

    def test_invalid_optional_stop_metadata_is_not_silently_ignored(self):
        for changes in (
            dict(stopped_word=True),
            dict(stopped_word=True, stopping_word=None),
            dict(stopped_word=True, stopping_word="unrequested"),
            dict(stopped_word=True, stopping_word=""),
            dict(stopped_eos=True, stopping_word="<|im_end|>"),
            dict(stop=True, stop_type="eos", stopped_word=True),
            dict(stop=True, stop_type="word", stopped_eos=True, stopping_word="<|im_end|>"),
            dict(stop=True, stop_type="word"),
            dict(stop_type="eos"), dict(stop=None), dict(stop=1),
            dict(stopped_limit=0), dict(stopped_eos=1), dict(stopped_word=0),
        ):
            with self.subTest(changes=changes):
                result = self.execute(envelope(**changes))
                self.assertEqual(result.status, "failed")
                self.assertEqual(result.measured_usage["output_tokens"], 3)
                self.assertEqual(result.content, b' {"fictional":true}\n')

    def test_absent_stop_causes_and_exact_legacy_or_explicit_stops_are_accepted(self):
        for changes in ({}, dict(stopped_limit=False), dict(stopped_eos=True),
                        dict(stopped_word=True, stopping_word="<|im_end|>"),
                        dict(stop=True, stop_type="eos"),
                        dict(stop=True, stop_type="word", stopping_word="<|im_end|>")):
            with self.subTest(changes=changes):
                self.assertEqual(self.execute(envelope(**changes)).status, "returned")

    def test_rejected_echo_keeps_exact_bytes_hashes_and_measured_usage(self):
        raw = b"\xef\xbb\xbf \n" + canonical(envelope(prompt=PROMPT + " ")) + b"\n"
        result = self.execute(raw=raw)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.raw_envelope, raw)
        self.assertEqual(result.response_sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(result.content_sha256, hashlib.sha256(result.content).hexdigest())
        self.assertEqual(result.measured_usage["input_tokens"], 2)
        self.assertEqual(result.estimated_usage["input_tokens"], len(PROMPT.encode()) + 32)
        self.assertNotEqual(result.measured_usage["input_tokens"], result.estimated_usage["input_tokens"])

    def test_usage_and_echo_settings_reject_numeric_boolean_coercion(self):
        cases = []
        for field in ("tokens_evaluated", "tokens_predicted"):
            for value in (True, False, 1.0, -1, "1"):
                cases.append((envelope(**{field: value}), False))
        for field, value in (("seed", False), ("seed", 0.0), ("temperature", 0),
                             ("n_predict", 7.0), ("stream", 0), ("stop", "<|im_end|>")):
            document = envelope()
            document["generation_settings"][field] = value
            cases.append((document, True))
        for document, retain_usage in cases:
            with self.subTest(document=document):
                result = self.execute(document)
                self.assertEqual(result.status, "failed")
                self.assertEqual(result.measured_usage is not None, retain_usage)

    def test_usage_exact_reservation_and_output_limit_have_distinct_boundaries(self):
        bound = len(PROMPT.encode("utf-8")) + 32
        self.assertEqual(self.execute(envelope(tokens_evaluated=bound, tokens_predicted=7)).status,
                         "returned")
        for changes in (dict(tokens_evaluated=bound + 1), dict(tokens_predicted=8)):
            with self.subTest(changes=changes):
                result = self.execute(envelope(**changes))
                self.assertEqual(result.status, "failed")
                self.assertIsNotNone(result.measured_usage)
                self.assertIsNotNone(result.content)

    def test_multibyte_prompt_reservation_uses_bytes_and_preserves_payload(self):
        prompt = "😀" * ((16384 - 7 - 32) // 4)
        payload = prepare_completion(prompt, maximum=7)
        self.assertEqual(payload["prompt"], prompt)
        with self.assertRaises(ContractError):
            prepare_completion(prompt + "😀", maximum=7)


if __name__ == "__main__":
    unittest.main()
