# Python parentage: narrow transport correction

The retained harmless probe supports preparing a **direct base-interpreter
worker with controlled accepted-venv context**. It does not yet qualify forced
timeout cleanup or authorize another source request. Exact evidence is in
[the peer record](PYTHON-PARENTAGE-PEER-REVIEW.json).

The reviewer checked the probe source/hash and all three raw stdout/stderr
pairs. Normal venv launch produced a separate worker: launched PID 30780,
worker PID 26472, worker PPID 30780. Direct base launch produced worker PID equal
to the retained Popen PID. Adding only controlled `__PYVENV_LAUNCHER__` pointing
to the accepted venv retained version 0.3.11, expected prefix and `-I -B` while
worker PID 18132 equalled Popen PID and PPID 32896 equalled the owner.

The exact base executable still hashes to
`d2ec5b9401b6471874373fe3e4329da1da85014d98f8abedd4e0f02ffdaa21a1`.
All **85 accepted installed package files** remain unchanged. The logical
`sys.executable` value under this context names the venv; the actual fixed argv
must name the pinned base executable.

Before a new v3 fetch:

- Freeze a new helper/protocol; preserve the consumed v2 output and decision.
  Pin/lease the base executable through a narrow read-only exception for that
  exact external path; retain venv configuration/launcher and package pins.
- Update both fixed argv and the parent subprocess audit's executable check.
  Set the one controlled venv-context key in the minimal child environment.
  Keep strict PPID equality; also require reported worker PID equals Popen PID,
  expected base/prefix/version and isolation flags before source qualification.
- Run a harmless forced-timeout fixture with that exact transport. Establish
  worker identity before its bounded sleep, kill/wait only the owned handle,
  and record worker exit, captures and cleanup. A normal-exit probe cannot
  substitute for this check. Root/peer exact-hash review precedes any HTTP call.

The failed v2 receipt's eight output hashes and seven-event journal verify.
There are zero source files and no child-started marker; the failure occurred
at the strict reservation check before urllib import/request. Its actual worker
PID was not recorded. The new probe demonstrates a launcher mechanism consistent
with this failure; it does not retroactively supply the missing worker identity.

Earlier timeout/reap wording should therefore say **the launched Popen handles
were reaped**. Where that handle belonged to a venv launcher, the retained
records alone do not prove descendant-worker termination. Neither orphaning nor
resource leakage is established. Successful hash-verified replays remain valid;
their scientific guarantees are unchanged. Direct native-EXE children are a
separate transport and are not invalidated by this Python-launcher observation.

This peer review performed only stdlib reads/hashes. It launched no probe or
helper and made no HTTP, native, tokenizer, model or GGUF call. No process-tree
sandbox or full OS/interpreter attestation is claimed.
