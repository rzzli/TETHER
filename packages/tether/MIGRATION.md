# Package and version compatibility

## Shared file primitives

File/package proofs and bounded stable reads now live in
`tether_engine.file_proofs` and `tether_engine.stable_read`. The corresponding
`tether` aliases expose those same modules. The existing
`tether_engine.study.proofs` and `tether_engine.study.stable_read` paths remain
module-identity aliases, so their functions and monkeypatches share one
implementation. The maintained CLI no longer imports study drivers to read files.

The extraction preserves read bounds, caller-root checks, Windows sharing rules
and error behavior. Exact package proofs change because their source inventory
changes. Use the original code and wheel for old implementation-bound proofs;
this refactor does not migrate or reseal frozen scientific results. Historical
drivers and their public aliases are still present in this compatibility stage.

## Explicit source roots

Source-inclusive `verify_run`, public `verify_engine`/`verify_outer`, and
`evaluate_bound` now accept the keyword `source_roots=(Path(...), ...)`. The
corresponding `verify`, `evaluate` and `evaluate-baseline` commands accept
repeatable `--source-root PATH`. External normalized packets, originals,
download receipts and computation assets need caller grants. Serialized roots
in receipts or archived catalog policies cannot grant filesystem permission.

The caller-selected run directory and this executing package's fixed bundled
demo directory remain implicit roots. A copied demo in an arbitrary directory
needs an explicit grant; a producer's `synthetic_demo` declaration grants none.
The installed `tether demo` then `tether verify` quick start needs no new flag.
For bound evaluation, the selected producer-manifest directory contains its
local run artifacts; other referenced locations require explicit roots. The
cohort, producer and label files explicitly selected by the caller remain
readable without granting their entire directories to the producer manifest.

```powershell
tether verify --run-dir .\run --receipt-sha256 $receiptHash `
  --source-root .\normalized --source-root E:\projects_data\drug_target_agents_data
