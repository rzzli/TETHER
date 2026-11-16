# Changelog

## Unreleased

- Add pinned correctness lint, staged strict typing/formatting, and a reviewed
  Windows/3.11 parent-process coverage baseline. Keep tooling out of runtime dependencies.
- Repair the wrapper lockfile and qualify the noneditable README quick start.
  Preserve platform-skipped test source identities and distinguish absent ingestion
  dependencies from broken or incompatible installations. Linux WSL core/export
  checks pass; hosted Windows/Linux/macOS CI qualification remains pending.
- Prepare retained CI reports, measured fast-gate timing and concurrency limits;
  add contribution, security, citation and explicit platform/assurance guidance.

- Build slim engine `0.6.0.dev1` and wrapper `0.8.0.dev1` wheels. Preserve core
  CLI and archive commands; remove historical study drivers, resources and 35
  aliases from default installations. Preserve original source/tests at `6b20498`
  and require separate matching environments for historical reproduction.
- Extract file proofs and stable reads into core modules, retaining module-identity
  aliases at the two former study import paths. Reject stale research payloads
  in wheel validation; list historical tests without importing their drivers.

- Require explicit `--allow-legacy` / `allow_legacy=True` for known legacy byte
  verification. Default portable verification now fails when semantic replay is
  unavailable; explicit `--bytes-only` remains supported. Weaker results report
  `byte_integrity_verified` and a distinct `assurance` field.
- Share review/state and dossier reconstruction checks across verification paths.
  Normalize caller receipt/manifest anchors and distinguish parent receipt bindings
  from independently supplied anchors. Apply the public CLI's code policy to bare
  native run directories as well as outer presentations.

- Bound receipt archive verification to eight read attempts for Windows access
  contention, retaining exact-byte checks and propagation of persistent errors.
  Publication itself is never retried. Existing receipt bytes remain unchanged.
- Canonicalize temporary fixture roots before recording path identities, and
  classify Windows-only tokenizer fixtures explicitly in portable CI. Runtime
  path and file-sharing protections remain enforced.
- Rebind the archive dependency declaration to the reviewed receipt-read build.
  Preserve its semantic policy and exact-hash rejection of unsupported code;
  qualify archive and receipt behavior together in a fresh installation.
- Compare shared preparation deadlines as absolute timestamps, avoiding false
  rejection of an exact 300-second limit through subtraction roundoff. The cap
  remains unchanged; expired and nonfinite endpoints stay rejected, and remaining
  time helpers explicitly reject booleans.
- Accept the immutable task sequence when validating a production refinement
  frame. The former list comparison rejected qualified frames before dispatch;
  regression coverage now exercises the actual JSON-to-immutable loading path.

## Interface 0.6.0 / engine 0.4.0

- Standardize the engine distribution, imports, commands, resources and serialized
  identities on TETHER. The public command and namespace remain `tether`.
- Use exact dossier copying and matching-version semantic verification.
- Retain generic version-one byte checking with explicit semantic limitations.
- Require new artifact grants for newly named products; preserve original sealed
  runs under their original code and proof identities.
- Keep the default runtime dependency-free, with optional PyArrow 21.0.0 ingestion.
- Publish reusable source requirements without local collection state or artifact
  grants; keep working notes, drafts and generated outputs outside the public tree.

See [upgrade guidance](packages/tether/MIGRATION.md) and
[historical compatibility](docs/ARCHIVE.md). Earlier source versions and their
change records remain in Git history.
