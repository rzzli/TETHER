# Q02: artifact-specific catalog policy — design and readiness

2 November 2026 UTC. **Design only; no policy migration, collection promotion or new execution has occurred.** This review reads the catalog, current readers/tests and named neutral technical metadata. It does not read original biological rows, protected clinical outcomes, expert responses or their derivatives. See [READINESS.json](READINESS.json) for the exact catalog, product inventory, consumer paths and metadata hashes, and [TEST-CASES.json](TEST-CASES.json) for proposed acceptance cases. Tests in that file are specifications, not passing results.

## Decision

Implement an **additive canonical TETHER schema-2 policy** and a checked, use-specific schema-1 projection. Keep `data/catalog/sources.json`, the prior catalog history, sealed runs and the frozen AsOf 0.3.11 engine unchanged. Do not change the existing transport worker. This avoids invalidating archived dependency fingerprints or pretending that legacy readers enforce new fields.

The policy can index all **178 products / 83 providers** immediately. Only artifacts in an explicitly selected, pinned frame receive usable artifact records; undeclared artifacts are denied. There is no need to migrate every historical run, every original on E:, or all planned data products to implement this gate. Start with the named contemporary ten-case frame and its exact source/packet identities, plus AACT technical metadata records that remain blocked for prediction. The separately frozen P05 frame is a later explicit import, not an automatic union with the ten-case frame. Existing runs retain their original policy and guarantees.

The deterministic next task is feasible without downloads, an expert, account credentials or database access: implement the schema, pure policy checks, projection/binding checks and fictional fixtures; import selected neutral metadata with no status promotion. Qualifying historical AACT availability, genetics or clinical labels remains a separate scientific task.

## Verified starting point

- The schema-1 catalog SHA-256 is `eafd955cad30dd36bd7417de165a508b1e891f90f42e2cc4bcb573043eaa65ac`. There are 299 unconditional dependency edges, five products with conditional groups and one 38-component Virtual Biotech requirement list.
- Collection status is 22 collected, 19 queued, three partial and 134 planned. Parsing is one parsed and 177 not run; all 178 scientific-validation statuses are not run. Those are product observations with scopes, not 22 scientifically ready products.
- `maintenance.validate_catalog` checks references, cycles, status enums and role names. `provenance.catalog_index` is a different, lighter schema-1 reader. Both reject schema 2. Runtime `InputGraph` checks each supplied node's product role and actual parent graph; it does not enforce the catalog's product dependency lists or free-text profile policy.
- `genetics_results -> genetics_qc_cases` mixes a validation fixture with scientific inputs. `genetics_results -> igsr_ld_reference` is unconditional even though its conditional groups already say LD is needed for applicable methods. Both need precise classification; neither proves an existing admitted feature leaked labels.
- `aact_snapshots` is currently agent evidence at product level, although January/April 2026 technical records explicitly mark evaluator-only uses. A release date alone cannot identify whether an artifact is an origin input or follow-up label source.
- The newly corrected PowerShell verifier compares queue and receipt identity. **The Python catalog-promotion reader `acquisition_report` still omits `receipt_id` and URL equality.** Its fixtures omit those fields, so they do not test this property. Do not use that legacy report as the sole new-policy acquisition authority.

## Small schema-2 contract

Retain stable provider/dataset IDs and the descriptive metadata; do not rename `asof_normalized_packets` or old schema IDs. Add a new immutable file such as `data/catalog/policies/tether-policy-v2-20261102.json`, with the source catalog path/hash and migration version. Use four structures, not a new database:

1. **Products:** `dataset_id`, existing provider/descriptive fields, `input_dependencies`, `validation_dependencies`, conditional dependency groups and a dependency-review state. Keep the original `dependencies` as explicitly inert `legacy_dependencies` for traceability. Product roles describe possible use classes, never an artifact grant. Preserve the legacy evaluator-product deny explicitly: any existing product containing `evaluation_only` cannot receive an agent/reference input grant merely because it also contains `reference`. Adding artifact-specific evaluator restrictions to AACT does not make every AACT release an evaluator-only product. Every existing collection/parse/science status remains unchanged in this first migration.
2. **Artifact records:** exact dataset ID, release ID, approved root alias, normalized relative path, SHA-256, size, raw/derived kind, selected-subset scope, receipt/provenance references, availability basis and explicit parent identities for derived data. An unqualified record can exist with null unknowns and a reason, but it cannot authorize access. Do not invent a raw download receipt for user-supplied AACT archives.
3. **Use records:** exact artifact identity, role, intended use (`contemporary_evidence`, `normalization_reference`, `origin_context`, `endpoint_evaluation`, `ascertainment_evaluation`), profile, protocol/frame hash and origin/cutoff where relevant. A use may be `blocked` with explicit reasons. The same bytes can have different separately adjudicated uses; a denied evaluator use cannot be relabeled by passing a different string. No wildcard release or directory-wide grants.
4. **Scoped observations:** acquisition verification, parsed subset and scientific qualification are separate fields, each with a retained report identity and scope. Existing coarse product statuses remain legacy summaries. File existence, database restoration or a parser success cannot promote scientific qualification.

