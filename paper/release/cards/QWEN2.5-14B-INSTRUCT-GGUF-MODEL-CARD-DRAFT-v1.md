# Qwen2.5-14B-Instruct-GGUF development model card

Status: DRAFT; **metadata/card only, no model weights or inference runtime bundled**. Official pages accessed 2026-11-01. This review performed no inference and acquired no model bytes.

## Retained identity and role

The closed P04/P04b development branch used `Qwen/Qwen2.5-14B-Instruct-GGUF`, Q4_K_M, revision `b466e1f8c07172155743e8e1307507d8a4f91fbd`, with three shard hashes retained by the frozen development protocol. This card identifies the historical dependency; it does not authorize restarting that branch. P05's evaluated native arms are deterministic and make no model calls. Negative development probes are not evidence of model, biological or clinical superiority.

The [official revision tree](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF/tree/b466e1f8c07172155743e8e1307507d8a4f91fbd) exists, and its [commit page](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF/commit/b466e1f8c07172155743e8e1307507d8a4f91fbd) displays 2024-09-20. The repository's total size spans other quantizations; it is not the selected local model's size.

## Official licence evidence

The [revision-pinned README metadata](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF/blob/b466e1f8c07172155743e8e1307507d8a4f91fbd/README.md) declares Apache-2.0 and links its repository licence. The [current official GGUF LICENSE](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct-GGUF/blob/main/LICENSE) contains Apache License 2.0 and an Alibaba Cloud 2024 copyright notice. However, exact-revision LICENSE blob/raw/resolve requests were unavailable to the review tool. The exact tree lists LICENSE, but this review did not byte-compare its historical contents with current main. This limited gap is retained rather than replaced by an assertion of a verified historical licence file.

This finding is specific to this official 14B Instruct GGUF repository. It does not classify every Qwen model, certify training-data rights, or establish a licence for linked upstream datasets. The separate inference runtime's source and binary licences require their own inventory if distributed.

## Release disposition

Include this project-authored card, official revision/quantization identifiers, relevant protocol metadata and reviewed shard hashes if allowlisted. Exclude all `.gguf`, safetensors, tokenizer/model payloads, model caches and inference executables. Refer recipients to the official provider if a separately authorized development reproduction needs them; do not implement an automatic download or model run in the P05 reproduction path.

A future weight redistribution decision would need the exact applicable licence/notices and a separate explicit allowlist. The Apache label is not a reason to add weight files to this release. Evidence and failed retrieval URLs are in `planning/review-assets/preprint-p09-20261101/RIGHTS-SOURCE-AUDIT-v1.md`.
