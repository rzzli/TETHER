# SC02 independent parity and exposure controls

6 November 2026, pre-execution methods specification. This review is based on the retained original MultiVerS source at `a6ce033f0e17ae38c1f102eae1ee4ca213fbbe2e`, the retained Transformers 4.2.2 and 4.57.1 Longformer sources, and the local proposed acquisition/dependency manifests. It does not qualify a model merely because the assets are available or an import succeeds.

## Primary route and interpretation

The intended `fever_sci` release is the full-context joint architecture before documented SciFact target fine-tuning. Its documented prior tasks are FEVER, PubMedQA and Evidence Inference. The target-trained `scifact` release is excluded from the primary public-dev comparison: published training count 1,109 matches 809 public train plus 300 public dev, but exact checkpoint training IDs remain unverified. `fever_sci` is not globally contamination-free: shared scientific pretraining and prior method/model-selection exposure remain possible.

This architecture jointly encodes the claim, title and one full abstract. It is not a multi-paper full-text solver. The prospective matched-retrieval condition preserves all original five retrieved documents per claim and all 300 claims. External pretraining changes supervision relative to the sparse baseline. Any fitting or threshold selection uses the declared fit/tune partitions, never the exposed 300 dev references.

## Exact source behavior to preserve

`data.py` builds `claim + EOS + title + EOS + sentence_0 + EOS + ...`, with the tokenizer's outer BOS/EOS. With no title, one fewer prefix EOS is skipped. The original non-RoBERTa path does not truncate. Titles and all original abstract sentences remain present and in order; sentence IDs refer to their original zero-based positions.

The ten science markers are added with `tokenizer.add_tokens` in this order: `<|sec|>`, `</|sec|>`, `<|sec-title|>`, `</|sec-title|>`, `<|abs|>`, `</|abs|>`, `<|title|>`, `</|title|>`, `<|sent|>`, `<|par|>`. They are ordinary added tokens, not a new `additional_special_tokens` list. Global attention is true at BOS/EOS and at positions strictly before the first EOS; title tokens and science markers do not gain global attention merely by category. Padding uses the tokenizer pad token, zero ordinary attention and zero global attention. Padded sentence offsets are zero and never eligible rationale sentences.

The label head uses the encoder pooler output. The rationale head concatenates pooled output first and selected sentence hidden state second. Each head has linear/GELU/dropout then linear/identity. Eval mode disables all dropout. Label mapping is `0=CONTRADICT`, `1=NEI`, `2=SUPPORT`. Without a label threshold, use argmax; with a retained explicit threshold, follow the original NEI-score replacement rule. Rationale selection uses `sigmoid(logit) >= threshold`, default 0.5 only when the checkpoint has no threshold field.

The release-default condition is `force_rationale=false`, with `no_nei=false`. A non-NEI document with no above-threshold sentences remains a selected document with an empty sentence list. Do not suppress the document or force a top sentence. Native formatting omits predicted NEI documents. Empty evidence from all-NEI document predictions is substantive only when the claim execution succeeds.

Rationale indices come from indicator `nonzero()` and therefore follow original sentence order, not descending rationale score. This matters because the native abstract score and strict supplement only inspect the allowed prefix. There is no extra inference-time native gold-derived rationale cap. The official cap belongs to scoring, not predictor input.

## Independent control matrix

