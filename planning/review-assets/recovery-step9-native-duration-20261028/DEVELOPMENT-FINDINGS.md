# Native relative-duration correction

Chronological 0.3.10 correction record; completed checks are below and the final
acceptance is sealed separately in acceptance.json. Preserve the accepted 0.3.9 wheel, simulation
and all earlier matching verifiers. The retained AI audit first reproduced a
component accepting a transport duration of 9,999 seconds against 244.906 seconds allocated; it
did not demonstrate original execution overrun or a full resealed-run bypass.

Before-fix regressions record 17 expected failures in seven tests (89.814 seconds),
including a controlled whole-case fixture whose wrapper duration exceeds its
enclosing report. The correction validates a complete typed budget, requires
finite nonnegative native duration strictly below its cap, and checks native
duration against a validated enclosing report at controller finalization/replay.
The report comparison uses the existing absolute 1 µs tolerance; budget expiry has
no added tolerance. Zero/report equality are valid; budget equality is expired.

There are 13 new tests. The component group of 25 tests passes in 19.451 seconds;
the final native/adapter/mode/accounting/controller group of 75 passes in 289.852
seconds and eight recorded regressions pass in 97.275 seconds. Ruff/format checks pass on the four
owned files. Only two study runtime modules/two existing test files changed;
the generic session and legacy/default code paths remain unchanged. Normalized
diff and targeted completion hashes are retained.

Root then advanced the initializer/project metadata to 0.3.10 and recorded the
initializer as the only changed legacy semantic helper. Current installed
metadata, discovery and inventory agree: 1,737 tests and 324 pins. Full frozen
validation passes with zero failures/errors/skips, probes, PowerShell syntax and
offline wheel/demo checks in 2,361.641 seconds. All 324 pins and both hash-only
protected outcomes are unchanged. All nine previous matching installed verifiers
pass. A new prospective simulated real-input run and guarded installed
qualification remain required; the finite simulation protocol is now retained.

## Final operator qualification

The prospective same-input simulation passes at 295.922 seconds, with read-only
source/model replay at 61.203 seconds. All six wrapper/report/allocation comparisons
pass. Input/output reservations remain 24,558/6,144; six actual tokenizer children,
six simulated stages, one simulated process and two pure results. Actual model/
server calls and provider spending are zero. Parent peak is 497,668,096 bytes;
bundle is 999,354 bytes; child/GPU peaks are unknown.

This leaves only 4.078 seconds of the unchanged 300-second case budget without
actual startup or inference. The retained resource-risk note compares recorded
anchors only; no favorable-time retry, budget increase or causal attribution of
slower timing was performed. Actual integrated native feasibility is unestablished.

Default installed qualification passes seven legacy families, twelve interface
preparations, native-wrapper checks and eight duration cases. Optional installed
source/model replay passes in 79.734 seconds; guarded run-copy relocation passes
in 76.359 seconds. All guard lists are empty. The old 0.3.9 evidence/wheel remain
byte-identical. Raw/model originals remain explicit replay dependencies; this is
not full independent input restoration. Scientific and native-grammar gates stay open.

No actual model/server inference or provider spending occurred. Human scientific
reviews are pending. The owner installed C++ Build Tools; a separate tiny
own-source compile/run probe passed without a restart. That probe
does not qualify llama ABI, native grammar, biological interpretation or R10–R16.
