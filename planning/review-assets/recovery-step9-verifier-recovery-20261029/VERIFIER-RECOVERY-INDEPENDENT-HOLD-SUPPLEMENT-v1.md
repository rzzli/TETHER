# Verifier v1: scoped hold after limited peer review

The earlier limited source/pure review remains preserved. Before acceptance, root identified a further ownership defect: `hash_files` treats a malformed open return or null typed return as an owned lease and can later close it. Only an explicit owned-success return may transfer a nonnull handle; known no-handle failure and unknown return need separate outcomes.

The reviewer also confirmed that the three post-reservation authority/file/checker factories lack prior durable stage-attempt records. Reuse the existing bounded stage machinery under the original clock; do not add a real bootstrap or adapter.

The [machine supplement](VERIFIER-RECOVERY-INDEPENDENT-HOLD-SUPPLEMENT-v1.json) binds exact source and earlier evidence. The original fixes remain valid, but source/pure acceptance is held for these narrow corrections and their synthetic regressions. No reviewed helper, test, old original, payload, SDK, compiler or native operation ran during this review.