Paths, identities and URLs are case-sensitive contract strings even on Windows. Resolve approved root aliases separately; reject traversal, conflicting aliases, duplicate artifact keys, ambiguous use matches and unknown fields. Compare `(dataset_id, release_id, root_alias, relative_path, sha256, bytes)` and receipt identity exactly. Legitimate relocating of an archive requires an explicit verified mapping, not a silent path substitution.

### Dependency classification

`input_dependencies` describe inputs needed for a named interpretation/normalization operation. They are not proof that those inputs were consumed and not permission to retrieve them. Actual computation ancestry is the sealed source DAG. Do not recursively add catalog dependencies to a manifest, grant their roles, or force every raw provider file to claim local annotation ancestors: many existing edges describe interpretation needs, not the provider file's physical derivation.

For the first migration, retain all 178 records. Carry the existing edges conservatively as product requirements with `dependency_review_status: legacy_carried_forward`, except the reviewed corrections below. Active-frame products can receive `reviewed_for_selected_frame` after their specific interpretation requirements are checked; this is not a blanket certification of all 299 edges. Unreviewed optional combinations remain unusable for new generation.

| Product/edge | Proposed classification | Rationale and boundary |
| --- | --- | --- |
| `genetics_results -> genetics_qc_cases` | `validation_dependencies` | Expected answers/failure cases test a method; they are not the biological input to a new result. A validation attestation binds method/code/fixture/report hashes without putting answers in agent input. If those answers are actually consumed during prediction, they remain forbidden actual ancestors. |
| `genetics_results -> igsr_ld_reference` | Remove unconditional edge; retain method-conditional LD group with `study_ld_matrices` alternative | A single-instrument Wald ratio and basic ABF colocalization do not universally require a dense LD matrix. Methods that require LD must declare compatible panel, ancestry/build, alleles and variant ordering. No method is qualified by this catalog edit. |
| Remaining `genetics_results` unconditional edges | `assay_gene_map`, `gwas_study_metadata` as carried product requirements | Exposure/outcome products still come from declared conditional groups; endpoint, assay, sample-size and ancestry requirements remain method-specific. Existing broad required-field lists are not universal executable method contracts. |
| `asof_normalized_packets` | Four input requirements: target, disease, evidence, HGNC | Applicable to the pinned contemporary adapter. Preserve every actual original and mapping parent. |
| `program_linkage` optional `vbt_linkage` | Optional input only for an explicitly qualified use; default denied | `vbt_linkage` has `evaluation_only` and `reference`; the evaluator deny wins for agent input. An optional edge is not a bypass. |
| `gold_mappings`, `dated_outcomes` optional groups | Evaluator workflow alternatives | Alternative adjudication/weak-label routes do not become automatic ground truth; no opening of their outputs is needed for Q02. |
| `feature_snapshots` optional genetics | Only a declared genetics-enabled arm | Unavailable genetics stays unavailable; no zero fill or implied readiness. |
| `scorer_artifacts -> dated_outcomes, split_definitions` | Genuine training ancestry; retain and block general inference-source admission | Training labels must not be relabeled as validation fixtures to satisfy a role checker. A separate future model-training/chronology contract is necessary. Q02 does not train or admit a scorer. |
| `vbt_compatibility_views` 38 component IDs | Required reference-reproduction inventory | Validate IDs and completeness for the selected pinned reproduction only. Missing historical components remain unavailable; do not substitute modern components. |

Validate dependency references and input cycles. Allow evaluator products to depend on other evaluator products. Reject agent-visible *artifact uses* with evaluation-only actual ancestors, including optional or generated descendants. A global ban on any product containing an evaluator dependency would mishandle legitimate training/evaluation descriptions. Separate validation attestations must never authorize scientific values.

## AACT use assignments

The neutral reports support seven acquired archive identities and technical restoration checks, not a qualified clinical benchmark. Assign use records against an exact protocol; do not infer origin from the filename, requested download date or being earlier than another file.

