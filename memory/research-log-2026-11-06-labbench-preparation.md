---
name: research-log-2026-11-06-labbench-preparation
description: Current BG04 LitQA2 preparation and additional scientific-method comparison after SciFact closure
metadata:
  type: project
---

# LitQA2 preparation and peer methods

BG01–BG03 are complete in their scoped engineering/public-development evaluations.
SciFact closure commit is `5dae314`; 300 predictions produced/admitted,27 strict-
correct, identical raw/checked scores. Its weak result remains frozen. See
[[research-log-2026-11-06-scifact-results]]. BG04 remains incomplete.

The original199 public LitQA2 items were selected before candidate performance.
HF revision `5c77cec648430f30611808808861eb86f81d5eaa`, original code commit
`998a8e0a40cf116c80e1b0e7a805ebb5fb9fa838`. Acquisition receipt SHA256
`620cf7d9d166d892b8c33da9a3f6a896d0c8d3659bbc10b4b6144fcadcd723bd` binds17files/
719,061bytes. General-question Europe PMC metadata/full-text probe succeeded;
benchmark source coverage remains unknown. Reference answers/key passages/source
hints are excluded from answering. All options including unsure are shuffled.
Exact historical MSigDB files have a public archive, so DbQA is not universally
account-blocked; it still needs product/version-specific qualification.

[[TETHER LitQA2 Evaluation Protocol 2026-11-06]] is an implementation draft with
family/cohort fixed before performance. Final code/configuration/budgets require
fictional qualification before benchmark retrieval or generation. New modules
cover projection/retrieval, MCQ contract/scoring/policy and a task-specific local
Qwen transport. Existing weights/runtime will be freshly qualified; no historical
T6 launcher/cell is reopened. As of this checkpoint no benchmark answer has been
generated or scored and no model has been started for BG04.

[[TETHER benchmark comparison update 2026-11-06]] adds PaperQA2, OpenScholar and
Self-RAG to the prior peer review. Useful transfers are source-grounded contextual
reranking, bounded semantic repair, and conditional retrieval; these are not proved
by current structural review. ScholarQABench is a later synthesis benchmark.
MultiVerS-style joint labels/rationales, ERASER evidence interventions and matched
risk/coverage remain targeted additions. Retain raw passages when testing generated
summaries; weak summarizers can damage answers. Do not turn model self-critique,
valid citations or exact gold-passage matches into semantic truth.

The current execution order remains BG04 LitQA2, BG05 equivalent-policy Inspect,
BG06 final audit. New peer interventions are follow-on proposals, not silent
requirements or claimed implemented improvements. No paid calls, external human
reviews or deferred author facts are requested.
