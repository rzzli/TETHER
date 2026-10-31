# Pending metadata APIs and return-order scope

The six proposed input-stream APIs do not perform ancestry checks or directory
enumeration. Those operations are a **separate pending platform stage**, and the
output writer also needs its own exact API census before any live implementation.
The original design files remain unchanged.

The proposed metadata stage uses `GetFileAttributesExW` for a precomputed exact
ancestor roster and known scan directories. This call returns attributes without
transferring a handle. It can inspect a link's attributes, but that observation
does not remove namespace race limitations. [Microsoft documentation](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfileattributesexw)

Bounded run-root scans would use `FindFirstFileExW` and `FindNextFileW`. A valid
initial result transfers a search handle to its reserved owner slot. Failed
result buffers are undefined; ordering is not guaranteed. Only an observed
`ERROR_NO_MORE_FILES` ends an established iterator normally. Unknown/reparse
entries are never opened or traversed. [Initial search](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-findfirstfileexw),
[continuation](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-findnextfilew)

Search handles require `FindClose`, rather than the stream port's `CloseHandle`.
Each gets one close attempt, with known failure or uncertainty vetoing completion.
[Microsoft documentation](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-findclose)

Prospective caps are two scans, eight declared directories per scan, depth four,
64 non-dot entries plus bounded dot/overflow observations per scan. This permits
at most16 initial searches,178 continuations and16 search closes. The unique
ancestor roster is capped at1,024 before inspection; directory checks add at
most16 attribute calls. The exact event reservation must still fit the existing
fixed allowance. These are design proposals, not implemented or activated limits.

“Immediate registration” means the earliest application assignments **after
ctypes makes a return visible to Python**. It excludes deliberate record
allocation, conversion, identity queries, clock checks or logging before that
assignment. It cannot make native return conversion atomic or allocation-free.
If Python does not observe a return, ownership/byte effects remain unknown; the
component cannot promise that no OS resource was created or that it was closed.

The pending sink census is explicit: one `CreateDirectoryW` for the fixed new
namespace, at most nine `CreateFileW(CREATE_NEW)` outputs, synchronous `WriteFile`,
`FlushFileBuffers` and one `CloseHandle` per output. Its proposed byte/record-derived
caps are2,460 writes and2,065 flushes across at most16,809,984bytes. Failed or
unreturned writes are never retried; successful partial writes retain their
counts and consume the same fixed budget. There is no rename, replacement,
recursive-directory or hidden filesystem-wrapper fallback. Exact bindings and
caps remain subject to source/SDK and independent review before implementation.
The signatures and basic behavior come from Microsoft's
[directory](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createdirectoryw),
[file](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew),
[write](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-writefile)
and [flush](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers)
references; the numeric caps are this proposal's limits, not API guarantees.

The loader's finite own-module/dependency map also rejects preloaded own-helper
objects in `sys.modules`. It accepts only fresh modules compiled from this
invocation's leased captured bytes. Relative imports resolve through that exact
map, and the approved standard-library whitelist freezes explicitly. No default
path finder, importlib, linecache or traceback source lookup supplies own code.

Implementation remains held pending root and independent review. A subsequent
source/pure phase may implement origin/handoff and injected ownership interfaces;
it would not implement or invoke these real platform APIs.
