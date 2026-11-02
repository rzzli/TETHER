# CE03: all-input receipt availability

The correction applies the existing public-download receipt relationship to every
supplied raw policy input, including explicitly granted inputs that no accepted
packet uses. Preparation and verification call the same pure
`asof.provenance.check_receipt_availability` helper as used-ancestor verification.
Receipt identity, bytes and source paths are still checked separately. The helper
adds no original-file hashing pass, and the policy binding format is unchanged.

A declared `public_download_receipt` bound must not precede receipt completion;
its evidence reference must identify the exact receipt, and its source URL must
match. Other documented availability bases retain their existing rules. A later
download is not silently interpreted as proof of historical availability.

## Evidence

- `red-v2/results.json`: 9 regression methods, 5 failures, zero errors/skips before
  the source fix. The unused-node cases reached dispatch or passed resealed
  verification; equivalent used-node cases already rejected.
- `green-v1/results.json`: the same 9 methods pass after the source fix.
- `related-v2/results.json`: 85/85 methods pass, zero skips, using the source and
  metadata aligned TETHER 0.5.1 / engine 0.3.12 development environment. This
  combines CE03, catalog policy/binding, store temporal and source-fact-source
  suites; it overlaps the standalone 9 and must not be added as independent tests.
- `legacy-create-v2/results.json` and `legacy-verify-v1/results.json`: the retained
  installed 0.5.0 / 0.3.11 code produced three fictional policy seals. Corrected
  code accepts the valid unused-input seal and the valid alternative-basis seal,
  while rejecting the contradictory unused-input seal that old code accepted.
  This is policy-seal compatibility, not a full old engine run verification.

The new tests cover used/unused date and evidence-reference contradictions, missing
receipt-derived bounds, URL mismatch, future cutoff, exact/conservative valid
bounds, alternative availability bases, no child dispatch, archived controls
resealed around invalid metadata, and retained receipts/raw proofs. Every source
and receipt is fictional. No scientific claim or publisher authenticity follows.

## Retained unsuccessful audit attempts

`red-v1` exposed two test-helper problems: an unconstrained dispatch mock returned
a nonserializable object, and the resealing helper normalized unchanged source
catalog bytes. Both were corrected before the meaningful `red-v2` baseline.

`related-v1` ran while root advanced source versions, leaving that interpreter's
installed metadata stale; default Windows temporary-directory cleanup also failed.
The runner now confines temporary files to workspace cache and the rerun uses the
aligned development interpreter. No version or filesystem protection was bypassed.

`legacy-create-v1` used the correct frozen code (hashes retained), but the fixture
loader temporarily inserted checkout paths, shadowing the reported distribution
version. The loader now restores its original search path before recording
metadata; `legacy-create-v2` is the authoritative compatibility producer.

## Reproduction

`run_regressions.py OUTPUT_DIR [TEST_MODULE ...]` requires a new output directory.
Use the aligned development interpreter; the authoritative suite names are in
`related-v2/results.json`. `check_archive_compatibility.py create CACHE_DIR
OUTPUT_DIR` uses the retained 0.5.0/0.3.11 environment with `-I`; `verify CACHE_DIR
OUTPUT_DIR` uses the corrected environment. All output destinations are exclusive.
Fictional old seals remain under `data/cache/tether-ce03-legacy-seals-v2`; compact
version, hash and decision records are retained here.

Changed implementation: `src/asof/provenance.py` and
`packages/tether/src/tether/_catalog_binding.py`. New regression file:
`packages/tether/tests/test_ce03_receipt_time.py`. Root owns the version bump,
combined qualification, current documentation and commit.
