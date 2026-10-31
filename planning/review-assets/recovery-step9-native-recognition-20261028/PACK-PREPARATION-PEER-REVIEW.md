# Independent static review of finite pack preparation

28 October 2026. **Clear for the separately authorized own-code pure preparation scope at the exact hash below. No native execution is authorized or qualified.** No remaining material format/input-shape blocker was found after the root corrections. This is source/metadata inspection only: the reviewer did not import or execute the helper/oracle, compile the bridge, fetch anything, load a DLL, read a GGUF, call a tokenizer/model/server, or open biological label/outcome/human files. Retained engineering metadata and one synthetic preparation/fixture wrapper were inspected for field names/bindings; no scientific conclusion was drawn.

The review leaves the frozen bridge and design unchanged:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `prepare_recognition_pack.py` in this directory |14,014| `2f760a22b1568084c18c4d8ffa61a6f751a3550c1d2ebf5d04eb1fb7748356c6` |
| `typed_public_c_recognizer.cpp` in this directory |47,485| `3f7e13ec7695bd5257e3e58d627ae71c1a2cdcaea7dbec8aad869424a0f5188b` |
| `BRIDGE-DRAFT-DESIGN.md` in this directory |19,551| `2bb222d6830a52513fab88c1db29b0d5b7cc093d5357ff224f3d3a42b2f8431b` |
| `planning/review-assets/recovery-step9-generation-contract-20261028/finite_gbnf_oracle.py` |4,040| `f59671fc66f55425e36d81e779501f9902b180248674688360d5a7fe5b68fa7d` |
| `data/cache/r09-generation-corpus-extension-v1-20261028/FROZEN-INPUTS.json` |17,120| `1b80e365e42b28fe237c22fc35e215d1a0410729203a77255fc628309a9da414` |

Paths other than this-directory names are relative to `D:/Projects/drug_target_agents`. Each hash above was rechecked locally after corrections. All line references below are one-based in the reviewed helper unless another file is named.

## Material findings and corrections retained

The root preserved the previous draft as `prepare_recognition_pack_pre_review.py`; its prior supplied hash was `08deb16e3a942f39d5ade71321dd330620e870aa61b00317124875d8c9637a49`. No failed helper execution is claimed: these were defects found before execution.

1. **Wrong oracle pin lookup.** The accepted receipt has an `evidence_files` dictionary, but that dictionary has no `finite_gbnf_oracle.py` entry. The earlier lookup would raise `KeyError`. The actual frozen authority is `FROZEN-INPUTS.json["source_pins"][exact_relative_oracle_path]`, whose value is directly the hash string above. The corrected helper verifies the exact frozen input inventory, retrieves that string, and hashes the oracle before loading it (163–167). No invented accepted-receipt entry is used.
2. **Two non-ASCII original case IDs.** The original manifest has two legacy IDs outside printable ASCII (document hashes `8dd74521428609df2f89a69578761db43cc0d92444962a91546fac16ca493292` and `0f6552eee00df8a19753ac024e24e8540a894fa9a4886cc50aceb616da496382`). Passing the original IDs to `.encode("ascii")` would fail, while relaxing the frozen bridge ID contract would change the format. The corrected helper assigns stable transport IDs `primary/000` through `primary/166`, retaining every exact original manifest entry/ID in provenance (111–118). Prefix lookup uses original provenance IDs (181–184). Documents and original corpus IDs remain unchanged.
3. **Windows receipt separators.** The receipt has38 output metadata entries with Windows-backslash keys. The root's earlier correction normalizes them through `Path(key).as_posix()`, checks that normalization did not collapse duplicates, then looks up the exact relative preparation/fixture path (122–135). This matches the actual retained receipt shape; it is not a list of output records.
4. **Explicit18-fixture bindings.** Receipt-file hashes/bytes are verified first. The corrected helper additionally verifies the report's logical canonical fixture hash, preparation request/payload identities, five shared fixture/preparation fingerprints, and exact grammar hash/byte count against both wrapper and report (137–148). The logical report fingerprint is distinct from the newline-bearing wrapper file hash; comparing the file bytes directly to that logical fingerprint would be wrong. The helper uses the correct separate checks.

## Format comparison with the frozen bridge

The encoder at208–228 matches `parse_pack` in the frozen C++ source:

