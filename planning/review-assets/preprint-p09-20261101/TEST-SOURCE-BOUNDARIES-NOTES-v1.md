# Default-test portability and optional-import repair

The reviewer changed only the three authorized tests plus focused evidence/checker files. No core runtime, P05 producer, frozen source bundle or data artifact was changed by this repair. A separate read-only peer review found no remaining issue in these changes.

The diagnostic test no longer discovers an archived manifest or follows its request paths. Its replacement explicitly loads the packaged, authenticated `synthetic-context` and `synthetic-orientation` resources, then checks both current and simplified codec roundtrips while `Path.exists` and `Path.read_bytes` are blocked. The existing four exact synthetic HTTP-payload hash assertions remain unchanged. The method count is unchanged.

Former optional real-request parity is separate, unqualified local integration scope. The default suite now makes no claim that it replayed those historical requests. Such a check requires explicit caller-supplied inputs and separate qualification; it is not silently enabled by local file presence. The original test source remains in Git, with its exact before hash recorded below. No old manifest or request bytes were opened to reproduce or repair the problem.

The Parquet method now skips only genuine package absence, using `install the ingest extra for source-audit tests`. Installed wrong versions raise `ContractError` before the Parquet import, and broken imports propagate as errors. No broad import exception is caught. Its literal negative-zero, absent-schema and invalid-row assertions remain unchanged. The linked validation metatest uses valid fake package specs and asserts that wrong/broken installations have one error and zero skips; neither core nor full validation accepts them. Genuine absence alone has one approved core skip.

Controlled before/after probes establish the mechanism without actual data:

- Before: forcing the old manifest-presence branch attempted one implicit archive read, intercepted before I/O; a broken Parquet import became a canonical skip that core validation accepted.
- After: the explicit synthetic codec test passes with discovery blocked; wrong version and broken import each produce one error, zero skips, and failed core/full gate eligibility. Genuine absence retains the canonical skip.

| Existing environment | Targeted methods | Result | Seconds |
| --- | ---: | --- | ---: |
| Workspace full environment, Arrow 21.0.0 | 37 | PASS, no skips | 1.029 |
| Existing C: core environment, no Arrow | 37 | PASS, one canonical optional skip | 1.033 |

Both runs use the three repaired modules, workspace cwd/TEMP/TMP and no injected source import path. No package was installed, source/provider file opened, model launched or network request sent. The no-Arrow lane still runs all pure tests. These focused results do not resolve the unrelated failed full-v2 integration test or replace final broad validation.

| Test source | Before SHA256 | After SHA256 |
| --- | --- | --- |
| `tests/test_study_diagnostic.py` | `2d5da677e9ad9896b03e608d10303949d67882a1e1b25cbba43c8e4b149e9c73` | `1ac96b84c2079d6e26dfb33b0172e3e573e01b44d5038943d704d6e541f7d0e4` |
| `tests/test_study_source_fact_sources.py` | `42acace06fe4e53dc3c3c9f4a05d093aa890809ba36ae0c038b504bdf108fdcc` | `827e7ce4d322f0916975a63111e693a0e456d2b064759a9a183931ae7a254e68` |
| `tests/test_validation.py` | `65230f33691386a24dd6382bf15e7901c9820fefde89d4099a6329965329beb8` | `061751a6e22a0cee893c25799a12d09e25a14a2a22090a7d097f2357d2863f97` |

Retained evidence:

- `check_test_source_boundaries_v1.py`: `dec0cc082f683b55509d61eb1cf05bb2dd3ce29b55ae0a2111e6398ff296bfff`
- `TEST-SOURCE-BOUNDARIES-before-v1.json`: `57fcf6416c9b116ee05bf9b43d0b9829b3309625a71800fd468ebfbefeae3408`
- `TEST-SOURCE-BOUNDARIES-after-v1.json`: `507b4ab0aa08f6c72ad51b2117d13f86e0cee08c88bc428541941bd98174367c`
- `TEST-SOURCE-BOUNDARIES-full-v1.txt`: `11b1560cc2a8761e903d132ffd140771138622de47364317ef740eb50b5c901e`
- `TEST-SOURCE-BOUNDARIES-core-v1.txt`: `cdcc83a157fdd0ebe33f9919b42d9c1d58eafadf7a21350db8e70c96fdb6fd97`

Before probes require the original test-source version; after probes target the replacement. Evidence publication is exclusive and preserves earlier outcomes.
