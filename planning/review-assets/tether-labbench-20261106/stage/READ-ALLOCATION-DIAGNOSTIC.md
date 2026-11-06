# Source-only file-read allocation diagnostic

Observed during parent finalization on 6 November 2026 UTC, after the generation worker reported completion. **No frozen source was modified; no candidate, reference, model asset or active output was read by this probe.** This is a small diagnostic of one Python file-read operation, not a profile of the running parent and not a benchmark-answer result.

The retained [probe code](READ-ALLOCATION-PROBE.py) is exactly the Python body executed through stdin from the project root. The interpreter command was:

```text
data/cache/tether-scifact-env-attempt02/environment/Scripts/python.exe -I -B -X pycache_prefix=D:\Projects\drug_target_agents\data\cache\labbench-read-allocation-diagnostic-unused -
```

It read `experiments/labbench/run.py` as ordinary bytes, without importing production code. The file was 36,668 bytes, with frozen generation SHA-256 `dd2fa380a754045986bfb57111d11a9b72719e10b96c19c18875818b8a0e8e78`. The [retained results](READ-ALLOCATION-RESULT.json) reproduce the observed JSON values from that single execution; this document does not claim a second validation run.

| Requested read bound | Five-read elapsed time | Tracemalloc peak | Bytes returned per read |
|---|---:|---:|---:|
| 512 MiB + 1 | 0.4546153 s | 536,916,611 | 36,668 |
| 64 MiB + 1 | 0.0569256 s | 67,154,563 | 36,668 |
| Actual file size + 1 | 0.0007187 s | 82,367 | 36,668 |

In frozen `run.py`, `proof()` calls `read(path, 512 * 1024**2)`, and `read()` calls `stream.read(limit + 1)` regardless of the file's actual size. `recover_cases()` makes up to 16 artifact-proof reads per case; `_inventory()` subsequently reads retained files again. The diagnostic confirms that a small file read with this large requested bound can incur a roughly 512 MiB transient Python allocation. Repeated allocations therefore provide a concrete potential explanation for substantial finalization overhead. They are not evidence that hundreds of MiB of file content were read each time, nor are traced allocations equivalent to process RSS or physical I/O.

The reviewed case recovery uses dictionary/set lookups and per-case loops; recursive freezing traverses its supplied values, and canonical serialization also sorts mapping keys. No obvious quadratic-in-case-count traversal was found in these paths. The exact latency contribution remains unknown without profiling the running workflow. The five reads per condition ran sequentially, with warm-cache and concurrent-system effects uncontrolled; do not extrapolate the timings into a measured stage cost or universal speedup.

Separately, the controller captures its `parent_resources` before `_seal()`. Case recovery, publication and final inventory/sealing fall outside that recorded duration and outside the worker supervisor's deadline. Thus the current output cannot establish a hard end-to-end stage bound from those fields alone. Preserve this limitation in the final report.

A later, separately qualified implementation could use a bounded size-aware stable read or streaming hash while retaining oversize rejection and identity checks. No such change is part of this frozen run; source-inclusive replay and native scoring must use the held implementation even if this overhead recurs.
