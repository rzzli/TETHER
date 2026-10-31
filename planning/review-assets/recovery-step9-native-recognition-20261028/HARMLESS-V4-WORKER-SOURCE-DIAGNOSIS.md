# Harmless v4 overflow: bounded source diagnosis

**Finding: no explicit reachable descendant launch explains the overflow case's extra final association. The cause remains unresolved. ABI execution stays blocked.** This review reads source and retained records only; it does not rerun the worker, invoke Windows APIs, import reviewed modules, or justify a generic total-2 acceptance rule.

## Recorded path and source control flow

The actual output is `data/cache/r09-harmless-launcher-qualification-v4-20261028T202617Z`. In `execution/journal.jsonl`, sequence 18 records the overflow argv: canonical base Python 3.11.15, `-I -B`, the pinned `harmless_launch_worker.py`, `overflow`, its child-output path, the archived effective protocol, and protocol SHA256 `43dd462a3701c4abddc1196e345460277f85ac1e84d120154902d33ad95289f8`. This is a direct executable invocation, with no shell, venv launcher or command-search fallback. Creation flags are `134743044`: suspended, no-window, extended startup information and Unicode environment.

The explicit environment has eight entries: `SystemRoot`/`WINDIR=C:\Windows`, `SystemDrive=C:`, `PATH=C:\Windows\System32`, `TEMP`/`TMP` equal the output root, and both OMP thread limits equal `1`. No inherited `PYTHONPATH`, `PYTHONHOME`, `__PYVENV_LAUNCHER__`, `COMSPEC` or additional environment entry is supplied by this source path.

The [worker](harmless_launch_worker.py:77) publishes its identity, then the overflow branch writes up to 73,728 bytes with `os.write`, sleeps for 120 seconds, and raises if still alive. Every path leaving that branch does so by exception or termination. Its only explicit `subprocess.Popen` call, at line 97, occurs later in the resources path, after the overflow and sleep branches. Thus the reviewed overflow flow cannot reach that planned descendant attempt. No `os.system`, `os.startfile`, `AllocConsole`, `conhost`, multiprocessing or other explicit launch appears in the worker.

The journal observes PID `32192`, total/active `1/1`, before resume and in the first running snapshot. After the expected capture stop, it retains final raw total/active/terminated `2/0/0` with an empty PID list. This bounded source review did not observe the identity of any additional process. The independent result review owns complete artifact/chain qualification.

## Import and startup checks

Direct worker imports are `hashlib`, `json`, `os`, `pathlib`, `subprocess`, `sys` and `time`. The local `Lib/subprocess.py` Windows import path imports `msvcrt` and `_winapi`; its explicit `_winapi.CreateProcess` call is within `Popen._execute_child`, not its module-level import code. Importing the name `subprocess` is therefore not evidence that the resources call ran.

`-I` does not imply `-S`; local `Lib/site.py` still has a global-site startup path. A bounded current directory inspection found one global `.pth`, `distutils-precedence.pth`. Its statement imports `_distutils_hack` and calls `add_shim`; the reviewed implementation inserts a finder into `sys.meta_path`. No process-launch call was found there. No `*customize*` entry was present in the inspected base `Lib` or global `site-packages` listings. These are present-day source observations, not a retained complete startup/import trace at dispatch.

## Evidence and limits

Freshly checked source hashes:

| File | SHA256 |
|---|---|
| Worker | `dc388b9a83d11d76ed30403658ee31f8cbf91276ffeafca1b6f91f9b49eb9811` |
| Harmless v4 driver | `1a85332d4a4cf96960bdbea1f3105bfb444d229710bcb8a07f4d811e1aa57ca3` |
| Frozen SDK | `c111ac5f42209eb61fc49522d4cd6db544987b1c4230577404022e1add6eb2f4` |
| Local `Lib/subprocess.py` | `baa9f9138d8d20df6284f67e7d2e790f847f65e2c5370de322d54cccd737f2d9` |
| Local `Lib/site.py` | `0577e4b379d8ef4aa0ecf88a264ef18c10f72ea72119afae36524d1aae77c9bf` |
| `distutils-precedence.pth` | `2638ce9e2500e572a5e0de7faed6661eb569d1b696fcba07b0dd223da5f5d224` |
| `_distutils_hack/__init__.py` | `df81e6bcba34ee3e3952f776551fb669143b9490fdd6c4caeb32609f97e985b4` |

The EXE pin and explicit environment narrow the possibilities; they do not attest every transitive extension, startup native initializer, OS console behavior, or process-association event. Neither a console-host explanation nor SDK accounting corruption is established by this review. Preserve the failed attempt, investigate identity/accounting evidence prospectively, and keep the generic ABI predicate unchanged.
