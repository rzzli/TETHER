# Independent pre-freeze Inspect extension review

Scope: `records.py`, `accounting.py`, `archive.py`, `task.py`, `runtime.py`, and `evidence.py` in `experiments/inspect_policy`, read while the implementation was under development. No frozen 109-case comparison, provider call, model inference or scientific data scoring was executed. This is a bounded implementation review, not proof that all defects have been found.

The independent [fictional probes](review_probes.py) ran against the new implementation using the qualified Inspect interpreter without starting an asyncio event loop. Their first retained [output](REVIEW-PROBES-01.log) reproduced four defects. It is intentionally retained even after fixes; closure requires fresh evidence.

| Finding | Reproduction and consequence | Required correction |
|---|---|---|
| R1: scorer identity join | A valid record and matching output for fictional case B, substituted into case A's mutable metadata, received native score `C`. The expected decision happened to match; no request/result/control-ID join rejected the substitution. | Bind the reopened record, request, result, nested decision and sample identity before scoring. Apply the equivalent join to runtime scoring and final reconstruction. |
| R2: incomplete provider configuration binding | A reserved request dispatched once with temperature `0.9` while the declared configuration was `0.0`. Only retry, cache and output-token settings were compared. | Freeze and compare the exact effective request/payload/configuration before dispatch; reject unexpected settings rather than merely recording them afterward. |
| R3: output inside input | `execute_archive_case` accepted an output directory inside its input bundle, wrote four case files there and returned `completed/accept`. | Reject output/input overlap before creating any case record, including the full task's protected bundle roots, not just the current case. Preserve existing inputs and no-clobber behavior. |
| R4: cross-step duplicate claims | Committing `obs-1` twice to the same live ledger appended the same canonical claim ID twice. A per-request uniqueness test did not enforce run-level claim uniqueness. | Maintain immutable ledger identity/order across steps and reject or otherwise explicitly prevent duplicate commits before appending. Keep the reviewed-prefix deadline behavior. |

These findings concern new BG05 code before its comparison freeze. They do not imply that an earlier benchmark result changed. The implementation owner owns regression tests and fixes; this reviewer did not edit production modules.

## Correct behavior and remaining qualification boundaries

The reused admission path calls native case/program/lineage/publication checks and scorer preflight before provider reservation. Admitted records, fingerprints, copied telemetry views, requests and returned claims are recursively frozen. Action/modality/tissue feature applicability is correctly separated from eligibility of raw contextual observations. The accounting object reserves durably before dispatch, retains unresolved quotes and stops further work after error or validated overquote. These are code-review observations; the retained runtime witnesses must still establish execution behavior.

Oracle values are absent from `Sample.target`, solver inputs and model requests. The scorer loads a separately pinned oracle only after a retained result. This is a trusted-code information-flow convention in one process, not an adversarial filesystem boundary.

`inspect_record` explicitly verifies bytes and hash-chain structure. It is not itself source-inclusive runtime semantic verification: final reconstruction must independently reconcile reservations, accountings, claims, native output/usage, callback identity and terminal state. A native evaluation completing or receiving `C` must not automatically fill those coverage rows. Required hook events can fail or be disabled; the final reconciler must detect that when assessing IX07.

An explicit zero review-retry configuration is faithful for that bounded runtime witness. It does not establish positive retry behavior. Until a positive retry witness exists, that clause remains archival-only; backend failure must never trigger automatic retry. Full eight-specialist category inventory and autonomous therapeutic scheduling remain outside the small native runtime port.

## Prospective protocol review

The 109-case, three-arm, three-repetition order-rotated design is appropriate for descriptive archive conformance and batch costs. The final protocol elects no cold subset; the earlier design's optional nine-case diagnostic therefore must not appear as an executed condition. Keep native verdict-conditioned metrics distinct from the all-scheduled denominator and count unsupported/error/missing results without awarding correct rejection.

One normative accounting distinction requires an explicit decision before freeze. The unchanged `EP-EXEC-02` contract assigns quoted conservative usage to invalid or unqualified local responses; fully qualified responses, including valid overquote, receive measured accounting. The protocol draft instead says valid usage must be retained when content is malformed. Retaining native reported usage separately as telemetry is consistent with the original contract. Replacing its conservative policy accounting with that usage would be a prospective runtime-policy difference and must be labeled accordingly rather than called unchanged-policy parity.

Completion of this review's findings requires fresh probe output plus owner regressions. A later closure note must distinguish fixed defects, tested runtime guarantees and explicit untested clauses.
