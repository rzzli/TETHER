# Data, acquisition and scientific-input review

Reviewed 2 November 2026 UTC, from baseline commit `21f64e7`. This is a critical
review of the retained local project, not a new acquisition or biological study.

## Verdict

The existing data supports the bounded contemporary source-reporting paper and
its selected ten development dossiers. It does not yet support a calibrated
clinical predictor, causal genetics features, full Virtual Biotech reproduction,
or the complete original T1–T6/H1–H6 programme. The catalog is structurally
consistent but mixes requirements, artifact history and outdated operational
observations. A new acquisition decision should start with a versioned, neutral
inventory reconciliation rather than treating every `planned` or `queued` entry
as an instruction to download.

Two current utility defects were reproduced and corrected. The downloader,
monitor, catalog, scientific originals, previously frozen outputs and original
interpretations were left unchanged.

## Scope and fresh evidence

- Inventoried all **178 dataset products / 83 providers / 16 families**. Existing
  catalog validation passes unique identities, references, roles, allowed statuses
  and acyclic unconditional dependencies.
- Catalog counts are **134 planned, 22 collected, 19 queued and 3 partial**;
  **177 parse-not-run / one parsed**, and **178 scientific-validation-not-run**.
  Temporal classifications are **171 unverified / seven contemporary-only**.
  These are product-level catalog declarations, not evidence that no subsets were
  parsed. Technical subsets and scientific validity require separate records.
- Statted **1,222 explicitly catalog-named paths** under the authorized E: root:
  **1,145 present / 77 absent**. The absent paths belong to already queued/partial
  products: variant 25, study one, coloc 25, eCAVIAR 25, ChEMBL one. This is neither
  a complete drive inventory nor a fresh content-hash validation of those originals.
- All **12 distinct referenced neutral metadata files** checked exist; all **nine
  explicit SHA-256 pins** in that scope match. No expert response, addendum,
  protected normalized outcome or response-derived judgment was read.
- Read four actual Parquet footers with PyArrow **21.0.0**: one target file
  (7,821 rows/29 fields), disease file (39,530/14), credible-set file
  (106,526/27), and GWAS evidence file (17,714/90). This checks readable metadata,
  not source-wide completeness, row semantics, publisher authenticity or biology.
- Fresh bounded regressions: **61 clinical/genetics/historical tests pass**;
  **six verifier regression methods / twelve synthetic fixture executions pass**.
  The initial test run hit sandbox C: temporary-directory permissions; the same
  tests ran successfully with a workspace temporary directory. That initial
  environment failure remains retained separately.
- Free space observed: D: **1,704,699,858,944 bytes (1.550 TiB)**; E:
  **1,682,538,872,832 bytes (1.530 TiB)**. Capacity for the full 178-product plan
  remains unknown because expanded representations, indices, intermediates and
  backup overhead have not been sized for every selected artifact.

Primary evidence: [catalog inventory](CATALOG-AND-INVENTORY.json),
[sample schemas](SELECTED-SCHEMA-REVIEW.json),
[final regressions](TARGETED-TESTS-FINAL.txt),
[verifier regressions](VERIFIER-REGRESSIONS-AFTER-v2.txt).

## Findings and corrections

