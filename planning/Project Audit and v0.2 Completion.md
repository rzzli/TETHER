---
title: Project Audit and v0.2 Completion
date: 2026-10-11
timezone: America/Los_Angeles
status: technical-pilot-complete-administrative-closeout-open
updated: 2026-10-12
tags:
  - asof
  - audit
  - v02
---

# Project audit and v0.2 completion

This is the correction record for the full-project pass requested after [[Framework Code Review and Next Stage Plan]]. It covers the proposals and requirements, runtime modules, tests, supporting utilities, catalog, selected local input files, archived runs, documentation and memory. It does not certify the scientific correctness or completeness of every provider collection. Original proposals and dated research logs are preserved.

## Corrections and evidence

| Finding | Correction | Verification and boundary |
| --- | --- | --- |
| Five original framework correctness findings | V2 contracts; copied and recursively frozen evidence; program/scorer preflight; hypothesis-scoped features; complete input lineage separated from computation time; durable run accounting | Regression tests cover nested mutation, zero-dispatch invalid inputs, different actions/modalities/tissues/programs, old-input/new-computation eligibility and interrupted calls. V1 execution is retired; archived receipt verification remains available. |
| Rehashed run metadata and accounting could contradict execution | Reconcile case/snapshot/backend identity, configuration, budgets, call counts and measured/estimated usage against journal events | New failing probes reproduced the defect before correction. Tampering and finalization regressions now enforce reconciliation. |
| Committed journal evidence could differ from ledger evidence | Compare complete committed claims and ledger fingerprints | Rehashed journal/ledger divergence is rejected. |
| Omitted raw-parent proofs were accepted without an external receipt anchor | Require the exact eligible artifact/ancestor proof closure, including in outputs-only verification; source-inclusive verification reuses admission | Missing-parent proof, future-publication and role/lineage tests. An external retained receipt hash remains necessary to detect coherent wholesale replacement. |
| CLI request file was outside the seal | Optional receipt `auxiliary_outputs` hashes `request.json` | New runs seal it. Valid older v2 receipts remain accepted and explicitly report the unsealed request. |
| Repeated ledger searches and late Python filtering | Index admitted evidence and case/category queries; filter Arrow batches before converting selected rows | Lookup gates/fingerprints retained; tests cross batch and row-group boundaries and check original physical locators. Wall-time checks during commits retain partial results and abstain. |
| Failed real build had no retained termination evidence | Reserve output before inspection; append hash-chained stages/progress/counters/failures; make `inspect-run` understand builds | Inspection failure, packet-write failure, interruption and concurrent reservation tests. The original incomplete directory is retained; its original termination cause remains unknown. |
| Adapter dropped biosample/model/variant/trait contexts | Expand explicit scientific projection and preserve unresolved values in source metadata | Actual-format tests and original-row review. Cell type does not imply tissue; variant effect does not imply intervention direction; provider scores remain descriptive. |
| Transport retries can rewrite receipt bytes | Copy inspected bytes once into the E: content-addressed receipt archive and bind lineage to those copies | Exact-byte test deliberately rewrites a transport receipt after inspection. The downloader and its receipts are not edited. |
| Stale v1 documentation and obsolete review fixtures | Current README/reference, explicit migration guide and v2 review utility | Commands and probes checked against current code; archived v1 findings remain a dated record. |
| Pilot exposed an output/input size-limit mismatch | Separate bounded 256 MiB ledger reader; keep input packet cap at 64 MiB; reject oversized ledger before receipt creation | The first corrected-build pilot reached CFTR but its 73,413,457-byte ledger failed the old input reader. That failed attempt is retained. Regressions cover valid >64 MiB ledgers, unchanged input rejection and >256 MiB output rejection. |
| Catalog/document index count mismatch | Add normalized-product index entry and retain 83 providers / 178 products | Provider, dependency, overlap and documentation references are checked. Technical parsing and scientific validation are separate states. |

## Complete requirements status

