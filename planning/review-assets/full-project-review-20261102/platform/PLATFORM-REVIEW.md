# TETHER platform review and bounded correction — 2026-11-02 UTC

The review reproduced two execution-consistency gaps and a dossier-binding gap in the frozen AsOf 0.3.11 engine used by TETHER 0.4.0. These gaps are now rejected at the **TETHER 0.4.1 command boundary**. The frozen engine, original scientific results and historical release artifacts were not rewritten. Current package validation passes **73 tests**; a fresh offline wheel also passes isolated installed execution and externally anchored verification.

This is an engineering assessment. It does not validate biomedical conclusions, historical data eligibility, model performance or the manuscript's scientific interpretation. Other reviewers own the data/results/planning assessment in the parent review directory.

## Findings and disposition

| ID | Severity / basis | Finding | Correction or next action |
|---|---|---|---|
| P01 | P1; reproduced | `src/asof/semantics.py:15` checks identity/accounting but does not reconstruct category states. A synthetic completed run with a retained probability was accepted with genetics coverage `failed`, `biologically_absent`, or `invented_status`. The original producer generated the receipt, and source-inclusive verification accepted its external receipt anchor. | New `packages/tether/src/tether/_semantics.py:27` replays category states, attempts, terminal events, coverage and status. New TETHER finalization/verification calls it; explicit regressions reject the three examples. |
| P02 | P1; reproduced | Review decisions were not bound to committed claims. Replacing all review selections by empty lists left nine committed synthetic claims accepted by original finalization and verification. | New checker requires ordered committed IDs to equal the accepted selection, except an explicit deadline permits only a committed prefix. It checks review/accounted usage, bounded-request membership, retry order and attempt disposition. |
| P03 | P2; reproduced | `src/asof/artifacts.py:184` verifies the dossier's hash, but does not reconstruct its text. A new receipt for an altered dossier can report semantic consistency despite additional invented prose. | New `check_engine_semantics` reconstructs the original deterministic engine dossier from verified inputs, claims, features, prediction, exclusions and coverage. Only equivalent LF/CRLF forms pass. Outer branding projection retains its separate exact-byte check. |
| P04 | P2; inspected, not a demonstrated production hang | `packages/tether/src/tether/_presentation.py:206` uses main `communicate()` without a deadline or streamed stdout/stderr cap. Cleanup is bounded after an exception, but normal execution can wait indefinitely for a nonreturning child and can accumulate child output. Workflow time accounting cannot preempt arbitrary synchronous backend code. | Retain the current trusted-local execution qualification. Next version should define an absolute child deadline and bounded output capture, with terminated-child accounting and no automatic retry. No frozen engine edit or live-model test was attempted. |
| P05 | P2; inspected | `src/asof/local_model.py:187` and `src/asof/study/source_fact_transport.py:269` pass a timeout to urllib and then perform a bounded response read. That is not a demonstrated absolute wall-clock deadline across repeated incoming bytes. `src/asof/study/native.py` uses an explicit absolute watchdog; the transport families have different guarantees. | Qualify deadline wording and use the newer watchdog contract for future transport revisions. A future slow-response synthetic server test should cover headers and body, partial capture, shutdown and accounting. |
| P06 | P3; inspected | `src/asof/chrono.py:193` checks packet size before an unbounded `read_bytes()`. Exact bytes are hashed before decoding, so this is not a demonstrated checksum bypass, but concurrent growth can exceed the intended memory bound before rejection. | Future version should use a stable bounded read of the same captured bytes. Preserve the frozen engine and avoid claiming filesystem exclusivity. |
| P07 | Compatibility/design boundary; documented | Python aliases such as `tether.artifacts.verify_run` intentionally expose the frozen engine. They do not silently acquire the new CLI guarantee. Current launcher fingerprints also differ from archived 0.4.0 outer receipts. | Package documentation names the stronger command boundary and the weaker compatibility API. Verify historical 0.4.0 outer artifacts using their pinned old wheel/source; current 0.4.1 verification is not a substitute for that archived implementation. |

P01–P03 are **not an old-receipt anchor bypass**. The demonstrations use new synthetic producer outputs or a newly resealed synthetic dossier. The original saved external hash still rejects changed bytes. Their implication is narrower and important: previously, a valid producer receipt alone could accompany internally contradictory execution or unbound prose. No retained scientific artifact was mutated to demonstrate this.

## Correction details and peer review

`tether verify` now runs the original source-inclusive checks and adds `tether.execution_semantics.v1` for v2 artifacts. New outer runs must pass that check before the TETHER success receipt is published. Verification neither dispatches a backend nor retries an attempt. Version-one receipts continue through the existing legacy path, without claiming v2 semantics.

The new state replay checks accepted reviews against claims; bounded selection membership; accounted attempts with a review or terminal disposition; contiguous retries; disabled-review behavior; quote/backend terminal failures; known fatal/interrupt termination; explicit wall-time truncation; coverage status and retrieval metadata; and deterministic dossier reconstruction. Known `RecursionError` follows the engine's recoverable `RuntimeError` branch. Valid completed, partial, fatal, interrupted, budget-exhausted, empty-selection, empty-retrieval, disabled and no-observed cases are retained in tests.

