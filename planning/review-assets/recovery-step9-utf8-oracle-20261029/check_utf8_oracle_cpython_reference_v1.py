"""Independent postfreeze bytewise CPython reference; not a production adapter.

Successful prefix output and pre-call codec buffers provide semantic evidence.
The frozen oracle's byte-consumption/error policy is checked separately against
the RFC byte table; no codec state is read after an exception.
"""
import codecs
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
FREEZE = HERE / "UTF8-ORACLE-FIXTURE-FREEZE-v2.json"
FREEZE_SHA = "285a46b3b7ac00cf7bbb0b262242ffc04f2c3049e4b7cf541dbcfdf0080f1eac"
SPEC_SHA = "f4f3835481f1961c01830bf6ba37107cf270ebaad7a9321d6f1b4ee0fcdec44a"
CORPUS_SHA = "65428d32cc06c58836d1d541bde0e893db13cef9e5ae756e26d6e353908b302d"
PROOF = HERE / "UTF8-ORACLE-CPYTHON-REFERENCE-PROOF-v1.json"
DEADLINE_SECONDS = 20
DENIALS = []


def guard(event, args):
    if event.startswith(("socket.", "subprocess.", "ctypes.dlopen", "os.system")):
        DENIALS.append(event)
        raise RuntimeError("Independent reference forbids process/native/network calls")
    if event == "open" and isinstance(args[0], (str, bytes)):
        value = str(args[0]).lower().replace("/", "\\")
        if value.startswith("e:") or value.endswith((".gguf", ".dll", "recognition.pack")) or "\\data\\benchmark\\" in value:
            DENIALS.append("protected_payload_open")
            raise RuntimeError("Independent reference forbids protected/model/native payload access")
        mode = args[1]
        if isinstance(mode, str) and any(char in mode for char in "wax+") and Path(args[0]) != PROOF:
            DENIALS.append("unexpected_write")
            raise RuntimeError("Only the fresh reference proof may be written")


sys.addaudithook(guard)


def require(value, message):
    if not value:
        raise RuntimeError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def pending_width(raw):
    if not raw:
        return None
    first = raw[0]
    require(0xC2 <= first <= 0xF4, "Codec pending lead outside strict table")
    return 2 if first <= 0xDF else 3 if first <= 0xEF else 4


def rfc_error_category(pending, byte):
    """Classify an observed first rejection, independently of codec messages."""
    if not pending:
        if 0x80 <= byte <= 0xBF:
            return "unexpected_continuation"
        require(byte in (0xC0, 0xC1) or 0xF5 <= byte <= 0xFF, "Unexpected codec boundary rejection")
        return "invalid_lead"
    if not 0x80 <= byte <= 0xBF:
        return "invalid_continuation"
    if len(pending) == 1:
        lead = pending[0]
        if (lead == 0xE0 and byte <= 0x9F) or (lead == 0xF0 and byte <= 0x8F):
            return "overlong_sequence"
        if lead == 0xED and byte >= 0xA0:
            return "surrogate_scalar"
        if lead == 0xF4 and byte >= 0x90:
            return "out_of_range_scalar"
    raise RuntimeError("Codec rejected a byte allowed by the independent RFC table")


def reference_steps(case):
    decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
    pending = b""
    decoded = []
    consumed = examined = 0
    failure = None
    finished = False
    observations = []
    codec_errors = []
    for step_index, step in enumerate(case["steps"]):
        require(not finished, "Corpus requests a feed after successful finalization")
        raw = bytes.fromhex(step["chunk_hex"])
        final = step["final"]
        require(type(final) is bool, "Frozen corpus final flag is not strict bool")
        old_consumed, old_examined = consumed, examined
        emitted = []
        unconsumed = raw if failure is not None else b""
        if failure is None:
            for index, byte in enumerate(raw):
                before, codec_flag = decoder.getstate()
                require(type(before) is bytes and codec_flag == 0 and before == pending, "Unexpected pre-call codec state")
                examined += 1
                try:
                    text = decoder.decode(bytes([byte]), final=False)
                except UnicodeDecodeError as error:
                    # Never call getstate/decode on this decoder after error.
                    failure = dict(code=rfc_error_category(before, byte), byte_offset=consumed,
                                   sequence_start_offset=consumed - len(before), offending_byte=byte)
                    pending = before
                    unconsumed = raw[index:]
                    codec_errors.append(dict(step=step_index, call="one_byte", exception_class=type(error).__name__,
                                             reason=error.reason, exception_offsets_not_used=True))
                    break
                else:
                    consumed += 1
                    values = [ord(char) for char in text]
                    emitted.extend(values)
                    decoded.extend(values)
                    pending, codec_flag = decoder.getstate()
                    require(codec_flag == 0, "Unexpected successful codec flag")
            if failure is None and final:
                before, codec_flag = decoder.getstate()
                require(codec_flag == 0 and before == pending, "Unexpected pre-final codec state")
                try:
                    text = decoder.decode(b"", final=True)
                except UnicodeDecodeError as error:
                    require(bool(before), "Codec EOF error without pending bytes")
                    failure = dict(code="premature_eof", byte_offset=consumed,
                                   sequence_start_offset=consumed - len(before), offending_byte=None)
                    pending = before
                    codec_errors.append(dict(step=step_index, call="empty_final", exception_class=type(error).__name__,
                                             reason=error.reason, exception_offsets_not_used=True))
                else:
                    require(not text and not before, "Unexpected final output/buffer in bytewise reference")
                    pending = b""
                    finished = True
        status = "error" if failure is not None else "finished" if finished else "pending" if pending else "boundary"
        observations.append(dict(status=status, emitted_scalars=emitted, decoded_scalars=list(decoded),
            pending_hex=pending.hex(), pending_width=pending_width(pending),
            consumed_in_chunk=consumed - old_consumed, examined_in_chunk=examined - old_examined,
            consumed_total=consumed, examined_total=examined, unconsumed_hex=unconsumed.hex(),
            error=None if failure is None else dict(failure),
            finalization=("failed" if failure is not None else "succeeded") if final else "not_requested"))
    return observations, codec_errors


