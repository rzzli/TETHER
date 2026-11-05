# Equal-policy coverage ledger

The current pre-scoring ledger is [COVERAGE-QUALIFICATION-v2.md](COVERAGE-QUALIFICATION-v2.md), dated November 5, 2026. It separates implementation qualification, the 108 authored native cases, component checks, runtime witnesses and clauses not exercised in the paired corpus. It is not a passing paired comparison report.

The [original ledger](COVERAGE-v1.md) is preserved byte-for-byte (SHA-256 `95244117b6d919ca42a15b49ecdff759cccda30f179b18b0262ceb6e649aaa08`). Its pending rows describe the original pre-implementation state.

The normative [POLICY-SPEC.md](POLICY-SPEC.md) and [policy-spec.json](policy-spec.json) remain unchanged. No obligation was deleted or weakened. The freeze must pin this index, qualification addendum and evidence, preserved ledger, current qualified implementation and final execution protocol. Coverage documentation is not an oracle.

- Primary inventory: 108 cases; 64 prepare / 42 verify / 2 inspect; 92 catalog1 / 16 policy-v2; 95 new synthetic / 13 exposed regressions.
- Expected dispositions: 43 accept, 64 reject, 1 inspect-only. These are not observed scores.
- Every obligation family has primary cases; clauses/boundaries without primary examples remain explicit in the addendum.
- Archived-v1 unsupported scope handling is separate and outside the v2 denominator.
- Runtime guarantees use separately identified witnesses; file validation cannot prove physical execution or scientific validity.
- EP075 retains normative archived-replay request-binding rejection even if current TETHER fails it. Its oracle must not be weakened to improve a score.
