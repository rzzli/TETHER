# Synthetic deterministic baselines

The 0.3.2 engineering slice adds pure extraction and lexical selection for two
authenticated, invented source fixtures. It supplies part of recovery R09. Real
source admission, generated interpretation, adapted Virtual Biotech, end-to-end
retrieval and scientific comparison remain separate unfinished requirements.
The stopped R07 native experiment is preserved without retry or answer repair.

## Public interface

`asof.study.baselines.run_baseline(request, policy)` returns an immutable result.
`verify_baseline(request, policy, result)` recomputes it against the caller's
expected request and policy. `reviewer_view(result, neutral_label)` verifies the
result before projecting literal sources and coverage under a label from
`Candidate A` through `Candidate Z`. A label or recognizable extractive format
does not establish blinded review.

Public execution accepts only the complete authenticated requests returned by
`load_synthetic_request("synthetic-context")` or
`load_synthetic_request("synthetic-orientation")`. Self-reported source roles,
synthetic-looking identifiers or a rehashed modified record do not authorize
another request. The reused structural question validator does not establish
real-data admission, temporal eligibility or scientific relevance.

Supply exactly these policy fields:

| Field | Meaning |
|---|---|
| `schema_version` | Integer 1 |
| `method` | `extractive` or `lexical` |
| `query` | Null for extractive; explicit string for lexical |
| `max_excerpts` | Integer 0–64, within the source request's claim bound |
| `max_quote_bytes` | Positive UTF-8 byte ceiling, at most 8,192 |
| `max_request_bytes` | Positive complete canonical-request byte ceiling, at most 1 MiB |
| `max_result_bytes` | Positive complete canonical-result byte ceiling, at most 1 MiB |

Booleans are not integer budgets. Input/output byte limits include framing and
audit metadata; whole-envelope overflow fails. Individual oversized statements
receive an explicit omission reason. No quote is clipped to fit.

## Selection and meaning

Only the source record's original `/statement` string is offered in this version.
Nested text-mining passages are outside this interface. Extraction orders by
observation identity and pointer. Lexical selection ranks unique token-set
intersection with the explicit query, then uses the same stable tie-break.
The tokenizer uses Unicode NFKC normalization, casefolding and Python Unicode
word tokens for ranking only. It does not stem, expand biomedical synonyms or
use provider scores. Zero overlap is an explicit nonselection, with no fallback.

Copied quotation text retains its original Unicode and literal markup. Each
excerpt binds observation identity, original pointer, source fingerprint,
character/UTF-8 spans and text hash. Repeated strings retain distinct provenance.
Trace records distinguish empty text, excessive size, zero overlap and count
limits. Original missing-input declarations remain separate from selected counts;
nonselection cannot establish biological absence.

`extraction_state` describes literal selection coverage. The scientific answer
status is `not_attempted`; generated interpretations and prediction features are
empty, and clinical probability is null. Model calls, model tokens and provider
spending are zero. CPU time and energy are not measured by the pure API. It uses
no model-oriented StudySession reservation or fabricated prompt/token accounting.

## Installed fixture check

```powershell
python -m asof.study.baseline_smoke smoke --output data/cache/baselines-example
python -m asof.study.baseline_smoke verify --path data/cache/baselines-example --sha256 YOUR_RETAINED_SHA256
```

Use a new output directory. The command creates four deterministic results:
two source fixtures × two methods. It records their complete source requests,
policies, results, reviewer projections, fixed evaluator assignment and zero
model accounting. Reviewer files are separate from the assignment key; do not
distribute the whole internal bundle as a masked scientific review packet. The
fixture labels are fixed, not randomized.

Atomic publication preserves existing destinations and concurrent-output safety.
Failures retain partial files and a best-effort failure marker; interruption and
the primary error propagate. There is no retry/resume or real-case input mode.
Verification requires an externally retained receipt SHA256, exact member
inventory, matching trusted package/resources and deterministic recomputation.
Resealing changed results, accounting, policy, views or assignments cannot make
them semantically valid. Archived code is never imported by this verifier.

## Preservation and remaining gates

The R07 receipt binds 0.3.1. Its reviewed wheel and prior profile are retained at
`data/reference/recovery-r07-verifier-031-20261026/`. Explicitly run the reviewed
installed 0.3.1 verifier when checking that old native experiment; 0.3.2 does not
pretend to match the old package fingerprint. The retained guard helper under
`planning/review-assets/recovery-step9-20261026/verify_frozen_r07.py` proves that
check without live source imports, archived-code execution or dispatch. Original
source paths remain required; this is not independent new-format relocation.

R09 as a whole remains open. A later real-source path needs admitted lineage,
qualified scope and complete payload budgets. Fresh evaluation requires source
references before generation, appropriate comparator adaptation and independent
human review. These synthetic fixture checks establish engineering behavior,
not source sufficiency, biological truth, model capacity or H5 superiority.
