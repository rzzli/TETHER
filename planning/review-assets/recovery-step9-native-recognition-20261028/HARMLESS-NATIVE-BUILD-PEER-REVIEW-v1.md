# Native harmless build v1: focused peer review

**HOLD for one narrow PE-policy correction.** Exact helper fb096d3d... and protocol73b8bfcf... remain unexecuted.

pe_policy treats every `_exec` prefix as process launch, including CRT `_execute_onexit_table`. That helper runs CRT exit callbacks; it is not a process-launch function. [Microsoft reference](https://learn.microsoft.com/en-us/cpp/c-runtime-library/execute-onexit-table-initialize-onexit-table-register-onexit-function?view=msvc-170). A legitimate import would therefore fail this classifier. This is not a claim that the pending PE imports it. Match the actual execl/execv families or exclude the CRT helper and add one pure acceptance case; preserve this preparation.

Other checks pass:206 current pins/all193 inherited, exact c22 source copy, fresh absent output, two /MD compile/link commands, frozen733a tool/audit/PE/environment reuse. Twelve retained pure artifacts validate, including both three-event journal chains, ordinary complete seal and primary-plus-late-close failure veto. Cleanup is honestly scoped to context-manager return, not individual-handle attestation.

No other material blocker was identified. No helper, pure test, compiler, API or worker ran during review. This review grants no compilation or execution permission.
