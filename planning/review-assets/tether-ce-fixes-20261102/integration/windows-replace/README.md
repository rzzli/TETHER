# Bounded Windows JSON replacement resilience

Two retained full-gate attempts encountered native `WinError 5` during
`serde.write_json` replacement of different fictional files. The earlier exact
test passed three isolated retries; that did not establish the environmental
cause or make the failed whole-gate attempts successful. No antivirus cause,
permission change or environment/security intervention is assumed here.

## Implemented contract

Only `src/asof/serde.py` changes. Its replacement step permits **three total
`os.replace` attempts**, with requested sleeps of **50 ms then 100 ms**, solely
on Windows for native error codes **5, 32 or 33**. Error 5 is generic access
denial and can be permanent; 32/33 identify sharing/locking failures. The policy
is bounded resilience, not classification of an error as transient. See
[Microsoft's error-code definitions](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-).

Serialization, staging, flush/fsync and close occur once. Retries use the same
staged file and destination; they never unlink the destination, rewrite payloads,
change permissions, copy as a fallback, or redispatch any model/provider call.
The final genuine OS exception retains its type, native error and filenames.
Interruptions are not retried. A secondary staging-cleanup failure adds a note
instead of masking an already pending primary failure or interruption.

Successful replacement retains the same primitive and overwrite behavior
documented by [Python](https://docs.python.org/3.11/library/os.html#os.replace).
`atomic.publish_bytes` and `maintenance.write_new_json` are unchanged: Windows
no-clobber rename and POSIX link publication are not replaced by this helper.

## Validation and limits

`VALIDATION.json` hashes the source, regression driver, result JSON and logs:

- Red: ten methods; five assertion failures and six errors including subtests.
- Green: **10/10 new methods**, zero skips, including two real Win32 private-file
  controls. A held deny-delete handle reproduces native WinError 5; release before
  retry permits success, while continued denial fails after three attempts.
- Related workflow/local-model tests: **72/72**, zero skips, including both
  original full-gate failing methods and the CE02 usage regressions.
- Atomic publication/catalog maintenance tests: **21/21**, zero skips, including
  existing concurrent no-clobber and write-failure controls.

Source `serde.py` SHA-256:
`fa910ce74c0766240eac3a64443b4b4baf7b6b64b064a1b028cda4ace66eb79c`.
The native handle experiment proves a reproducible mechanism, not the cause of
the original full-gate errors. This qualification permits failures that persist
beyond the bound. It does not guarantee successful publication under competing
writers or prolonged locks. Mutable `write_json` remains last-completing-writer-
wins, with no compare-and-swap or invocation-order guarantee; retry can widen
the time window in which competing writers complete in a different order.

The 150 ms bound describes requested backoff only, not time inside filesystem
calls or operating-system scheduling. General directory durability, hostile
external changes to staging files and cross-filesystem guarantees are unchanged.
Successful-path cleanup errors still propagate. When cleanup also fails after
a primary error, the staged path is reported in an exception note and may remain
for inspection; cleanup failure is not silently presented as success.

The separate peer stress exercise is under `integration/windows-replace-peer`.
Its outcomes, including any bounded denial under concurrent writers/readers,
must be retained; the scope above does not require every contending writer to
succeed. Full-gate rerun, archive-profile migration and independent review are
root-owned gates. No model execution, scientific data acquisition or provider
spending occurs in these focused tests.

## Reproduction

Use aligned `data/cache/tether-051-dev/Scripts/python.exe`, workspace-local
`TEMP`/`TMP`, and a **new** phase argument to `run_regressions.py`. The driver
refuses existing result/log names. Its default module is the new regression file;
additional module names select the related suites. `summarize.py` independently
checks retained hashes and refuses to overwrite the final validation record.
