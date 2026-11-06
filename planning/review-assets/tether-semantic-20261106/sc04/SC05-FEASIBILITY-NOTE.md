# SC05 forward feasibility - not activation or an execution freeze

Prepared on 6 November 2026 while SC04 remains active. This is documentation-only,
read-only preparation allowed by the current execution plan. It does not start
SC05, approve a final protocol, change any frozen experiment, or claim that the
scientific prerequisites below have passed. SC04 must complete first.

## Recommendation recorded before SC04 answers

Use the **SC04 L/O lexical-source, lexical-selection arm** as the future first-pass
baseline, independently of which arm obtains the best SC04 score. At
`2026-11-06T21:59:22.518300+00:00`, the path
`D:\Projects\drug_target_agents\data\benchmark\litqa_comparison\primary-production-20261106-attempt01\answer`
did not exist. This establishes that the recommendation was recorded before that
run's answer directory appeared. It is a filesystem observation, not process
attestation or proof of global non-use. No SC04 production predictions were scored
for this recommendation. Historical public-development results remain exposed.

Reusing L/O is conditional on the eventual complete, externally anchored,
source-inclusive SC04 acceptance. A partial run or files without acceptance are
insufficient. The recommendation does not select the eventual best-performing
SC04 arm after inspecting answers.

## Exact-plan interpretation

The [active plan](../../../TETHER%20Semantic%20Capability%20Execution%20Plan%202026-11-06.md)
requires all three comparisons: one pass, critique only and one bounded repair,
with complete schedules, matched total caps, repaired/damaged-answer accounting,
preserved raw evidence and evidence dependence. Its scientific contract explicitly
reserves the 69 SciFact calibration claims for a separately verified calibration
route. It prohibits using the 199 LitQA2 evaluation answers to fit their own
thresholds. Until another eligible LitQA2 calibration source is qualified, fixed
settings or descriptive curves are permitted there without calibrated-risk claims.

The faithful design therefore has two distinct components:

1. Full 199-question LitQA2 critique and bounded retrieval/answer repair.
2. Calibration and selective prediction on SciFact using the existing reserved
   split and the same actual SC03 model, subject to eligibility checks.

SciFact calibration must not be described as calibrating LitQA2 or a drug-target
clinical probability. The absence of an eligible local LitQA2 calibration source
does not itself block the separate route already allowed by the plan.

## Proposed LitQA2 design

| Condition | Operation | Maximum logical generations per question |
|---|---|---:|
| One pass | Reuse the accepted L/O original answer and original sources | 1 |
| Critique only | Review that answer against its sources; retain or withhold it | 2 |
| One bounded repair | Same critique, at most one refinement retrieval cycle, then one revised answer | 3 |

Preserve all 199 native IDs and option orders. Use the same pinned Qwen model and
generation configuration. No reference answer, annotated paper identity or key
passage enters critique, retrieval or repair.

The critic should return a bounded structured support disposition, source IDs,
short criticism and at most two safe literal query-term lists. Critique-only must
preserve the original candidate: withholding is a separate semantic-selection
abstention, not a provenance failure or a fabricated native unsure response.
Critic confidence is not ground truth or a calibrated probability.

The repair arm can make one additional public metadata/XML retrieval cycle under
the existing rights and receipt rules. A frozen merge, deduplication and selection
policy combines original and new raw passages. Keep original text, criticism,
summaries, source offsets and all prior candidates separately. Generate one revised
answer for every scheduled case unless its explicit capacity/failure policy
prevents dispatch. Do not selectively repair examples using their reference labels.

Suggested common caps, to qualify and freeze after SC04:

- Three generations / 768 generated tokens per primary condition, 256 per call;
  no dummy calls consume unused allowance.
- Existing 16,384-token context,14,000-byte prompt and 120-second call deadline.
- Baseline plus at most one refinement cycle:four metadata requests and six
  article attempts per question, with 16 MiB aggregate response allowance.
- Candidate pool 16 raw chunks/10,000 bytes; selected context eight chunks/8,000
  bytes. Preserve excluded data and cap-related missingness in accounting.
- At most 398 new primary generations when all 199 baseline calls are reused.
  At most 995 new HTTP attempts cover the refinement cycle.
- Add a separately labelled full 199 final-repair evidence-removal diagnostic:
  total at most 597 new generations / 152,832 generated tokens including this
  diagnostic, plus the 199 previously executed baseline generations. If prior
  candidate/critique remain visible, the diagnostic measures raw-source dependence
  conditional on generated content, not complete removal of all evidence.

Shared baseline and critique calls need both logical attribution and distinct
physical accounting. Do not sum logical arm totals and call that physical cost.
Prompt capacity and wall budgets require actual invented-input qualification.
The critic and repair prompts are new instruments, not already qualified by SC04.

Use a new contemporary availability cutoff after refinement collection. Preserve
the declared publication cutoff and actual acquisition times; newly captured
information must not be backdated to the original SC04 execution cutoff.

Retain repaired errors, damaged correct answers, persistent errors, abstentions,
false withholding, substantive precision/coverage, correct-and-admitted yield,
source changes, fallback counts and resource differences. Keep the original
publication-component pairing and full 199 denominators. A critique-only filter
cannot create a correct answer that was absent from its first-pass candidates.

## SciFact calibration eligibility and implementation

