# Frozen extension: comparison stopped on a schema-oracle discrepancy

28 October 2026 UTC. The [prospective protocol](CORPUS-EXTENSION-PROTOCOL.md)
produced a separate **58-case** extension and compared it alongside the unchanged
original **109 cases**. This is pure engineering evidence. No native grammar,
vocabulary, tokenizer, model, inference, server or scientific evaluation ran.

**The comparison is not a clean pass.** All 167 strict-validator expectations and
all 58 authored extension generation-membership expectations match. The independent
pinned PowerShell schema oracle has one unexpected acceptance; the retained report
and terminal record say `expectation_mismatch_stop` and `failed`, respectively.
Do not reinterpret those records as a passing schema qualification.

## Inputs and execution

The original file remains SHA-256
`01286d35689c7005ea67fa817c4b4098cecd05c4233c3949e7ec744bc5f5d97a`.
Its documents were replayed in their original serialized bytes. The current base
acceptance schema matches the old pinned schema exactly, SHA-256
`a75dd967b16fd387da820e0bd90071aba511aee5363f700e9ac5849f8cc72911`.

The new corpus uses `generation-domain-extension-v1`, with the base synthetic-context
request and one separately tagged fixed synthetic source-literal variant. Original
serialized extension documents, authored expectations, requests, payloads, acceptance
schemas and grammars were frozen before oracle execution. The [frozen manifest](../../../data/cache/r09-generation-corpus-extension-v1-20261028/FROZEN-INPUTS.json)
has SHA-256 `1b80e365e42b28fe237c22fc35e215d1a0410729203a77255fc628309a9da414`.

An initial Python helper launch failed during isolated-mode sibling import, before
an execution plan or any child. Its [failure](CORPUS-HARNESS-PREEXECUTION-FAILURE.json)
is retained. Adding the explicit local helper directory corrected the harness;
no corpus bytes or expectations changed. The schema oracle then ran **once**:
PowerShell 7.6.5, exact pinned script/executable/four assemblies, one child, 0.820
seconds, exit zero, 9,704 stdout bytes, empty stderr and no timeout. The complete
comparison took 10.622 seconds. There was no second schema-oracle attempt.

## Observed agreement and discrepancy

Across all 167 cases, schema acceptance is 52, strict acceptance 49 and pure
generation membership 44. Counts differ for documented reasons; none is a measure
of scientific correctness. The [per-case results](../../../data/cache/r09-generation-corpus-extension-v1-20261028/COMPARISON-RESULTS.json)
preserve authored labels separately from all three observations.

The unexpected case is `extension/combining_over_1800`: the literal sequence
`e` followed by U+0301 COMBINING ACUTE ACCENT, repeated 901 times. It contains
**1,802 decoded Unicode code points**. The pinned `Test-Json` tool accepts the
schema with `maxLength: 1800`; the strict validator and the pure grammar both reject
it, matching the frozen authored expectation. A grapheme-counting implementation
could explain this pattern, but its cause has **not** been established from source.
This observation does not justify normalization, changing the bound, rewriting
the corpus or treating the schema oracle as authoritative for this length case.

Seven extension documents are strict-valid but outside the declared generation
serialization domain: raw less-than/delimiter spellings, leading/trailing document
whitespace, alternate root-key order, and two alternate known-literal spellings.
Their decoded values remain valid; their original bytes were not canonicalized.
Both original and extension duplicate-claim-text cases pass schema/pure grammar
and fail strict validation, as the documented post-validation-only exception.
All five deliberately unspecified schema parse-edge cases—three invalid surrogate
forms and two duplicate-key documents—were rejected by all three checks.

## Retained evidence and next disposition

The [comparison report](../../../data/cache/r09-generation-corpus-extension-v1-20261028/CORPUS-COMPARISON.json)
has SHA-256 `1e812ea6c82a3e85e1def4fba6b0d5d5c095d3b02c7d7060767f50297affde59`.
The [future native-corpus manifest](../../../data/cache/r09-generation-corpus-extension-v1-20261028/FUTURE-NATIVE-CORPUS-MANIFEST.json)
has SHA-256 `43aa4b18d3d9c7393198d0eaa93095999d1ef54f0d2757ffe6265c7d95a26e4a`.
It preserves original document locators/hashes and variant schema/grammar bindings;
it explicitly denies execution authorization. Original109 generation membership
is observed replay evidence, not a retroactively authored gold label.

Independent review should disposition the schema-tool discrepancy before declaring
this comparison qualified. Any further diagnostic needs its own prospective scope;
the one-child batch is spent. The complete strict validator remains mandatory.
The restricted interpreter is not actual DLL parsing, tokenization/EOG, prefix-stack
performance or case-runtime feasibility evidence. Native and scientific gates remain
pending, with no permission to retry the closed converter or activate a model route.
