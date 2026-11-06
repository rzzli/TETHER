# Semantic execution plan scope review

Reviewed 6 November 2026 against `planning/TETHER Semantic Capability Execution Plan 2026-11-06.md`, before the first diagnostic execution. This is an independent AI-assisted methods review within the project, not external scientific adjudication.

**Result: scope and measurement gates pass.** SC01–SC09 retain baseline diagnosis, a stronger full-context joint solver, evidence-use interventions, LitQA2 query expansion/reranking, bounded repair, ALCE, appropriate ScholarQABench evaluation, R2E, and final evidence reconciliation. None is silently dropped after an easy preparation stage. Later stages remain incomplete until their actual required measurements and independent checks exist.

The plan correctly separates completion of a negative measurement from demonstration of scientific improvement. It preserves all scheduled denominators and immutable old runs, treats a pretrained solver as a changed-supervision condition, keeps evaluation gold out of generation/selection, and requires no new human expert. Operational blockers retain incomplete status; they are not converted into weakened success criteria.

The execution protocol for each subsequent stage must make the following details concrete:

- Reference-derived rationale-only/removal masks are diagnostic inputs. They remain isolated from the primary solver's input and are labelled as reference-informed conditions; their scores do not become ordinary end-to-end retrieval performance. Context budgets and truncation policy remain comparable and explicit.
- The term "calibrated" in SC05 requires a declared independent calibration source or held-out split and fixed selection rule. The same 199 LitQA2 evaluation answers cannot both fit a threshold and establish its evaluation performance.
- Pinned full-context checkpoint metadata must resolve development-label exposure before a primary route is accepted. A pre-SciFact checkpoint may avoid direct SciFact train/dev finetuning while still having public-pretraining exposure; those are separate disclosures.
- Native benchmark adapters preserve task-specific metric assumptions and annotation support. A suitable ScholarQABench subset is selected before scoring; ALCE family and R2E candidate-universe coverage remain visible in the final denominator.

One nonblocking historical-reference correction was sent to root: the reviewed draft calls the previous study BG01–BG06, whereas `planning/TETHER Benchmark Goal Completion Audit 2026-11-06.md` records five BG01–BG05 stages. The intended historical range should be checked before freeze. This does not alter the SC01–SC09 scope.

No actual baseline decomposition or model execution was conducted for this plan review.
