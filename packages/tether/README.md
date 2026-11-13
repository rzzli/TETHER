# TETHER

**Auditable evidence workflows, with source-linked dossiers and bounded execution.**

The public package is `tether-target-agents` **0.7.0**, command and namespace
`tether`. It pins `tether-target-engine==0.5.0`, whose namespace is `tether_engine`
and direct command is `tether-engine`. The runtime has no third-party library
dependencies; optional ingestion pins `pyarrow==21.0.0`.

From the repository root, follow the [quick start](../../README.md#quick-start).
Use a fresh output directory with an existing parent:

```text
tether --version
tether demo --output runs/fresh-demo
tether verify --run-dir runs/fresh-demo --receipt-sha256 <saved-hash>
tether inspect-run --run-dir runs/fresh-demo
```

The bundled demo uses fictional evidence and deterministic offline extraction.
Local models are separate opt-in configurations, not part of the default demo.

## Output and verification

`demo` and `run` reserve a new outer directory. `engine/` contains the engine's
source bindings, claims, journal and receipt. The outer `dossier.md` is an exact
byte copy of the engine dossier, checked under `identity_dossier_v2`.
`tether-manifest.json` binds the full file inventory and launcher code;
`tether-receipt.json` seals the completed attempt. Save the printed receipt hash
separately: a sibling receipt cannot detect replacement of the entire tree.

Verification checks the launcher, journal, inventory, dossier, source bindings
and deterministic execution consistency. Outer `--outputs-only` is rejected.
Scientific correctness and clinical validity are not established by verification.
See [verification limits](../../docs/TETHER-VERIFICATION-SCOPE.md).

## Fixed-horizon evaluation

Evaluation reads labels separately from agent execution. Provide a registered
cohort, a producer manifest, labels and independently retained hashes:

```text
tether evaluate --cohort <cohort.json> --cohort-sha256 <hash> \
  --producer <producer.json> --producer-sha256 <hash> \
  --labels <outcomes.json> --labels-sha256 <hash> --output <fresh-report.json>
```

TETHER records bind exact engine run receipts and prediction bytes. For a wrapper
run, the producer points to its `engine/` directory. External baselines use
`evaluate-baseline` and a distinct producer declaration. `evaluate-raw` accepts
unverified prediction files for diagnostics only. Fictional predictions require
`--allow-synthetic` in every route.

All registered cases remain accounted for. The full horizon plus reporting lag
must elapse before a case enters the binary population; early positives do not
bypass this rule. Missing labels or predictions withhold full-population metrics.
See [contracts and report interpretation](../../docs/FRAMEWORK.md#fixed-horizon-evaluation).

Failures preserve `tether-failure.json` and available journals. `inspect-run`
reads them without restarting calls. A later attempt requires a new output path.
This is trusted local execution, not an operating-system sandbox.

## Explicit artifact permissions

The optional policy path requires all five arguments together:

```text
tether run --case <case.json> --snapshot <snapshot.json> --output <fresh-output> \
  --catalog <schema1-catalog.json> --catalog-policy <schema2-policy.json> \
  --policy-use <use-id> --policy-roots <roots.json> --policy-frame-sha256 <hash>
```

`roots.json` maps root aliases to absolute local paths, including `metadata`.
Every supplied packet and source ancestor, including unused nodes, must have an
exact grant. Controls are copied into the attempt, while raw originals remain
external and pinned. Eligibility and publication filters still apply. A current
computation may use older eligible information; a receipt is not evidence of
historical availability.

This path supports only the offline extractive backend without scorer, replay or
local-model configuration. Demo and ingestion commands do not support it.
Ordinary schema-1 execution remains available with explicitly weaker catalog
scope. Direct module aliases do not acquire artifact authorization.

## Process and file limits

Engine-backed commands default to a 3,600-second process deadline and aggregate
16 MiB stdout/stderr limit; use `--process-timeout-seconds` and
`--process-output-bytes` to set explicit limits (output maximum 64 MiB).
The engine workflow's 300-second default budget is separate. Cleanup has its own
five-second budget. These controls do not contain descendant processes, preempt
OS process creation, or bound later outer verification. Uncertain calls are
never automatically repeated.

Metadata/journal reads are capped at 64 MiB; dossiers at 256 MiB. Bounded reads
reject links, reparse points and nonregular files and check file identity.
Policy I/O uses a separate 300-second deadline. These checks do not guarantee
exclusive ownership of external files. Windows is the qualified supervisor
platform; other platform guarantees remain limited to their tested scope.

## Version boundary

The new namespace, distributions, method identities and code fingerprints are a
breaking release. The public aliases share the new engine's module/class objects.
There is no old namespace shim. Pre-migration version-two runs require their
original source checkpoint; generic version-one byte verification still reports
semantic verification unavailable. See [migration details](MIGRATION.md).
