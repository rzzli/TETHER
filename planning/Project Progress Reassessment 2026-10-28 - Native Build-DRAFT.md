# Project progress reassessment — typed native build checkpoint

**28 October 2026 UTC. Draft: independent build-result verification pending.**
Accepted software remains AsOf **0.3.11**. This assessment follows the
[sixteen-step plan](Project%20Recovery%20and%20Evaluation%20Plan%202026-10-26.md)
and preserves the earlier
[generation assessment](Project%20Progress%20Reassessment%202026-10-28%20-%20R09%20Generation.md).
It assesses the whole project's recorded status; it does not reopen every raw
dataset or certify scientific conclusions. Human responses and protected outcome
payloads were not inspected.

## Concrete progress and qualification boundary

The owner-installed C++ Build Tools work without a restart. A typed public-C
consumer of the pinned llama.cpp headers now compiles and links successfully.
The [build report](../data/cache/r09-public-c-bridge-build-20261028T175036Z/build-report.json)
records two successful owned tool processes, about 3.547 seconds through helper
completion, no capture/cleanup error and a 188,416-byte x64 executable with SHA-256
`9f955aec8310ded1cd26648c7d9828369751219975893d5f45b35073b6927696`.
The compiler uses warnings-as-errors and the exact MSVC/SDK environment. Static
inspection finds no upstream llama/GGML, network or process-spawning imports.
The executable has **not run**. Recognition is disabled in its data header;
`--abi` exists for a later separately qualified observation. The build report's
literal `ABI_disabled...built_not_executed` status must not be interpreted as an
ABI test or as the absence of an ABI entry point.

The [build decision](review-assets/recovery-step9-native-recognition-20261028/BUILD-ROOT-DECISION.json)
permits only compiler and linker execution. Its 193 pinned inputs, seven copied
public headers and scoped source/helper reviews are retained. Compiler ownership
covers the launched handles; complete compiler-descendant, memory and OS write
isolation were not established. That disclosed trusted-tool scope differs from
the stronger boundary required before native target execution.

Source prerequisites now have a finite
[qualification](review-assets/recovery-step9-native-recognition-20261028/SOURCE-QUALIFICATION.md):
22 new exact-commit references, 1,242,387 bytes and 207 receipt-bound output hashes.
The public repository include graph closes at seven headers/thirteen edges.
The selected no-allocation/vocabulary-only path skips explicit tensor-blob reads;
metadata, vocabulary, file opening and sizing remain. Fresh whole-shard hashing
would itself read weight-file bytes. Source identity, release-binary identity,
ABI compatibility and actual behavior remain different claims.

The prospective initialization route loads one exact CPU provider, checks its
sole CPU registry/device identity and then calls the public initializer without
its zero-registry discovery branch. Delegated CPU initialization, dynamic-loader
bodies, build flags and DLL startup effects remain source-review limits. No
proof of zero GPU API activity or complete dependency unload is claimed.

## Findings that changed the next action

1. **Header and initialization assumptions were incomplete.** The missing
   `ggml-alloc.h` dependency and delegated GGUF/file/Qwen2 behavior were resolved
   within a bounded source scope. The tokenizer example creates a context, so it
   is unsuitable as a no-context shortcut. Exact declarations and bridge-owned
   code replace guessed layouts/private-object access.
2. **The first bridge's ABI module rule contradicted PE imports.** The actual
   base DLL imports OpenMP. Static inspection caught this before compilation or
   execution. The original source/review remain intact; a separately reviewed
   revision permits, hashes, leases and securely preloads only the required
   exact OpenMP dependency. CPU registration stays outside ABI-only mode.
3. **The first input pack conflated a harness exclusion with native rejection.**
   Independent decoding verified all 189 bindings, four grammars, six prefixes
   and 111 input hashes, but one original primary document contains raw NUL.
   Its bytes remain unchanged. The
   [retained review](review-assets/recovery-step9-native-recognition-20261028/PACK-RESULT-VERIFICATION.md)
   holds native eligibility. Prospective format 2 preserves all 167 original
   documents and their pure 44/123 comparator observations, while separating
   166 byte-front native candidates (44/122) from that one harness-only case.
   Its expected native membership is null. The 18 new canonical serializations
   of retained authored abstentions and four byte guards are separate groups,
   never recovered historical raw responses or model answers.
