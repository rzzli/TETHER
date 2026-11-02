# Independent review of validation failure reporting

The current `tools/validate.py` change passes its stated bounded lifecycle scope.
The destination collision check precedes prerequisites, structural checks and
discovery. Caught exceptions and KeyboardInterrupt retain a failed/interrupted
status, current stage and exception metadata. `sys.argv` is restored around
required probes, and temporary work is cleaned through its context manager.
Final atomic publication preserves a competing destination.

Four independently authored mocked scenarios pass: missing full-mode prerequisite,
KeyboardInterrupt during discovery, packaging exception after one successful
fixture test and successful required probes, and complete successful execution.
Discovery was intercepted for every scenario; no framework-wide discovery,
real package build or model/source probe was invoked. Pins and observations are
in [VALIDATOR-PEER.json](VALIDATOR-PEER.json).

No additional defect was found in this narrow correction. This does not qualify
forced process termination, durable per-test incremental records or exclusive
cross-process execution. If the final filesystem publication fails, the report
cannot be promised at the requested path; stdout/error is the available fallback.
An interruption inside unittest can omit its incomplete result counts, but is
correctly marked interrupted rather than passed.

The root's initial accidentally broad discovery transcript was interrupted and
is not passing test evidence. This peer probe's first direct-file invocation
failed before importing `tools` because its script directory was the import root;
the probe now explicitly adds the repository root and its four scenarios pass.
Neither checker setup issue is a runtime validation success claim.

The integrated data quantities match the retained scoped records. One planning
wording issue was sent to root: complete regional QTL/GWAS plus compatible LD
cannot be a universal requirement for every MR/colocalization method. ABF and
single-instrument Wald routes have different input requirements from SuSiE or
correlated-instrument MR. Preserve this method-specific distinction in Q03.
