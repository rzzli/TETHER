# TETHER equal-policy validator specification

This is the complete declared comparison contract for qualified TETHER 0.5.1 / compatibility engine 0.3.12 at commit `4dcd16c`. The machine-readable specification is `policy-spec.json`; it contains the exact typed field/default inventory and reference source hashes. This contract is frozen before scored comparisons; changes require a new revision with preserved prior bytes.

## Boundary and common interface

Both validators receive the same native JSON/file bytes, trusted runtime identity manifest, source roots and external anchors. They may use different implementations. The independent validator must not import TETHER/asof, call their validation helpers, or turn their answer into its own verdict.

`validate_bundle(root, descriptor, *, scratch_dir=None)` returns `schema_version`, `control_id`, `decision`, `stage`, `violated_obligations`, `checked_scope`, and `observables`. Decision is one of `accept`, `reject`, `inspect_only`, `unsupported`, or `error`. Diagnostic reason/details may be added. Missing implementation coverage is `unsupported`; infrastructure/programming failure is `error`. Neither is a correct rejection by default.

Descriptor keys are exactly `schema_version`, `control_id`, `operation`, `variant`, `paths`, `options`, and `anchors`. Its schema version is 1. Operations are `prepare_run`, `verify_run`, and `inspect_run`. Variants are `core_v2_catalog1` and `artifact_policy_v2`. Paths may name case, snapshot, catalog, scorer, replay, local_model, catalog_policy, policy_roots, run_dir, or trusted_runtime. They are relative references contained in the frozen bundle. Optional omitted/null paths are absent. Native file payloads retain their original schemas, defaults and fingerprints.

Options are budget, disabled, review_enabled, process_limits and policy_use. Anchors are receipt_sha256 and frame_sha256. Nonempty inapplicable fields are errors, not ignored instructions. Artifact-policy mode requires all policy/catalog/use/roots/frame inputs, non-demo profile and offline extraction without scorer/replay/local-model. Ordinary catalog1 inputs have explicitly weaker artifact-authorization scope. A schema1 projection alone never becomes schema2 authorization.

`prepare_run` validates inputs only. It returns admitted observation IDs, eligible observed case/program candidates, ordered native exclusions, and a null-or-string scorer preflight reason. It performs no quote/select/replay, feature computation, prediction, budget consumption or scheduler simulation. A zero budget can prepare successfully. Selection, feature values, scorer results and zero-budget abstention belong to `verify_run` fixtures.

`verify_run` consumes the same sealed native tree for each implementation and applies source-inclusive canonical verification, including state/prose checks. It may validate incomplete inner runs; outer success requires a completed inner run. `inspect_run` reads recoverable durable records without retrying or converting them into verified success. Outcomes that exclude unavailable evidence or abstain from prediction are distinct from invalid-contract rejection.

Schema2 preparation uses a caller-supplied empty scratch directory outside the frozen bundle. Each implementation retains immutable control/packet/mapping/provenance/receipt copies and rechecks original/copy stability. Raw originals remain external. Format-specific copied-byte overhead is measured separately; decision parity alone does not prove matching physical execution or identical I/O.

Defaults: 16 calls, 32,000 input tokens, 8,000 output tokens, $0, 300 workflow seconds, one review retry; no disabled categories; review enabled. Outer process defaults are 3,600 seconds and aggregate 16 MiB output, independently bounded at 64 MiB. Local retrieval defaults are 12 records / 12,000 bytes / canonical wire format; default selection cap is three. Native defaults and allowable ranges remain explicit below.

## Required obligations

Every obligation below must be implemented and covered or reported as a gap. Broad families are not permission to test one easy case and claim all their clauses verified. The corpus coverage table must enumerate clauses and boundaries actually exercised.

### EP-WIRE-01 — Native JSON, typed contracts and normalization

