# Independent project review

**Review date:** 26 October 2026 UTC / 25 October Los Angeles. **Baseline:** `cc0042c5e8a83d86c8718a2e2a6762fc24a26390`. **Reviewer:** Codex, with separate engineering, scientific-feasibility and review-instrument audits. These are AI reviews, not independent human scientific validation.

**Conclusion:** AsOf has a useful, technically tested provenance framework and substantial development evidence. It has not demonstrated clinical prediction, causal genetics or superior scientific dossier quality. The next phase should test whether source-grounded interpretation is useful on a bounded contemporary development set, with independent human references. Another elaborate repair of the exposed IL6R pilot should not be the automatic next task.

The [detailed recovery plan](../planning/Project%20Recovery%20and%20Evaluation%20Plan%202026-10-26.md) orders the work. The [expert recruitment brief](expert-review-20261026/Recruitment.md) and [blank expert exercise](expert-review-20261026/Expert-review.html) separate the immediate human requirement from engineering work.

## 1. What this review did

I read the complete [Opus review](Opus_20261026T050236Z_review.md), compared its proposed P0–P6 sequence with the original H1–H6 proposal and subsequent feasibility decisions, inspected the core admission/execution/verification path, and commissioned independent read-only audits of correctness and scientific design. I inspected the catalog, canonical run registry, retained validation/accounting/failed-pilot reports, current review tools, CI configuration, packaging and documentation organization.

This is a repository-wide review by component and dependency, supplemented by targeted executable checks. It is not a claim that every line or every raw data row has been independently inspected. Clinical outcome payloads were hashed without reading their contents. No model call, new data download, paid query, Git push, automatic monitor or download-worker change was made.

Evidence is separated below:

- **Fresh check:** executed during this review, including synthetic reproductions and repository inventory.
- **Retained evidence:** prior report inspected and, where stated, checked against current byte hashes.
- **Recommendation:** a design judgment or proposed change, not an observed result.

### Audit coverage

| Component | Coverage and result | Limit |
|---|---|---|
| Production framework | All 21 tracked Python modules inventoried and parsed; targeted review of contracts, chronology, retrieval, local transport, workflow, artifact verification and packaging | Static inventory does not prove correctness |
| Research utilities | All 97 tracked Python modules inventoried; focused independent review of lifecycle, code proofs, clinical/genetics qualification and interpretation families | No line-by-line certification of all 20,974 lines |
| Tests | 95 tracked Python files / 17,089 physical lines inventoried; fresh full validation reported separately below | Test count is not coverage or scientific validity |
| Catalog and data documentation | 83 providers / 178 datasets; structural/catalog validation included in the validation gate | A catalog product is not necessarily collected, licensed, parsed or scientifically usable |
| Ten canonical dossiers | Two registered report hashes and ten receipt hashes freshly match the explicit canonical registry | Hash matches alone are not fresh raw-source scientific review |
| Clinical feasibility | Origin/follow-up/source-readiness aggregate reports and prior decisions examined; two protected outcome payload hashes unchanged | No label re-adjudication or new outcome access |
| Genetics | Full-cis technical report and scientific qualification limits examined | No new MR, colocalization or estimator validation |
| Latest model attempt | Original candidate, model-visible source view, failure report and third adjudication inspected | Exposed development case, not a fresh evaluation |
| Release and durability | Packaging/CI definitions, Git ancestry and backup claims examined | Remote state was not refreshed; E: is a local drive, not established off-site storage |

Fresh inventory reproduces 3,946 core Python lines and 20,974 utility lines. The installed wheel contains the core, not the research study stack. The 213 source/test pins in the previous full-validation code guard match the current files. All 12 canonical registry report/receipt pins match. Both protected outcome hashes match. See [audit evidence](../planning/review-assets/opus-response-20261026/audit-evidence.json) and its repeatable, read-only helper.

The earlier full-mode report contains **1,262 tests, zero failures/errors/skips**, required probes and dependency-free wheel/demo checks. Its code guard still matches. Opus independently reran core mode with one expected PowerShell skip; that is a different environment, not a contradictory test result. This review also freshly passed full mode: **1,262 tests, zero failures/errors/skips**, required probes and installed-wheel/demo verification, in 618.3 seconds outside the restricted sandbox. The failed sandbox attempts remain separately retained.

