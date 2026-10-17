---
title: Clinical and genetics feasibility pilot
date: 2026-10-16
status: origin-screen-complete-regional-qc-qualified-followup-missing
tags: [asof, feasibility, clinical, genetics]
---

# Clinical and genetics feasibility pilot

The user resumed the two deferred feasibility steps. The **24-trial origin mapping screen is complete**, while the longitudinal program/outcome audit remains incomplete. The **IL6R–rheumatoid arthritis regional acquisition and technical QC are complete with source exceptions**. Neither pilot establishes clinical predictive validity or independently validated biology.

Dates in this report use America/Los_Angeles; artifacts retain their actual October 17 UTC timestamps. The January 2023 database was queried read-only and shut down cleanly. The existing downloader and stopped monitor were untouched. Provider spending was $0.

## Clinical screen

Open the [24-case review](../data/benchmark/cohorts/aact-origin-audit-20261017T021043Z/Review.html) for readable cards with decisions, endpoints, current-source links and unresolved follow-up. The [Markdown review](../data/benchmark/cohorts/aact-origin-audit-20261017T021043Z/REVIEW.md) is also retained.

The frozen selection protocol used the restored January 1, 2023 AACT snapshot, exact normalized intervention/alias matches, eligible interventional phases and origin statuses, first-posted dates and nonempty conditions. A deterministic hash-ordered, round-robin selection produced 24 trial representatives across seven target families from 2,078 matched trials. There were 1,696 eligibility exclusions; the remaining eligible trials were not all sampled. The provisional drug/verbatim-condition key deduplicates candidates but does not establish independent programs. Current registry records were fetched only after selection. A later guard against future origin-record updates replays to identical selections and exclusions; the exact original executed script is retained separately.

| Screen decision | Count | Interpretation |
| --- | ---: | --- |
| Candidate | 12 | Eligible for further mapping and dated outcome adjudication, not benchmark-ready |
| Exclude as anchor program | 4 | Rescue treatment, comparator, background therapy or closed platform arm |
| Exclude from fresh-outcome cohort | 1 | Results already posted before origin |
| Split or separate review needed | 7 | Multi-arm/cohort/phase, safety extension or combination context |

Important corrections surfaced by original registry descriptions:

- NCT05535244 lists tocilizumab as CRS rescue treatment; the investigational myeloma therapy is cevostamab.
- NCT04255433 uses dulaglutide as the comparator to tirzepatide.
- NCT04381936 retained a recruiting platform status while its tocilizumab arm was already closed.
- NCT02923180 had results posted in August 2021 despite an active origin status.
- NCT04043806's present-day record reports a December 2022 completion that was updated later; event occurrence and public reporting must be separate.
- Current stop reasons include business decisions and slow enrollment. These are not automatic biological failures.

All 24 current API responses have retained hashes and retrieval receipts. These contemporary observations are evaluator-only and **cannot stand in for the January 1, 2025 endpoint snapshot**. Success, failure, event date, event-publication date and censoring date remain null. No event count, power calculation or model training follows from this screen.

Target identifiers use the pinned October 2026 HGNC reference solely for contemporary evaluator normalization. Disease mappings retain verbatim conditions; dated ontology mappings and cross-trial program identities are unadjudicated. Exact historical first-public availability of the AACT snapshot remains unverified. SCN9A has no selected qualifying seed-matched trial; this is not evidence of biological absence. Reviews are single-AI development judgments with primary-source checks, not independent expert gold. Mechanism URLs are references, not archived or historically validated annotation releases.

## Regional genetics pilot

The prespecified question is **IL6R monocyte transcript abundance and rheumatoid arthritis**, GRCh38 chromosome 1, **153,900,000–154,900,000**, one-based inclusive. This is a contemporary technical feasibility example, not IL6R protein abundance, drug blockade, MR or colocalization. No significance threshold selected the downloaded variants.

| Input | Selected release/product | Retained regional rows | Compressed subset bytes |
| --- | --- | ---: | ---: |
| Expression QTL | BLUEPRINT naive monocytes, QTD000021/QTS000002; reported N=191; processed file April 2023 | 207,274 across genes | 4,287,910 |
| Outcome GWAS | GCST90132223 European rheumatoid arthritis; GRCh38 harmonized file October 2024 | 3,109 | 89,770 |
| LD genotypes | 1000 Genomes direct GRCh38 calls, 20190312; exact EUR panel membership | 25,641 | 3,101,607 |

Official input URLs and response headers are in the frozen protocol and receipts. QTL ALT is the effect allele; GWAS effect/other alleles are explicitly aligned to it. Of 3,400 IL6R QTL rows, 455 differ only by rsID and collapse to 2,945 unique variants; no conflicting keys were found. QC retains **1,690 shared SNPs and all 503 requested European reference samples**. Exclusions are explicit: 726 lack an allele-matched GWAS record, 455 are palindromic/non-biallelic SNPs or mismatches, 44 lack an exact LD REF/ALT record and 30 fail reference MAF ≥0.01. Source rows remain intact. No GWAS sign flip was needed in this selected intersection; synthetic tests exercise opposite allele orientation.

