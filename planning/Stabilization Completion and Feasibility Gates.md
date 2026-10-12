---
title: Stabilization completion and feasibility gates
date: 2026-10-12
status: stabilization-verified-scientific-gates-open
tags: [asof, implementation, verification]
---

# Stabilization completion report

The revised plan's repository and contract corrections are implemented. The ten-case
v0.2 technical pilot remains complete. Scientific evaluation is explicitly gated on
data and reviewer evidence that is not yet available; see [[Feasibility Gate Decision]].
Original proposals and the independent repository review were preserved.

| Work package | State | Evidence and limits |
| --- | --- | --- |
| A — Completion record and Git | Implemented | Baseline `91e9cc4`; versioned [[planning/run-registry.json]] selects ten canonical dossiers; superseded/unknown-failure sidecars are outside sealed outputs. No remote published. |
| B — Utility/catalog ownership | Implemented | `asof.maintenance` validates reports, prior hashes, references and exclusive writes; preparation is read-only; fresh-output reports cannot overwrite history. Catalog stays 83 providers / 178 products. |
| C — Program contracts/required checks | Implemented | Invalid T6 context fails before dispatch. Withdrawn dated context remains valid; confidence-zero mappings cannot support program-specific claims. Mandatory relocated v1 fixture verifies with legacy semantic limits explicit. |
| D — Reproducible validation | Passed locally from fresh checkout | Full: 114 tests, zero skips. Core: 114 discovered, 92 executed, 22 explicit ingestion skips. Both pass ten probes and installed-wheel demo checks. Hosted CI has not run. |
| E — Scientific feasibility | Review package prepared; required evidence missing | User can arrange domain review; ten unanswered forms/20 selected claims prepared. Historical/regional files confirmed absent locally. Historical restore, empirical event counts/power, regional QC and independent expert gold remain unverified. |
| F — Live specialist | Deferred behind E | No model adapter or provider requests added; spending remains $0. |

## What changed and why

Transport inspection now emits a fresh sanitized report rather than replacing catalog
policy or scientific status. One updater owns catalog mutations, with lock/proposal
checks, atomic replacement and provenance. The normalized ten-case product is
collected/parsed with scientific validation `not_run`, justified by retained report
hashes and sealed outputs. Receipt inspection does not certify parsing or historical
availability. See [[docs/MAINTENANCE]] for commands and field ownership.

Program contracts now apply identity, phase-domain, mapping-confidence and actual
eligibility-date rules to supplied T6 context as well as T1. T1's active Phase 1/2
endpoint rules remain specific to T1. Query, ledger and semantic checks use the same
program capability rule. Original program-free pilot cases remain compatible.

Manifest/demo utilities accept explicit paths and fresh destinations. Monitor
identity comes from its queue; only `-ValidateOnly` was exercised. No monitor was
restarted. The download worker and frozen pilot input manifest remain byte-identical:

- Worker SHA-256: `e432007fea83a2e6838002318cfaa87351ce59328533fa6b023182d422659601`.
- Frozen manifest SHA-256: `c78c5a925ed096dde03ed80ed9bb05ff4bba65cff7e03b7b4416432bff2ff5ad`.

## Verification

The first integrated implementation pass ran 112 tests with no failures/skips,
all ten required review probes, PowerShell syntax checks and an isolated installed-wheel
demo/verification. Two additional regression tests subsequently confirmed that a
required test failure or unexpected skip returns nonzero, including core/full skip
policy. The final integrated run passed **114 tests with zero skips** and all ten
probes. A fresh local Git clone at `8e022e7` passed the same full gate and the core gate
(92 executed, 22 named optional ingestion skips). Both built and installed the wheel
into a separate dependency-free environment and verified its demo. No private runs,
queues or E: data were copied into the checkout. Retained reports:

- [[data/manifests/public/2026-10-12-stabilization-validation.json]].
- [[data/manifests/public/2026-10-12-clean-checkout-full.json]].
- [[data/manifests/public/2026-10-12-clean-checkout-core.json]].

The later expert-review packaging utility was checked separately against the canonical
artifacts: ten forms/20 source-bound claims, all reviewer fields unanswered, valid file
hashes, existing-output rejection and enforcement of evaluator-only output placement.
It does not modify runtime execution, archived runs or catalog scientific status.

All ten canonical dossiers were freshly verified against their retained receipt
anchors and source originals using the updated runtime. Byte integrity and semantic
consistency passed, including sealed requests. See
[[data/manifests/public/2026-10-12-retained-run-verification.json]]. Their archived code
fingerprints correctly differ from the modified runtime (`code_matches_current=false`);
old outputs and receipt bytes were preserved. Scientific validity remains
`not_established`. This compatibility check does not claim the old runs executed the
new code or repeat the independent biological review that is still absent.

The retained production metrics remain 2,141 files / 3,752,440,123 bytes; 14,207 matching
source rows and 16,914 case records; 65 missing inputs. The 20-row source audit is
technical fidelity evidence, not adjudicated biological gold. No regeneration was
needed. See [[Project Audit and v0.2 Completion]] for resource measurements and the
complete requirement/task/hypothesis status matrix.

## Remaining boundaries

Clean checkout checks use synthetic fixtures and pinned dependencies without copying
private queues, E: payloads or ignored runs. Hosted Linux/Windows execution is only
configured, not observed. Local tests are not an OS network/filesystem sandbox.
Catalog locks coordinate compliant local writers, not hostile/manual concurrent edits.
The standard Apache license is retained; project rights-holder attribution remains
unresolved. Real probabilities, clinical cohorts/scorer training, MR, competitors,
T2–T5, H6, bulk acquisition expansion and live calls remain later work.
