# Bounded data-to-policy integration review

Reviewed `experiments/scifact/tether_adapter.py` against the G1/G2 manifest API on
5 November 2026, before any real SciFact fit or prediction. This is a source review
of the integration boundary, not a full native-policy qualification.

The physical-container normalization and core `InputGraph` admission preserve the
original transport receipt and restrict the new proof to preparation. Logical
product authorization follows explicit product parents and exact permitted member/
field leaves. Split membership is separately identified as trusted preparation
control metadata. `build_context` first reconstructs preparation, then admits
corpus/query products for prediction and fit-only products for model provenance.
The full manifest/context remains supervisor-private; root confirmed that workers
will receive sanitized consumer recipes without reference counts, grouping or
reference-product paths.

One material gap was reported to the policy implementer and root before training:
the inspected `_validate_model` required fitting product names and claim IDs but
did not require hashes/lengths of the fitting and index input products actually
consumed. Names and IDs cannot distinguish two label/source versions sharing those
identities. The requested correction is a required per-product byte proof,
reconciled with the verified preparation manifest and the worker's fitting recipe;
index ancestry must also bind its exact corpus bytes. A preparation-manifest hash
can additionally bind projection authority but does not replace the input byte
records. A failing regression and successful correction belong to the policy
qualification, not this review note. This note does not claim that the gap remains
after subsequent policy edits.

No G1/G2 source, completed preparation, runtime or frozen BG02 artifact was changed
by this review. Current data anchor remains
`cb32f1384c49b66b912a62120abd7137a8a19b303f3ad052f035f21779c131f8`.
