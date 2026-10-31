"""Narrow CPython reference diagnosis: 512 fixed completion checks, not fixtures."""
import codecs
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "UTF8-ORACLE-CORPUS-v2.json"
CORPUS_SHA = "65428d32cc06c58836d1d541bde0e893db13cef9e5ae756e26d6e353908b302d"
FREEZE = HERE / "UTF8-ORACLE-FIXTURE-FREEZE-v2.json"
FREEZE_SHA = "285a46b3b7ac00cf7bbb0b262242ffc04f2c3049e4b7cf541dbcfdf0080f1eac"
PROOF = HERE / "UTF8-SURROGATE-NONEXTENDABILITY-CERTIFICATE-v1.json"
IDS = ("invalid/surrogate_low", "invalid/surrogate_high", "split_restricted/surrogate")


def main():
    started = time.monotonic()
    assert sys.flags.isolated and sys.dont_write_bytecode and sys.version_info[:3] == (3, 11, 15)
    raw = CORPUS.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CORPUS_SHA
    assert hashlib.sha256(FREEZE.read_bytes()).hexdigest() == FREEZE_SHA
    cases = {row["id"]: row for row in json.loads(raw)["cases"]}
    prefixes = sorted({bytes.fromhex(cases[identity]["raw_hex"])[:2].hex() for identity in IDS})
    assert prefixes == ["eda0", "edbf"]
    rows = []
    total_completion_calls = total_trace_calls = getstate_calls = 0
    for prefix in prefixes:
        data = bytes.fromhex(prefix)
        decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
        trace = []
        for chunk, final in ((data[:1], False), (data[1:], False), (b"", True)):
            before, flag = decoder.getstate(); getstate_calls += 1
            item = dict(input_hex=chunk.hex(), final=final, pre_pending_hex=before.hex(), pre_flag=flag)
            total_trace_calls += 1
            try:
                text = decoder.decode(chunk, final=final)
            except UnicodeDecodeError as error:
                item.update(outcome="raised", exception_class=type(error).__name__, reason=error.reason,
                            exception_start=error.start, exception_end=error.end, posterror_state_not_read=True)
                trace.append(item)
                break
            else:
                pending, flag = decoder.getstate(); getstate_calls += 1
                item.update(outcome="returned", emitted_scalars=[ord(c) for c in text], post_pending_hex=pending.hex(), post_flag=flag)
                trace.append(item)
        completions = []
        for third in range(256):
            assert time.monotonic() - started < 10, "Finite certificate deadline"
            candidate = data + bytes([third])
            total_completion_calls += 1
            try:
                text = candidate.decode("utf-8", "strict")
            except UnicodeDecodeError as error:
                item = dict(third_byte=third, input_hex=candidate.hex(), outcome="rejected",
                            exception_class=type(error).__name__, reason=error.reason,
                            exception_start=error.start, exception_end=error.end)
            else:
                item = dict(third_byte=third, input_hex=candidate.hex(), outcome="accepted", scalars=[ord(c) for c in text])
            completions.append(item)
        rejected = sum(item["outcome"] == "rejected" for item in completions)
        rows.append(dict(prefix_hex=prefix, fixture_ids=[identity for identity in IDS if cases[identity]["raw_hex"].startswith(prefix)],
                         bytewise_then_empty_final_trace=trace, completions=completions, rejected=rejected,
                         accepted=256-rejected, no_valid_third_byte_completion=(rejected == 256)))
    assert total_completion_calls == 512 and total_trace_calls == 6 and getstate_calls == 10
    assert hashlib.sha256(CORPUS.read_bytes()).hexdigest() == CORPUS_SHA
    status = "all_512_completions_rejected" if all(row["no_valid_third_byte_completion"] for row in rows) else "failed"
    proof = dict(schema_version=1, status=status, corpus_sha256=CORPUS_SHA, freeze_sha256=FREEZE_SHA,
                 helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), CPython_version=sys.version,
                 prefixes=rows, bounded_completion_decode_calls=total_completion_calls,
                 separate_probe_incremental_decode_calls=total_trace_calls, separate_probe_getstate_calls=getstate_calls,
                 elapsed_seconds=time.monotonic()-started, deadline_seconds=10,
                 findings="Nonfinal buffering/diagnostic timing is not the chosen earliest-error API contract. All possible third bytes are tested for these two fixed malformed prefixes only.",
                 new_corpus_fixtures=0, adapter_imports=0, vendor_or_native_calls=0, CPU_GGUF_oldpack_operations=0,
                 original_failed_reference_preserved=True, corpus_or_spec_edits=0)
    with PROOF.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(proof, stream, indent=2); stream.write("\n")
    print(json.dumps(dict(status=status, completion_calls=total_completion_calls, separate_trace_calls=total_trace_calls,
                          accepted=sum(row["accepted"] for row in rows), elapsed_seconds=proof["elapsed_seconds"])))
    return 0 if status == "all_512_completions_rejected" else 1


if __name__ == "__main__":
    raise SystemExit(main())
