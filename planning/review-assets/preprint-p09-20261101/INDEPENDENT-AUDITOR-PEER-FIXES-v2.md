# P09 independent auditor peer fixes

The focused transaction and value-free bridge regressions pass: 12 tests in 0.573 seconds. The retained failing-before run recorded 28 false-accept subtest failures in 12 tests. Journal tamper fixtures rebuild the hash chain and final receipt, so the tests check semantic byte bindings after ordinary integrity checks succeed.

The auditor now binds the terminal journal entry to the exact reconstruction bytes and the comparison journal entry to the protocol-pinned comparison bytes. It also checks existing schema and scope fields with type-sensitive equality, exact historical guard inventory, complete historical decision fields, and typed source-derived denominators. The bridge decision schema omits `output_cell_id` by its declared export contract; identity remains bound by the fixed decision ID/policy schedule.

Only `audit_v1.py` and its tests changed. The complete invented 137-file, 38-output, 90-decision fixture was migrated to the same report/seal/receipt and journal fields. A fresh complete run is deferred until the narrow peer review closes. The peer separately reported the pre-fix 18-test suite passed in 100.758 seconds; that result does not validate the new guards.

The JSON companion records exact code and log hashes. The v1 implementation report and all earlier failures remain retained. No actual original sources were opened, no actual reconstruction was run, and no producer or frozen P05 code changed. Actual-source and installed release qualification remain pending root freeze and explicit authorization. Scientific validation and study independence remain unestablished.
