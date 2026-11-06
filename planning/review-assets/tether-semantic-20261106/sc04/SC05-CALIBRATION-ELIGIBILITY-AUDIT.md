# SC05 calibration eligibility: retained local evidence

Audit completed **6 November 2026, 22:14 UTC**. Scope: scientific prerequisites
and retained-file verification only. SC05 remains unstarted; SC04 acceptance is
still required before proceeding. No model inference, calibration fitting,
confidence calculation, outcome scoring, network access or source-code changes
were performed by this audit.

**Decision: the 69 locally reserved SciFact claims are conditionally eligible for
the proposed separate calibration route using the actual SC03 MultiVerS
`fever_sci` model.** Their supervised local use was reserved, and usable native
probabilities survive for the 300 development claims. They are not globally
untouched data. A purpose-aware controller and a prospectively fixed calibration
protocol are still required. No missing external file or credential was found.

## What was verified

The [retained audit program](sc05-calibration-audit01/audit.py) independently
reconstructed the preparation from its original archive, rather than accepting
partition names as proof. Its final run checked 10,900 proof entries covering
10,876 distinct file paths and completed in 9.657 seconds. All assertions passed.
The [summary and artifact anchors](sc05-calibration-audit01/SUMMARY.json) identify
the complete reports and file-proof inventory under ignored `data/cache/`.

| Requirement | Observed evidence | Judgment |
|---|---|---|
| Original data identity | Original tarball, download receipt, archive members, preparation manifest and projected products match their retained byte proofs | Passed |
| Split reconstruction | Original 809 training and 300 development claims reproduce the stored connected components and seeded allocation exactly | Passed |
| Local calibration reservation | 69 claims in 49 components; no shared claim IDs, normalized exact claim text or annotated document IDs with fit, tune, development or quarantined training partitions | Passed within the stated grouping rule |
| Original baseline fitting and tuning | 21 fit/predict/evaluation recipes and 3,423 retained I/O events; zero reads of the calibration query/reference products; fit uses 380 claims, tuning uses 82, development uses 300 | Supported by retained worker records |
| SC02 qualification | Both attempt directories preserve exactly the frozen fictional controls; the completed attempt has nine fictional inputs, with no normalized calibration-claim match | Supported; failed first attempt has no per-case input products |
| Actual SC03 execution | All five condition receipts and their files verify; every ordered input schedule is the original 300 development IDs with original claim text; no calibration claim is scheduled | Passed |
| Current execution identity | SC03 frame, condition freezes, current code/runtime pins, external-model manifest and each worker's acquisition-receipt binding verify | Passed |
| Actual model | Fresh streaming hash of all 5,253,768,950 bytes matches the retained `fever_sci` checkpoint and required S3 object version | Passed |
| Development confidence inputs | All 1,500 primary pair files retain three label probabilities and 13,000 sentence probabilities; finite values, ranges, normalization, dimensions and release-default decoding verify | Passed; no new development inference required for a function of these retained values |
| Calibration-role authority | Calibration queries and references permit `calibrate` and `preparation_audit`; they do not permit `fit`, `tune` or `predict` | Separate controller required |

## What “reserved” means here

The original split joins claims sharing an annotated/cited document identity or
identical normalized claim text, using NFKC normalization, case folding and
whitespace normalization. Any component connected to the original development
set excludes its training members from fit/tune/calibration. The remaining
components are assigned by the fixed seed and the stored 70%/85% boundaries.
The independent reconstruction reproduced all partitions:

| Partition | Claims |
|---|---:|
| Fit | 380 |
| Tune | 82 |
| Calibration | 69 |
| Original development | 300 |
| Quarantined training | 278 |

The calibration partition contains 52 distinct annotated/cited document IDs.
Its 49 groups comprise 32 singletons, 15 groups of two, one group of three and one
group of four. These are the available grouping units for uncertainty, not 69
independent observations. This rule does not detect every paraphrase or duplicate
article registered under a different document ID, nor establish independence
against unknown external training corpora.

**The corpus was shared.** All 5,183 public abstracts were available to the
original sparse baseline and its retrieval index. In every SC03 condition, six
of the 52 calibration-annotated document identities appeared among inputs to six
development claims. Those six documents connect to seven calibration claims.
They were not accompanied by those calibration claims or their labels in the
SC03 worker inputs. Primary SC03 used the original document texts; transformed
conditions are reported here by document identity, without claiming every
transformed document preserves the same text.

Consequently, “locally reserved claim/label use” is supported; “no source text was
ever exposed” is false. Do not silently remove these seven claims to improve an
unseen-data claim or denominator. Any additional exposure-stratified sensitivity
analysis would need a declared role and protocol before outcome analysis.

Preparation necessarily read the public supervised archive to produce split and
reference products. This provenance audit also read the original supervised
containers and reference projections to compare their bytes and source IDs. It
did not use label values or correctness to choose a method, threshold or sample.
The appropriate statement is **no retained local fitting/tuning of these
calibration claims**, not that no process has ever opened their references.

The baseline worker I/O records support absence of calibration-product reads
within those recorded workers. SC03 instead has bounded recipes, source pins and
retained input/dispatch events; it does not provide independent operating-system
attestation against arbitrary hidden reads. These records cannot establish
global non-use outside the retained execution.