An independent reviewer found three additional false acceptances while this correction was being developed: continuation after backend failure, continuation after quote failure, and removal of rejected-review dispositions from a retry trace. All were fixed. The reviewer also checked bounded-request membership. The independent before/after reports live in `../results/SEMANTICS-INDEPENDENT-REVIEW.md`; those failures are not concealed by the final green suite.

The replay is deterministic **consistency verification**, not authentic execution attestation. A serialized `error_class` does not encode arbitrary Python subclass inheritance. Known standard error names are constrained, but custom fatal/interrupt ancestry cannot be recovered from this trace alone. Generic backend request fingerprints and retrieval decisions are not independently reconstructed from a fully archived backend implementation; the existing local-structured backend has its own deeper request/archive check. Provider billing, actual elapsed time, complete upstream capture and truthful source content remain outside the new guarantee.

## Validation retained

| Check | Result | Evidence |
|---|---|---|
| Original TETHER suite in workspace temporary directory | 49 passed | `TETHER-BASELINE-TESTS-WORKSPACE-TEMP.txt` |
| Original semantic gaps | Five synthetic examples accepted before correction | `probe_semantics.py`, `SEMANTIC-PROBES-BEFORE.json` |
| Final current package suite, core-only canonical environment | **73 passed, 28.328 seconds**; 24 new semantic tests plus the original 49 | `TETHER-041-FULL-TESTS-FINAL-v2.txt` |
| Independent adversarial follow-up | Four probes reject; independent targeted suite retained by peer | `../results/SEMANTICS-INDEPENDENT-REVIEW.md` |
| Offline wheel build/install with pinned cached setuptools and original core wheel | Passed; no dependency conflict | `WHEEL-BUILD-FINAL-v3.txt` |
| Installed wheel from fresh workspace-cache environment | 21 members, full RECORD/CRC check, 15 runtime source files match working tree; no `asof` ownership | `WHEEL-QUALIFICATION-FINAL-v3.json` |
| Installed isolated demo, externally anchored strong verify, wrong anchor | Passed; wrong anchor rejected; journal unchanged/no redispatch | Same wheel report |
| Frozen core change check | `git diff --exit-code 21f64e7 -- src/asof` returned zero | Parent final diff and inventory |

Final wheel: `data/cache/tether-041-qualified-build-v3/wheels/tether_target_agents-0.4.1-py3-none-any.whl`, **28,747 bytes**, SHA-256 **`b392440919fddb8cab17b1741ee716bfa95d4cc1172878725b2603b115b322d5`**. It was installed with the original `asof-target-agents==0.3.11` wheel. Python imports resolved under that fresh environment's site-packages with `-I`; PyArrow was absent. This is local installed-wheel qualification, not a rebuilt manuscript package or hosted CI result. Earlier wheel reports are retained intermediate builds and do not identify the final package.

Initial default-temporary-directory tests failed because the sandbox could not create files under its C: temporary directory. Rerunning with a project-cache temporary directory resolved that environmental failure. Intermediate test logs also retain the finite-alias integration omission, unsupported whole-RunResult decoding, an obsolete delegation-test assumption and two malformed negative test fixtures discovered during implementation. The final fixes were tested rather than erasing those failed attempts.

## Review coverage and limits

This pass inventories the Python modules under `src/asof` and `packages/tether/src/tether`, with focused source inspection and adversarial execution at the highest-risk boundaries. It is not a claim that every line or every one of the repository's scientific workflows was re-audited.

| Area | Coverage in this pass |
|---|---|
| TETHER front door | Detailed read of CLI dispatch, finite aliases, launcher proof, output inventory, stable reads, child invocation/cleanup, finalization and outer verification. Entire current package test suite run. |
| Engine execution and verification | Detailed selected-function review of workflow, semantics, artifacts, ledger, chrono admission, provenance, contracts/serialization, deterministic feature/scorer connections and review selection. Synthetic counterexamples and current-boundary regression tests. |
| Ingestion | Module/entrypoint inventory and interface review only here. This reviewer did not reread provider originals or rerun real-data snapshot construction; the independent data review owns those checks. |
| Study runtime | Selected process/transport/stable-read/native deadline paths inspected. Compared old urllib paths with newer absolute-watchdog path. No native model server, tokenization corpus or science benchmark was executed. |
| Archive boundary | Checked preservation strategy, finite namespace forwarding and old/current code-proof distinctions. Did not independently requalify every historical archive; parent review owns original packet checks. |
| Tests | Existing 49 package tests plus 24 new semantic regressions; focused peer probes and installed-wheel smoke. The complete legacy scientific test suite was not rerun by this reviewer. |

`PLATFORM-REVIEW.json` inventories module hashes and labels focused-read versus inventory-only coverage. Module inventory is not counted as deep review. Zero new model calls, provider downloads or provider spending were introduced. Remaining P04–P06 limitations are versioned follow-up work, not evidence that current biological results have been validated or falsified.
