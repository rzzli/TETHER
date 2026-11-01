# Final P09 authority fixture/test closeout

1 November 2026. This was a narrow test-contract migration; no producer code was edited and no actual original/source reconstruction or model/network operation ran.

The positive protocol fixture now explicitly sets `actual_reconstruction_authorized=True`. One added table-driven method rejects missing authorization, `False`, integer `1`, and boolean `schema_version=True`. Each negative document receives a newly computed correct external byte SHA, so rejection exercises runtime authority rather than a stale digest. The test asserts that only the protocol file is read and that no bundle descriptor/source read occurs.

The updated suite ran once with the absolute workspace `.venv` interpreter and workspace TEMP/TMP: **19 methods passed, zero failures/errors/skips, 19.467 seconds**. Existing fictional CLI/core/filesystem integration coverage remains included. Development PYTHONPATH was used; this is not installed actual-source qualification.

| File | Exact SHA-256 |
| --- | --- |
| `paper/release/code/tests/test_cli_v1.py` | `91fe3cef8a35c68b39512d07dadba650030b5a9d25fee61996dcd15082185249` |
| `paper/release/code/src/asof_p05_replay/authority_v1.py` | `bdb615d12175c0fc23e79d8c1021113caa2d4b6d74b9cde67ddabdf00b5a941e` |
| `paper/release/code/src/asof_p05_replay/cli.py` | `70a22a50386bcae3d6f5a9eebd62447d0cb6a64a73e97698ed800dd9c9ab541e` |

Root's preceding run session 34342 reproduced three assertion failures and one error from the older positive fixture after the authority predicate was strengthened. Those are expected preparation/test-contract migration failures, not native-source or reconstruction failures. This closeout preserves that distinction.

The authorization field is root's runtime reconstruction authority. It is separate from owner publication declarations and creates no new request for external expert approval. Actual installed/relocated reconstruction, independent source audit and release qualification remain separate steps after the appropriate freeze.
