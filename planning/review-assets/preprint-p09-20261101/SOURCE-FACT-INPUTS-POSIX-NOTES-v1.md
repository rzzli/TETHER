# InputTests fixture platform boundary

Only `tests/test_study_source_fact_inputs.py` and focused probes/evidence were changed by this repair. No production lock, source-admission, eligibility, date, receipt, schema or value logic changed. The main test count remains 12.

The previous Ubuntu/full mismatch was concrete: seven tests call preparation, whose first metadata lock fails closed outside Windows. Before correction, a controlled Windows probe set only the production lock module's OS namespace to POSIX and reproduced that rejection in the positive invented preparation test. No Linux process or provider input was used. The original source SHA256 was `4d2313e402e07e3621635485478b8fa8ac0af1d32f4103f2c89cd101d68e77e6`.

The test-only boundary now leaves `inputs.stable_files` untouched on Windows. Off Windows it injects a Python context restricted to that test's fresh absolute fixture root. It requires existing unlinked regular files, checks root and path components for symlinks/reparse points and aliases, rejects traversal/outside paths and multiple-link files, and enforces deadlines. An `ExitStack` restores the original function after each test. This fictional context provides no operating-system locking guarantee.

Validation under the existing Windows environments:

| Check | Result | Seconds |
| --- | --- | ---: |
| All 12 methods with genuine Windows lock implementation active | PASS, no skips | 1.329 |
| All 12 methods with only the test module's OS branch set to POSIX | PASS, no skips | 0.922 |
| Existing no-Arrow core environment | Four pure methods pass, eight canonical optional skips | 0.004 |

The simulation leaves Windows, production `stable_read.os` and source policy unchanged. Additional scope probes admit a valid inside file and reject missing, outside, empty, directory, relative and traversal inputs. Explicit `lstat` shape controls reject symlink, reparse, hardlink and linked-parent cases; no actual link/junction creation or POSIX filesystem behavior is claimed. An expired deadline is rejected. A separate controlled call to the original production primitive still rejects the POSIX OS namespace. There are 13 recorded boundary checks including the valid-file control. The unmodified source/date/eligibility and integrity assertions all remain in the 12 main methods.

This is **not Linux or native-source qualification**. It removes the known unqualified fixture-lock assumption while preserving the production unsupported-platform boundary. A read-only peer review passed. No installs, source/provider reads, model calls or network operations occurred; all input bytes were freshly invented fixtures.

Final SHA256 pins:

- `tests/test_study_source_fact_inputs.py`: `d4cec8bff8944c1c9c96519e9526473b648e5982d3b3768d774eac02342713eb`
- `check_source_fact_inputs_posix_v1.py`: `cbbdb22e29c28355e578de87367de6c6e56babb41a9e9da7cfc5ae6c5a317ab8`
- `SOURCE-FACT-INPUTS-POSIX-before-v1.json`: `fd1c46cd523d7cf374c077646db73366699d773ffd04692337285a50f40aa3ae`
- `SOURCE-FACT-INPUTS-POSIX-after-v1.json`: `d5d8d4a2a6fabfe8d3dae3042b7f1ad8c8c265e2a6d77527a222f0f03c0cc2d8`

The JSON binds both 12-method logs and the scope checks; the core log is `SOURCE-FACT-INPUTS-POSIX-core-after-v1.txt`. Earlier optional-boundary evidence remains unchanged and describes its earlier source revision. Full/core broad validation must use the current test bytes after the separate unrelated full-v2 error is resolved.