## 2. Where I agree with Opus

The main diagnosis is sound. The reusable provenance core is stronger than the current scientific result. Repeatedly extending study-specific controllers around one failed interpretation has diminishing value. The live scientific dependency is a credible reference-and-capability experiment, not more AACT files for that interpretation. The core selector and the research interpretation sidecar also have different capabilities and should not be described as one already validated reasoning system.

The duplication is substantial: study-specific launchers, journals, seal verifiers, code-closure logic and PostgreSQL wrappers have grown into parallel infrastructures. The wheel does not install these research workflows. README, TODO and memory mix current state with long historical narratives. Repeated version `0.2.0` understates changes even though code hashes disambiguate runs. Absolute paths impede restoration elsewhere.

Opus also correctly preserves important strengths: immutable evidence, explicit missingness, conservative failed-call accounting, evaluator separation, semantic recomputation and retention of negative results. A recovery phase should retain those guarantees while reducing exploratory ceremony.

## 3. Where Opus needs correction or qualification

| Opus recommendation or claim | Independent assessment | Consequence |
|---|---|---|
| Delete superseded live modules after Git tags and code hashes | Unsafe with current research verifiers: they recompute live code paths and require pinned current files | Prove archived-code restoration and verification before moving or editing code used by sealed studies |
| E: bundles provide an off-machine copy | They establish another local-drive copy only | Separate local backup, off-machine durability and hosted CI evidence |
| Complete consolidation before interpretation work | Too broad a prerequisite | Correctness and small compatibility-preserving interfaces come first; human preparation and bounded capacity diagnostics can proceed without a repository rewrite |
| One stronger-model run separates weak model from bad task | It supplies a useful diagnostic, not causal separation | Match evidence and semantics, separate interface conditions, and reserve fresh cases for evaluation |
| At least two experts and twenty cases complete H5 | This is a new pilot scope | Original H5 specifies six scientists / forty pairs; T6 proposes about fifty pairs. Amend explicitly and justify final size |
| Regional genetics inputs are missing | Existing IL6R data are substantial but scientifically unqualified | Audit exact assay, source exceptions, overlap, ancestry and estimator eligibility; do not reacquire everything |
| B0 failure describes a simple predictive baseline | Two different uses of B0 exist | Call the stopped route the **registry-content audit**; it is not the original base-rate predictor |
| H6 and every T2–T5 extension depend on T1 | Overgeneralized | H6 has its own data/identifiability gate; some mechanism tasks can be independently scoped. No automatic extension now |
| A version bump and mass formatting are immediate safety fixes | They are release/maintenance improvements | Schedule after compatibility tests; neither proves scientific capability |
| Lint counts and Python 3.15 caches demonstrate broken production behavior | They demonstrate maintenance risk or ignored artifacts | Assess actual execution/import paths before calling them correctness failures; do not mass-delete user files |
| Clinical power threshold transfers to an H5 sample | Different endpoint and dependence structure | Design dossier evaluation around paired case outcomes, reviewer agreement and meaningful coverage, not an AUROC formula |

The original proposal's H5 estimate was six experts × approximately fifteen hours, not a measured workload. Neither that estimate nor Opus's replacement should be promised to recruits before a timed pilot.

## 4. Correctness findings and their priority

The fresh synthetic reproductions are retained in the review evidence folder. They use fixtures, not real clinical labels or live model calls. They demonstrate failure mechanisms; they do not show that an archived scientific result was corrupted.

### R1. Publication precision needs an explicit policy

**Observed:** `chrono.observation_exclusion` rejects an exact publication date after origin, but a year equal to the origin year passes that particular gate. The probe reproduces this difference.

**Qualification:** valid independent proof that the identical information was public before origin can establish eligibility despite an imprecise publication field. A permissive year comparison alone is not evidence of an actual leaked record; the lineage gates also apply. A blanket December 31 substitution would unnecessarily exclude information with stronger availability proof.

