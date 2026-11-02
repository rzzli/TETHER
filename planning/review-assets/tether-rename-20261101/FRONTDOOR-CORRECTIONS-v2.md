# TETHER front-door correction closeout

**PASS: 36 owned fictional methods in 13.239 seconds; 12 unchanged independent probes in 0.306 seconds.** Four independent before-fix failures now pass. Prior 26-method logs and implementation notes remain unchanged.

The reader now delegates to the unchanged core stable bounded reader. Metadata/journals have an explicit 64 MiB limit; dossiers have a separate 256 MiB limit. Oversized/nonregular inputs reject before open; chunks are bounded; links/reparse and changed descriptor/path identities reject. Manifest/journal parsing uses the same captured bytes as hash checks. Outer/inner inspection uses bounded journal snapshots. Engine verification and direct legacy verify/inspect through the new front door preflight journals/traces without changing the engine.

Any exception from engine communicate now attempts bounded termination/draining, killing/draining if necessary and waiting. Original OSError/SystemExit identity is preserved; KeyboardInterrupt retains its original cause through EngineInterrupted. Failed cleanup, unreaped status and all available partial captures are retained without retry. Failure-metadata faults do not replace the primary exception.

Regressions use tiny invented files, mocked oversized metadata and process controls; no huge allocation or real provider/model work. Per-read stability/preflight is not an exclusive filesystem lock across future engine reads. No old runtime/source/archive bytes are changed. Root owns final wheel/integration qualification.

Final changed source pins:

- `packages/tether/src/tether/_presentation.py`: `747c8467e5bb9019134e9949a0027eb4c96b8fdbe273010a2330d240320e070c`.
- `packages/tether/src/tether/_cli.py`: `fdd15b7067dcc71b1a0305eb8bdc6b93702ef33aea39eae9aad434495db49817`.
- `packages/tether/tests/test_frontdoor.py`: `9afccf04630ba80984d0b3c37e89f3fa5884a826aa258ecf532570578d2634be`.
- `packages/tether/README.md`: `56b743d3db7de70a01f74fd98e442d3e087e7479faca0ea831ab8d6ac6a8aba3`.

Evidence pins:

- `FRONTDOOR-TESTS-v1.txt`: `7e3076b5e68086efed4938d5b42e4000f11c4324cef45aceb68774b763639c67`.
- `FRONTDOOR-TESTS-v2.txt`: `dc04f4e5ead2e123698797562c65270fc2887cbc72bc2380e3de6e7d2bbc896d`.
- `FRONTDOOR-INDEPENDENT-PROBES-BEFORE-v4.txt`: `4087ce7f51671de6cf4fcc522ef1205b47ce3ff8a603d935e0f6dcb045852a15`.
- `FRONTDOOR-INDEPENDENT-PROBES-AFTER-v1.txt`: `d7d9bc948ba2761281c866bf3af306f88d67cdd30797a85c588926b3c93acb94`.
- `FRONTDOOR-IMPLEMENTATION-v1.json`: `1823d2e5d03a3481af22b23d617bb6f52cdb908443d9c5cd82d7181e8fdc4649`.
- `FRONTDOOR-IMPLEMENTATION-v1.md`: `dda352b0039d5a2c65ac1ecb295bb7edd2d72fff180156cea2ff99e58885429e`.

No separate reader-only test run occurred before the combined correction. No original/provider/protected/human reads, model/network calls, scientific rerun or legacy-core edits occurred.
