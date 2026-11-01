# P09 installed source-inclusive reconstruction: design review

Read-only review, 1 November 2026. No original biological rows, generation/reference values, human responses or protected outcomes were read. No study, model, network or actual replay was executed. Frozen `src/asof` and P05 code/protocols remain unchanged.

## Conclusion and supported claim

A separately versioned **installed Windows source-inclusive deterministic reconstruction** is feasible outside the checkout and original drive roots. It can reread the complete exact originals, reconstruct the 24 native literal/abstain outputs and 14 project-authored constructed outputs, recompute all 90 decisions, and compare them with independently retained historical output hashes and decision/count metadata. This is reproduction work, not another once-only experimental run or new model result.

Two boundaries must be explicit:

1. A new public root-pinned manifest can authenticate its own code, source inventory, receipts, configuration and reconstructed bytes. Without the original private trees it cannot re-prove the original P05 journal/seal/file-set integrity. Call this public reconstruction, not byte-verification of the old private execution archive. The original full-integrity mode remains optional and separate.
2. A privacy-safe catalog changes core reference fingerprints. Use genuine newly compiled/verified references under the new catalog; never overwrite a catalog digest or fabricate `VerifiedReference`/`ScoredCell` objects to imitate historical identities.

No core portability change is needed for the initial Windows scope. Cross-platform source-inclusive replay is not qualified by this design.

## Existing API feasibility and actual blockers

The unchanged core compiler accepts an explicit absolute raw root and whole `Snapshot`/catalog authority. It records logical source/receipt paths and clears only `Snapshot.raw_root` before binding the snapshot-policy fingerprint ([compiler](D:/Projects/drug_target_agents/src/asof/study/source_fact_sources.py:341), especially lines 414 and 499). `verify_reference` reconstructs from source and returns a genuine immutable reference; `score_cell` requires that object and returns a genuine score ([verification](D:/Projects/drug_target_agents/src/asof/study/source_fact_sources.py:521), [scoring](D:/Projects/drug_target_agents/src/asof/study/source_fact_evaluation.py:87)). Existing fictional core tests explicitly exercise root relocation while retaining catalog/deny/snapshot-policy binding.

The frozen wrappers are intentionally stricter than the core: checkout-relative imports, original raw/output roots, absolute inventory and receipt descriptors, exact interpreter location/environment, current helper-code pins, and full serialized Snapshot equality are embedded in their guards ([reference freeze/context](D:/Projects/drug_target_agents/tools/science/build_source_validation_references.py:140), [source replay](D:/Projects/drug_target_agents/tools/science/build_source_validation_references.py:326), [runner admission](D:/Projects/drug_target_agents/tools/science/run_source_validation_experiment.py:757)). Their original code must not be made portable by monkeypatching globals, rewriting frozen READY bytes, substituting code pins or dynamically executing archived code.

The current wheel packages `src/asof` and its declared JSON resources; it does not install `tools/science` or the P05 protocols/audit-helper closure. The existing package smoke is not an installed native study replay. A new installed adapter is necessary.

The installed development `source_fact_reporting.literal_report` is not a native P05 replacement: its view requires literature-provider rows and forbids joins ([reporting view](D:/Projects/drug_target_agents/src/asof/study/source_fact_reporting.py:52)). The reviewed P05 native packet view/assembler must therefore be carried as a small new versioned pure adapter, preserving its one-to-many locus and missingness behavior.

`stable_files` explicitly fails closed off Windows ([stable reads](D:/Projects/drug_target_agents/src/asof/study/stable_read.py:122)). Advertise Windows source-inclusive reconstruction using a fresh C: or other approved local root; Linux/core/demo checks are a different supported scope. Do not inject a no-op lock to claim Linux parity.

## The public catalog fingerprint constraint

Core references bind the entire `catalog_index`, not only referenced dataset roles. A metadata-only inspection found 178 current dataset entries and absolute local-path strings in several catalog metadata fields. No raw scientific values were inspected. Shipping that exact index would conflict with a no-private-path public package; pruning or sanitizing it necessarily changes `method.catalog_sha256` and the full reference fingerprint.

The new public catalog should contain the exact required source-dataset roles and a default-deny policy for every other dataset/source. Preserve the complete pinned 137-node original graph, including HGNC's `reference` role and the other original roles. Root-pin the new catalog hash. This preserves effective role/ancestor admission over the advertised fixed frame without publishing unrelated catalog metadata.

