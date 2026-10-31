# Independent verification of the prepared v2 recognition pack

28 October 2026 UTC. **PASS for retained binary/source bindings. Native conformance remains unverified.** This AI engineering review did not import or rerun the preparer/oracle, execute the bridge, read a GGUF, or call a tokenizer, model, server or network service.

The actual prepared pack at [recognition.pack](D:/Projects/drug_target_agents/data/cache/r09-native-recognition-pack-v2-20261028T183647Z/recognition.pack) is259,867 bytes, SHA-256 `f75ab9937c57b5f03c2234643a8a9c91cda852ca0cca0de0478369f793e57e5f`. Its [preparation report](D:/Projects/drug_target_agents/data/cache/r09-native-recognition-pack-v2-20261028T183647Z/preparation-report.json) hash is `1ff800d4e2a01137eb47acb7d3d7051d64e35b71a0b0bca077f914acdaf60f7e`; the separately retained root decision hash is `562f85fabde6eaf1cf6bba6ac05535c8a3ac2c29acacdbcf4d86f5333ba2d69a`. The output directory contains exactly these two declared files and no failure record.

Detailed checks are retained in [PACK-V2-RESULT-VERIFICATION.json](D:/Projects/drug_target_agents/planning/review-assets/recovery-step9-native-recognition-20261028/PACK-V2-RESULT-VERIFICATION.json), SHA-256 `dae9dd3ea43398c02233f7353d9fa79e544a1543951bf9bb3735eadd3d7feba9`.

## Independent decode and comparisons

A fresh stdlib binary reader decoded `R09NC02\0`, version2, four grammars,189 cases and six prefixes to exact EOF. All ID, hash, length, group and index fields match the report and declared limits. All **113 input pins** still match the preparer's report and the independently reviewed frozen input universe; input path/ancestor checks found no symlink/reparse attribute. The former111 inputs remain identical; the two additions are precisely the old pack and its retained layer-review JSON.

The old pack still hashes to `0c28da7444c1837ac5099b5312b864a4d17cd9dafb5176c3452b2f229ae4e0f5`. Both decoders return identical four grammar byte strings, all189 document byte strings, all189 provenance records and all six prefix fields. The only structural case change is `primary/161.expected_kind:0→3`. Exactly **three byte positions** differ between the same-sized binary packs:

| Offset | v1 | v2 | Meaning |
|---:|---:|---:|---|
|6|49|50|ASCII format digit1→2|
|8|1|2|little-endian format version|
|253446|0|3|sole primary raw-NUL harness expectation|

Every primary wire was also compared directly against its unchanged original container string or extension file and full manifest provenance. The18 authored serializations reproduce their unchanged parsed response dictionaries through independent compact sorted-key UTF8 serialization; they are explicitly new serializations, with `historical_raw_wire=false`, abstention status, empty features and null clinical probability. Four independent byte guards retain their exact bytes and UTF8/NUL dispositions. Four fixed prefix slices and two unresolved natural-boundary selectors remain unchanged.

## Correct interpretation of counts

The original pure corpus remains **167 documents:44 members and123 nonmembers**. Prospective native byte-front candidates are **166:44 member expectations and122 nonmember expectations**. The remaining original document `primary/161` is a separate harness disposition: exact unchanged raw SHA-256 `8414c3ed0614d67fa5b8c152438a2f2eb71f534a7ba1a1658c386f642349b308`, sole NUL offset169, retained **pure=false**, expected harnesskind3 and **native expectation=null**. It is not a native negative result.

The189 packed cases comprise167 retained primary wires,18 new authored abstention serializations and four independent guards. The report still states `execution_authorized=false`; no probability or scientific conclusion follows from this pack. Pure comparator observations were retained and source-bound, not rerun by this reviewer. Actual tokenization may expose further piece-level ineligibility, so166 is a byte-front candidate count rather than observed native test completion. Two natural UTF8 prefix slots remain coverageunknown until actual tokenization. ABI, token-piece round trips, native membership/EOG, resource fit and scientific gates remain separate.
