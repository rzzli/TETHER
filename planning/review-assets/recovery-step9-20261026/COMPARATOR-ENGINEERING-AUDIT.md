# R09 Virtual Biotech comparator engineering audit

**A small synthetic recorded-contract implementation is feasible next. An interpretation comparator, end-to-end retrieval comparison and unmodified Virtual Biotech reproduction are not complete.** This local read-only audit introduced no model calls, external retrieval, source replacement, protected outcome reads or runtime/test changes. The current R07 native-version stop remains in force. Pending human references do not prevent the engineering work described below, but synthetic contract checks cannot replace scientific review or authorize real-case generation.

## Exact local source boundary

Upstream revision: `71f9da68c95c5ee0ef4c1d9b8f45f10693de022d`. The twelve source-derived role files under `data/derived/science7-upstream-source-20261020T054000Z/` were freshly checked against their retained manifest and adapter-policy pins. Manifest SHA256: `f25a309f93f169fedcf6e5957dbc1946b2f2f33d6909fc85d307a23a30d0634b`.

| Original source | Exact SHA256 |
|---|---|
| `src/agents/registry.py` | `b8eecbbc21716e0636c4e635c69852438d29ce095bd69c8169cdf6e98f66227c` |
| `src/agents/cso/system_prompt.md` | `ce111aaf81408dc1ef0119dcde12de0e03beaada11212d270cfbbc901c0366ec` |
| `src/agents/chief_of_staff/system_prompt.md` | `8bcdef74c90cc045f6cbd36bcbedcbfb6432b7dab2286ddc188ef40c60aaf016` |
| `src/agents/scientific_reviewer/system_prompt.md` | `0858303b50d034ed5b5b68c6a507243c20409d18e60f3dc8d8823389d5163953` |
| `src/agents/target_id/system_prompts/genomics_analyst_short.md` | `ddc34ab89d5f1f84d03623629c972d7c10a8bf5a1ae7d6364637d20253da0c66` |

The remaining specialist prompts, legacy adapter modules, protocol, upstream models/dataset configuration, README and environment are individually pinned in [COMPARATOR-SOURCE-PINS.json](COMPARATOR-SOURCE-PINS.json): **23 freshly hashed local files**. `audit_comparator_sources.py` parses eleven registry definitions through Python AST without importing or executing upstream code. Exact registered tool-name lists, model expressions, prompt composition expressions and source lines are retained there. Source hashes establish byte identity, not tool behavior or dataset completeness.

## What the original source actually specifies

Registry callable: `build_specialist_agents(prompts, workspace_dir: str = None, specialist_model: str = 'inherit')`. It constructs SDK `AgentDefinition` objects whose prompts concatenate a per-agent workspace instruction with the named supplied prompt. Workspace instructions require isolated per-agent directories, saved analysis artifacts, explicit provenance registration and disclosure of failed data queries. This is not a closed immutable-evidence interface.

The CSO prompt forbids direct data querying and scientific analysis, delegates through `Task(subagent_type=..., description=..., prompt=...)`, allows independent specialists to operate in parallel and allows sequential delegation when work depends on earlier findings. It calls a chief-of-staff for due diligence and a scientific reviewer for critique, with possible redelegation. The prompt's Task examples establish these named arguments; they are not a complete SDK argument schema.

The registry gives the chief-of-staff filesystem/shell and `WebSearch`/`WebFetch` capabilities; the reviewer has `Read`. Specialist tool-name examples include `mcp__genetics__query_gwas_associations`, `query_l2g_predictions`, `get_credible_sets`, `get_qtl_colocalization`; `mcp__target__get_target_info`, `search_targets_by_name`, `get_target_tractability`; and disease name/ID queries. Other specialists have functional-genomics, single-cell, drug, pathway, safety and clinical-trial tools. Exact lists are retained, not silently reduced to these examples.

**Exact MCP argument/return schemas are not established by this local source bundle.** Registry names and descriptive prompt text are not function signatures. The scoped archive does not contain the corresponding server implementations/schema exports or the full original runtime session orchestrator. A source-derived adapter must declare its own schema and cannot label it an original tool-compatible implementation. No clinical linkage/labels were opened to investigate this gap.

