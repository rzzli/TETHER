# Package and version compatibility

The public interface is `tether-target-agents` 0.6.0, with command and import path
`tether`. It pins `tether-target-engine` 0.4.0, imported as `tether_engine` and
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

Version-two semantic verification rejects different engine software identities;
use the original run's matching checkout and dependencies. Generic version-one
byte verification remains supported, with semantic consistency unavailable.
See [historical compatibility](../../docs/ARCHIVE.md) and
[verification limits](../../docs/TETHER-VERIFICATION-SCOPE.md).
