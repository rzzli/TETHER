# Focused biomedical factual review

Reviewed 5 November 2026 against the primary-source checks retained in
[biomedical_benchmarks.md](<D:/Projects/drug_target_agents/research_notes/TETHER benchmark fit and advances/biomedical_benchmarks.md>).

Reviewed report: [TETHER benchmark fit and advances.md](<D:/Projects/drug_target_agents/reports/TETHER benchmark fit and advances.md>).
Initial reviewed SHA-256: `7ddb2b10259dba126d4874538cd574e8dd1e8310c4b60f51658a5af0a70a164a`.
Scope: biomedical benchmark tasks, available releases, scoring/access limitations,
peer-method interpretation and actual versus planned TETHER results. General
agent benchmark facts are assigned to the other source review. No runtime edit,
download, model call or new broad research occurred.

| Check | Finding |
|---|---|
| Actual versus planned | Correctly leaves BG02 unscored and native SciFact/LAB/Inspect unfinished; does not turn parser, gold replay or unit tests into answering performance. |
| SciFact | Task/rationale scoring and separate claim/abstract/code licenses match official documentation. Test submission availability remains explicitly untested. |
| Original LAB-Bench | Public LitQA2 199/DbQA 520 and CC-BY-SA-4.0 match the checked card. Privileged key passages remain evaluator-only outside a labeled oracle arm. |
| LABBench2 | Clearly separate from original LAB-Bench. Gated access, revised SourceQuality set, later answer correction and harness/published-result mismatch are retained; it is optional rather than a new gate. |
| R2E and Virtual Biotech | Correctly distinguishes gene ranking and broad scientific-system workflows from TETHER's current source-reporting endpoint. Makes no clinical-superiority or full-reproduction claim. |
| TRQA | Correctly identifies model-assisted MCQ scoring, weak question joins and potential skipped rows as evaluator qualification concerns. Does not advertise an unqualified deterministic scorer as native replication. |
| GenomeArena, BixBench, BiomniBench, TxBench | Retains unresolved redistribution/source requirements, version-dependent computational tasks, gated public 50/100 split, and seven-example release limitation respectively. |
| Identity/Evidence interpretation | Correctly limits blinding effects to dependence under the intervention; acknowledges essential lookup keys/context and inconclusive controls. One scope-precision correction requested below. |
| Existing local methods | Describes source-only isolation, masks and neutral labels as existing/partial. The missing claim is a qualified joint native intervention, not total absence of safeguards. |
| Human-expert requirement | Introduces no new human recruitment or return-processing prerequisite. Existing public benchmark references remain optional isolated evaluator assets. |

One low-severity factual precision correction was sent directly to the writer:
the phrase “Its one-model/one-mask results” can sound as though all experiments
in Identity/Evidence use only one model. The full text repeats selected contrasts
with a smaller model. Requested wording narrows the statement to the **primary
LitQA2 redaction analysis**, which uses one model and one fixed mask, while
retaining that these results do not establish a universal effect or prove
memorization. [Primary preprint, sections 3 and 4.4](https://arxiv.org/html/2610.36510v1).

No other biomedical factual correction was identified in this bounded review.
This is a source-consistency review, not independent reproduction of peer results.

Correction confirmed in the report after the writer's update. Final checked
SHA-256: `8c9b5235166b833b8793aa9af5b760800f2a6bd6283e311094bcbbf7dce4daa3`.
Disposition: **PASS for this focused biomedical source-consistency scope; no
unresolved factual finding.**
