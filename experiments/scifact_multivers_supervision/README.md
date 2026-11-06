# Qualification process supervision

`supervise.py` starts exactly one pinned, isolated Python script. It never retries.
The process deadline includes imports before the child creates any output. The
case deadline begins at the child's `case_started.monotonic_seconds` and includes
both model forwards plus case output and assertions. Python's monotonic clock is
shared across processes on the qualified Windows runtime. Completed events must
occur before the case deadline, including when start and completion arrive in the
same polling read.

The parent polls at most every 0.25 seconds and kills only its owned child PID on
timeout or interruption. The qualification child must use no subprocess workers.
Python scheduling and bounded local event reads can add polling latency; parent
source hashing and finalization are cooperative local I/O outside the owned-child
deadline. The controller does not claim a hard deadline for those parent I/O
operations. Model imports are never allowed outside the child process deadline.

The root supplies an externally hashed manifest, with all paths absolute:

```json
{
  "schema_version": 1,
  "kind": "multivers_qualification_supervision",
  "cwd": "D:/Projects/drug_target_agents",
  "launch_output": "D:/Projects/drug_target_agents/planning/review-assets/tether-semantic-20261106/solver-qualification/actual-launch-attempt01",
  "qualification_output": "D:/Projects/drug_target_agents/data/benchmark/scifact_multivers/qualification-20261106-attempt01",
  "limits": {"process_seconds": 1800, "case_seconds": 120, "poll_seconds": 0.05},
  "schedule": ["exact ordered IDs from the pinned fictional-controls.json"],
  "command": ["absolute pinned python.exe", "-I", "-B", "-X", "utf8", "absolute pinned qualify.py", "--acquisition-root", "absolute completed acquisition directory", "--receipt-sha256", "actual completed receipt SHA256", "--reference-bundle", "absolute source receipt directory", "--output", "same absolute qualification_output", "--device", "cuda:0"],
  "pins": [{"path": "absolute resolved file", "bytes": 123, "sha256": "actual SHA256"}]
}
```

This is a schema illustration, not an executable actual manifest. `pins` must
include the interpreter, supervisor script and child entrypoint. The root must
also include the fictional controls, full adapter source closure, frozen source
receipts/original files, acquisition receipt and environment inventory/fingerprint
authorities. All supplied pins are checked before and after the run, never per
case. Paths in pins use the canonical native spelling returned by `pin()`.
The two output trees must be unused, disjoint workspace directories. The command
supports direct script entrypoints and `-I`, `-B`, `-u`, `-X value` flags.

Launch with a qualified interpreter:

```text
python.exe -I -B -X utf8 experiments/scifact_multivers_supervision/supervise.py --manifest ABSOLUTE_MANIFEST --manifest-sha256 EXTERNAL_SHA256
```

Before the child starts, the parent retains `FROZEN.json` and `COMMAND.json`.
`stdout.txt`, `stderr.txt` and the child's output remain intact for every outcome.
`OUTCOME.json` records process exit, source preservation, deadline scope and each
scheduled case's observed state. A case is completed only after its matching
retained completion event. The current case gets timeout/interrupted/failure;
later cases are unexecuted according to the event protocol. An incomplete next
start line is recorded as `unknown_start`. A successful exit without the full
ordered schedule and terminal event fails. These are execution dispositions and
never fabricated model labels, evidence or benchmark scores.

Run the standard-library-only tiny-child controls in a new output directory:

```text
data/cache/tether-scifact-env-attempt02/environment/Scripts/python.exe -I -B -X utf8 experiments/scifact_multivers_supervision/qualify.py --output ABSOLUTE_FRESH_OUTPUT
```

The retained qualification contains test logs, source/interpreter pins and each
real child's command, output and outcome. No test imports torch, loads checkpoint
weights, reads benchmark examples or dispatches inference.