`src/config/models.py` in the compatibility archive defaults to `claude-sonnet-4-5-20250929`. Specialist model selection can inherit the chosen model; chief and reviewer are pinned to the SDK alias `haiku`. The source lists several selectable model labels and passes model IDs through for provider validation. Those strings do not demonstrate current availability, resolved alias version, identical inference or authorized paid access. An unmodified reproduction would need exact resolved provider/model/runtime behavior and its usage/accounting.

Original environment dependencies include Python 3.11, `claude-agent-sdk==0.1.69`, `anthropic==0.86.0`, `fastmcp==3.2.0`, `mcp==1.26.0`, `pyarrow==20.0.0`, pandas/scientific libraries, single-cell tools and R integration. The dataset configuration declares 38 Open Targets 25.09 directories, including evidence, expression, credible sets, L2G, colocalisation, literature/vector tables, drug/known-drug and safety products. Local selected OT target/disease/evidence files do not establish availability or compatibility of that entire surface. Clinical/known-drug inputs are outside the present comparator source world.

The genomics prompt gives an expected range of 8–15 MCP calls and qualitative bounded-curiosity guidance. This is not a verified hard global source-byte, token, tool-call, timeout or turn budget. The available original documentation does not establish a complete runtime resource envelope; do not substitute the project's adapted limits and call them original VB defaults.

## Existing project adaptation: useful precedent, different task

Relevant files: `tools/science/comparison_workflow.py`, `role_backend.py`, `run_comparison.py`, `planning/protocols/science7-matched-t6-v0.2.json`, and `planning/review-assets/science-prerequisites-20261018/item7/adapter-role-policy-r1.json`.

The adaptation rewrites original role guidance into five fixed stages: chief_of_staff → coordinator_delegate → mapped_specialist → scientific_reviewer → coordinator_synthesize. Every role receives the same bounded category packet and uses the same pinned local Qwen configuration; original provider models, Haiku distinction, SDK orchestration, adaptive delegation and external tools are absent. It returns observation IDs, then copies admitted records as claims. This is source-selection evaluation, not generated scientific interpretation.

Reviewer and synthesis output IDs are restricted to subsets accepted by the preceding role. The hard output constraint was a documented response-informed development amendment; it is not an unchanged original-system behavior or held-out result. Perturbation/literature map to target-biologist, partly because the original functional-genomics scope is cancer-specific. The CSO seeing the same scientific packet also differs from its original no-direct-analysis architecture.

Legacy ceilings are explicit: 12 whole records / 12,000 request bytes per category, a 2,048-byte control reserve, up to three selected IDs, 256 output tokens per call, 120-second call timeout, seed 20261017, and per-case/per-arm caps of 16 calls / 32,000 input tokens / 8,000 output tokens / 300 seconds / $0. Five stages across multiple populated categories can exhaust the case ceiling. Equal ceilings do not imply equal calls or completed work. These are adaptation settings, not proposed R09 defaults or evidence of actual runtime consumption in this audit.

The old runner imports checkout-local `tools.science`, reads a planning policy and expects original absolute source roots. It is not the installed source-independent R09 interface. Reusing it unchanged would reintroduce packaging/path dependencies and the wrong output task. Preserve it as history, not a shortcut around the current frozen package or native stop.

## Keep two comparison tracks separate

| Track | Controlled evidence | What can differ | Minimum additional prerequisites |
|---|---|---|---|
| Fixed-evidence interpretation | Exact same question, hypothesis and source records/passage bytes for all arms, with equal source-scope fingerprints | Explicit role/prompt strategy and recorded multi-stage control, later generated interpretations | Strict distinction between literal quotations and authored interpretation; complete prompt/response bounds; stage lineage; native/interface qualification before any future generation; independent source-only references for scientific review |
| End-to-end retrieval plus interpretation | Same admitted searchable corpus/index version, eligibility rules and resource limits, not necessarily identical retrieved rows | Queries, retrieval/selection strategy and resulting interpretation | An actual bounded retrieval interface with query/response hashes, IDs, ranks, filter/scope/missingness proofs, corpus/index pins, tool-failure handling and complete access accounting; explicit mapping of adapted vs original VB capabilities |