Operations: prepare_run, verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Reject duplicate JSON keys, malformed UTF-8/JSON and NaN/Infinity. Typed dataclass decoding rejects unknown fields, missing required fields, bool-as-int/float and wrong container/scalar types; decode date as exact YYYY-MM-DD and aware datetime normalized to UTC. Preserve the native required/default field inventory recorded in wire_contracts.
- Canonical fingerprints encode frozen dataclasses/enums/mappings/sequences, normalize aware timestamps, sort keys, use UTF-8 without ASCII escaping and compact separators, reject nonfinite numbers, and preserve native numeric spelling such as 1 versus 1.0. Do not fingerprint a lossy normalized replacement of original policy control bytes.
- Core defaulted null mapping fields are limited to Snapshot.coverage and Observation.source_locator/source_metrics/missingness. Other nulls follow the typed contract. Deep immutability is a runtime invariant, separately exercised; a file validator alone cannot prove immutable Python objects.

Source boundaries: `src/asof/serde.py`, `src/asof/contracts.py`.

### EP-CASE-01 — Supported cases and hypothesis identity

Operations: prepare_run, verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Require schema 2 and task T1 or T6; nonempty case ID and target/indication IDs, namespace versions, intended action and modality. Require exact aware origin_at whose UTC date equals origin; snapshot origin and origin_at must equal the case.
- Require eligible hypothesis mapping/annotation Availability. The hypothesis fingerprint contains target_id, indication_id, target_namespace_version, indication_namespace_version, intended_action, modality and tissue, including null tissue; it excludes availability.
- Action/modality are nonempty strings, not an invented closed biomedical vocabulary. T6 does not require an endpoint or active phase. Do not silently substitute canonical IDs or alter hypothesis fields.

Source boundaries: `src/asof/contracts.py`, `src/asof/chrono.py`.

### EP-PROGRAM-01 — Program context and T1 eligibility

Operations: prepare_run, verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Every supplied program, including T6 context, needs eligible availability, nonblank program/molecule/sponsor/status, integer phase 0..4, finite mapping confidence in [0,1] and eligible_since <= origin.
- T1 additionally requires program and endpoint, active phase 1 or 2, matching phase_1_to_2 or phase_2_to_3 endpoint, positive horizon and mapping confidence >0. T6 may retain unresolved confidence zero.
- Program-specific observations are queryable only for matching supplied program ID with confidence >0; null program IDs are contextual. With supplied zero-confidence mapping, program-specific observations are excluded as unresolved_program_mapping.

Source boundaries: `src/asof/contracts.py`, `src/asof/chrono.py`.

### EP-TIME-01 — Information availability without invented historical dates

Operations: prepare_run, verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Availability basis must be nonblank. Each known first/release/record/annotation date is conservatively end-of-day UTC; none may exceed the exact cutoff or retrieved_at. This permits same-date exclusion for a cutoff earlier than end-of-day.
- An aware known_public_by with nonempty evidence_ref may supply a bound when component dates are unknown; it must not exceed cutoff or retrieved_at date. Without that bound all four component dates are required. Retrieval date alone never proves historical availability.
- Computed node/result timestamps are a separate clock: eligible information ancestry controls eligibility; newly computed results may be after origin. Do not impose an extra availability gate on computed-node metadata or computed-observation own availability.

Source boundaries: `src/asof/contracts.py`, `src/asof/provenance.py`, `src/asof/chrono.py`.

### EP-DAG-01 — Complete structural lineage and role validation

Operations: prepare_run, verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Require a nonempty unique source-ID inventory, valid source/release/hash identity, all references present and an acyclic graph, including unused supplied nodes. Validate every source path without opening ineligible bytes.
- Each source role must be agent_evidence or reference. Non-demo catalog1 requires a registered dataset, role included in product roles and no evaluation_only role. Computed nodes require nonempty parents and versioned method with aware computed_at; raw nodes cannot declare parents.
- Artifact/source identifiers cannot collide. Missing lineage is invalid, never a default to current annotation or an untracked parent.

