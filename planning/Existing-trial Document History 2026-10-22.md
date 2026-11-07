# Existing-trial document metadata — October 22, 2026

The next bounded diagnostic is complete. Neither the retained January1 nor
April1,2026 extraction contains a document row for NCT05997277. Both document
tables were explicitly queried with their full available schema; these empty
arrays are **not missing-table placeholders**. They do not establish global
nonavailability, a clinical outcome or historical access to the newly collected
protocol/SAP.

## Method and exposure

The [local validation policy](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/protocols/existing-trial-document-history-v0.1.json)
was committed/pushed at `e27a24b` before independent revalidation. An earlier
root-authorized metadata peek is disclosed and remains immutable. This is
exposed validation, not a prospective/blinded experiment. The technical verifier
who performed that peek independently reconstructed root's execution, but is
not an unexposed reviewer.

The job verified the complete retained source and repeated-extraction hashes,
original request regeneration, schema/projection coverage, exact selected line,
byte offset, row hash and trial identity. It then read only the frozen trial's
posting fields and `documents`/`provided_documents`. It did not open results,
other trial contents, a database or a network source. Six synthetic checks
exercise empty-versus-unprojected data, missing arrays, wrong trial, future
posting dates and nonabsence semantics. No runtime/package code changed in this
diagnostic; the earlier658-test/four-CI checkpoint remains the framework result.

## Retained findings

| Snapshot | Record last update / type | `documents` | `provided_documents` | Exact selected PDF URL |
|---|---|---|---|---|
| January1,2026 | May7,2025 / ACTUAL | Queried;0 rows | Queried;0 rows | Not recovered |
| April1,2026 | May7,2025 / ACTUAL | Queried;0 rows | Queried;0 rows | Not recovered |

The first-posted field is August18,2023 in both rows. Under the existing
date-only offset-envelope policy, both record versions pass the inherited
April1,2026 eligibility cutoff. That status is reconstructed date eligibility;
it is not exact historical public-timestamp or original-PDF-byte qualification.

Both parent requests contain all six `documents` columns and eight
`provided_documents` columns. Neither table appears in missing-source-column
metadata. The repeated full frames match byte-for-byte. Selected rows retain
line9/offset102643 in January and line9/offset107879 in April, with their own
row hashes and source/report/request provenance. The original archive/restore
lineage is inherited from the retained extraction; no bulk dump rehash or new
database query was performed here.

An empty selected table can reflect collection, registry-version or source
coverage limitations. This diagnostic cannot distinguish all such causes or
say whether the PDF was available through another channel. Current API upload
metadata, internal revision dates and the present PDF hash cannot fill that
historical evidence gap. No newer consent/protocol version was substituted.

## Disposition and next priority

The prior [protocol audit](Existing-trial%20Protocol%20Audit%202026-10-22.md)
supports endpoint/model provisions but not a complete primary decision rule,
authentic adoption-before-analysis or historical public availability. This
diagnostic leaves those scientific holds in place. Old36 and later36 label
artifacts remain unchanged. No next12 membership, cohort activation, scorer,
features, probabilities or clinical efficacy result was introduced.

The next useful step is a separately frozen **single-trial public chronology
and primary-report search**: reconcile document submission/upload versus public
posting/version history, then look for the authentic primary report and analysis
or unblinding chronology. Keep occurrence, decision and disclosure separate and
retain access failures. Do not expand the cohort or revise the cutoff merely
because this channel did not recover historical documents. An additional local
restore query is unnecessary to repeat the already queried empty fields; it
would need a distinct source-gap hypothesis and bounded request.

Artifacts and independent reconstruction are retained under
`data/benchmark/labels/registry-document-history-20261022/`. Acceptance and the
verified E: backup receipt are in the corresponding planning review-assets
folder. This phase used0 new source downloads,0 network requests,0 database
queries and$0 provider spending; it establishes metadata coverage, not clinical
scientific validity.
