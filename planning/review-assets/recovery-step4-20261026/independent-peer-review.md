# Final R04 peer review and R05–R06 implementation boundary

Reviewed 2026-10-26. Read-only review of source, tests, candidate compatibility resource, recovery plan and existing development documentation. No model call, network request, source/profile/test edit, or clinical outcome payload read. This is an engineering review, not scientific validation.

## R04 conclusion

No new correctness blocker was identified in the scoped final changes. Final acceptance remains conditional on the root task's fresh full validation, package checks and seven installed original-root-denied archived-run replays. The reported 72-test focused pass is not described here as a full pass.

`profile-check.json` independently records 22 matching module hashes and a successful `ensure_supported_semantics()` call. Candidate resource SHA-256: `25ace81b97bcfefb024f2759625a65232ff3032a35aae5d73394f5d0e3423838`. The resource records its predecessor hash and refers to the retained semantic-delta review; it does not replace original receipts or execute archived Python.

| Boundary | Reviewed outcome |
|---|---|
| Store construction | Constructor resolves an explicitly supplied relative base immediately. Query-only stores retain explicit `None`. Execution rejects missing/non-directory/post-mutated relative bases and archive verification stores before preparation, quote or dispatch; final writer repeats the readiness guard. |
| Publication | Live admission rejects invalid types, conflicting exact date/year and explicit future information. Same-year and missing-publication metadata remain eligible only through existing complete lineage/availability admission. A recent computation does not turn old inputs into new information. Archive core retains the old copied publication gate; the differential regression makes the distinction explicit. |
| Local transport/protocol | URLError and HTTPError become recoverable ConnectionError while the native failure identity is retained. Invalid response envelopes/content/count presence become ContractError. Generic OSError and interruption behavior remain distinct. Existing full-workflow peer regressions cover continuation, no failed-category retries, conservative accounting and semantic finalization. |
| Payload | `prepare_request` renders the complete exact payload before reservation/dispatch, including framing and escaping. Retrieval allowance remains distinct from the 16,384-byte prompt cap. Existing payload construction remains unchanged for valid historical requests. |
| Archive reads | JSON consumers pass bounds into the resolver before buffering. Declaration/stat/fstat/stream checks enforce those bounds; raw proof validation streams without a JSON cap. Interpretation pin checking now authenticates by streaming and journal parsing uses the authenticated buffer. |
| Publication/filesystem | Shared atomic byte publication uses same-directory Windows no-clobber rename or POSIX no-clobber link, with no unsafe fallback. The directory-init lock is explicitly in-process; the OS publication primitive handles competing processes. Tests cover concurrent writers, conflicting receipts and cleanup. This does not establish power-loss durability or arbitrary network-filesystem behavior. |
| Contracts/path spelling | Mapping factories preserve canonical empty-mapping values; union failures retain branch causes without changing valid decoding. Extended Win32 drive/UNC identity normalization rejects non-equivalent/device spellings and retains resolved containment. |

Remaining limits are explicit rather than new R04 failures: supported native successful-question callbacks remain outside the archive representative set; the original-root-denied replay matrix must pass on the final installed code; source fidelity is not independent biological credibility; hosted CI and off-machine durability remain open. Archive envelope and JSONL input limits are artifact-specific, not a claim that every possible input is capped at 64 MiB. No broad new guard or behavior change is proposed during the frozen validation pass.

## Exact R05 minimum

The controlling requirements are Step 5 (items 1–7) and its validation/stop paragraphs in `planning/Project Recovery and Evaluation Plan 2026-10-26.md`. R05 is preparation with **zero model calls**.

1. Retain a fresh read-only hardware/resource inventory: CPU, physical/available RAM, GPU identity and dedicated/free memory where measurable, runtime version and support, current owned-process/listener state, and approved model files. Reconcile complete exact weight/runtime hashes with existing receipts. Do not equate disk capacity, declared config or old timing with current memory fit.
2. Define one semantic evidence/question contract separately from each wire format. Use the exposed IL6R mechanism source as diagnostic material and one or two small synthetic sources with known facts and explicit unknowns. Avoid adding the scientifically unqualified full-cis MR task merely because its old launcher lists it. Keep synthetic expectations and human answers in evaluator-only files, absent from prompts and agent manifests.
3. Prepare cells for the existing model/current interface and existing model/simplified supported interface using identical semantic evidence, questions and candidate order. Prepare a stronger-model/simplified cell only if an already approved available asset qualifies. An unavailable cell stays undispatched with a reason; two interfaces on one model cannot identify a capacity effect. The stronger/current cell is optional.
4. Freeze exact source/request/payload/config hashes, source order, output meaning, response post-validation, temperature/seed, explicit input/output/context/time/call/memory bounds and failure policy. Token reservations may differ across tokenizers; evidence may not silently differ or truncate. A diagnostic plan must record interface/format compliance separately from source-entailment and scientific usefulness.
5. Implement a no-dispatch preparation/preflight command that proves semantic source/request equality and complete payload fit, checks answer isolation, and emits every planned/blocked cell. It must not start a server merely to prepare the plan. Use documented runtime/context limits, existing measured observations and explicit unknowns for estimates. Do not call estimates measured new latency/peak memory.