```

The public `tether run` also accepts these grants for its mandatory post-run
verification and checks required paths before dispatch. Its Python launcher
accepts `source_roots`. Native engine execution remains the trusted explicit
snapshot-input route; granting roots is not an OS sandbox for arbitrary agents.
An explicitly selected `PolicyRequest.roots_path` authorizes preparation; its
archived copy never authorizes a later independent verification.

Caller-selected root ancestors may be local directory links. They are resolved
once, with network/device targets rejected before inspection. Descendant links
are rejected. Source reads use no-follow handles, preflighted file identities
and hashes; originals are streamed rather than loaded wholesale. Installer
hardlinks are allowed for hash-bound source files, preserving uv's demo install;
portable bundle members retain their stricter single-link rule. These checks
trust the OS and do not claim exclusive ownership across an entire multi-run
evaluation. Source checks remain scoped to each run's verification.

Native run receipts and declared outputs also use no-follow reads. Interpretation
uses identity-checked bytes rehashed against the receipt, including the trace.
A sealed output journal may retain its owner's write handle; output reads permit
that handle and check for changes, rather than claiming an exclusive writer lock.
The verifier never opens an unsealed request just to report its presence.

Maintained pilot/replay utilities accept repeatable `--source-root`. The pilot's
explicitly selected normalized bundle is allowed, and all other original/receipt
paths are checked before its first child dispatch. The dossier-binding utility
forwards its existing `approved_roots` grants to native verification.

`--outputs-only` still reads no original sources and reports weaker assurance.
`--allow-legacy` alone does not authorize legacy source paths; combine it with
roots for source checks, or explicitly select outputs-only byte verification.
Existing receipts and scientific results must not be rewritten to add grants.

The public interface is `tether-target-agents` 0.7.0, with command and import path
`tether`. It pins `tether-target-engine` 0.5.0, imported as `tether_engine` and
invoked directly as `tether-engine`. Public aliases share the engine's class and
module identities; no former namespace shim is installed.

## Current identities

| Contract | Identifier |
|---|---|
| Feature schema | `tether-features-v2` |
| Shared scientific wire format | `tether-shared-scientific-fields-v1` |
| Normalized product / method | `tether_normalized_packets` / `tether.opentargets.normalize` |
| Installed engine proof | `installed_tether_engine_package` |
| Study arm / stage key | `tether_interpretation` / `tether_stages` |
| Outer presentation / launcher proof | `tether.engine_presentation.v2` / `tether.launcher_code.v2` |
| Dossier projection | `identity_dossier_v2` (exact byte copy) |

## Upgrading

Install both distributions into a clean environment using the current lockfiles.
Editing import paths does not update installed wheel metadata or entry points.
Use public `tether` aliases or the `tether_engine` namespace in consumers.

New artifacts must bind the current identities and code proofs. If a source-backed
conversion is required, create a new derived artifact with complete lineage;
never edit the bytes or receipt of a sealed original in place. Renamed catalog
products require new artifact grants.

New version-two runs require policy `tether.derivation.v1`. Known engine 0.4.0
version-two receipts retain limited byte verification; semantic consistency and
derivation are unavailable in that route. Use the original matching checkout for
its exact semantic replay. Generic version-one byte verification remains supported.
Both legacy formats now require `tether verify --allow-legacy`, or
`verify_run(..., allow_legacy=True)` in Python. Without that opt-in they fail the
default semantic request. Their successful byte checks have status
`byte_integrity_verified`, not `integrity_verified`; no receipt is rewritten.
Portable bundles with missing originals or unsupported replay require the existing
explicit `--bytes-only` / `replay=False` mode. Consumers should inspect `assurance`
and source/semantic fields instead of interpreting every successful exit as full
verification. Current supported source-inclusive runs keep their existing status.
See [historical compatibility](../../docs/ARCHIVE.md) and
[verification limits](../../docs/TETHER-VERIFICATION-SCOPE.md).

## Packet availability correction

Packet envelopes also enforce their declared information availability and temporal
classification, using the same policy as source lineage. A future or unverified
packet cannot inherit an eligible status from its parents. These existing v2 fields
describe the information, not the time the packet file was generated. Registered
computations performed later on eligible old inputs remain supported. If an older
builder put file-creation time in these fields, rebuild a new source-backed packet
with justified information bounds; do not edit a sealed original or automatically
replace its dates. Native verification re-applies this gate to admitted claims and
the required source-proof inventory.

## Evaluation migration

Current scientific chronology helpers normalize timezone-aware ISO instants to
UTC and reject timezone-free, compact/week-date and sub-microsecond strings that
would otherwise be ambiguous or silently truncated. Input/model information
available exactly at a feature origin now follows the engine's inclusive boundary.
Reference-panel year/month publication dates are treated as full periods; a period
overlapping its cutoff no longer passes by padding the first month/day. Original
dated qualification reports are unchanged and should be read under their recorded
rules. These changes do not qualify scientific labels or authorize fitting.

Publication eligibility is also stricter: a same-day publication without a time
does not establish eligibility before that day's end, and a year-only publication
overlapping the cutoff is `publication_timing_unresolved`. Previously, the latter
passed with otherwise eligible information lineage. A consistent full date is
used instead of its coarse year. Preserve old packets and qualification results;
do not rewrite their dates to satisfy current checks. New source packets should
retain supported precision and explicitly report unresolved publication timing.

Normalization `2.3` applies that gate before writing new packets, rejects malformed
supplied dates and reports partial `publicationDate` values that the day-only
contract cannot represent. It retains `publicationYear` support. Existing `2.2`
products and their original source-review results stay unchanged; a new build is
a distinct product, and current revalidation may exclude formerly accepted rows.

The former `evaluate --predictions ...` command is now `evaluate-raw`. Its Python
counterpart remains `tether_engine.evaluation.evaluate`; both report unverified
prediction provenance. Their corrected report uses schema version 2. Existing
prediction and outcome wire formats are unchanged; archived metric files retain
their original semantics and must not be relabelled as corrected evaluations.

`evaluate` now requires explicit cohort, producer and outcome manifests with
their expected SHA-256 hashes. `evaluate-baseline` uses a separate external
producer declaration. Both require an explicit fixed-horizon policy, including
reporting lag. See [evaluation contracts](../../docs/FRAMEWORK.md#fixed-horizon-evaluation).

These changes remain in the unreleased engine 0.5.0 / wrapper 0.7.0 development
series. Retain the exact Git checkpoint and wheel hashes: a version string alone
does not identify a development build. Source-inclusive engine verification can
report `code_matches_current: false` for a same-policy run from an earlier build;
the evaluation binding retains that fact. Exact outer/launcher verification
still needs the original build and is not relaxed by this evaluation interface.
Keep accepted environments and originals; use a separate installation for the
new evaluation code. Portable cross-version verification remains future work.

## Computed evidence policy, November 2026

The case/snapshot/packet wire version remains 2. New optional `derivation` fields
on observations and source nodes are omitted when absent; all older fields keep
their existing encoding. Original v2 fixture bytes and canonical fingerprints
remain unchanged. New execution always enforces the strict policy, including for
directly constructed stores; there is no legacy execution option.

A computed record needs a supported immutable descriptor binding exact input
and asset hashes, registered method/version and implementation, parameters and
their digest, output schema, method date and timing mode. The first method is
`tether.json_projection` v1 with parameters `input` and `pointer`. Output schemas
are `observation.v2` and `canonical_json.v1`. Projection preserves the complete
source information; it cannot replace prose or numerical fields. Keep information
availability dates from the source and put the later execution time in `computed_at`.
The method date is local registration evidence, not a trusted public timestamp.

Previously arbitrary computed fixtures must be rebuilt as new derived artifacts
from complete eligible inputs; they cannot be upgraded by filling in a method
name or copying the claimed output's hash. Do not alter sealed originals.
See [the worked fixture builder](../../tests/derivation_fixtures.py) and
[execution tests](../../tests/test_derivation_execution.py).

Receipt policy, run policy and configuration must match. Dropping the policy
from a current-engine receipt does not make it a legacy run. Legacy verification
checks only its declared byte inventory and cannot qualify a new run. The old
archive semantic dependency resource is unchanged; new-policy relocated replay
is a later supported-workflow task, not implied compatibility.

## Receipt-read build correction, 7 November 2026

The historical engine 0.4.0 development build bounded Windows `EACCES` retries while
reading an archived receipt. It does not retry publication, change receipt bytes,
or alter lineage, temporal eligibility, claims, features or scoring semantics.
The exact ingestion module pin is updated in the archive dependency declaration;
the executing build profile is `tether-engine-0.4.0-receipt-read-v2-20261107`.

The semantic policy remains `tether-engine-0.4.0-20261106`. Every declared module
still requires one exact reviewed hash, and unsupported engine versions remain
rejected. The predecessor resource hash records which declaration changed; it
does not grant compatibility with arbitrary source files. Reports retain the
executing dependency-resource hash to distinguish builds.

Existing environments, sealed receipts and original source proofs are preserved.
Use a fresh installation to check this build; changing checkout files does not
update an installed wheel. Qualification must exercise archive reconstruction and
receipt handling together against that installation, including rejection of an
incorrect module pin. Earlier results retain their original source identities.

## Preparation deadline correction, 7 November 2026

Five preparation helpers now compare absolute monotonic endpoints. Subtracting
the current clock from an endpoint created exactly 300 seconds ahead can round
slightly above 300 and incorrectly reject that endpoint. The absolute comparison
accepts the declared limit and rejects the next representable value above it;
no tolerance or additional execution time is granted.

Helpers that return remaining time cap that duration at 300 only after validating
the endpoint. They explicitly reject booleans as endpoints. Expired and nonfinite
values remain invalid. These changes affect source-code proofs and require fresh
qualification; existing sealed artifacts and recorded timings are not rewritten.

On 15 November, tokenizer preparation/replay additionally began capping a longer
parent deadline at the existing local 300-second limit. Shorter parents are never
extended. Source/retrieval preparation retain their separate endpoint ceilings.

## Study-driver seal boundary

Current study drivers retain writable failure journals until terminal receipt
publication. A failure while staging or syncing the receipt leaves an unsealed
attempt with its original accounting. After atomic publication, cleanup or
presentation errors preserve the receipt and journal; callers should inspect and
verify the retained record rather than repeat the call. Older drivers that
withdrew a receipt after publication retain their original-runtime reproduction
path. No archived result or receipt is rewritten by this change.

Deadline enforcement includes the final pre-publication gate after staging/sync;
it does not promise preemption of a blocked OS publication syscall. Receipt formats
and original byte conventions are unchanged. Study package-code pins still require
the matching implementation for exact historical replay.

## Windows owned-process containment

Native CLI, tokenizer and owned-server execution now share a core Windows Job
Object controller. It assigns the suspended initial process before execution and
closes the job on cleanup; inherited descendants also stop if the owner exits
abruptly. Assignment/resume faults retain the owned process handle and do not
trigger a replacement call. Existing receipt fields remain unchanged and do not
retroactively certify containment for older implementations.

This path is qualified with finite Python fixtures on Windows CPython 3.11 and
3.14; an installed 3.14 wheel demo and anchored verification also pass. Other
platforms and trusted injected process factories retain the previous single-child
scope. External brokers and hostile host compromise are outside this lifecycle
guarantee. Historical scientific artifacts retain their exact-runtime replay path.

## Correctness and reporting corrections

Budget decisions and semantic replay now sum the decimal representations of USD
amounts exactly. Three 0.10 charges fit a 0.30 cap; even a smaller-than-float-display
overrun is rejected. Numeric wire totals remain floats. Historical rounded totals
that do not reconcile with their events need their original runtime; they are not
rewritten or silently accepted. Zero-cost archived runs remain supported.

JSON parsing rejects nonfinite exponent results, invalid Unicode, excessive
nesting and excessively large integers with `ContractError`. Dependency component
identity no longer depends on display labels. This repairs accidental grouping;
it does not validate numerical features scientifically.

The retained source-validation utility writes `PENDING_TERMINAL_SEAL` before
publication. Consumers must verify the bound terminal seal to establish successful
execution, and must not promote `intended_status` alone. Local storage failures
are fatal `local_io_failure` events rather than evidence of source unavailability.
Changed utility hashes require a fresh qualification/freeze for any new execution.

Reason-qualified conformance reporting requires explicit expected rejection
reasons, valid-case controls and the full scheduled denominator. Legacy decision
agreement is retained under its original meaning. Missing scientific measurements
remain distinct from available identifiers; all-null measurement coverage is null.
