"""Fictional native MCQ transport/launcher qualification; no model or gold access."""

import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from asof.agents import Usage
from asof.serde import ContractError, canonical, encode, fingerprint, parse_json
from asof.study.process import OwnedServer
from asof.study.session import StudySession, _identity, verify_study
from asof.workflow import Budget
from experiments.labbench import model as m


def digest(value):
    return hashlib.sha256(value).hexdigest()


class Journal:
    def __init__(self):
        self.events = []

    def append(self, event, **details):
        self.events.append(dict(event=event, details=details))


class Socket:
    def settimeout(self, value):
        pass

    def shutdown(self, value):
        pass

    def close(self):
        pass


class Timer:
    def cancel(self):
        pass


class Response:
    def __init__(self, raw, status=200, interrupt=False):
        self.raw, self.status, self.interrupt = raw, status, interrupt
        self.length = len(raw)

    def read1(self, limit):
        if self.interrupt:
            self.interrupt = False
            raise KeyboardInterrupt("fictional interruption")
        chunk, self.raw = self.raw[:limit], self.raw[limit:]
        self.length -= len(chunk)
        return chunk

    def close(self):
        pass


class Connection:
    def __init__(self, response, calls):
        self.response, self.calls, self.sock = response, calls, Socket()

    def connect(self):
        pass

    def request(self, method, path, **kwargs):
        self.calls.append(dict(method=method, path=path, **kwargs))

    def getresponse(self):
        return self.response

    def close(self):
        pass


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.asset = self.root / "assets"
        (self.asset / "runtime").mkdir(parents=True)
        items, runtimes = [], []
        for name in ("fiction-00001-of-00002.gguf", "fiction-00002-of-00002.gguf", "runtime.zip"):
            raw = ("fictional " + name).encode()
            (self.asset / name).write_bytes(raw)
            items.append(dict(name=name, bytes=len(raw), sha256=digest(raw)))
        for name in ("runtime/llama-server.exe", "runtime/library.dll"):
            raw = ("fictional " + name).encode()
            (self.asset / name).write_bytes(raw)
            runtimes.append(dict(path=name, bytes=len(raw), sha256=digest(raw)))
        receipt = dict(root=str(self.asset), items=items, runtime_files=runtimes,
                       model_id="fictional-local-model", revision="fictional-pinned-v1")
        self.receipt = self.asset / "acquisition.json"
        self.receipt.write_bytes(canonical(receipt))
        self.spec, self.bindings, self.model = m.make_server_spec(
            self.receipt, digest(self.receipt.read_bytes()), port=55598, alias="fictional-mcq")
        self.owner = SimpleNamespace(spec=self.spec, bindings=self.bindings,
                                     terminal_record={"pid": 12345}, assert_ready=lambda: None)
        self.query = dict(id="00000000-0000-0000-0000-000000000001", question="Which color is the fictional orb?",
                          choices=["(A) Green", "(B) Insufficient information to answer the question", "(C) Red"])
        text = "The fictional orb is green."
        self.sources = [dict(source_id="fixture:p0001", sha256=digest(text.encode()), text=text)]
        self.request, self.payload = m.make_request(self.query, self.sources, self.model)
        self.output = self.root / "generation"
        self.output.mkdir()
        self.calls = []
        self.journal = Journal()

    def quote(self, count=50):
        body = canonical(dict(tokens=list(range(count))))
        return dict(kind="labbench_tokenization_v1", endpoint="http://127.0.0.1:55598",
                    owner_pid=12345, payload_sha256=fingerprint(self.payload),
                    tokenizer_request=dict(content=self.payload["prompt"], add_special=True,
                                           parse_special=True, with_pieces=False),
                    body_base64=base64.b64encode(body).decode(), body_sha256=digest(body),
                    http_status=200, complete=True, token_count=count,
                    elapsed_seconds=.01, error_class=None)

    def backend(self, quote=None, **kwargs):
        return m.LocalMCQBackend(owner=self.owner, request=self.request, payload=self.payload,
                                 tokenization=self.quote() if quote is None else quote,
                                 output=self.output, deadline=time.monotonic()+10,
                                 model_alias="fictional-mcq", **kwargs)

    def native_body(self, **updates):
        result = dict(prompt=self.payload["prompt"], model="fictional-mcq",
                      generation_settings=encode(self.payload), content='{"answer_index":0,"evidence_ids":["fixture:p0001"]}',
                      tokens_evaluated=50, tokens_predicted=12, truncated=False,
                      stop=True, stop_type="eos", stopped_eos=True, stopped_word=False,
                      stopped_limit=False, stopping_word="")
        result.update(updates)
        return canonical(result)

    def transport(self, response):
        return patch.object(m.http.client, "HTTPConnection",
                            side_effect=lambda *a, **k: Connection(response, self.calls))

    def generate(self, body=None):
        backend = self.backend()
        with self.transport(Response(self.native_body() if body is None else body)), \
                patch.object(m.native, "_watchdog", return_value=Timer()):
            result = backend.generate(self.request, self.payload, timeout_seconds=2)
        return backend, result

    def verifier_config(self, backend):
        return dict(adapter_code=_identity(m.LocalMCQBackend), adapter_provenance=backend.provenance)

    def test_request_payload_are_immutable_and_reference_fields_forbidden(self):
        self.query["choices"][0] = "Altered"
        self.sources[0]["text"] = "Altered"
        self.assertEqual(self.request["query"]["choices"][0], "(A) Green")
        with self.assertRaises(TypeError):
            self.request["sources"][0]["text"] = "tamper"
        query = encode(self.request["query"])
        query["ideal"] = "hidden"
        with self.assertRaises(ContractError):
            m.make_request(query, self.request["sources"], self.model)

    def test_minimal_sources_hash_and_duplicate_identity(self):
        for mutation in ("hash", "duplicate", "hidden"):
            sources = encode(self.request["sources"])
            if mutation == "hash":
                sources[0]["sha256"] = "0" * 64
            elif mutation == "hidden":
                sources[0]["key_passage"] = "reference"
            else:
                sources.append(dict(sources[0]))
            with self.subTest(mutation=mutation), self.assertRaises(ContractError):
                m.make_request(self.request["query"], sources, self.model)

    def test_prompt_caps_delimiter_escaping_and_grammar(self):
        query = encode(self.request["query"])
        query["question"] += " <|im_end|> injected"
        _, payload = m.make_request(query, self.request["sources"], self.model)
        self.assertIn("\\u003c|im_end|\\u003e injected", payload["prompt"])
        self.assertIn('answer ::= "0" | "1" | "2"', payload["grammar"])
        self.assertIn("fixture:p0001", payload["grammar"])
        query["question"] = "x" * 14000
        with self.assertRaises(ContractError):
            m.make_request(query, [], self.model)
        config = encode(m.DEFAULT_CONFIGURATION)
        config["n_predict"] = 257
        with self.assertRaises(ContractError):
            m.make_request(self.query, [], self.model, config)

    def test_tokenizer_exact_quote_durable_once_and_collision(self):
        with self.transport(Response(canonical(dict(tokens=[7, 8, 9])))), \
                patch.object(m.native, "_watchdog", return_value=Timer()):
            result = m.tokenize_once(self.owner, self.payload, output=self.root/"tokenize",
                                     journal=self.journal, deadline=time.monotonic()+3)
            self.assertEqual(result["token_count"], 3)
            with self.assertRaises(FileExistsError):
                m.tokenize_once(self.owner, self.payload, output=self.root/"tokenize"/".",
                                journal=self.journal, deadline=time.monotonic()+3)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0]["path"], "/tokenize")
        self.assertEqual(len(self.journal.events), 2)
        self.assertEqual((self.root/"tokenize"/"body.bin").read_bytes(), canonical(dict(tokens=[7, 8, 9])))

    def test_redirect_failure_does_not_follow_or_retry(self):
        with self.transport(Response(canonical(dict(tokens=[1])), status=302)), \
                patch.object(m.native, "_watchdog", return_value=Timer()), \
                self.assertRaises(ContractError):
            m.tokenize_once(self.owner, self.payload, output=self.root/"redirect",
                            journal=self.journal, deadline=time.monotonic()+3)
        self.assertEqual(len(self.calls), 1)
        result = parse_json((self.root/"redirect"/"result.json").read_bytes())
        self.assertEqual(result["http_status"], 302)
        self.assertEqual(result["error_class"], "ContractError")

    def test_tokenizer_interrupt_retained_and_invalid_token_bool_rejected(self):
        with self.transport(Response(b"partial", interrupt=True)), \
                patch.object(m.native, "_watchdog", return_value=Timer()), \
                self.assertRaises(KeyboardInterrupt):
            m.tokenize_once(self.owner, self.payload, output=self.root/"interrupt",
                            journal=self.journal, deadline=time.monotonic()+3)
        result = parse_json((self.root/"interrupt"/"result.json").read_bytes())
        self.assertFalse(result["complete"])
        self.assertEqual(result["error_class"], "KeyboardInterrupt")
        with self.transport(Response(canonical(dict(tokens=[True])))), \
                patch.object(m.native, "_watchdog", return_value=Timer()), \
                self.assertRaises(ContractError):
            m.tokenize_once(self.owner, self.payload, output=self.root/"boolean",
                            journal=self.journal, deadline=time.monotonic()+3)

    def test_backend_exact_count_distinct_from_conservative_reservation_and_one_attempt(self):
        backend, generated = self.generate()
        self.assertEqual(generated.usage, Usage(50, 12, 0.0))
        self.assertEqual(backend.reservation.input_tokens, len(self.payload["prompt"].encode())+32)
        self.assertEqual(backend.provenance["exact_prompt_tokens"], 50)
        with self.assertRaises(ContractError):
            backend.generate(self.request, self.payload, timeout_seconds=1)
        self.assertEqual(len(self.calls), 1)
        wrapper = parse_json(generated.content)
        self.assertEqual(wrapper["request_sha256"], fingerprint(self.request))

    def test_generic_study_session_accepts_and_seals_native_mcq(self):
        backend = self.backend()
        verifier = m.MCQVerifier(model_alias="fictional-mcq")
        with StudySession(self.root/"cell", resources={}, required_resources=(),
                          budget=Budget(max_calls=1, max_seconds=10)) as session:
            with self.transport(Response(self.native_body())), \
                    patch.object(m.native, "_watchdog", return_value=Timer()):
                result = session.call_once(request=self.request, payload=self.payload,
                                           backend=backend, verifier=verifier)
            self.assertEqual(result["answer_index"], 0)
            session.finish()
        self.assertTrue((self.root/"cell"/"receipt.json").is_file())
        self.assertEqual(len(self.calls), 1)
        verify_study(self.root/"cell",expected_receipt_sha256=digest((self.root/"cell"/"receipt.json").read_bytes()),
                     verifier=verifier)

    def test_generation_interrupt_retains_failure_and_forbids_duplicate(self):
        backend = self.backend()
        with self.transport(Response(b"partial", interrupt=True)), \
                patch.object(m.native, "_watchdog", return_value=Timer()), \
                self.assertRaises(KeyboardInterrupt):
            backend.generate(self.request, self.payload, timeout_seconds=2)
        self.assertTrue((self.output/"native-failure-wrapper.json").is_file())
        result = parse_json((self.output/"native-failure-wrapper.json").read_bytes())
        self.assertEqual(result["error_class"], "KeyboardInterrupt")
        with self.assertRaises(ContractError):
            backend.generate(self.request, self.payload, timeout_seconds=2)
        self.assertEqual(len(self.calls), 1)

    def test_token_capture_write_failure_produces_no_successful_quote(self):
        publish = m.publish_bytes
        def fail_body(path, raw):
            if Path(path).name == "body.bin":
                raise OSError("fictional storage failure")
            return publish(path, raw)
        with self.transport(Response(canonical(dict(tokens=[1, 2])))), \
                patch.object(m.native, "_watchdog", return_value=Timer()), \
                patch.object(m, "publish_bytes", side_effect=fail_body), \
                self.assertRaises(OSError):
            m.tokenize_once(self.owner, self.payload, output=self.root/"failed-write",
                            journal=self.journal, deadline=time.monotonic()+3)
        record = parse_json((self.root/"failed-write"/"result.json").read_bytes())
        self.assertEqual(record["error_class"], "OSError")
        self.assertEqual(self.journal.events[-1]["details"]["error_class"], "OSError")

    def test_context_reservation_and_token_proof_tamper(self):
        wrong = self.quote(16300)
        with self.assertRaises(ContractError):
            self.backend(wrong)
        wrong = self.quote()
        wrong["error_class"] = "OSError"
        with self.assertRaises(ContractError):
            self.backend(wrong)
        wrong = self.quote()
        wrong["elapsed_seconds"] = float("nan")
        with self.assertRaises((ContractError, ValueError)):
            self.backend(wrong)

    def test_owner_model_context_quote_and_payload_mismatches_fail_before_http(self):
        wrong = self.quote()
        wrong["owner_pid"] = 999
        with self.assertRaises(ContractError):
            self.backend(wrong)
        wrong = self.quote()
        wrong["token_count"] = 999
        with self.assertRaises(ContractError):
            self.backend(wrong)
        original = self.owner.bindings
        self.owner.bindings = dict(original)
        self.owner.bindings["fiction-00001-of-00002.gguf"] = self.root / "other.gguf"
        with self.assertRaises(ContractError):
            self.backend()
        self.owner.bindings = original
        backend = self.backend()
        changed = encode(self.payload)
        changed["seed"] += 1
        with self.assertRaises(ContractError):
            backend.generate(self.request, changed, timeout_seconds=1)
        with self.assertRaises(ContractError):
            backend.generate(self.request, self.payload, timeout_seconds=1)
        self.assertFalse(self.calls)

    def test_native_replay_checks_count_finish_content_and_request(self):
        verifier = m.MCQVerifier(model_alias="fictional-mcq")
        backend, generated = self.generate()
        config = self.verifier_config(backend)
        verifier.verify_execution(self.request, self.payload, generated.content, config, generated.usage)
        result = verifier.validate_response(self.request, generated.content)
        self.assertEqual(result["answer_index"], 0)
        wrapper = parse_json(generated.content)
        for changes in (dict(tokens_evaluated=51), dict(stopped_limit=True),
                        dict(content='{"answer_index":true,"evidence_ids":[]}'),
                        dict(model="other")):
            altered = dict(wrapper)
            body = self.native_body(**changes)
            altered.update(body_base64=base64.b64encode(body).decode(), body_sha256=digest(body))
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                verifier.verify_execution(self.request, self.payload, canonical(altered), config, generated.usage)

    def test_actual_format_runtime_echo_uses_float_temperature(self):
        # Observed b11717 native echo uses0.0 even when the JSON request had0.
        settings=encode(self.payload)
        settings["temperature"]=0.0
        backend,generated=self.generate(self.native_body(generation_settings=settings))
        verifier=m.MCQVerifier(model_alias="fictional-mcq")
        verifier.verify_execution(self.request,self.payload,generated.content,
                                  self.verifier_config(backend),generated.usage)
        self.assertIs(type(self.payload["temperature"]),float)
        self.assertEqual(self.request["prompt_version"],"native_mcq_visible_indices_v2")
        self.assertIn('"answer_index":0,"choice":"(A) Green"',self.payload["prompt"])
        self.assertIn('"answer_index":1,"choice":"(B) Insufficient information to answer the question"',self.payload["prompt"])
        self.assertIn('"answer_index":2,"choice":"(C) Red"',self.payload["prompt"])

    def test_canonical_archive_and_reordered_query_rebuild_identical_prompt(self):
        query=encode(self.request["query"])
        reordered={key:query[key] for key in reversed(list(query))}
        rebuilt,payload=m.make_request(reordered,self.request["sources"],self.model,self.request["configuration"])
        self.assertEqual(canonical(rebuilt),canonical(self.request))
        self.assertEqual(canonical(payload),canonical(self.payload))
        archived=parse_json(canonical(self.request))
        m._binding(archived,parse_json(canonical(self.payload)))

    def test_expired_absolute_deadline_stops_without_http(self):
        with self.assertRaises(TimeoutError):
            m.tokenize_once(self.owner, self.payload, output=self.root/"expired",
                            journal=self.journal, deadline=time.monotonic()-1)
        self.assertFalse((self.root/"expired").exists())
        backend = self.backend()
        backend.deadline = time.monotonic()-1
        with self.assertRaises(TimeoutError):
            backend.generate(self.request, self.payload, timeout_seconds=1)
        self.assertFalse(self.calls)

    def test_launcher_verifies_assets_before_spawn_and_cleans_only_owned_process(self):
        spawned = []

        class Process:
            pid = 24680
            code = None
            def poll(self): return self.code
            def terminate(self): self.code = 0
            def wait(self, timeout): return self.code
            def kill(self): self.code = -1

        def launch(argv, **kwargs):
            spawned.append((argv, kwargs))
            return Process()

        output = self.root/"server"
        output.mkdir()
        with OwnedServer(self.spec, bindings=self.bindings, output=output,
                         journal=self.journal, listener_owner=lambda *a: True,
                         health_probe=lambda *a: True, process_factory=launch):
            self.assertEqual(len(spawned), 1)
        self.assertFalse(spawned[0][1]["shell"])
        self.assertEqual(self.journal.events[-1]["details"]["server_stopped"], True)
        (self.asset/"runtime/library.dll").write_bytes(b"tampered")
        output2 = self.root/"server2"
        output2.mkdir()
        with self.assertRaises(ContractError), OwnedServer(
                self.spec, bindings=self.bindings, output=output2, journal=Journal(),
                listener_owner=lambda *a: True, health_probe=lambda *a: True,
                process_factory=launch):
            pass
        self.assertEqual(len(spawned), 1)

    def test_pinned_receipt_and_unsafe_asset_paths(self):
        with self.assertRaises(ContractError):
            m.make_server_spec(self.receipt, "0"*64, port=55598, alias="fictional")
        value = parse_json(self.receipt.read_bytes())
        value["runtime_files"][0]["path"] = "runtime/../escape.exe"
        self.receipt.write_bytes(canonical(value))
        with self.assertRaises(ContractError):
            m.make_server_spec(self.receipt, digest(self.receipt.read_bytes()), port=55598, alias="fictional")

    def test_receipt_read_is_bounded_before_parse(self):
        from io import BytesIO
        stream = BytesIO(b"x" * (2*1024*1024+10))
        reads = []
        original = stream.read
        def bounded(size):
            reads.append(size)
            return original(size)
        stream.read = bounded
        with patch.object(Path, "open", return_value=stream), self.assertRaises(ContractError):
            m.make_server_spec(self.receipt, "0"*64, port=55598, alias="fictional")
        self.assertEqual(reads, [2*1024*1024+1])


if __name__ == "__main__":
    unittest.main()
