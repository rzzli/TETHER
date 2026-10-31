# R07 interface and methods triage — AI-assisted development review

Date: 2026-10-26. Status: retained engineering interpretation, **not independent expert review, scientific validation, or gold labels**.

**Stop expansion to 20 cases. Proceed only with bounded offline interface clarification and regression fixtures before considering a separately frozen repeat.** The six completed responses all failed their output contracts, but their failures do not establish that every statement was wrong or that model capacity caused the failures.

## What was checked

The reviewed run is `runs/r07-native-diagnostic-20261026T165505Z`, terminal-seal SHA256 `863bf2a9cfb8d4fd01a5223b993d87fbe2ac06992e7206d3d32ef4c712cf2d41`. Trusted source-inclusive verification passed again during this review: six dispatch reservations, six retained failed cells, scientific acceptance not established, human review pending. The parent report records owned-server termination and 59.391 seconds elapsed. All six transport wrappers record HTTP 200, complete bodies, and EOS termination. Thus these observed failures arose after transport completion, rather than from a missing response or exhausted output limit.

This review read the sealed requests, payloads, original native response bodies, failure records and journals. It compared assertions only with the offered facts and declared protocol. It did not search for additional biology, read evaluator answers, repair responses, change validators, rerun a model, or modify the sealed run. Exact file proofs, original-body hashes, token counts and quote choices are retained in `interface-findings.json` beside this report.

## Paired results

The error column is the first rejection reproduced by the unchanged validator. Other defects below are observations about the original JSON, not results from repairing and resubmitting it.

| Case / interface | First contract rejection | Additional interface observations | Content compared with offered facts |
|---|---|---|---|
| IL6R / current | `Claims contradict answer state` | `partial` has null `abstention_reason`. Original quote pointers resolve. | Reports the negative exposure/outcome association, but cites a prior-study discussion passage and a results heading. Says replication and estimates/uncertainty are not provided despite offered passages containing both. |
| IL6R / simplified | `Invalid paired quote bounds` | One source ID is paired with five object-valued offsets; the contract requires one or two paired string pointers. A `source_report` is a synthesized paragraph rather than an exact offered quote. | Combines a negative association and variant information present in the excerpts, but merges cited prior work with the present study and omits the offered replication qualification and numerical uncertainty. |
| Synthetic orientation / current | `Claims contradict answer state` | `partial` has null `abstention_reason`. Uses a valid `/statement` pointer. | Preserves exposure/outcome orientation and both discovery and replication estimates/intervals. Limitations retain the missing units and intervention evidence. The proposition predicate is awkward; some unprovided contextual fields are the string `unspecified` rather than null. |
| Synthetic orientation / simplified | `Invalid simplified fields` | Uses `reason` instead of `abstention_reason`. Its quote pointer is an object with a transformed-view path, not an allowed original string pointer. | The claim text exactly matches the complete offered synthetic statement, including missing units and intervention effects. |
| Synthetic context / current | `Claims contradict answer state` | `partial` has null `abstention_reason`; both `/statement` pointers resolve. | Both claim texts exactly match offered statements. Mouse/liver/cell, comparator, timing and unmeasured outcomes remain visible; the unrelated human skin-cell study is kept separate. Calling the case a `context_mismatch` is stronger than warranted because the synthetic hypothesis has unspecified tissue/modality. |
| Synthetic context / simplified | `Invalid simplified fields` | Uses `reason`, omits claim `limitations`, and emits transformed-view `/records/.../scientific_context/statement` paths. | Both claim texts exactly match offered statements. Its unresolved scope recognizes missing human/protein/safety measurements; that does not establish applicability to the unspecified hypothesis. |

These are six invalid contracts out of six attempted cells: current 0/3, simplified 0/3. Exact matching text is a mechanical observation, not a scientific score. Correctly copied excerpts can still be selected incompletely or interpreted incorrectly.

## Interface findings supported by the retained payloads

1. **The state rule is incompletely communicated and constrained.** The current guide says `partial=claims plus unresolved-scope reason`; its grammar permits `partial` with a null `abstention_reason`, although the semantic validator rejects that combination. All three current responses take this invalid combination. This is an observed common failure and a testable interface weakness, not proof of its causal sufficiency. The simplified guide names `abstention_reason` initially but later says “reason”; both synthetic responses introduce a literal `reason` key.