Source boundaries: `src/asof/provenance.py`, `src/asof/chrono.py`.

### EP-DAG-02 — Ancestral temporal eligibility

Operations: prepare_run, verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- For all parents in each relevant closure, apply availability to raw informational nodes. Historical profile requires verified_historical, or reconstructed only when allow_reconstructed is true; contemporary/demo reject unverified classification.
- Core admission reports ineligible artifact/observation exclusions rather than rejecting the whole valid request, and does not open rejected packet bytes. Derived node own availability/classification and artifact own availability/classification do not replace ancestor eligibility.
- Core structural validation includes unused nodes but core byte/receipt proof verification covers eligible artifact closures; schema2 all-supplied inventory has the stronger obligations in EP-POLICY-02/03.

Source boundaries: `src/asof/provenance.py`, `src/asof/chrono.py`.

### EP-SOURCE-01 — Source bytes, transport receipts and proof completeness

Operations: prepare_run, verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Every eligible packet and its complete ancestor closure requires exact hashes and identities. Real raw sources require pinned receipt paths/hashes; synthetic_demo may omit receipts. Computed inputs remain hash-bound even when their computation date is newer.
- Core raw receipt verification requires completed status, source SHA256, dataset/release, safe relative payload path and actual byte size. For public_download_receipt basis additionally require known_public_by >= receipt completion, evidence_ref == receipt_sha256 and source_url == receipt URL; alternative eligible availability bases do not inherit a false download cutoff.
- Verification reconstructs the complete eligible proof inventory even with no external anchor and even when no observation was selected. Missing, extra or altered parent proofs reject. Original source bytes/receipts must remain available for this source-inclusive endpoint.

Source boundaries: `src/asof/provenance.py`, `src/asof/chrono.py`, `src/asof/artifacts.py`.

### EP-PACKET-01 — Artifact inventory and normalized packet integrity

Operations: prepare_run, verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Require schema2 snapshot with nonblank ID, unique artifact IDs and paths, explicit releases, lowercase 64-hex hashes and agent_evidence packet role. access_approved false is a core exclusion before catalog-role lookup; schema2 selected grants require access_approved true.
- Eligible packet paths stay inside snapshot root; file must exist and fit 64 MiB. Hash the bytes actually decoded. Require EvidencePacket schema2; duplicate observation IDs across all read eligible packets reject, including excluded observations.
- Do not silently truncate oversized packets, merge conflicting IDs or treat unopened/rejected input as empty biological evidence.

Source boundaries: `src/asof/chrono.py`.

### EP-OBS-01 — Scientific record validity, lineage and publication

Operations: prepare_run, verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Require observation identity/target/indication/statement, complete input_refs, supported source kind primary/integrated/computed/clinical, supported category/status/polarity, mechanism direction inhibit/activate/degrade/uncertain/not_applicable, and QC passed/failed/not_run. Computed observations need computed_at and versioned method.
- Validate positive standard error/sample size, p-value in [0,1], paired nonreversed confidence limits. Numerical features require observed status, passed QC, nonclinical source/category, versioned method, nonempty feature_scope, known feature/category mapping and declared range.
- Observation ancestor closure must be a subset of its artifact's closure. Apply raw information eligibility and noncomputed observation availability; reject malformed publication types/year outside 1..9999, but exclude inconsistent date/year or explicit future publication. A year overlapping origin is not converted into an exact date.

Source boundaries: `src/asof/contracts.py`, `src/asof/chrono.py`.

### EP-SCOPE-01 — Hypothesis/program capabilities and contextual visibility

Operations: prepare_run, verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Retrieval requires exact target, indication and specialist category plus permitted program identity. Nonmatching records may remain admitted but are not offered to that specialist or committed.
- Features require exact seven-field hypothesis fingerprint, including intended action, modality and tissue. Mismatched features are suppressed in specialist views and deterministic aggregation; the raw observation remains context, with outside_applicability missingness.
- Specialists receive evidence views and case JSON, not path/catalog/environment capabilities. This is a trusted-code API boundary and source-text treatment policy, not an OS sandbox or proof that a model obeys instructions.