The ALT-dosage LD matrix is finite, symmetric and has unit diagonal. An independent `corrcoef` computation on 40 deterministic variant indices agrees with the corresponding matrix entries. Dosages, sample order, variant order and exclusion records are retained. With 1,690 variants and 503 samples the matrix is expected to be singular; it was neither inverted nor regularized.

### Source exceptions and scientific limits

- The LD README states N=5,248; the actual VCF header has 2,548 samples. The requested 503 EUR samples all match the separate panel. The discrepancy is retained without changing provider text.
- The GWAS metadata YAML does **not** match its published MD5: expected `f0f6f56d1b808a1e8634003221b1c6f1`, observed `e564a41aadc76047d8b761d0e401db94`. A separate retrieval returned identical bytes. Its HTTP last-modified date is February 2025. Cause remains unresolved. Both GWAS and LD index MD5s match their provider manifests. Local metadata SHA-256 is pinned, which identifies bytes but does not resolve the provider discrepancy.
- Full source-wide hashes were not verified because only indexed regional subsets were acquired. Coverage means all records returned by those source indices for the specified interval; it does not prove every genomic variant or the full cis window is represented.
- External EUR LD is a proxy rather than study-specific LD; cohort overlap remains unknown. GWAS per-variant sample size and all 1,690 selected effect-allele frequencies are missing. Aggregate GWAS counts (22,350 cases/74,823 controls) are metadata, not substituted per-variant N. Selected QTL reported allele number is 382.
- Processed QTL, GWAS and current annotations are not eligible January 2023 historical features. Scientific interpretation, instrument selection and causal inference remain unperformed.

### Resource and provenance record

Regional acquisition took 27.55 seconds for QTL, 11.29 seconds for GWAS and 17.90 seconds for LD, excluding metadata/tool setup. QC took 3.13 seconds. Compressed regional subsets total 7,479,287 bytes; local indices total 3,675,589 bytes. The LD matrix is approximately 22.85 MB. Uncompressed selected row streams total 297,559,390 bytes. Actual network transfer bytes, end-to-end wall time and peak process memory were not measured; no estimates are presented as measurements.

The tools used isolated pysam 0.24.1 under existing WSL and NumPy 2.3.4 under an isolated cache. Wheel hashes and source metadata receipts are retained. Default AsOf dependencies are unchanged. These scoped subsets do not promote whole-provider catalog acquisition or parsing status; the public pilot manifest records the acquired scope.

## Verification and reproducibility

Public provenance: `data/manifests/public/2026-10-16-feasibility-pilots.json`. It binds local evidence manifests, source hashes, validation report and code. Clinical records remain in ignored evaluator-only folders; genetics payloads remain on E:. No agent-visible snapshot was changed.

Local artifacts:

- Clinical: `D:/Projects/drug_target_agents/data/benchmark/cohorts/aact-origin-audit-20261017T021043Z/`
- Genetics: `E:/projects_data/drug_target_agents_data/derived/regional_genetics/il6r-ra-20261017T021530Z/`
- Independent checks: `data/derived/feasibility-verification-20261017.json`
- Framework regression report: `data/derived/feasibility-tests-20261017.json`

The verifier replays origin selection, checks 24 current-record hashes and regional/index/metadata hashes, scans coordinates and row counts, reconciles QC counts and independently recomputes selected LD correlations. Its qualified result preserves both source exceptions. All **126 tests passed with no skips**, along with all ten required probes and PowerShell syntax checks. Six new regression tests cover temporal selection, duplicate program sampling, outcome isolation, allele flipping, ambiguous alleles and invalid statistics. Packaging was not rerun because runtime dependencies and packaging configuration are unchanged. The HTML has 24 cards and expandable evidence sections with no executable scripts; a browser visual check was not performed. See `tools/feasibility/README.md` for commands and scope.

At closeout the clinical evidence manifest binds 56 files / 10,206,970 payload bytes; the genetics manifest binds 31 files / 36,478,820 payload bytes. These totals exclude the manifests themselves and shared tooling caches. They are a small scoped addition, not a capacity estimate for the complete data plan.

## Next steps and gates

| Work | Status | Required next action |
| --- | --- | --- |
| January 2023 restoration | Complete with previously documented source exceptions | Preserve archive, restore evidence and availability qualification |
| 24-trial origin mapping screen | Complete as AI development review | Resolve seven complex records and adjudicate cross-trial identities/ontology mapping before cohort inclusion |
| Longitudinal event/censoring audit | Blocked on missing dated follow-up | Obtain January 1, 2025 AACT snapshot through authorized account access, restore separately, compare the frozen candidates; retain event/publication dates and uncertainty |
| Regional acquisition and LD QC | Technically complete with source exceptions | Reconcile metadata checksum and README count; review ancestry/overlap, interval coverage and interpretation before inference |
| Empirical power, clinical scorer, MR/colocalization | Not started | Require adjudicated events or scientifically reviewed genetics assumptions respectively |

The requested follow-up snapshot is pending. No endpoint/date substitution, paid access or clinical-label inference was performed to bypass it.
