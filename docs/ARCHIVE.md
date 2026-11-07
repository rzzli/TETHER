# Historical compatibility

Current code and documentation use TETHER. Exact earlier software and proof
identities remain in Git history. Version-two receipts must be verified with the
matching code and dependencies; renaming a package does not migrate a sealed run.

The pre-namespace implementation is pinned at commit
`b492a8fca9bb1aa500d2939b3e2d19242a55cb96`, tag
`tether-pre-namespace-migration-20261106`. Some compatibility tests recover exact
fixture bytes from this commit through [tools/history.py](../tools/history.py).
They do not rewrite or execute archived project notes.

For an original-version reproduction, use a separate checkout and its documented
input/environment requirements. Some proofs bind absolute roots as well as bytes;
a new checkout alone does not relocate those bindings. Original datasets and
model weights are not supplied by this repository.

The current public tree contains maintained code and usage documentation. Working
notes, local run records and generated research artifacts are excluded. Their
removal from the current tree does not rewrite Git history. See
[version migration](../packages/tether/MIGRATION.md) for current identities.
