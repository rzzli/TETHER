# Pinned asset transport

Downloads an approved manifest into a new attempt directory. It does not extract
archives, install dependencies, load weights, retry or resume partial downloads.
The existing project downloader is unchanged.

```text
python -I -B <absolute-download.py> --manifest <manifest.json>
  --manifest-sha256 <external-sha256> --code-sha256 <source_fingerprint()>
  --output <existing-approved-root/new-attempt>
```

Use the ordinary CLI on Windows: the parent owns a process job, reserves the
attempt once, supervises one worker, retains process/stdout/stderr records and
rehashes every published payload before writing `RECEIPT.json`. The internal
worker and injected-stream API are not independently approved acquisition routes.
Portable tests substitute invented HTTP streams and exercise real Python child
success, failure and timeout; they do not establish real-service access.

The manifest has `schema_version: 1`, `kind: alce_acquisition_manifest_v1`,
`approved_root`, `allowed_hosts`, `limits` and ordered `assets`. Each asset binds
its ID/product, revision, HTTPS URL, relative destination, exact byte count,
content SHA256 or Git-blob SHA1, metadata proof and rights reference. A local
SHA256 is always retained. Missing sizes and digests are rejected. Code archives
without known transport hashes need a separate verified acquisition protocol.

Limits cover aggregate bytes, whole-attempt seconds, socket seconds, stalled
worker seconds and redirects. Reads are at most 1 MiB. Every redirect stays on an
exact approved HTTPS hostname. Partial/range and encoded responses are rejected.
Signed redirect query strings are replaced in receipts by hashes. The total
budget includes parent preflight, transfer and final streaming rehash. A parent
watchdog permits up to 10 additional seconds for termination cleanup; OS process
creation and uninterruptible kernel I/O remain OS boundaries.

```text
attempt/
  RESERVATION.json, COMMAND.json, REQUEST.json, INPUT-MANIFEST.json
  journal.jsonl
  payloads/<manifest destination>
  partials/<asset ID>.part                 # retained on failure
  receipts/<asset ID>.started.json
  receipts/<asset ID>.json
  WORKER-RECEIPT.json                     # transfer complete, not final approval
  PROCESS.json, stdout.bin, stderr.bin
  RECEIPT.json                           # verified parent completion only
```

Failures retain available partials and `FAILED.json` or
`SUPERVISOR-FAILED.json`; a stopped worker may leave a timeout marker instead of a
terminal record. Abrupt host failure can prevent terminal persistence. An existing
attempt is never reused or overwritten.

Consumers require an externally anchored root receipt, its worker receipt and
manifest proofs, exact selected asset membership and a fresh payload hash check.
Placement or an unanchored status is insufficient. Transfer receipts do not
establish scientific validity, archive safety, redistribution rights or historical
availability.
