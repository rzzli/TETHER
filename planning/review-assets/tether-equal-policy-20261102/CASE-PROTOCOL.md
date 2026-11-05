# Equal-policy synthetic case protocol — BG02

Status: **construction in progress; not frozen and not scored**. This document is the independently specified case/oracle protocol. It does not report comparative accuracy or completion of BG02.

## Question and comparison boundary

The comparison asks whether implementations enforce the same declared supported TETHER contract on identical supplied bytes, and what engineering/runtime cost accompanies that enforcement. An equal-policy claim requires every declared obligation below to be implemented or to remain an explicit blocker. A weak hash/schema diagnostic and reject-all control are separate ablations, not substitutes for the independent validator.

The input envelope references original runtime-format files. The case oracle is separate from the implementation-visible descriptor. Eligible input, valid abstention, invalid input, honest retained execution failure, and unresolved inspect-only recovery are different outcomes. A future source excluded from retrieval can be a valid input with missing evidence; it must not automatically be scored as an input rejection. Likewise, a correctly recorded failed backend call can have a valid verifiable record.

`prepare_run` stops at pre-dispatch input validation. It returns admitted observations, queryable observed candidates, ordered native exclusions and the scorer preflight reason. It does not quote/select evidence, consume budget, aggregate numerical features or predict. `verify_run` assesses a pre-produced sealed native record; scoring, selection, accounting and completed-failure oracles belong here. `inspect_run` reads retained recovery state without starting or repeating work. Accepted preflight with a zero-call limit is distinct from a later correctly abstained execution.

## Construction and independence

The corpus author determines outcomes from declared rules before running either implementation. Cases use fictional identifiers, data, sources, dates, effects and receipts. No observed trial outcomes, protected expert responses, model-generated biological conclusions or downloaded data enter this corpus. Primary source files are small. URLs use `example.invalid`.

Two exposure strata remain separately reported:

1. `exposed_regression`: a new small construction representing a defect already exposed in this repository's tests/reviews, such as future T6 program context, invalid scorer preflight, missing parent proofs, contradictory accounting, journal/ledger disagreement, or unused download-receipt availability.
2. `new_synthetic_construction`: newly written cases and boundary pairs. The policy, repository and previous tests are visible to the authors; these cases are not a blinded or independently held-out natural test set.

Synthetic success rates describe this finite conformance corpus. They do not estimate natural fault prevalence, clinical utility, model intelligence, scientific validity, or coverage of every possible malformed file. Shared specification and shared fictional file serialization are declared dependencies. The independent validator must not import or call TETHER/AsOf validation, admission, feature, scoring or verification implementations.

## Obligation and case map

