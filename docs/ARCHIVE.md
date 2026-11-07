# Historical evidence and reproduction

The current repository uses TETHER throughout its executable package and project
documentation. Exact historical sources, receipts, logs, protocols and review
packets are preserved at
[tether-pre-namespace-migration-20261106](https://github.com/rzzli/TETHER/tree/tether-pre-namespace-migration-20261106),
commit `b492a8fca9bb1aa500d2939b3e2d19242a55cb96`.

Those originals retain their actual identifiers. They were removed from the
current branch rather than edited into invalid receipts. Local bulk data,
acquisition receipts and paused experiment outputs are also unchanged.

To reproduce an old experiment, use its original code and environment:

```powershell
git fetch origin --tags
git worktree add --detach data/cache/original-reproduction tether-pre-namespace-migration-20261106
```

Use a fresh destination. Historical runtime dependencies and external datasets
still need their original versions and access permissions. The current engine
does not claim semantic compatibility with old execution fingerprints.
Some historical proofs also bind absolute data or environment paths. A worktree
alone does not relocate those proofs; follow the original run's root requirements
instead of rewriting its hashes.

Historical prose in the current tree uses the current project name for
readability. Its dated measurements and hashes refer to the original checkpoint,
not to experiments rerun with the renamed software. Refer to that checkpoint for
exact historical commands, filenames and quoted technical identifiers.

The local preservation ZIP was checked against every original Git blob:
10,226 files, 337,071,357 uncompressed bytes. Archive SHA-256:
`9a3bc123ae17dcee10840d1fb13ad48af1f662cff609d336432be25a67e7fa25`.
It is an ignored local backup; the public tag is the portable source of history.
