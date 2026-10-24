# Prospective frame preparation — October 24, 2026

Status: **offline request preparation complete; live source qualification pending**.
This implements the next technical step after the [readiness design](Prospective%20Endpoint%20Readiness%202026-10-23.md).
It preserves the original clinical scientific requirements and failed B0 stop.

`tools/science/prospective_frame.py` now builds and verifies an exact, dated,
non-dispatch request against the pinned protocol and archived official metadata.
It reserves a fresh output directory, records a hash-chained journal, pins code and
parents, restricts the nine requested leaf fields and retains unresolved query
semantics. There is no HTTP client or source-query execution path in this module.

Offline response checks reject results/other unrequested fields, malformed shapes,
wrong URLs/parameters, duplicate identities, token loops, truncation, count/version
drift, out-of-window dates and byte/time overruns. Screening retains unknowns;
deterministic selection is returned only after complete terminal enumeration.
The fixed cap is500 records, not the first500 of a larger universe. Capacity of
the proposed unfiltered30-day frame remains unmeasured. A cap failure would be a
source-acquisition limit, not evidence that authentic clinical rules are absent.

## Verification and corrections

- **834 tests pass, no skips**, required probes, PowerShell syntax, package and
  dependency-free demo pass. Full validation elapsed139.047seconds.
- **34 new tests**, including10 independent peer tests, exercise shape/temporal/
  complete-frame/source-boundary/lifecycle failures with synthetic study records.
- The same34 tests pass in an isolated clean source copy with no ignored data
  payloads. Root corrected the initial ignored-metadata fixture dependency by
  tracking four small public schema responses; they contain no trial records.
- Independent review corrections added the120-second per-request ceiling,
  immutable journal-pin support and exact array-shape checks. Runtime code and peer
  tests remain at their reviewed hashes. The old reviewed test source is retained
  separately because the subsequent portability correction changed its setup.
- Existing clinical artifacts were checked by hash only and remain unchanged.

## Actual retained request

Built2026-10-24T15:33:46UTC under
`data/benchmark/labels/prospective-endpoint-readiness-20261023/request-20261024T153346Z/`.

| Property | Retained state |
|---|---|
| Readiness capture dateR | 2026-10-24 UTC |
| Closed first-posting date interval | 2026-09-24 through2026-10-23 inclusive |
| Contract SHA256 | `3c92d09ab93c4269f74856692d5013888be78970f23eb715ca0a2c68d89fd51e` |
| Source study queries / selected members | 0 / 0 |
| Live transport / exposure inventory qualification | false / incomplete |
| Future clinical originF / probabilities | null / null |
| Provider spending / model calls | $0 / 0 |

This is not a current registry snapshot, cohort or clinical prediction freeze.
The candidate Essie date expression, leaf projection and pagination behavior still
require actual server qualification. Readable metadata does not establish these.
The actual capture must occur onR; an expired request cannot slide dates silently.

## Next planned work

Seal a known-exposure inventory from retained origin/membership manifests without
parsing old outcome answers. Implement and validate bounded, allowlisted source
transport with durable request/response receipts and actual deadlines. Then qualify
the exact server request under the fixed caps; preserve failures without retry,
partial sampling, cutoff adjustment or outcome-informed replacement. Only after
those gates pass may the fixed members receive an origin-rule availability audit.
Existing user authorization covers that safe sequential work; no new user archive
or human approval requirement has been established.

Earlier clinical training/calibration, scorer/predictors, H1 sidedness/Brier/
multiplicity, scientific reference quality, power and the later locked evaluation
remain unqualified. Future outcome labels are required for analysis after a genuine
prediction freeze, not before it. Source-readiness engineering does not close those
gates or original Tasks6–8.

Evidence is retained in `planning/review-assets/prospective-endpoint-readiness-20261023/`:
`full-validation.json`, `clean-checkout-validation.json`, `code-review.json`,
`request-freeze.json` and `frame-stage-acceptance.json`. The first clean-checkout
helper assertion mistook tracked `.gitkeep` placeholders for ignored payloads;
the corrected check verifies payload absence, without altering scientific inputs.

## Subsequent inventory checkpoint

Named-origin exposure inventory now records43,393 canonical NCT identifiers.
Its16 explicit sources total1,458,436,692bytes; projection/source-hash and all first
byte-locator checks completed in31.922seconds. Only identifiers were extracted;
related NCT mentions are conservatively included. No old outcome answers were
parsed. This is closure for named retained origin sources and the protocol's
incidental list, not universal agent/model-training exposure or holdout proof.

The new`exposure-bound-request-20261024T154310Z` binds all exclusions; contract
SHA256`53a60efdeb20bc3bf0dd8eaad0850498706902c755406b03f7253d60ba5c825c`.
Query bytes and dates remain identical, and selected members remain zero. Evidence:
`exposure-inventory.json` and `exposure-bound-request.json` in the tracked review
assets directory. The initial request stays immutable.

Bounded source transport is the active next implementation. It must pass synthetic
failure/limit/ownership guards and root review before a separate source execution
manifest is sealed. No actual study query has run at this checkpoint.

## Actual cold capture: frozen capacity gate failed

The transport and36 synthetic tests subsequently passed; full870/no skips,
probes, syntax and package/demo checks passed in171.516seconds.70 new frame/
transport tests also passed in an isolated clean source copy. Source manifest
`25e30b6a...` was committed at`f5fdab8` before the guarded one-shot runner ran.

Both actual HTTP attempts returned200:71-byte version and38,595-byte firstpage.
The source declared **4,277 records**; the first100 passed the requested nine-leaf
projection and interval checks (all September24firstpost). The frozen500-record
gate then stopped capture. No second page, after-version, complete-frame claim,
selected member, source-rule PDF, model call or clinical activation followed.
Both attempts have terminal receipts; unresolvedattempts and automaticretries are0.

`source-attempt-summary.json` and`source-stop-audit.json` retain the failure,
rawbody/manifest/journal hashes and sourcecoverage limits. This demonstrates
accepted first-request shape, not closed upper-bound or cross-page completeness.
An initial audit-helper mappingproxy serialization failure is retained separately;
the corrected audit reran only local verification and made no HTTP request.

The unfinished acquisition task is an **explicit capacity-only amendment**. A
reviewable option is max5000 records/page500/10pages, keeping the30-day universe,
interval, leaf fields, eligibility, exclusions, max12audit and20MiB/600s limits.
The archived API documentation describes pages up to1000;500 is only a proposed
new operating choice. Preserve the original sampling seed instead of changing
ordering when only transport caps change. At the observed count,9 pages would be
needed; sizes/time/full count stability remain unverified, not guaranteed by the
firstpage. Preserve failedv0.1 code/receipts and semantic no-redispatch claim. No
new cap is enacted by this paragraph and no source call should resume against the
failed manifest. This capacity result says nothing about authentic rule availability.
