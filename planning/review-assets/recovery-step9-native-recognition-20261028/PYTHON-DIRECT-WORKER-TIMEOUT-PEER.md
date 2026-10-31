# Direct-worker timeout: retained evidence verified

The exact authored fixture and retained stdout/stderr support its narrow result:
**the timed-out worker was the process represented by the owned Popen handle**.
Worker PID/Popen PID were both 13808; worker PPID/owner PID were both 38280.
The fixture killed and reaped that handle after its one-second timeout; recorded
wall time including cleanup was 1.031 seconds and return code was nonzero.

The peer checked the helper and result hashes, raw captures, expected venv
context/version/isolation flags, all 85 accepted installed package files, and
the canonical base executable plus nine file/ancestor components without
reparse violations. The base is the canonical `cpython-3.11.15` path, SHA256
`d2ec5b9401b6471874373fe3e4329da1da85014d98f8abedd4e0f02ffdaa21a1`;
the earlier `cpython-3.11` spelling should not replace this exact path in v3.

[The peer record](PYTHON-DIRECT-WORKER-TIMEOUT-PEER.json) binds the full evidence.
This satisfies the harmless forced-timeout prerequisite for preparing the same
direct-base/controlled-venv transport. The new source helper/protocol must bind
these records, retain strict PPID checks and compare reported worker PID to the
owned Popen PID. It still needs separate exact-hash review and root authorization
before a source request.

This was one authored print-and-sleep worker, not a fetch test, process-tree
sandbox, OS attestation or native-model qualification. Its statically small
output and post-capture size assertion do not replace the fetcher's live capture
caps. No fixture was rerun or imported by the peer; no HTTP, native or GGUF call
was made. Previous parentage reviews remain unchanged.
