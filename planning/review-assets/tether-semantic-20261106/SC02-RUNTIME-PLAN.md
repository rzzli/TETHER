# SC02 isolated solver qualification

Execution begins only after [SC01 root acceptance](decomposition/ROOT-ACCEPTANCE.json), retained at local commit `6166217`. This stage qualifies a solver and runtime; it does not execute the 300 development claims or complete SC03.

The selected peer is the released MultiVerS `fever_sci` full-context joint model. The source revision, checkpoint version, training-exposure limits and rights review are in [feasibility](solver-feasibility/MultiVerS-feasibility.md). No explicit checkpoint-specific redistribution license was located. This is local research use of author-published assets; weights will not be bundled into a release.

## Acquisition and installation

- Use the fixed [acquisition manifest](solver-feasibility/acquisition-manifest.json): 30 assets, 8,571,393,927 payload bytes, maximum 9,000,000,000. It includes the 5.254 GB checkpoint, 25 wheels and four tokenizer/config assets. Receipt/metadata overhead is recorded separately.
- New payload root: `data/cache/tether-multivers-acquisition-20261106-attempt01/`. Each file receives a content digest and receipt. Verify published wheel digests, exact byte lengths and pinned upstream identities. The checkpoint's multipart ETag is an identity observation, not a whole-file digest.
- Stream bounded chunks, preserve failed partials and terminal records, and do not overwrite/resume a failed attempt implicitly. The existing download worker and stopped monitor remain untouched. The new transport worker has a two-hour hard deadline and network/stall controls; the parent's final small journal/root-receipt publication uses cooperative local I/O and lies outside that watchdog boundary.
- Create `data/cache/tether-multivers-env-20261106-attempt01/environment/` using the qualified Python 3.11.15 base. Install the hash-locked wheels with uv 0.11.2, no index, no network, no automatic Python download and no discovered user/project configuration. Keep temporary/cache paths inside the workspace and record tool identities, commands, output and package inventory.
- Initial working-storage allowance is 50 GB for originals, expanded environment, temporary files and derived inference artifacts, against approximately 1.70 TB free on D: at review. This is a conservative local allowance, not a measured full-project size. No paid provider calls or transfer service is introduced.

## Qualification gates

1. Inspect checkpoint format and static globals before restricted loading. Use `weights_only=True`; do not silently fall back to unrestricted pickle. Any narrow safe-global allowance requires an explicit retained audit. Verify complete parameter keys/shapes and reject missing or unexpected learned tensors. Optimizer state is not an inference input.
2. Reproduce original tokenizer additions/order, text delimiters, sentence offsets, global attention, pooled label head, pooled-then-sentence rationale head, label mapping and released decoding. Compare the adapter against retained original source with documented compatibility shims; do not claim historical binary equivalence.
3. Use FP32, batch one, evaluation/inference mode, eager attention and disabled TF32 initially. No online fallback. Account for tokens before dispatch; reject overlength input explicitly, with no silent sentence deletion. Qualify examples longer than 512 tokens and the declared maximum-length boundary.
4. Run invented controls before actual benchmark use: supported/contradicted/irrelevant contexts, changed sentence ordering, empty/malformed input, NEI decoding, threshold boundaries, force-rationale behavior, strict checkpoint admission and failure accounting. Preserve semantic misses. Passing architecture/transport tests alone does not establish useful scientific reasoning.
5. Measure actual load/forward time and CPU/GPU memory boundaries. Initial qualification ceiling: 30 minutes per owned qualification process, 120 seconds per inference case, batch one and at most approximately 90% of GPU memory. A qualified supervisor must retain timeout/interruption records. No uncertain inference call is repeated automatically.
6. Retain source/checkpoint/environment/code/configuration pins, failed attempts, predictions, parity results and an independent review. A successful import or an unscored example is insufficient for SC02 completion.

The primary release-default setting is `force_rationale=false`; the paper's forced-rationale description differs from the released prediction script. Any forced variant must be declared prospectively. The 380 fit, 82 tune and 69 calibration roles remain distinct, and development labels remain evaluator-only. No fit, tune, calibration or development inference is required for this invented-input qualification.

The subsequent SC03 protocol will fix the retained retrieved documents for the primary solver comparison and separately label reference-informed evidence interventions. Solver supervision differs from the sparse baseline and is not an isolated architecture ablation. A negative comparison remains a reportable measurement.