Source boundaries: `src/asof/chrono.py`, `src/asof/agents.py`, `src/asof/features.py`, `src/asof/ledger.py`.

### EP-FEATURE-01 — Deterministic dependency-aware feature reconstruction

Operations: verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Use schema asof-features-v2 and mean_of_unique_dependency_groups_v2. Join dependence transitively through explicit group, study ID or shared cohort, including observations without applicable features; different labels do not establish independent sampling.
- Within each connected component and feature, identical values count once; conflicting values exclude the whole component. Average accepted component values; sort observation IDs/excluded groups. Missing becomes conflicting or not_measured, never zero evidence weight by default.
- Derive missing reasons from coverage nonobserved statuses, source_incomplete when nonempty coverage is not complete, and outside_applicability for mismatched feature scopes. Rebuild and compare the entire archived FeatureVector.

Source boundaries: `src/asof/features.py`, `src/asof/semantics.py`.

### EP-SCORER-01 — Scorer predispatch validity and chronology

Operations: prepare_run, verify_run. Variants: core_v2_catalog1.

- Validate schema2, synthetic_demo/frozen_model kind, fixed feature schema/aggregation, nonempty model/coefficient inventory, known feature names, required/imputed subsets, training hash, coverage [0,1], finite parameters, range-valid frozen imputations and supported calibration declaration.
- Synthetic model weights only pair with synthetic_demo profile; synthetic profile cannot use a frozen real scorer. Training origin, training-label and any calibration-label cutoff must each be strictly before the case origin date; equality rejects.
- Invalid scorer inputs reject before backend calls even for T6 or otherwise inapplicable models. A well-formed but out-of-scope scorer yields explicit abstention, not validation rejection.

Source boundaries: `src/asof/scorer.py`, `src/asof/workflow.py`.

### EP-SCORER-02 — Scoring applicability, contributions and abstention

Operations: verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- T6 always has null probability and audit_only status. T1 with no model abstains; a model outside endpoint/horizon/phase/action/modality/namespace scope abstains. Incomplete run always abstains with run_incomplete.
- For an applicable complete T1 run, enforce required features, minimum present coefficient coverage and explicit frozen imputation; otherwise abstain with the declared reason. Compute sorted contributions value*coefficient, imputation flag and source observation IDs, then stable logistic(intercept+sum); reject nonfinite logit.
- Compare complete Prediction, not probability alone. Synthetic profile marks outputs synthetic. Artifact-policy runs have no scorer and cannot acquire one through a generated packet or projection.

Source boundaries: `src/asof/scorer.py`, `src/asof/semantics.py`.

### EP-POLICY-01 — Schema2 policy and original catalog integrity

Operations: prepare_run, verify_run. Variants: artifact_policy_v2.

- Strict schema2 envelope/product/artifact/use field sets, finite JSON, exact UTC timestamps, provider/product uniqueness, valid roles, exact reconstructed schema1 catalog fingerprint plus original-byte SHA256. Preserve all original metadata/status values.
- Validate known/disjoint input and validation dependencies, conditional group references, required components and acyclic input-dependency graph. Genetics QC remains validation-only and LD method-conditional where those products exist. This checks declared classification, not scientific sufficiency or inferred completeness of every conditional requirement.
- Artifact identity fingerprints dataset/release/root/path/hash/bytes. Validate safe portable paths, kinds/raw-parent relationship, full ancestry, provenance evidence, receipt references/URL, and not_established scientific status. Manual archives remain blocked for inference. Allowed selected products must have reviewed_for_selected_frame dependency status.

Source boundaries: `packages/tether/src/tether/_catalog_policy.py`.

### EP-POLICY-02 — Exact use/frame/grant and all supplied inventory authorization

Operations: prepare_run, verify_run. Variants: artifact_policy_v2.

