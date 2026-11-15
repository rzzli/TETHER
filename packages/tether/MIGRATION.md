# Package and version compatibility

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
