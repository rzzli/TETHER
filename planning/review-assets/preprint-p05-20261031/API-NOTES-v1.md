# P05 feasibility design and API notes

Status: **DESIGN_NOT_LOCKED**. These are prospective repository requirements, not an implemented API, source-ready cohort, scan approval or execution protocol. The companion [FEASIBILITY-DESIGN-v1.json](FEASIBILITY-DESIGN-v1.json) contains the detailed gates, schemas and unknowns.

No `src` file changes belong in this step: the current P04 protocol pins the complete source inventory. Keep its endpoint, code pins, original inputs and unsuccessful attempts unchanged. Wait for its retained terminal closeout before reconciling catalog/acquisition metadata or implementing a new builder.

## Current boundary

P04 has two exposed development contexts and one synthetic withholding condition, not three independent cases. Its builder deliberately requests ID/date/cellType fields. The generic reference compiler already supports finite native measurements and exact-key same-release joins, but that does not make the fixed P04 input builder generic.

The sanitized completed credible-set report supplies one developmental exact match with beta, SE and p-value components. Sample size is null; units, ancestry and verified upstream study identity are unavailable. It is not a fresh cohort or causal/MR qualification. Its evaluator-only selected-row packet must not become an agent input. New generation packets must derive directly from separately admitted originals under a clean neutral plan.

## Proposed interface boundaries

The following names are requirements only:

```text
reconcile_source_inventory_metadata(catalog, receipt_index_metadata,
    approved_roots, source_families) -> reconciliation_report

plan_source_fact_feasibility(source_spec, reconciliation_report,
    exposure_register, explicit_limits) -> bounded_inventory_plan

scan_source_fact_feasibility(approved_scan_plan, original_inventory,
    catalog_and_deny_policy, approved_roots, deadline_and_caps)
    -> candidate_exclusion_register, exposure_dependence_register,
       sanitized_availability, scan_accounting, resources

prepare_source_fact_generation_inputs_v2(neutral_task_plan,
    admitted_original_inventory, catalog_and_deny_policy, approved_roots,
    independent_expected_hashes, deadline_and_caps)
    -> source_only_packets, value_free_binding_slots, proofs, blocked_tasks

prepare_source_fact_references_v2(same_neutral_task_plan,
    independently_admitted_original_inventory, catalog_and_deny_policy,
    approved_roots, independent_hash_anchors, deadline_and_caps)
    -> evaluator_only_verified_references, derivation_checks, seals
```

The reference path independently reconstructs original locators, joins and literal facts; it does not derive answers from generation packets or emitted outputs. It can reuse `compile_reference`/`verify_reference` after independently checking selection and derivation. Generation accepts no references, scores, human-response descendants or evaluator-only P02 packets. Trusted roots remain explicit caller arguments.

Selectors are finite declarative operations: exact native keys, explicit joins, stable ordering and physical-locator tie breaks. No arbitrary expressions, fuzzy locus mapping, first-success selection or performance-driven replacement. Enumerate the entire declared inventory before claiming completeness or applying a prespecified selection cap. Record every zero, duplicate, conflict, unresolved join and terminal scan failure.

## Measurement contract

The proposed measurement endpoint is separately versioned and **not locked**. It requests original effect, uncertainty and significance groups under exact source composition; IDs/dates support provenance. Group p-value mantissa/exponent or interval bounds together. Use the current group-weighted mechanical coverage and failure semantics, with a later frozen measurement-only primary rule and 60/80/100% sensitivities. Unknown-only measurement groups yield no denominator; zero answerable groups leave measurement coverage/completion null.

Reuse the existing wire reasons exactly: `field_not_in_schema`, `null_source_value`, `empty_source_value`, `unavailable_join`, `conflicting_join`, `failed_qc`. Keep collection and join dispositions distinct. A null unit does not gain a new unit-specific reason field in `typed_facts_v1`; record absent/unrequested/null/unverified unit context separately with `value: null` and a reason. A new wire behavior would require its own version, implementation and tests.

Finite native numeric types remain literal; Booleans are not measurements and `pValueExponent` is an integer. Do not coerce values, compute missing intervals, reconstruct p-values, borrow ancestry/sample size or infer gene/drug direction. Exact projection is the ceiling comparator; success measures source reporting and composition.

## Registers and decision gate

The JSON specifies candidate/exclusion, exposure-event, dependence-node/edge and scan-terminal schemas. Keep rights, date, ancestry admission, publication, exposure, study identity and source role as separate gates with evidence and explicit unknown reasons. Native `studyId` alone does not verify an independent upstream study.

Group shared records, studies/cohorts, articles, declared loci/regions and source-defined target families conservatively before development/evaluation allocation. Shared release/shard alone is not biological dependence. Unknown relationships cannot become proven independence. Used development material and controls remain exposed; sealed reference-only preparation requires enforced generation isolation. Project freshness says nothing conclusive about model-training exposure.

No actual source pins, candidate IDs, eligible counts or schedules are frozen here. After P04 terminal closeout, reconcile metadata, implement/verify the generic contract, and prospectively bound a full-inventory source-only feasibility scan. Actual counts and dependence groups then determine the scope and precision claim before a separate lock.

The 12-group / 60-cell / at-most-39-call example is illustrative. It assumes four arms, 12 clean groups and three synthetic withheld conditions; it excludes additional fault/ablation cells and proves neither candidate availability nor runtime fit. Use the one existing model, no downloads and $0 provider spending. If fresh coverage or precision is inadequate, declare exploratory source-reporting or technical feasibility scope before generation.

## Checks for these assets

Strict JSON parsing, design-state/unknown-boundary checks and illustrative arithmetic are sufficient for this documentation step. Compute file hashes and sizes. Do not claim application tests, data replay, a new scan, model inference, source qualification or P05 locking.
