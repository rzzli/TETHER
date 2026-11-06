# Independent SciFact result reconstruction

This is a separate analysis implementation. `reconstruct.py` imports only Python standard-library modules. It does not import the producer, runner, data projector, native evaluator wrapper, TETHER policy or their aggregation helpers. Its only scoring dependency is the unchanged upstream evaluator at commit `66feffc5b2cc9e28e3ce3b8c9e824c3c642981eb`, checked against its pinned SHA-256 before execution as a separate CLI process.

The preparation qualification uses invented claims and small artifacts only. It does **not** establish that the future production stage passes. The complete-stage integration will be checked after immutable actual candidates and the stage receipt exist.

## Execute after the stage finishes

Supply the receipt hash recorded outside the stage. Use a fresh output directory outside the input stage:

```powershell
& data/cache/tether-052-dev/Scripts/python.exe `
  planning/review-assets/tether-scifact-20261105/reconstruction/reconstruct.py `
  --stage <completed-stage-directory> `
  --expected-receipt-sha256 <externally-recorded-stage-receipt-sha256> `
  --output <new-ignored-evaluator-output-directory>
```

The CLI requires exactly 300 scheduled development claims. It refuses missing final receipts, failed/incomplete stages, extra/missing files, duplicate schedule IDs and mismatched frozen inputs. It checks completed native candidate sessions before opening reference answers. This is a terminal analysis helper; it does not restart workers or retry failed runs.

The output directory contains reference-bearing copies for the official CLI under `official/`. Treat the entire reconstruction output as **evaluator-only**. These files must not be passed to later prediction workers.

## What it rebuilds

- Complete producer, auxiliary and checker attempt inventories, journal chains, terminal cells, configuration, model assets, runtime/package proofs and original transport/normalized receipt links.
- Exact producer-to-checker candidate arrays, request fingerprints, source bindings and original per-call resource measurements; checking does not become another prediction.
- Nine tuning configurations, all 12 official precision/recall/F1 fields and the predeclared tie-break; the selected configuration must match the development freeze.
- Both raw and checked native projections and every primary field in `evaluation.json`: counts, status counts, per-case results, all-scheduled rates and official metrics. A failure-as-empty projection cannot become a successful native NEI or useful completion.
- Original corpus/query/reference projections directly from the pinned release archive. Every retrieved document fingerprint and returned sentence hash is checked against original fields. A semantically incorrect but source-valid label remains policy-valid.
- Source/exact-text components by an independent graph traversal. Per-case component IDs and descriptive SUPPORT/CONTRADICT/NEI/mixed strata retain scheduled, produced, accepted, strict-correct and strict-correct-and-admitted counts. No inferential confidence intervals are claimed.
- Retrieval coverage independently of classification: retrieved annotated claim/document pairs divided by all annotated pairs, and complete-gold-set retrieval divided by nonempty-gold claims. Per-case NEI recall and complete-set status remain null. This measures coverage of supplied annotations, not all scientifically relevant literature.
- Resource panels separate fitting, tuning setup/inference/scoring, development setup/inference/checking/scoring, checker setup/verification and controller accounting.

Resource input/output bytes are logical declared product sizes, **not physical disk I/O**. Checker setup input bytes count the candidate-array product; source/context reconstruction reads additional files. Peak memory values are process-lifetime maxima, not additive per-cell allocations. Unknown measurements remain counted as unknown. Controller durations are retained measurements: independent aggregation cannot remeasure past execution.

`paired-candidates.json`, `rebuilt-evaluation.json`, `source-class-strata.json` and `retrieval-coverage.json` preserve the detailed joins. `RECONSTRUCTION.json` records the result; `RECEIPT.json` binds all reconstruction outputs. A failure writes `FAILED.json` and leaves the output directory intact. Input cases, outcomes and denominators are never corrected or excluded to obtain a passing reconstruction.

## Qualification

`test_reconstruct.py` uses invented examples to check native rationale caps and alternatives, opposite labels, missing/empty predictions, duplicate/omitted schedules, successful NEI versus operational failure, exact original sentence coverage, resource unknowns, receipt tampering, rehashed accounting and budget contradictions, source component joins, selection tie-breaks and the unmodified official CLI.

`qualify.py` reserves a fresh qualification directory, snapshots this helper and its tests before running them, retains the complete subprocess log, and checks that the source hashes did not change. The qualification scope is these fictional helper tests. Production reconstruction remains a separate required gate.