“Implemented” below refers to the named deliverable, not to all proposed research. “Partially implemented” means a concrete subset exists. “Deferred” means outside this milestone. “Externally blocked” identifies a required input/access decision that code cannot supply.

| Requirement from the data plan | Status | Retained capability and remaining work |
| --- | --- | --- |
| R01 Identifiers/coordinates | Partially implemented | Approved HGNC symbols and selected OT Ensembl IDs checked against pinned originals; full coordinate, isoform, variant and historical crosswalks remain. |
| R02 Indication mapping | Partially implemented | Exact fixed disease IDs and source names checked; expert ontology equivalence and historical mappings remain. |
| R03 Evidence/baseline compatibility | Partially implemented | OT 25.09 target/disease/nonclinical evidence adapter; complete 38-slot compatibility requirements are inventoried. No Virtual Biotech execution or historical backfill. |
| R04 Clinical program identity | Deferred; historical access externally blocked | T1 program contracts exist. AACT restoration and dated program/drug/target adjudication are not completed. |
| R05 Events/follow-up | Deferred; source availability unresolved | Evaluator contracts distinguish censoring and unresolved labels; no real at-risk cohort or independently adjudicated outcomes. |
| R06 Molecular QTLs | Deferred; access/sizing externally blocked | Requirements include complete regional statistics and assay identity. No authenticated retrieval or scientific harmonization. |
| R07 Outcome GWAS/LD | Deferred | Ancestry/build/overlap and LD requirements documented; no MR/colocalization implementation. |
| R08 Direction/genetic safety | Partially implemented | Reported integrated variant effects/directions and model context preserved without therapeutic inference; no direction classifier or genetic safety validation. |
| R09 Perturbation | Partially implemented | Selected integrated animal/pathway records retain context; no direct screen reanalysis or effect feature derivation. |
| R10 Expression/proteomics | Partially implemented | Selected OT RNA evidence and explicit missingness; no direct single-cell/proteomic pipeline or surface-exposure conclusions. |
| R11 Pathway/disease context | Partially implemented | Integrated pathway evidence retained with source identity; independent study-level deduplication/causal interpretation remain. |
| R12 Structure/modality | Deferred | Action and modality are hypothesis keys; no pocket, topology, delivery or chemistry computation. |
| R13 Literature quality | Partially implemented | Integrated literature records and publication eligibility; no frozen full-text corpus, retraction pipeline or embeddings. |
| R14 Safety/organ categories | Deferred | Restricted terminology and independent organ-category requirements documented; no pharmacovigilance analysis. |
| R15 Competition/patents | Deferred | Inventory only; clinical evidence is excluded from this pilot. |
| R16 Spatial/signature reversal | Deferred | Inventory and source/QC requirements only. |
| R17 External evaluation | Deferred | Component benchmark inventory retained; no competitor runs, common-source comparison or contamination audit. |
| R18 Gold/splits/audits | Partially implemented | Synthetic failure/temporal fixtures and technical original-row review; no expert gold, locked partitions or blinded ratings. |
| R19 Prediction/process attribution | Partially implemented | Ledger, deterministic feature/scorer interface, receipts, journals and descriptive evaluator; real features empty and clinical probabilities null. |
| R20 Prospective/H6 | Deferred; original H6 assets externally blocked | No prospective prediction registry, mature follow-up or original H6 feature matrix. |

