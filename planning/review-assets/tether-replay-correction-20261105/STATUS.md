# Archived replay correction: current qualification status

Checkpoint: 5 November 2026, 21:45 UTC. BG02 remains incomplete. The original
108-case comparison and its causal counterexample are retained without rescoring.
The comparative research report predates that execution; its recommendation to
test equal policies, then native SciFact, original LAB-Bench and Inspect is unchanged.

Candidate versions are AsOf 0.3.13 and TETHER 0.5.2. The new replay verifier uses
the recorded response and eligible source records to reconstruct consumed requests
and check selections, accounting and feedback. Source-free verification declares
its weaker retained-dispatch binding. No model call is made by verification.

| Scope | Evidence and state |
|---|---|
| Regression correction | `green02` passes 25 focused tests, including quote/retry boundaries; the retained diagnostic replay counterexample now rejects |
| Archive compatibility | `archive-profile/VALIDATION.json` passes 52 tests, with authentic legacy v1 receipt-only scope and retained v2 controls |
| Candidate wheel qualification | Fresh isolated two-wheel build/install and 14 commands pass: `data/cache/tether-052-installed-qualification-attempt01/QUALIFICATION.json`, SHA256 `7486fc505eaff3351238b6c5d05c19d8e969eba8398753a72ac9670aff180315` |
| Full gate attempt 01 | Failed after 136 tests: sandbox denied a required hard-link operation; cached packaging also failed. Preserve `integration/full-gate-01.*`; zero assertion failures does not make this a pass |
| Full gate attempt 02 | Aborted before child dispatch because the historical driver derives a globally shared temporary directory from the stem name; `data/cache/full-gate-02-temp` already existed. The before-source record remains. No existing directory was removed or reused |
| Full gate attempt 03 | Running under session 54110, with the unique `tether052-full-gate-03` stem, required filesystem permissions and existing offline uv cache. Poll that session; do not restart |
| Facade checks | 138 tests pass with zero failures/errors/skips and unchanged source/distribution metadata; `facade/VALIDATION.json` |
| Installed replay checks | Isolated 0.3.13/0.5.2 accepts the valid replay after its original input file is removed, and rejects the preserved EP075 diagnostic through all three tested verification surfaces; `INSTALLED-REPLAY-VALIDATION.json`. This does not complete the full release gate |
| Corrected comparison | Version-two corpus has 109 cases and 103 execution/evidence pins. The missing qualification closure is corrected; 42 runner and 40 independent reconstruction tests pass. Fresh old-runtime attempt02 and patched attempt01 pass independent preflight and are frozen, with hashes recorded in `../tether-equal-policy-v2-20261105/EXECUTION-STATE.json`. Neither corrected comparison has executed. First preparation and all previous results remain retained |

The new editable development environment is `data/cache/tether-052-dev`. Initial
setup encountered a sandbox cache-write failure and a simultaneous editable-source
URL conflict; separate offline editable core and facade installation succeeded.
Old installed 0.5.1/0.3.12 and all original comparison producers remain intact.

Next: complete the full gate and aggregate preservation check; run separate
four-arm comparisons against original and
patched installations; independently reconstruct every result and audit causes.
SciFact, LAB-Bench and Inspect remain subsequent, unfinished stages. Provider spend
remains zero. These are software conformance checks, not biological validation.
