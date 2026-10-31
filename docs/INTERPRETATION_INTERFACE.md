# Original-path interpretation interface

Introduced and accepted in AsOf 0.3.8; retained in 0.3.10. This pure interface prepares prompts and
validates replies. It does not admit evidence, prove history, quote token usage,
start a model, contact a server or establish scientific truth. R07's original
interfaces and failed outputs remain unchanged.

The separate [native integration](NATIVE_INTERPRETATION.md), including the 0.3.10 duration correction, is qualified with
simulated transport and explicit source/history/token authority. It does not
qualify actual native grammar or model quality. Pure preparation alone grants
none of that execution authority.

## Use with an independently authorized source request

```python
from asof.study.interpretation_interface import (
    prepare_payload, request_from_payload, validate_output,
)

prepared = prepare_payload(question_request, "asof_interpretation", 0, [])
payload = prepared["payload"]
assert not prepared["execution_authorized"]
original = request_from_payload(payload)
# response_bytes must be retained unchanged by an independently authorized adapter.
result = validate_output(original, payload, response_bytes)
```

The request uses the existing question/source contract. Preparation supports the
existing one AsOf/five adapted Virtual Biotech stages and exact source-ID history
shape. It reuses those bounds and role definitions. The full original request
remains in the prompt, including context, coverage, nulls and unknowns. Inputs
support one to three source aliases; limits fail explicitly rather than silently
dropping sources, statements or context. Caller-provided history is structurally
checked but is not proof that a prior stage was accepted.

## Quote identities and authored assertions

A deterministic quote catalog assigns Q0, Q1 and subsequent IDs to original
statements and reported text passages. Each entry records the source alias,
observation ID, scientific-record-relative pointer, full-original-request pointer,
UTF-8 text hash and character count. Order follows original sources and existing
quote-choice order, never inferred relevance. The catalog is capped at 256 entries.
This avoids pairing separate source/pointer arrays or asking for original paths
after moving the quoted fields into another view.

Replies contain `answer_status`, `claims`, `unresolved`, `abstention_reason`.
Each claim contains `kind`, `text`, `quote_refs`, `limitations`. A `source_report`
must copy one whole original string and one quote ID. A `scientific_inference`
or `caution` is authored text and needs limitations. The returned result preserves
that text and the original response object; a separate `quotes` array copies
exact original strings. It creates no propositions, resolves no scientific
ambiguity and repairs no assertion. Features stay empty and probabilities null.

## Shared schema and post-validation rules

| State | Claims | Reason |
|---|---|---|
| answered | Nonempty | null |
| partial | Nonempty | Nonblank, at most 512 characters |
| abstained | Empty | Nonblank, at most 512 characters |

The active claim limit is `min(3, inherited max_claims)`; each claim has one or two
distinct quote IDs. Text and list strings are nonblank and at most 1,800 characters;
limitations and unresolved arrays have at most four entries. Source-report
text/reference pairs are bound by per-request schema constants and independently
checked against originals. Unknown references, extra fields, malformed or
duplicate-key JSON and contradictory states fail. Cross-claim text uniqueness
and request/payload binding are post-validation checks; schema alone does not
establish them or scientific entailment.

The explicit Unicode whitespace pattern matches the Python nonblank rule. The
initial `\S` shorthand differed in the external schema engine and was corrected,
with the initial failing report retained. This does not imply that the native
runtime's schema-to-grammar converter implements the same behavior.

Full prompt and HTTP limits remain 32,768/65,536 bytes with 1,024 output tokens,
temperature 0, seed 42, no prompt caching/streaming and escaped source control
delimiters. Payload replay reconstructs the entire guide, stage, history, quote
catalog, schema and options. No global case budget or default byte admission
policy is changed.

## Validation status and next integration

Twenty-one new tests and 33 focused codec/legacy regressions pass. A separate
105-case installed PowerShell 7.6.5/JsonSchema.NET oracle checks states, quote/text
pairs, bounds and all 29 Python whitespace codepoints in text and reasons. Its
one declared difference is cross-claim text uniqueness. The executable and loaded
library versions/hashes are retained. Full validation passes 1,681 tests with no
failures/errors/skips and 316 unchanged code/resource pins. Twelve installed stage
preparations check all three response states; seven legacy families and all seven
matching 0.3.1–0.3.7 verifiers pass. [Acceptance evidence](../planning/review-assets/recovery-step9-interface-20261027/acceptance.json)
preserves the original failures and stated limits.
No new independent peer or scientific review is claimed.

The [contract](../planning/review-assets/recovery-step9-interface-20261027/CONTRACT.md)
and [next adapter design](../planning/review-assets/recovery-step9-interface-20261027/NEXT-ADAPTER-DESIGN.md)
require explicit current source/history/token authority, owned transport and
durable accounting before any future execution. Pending human references and
source/question sufficiency remain separate scientific requirements.

Schema semantics follow the official [combination reference](https://json-schema.org/understanding-json-schema/reference/combining)
and [constant-value reference](https://json-schema.org/understanding-json-schema/reference/const).
The external oracle uses the existing [PowerShell Test-Json implementation](https://github.com/MicrosoftDocs/PowerShell-Docs/blob/main/reference/7.6/Microsoft.PowerShell.Utility/Test-Json.md).