The local preparation contains 69 calibration claims in 49 source/text-connected
groups, with group sizes from 1 to 4. Calibration query/reference products and the
corpus total 8,136,615 bytes. Their permissions authorize `calibrate`, not ordinary
`predict`. Existing controller code distinguishes tune from predict, so a new
purpose-aware calibration controller is required; bypassing the grant is not a fix.

The actual SC03 solver is **MultiVerS fever_sci**, not Qwen and not the released
SciFact-finetuned checkpoint. SC03's primary recipe pins the acquisition receipt
below. The runtime requires the fever_sci object and its S3 version, while
`experiments/scifact_comparison/policy.py` records the pre-SciFact-finetuning route.
The archived author training documentation identifies fever_sci as stage-one
FEVER/PubMedQA/Evidence Inference training, before target-dataset fine-tuning.

This supports conditional use of the 69 locally reserved calibration claims with
the same SC03 solver. It does **not** establish global contamination freedom:
encoder/scientific-corpus overlap and inherited model-development exposure remain
unexcluded. A complete local fitting/tuning/non-use audit is still pending. Do not
silently substitute the weaker sparse baseline or call these claims untouched.

Proposed execution after that audit:

1. Reverify original products, source/text-group separation and all retained
   fitting/tuning input roles. Keep calibration references away from prediction.
2. Freeze a scalar confidence rule before examining calibration outcomes; for
   example, the minimum predicted-label probability across the five fixed retrieved
   documents. Explicitly acknowledge that it is an imperfect proxy for complete
   document/label/rationale correctness.
3. Execute all 69 queries using the same frozen retrieval method, checkpoint and
   decoding: up to 345 claim/document forward passes. Seal probabilities and outputs.
4. Fit a prespecified regularized one-dimensional calibration mapping to the
   explicitly declared native/strict correctness endpoint using only these 69
   labels. Fix fitting algorithm, regularization and convergence handling first.
5. Freeze calibration parameters, then apply them to the retained 300 SC03 primary
   predictions. No development-answer threshold tuning or new development
   inference is needed.
6. Report reliability/Brier measures, fixed selection cutoffs, correct/wrong
   acceptance and rejection, and coverage with source-group-aware uncertainty.

Only 49 calibration groups support uncertainty. A score of 0.9 does not establish
90% precision or a finite-sample risk guarantee. Poor calibration or a zero-coverage
operating point is a possible negative result, not permission to tune on the 300
development answers. Genuine full-cohort execution still precedes such a result;
an all-abstention shortcut cannot complete the experiment.

## Evidence observed in this read-only check

Workspace root for the relative paths below is exactly
`D:\Projects\drug_target_agents`. Small metadata/document files were freshly
hashed. The 5.25 GB checkpoint hash is the value in the freshly verified acquisition
receipt; the weight payload was not rehashed in this feasibility check.

| Artifact | Exact workspace-relative path | SHA-256 |
|---|---|---|
| Active plan | `planning/TETHER Semantic Capability Execution Plan 2026-11-06.md` | `085ed3bb65c995db134946ad16773e25196f36933a800b7dfa4772c9da9ebbb7` |
| SciFact preparation manifest | `data/benchmark/scifact/preparation-20261105-attempt03/manifest.json` | `cb32f1384c49b66b912a62120abd7137a8a19b303f3ad052f035f21779c131f8` |
| Calibration queries | `data/benchmark/scifact/preparation-20261105-attempt03/views/queries_calibration.jsonl` | `2ca8f334046a6397a87b25b2b33710ad2414726b573519135f2bbc6ec9c0d31b` |
| Calibration references | `data/benchmark/scifact/preparation-20261105-attempt03/restricted/references_calibration.jsonl` | `14f8978bd125830e8c1769cbdd4549737c6f23da097c55e8d50ab3139cf0f9d1` |
| Model acquisition receipt | `data/cache/tether-multivers-acquisition-20261106-attempt01/RECEIPT.json` | `a76d300564d0a5a4477a31cf167748e2e5b8540696b1c836d0fb8fab537b1610` |
| Recorded checkpoint payload | `data/cache/tether-multivers-acquisition-20261106-attempt01/checkpoint/fever_sci.ckpt` | `6b48f1b83eaedbc2570bc50135518ef3cf6f3c6dcdd380a9a3a433918e7f982d` |
| Archived author training document | `planning/review-assets/tether-semantic-20261106/solver-feasibility/source/doc/training.md` | `dfd60f500830e752fa93c1eb3f6cb2494e6789f3f77c65bb28d6009474661136` |
| SC03 actual primary recipe | `data/benchmark/scifact_comparison/production-20261106-attempt01/primary/recipe.json` | `1eb6785895ff628a27740235a7caf93fad0da7d96d42902a4d4c562ad07faa66` |

The recorded checkpoint has 5,253,768,950 bytes and version ID
`GYe58tFsyvvn1n7rib5H4wrsiq32ZY5Y`. The archived training document hash also matches
the SC02 `solver-qualification/full-freeze-attempt02/MANIFEST.json` pin.

## Unresolved gates

- SC04 complete execution and independent acceptance before baseline reuse.
- SciFact calibration non-use/role audit and source-preservation revalidation.
- New critique/repair prompts, exact budgets, failure policies, purpose grants,
  source merging and independent replay qualification.
- No separately eligible LitQA2 calibration source is established locally.
- Formal risk guarantees and absence of model-pretraining contamination are not
  established by the present evidence.

No new acquisition, inference, threshold fitting or calibration-label inspection
was performed for this note. No external expert or new credential is needed for
the proposed public/local routes. SC05 remains unstarted.
