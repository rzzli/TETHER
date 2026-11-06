# BG04 native LAB-Bench feasibility and policy review

Status: design review; no benchmark questions, answer records or model outputs were inspected, and no inference, retrieval run or benchmark acquisition was performed by this reviewer. Prepared across 2026-11-05 local time / 2026-11-06 UTC for the `20261106` work package. SciFact, core runtime and closed historical model artifacts remain unchanged.

## Decision and scope

**Proceed conditionally with all 199 public LitQA2 questions, question-only bounded public-literature retrieval, and the already acquired local Qwen2.5-14B model.** The root selected LitQA2 before candidate performance was available. This is a feasible engineering route to a $0-provider-spend answering evaluation, not a claim that source access, runtime capacity or answer quality has already passed qualification. Do not choose a source-accessible or model-successful subset after seeing results.

The [execution plan](<../../TETHER Benchmark Execution Plan 2026-11-02.md>) requires actual native answering and matched raw/checked outputs. The [comparison report](<../../../reports/TETHER benchmark priorities and methods.md>) identifies why provenance-only fixtures cannot establish scientific answering ability. Existing model files remove a large acquisition dependency; they do not remove the need for a new task-specific adapter or allow retrying P04/P04b/R07.

DbQA is a credible later alternative, especially its versioned gene-location subtask, but a one-source implementation does not cover its ten distinct database tasks. Do not describe DbQA as uniformly account-blocked: its MSigDB 2023.2.Hs C1/C3/C6/C7 products have an [official public release directory](https://data.broadinstitute.org/gsea-msigdb/msigdb/release/2023.2.Hs/). Product-specific rights, completeness, named annotation releases and task semantics still need qualification. An isolated gene-location run would be a declared subtask evaluation, not a 520-question family result. The data agent owns that separate access inventory; it is not a prerequisite to the selected LitQA2 route.

## Native task boundary

The [official dataset card](https://huggingface.co/datasets/futurehouse/lab-bench/blob/main/README.md) describes 199 public LitQA2 and 520 public DbQA records and CC-BY-SA-4.0 licensing. LitQA2 contains answer/distractor fields and privileged article references, key passages and access metadata. The Hugging Face split name `train` describes its distribution layout; this evaluation must not treat it as permission to fit or tune on the answers. The preparation owner resolved dataset revision `5c77cec648430f30611808808861eb86f81d5eaa`; production must independently receipt/hash the exact artifact and pin the corresponding code definition. This reviewer did not retrieve its question rows.

The [original paper](https://arxiv.org/html/2407.10362v3) distinguishes full-text literature questions from abstract-only lookup and reports tool-free initial model baselines. A retrieval-enabled experiment has different affordances from those published baselines and cannot claim a matched superiority comparison. Public release is a development evaluation, not the private contamination holdout.

The [official input code](https://raw.githubusercontent.com/Future-House/LAB-Bench/main/labbench/utils.py) gives the agent only ID, question and displayed choices for these families. It shuffles the ideal, refusal choice and distractors together. Its dataset loader catches validation failures and can skip rows. Therefore freeze one reproducible all-option permutation per ID, keep its answer/unsure mapping evaluator-only, and require an exact 199-ID inventory before execution. A fixed final refusal option is possible only as a disclosed prompt convention change. Native choice text necessarily contains the correct answer among alternatives; its identity and original unshuffled position must remain hidden.

The [LitQA2 task class](https://raw.githubusercontent.com/Future-House/LAB-Bench/main/LitQA2/task.py) retains `sources`, `key_passage`, `is_opensource`, tag and version in the task record, but inherits the restricted input projection. Giving the producer the question-specific URLs, privileged passage, or a corpus selected from gold-linked URLs changes retrieval conditions. Call that a supplied-source/oracle-corpus derivative if ever studied; do not call it question-only open retrieval.

## Concrete local model route

The current pointer [active-local-model-acquisition.json](../../../data/derived/active-local-model-acquisition.json) identifies this existing receipt:

`E:\projects_data\drug_target_agents_data\models\qwen25-14b-q4km-20261018T032528Z\acquisition.json`

Its retained SHA-256 is `cc95c56ce1f497b36d6b9ed62b22721d8af7eaccc0a8c50da91439c5b076acbf`; the pointer/receipt hash was checked during this review. Model ID is `Qwen/Qwen2.5-14B-Instruct-GGUF`, revision `b466e1f8c07172155743e8e1307507d8a4f91fbd`. Every file below is directly beneath that model root except the explicitly prefixed runtime files.

| Existing file | Bytes | Retained SHA-256 |
|---|---:|---|
| `qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf` | 3,991,999,872 | `a09ea5e7b1eafb1b30b241726c3cc3c905c96f14ad41e246ffa5f44e53904f68` |
| `qwen2.5-14b-instruct-q4_k_m-00002-of-00003.gguf` | 3,989,373,504 | `21b9457d079680d284e90ef69607c4b2d8ef64a09d4729cb7b5e1357bdba41ae` |
| `qwen2.5-14b-instruct-q4_k_m-00003-of-00003.gguf` | 1,006,737,120 | `c8d37006760a387a35216e070e6664d7da927f10be8eb870fef2e3d4833d9976` |
| `llama-b11717-bin-win-vulkan-x64.zip` | 32,307,240 | `773381d83f0b872c6deb1fe5ddc769d1ad6d7da80e6b1fa155374837724a20a3` |
| `runtime\llama-server.exe` | 9,216 | `d5055c9523ef34fdc62d7c5836d105e32be54628704250343638be0092429359` |
| `runtime\llama-server-impl.dll` | 9,357,824 | `3d0764889c21dd557b83983b165f872888b870bd42fcf7021a17cafb80e4c0c7` |

The three shards total **8,988,110,496 bytes**. Read-only checks confirmed all three and the archive exist with retained sizes, and the server executable exists with its retained size. The receipt contains 52 runtime entries. This review did **not** freshly rehash 9 GB of weights/runtime, launch the server or test current device memory. Receipt status remains `downloaded_hash_verified_not_inference_validated`; later historical runs provide separate evidence and do not change this receipt.

The retained [resource inventory](../../../research_notes/TETHER%20benchmark%20priorities%20and%20methods/bg03-resource-inventory.json) reported an RTX 5070 Ti with 16,303 MiB, approximately 31.84 GiB system RAM and 28 logical CPUs. Model weight size alone cannot establish capacity once context/KV cache and other processes are included. Fresh bounded fictional qualification must measure that.

The [model card](../../../paper/release/cards/QWEN2.5-14B-INSTRUCT-GGUF-MODEL-CARD-DRAFT-v1.md) documents the official revision README's Apache-2.0 declaration and the unverified exact-revision LICENSE byte comparison. Keep this limitation. No model weights, runtime or complete article texts should enter the public project release by default; task licensing does not confer rights to linked papers. Local use does not establish redistribution permission.

### Reuse mechanics, with a new MCQ contract

- [StudySession](../../../src/asof/study/session.py) exposes generic `StudyBackend` and explicit `StudyVerifier` protocols, durable accounting and replay mechanics. An adapter needs `quote(request,payload)`, `generate(...,timeout_seconds)` returning captured bytes/usage, and payload/response/execution verification. Real LLM token fields must be measured or conservatively reserved; they are not `not_applicable` as in SciFact's non-LLM actor.
- [OwnedServer](../../../src/asof/study/process.py) provides an owned loopback process with explicit asset bindings, startup/cleanup limits, listener-owner and health callbacks. Use a new reserved port, alias and exclusive BG04 output path, hidden window, no proxy/redirect discovery, and explicit cleanup of only its owned process.
- [LocalBackend](../../../src/asof/study/native.py) is already one-use HTTP transport, but its payload validation imports the diagnostic task. [TokenQuotedNativeBackend](../../../src/asof/study/native_interpretation.py) binds the interpretation interface. Neither is an unchanged native LitQA2 answer adapter. A small explicit new adapter may reuse the generic mechanics and exact-token capacity tools, with its own MCQ binding and replay proof. Do not invent T6 target IDs or weaken existing verifiers.
- [run_local_pilot.py](../../../tools/framework/run_local_pilot.py) demonstrates the existing binary's loopback `/completion` route and flags (`--ctx-size 16384`, `--parallel 1`, `--n-gpu-layers 99`, `--threads 8`, `--offline`, `--no-webui`). Those are historical configuration evidence, not newly measured settings. Do not invoke that launcher for BG04: it reads the old T6 registry and writes old active pointers. Freeze a separate new controller and prospective configuration.

The [closed P04b outcome](../preprint-p04b-20261031/README.md) remains verified negative with no retry. Fresh fictional MCQ qualification tests a new benchmark contract; it must not rerun old cells, repair their outputs, relabel their pass/failure, or tune using their protected material. The [policy decision](../../decisions/2026-10-31-no-external-expert-input.md) also excludes historical human responses and descendants as new inputs.

## Isolation and matched evaluation design

1. A trusted preparation process pins all 199 records, IDs, native option mapping, licenses, source definition and projector code. Produce a minimal consumer view and a separately restricted evaluator view. Raw task storage is a mixed-content container, not a prediction input. Reference files and their manifests are absent from producer grants; source-inclusive auditing may read them only in its separately declared supervisory role.
2. Retrieve from question text using frozen deterministic public API rules. Europe PMC is the proposed access route, pending its own permission/schema/full-text qualification. Do not query with the gold answer, key passage, per-question source URL association or hidden metadata. Preserve returned source bytes, public identifiers, retrieval timestamp, access failures and exact passages, including zero-result cases. Abstract-only and complete-article results must be distinguished. Missing access remains a limitation, not evidence that a claim is false.
3. Build one bounded native request from the question/options and retrieved passages. Freeze prompt, grammar, runtime/model hashes, seed, sampling, context, query/call limits, timeouts and response cap before any actual question. A grammar-constrained answer letter plus optional source/sentence IDs is a reasonable new wire format. Choice and citation parsing must be deterministic; grammar success does not establish source support or correctness.
4. Retain one original producer response per scheduled question. Derive its native answer projection once. The raw arm scores that answer. The checked arm consumes the **same bytes**, request, sources and configuration, making an explicit admission or rejection. No second model call, answer repair, additional retrieval, hidden rationale rescue or unequal affordance is allowed between arms.
5. Bind source citations to actual allowed retrieved bytes/locators, original request/options, model/runtime, prompt and configuration. Make the checked policy explicit about uncited answers, native refusal and empty retrieval. A valid but wrong letter with valid provenance must be able to pass a provenance-only policy; never inspect the hidden ideal to determine admission. If non-refusal answers require citations, that is an added acceptance policy and its rejection cost must be reported.
6. Reserve outputs and journal before model dispatch. One irreversible attempt per cell; timeout, interruption, missing usage, malformed response and write failure leave terminal records without automatic replay. Declare whether a failed cell permits subsequent fresh scheduled cells; global budget/ownership loss stops the stage. Unexecuted cells still stay in the denominator. Independent replay reads frozen bytes without querying a live model or changing retrieval.
7. Seal all candidate outputs and admission dispositions before evaluator reference access. The evaluator can then join frozen IDs and native keys. Any posthoc diagnostic using gold-linked article passages must be labeled separately and cannot feed back into the actor, case selection, prompt, retrieval settings or acceptance threshold for this evaluation.

These are implementation requirements, not claims that Python import/path controls provide an adversarial OS security boundary. Use allowlisted file/network affordances and process isolation as enforced engineering controls, disclose their threat model, and do not call declarative hashes proof of actual training non-contamination.

## Scoring and denominator policy

The [official evaluator](https://raw.githubusercontent.com/Future-House/LAB-Bench/main/labbench/evaluator.py) reports accuracy = correct/all, precision = correct/sure, coverage = sure/all. A returned value unequal to the refusal letter is `sure`, even when malformed; its explicit `UnanswerableError` path is not sure. Other exceptions can terminate the run. Pin and test these details instead of assuming native coverage equals valid-answer coverage.

For this run let `N=199` always, `C` be correct native answers, `A` the native attempted count under a prospectively specified failure projection, and `J` the checked-admitted set. Report:

- Native accuracy `C/N`, precision `C/A`, and native coverage `A/N` for raw and checked projections; show counts alongside percentages. If `A=0`, preserve the native zero convention and explicitly say no attempted answers.
- Correct-and-admitted utility `|correct ∩ J|/N`, admission `|J|/N`, and false rejection `|correct outside J|/C` with an undefined/null rate when `C=0`.
- Native refusal, invalid-format return, transport failure, timeout, budget stop, policy rejection, unavailable source and never-executed counts separately. Do not merge failure with voluntary refusal in operational tables, even if their disclosed native scoring projection is the same.
- A frozen rule for malformed and absent responses. In particular, silently converting every malformed returned string into the refusal option changes the native attempted denominator. If an answer-envelope parser cannot produce a letter, retain the original malformed response and declare its exact native compatibility projection. Do not use an LLM parser fallback.
- Mechanical citation validity, access/full-text coverage and passage availability as separate source measures. Valid citations do not measure entailment. Any post-freeze gold-source overlap diagnostic measures overlap with that reference, not biological truth.
- Paired changes and their uncertainty at question level. Claim-level independence is an assumption: shared papers/questions can correlate. Include paper-group sensitivity only if reference-only grouping is frozen without influencing inference or subset inclusion. A single seed/single public set is not a robust generalization or power demonstration.

No answer performance is reported in this review. Native grammar and fictional conformance tests are engineering results, not answering accuracy. Correctness unchanged with extra check cost is an acceptable outcome, as is weak accuracy from the local actor.

## Qualification gates and hard blockers before performance

| Gate | Current finding | Required before actual answering |
|---|---|---|
| Task/release projection | Original interface read; dataset revision reported by preparation owner; no rows read here | Receipt/hash acquisition, 199 unique IDs, original-code pin, licensed fields, deterministic all-option map, projector and reference-access negative controls |
| Source feasibility | Question-only route proposed; no all-case full-text availability established | Frozen bounded retrieval rules, public endpoint/rights checks, exact source recording, failures preserved, no gold-assisted retrieval; incomplete access limits scope rather than silently removing cases |
| Model assets | Files and sizes present; historical hashes recorded | Fresh byte verification of shards and every executable/DLL dependency used, isolated launch/ownership/cleanup, actual tokenizer/context and resource qualification |
| Native answer route | Generic mechanics exist; older adapters are task-bound | New MCQ adapter and strict deterministic projection, real fictional inference, grammar/source-ID limits, measured time/tokens/memory, no fake T6 objects |
| Harness fairness | Design only | Same frozen producer bytes/source/tool access, explicit citation acceptance policy, valid-but-wrong positive provenance control, tamper/rejection/timeout/write-failure/alias controls |
| Scorer compatibility | Native formulas and failure quirks inspected | Fictional native answer/refusal/malformed/missing/duplicate tests and independent scorer agreement; exact 199-cell reconciliation |
| Production freeze | Not yet completed in this review | Model/runtime/prompt/source-policy/code pins, explicit finite per-cell and stage budgets, reserve/journal/failure rules, candidate-before-gold ordering, independent reconstruction plan |

A missing permission or inaccessible file should be reported to the owner if it blocks this route. An inaccessible article can instead remain an explicit scheduled retrieval failure under the frozen all-case design; it does not justify silently moving to a gold-selected article corpus. No unsupported conclusion about complete source availability is needed to execute a clearly bounded retrieval evaluation.

Provider/API spending can remain **$0** because inference uses existing local assets and acquisition is restricted to authorized public endpoints. Record CPU/GPU/wall time, peak monitored memory and its limitations, token totals, source/retrieval bytes, startup and source-verification overhead separately. Host energy, equipment depreciation and platform-agent usage are not measured here and must not be called zero cost. The quoted same-model raw/check comparison concerns retained actor output and additional policy overhead, not an independently rerun actor.

Public questions and articles may have been in model training or later development material. The model's 2024 release does not prove absence of the public 2024 benchmark. Preserve contamination warnings and benchmark canary metadata in the evaluator/audit view; a canary's presence or absence does not certify clean training. The endpoint is source-grounded public development answering with transparent costs and restrictions, not a contamination-free private test or a clinical validation.
