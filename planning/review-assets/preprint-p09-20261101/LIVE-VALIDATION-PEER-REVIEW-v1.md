# Live validation diagnostics peer review

PASS for accounting and fail-fast behavior at these SHA256 pins:

- `tools/validate.py`: `6338c4f0e0f5ed4ed95d9d2615a9efcd03cf2896775bd98eebb36f46ddf1a36f`
- `tests/test_validation_live_errors.py`: `b0ce320ab7d96250d0959230374b9dc272cd260ab7886b7a643ee18c84534302`
- Existing gate tests: `061751a6e22a0cee893c25799a12d09e25a14a2a22090a7d097f2357d2863f97`

`LiveErrorResult` calls the standard superclass accounting before printing/flushing the retained error or failure traceback. Standard fail-fast stopping therefore records the failure first; `successful_tests` still rejects it. The default remains complete discovery/execution without fail-fast. With fail-fast enabled, an all-success suite still executes all cases. Approved skips remain core-only; full-mode skips and unapproved core skips still fail the gate. Discovery, structural checks, package checks and required-probe rules were not weakened. A diagnostic stream exception propagates rather than producing a passed report.

Targeted run: `python -m unittest tests.test_validation_live_errors tests.test_validation -v`, **6 PASS in 0.070s**. Log `LIVE-VALIDATION-PEER-TESTS-v1.txt` SHA256 `2e2339476cd89c60517085c5327367ba459c2e553396566c764e432caaf62a78`. Tiny synthetic probes also confirmed full execution on success, continued execution after approved skips, and rejected gates after unapproved skips.

Known diagnostic limitation: inherited `addSubTest` records subtest failures without using the new immediate traceback hook. A direct subtest probe recorded one failure, no immediate marker, and failed both core/full eligibility. Its traceback remains available in normal final diagnostics. This does not create a false pass; immediate subtest trace support is not claimed by this review.

Review was read-only apart from these notes/logs. No runtime/source edits, actual provider/data reads, native process, model, network, installs or long suites occurred. This is not a substitute for the independently running broad full/core gates.
