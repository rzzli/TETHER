# Source-fact cell/controller discovery repair

Only the two owned test modules and this focused checker/evidence were changed. No `src/asof`, frozen controller, model protocol, sealed production artifact or data file was edited.

The original package-mode command used by `tools.validate` was reproduced before correction:

```text
.venv/Scripts/python.exe -m unittest discover -s tests -t . -p test_study_source_fact_c*.py -v
```

It produced two loader errors because the modules used a bare sibling import. The retained `SOURCE-FACT-DISCOVERY-before-v1.txt` has SHA256 `182e8013c7e0963bf569221a530bfbf3c1ce7760c54945ec40a70213e7266c52`. Those loader failures mean the previous default package-discovery gate had not executed either module's 32 methods through `tools.validate`; they were not 32 passing test results.

Each module now selects a relative sibling import when `__package__` is set and a top-level sibling import for `-s tests` discovery. There is no broad `ImportError` fallback that could hide a dependency failure.

Once imports worked, both modes discovered 32 methods but failed the same controller test with `Original catalog pin differs`. These failures remain intact in `SOURCE-FACT-DISCOVERY-{package,top-level}-after-v1.txt` and `SOURCE-FACT-DISCOVERY-after-v1.json` (JSON SHA256 `c54aa3aaf7f251fcdeeee9adffb29c0c5a228722088bc3c63c12ab29991f9cdc`). That old test depended on retained production generation packets and catalog metadata. Its failed execution opened those retained derivative packets before catalog rejection; no packet values were inspected or printed by the reviewer. These first attempts are not represented as wholly fictional reads. No provider-original, evaluator-value member, model, human response or protected clinical input was opened.

The corrected controller fixture is self-contained: 111 invented flat receipt-bound source nodes and symbolic inventory sizes, three invented packet/task pairs, a local catalog and neutral plan, exact hashed files, genuine build journals and preparation seals. The existing production admission and original-only/source-role/date guards run unchanged. The test asserts that the evaluator sentinel is never opened, a changed preparation seal fails, and a changed fixture catalog fails. All paths used by admission are beneath its temporary invented workspace. The test's environment facts are explicitly fictional so a core installation does not need PyArrow distribution metadata.

Final focused results, retained in `SOURCE-FACT-DISCOVERY-after-v2.json` at SHA256 `4148d0774bc9fc9ed044f12cde7cdc09316829f7bdb15fb762e365ce4edd7710`:

| Mode | Methods | Result | Seconds |
| --- | ---: | --- | ---: |
| Package discovery, `-s tests -t .` | 32 | PASS | 1.353 |
| Top-level discovery, `-s tests` | 32 | PASS | 1.351 |
| Dependency-free package discovery, `python -S` | 32 | PASS | 1.363 |

The `-S` run disables site packages and uses only the explicit source `PYTHONPATH`; the same 32 methods pass without Arrow or other installed dependency packages. Every run used the absolute workspace interpreter/cwd and workspace TEMP/TMP. The corrected v2 fixture opened no retained production packets or provider originals and made no real process, network or model call.

Final SHA256 pins:

- `tests/test_study_source_fact_cell.py`: `85d0f72dc32f5e5b39ddf36e578965be7cbb57949b04511acc03f740b45d7603`
- `tests/test_study_source_fact_controller.py`: `998434189057f53c4c3fdc640d1923ab226f26ab42efc3d25e68ac30607c8589`
- `check_source_fact_test_discovery_v1.py`: `426f5a38750486a4ea75137e149387cc75853bc712be841f398bf0261b5857ac`

The checker uses exclusive versioned evidence files. Use a fresh `--attempt v3` or later for any rerun; do not replace failed evidence. This focused result does not replace the separately required full/core shared validation reruns.