4. **Initial OS probe assertions were insufficient.** Memory allocation and a
   descendant attempt were rejected; owned explicit termination and last-job
   closure reaped their handles. However,
   [independent review](review-assets/recovery-step9-native-recognition-20261028/OS-PROBE-RESULT-VERIFICATION.md)
   found two active-process counts with a configured limit of one. The original
   passing-status report remains preserved; unqualified containment is held.
   A new finite diagnostic will compare raw accounting with job-owned PID lists
   and read-only image/creation metadata. No cause is inferred. Review also
   found uncapped capture paths and non-atomic worker markers in the first
   unexecuted diagnostic; those require correction before it can run.
5. **Token flags are insufficient evidence of exact input consumption.** Native
   testing requires strict whole-input UTF-8/NUL guards, counted-byte roundtrip,
   document EOG exclusion, fresh samplers, apply-before-accept and every actual
   vocabulary EOG ID. Harness exclusions, token/grammar rejection, completion
   probes, resource failure and unavailable natural-prefix coverage must remain
   distinct. No repair, retokenization workaround or vocabulary substitution is
   permitted to manufacture agreement.

There was no new biological/model download or new target-DLL, GGUF, tokenizer,
inference or server execution in this checkpoint. The earlier R07 generation and
closed converter diagnostics remain historical facts, not new successes. Provider
spending stays $0. The package's 1,774 passing tests/327 source pins are the retained
0.3.11 software evidence; they do not test this unexecuted native executable.
Two current working documents also had a Windows-default encoding roundtrip
corrected reversibly from retained backups; subsequent text edits use explicit
UTF-8. No frozen evidence was rewritten.

## Complete recovery and human status

| Step | Current status | Remaining condition |
|---|---|---|
| R01 Scope/governance | Accepted in scope | Preserve contemporary T6 focus, original hypotheses and conditional branches. |
| R02 Checkpoint | Accepted in scope | Local retained artifacts are not independent off-site durability. |
| R03 Archive compatibility | Accepted in scope | Seven legacy families/ten matching earlier versions qualify; full raw/model restoration and cross-platform behavior remain separate. |
| R04 Correctness boundaries | Accepted engineering | Current tests support their defined invariants, not absence of every defect. |
| R05 Diagnostic preparation | Accepted preparation | Stronger capability control and independent scientific references remain unavailable/pending. |
| R06 Minimal infrastructure | Accepted in scope | Reuse the bounded framework; avoid a broad platform rewrite. |
| R07 Bounded diagnostic | Technical negative closed; science open | Preserve six original responses/zero accepted contracts; no restart, human assessment pending. |
| R08 Fresh frame/source feasibility | Preparation only | No fresh scientific case is qualified; exposure, dates, sources and reviewer coverage remain. |
| R09 Interpretation/comparators | Engineering progress; whole step open | Typed build is unexecuted; native ABI/document/EOG, full-case resources and usefulness remain unqualified. Default dispatch stays v2. |
| R10 Human pilot | Not activated | Qualified cases, source-only references, masking and independent timed ratings. |
| R11 H5 sizing/preregistration | Pending pilot | Case-level estimand, dependence/variance, failures/ties, workload and justified precision/power. |
| R12 Locked H5 | Gated | Frozen assets/analysis, sized independent panel, once-only outputs and appropriate registration. |
| R13 Clinical outcome alternative | Conditional/deferred | Endpoint validity, mapping, chronology, censoring and independent outcome information. |
| R14 Predictors/genetics/scorer | Conditional/deferred | Estimator-specific data/QC, intervention interpretation and chronological fitting/calibration. Features empty; probabilities null. |
| R15 Clinical comparisons | Conditional/deferred | Qualified endpoints/predictors, dependence-aware power and locked baselines/ablations. Adapted roles are not full Virtual Biotech reproduction. |
| R16 T2–T5/H6/release | Separately conditional | Task-specific sources/endpoints, H6 inputs, licensing, release/restore and cross-platform evidence. |

| Human gate | Current status | Required evidence |
|---|---|---|
| HR1 Recruitment | Pending owner workstream | Domain coverage, commitment, conflicts and exposure records. |
| HR2 Orientation | Independent submissions pending | Two submissions and measured usability/timing; methods expertise where needed. |
| HR3 Fresh pilot references | Gated | Source-only references locked before candidate exposure, masked ratings/adjudication. |
| HR4 Final panel | Pilot/sizing-dependent | Adequate independent domain coverage, retained disagreements and final adjudication. |

