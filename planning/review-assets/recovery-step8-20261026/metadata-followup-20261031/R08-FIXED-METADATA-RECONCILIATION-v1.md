# R08 fixed-article metadata reconciliation — 31 October 2026 UTC

**The two article identities were already resolved in the retained 26 October follow-up.** The earlier bounded-source report and `article-metadata-status.json` preserve the failures that preceded that addendum. They should be read chronologically, not treated as newly unfinished identity work. This reconciliation leaves all original records, source selection and passages unchanged.

The [retained follow-up](../metadata-followup-v1.json), SHA `98f462151d03dbdbc4b7e39411491d5ad267ea34ba31bf4c89c9993cfbd8ba4b`, is itself pinned in `preparation-closeout.json`. The original [bounded report](../bounded-source-qualification.md) remains the record of the first attempted lookups. Neither an old failure nor a later current metadata observation is a historical article-version pin.

| Fixed article | Original OT date, preserved | Retained official-source observation on 26 October | Precision and rights limits still present |
|---|---|---|---|
| [PMID 35784333](https://pubmed.ncbi.nlm.nih.gov/35784333/), PMC9243421 | `2022-06-16`, publication/evidence date; year 2022 | *Co-Inhibitory Molecules - Their Role in Health and Autoimmunity; Highlighted by Immune Related Adverse Events*; DOI `10.3389/fimmu.2022.883733`; review; publisher publication date 16 June 2022. The earlier addendum reports an attribution license named CC BY. | Day agrees with the raw date in that retained current observation. Numbered license version and historical article/release version remain unverified. This pass does not newly verify the publisher/license. |
| [PMID 15059373](https://pubmed.ncbi.nlm.nih.gov/15059373/) | `2004-03-01`, publication/evidence date; year 2004 | *Association between the cytotoxic T lymphocyte antigen-4 gene microsatellite polymorphism and inflammatory bowel diseases in the Chinese*; official PubMed search metadata reports March 2004. | Independently observed precision is month, not March 1. Article-specific reuse license and historical article/release version remain unknown. Preserve the raw day without promoting it to observed day precision. |

The titles above identify the fixed records; no abstract, article body, passage, clinical outcome or source replacement was read or incorporated in this pass. Existing source-record path strings were not followed. Dates observed in current metadata do not establish the date a historical agent could access a particular release, annotation or excerpt version.

## Today's bounded requests

One batch of four official metadata requests was dispatched for a current recheck. Root then narrowed the task to reconciliation; no further requests were made. Their results are retained in the companion JSON:

- PubMed 35784333 returned a browser-check page.
- PubMed 15059373 returned a tool cache miss.
- The [NCBI OA metadata endpoint for PMC9243421](https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC9243421) was inaccessible through the web tool.
- The [Europe PMC lite metadata query](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID%3A35784333%20AND%20SRC%3AMED&format=json&resultType=lite) was inaccessible through the web tool.

These are tool observations, not verified HTTP status codes, evidence of an absent article, an OA-dataset exclusion or a change in rights. No browser challenge was bypassed; no retry, direct network workaround, fulltext/PDF/data download or new study followed. Today's failures do not erase the retained 26 October observations.

## Practical disposition

There is **no required identity-lookup task left for these two fixed articles before the source-only human/reference gate**. Another equivalent lookup would add little while the prior identity evidence remains retained. Month-only precision and unknown rights details should remain explicit fields. The [provider terms review](../terms-review.md) and attribution/provenance record apply to the retained OT product; absence of an article-specific license is not a finding that the existing snippets are prohibited. These observations do not authorize separately retrieving or redistributing a full article.

What remains is independent domain-matched judgment of these exact excerpts' linkage, sufficiency, applicability and missing context, plus exposure/freshness policy and the later complete-payload preflight. The BTK linkage ambiguity, duplicate sentence and potential prior article overlap remain substantive issues; resolving an identity does not repair them. If an intended future use specifically requires a numbered license or an exact historical article version, qualify that use/version then, under a separate bounded check. Do not turn an optional refresh into an automatic model/native expansion.

All six fixed current identities had a retained official-source check by the 26 October addendum. All six article-specific licenses, historical versions and scientific conclusions are not thereby verified. R08, HR3 and the broader project remain incomplete; no human submissions or freshness certification are inferred.
