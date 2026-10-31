# Fixed Unicode controls for the actual v3 response grammar, revision 2

This is a **new source-only profile**, separate from the failed 189-case recognition experiment. It asks whether the exact v3 response grammar handles prescribed Unicode-containing full responses and rejects EOG at naturally occurring incomplete UTF-8 token-piece boundaries. No runtime, bridge, native pack, tokenizer or model work is authorized. The old profile, its unavailable BMP/astral slots and its failure remain unchanged.

## Actual questions and grammar instances

Use the packaged `synthetic-context` mechanism question and `synthetic-orientation` genetics question. Prepare each through the accepted `source-quote-interpretation-v3-gbnf` interface for two real initial stages: `asof_interpretation` index0 and `adapted_virtual_biotech_interpretation` index0 (`chief_of_staff`), with empty predecessor feedback. These are four stage/payload instances, possibly fewer unique grammar hashes. Duplicate grammar bytes must be disclosed rather than described as four independent languages.

Retain the complete synthetic request, registered question identity, exact stage and guide, quote catalog, full generated GBNF, payload and their fingerprints. The grammar comes from the actual accepted `strict-interpretation-gbnf-v1` builder; do not extract a permissive string rule or substitute a toy language. Every byte document is a full response in this interface. Generic fields are `claims[0].text`, `abstention_reason` and `unresolved[0]`; source-report controls exercise the exact source literal branch. Pure v3 validators check the expected semantic outcomes, but do not certify native grammar membership.

## Fixed input grid

The corpus contains84cases, declared before token observation:

| Stratum | Count | Construction |
|---|---:|---|
| Stage/source-report controls |4| One exact source report for each real stage instance |
| Scalar/field grid |42| Fourteen frozen UTF-8 oracle scalar/encoding pairs × three fixed field/context pairings |
| ASCII escape counterparts |14| Same decoded response as the first field/context case for each scalar, represented with ASCII JSON escapes |
| Mixed/normalization/escape controls |8| Numeric ascending/descending scalar chains, NFC/NFD text, quoting/backslash, escaped NUL, escaped less-than and short newline escape |
| Grammar/semantic/JSON controls |10| Fixed unknown reference, blank text, wrong literal, duplicate claim text, raw less-than, key order/spacing, raw newline, lone surrogate escape and duplicate object name |
| Byte-harness ineligibility controls |6| Raw NUL and five fixed malformed/incomplete UTF-8 documents |

This is a chosen grid, **not** a14×3field×3context factorial. Its pairings are: `claims[0].text = A + scalar + B`; `abstention_reason = X + scalar repeated8times + Y`; `unresolved[0] = e + U+0301 + A + scalar + U+1F600 + Z`. Stage assignment for the42cases is `(3*scalar_index + field_index) mod4`, using the frozen oracle pair order. An ASCII counterpart uses the same stage and decoded response as its raw claim-text case. Other controls have fixed explicit assignments.

Every case retains stable ID, stage/grammar ID, exact raw hex/byte count/SHA-256, expected decoded JSON when representable, strict project-JSON result, scalar-string eligibility, v3 semantic-validation result and generation-grammar membership expectation. These are separate dimensions. Pure semantic validation receives the exact raw bytes, never an already parsed/repaired object. For example, raw less-than can pass the semantic validator but lies outside the generation serialization domain; duplicate claim text can fit the grammar but fail the post-validation uniqueness rule. Raw NUL/malformed UTF-8 are harness dispositions with **null native membership**, not negative native experiments. ASCII escape spelling is not evidence of a raw multibyte boundary. Values outside strict parse or Unicode-scalar domains remain null with explicit reasons.

## Whole-corpus piece ledger

Any later authorized experiment evaluates all84cases once, preserving every outcome and every bounded token-piece ledger, including zero-length pieces. For a native-byte-eligible case it retains `token_ids`, `piece_byte_lengths` and `piece_hex` arrays of equal length, in original token order. Their concatenation must exactly equal the frozen raw document bytes; do not normalize, repair, re-tokenize, drop empty pieces or trim any array. The six declared harness-ineligible cases instead retain a null ledger, the exact harness reason and zero per-case document native calls. Their contribution to the predefined coverage population is zero by declaration, not a measured absence of boundaries. Unexpected QC/unknown cases retain null boundary counts, not zero.