**Action:** specify date precision, precedence and contradiction handling. Use exact dates when supplied; accept incomplete dates only with a sufficient public-by bound; otherwise report temporal uncertainty. Reject inconsistent exact chronology explicitly. Reuse the same policy at admission and verification. Test before/at/after origin, partial dates, conflicting metadata and complete annotation lineage. Version any changed semantic policy; do not reinterpret old receipts silently.

### R2. Expected backend failures are misclassified

**Observed:** a fixture `URLError` yields a whole-run failure after one attempted category; a `TimeoutError` produces category failures and a partial run. A missing `content` field raises `KeyError`. These errors cross an adapter boundary without a coherent typed error contract.

**Action:** normalize known transport/protocol failures inside the backend, preserve request and conservative usage records, then let the workflow apply a declared partial/fail policy. Do not make every `OSError` or `KeyError` recoverable: a storage failure or programming defect can require terminating the run. Interruption and unknown billed calls must remain visible; no automatic retry.

### R3. Valid retrieval settings can produce undispatchable local requests

**Observed:** a 20,183-byte prepared request passes the 64,000-byte retrieval-policy allowance but fails the local prompt's 16,384-byte limit. The existing question sidecar has a separate, tighter 14,200-byte cap. These are distinct contracts.

**Action:** expose backend capabilities and preflight the complete escaped/framed payload, including instructions and output reservation. Do not use one global cap for backends with different formats and context limits. Verify zero backend calls when preflight fails.

### R4. Directly constructed stores lack a required invariant

**Observed:** an `EvidenceStore` constructed without the loader can run, then fail in `write_run` with `AttributeError: snapshot_base`. The loader attaches this field dynamically.

**Action:** make the base path an explicit constructor requirement or provide a validated constructor/factory whose failure precedes dispatch. Preserve public loader behavior and test direct construction plus finalization.

### R5. Portability and verification are incomplete migration contracts

**Observed:** receipts contain absolute roots; research verifiers bind live code closures. Content hashes prove byte identity but do not make old software executable or paths resolvable on another machine.

**Action:** design a versioned resolver mapping declared root IDs to caller-approved roots, with traversal/link/escape checks and complete receipt, raw-parent, packet and code proofs. Keep original receipts unchanged. Test restoration with the original roots unavailable. Compare verification results and explicitly report historical verification semantics. A copied demo alone is insufficient.

### Lower-priority findings

| Finding | Assessment and appropriate test |
|---|---|
| C4 repeated request serialization | Real, bounded growth cost; current policy caps at 100 records. Measure before optimizing; preserve deterministic ordering and fingerprints |
| C5 hard-link publication | Also a reproduced operating-environment limitation: sandbox hard links fail on the current drive, while an approved outside-sandbox fixture succeeds. A replacement must preserve atomic no-overwrite publication and concurrent-writer safety; an exists-check followed by replace is unsafe |
| C6 `Mapping = None` annotations | Real type-contract clarity issue; change annotations/initialization without changing serialized fields |
| C8 union decoder errors | Real diagnostics issue; keep branch causes without exposing sensitive payloads or weakening strict decoding |
| C9 unused imports/variables | Useful scoped cleanup after pin-migration safeguards; no scientific gain by itself |
| Complexity and style | Reduce high-risk functions incrementally under behavior and archived-verification tests; an arbitrary complexity score is not an acceptance proof |

## 5. Scientific and data feasibility

### Clinical prediction remains unqualified

The retained clinical work includes restored AACT snapshots, registry-scale frames, origin mappings and extensive source follow-up. It does not yet supply a qualified target–program outcome benchmark. The 36 audited endpoints remain unresolved; the fixed twelve-member prospective readiness route is 0/12 joint-ready; the separate registry-content audit stops at 53.125% coverage. Those are scoped negative results, not proof that every clinical benchmark is impossible.

AACT status transitions are not automatically efficacy outcomes. Public posting, trial dates, analysis dates and decision dates are different clocks. Negative, censored, unresolved and unavailable outcomes must stay distinct. A public benchmark label can be an evaluator asset, but not a model input or automatic ground truth. Target/program mappings, endpoint definitions, source chronology, dependence and reuse permissions still require qualification.

