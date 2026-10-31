"""Retain the never-executed V1 driver and create its bounded-cleanup successor."""
import hashlib
import json
from pathlib import Path

base=Path(__file__).resolve().parent
prior=base/"build_native_carrier_component_v1.py"
original=prior.read_bytes();text=original.decode()
text=text.replace('    results = []\n','    results = []\n    primary_dispatch_error = None\n',1)
start=text.index('    def run(label, argv):\n')
end=text.index('    terminal = "BUILD_FAILED"\n',start)
replacement='''    def run(label, argv):
        nonlocal primary_dispatch_error
        remaining = 60 - (time.monotonic() - start)
        if remaining <= 2:
            raise TimeoutError("Build work deadline before " + label)
        emit("dispatch_reserved", label=label, argv=argv)
        process = subprocess.Popen(argv, cwd=out, env=environment,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=False)
        error = None
        cleanup_errors = []
        first_stdout = first_stderr = None
        stdout = stderr = None
        output_complete = False
        kill_attempted = kill_acknowledged = False
        try:
            # Reserve bounded cleanup time INSIDE the unchanged60-second cap.
            stdout, stderr = process.communicate(timeout=remaining - 2)
            output_complete = True
        except BaseException as caught:
            error = caught
            primary_dispatch_error = dict(type=type(caught).__name__, message=str(caught))
            first_stdout = getattr(caught, "output", None)
            first_stderr = getattr(caught, "stderr", None)
            stdout, stderr = first_stdout, first_stderr
            try:
                if process.poll() is None:
                    kill_attempted = True
                    process.kill()
                    kill_acknowledged = True
            except BaseException as cleanup_error:
                cleanup_errors.append(dict(stage="kill", type=type(cleanup_error).__name__,
                                           message=str(cleanup_error)))
            cleanup_remaining = min(2.0, max(0.0, 60 - (time.monotonic() - start)))
            if cleanup_remaining > 0:
                try:
                    stdout, stderr = process.communicate(timeout=cleanup_remaining)
                    output_complete = True
                except BaseException as cleanup_error:
                    cleanup_errors.append(dict(stage="bounded_reap", type=type(cleanup_error).__name__,
                                               message=str(cleanup_error)))
                    newer_stdout = getattr(cleanup_error, "output", None)
                    newer_stderr = getattr(cleanup_error, "stderr", None)
                    if newer_stdout is not None:
                        stdout = newer_stdout
                    if newer_stderr is not None:
                        stderr = newer_stderr
            else:
                cleanup_errors.append(dict(stage="bounded_reap", type="NOT_ATTEMPTED_DEADLINE",
                                           message="No cleanup time remains; exit/pipe completeness may be unknown"))
        for suffix, value in (("first-error.stdout", first_stdout), ("first-error.stderr", first_stderr)):
            if value is not None:
                (out / (label + "." + suffix)).write_bytes(value)
        # Keep each first-visible prefix even if a later cleanup disagrees.
        for channel, first, latest in (("stdout", first_stdout, stdout), ("stderr", first_stderr, stderr)):
            if first is not None and latest is not None and not latest.startswith(first):
                cleanup_errors.append(dict(stage="output_reconciliation", type="PREFIX_MISMATCH", channel=channel))
                output_complete = False
        (out / (label + ".stdout")).write_bytes(stdout if stdout is not None else b"")
        (out / (label + ".stderr")).write_bytes(stderr if stderr is not None else b"")
        row = dict(label=label, argv=argv, pid=process.pid,
                   returncode=process.returncode,
                   stdout_bytes=len(stdout) if stdout is not None else None,
                   stderr_bytes=len(stderr) if stderr is not None else None,
                   output_complete=output_complete,
                   primary_error=primary_dispatch_error if error else None,
                   cleanup_errors=cleanup_errors, kill_attempted=kill_attempted,
                   kill_acknowledged=kill_acknowledged,
                   main_exit_observed=process.returncode is not None)
        results.append(row)
        emit("dispatch_returned_or_failed", **row)
        if error:
            raise error  # The original error survives kill/reap failures.
        if process.returncode != 0:
            raise RuntimeError(label + " returned " + str(process.returncode))

'''
text=text[:start]+replacement+text[end:]
text=text.replace('failure = dict(type=type(caught).__name__, message=str(caught))',
                  'failure = dict(type=type(caught).__name__, message=str(caught), original_dispatch_error=primary_dispatch_error)',1)
text=text.replace('process_scope="Known subprocesses killed/reaped on failure; no OS-wide descendant attestation",',
                  'process_scope="Known main process cleanup attempted within remaining cap; original and cleanup failures separate, incomplete pipes/exit explicit; no OS-wide descendant attestation",',1)
output=base/"build_native_carrier_component_v2.py"
raw=text.encode()
with output.open("xb")as stream:stream.write(raw)
record=dict(schema_version=1,status="NAMED_TRUSTED_BUILD_DRIVER_CORRECTION_NOT_EXECUTED",
    before=dict(path=str(prior),bytes=len(original),sha256=hashlib.sha256(original).hexdigest()),
    after=dict(path=str(output),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),
    finding="Independent finite prebuild review: V1 kill or unbounded second communicate could replace the original timeout/interruption and lose partial output/result evidence.",
    correction="Reserve2seconds inside60 for bounded cleanup; retain original error/prefixes independently, record cleanup failure and unknown output/exit, never retry a build command or execute the image.",
    limits="Kill and other OS calls themselves remain cooperative/unattested for whole-process descendants. A first timeout cannot become success because cleanup later observes exit0. No Job framework added.",
    activity=dict(builds=0,subject_or_native_runs=0,original_target_reads=0))
with(base/"NATIVE-CARRIER-BUILD-DRIVER-CORRECTION-v2.json").open("x",encoding="utf-8")as stream:
    json.dump(record,stream,indent=2);stream.write("\n")
if prior.read_bytes()!=original:raise ValueError("V1 preservation")
print(json.dumps(record["after"]))
