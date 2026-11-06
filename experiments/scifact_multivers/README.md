# Native SciFact MultiVerS producer

This isolated experimental producer ports the complete released MultiVerS model:
one claim and full abstract jointly feed a Longformer-large encoder, label head
and sentence-rationale head. It does not upgrade the core T6 or specialist
backend. Solver-condition utility and provenance-check effects must be reported
separately.

`runtime.load_components` requires the SHA256 of a completed acquisition receipt,
validates the pinned tokenizer/config assets, and restricts checkpoint loading to
`weights_only=True` with at most the explicit `argparse.Namespace` allowlist.
Every learned tensor loads strictly; the former position-ID buffer is explicitly
retained and validated. No network lookup, unrestricted pickle fallback,
truncation, or inference-time tuning occurs.

`LoadedSolver` in `inference.py` keeps the model resident. Callers supply only
sanitized `id`, `claim`, `doc_ids` fields plus the corpus. It preserves the frozen
document order and released `force_rationale=false` behavior. Completed pair
events include full predicted labels, rationale indices and probabilities;
exceptions emit `pair_failed` and propagate. The outer controller must record
unexecuted schedule entries and hard timeouts, and must not format them as NEI.
One claim/five documents per call permits durable per-claim candidate commits.
The controller owns candidate fingerprints, input/source isolation, journals,
paired raw/check policy checks, and the fixed 300-claim development schedule.

`qualify.py` runs only the predeclared fictional controls. It records all token
IDs/masks, offsets, both models' logits/probabilities and decodes, timing and
memory. Full-architecture numerical agreement is against hash-pinned archived
source under modern PyTorch; it is not historical binary parity with torch 1.7.1
or tokenizers 0.9.4. Observed correctness on invented claims is diagnostic and is
never used to select cases or pass the architecture gate.

The runtime is an isolated Python 3.11/torch 2.7.1+cu128/Transformers 4.57.1
environment. Its wheel lock and 8,571,393,927-byte acquisition manifest reside in
`planning/review-assets/tether-semantic-20261106/solver-feasibility/`. Retained
upstream code and license receipts are in the same preparation directory.
Do not infer qualification or benchmark success from the presence of this code;
accepted execution receipts are required.
