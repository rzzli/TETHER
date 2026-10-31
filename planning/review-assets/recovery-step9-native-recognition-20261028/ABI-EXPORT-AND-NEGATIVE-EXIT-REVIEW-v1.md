# ABI failure: static export ownership and terminal evidence

**HOLD reuse of the v3 bridge/EXE for the known export-owner defect.** The consumed negative attempt and all prior source/build/review assets remain unchanged. This source-only review authorizes no rebuild, DLL load, API call or retry.

Own bounded PE parsing rehashed the exact four approved DLLs and enumerated named exports without loading them. llama.dll has282 names and every one of the15 required LLAMA names, including llama_version (ordinal257, RVA1105568) and llama_model_default_params. This is not an unavailable-version-symbol finding.

The bridge resolves all ten GGML names from the ggml.dll handle. Five are absent there and present in ggml-base.dll:

| Owner ggml.dll | Owner ggml-base.dll |
|---|---|
| ggml_backend_load | ggml_backend_reg_name |
| ggml_backend_reg_count | ggml_backend_reg_dev_count |
| ggml_backend_reg_get | ggml_backend_reg_dev_get |
| ggml_backend_dev_count | ggml_backend_dev_name |
| ggml_backend_dev_get | ggml_backend_dev_type |

All required named entries are direct nonzero exports without forwarders. The first predicted missing lookup in constructor order is ggml.dll!ggml_backend_reg_name. The old generic error did not capture the actual owner/name, so this is a source/table inference, not a per-call trace. Eager resolution of unused registry/device functions happens before either intended ABI query. [GetProcAddress retrieves a named export from the specified DLL and requires exact spelling/case](https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getprocaddress).

The bounded export proof is `ABI-EXPORT-STATIC-CROSSCHECK-v1.json` SHA64c0f7644360b0ddf2983db279ff92dd5e0f89afa34ca3aa4bb406501cb27ae8. Earlier build preparation's static_runtime stored hashes and ordinary/delay imports; the post-build checker checked the EXE's forbidden imports. Neither compared dynamic lookup names against the selected DLL exports. Public headers/decltype proved declarations and pointer types, while GetProcAddress names were string data with no target import-library link check. The same backend header declares both groups with GGML_API and does not establish which selected handle owns each export. The peer missed this preventable mapping check; build success was never ABI success and is not reinterpreted now.

The proposed v4 split is supported: retain LLAMA15 against llama; explicit five-name ggml and five-name base groups; pass the already loaded base handle; preserve typed declarations, mode/load/call policy and all gates. Report fixed owner plus symbol on failure, with no fallback or substitute. Before any compiler dispatch, static regressions must make old v3 fail exactly these five mappings and make v4's disjoint groups cover all original names at the correct pinned nonzero/direct exports. Include wrong-owner/missing/zero-RVA/changed-pin negatives and bounded table validation. This addresses export ownership only; it does not prove ABI compatibility.

The parent has a separate evidence gap: nonzero exit is raised before EOF drain/final Job/peak queries, then Owner.cleanup closes their handles. The actual missing terminal observations remain unknown. A narrow new parent helper should record observed exit failure as primary, independently attempt bounded drain/EOF, raw final Job plus generic evaluation, and limits/peaks before close. Secondary query/capture/publication errors cannot replace the exit primary or suppress the other steps/owned cleanup. Use the work deadline with cleanup reserve; expired work is explicitly skipped/unknown.

For unknown creation, absent process handle, failed wait or a still-live child, label observations pre-cleanup/unknown rather than final. Reuse unchanged Owner.cleanup for termination/reaping/closure; do not build another termination framework for the known-exited negative case. Any state after handle close remains unobserved unless it was retained earlier. Tests should cover exit2 ordering, each independent observation fault, unknown creation, observation timeout with cleanup still running, and primary-plus-late-close/seal vetoes. SDK3bf remains unchanged; no current result is repaired or rerun.
