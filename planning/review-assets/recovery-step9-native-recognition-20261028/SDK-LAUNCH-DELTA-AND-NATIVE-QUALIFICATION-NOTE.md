# SDK launch delta and next native qualification gate

Source-only assessment; no helper, compiler, SDK API, child or native target was executed. No evident x64 structure/prototype/flag/stdio binding defect was identified in c111. The overflow worker's explicit branch writes, sleeps and raises before the resources Popen code; it contains no explicit descendant call on that path. This does not instrument Python/DLL startup effects or identify the cumulative second entry.

The earlier accepted accounting probe is not an otherwise identical control:

| Item | Accepted probe v3 | c111 harmless path |
|---|---|---|
| Job association | Running Popen followed by AssignProcessToJobObject | SUSPENDED plus creation-time JOB_LIST |
| Stdio | Restricted redirected handle list; pipe stdin closed | Restricted three-handle list; NUL stdin |
| Primary thread handle | Popen closes immediately | Retained until cleanup |
| Final process-handle order | Close before final query | Query before close |
| Limits |64MiB process commit, flags0x2108 |256MiB process and Job commit, flags0x2308 |
| Context | Project cwd; minimal Windows environment | Fresh output cwd; added TEMP/TMP and OMP limits |
| Work | Sleep then terminate | Protocol/source validation and overflow/other fixture work |

Installed subprocess.py1482-1507 already builds a redirected stdio HANDLE_LIST with close_fds=True. Upstream CPython3.11.15 _winapi.c1230-1239 also adds extended-startup and Unicode-environment flags; the explicit new creation-flag difference is SUSPENDED. Do not treat extended startup or restricted stdio as wholly new features. [CPython primary source](https://raw.githubusercontent.com/python/cpython/v3.11.15/Modules/_winapi.c). This is source correspondence, not reverse engineering of the installed extension.

The agreed minimal next gate is an own standalone C++ harmless worker matching the retained bridge's **/MD**, not /MT. build_public_c_bridge.py350-352 and retained compile argv both specify /MD. Inspect/pin its actual CRT imports after a separately authorized build. Keep the existing SDK parent and fixed256MiB limits; predeclare four cases once each, strict generic final total1 and only the explicit rejected-child resource final total2. Do not change counter policy again to obtain a pass. A native pass would qualify that compiled-child architecture only; the negative Python runs and original active2 remain unexplained and preserved.

If that native fixture has any unexplained count, stop and require a separately declared job-scoped PID diagnostic. Its minimal observer needs CreateIoCompletionPort and GetQueuedCompletionStatus, existing SetInformationJobObject(class7), and the16-byte public association struct; optional query-only OpenProcess adds one binding. Associate while empty; cap64 messages/16 reported PIDs within the existing time reserve. Retain raw NEW/EXIT IDs and read-only image/creation metadata where available, never terminate by observed PID or enumerate globally.

This observer is not implemented or authorized here. ACTIVE_PROCESS_LIMIT supplies no PID; notifications can be absent and reported IDs can expire/recycle unless a handle is held. Therefore missing events cannot prove that no second process existed. [Microsoft job notification contract](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_associate_completion_port), [bounded dequeue API](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-getqueuedcompletionstatus). A failed or incomplete diagnostic remains inconclusive, never a total2 waiver.

Read anchors:

- Frozen SDK: `c111ac5f42209eb61fc49522d4cd6db544987b1c4230577404022e1add6eb2f4`
- Worker: `dc388b9a83d11d76ed30403658ee31f8cbf91276ffeafca1b6f91f9b49eb9811`
- Accepted probe: `d5f23f471adc9d4ee293d2bee27a3d85443b578a4a116e50ce53ccd235920e49`
- Installed subprocess source: `baa9f9138d8d20df6284f67e7d2e790f847f65e2c5370de322d54cccd737f2d9`
- Retained builder: `733a47bb8c047e129560c0c68dd63d97cf09c95c23b3cabd105df7791927c09c`

Recorded UTC: 2026-10-28T20:38:17.934147+00:00
