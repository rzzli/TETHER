"""Pinned census-observation sealer: SDK v3 body, one success-status literal change.

All ownership, cleanup, hashing and failure semantics are retained.
"""
from pathlib import Path
import time


def make_sealer(sdk):
    safe, file_pin, write_new, require = sdk.safe, sdk.file_pin, sdk.write_new, sdk.require
    def seal_post_lease_cleanup(output, api, leases, primary_failure, earlier_status, started, deadline):
        'Always retain close outcomes separately from the immutable early receipt.\n\n    A terminal seal is mandatory even when an earlier receipt exists. Every\n    authoritative failure marker wins; missing terminal seal is incomplete.\n    '
        output = Path(output).absolute()
        original_marker = earlier_receipt = None
        outcomes, close_errors = [], []
        for record in reversed(leases):
            outcome = dict(path=record["path"], handle=record["handle"],
                           validation=record["validation"], closed_before=record["closed"],
                           prior_cleanup_errors=list(record["cleanup_errors"]),
                           primary_validation_error=record.get("primary_error"),
                           close_attempted=False, close_return_observed=False,
                           close_success=None, close_error=None)
            if not record["closed"]:
                outcome["close_attempted"] = True
                try:
                    require(api is not None, "No API available for a tracked live lease")
                    api.close(record["handle"])
                    record["closed"] = True
                    outcome.update(close_return_observed=True, close_success=True)
                except BaseException as error:
                    close_error = dict(error_class=type(error).__name__, error=str(error)[:512])
                    outcome.update(close_success=False, close_error=close_error)
                    record["cleanup_errors"].append(close_error)
                    close_errors.append(dict(path=record["path"], handle=record["handle"], **close_error))
            outcome["closed_after"] = record["closed"]
            outcomes.append(outcome)
        cleanup_path = output / "post-lease-cleanup.json"
        try:
            output = safe(output, output=True)
            original_marker = file_pin(output / "failure.json") if (output / "failure.json").exists() else None
            earlier_receipt = file_pin(output / "receipt.json") if (output / "receipt.json").exists() else None
            expired = time.monotonic() >= deadline
            cleanup = dict(schema_version=1, status="failed" if close_errors or expired else "close_outcomes_retained",
                           earlier_status=earlier_status, primary_failure=primary_failure,
                           primary_failure_marker=original_marker, earlier_receipt=earlier_receipt,
                           parent_elapsed_after_leases_seconds=time.monotonic()-started,
                           parent_deadline_exceeded=expired, close_errors=close_errors, outcomes=outcomes)
            write_new(cleanup_path, cleanup)
            late = None
            if close_errors or expired:
                late = dict(schema_version=1, authoritative=True, automatic_retry=False,
                            phase="post_receipt_lease_cleanup", error_class="LeaseCleanupOrParentDeadline",
                            primary_failure=primary_failure, primary_failure_marker=original_marker,
                            cleanup_artifact=file_pin(cleanup_path), close_errors=close_errors,
                            parent_deadline_exceeded=expired)
                write_new(output / "late-failure.json", late)  # Never replaces a primary marker.
            failed = bool(primary_failure or original_marker or late or earlier_status == "failed" or earlier_receipt is None)
            outputs = {}
            for path in sorted(output.rglob("*")):
                if path.is_file():
                    item = file_pin(path)
                    outputs[path.relative_to(output).as_posix()] = {key:item[key] for key in ("bytes", "sha256")}
            seal = dict(schema_version=1, status="failed" if failed else "module_census_observations_retained_not_ABI_qualification",
                        required=True, earlier_receipt=earlier_receipt, cleanup_artifact=file_pin(cleanup_path),
                        primary_failure_marker=original_marker,
                        late_failure_marker=file_pin(output / "late-failure.json") if late else None,
                        outputs=outputs, parent_elapsed_before_terminal_seal_seconds=time.monotonic()-started,
                        failure_veto="failure.json, late-failure.json or after-seal-failure.json override any seal; missing terminal-seal.json is incomplete")
            write_new(output / "terminal-seal.json", seal)
            if time.monotonic() >= deadline:
                write_new(output / "after-seal-failure.json", dict(authoritative=True, automatic_retry=False,
                          error_class="ParentDeadlineAfterTerminalSeal", terminal_seal=file_pin(output / "terminal-seal.json")))
                seal["status"] = "failed"
            return seal
        except BaseException as primary:
            # A failed terminal artifact cannot be repaired/retried in place. Even
            # with an earlier primary failure, attempt a separate late supplement.
            if not (output / "late-failure.json").exists():
                try:
                    write_new(output / "late-failure.json", dict(authoritative=True, automatic_retry=False,
                              phase="post_lease_cleanup_or_terminal_sealing", error_class=type(primary).__name__,
                              error=str(primary)[:512], primary_failure=primary_failure,
                              primary_failure_marker=original_marker, close_outcomes=outcomes))
                except BaseException:
                    pass
            raise
    return seal_post_lease_cleanup
