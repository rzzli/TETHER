# R07 compatibility profile review

The 0.3.1 native consumer adds two study modules and uses the unchanged 0.3.0
proof/session/process/diagnostic interfaces. No R04 top-level semantic helper
changes. The only top-level change is the version string in `asof/__init__.py`.
The previous legacy guard must refuse that byte change before a reviewed update.

The next executing-build profile updates only this version-file hash and retains
the previous resource hash. Original v1/v2 inputs, receipts, code pins, the seven
restored families and accepted R06 artifacts remain unchanged. The new native
consumer is not imported by the legacy compatibility engine. Its own package
proof includes the complete new code/resource inventory.

The source gate ran under 0.3.0. All 36 compiler source files were copied and
rehashed as inert data before changing the version; no archived compiler is
executed. Scientific admission helpers are unchanged, and the gate's rebuilt
request exactly matches R05. Native wrappers retain original response bytes and
are separately verified through the trusted 0.3.1 consumer, not legacy adapters.

Acceptance requires final source-frozen tests/package checks and seven installed
legacy replays. A prior green report is not a current-profile replay. Successful
native callbacks remain outside the old legacy archive support matrix; this
native diagnostic has its own terminal-seal verifier and declared local provenance,
not a remote execution or scientific attestation.
