# Independent source-inclusive P05 experiment auditor

Status: prepared and fictionally tested. No actual P06 experiment directory,
native source payload, generated native output or actual study ledger was opened
during this preparation. Actual audit execution requires a new root instruction
after producer closure, the exact ledger byte SHA, exact seal byte SHA, exact
root READY byte SHA, and a fresh audit-output path. Existing audit reports are
preserved.

The entry point is `tools/science/audit_source_validation_experiment.py`. Its
actual-audit report contract is:

```json
{
  "status": "PASS_INDEPENDENT_EXPERIMENT_AUDIT",
  "method": "p05.independent_source_inclusive_experiment_audit.v1",
  "subject": {
    "ledger_path": "<absolute path to the audited ledger.json>",
    "ledger_sha256": "<exact retained ledger byte SHA256>"
  },
  "source_inclusive": true,
  "independent_projection": true,
  "unresolved_findings": [],
  "scientific_validation": "not_established"
}
```

The analyzer must receive an independent exact byte SHA for this report and the
same independent ledger byte SHA. A report's own subject/hash declarations do
not authorize it. Actual source failures, mismatches or lifecycle failures retain
a FAIL audit disposition; they do not repair, replace or rerun an experiment.

## Independent expectations and shared dependencies

The actual auditor imports none of the experiment producer, literal assembler,
producer selection/mapping/task helpers, core reference compiler, retained-byte
adapter or scorer. It reuses the independently authored original scan, canonical
mapping and precision-date implementations from these three earlier audit files:

- `audit_source_registry_v3.py`
- `audit_source_inputs_v1.py`
- `audit_source_references_v1.py`

These are code dependencies, never source-value or answer parents. Root READY
must include their exact hashes and the new auditor in `extra_code_sha256`.
The fictional auditor regression file is also one of the runner's seven exact
extra-code paths. These notes are retained in Git; they are not an extra runtime
code path and must not be added to that closed set. Core contracts,
catalog/lineage admission and the public field-family taxonomy are shared protocol
dependencies, already covered by active `src/asof` pins. They do not provide the
auditor's expected values or emitted-report oracle.

The auditor freshly hashes all 137 originals and exact receipts under original
file locks, validates roles/availability/canonical mapping, and scans the complete
selected source frame. Original native rows define facts, null/absent/empty
reasons, physical bindings, locus joins, groups and denominators. Current sealed
references and generation packets are comparison targets only. Native literal
and abstain bytes are independently reconstructed from original facts and the
unchanged neutral Tasks. The original-to-packet/task/reference separation and
register denominator bindings are checked.

The auditor has its own strict typed-facts parser, including duplicate-key, UTF-8,
finite-value, source-binding, shape and 256-KiB checks. Exact matching preserves
Boolean/integer/float distinctions and signed zero. It independently recomputes
critical errors, matched components, correct unknowns, omitted requests, false
assertions, equal-group fractions and 60/80/100% thresholds. Measurement passes
use exact `Fraction(4, 5)`, not rounded display coverage. Accounting includes
`matched`, `false_asserted_values` and its `false_asserted` compatibility alias.
Unknown facts receive no measurement credit, and zero-denominator coverage/pass
remain null while completion is false.

## Fictional byte and truth checks

Four valid and ten fault constructions are independently authored as literal
source documents and mutation recipes from the frozen design. The auditor
checks the observed source and receipt bytes against that protocol, retaining
F01's stale clean anchor separately from its changed observation. It derives
G0 checksum, G1 original/receipt/role/ancestry, G2 date/mapping/full-inventory,
G3 strict native type/date/scope, and G4 retained-output outcomes from those
bytes. It then reconstructs each policy's required stages and paired verdict.
Stored fixture oracle labels and guard/stage results are comparison targets.

F03/F04 may produce a genuine base score while G2 rejects FULL qualification.
F09 Boolean measurements remain schema-valid JSON but fail native numeric QC.
F08 duplicate keys and all 262,145 retained F10 bytes are rejected without repair
or truncation. C02 null, absent and empty unknowns remain different. C03's negative
native SE is retained technically without a scientific-plausibility claim. C04
may be an exact valid report with no answerable measurements and no completion.

The complete frozen schedule is rebuilt independently: 38 outputs and 90
decisions, including native literal/abstain pairing, all failed/unexecuted
terminals, whole artifact seals, hash-chain/cleanup bindings, current READY/code
and immutable input/reference/register/fixture anchors. Scores and core aggregate
contributions are recomputed rather than trusted as serialized results. False
acceptance/rejection, no-decision and paired-discordance counts remain descriptive
for the fixed constructed scenarios.

## Fictional verification

Command executed successfully:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s planning/review-assets/preprint-p05-20261031 -p test_audit_source_validation_experiment.py -v
```

Result: **23 tests passed in 4.448 seconds**; the final quiet regression run
also passed all 23 tests in **4.419 seconds**. This includes all fourteen real
producer fictional guard/scorer/accounting outputs compared against the auditor's
independently derived facts, exact candidate bytes, stages and policy verdicts.
The producer is imported only inside that fictional integration test; its results
are comparison targets. No producer helper constructs the expected facts or
verdicts. Invented regression sources stay in an isolated temporary `data/cache`
directory whose resolved cleanup target is checked before deletion. No actual
native source or study output is read by these tests.

Other regressions cover missingness, multiplicity, abstention, non-return partial
bytes, wrong values/bindings/units/reasons, duplicate/unknown fact IDs, exact
numeric types/signed zero, malformed JSON, Unicode, BOM compatibility, group
denominators and no-decision handling. Test repetitions are not experimental
observations.

## Actual entry and resource qualification

```powershell
.\.venv\Scripts\python.exe tools/science/audit_source_validation_experiment.py --ledger <absolute-ledger.json> --ledger-sha256 <external-byte-SHA> --ready-sha256 <external-READY-byte-SHA> --seal-sha256 <external-seal-byte-SHA> --audit-output <fresh-audit.json> --authorized-actual-audit
```

The separate audit deadline is 3,600 seconds. Completed logical hash bytes are
counted and checked together with declared production work against 512 GiB;
original row passes are separately recorded and checked against the combined
four-pass cap. Win32 `GetProcessMemoryInfo` provides an independent RSS and
process-lifetime peak fallback; missing readings do not qualify the 2-GiB bound.
Physical disk/cache traffic remains unmeasured. No model, provider, network,
download or external-expert call is made. These are cooperative checkpoints,
not a hard OS watchdog or hostile-OS isolation guarantee.

Byte integrity, literal semantics and scientific validation remain separate.
All scientific validation and study independence remain unestablished. This
auditor does not make the study ready or authorize actual production execution.