| ID / priority | Evidence and consequence | Disposition / required next change |
| --- | --- | --- |
| D01 / P2 | `tools/data/Test-DownloadBatch.ps1` checked URL/path/hash/size but ignored receipt ID, dataset ID and release ID. A synthetic wrong-dataset/wrong-release/wrong-receipt file was reported `complete: true`. This was a false transport-identity claim; core `maintenance.acquisition_report` separately checks dataset/release. | **Fixed** at current lines 27–34. Require case-sensitive status/receipt/dataset/release/URL/path equality. Six regression methods pass; the original six failing identity subcases and five later case-only failing subcases remain retained. No real receipt or source was rewritten. |
| D02 / P2 | `tools/feasibility/qc_genetics_region.py:15` returned orientation `+1` for `A/A`, `C/C`, `G/G`, `T/T` pairs, which are not valid biallelic SNPs. | **Fixed** at line 18: identical REF/ALT or effect/other alleles return unresolved. Four failing-before SNP subcases reproduce the defect; 26 focused tests and the final 61-test pass succeed. The old exact recipe is retained as `qc_genetics_region-before.py.txt` and in Git. No old QC output was regenerated or retrospectively scientifically qualified. |
| D03 / P2 design | Catalog `genetics_results` (line 25156, `agent_evidence`) unconditionally depends on `genetics_qc_cases` (line 24359, `evaluation_only`; edge at 25247). The catalog defines dependencies as normalization/interpretation/validation requirements, while runtime lineage treats evaluator ancestry as ineligible. These two meanings cannot safely be collapsed. | **Open, versioned schema change needed.** Separate `input_dependencies` from `validation_requirements`; validation artifacts attest the method without becoming predictor information. Never remove a genuine evaluator parent merely to make admission pass. No actual leakage or admitted genetics feature was demonstrated. |
| D04 / P2 design | `aact_snapshots` (catalog line 11408) has product role `agent_evidence` while its seven selected releases include explicitly evaluator-only January/April 2026 technical snapshots. Origin inputs and endpoint/ascertainment assets share a coarse product. | **Open.** Add artifact/release-level role and intended-use records, with separate selection, follow-up and ascertainment manifests. Temporal gates remain necessary but cannot replace outcome-role isolation in contemporary use. This is a catalog expressiveness hazard, not proof that an existing run read outcomes. |
| D05 / P2 planning | Catalog operational state is stale: many queued products already have all named files present (e.g. literature 334, literature vectors 256, interaction evidence 200). AACT is collected yet still carries the generic `No acquired artifact in this scaffold` temporal note. Regional QTL/GWAS/LD subsets and technical dossier products exist while their product entries remain planned. | **Open.** Publish a dated observation ledger for scoped artifacts, then make a separately pinned catalog revision only after receipts/hashes/roles are checked. Presence is not collection proof; subset QC is not whole-product parsing. Preserve prior catalog bytes and distinguish acquisition, parsing and scientific qualification. |
| D06 / P2 operational | `Start-DownloadBatch.ps1:124` still rewrites a receipt on a verified cache hit with a new timestamp/cache flag. Existing pinned transport-receipt hashes can therefore change even when raw bytes do not. The retained core state also says `running` from 11 October; its recorded PID 12968 was absent at this review. | **Open by explicit unchanged-worker boundary.** Current content-addressed receipt archives mitigate downstream replay risk. Before any future worker reuse, create a separately versioned implementation with immutable first-capture receipts, append-only retry/observation records and process-start identity checks. Do not treat a stale state string as live progress or automatically redispatch. |
| D07 / P2 operational | `fetch_genetics_region.py:50` calls remote `pysam.TabixFile`/iteration without an explicit total I/O deadline. Its row-byte cap does not bound time stalled inside native HTTP reads, total transfer bytes or header bytes. | **Open before future acquisition.** Supervise regional retrieval in a process with wall deadline, bounded headers/output, retained partial/failure receipt and explicit remote-byte accounting where measurable. No network was invoked during this review. |
| D08 / scientific feasibility | Restored AACT snapshots and technical regional statistics do not supply qualified efficacy labels, study identity, allele/assay transfer, ancestry/overlap or a causal estimator. The retained genetics disposition defers every predictive feature. | **Keep deferred.** Future activation needs an endpoint-specific source contract, objective source-resolvable event rules and eligible complete lineage, plus method-specific numerical validation. More archives, agent agreement or test counts cannot replace missing identification assumptions. No external expert response is introduced as a prerequisite. |

The first seven findings concern data-system correctness or planning quality.
D08 is a scientific feasibility judgment and must not be reported as a software
test failure. No finding establishes that an existing paper result is false.

## The missing-input counts must retain their scopes

The canonical ten-dossier registry points to
`data/derived/literature-coverage-20261017T082208Z/build-report.json`. Its anchored
report records **2,206 selected files / 9,038,960,079 bytes / zero missing manifest
inputs**, including 2,194 evidence files. It scanned 29,823,171 physical rows,
retained 26,985 source rows and produced 31,554 case observations. Ten cases are
unblocked. The largest case is split into bounded packets; whole-case byte totals
need not fit a single 64 MiB packet. These are retained historical report facts;
this review did not rerun that ingestion or rehash all 9.04 GB.

**The 65 missing inputs belong to the older frozen interpretation slice**, not
the current canonical literature build or every file currently on disk. The
**36 unqualified labels**, **17/32 observable registry states**, and **0/12 jointly
source-ready cases** are three other feasibility scopes. None can be added to the
others or translated into a biological absence or a single global missing-file
count. Current planning should link each number to its named manifest/cohort and
observation date before deciding what to acquire next.

