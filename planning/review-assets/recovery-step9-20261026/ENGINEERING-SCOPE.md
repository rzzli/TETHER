# R09 finite engineering scope — synthetic deterministic baselines

Date: 2026-10-26. Status: implementation authorized; acceptance pending tests and
installed verification. **R09 remains partial.** This is engineering preparation,
not a new scientific experiment, real-case candidate run or comparator result.

The controlling recovery plan permits engineering while human reviews are pending.
R07's negative native disposition remains in force: no retry, response repair,
native expansion or twenty-case generation. R08's two contexts remain unqualified;
the shared article and all source selections are retained without replacement.

Before changes, the frozen installed 0.3.1 native verifier passed with live project
source reads, repository imports, archived execution and dispatch guarded:
`frozen-r07-verification-before-v2.json`. This does not by itself accept 0.3.2 or
replace the required post-change compatibility checks.

## Exact implementation boundary

One new packaged baseline module exposes:

```python
run_baseline(request, policy) -> frozen_result
verify_baseline(request, policy, result) -> bool
reviewer_view(result, neutral_label) -> frozen_view
```

Policy fields are exactly `schema_version` (1), `method` (`extractive` or
`lexical`), `query` (null for extractive; explicit string for lexical),
`max_excerpts` (nonnegative integer), `max_quote_bytes`, `max_request_bytes` and
`max_result_bytes` (positive integers). Booleans do not count as integers.
Request/result caps are at most 1 MiB; the quotation cap is at most 8,192 bytes.
The request cap measures canonical request bytes; the separately bounded query
is at most 8,192 UTF-8 bytes. The excerpt count also respects the request's limit.
Empty lexical queries and zero excerpt limits have explicit empty-selection
outcomes; no fallback, inferred query or silent budget enlargement is permitted.

Public execution accepts only the two hash-authenticated packaged synthetic
fixtures, by exact complete request fingerprint. A `SYNTHETIC:` namespace,
`known_source` label, self-reported source role or rehashed modified request is
not admission. Each fixture's source-record fingerprint and exact synthetic
source-reference shape must also match. Internal pure helpers may exercise
invented Unicode/boundary values in tests without admitting new executable cases.
No additional real-data fixture or agent-visible manifest is created.

Reuse installed `diagnostic_codec.validate_request`, canonical serialization,
fingerprinting/freezing and authenticated resource loading. The existing validator
checks structure and binding, not temporal eligibility or complete source lineage.
Do not advertise it as real-source admission or recursively interpret prose words
as metadata roles. Any later real-source route needs its own admitted lineage.

Only original `/statement` strings are eligible in this version. Copy full UTF-8
strings, record original pointers, source identities, byte spans and text hashes;
do not normalize, clip, summarize or complete copied text. Rank by stable source
identity, with a declared lexical token-overlap rule and deterministic tie-breaks.
Lexical tokens are unique Unicode `\w+` matches after NFKC normalization and
casefolding, used for ranking only; zero-overlap statements are explicitly omitted.
Scores are selection metadata, not biological support. Preserve repeated text
with distinct provenance, missing-input declarations and explicit exclusions.

The separate result contract contains literal excerpts and **empty generated
interpretation**. Extraction states describe selection coverage; they do not claim
that a scientific question was answered. Numerical prediction features remain
empty, probabilities null, absence claims false. Check the entire canonical input
and result envelopes against their byte bounds, including audit/escaping overhead.
Full-envelope overflow fails without dropping fields until it fits.

## Accounting, replay and reviewer projection

This scope selects **pure computation plus exact recomputation verification**.
It supersedes the draft's optional StudySession/backend-adapter proposal.
Do not invent prompts, output-token reservations, billed calls or model dispatches
to fit the model-oriented session interface. Actual model calls, model tokens and
provider spending are zero; local runtime/bytes may be measured separately.

The coordinator's small, separate fixture writer may reuse `atomic.publish_bytes`
and existing static file/package proofs. It is not another workflow controller,
does not import repository tools/planning as runtime dependencies and cannot run
real cases. Archived proof data is never executed. Verification reconstructs the
expected result and compares canonical content; merely resealing altered outputs
does not make them valid.

Reviewer projection first verifies the result against its authenticated fixture.
It exposes only a neutral externally assigned label, literal sources and honest
coverage/interpretation absence. Arm identity, lexical scores and the mapping key
remain outside the reviewer view. This demonstrates maskability mechanically;
an extractive format may still reveal its method. No human submission is implied.

## Acceptance and remaining gates

Required regressions cover altered/rehashed fixture and evaluator-role inputs;
source identity and UTF-8 fidelity; deterministic ties; exact request, quote and
result bounds; zero query/zero limit/missingness; altered result/state/accounting;
resource tampering; and verified reviewer projection. Independent tests must probe
the public boundary, not simply restate private helpers. Installed fixture
execution must avoid repository runtime imports and preserve frozen R07 replay.

This work addresses deterministic parts of R09.1–R09.6 only. Fixed-input lexical
selection is not end-to-end retrieval. Generated interpretation, the adapted
Virtual Biotech arm, qualified real-source interfaces, matched scientific budgets,
fresh-case eligibility, independent references and masked human comparison remain
open. No full Virtual Biotech reproduction, scientific usefulness, H5 completion
or permission to restart the native route follows from passing these fixtures.
