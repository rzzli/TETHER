# BG04 interpretation and closure checklist

Prepared while the root reports all 199 worker cases terminal but parent finalization remains pending. **This document contains no benchmark scores and does not establish a completed generation seal.** No answer references or candidate correctness were inspected to prepare it. Bracketed fields below remain pending until independently anchored outputs are available.

The governing sources are the [protocol and prospective A01 weak-solver amendment](../../../TETHER%20LitQA2%20Evaluation%20Protocol%202026-11-06.md), [A02 generation-path amendment](generation-freeze-attempt02/AMENDMENT.md), and [paired-comparison scope](PAIRED-COMPARISON-SCOPE.md). This checklist changes no producer, policy, metric, budget or completion threshold.

Before opening references or filling the result fields:

- [ ] Confirm the parent's completed generation seal, anchored manifest, full ordered 199-case schedule, exactly-once dispatch accounting and verified normal server cleanup. A worker-terminal event alone is insufficient. Retain failures and partial artifacts without replay.
- [ ] Verify original collection freeze and completed source audit; separately verify A02's corrected generation code and qualification. Preserve the original frozen source bytes and the cache-path regression. A02 changes two path checks, not the scientific settings or A01's failed semantic control.
- [ ] Confirm source/answer isolation and that the original candidate bytes are identical across raw reporting, session replay, native parsing and admission. Only after this gate may the evaluator open pinned originals and reconstruct the frozen option mapping.
- [ ] Complete native scoring, source-inclusive replay and independent operational/result reconstruction; retain their external anchors and any disagreements. Do not substitute successful software tests for actual run verification.

Use the following result structure. Count each question once, not each source, option, repeat check or journal event. Keep every scheduled case, including an unavailable input or unexecuted case.

| Quantity | Required report entry |
|---|---|
| Scheduled and actual operations | `N = 199`; produced [ ]; malformed [ ]; timeout/error/interruption [ ]; input unavailable [ ]; unexecuted [ ]; generation and tokenizer attempts separately [ ]. |
| Native raw answering | Correct `C = [ ]`; substantive answers `A = [ ]`; valid unsure [ ]; accuracy `C/199`; precision `C/A`; coverage `A/199`. If `A = 0`, label precision undefined; disclose any numeric zero used by the machine convention. |
| Admission of the same candidates | Accepted [ ]; rejected [ ]; check errors [ ]; not checked [ ]; correct-and-admitted `Ca = [ ]`; substantive admitted `Aa = [ ]`; yield `Ca/199`; selective precision `Ca/Aa`; coverage `Aa/199`. |
| Losses and retained errors | Correct but explicitly rejected [ ]; correct otherwise not admitted [ ]; incorrect substantive admitted [ ]; accepted unsure [ ]. Do not call accepted unsure a false scientific claim or hide it among operational failures. |
| Source diagnostics | Completed source cases with/without eligible articles [ ]; failed/unexecuted collection cases [ ]; annotation-relative retained-document recall [ numerator / denominator ]; intended-prompt source recall [ numerator / denominator ]; unresolved/unannotated identifiers [ ]. |

Check the invariant `Ca ≤ C`: a filter applied to fixed candidate bytes cannot increase all-scheduled correct-answer yield. A change in selective precision can result from discarding answers and must be read with coverage and correct-answer loss. The raw arm already shares TETHER's source eligibility, captured inputs, grammar and transport; it is **not** a wholly TETHER-free end-to-end comparator. A high admission rate is unsurprising under constrained valid interfaces and does not demonstrate entailment or improved reliability.

The strict JSON adapter projects malformed output to an operational failure: incorrect on scheduled accuracy and outside substantive precision/coverage. Disclose its difference from upstream free-form parsing. Never relabel a missing, rejected or timed-out answer as a successful native unsure. Any all-unsure outcome remains a valid negative measurement under A01, with zero substantive coverage, not task competence. No post-result minimum accuracy threshold may be introduced.

Source recovery is relative to normalized benchmark annotations and the fixed Europe PMC search, license, article and passage bounds. Missing eligible text may reflect retrieval, access, licensing or extraction limits; it is not absence of scientific evidence. Intended prompt coverage for an unexecuted case does not prove the model received those inputs. DOI identity or lexical passage alignment does not establish support for the chosen answer. Contemporary, tool-assisted public-question results are not a reproduction of the original tool-free model condition, a private holdout test or evidence that model training excluded these tasks.

| Cost layer | Required accounting and limitation |
|---|---|
| Source collection | Wall/CPU time, declared HTTP requests, known body bytes, conservative unknown-transfer bounds and selected text. Body bytes exclude HTTP/TLS overhead; retained bytes are not physical I/O. |
| Shared producer workflow | Source verification, model asset verification/startup, tokenization and generation. Separate measured native tokens from conservative reservations, and report failed attempts. Do not count this shared work twice as two independent arms. |
| Additional checks and evaluation | Directly measured admission time, replay/reconstruction and native scoring. Marginal checking is not total provenance or runner cost. Mark uninstrumented subcomponents unknown rather than subtracting approximate timers to invent them. |
| Resources and money | Process CPU/RAM scope and sampling method; startup versus after-readiness sampling; parent/worker measurements may overlap. GPU memory, energy, depreciation and labour are unknown unless actually measured. Zero external-provider charges do not mean zero total cost. Keep fictional control/development costs separate from the actual evaluation while disclosing both where retained. |

The frozen controller captures `parent_resources` **before** calling `_seal`; that field therefore excludes final case recovery, output publication, inventory hashing and sealing. The supervised worker's deadline does not bound this later parent finalization, which has no deadline check. Do not describe either the worker timer or `parent_resources` as total end-to-end latency or a hard bound on the complete stage. Report finalization separately only from retained external measurements; otherwise mark its exact duration and total-stage wall time unknown. A source-only microbenchmark found substantial transient allocation overhead in fixed-cap file reads, but it does not profile the running parent or assign an exact share of its elapsed time. See the [allocation diagnostic](READ-ALLOCATION-DIAGNOSTIC.md). Preserve the frozen code through reconstruction.

Suggested closing paragraph, completed only from sealed aggregates:

> The fixed 199-question public LitQA2 measurement [completed / remained partial], with [C] raw correct answers and [Ca] correct answers retained by the source-backed admission policy. [State observed loss/error/coverage differences without implying that filtering generated better answers.] This is a measurement of one frozen weak solver under bounded question-only public retrieval. The fictional positive-answer control remains failed, although native transport and replay qualified. Provenance checks establish the declared identities, eligibility and source bindings; scientific entailment, independent biological correctness, clinical utility and contamination-free generalization remain unestablished. Total and incremental costs are reported separately.

Final closure requirements:

- [ ] All metric numerators, denominators and percentages reconcile with the complete schedule and original scorer/reference reconstruction; no answer-based exclusions or silent retries.
- [ ] Actual control outcomes, A01/A02 chronology, source-access restrictions and measured/unknown costs are retained. Any analytical chance or always-unsure reference is labelled unexecuted, not given invented runtime costs.
- [ ] Results, audits, current status and memory agree and link the sealed evidence; preserve historical proposals and failures. Record the timestamped local commit without claiming third-party chronology attestation.
- [ ] Mark **measurement completion** only after the declared generation, scoring and audit gates pass. Keep partial execution explicitly partial. State **scientific capability** separately; successful finalization never turns the failed semantic control into a pass. Begin the planned equivalent-policy Inspect comparison only after BG04 closure, not from a worker's provisional completion alone.
