# R08 bounded source-only qualification: two fixed contexts

**Development preparation completed; neither context is certified fresh or scientifically validated.** The prospective plan was written and hashed before any passage read: `bounded-source-plan-v1.json`, SHA256 `bf23203020e88c591512c64b81bfedf733b641bbf6b61f7c8e10a3f89992cdc2`. It pins final exposure-v4 SHA256 `7fa00b8859b8c196b429981d3e0a32ab45c068e79d08eb38053c1e3eb743905d` and selects the first two distinct target identity groups in approved-symbol/disease-ID order from the 25 conservative nonmatches. No model success, source conclusions or human answers determined selection.

| Fixed source-reporting context | Matching metadata rows in selected inventory | Fixed articles | Intact snippets | Words, including duplicates | Text duplicates |
|---|---:|---:|---:|---:|---:|
| BTK / psoriasis EFO_0000676 | 9 | 3 | 4 | 234 | 1 |
| CTLA4 / Crohn's disease EFO_0000384 | 18 | 3 | 4 | 119 | 0 |

Articles were fixed in evidence-ID/article-ID/original-locator order before reading text. All selected records' offered snippets fit the declared ceilings (three articles, six snippets, 1,500 source words per context). None was clipped, substituted or excluded after reading. No empty record or cap failure occurred. No explicit flagged GEO accession appeared in these eight snippets; their absence does not resolve prior article/cohort overlap. The other 6 BTK and 15 CTLA4 inventory rows were not inspected for text and remain outside this bounded sample. Actions, modalities and tissue remain null. These are question contexts, not new case files, model requests or development/confirmatory assignments.

The distinct denominators are **six selected evidence records, six distinct article identifiers, eight passage occurrences, and seven unique exact text strings**. Including the duplicate gives 353 source words; unique text gives 286. Different pointers on the duplicated BTK sentence do not create independent scientific evidence. `article-metadata-status.json` identifies each article, original record file and exact source-object JSON pointer without substituting or repairing text.

## Technical verification

All six source rows were projected by selected columns and selected at their exact row-group/row index in Arrow before Python conversion. Their metadata matched the earlier cache exactly. Six originals totaling **486,979,325 bytes** and their receipt digests were freshly rehashed again; the read/hash/extraction pass took **1.609 seconds**. The extraction retains original section names, text, target/disease offsets, list indices, article IDs, source hashes and exact text hashes. All original target/disease offset pairs are in bounds; interpreting them as zero-based half-open spans yields the recorded entity strings below. No passage was rewritten or entity pointer repaired.

The source objects and original selected records are retained under `data/cache/recovery-step8-bounded-sources-20261026/`, marked evaluation-only. Full question payload serialization/token capacity was not tested because no model request was created; snippet/word ceilings passed, not a complete prompt preflight. Source-only preparation does not automatically admit these cache artifacts into agent-visible manifests.

## Source-fidelity observations — AI development review, not an answer key

**BTK:** PMID 40571861 contributes a psoriasis comorbidity sentence whose target span is the abbreviation `AT`; the article identity concerns autoimmune polyglandular syndrome and GAD65-related epilepsy. PMID 32697884 also maps `AT` to the target in a sentence about angiotensin receptor notation. Neither offered sentence explicitly reports BTK. These are target-linkage concerns requiring review, not evidence of BTK absence or permission to relabel the target. PMID 31019502 explicitly includes BTK among B-cell-associated genes in a psoriasis transcriptome clustering statement; exactly the same sentence appears twice with different disease spans. Retain the duplicate, count it once for independent scientific content, and do not treat clustering as an intervention effect. The fixed BTK sample can test recognition of weak or mismapped evidence, but it does not supply an action/modality conclusion.

**CTLA4:** The snippets include a secondary statement about CTLA-4 genetic changes and early-onset Crohn's disease; a secondary statement concerning abatacept in an IBD clinical trial; a Chinese Han association-study methods excerpt with 68 IBD patients (14 Crohn's, 54 UC) and 140 controls; and a multi-disease genetic-cluster statement. These fragments do not provide complete results, effect estimates, uncertainty, variant details or an independently resolved intervention direction. The trial sentence is literal public literature content in the selected passage, not a protected outcome file or structured clinical-status column. No clinical conclusion is generated from it. Preserve that distinction in any later source-only question.

