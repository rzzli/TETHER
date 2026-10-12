---
name: research-log-2026-10-10
description: Completion audit of the accepted AsOf documentation-only data scaffold
metadata:
  type: project
date: 2026-10-10
---

# Research log — October 10, 2026

User objective: start work on the accepted plan if anything remains unfinished. Inspected [[data/README|the scaffold]], [[data/DATA_PLAN|requirements]], the machine catalog and project memory before extending work.

Found two concrete documentation gaps: 15 documentation-checked products had no evidence reference attached, and the genetics contracts inherited generic gene/assay fields into outcome GWAS while omitting phenotype-specific quantities and overlap/effect context. The raw IGSR panel was also described as if an LD matrix were supplied.

Completed source evidence references through official pages/papers/terms. PDC and the expanded AlphaFold FAQ had rendering limits, so their official indexed excerpts are explicitly identified. No new access or redistribution clearance is implied.

Updated 13 normalized field contracts: six QTL products; three outcome GWAS products; OpenGWAS endpoint responses; IGSR panel; study-specific LD; and calculated genetics/LD provenance. Binary case/control counts and case fraction are conditional, quantitative transformation/variance remains explicit, and outcome GWAS do not require a gene-specific assay. Clarified that analysis dependencies are not access permissions or mandatory raw-download order.

Added [[data/manifests/public/2026-10-10-completion-audit.json|a sanitized completion audit]], updated catalog metadata, README, data plan and [[project-goals]]/[[data-acquisition-plan]]. Kept 83 providers and 177 products, all planned/unparsed/unvalidated. Subsequent acquisition and scientific protocol gates remain separate from this completed documentation milestone.

Completion checks passed: 177 indexed products; provider/dependency/overlap references; evidence links for all 75 checked records; trait-specific conditional fields; raw panel versus LD distinction; no unconditional dependency cycles or broken updated wiki links; public-audit/label/credential ignore cases; unchanged original planning/feasibility hashes; and no biological payloads acquired.

## Later session: capacity check and downloads started

The user subsequently authorized starting downloads and identified E: bulk storage. Measured distinct NTFS disks with approximately 1.63 TiB free on D: and 1.72 TiB on E:; 20% capacity reserves leave approximately 2.62 TiB usable. Inventoried 23,161 native payloads in Open Targets 19.11/21.11/23.12/25.09, approximately 196 GiB with conservative bound 198.47 GiB. ChEMBL 35 SQLite exact Content-Length is 4,986,486,022 bytes; expanded sizes remain unknown.

Three starter files (VBT labels/linkage, HGNC snapshot) completed on E:, totaling 33,422,927 bytes. Started a 3,513-file, 34.04 GiB-bounded core batch. A connection reset interrupted the initial attempt after 121 completed files. Partial/complete data were preserved, native-stderr handling was isolated per worker, and the batch resumed under a tool-managed shell. GCS mirror returned requester-pays UserProjectMissing; no paid project/transfer was used.

Created transport/inventory/status/catalog-sync scripts, private queues, public size/capacity/acquisition snapshots, an E-root README and [[data/STORAGE_AND_DOWNLOAD_REPORT]]. Updated authorization and acquisition states in project memory. Future scientific/model validation is separate from raw download integrity.

Transport checks passed for corrupt Parquet rejection, expected-hash mismatch, cached-file revalidation and isolated missing-URL failure alongside a successful peer. The resumed core worker was observed running with no failed records in the current attempt. Live status/receipts, not this dated log, determine later completion.

## Fifteen-minute monitoring goal

The user requested checking the active download every 15 minutes until finished. Added a tool-managed watcher for the core 3,513-file batch, which records actual worker PID/creation identity and progress at that interval. Live monitor state/history are in the E data root's `manifests/`; private storage config records the tool handles. Initial watcher observation confirmed a live worker and 1,073 completed files, with no failed records.

