# Final preparation-suite launch: retained sandbox failure

The first final 40-test preparation launch on 1 November used the sandbox's
default `tempfile` directory. It ended with 36 errors in 1.439 seconds. The
tracebacks reported `PermissionError: [WinError 5] Access is denied` during
temporary-directory operations/cleanup under the sandbox package's `AC/Temp`.
The tool output was truncated; no complete on-disk transcript was created for
that launch. This note records that evidence limitation rather than fabricating
a full log. No production source was changed in response.

The explicit workspace-local TEMP/TMP rerun passed all 40 tests in 2.214 seconds.
The complete transcript is `ROOT-PREPARATION-AND-PACKAGE-TESTS-final-v3.txt`.
This environment correction does not erase or diagnose the separate earlier
non-sandbox Windows sharing errors in the broad v2 runs.
