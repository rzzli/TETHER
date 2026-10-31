# Source equivalence and marshal representation

28 October 2026 UTC. The [focused retained probe](OPTIONAL-ARROW-MARSHAL-REPRESENTATION-PROBE.json)
explains the failed peer comparison for `_generated_version.py`. Compiling its
unchanged source with the validated cached filename object, while retaining the
compiled code object, reproduces the original/current payload bytes. A distinct
equal filename changes a reference flag and index; serializing a temporary code
object changes the top-level reference flag and further indices. The decoded
code fields and filename values remain identical. No source/cache bytes were
normalized, repaired or executed.

This is consistent with the exact CPython 3.11.15 implementation: `w_ref` uses
object reference counts and interning when emitting reference flags/indices;
string serialization also distinguishes interned strings. [Primary source](https://github.com/python/cpython/blob/v3.11.15/Python/marshal.c)
The general module documentation describes an interpreter-specific format rather
than a canonical semantic fingerprint. [Python documentation](https://docs.python.org/3.11/library/marshal.html)

The byte-for-byte claim is therefore tied to the documented compiler/filename
object method. Independently checking the expected filename **value**, pinned
source bytes and every recursive code field remains mandatory. Reusing a
validated filename object supplies no cached instructions or source text to the
compiler. This explanation alone does not qualify the environment: the separate
full inventory, source/binary hashes, headers and path checks must still pass.