No scorer should be trained merely because data engineering passes. A non-genetic scorer need not wait for MR, but it still needs qualified labels, predictors, splits and calibration data. Clinical probabilities remain null.

Fresh drive checks found 1,727,089,790,976 bytes free on D: and 1,684,970,143,744 on E: (about 1.57 and 1.53 TiB). That is ample for this review/pilot's small outputs, not a sizing proof for every catalog product. GPU/RAM inspection was unavailable through the restricted CIM interface; a larger local model's fit remains unestablished. No additional user-supplied dataset is needed for the immediate expert exercise.

### Genetics has technical assets, not validated causal features

The [full-cis report](../planning/Full%20Cis%20Genetics%20Revision.md) records 6,120 IL6R QTL rows, 5,722 regional GWAS rows, 2,979 shared QC variants, 503 reference LD samples and a retained 38-file set. It also records a source checksum exception, coordinate/duplicate exclusions, incomplete study-specific metadata and a transcript-abundance exposure in naive monocytes. This is not automatically a protein or drug-inhibition instrument.

Before computation, the selected estimator needs justified regional coverage, alleles/build/units/uncertainty, ancestry and LD compatibility, per-variant N where required, assay identity, sample overlap and appropriate sensitivity analyses. Historical eligibility is separate from present-day technical usability. MR/colocalization and treatment-direction claims remain deferred. The latest pilot's MR interpretation task was never dispatched; there is no new MR-model failure result.

### Contemporary T6/H5 is the most tractable next branch

The ten development dossiers are real finalized artifacts with retained technical source audits. They cover ten hypotheses but only eight targets; repeated targets/modalities are not independent cases. Provider scores remain descriptive; numerical prediction features are empty. Selected-subset coverage and missing inputs preclude broad absence claims.

The core model action selects IDs from lexical-prefiltered evidence. This is a useful controlled extractor, but parity with lexical selection is not evidence about open-ended reasoning. Conversely, interpretation-sidecar failure does not invalidate the immutable ledger or the extractor. Evaluate retrieval, selection and scientific interpretation as separate components.

The latest exposed IL6R attempt reports 4,650 input and 601 output tokens, one failed response and an unrun second question. It omits reported cellular context, links one proposal to an insufficient passage and supplies unsupported applicability labels. The retained adjudication credits supported tentative proposals and treats its broad context limitation as ambiguous rather than inventing an unequivocal critical denial. Contract nonconformance and scientific usefulness are separate outcomes.

Relevant context already exists in the supplied record. An exponentially expanded native reason-string grammar is therefore not the default highest-value investment. Prefer a simple, documented, versioned interface, strict post-validation, transparent failure accounting and a bounded diagnostic of capability. If a constraint cannot be enforced natively, report the native/post-validation distinction; do not modify a failed answer to make it pass.

### Independent references are the immediate human requirement

AI agents can prepare evidence cards, check locators, propose rubrics, blind system names and calculate agreement. They cannot supply an independent human scientific reference by labeling their own output expert review. Human reviewers should first assess source evidence without system outputs, then independently review masked outputs. A third relevant reviewer adjudicates substantive disagreements while original answers remain intact.

Two qualified judgments are needed **per case**. The eventual panel needs coverage of the domains actually included; two people cannot be assumed competent across oncology, immunology, metabolic disease, ion channels and causal genetics. The immediate IL6R packet is orientation/development only. It measures reading, ambiguity and usability, not professional competence or general H5 performance.

Clinical endpoint adjudication and advanced genetics may need different human expertise later. The separate human workstream documents these conditional needs rather than implying that one immunology reviewer resolves the whole project.

## 6. Evaluation design that would answer the right question

