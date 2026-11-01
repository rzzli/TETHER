# P03 source-fact evaluator evidence

The separate source-reporting evaluator is implemented and tested. It is not a
scientific-truth reference, qualified model comparison or completed preprint.

- [Current contract](../../../docs/SOURCE_FACT_EVALUATION.md),
  [retained initial contract](TASK-CONTRACT-v1.md),
  [initial checkpoint](CONTRACT-FREEZE-v1.json) and
  [pre-generation clarifications](CONTRACT-CLARIFICATIONS-v1.json).
- [Targeted validation](TARGETED-TESTS-v1.json) and [full log](TARGETED-TESTS-v1.txt):
  173 methods pass, zero skips; 99 new/74 relevant legacy, not a full-suite rerun.
- [Installed smoke](INSTALLED-SMOKE-v1.json), [smoke code](installed_smoke.py) and
  [offline build log](WHEEL-BUILD-v2.txt): fresh dependency-free installed JSON
  API outside the checkout. This wheel is an exact-hash development artifact,
  not a final research release or replacement for old 0.3.11 archives.
- [Selected actual-source replay](ACTUAL-SOURCE-REPLAY-v1.json) and
  [replay code](replay_actual_source.py): one receipt-bound original Parquet row,
  15 literal fields; 0/4 measurements answerable, measurement coverage/pass null.
- [Initial missing-module test](INITIAL-EVALUATOR-TESTS-v1.txt),
  [TEMP failure](TEMP-ENVIRONMENT-FAILURE-v1.json),
  [fixture-group failure](EVALUATOR-TESTS-v1.txt),
  [corrected evaluator run](EVALUATOR-TESTS-v2.txt) and
  [initial build-cache failure](BUILD-ENVIRONMENT-FAILURE-v1.json) are preserved.

Independent controls exposed compiler/wire representability failures before
correction. Literal source/type/group checks, raw-byte scoring and all-cell
accounting are mechanical guarantees. Source timing, scientific validity, full
collection completeness and model usefulness require their own evidence.

Original source and transport receipts remain unchanged; one 841-byte
content-addressed receipt was archived under the separately authorized E: root.
No download worker/monitor/model was launched. Answer-bearing references remain
ignored and evaluator-only. See the [full progress review and P04 prerequisites](
../../Project%20Progress%20Reassessment%202026-10-31%20-%20Source%20Fact%20Evaluator.md).
