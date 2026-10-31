# R05 capacity/interface diagnostic preparation

Date: 2026-10-26. Status: inventory and paired no-dispatch payload preparation passed;
runtime adapter/post-validator and execution package are not yet qualified.
Current preparation version: **v2**, superseding the first payload package because
its simplified claim cap did not match the exposed real request's cap. See final
supersession section; all original proofs, helper bytes and payloads remain retained.
No model calls, downloads, remote access or provider spending. This is a development
diagnostic, not H5 qualification, a historical arm or held-out scientific performance.

## Available assets and measured resource basis

`inventory.json` contains freshly computed size/SHA256 for every acquired model shard,
runtime binary and acquisition archive, compared to `acquisition.json`. The only model
directory in the authorized project model root is Qwen/Qwen2.5-14B-Instruct-GGUF,
revision `b466e1f8c07172155743e8e1307507d8a4f91fbd`, Q4_K_M, three shards totaling
8,988,110,496 bytes (8.37 GiB). Runtime is llama.cpp b11717 Windows Vulkan.
This inventory does not claim there are no models elsewhere on the computer.

Read-only NVIDIA inspection initially reported RTX 5070 Ti, 16,303 MiB total and
14,741 MiB free, driver 610.88. The machine-readable inventory records a second
timestamped observation. CIM queries were denied; GlobalMemoryStatusEx supplies
physical RAM and current availability without privilege escalation. Disk/model
size does not establish GPU fit: KV cache, runtime buffers, context and resident
applications must also fit. No model server was launched to measure those costs.

Pinned runtime configuration supports a 16,384-token context envelope with at most
2,048 output tokens; existing code conservatively reserves UTF-8 prompt bytes + 32
as input tokens. Preserve this bound, rather than treating byte counts as measured
tokenizer counts. Startup admission must record actual context, offload, runtime
identity, resident/peak CPU and GPU memory; never silently reduce context or change
quantization. Peak memory and latency estimates remain unavailable until a qualified
owned startup/run; there is no fabricated tokens/second estimate.

## Diagnostic cases and exact matching rule

Use **three case slots**, one exposed real case and two explicitly synthetic cases:

1. IL6R genetic exposure/outcome orientation: reuse the exact evidence, question,
   hypothesis and candidate order of
   `runs/question-development-20261026T023832Z/preparation/mr-discovery-replication-request.json`.
   No evaluator answer, adjudication file or prior candidate response enters prompts.
   Current renderer produces 12,785 UTF-8 prompt bytes; output-schema JSON is 3,090
   bytes under ordinary `json.dumps`. These are distinct from complete HTTP payload
   size and token usage. Do not use both exposed IL6R tasks to imply two independent cases.
2. Synthetic orientation control. Source E0, exact passage: "In a synthetic cohort,
   genetically predicted protein X was the exposure and outcome Y was the outcome.
   Discovery estimated beta 0.20 (95% CI 0.05 to 0.35). Replication estimated beta
   0.03 (95% CI -0.10 to 0.16). Effect units and intervention effects were not reported."
   Question: "What exposure/outcome orientation, discovery and replication results,
   uncertainty and intervention-transfer limits are supported by this source?"
3. Synthetic absence/context control. Source E0, exact passage: "In cultured mouse
   liver cells, compound Z reduced transcript X after 24 hours compared with vehicle.
   Human efficacy, protein abundance and adverse effects were not measured."
   Source E1, exact passage: "An unrelated human skin-cell study measured protein W;
   it did not measure X or compound Z."
   Question: "What does the evidence establish about compound Z and X, in which
   context, and what remains unknown about human efficacy and safety?"

Synthetic hypotheses must use explicitly synthetic identifiers, unspecified target
action unless declared in the question, and no real biomedical source attribution.
Reference expectations are evaluator-only: orientation is not reversed; nonsignificant
replication is not proof of no effect; units remain unknown; mouse transcript evidence
is not human protein/efficacy/safety evidence; unrelated E1 cannot support a Z claim.
These reference sentences are **not appended to any model prompt**.

