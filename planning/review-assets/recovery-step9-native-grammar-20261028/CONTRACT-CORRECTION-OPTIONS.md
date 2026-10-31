# Conditional contract correction options

**Conditional on the actual converter result. This is not execution, repair or
retry authorization.** A pre-native harness failure says nothing about converter
behavior. Inspect the retained once-only unchanged-schema result before selecting
any correction. No source, frozen corpus or historical output is changed here.

If the approved converter emits an incomplete-conversion warning, fails, returns
empty grammar or selects an unsupported backend, retain that negative disposition
and stop before vocabulary loading. Preserve the exact schema, binary/header
hashes, stdout/stderr, failure/accounting and original 109 cases. Do not silently
anchor a pattern, remove keywords, normalize an answer or repeat the same version.

## What the next version must preserve

| Requirement | Where it belongs |
|---|---|
| Exact fields/types, answer-state combinations, list/claim bounds, permitted quote IDs, literal source-report text/ID pairs, nonblank strings, codepoint lengths and distinct quote references | Expressible in the standard acceptance schema, with strict post-validation retained. Each native-generation constraint needs independent qualification; JSON Schema expressibility does not prove converter support. |
| Unique claim texts across otherwise different objects; serialized byte caps; request/payload fingerprints; trusted source/lineage/history/quote bindings; null probabilities and empty features | Trusted post-validator/controller invariants. Whole-object `uniqueItems` cannot express uniqueness of one property across claims. A generated JSON object cannot prove its own evidence authority. |
| Scientific entailment, source sufficiency, intervention interpretation, biological/clinical usefulness | Scientific evaluation and independent references; neither schema nor exact quotations establishes these. |

The [current renderer](D:/Projects/drug_target_agents/src/asof/study/interpretation_interface.py:67)
and [post-validator](D:/Projects/drug_target_agents/src/asof/study/interpretation_interface.py:255)
already separate some of these. Preserve authored text and exact quote materialization;
rejection must remain rejection. The reused
[flat validator](D:/Projects/drug_target_agents/src/asof/study/diagnostic.py:143)
checks answer states, text limits, distinct claim texts and verbatim reports.

## Correction choices

Prefer a separately versioned generation contract whose native grammar deliberately
encodes the required generation constraints, while keeping the complete acceptance
schema/post-validator. If the pinned JSON-schema converter cannot represent them,
an explicit deterministic GBNF renderer may be necessary. Specify its supported
serialization domain, Unicode/escape semantics, size limits and native checks;
do not label a finite canonical-document check as universal JSON-language equivalence.
Preserve all allowed one/two-reference combinations and original text, rather than
reducing capabilities to make the grammar easier.

Alternatively, explicitly moving constraints to post-validation would require a
prospective protocol amendment, a declared enforcement boundary and measured
rejection cost. It would **not** complete the existing full native-conformance
claim. Removing unsupported keywords just to obtain a successful conversion is
not the recommended correction.

Any correction needs a new renderer/interface identity, payload fingerprints,
quoted capacity and matching verification/version boundary. Retain old wheels,
receipts and failed results. Changing this pure machinery does not authorize a
new model batch or repair the R07 result.

## Pitfalls to resolve before implementing

- **Anchoring:** the acceptance pattern searches for at least one non-whitespace
  character. Simply adding anchors can change that meaning. The
  [exact converter](D:/Projects/drug_target_agents/data/cache/r09-native-converter-source-20261028T030704Z/sources/common/json-schema-to-grammar.cpp:406)
  requires anchors and can replace unsupported patterns with a broad string rule
  plus warning. Its pattern branch also precedes separate length handling
  [here](D:/Projects/drug_target_agents/data/cache/r09-native-converter-source-20261028T030704Z/sources/common/json-schema-to-grammar.cpp:933).
  Anchoring alone therefore does not establish bounded nonblank-string semantics.
- **Lengths:** distinguish decoded Unicode codepoints, UTF-8 bytes, UTF-16 units
  and JSON escape spellings. The native string atom can count separate surrogate
  escapes differently from one raw astral character. Combining marks must not be
  silently normalized. Whole-response byte limits remain independently enforced.
- **Reference uniqueness:** the
  [array node](D:/Projects/drug_target_agents/data/cache/r09-native-converter-source-20261028T030704Z/sources/common/json-schema.h:165)
  stores item/count constraints, not uniqueness. For a finite quote catalog and
  at most two references, explicit permitted ordered sequences are possible, but
  size grows with the catalog. Preserve existing preflight limits and fail oversized
  schemas/grammars explicitly; never prune IDs or source records silently.
- **Tokenizer/EOG:** grammar initialization is not complete-document acceptance;
  empty grammar creates a no-op sampler. Require exact UTF-8 token round trips,
  per-token filtering, complete-input and incomplete-prefix EOG controls. Report
  vocabulary-only loading separately from tensors, inference and servers. Never
  accept a rejected EOG token; the
  [native path](D:/Projects/drug_target_agents/data/cache/r09-native-grammar-source-20261028T020623Z/sources/src/llama-grammar.cpp:1402)
  can abort. Character EOF tests do not replace actual-vocabulary EOG checks.

## Required next-version validation

Keep the 109 old cases unchanged and add a separately frozen extension: all answer
states; missing/extra fields; valid and mismatched literal/ID pairs; duplicate refs
and duplicate claim text; ASCII/astral bounds; every current whitespace character;
raw versus escaped astral/whitespace strings; combining marks; DEL; malformed or
unpaired Unicode; truncation, trailing material and EOG at incomplete prefixes.
Include maximum catalog/grammar/payload bounds, unknown-backend/empty-grammar
rejection and warning/failure stopping with zero vocabulary/inference calls.

Recheck independent schema results, trusted post-validation and actual pinned
native conversion/acceptance separately. Preserve mismatches rather than replacing
cases. Then run affected framework, installed/relocated and matching archived-version
checks. No automatic retry follows a failed gate.

This model-free engineering work can proceed while human reviews are pending.
It does not qualify fresh scientific cases, source/question fit, R10/R12, causal
genetics, clinical probabilities or independent biological conclusions.