1. **Declare the claim.** First establish faithful, useful contemporary interpretations under known evidence/budget constraints. Keep the original clinical hypotheses deferred unless their data gates reopen.
2. **Separate diagnostics from inference.** An exposed-case comparison can diagnose transport or capacity problems. Fresh, sealed cases are required for performance estimates. A stronger model's success is neither proof of causality nor historical eligibility.
3. **Separate source validity from answer fidelity.** A candidate can accurately summarize a flawed review. Human judgments need separate source entailment, citation correctness, context, underlying scientific credibility, applicability and utility fields.
4. **Use two comparison tracks.** A fixed-evidence interpretation comparison isolates interpretation; an end-to-end comparison includes retrieval. Do not attribute a gain to reasoning when evidence access differs.
5. **Count failures.** Nonfinalized, malformed, timed-out and all-abstention outputs belong in operational denominators. Report supported useful coverage alongside error rate so silence cannot win on low errors.
6. **Analyze dependence.** Claims, modalities and reviewers within a target/case are correlated. Use the case or declared target-family cluster as the analysis unit; report ties and missing ratings. Size the final study using observed pilot variation and a declared precision or power objective.
7. **Account for full resources.** Provider spending can be zero while local inference, engineering and external AI review are costly. Report measured local time/energy when available and explicitly unmetered preparation/review work. Do not claim end-to-end cheapness from API cost alone.
8. **Name the comparator honestly.** The present adapted Virtual Biotech arm is not an exact reproduction of its original data/tools/models. Freeze and disclose the adaptation; keep the original 38-directory/release-compatibility requirements separate.

## 7. Recovery priorities and completion boundaries

**Now:** adopt a scoped decision record, correct the reproduced boundary failures, prepare/recruit the human development review, and design a bounded capacity/interface diagnostic. No new paid access or automatic download is implied.

**Next:** prove archive restoration and relocation; extract only shared infrastructure needed for the next study; package a minimal configurable interpretation interface; measure a small development comparison; choose the final H5 design and sample size from those results.

**Later, conditional:** fresh locked H5 evaluation; a separately qualified clinical cohort and non-genetic scorer; causal genetics if estimator prerequisites pass; original baselines/ablations; individually justified T2–T5 and H6. Neither a successful expert exercise nor green tests completes these items.

The recommended plan pauses the old automatic wire-repair/pilot sequence. It preserves the failed artifacts and original proposals. The pending converter experiments may inform design, but they do not authorize another native run or establish scientific qualification.

## 8. Validation record

| Check | Fresh outcome |
|---|---|
| Full mode, portable PowerShell, Arrow 21.0.0 | 1,262 tests; zero failures, errors or skips; PowerShell syntax check passes |
| Required framework probes | Exit 0 |
| Wheel/install/demo/source verification | `asof_target_agents-0.2.0` builds; dependency-free installed demo runs and verifies |
| Framework/code baseline | All 213 previous validation pins still match; no production framework/test edits |
| Engineering reproductions | C1 precision behavior, C2 error taxonomy, C3 cap mismatch and C7 constructor failure reproduced with synthetic fixtures |
| Existing local-model regressions | 14 pass, no skips |
| Expert instrument | 18 unanswered items / 90 choices, seven unique source passages / twelve occurrences; no AI verdicts or local private paths in shareable files |
| HTML interaction | Ten headless-browser checks pass, including stage order, draft preservation, export and rejection of a wrong-packet import |
| PDF | Nine pages, 63 fields / 135 widgets; blank choices, bounds, appearances and fill/read-back checked; rendered layout inspected |

The [full validation report](../planning/review-assets/opus-response-20261026/full-validation.json), [engineering probes](../planning/review-assets/opus-response-20261026/engineering-probes.json), [independent engineering notes](../planning/review-assets/opus-response-20261026/engineering-audit.md), [scientific audit](../planning/review-assets/opus-response-20261026/science-audit.md) and expert validation reports are retained under `planning/review-assets/opus-response-20261026/`.

Two initial environment failures are not erased: system-temp validation stalled and was interrupted; workspace-temp sandbox validation ran all 1,262 tests with 89 errors and one failure, then packaging failed on uv cache persistence. A standalone hard-link probe reproduced access denial inside the sandbox and succeeded outside it. The approved offline outside-sandbox rerun passed unchanged code. This is an execution-environment dependency to document, not a reason to weaken the no-overwrite implementation or disguise the failed checks. Logs remain in the ignored audit cache and are identified by hashes in the closeout evidence.

No framework correctness fix or new scientific experiment is implemented in this documentation task. The defects and all subsequent scientific work remain explicitly open in the recovery plan.

