# Evaluation-only atomic claim audit, version 1

This is preparation for the original full T6/H5 study. It validates source
bindings and review structure; it does not evaluate therapeutic truth, generate
interpretations, train a scorer or establish that a scientific review is correct.
All data supplied to this module must remain evaluator-only.

Entry point: `tools.science.t6_claim_audit.audit_claims(manifest, review, sources,
approved_roots)`. It returns a JSON-serializable descriptive report and writes
nothing. Tests in `tests/test_science_t6_claim_audit.py` contain a complete
synthetic example. There is no network client or model dispatch.

## Claim inventory

Use `schema_version: 1`, `role: evaluation_only`, a sealed `dossier_sha256`, an
identified `atomizer_id` and `atomization_status: reviewed_complete`. The `question`
contains the seven fields used by the runtime hypothesis fingerprint: target and
indication IDs, both namespace versions, intended action, modality and tissue.
Unspecified tissue is null. Hypothesis availability and source chronology remain
separate qualification requirements; this interface does not replace them.

Each ordered atomic claim has a unique `claim_id`, its exact `statement`, a
`kind` (`resource_observation` or `scientific_interpretation`), matching
`question_sha256`, `atomicity_attested: true` and `cited_source_ids`. Empty citations
are allowed so uncited claims cannot disappear from the audit denominator. Repeated
identical statements must be consolidated rather than inflating the denominator.

Complete atomization is a reviewer attestation, not automatic NLP validation.
This version checks the supplied dossier digest's syntax but does not open the
dossier, verify extraction completeness, or establish output-seal chronology.
A later integration must bind it to the actual frozen prediction receipt before
claiming an audited model run. Do not advertise this prototype as that integration.

## Original source references

Each source has a unique `source_id`, `format: json`, an `original` pin containing
absolute path/SHA256/byte length, an RFC6901 `json_pointer`, and `value_sha256`
computed using the runtime canonical fingerprint of the pointed-to value.

The function resolves paths beneath explicit approved roots, reads at most
64 MiB plus one sentinel byte per original, hashes the same bytes it parses,
rejects changed originals/rows and rejects duplicate hash/pointer evidence units.
It never treats a URL as an original. A pinned file is not proof of publisher
authenticity: official download receipts and lineage need separate qualification.
Different rows from one study are not automatically independent studies.

Version 1 intentionally accepts JSON originals only. Parquet and PDF fail
explicitly. A JSON extract of a Parquet row is not an original Parquet verification;
production Open Targets review therefore still needs a separately qualified
physical-row adapter. Do not convert a source to JSON just to evade that gate.

## Blinded review

A review uses `schema_version: 1`, `role: evaluation_only`, an identified
`reviewer_id`, `review_mode: blinded_source_review`, exact `claims_sha256` and
`sources_sha256`, and `therapeutic_truth: not_established`. Blinding is attested
here; a later executor must enforce arm anonymization and prediction/reference
seals. Two independent reviews and third adjudication remain study requirements;
this validator checks one review at a time and does not certify independence.

Every atomic claim appears exactly once in frozen order with:

| Field | Allowed values / purpose |
|---|---|
| `entailment` | `supported`, `contradicted`, `unsupported`, `unassessable` |
| `applicability` | `applicable`, `context_mismatch`, `uncertain`, `not_claimed` |
| `citation_status` | `supported`, `missing`, `misattributed`, `unassessable` |
| `uncertainty` | `low`, `moderate`, `high` |
| `reason` | Nonempty source-grounded rationale |
| `evidence_source_ids` | Distinct resolvable original rows used by the reviewer |

A substantive entailment judgment requires evidence. Supported citations require
supported entailment and an intersection with the claim's actual cited originals.
Missing citations must agree with the empty citation inventory. Interpretive
claims require a contextual applicability assessment. These are consistency checks;
the reviewer still decides whether source text entails the statement.

Report entailment, context and citations separately. A correct annotation may be
irrelevant to the intended intervention. A true uncited statement retains missing
citation status. Association does not establish clinical efficacy. Unsupported
does not mean false. Unassessable claims remain visible; an empty or wholly
unassessable dossier has null assessable-denominator fractions, not zero error.
An additional coverage/completeness reference is needed to prevent omission of
important evidence from rewarding a terse dossier.

## Scope of the returned report

The result records manifest/review/source fingerprints, total and assessable
claim counts, all disposition counts, and separate contradiction and unsupported
fractions among assessable claims. It does not call either fraction the original
H5 scientific error rate. No independent event count, preference p-value, clinical
probability, causal effect or numerical feature is computed.

Next integrations are output-seal binding, original columnar/PDF source adapters,
two-review/adjudication sealing, a completeness reference and a bounded
interpretation layer. Fresh question selection and frozen paired analysis must
precede any full quality experiment. Existing exposed cases remain development.


## Reuse path for original Open Targets verification

The repository already has production original-row checks in
`tools.science.reference_packets.audit_observation`, its mapping/source helpers,
and `tools.framework.run_pilot.SourceAudit.parquet_row`. These check archived
receipt identity, source hash, physical row group/offset, canonical mappings,
complete projection, preserved context and eligible lineage. The next adapter
should reuse that complete boundary and bind its result to this audit inventory.
A new JSON extract or a bare Parquet lookup must not replace those checks.
The current version has not integrated that adapter.