| Control | Required positive observation | Negative or boundary observation |
|---|---|---|
| Asset identity | Exact checkpoint length, version ID and computed local SHA-256; tokenizer/config hashes and pinned revision/blob identity | Wrong bytes/version/revision or redirected unapproved host stops before loading |
| Token additions | Exact strings, order, IDs and final embedding-compatible vocabulary | Reordered/omitted tokens or special-token registration mismatch is detected |
| Tensorizer | Original-source and adapter token IDs, attention masks and sentence offsets are identical on short/long fictional text | Absent title, empty-string title, punctuation, whitespace, Unicode and literal reserved-token content cannot silently shift sentence IDs |
| Full context | A >512-token input retains all sentences and final-sentence offsets | 4096 boundary counts include BOS/EOS; 4097+ tokens yield an explicit declared failure before model dispatch, not truncation or sentence dropping |
| Global attention | Original-source mask agrees at every position, including a long sequence and title | Claim-only, all-token-global and padding-global mutations are distinguishable controls; science marker presence alone gives no global bit |
| Sentence masking | Valid offsets gather the same sentence states; padded zero offsets are excluded | A high rationale score at padded position never produces a native sentence ID |
| Head mathematics | Same captured hidden/pooler tensors produce matching original and adapter logits | Swapped pooled/sentence concatenation or wrong head label order is caught |
| Native decode | All three label IDs map correctly, threshold equality is included, selected IDs stay ascending | Empty rationale for SUPPORT/CONTRADICT remains empty at force=false; NEI evidence is omitted; a malformed/out-of-range sentence ID fails validation |
| Model tensors | All learned encoder and head keys/shapes/dtypes are checked and loaded strictly; tensors are finite | Missing, unexpected, wrong-shape or nonfinite learned tensors stop; no broad `strict=False` fallback |
| Legacy buffer | If needed, only the documented position-ID buffer is reconciled after checking its exact expected arange/shape | Arbitrary key stripping or synthesizing learned weights is disallowed |
| Restricted checkpoint load | Static global scan plus explicit `weights_only=True`, CPU mapping and narrow audited primitive namespace allowance | Unknown globals, unsupported dynamic objects and loader exceptions stop; never retry with unrestricted pickle |
| Runtime | Actual qualified CUDA eager FP32 batch-one inference has finite outputs and retained RAM/VRAM/timing | OOM, timeout, unsupported kernel or nonfinite result is a retained failure; import success is insufficient |
| Numerical parity | Retained 4.2.2 reference source and modern adapter use identical tensors/inputs and meet a prospectively frozen tolerance | Record per-output max absolute/relative differences and label/rationale agreement; do not loosen tolerance after seeing results |
| Repeatability | Repeated evaluation on the same fictional input under frozen flags yields declared numerical agreement | Training mode, stochastic dropout, online downloads and undocumented mixed precision are detectable |

Pure decoding/masking controls may use injected fictional logits and exact hand expectations. Actual model behavior on invented positive, negative, irrelevant and conflicting contexts is reported separately: disagreement with an expected semantic label is a scientific weakness to retain, not permission to replace an input until the model looks correct. These controls must never use dev gold to tune the route.

The actual legacy/new numerical comparison needs both short and >512-token inputs, and preferably a near-window-boundary example within declared resource limits. It should retain label logits, rationale logits/probabilities, decoded outputs, exact tokens/masks/offsets, model/asset/source hashes, runtime flags and resource observations. No duplicate heavy GPU run is required from this reviewer; a frozen primary run can supply the captured artifacts for independent analysis.

## Pickle and compatibility boundaries

A static global scan is not a proof that arbitrary pickle is safe. Its role is inventory; the restricted loader remains mandatory. If `argparse.Namespace` is explicitly needed, allow only that identified class and recursively validate retained hyperparameters as bounded primitive data. Optimizer/trainer state does not move to GPU or become an inference parent. A failed restricted load is preserved and investigated without switching to `weights_only=False`.

The original source constructor would download other weights and use unrestricted `torch.load`. The adapter must instantiate from captured local config and load the complete released encoder/head state, after proving that state is present. Original-source parity shims may bypass training/logging/dependency infrastructure and network initialization, but may not change attention, embeddings, pooler, head math or decode behavior. Record every shim.

Transformers 4.2.2 source executed under modern torch is a source-level numerical reference, not historical binary/environment reproduction. Original `data.py` run with the same modern tokenizer backend verifies tensorizer logic; it does not independently establish tokenizers 0.9.4 historical equivalence. State the tested boundary. All inference assets remain local-only with no remote-code trust or online fallback.

## Gate status

The inspected acquisition lock has explicit byte ceilings, hashes for wheels, version/revision constraints for the checkpoint and tokenizer, a fresh-attempt requirement and no global installation route. These are appropriate preconditions, not evidence of acquired payload integrity or runtime compatibility. SC02 remains incomplete until actual payload verification, restricted loading, strict tensor coverage, fictional controls, numerical/source parity and resource probes are retained and accepted. A valid but semantically weak model measurement does not erase later authorized stages.
