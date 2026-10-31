# Converter qualification closed negative — do not rerun

The once-only V3 diagnostic completed its two permitted native children and
sealed a **negative result: `conversion_incomplete_warning`**. The fixed mixed-JSON
ABI round-trip passed. Conversion of the unchanged response schema returned GBNF
text but explicitly warned that its unanchored non-whitespace patterns were
unsupported and would accept any string for those pattern constraints. Under the
prospective strict diagnostics rule, this schema/runtime pair is **not qualified**.

The [scoped result and raw pins](RESULT.json) summarize the original
`data/cache/r09-finite-converter-execution-20261028T043655Z/` artifacts. This is an
execution-author summary; independent engineering verification is a separate
workstream. It does not constitute independent scientific review.

| Observation | Retained result |
|---|---|
| Accepted parent software | AsOf 0.3.10; acceptance `27f33a36fd01d48b79e1492ad6b4b185a60e4bd662bb1ee0d955e5a284079cdc` |
| Native calls | Exactly two, both exit 0 and reaped; no timeout, truncation or cleanup error |
| ABI control | One 271-byte mixed synthetic JSON fixture; returned bytes match exactly |
| Conversion input | One unchanged 7,563-byte schema shared by the frozen 109 synthetic cases |
| Schema SHA256 | `a75dd967b16fd387da820e0bd90071aba511aee5363f700e9ac5849f8cc72911` |
| Returned GBNF | 14,866 bytes; SHA256 `1abe05ff0c8b9004f9e0757cd9ecdbc273ffb595417f2f8545ce5721dee87bc8` |
| Native diagnostics | 2,955 stderr bytes; seventeen unsupported-pattern warnings |
| Stderr SHA256 | `98073196b103fa927fc89bb2cc281877d8189ee80375723ec35fa76a8efdcf8b` |
| Time | Seal state records 1.297 seconds elapsed and 0.109 seconds sealing |
| Memory/GPU peaks | Not instrumented; unknown |
| Model/vocabulary/context/inference/server calls | Zero |
| Provider spending | $0 |

Raw diagnostics are retained at
`stages/01-convert/stderr.bin`; they identify the missing anchors and the permissive
string substitution. A returned GBNF string and `native_call_returned` status do
not override that warning or prove grammar enforcement. Both children report the
same five approved native modules before/after their operations, with path/hash
checks; this is program-reported evidence, not independent OS attestation.

The protocol SHA256 is
`a4f09687d19bc2803a4b419c6c707044d6f0097515a0f5778770563f0f267ce0`.
Receipt SHA256 is
`73c3f2bede92d2f51238831dea8012e3e4d20a0dd9655002d9f51432bdefcaa4`.
The seal state binds that receipt; no authoritative failure marker is present.
This seals a negative engineering observation, not a scientific validation or
successful native grammar gate.

The bounds were unchanged: two children maximum, 30 seconds each/120 seconds
overall, 64 KiB input, 1 MiB stdout/stderr each, and 4 MiB returned text. Independent
end-to-end wall time and peak resources were not measured; the timing above names
the retained seal-state observations. Hashing existing DLL files is distinct from
loading model weights. No GGUF/vocabulary file, model handle or inference context
was used by this diagnostic.

## Preserved history and stop

V2 failed in the parent guard before subprocess audit/CreateProcess: zero native
children, no PID and empty stdout/stderr. Its authorization was consumed and its
output/claim remain preserved. V3 was a separately reviewed protocol after focused
harness corrections. Earlier build and synthetic-test failures are retained; none
was a native model response retry. The original R07 negative result remains
unchanged and is not reinterpreted by this different interface/runtime test.

**Stop here.** Do not rerun V3, anchor or otherwise repair its schema, force an
alternate backend, substitute a new case, or proceed to vocabulary/document/EOS
filtering or model inference under this protocol. The 109 native filtering cases
were not executed. Any later correction requires a separate prospective version,
explicit acceptance criteria and execution decision, preserving this result.

The observed ABI round-trip is limited to the fixed fixture. Broader ABI behavior,
native document/EOS enforcement, model quality, fresh-case/source sufficiency,
human references and the original scientific programme remain unqualified.
