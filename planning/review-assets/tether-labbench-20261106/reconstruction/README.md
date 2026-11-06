# Independent native-score reconstruction

This helper is separate from the production scorer. It imports only Python's standard library and does not import `score_run`, `evaluate`, `native_contract`, or other project implementations. Actual answer-containing originals and reference products remain unopened during qualification. The parent must explicitly confirm that generation is sealed before dispatching the actual reconstruction.

The pinned original LAB-Bench commit is `998a8e0a40cf116c80e1b0e7a805ebb5fb9fa838`. Its `utils.randomize_choices` shuffles `[ideal, refusal, *distractors]`; the original `Evaluator.compute_metrics` reports correct/all scheduled, correct/non-refusal answers, and non-refusal answers/all scheduled. Zero-attempt precision is numerically zero in the original, with an additional undefined flag here. A literal `"null"` ideal remains its own answer option. The protocol's strict-JSON parsing failures are operational unanswerable, not arbitrary attempted strings; all remain in scheduled accuracy.

The helper independently reconstructs the seeded native permutation, checks query text/order, compares the prepared reference map if supplied, and recalculates all native metrics and paired admission counts. It verifies the externally anchored generation inventory, candidate/disposition joins, original native response content, offered source identifiers and retained admission decisions. It does **not** replace the separate generic session/runtime verification, full source-lineage replay, model asset verification or scientific entailment evaluation.

Nine focused fictional controls pass in [fictional-tests02.log](fictional-tests02.log). They include hand-computed mixed outcomes, original-metric parity, all-unsure undefined precision, literal-null/duplicate-option preservation, changed permutations, malformed and Boolean choices, duplicate JSON fields, source/response substitution, omitted cases and proof that an invalid generation seal fails before reference access. Two exact pinned public source functions are extracted with Python AST solely in tests; no benchmark row, answer key or evaluation package is imported or executed. This is function-level parity, not a claim of executing the entire original dependency-heavy evaluation application.

Observed grouping uses exact shared annotation strings and whitespace-normalized identical questions, with transitive closure. It does not resolve all DOI/PMID/PMCID aliases, estimate the effective sample size, or justify confidence intervals or power calculations under independent questions. Analytical always-unsure and uniform-position controls are explicitly labelled as expectations, not fabricated model runs.

Run only after the parent provides the sealed paths and external hashes:

```text
python -I -B reconstruct.py --generation-sealed-authorized 
  --generation-root <sealed generation> --generation-sha <SHA256 of SEALED.json>
  --original-path <pinned original JSONL> --original-sha <pinned SHA256>
  --references-path <prepared reference JSON> --references-sha <pinned SHA256>
  --evaluation-root <sealed primary evaluation> --evaluation-sha <SHA256 of SEALED.json>
  --output <fresh reconstruction directory>
```

Both the reference-map and primary-evaluation comparisons are optional API capabilities, but the intended actual acceptance run supplies both. The reconstruction opens originals only after generation sealing and candidate-byte joins. It emits aggregate results without per-question correct indices, creates a new output directory exclusively, and retains failures without rerunning any model or retrieval operation. A reconstructed partial generation remains descriptive partial evidence; a successful score reconstruction does not imply completed generation or semantic competence.
