# TETHER active documentation and catalog rename

Completed the authorized active branding change to **TETHER — Target Evidence Tracking Harness for Evaluation and Reproducibility**. Canonical usage names `tether-target-agents` 0.4.0 in `packages/tether`; the frozen AsOf 0.3.11 engine remains the compatibility implementation.

Validation: **221/221 scoped checks pass**, with 119 local Markdown links resolving. Both catalog versions pass the unchanged core catalog validator; all 178 dataset IDs remain indexed and all 83 providers remain present. Historical module CLI examples and the five excluded docs are unchanged. `git diff --check` passes. Namespace/CLI agents separately qualify executable aliases; this task performed no package install, CLI execution, broad test run or original-source replay.

Changed existing files (24):

- `data/catalog/sources.json`
- `docs/AUTHORITY_FOUR_ARM_COMPARISON.md`
- `docs/BOUNDED_INTERPRETATION.md`
- `docs/BOUNDED_RETRIEVAL.md`
- `docs/DETERMINISTIC_BASELINES.md`
- `docs/FIXED_EVIDENCE_COMPARISON.md`
- `docs/FRAMEWORK.md`
- `docs/INTERPRETATION_GENERATION.md`
- `docs/INTERPRETATION_INTERFACE.md`
- `docs/MAINTENANCE.md`
- `docs/NATIVE_INTERPRETATION.md`
- `docs/QUESTION_INTERPRETATION.md`
- `docs/QUESTION_LOCAL.md`
- `docs/QUESTION_PILOT.md`
- `docs/QUESTION_RUNTIME.md`
- `docs/SOURCE_AND_TOKEN_PREPARATION.md`
- `docs/SOURCE_FACT_EVALUATION.md`
- `docs/STUDY_RUNTIME.md`
- `docs/T6_CLAIM_AUDIT.md`
- `docs/T6_DOSSIER_BINDING.md`
- `docs/V02_MIGRATION.md`
- `README.md`
- `data/README.md`
- `data/DATA_PLAN.md`

New public files:

- `data/catalog/README.md`: current/display identity, immutable historical catalog and fingerprint boundaries.
- `data/catalog/history/sources-pre-tether-20261101.json`: byte-exact old master catalog.

The master catalog diff is exactly `$.title` and `$.providers[81].name`. All other fields, ordering, IDs, roles, status/date facts and bytes are preserved apart from those two string substitutions.

Original: `3c3108e6318e791985892fecea6ca9ea6185af7810a5ffd4a6311be3ca6f6109` (1229616 bytes).

Current: `eafd955cad30dd36bd7417de165a508b1e891f90f42e2cc4bcb573043eaa65ac` (1229620 bytes).

Compatibility/history exemptions:

- `docs/Expert Review Coordinator Guide 2026-10-26.md`: expert instrument/coordinator archive.
- `docs/Independent Project Review 2026-10-26.md`: dated original review.
- `docs/Opus_20261026T050236Z_review.md`: dated original model review.
- `docs/T6_PRIMARY_REFERENCE.md`: dated primary-proof checkpoint.
- `docs/T6_CONTEXTUAL_AUDIT.md`: research-pinned legacy contextual contract.

- `docs/history`, prior proof/review evidence, paper/release assets, receipts/READY/sealed artifacts, source code and protected/human files were not edited by this task.
- Accepted AsOf version statements, fixed historical arm names, `python -m asof...` examples, `src/asof` paths and legacy schema/method/dataset IDs remain literal.
- `asofDate` and `asof_release_date` are temporal/contract keys; `asof_normalized_packets` is a stable dataset ID. None were renamed.
- Old tools with the live catalog path and old hash intentionally reject the cosmetically renamed catalog. The archived catalog and sealed P09 source-policy remain original; no frozen tool was retargeted or silently rehashed.

Current data summaries now record P09/P10b local completion and deferred owner facts instead of treating P03/P04 as current. Dated acquisition/development chronology retains its earlier scope. No new collection/validation, hosted, publication, scientific-independence or clinical claim follows.

Retained evidence: `rebrand_active_docs_v1.py`, `ACTIVE-DOCS-BRANDING-CHANGES-v1.json`, `validate_active_docs_v1.py`, `ACTIVE-DOCS-BRANDING-VALIDATION-v1.json`. A reviewer-only initial Windows default-encoding failure is retained separately; explicit UTF-8 reads corrected the validator without changing the documents.