Some snippets contain literal HTML tags, which must be displayed as source text rather than executed markup or silently stripped. A console inspection briefly showed apparent mojibake because Windows default decoding was used; UTF-8-aware replay confirmed proper source apostrophes. No source encoding defect was found. Scientific sufficiency and applicability remain unadjudicated.

## Limited official metadata qualification

On 2026-10-26, four selected PMID identity/date records were readable through the web tool. This is a current metadata observation, not a historical version pin or replacement for the original source dates.

| PMID | Official identity/date result | Date qualification |
|---|---|---|
| [40571861](https://pubmed.ncbi.nlm.nih.gov/40571861/) | Autoimmune polyglandular syndrome and GAD65 related-temporal lobe epilepsy; DOI 10.1007/s10072-025-08330-4 | Epub 2025-06-26 matches the raw date; issue is October 2025. |
| [31019502](https://pubmed.ncbi.nlm.nih.gov/31019502/) | 2D Visualization of the Psoriasis Transcriptome Fails to Support the Existence of Dual-Secreting IL-17A/IL-22 Th17 T Cells; DOI 10.3389/fimmu.2019.00589; PMC6458264 | 2019-04-04 matches the raw date. |
| [32697884](https://pubmed.ncbi.nlm.nih.gov/32697884/) | The role of the renin-angiotensin system in skin physiology and pathophysiology; DOI 10.1111/exd.14159 | Official issue metadata gives September 2020, not an independently verified September 1 day. Preserve raw 2020-09-01 without asserting day precision. |
| [35784333](https://pubmed.ncbi.nlm.nih.gov/35784333/) | PubMed browser-check response; Europe PMC page unavailable through this tool | Current identity/date not verified; retain raw 2022-06-16 and PMC9243421 as source metadata. |
| [15059373](https://pubmed.ncbi.nlm.nih.gov/15059373/) | PubMed cache miss; Europe PMC page unavailable through this tool | Current identity/date not verified; retain raw 2004-03-01 without asserting independently verified day precision. |
| [22284131](https://pubmed.ncbi.nlm.nih.gov/22284131/) | Emerging patterns of genetic overlap across autoimmune disorders; DOI 10.1186/gm305; PMC3334554 | 2012-01-27 matches the raw date. |

The Europe PMC six-ID metadata API URL failed through the web tool; one bounded direct API request for 35784333 failed at DNS resolution in the default environment. No response body was downloaded by that attempt. Search fallback yielded no additional eligible selected-article metadata. No full article, account, paywall, new dataset or model was accessed. Current article-specific license details were not verified. The PubMed pages for 40571861 and 32697884 display publisher copyright notices; a copyright notice alone does not determine the permitted use of the already supplied OT snippets. Apply the separate [provider terms review](terms-review.md), retain attribution, and qualify the intended excerpt use without inventing a blanket legal prohibition or requiring whole articles by default.

## Completed versus unresolved

**Completed:** prospective v4 pin and deterministic selection; fixed six articles; original file/receipt hashes; exact row and snippet locators; duplicate and offset checks; intact bounded source extraction; four current metadata identity/date checks; explicit failure records for two current identity/date lookups; retained unknown exposure, rights and context. Old feasibility/date pins remain unchanged.

**Still unresolved:** prior article/cohort crosswalk and freshness; target-linkage quality; passage-specific intended-use qualification; two current metadata identities and day precision where unspecified; domain reviewer coverage and independent source-only judgments; scientific sufficiency; any full payload preflight. These limits are not repaired by the readable short excerpts.

The next human action is to recruit immunology/IBD/psoriasis and evidence-methods coverage, disclose prior exposure, and independently judge what these exact excerpts can support and what is missing, including the BTK entity ambiguity and duplicate. Do not give this AI assessment as a reference answer. Keep source-only references separate from future candidate ratings. If a context is judged insufficient, record that result without automatic replacement. No native generation or larger study is authorized by this preparation result.

This finite preparation can close as **technically extracted, scientifically unqualified at the declared bound**. The remaining bounded technical action, if pursued, is official metadata-only qualification for the same six fixed article identities/versions and intended snippet use, prioritizing the two failed identity lookups; retain any failures and do not replace sources. An independently qualified source-only reviewer remains the next scientific gate, not further model execution.