| Task, hypothesis or ablation | Status and next gate |
| --- | --- |
| T1 next transition | Contract and synthetic evaluator implemented; historical cohort, labels and trained scorer deferred. |
| T2 matched pairs | Deferred; needs T1 cohort and prespecified matching. |
| T3 all-gene ranking | Deferred; needs dated candidate universe and ascertainment-aware outcomes. |
| T4 direction | Deferred; needs context/action gold and validated derivations. |
| T5 safety | Deferred; needs reason-specific outcomes, organ labels and adequate event counts. |
| T6 dossiers | Contemporary technical development pilot in this milestone; independent scientific/blinded review remains. |
| H1/H2 prediction/comparison | Deferred; no real prediction performance or competitor advantage established. |
| H3 popularity confounding | Deferred; needs dated publication counts and the prespecified low-popularity analysis. Chronology and model contamination remain cross-cutting validity gates. |
| H4 causal genetics | Deferred; no MR, colocalization or intervention-direction result established. |
| H5 dossier quality/error/cost | Technical source fidelity checked; expert blinded comparisons, audited biological error rates and measured live-model cost remain deferred. |
| H6 reanalysis | Externally blocked on original assets or explicitly approved reconstruction. |
| A1 genetics deletion | Feature-family interface tested synthetically; real genetic calculations deferred. |
| A2 shared scorer | Synthetic scoring/contributions tested; real training/calibration and ablation deferred. |
| A3 critic removal | Bounded critic/no-review software controls exist; expert claim/method gold and comparative study deferred. |
| A4 perturbation deletion | Family-level interface exists; direct perturbation derivations deferred. |
| A5 literature deletion | Family-level interface exists; frozen corpus/embeddings/popularity baseline deferred. |

## Remaining limitations

- A contemporary download timestamp establishes present-day availability only. No current annotations fill historical gaps.
- The frozen manifest has 65 missing inputs. Selected-subset coverage and unknown context cannot support absence-of-evidence claims.
- Real numerical prediction features stay empty and probabilities stay null. Source review tests transcription/normalization fidelity, not biological causality or clinical validity.
- Runtime protocols are not OS containment; arbitrary external agents need separate evaluator/credential isolation and network controls.
- Time checks cannot forcibly interrupt an arbitrary blocking backend. Future live adapters require deadlines/process supervision. No live backend is introduced here.
- Local hash chains and receipts are not trusted timestamps or immutable storage. Retain receipt anchors independently for stronger tamper detection.
- The disk capacity verdict applies to this pilot and bounded subsets, not the entire source inventory. Transfer charges and account-mediated sources remain separately gated.

## Production completion evidence

Updated October 12: the technical pilot is complete. The canonical [ten-dossier index](../runs/v02-realdata-20261012T015124Z/README.md) links all finalized cases. Its [pilot report](../runs/v02-realdata-20261012T015124Z/pilot-report.json) records source-inclusive semantic verification, sealed request files and matching runtime fingerprints for every case. The [retained source audit](../runs/v02-realdata-20261012T015124Z/source-review.json) checks 20 distinct original rows across all ten cases. Receipt anchors and the source-audit hash matched during the replanning check. This is technical fidelity review; independent scientific adjudication remains unperformed.

The [production build report](../data/derived/v02-contemporary-pilot-20261012T014305Z/build-report.json) records 2,141 files / 3,752,440,123 bytes, 14,940,949 physical rows scanned, 14,207 accepted matching source rows and 16,914 normalized case records. There are no blocked cases; 65 missing inputs remain explicit. Build elapsed time was 255.25 seconds with peak memory 1,150,431,232 bytes. The largest packet is 60,883,175 bytes, below 64 MiB. The pilot plus source verification/audit took 242.609 seconds; its parent-process peak was 1,544,667,136 bytes, not an aggregate child-process peak. Provider spending was $0. All real probabilities remain null and numerical features empty.

The final integrated suite passed **100 tests**; the current review utility passed **ten probes**. A dependency-free demo ran and verified with site packages disabled. Original plans/downloader/monitor hashes, archived v1/v2 verification and the 83-provider/178-product documentation index were checked in [[data/manifests/public/2026-10-11-project-checks.json]]. V1 semantic verification remains unavailable.

Administrative completion is still open: generated-product catalog status needs a scoped update, and version control, CI, portable legacy verification fixtures and a canonical-run registry need implementation. The user requested replanning after [[Full Repository Review and Verified Findings_claude10112026]]. [[Revised Next Stage Plan after Repository Review]] now governs these corrections and the scientific feasibility gates. The completed dossiers do not establish a live model system, clinical predictor or scientifically validated benchmark.
