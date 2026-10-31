# Retained timing audit: successful simulation with little time margin

28 October 2026 UTC. AI engineering resource assessment of one retained
0.3.9 simulated case and one retained 0.3.10 simulated case. No case, tokenizer,
model, server or source-inclusive verifier was rerun for this audit. All 68
inspected metadata/prompt files remain byte-identical; selected run metadata was
checked against its existing receipt. The
[machine-readable audit](STAGE-TIMING-AUDIT.json) records input hashes and derivation.

The 0.3.10 case passes, but its complete execution takes **295.922 of 300 seconds**,
leaving **4.078 seconds / 1.36%** of the fixed budget with **no actual inference or
native server startup**. This establishes completion of the declared simulation,
not practical margin or actual integrated native-case feasibility.

## Comparable inputs; uncontrolled timing conditions

Both cases use the same original source authority, coverage, selected record,
all six exact prompt hashes/token counts and 24,558 input/6,144 output reservations.
Each runs six actual offline tokenizer children, six simulated HTTP stages and
one simulated process. Source/question sufficiency remains unqualified.

They are nevertheless single observations at different times with different code
versions, not a randomized or controlled performance experiment. Machine load,
file/cache conditions and independent physical I/O/CPU measurements were not
controlled here. The timing difference cannot be causally assigned to the duration
correction, to a particular code path or to hardware from this pair.

## Root-clock intervals

These intervals are differences between recorded anchors on the same root case
clock. They partition sealed elapsed time; their labels do not claim exclusive
function-level costs. In particular, the source-ready interval includes earlier
reservation, leases and package work; the intervals around native preparation
include setup/asset verification and a **fake** startup, not actual model loading.

| Recorded anchor interval | 0.3.9 seconds | 0.3.10 seconds |
|---|---:|---:|
| Case start through source-ready | 2.313 | 2.312 |
| Source-ready → retrieval-ready | 6.422 | 9.875 |
| Retrieval-ready → tokenizer-spec-ready | 6.375 | 8.313 |
| Tokenizer-spec-ready → native-preparing | 13.171 | 17.891 |
| Native-preparing → context-qualified | 6.750 | 8.343 |
| Context-qualified → sixth cell accepted | 128.235 | 185.391 |
| Sixth cell accepted → summary time | 0.281 | 0.500 |
| Summary time → receipt sealed | 36.453 | 63.297 |
| **Sealed total** | **200.000** | **295.922** |

Outer helper execution is 200.016/295.922 seconds, a difference of 95.906 seconds
(1.47949× in this observation). The sealed-clock difference is 95.922 seconds;
the two measures are not silently treated as identical. The root source,
preparation, stages and sealing all count toward the unchanged case budget.

## Quote and acceptance intervals

The next table gives `quote_ready → cell_accepted` root-clock gaps. They include
more than transport: admission, generic session work, finalization and verification
can occur inside them. They are not measured native inference latency.

| Cell | 0.3.9 gap seconds | 0.3.10 gap seconds |
|---|---:|---:|
| 0 | 3.766 | 7.500 |
| 1 | 3.922 | 7.313 |
| 2 | 4.062 | 7.500 |
| 3 | 4.156 | 7.843 |
| 4 | 4.344 | 7.969 |
| 5 | 4.391 | 8.563 |
| **Sum** | **24.641** | **46.688** |

Separately, the six quote files' own recorded intervals sum to 83.438/102.298
seconds; their actual tokenizer-child intervals sum to 2.265/2.063 seconds.
Quote intervals include asset/package/trace work and exclude later receipt
publication. Their non-child remainder is **not** an independently measured
hashing cost. These intervals sit inside the root stage intervals and must not
be added again to the partition above. Child reports likewise overlap those
root intervals. All six new native-versus-budget/report comparisons pass.

The receipt's sealing measurement is 36.437/63.266 seconds. Its source-release
measurement (0.000/0.016 seconds) is nested inside sealing, not an additional
interval. The small difference from `summary → sealed` reflects differently
placed anchors; no missing per-method timestamp is invented. The fake process's
134.969/193.672-second lifetime also overlaps stage work and is not additive.

The helper reports a same-environment replay/check interval of 36.250/61.203
seconds outside the original case execution. It includes verification and
post-replay checks/instrumentation, so it is not labeled pure verifier time.
Parent peak working sets including these checks are 533,012,480/497,668,096 bytes.
Tokenizer-child/GPU peaks and actual model memory remain unmeasured here.

## Consequence for the next major step

Keep this successful observation and its small margin. Do not raise the
300-second budget, repeat the case until a favorable time appears, or claim
that real startup plus six native answers will fit. Nor does this one pair prove
that the code change caused a performance regression or that every execution is
impossible. Any performance correction or integrated feasibility experiment needs
its own prospective scope, correct accounting and acceptance evidence.

The next actual-DLL converter probe is a distinct bounded conformance experiment,
not a substitute for integrated case performance. Its typed bridge is compiled
but not yet executed, and own-source toolchain usability is not DLL ABI proof.
After framework acceptance, freeze ABI round-trip/conversion inputs, bounds,
module identities and diagnostics before execution. **A conversion warning,
unsupported mode, exception or ABI failure must close that declared gate negative
and stop before vocabulary initialization.** Preserve the fixed uniqueness and
pattern/length negatives; do not weaken the schema or silently switch backends.

A clean converter result can only permit a separately declared grammar/EOG
acceptance stage. It does not establish model quality, full-case timing, fresh
source sufficiency or independent scientific review. R08/HR gates remain required
before fresh R10 generation, and the old R07 negative result remains unchanged.