The user subsequently requested stopping the 15-minute checks and will ask for status when needed. Stopped the watcher after verifying its process identity, disabled monitoring in the private storage config, and paused the monitoring goal. The download worker was confirmed running and left untouched. Future status checks are on request; download completion and independent verification remain unconfirmed.

## Initial agent framework

The user then requested starting the agent framework. Implemented the narrower core recommended by [[AsOf Feasibility Analysis and Peer Survey]], borrowing Virtual Biotech's plan/review/provenance pattern while separating extraction from prediction. Code is in `src/asof/`; see [[README]] and [[docs/FRAMEWORK]].

Implemented strict normalized contracts and catalog-role checks; conservative source/release/record/annotation date gates including case mappings/program state; exact artifact hashes and constrained paths; category routing; model-independent selection, offline/replay backends and bounded reviewer retries; grounded append-only claims; study/cohort/dependency grouping; explicit null/missingness coverage; frozen logistic scoring with earlier-label/applicability gates and abstention; hash-chained private run artifacts; separate evaluator-only descriptive T1 metrics with censoring/maturation/coverage checks.

Created a local Python 3.11 virtual environment using existing uv-managed Python; no runtime dependencies or provider credentials. Synthetic fixtures include a duplicate study, unmeasured perturbation and two future-evidence canaries. No live provider calls, real biological analyses, downloaded-dataset parsing, scorer training or benchmark superiority measurement occurred. The bulk worker and paused monitoring configuration were not touched.

Verification passed: 51 automated checks covering strict schemas, dated mappings/state and source/annotation gates, canary withholding, catalog label-role rejection, grounding/retries, dependence and missingness, budgets including billed failures, scorer cutoffs/applicability/imputation, output/source integrity, censoring/label-freeze metrics and CLI run/evaluator round trips. The packaged CLI demo completed with nine grounded claims; seven output files, one admitted original and the 27-event trace passed integrity verification. A recorded-response run without a scorer completed with explicit abstention. Final demo artifacts are under `runs/framework-v0.1-verified/`; no fixture probability is interpreted scientifically. Original planning/feasibility document hashes remain unchanged. Code carries the requested Apache-2.0 license, separate from data terms.

The remaining scientific/integration gates are real dated adapters/cohorts, a chosen model backend, fixed genetics computation and independent method QC, validated scorer training/calibration, OS isolation and pinned competitors, clustered inference/power, further tasks and prospective anchoring. A packet interface and local hash receipt cannot certify historical provenance, model knowledge or host containment.

## Code review and next-stage plan

The user requested reviewing the current code and planning the next stage. Re-ran the 51 existing tests successfully, reviewed all runtime modules and retained their SHA-256 fingerprints. Added `tools/review/probe_framework.py` and [[planning/review-assets/framework-review-2026-10-10.json]]: ten fictional probes reproduced five correctness issues and four integration gaps. No runtime source or original planning document was changed.

Confirmed T6 future-program context reaches backend requests; mutable admitted evidence and finalized feature vectors can yield source/trace/prediction inconsistencies while integrity verification passes; action-conditioned features lack hypothesis binding; timeout/value errors escape without a returned run; and scorer cutoff rejection occurs after eight attempted calls. Existing tests do not cover these cases. Other gaps concern locked evaluation, archived input policies/backend metadata, feature-level missingness reasons and separate temporal eligibility for the parents of newly computed results.

Wrote [[Framework Code Review and Next Stage Plan]] with ten implementation tickets, acceptance tests, bounded real-data ingestion, ten development dossiers, optional provider/replay integration and a separately gated historical cohort/locked evaluation. Proposed v0.2 effort is 10–16 engineering days; cohort/evaluation adds 5–8 days after usable access. [[framework-code-review]] records the enduring findings. Arrow's primary documentation supports selected-column/filter/batch ingestion; AACT pages failed browser retrieval and no restoration was attempted.

No live model/API runs, real scientific analysis, biomedical downloads, account actions, download-status checks or monitoring changes occurred in this review. Benchmark superiority, empirical power, actual historical access and training/containment guarantees remain unestablished.