Before dispatch, materialize one semantic request per slot with canonical hashes for
question, evidence records, ordering, context and source IDs. Both interface renderers
must round-trip to those identical hashes. Pin all complete rendered prompt bytes,
native schemas and canonical HTTP bodies separately. No filtering, source substitution,
truncation or post-response repairs are permitted to obtain fit. Synthetic requests
still need materialization through the qualified admission/request builder in R06;
the prose above is a frozen design specification, not a claim that executable requests
already passed the v2 source contract.

`current-preflight.json` retains a no-dispatch current-interface check: canonical
request fingerprint and decoded-prompt fingerprint both equal
`14b735ef940bde56c04ea964cf145f3f7d1e343b2fe1e35de157cc8a5af2d61a`.
The complete canonical HTTP payload is 16,702 bytes; the conservative reservation
is 12,817 input plus 2,048 output tokens. The canonical payload SHA256 is
`00bfc6e31a3b506cf81813ad4cf7367b2d943402aba7ba078eb59df994a9ac01`.
These measured values apply only to the existing current interface and retained
request/configuration, not the pending simplified or synthetic cells.

## Matched conditions and output meaning

| Cell | Model | Interface | Availability |
|---|---|---|---|
| A | Existing pinned Qwen 14B | Existing question/proposition contract | Assets present; new diagnostic execution not authorized by this preparation |
| B | Same exact Qwen weights/runtime | Simplified flat JSON response | Adapter/post-validator preparation required |
| C | Stronger approved model | Same simplified interface as B | Unavailable; no local asset or approved external access identified |
| D | Stronger model | Existing interface | Optional, currently unavailable; do not add by default |

Simplified response meaning: an object with `answer_status` (answered/partial/abstained),
`claims` (maximum three), `unresolved` (array of at most four strings), and
`abstention_reason` (null or a nonblank string of at most 512 characters). Each claim
has `kind` (source_report/scientific_inference/caution), `text`, `source_ids`,
`quote_pointers`, and `limitations`. Text is bounded to 1,800 characters; source IDs
and quote pointers must resolve exactly; unsupported IDs, duplicate claims, invalid
states and empty/nonblank violations fail post-validation. Abstained requires no
claims and an explicit reason. Flat JSON syntax may use a generic object grammar;
semantic validation remains strict Python validation, not an unsupported native
regex/schema-converter feature. Do not manufacture omitted structured propositions
to make B appear compatible with A's full contract.

All cells answer the same questions and report the same scientific distinctions;
evaluate common source entailment, orientation, context, uncertainty and abstention
criteria. Interface-specific schema success is reported separately. A/B isolates an
interface package change, not model capacity or solely grammar complexity. B/C can
inform capacity only if the stronger cell actually runs with equivalent sources and
budgets. Missing C means **capacity unresolved**, regardless of A/B outcomes.

## Bounded payload/resource contract

- Temperature 0, seed 42 where supported, one response per case/cell, no retries.
- Keep candidate order E0 then E1; no random reordering after observing output.
- Prompt cap 14,200 UTF-8 bytes; 2,048 output tokens; context ceiling 16,384.
  Verify framing, Unicode escaping and model control-token escaping before dispatch.
  Full HTTP body capped at 65,536 bytes separately. Retrieve no new source material.
- Each case has existing aggregate ceilings: 32,000 input-token reservation, 8,000
  output tokens, 16 calls, 300 seconds, $0. The diagnostic narrows this to A/B once
  each (two calls, at most 28,464 conservative input tokens and 4,096 output tokens).
  Share the 300-second case budget across A/B, reserving at most 150 seconds each;
  do not reset the case budget per arm. Startup/teardown is recorded separately with
  an overall diagnostic ceiling of 20 minutes for all three cases and lifecycle.
- C cannot be silently added to A/B under these reservations: freeze a revised
  allocation that still fits the unchanged aggregate ceilings, or a separately
  justified comparison design before execution. No automatic budget inflation.
- No download or provider-spend allowance. A stronger-control proposal needs a named
  immutable model/revision, license/access basis, exact compressed/expanded storage,
  KV/buffer/RAM/offload estimate, tokenizer/context fit, capped acquisition/compute
  plan and explicit owner authorization if new access/spending is needed. No current
  model/version recommendation is made without the required source verification.
