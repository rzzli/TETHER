# Once-only driver source/fake review

Source-only clearance for `execute_self_module_census_once_v2.py`, SHA256 `c6fff0d0b44b942fd2d7766f150d3f1da194b29325e6af2b2d72214085f12419`. This is not a root decision or native execution authorization.

The binding is acyclic: the external CLI supplies the decision hash; that decision binds the frozen driver, parent and protocol; the driver embeds the parent/protocol hashes but no decision hash. Its self-pin is compared to the separately retained decision. No parent/protocol bytes were changed by this review.

[Six AST/fake tests](SELF-MODULE-CENSUS-ONCE-DRIVER-PURE-PROOF-v2.json) pass. They cover wrong decision hash, wrong driver/helper/protocol/role and boolean/integer confusion, consumed output before import, exactly one successful execute callback, failed return/exception without retry, and KeyboardInterrupt/SystemExit without retry. The test executes only extracted `main` against authored in-memory pins/files/import/parent fakes. No actual parent import, SDK constructor, driver invocation, child or reported-image read occurred.

The original v1 accepted `maximum_attempts=true` through Python integer/boolean equality. Its source and [failed regression proof](SELF-MODULE-CENSUS-ONCE-DRIVER-PURE-PROOF-v1.json) remain unchanged. V2 adds the explicit integer type check and strict JSON comparison of limits; the same six-method suite, including the limits boolean vector, passes.

The driver calls `helper.execute` once and contains no retry. Persistent consumed-output exclusion still relies on the separately reviewed parent's exclusive output reservation before dispatch; these fake tests do not independently prove a process or filesystem barrier. Root must separately retain and pin the decision before any actual invocation.