- Require all policy/catalog/use/roots/frame inputs together; only run, non-demo, offline extraction without scorer/replay/local-model. Select one allowed nonempty nonevaluation use bound to exact case/snapshot fingerprints, profile/origin and independent frame hash.
- Absolute local distinct root aliases include metadata and distinct raw/snapshot aliases. Raw root and actual snapshot parent must agree. Validate no physical path aliases or collision with copied snapshot controls.
- Every supplied source/packet, including unused nodes, must match exactly one granted artifact identity, role, kind, metadata and parent edges; grants equal supplied inventory and include every actual ancestor. Deny evaluator/comparison roles, evaluator products, scorer_artifacts and missing/extra grants. Packet access must be true; derive a schema1 projection granting only selected-use roles.

Source boundaries: `packages/tether/src/tether/_catalog_policy.py`, `packages/tether/src/tether/_catalog_binding.py`, `packages/tether/src/tether/_cli.py`.

### EP-POLICY-03 — All-node raw availability and receipt consistency

Operations: prepare_run, verify_run. Variants: artifact_policy_v2.

- All supplied raw inputs must have eligible availability/classification at use origin, even if unused by any packet. All selected bytes and sizes, metadata evidence and receipts are checked; unused input cannot bypass these checks.
- Require exact receipt ID/dataset/release/URL, completed status, integer byte count, payload hash, eligible UTC completion and safe relative transport path. Only slash/backslash spelling in transport receipt paths is normalized; case, IDs and URL remain exact.
- For every public_download_receipt node, the bound cannot predate receipt completion, evidence_ref must equal the pinned receipt hash and node URL must equal receipt URL. Preserve legitimate separately evidenced historical bases. A present-day download does not prove historical availability.

Source boundaries: `packages/tether/src/tether/_catalog_binding.py`, `packages/tether/src/tether/_catalog_policy.py`, `src/asof/provenance.py`.

### EP-POLICY-04 — Copied controls, immutable receipts and actual engine binding

Operations: prepare_run, verify_run. Variants: artifact_policy_v2.

- Seal exact policy/catalog/case/snapshot/root controls, deterministic projection/decision, all snapshot-root packet/mapping bytes, selected metadata evidence and receipt copies in the reserved output. Raw originals remain external; archived receipt bytes must equal still-required original pinned receipt bytes.
- Reconstruct the decision/projection and complete copies/external/receipts/provenance inventories from sealed controls; match byte hashes and sizes; reject extra/omitted proof rows or changed execution paths. Re-admit copied packets before dispatch and again for verification.
- Actual engine inputs must equal decoded copied case/snapshot/projected catalog, scorer null, snapshot_base the copied inputs directory and backend offline-extractive-v1. A projection alone is never an artifact authorization.

Source boundaries: `packages/tether/src/tether/_catalog_binding.py`.

### EP-EXEC-01 — Budget and effective configuration

Operations: prepare_run, verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Use default budget calls16/input32000/output8000/cost0/time300/retries1 unless explicitly overridden. Calls/tokens/retries are nonnegative integers; cost finite nonnegative; time finite positive. Disabled categories and review-enabled boolean remain archived effective configuration.
- Before dispatch require case/store temporal consistency, explicit live snapshot base and scorer preflight. Query-only/archive-verification stores cannot execute. Reserve only when calls/time and used+quote token/cost bounds permit; inclusive token/cost caps, strict elapsed-time cutoff.
- Preserve separate outer process defaults time3600 and output16MiB with maximum64MiB; no conflation with workflow budget.

Source boundaries: `src/asof/workflow.py`, `packages/tether/src/tether/_process.py`.

### EP-EXEC-02 — Backend request, bounded retrieval and local response provenance