| Obligation | Required constructions and independently expected behavior |
|---|---|
| EP-WIRE-01 | Valid strict JSON; duplicate key, unknown contract field, wrong primitive type and wrong v2 version reject. |
| EP-CASE-01 | Valid T1/T6; exact UTC origin and namespace-bound hypothesis; missing/mismatched origin or unsupported task reject. |
| EP-PROGRAM-01 | Supplied future program rejects for T1 and T6; T1 needs active eligible phase/endpoint; valid inactive T6 context remains usable. |
| EP-TIME-01 | Exact eligible cutoff boundary; later/unknown information excludes evidence; invalid case mapping availability rejects. Retrieval date alone cannot prove historical availability. |
| EP-DAG-01 | Complete acyclic all-node graph, explicit release/method identity and approved safe roles/paths; missing parents, cycles and evaluator-only ancestors reject. |
| EP-DAG-02 | Eligible older ancestors allow a newer computation; future annotations and unapproved reconstructed ancestry exclude the dependent packet. |
| EP-SOURCE-01 | Original bytes, exact receipt identity/size/hash and required proof closure; mismatches and omitted raw-parent proofs reject. |
| EP-PACKET-01 | Versioned packet with unique IDs and valid hash; duplicate IDs, conflicting identities, invalid role or altered bytes reject. |
| EP-OBS-01 | Valid measurements and complete observation lineage; future exact publication/year excludes, overlapping year is not imputed, inconsistent date/year excludes. |
| EP-SCOPE-01 | Target/indication/program gates and action/modality/tissue-bound feature scope; contextual evidence can remain while incompatible features are omitted. |
| EP-FEATURE-01 | Independent groups aggregate deterministically; shared study/cohort is not counted twice; within-group conflict remains missing/conflicting and can cause abstention. |
| EP-SCORER-01 | Valid schema/profile/training/calibration preflight; any invalid cutoff/schema/profile rejects before backend dispatch. |
| EP-SCORER-02 | Applicable synthetic scoring; no scorer, mismatch, missing requirements/coverage or undeclared imputation abstains; configured contributions must rebuild exactly. |
| EP-POLICY-01 | Complete schema2 policy/product/provenance declarations; malformed products/roles/records reject. |
| EP-POLICY-02 | Exact use/frame and grants cover the complete supplied inventory, including unused nodes; extra/missing grant and wrong frame reject. |
| EP-POLICY-03 | Used and unused receipt-derived bounds bind completion time, evidence reference and URL; equivalent UTC timestamps and independently valid alternative availability bases remain accepted. |
| EP-POLICY-04 | Copied controls and effective projection are bound and rechecked; changed internal projections or copied controls reject. |
| EP-EXEC-01 | Valid budgets/configuration; negative/invalid limits reject; a valid zero-call cap abstains without dispatch. |
| EP-EXEC-02 | Exact request/retrieval/replay/backend binding; wrong request fingerprints cannot admit a selection. |
| EP-EXEC-03 | Selected claims are unique, approved, category/case scoped and source-fingerprint bound; unsupported or changed claim content rejects. |
| EP-EXEC-04 | Calls, reservations, measured/estimated usage, journal claims and terminal status agree; known overquote remains measured, unknown usage remains estimated. |
| EP-VERIFY-01 | Inner receipt, required outputs, auxiliary request output and external anchor match; altered bytes/anchor reject. |
| EP-VERIFY-02 | Semantic feature/contribution/claim/trace rebuild and complete eligible source proofs agree; resealing only byte hashes cannot repair semantic contradiction. |
| EP-VERIFY-03 | Outer inventory, effective code identity, dossier projection and outer journal remain consistent; a mismatched presentation is not treated as verified. |
| EP-IO-01 | Safe bounded reads and regular files; traversal, missing or nonregular required inputs reject, without reading protected paths. |
| EP-FAIL-01 | Honest terminal failures preserve accounting; unresolved dispatch inspection retains uncertainty and never automatically repeats a potentially billed call. |
| EP-PROCESS-01 | Declared process limits and successful outer supervision agree; invalid bounds and contradictory retained process supervision reject. |

Every final case carries a stable ID, obligation IDs, a short normative rationale and an exposure stratum. Positive boundary controls accompany failure families where feasible. A single fault may trigger more than one contract rule; the oracle will identify the expected decision and minimum relevant obligations without requiring implementation-specific exception wording or check ordering.

The current construction schedule contains **108 cases, 27 obligations and three separate runtime immutability witness families**. These are construction counts, not scored successes. The case set remains amendable until the freeze. Core fixtures are written from scratch by `experiments/equal_policy/cases.py`, with no imports of either validator or existing test fixture producers. Seventeen corpus-construction tests passed in `case-tests-02.log` (11 core, 6 schema2); these tests validate identity, independence of copied objects, provenance bytes, explicit mutations and operation boundaries, not policy performance.

The separate runtime witnesses attempt nested mutation through a store query, a ledger claim and finalized coverage/trace/configuration. Their expected invariant is unchanged admitted/committed/finalized state. Additional runtime controls exercise output collision and interrupted-journal inspection without redispatch. [Ten controls and three launcher tests passed](RUNTIME-WITNESSES.md) on the installed candidate. Static validators do not implement mutable execution APIs, so these witnesses are reported separately from paired acceptance denominators. They cannot be counted as additional comparator errors.

## Envelope, observables and preparation recipes

Descriptors contain exactly `schema_version`, `control_id`, `operation`, `variant`, `paths`, `options` and `anchors`. Operations are `prepare_run`, `verify_run` and `inspect_run`; variants are `core_v2_catalog1` and `artifact_policy_v2`. Paths reference original-format case, snapshot, catalog, scorer, replay, local-model configuration, schema2 policy, root map, run directory or trusted-runtime manifest as needed. Unused optional paths are omitted. The trusted-runtime manifest is release evidence, not an expected-answer file.

