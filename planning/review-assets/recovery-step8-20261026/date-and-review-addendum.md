# R08 date qualification and bounded source-only review addendum

This addendum preserves the initial feasibility report and every original pin. It analyzes cached metadata only; no source passages, model responses, protected outcomes or labels were read. No case was selected or frozen.

## Date findings

All 10,343 populated publicationDate values and all 10,343 populated evidenceDate values are valid ISO `YYYY-MM-DD` strings. Both fields are null on the remaining 70 rows. The two fields are equal on all 10,413 rows, including nulls; their agreement is not independent corroboration of chronology.

The 440 publicationYear/date-year disagreements involve 356 distinct literature identifiers, 35 preliminary target/concept combinations and 99 original shards. All are `europepmc/literature`: 239 rows in the original evidence directory and 201 in the supplemental directory. Exact per-shard paths, hashes and counts, affected combinations, year histograms and eleven records with differences greater than one year are retained in `data/cache/recovery-step8-date-followup-20261026/date-analysis.json`.

| publicationYear minus publicationDate year | Rows |
|---|---:|
| −1 | 106 |
| +1 | 323 |
| +2 | 4 |
| +3 | 1 |
| +27 | 1 |
| +34 | 4 |
| +36 | 1 |

The six differences exceeding three years include literature IDs 407624, 622045, 625917, 628096 (two rows), and 667056, whose date years are 1977–1978 while publicationYear is 2004–2014. This establishes disagreement between source fields, not which value is correct. Possible print/electronic indexing conventions cannot explain these records without checking their actual provenance; no such explanation is assumed. The 429 one-year disagreements likewise remain unresolved rather than automatically labeled ordinary online/print differences.

The affected publicationYear values span 2001–2025; corresponding date years span 1977–2025. Exact actual-year counts are in the JSON. No populated date is later than 2025-07-11 in this selected metadata frame, but a syntactically valid old date is not sufficient proof of correct article identity, historical availability or source eligibility.

## Explicit date policy before case freeze

1. Preserve publicationYear, publicationDate, evidenceDate, source IDs, original locators and download observations unchanged. Record a separate disagreement flag and resolution status. Do not overwrite a value, silently choose the earliest/latest field, or manufacture a single canonical publication date.
2. For a contemporary reporting exercise, verified public-download observations can establish that these particular bytes were available by the intended cutoff if the cutoff is no earlier than the observation. This permits a bounded availability claim; it does not resolve article chronology or establish historical eligibility. Preserve annotation and receipt lineage.
3. Any question whose answer depends on publication order, first discovery, pre-cutoff article timing or replication chronology requires source-specific date/identity qualification first. When conflicting date intervals cross the cutoff, or identity is uncertain, chronology-dependent use is ineligible or explicitly unresolved. Do not cure this by backdating current metadata.
4. A later correction must be a separately pinned source/version and derivation with an explanation, leaving the old values intact. Bibliographic correction requires an authorized source lookup or provided verified metadata; a human's recollection is insufficient. Do not infer a chronology answer from the repeated evidenceDate field.
5. Date disagreement alone must not become a post-output exclusion. Predeclare the treatment before selecting sources and generating candidates. Source-only reviewers may identify uncertainty, but they should not be asked to invent missing dates.

## RA and rights clarification

The owner case pack identifies **EFO_0000685** as the intended rheumatoid arthritis concept. **HP_0001370 is an alternate concept and must not inflate the number of independent candidate cases.** Retain its metadata for mapping and dependence audit; do not automatically merge or relabel its rows into EFO_0000685. The intended unselected frame is therefore 14 targets × four disease concepts, or 56 combinations, not 70 independent cases. This is a clarification of the frame, not approval of any case or a claim of freshness.

The root coordinator has now verified current official HGNC CC0 terms at https://hgnc.genenames.org/about/license/ and current OT data CC0 terms at https://platform-docs.opentargets.org/licence . The retained [terms review](terms-review.md) and [scope record](terms-review.json) document that evidence. OT's table also states that listed providers agreed to unrestricted use for Platform users, while identifying publication-dependent Europe PMC licenses. This supersedes the initial report's unresolved current HGNC provider-terms statement without rewriting the sealed catalog or proving historical terms. Per-publication excerpt/full-text rights remain separate; a PMC identifier does not itself license reuse. This is not a finding that existing snippets violate terms or a blanket legal block. Bounded existing snippets can suffice when their provenance, permitted use and scientific context support the question; full-article acquisition is not required for every review.

## Minimum bounded passage-review preparation

The existing Parquet schema contains `textMiningSentences`, a list of structs with `text`, `section`, `tStart`, `tEnd`, `dStart`, and `dEnd`. Schema inspection confirms a possible passage carrier only: it does not establish populated text, valid offsets, complete paragraphs, scientific sufficiency, or passage rights. No text was loaded for this addendum. Current ingestion has a 64 MiB packet ceiling; that is an engineering maximum, not a reviewer-friendly reading target.

After exposure reconciliation and reviewer-domain coverage, prepare a small **source-only** qualification sample with a declared deterministic ordering and documented stop conditions. A practical proposed ceiling is two proposed case questions, at most three distinct article IDs per question, up to six intact source excerpts per question and at most 1,500 source words per question. These are preparation proposals, not frozen case/sample sizes or implemented selection rules. If preserving a meaningful unit plus essential context exceeds a cap, mark the source review infeasible at that bound or explicitly amend the preparation budget before generation; never clip text silently. Do not fill six slots by repeating the same article or counting HP/EFO aliases as independent material.

Each displayed passage needs the original article/reference IDs, source-file hash, row-group/row index, list-element index, exact passage text/hash, reported section and original offsets, date values with disagreement flags, observed availability, annotation version and reuse status. Offset semantics must be checked against exact source text; offsets alone cannot justify extracting or repairing content. Preserve a source-count denominator and record omitted/unavailable material. Unknown study design, species, tissue, scale, uncertainty, intervention direction or modality remains unknown unless the actual supplied passage states it.

The coordinator should ask a domain-matched scientist to confirm expertise and prior exposure, then independently review only these sources and the explicit question: (a) what the excerpts directly report; (b) what context or uncertainty is missing; (c) whether discovery/replication and direction can be distinguished; (d) whether the proposed question is answerable within this bounded material; and (e) what additional source would be necessary. Include cannot-assess/outside-expertise choices, rationale, conflicts and actual elapsed time. The coordinator must arrange two independent references for a case before later candidate exposure; this document is neither a human response nor an AI answer key.

No source-only packet or response payload was created here. Freshness, article-level chronology/identity where needed, passage qualification, rights, bounded payload preflight and HR3 coverage remain gates. Current metadata availability is sufficient to begin that preparation once those decisions are supplied, but it does not itself qualify a study case or scientific conclusion.