Operations: prepare_run, verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Offline selects all observed eligible views with zero usage. Replay schema2 entries require exact request fingerprint at runtime quote/select, increment only selection; replay and local-model config are mutually exclusive. For sealed recorded runs, validate retained provenance.document against reconstructed requests, selections and usage. The original replay path need not remain available; its original byte hash is an opaque declaration because retained JSON formatting may differ.
- Local config requires explicit HTTP127.0.0.1 port with no credentials/path/query/fragment; declared weights/runtime hashes; generation1..256, timeout(0,120], integer seed, selection cap1..3(default3), retrieval count1..100(default12), bytes1024..64000(default12000), supported wire format. No live calls in BG02.
- Local retrieval ranks literal case-token overlap then ID, retains whole records within record/byte caps, and preserves case/instructions/feedback. Rebuild source-linked retrieval traces and exact escaped prompt/payload (16KiB prompt cap); local response capped1MiB, truncated must be false, content exactly unique allowed IDs within cap and valid measured integer counts. Verify request/payload/response hashes, quotes, attempt/account association, selections and source scope. Invalid/unqualified responses retain unknown quoted usage; fully valid overquote responses retain measured usage and terminal breach.

Source boundaries: `src/asof/agents.py`, `src/asof/local_model.py`, `src/asof/retrieval.py`, `src/asof/wire.py`.

### EP-EXEC-03 — Selections, reviews and immutable source-grounded claims

Operations: verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Only unique IDs inside the actual offered specialist request can pass review. Review retries occur only for rejected selection and within configured retries; backend failure does not trigger automatic retry for that category.
- Claims require currently admitted immutable record fingerprint, exact case/category/program capability, observed status and write-time noncomputed availability. Claim ID is claim- plus first20hex of canonical case-ID/evidence fingerprint; extraction_mode is verbatim_source_selection.
- Reconcile accepted review order to complete committed claim order, or a prefix only with explicit claim-commit time exhaustion. Journal committed claims must equal ledger; unselected, duplicated, fabricated or altered source claims reject.

Source boundaries: `src/asof/agents.py`, `src/asof/ledger.py`, `src/asof/workflow.py`, `packages/tether/src/tether/_semantics.py`.

### EP-EXEC-04 — Journal, accounting, category state and termination

Operations: verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Verify hash-chain sequence/previous hashes, exact durable journal/trace bytes, one plan, complete eight-category inventory, run/case/snapshot/backend/configuration identity, reservation capacity and nonoverlapping uniquely identified attempts with one accounting event each.
- Measured+estimated totals must equal total usage and calls equal dispatches. Unknown usage equals reserved quote, never measured zero. Fully validated overquote local usage requires exact breach event and no later dispatch. Finalized run cannot have unresolved attempts.
- Replay canonical facade category state transitions, ordered specialists/attempts, review/claim flow, retrieval coverage, terminal failure/budget/interruption status, and final feature/prediction/status fingerprints. Known error classes constrain status; arbitrary custom exception inheritance cannot be proven from class-name strings.

Source boundaries: `src/asof/journal.py`, `src/asof/workflow.py`, `src/asof/semantics.py`, `src/asof/local_model.py`, `packages/tether/src/tether/_semantics.py`.

### EP-VERIFY-01 — Inner receipt byte integrity and external anchor

Operations: verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Require v2 receipt and exact required run/inputs/ledger/features/prediction/trace/dossier/journal output set; check each hash, input fingerprint and run linkage. Validate declared auxiliary_outputs restricted to request.json/backend-execution.json. Local execution archive is mandatory for local backend.
- External receipt anchor when supplied must match; without one report no external anchor rather than claiming tree replacement detection. request.json can be absent or a compatible old unsealed auxiliary; hashing it does not add a semantic reconstruction obligation not implemented by the verifier.
- Always source-inclusive in BG02. Direct canonical engine verification may report code_matches_current false without rejecting an otherwise valid v2 run; outer verification requires current inner code. Inner receipt code inventory is evidence, not an external trust anchor by itself.

Source boundaries: `src/asof/artifacts.py`, `packages/tether/src/tether/_presentation.py`.