## Correct model and probability reuse

All five SC03 recipes bind the same acquisition receipt, with checkpoint:

- Object: `fever_sci.ckpt`; S3 version `GYe58tFsyvvn1n7rib5H4wrsiq32ZY5Y`.
- SHA-256: `6b48f1b83eaedbc2570bc50135518ef3cf6f3c6dcdd380a9a3a433918e7f982d`.
- Configuration: float32, no forced rationale, 4,096-token maximum, retained
  baseline top-five retrieval, label argmax in `CONTRADICT, NEI, SUPPORT` order,
  sentence threshold 0.5.

The pinned [author training documentation](../solver-feasibility/source/doc/training.md)
identifies this checkpoint as stage-one FEVER/PubMedQA/Evidence Inference training,
before target-specific SciFact fine-tuning. That supports the intended
pre-SciFact-fine-tuning route. Encoder training, weak-supervision source overlap,
public benchmark exposure and model-development contamination remain unexcluded.
This audit neither substitutes the fitted sparse baseline nor approves the
released SciFact-fine-tuned checkpoint.

All 1,500 primary claim/document files contain the probability arrays required
to reconstruct a prospectively declared confidence rule. The audit checked
finite `[0,1]` values, three-class normalization, sentence counts against the
original request, and agreement of argmax/0.5 decoding with retained predictions.
It did not compute scalar confidence, reliability, new correctness labels or
calibration scores. Thus no argmax-only surrogate and no repeat 300-case forward
pass is needed for a confidence function limited to these preserved arrays.
Calibration outputs are absent from the examined runs; the 69-case route still
requires its own inference, potentially 345 claim/document forward passes.

## Conditions to freeze before calibration outcomes are used

1. **Finish SC04 and retain independent acceptance.** This audit is permission to
   prepare the separate scientific route, not an activation or a substitute for
   SC04 completion.
2. **Freeze the model and retrieval identity.** Reuse the verified checkpoint,
   original retrieval implementation/model and fixed top-five policy. Do not
   fit a different predictor on the reserved set or choose a new checkpoint from
   its outcomes.
3. **Add a controller that authorizes `calibrate`.** The old
   `experiments/scifact/run.py` maps every non-tune prediction request to `predict`.
   Passing calibration through that route would violate its product grants.
   The inference worker may receive calibration queries and the corpus; it must
   not receive calibration references. After sealed inference, a separate
   calibrator may receive references with the `calibrate` role.
4. **Fix one scalar and one endpoint before fitting.** The feasibility note's
   minimum predicted-label probability across five documents is an available
   proxy, not an approved probability of complete claim correctness. It includes
   NEI distractors and does not directly certify retrieval or rationale quality.
   Fix ties, missing pairs, capacity failures and abstentions explicitly. If the
   endpoint follows existing strict correctness, state that it requires the
   exact evidence-document set, correct labels and at least one complete gold
   rationale within the native sentence cap, with successful production and
   admission. This is a claim-level supplemental endpoint, not just label accuracy
   or the native aggregate F1 score.
5. **Fix fitting and reporting rules before label-based selection.** Specify the
   one-dimensional mapping, regularization, optimizer, convergence/failure
   handling, probability clipping and any fixed cutoffs. Preserve all 69 IDs and
   their 49 groups; unavailable executions remain explicit. No fitting choices
   should be selected using the 300 development answers or the 199 LitQA2 answers.
6. **Seal parameters before applying them to development.** Reuse the verified
   SC03 probability arrays and retain raw and calibrated confidence separately.
   Report operational missingness, selection coverage and correctness with group-
   aware uncertainty. Only fitted/calibrated estimates supported by those data
   may be claimed; 49 calibration groups do not establish a formal risk guarantee.

This SciFact route does not calibrate LitQA2, clinical success probabilities, or
general drug-target judgments. No eligible separate LitQA2 calibration source was
established in this audit.

## Reproducibility and limits

Final report: `data/cache/sc05-calibration-eligibility-audit-20261106T221428265016Z/REPORT.json`,
SHA-256 `513069c5801fe1540812d517871a86f66fcd57066c815c2c867a7c995b208cf6`.
Full file inventory: adjacent `PROOFS.json`, SHA-256
`9ef9553a317b24a9f7276934c45da92a1a59ad82aa4e47ea1f8929077deabed9`.
The earlier narrower audit output is preserved in its original timestamped cache
directory. The final run added explicit SC03 current-code/frame binding and
release-decode checks; no retained original was rewritten.

Reproduction from the repository root:

```powershell
& data/cache/tether-scifact-env-attempt02/environment/Scripts/python.exe -I -B planning/review-assets/tether-semantic-20261106/sc04/sc05-calibration-audit01/audit.py
```

The audit creates a fresh ignored output directory, has a 285-second watchdog,
and retains a terminal failure record on assertion/error. It uses local stdlib
file operations only. Two audit executions passed; the final assertion set is
the authoritative result above. There were zero model calls and $0 provider
spending. Filesystem consistency and local provenance are supported; scientific
generalization and global contamination freedom remain unproven.
