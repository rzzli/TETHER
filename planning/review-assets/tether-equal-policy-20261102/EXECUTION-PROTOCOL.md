# BG02 paired validator execution protocol

Status: implementation and unscored development qualification in progress. This
protocol does not report a completed comparison. The policy specification and
independently authored fictional oracle govern correctness, not agreement with
TETHER. A current implementation can fail its declared policy.

## Compared surfaces

The installed, BG01-qualified TETHER 0.5.1 / AsOf 0.3.12 and the independent
stdlib validator consume identical original-format bytes. Preparation validates
inputs without calling a backend. Verification consumes native sealed run
artifacts. Inspection reads unresolved durable attempts without redispatch.
Schema2 preparation retains checked copies in separate fresh scratch paths for
both implementations. The exact policy and return contract are in POLICY-SPEC.md.

Two explicitly weaker controls accompany the comparison: a hash/schema-only
diagnostic and reject-all. Neither substitutes for the independent equal-policy
validator. Legacy v1 receipt-only verification remains a separate declared scope
control, outside current-v2 semantic accuracy denominators.

Runtime-only properties such as object immutability, exclusive publication and
dispatch durability are separately witnessed. A file validator does not recreate
an agent scheduler or demonstrate those properties merely by accepting a trace.

## Preparation, freeze and execution

1. Independently author fictional source documents, mutation recipes and expected
   decisions. Mark exposed regressions separately from new constructions. Authors
   know the repository and policy; no claim of blinded held-out evaluation applies.
2. Qualify experiment components with unit tests. These are development tests,
   not scored benchmark observations. Record implementation errors and corrections.
3. Materialize each native archive once using the pinned installed runtime and
   explicit fictional backends. Local-model transport fixtures use an in-memory
   response object; no model, weights or network endpoint is executed. Preserve
   all producer attempts and preparation failures. Apply only declared mutations.
4. Freeze the complete schedule, oracle, descriptors, byte inventory, experiment
   code, policy, installed runtime proof and execution settings before comparison.
   A missing recipe is a preparation failure, never a silently omitted case.
5. Run every scheduled case through all four implementations in fresh isolated
   processes. Use the same Python environment, input paths, external anchors,
   per-call deadline and output cap. Alternate implementation order deterministically
   by case index; report timings descriptively without inferring superiority from
   a single small measurement. Each invocation gets separate scratch storage.
   Output sizes are checked during polling and again after exit; these are
   terminal qualification thresholds, not hard retained-byte ceilings. Direct
   file capture can overshoot between polls. No process-tree sandbox is claimed.
6. Retain a terminal record for every scheduled cell. Timeout, crash, unsupported,
   invalid worker output and fixture/source changes are separate failures, not
   successful policy rejections. No automatic retry enters the same comparison.
7. Rehash the immutable corpus and implementation inputs after execution. Independently
   reconstruct dispositions, denominators, observable agreement and resource summaries.
   Any corrected experiment is a new version/freeze; preserve the original attempt.

## Primary reporting

Report false admission among oracle-rejected cases and false rejection among
oracle-accepted cases separately. Include failure/unsupported counts and denominators;
an error is not a correct rejection. Inspect-only cases have their own recovery
agreement measure; an inspect-only disposition for an oracle-invalid journal is
reported as invalid inspection acceptance, separately from false admission.
For accepted verification cases, also compare the declared
prediction, features, selected IDs, exclusions and accounting observables. Do not
count an accept with wrong observables as fully conformant.

Report per-policy-family and exposure-stratum results without adding overlapping
family counts into an independent sample size. Synthetic controls establish finite
conformance observations, not natural fault prevalence, biological truth, clinical
benefit or general agent intelligence. Identical mistakes by both implementations
remain wrong against the independent oracle.

Wall and CPU durations, memory and logical input/copy volume have separately named
measurement boundaries. File sizes/open volumes do not establish physical disk I/O.
Retained-copy overhead is part of schema2 preparation and is not silently removed
from one implementation. Report runtime code, experiment glue, tests, dependencies
and evidence files separately when comparing maintenance surface.

## Boundaries preserved

All source data in this corpus are fictional. No protected clinical outcomes or
expert returns are read. No provider calls, paid resources, external downloads or
changes to old experiments, archived releases, the downloader or periodic monitor
are required. A negative result is retained rather than tuned away. BG03 SciFact,
BG04 LAB-Bench and BG05 Inspect remain subsequent authorized stages.
