# Schema-oracle disposition: a qualified alternative with explicit limits

28 October 2026 UTC. This disposition reads retained results only; no oracle,
strict-validator, grammar or model call was repeated. The independently prepared
cached **jsonschema 4.26.0** reference passes **162 typed schema comparisons and
16 separate Unicode-length controls**. This qualifies that exact alternative
reference for this frozen scope. It is not proof of universal engine correctness.

The original PowerShell [comparison](../../../data/cache/r09-generation-corpus-extension-v1-20261028/CORPUS-COMPARISON.json)
remains `expectation_mismatch_stop`; its [terminal record](../../../data/cache/r09-generation-corpus-extension-v1-20261028/COMPARISON-TERMINAL.json)
remains `failed`. Neither observation is overwritten or relabeled. Both the
original 109 documents and the separate 58-case extension, including their authored
expectations, remain byte-for-byte unchanged.

## Evidence and length decision

The [once-only parent receipt](../../../data/cache/r09-jsonschema-reference-parent-20261028/receipt.json)
has SHA-256 `18764b64c8829d2905ab14d1605d6b34d16673d52e6bdb3f92c3bb79bca7fd5e`;
the [reference result](../../../data/cache/r09-jsonschema-reference-batch-20261028/REFERENCE-BATCH-RESULT.json)
has SHA-256 `1fa0be7bb260e95e200902311af3c0d18ae31014dd904609ba35ff7ca948e164`.
One child exited zero and was reaped, with empty stderr, no capture overflow,
timeout, cleanup errors or guard attempts. Child qualification took 0.265 seconds;
the parent recorded 1.954 seconds before sealing. These are tool timings, not
native model or complete-case resource measurements.

For `extension/combining_over_1800`, 901 repetitions of `e` plus U+0301 contain
**1,802 decoded code points**. The alternative reference rejects it, agreeing with
the frozen expectation, strict validator and pure grammar. All 16 diagnostic
controls also match their prospective labels, covering empty/ASCII strings,
astral scalars, combining sequences, precomposed characters and mixed forms.

The exact [cached implementation](C:/Users/zzric/AppData/Local/uv/cache/archive-v0/k5zMh1I94cktfILjawn79/jsonschema/_keywords.py:231)
uses Python `len` for string bounds. The [earlier length note](SCHEMA-LENGTH-DISCREPANCY-NOTE.md)
links the JSON Schema specification and independent Ajv documentation supporting
the declared character metric. Those documents support the metric; they do not
diagnose the PowerShell implementation. Its internal root cause remains
unconfirmed. No normalization, changed limit, altered label, corpus replacement
or PowerShell rerun follows from this disposition.

## Five parsing edge cases remain outside the graded agreement

There is **no claim of agreement on all 167 schema observations**. The reference
uses Python JSON parsing and records five separately identified edge cases:
three unpaired/reversed surrogate strings and two duplicate-key documents.
Its parser retains non-scalar strings and keeps the last duplicate-key value;
the resulting instances pass schema validation. PowerShell, strict validation
and pure grammar reject those five original documents. These outcomes are all
retained, with the five cases excluded from the 162 typed comparisons.

This difference demonstrates that instance-schema validation does not establish
the project's wire parsing contract. The strict duplicate-key/scalar checks remain
mandatory. Two duplicate-claim-text cases also remain the explicitly documented
post-validation-only uniqueness exception; passing schema or grammar does not
authorize their acceptance.

## Scope and remaining gates

The alternative ran in a separate environment assembled from the existing
139 RECORD-qualified files, with an explicitly denied reference retriever and
network/dispatch guards. Its import and reference-extension ABI returned in this
environment; that does not establish arbitrary binary compatibility. Project
runtime dependencies and old accepted artifacts remain outside this tool scope.

The [machine disposition](SCHEMA-ORACLE-DISPOSITION.json) binds both outcomes and
the frozen input hashes. The existing [future native manifest](../../../data/cache/r09-generation-corpus-extension-v1-20261028/FUTURE-NATIVE-CORPUS-MANIFEST.json)
is unchanged and still denies execution authority. This disposition supports a
scoped pure schema-reference qualification only. Actual GBNF parsing, vocabulary
tokenization/EOG, prefix-stack performance, full-case timing, human review and
scientific validation remain separate gates. No llama, vocabulary, model, tokenizer,
inference, server or provider call occurred in this reference batch.
