# Optional Parquet test boundary

Only `tests/test_study_source_fact_inputs.py` and focused evidence/checker files were changed. Its eight methods that construct the actual-format invented Parquet fixture now use method-scoped availability decorators. Four pure lexical-selection, duplicate-conflict, mapping and packet-schema methods remain active. No test count, fixture data, actual-format assertion or `src/asof` implementation changed.

The decorator skips only when `importlib.util.find_spec("pyarrow")` is absent, using the existing canonical reason `install the ingest extra for adapter tests`. It does not catch `ImportError`. If Arrow is installed, the fixture explicitly requires version 21.0.0 before importing the Parquet module; a wrong/broken installation is an error, not an approved skip.

The true-absence reproduction used the existing C: `env-core` interpreter without installing anything. Its original 12-method run produced eight `ModuleNotFoundError` errors, retained in `SOURCE-FACT-INPUTS-OPTIONAL-before-v1.txt` at SHA256 `a776dd29a3cf6a8972a10c3bacbc4295f9a920985f3b9361bb90089e48de6a33`.

| Targeted lane | Methods | Result | Seconds |
| --- | ---: | --- | ---: |
| Existing core environment; Arrow spec genuinely absent | 12 | Four pass, eight canonical skips; no errors | 0.004 |
| Workspace full environment; Arrow 21.0.0 | 12 | All pass, no skips | 1.248 |
| Full environment with only in-memory Arrow version changed to 0.0.0 | 12 | Eight expected version-denial errors, four pure passes, no skips | 0.010 |

The third lane is a negative control: it changes no installed package or source file. The checker requires exactly the eight intended errors and zero skips; a different failure or accidental skip fails the check. All runs used workspace cwd/TEMP/TMP and no injected source import path. They read only invented fixture data and made no model or network call. A separate read-only peer review confirmed the eight method-scoped decorators, four active pure methods and unchanged assertions.

The complete result and log hashes are in `SOURCE-FACT-INPUTS-OPTIONAL-after-v1.json`, SHA256 `9ade7ed26be4791c380f89c72fc8db199f1f8573d9d8ca8a6eaf2f21e7c606ad`.

Final pins:

- Input test: `4d2313e402e07e3621635485478b8fa8ac0af1d32f4103f2c89cd101d68e77e6`
- `check_source_fact_inputs_optional_v1.py`: `698b807d9f4d3773b156c6fe73c9026a896b846ad226be0d2aef0f8795a26ec2`

The checker retains evidence exclusively; use a fresh attempt version for another run. These focused checks do not replace the pending complete full/core validation reruns.
