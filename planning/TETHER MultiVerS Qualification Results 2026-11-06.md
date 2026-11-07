# MultiVerS qualification: SC02 complete

The released **MultiVerS fever_sci** model is qualified for the next SciFact
experiment on this workstation. This is a fictional-input implementation and
resource qualification, **not a SciFact performance result or a production T6
upgrade**. SC03–SC09 remain incomplete.

## What passed

| Requirement | Retained evidence |
|---|---|
| Exact public assets and isolated installation | 30 receipt-bound assets, 8,571,393,927 bytes; offline installation of 25 pinned packages. |
| Restricted checkpoint loading | `weights_only=True`, complete 544-tensor state admission; 437,763,076 learned parameters. No unrestricted pickle or Lightning import. |
| Full-context numerical parity | Eight adapter/reference forward pairs agree on captured logits, probabilities and released decoding; observed maximum absolute differences are zero. Includes 700- and 4,080-token examples. |
| Length boundary | A 4,100-token fictional input is rejected before model dispatch. No silent truncation. |
| Semantic diagnostics | All eight fictional expected labels match, including support, contradiction, unrelated evidence and claim negation. These were retained diagnostics, not the parity pass criterion. |
| Component and failure controls | 24 component tests pass without skips; 13 supervisor controls cover deadlines, interruption and incomplete execution accounting. |
| Independent reconstruction | Separate stdlib reader reconstructs captured masks, offsets, scores, decoding and all nine dispositions without importing the model. |
| Root acceptance | 421 assertions pass; 228 distinct files checked or inventoried, including all 30 freshly hashed payloads, 81 frozen runtime/source pins, failed attempt and preserved prior code. |

The source-level comparison executes the archived implementation's mathematics
under the same modern runtime as the adapter. It does **not** reproduce historical
PyTorch/tokenizers binaries. The separate reader checks captured token IDs and
mask/offset rules; it does not independently retokenize source text. Selected
runtime files and installation authorities are pinned, not the complete host.

## Checkpoint correction and retained failed attempt

The first full qualification stopped before inference because the legacy archive
contains two training-only global identifiers. Its nine cases remain explicitly
unexecuted. The old adapter and freeze helper were copied before editing, and the
failed launch, stderr, events and outcome remain unchanged.

A static `pickletools` inspection found `ModelCheckpoint` used as a callbacks
dictionary key and `_gpus_arg_default` as the unused `tpu_cores` training default.
Neither identifier has later memo references. The amended restricted loader maps
only these two exact identifiers to inert local markers that raise if invoked or
constructed. It records the unused default as null with its original identifier
and reason. Unknown globals and markers in inference parameters remain rejected.
`argparse.Namespace` remains an explicit existing allowance. No training callable
is executed and no Lightning code is imported.

The new regression first failed on the missing explicit policy argument, then
passed after implementation. Controls reject callable invocation, object
construction and a marker substituted for an inference parameter. The second
full qualification used a fresh frozen manifest and output directory; no failed
output was overwritten and no uncertain call was automatically repeated.

## Measured resources

FP32, batch one, eager attention, TF32 disabled; NVIDIA RTX 5070 Ti. Runtime:
Python 3.11.15, torch 2.7.1+cu128, transformers 4.57.1, tokenizers 0.22.1.

| Measurement | Observed |
|---|---:|
| Model-loading interval reported by qualifier | 10.709 seconds |
| Qualifier wall time | 16.218 seconds |
| Supervisor child phase, including startup | 23.969 seconds |
| Process CPU time reported by qualifier | 18.547 seconds |
| Peak process working set | 7,691,403,264 bytes |
| Maximum observed CUDA allocation | 4,182,130,688 bytes |
| Maximum observed CUDA reservation | 4,479,516,672 bytes |
| Provider spending | $0 |

CUDA observations include both resident models used for parity. Per-case peaks
are reset before inference, so these are observed forward-pass peaks, not a
complete device-wide peak trace. The model-loading interval excludes subsequent
reference construction and device transfer; process wall measurements have
different scopes as labelled. These controls establish local feasibility, not
the duration or peak usage of the full benchmark.

## Exposure, rights and scientific limits

The selected checkpoint precedes SciFact fine-tuning. The released SciFact-trained
checkpoint is excluded from the primary route because its reported 1,109 training
examples match 809 train plus 300 dev; exact per-ID training membership has not
been verified. This choice does not establish absence of pretraining or
model-development exposure. Source and rights details remain in the
[pre-acquisition review](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-semantic-20261106/solver-feasibility/MultiVerS-feasibility.md).
No explicit checkpoint-specific redistribution license was located; locally
acquired weights are excluded from Git and release bundles.

No fit, tuning, calibration or development predictions were made in this
qualification. Expected labels on invented examples are not biomedical accuracy.
The stronger solver has different supervision from the previous sparse baseline;
SC03 must report a solver-condition comparison, not an isolated architecture
effect or a benefit caused by provenance checking.

## Evidence and reproduction

- [Root acceptance](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-semantic-20261106/sc02-acceptance-attempt01/ROOT-ACCEPTANCE.json): SHA-256 `bb21dfe9c08f01796457dcf634dcc9a9bc9082c9aec711e765d1b71b5a974ef4`.
- [Actual launch outcome](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-semantic-20261106/solver-qualification/actual-launch-attempt02/OUTCOME.json), [81-pin freeze](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-semantic-20261106/solver-qualification/full-freeze-attempt02/MANIFEST.json), and [independent parity review](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-semantic-20261106/methods/sc02/actual-parity-review-attempt01/PARITY-REVIEW.json).
- [24-test result](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-semantic-20261106/solver-qualification/metadata-regression-green01/TEST-SUMMARY.json), [supervisor review](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-semantic-20261106/methods/sc02/SUPERVISOR-REVIEW.json), and [static metadata audit](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-semantic-20261106/solver-qualification/checkpoint-static-audit-attempt01/REPORT.json).
- Local captured inputs/tensors/outputs: `data/benchmark/scifact_multivers/qualification-20261106-attempt02/`; report SHA-256 `e54fd34919a6c965cbc54397d1b7c44ecadf837e1123cb226ecdc44ff1292374`.
- Acquisition receipt SHA-256 `a76d300564d0a5a4477a31cf167748e2e5b8540696b1c836d0fb8fab537b1610`; installation receipt SHA-256 `9291f74f724d8490c2eb0720c0baa341c1e4edea3b3c56910f5ebb826f496961`.

Recheck retained artifacts without model execution using `accept_sc02.py --output
<fresh-directory>` with the qualified stdlib Python. The input payloads and
isolated runtime must remain at their declared paths. The qualification manifest
retains the exact inference command; a new execution requires a fresh output and
prospective freeze, not overwriting this result.

Next: implement and freeze SC03 for all 300 claims with fixed retrieved top-five
documents, followed by separately labelled rationale-only, evidence-removal,
irrelevant-context and constructed-conflict diagnostics.
