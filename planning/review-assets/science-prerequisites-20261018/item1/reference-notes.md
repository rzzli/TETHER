# T6 reference qualification contract — October 18, 2026

This is an evaluator-only contract for an **agent-reviewed scientific development reference**. It permits source-grounded review now, without waiting for human availability. It does not turn agent agreement into independently validated biological truth, human expert review, a clinical endpoint, or clinical performance. No cases or outputs are selected by this document.

## Existing material and applicability

The retained AI-assisted review covers ten exposed development hypotheses and twenty purposive excerpts. Its provenance explicitly says unblinded, unadjudicated, not representative and not a full-dossier assessment. Its review forms reference `v02-realdata-20261012T015124Z`; current source packets and local-model challenge outputs are later products. The review is useful development feedback, not absent and not current gold by default.

Crosswalk every reused assessment to the exact current hypothesis fingerprint, source record fingerprint, statement bytes, source release, packet lineage and source locator. Classify reuse as `exact_match`, `same_source_changed_statement`, `same_statement_changed_context`, `source_version_changed`, `hypothesis_changed`, `unmatched`, or `not_rechecked`. Even an exact match retains the original unblinded provenance. A changed target namespace, disease namespace, action, modality or tissue requires a new hypothesis-scope assessment. A source article cited by the old review does not imply the current packet contains that article or its findings.

Primary local evidence read for this contract:

- `data/manifests/public/2026-10-15-ai-assisted-review.json` — dates, ten cases, twenty claims, role and limitations.
- `data/benchmark/gold_evidence/ai-assisted-review-20261013/reports/combined-assessments-20261015.json` — merged reviewer provenance and evaluator-only source research.
- `data/benchmark/gold_evidence/t6-development-review-20261012/manifest.json` and the CD276 review form — original run, hypothesis and source binding.
- `planning/review-assets/task6-resumption-20261018/review-inventory-correction.json` — fourteen review artifacts and ten blank original forms rehashed; not a scientific re-review.
- `planning/Task 6 Development Comparisons 2026-10-18.md` — current challenge, transport distinctions and absence of an independent quality endpoint.
- `src/asof/contracts.py` — existing hypothesis fingerprint includes target/disease IDs, namespace versions, action, modality and tissue.

No new original-source hash validation, external scientific literature review or scientific judgment was performed for this contract. Item 2 must retain its own evidence.

## Review units and dimensions

Keep three different objects separate: a source observation, a dossier's assertion about that observation, and a therapeutic inference. A record accurately saying a database links a target to a disease may have high literal fidelity and little support for the proposed intervention. Evaluate each dimension independently; do not average categorical labels into an invented clinical score.

1. **Source fidelity:** exact support, partial support, unsupported, contradicted, or unverifiable. Require the source row locator and, for article-level claims, the accessible original passage/table/figure. Abstract-only support cannot certify uninspected full-text findings.
2. **Identity and disease relevance:** exact target/variant/disease/population, related but extrapolated, mismatched, uncertain, or not applicable.
3. **Action relevance:** direct intervention evidence, mechanistically indirect, association only, opposing direction, uncertain, or not applicable. Variant consequences and trait associations alone do not establish pharmacological action direction.
4. **Modality relevance:** direct, indirect, absent, conflicting, uncertain, or not applicable. Expression does not by itself establish ADC internalization, payload sensitivity, delivery, or therapeutic window.
5. **Context:** retain reported species, ancestry, tissue, cell type, model, disease state, dose/time and comparator separately. Rate transferability to the proposed hypothesis as direct, limited, mismatched, uncertain, or not applicable. Cell type is not automatically tissue; unspecified hypothesis tissue is not permission to invent one.
6. **Uncertainty and missingness:** distinguish uncollected inputs, failed QC, inaccessible data, context unreported, ambiguous mapping, not measured and measured biological absence. Distinguish source contradiction from a mismatch in study populations, interventions or endpoints.
7. **Interpretation risk:** identify the exact unsupported extrapolation, its likely consequence and a correction. Use descriptive `none_identified`, `minor`, `material`, `critical`, or `uncertain`; these are rubric categories, not universal clinical safety thresholds. Critical means a plausible reversal or unsafe therapeutic implication in this case, with rationale, not an invented quantitative cutoff.
8. **Dossier coverage:** assess against pre-frozen reference questions and eligible source pool, including important caveats and refuting evidence. Unsupported new external facts may inform evaluator critique but cannot increase the agent's in-world evidence coverage. Coverage applies to the selected input world, not all biology.

