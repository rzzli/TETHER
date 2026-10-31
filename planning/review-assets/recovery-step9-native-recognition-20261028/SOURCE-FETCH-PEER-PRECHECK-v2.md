# Exact source-fetch v2 peer clearance

The separately frozen helper
`e49bc2907f864e1c0e43621865742e566a409390d1b3552fbf92a583d9443ea5`
and protocol
`633b630163060b3216ad94de60aa90799791565981a38971fd4cfdaed16bf607`
have **no remaining blocking finding within this source-only acquisition scope**.
Execution still requires root's separate exact-protocol decision.

The v2 diff rejects any parent `error_class` or `interrupted` key before source
qualification. Its remaining changes separate protocol/fixture paths and pin
the unexecuted v1 artifacts and peer rejection. The twelve URLs, pinned commit,
1 MiB per-file/4 MiB aggregate retained-body bounds, 20-second whole-child cap,
300-second aggregate checkpoints and 30-second finalization reserve are unchanged.

Read-only verification rehashed **116 pins** and checked **145 distinct path
components** without symlink/reparse violations. Both proposed acquisition
directories remain unconsumed. Both retained no-network fixture journals verify:

- An interrupted read claiming zero retained bytes becomes unknown receipt.
- An otherwise successful child carrying parent interruption is also rejected.

Each fixture retains its 1 MiB conservative reservation and stops the remaining
eleven requests. Both have zero actual children/requests; their journals and
underlying synthetic captures match the records. This verifies the intended
regression evidence without rerunning fixtures or importing the helpers.

Review also covered fixed host/path identity, redirects/proxies, exclusive output,
`lstat` ancestry, fixed isolated dispatch, capped captures, owned kill/reap,
post-cleanup child timing, hash-chained progress, no retries and terminal failure
vetoes, including after receipt publication and lease cleanup. Retained-body
accounting is not measured network transfer. Filesystem timing is enforced by
cooperative checkpoints, not an OS sandbox.

[The companion record](SOURCE-FETCH-PEER-PRECHECK-v2.json) retains exact hashes and
checks. This clearance authorizes no fetched-code execution, build, DLL/GGUF
access, vocabulary/model load, context, inference or server. The peer review
performed none of these and made no network requests.
