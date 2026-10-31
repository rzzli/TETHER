# Finite converter protocol ready for root review — not executed

Preparation and installed dry-run only, 28 October 2026 UTC. No bridge, llama DLL,
vocabulary, model, context, inference or server was executed by this preparation.
Root must approve the exact protocol and explicitly invoke execution separately.
The earlier build-only restriction remains in force until that decision.

- Protocol: [FINITE-CONVERTER-EXECUTION-PROTOCOL-v2.json](FINITE-CONVERTER-EXECUTION-PROTOCOL-v2.json).
- Protocol SHA256: `30966db2bf9846f3280b3ff881e423cd66adeac175113157e326f196c034ed68`.
- Operator helper: [run_finite_converter_probe.py](run_finite_converter_probe.py).
- Accepted software: dependency-free installed AsOf 0.3.10, acceptance SHA256
  `27f33a36fd01d48b79e1492ad6b4b185a60e4bd662bb1ee0d955e5a284079cdc`.
- Only permitted bridge: v3 cache `data/cache/r09-typed-converter-bridge-build-20261028T033334Z/`,
  executable SHA256 `ea5064b8e2b68aa193efb0e129ef1da6087809d1a6fb21facccefaad70c362ca`.

The installed dry-run passed in 0.469 seconds, checking 140 pinned records under
ordinary stable-file leases. It verified the 83 installed wheel members, accepted
wheel, v3 bridge/build/header bindings, thirty DLLs plus two existing runtime EXEs,
frozen corpus and two input files. It checked type-aware comparison and the exact
single schema shared by the 109 frozen cases. No execution output directory or
once-only claim was created; dispatch/denied-operation counters are zero.

Dry-run artifact:
`data/cache/r09-converter-dry-run-1793161187064855200/dry-run-report.json`.
This validates preparation and leases; it does not exercise a real native child's
ABI, timeout/capture behavior or grammar enforcement.

## Reviewed execution scope

Only two once-only children are permitted: one fixed mixed-JSON parse/dump
round-trip, then one conversion of the unchanged shared schema if the first call
is clean. Type-aware comparison distinguishes booleans, integers, floating values,
strings, objects and arrays. Conversion always uses the bridge's
`force_gbnf=false`; the protocol does not anchor or otherwise repair the schema.

Each child is limited to 30 seconds, with a 120-second overall checked deadline,
64 KiB input, 1 MiB retained stdout and stderr each, and 4 MiB native return bytes.
Bounded readers preserve explicit truncation/error state. Only the owned Popen
handle can be killed/reaped. Shared deadlines are checked around synchronous I/O;
this does not establish hard OS preemption or an OS-wide sandbox.

The exclusive output directory and separate exclusive claim prevent repeating a
protocol. RunJournal records reservation, dispatch, PID, capture/accounting and
terminal disposition. Configuration, helper, accepted wheel and provenance are
archived; the terminal artifact inventory binds the journal and files. Archives
are evidence and are never imported as executable replay code.

Any ABI discrepancy, native diagnostics, timeout, partial capture or cleanup
problem stops before the next child. Converter warnings, incomplete conversion,
exceptions, empty output or unsupported backend close this gate negative before
any vocabulary stage. A native `native_call_returned` status is not a conformance
pass. Actual module paths/hashes are checked against the pinned manifest; they
are program-reported observations, not independent OS attestation. System CRT
hashes are environment provenance only, with version fields explicitly unknown.

No vocabulary/model stage exists in this protocol. Even a clean converter return
does not establish document/EOS grammar enforcement, scientific usefulness or any
human-review gate.

## Commands for root

The completed dry-run used:

```powershell
data/cache/recovery-step9-duration-wheel-20261028/environment/Scripts/python.exe -I planning/review-assets/recovery-step9-native-grammar-20261028/run_finite_converter_probe.py --dry-run --protocol-sha256 30966db2bf9846f3280b3ff881e423cd66adeac175113157e326f196c034ed68
```

Only after root review/approval, the same installed command with `--execute`
instead of `--dry-run` would dispatch the two bounded stages. It has not been run.
The fixed execution output would be
`data/cache/r09-finite-converter-execution-20261028T041937Z/`.

V1 protocol/helper snapshots are preserved as unexecuted preparation history.
V2 adds the corpus itself to the leased inventory and gives a native incomplete-
conversion diagnostic its explicit negative classification. No actual call was
repeated or repaired.
