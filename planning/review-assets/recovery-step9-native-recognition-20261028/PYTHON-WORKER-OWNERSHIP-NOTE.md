# Windows Python worker identity and timeout scope

28 October 2026 UTC. The first actual source-acquisition attempt used the frozen
v2 helper and stopped before its HTTP code. Its child rejected the reservation's
parent PID. The protocol hash and deadline match; the failed attempt, eight-file
receipt and journal remain preserved. This is a transport/identity failure, not
evidence that any proposed upstream file is unavailable.

The [harmless parentage probe](PYTHON-PARENTAGE-PROBE.json) establishes the cause
for this runtime: launching the accepted virtual-environment `python.exe` creates
an intermediate launcher. Popen's PID identifies that launcher, while the Python
worker has another PID and reports the launcher as its parent. Normal exits in
the probe returned successfully. These observations do not themselves establish
what happens to descendants during forced termination.

The candidate correction launches the **canonical, hash-pinned base interpreter**
directly, using only a controlled `__PYVENV_LAUNCHER__` value to retain the approved
environment. The observed worker then equals Popen's PID and has the expected
parent, prefix, installed 0.3.11 distribution and `-I -B` flags. This is a qualified
configuration of this exact runtime, not a general guarantee about all launchers.
The [independent parentage review](PYTHON-PARENTAGE-PEER-REVIEW.md) retains those
limits.

The separate [forced-timeout fixture](PYTHON-DIRECT-WORKER-TIMEOUT.json) identifies
the actual worker before it sleeps, then kills and reaps that same owned handle
after a one-second timeout. It completes in 1.031 seconds. The
[independent timeout review](PYTHON-DIRECT-WORKER-TIMEOUT-PEER.md) verifies identities,
captures, the base executable hash and all 85 installed package files. No HTTP,
AsOf module body, native target or model runs in these fixtures. This is not a
general Job Object/process-tree containment proof.

V3 source-fetch preparation must bind the exact canonical base executable,
accepted environment context, worker PID/PPID handshake and timeout evidence.
It must retain the strict reservation check rather than accept an unexplained
parent mismatch. Writes outside the new D: cache and source scope remain forbidden.
The frozen v2 helper/protocol and failed output must not be rewritten or restarted.

Earlier Python-verifier records establish that their **launched handles** were
reaped. Without further evidence, that fact alone cannot establish termination
of every descendant after a forced timeout. No actual orphan or leak has been
demonstrated, and successful normal-exit replay results are unchanged. Native
converter stage executables were launched directly; this specific Python
redirector observation does not apply to those stage executables. Carry this
scope limit into the next full-project reassessment and future tool protocols.