def main():
    started = time.monotonic()
    deadline = started + DEADLINE_SECONDS
    require(sys.flags.isolated and sys.dont_write_bytecode and sys.version_info[:3] == (3, 11, 15),
            "Accepted CPython3.11.15 -I -B required")
    require(not PROOF.exists(), "Reference proof already consumed; no automatic repeat")
    raw = FREEZE.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == FREEZE_SHA, "Frozen fixture decision differs")
    freeze = json.loads(raw)
    require(freeze["status"] == "frozen_model_independent_strict_UTF8_fixtures_before_adapter", "Fixtures not frozen")
    pins = {}
    for name, record in freeze["artifacts"].items():
        path = Path(record["path"])
        require(path.parent == HERE and path.name == name, "Frozen metadata locator outside current phase")
        data = path.read_bytes()
        require(len(data) == record["bytes"] and hashlib.sha256(data).hexdigest() == record["sha256"], "Frozen metadata changed: " + name)
        pins[name] = dict(record)
    require(pins["UTF8-ORACLE-SPEC-v2.md"]["sha256"] == SPEC_SHA and pins["UTF8-ORACLE-CORPUS-v2.json"]["sha256"] == CORPUS_SHA,
            "Exact reviewed semantic fixture pins differ")
    corpus = json.loads((HERE / "UTF8-ORACLE-CORPUS-v2.json").read_bytes())
    rows, mismatches, exceptions = [], [], []
    expected_steps = 0
    for case in corpus["cases"]:
        require(time.monotonic() < deadline, "Reference check exceeded20s budget")
        expected_steps += len(case["steps"])
        try:
            observed, errors = reference_steps(case)
            failures = []
            for index, (actual, step) in enumerate(zip(observed, case["steps"])):
                if canonical(actual) != canonical(step["expected"]):
                    mismatch = dict(id=case["id"], step=index, expected=step["expected"], actual=actual)
                    mismatches.append(mismatch)
                    failures.append(index)
            rows.append(dict(id=case["id"], steps=len(observed), matched=not failures, mismatched_steps=failures,
                observed_states_sha256=hashlib.sha256(canonical(observed).encode()).hexdigest(), codec_rejections=errors))
        except BaseException as error:
            exceptions.append(dict(id=case["id"], error_class=type(error).__name__, error=str(error)))
    # Verify required declared representative cut coverage without calling an encoder.
    by_id = {case["id"]: case for case in corpus["cases"]}
    interior = []
    for pair in corpus["expected_scalar_encoding_pairs"]:
        width = len(bytes.fromhex(pair["hex"]))
        require(2 <= width <= 4, "Declared representative width outside scope")
        for cut in range(1, width):
            identity = "interior/" + pair["id"] + "/" + str(cut)
            require(identity in by_id, "Missing declared interiorcut: " + identity)
            require(by_id[identity]["steps"][0]["chunk_hex"] == pair["hex"][:2 * cut], "Wrong interiorcut framing")
            interior.append(identity)
    require(len(corpus["cases"]) == 107 and expected_steps == 167, "Frozen fixture count differs")
    for name, record in pins.items():
        require(hashlib.sha256((HERE / name).read_bytes()).hexdigest() == record["sha256"], "Fixture changed during reference: " + name)
    require(hashlib.sha256(FREEZE.read_bytes()).hexdigest() == FREEZE_SHA, "Freeze changed during reference")
    elapsed = time.monotonic() - started
    status = "passed" if not mismatches and not exceptions and elapsed < DEADLINE_SECONDS and not DENIALS else "failed"
    proof = dict(schema_version=1, status=status, freeze_sha256=FREEZE_SHA, spec_sha256=SPEC_SHA, corpus_sha256=CORPUS_SHA,
        checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), CPython_version=sys.version,
        interpreter=sys.executable, elapsed_seconds=elapsed, budget_seconds=DEADLINE_SECONDS,
        fixtures=len(corpus["cases"]), steps=expected_steps, supplied_bytes=sum(len(bytes.fromhex(case["raw_hex"])) for case in corpus["cases"]),
        checked_interiorcuts=len(interior), cases=rows, mismatches=mismatches, exceptions=exceptions, pinned_metadata=pins,
        codec_reference="CPython strictutf-8 single-byte feeds and empty final requests; successful prefix/pre-call pending state only",
        chosen_contract="RFC-table first-error classification plus explicitly specified consumption/absorbing-tail policy; not inferred from codec posterror state",
        no_postexception_codec_state_or_recovery=True,
        adapter_API_type_afterfinal_immutability="Not executed: no production adapter exists; these chosen wrapper rules remain a later independent gate",
        vendor_algorithm_or_DLL_equivalence="Not tested or claimed", audit_denials=DENIALS,
        actual_adapter_imports=0, target_API_calls=0, vendor_extractions=0, compiler_calls=0, CPU_GGUF_oldpack_operations=0,
        scientific_or_native_qualification=False)
    with PROOF.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(proof, stream, indent=2)
        stream.write("\n")
    print(json.dumps(dict(status=status, fixtures=proof["fixtures"], steps=expected_steps, interiorcuts=len(interior),
                          mismatches=len(mismatches), exceptions=len(exceptions), elapsed_seconds=elapsed)))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
