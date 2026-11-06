# Bounded SC02 public acquisition

This new, standard-library-only helper downloads the root-approved manifest into one fresh attempt. It neither invokes the old downloader nor installs packages or deserializes model weights. Root launches the actual CLI after qualification and review. There is no retry or resume mode. Existing attempts, partials, receipts and errors remain unchanged.

Use a qualified Python with `-I -B`, an explicitly fresh workspace pycache prefix and workspace `TEMP`/`TMP`. The CLI requires the exact manifest and helper source SHA-256:

```text
python -I -B -X pycache_prefix=<fresh-workspace-prefix> <absolute-download.py> --manifest <absolute-manifest.json> --manifest-sha256 <manifest-sha256> --source-sha256 <download.py-sha256> --output <fresh-absolute-attempt>
```

Do not invoke the internal `--worker` path or the injected-stream API for actual acquisition: only the ordinary CLI applies the parent watchdog. The supervisor atomically reserves the fresh root, writes `SUPERVISOR-STARTED.json`, and launches exactly one worker. Its command and worker execute the same pinned `download.py`; all imported dependencies are standard library. The worker authenticates the parent reservation and may not reuse an already started directory.

The worker is hard supervised for two hours total and 30 seconds without a control heartbeat. HTTP operations also use a socket timeout no greater than 30 seconds. Each at-most-1-MiB `read1` and streaming hash update sends an internal heartbeat; only per-asset completion and approximately 256-MiB progress updates are printed and retained in the journal. There is no large post-download checksum scan that could starve the watchdog. A stopped worker is killed and reaped; bounded cleanup may add up to five seconds plus one second for the pipe reader. The parent's final small journal/root-receipt writes are cooperative local I/O, not independently hard-preempted; an external outer command bound is needed to include a hung parent filesystem operation in a hard total ceiling. This timing scope is recorded, not presented as a whole-process attestation.

Manifest validation checks its exact fields, unique case-insensitive output IDs, Windows-reserved names, immutable HF commit URLs, exact S3 version URL, expected sizes, required upstream wheel hashes, allowed HTTPS source hosts, aggregate size and the 9,000,000,000-byte ceiling. Public requests disable inherited proxy handling. Every redirect is checked before following it and at most five are allowed. Content encoding other than identity, duplicate selected headers, HTTP partial/range responses, unexpected sizes, mismatched source versions or hashes abort the attempt without retry.

Payload layout is:

```text
<attempt>/wheel/<logical_id>
<attempt>/checkpoint/fever_sci.ckpt
<attempt>/tokenizer/{config.json,vocab.json,merges.txt,tokenizer.json}
```

Each payload has an adjacent `<logical_id>.started.json` and immutable `<logical_id>.receipt.json`. Streaming writes use `<logical_id>.partial`. A complete, verified file is published without replacing any destination. On failure, its partial and failure receipt remain; later assets are unexecuted. SHA-256 is computed over every successful file. Checkpoint ETag/version equality binds the requested S3 object but is not called an upstream SHA-256; the recorded local digest must be verified before any later deserialization. HF files additionally verify `X-Repo-Commit`, ETag and the exact Git blob SHA-1 calculation, and retain their local SHA-256.

Root `RECEIPT.json` exists only after the worker's success receipt, successful process exit and journal completion validate. Its schema has `schema_version: 1`, `status: "PASS"`, `manifest_sha256`, `source_sha256`, `root`, `total_payload_bytes`, `files`, `supervision` and `journal_tail_sha256`. Every `files` entry has `kind`, `logical_id`, absolute `path`, `relative_path`, absolute `receipt_path`, `bytes`, local `sha256`, source/final URLs, expected size/hash, observed ETag/version/repo commit, timestamps and `status: "completed"`. Root status is **PASS**; per-asset status is **completed**. The solver/installer must verify the complete expected 30-file manifest correspondence and file hashes independently before use.

The worker retains `STARTED.json`, the exact `INPUT-MANIFEST.json`, `journal.jsonl`, and either `WORKER-RECEIPT.json` or `FAILED.json`. The supervisor adds `SUPERVISOR-FAILED.json` on failure, including interruption or watchdog termination; a killed worker need not have had a chance to write its own failure receipt. The journal binds sequence number, previous event hash and canonical event bytes. A truncated/corrupt journal is preserved and reported, not rewritten. `KeyboardInterrupt` is retained where caught. Sudden host power loss or forced termination of the supervisor itself cannot be guaranteed a terminal record; absence of the root PASS receipt means the attempt is not usable as completed acquisition.

`qualify.py --output <fresh-review-directory>` runs the invented tests, retains a three-file fake acquisition, and checks the actual 30-asset manifest against `dependency-lock.json` and `requirements.lock.txt` without contacting any endpoint. The first test run preceded implementation and its expected red import failure is retained under `acquisition/qualification-red01/TEST-FIRST.json`.