Oracles contain the decision and a declared observable projection. For preparation this projection uses `admitted_observation_ids`, `eligible_observation_ids`, `scorer_preflight` and optionally `exclusion_reasons`. `exclusion_reasons` projects the `reason` strings from the native ordered `exclusions` list; it does not replace or change either implementation's full exclusions. Execution/verification projections additionally use prediction status/reason/null probability, selected observation IDs, exact feature values/status/group counts, accounting basis and recovery state as appropriate. No implementation-specific exception wording is an answer key.

`write_source_bundle(bundle_dir, spec, trusted_runtime=...)` creates a fresh directory and returns `(descriptor, pending_recipe)`. Empty pending recipes mean the original input bytes are ready for preflight. Nonempty recipes must be fully materialized and frozen before any scoring. The root-owned `prepare_sealed_case(bundle_dir, spec, descriptor)` callback consumes the already written mutated inputs; it must not replace them with a generic base or choose expected outcomes from execution.

The native producer recipes are `valid_scored` (ordinary offline execution, which may intentionally abstain under changed inputs), `unknown_selection`, `duplicate_selection`, `known_overquote`, `malformed_usage`, `unknown_timeout`, `valid_recorded`, `unresolved_dispatch`, `local_valid`, `local_malformed_response`, `local_known_overquote` and `valid_outer_schema1`. Local adapter cases use the native bounded adapter with an injected in-memory opener. They perform no network request or model inference; their declared fictional weight/runtime strings are schema/provenance controls, not claims that those files exist or that physical weights ran.

Each post-production mutation is named explicitly in the schedule. A `*_reseal` mutation intentionally repairs the relevant byte-level container hashes while preserving the stated semantic contradiction, so semantic checks are exercised rather than only a stale-file checksum. The callback records exactly which containers/anchors it changed. Byte-integrity cases intentionally preserve the stale pin. No callback may repair the actual fault, silently omit its case or relabel it as an expected validator failure when preparation itself fails.

Schema2 recipes cover valid policy, used/unused receipt faults, valid UTC aliases/alternative bases, exact grants and frame, denied evaluator products, unsupported scorer combination, copied-control/projection/dossier faults and a valid outer run. The shared schedule lists every recipe, whether currently implemented or still pending.

## Freezing and execution sequence

1. Agree on descriptor/result fields and supported variants, including recovery inspection.
2. Implement deterministic fictional inputs and explicit mutation recipes. Validate the corpus structurally without obtaining its expected decisions from either implementation.
3. Materialize native verification bundles when a case requires a sealed run, then apply the predeclared mutations. Retain the unmodified producer identity and exact mutation operations. Producing a bundle is preparation, not scored validation. Both implementations receive the same resulting bytes.
4. Review every oracle against its declared rule, resolve specification ambiguities, and freeze the complete schedule, input manifest, expected decisions, protocol, code/dependency pins and paired-run settings. Record a UTC freeze time and hashes before comparison.
5. Execute every scheduled case against each implementation and control under identical declared input/policy conditions. Retain exception, crash, timeout and unsupported dispositions; do not silently convert them to rejection or remove hard cases.
6. Diagnose discrepancies. Corrections require a versioned follow-up corpus/code freeze and a new complete comparison; retain the original attempt. Never edit old expected outcomes to match an implementation without an explicit normative error analysis.
7. Independently reconstruct denominators and results from frozen schedule and terminal records.

## Reporting

Report false admission and false rejection separately, plus valid abstention/failure/recovery agreement. Preserve per-obligation and exposure-stratum tables and all scheduled denominators. Report unsupported obligations as blockers to equal-policy completeness. Wall/CPU time, memory when actually measured, logical bytes, code size and maintained dependency surface need consistent measurement boundaries. Small synthetic timings are descriptive; no speed or statistical superiority claim follows merely from one faster run.

There are no live model calls, downloads or provider charges in this corpus stage. Previously closed scientific/model cells and retained releases remain untouched.