Agents' source, code and literature assessments do not complete these human
gates. Existing expert packets remain shareable; no completed answers are implied.

## Data and scientific feasibility remain limiting

This checkpoint revalidated engineering inputs and retained status reports; it
did not perform another complete biological raw-data audit. Existing data/catalog
entries do not establish complete collection, historical eligibility, access rights
or scientific validity. No current annotation may silently fill a historical gap.

The exposed IL6R development case still has five literature candidates with one
whole record selected, nine available observations and 65 missing inputs. Equal
selection by two policies proves neither retrieval superiority nor source/question
sufficiency. Preparation and authored abstention responses are not fresh scientific
performance examples. Model knowledge/exposure and article identities/dates still
need appropriate controls.

The retained feasibility findings remain substantive: 36 unqualified endpoint
labels, 17/32 observable registry primary states and 0/12 jointly source-ready
clinical cases. Registry status, efficacy, approval and sponsor continuation are
different endpoints. Historical AACT access alone cannot resolve those differences.
The original 0.05 AUROC improvement and co-primary Brier requirements remain unless
prospectively amended. Genetics still needs complete regional inputs, assay/build/
allele/sample/ancestry/LD/overlap QC and defensible intervention interpretation.
No causal estimator, calibrated clinical probability or biological conclusion is
validated by this native build.

At this checkpoint drive metadata reports approximately 1.55 TiB free on D: and
1.53 TiB on E:. This is sufficient headroom for these small engineering artifacts;
it does not size the entire dataset inventory. The downloader, transport receipts
and stopped periodic monitor remain untouched.

## Critical next stage and stop conditions

The next major stage is **bounded native qualification**, not another model answer
batch. The following order retains the scientific and resource boundaries:

1. Independently verify the actual build receipt, executable/object hashes, two
   tool attempts, journal, captures and frozen inputs. Accept only a built,
   unexecuted ABI-only artifact; keep recognition disabled.
2. Correct and review the OS identity diagnostic. Run its exact once-only protocol
   with one own-source worker, five fixed snapshots, sixteen-PID bound, read-only
   metadata and retained failures. Explain or explicitly retain the accounting
   discrepancy before qualifying native containment. Do not terminate arbitrary
   observed PIDs, enumerate the whole machine, request elevation for convenience
   or infer a process identity from a guessed cause.
3. Independently decode format-2 input bytes and compare every case to its original
   source. Verify all group, pure/native/harness distinctions and exact prefix
   hashes. Natural BMP/astral token-boundary existence remains untested; absence
   must be reported without substituting text or tokens.
4. Freeze a separate ABI-only execution protocol after containment qualifies.
   Bind exact EXE, source/header/build/PE inputs and module policy. Measure and
   record startup, memory, captures, modules and cleanup. Query only version and
   native defaults; no registry, model, GGUF, tokenizer, grammar or inference.
   Treat unexpected modules/defaults/crashes as terminal evidence. An observed
   version string must be reviewed before later pinning, not guessed from CLI text.
5. Only after ABI success, prospectively prepare a newly enabled recognition header
   and build. Recheck all three existing shard hashes/read leases, explicit CPU
   identity and vocabulary-only overrides. Run the exact corpus and every EOG
   probe under finite memory/time/output bounds; record harness exclusions and
   unavailable coverage separately. No native rejection is inferred from a failed
   process, prevalidation or incomplete collection.
6. Qualify full-vocabulary mask cost, boundary strings and stack growth. Singleton
   membership tests alone cannot size production sampling. Metadata-only loading
   still owns a model handle and allocates vocabulary structures. Time spent
   hashing whole weight files is real even when tensors are not allocated.
7. Before an integrated native case, resolve the preserved 295.922/300-second
   simulation with only 4.078 seconds spare **without real startup/inference**.
   Profile hashes/leases, preparation, tokenization, reservations, transport,
   inference, cleanup and sealing under declared stop conditions. Do not increase
   the case budget, weaken integrity or select an easier case to obtain a pass.
8. In parallel, keep HR1–HR3 and fresh-source feasibility visible. Activate R10
   only after the frame, references, reviewers and mechanics qualify; size R11
   before R12. R13–R16 retain their independent scientific/data gates.

The scientific case budget remains 300 seconds, provider spend $0, numerical
features empty and clinical probabilities null. Whole R09 and the original
H1–H6 programme remain unfinished.
