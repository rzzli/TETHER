# V3 receipt-path supplement — peer clearance

The separately retained supplemental fixture supplies valid reservation,
worker-PID/PPID and accepted-environment metadata, together with otherwise clean
process/capture results. Its raw captures and two-event journal verify that the
frozen v3 `collect` rejects specifically with **`RuntimeError: Incomplete/unbound
source receipt`**. The parent marks receipt unknown, retains the 1 MiB
reservation and stops the remaining eleven requests. There were zero actual
children or requests.

This resolves the test-evidence hold in
[the original v3 precheck](SOURCE-FETCH-PEER-PRECHECK-v3.md). That precheck and
the original missing-identity fixture remain preserved; neither is relabeled.
The supplemental helper/report hashes are respectively
`9c5a4ba1cfc58b3867adb68d718b706d3e64accf4b6014e4d1a06cf0d2a6b231`
and `15cb6a04076fd142940e2f6d7b6316f7b896dc4fd1e0c0f2ad3555b3b1b6ecdc`.

All **139 original protocol pins** rehash unchanged, and the v3 output remains
unconsumed. No source logic, URL, acquisition limit or runtime policy changed.
There is no remaining blocker within this source-only scope, conditional on a
new root decision binding the exact helper `f923e3bd…0387bc0f`, protocol
`8b07e457…1f85158`, original held precheck, supplement helper/report and
[this supplemental clearance](SOURCE-FETCH-PEER-SUPPLEMENT-CLEARANCE-v3.json).

The peer inspected source/raw evidence and hashes only. No helper was imported,
no fixture rerun, and no request, native call or GGUF access occurred. This
clearance is not source-fetch execution, process-tree containment, native
recognition or scientific qualification.