The existing documented approved model is Qwen2.5-14B-Instruct Q4_K_M, revision `b466e1f8c07172155743e8e1307507d8a4f91fbd`, three GGUF shards totaling 8,988,110,496 bytes; existing runtime documentation names llama.cpp b11717 Vulkan and a 16,384-token single-slot context. These are historical metadata to recheck, not a fresh hardware finding. This review establishes no stronger local asset or stronger-model fit.

Suggested retained outputs: `hardware-and-assets.json`, `diagnostic-plan.json`, exact read-only source/request/payload files, an evaluator-only synthetic expectation file, and `preflight-report.json`. All should be newly reserved/versioned and have explicit development exposure, provider cost zero and `model_calls: 0`. No new catalog data ingestion is needed.

## Exact R06 minimum

The controlling requirements are Step 6 (items 1–7) and its installed-wheel validation paragraph. Select **one new diagnostic study** as the migration consumer; do not modify the seven old launchers to make them share a new stack.

1. Reuse packaged `RunJournal`, usage/budget types and atomic publication. Add only the small missing study reservation/terminal-failure wrapper, package-aware code/resource proof capture and owned-server lifecycle helper needed by that diagnostic. Preserve no-overwrite behavior, primary exceptions, interruption records, unknown potentially billed calls, and cleanup of the exact process created by this launcher. Never stop an arbitrary listener or redispatch from recovery.
2. Define explicit backend capability and trusted verifier interfaces. Backend IDs remain provenance; capability, request rendering, budget fit and verification behavior must not depend on a growing `if backend_id` list. Keep supported legacy trace adapters versioned and do not automatically import arbitrary archived callbacks.
3. Make the new study's case specifications, role instructions, templates and interface policy packaged versioned resources or explicit supplied files. Include their bytes in request and archive fingerprints. Keep expected answers/evaluator resources out of model request preparation. Add package-data entries only for the actual new resources.
4. Migrate the single diagnostic's recorded success and failure paths to these helpers. Provide a fully installed-wheel smoke entry point that prepares/executes recorded synthetic fixtures without repository `tools/` or `planning/` imports. Its optional local execution path can be prepared without running inference. Both successful and failed fixture artifacts need inspection/verification; a failed fixture is not silently repaired.
5. Introduce bounded shared HTTP transport only if this scheduled consumer actually uses it. The stopped clinical route has no scheduled AACT consumer here: do not extract PostgreSQL sessions now. A thin wrapper that still imports repository `tools.science` does not satisfy the wheel gate.
6. Add a new version and concise CHANGELOG entry for the new public API, keep package/version metadata consistent, and scope formatting/lint plus coverage reporting to the changed modules. Build/test tooling must not become an accidental default runtime dependency. Preserve independent review tests.
7. Re-run old artifacts through the supported archive path after modifying any pinned live helpers. If migration touches a semantic guard dependency, use the same explicit review/replay procedure; do not silently regenerate its pin resource. Prefer new packaged modules to avoid unnecessary changes to stable helpers.

R05 can freeze semantic questions and proposed cells before implementation; final payload fingerprints should be sealed against the actual R06 renderer used for dispatch. If a renderer changes, emit a new prepared version with an explicit supersession link rather than rewriting the frozen plan. R07 uses that final version only.

## Blockers versus work that can proceed

| Dependency | Current evidence and effect |
|---|---|
| R04 validation | Engineering gate: wait for the full run and seven final installed replays before changing frozen dependencies. Read-only R05 inventory/design can proceed while validation runs. |
| Stronger model | Availability and fit are unestablished. Inventory/preflight and existing-model interface design can proceed. If no approved stronger asset qualifies, record the capacity comparison as unresolved and present the exact optional resource request; no download or paid call follows implicitly. |
| Independent humans | The current shareable IL6R HTML/PDF, recruitment brief and coordinator guide exist. The inspected current records do not establish two returned independent submissions. This does not block R05/R06 engineering or recorded-fixture smoke tests. It blocks independent scientific qualification. Before R07 native execution, honor the plan's HR2/scientific-review gate; do not silently relabel AI ratings as human references. |
| Fresh cases | Not required for exposed/synthetic R05 diagnostics. Fresh eligibility, source completeness, exposure and reviewer coverage belong to R08 and later. |
| Genetics/clinical access | Existing local assets and stopped scientific gates are separate. Neither historical labels nor MR computation is a prerequisite for this mechanism/interface diagnostic. No protected outcome inspection or new acquisition is justified by R05/R06. |
| Hosted CI/off-machine backup | Open release gates; not blockers for local no-inference preparation and installed-wheel recorded smoke verification. Do not claim those gates passed. |

Proceed after R04 acceptance with the no-call R05 preparation and the single-consumer R06 migration. The first need for owner input is a concrete unavailable resource or required human submission, not a request to reapprove already authorized engineering.