| Snapshot identity | What the retained metadata supports | Initial policy disposition |
| --- | --- | --- |
| 2023-01-01 | User-confirmed version, archive hash/size, restored tables, documented identifier exceptions | Candidate `origin_context` for a protocol that explicitly uses that origin; blocked for strict historical use until public-availability evidence is qualified. |
| 2023-07-02 | Actual dump date, although requested as July 1 | Technical intermediate/follow-up use. Do not label this July 1. Origin use requires a separate protocol and temporal qualification. |
| 2024-01-01 / 2024-07-01 | Intermediate archive identities and technical subset comparison | Follow-up/evaluator uses for the original 2023-origin trajectory; not universal restrictions on all future studies. |
| 2025-01-01 | Archive identity and the original two-year follow-up restoration | Evaluator use for that original study. A later protocol may nominate it as origin only through a new blocked/qualified use record. |
| 2026-01-01 | Explicit evaluator-only endpoint technical acceptance | `endpoint_evaluation`; no agent-visible grant. |
| 2026-04-01 | Explicit evaluator-only ascertainment technical acceptance | `ascertainment_evaluation`; no agent-visible grant. |

Exact first public timestamps and publisher checksums remain null. Local receipt/capture time is a present-day observation, not proof of historical first availability. Original bytes are not inspected again in this design review. No source labels, adjudication answers or database rows are read.

## Projection and runtime integration

Add canonical modules, for example `tether._catalog` and its tests; register them in the finite module inventory. Do not edit `src/asof/provenance.py`, `maintenance.py`, other pinned engine modules, archived code fingerprints or old study plans. Leave old schema-1 callers documented as weaker. Passing schema 2 directly to a legacy reader must continue to fail.

1. Validate the new policy and all exact input bindings using bounded, duplicate-key rejecting JSON reads. The requested use/frame/cutoff must match a policy record. Check **every supplied source node, every normalized artifact and all parents**, including unused nodes; checking only selected dataset IDs is insufficient.
2. Reject missing/conflicting receipts, undeclared artifacts, role/use changes, undeclared ancestors, unknown classification, declared future lineage and forbidden evaluator descendants before backend invocation or biological-value parsing. Record-level publication checks still occur when the existing engine parses eligible packets, before dispatch; preflight cannot know unparsed publication fields. Catalog eligibility is additional to existing temporal/receipt/publication gates, not a replacement.
3. Reserve a fresh destination and copy the exact inspected policy, case, snapshot/manifest and selected receipt bytes into the attempt using atomic no-clobber publication. Bind their hashes. Invoke the engine using these immutable copied inputs and a frozen schema-1 projection, **never the original mutable control-file paths checked earlier**. Preserve relative resolution: copied snapshots need their selected normalized packet files copied and verified under the same relative layout, or an explicit checked relocation binding; moving only `snapshot.json` changes the engine's base directory and is insufficient. Stable-read/copy verification is necessary to avoid validating one file and executing changed bytes. Original raw payloads retain their approved root, source hashes and runtime verification; copying every raw source is not required. This is not an OS sandbox.
4. Make the projection narrowly represent the selected use: no unknown/extra products gain an allowed role. Prefer a complete structurally valid schema-1 projection with nonselected products denied, or a documented minimal execution-only projection; choose one and test it consistently. Preserve legacy field semantics within the projection. Its hash is bound to policy, use, exact input inventory and wrapper/code version. A projection is not a new global catalog.
5. Archive both the schema-2 policy and projection in the outer run receipt. On canonical verification, reconstruct the projection and repeat policy-to-case/snapshot/source bindings from retained bytes before accepting stronger guarantees. Tampered use records, omitted policy, changed artifact hash, switched cutoff or a schema-1 projection transplanted from another run must fail even if the legacy inner receipt is internally valid.
6. Report legacy byte/semantic checks separately from canonical artifact-policy consistency and from scientific qualification. No old run is upgraded automatically. New scientific execution remains separately authorized/frozen; Q02 fixture checks do not reopen closed experiments.

For `inspect-source`/`build-snapshot`, preflight the explicit raw manifest first. Generated packets must then be registered against actual output hashes and complete parent identities before they receive a usable new-policy record. Q02 need not rerun ingestion to demonstrate this: existing retained snapshot metadata plus fictional fixtures suffice. Fail closed if no canonical wrapper supports a requested policy operation.

## Exact reader/consumer migration surface

