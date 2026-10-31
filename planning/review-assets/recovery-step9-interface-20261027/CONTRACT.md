# R09 versioned interpretation interface and deterministic qualification

27 October 2026. Continue the authorized recovery plan, R09. Human reviews remain
pending. This interface work does not restart the failed R07 experiment or launch
a new native experiment, server, model acquisition or study.

## Concrete correction

Add `asof.study.interpretation_interface` with a distinct
`source-quote-interpretation-v2` identity. Preserve all old codec, payload and
native interfaces and their original failure records. Reuse current request
validation, stage/history validation and role definitions. Do not add a scheduler,
transport, scientific estimator, response converter or new source selection.

Offer the complete original request. A deterministic quote catalog binds Q0, Q1,
etc. to original source aliases, observation IDs, scientific-record-relative
RFC6901 pointers, full-request pointers, and UTF-8 text hashes/character counts.
The model cites quote IDs, not parallel source/pointer arrays or relocated view
paths. Only original statement and reported-passage choices are quotable. Catalog
order is original source order and existing quote-choice order, never relevance.
Cap the catalog at 256 entries and fail rather than silently selecting/truncating.

The response has answer_status, claims, unresolved and abstention_reason. Each
claim has kind, text, quote_refs and limitations. Keep the active three-claim
ceiling, at most two unique quote references per claim, 1,800-character text/list
strings, four limitations/unresolved items, and 512-character reason; inherited
lower claim caps remain lower. source_report copies one whole original string
and one quote ID. scientific_inference/caution remains authored text and needs
limitations. Exact materialized quotations are separate from generated assertions.
No repairs, clipping, inferred propositions, probabilities or prediction features.

The per-request JSON Schema and post-validator both enforce the three states:
answered has claims and a null reason; partial has claims and a nonblank reason;
abstained has no claims and a nonblank reason. Schema branches bind source reports
to exact quote/text pairs and restrict all quote IDs. Post-validation additionally
checks unique claim texts and anchored request/payload identity. Schema validity
does not prove scientific entailment. Native grammar support is not assumed.

API: `prepare_payload(request, arm, index, feedback)` returns a bound immutable
preparation; `request_from_payload(payload)` authenticates the entire renderer,
guide, quote catalog, roles, history and options; `validate_output(request,
payload, document)` retains original generated content and copies exact quoted
source strings into a distinct immutable result. Preparation is structural, not
source admission, accepted-history proof, token quotation or dispatch authority.
Internal quote-ID expansion reuses the existing strict flat state/text/literal
validator. It changes no generated assertion and cannot convert a retained R07
answer into a successful new response.
Existing source/lease/history/capacity layers must authorize any later execution.

Keep complete prompt32,768-byte and HTTP65,536-byte caps,1,024 output tokens,
temperature0/seed42/no prompt cache/no stream, source-control escaping and no
silent omission. No bound increases or changes to the default aggregate budget.

## Validation and version boundary

Write regressions before implementation. Check all state combinations, exact
source reports, unknown/duplicate references, inference limits, malformed JSON,
UTF-8/control escaping, nulls and full-source preservation, inherited bounds,
cross-request/payload/guide/options/history mutation, deep immutability and no
dispatch. Verify schema/state/pair fidelity using the existing PowerShell 7.6.5
Test-Json oracle in a separate offline qualification, not a second handwritten
schema validator. Retain oracle/version/input/output bytes and explicit limits.

Freeze0.3.8 only after focused regressions pass. Full regressions/probes/package,
unchanged code/protected hashes, dependency-free installed exercise, seven legacy
families and all seven matching preserved 0.3.1–0.3.7 verifiers are required for
engineering acceptance. Preserve the accepted0.3.7 wheel/profile before changes.
No new independent peer/scientific review is implied by code-author tests.

Subsequent work is adapter qualification and a separately declared finite native
experiment under R07 stop rules. Pending human references still gate scientific
usefulness, fresh R10/R12 studies and independent acceptance.

Schema references: [combination semantics](https://json-schema.org/understanding-json-schema/reference/combining),
[constant values](https://json-schema.org/understanding-json-schema/reference/const),
[PowerShell Test-Json documentation](https://github.com/MicrosoftDocs/PowerShell-Docs/blob/main/reference/7.6/Microsoft.PowerShell.Utility/Test-Json.md).
