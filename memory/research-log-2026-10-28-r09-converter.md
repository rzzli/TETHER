---
name: research-log-2026-10-28-r09-converter
description: Actual typed-DLL round-trip passes but unchanged-schema conversion closes negative; toolchain usable without restart
metadata:
  type: project
updated: 2026-10-28
---

# Actual converter diagnostic and current project gate

The owner-installed Microsoft C++ tools compile/link/run without restarting.
The typed bridge builds against three exact consumer headers. Under a separately
frozen, root-reviewed protocol, a mixed-JSON actual-DLL round-trip passes and
unchanged-schema conversion returns 14,866 grammar bytes with an explicit
incomplete-conversion warning: unsupported nonblank patterns accept any string.
This closes the finite gate **negative**, despite both child exit codes being zero.
No vocabulary, model, inference or server stage followed; provider spending is $0.

The [disposition](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/recovery-step9-native-grammar-20261028/DISPOSITION.md)
retains exact inputs/outputs, diagnostics, module proofs and original failed
attempts. Protocol SHA256:
`a4f09687d19bc2803a4b419c6c707044d6f0097515a0f5778770563f0f267ce0`.
Receipt SHA256:
`73c3f2bede92d2f51238831dea8012e3e4d20a0dd9655002d9f51432bdefcaa4`.
Two children took 0.094/0.078 seconds; sealing-inclusive execution took 1.297s.
Child peak memory is unknown. These are cooperative deadline/typed-operation
observations, not OS sandbox attestation, complete ABI coverage or reproducible
source/build proof.

An earlier once-only protocol failed before process creation: its guard blocked
Windows NUL stdin. Its zero dispatch/spawn counts, null PID, failure and valid
journal remain preserved. The new harness permits only the exact NUL setup
operation and checks deadlines through sealing. Three focused regressions pass:
one harmless Python child with rejected unauthorized writes, inventory expiry,
and post-receipt expiry whose failure marker vetoes the receipt. The 150-pin
installed dry-run passes. Test-fixture failures are preserved separately and are
not native attempts. No accepted runtime/test file changed; the prior 1,737 full
tests remain the accepted 0.3.10 result, not a new full-suite run.

The 109-case corpus and original schema remain unchanged; no native document/EOG
corpus was executed. Preserve this negative before considering a separately
versioned generation contract. An anchor-only patch is insufficient: pattern/
length, Unicode escape/codepoint and reference uniqueness boundaries need declared
semantics and independent native qualification. Keep strict acceptance and
post-validation unchanged, without output repair or corpus replacement.

The [new whole-project reassessment](../planning/Project%20Progress%20Reassessment%202026-10-28%20-%20R09%20Converter.md)
reconciles R01–R16/HR1–HR4 and critically reviews the next contract/resource step.
The 295.922/300-second simulation still leaves only 4.078 seconds without actual
inference; actual-case feasibility is unestablished. Human reviews remain pending,
no fresh scientific frame is qualified, R07 stays stopped, and clinical/genetics/
scorer/T2–T5/H6 branches remain gated. See [[research-log-2026-10-28-r09-duration]]
and [[project-goals]].
