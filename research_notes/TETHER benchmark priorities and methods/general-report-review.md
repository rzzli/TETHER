# General methods and scorer review

**PASS, bounded to the assigned general-method/source scope.** Reviewed report: `reports/TETHER benchmark priorities and methods.md`, SHA-256 `90dc3f83d6f79e556fad4f5e18db64d2268764b587fb032890914db2c99c43c3`.

Verified against primary sources retained in [general.md](general.md): SciFact's four native metric families, `max(3, shortest_gold_rationale_length)` cap, complete-rationale sentence scoring, native empty-evidence versus operational abstention, MultiVerS's explicit CUDA path, Inspect same-policy and scorer-denominator caveats, ALCE's task/evaluator scope, ERASER evidence interventions, selective prediction and conditional conformal-risk claims. No blocking correction identified. The biomedical comparison claims were reviewed by the separately assigned specialist, not re-audited here.

The report correctly incorporates the completed corrected BG02 result and does not call SciFact acquisition a trained or scored benchmark. Direct code-ZIP inspection additionally confirmed pinned SciFact/evaluator license members; `COMPLETE.json` still records its earlier formal license-review status as pending, so the report's status wording remains explicitly attached to that receipt. No source archive, dataset, runtime, frozen result or expert return was changed or newly evaluated in this review.

Exact pinned evaluator commit: `66feffc5b2cc9e28e3ce3b8c9e824c3c642981eb`; member `evaluator/eval.py` SHA-256 `2554fed44c3f5592bdeed59ab0d3918a412b452ba1c77da73ba0f62e74c9987f`; rationale cap is at lines 157–161. These member bytes were read from the already acquired source ZIP, without extracting dataset labels.