2. **The simplified interface requests original pointers while displaying a transformed source view.** Offered passages appear under `records/.../reported_passages` or `scientific_context`; accepted pointers instead use `/statement` or `/source_metrics/textMiningSentences/N/text` relative to the original evidence. There is no explicit source-to-allowed-pointer table in the simplified prompt. Its generic object grammar supplies no pointer enum. Observed outputs use displayed-view paths or text-mining offset objects. The current grammar does enumerate original pointers and all current responses use allowed ones.

3. **An enforced verbatim requirement is absent from the simplified guide.** `source_report` must copy exactly one allowed quote. The guide lists that claim kind but never states this rule. IL6R's simplified paragraph therefore fails an additional substantive contract requirement even beyond its invalid references. The synthetic simplified outputs happen to copy exact text; that does not resolve the specification omission.

4. **Visible inherited limits need an explicit relationship to active output limits.** The source-request context retains `max_quotes_per_claim: 8`; active native outputs allow at most two reference pairs. These are nested ceilings, not logically incompatible rules, but the prompt does not clearly label one as retained input metadata and the other as the active response contract. Other inherited source instructions are compatible with grounding and uncertainty; no malicious or competing task instruction was found in the inspected offered content.

5. **This A/B comparison changes more than proposition complexity.** Current responses have a detailed native grammar; simplified responses use only `{"type":"object"}` plus prose rules. The arms also differ in guidance and citation affordances. Their failure patterns cannot isolate the effect of removing propositions, much less establish that the model lacks the necessary scientific capacity.

## Real-source interpretation concerns

The IL6R source is one admitted literature annotation containing multiple extracted passages; it is not an independently reviewed full paper. The offered evidence nonetheless contains information the current response calls unprovided:

- `/source_metrics/textMiningSentences/5/text` and `/9/text` report the RA estimate, confidence interval and p value; the effect scale must still remain unknown rather than inferred.
- `/8/text` reports no genetic association in the replicated MR analysis. That is a reported replication limitation, not proof of absent biology, and it should not disappear behind a claim that replication information is unavailable.
- `/11/text` explicitly names two-sample MR; `/2/text` and `/10/text` contain variant/proxy information. The excerpts do not supply a complete instrument inventory, but “incomplete” and “no information supplied” are different claims.
- `/0/text`, `/4/text` and `/7/text` identify prior findings. The question explicitly asks to distinguish prior work from the present study; neither response adequately does so.

Both arms avoid a numerical drug-effect or clinical-probability prediction. That boundary is useful, but it does not compensate for omitted counterevidence, misattribution, or broad assertions about what the entire study did not report. The synthetic cases show that several offered facts survive generation even when their envelopes fail. There is no independent human adjudication of these candidate outputs.

## Bounded next action and stopping rules

Retain this run as a failed development diagnostic. Do not silently fix its outputs or loosen admission rules to make it pass. Do not add these candidates or this AI review to clean source-only expert packets.

The next engineering action should be an **offline, prospectively versioned interface proposal**, with no model calls initially:

1. State exact output keys and the three legal state/claims/reason combinations. Use `abstention_reason` consistently. Verify compatible grammar constraints where supported while retaining semantic validation.
2. Expose an explicit E-alias/allowed-original-pointer table, explain that displayed-view paths and provider offsets are not response references, and state the verbatim `source_report` rule. Label inherited bounds as input metadata; state the active response cap once.
3. Add deterministic positive and negative fixtures for partial/null state, renamed fields, missing limitations, object-valued and transformed-view pointers, and verbatim reporting. Test the interface without altering archived payloads or weakening validators.
4. Predeclare a small repeat design only after those checks pass. Make clear which interface factors change; retain all failures and count all attempts. Any repeat uses a new frozen plan and is a new development experiment, not a retry that replaces this result. Keep human scientific review and clean references separate.

There is **one exposed real case, two invented synthetic cases, one response per arm per case, and zero stronger-model controls**. No confidence claim, generalization to T6, capacity diagnosis, validated biological conclusion, or permission to expand to 20 cases follows. Stop further generation if the interface remains ambiguous, source isolation cannot be demonstrated, or the next comparison is not prospectively specified. Human source-only review remains pending; this AI triage cannot satisfy that gate.
