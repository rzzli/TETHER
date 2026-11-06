# SC02 independent static adapter review

6 November 2026, implementation in progress. Reviewed `experiments/scifact_multivers/{checkpoint,contracts,data,model,reference}.py` and its initial tests. This review does not freeze those changing sources or claim executed checkpoint/model qualification.

The implementation follows the inspected original inference route: captured local tokenizer bytes, ten ordinary science tokens in their original order, original concatenation and global-attention rules, full input without implicit truncation, pooled classification and pooled/sentence rationale heads, native three-label mapping, threshold selection, ascending rationale sentence IDs, and release-default unforced rationale decoding.

The checkpoint route uses a single open handle, checks length and SHA-256, statically inventories unsafe globals, permits only the explicitly named `argparse.Namespace` when needed, and calls `torch.load(..., weights_only=True, map_location='cpu')`. It rehashes the same handle after load and has no unrestricted fallback. Retained metadata is recursively restricted to finite bounded primitives. Optimizer/trainer state is not returned for inference. Static global inspection is correctly supplemented by restricted loading; it is not claimed to certify arbitrary pickle safety.

Model state loading requires the exact key set, tensor shape and dtype, finite floating values, and the exact documented position-ID buffer before `strict=True`. The modern implementation does not silently discard unexpected keys or synthesize learned parameters. Reference execution retains the original inference function/class bodies and replaces framework initialization/training hooks; its limitations explicitly exclude historical binary reproduction.

The following qualification details were sent to the implementation agent before actual model execution:

- The initial threshold-equality test injects `predicted_rationales`; it therefore checks decode but does not exercise forward's `>=` boundary. A zero rationale logit, giving probability exactly 0.5, must exercise the actual forward selection path.
- The native formatter preserves every claim ID and produces empty evidence when no non-NEI pair is supplied. The eventual runner must verify every scheduled claim/document result or retain an operational failure. A missing pair computation cannot silently become a substantive empty-evidence prediction.
- The captured base configuration's vocabulary of 50,265 requires explicit reconciliation to the verified finalized tokenizer/checkpoint vocabulary of 50,275 before model construction. All learned tensor keys must still load strictly.
- Actual numerical parity must include more than 512 tokens and preferably a near-window-boundary input. Freeze tolerances and accepted prediction agreement before observing those results. Tiny random-weight parity alone does not qualify the released 24-layer checkpoint.

The standalone original-source controls in `source-controls-attempt01/CONTROLS.json` supply independent hand expectations for decoding and masks. They confirm that non-NEI documents with no selected rationale remain present, padded rationale positions are ignored, sentence output remains in original ascending order, NEI documents are omitted, `title=None` differs from `title=''`, and science-marker tokens are not automatically global. They do not execute a tokenizer backend, transformer forward pass or GPU.

No blocking design error was established by this static review. SC02 remains open pending actual acquisition integrity, runtime/weight loading, strict state coverage, the promised fictional controls and full-checkpoint reference/adapter parity. Follow-up source changes and executed output receipts require a later review; this note is not blanket approval of an unfinished runner.
