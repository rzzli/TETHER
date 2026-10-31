# Acceptance publication correction

28 October 2026 UTC. V4 passed every evidence gate and then failed to publish
with `PermissionError: WinError 5` at the same-directory `os.link` call. The
temporary file was removed by its existing cleanup; `acceptance.json` remained
absent. Preserve [the observed failure](ROOT-ACCEPTANCE-ATTEMPT-v4.json) and v4
helper unchanged. The precise hard-link denial cause and filesystem type were
not established; this was not an automatic approval-review rejection.

V5 changes only publication and its supporting function. It requires Windows,
writes and fsyncs an exclusively created temporary file in the resolved final
directory, closes it, then calls `os.rename` without replacement. On Windows
this operation rejects an existing destination. The same-directory source and
destination avoid a cross-filesystem move. [Python documentation](https://docs.python.org/3.11/library/os.html#os.rename)
It does not use `os.replace`, copy over an existing acceptance, change permissions
or require elevation. This does not claim power-loss durability or independent
backup guarantees.

All five [publisher-only fixtures](ACCEPTANCE-PUBLICATION-V5-RESULT.json) pass:
complete publication; preservation of an existing destination; exactly one
complete winner from two concurrent writers; no publication on injected fsync
failure; and a non-Windows stop before file creation. Fixtures run solely in
a new retained cache directory; they do not execute acceptance aggregation,
project/runtime modules, native targets or models.

Every metadata, source, wheel, corpus, installed, compatibility and exact-five
cache-derivation gate remains identical to v4. Re-run that unchanged aggregation
with the reviewed publisher to obtain a newly sealed acceptance; passing the
publisher fixtures alone is not acceptance. Retain all prior failure records.