### EP-VERIFY-02 — Semantic source re-admission and final output reconstruction

Operations: verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Rebuild eligible proof inventory, re-admit source packets from originals, compare complete admitted fingerprint map, exclusions, per-category observed/nonobserved/source coverage and citation identities. Resealing local hashes cannot repair a source/claim or proof mismatch.
- Rebuild features, configured scorer result/contributions and final trace fingerprints; perform canonical facade state replay and deterministic complete engine dossier reconstruction, accepting platform LF/CRLF rendering equivalents.
- Report byte integrity, semantic consistency, source binding, code identity and scientific validity separately. Verified software consistency never means validated biology, calibrated probabilities or independent source authenticity.

Source boundaries: `src/asof/artifacts.py`, `src/asof/semantics.py`, `packages/tether/src/tether/_semantics.py`.

### EP-VERIFY-03 — Outer facade envelope, complete inventory and launcher proof

Operations: verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Outer success requires no retained failure, exact completed evaluation-only/agent_visible=false/not_established envelopes, source-inclusive completed inner run with current code, current pinned launcher source/version proof, exact receipt/manifest/engine hashes and complete files/directories inventory.
- Require exact outer journal event schedule and proof/dispatch/supervision/finalization bindings; compare all artifact path/hash/size descriptors. Verify exact first-header-only TETHER dossier projection and absence of unbound policy directory when no policy binding.
- Independently pinned trusted_runtime supplies only reference release/source identities. It does not contain oracle labels or grant arbitrary acceptance. Old differently pinned facade archives are separate legacy compatibility interfaces, not silently accepted as this canonical release.

Source boundaries: `packages/tether/src/tether/_presentation.py`.

### EP-IO-01 — Path, file-kind, size and stable-read boundary

Operations: prepare_run, verify_run, inspect_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Envelope path references are contained relative paths. Native source paths follow their declared approved roots: forbid traversal/absolute/drive/ADS relative paths and require post-resolution containment. Do not make core catalog1 claim schema2 root authorization.
- Facade/policy reads reject links/reparse points/nonregular files, bound bytes before/open/during read and check file identity before/after. Metadata/trace bound64MiB; policy controls16MiB; packet64MiB; ledger/dossier256MiB; selected policy passes have300s I/O deadline.
- Read stability is per operation, not exclusive filesystem ownership, sandboxing, authenticated data provenance or a race-proof global transaction. Native malformed records and limit failures reject; no silent truncation.

Source boundaries: `src/asof/serde.py`, `src/asof/study/stable_read.py`, `packages/tether/src/tether/_presentation.py`, `packages/tether/src/tether/_catalog_binding.py`.

### EP-FAIL-01 — Durable failures and inspection-only recovery

Operations: inspect_run, verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Inspection reads one durable valid hash-chain prefix; an unterminated last partial line may be ignored only in inspection. Report unresolved attempts, measured usage and conservative estimated upper usage including outstanding reservations; never automatically redispatch.
- Outer failed/interrupted attempts retain available journals, diagnostics/captures and cleanup uncertainty; failed attempt cannot qualify as success. Failure metadata publication itself may fail; report the limitation rather than asserting every storage failure leaves complete records.
- Reservation/write durability, nested immutability, bounded commit timing, no-clobber output race behavior, interruption and cleanup are runtime-only invariants tested through common scripted controls. A validator reading a record cannot independently prove that physical execution/history occurred.

Source boundaries: `src/asof/journal.py`, `src/asof/workflow.py`, `packages/tether/src/tether/_presentation.py`, `packages/tether/src/tether/_process.py`.

### EP-PROCESS-01 — Success supervision evidence and bounded execution scope

Operations: prepare_run, verify_run. Variants: core_v2_catalog1, artifact_policy_v2.