## Family-by-family feasibility

These ratings use local catalog and retained project evidence. Current external
availability, legal terms and transfer pricing were not newly verified.

| Family (catalog products) | Current useful evidence | Critical next gate |
| --- | --- | --- |
| Identifiers/coordinates (13) | HGNC collected; selected OT identifiers and historical projections exist | Artifact-specific annotation dates, build/namespace mappings and withdrawn/ambiguous identifiers; do not use current annotations to fill historical gaps |
| Target evidence/baseline compatibility (39) | OT selected components and canonical evidence route are usable technically | Reconcile all 38 pinned Virtual Biotech components; many named queued files exist but study/variant/coloc products remain absent. Full reproduction is not proved by a directory inventory |
| Clinical programs/labels (13) | Seven selected AACT archives technically restored; VBT label/linkage artifacts collected | Origin eligibility, intervention/regimen/population mapping, event vs posting times, censoring and outcome role. AACT state change is not efficacy |
| Causal genetics (14) | Credible-set source fields and one regional transcript/GWAS technical subset | Exact study/variant identity, assay and scale, method-specific complete region, ancestry, overlap, provenance; no MR/coloc output or feature admitted |
| Outcome GWAS/LD (2) | Regional external-reference LD subset technically checked | Distinguish reference genotype panels from study-matched signed correlation matrices; reference N cannot fill study N |
| Direction/burden/safety genetics (9) | Requirements catalog only | Eligible original studies, allele interpretation and endpoint context; no inferred drug direction from arbitrary gene-associated signs |
| Perturbation (8) | OT-integrated selected evidence; direct source products planned | Cell/model identity, controls, replicates, dose/time, intervention semantics and duplicate upstream evidence |
| Expression/proteomics/spatial (13) | OT expression/context and planned direct products | Select a question-specific subset before single-cell/spatial bulk; harmonize tissue/cell labels without equating them |
| Pathways/disease context (7) | Some integrated evidence and named OT files present | Release-pinned direct inputs, pathway membership vs causal support, overlap with OT sources |
| Structure/modality (9) | Planned products and selected descriptive target annotations | Separate structure confidence, computed pocket features, assay tractability and real delivery feasibility; restricted PROTAC source remains optional |
| Literature quality (6) | Canonical literature-containing OT subset exists | Direct article versions, study identity, publication/retraction status and lawful reuse; a citation or sentence match does not establish therapeutic entailment |
| Safety/competition (11) | Some OT openFDA files present; most direct products planned | FAERS reporting biases/denominators, indication confounding, terminology rights and endpoint-specific validation; no causal safety claims from counts |
| External evaluation (10) | Inventory/requirements only | Exact release/license/task eligibility, exposure assessment and comparable input/compute access; no competitor-performance claim yet |
| Project validation (13) | Technical references/dossiers/registry diagnostics exist outside many coarse catalog statuses | Artifact-level evidence register; preserve evaluator role and exclusion of retired expert-response descendants |
| Derived products (7) | Ten normalized dossiers and paper reporting products exist | Separate method validation from predictor input lineage; feature snapshots/scorer artifacts remain unqualified |
| Optional dependencies (4) | Catalog only | Access/licensing and a demonstrated necessity before acquisition; keep the default public-data route independent |

## Recommended order

1. Accept the two small utility fixes with the retained regressions.
2. Publish the scoped operational observation ledger and a manifest/cohort-keyed
   data-readiness table; do not rewrite old acquisition snapshots.
3. Introduce catalog v2 artifact roles, release identity, input dependencies,
   validation attestations and status evidence. Reject the two demonstrated
   design ambiguities in synthetic tests before migration.
4. Keep the current paper's data/replay scope fixed. For any new science branch,
   predeclare the question and an eligible minimally sufficient source set before
   further source searches or acquisition.
5. Only after a source gap demonstrably blocks that question, qualify a versioned
   bounded downloader/regional retriever and collection budget. Preserve the
   existing worker and stopped monitor unless separately instructed.

This review did not freshly authenticate providers, inspect every original row,
restore databases, execute model calls, rerun MR/colocalization, or establish
scientific truth. It also did not globally refresh old statuses or requalify
historical reports merely because current utility code has been corrected.