Keep historical task/output/reference hashes as historical anchors. Newly compiled reference fingerprints are new identities and must be labeled accordingly. To verify equivalence beyond the native output hashes, export before reconstruction an independently checked **reference-projection hash that removes only `method.catalog_sha256`** from each historical reference document. Compare that projection with the genuine newly replayed reference. Every other fact, typed value, unit, unknown reason, join, logical source/receipt proof, deny policy, field map and root-neutral snapshot-policy binding remains covered. If any additional field differs, fail or introduce an explicitly reviewed new projection version; do not silently broaden the exclusion.

If exact historical reference fingerprints are required, use the optional private archive mode with its exact original catalog/context. The privacy-safe public mode cannot promise both properties simultaneously.

## Smallest module and packaging shape

Create the separate `asof-p05-replay` distribution under `paper/release/code/`, with modules in `paper/release/code/src/asof_p05_replay/`. It depends on the exact released `asof-target-agents` wheel plus `pyarrow==21.0.0`; installed wheel/source-byte proofs and environment are independently pinned. Leave the old package source and P05 scripts unchanged.

Use a small explicit package rather than a generalized workflow framework:

- `cli.py`: two advertised operations, authority loading, output reservation, bounded reporting and terminal seal.
- `policy_v1.py`: explicit-root original admission and the P05 mapping/date/selected-inventory/task policy. Port only the necessary reviewed pure semantics; no imports from a checkout's `tools/science`, no `sys.path` injection and no archived-code loader.
- `baseline_v1.py`: pure P05 packet validation and literal/abstain assembly. It accepts source-only packet objects, never references, historical outputs or expected hashes.
- `audit_v1.py`: separately authored source projection and result reconciliation. It must not derive expected facts from the producer assembler/compiler output. Shared core contracts, stable reads and source bytes are allowed and disclosed.

Use normal installed imports for trusted code. `asof.study.proofs.capture_package_proof` can capture the unchanged executing core Python/resource closure without depending on its original installation path. The new distribution needs its own complete installed-code/resource proof. Map original `src/asof/...` code-pin identities to installed `asof/...` bytes explicitly, retaining exact file hashes and detecting missing/extra code. Do not assume version `0.3.11` alone proves matching code.

## Two public input roles and independent authority

Keep the package and scientific inputs separate:

1. **Source policy/configuration:** neutral tasks and case routing; logical full-original/receipt inventory; required schemas/footer counts; exact cutoff, source URLs, roles and availability; safe public catalog; complete deterministic policy/version/limits; project-authored fictional source/receipt recipes including exact malformed bytes. Original files are external lawful local copies, not bundled implicitly.
2. **Comparison authority, evaluator-only:** historical 38 raw-output byte hashes/sizes/terminals; all 90 policies/verdicts/first-failure metadata; relevant guard/exactness/count projections; task hashes and historical reference/projection hashes; published aggregate analysis quantities; original experiment/audit/analysis code and artifact hash identities. These anchors are exported from retained accepted artifacts and independently checked before P09 reconstruction, not learned from the new results.

A root-pinned P09 protocol/release manifest binds both roles and its exact code/environment. The caller supplies the manifest's independently retained exact byte SHA. A digest read from the same untrusted bundle is insufficient. The old P05 READY remains historical evidence; it does not authorize the new operation or acquire new paths.

The generation view receives only source policy, neutral task/slots and newly admitted original rows. The historical comparison file is never a generation value parent. Seal reconstructed outputs before comparing their hashes. No retry, substitution, post-comparison repair or answerability reranking is permitted.

## CLI contract

An illustrative interface is:

```text
asof-p05-replay reconstruct \
  --protocol <public-protocol.json> --protocol-sha256 <external-byte-sha> \
  --bundle-root <neutral-and-fictional-assets-root> \
  --originals-root <lawful-complete-originals-root> \
  --output <fresh-local-reconstruction-directory>

asof-p05-replay verify-archive \
  --protocol <private-archive-protocol.json> --protocol-sha256 <external-byte-sha> \
  --archive-root <complete-retained-archive-root> \
  --originals-root <lawful-complete-originals-root> \
  --output <fresh-local-verification-directory>
```

`reconstruct` means all 38 deterministic reconstructions, all 90 recalculated decisions and descriptive-count comparison. It must not invoke the original experiment runner, dispatch model work, acquire data or modify old artifacts. It reports new runtime/resources separately from historical study measurements. Its report method/status must identify P09 reconstruction, not impersonate a new P05 experiment ledger.

`verify-archive` is optional and may be implemented later. It verifies existing output bytes and the complete original sealed file/journal sets, without generating new candidates. The independent inventory audit identifies the original final-audit closure as 42 experiment files, 235 stage-two input files and 230 reference files, plus the required fixture/neutral/anchor closure; deleting `_private` receipt/code/recipe members weakens that original guarantee. It does not require rerunning stage-one selection or treating its audit captures as source parents.

