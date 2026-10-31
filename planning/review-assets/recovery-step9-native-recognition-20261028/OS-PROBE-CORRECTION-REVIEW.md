# Corrected Windows Job probe: scoped source clearance

Exact helper
`fdd651b4393cf0afd7e86061c710d2210a4d44aafe74a374fe27f90e4c265590`
has **no remaining material blocker within this OS-only fixture scope**.
The original `81a2a834…0c2e994` helper remains preserved as
`probe_windows_job_pre_review.py`; the earlier
[draft findings](OS-PROBE-DRAFT-REVIEW.md) remain unchanged.

The corrected nested cleanup closes the created job in an unconditional finally,
even if termination or wait fails. If job termination does not reap the owned
worker, bounded wait/kill/wait fallback addresses that exact process handle,
including failed assignment. Process handles are closed after reaping; bounded
active-process queries occur while the job remains open. No unrelated process
or enumerated PID is targeted.

Output and child paths now require resolved cache containment and fresh checks
of the full existing ancestry for symlinks/Windows reparse attributes. Child
mode, leaf name and parent directory prefix are constrained. The parent reserves
exclusive directories and publishes authorization only after successful job
assignment and an active-worker query.

The source asserts queried flags `0x2108`, active limit one and 64 MiB process
commit cap. The resource fixture requires the selected quota error 1816 rather
than treating arbitrary spawn failures as proof. All fixture diagnostics must
be empty. Direct worker identities, finite ready/wait/cleanup intervals and the
explicit termination exit code 87 are checked.

For kill-on-last-handle closure, a ready marker precedes the child's fixed
thirty-second sleep; prompt reap after closing the last job handle supplies the
intended observation. **No nonzero exit-code requirement is needed**: the
documented termination behavior does not specify that value. This corrects the
overly strict recommendation in the prior draft review. A successful fixture
would qualify this observed configuration, not a general OS scheduling or
process-tree guarantee.

Imported wintypes names and static x64 layouts remain consistent with the prior
source review. This clearance is readiness only. The peer imported or executed
no helper, called no Windows API or target DLL, and made no network, GGUF,
tokenizer or model access. Root's explicit finite OS-only execution decision is
separate from this review.
