# Open Targets 25.09 source and data card

Status: DRAFT; release disposition recommendation, not legal certification. Official pages accessed 2026-11-01. No source payload was acquired or inspected for this review.

## Asset and scientific scope

The actual P05 source collection uses these retained Open Targets Platform 25.09 products, rather than fictional substitutes:

| Product relative to the 25.09 output root | Format | Original files | Retained bytes | Proposed disposition |
| --- | --- | ---: | ---: | --- |
| `evidence/sourceId=gwas_credible_sets/` | Parquet | 100 | 180,049,263 | External originals; publish reviewed URLs/hash manifests |
| `credible_set/` | Parquet | 25 | 2,588,111,695 | External originals; publish reviewed URLs/hash manifests |
| `target/` | Parquet | 10 | 75,568,567 | External originals; publish reviewed URLs/hash manifests |
| `disease/` | Parquet | 1 | 5,545,555 | External originals; publish reviewed URLs/hash manifests |

The [official 25.09 release announcement](https://blog.opentargets.org/open-targets-platform-25-09-release/) is dated 2025-09-17. The retained provider directory is [25.09/output](https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/25.09/output/). The directory listing could not be fetched through the review web tool on the access date; existing neutral acquisition metadata supplies the exact per-file URLs, sizes and local hashes. Availability of those exact external bytes for a fresh recipient remains untested. These are selected products within a broader provider release.

P05 evaluates deterministic reporting fidelity against retained sources. It does not validate biological truth, study independence, clinical usefulness, causality, or historical field-level availability. The twelve native units have locus-only joins with study/variant agreement unresolved. Target/disease/HGNC normalization inputs are still part of the actual-format reconstruction dependency, even where a final report uses only a narrow projection.

## Official rights evidence and boundaries

Open Targets marks Platform **data CC0 1.0** and its **software Apache-2.0**. Its licensing page also says listed contributing sources permit unrestricted use by Platform users; it lists heterogeneous upstream licences. The [Platform licence](https://platform-docs.opentargets.org/licence) and [terms of use, updated June 2021](https://platform-docs.opentargets.org/licence/terms-of-use) must be read together: the latter preserves original owners' rights and places third-party-rights responsibility on users. The current licensing page is mutable; no release-specific 25.09 licence-page byte capture was established here.

The [GWAS Catalog licensing statement](https://www.ebi.ac.uk/gwas/docs/about/#licensing-information) puts Catalog contents under EMBL-EBI terms and summary statistics under CC0 unless stated otherwise, directing users to individual dataset terms. The [EMBL-EBI terms](https://www.ebi.ac.uk/about/terms-of-use/) show revision 2026-10-14. These statements distinguish integrated Platform products from independently obtained study summary statistics, articles, ontologies, and other upstream products. This review did not establish a record-by-record upstream rights map for the full 25.09 objects; a publication link or identifier does not itself license the linked article or data.

## Release rule and reconstruction

For this draft, exclude the 136 complete Open Targets originals from the distributable archive. Include only explicitly reviewed project code, neutral schemas/routing, source URLs, byte sizes, local SHA-256 values, receipt provenance and this card. Preserve attribution to Open Targets, its version-specific release and relevant upstream resources when identifiable. This conservative packaging choice does not assert that CC0 redistribution is prohibited.

Actual-source replay must receive the original Parquet products through an explicit external input root and verify the full frozen file inventory before execution. The P05 full collection, including HGNC, has 137 originals; twenty-four selected rows or toy JSON cannot reproduce its original-file hashes. If exact bytes are unavailable, report reconstruction unavailable rather than silently substituting a newer release, API response, reduced extract or fictional fixture. A new smaller actual-format reproduction would require a separately labelled protocol and binding; it is not the frozen full-source replay.

Source-derived packets, references, row extracts and raw reports inherit a separate release review; they are not made Apache-2.0 by serialization or by the project code licence. No such payload is admitted by this card alone.

Evidence anchors and unresolved retrievals are recorded in `planning/review-assets/preprint-p09-20261101/RIGHTS-SOURCE-AUDIT-v1.md`.
