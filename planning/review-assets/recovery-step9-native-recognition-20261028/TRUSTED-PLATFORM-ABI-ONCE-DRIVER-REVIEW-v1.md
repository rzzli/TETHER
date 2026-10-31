# Trusted-platform ABI once-only driver review

Source/fake-boundary clearance for driver `507211b3cdfb728c3ffb6a238f313905f4594434da22277eb57f87219a85732c`. This is not an execution decision or native ABI qualification.

Compared with qualified census driverc6fff, the file-pinning function is AST-identical. The delta binds the new frozen parentf268/protocol5e175, requires ABI mode and the exact ordered version/default call pair, keeps recognition false and the no-model/CPU-path flag true, and validates the separately declared success literal. It does not depend on a nonexistent parent `STATUS` global. That literal matches the retained SDK seal. The parent remains responsible for exact actual argv/input/source validation.

[Six AST-extracted fake tests](TRUSTED-PLATFORM-ABI-ONCE-DRIVER-PURE-PROOF-v1.json) pass across20 scenarios: wrong decision/driver/helper/protocol/role/success/call/CPU/recognition/boolean fields; consumed output before import; success exactly once; failed or wrongly labelled results; exception, KeyboardInterrupt and SystemExit without retry. The fake parent deliberately has no `STATUS` attribute. Only one execute call site exists, with no retry path. Persistent consumed-output exclusion still relies on the separately reviewed parent's exclusive reservation before native dispatch.

The external CLI pins a separately retained decision; that decision pins the frozen driver/parent/protocol. No decision hash is embedded in those upstream bytes, so the self/decision graph is acyclic. No real parent import, SDK constructor, driver invocation, child or reported-image read occurred. A separate root decision and the final parent/protocol review remain required.
