# WP0 local checkpoint and sizing-protocol freeze

Local WP0 work completed on October 17, 2026. The recoverable code checkpoint is
`f36f548d2d1459d39a14346305f83c4d045d2e39`. It captures the previously uncommitted
October 17 work, the narrow status-correction writer and the frozen v0.4 protocol.
The subsequent closeout commit records this report and the current memory state.

- `validation.json` and stdout/stderr logs: full local validation, 175 tests,
  zero skips/failures/errors, required probes, PowerShell syntax and wheel/demo pass.
- `staging-whitespace-check.txt`: check passed while preserving hash-bound CRLF
  bytes. `.gitattributes` explicitly accepts CRLF; existing receipts were not rewritten.
- `preserve_local.py`: exclusive local recovery-copy recipe. It writes a new
  directory under the authorized E: project backups, verifies every archive entry,
  restores a sealed milestone and clones the Git bundle. It performs no deletion
  or external transmission. Do not rerun it into an existing destination.
- `data/manifests/public/2026-10-17-wp0-local-checkpoint.json`: sanitized completion
  record, including local backup hashes and outstanding dependencies.
- `planning/protocols/registry-sizing-v0.4.json`: frozen before registry enumeration;
  freeze anchor is `data/manifests/public/2026-10-17-registry-sizing-v04-freeze.json`.

Recovery destination:
`E:/projects_data/drug_target_agents_data/backups/wp0-20261017-f36f548/`.
The local archive preserves 1,811 files / 719,427,970 source bytes in a
72,528,636-byte ZIP. Every archived payload was rehashed; the restored 21-file
milestone seal passed; the restored repository HEAD equals the code checkpoint.
`recovery-report.json` at that destination retains the full per-file list.

This is an on-machine recovery copy. It does not protect against loss of both
local drives. Bulk raw archives, database pages/credentials and large external
scientific payloads are excluded. No remote is configured, no push or hosted CI
was performed, and no off-machine destination was invented.

Catalog corrections are limited to AACT technical-restoration prose and observed
idle/incomplete ChEMBL/colocalisation collections. Dated acquisition snapshots,
transport receipts, access/role policy and scientific-validation status are preserved.
The status-correction proposal and file/process observation are retained separately
under `data/manifests/public/` and applied by the existing single catalog writer.

No registry-scale SQL, model call, new acquisition, database restart, clinical
label or power estimate was produced. Next: read-only origin/follow-up extraction
under the frozen protocol, with role ambiguity and mapping coverage reported.