- Validate positive finite outer deadline and integer output cap1..64MiB. Success report must use exact schema/method/keys/limits, started and reaped true, both EOF true, termination exited, no cleanup errors and exact retained/observed stdout+stderr counts within cap.
- Elapsed timings finite nonnegative; execution strictly less than deadline, total >= execution. Exact-cap output succeeds; observed extra byte fails and is not retained above cap.
- Actual launch-once polling, deadline+pipe-EOF enforcement, separate5s cleanup and owned-child termination are execution-control tests, not inferred from self-declared timing. No process-tree containment, OS-process-creation preemption, Linux qualification or arbitrary embedded Windows multithreaded guarantee.

Source boundaries: `packages/tether/src/tether/_process.py`, `packages/tether/src/tether/_presentation.py`.

## Runtime-only invariants

- Deep immutable admitted/query/ledger/finalized objects.
- Exclusive new output reservation and concurrent writer/no-clobber behavior.
- Journal write/fsync ordering, interrupted writes and available failure diagnostics.
- Actual request/quote/dispatch sequencing and no automatic billed-call recovery.
- Actual local transport loopback/no-redirect/payload/response bounds (only fake opener in BG02).
- Monotonic workflow timeout checks including long claim commits.
- Owned child deadline/output/EOF cleanup and reaping.
- Windows bounded atomic replacement and primary error preservation.

These require common scripted execution controls and retained witnesses. They remain in project coverage but cannot be attributed to a file validator merely because a self-consistent transcript declares them. No live model/server/provider is run for this comparison.

## Trust and limitations

- Trusted runner code, local machine/OS, clocks and declared roots; no adversarial filesystem-owner or process-isolation claim.
- Externally supplied receipt/frame anchors are trusted caller selections, not derived from the artifact being judged.
- Source receipts/checksums prove byte/identity consistency, not authenticity or truth of biological data or publication assertions.
- Archived scorer training hash/date declarations do not inspect training data, establish no model pretraining leakage, or establish calibration.
- Stored local model/runtime hashes are launcher declarations, not remote-server attestation; measured token counts are validated adapter reports.
- Exclusion metadata and source completeness are declared scientific context; no availability test establishes biological absence.
- Both implementations use same frozen native bytes, approved paths, limits, anchors, runtime identities and observable comparison policy; oracle labels remain separate.

## Separate and legacy interfaces

- v1 receipt verification reports semantic consistency unavailable; no new v1 execution.
- Direct asof/tether legacy aliases lack canonical facade state/dossier/artifact-policy additions; not substituted for canonical endpoint.
- Relocated archive verifier preserves historical policy/source/code identities and does not execute archived Python; separate interface, not current outer run.
- Study-specific protocols under asof.study (native grammar/role experiments/four-arm/interpretation/generation/source-fact studies), historical closed study locks and evaluator CLI are not generic run endpoints.
- inspect-source/build-snapshot adapters and data download/clinical cohort/scorer training/MR computation are separate acquisition/science workflows; their produced normalized inputs are subject to this contract when supplied.
- T2-T5, H6, live paid model/provider and clinical efficacy/calibration are not supported claims of this comparison.

## Oracle, exposure and freeze

Expected decisions and observed-field projections live in a separate oracle, with explicit obligation IDs and exposure strata. Prior regression families are labeled exposed; developer-authored new controls are not represented as an independently blinded benchmark. Valid and invalid examples, exclusion versus rejection, scorer abstention, same-date/time edges, unanchored versus anchored evidence, and malformed/unknown usage all need paired controls. The current run must not tune either implementation against scored answers. Any post-freeze correction is a new revision with the old result retained.

No implementation parity, scientific quality, benchmark performance, speedup, or aggregate completion is established by this specification alone.

Recorded-run source/request binding is a normative obligation. A possible omission in current product replay verification is retained as an implementation question, not excluded from the oracle. Reconstruction uses the archived replay document; no new requirement to reopen its original formatted JSON file is introduced. Legacy v1 receipts are explicit unsupported separate-interface controls, not invalid historical artifacts and not part of supported-v2 accuracy denominators.
