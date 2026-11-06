# BG05 isolated Inspect environment

Qualification passed on 6 November 2026 UTC. This qualifies the dependency environment and a canned Inspect execution path; it does not complete BG05's framework comparison.

Use `D:\Projects\drug_target_agents\data\cache\tether-inspect-env-attempt02\environment\Scripts\python.exe` with `-I -B`. It is Python 3.11.15 and contains Inspect 0.3.287, the exact authorized asof-target-agents 0.3.13 and tether-target-agents 0.5.2 wheels, and 84 distributions in total. Keep this environment unchanged during matched comparisons.

The [qualification receipt](attempt02/ENVIRONMENT-QUALIFICATION.json), SHA-256 `d759f9fb05bcb985167add81a273e09294cfa325870c2de072e309fcdb9053b6`, binds the following checks:

- Eighty third-party wheels were acquired only from the explicit public PyPI index with zero retries, then independently matched to official release metadata by filename, bytes and SHA-256. Their compressed total is **81,234,458 bytes**. The full [version/hash lock](attempt02/requirements-lock.txt), [wheel inventory](attempt02/WHEELS.json), original wheels and original PyPI JSON remain retained.
- Installation used `--no-index --require-hashes` from the retained wheel directory. The two [product wheels](attempt02/PROJECT-WHEELS.json) were installed separately with `--no-index --no-deps`; CPython's original bundled pip/setuptools wheels are also retained separately. No existing environment, project dependency declaration or downloader was changed.
- Both dependency checks pass. All **8,071** installed files carrying RECORD hashes match them. The **936** RECORD entries without expected hashes are retained with explicit missingness; their current bytes are independently hashed in the full environment inventory. Raw installed METADATA, RECORD and related distribution files are archived under `installed-metadata-exact/`; the earlier text-normalized copies remain as separate audit evidence.
- All **85** installed TETHER/asof Python sources match their exact authorized wheels and the existing qualified SciFact environment. The final complete inventory has **9,014 files / 209,294,632 bytes**, below the distinct 1 GiB expanded-environment cap. Compressed acquisition and expanded storage are not interchangeable; wire-transfer bytes were not instrumented.
- The [mock evaluation](attempt02/MOCK-EVAL-03.json) completes two canned samples through real Inspect `Task`, `generate()` and `match()` components, obtaining the intended C/I scores. Its 14 input and 4 output token counts are explicitly synthetic fixture usage. There were **zero real-model calls, zero external-provider calls and zero external-network/DNS attempts**. Provider spend was $0.

## Windows execution caveat

In this session's sandbox, even `asyncio.run(asyncio.sleep(0))` hangs in Python's Windows loopback socketpair `accept`. The identical [model-free probe](probe_asyncio.py) succeeds under approved escalation. The mock's trusted audit therefore permits only the recorded connection made by the exact stdlib `_fallback_socketpair` function to a loopback address; other connect, DNS and sendto attempts are denied. One internal self-pipe connection was observed. This is not an OS network sandbox and must not be described as making all networking impossible.

Use the loopback-capable execution mode for async integration tests, with cleaned environment variables and `PYTHON_DOTENV_DISABLED=1`. [Observed API signatures](attempt02/OBSERVED-API.json) come from this installed version. Model/provider optional extras, remote endpoints, actual language-model inference and benchmark performance have not been qualified here.

## Preserved failures

1. Acquisition attempt01 stopped before installation when a monitor raced with pip deleting a temporary directory. [Three focused guard controls](guard-tests01.log) verify the narrow missing-path correction; permission and other I/O errors still fail. The entire first attempt remains intact.
2. Mock01's blanket socket audit blocked Windows asyncio's own self-pipe before generation. Its [failure](attempt02/QUALIFICATION-FAILED.json) and logs remain intact.
3. Mock02 allowed the self-pipe in trusted code but timed out in the execution sandbox. The independent probe isolated the same failure without Inspect or any model. The [timeout record](attempt02/08-mock-qualification.json), original helper and output directory remain intact. Fresh mock03 passed outside that sandbox without changing installed dependencies.

The successful mock and final file inventory were recorded after those failures. They do not retrospectively mark the failed attempts successful. All package originals, runtime logs and bulk metadata remain under the ignored cache tree; only bounded locks, provenance and qualification records are intended for tracking.