Each judgment has a rationale, source pointers, review timestamp, uncertainty reason, reviewer identity/type and evidence-access depth. Use `null` plus a reason for unavailable quantities. Separate a claimed number's fidelity from its scientific interpretation. Provider evidence scores remain descriptive, not support weights, effects or probabilities.

## Blinded agent procedure

Freeze the reference questions, source world, hypothesis fingerprints, rubric version and exposure log before reviewing new arm outputs. Reference builders see source material and questions, not arm identities or output selections. In separate fresh contexts, two agent reviewers assess the same anonymized claims/dossiers, without seeing each other's assessments. Preserve their prompts, model/version if exposed, execution identifiers, source access and output hashes. Do not invent hidden platform model versions: use null with an explicit reason.

A separate adjudicating agent receives the disagreements and original source evidence after the first two reviews are sealed. It must record an evidence-based resolution or `unresolved`; a vote or polished narrative is not adjudication evidence. A separate integrity audit checks all source locators/bindings and a frozen sample of agreements for correlated mistakes. All material and critical disagreement must be resolved with evidence or retained as unresolved. Unresolved items remain in the report and are excluded only from metrics requiring determinate truth, with both denominators reported.

An anonymization custodian alone retains the arm-to-code map in evaluator-only storage. Randomize display order under a retained seed and standardize formatting without changing claim wording. Reviewers still see scientifically necessary target/action/modality/context and source provenance. Those can reveal an arm through stylistic or content clues; collect suspected-arm guesses and prior exposure rather than claiming perfect blinding. Reviewers who previously saw a case or built an arm must declare it. Existing case exposure cannot be undone by anonymous filenames.

Independent agent contexts establish **procedural separation** and reduce direct answer copying. Shared training, model family, prompts, source providers and prior conversation may cause correlated errors. Agent consensus is an explicitly agent-derived reference; report comparison results as agreement with that reference, not independently established scientific accuracy. Human review is a possible later external validation layer, not a prerequisite for this agent development reference. Medical efficacy, causal validity and clinical safety cannot be certified by agent consensus.

## Dependency and leakage controls

Record separate dependency groups for target/action families, disease/population, intervention, primary study/cohort and exact source rows. Repeat modalities for the same target are related cases. Open Targets plus the same original paper are two representations of one evidentiary lineage, not independent replication. Do not make every case one biological cluster merely because all use Open Targets; retain dataset dependency separately from primary-study dependency.

Reference answers, article research, arm map, adjudication and endpoint labels must be `evaluation_only` through transitive lineage. An arm receives only the frozen authorized evidence manifest. Bind every review to the exact output receipt and hypothesis/statement fingerprints; changing output bytes or source versions invalidates applicability until reviewed. The blind packet must not expose reference answers through file names, path labels, hidden metadata or source-ranking hints. Canary tests must cover both direct reads and inherited reference parents.

## Qualification gates and reporting

The operational gates below are pass/fail completeness and isolation checks; they are not universal thresholds for therapeutic correctness.

- **Registered:** versioned local protocol, dimensions, source eligibility, questions, sampling/exclusion rules, dependency units, metrics and exposure declarations exist before the reviewed comparison. Any post-output changes are separate exploratory amendments.
- **Bound:** every assessed item resolves to the frozen hypothesis, output, source fingerprint and original locator; missing proofs fail qualification rather than becoming unverifiable claims marked correct.
- **Separated:** answer-bearing material is evaluator-only; blind packet checks and canaries pass; any unsuccessful blind is disclosed and analyzed separately.
- **Reviewed:** two separately executed initial assessments exist per required unit, with evidenced adjudication or retained uncertainty. No raw initial assessment is overwritten.
- **Audited:** original-source fidelity, statement preservation, crosswalk statuses, dependency groups, counts and all required fields pass integrity checks. Review sampling coverage is reported, not extrapolated.
- **Reportable:** output clearly distinguishes source fidelity, hypothesis relevance, missingness, disagreement and unresolved counts; states agent-derived reference status and development exposure. It provides denominators for every statistic and uncertainty by independent case/study group where sample size permits.

A qualified agent development reference allows exploratory paired T6 comparisons. It does **not** activate locked clinical evaluation, qualify clinical labels, validate genetics, establish calibration, or justify a superiority claim. Small pilot confidence intervals and descriptive paired differences should show their imprecision; case/claim counts cannot replace independent target/study counts. Confirmatory thresholds and sample-size decisions require a separately frozen, scientifically justified analysis plan, not a convenient score cutoff.

The adjacent `reference-fields.json` is the field/interface contract. Its status is `specified_not_populated`; it deliberately contains no selected cases, assessments or new scientific answers.
