# V3 finite converter harness ready for review — not executed

The V2 operator authorization was consumed by a **pre-native harness failure**.
Its preserved failure, parent attempt and journal prove zero subprocess audit
events, zero created children, no PID and empty stdout/stderr. Its journal dispatch
entry recorded intent. The guard rejected Popen's stdin DEVNULL open before the
subprocess audit/CreateProcess boundary. V2 is not retried and its files remain
unchanged.

V3 uses new helper filenames and a fresh explicit protocol/output. No bridge or
llama DLL has been executed during V3 preparation/regression validation.

- [Runner](run_finite_converter_probe_v3.py) and [preparation helper](prepare_finite_converter_probe_v3.py).
- [Protocol](FINITE-CONVERTER-EXECUTION-PROTOCOL-v3.json), SHA256
  `a4f09687d19bc2803a4b419c6c707044d6f0097515a0f5778770563f0f267ce0`.
- Installed dry-run: `data/cache/r09-converter-dry-run-1793162263194648800/dry-run-report.json`.
- Focused regression result: `data/cache/r09-converter-harness-v3-regressions-1793162150480679000/regression-report.json`.
- Fresh, still absent execution output: `data/cache/r09-finite-converter-execution-20261028T043655Z/`.

## Corrections and validation

The allowed device exception is exact: raw `os.devnull` (`nul`), mode `None`, and
Windows audit flags `O_RDWR|O_NOINHERIT` (130), only while a fixed authorized argv
is active. The old guard recorded the normalized device name `\\.\nul`. No general
device/path exception was added. Normal output writes retain their existing
restrictions; another regular write, write-only NUL and a path-qualified NUL alias
are rejected by the regression.

Finalization now checks the global deadline per inventory file, through each
bounded hash and before/after receipt and seal-state writes. Reported total and
sealing elapsed times are separate. `failure.json` is authoritative and vetoes
any receipt or seal state, including a failure detected after receipt creation.
A receipt alone cannot imply a clean finish; its seal-state binding is required.

All **three focused regressions pass** in 0.111 seconds: one harmless isolated
Python child proves DEVNULL EOF, actual creation and reaping; inventory-hash
overrun fails before a receipt; post-receipt overrun retains the receipt but writes
the authoritative failure marker and no seal state. No converter child or llama
library ran. Initial synthetic test failures are preserved: the first assumed
audit flags2 instead of130; the next used text stdout, whose Windows CRLF was
correctly retained. The final fixture uses binary stdout. The first failed test
report's intended child count was hard-coded; its audit evidence shows no spawn.
The corrected final report derives counts from observed starts.

The installed dry-run passes with zero dispatches/spawns and verifies current
pins/leases, input/schema identity and absence of the fresh execution claim. The
protocol includes the prior zero-call failure disposition and proofs. Exact V2
runner/preparation snapshots remain available independently of V3.

## Scope remains unchanged

At most one mixed-JSON ABI round-trip child, then one unchanged frozen-schema
conversion child. The same v3 bridge, accepted0.3.10 wheel, thirty approved DLLs
plus two runtime EXEs, 109-case corpus/schema and `force_gbnf=false` remain pinned.
Limits stay30 seconds per child/120 seconds overall, 64 KiB input, 1 MiB stdout
and stderr each, and4 MiB returned grammar. No native vocabulary/model/context/
inference/server stage or automatic retry is present. Any ABI problem, diagnostics,
incomplete conversion, unsupported backend, timeout or cleanup failure stops.

Root must review/approve this exact hash before a separate `--execute` invocation.
The completed dry-run command was:

```powershell
data/cache/recovery-step9-duration-wheel-20261028/environment/Scripts/python.exe -I -B planning/review-assets/recovery-step9-native-grammar-20261028/run_finite_converter_probe_v3.py --dry-run --protocol-sha256 a4f09687d19bc2803a4b419c6c707044d6f0097515a0f5778770563f0f267ce0
```

Preparation, synthetic regression tests and a returned native status do not
establish actual ABI compatibility, grammar/EOS enforcement or scientific quality.
