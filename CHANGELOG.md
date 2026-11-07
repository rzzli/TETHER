# Changelog

## Unreleased

- Bound receipt archive verification to eight read attempts for Windows access
  contention, retaining exact-byte checks and propagation of persistent errors.
  Publication itself is never retried. Existing receipt bytes remain unchanged.
- Canonicalize temporary fixture roots before recording path identities, and
  classify Windows-only tokenizer fixtures explicitly in portable CI. Runtime
  path and file-sharing protections remain enforced.
- Rebind the archive dependency declaration to the reviewed receipt-read build.
  Preserve its semantic policy and exact-hash rejection of unsupported code;
  qualify archive and receipt behavior together in a fresh installation.

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