| Consumers | Current behavior and required handling |
| --- | --- |
| `src/asof/maintenance.py` | Full schema-1 structural check, acquisition reports and sole legacy updater. Leave frozen; new reconciliation must independently enforce exact receipt ID/URL as well as bytes/path/release. |
| `src/asof/provenance.py` | Lightweight catalog reader, product role check and `InputGraph`. Leave frozen; never discard schema-2 constraints by merely calling this reader on a projection outside canonical binding checks. |
| `src/asof/chrono.py`, `semantics.py`, `artifacts.py`, `cli.py` | Admission, proof reconstruction, effective policy archival and verification. Keep archived policies unchanged; outer canonical guard supplies the additional policy binding. |
| `src/asof/ingest.py` | Schema-1 inspector/builder and content-addressed receipt copies. Preserve it; canonical preflight/post-build registration is explicit. |
| `src/asof/study/source_fact_inputs.py` | Also reads `roles` directly after `catalog_index`; cannot assume replacing one helper covers this path. Frozen study only. |
| `src/asof/study/source_fact_sources.py` | Accepts a full document or an already indexed mapping; a raw mapping cannot be treated as a schema-2 policy. Frozen study only. |
| `src/asof/study/source_preparation.py`, `src/asof/archive/core.py`, `src/asof/archive/interpretation.py` | Actual lineage/read protections and frozen archive closure. Do not alter archive semantics or code pins. |
| `packages/tether/src/tether/_cli.py`, `_presentation.py`, `_semantics.py`, `_aliases.py` | Canonical extension point. Bind policy/projection and advertise the exact stronger path; aliases to legacy APIs do not inherit it automatically. |
| `tools/validate.py`; `tools/framework/prepare_v02_inputs.py`, `run_local_pilot.py`; `tools/data/Sync-DownloadCatalog.ps1` | Existing schema-1 tooling. Add a separate schema-2 structural fixture validation; do not replace their pinned catalog argument behind the caller's back. |
| `tools/science/prepare_source_validation_set.py`, `prepare_source_validation_register.py`, `run_source_fact_pilot.py`, `run_comparison.py`, `t6_challenge.py` | Frozen/earlier study entry points with current-path or exact catalog pins. New policy does not authorize reruns or repoint them. P05 pins the pre-TETHER catalog hash, not today's live schema-1 hash. |

This is the direct reader/admission and explicit catalog-path inventory from bounded `src`, `packages/tether`, `tools` and named tests. Transitive callers inherit the stated boundaries. It is not a claim that every historical prose mention or dynamically generated script is a current executable consumer.

## Neutral evidence and immutable receipts

The public AACT reports establish retained archive identity assertions, technical checks, seven version dates and exact scope. The normalization report binds the canonical build report; its 2,206-file / 9,038,960,079-byte selected frame has no missing inputs. This does not supersede the older 65-missing interpretation slice or qualify biological absence. The P05 neutral frame independently names 137 originals / 2,866,248,239 bytes; do not pool these scopes or rerun its closed study.

A catalog reconciliation can verify **metadata hashes, source/receipt identity consistency and explicit status scope** from these records. Without reading original bytes it cannot claim fresh payload integrity or parsing. Source records copied from old reports must say `inherited_retained_check` with the original check date, rather than `freshly_verified` today.

Before any new acquisition promotion, the canonical reconciler checks queue `receipt_id`, dataset, release, exact URL and normalized relative path; receipt status; file size; source hash and optional publisher digest separately. Missing identity is unresolved, not a permissive legacy fallback. Manual archives use their own retained acquisition/technical evidence kind, not invented URLs or transport jobs. The reconciler must not promote statuses simply because catalog-named files exist.

Copy already inspected receipt bytes under `manifests/receipt-archive/<sha256>.json` when authorized to write that root; if an existing content-addressed file differs, fail. Never rewrite a pinned transport receipt. A future separate downloader may emit new immutable attempt/observation records and link them to the original capture; no changes to `Start-DownloadBatch.ps1` or the stopped monitor are included. This design review performs no E: writes.

## Implementation order and stopping conditions

1. Add pure schema-2 validation and deterministic product migration with the two explicit genetics corrections. Preserve all original status fields and pin the schema-1 source. Validate references, selected-frame review states and conditional semantics with fictional tests.
2. Implement one exact artifact/use selector, stable copying and deterministic projection. Run the role, path, ancestry and file-swap negative tests before integrating the wrapper.
3. Integrate canonical execution/verification binding and retain existing schema-1 compatibility tests. Prove zero backend calls on rejection and reject an archived-policy/projection substitution. Qualify the new wrapper revision separately from Q01.
4. Import the canonical contemporary frame and AACT neutral technical records as explicit scoped observations. Keep AACT predictor use blocked, clinical labels excluded and numerical genetics/scorer qualification unchanged. Require a later explicit import for P05 or any other frame.
5. Document capability boundaries and exact migrated frame counts. Record that 178 indexed products does not mean 178 admitted products. Do not declare Q02 complete until the new implementation tests pass; this proposal alone is not completion.

No external dependency blocks steps 1–3. A missing selected neutral receipt, ambiguous artifact identity or unknown intended use blocks that artifact only; the default-deny schema and fictional tests can still be completed. Historical first availability, scientific interpretation, missing study/assay metadata, complete regional genetics and future model training are scientific/data limitations rather than reasons to halt the deterministic catalog migration.
