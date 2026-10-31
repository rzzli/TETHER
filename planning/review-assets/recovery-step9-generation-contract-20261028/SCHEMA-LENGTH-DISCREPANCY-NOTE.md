# Schema-tool length discrepancy: investigation, not a passing disposition

28 October 2026 UTC. The frozen [corpus result](CORPUS-EXTENSION-RESULT.md)
retains the original PowerShell batch and its stopped comparison. Do not replace
its observations, rerun that batch or change the original/extension documents.

One case contains 901 repetitions of `e` plus U+0301: 1,802 decoded code points.
The declared project limit is 1,800 code points. Strict post-validation and the
pure production interpreter reject it; pinned PowerShell Test-Json accepts it.
No cause inside the PowerShell/schema implementation has been established.
Grapheme counting is a possible explanation, not a demonstrated root cause.

The project's decoded-character metric remains unchanged. The
[JSON Schema validation specification](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.3.1)
defines string length through RFC 8259 characters. The independent
[Ajv implementation documentation](https://ajv.js.org/json-schema.html#maxlength--minlength)
explicitly distinguishes combining clusters from a single code point and counts
a Unicode surrogate pair as one character. These sources support the project's
chosen metric; documentation is not execution evidence for either local engine.
No Unicode normalization, larger bound or altered authored expectation is justified.

Bounded [cache discovery](SCHEMA-REFERENCE-ENGINE-DISCOVERY.md) and
[read-only qualification](CACHED-REFERENCE-QUALIFICATION.json) identify an existing
jsonschema 4.26.0 dependency closure: six distributions, 139 RECORD-verified files,
including a CPython 3.11 x64 rpds extension. The exact cached implementation uses
Python `len` for min/max length and dispatches the enforcing keywords used here.
This is source evidence; import/ABI and corpus validation are not yet established.

A separate prospective protocol will assemble only these existing verified files
in an isolated ignored test environment, preserving the project environment and
empty default-runtime dependency list. It must deny reference retrieval and
network/child/model access. The frozen 167 cases must all remain represented.
Schema expectations apply to the 162 typed comparisons; the five deliberately
unspecified parse-edge cases require separately reported parser/schema outcomes,
without borrowing the trusted post-parser as independent gold. Extra Unicode
length controls may be added only in a separately identified diagnostic input.

Retain both engines' results, even if they disagree. Acceptance requires a reviewed
disposition of the disagreement and the new full/installed/compatibility checks;
it cannot be inferred from a replacement engine's name or source alone. Native
GBNF/vocabulary/EOG, full-case timing and human scientific gates remain separate.
