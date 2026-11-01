# Active P09 checkpoint

Updated 1 November 2026, approximately 22:00 UTC. This is a working handoff,
not a passing release report. The owner deferred author declarations; do not ask
again during engineering or invent facts. P08c/P10 author facts remain pending.

## Qualified reconstruction

Final corrected protocol: `e28461a5681bcaaae89752f0cf7e1ac6fb644c4eebdf501a1f2c2ec7c26dd529`.
READY-v2 was committed at335b880 before dispatch. Bundle source is
`data/cache/p09-runtime-bundle-20261101T213500Z`. Actual C: qualification root is
`C:\Users\zzric\AppData\Local\Temp\asof-p09-20261101T204845Z`:
`bundle-release-v2`, `originals`, `env`, `env-core`, `reconstruction-v2`, `audit-v2`.
All137 original files/receipts remain complete; original E: files unchanged.

Final reconstruction289.938s/481636352B peak passes38 raw hashes/90 decisions.
Reporta0f4e0e76ad5dfd746664c69023549cb0bf23fd74316b02a40ef85c54bfd8acb;
receiptb184839bdedea102e022786de51bd7fcec062e2eb232c45699b6d55444814b8e.
Final source audit6,862PASS15.187s/298418176B peak:
reportb7e8bdd49fe0a29a78277a65ba627e405b652b6aa5e060f930796421958f62ca;
receiptc981dfe9d5964b8be6d2fd49ccdfc5300be3eeb60628c2ae8f998c1fbbbe1977.
Exact159-file archive under
`data/derived/preprint-p09-installed-20261101T205500Z/revision2/`.
All38 raw outputs and12 references are byte-identical to initial revision.
Peer revision2 metadata review passes3,481 checks. No extra provider-source pass.

Original protocol650859b1/run remains retained. Its source-test command omitted
`-B`, producing4 .pyc files in its temporary C: bundle after successful initial
audit. Canonical D: bundle never changed. New draft/READY corrects only the README
and authority;310 other members/100 package payloads/4 test files unchanged.
Corrected -B suite82PASS182.260s; clean312-file bundle unchanged. Do not delete
the original cache-drift evidence. Reference comparison still removes ONLY
method.catalog_sha256; runtime-scenario root/timing comparisons are separate.

## Framework gates: NOT qualified

First full gate:1941 tests/3 errors/0 skips,2332.406s. First core gate:1941 tests/
10 errors/86 allowed skips,2757.468s. All10 probes/offline wheel demos passed.
Both complete failed reports/logs are retained. Missing imports concealed32 tests.

Corrected tests only (no src/asof changes): explicit package/top-level fixture
imports; invented controller input fixture replacing old private catalog/data
coupling; interpretation setup writes adapted case once rather than overwriting
copy (original transient WinError5 cause unknown, controlled handle reproduction
and byte-equivalence retained);8 true-Parquet optional guards retain4 pure tests
and reject installed wrong Arrow. Combined76 tests PASS11.361s. Current committed
test fixes:31a98ed. All78 frozen P05 source pins remain unchanged.

Second complete gates started about21:52 UTC:

- Full live exec session74317; report `data/cache/p09-full-validation-v2-20261101T215100Z.json`;
  log `FULL-VALIDATION-v2.txt` in this directory.
- Core live exec session80156; report `data/cache/p09-core-validation-v2-20261101T215100Z.json`;
  log `CORE-VALIDATION-v2.txt`.
- **Full-v2 already has one ERROR** in
  `tests.test_science_comparison_evaluation.ComparisonEvaluationTests.test_complete_synthetic_six_arm_postseal_integration_without_inference`.
  Standard unittest prints its traceback only at suite end. Exact targeted test
  passes3.044s; full19-test module passes37.474s. Cause UNKNOWN. Do not increase
  timeout, add retries, skip or claim corrected without terminal traceback.
- Core-v2 has no observed error at this checkpoint; await terminal report.

Poll the same exec handles; do not restart existing processes on observation
timeout. CRLF log monitoring must match `\.\.\. (ERROR|FAIL)` without a `$`
anchor, which previously hid live errors. Do not claim a passing full gate.

## Next operations

1. Await both terminal reports; debug full-v2 exact error. Preserve failures and
   validate real corrections. No publication/package qualification before gates.
2. Finalize public qualification JSON with strict packager contract from
   `tools/science/package_p09_release.py`; final protocol above, evaluator-only,
   scientific validity/independence not established, declarations deferred,
   publication false. Never export private scenario roots/raw/reference values.
3. Build/readback/repeat-check positive-allowlist ZIP using
   `paper/release/PACKAGE-README.md`. Its final anchors/costs already updated;
   inner frozen bundle retains earlier paper snapshot. No actual ZIP built yet.
4. Apply the conditional P10 wording **v2** only once gates pass. Preserve inner
   frozen paper bytes. Rebuild current working PDF with PDF skill marker once,
   ordered-text/failure/visual/repeat QA; update content audits. No author facts.
5. Prepare local working submission package, retain R01-R16/HR status and memory,
   timestamp commits. P08/P10 remain incomplete while owner facts deferred.

Both PDF skills were read; the marker has NOT been run for this next manuscript
operation. Renderer is unchanged `tools/science/build_preprint_manuscript.py`;
bundled Python runtime/Poppler available. No need dependency downloads. The skill
operation marker must run immediately before authoring, exactly once.

No model calls/new downloads/paid queries/accounts or worker/monitor changes.
Source cards, rights exceptions and136 external OT originals remain explicit;
exact reacquisition is untested. No current hosted result or native Linux claim.
Goal API retains an older blocked state and cannot be resumed by tool; manual
work continues under owner steering. Do not create a replacement/complete goal.
