# Independent verification of the finite native converter result

AI engineering review, 2026-10-28 UTC (2026-10-27 America/Los_Angeles). This review verifies retained evidence; it is not a human scientific review. The reviewer executed no native bridge, converter, vocabulary, tokenizer, model, server, network request or accepted framework test.

**The exact v3 finite converter gate closed negative, with intact retained evidence.** The typed-JSON roundtrip passed. The converter returned GBNF but explicitly warned that conversion was incomplete and that unsupported, unanchored patterns were being replaced by unrestricted strings. The protocol correctly stopped before vocabulary or grammar-corpus execution. Process exit code zero does not qualify the grammar.

## What was independently checked

The [read-only verification record](RESULT-VERIFICATION.json) covers the [original run](../../../data/cache/r09-finite-converter-execution-20261028T043655Z/terminal-report.json), exact protocol `a4f09687d19bc2803a4b419c6c707044d6f0097515a0f5778770563f0f267ce0`, all **48 receipted outputs**, the exact set of **50 run files**, and **150 external pin entries**. File contents, sizes and SHA-256 hashes match. The seal binds the receipt; `failure.json` is absent; the shared once-only claim identifies the journal's owner. The 14-event journal chain validates and agrees with terminal records, child PIDs, classifications and source hashes.

The receipt SHA-256 is `73c3f2bede92d2f51238831dea8012e3e4d20a0dd9655002d9f51432bdefcaa4`; seal SHA-256 is `2d1d4eff84ec786907fba754eb46c5db610463384708b2a5ba23869708866ffe`.

Both stages were checked beyond the runner's early negative-classification branch: their original input identities, native result JSON, stdout equality, output bytes, parent-attempt records, complete captures, and all reported native-module paths/hashes/sizes agree with the pinned protocol. Each stage reports the same five approved native libraries before and after its native call. Both owned children were reaped, exited zero and have no timeout, truncation, capture error or cleanup error. This is evidence from the bounded harness and recorded module snapshots, not an operating-system-wide sandbox or process attestation.

| Stage | Retained result | Child elapsed | Output |
|---|---|---:|---:|
| Typed roundtrip | Typed values and original fixture match; empty stderr | 0.094 s | 271 B |
| Schema conversion | `conversion_incomplete_warning`; 17 explicit warnings accepting any string | 0.078 s | 14,866 B GBNF |

The original 1,103,161-byte corpus remains hash-identical, contains 109 cases, and every stored schema has the original schema hash `a75dd967b16fd387da820e0bd90071aba511aee5363f700e9ac5849f8cc72911`. Both the archived conversion input and original source input match that hash. The warning is consistent with unanchored patterns present in the original schema. No corpus, schema, source/model asset or accepted artifact was edited by this reviewer.

## What this proves and what remains open

The actual pinned DLLs completed one typed-JSON roundtrip with normal C++ lifetimes for this fixture and environment. This resolves the earlier build-only uncertainty for that bounded call; it is not a general guarantee of C++ ABI compatibility.

Conversion is **not qualified**. The diagnostics explicitly describe weakened schema constraints. The 109 corpus cases were checked for preservation and schema identity, not executed against native grammar. `uniqueItems`, pattern/length behavior, vocabulary/EOG conformance and grammar rejection behavior remain untested. Do not treat a 14,866-byte grammar file as successful enforcement or advance it to a model run.

The terminal report records 1.172 seconds before sealing; the seal records 1.297 seconds at state creation, including 0.109 seconds of sealing. These values lie within this diagnostic's 120-second bound. No unavailable later completion timestamp is inferred. They do not resolve the separate 295.922/300-second simulated full-case resource risk, actual model startup/inference cost, or peak-memory requirements.

The original v2 attempt remains a separate preserved harness failure before native process creation. Its NUL-device guard defect and the pre-execution finalization-deadline correction are documented in [HARNESS-REVIEW.md](HARNESS-REVIEW.md); neither failure is hidden by v3's result.

## Consequence for the next step

Keep this gate closed negative and preserve the exact corpus and execution artifacts. Any schema/converter correction requires a separately versioned contract and evidence establishing constraint semantics; silently anchoring patterns, dropping constraints, forcing an alternate backend or repairing the corpus would change the tested question. Native grammar, vocabulary/EOG, model-quality, fresh-source and human-science gates remain separate. Whole R09 and the project remain incomplete.
