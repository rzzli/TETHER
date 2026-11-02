# CE02 validated usage on failed local selection

The correction preserves validated adapter-reported usage when a local response
exceeds its reservation. It does not authenticate physical token consumption and
does not turn malformed or otherwise unqualified responses into measured usage.
All transports in this qualification are fictional in-process objects. No actual
model, network request or provider charge occurred.

## Correction

`src/asof/local_model.py` introduces `LocalUsageReservationExceeded`, retaining the
direct caller's `ContractError` boundary and carrying `BackendFailure.usage` into
the existing workflow. Before raising, the adapter retains `measured_usage` and
`failure_kind=usage_reservation_exceeded`. The existing workflow accounts that
usage, emits the violation, returns `budget_exhausted`, and performs no further
dispatch. No workflow source change was necessary.

The execution-archive checker now reconciles account counts, attempt IDs and
reservations; checks retained failed-response hashes; recomputes already valid
reported usage; requires its measured accounting and terminal dispatch; and binds
the violation event. Malformed/unqualified content or invalid token counts remain
unknown, with the exact conservative reservation charged. Frozen journal mappings
are accepted without relaxing usage validation.

Archive schema remains 1. Valid historical normal/unknown-failure shapes retain
compatibility; a historical archive that discarded valid over-reservation usage is
not granted stronger semantic verification. Its original bytes are preserved,
not rewritten. The root integration versions this correction as engine 0.3.12;
original 0.3.11 artifacts and their version-specific guarantees remain separate.

## Retained evidence

- `red-results.json`: eight initial regression methods on the original runtime
  hashes; six failed assertions (including subtests) and one exception-type
  mismatch reproduce the defects. Other controls pass.
- `green-results.json`: first implementation attempt fails because decoding
  numeric zero as a float changed fingerprint comparison. This is retained.
- `green2-results.json`: the original eight methods pass after using validated
  numeric Usage equality rather than comparing re-encoded zero representations.
- `green3-results.json`: eleven methods pass after additional accounting/order,
  response/usage and missing-violation controls.
- `compatibility-results.json`: initial broad run exposed immutable-journal
  decode compatibility and four test-loader imports. Both issues were corrected.
- `green4-results.json`: all twelve final new regression methods pass, zero skips,
  including immutable journal forms, measured usage, one-call termination,
  malformed content/types and transport failures.
- `compatibility2-results.json`: all 122 existing focused adapter/framework/role
  tests pass, zero skips. These do not include the twelve new methods.
- `SETUP-ATTEMPTS.json`: two interrupted setup attempts before the working
  workspace-temp runner; neither is represented as a completed regression run.

The final local-model source hash is
`1bdd8f50e2db729cd8854e1ba3859e71de70833ac70a11a9ff3d0a24a56697e4`.
The workflow hash remains
`eafb5f8646e8d64d7aa797f636d66e3d321646cd859e92020973d01c15c9fcf6`.
See result JSON for the authoritative full hashes and original failure traces.

## Repeat in a fresh result namespace

Use workspace-local `TEMP`/`TMP` (for example
`D:\Projects\drug_target_agents\data\cache\ce02-test-temp`) and the aligned
`data/cache/tether-051-dev/Scripts/python.exe`. The runner rejects an existing
result name rather than overwriting evidence:

```powershell
$env:TEMP = (Join-Path (Get-Location) 'data/cache/ce02-test-temp')
$env:TMP = $env:TEMP
data/cache/tether-051-dev/Scripts/python.exe planning/review-assets/tether-ce-fixes-20261102/ce02/run_regressions.py fresh-regressions
data/cache/tether-051-dev/Scripts/python.exe planning/review-assets/tether-ce-fixes-20261102/ce02/run_compatibility.py fresh-compatibility
```

Full release qualification and the independent peer review are root-owned gates;
these focused checks alone do not certify the whole release or scientific results.