## Explicit runtime relocation

Preserve archived authorization and descriptor bytes as historical identities; never run a blanket D:/E: search-and-replace. Construct separate runtime objects from the new independently approved roots:

- payload runtime path = new originals root + unchanged logical payload path;
- receipt runtime path = new originals root + unchanged logical receipt path;
- `Snapshot.raw_root` = caller-approved new originals root;
- retained artifact lookup = new bundle/archive root + a predeclared logical member identity.

All node IDs, source hashes/lengths, receipt hashes/lengths, relative paths, URLs, roles, parents, release identities, availability instants/uncertainty, task values and physical locators remain unchanged. Only runtime absolute bindings change. Receipt contents remain exact original bytes; normalize Windows versus POSIX separators solely for their declared relative-path identity comparison. Do not case-fold, collapse traversal or rewrite receipts. New copy times are execution metadata, never new information-availability dates.

## Guard preservation

| Guard | Required portable behavior |
| --- | --- |
| G0 | Independently authenticate new protocol/code/neutral/fictional anchors; stable-hash every complete original and receipt before source values; anchor reconstructed output bytes and terminal accounting. Public mode explicitly does not claim verification of unavailable old private journals. |
| G1 | Instantiate and admit the entire source graph and every ancestor under the pinned role catalog and original cutoff before value parsing. Preserve reference/evidence roles; no neutral configuration or evaluator artifact becomes raw evidence. |
| G2 | Reread all mapping originals; require unique canonical HGNC/target/disease identities; scan the complete original GWAS and credible-set frame with Arrow filtering before Python materialization; project every applicable publication/release/annotation guard field. Retain all eligible matching physical rows and excluded duplicates, exact locators, one-to-many locus inventory, conflicts and blocked cases. Rebuild and compare the neutral tasks. No replacement, truncation, composite study/variant inference or invented date/context. |
| G3 | Call unchanged core source-inclusive verification with the rebased Snapshot, explicit approved root and pinned public catalog. Compare genuine new reference/projection hashes; do not construct verified objects manually. Preserve numeric type/finite/exponent/unit/unknown and whole-graph checks. |
| G4 | Use the unchanged typed wire adapter and genuine core scorer; separately enforce strict answered/all-slot exactness. Recompute guard-policy projections from actual guard results, not expected labels. Preserve all 38 outputs/90 decisions, including malformed controls and nonreturns. |

The fourteen constructed scenarios remain generic JSON/core controls. C02 does not qualify native Parquet absent-column ingestion. Native actual-format testing must exercise the required-column scanner separately. C04 remains exact with undefined measurement coverage and no completion. No new scientific endpoint, causal conclusion or independent-study claim follows.

Use a P09 analysis view or a separately versioned count reconciler; do not relabel a P09 execution as the original P05 ledger merely to satisfy a legacy analyzer method check. Frozen analyzer logic can be carried as explicitly trusted installed code for a documented compatibility view, with inputs and transformation pinned. Compare all predeclared counts/missingness/errors and paired decisions, not just favorable native totals.

## Required tests and actual qualification

Before actual-source use, run meaningful fictional actual-format tests with real path/reservation/stable-read helpers:

- Install both wheels into a fresh environment outside the checkout, clear `PYTHONPATH`, run from an unrelated C: working directory and assert all imports resolve to installed packages. No fallback reads to old D:/E: roots or repository files.
- Copy a complete fictional multi-file Parquet/TSV frame and exact receipts to a second approved root. Require unchanged task/fact IDs, source-proof projections, strict wire bytes and guard outcomes. Explicitly test the new catalog-only reference-fingerprint delta.
- Reject a selected-row extract, missing original/receipt, changed payload, wrong URL/release/size/hash, changed logical path, forged external hash and changed catalog role before value parsing. Test both original Windows receipt spelling and canonical POSIX spelling without rewriting either.
- Exercise full canonical mappings, duplicate/conflicting mappings, eligible plus future/annotation-excluded duplicates, every physical credible match, schema/date precision conflicts, Boolean/NaN/noninteger exponent, unknown/empty/null distinctions and unsupported bounds. Preserve blocked units; never replace them.
- Recreate all fourteen controls and their exact malformed raw bytes; ensure actual G0–G4 calls determine the 90 decisions. Keep expected labels/hashes inaccessible to the pure generation function until sealing.
- Reconcile all 38 cells, 90 decisions and analyzer counts; reject omitted/duplicate cells, wrong output hashes, wrong first-failure metadata, fake verified/scored objects and unknowns replaced by zero.
- Test fresh-output reservation, failed hash/deadline, exception/interruption, stable-lock exit and metadata-write failure. Success is sealed only after required reads/cleanup and all comparisons; failure leaves a readable partial terminal report without qualified success.

