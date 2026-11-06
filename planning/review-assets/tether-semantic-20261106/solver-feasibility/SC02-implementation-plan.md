# SC02 concrete implementation and qualification contract

This plan became implementation-authorized only after root accepted SC01 in
`decomposition/ROOT-ACCEPTANCE.json`, SHA256
`77160e9bf5e11b6464d0cc11ba1f46e5ac98cd31ba718618a2caad68ff80aad2`.
Acquisition and installation remain root-owned. This agent owns the new
`experiments/scifact_multivers/` implementation and fictional qualification.

## Runtime and assets

The candidate lock is Python 3.11.15, torch 2.7.1+cu128, Transformers 4.57.1,
tokenizers 0.22.1, safetensors 0.6.2, huggingface-hub 0.36.0 and their pinned
transitive dependencies. `dependency-lock.json` records the exact wheel URL,
size, SHA256, Python requirements, dependency metadata and license metadata for
all 25 wheels. All 31 active dependency edges were checked for CPython 3.11 on
Windows AMD64. This metadata check does not establish import or CUDA success.

The planned payload is exactly 8,571,393,927 bytes: 3,314,913,170 bytes of wheels,
5,253,768,950 bytes of version-pinned fever_sci weights, and 2,711,807 bytes of
tokenizer/config files. The acquisition manifest caps the aggregate at 9 GB.
The weights have no located published whole-file SHA256; transport establishes
their local SHA256 while verifying the pinned S3 version and length. The runtime
accepts only a root `PASS` receipt whose per-asset rows are `completed`.

The runtime needs no Lightning, AllenNLP, pandas, spaCy, scispaCy, datasets,
torchvision, base Longformer weight download, or independent science-pretraining
weight download. It constructs the encoder from the pinned config and loads all
released encoder/head tensors. This omission of redundant initialization weights
is valid only when strict state validation succeeds.

## Exact adapter and source comparison

`model.py` retains the complete 24-layer Longformer-large architecture and the
original learned key names. The three-way label head consumes the pooled state.
The rationale head consumes the concatenated pooled and sentence-EOS states.
Its GELU, dropout placement, sigmoid threshold with inclusive equality, label
threshold behavior, and native label mapping follow the author implementation.

Transformers 4.2.2 stored `encoder.embeddings.position_ids` as a persistent
buffer; current Transformers removed it. The adapter explicitly reinstates this
non-learned buffer, checks its exact arange values, and then uses strict loading.
No learned key can be missing, unexpected, shape-mismatched, dtype-mismatched or
non-finite. The base vocabulary of 50,265 becomes 50,275 after the ten ordinary
`add_tokens` additions in author order.

`data.py` constructs the tokenizer from captured verified bytes, preserving
claim/title/sentence concatenation with EOS separators. Global attention covers
BOS/EOS and every claim token before the first EOS; added science markers and
title content do not automatically get global attention. Sentence offsets
exclude claim/title EOS and padding. Input strings are not normalized. Empty
title and absent title remain distinct. Inputs above 4,096 tokens fail explicitly.

`checkpoint.py` hashes the opened checkpoint handle, scans unsafe globals, and
loads on CPU with `weights_only=True`. The sole possible added safe global is
`argparse.Namespace`; unsupported objects fail without unrestricted fallback.
Hyperparameters undergo bounded recursive primitive validation. Optimizer state
is dropped before GPU transfer, and the opened file is rehashed after loading.

`reference.py` verifies 20 retained upstream sources against two pinned receipts
and extracts their original mathematical functions/classes. It executes the
archived Transformers 4.2.2 encoder, original MultiVerS heads/forward/decode and
original mask helper under the modern torch runtime. Only initialization/loading
infrastructure, training framework hooks and documentation decorators are
substituted. For example, legacy masking uses -10000 while modern code uses
floating-point minimum; full numerical comparison must establish compatibility.
This is source-level parity, not historical binary parity with torch 1.7.1 or
tokenizers 0.9.4. The original tensorizer comparison shares the modern tokenizer
backend and does not independently prove old tokenizer binary equivalence.

## Frozen fictional qualification

`fictional-controls.json` SHA256 is
`65a697882396742b46589bfd96f1a18c3862583447f202560dea1d6a3a6ada2e`.
Eight invented cases cover support, contradiction, irrelevant evidence, claim
negation, 700-token context, 4,080-token context, absent title and empty title.
A ninth case must reject 4,100-token overflow. The length construction algorithm
is fixed before output inspection. Expected semantic labels are diagnostic, not
a selection or architecture-pass criterion. All outcomes remain in the report.

The runtime uses complete FP32 weights, batch one, inference/eval mode, workers
zero, eager attention and TF32 disabled. CUDA allocator fraction is capped at
the smaller of 90% or 14 GiB. Internal timers cap the process at 1,800 seconds and
each case at 120 seconds; root provides external process supervision. Unbuffered
events include monotonic timestamps for model-load and case boundaries.

Each case preserves exact token IDs, all masks, sentence offsets, both models'
logits/probabilities/indicators and both decodes before numerical assertions.
The tolerances are absolute 1e-5 and relative 1e-4; decoded labels and rationale
indicators must agree exactly. Model loading and both forward times, CPU time,
process peak working set and CUDA peak allocated/reserved memory are recorded.
Overflow also produces a result record. Root records hard failures and any
remaining unexecuted schedule entries; a failure is never reformatted as NEI.

## Later scientific execution boundary

`inference.LoadedSolver` keeps weights resident and accepts the frozen original
top-five document IDs, yielding the ordered 1,500 claim/document computations.
It rejects annotation-bearing query objects. Complete pair scheduling is checked
before native formatting; full pair results and failures are journal callbacks.
The controller owns claim candidate commits, source isolation, fingerprints,
paired raw/check policy decisions and the all-300 development schedule.

This remains a native SciFact experimental producer. It makes no claim that the
core T6 or specialist backend was upgraded, and checking does not create semantic
correctness. Extra scientific pretraining differs from the sparse baseline's
380-fit budget. Optional later fine-tuning may use the same 380 fit/82 tune split;
the 69 calibration and 300 dev annotations are excluded from SC02. No fine-tuning
or scientific development inference is required to pass this fictional
qualification, and neither has been authorized to run through this module yet.