The current deterministic extractive/lexical baselines are an engineering foundation for source-copying/selection, not a completed interpretation benchmark. A frozen common shortlist produced before any arm's strategy is a fixed-evidence input, not evidence of end-to-end retrieval performance. Existing category-local bounded selection cannot be advertised as original VB tool use.

## Next finite implementation: source-bound recorded role contract

Build a **synthetic-only, no-dispatch** fixture consumer for a declared adapted role sequence. Suggested pure API: `prepare_role_request(source_request, role_policy, stage, accepted_history)` and `verify_recorded_role_chain(source_request, role_policy, recorded_chain)`. Keep this prospective; no implementation or activation occurs in this audit.

The implementation should:

1. Admit only the existing authenticated invented source fixtures initially. Pin the exact original role-source hashes as provenance and the separately reviewed rewritten guidance as a versioned adaptation. Do not execute or claim original prompts if the renderer uses rewritten text.
2. Bind each stage request to the unchanged question/hypothesis/source-scope/source bytes, complete policy, stage index and complete accepted prior-stage response hashes. Preserve literal quoted text/pointers separately from explicitly authored interpretation. An observation ID alone is not interpretation and a source quotation is not generated reasoning.
3. Make allowed output support and feedback semantics explicit. If reviewer/synthesis may only narrow a prior selection, enforce that prospectively; if they can revise reasoning, preserve every prior version and a structured revision record without inserting unoffered source IDs. Do not silently inherit the legacy subset rule for a different interpretation task.
4. Accept an explicitly supplied **evaluation-only recorded fixture** as transport test input, never as an agent-visible source parent or a human reference. Bind raw fixture response bytes to the exact stage-request fingerprint. Do not insert fixture expected answers or later evaluator judgments into prompts, source catalogs or tool results.
5. Enforce full request/response byte limits including feedback and prompt framing before a hypothetical dispatch. Record oversized/malformed/missing stages as failures; never truncate/retry/repair. A complete fixture chain still records zero actual model calls and no scientific validation, with any simulated usage clearly separate or omitted.
6. Recompute stage history, source pointers, quotation bytes, response-schema obligations, policy bindings and neutral reviewer projection during verification. Include resources/code closure in installed-package proofs. Do not import archived code or planning/tools during installed replay.

This is meaningful now because it tests the missing comparison boundary—source-equivalent multi-stage authored-output lineage—without demanding a model that passed neither interface nor scientific review. It can expose feedback leakage, output-support mistakes and unequal packet/budget assumptions before any additional expensive generation. It does not require reviewer names to implement mechanical invariants.

Tests should corrupt prior-stage hashes, reorder/omit/duplicate stages, introduce foreign source IDs/evaluator ancestors, alter quoted text or pointers, change the common source packet in only one arm, exhaust full feedback budgets, substitute a different prompt policy, and reseal invalid recorded responses. They must prove no tool/network/model invocation, preserve unknown/partial states, keep synthetic fixture answers out of model-visible inputs, and replay in an installed package. Passing these tests would complete a narrow engineering artifact only.

## What remains unimplemented or blocked

- New recorded interpretation role contract: implementable next, not implemented by this audit.
- Original MCP schemas/tool execution and full SDK orchestration: not reproduced from available scoped artifacts; requires a separate source/schema acquisition or verified local implementation review if later authorized.
- Actual matched interpretation generation: still held by current native-version qualification/stop rules; no real-case candidates authorized here.
- End-to-end retrieval comparison: no current source-bound original-tool-compatible retrieval interface; requires its own bounded corpus/index and eligibility contract.
- Fresh scientific case acceptance, human source references, blinded judgments, power and study claims: remain separate scientific milestones. Human availability is not a reason to claim this engineering work done, nor to block the safe recorded-contract work described above.

No R09 completion, superior accuracy/cost, original Virtual Biotech reproduction, biological validation or clinical prediction claim follows from this audit.