Then qualify one installed Windows actual-source reconstruction using lawfully copied complete originals in the approved relocated root. Record exact package/protocol/input/result hashes, all source proofs, root translation, guards, comparisons and measured resources; conduct a separate independent source-inclusive audit. This is the first actual P09 reconstruction, not authorization to rerun P06 or the model branch. No actual-source operation occurred in this design review.

## Hard blockers and work that is not needed

Implementation needs the new sanitized protocol/catalog/anchor bridge and its independent review; a separately installed adapter/auditor; and a lawful complete local originals/receipt copy before actual qualification. Exact historical reference fingerprints conflict with catalog sanitization; Windows-only stable reads prevent a Linux source-inclusive claim. These are concrete compatibility/claim boundaries, not requests for a generic security system.

No author/funding/conflict fact is needed for this engineering work. No additional questionnaire, expert response, model test, original study rerun, new download, selection expansion, old capture-value input or change to frozen core/P05 code is needed.

## Accepted implementation contracts

The source-policy JSON has exactly these eleven top-level members:

```text
schema_version: 1
method: "p09.source_policy.v1"
cutoff: exact frozen P05 UTC timestamp
inventory: ordered original descriptor array
expected_frame: {family: {files: int, bytes: int, rows: int|null}}
catalog: {schema_version: 1, datasets: required registered role records}
snapshot: complete original Source Snapshot with raw_root: null
cases: unchanged neutral routing array
tasks: {case_id: unchanged neutral Task}
exposed_symbols: the nine frozen known-use exclusions
limits: the eight original stage-two limit keys, at or below their hard caps
```

Each inventory member is `{source_id,family,dataset_id,release_id,relative_path,sha256,bytes,fields,rows,source_url,role,receipt}`; receipt is `{relative_path,sha256,bytes}`. Ordering is `(family,relative_path)` and IDs remain `original-NNN`. Each neutral case has exactly `{case_id,targetId,diseaseId,studyLocusId,release_id,unit_hash}`. The source-policy exporter/freezer validates the actual 137-file frame, identity/cutoff/routing and original metadata relation before assigning its independent authority. Small complete fictional frames are test fixtures, never actual-source qualification.

`policy_session(policy, originals_root, deadline, progress=None)` is a context manager. It yields `snapshot,catalog,tasks,cases,groups,source_proofs,coverage,resources,dispositions`. The Snapshot is genuinely decoded/reconstructed, with receipt-derived source availability compared to the full root-neutral declared Snapshot. Original and receipt locks span the caller's generation/core replay. Reader cleanup and lock exit must succeed before the caller publishes success. The session deadline is the earlier caller deadline or policy seconds cap.

`groups[case_id]` has `gwas_credible_sets` and `credible_set` sequences of `{source_id,family,locator,physical_row_0based,values}`. A disposition records `status` (`ready_for_base_compile` or `blocked`), `blocked_reason`, `eligible_inventory`, `excluded_inventory`, `neutral_task_sha256` and `normalization_sha256`. Structural authorization/hash/schema failures abort; per-case mapping, rebuilt-inventory, native-type/API/size failures retain the case as blocked. The caller must reconcile every disposition against its frozen comparison authority, not silently skip it.

`baseline_v1.literal_report(task,snapshot,groups,always_abstain=False)` returns canonical exact P05 bytes. There are no reference/comparison/expected-hash parameters or filesystem calls. It supports the existing JSON controls, including absent fields, while native policy ingestion remains strict about required Parquet columns. Shared pure policy helpers for controls retain the legacy signatures: `mapping_index`, `eligibility`, `date_guard`, `source_date_interval`, `interval_status`, `build_task`, `normalization_proof` and `native_representability`.

The root-owned bridge should have a versioned evaluator-only method, bind `source_policy_sha256`, and include historical artifact identities; native task/historical-reference/reference-projection hashes and frozen counts; all 38 output IDs/raw SHA/length/terminal records; all 90 decision IDs/cells/policies/guard/verdict/first-failure records; and the exact descriptive-count projection. The historical reference projection removes only `method.catalog_sha256`. No source-row, reference-fact or candidate values enter this bridge.

Exporter, freezer and builder are separate boundaries: the exporter derives the bridge from retained accepted artifacts, not new output; the freezer independently checks its provenance/allowlist, pins policy/bridge/code/environment and emits new P09 reconstruction authority; the installed builder verifies that external authority, uses source-only arguments for generation, seals outputs and only then compares evaluator anchors. The independent auditor reconstructs native expectations from originals without importing the producer policy/baseline/controls algorithms.