- Retain every attempted and undispatched cell, failures and timeouts in denominators.
  Reserve output before dispatch; seal journal, original response bytes, measured vs
  estimated usage, request hashes, runtime configuration, timing and termination proof.

## Remaining gates and interpretation

R05 inventory/design is useful preparation, **not a completed executable freeze**.
R06 must implement only the minimal simplified renderer/post-validator and build the
three paired payloads, with mechanical equality, escaping and fit tests. Current IL6R
payload fit is measured; simplified/synthetic complete payload fit is still pending.
No grammar/converter search loop is authorized. If the simple interface cannot express
the task, redesign before another controller stack.

Two independent human source-only references should precede exposure to candidate
outputs. No human recruitment or completed references were established by this pass.
AI mechanics/triage can proceed; independent scientific interpretation and H5 remain
unqualified until the required human process actually occurs. Previously exposed
IL6R material remains development-only. Do not claim successful target biology,
clinical prediction, historical validity or model superiority from this diagnostic.

If no cell produces useful grounded content, retain the negative result and keep the
extractive framework; do not expand to a twenty-case generation batch.

## Completed no-dispatch preparation (supersedes pending payload work above)

At the coordinating agent's request, `prepare.py` now materializes all three requests
and six paired payloads under ignored `data/cache/recovery-step5-payloads-20261026/`.
`paired-preflight.json` retains exact hashes, source-order/evidence equality, complete
canonical HTTP byte lengths, conservative native reservations and per-cell time bounds.
Both interfaces round-trip to the same complete question request, including the same
evidence and hypothesis. The simplified guide differs and uses native generic-object
grammar; its scientific source body is unchanged. No dispatcher/server is imported or
started by preparation. Synthetic requests use existing reviewed genetic/mechanism
question templates rather than adding the custom illustrative question phrasings above.
They have explicit synthetic identifiers and fixture notices; structural bindings do
not assert real-source admission. Reference expectations are stored in a distinct
evaluation-only artifact never supplied to the renderers.

`simplified-response-schema.json` records the future strict post-validation schema;
cross-field rules and source/pointer resolution remain explicit additional checks.
The actual response validator and adapter are still pending R06. Thus payload fit and
semantic input parity are now measured, but simplified output qualification and R07
execution are not complete or authorized by these artifacts. No performance result
or model-capacity conclusion follows from preparation.

All **56 acquired model/runtime/archive assets freshly rehashed and matched** their
acquisition entries. Latest GPU observation: 16,303 MiB total, 14,857 MiB free.
Physical RAM: 34,188,681,216 bytes total, 16,728,936,448 bytes available at observation.
These readings remain momentary; no memory-fit guarantee is made.

## v2 correction after independent review

`prepare_v2.py`, `paired-preflight-v2.json` and `preparation-check-v2.json` supersede
the initial preparation, with explicit hashes pointing to preserved original proofs.
New payloads are under `data/cache/recovery-step5-payloads-20261026-v2/`; no earlier
sealed bytes were replaced. Both interfaces now allow **two claims for real IL6R**
and **three for each synthetic request**, computed as
`min(3, request.source_request.bounds.max_claims)`. Each claim has at most **two quote
references**, and both arms reserve **2,048 output tokens**. Request-specific future
simplified post-validation schemas are pinned alongside each payload, and the helper
asserts equality against current-interface schema limits. The current interface's
structured proposition fields remain an intentional interface-specific difference;
the simplified interface must not fabricate them to mimic current output structure.

The retained IL6R genetics request was prepared for an earlier run but its MR task
was **undispatched**. Its source material is nevertheless exposed development content;
neither undispatched status nor payload reuse makes it a fresh holdout. Only source
request data enters the diagnostic; prior candidate outputs and evaluator answers do
not. Existing human orientation preparation concerns a mechanism task, not this
genetics diagnostic. Scientific evaluation here requires relevant genetics/MR methods
expertise and independently prepared source-only references; the mechanism packet
cannot satisfy that requirement. No such completed human evaluation is established.
