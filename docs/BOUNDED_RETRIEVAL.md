# TETHER — Bounded retrieval and interpretation preparation

TETHER (Target Evidence Tracking Harness for Evaluation and Reproducibility) is the current project name. The `tether-target-agents` 0.4.0 package in `packages/tether` supplies the `tether` CLI and import namespace over the frozen AsOf 0.3.11 engine. See [installation and compatibility](../README.md#installation-and-compatibility). Historical version/arm names, module commands, source paths and wire IDs below remain unchanged; the rename does not reactivate retired study or expert-review branches. Direct API aliases preserve legacy outputs; only the separate `tether._presentation` CLI layer wraps `demo`/`run` in the [TETHER run layout](../README.md#tether-cli-run-layout). Delegated source inspection, snapshot construction and evaluation keep their engine layouts.

AsOf 0.3.5 adds a receipt-bound bridge from an explicitly qualified candidate
universe to original-record interpretation requests. It is a collected-corpus
preparation track. It does not reproduce open-web search, original Virtual
Biotech tool access or scientific evaluation.

## Public interfaces

`asof.study.retrieval_preparation` provides:

- `fixture_authority(name)` and `authority_anchor(authority)` for the explicitly
  invented packaged corpus and its declared empty/oversized variants.
- `policy_for(strategy)` for the two versioned deterministic policies.
- `qualify_universe(authority, anchor, roots=..., deadline=...)` to reauthenticate
  the whole declared universe. A serialized dictionary or Python type is not
  source authority.
- `retrieve(...)` and `compile_retrieved(...)` to select whole records and compile
  original fields. Public inputs are copied/frozen before checking and use.
- `prepare_retrieval(...)` and `verify_retrieval_preparation(...)` for exclusive
  artifact publication and read-only replay with external receipt/authority hashes.

The initial limit is one category and at most 16 declared candidates. Every field
that can influence ranking must be qualified, including later excluded candidates.
No failed candidate is silently replaced or removed from an allegedly complete
universe. Protected parent paths are rejected before parent receipt reads.

Invented records are authenticated against immutable source-only package resources
and clearly marked invented. Their dates, methods, citations and lineage strings
are not real historical evidence or download receipts. Real records require a
fresh current-package source-preparation parent, full original-row and mapping
replay, exact grounded fingerprints and bounded receipt-checked buffers. Old
package receipts fail current admission; no automatic frozen-verifier fallback is
introduced. Real replay retains the optional `pyarrow==21.0.0` requirement.

## Policies and preserved data

`id_order_v1` orders candidates by observation ID. The existing
`literal_case_overlap_then_id_v1` ranks unique `[a-z0-9_]{3,}` tokens from case JSON
against statement tokens, then ID. It is not question relevance, biological
evidence strength, a provider score or a prediction feature. Both policies use
the same two-record and 12,000-byte canonical request limits. They report whole
record exclusions; they never clip a source to make it fit.

Retrieval views may contain transient feature-applicability metadata. Selected IDs
are resolved back to original records. Compilation preserves every original
scientific field, citation, statement and grounded fingerprint, in parent source
order. Retrieval rank order is retained separately. The compiled real request
preserves parent availability/missingness denominators; bridge-specific candidate,
qualified, selected and excluded counts have their own manifest.

An empty declared universe, all records exceeding a bound and failed qualification
are distinct states. Empty selections retain coverage and no fabricated scientific
answer. Incomplete collection or nonselection is never biological absence.

## Recorded integration

The installed finite integration is:

```powershell
python -m asof.study.retrieval_smoke smoke --output NEW_DIRECTORY
python -m asof.study.retrieval_smoke verify --path DIRECTORY --sha256 EXTERNAL_ANCHOR
```

Two retrieval preparations and two scripted consumer cells share one unchanged
default case budget/deadline. The cells reuse `StudySession`, the recorded adapter,
strict response validation and whole-source payload rendering. Source-report
text and exact quotations remain distinct from authored inference. Evaluator-only
stimuli are excluded from source resources and prompts. Existing baseline and
fixed-evidence fixture allowlists are unchanged.

Four-arm access manifests are preparation metadata. Only two recorded consumer
cells execute, one per policy; this is not four-arm execution or observed model
performance. The fixture declares 128 input/128 output usage in total, while actual
model usage is zero. Conservative reservations are 15,656 input/2,048 output. No
native server, model, tokenizer or network is used. Default runtime dependencies
remain empty. Replay never dispatches or executes archived code.

## Accepted evidence and remaining scope

The [0.3.5 acceptance](../planning/review-assets/recovery-step9-retrieval-20261026/acceptance.json)
passes **1,616 full tests, zero failures/errors/skips**, 34 retrieval tests including
seven independent peer tests, required probes/package checks and seven installed
legacy families. All 305 code/resource pins and both protected hashes stay unchanged
during validation. A restored integration verifies with the original bundle and
live code unavailable. Matching frozen 0.3.1–0.3.4 verifiers still pass.

The nontrivial invented corpus has six records and produces different pairs under
the two policies. A separately declared current-parent check uses only the same
single exposed IL6R record, reconstructing request `14b735ef...f2d61a`. Both policies
select that record and preserve nine available observations and 65 missing inputs.
This is actual-format adapter verification, not a nontrivial real retrieval study,
new source universe, biological adjudication or case-freshness qualification.

The separately accepted [0.3.6 four-arm composition](AUTHORITY_FOUR_ARM_COMPARISON.md)
now connects one invented subset to six recorded cells and two pure baselines.
It passes 1,646 full tests, current exact-token proofs, installed/restored replay
and matching older verifiers. The original 0.3.5 access manifests remain
preparation metadata. Default byte-capacity behavior remains unchanged; the new
path requires explicit trusted current token authority. Scientific real-access
evaluation remains unfinished; the later five-record mechanics check is below.
Human references, fresh-case qualification, native activation and H5 scientific
claims stay gated. Numerical features remain empty and clinical probabilities null.

## Five existing real candidates — 27 October

The [real-data acceptance](../planning/review-assets/recovery-step9-real-retrieval-20261027/acceptance.json)
uses all five existing literature records in the same exposed IL6R case. A fresh
current-package parent reconstructs every original row and eligible ancestor,
including later-excluded candidates. Parent availability remains nine and missing
inputs 65. The unchanged 0.3.6 APIs and two fixed policies pass source-inclusive
replay and an isolated installed verification with the existing optional Arrow 21.
No new source download, runtime change, tokenizer or model generation occurred.

Both policies select the same one record. Two candidates exceed 12,000 bytes even
alone; three fit individually, but no pair with the selected record fits. The
four exclusions therefore include cumulative size limits, not just individual
oversize. Source records are not clipped to force success. This is nontrivial
candidate admission/selection, not evidence that ranking is scientifically good
or coverage is sufficient. The [closeout and bound diagnostic](../planning/review-assets/recovery-step9-real-retrieval-20261027/CLOSEOUT.md)
retain this design limitation. Scientific evaluation and native generation retain
their source/reference, fresh-frame and model-quality prerequisites. Pending
human reviews do not prevent recorded engineering integration.

The subsequent [0.3.7 collected-source composition](AUTHORITY_FOUR_ARM_COMPARISON.md)
now executes this selected subset through six recorded stages and two pure
results with fresh source parents and token proofs. Source-inclusive installed
replay and run relocation pass; the old invented-only request gate is no longer
required for explicit collected input. Candidate count 5, selected count 1, parent
availability 9 and missing 65 remain unchanged. Source statements are copied as
evaluator fixtures, not interpreted or independently assessed.
