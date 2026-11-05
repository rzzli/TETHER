# Independent replay review and release-gate readiness

**No additional material replay defect or unjustified compatibility restriction was identified.** The correction is ready for integration qualification once the narrowly reviewed archive dependency profile and release metadata are stable. This is not a completed release gate.

This read-only pass reviewed the replay checker, its publication/verification hooks, the shared replay lookup, the quote/dispatch/review workflow, the 25 retained regressions, the validation driver, relevant facade tests and CI commands. It reused [green02.json](green02.json), which records 25 passing tests with zero failures, errors or skips, and verified its source hashes. It did not rerun that suite, modify code/profile/frozen artifacts, or execute a comparison corpus. The earlier detailed [peer note](../tether-equal-policy-result-review-20261105/replay-correction-peer-review.md) retains the correction's exact source pins.

## Behavior and compatibility

The new checker binds consumed entries to the same source-derived request construction used during execution. It validates ordering, retry feedback, usage, selections and terminal quote failures. Shared entry lookup preserves the old live replay behavior and leaves cursor advancement in `select`. Publication checks run before a new output directory is created; archive verification still runs common execution and semantic checks before the added replay check.

The retained regressions cover complete valid replay, consistently resealed request/dispatch forgeries, changed selections or usage, missing consumed roles, invalid retained schema/provenance, extra unused roles/entries, valid failed quotes including negative consumed usage, unused negative usage, missing retry entries, reordered retry entries, interruption with estimated accounting, zero-call budget, source-free verification, original-file removal and legacy-v1 receipt scope. The later follow-up also covers repeated terminal quote failure and counts source reconstruction for failed quotes. No stricter requirement for an original replay file, independently reread original-byte hash, or unused response consumption is introduced. Source-free mode explicitly states its weaker binding.

A finite regression set is not exhaustive. Disabled-role and mid-retry budget combinations are not additional dedicated tests in this 25-case file, but this review found no defect requiring another gate for them: their behavior follows the existing execution checks and the unchanged request/entry contract. This does not certify arbitrary custom backends that reuse the recorded replay backend's identity.

## Metadata readiness

The review initially identified the new module's finite namespace allowlist requirement. It is now present in `packages/tether/src/tether/_aliases.py`. At the final read, the two pyprojects, both lockfiles, core/facade version declarations, pinned facade engine dependency, and facade namespace/frontdoor test expectations consistently use **AsOf 0.3.13 / TETHER 0.5.2**.

Keep the original comparator's 0.3.12/0.5.1 fixtures and the old installed qualification unchanged. Their versions are intentional historical controls. Similarly, the old release qualifier has hardcoded old versions/wheel names; use a new versioned qualifier for the new pair rather than rewriting retained qualification history. The new independent runtime already declares only the exact pairs 0.5.1/0.3.12 and 0.5.2/0.3.13, with actual per-call payload/metadata checks.

## Lean integration checks and mandatory gates

| Order | Check | Reason and boundary |
|---|---|---|
| 1 | Reuse the 25-test replay receipt while its four source pins remain unchanged. | A duplicate run provides no new evidence. If these sources change, rerun their affected tests. |
| 2 | Finish the narrowly scoped archive dependency-profile review and its archive tests. | `agents.py`/`artifacts.py` are shared dependencies. Preserve archived semantics and explicit approved profiles; do not relax compatibility merely to clear a gate. This work is owned separately. |
| 3 | For an early integration check, use `tests.test_framework`, `tests.test_v02_hardening`, `tests.test_backend_hardening`, `tests.test_runtime_hardening_peer`, and facade `test_namespace`, `test_frontdoor`, `test_semantics`. | These cover replay execution, publication/verification, failures, finite aliases, version metadata and facade presentation. They are a lean debugging subset, not a replacement for the full gate. If proceeding directly to the full gate, avoid an unnecessary duplicate subset run. |
| 4 | Run `tools/validate.py --mode full --package --failfast --report <fresh report>` once against stable current source with before/after source pins. | Full mode requires PyArrow 21.0.0 and PowerShell 7, rejects all skips, checks structure/catalog/ignored paths, runs repository tests and required probes, and builds/installs/verifies the core wheel offline. Retain failures and reports. This driver has no hardcoded product-version requirement requiring a change. |
| 5 | Run the facade test suite separately: `python -B -m unittest discover -s packages/tether/tests -v`. | `tools/validate.py` discovers only the root `tests/` directory. Its `--package` check builds the core wheel, not both distributions; it cannot substitute for facade qualification. |
| 6 | Qualify newly built **both** wheels in a fresh isolated installation, using `-I` and pinned payload/metadata inventories. | Verify actual versions, dependency compatibility, source/wheel/installed bytes, offline demo/source-inclusive verification and entrypoints. Include new replay module and approved dependency profile. Existing 0.5.1 native parity is historical qualification, not proof of installed 0.5.2. |
| 7 | Finish corrected v2 native preparation and pre-freeze review, then freeze and compare. | The retained 8 corpus tests, 7 independent unit tests and 2 old-runtime native tests are separate experiment evidence. They are outside the root test discovery; no full-gate count should silently include them. The corrected 109-case corpus remains a new, exposed comparison. |

No test count is prescribed for the new full gate; discovery determines it. The old 2,020-test receipt describes its exact earlier source snapshot. Do not report that old count as current-release qualification or claim Linux/macOS coverage from this Windows run.