- Eight-byte magic `R09NC01\0`, followed by little-endian u32 version1, grammar count, case count and prefix count.
- Each grammar is an ASCII length-prefixed ID,32 raw SHA-256 bytes, then u32-length-prefixed exact grammar bytes.
- Each case is an ASCII length-prefixed ID, then **source_group, grammar_index, expected_kind** in that order,32 raw digest bytes, and u32-length-prefixed document bytes. The source_group field is present; it is not the earlier format without group provenance.
- Each prefix is an ASCII length-prefixed ID, then base_case_index, kind and cut, followed by32 raw digest bytes. The four byte-prefix views receive frozen hashes; the two natural-token selectors use reserved zero cut/hash pending actual tokenization.
- The u32 writer rejects non-integer/out-of-range values. Grammar/document caps are65,536 bytes, total pack20MiB, cases189 (within200), grammars at most20, and the pinned proposal supplies six prefix slots. The C++ consumer independently rechecks record counts, caps, hash fields, indices, categories, IDs and trailing bytes.

No document/grammar path or executable reference is serialized into the binary pack. The parent sidecar retains exact input identities/provenance; the later native consumer is bound to the whole pack path/bytes/hash by its separately generated pin header.

## Document groups and controls

**167 primary frozen wires:** the helper verifies the original109 container hash, reads its original `document_json` string and encodes that string as UTF8, or reads the exact extension document bytes. Every document must match the manifest byte count and hash (108–118); there is no document JSON parse/serialization, normalization, trimming, escape rewrite or repair. The manifest order and observed pure44/123 split are retained. The original-ID provenance prevents opaque transport names from becoming revised corpus identities. Legacy generation membership remains observed replay provenance, not retroactively authored gold.

**18 new authored serializations:** the helper reads exact receipt-bound wrappers and serializes the unchanged parsed abstention `response` dictionary with accepted `asof.serde.canonical` (150–154). These are explicitly `new_serialization_of_retained_authored_abstention`, `historical_raw_wire=false`; they are not recovered wire bytes or generated scientific answers. Each uses its own preparation grammar. The helper requires authored abstention, empty features and `clinical_probability is None` (143–144), and the pure membership check must accept all18 before packing. No such serialization is applied to the original167.

**Four byte guards:** exact hex/length/hash come from the pinned proposal (155–158). Two are UTF8 rejections and two raw-NUL rejections; these have source_group2 and expected_kind2/3. They are independent harness controls, not native document rejection. The frozen bridge checks these declared guard shapes before backend/model initialization and performs no tokenizer/grammar calls on their bytes.

**Six prefixes:** original-ID lookup binds each base to an already declared member. Empty/final-close/escape-backslash/high-surrogate byte cuts are derived from the unchanged positive base bytes, required valid UTF8/no-NUL, checked non-complete by the pure oracle and hashed (181–206). Proper prefixes of these independently accepted whole strings retain their original bytes; no document is repaired. The two natural multibyte token-boundary selectors remain `coverage="unknown"`, with the frozen first-occurrence rule. No token boundary or EOG result is invented by preparation.

The five schema parser-edge documents remain primary native controls. ASCII lone-surrogate JSON escapes and duplicate keys are not removed by a byte UTF8 precheck. Two post-only duplicate-claim-text grammar members and seven strict-valid serialization exclusions remain part of the original167, with native and strict layers distinct.

## Own pure oracle and remaining boundaries

The helper preloads the accepted installed `interpretation_grammar` module at18 and checks its installed-environment origin before preparation (59–60). The exact frozen oracle defines `parse(grammar)` and `accepts(rules, name, document)`; calls at175–179 and203 match those signatures. The oracle is trusted **own-source** pure comparator code, not fetched upstream implementation, target DLL code or a model. Its source hash is verified through the frozen authority immediately before `exec_module` (163–172). The saved `sys.path` is restored in `finally` (170–174), and the oracle's import of the already preloaded grammar module uses the cached accepted module rather than importing a new repository copy after its source-path insertion. The caller still owns the accepted interpreter/environment provenance; this review does not requalify that environment.

The pure oracle is executed only when the parent separately permits this helper to run; this reviewer did not execute it. It can validate prospective pure expectations and new serialized inputs, not actual native grammar, token pieces, EOG, ABI, loader/CPU behavior, full-vocabulary masking, case-time fit or scientific validity. The helper's60-second read-time checks and bounded files are not a hard process deadline or memory proof. Parent process/capture controls and terminal failure review remain separate.

Outputs are exclusive-create own cache artifacts, with original inputs never written. `recognition.pack` is written only after all pure comparisons/prefix checks and finite limits pass; `preparation-report.json` is retained on ordinary success/failure with `execution_authorized=false` (229–242). A Python crash/kill/write failure can still prevent that final report; the external owner must retain and disposition such failures. Exit success or a prepared pack does not enable native recognition. Native execution remains disabled until its separately reviewed ABI/header/loader/resource/pin protocol permits it.