For document length `B<=1024`, set `Ncap=min(65536,4*B+32)` before allocation. A larger reported token count is explicit failed QC, never a truncated ledger. Each piece length is at mostB, the total is exactlyB, every ID is within the observed vocabulary and ordinary document tokens contain no EOG. Retain zero-piece/zero-progress counts even though zero-length final pieces cannot qualify a coverage boundary. This is a profile-specific bound, not a universal claim that token count is bounded by byte count.

Compact JSON arrays have a conservative bound of `12*N + 3*B + 8192 + 64` bytes for a case row, including fixed field/counter overhead. At `B=1024,Ncap=4128`, this is60864bytes, below65536. Fixed overhead must be measured against the eventual exact row schema; exceeding any declared row bound fails explicitly. Across at most96cases and4selected prefixes, token work is at most412800 under these bounds, below the unchanged1,000,000limit.

Reserve the JSONL budget before execution: at most96case rows of65536bytes,96before-case rows of8192bytes,64stage rows of8192bytes,4selected-prefix rows of65536bytes and16global/footer rows of8192bytes. This totals7,995,392bytes, below8MiB, with at most276rows. Any required record that cannot fit causes an explicit incomplete/negative result; no silent deletion or cap increase is allowed.

## Boundary classes and deterministic selectors

Scalar byte intervals come from the frozen raw UTF-8 document and the independently qualified strict byte oracle, not from token IDs. A nonempty piece `j` occupies `[a,b)` in the exact concatenation. Consider it only when `0<b<B` andb lies strictly inside a scalar interval `[s,e)`, so `s<b<e`.

Required classes are `pending_width2`, `pending_width3`, `pending_width4` and `same_piece_complete_scalar_then_pending`. The width classes use `e-s`. The mixed class additionally requires a complete scalar interval `[u,v)` with `a<=u<v<=s`, wholly inside the **same** piece before the pending tail. A piece that merely finishes a scalar begun in an earlier piece and starts a new partial scalar does not qualify unless it also contains a separate whole scalar. ASCII width1 is a whole scalar for this rule; retain the full complete-width×pending-width matrix so that fact stays visible. Each matrix cell counts a qualifying boundary once per distinct contained complete-scalar width; repeated scalars of the same width do not multiply it. A boundary containing multiple complete widths can increment multiple cells, so the matrix sum can exceed the mixed-boundary total. Full piece arrays make all boundaries reconstructible. A selected record pins its piece interval, pending-scalar interval, all class labels and the earliest contained scalar witness for each distinct complete width.

Coverage population is fixed before measurement: cases expected to be native-byte eligible, generation members and v3-semantic eligible. Runtime membership success is not an additional selection filter. Record all boundaries for all cases, plus population/exclusion reasons, all per-case and global counts, zero-piece counts and any unknown count due to failed QC. A case mismatch is retained and makes the overall profile negative; it must not remove an inconvenient case from the ledger.

After scanning the entire fixed corpus, each class selects its lexicographically first `(case_ordinal,token_ordinal)` qualifying boundary. Class priority is width2,width3,width4,mixed. One boundary may carry multiple labels; de-duplicate equal `(case,token)` selections, test that prefix once and retain every class reference to it. There are at most four prefix sampler states. Use the original counted token prefix throughpiecej; **do not tokenize the incomplete byte prefix again**. All its ordinary tokens must be admitted, and every observed EOG must be rejected using the same full response grammar.

All required class counts must be known and positive. An unavailable class, unknown ledger, failed expected case outcome, failed selected prefix, missing case or missing record leaves this new profile negative or incomplete. Do not search beyond the frozen corpus, substitute a nearby scalar, revise context after token observation or rerun for a favorable result. The selector is prospective whole-corpus measurement, not permission for post-hoc corpus selection.

## Preserved limits and remaining gates

Keep the current ceilings:96profile cases within200, four stage grammars within20, token work1M, vocabulary262144, EOG64, JSONL8MiB, row64KiB, native pack20MiB, cooperative work117seconds, whole child120seconds, owner300seconds and process/job commit256MiB. This document does not show that actual hashing, vocabulary loading, measurement and sealing fit those limits.

Source/pure review and explicit fixture freeze precede bridge/pack/runtime implementation. A future exact source/ABI/parent/resource review and separate owner decision are still required. The distinct profile may establish new engineering observations; it cannot retroactively repair or replace the failed original experiment, establish full-vocabulary-mask behavior, model quality or scientific validity.
