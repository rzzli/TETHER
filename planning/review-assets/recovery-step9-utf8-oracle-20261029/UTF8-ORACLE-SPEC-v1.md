# Strict UTF-8 byte/chunk oracle specification

This prospective, model-independent contract defines a small fixed engineering fixture set. It is separate from the failed native recognition pack, the vendor grammar decoder, JSON parsing, vocabulary selection and scientific evaluation. No native/model qualification follows from passing it. The original 189-case experiment and its two unavailable natural-prefix slots remain unchanged.

The byte bounds follow [RFC 3629, sections 3–4](https://www.rfc-editor.org/rfc/rfc3629.html). An independent reference check may use [Python 3.11 incremental decoders](https://docs.python.org/3.11/library/codecs.html#incrementaldecoder-objects), feeding individual bytes and inspecting pending state. Python is a reference, not the definition of this contract's error-consumption accounting. No adapter or decoder implementation is supplied at fixture freeze.

## Encoding rules

All numbers below denote unsigned byte values or Unicode scalar values. Accept exactly these sequences:

| Width | Lead | Second | Remaining |
|---|---|---|---|
| 1 | `00–7F` | — | — |
| 2 | `C2–DF` | `80–BF` | — |
| 3 | `E0` | `A0–BF` | `80–BF` |
| 3 | `E1–EC`, `EE–EF` | `80–BF` | `80–BF` |
| 3 | `ED` | `80–9F` | `80–BF` |
| 4 | `F0` | `90–BF` | `80–BF`, `80–BF` |
| 4 | `F1–F3` | `80–BF` | `80–BF`, `80–BF` |
| 4 | `F4` | `80–8F` | `80–BF`, `80–BF` |

The scalar is the concatenation of the lead's payload bits and six payload bits from each continuation. No normalization, replacement, BOM removal or recovery occurs. `00`, other ASCII controls and `7F` are valid UTF-8 scalar encodings. Noncharacters such as U+FDD0, U+FFFF and U+10FFFF are valid scalar encodings here. UTF-16 surrogate values are not scalars. An initial `EF BB BF` emits U+FEFF; this is UTF-8, not UTF-8-SIG.

## Incremental state and consumption

Each fixture starts with no pending bytes, no emitted scalars and zero counters. A step supplies a byte chunk and a Boolean `final`. The machine processes bytes in order and commits each completed scalar immediately. A valid scalar before a later error in the same chunk remains emitted; a chunk is not atomic.

`pending_hex` holds the accepted bytes of one unfinished scalar, including its lead. Consuming a byte means accepting it into that pending sequence or a completed scalar. Consumed bytes therefore include buffered legal prefix bytes; they are distinct from completed output. `pending_width` is the selected total width while pending exists, otherwise null. Empty nonfinal chunks change nothing.

The first offending byte is **examined but not consumed**. It is the first byte that violates the table at its current sequence position. Keep the previously accepted pending bytes as error evidence; emit no scalar for that incomplete sequence. `unconsumed_hex` contains that offending byte and the rest of the current chunk. Both counters stop at that point. The error is absorbing: later chunks are wholly unconsumed and unexamined, produce no output, preserve the original error and pending evidence, and cannot resume decoding. No automatic replacement or reset is offered.

`consumed_total` and `examined_total` count work across all steps, including pending bytes, not original lengths of chunks ignored after error. At a byte error, `examined_total = consumed_total + 1`. At an EOF error, the totals are equal. Per-step increments are `consumed_in_chunk` and `examined_in_chunk`. An ignored post-error chunk increments both by zero. The initial error's absolute `byte_offset` counts bytes before that byte in the stream before rejection; `sequence_start_offset` points to the buffered lead, or the offending byte when no sequence was pending. These offsets remain unchanged after error.

`final=true` requests end of stream after the current chunk's consumed bytes. With no error and no pending bytes it yields `finished`; no further steps are permitted after successful finalization. With an unfinished sequence it yields `error`/`premature_eof` at `byte_offset=consumed_total`, with no offending byte. The pending evidence stays intact and no extra byte is examined or consumed. An already rejected stream remains rejected when finalization is requested. `finalization` is a per-step outcome: `not_requested`, `succeeded` or `failed`.

## Exact error precedence

Reject the earliest offending byte; do not wait for the rest of a sequence:

1. At a sequence boundary, `80–BF` gives `unexpected_continuation`. `C0–C1` or `F5–FF` gives `invalid_lead`.
2. While pending, a byte outside `80–BF` gives `invalid_continuation`.
3. If it is the second byte, `E0 80–9F` and `F0 80–8F` give `overlong_sequence`; `ED A0–BF` gives `surrogate_scalar`; `F4 90–BF` gives `out_of_range_scalar`.
4. Otherwise accept the byte. Emit the scalar only when the selected width is complete.
5. At requested EOF, pending bytes give `premature_eof` if no earlier byte error occurred.

The exact error object is `{code, byte_offset, sequence_start_offset, offending_byte}`. `offending_byte` is an integer for byte errors and null for EOF. There is no error object in a nonerror state.

## Machine corpus interface

`UTF8-ORACLE-CORPUS-v1.json` contains stable fixture IDs and an ordered list of steps. Each case includes its stratum, purpose, authored expectation rule, concatenated `raw_hex`, SHA-256 of those exact bytes, cumulative chunk cuts, and all expected states. Empty chunks may repeat a cut. Cuts include bytes supplied after an absorbing error; these supplied offsets are distinct from consumed/examined counters.

Each step has `chunk_hex`, `final` and an `expected` object with exactly:

- `status`: `boundary`, `pending`, `error` or `finished`;
- `emitted_scalars`: scalars completed in this step, and `decoded_scalars`: cumulative committed output;
- `pending_hex`, `pending_width`;
- `consumed_in_chunk`, `examined_in_chunk`, `consumed_total`, `examined_total`;
- `unconsumed_hex`, `error`, `finalization`.

Scalar expectations are explicit integer values, not strings decoded by the implementation being tested. Hashes and chunk cuts are framing checks, not semantic oracles. The fixture generator only instantiates literal scalar/encoding pairs and authored states, computes byte lengths/hashes/cuts and serializes them. It contains no UTF-8 decoder, Python codec call or vendor adapter. Structural checks may validate schema, IDs, counts, bounds and arithmetic before semantic review. Independent reference decoding begins only after the spec and corpus hashes are frozen.

## Fixed strata and bounds

The corpus uses fixed encoding-rule strata, not observed model token IDs or convenient post-run boundaries:

- literal 2-, 3- and 4-byte scalar examples and encoding boundaries; every interior cut of each declared representative;
- byte-at-a-time multi-chunk completion, empty feeds, mixed complete scalars plus a pending tail, and finalization on a separate empty step;
- every interior truncated prefix of one representative at each width, with both same-chunk and separate EOF requests;
- invalid leading/continuation bytes, shortest-form violations, surrogate encodings, out-of-range encodings, valid output before an error, and absorbing error with ignored tails;
- independent ASCII JSON escape spellings and unfinished JSON prefixes. They decode as ordinary ASCII; the oracle does not interpret `\u` escapes or decide JSON/grammar membership.

Maximums are 128 fixtures, 1,024 steps, 128 supplied bytes per fixture and 32,768 supplied bytes in total. No combinatorial or million-case expansion is allowed. A failed fixture is reported under its frozen ID; it does not trigger corpus repair, favorable subset selection or a native retry.

## Evidence and limits

Retain the spec, literal fixture generator, corpus, generator provenance and structural-check report with hashes before any test adapter implementation. Independent semantic review must distinguish strict reference behavior from the chosen consumption contract and identify every disagreement before authorizing an adapter. Any later comparison with the exact vendor decoder is a separately declared profile: its NUL sentinel, permissive byte handling and different result shape are not silently converted into this strict oracle's state.

Passing this corpus establishes only agreement with these strict byte/chunk fixtures. It does not qualify DLL ABI, actual vocabulary token boundaries, EOG, full-vocabulary masks, inference, the 300-second scientific resource limit, model quality or biological conclusions.
