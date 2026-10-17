---
title: Full Cis Genetics Revision
date: 2026-10-17
status: technical-completion-with-source-exceptions
tags: [asof, genetics, feasibility, provenance]
---

# IL6R full-window technical revision

The source-defined IL6R cis window is now retrieved and technically checked. The earlier pilot remains valid for its requested interval, but did not cover the full source-defined window. Neither version supports a causal or therapeutic conclusion.

The [eQTL Catalogue methods](https://www.ebi.ac.uk/eqtl/Methods/) specify testing within one megabase on either side of the gene start. The [versioned Ensembl 105 phenotype metadata](https://zenodo.org/records/7808390), published April 2023, gives IL6R `phenotype_pos=154405193` on GRCh38 chromosome 1. The gzip passed its publisher MD5 `b999b21dcffeecbfe0bf886a5a91997b`. This defines the one-based inclusive interval **1:153405193–155405193**, replacing the earlier 1:153900000–154900000 scope in a new protocol. The region was selected from annotation, without selecting association peaks.

## Measured results

| Item | Original pilot | Full-window revision |
| --- | ---: | ---: |
| All indexed regional QTL rows, across genes | 207,274 | 336,006 |
| IL6R QTL rows | 3,400 | 6,120 |
| Unique IL6R variants after rsID-only duplicate collapse | 2,945 | 5,325 |
| Regional GWAS rows | 3,109 | 5,722 |
| Regional LD VCF rows | 25,641 | 50,412 |
| Shared variants passing the existing QC rules | 1,690 | 2,979 |
| Selected EUR LD samples | 503 | 503 |

All new records within the old interval match the original ordered row streams exactly. Remote identity headers and index hashes also agree. A separate correlation calculation reproduced 3,600 deterministic LD entries with maximum absolute difference below `3.5e-15`. The 2,979-by-2,979 matrix is expected to be singular with 503 samples; it was not inverted or regularized.

The wider window revealed two distinct GWAS estimates sharing `rs2990223`, the harmonized position 155215184 and A/G alleles. The source also retains different legacy coordinates. The existing conflict rule excluded this allele key rather than choosing a favorable row. Two regional rows disagree between primary harmonized and secondary coordinate columns; neither enters the selected QC set. Raw rows and exclusions are retained.

Acquisition took 31.53 seconds for QTL, 13.49 seconds for GWAS and 23.30 seconds for LD, excluding setup and pauses. Compressed regional payloads total 12,689,659 bytes; uncompressed selected row streams total 573,664,391 bytes. The QC wrapper took 16.53 seconds and measured a peak process working set of 399,110,144 bytes. The sealed artifact set contains 38 files / 93,166,905 bytes, excluding its manifest. Actual network transfer bytes and acquisition peak memory were not measured.

## Limits and next gate

The full coordinate window does not prove that every variant was measured or indexed. The unchanged generic QC recipe retains its earlier conservative full-cis disclaimer; this revision's independent annotation check establishes the window coordinates, while source completeness remains qualified.

The GWAS YAML still fails its published MD5 despite identical repeated retrievals. Local hashes identify the retained bytes and do not reconcile that provider exception. Whole remote source files were not hashed. Study-specific LD, participant overlap, per-variant GWAS N and effect-allele frequencies remain unavailable or unverified. The exposure is naive-monocyte transcript abundance, not IL6R protein concentration or pharmacologic inhibition. Processed releases and annotations remain contemporary-only for this project. No MR, colocalization, clinical probability or historical admission was performed.

The primary IGSR paper corroborates 2,548 unrelated samples in this reference collection, supporting the VCF count rather than the README's 5,248. The README discrepancy itself is preserved. See [IGSR's primary report](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6943028/fullTextXML).

The next candidate for a separate technical comparison is Schmiedel 2018 naive monocytes, QTD000504/QTS000026, gene expression, reported N=91 in the pinned metadata. It was selected by assay/context rather than association significance. Its ancestry, participant independence, source-version compatibility and regional availability must be checked before comparison; no secondary-study data have been acquired. Do not pool studies or interpret a weak/null result as drug failure. No user account is currently required for this scoped public route.

## Provenance and recovery

Canonical revision: `E:/projects_data/drug_target_agents_data/derived/regional_genetics/il6r-ra-full-cis-20261017T071600Z/`.

Public anchor: `data/manifests/public/2026-10-17-full-cis-revision.json`. Evidence manifest SHA-256: `d9968672ffe65ef3e3ace22928697b1e3cd047b1bde4a59abfb6fca3ee9e83b5`.

Read `revision-summary.json`, `independent-verification.json`, `secondary-coordinate-review.json` and the source receipts. Exact executed recipes and inherited-file hashes are retained. Do not rerun acquisition or QC into this directory. The parent pilot, its receipts and public manifest remain unchanged. This selected subset does not promote whole-provider catalog collection or scientific validation.
