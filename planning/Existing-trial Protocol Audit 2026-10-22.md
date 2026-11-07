# Existing-trial protocol/SAP audit — October 22, 2026

The selected NCT05997277 document has been collected and reviewed. It supplies
the primary endpoint, treatment design and statistical provisions that were
previously missing from the retained sources. It does **not yet qualify a complete
primary efficacy decision rule, authentic prespecification or historical public
availability**. Clinical labels, features and probabilities remain unchanged.

## Source and execution

The [frozen request](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/protocols/existing-trial-protocol-audit-v0.1.json) selects only
`Prot_SAP_002.pdf` from previously retained, exact-trial registry API bytes. The
request and code were committed/pushed at `2d6a0cc` before the single PDF request.
No API refresh, search query, version replacement or retry occurred.

The source is3,658,121 bytes, SHA256
`d269854eb493c785bafe84e16549e2477bcdcd7d21073df16d173c1183165a39`.
Both original and final URL match the selected registry version. The source,
receipt, control, lineage and hash-chained completion records are retained under
`data/benchmark/labels/registry-protocol-audit-20261021/build-v1/`. This is a newly
sealed source hash, not a claimed match to previously held original bytes.

The version verifier now anchors a new-source receipt to its completed transport
journal and checks the frozen transport recipe. Independent probes reproduced
ten failing subtests before correction. All eleven new tests pass, and the full
suite passes **658 tests**. Dependency-free validation passes with57 expected
ingestion skips; packaging, the installed offline demo, verification probes and
all four hosted Windows/Linux jobs pass for `2d6a0cc`.

All20 physical PDF pages were extracted with pinned pypdf6.1.1; no failed or blank
pages were dropped. The source inserts spaces within words, so a separate local
visual supplement renders all20 pages with isolated PyMuPDF1.26.4. It preserves
the initial extraction unchanged. The package is research tooling, not a runtime
dependency; its source/version and file hashes are retained. See the
[official release record](https://pypi.org/project/pymupdf/1.26.4/).

Two fresh-context AI reviewers read every page and sealed independent drafts
before accessing any other current rating. They then checked eight and twelve
page images respectively and sealed visual addenda. A third agent independently
verified the original, extraction, lineage and source-page assertions. These are
technical/source reviews, not independent biological truth.

## Scientific findings

Physical PDF page numbers below include the cover; printed form pagination is
one less on the19-page investigator form.

| Finding | Source and implication |
|---|---|
| Trial and regimen | Cover and design sections link the document to NCT05997277;6mg deucravacitinib twice daily for16weeks versus placebo aligns with the selected origin arm. Version/approval and full population equivalence remain partial. PDF1,5,15–16. |
| Primary endpoint | Participant abscess/inflammatory-nodule count change from baseline to week16 is primary. Binary HiSCR response is secondary. PDF2,7–8,14. |
| Primary analysis | A repeated-measures linear mixed-effects model is named. The full analysis set requires a dose, baseline count and a post-baseline count. The full contrast, model specification and intercurrent-event estimand are not established. PDF14–15. |
| Statistical threshold | Alpha0.05 appears in sample-size planning using a two-sample t test. This is separate from the named primary mixed-model analysis; a full primary rejection rule, sidedness and multiplicity procedure were not observed. PDF14. |
| Planning assumptions |30planned participants,20active/10placebo and reported0.87power are assumptions, not observed outcomes or validated project power. PDF14. |
| Missingness/rescue | Rescue and withdrawal provisions exist, including a rescued-lesion accounting instruction. Complete missing-data assumptions, primary intercurrent-event handling and sensitivity analyses remain unresolved. PDF10,13–15,19–20. |
| Internal inconsistencies | One assessment paragraph names minocycline despite the placebo design. Secondary HiSCR language also contains inclusive/strict50-percent threshold tension. Neither was silently corrected or promoted to a primary decision rule. PDF8–9,14. |
| Version timing | The internal revision date is March22,2024. Unverified PDF metadata describes a January2026 export and February2026 modification. Those facts neither prove nor refute earlier existence/adoption of the text. No executed adoption or actual analysis/unblinding chronology resolves prespecification. PDF1–2,19–20. |
| Historical public access | Internal dates, current upload metadata and this download do not independently establish public availability of this exact source by April1,2026. That remains a separate evidence question. |

Reviewers agreed on eleven of twelve rubric dispositions. For the decision-rule
axis, one rated the missing complete rule unresolved; the other rated the
identifiable assessment timing partial. Reconciliation preserves both: endpoint
timing/model information is partial, while the complete primary decision rule
remains unqualified. Both visual addenda corrected their own description of the
revision-date location from header to footer where visible; substantive ratings
did not change. Original drafts remain sealed.

## Disposition and sequencing disclosure

This is a useful source gap closure, not an efficacy result. No trial-level
decision date or polarity was inferred. Old36 and later36 endpoint artifacts
retain their frozen hashes. The next12 cohort remains inactive and unsealed;
no origin-closure step, fitting, genetics, model call or predictor change occurred.

There was one disclosed sequencing error. After initially restricting next-step
investigation to schema/manifests, root asked the verifier to inspect two retained
single-trial document-metadata fields, then sent a correction to await a frozen
request. The correction arrived after the read. The bounded peek and row
locators are retained in `sequencing-disclosure.json`; no outcomes, other trial
contents, database query or network request were inspected. The follow-up
metadata check must be described as an exposed validation, not a prospective or
blinded test. An empty array will not become a claim of global nonavailability.

## Next step

Validate only this trial's `documents`/`provided_documents` fields from the already
retained January/April2026 extraction. First verify that the fields were actually
queried: the extraction code can emit empty placeholders for absent source
tables/columns. Check request projection, schema, source/repeat hashes and record
version eligibility before interpreting empty arrays. No new DB session or data
download is needed for that bounded diagnostic. Its result will distinguish
missing extraction coverage from a queried snapshot without matching document
rows; neither proves no public document existed elsewhere.

Any needed restore query, historical record retrieval, additional protocol
version or actual result/analysis-date research requires a separately frozen
request. Clinical/source-readiness activation remains withheld until those
scientific requirements are met.

The final acceptance, hosted-job evidence and bounded E: backup receipt are in
`planning/review-assets/registry-protocol-audit-20261021/`. The next diagnostic
will retain its own policy, exposure disclosure, validation and disposition.
