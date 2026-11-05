# BG02 executed comparison and required corrections

The first frozen comparison is terminal and independently reconstructed, but **BG02 is not complete**. Causal review found an archived replay-verification defect masked by a fixture rendering inconsistency, an incorrect recovery observable expectation, and additional fixture limitations. No original result or expected answer has been changed.

## Retained execution

- Input: `data/benchmark/tether-equal-policy-20261102-attempt03`; 108 cases, four implementations, three repetitions, 1,296 terminal cells. Process session47997 exited0 at 2026-11-05 21:07:29 UTC.
- Freeze SHA-256: `26b30fef132fc6ce6acd6f1844a41521da47fb091d53e513d4b14588db476736`. All seven after-run input/source/runtime checks passed.
- Independent reconstruction SHA-256: `6a16a1103791dab5d0255398414695c8c6bebc1e7fc673e4e7bda14920d96166`; every primary disposition, observable mismatch and denominator agrees.
- Both full implementations match 108/108 authored decisions but only 107/108 complete observable expectations. These descriptive counts repeat identically across the three trials; they do not establish full policy parity.
- The hash/schema diagnostic falsely admits 51/64 rejected cases and errors on one directory-read case. Reject-all wrongly rejects all43 eligible cases. Failures remain in the denominator.
- Median instrumented import-plus-operation time is0.398180s for TETHER and0.121888s for the independent validator. These are fresh-process, shared-host, artificial-case measurements. They do not establish production speed, scientific utility or equivalent minimal code complexity.

Detailed resources, groups and limitations are in the [independent reconstruction](../tether-equal-policy-20261102/reconstruction/NATIVE-RECONSTRUCTION-20261105.md). The [focused review](FOCUSED-REVIEW.md) and [all-case review](coverage-review.md) qualify the apparent decision agreement.

## Corrections required before closure

1. **Archived replay request binding:** EP075 changes a recorded request fingerprint, but canonical rewriting also changes coverage-map ordering and makes the old dossier table inconsistent. TETHER rejects the table inconsistency; the independent validator rejects the fingerprint. A separately retained, explicitly post-hoc copy with only the derived dossier and seals refreshed is accepted by TETHER despite its invalid fingerprint. Correct archived-v2 replay verification using retained provenance and request/selection/accounting evidence; preserve original installed0.5.1/0.3.12 and the counterexample.
2. **Recovery oracle:** EP077 corrupts the journal chain. Rejection is correct; expecting unresolved-attempt/recovery outputs after this rejection is incorrect. Preserve the old scored mismatch and correct the expectation only in a new experiment version.
3. **Clean lineage control:** EP023's unrelated source was copied before sealing and retains zero hashes. Its observed rejection reaches the intended lineage-escape defect, but the input is not a clean single-fault control. Seal that source in the next construction.
4. **Nonvacuous stopping control:** EP072/EP097 currently provide only genetics work, so zero later dispatches cannot alone prove prevention of available later work. Include an eligible later category in the revised controls; retain the separately qualified runtime tests.
5. **Versioned rerun:** Preserve original experiment sources and all frozen artifacts. Independently author corrected cases, include a clean recorded-replay parent, and qualify a new frozen complete comparison. All reused controls are exposed; this is not a fresh hidden test set.

Original EP001/EP025 share identical underlying input constructions and assess different policy lenses. Report this dependence rather than treating them as independent samples. The weak control's EP057 error remains an error; no result is converted post hoc into a correct rejection.

Current work is the archived replay correction and versioned corpus/integration. Native SciFact, one LAB-Bench family and Inspect remain subsequent required stages. No model calls, paid access, clinical inference, expert recruitment or changes to the downloader/monitor are introduced.
