# P05d descriptive analysis preparation v1

Status: preparation only. No actual experiment ledger, evaluator values, source
rows, generation packets, human returns or clinical outcomes were read or
analyzed. No actual P07 analysis was executed. The implementation is
`tools/science/analyze_source_validation_experiment.py`; fictional tests are
`test_analyze_source_validation_experiment.py` in this directory. The module
uses the Python standard library and imports no producer, compiler or scorer.

`analyze(ledger)` is a pure function over already audited serialized metadata.
It checks the exact 38 output IDs and 90 decision IDs, their case/arm/policy
associations, uniqueness, terminals, fixed twelve-unit denominator and
`scientific_validation: not_established`. The static schedule is transcribed
from the frozen DRAFT, not inferred from returned outputs. Native arm codes
`L/A` correspond to the DRAFT's literal/abstain producer labels. The constructed
fictional stratum is explicitly the generic JSON/core-control stratum; it is not
a successful native Parquet input build.

The analysis reports strict verified exact reporting separately from unchanged
80% measurement completion. The latter requires source admission and a returned
genuine scored result, but does not require strict completeness of every
unknown slot. A zero-answerable measurement denominator stays null and cannot
complete the measurement endpoint; its exact report can still be admitted.
Failed/unexecuted outputs stay in the fixed twelve-unit primary denominator.
The qualified-nonzero secondary denominator comes from all twelve entries of
`native_qualification`, independently of which outputs returned. An unresolved
qualification makes that secondary denominator/rate explicitly unknown.

The analyzer reconstructs equal-group coverage and 60/80/100% thresholds from
integer matched/answerable component counts with exact fractions, and checks
the stored core coverage, thresholds and completion. It preserves identity and
measurement family views and explicit audited fact accounting. Required family
counters are `requested`, `answerable`, `expected_unknown_by_reason`, `matched`,
`correct_unknown`, `omitted`, and `false_asserted`. Missing unknown counters do
not become zero; emitted-dependent counters may be null for malformed outputs.

Four valid and ten invalid fictional scenarios remain fixed per policy. Tables
show planned and attempted decision denominators, no-decision counts, false
acceptance/rejection counts and descriptive fractions. No-decision never counts
as successful rejection. Paired policy discordance is displayed for the same
fourteen scenarios and the same twelve native literal reports; literal versus
abstain remains a paired twelve-case display. Requested facts, policies and
controls do not enlarge an independent-study denominator. The genuine-scored
core aggregate is explicitly secondary; the entire 38/90 ledger is primary.
Resources and amortized source verification are retained separately. There are
no confidence intervals, significance tests, power estimates or causal/clinical
generalizations.

## P06 audit interface and actual P07 gate

The CLI requires independently supplied exact **byte** SHA256 values for both
the ledger and the retained final P06 audit. This is the audit interface agreed
with the independent auditor:

```json
{
  "status": "PASS_INDEPENDENT_EXPERIMENT_AUDIT",
  "method": "p05.independent_source_inclusive_experiment_audit.v1",
  "subject": {
    "ledger_path": "<absolute path to the exact ledger.json>",
    "ledger_sha256": "<externally retained 64-character byte SHA256>"
  },
  "source_inclusive": true,
  "independent_projection": true,
  "unresolved_findings": [],
  "scientific_validation": "not_established"
}
```

The subject object has exactly the two displayed fields. Other audit top-level
evidence is allowed. A generic PASS, non-source-inclusive check, unresolved
finding, different ledger, or wrong independent byte hash fails before output
reservation. The analyzer does not perform or impersonate P06's source audit.

Actual invocation requires `--ledger`, `--ledger-sha256`, `--audit`,
`--audit-sha256`, `--approved-ledger-root`, `--approved-audit-root`, and `--output`.
The ledger must be `ledger.json` in a root-approved
`data/derived/preprint-p05-experiment-<UTC>` directory. The audit is a direct JSON
child of this P05 review-assets directory or a root-approved
`data/derived/preprint-p05-experiment-audit-<UTC>` directory. No input chooses its
own filesystem authority. Existing symlink/reparse components are rejected;
reads are bounded to 16 MiB each, exact-hash checked and checked for file identity
changes. Duplicate JSON keys and nonfinite JSON constants are rejected.

The output must be a new direct
`data/derived/preprint-p05-analysis-<UTC>` directory. Existing output is never
overwritten or resumed. Complete analysis bytes and the final analysis seal are
published atomically without clobbering. The output records the ledger/audit
paths and exact byte hashes, analyzer file SHA256, absolute interpreter,
Python/platform/standard-library environment, and production timestamp separate
from scientific status. If the audited ledger contains `analysis_code_sha256`,
the live analyzer must match it before publication. If that binding is absent,
the output explicitly records that no frozen-code match was established; root
must independently compare the code against frozen P05 READY before actual
P07. The experiment producer now retains the READY analysis pin in that field.
No post-result code edit may be reused silently under this version.

## Fictional checks

Sixteen preparation tests pass with the absolute workspace `.venv` interpreter.
They use arbitrary, explicitly synthetic ledgers rather than actual results.
Coverage includes omitted/duplicate/unscheduled cells, wrong policy bindings,
nonreturn accounting, null denominators, exact 80% fractions, distinct exactness,
unknown counters, all three policies' planned/attempted denominators, paired
discordance, source/scientific consistency, independent audit/hash gates,
frozen analyzer pin mismatch, fresh output/no overwrite and duplicate/nonfinite
JSON rejection. One integration test imports **only** producer `blank_ledgers`
serialization defaults, with independently specified zero/unknown expectations;
it does not use producer guard results as an oracle. The first test invocation
had two filesystem errors from sandbox TEMP; fixtures were moved into the
workspace cache and all sixteen checks then passed. These preparatory checks
are not experimental observations.

Root's independent code/test review and final freeze are separate. Actual P07
must occur only after P06 has audited the retained actual ledger and its source
projection. No data, network or model call is made by this preparation.
