# Archived replay correction: current qualification status

Checkpoint: 5 November 2026, after full release validation and comparison closure. BG02 is complete within its finite exposed-conformance scope. The original
108-case comparison and its causal counterexample are retained without rescoring.
The comparative research report predates that execution; its recommendation to
test equal policies, then native SciFact, original LAB-Bench and Inspect is unchanged.

Locally qualified versions are AsOf 0.3.13 and TETHER 0.5.2. The new replay verifier uses
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
| Full gate attempt 03 | Terminal PASS/exit0 under session 54110: 2,100 tests, zero failures/errors/skips, probes and offline packaging pass; unchanged source bracket. Whole run 2,192.125 seconds |
| Facade checks | 138 tests pass with zero failures/errors/skips and unchanged source/distribution metadata; `facade/VALIDATION.json` |
| Installed replay checks | Isolated 0.3.13/0.5.2 accepts the valid replay after its original input file is removed, and rejects the preserved EP075 diagnostic through all three tested verification surfaces; `INSTALLED-REPLAY-VALIDATION.json` |
| Final release aggregation | `RELEASE-AGGREGATE-FINAL01.json` passes all eight scopes; SHA256 `d966fa3f74fa5ace029a041642a279bcacef346aa70df65f7bc048733835b01e`. See `CANDIDATE-RELEASE-COMPLETION.md` for distinct installed and full-gate wheel identities |
| Corrected comparison | Version-two corpus has 109 cases and 103 execution/evidence pins. The missing qualification closure is corrected; 42 runner and 40 independent reconstruction tests pass. Fresh old-runtime attempt02 and patched attempt01 pass independent preflight and are frozen, with hashes recorded in `../tether-equal-policy-v2-20261105/EXECUTION-STATE.json`. Both sessions 3300 and 87679 are terminal exit0, each with 1,308 cells and agreeing independent reconstruction. Original TETHER conforms on 108/109 cases; patched TETHER and independent conform on 109/109. Causal review is complete; the original replay defect and higher patched TETHER cost are retained. First preparation and all previous results remain retained |

The new editable development environment is `data/cache/tether-052-dev`. Initial
setup encountered a sandbox cache-write failure and a simultaneous editable-source
URL conflict; separate offline editable core and facade installation succeeded.
Old installed 0.5.1/0.3.12 and all original comparison producers remain intact.

See the [BG02 completion report](<../../TETHER Equal Policy Comparison Results 2026-11-05.md>) for results, resources, evidence and limits. Next: implement and evaluate native SciFact.
SciFact, LAB-Bench and Inspect remain subsequent, unfinished stages. Provider spend
remains zero. These are software conformance checks, not biological validation.
