# Generation worker cache-root correction proposal

**Status: proposed only; held experiment sources remain unchanged.** Prepared after the root identified a pre-dispatch path mismatch. No benchmark candidate or model call was made by this regression.

`run_stage` exclusively reserves a generation directory under `data/benchmark` and creates its worker import prefix at `<generation>/worker-import-cache`. Both `_worker` entry and final checks instead require the prefix to be below `data/cache`. The exact expected-prefix equality cannot overcome this incompatible root constraint. Thus the intended new generation worker fails before source verification or model startup.

The minimal proposed patch changes only the two worker checks from `cache_root=ROOT/"data/cache"` to `cache_root=Path(output).parent`. Here `output` is the exclusively reserved worker directory `<generation>/worker`; the authorized prefix remains inside the reserved generation directory and must still equal the exact recipe path. Parent-process checks continue to require `data/cache`. Neither `empty_import_cache` itself nor its isolated-mode, bytecode-disabled, empty-directory or exact-prefix guards change. There is no relocation of artifacts or workaround in runtime settings.

| Evidence | Status |
|---|---|
| [Held-source regression](red01.log) | Expected failure: valid intended path rejected at both worker checks, lines 238 and 283. Three tests ran; one failed. |
| [Proposed-copy regression](proposed-green01.log) | Three tests pass: the valid intended path passes both checks; different expected paths and populated prefixes remain rejected. |
| [Regression script](test_worker_cache_path.py) | Extracts the actual two check expressions from the explicitly hashed source and evaluates them with the real runtime function in fresh `-I -B -X pycache_prefix=...` child interpreters. No mocked path guard. |
| [Held source copy](run.held.py) | Original SHA-256 `e1a5dcd29460aab5afd829316722b96e92f76a05b42c19ed8fad187787dabba2`. |
| [Proposed source copy](run.proposed.py) | Candidate SHA-256 `dd2fa380a754045986bfb57111d11a9b72719e10b96c19c18875818b8a0e8e78`. |

Fictional outputs are retained under `data/benchmark/labbench-path-regression-red01` and `data/benchmark/labbench-path-regression-proposed01`. Each records child stdout/stderr. Prefixes remained empty except for the deliberately created negative-control sentinel, which remained intact. Only cache-check expressions execute; this is a path/bootstrap regression, not a complete worker, containment, collection or inference qualification. The original ten controller tests mocked the cache guard in their worker-loop integration control, which explains why that test did not detect this mismatch.

After collection closes, the root can apply the two-line patch, rerun this regression against `experiments/labbench/run.py` using a fresh output, rerun the combined component bracket and freeze a transparent generation revision. The older collection code pins and failed-first evidence must remain unchanged. Do not claim the held implementation is fixed based on the passing proposed-copy test.
