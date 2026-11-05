# Archived replay verification correction

The source-tree correction closes the EP075 defect confirmed in the preserved
BG02 comparison. The original experiment, qualified installed environment,
scores, oracle and copied diagnostic remain unchanged. A later installed release
and separately frozen comparison are still required before making a new result
claim.

## Change

- `src/asof/agents.py` factors the existing replay lookup into the pure
  `replay_selection` helper. Runtime quote/select behavior and cursor advancement
  remain unchanged.
- `src/asof/replay_validation.py` checks retained schema-v2 replay provenance,
  source-reconstructed requests, consumed response order, reservations, usage,
  reviewed IDs and retry feedback. It calls neither quote nor select and never
  opens the original replay path.
- `src/asof/artifacts.py` checks recorded replay before publishing a new run and
  during nonlegacy archived verification. Source-inclusive verification rebuilds
  requests from eligible observations. `verify_sources=False` binds responses to
  archived dispatch fingerprints only and reports that weaker scope explicitly
  in `replay_binding`. Legacy-v1 receipt scope is unchanged.

Unused response entries and extra role keys remain legal because the actual
ReplayBackend permits them. Missing entries, wrong request fingerprints or
negative usage can legitimately produce a retained quote failure with no dispatch.
A zero-call budget, exhausted retry, interrupted selection, and partially failed
run therefore do not become invalid merely because they contain unused or failed
responses. The original replay byte hash remains an opaque retained declaration;
JSON reformatting and disappearance of the original file do not invalidate an
otherwise valid retained document.

## Retained validation

| Record | Result | Meaning |
| --- | --- | --- |
| `red01.json` / `.log` | 19 tests; 11 failures, 2 errors | Before source changes: tampered archived responses were accepted; explicit binding metadata was absent |
| `green01.json` / `.log` | 19 passed | Initial correction |
| `red02.json` / `.log` | 25 tests; 2 failures | Additional probes exposed repeated terminal quote failures and an undercount of reconstructed failed-quote requests |
| `green02.json` / `.log` | 25 passed, no skips | Final focused source-tree regression qualification |
| `RETAINED-COUNTEREXAMPLE-RESULT.json` | PASS | The unchanged EP075 copied counterexample now rejects the replay mismatch in both verification modes |

Each focused record pins tested source files, the test file and the captured log,
and brackets sources before/after testing. Exact source snapshots are retained
alongside each record. `qualify_replay.py` writes fresh exclusive outputs for a
supplied tag; do not overwrite old records. `check_retained_counterexample.py`
preserves and checks the original frozen inputs and diagnostic.

Final tested hashes:

| File | SHA-256 |
| --- | --- |
| `src/asof/agents.py` | `d6517766232959f2fc0f9d5d84b3fc181c35774cb4dac32df2d88f99bcc4d2fc` |
| `src/asof/artifacts.py` | `bb8027adea7bc2719f24895db9afbe05b44281231ee0a7a3e29592047290cd98` |
| `src/asof/replay_validation.py` | `9ac7442fe07d5d82c6516d2e2bc214d68354c8e2e1e216ed40dc872cb5c45905` |
| `tests/test_replay_archive_verification.py` | `7c4b1c7b51b210b84bf4bfbdf90bc9f0365804f1dde52467ec09b83dc972b3c7` |

These are finite software regression results, not a new scored BG02 comparison
or scientific validation. Full project/release validation and fresh installed
qualification are owned by the release workflow. No provider call, model,
download, old environment modification or frozen-corpus modification occurred.

## Fresh candidate checks

The later source-tree facade qualification passed 138 tests with no skips and
unchanged source/metadata brackets; see `facade/VALIDATION.json`. The profile
migration passed 52 archive tests and preserved historical controls; see
`archive-profile/VALIDATION.json`.

After the independent installed-release qualification reported PASS, the prepared
`check_installed_replay.py` ran under the new isolated 0.3.13/0.5.2 interpreter
with `-I -B`. A fresh eight-call fictional recorded run verified after deletion of
its original replay-file copy. The unchanged EP075 diagnostic counterexample
rejected for the request-fingerprint mismatch on the live core source-inclusive,
live core archived-only and facade engine surfaces. Installed package bytes,
qualification bytes and the counterexample remained unchanged. The retained
index is `INSTALLED-REPLAY-VALIDATION.json`; the full payload inventory and result
are under `data/cache/tether-052-installed-replay-attempt01/RESULT.json`.

These additional checks do not replace the preserved scored BG02 comparison or
the separate full-suite release gate.
