# TETHER engine namespace migration

This release separates the public `tether-target-agents` 0.6.0 interface from
`tether-target-engine` 0.4.0. The engine's import path is `tether_engine`; its
console command is `tether-engine`. The facade retains `tether` as its command
and public import path. Public aliases share the executing engine's class and
module identities; no former namespace alias is installed.

The original implementation is preserved at source checkpoint `b492a8f`, tagged
`tether-pre-namespace-migration-20261106`. Original data, model captures and run
receipts remain original evidence. This migration does not rerun experiments,
re-seal historical results, or certify them under new source fingerprints.

## New identities

- Distribution/runtime pins: engine 0.4.0 and interface 0.6.0.
- Feature schema: `tether-features-v2`; scientific wire format:
  `tether-shared-scientific-fields-v1`. Field structures retain their existing
  versions; the renamed identifiers denote distinct contracts.
- Normalized product: `tether_normalized_packets`; method:
  `tether.opentargets.normalize`.
- Installed package proof: `installed_tether_engine_package`, with code/resource
  logical IDs rooted at `tether_engine/`.
- Study arm/key names: `tether_interpretation` and `tether_stages`. The packaged
  study plan is re-pinned to its changed bytes; its original source checkpoint
  remains the authority for historical plan hashes.
- Outer presentation: `tether.engine_presentation.v2`, launcher proof
  `tether.launcher_code.v2`, and exact dossier copy `identity_dossier_v2`.
- Archive executing-dependency policy: `tether-engine-0.4.0-20261106`, with a new
  explicit module-hash inventory. This does not reinterpret old code proofs.

## Verification and upgrading

Reinstall both distributions into a clean environment using the updated lockfiles.
Changing import paths in a virtual environment does not migrate already-installed
wheel metadata or scripts. Update consumers to the new engine import path, or use
the public `tether` aliases. New artifacts must carry the new identities and
source proofs. A source-backed migration, if needed, is a new derived artifact,
not an in-place rewrite of a sealed original.

Version-two semantic verification rejects a different engine software version;
use that run's original checkpoint. Generic version-one byte-integrity checks
remain supported, with semantic consistency explicitly unavailable. None of
these checks establishes scientific validity. The semantic experiment remains
paused while this naming migration is implemented and qualified.

See the [repository migration report](../../docs/TETHER-NAMESPACE-MIGRATION.md)
for preserved evidence, package qualification and regression results.
