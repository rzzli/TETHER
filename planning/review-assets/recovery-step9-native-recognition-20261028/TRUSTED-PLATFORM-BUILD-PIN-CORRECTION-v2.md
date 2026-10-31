# Retained build-preparation pin correction

The unprepared v1 builder transcribed the source checker pin as `e92dd42233ccfe2421e4072ddfbbee28b4c1749026da405b04d296ca76c335217` (65 characters), while frozen child proof955e and the actual checker agree on `e92dd42233ccfe2421e4072ddfbee28b4c1749026da405b04d296ca76c335217`. Its21-method pure suite retained18 passing tests,2 source-check errors and1 fake-compiler-boundary failure; no compiler callback was reached. The failed proof is `TRUSTED-PLATFORM-BUILD-PURE-CHECKS-v1.json` (SHA2565655ded8f89e2a84aebc2ce476866e789d518bb0415a752a2ae835c3fdfbd91b). V1 files remain unchanged and no v1 build protocol was prepared.

V2 uses the exact observed checker hash only after asserting equality to the independently retained child proof field. New filenames preserve the failed history. The same21 tests pass in proof3e000429, followed by successful metadata-only preparation of protocolc1475eb2. The C++source dbf76b19, contractfdd15d4f, vectorsb7e762b5, fingerprint807995f6, compiler commands, header and finalizer remain unchanged. Three historical v1 helper/checker/proof leaves are explicit provenance inputs; no binary/input-role scope was broadened.

No compiler, native bridge, CPU/provider or model execution occurred during either preparation sequence. Independent build-protocol review and a separate root decision remain required.
