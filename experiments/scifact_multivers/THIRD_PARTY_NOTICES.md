# Third-party code and checkpoint provenance

The MultiVerS model heads, tensorization, thresholds, decoding and archived
reference are adapted from David Wadden's `dwadden/multivers` revision
`a6ce033f0e17ae38c1f102eae1ee4ca213fbbe2e`, copyright 2022 David Wadden, MIT.
The complete notice is retained in `LICENSE.multivers`.

The archived Longformer implementation comes from Hugging Face Transformers
4.2.2, copyright 2020 The Allen Institute for AI team and The HuggingFace Inc.
team, Apache-2.0. The complete license is retained in `LICENSE.transformers`.
The installed Longformer implementation is pinned separately to Transformers
4.57.1. This adaptation changes runtime/framework integration and preserves
the original inference mathematics for numerical comparison.

Reference checks require a separately supplied upstream source bundle with
`source-receipt.json` and `source-reference-addendum.json` binding its files.
`reference.py` verifies both receipts and every source before extracting code.
The bundle is not included in the current public source tree.

The public fever_sci checkpoint is distributed by the MultiVerS authors at a
version-pinned S3 URL. A checkpoint-specific license was not found; this package
does not relicense or redistribute those weights. Acquisition and local use are
recorded separately by the experiment controller.
