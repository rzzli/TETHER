# Cached reference-engine qualification and prospective batch

**Current status after the root decision at 2026-10-28 05:51:51 UTC:** the reviewed
assembly-only step completed. The new isolated reference environment contains
all 139 files / 1,640,116 bytes. Its
[environment receipt](../../../data/cache/r09-jsonschema-reference-environment-20261028/ENVIRONMENT-RECEIPT.json)
is SHA-256 `57d07af03d355f04109900684c2ffdb6ab9b818bf4a1e1d7f7cb8b0729fa7239`
and says `offline_reference_environment_materialized_not_import_qualified`, with
zero package imports. The [root decision](REFERENCE-ASSEMBLY-ROOT-DECISION.json)
authorized no engine batch or package import. Protocol preparation and the batch
remain unattempted at this update. The preparation-only statements below preserve
the **pre-assembly source-qualification snapshot**, rather than implying that the
new environment is still absent. No helper or original qualification bytes changed.

28 October 2026 UTC. **Read-only closure verification passed. Execution is not
authorized by this document.** No package was imported, installed or copied; no
environment was created and no reference-schema case ran. The only executed
helper used standard-library filesystem, metadata and hash operations.

## Qualified bytes and remaining runtime qualification

The corrected uv cache contains a complete candidate tool dependency closure:

| Distribution | Selected version | Requires Python | Wheel tag | Selected files / bytes |
|---|---|---|---|---|
| jsonschema | 4.26.0 | >=3.10 | py3-none-any | 43 / 476,081 |
| referencing | 0.37.0 | >=3.10 | py3-none-any | 19 / 115,368 |
| jsonschema-specifications | 2025.9.1 | >=3.9 | py3-none-any | 28 / 47,261 |
| attrs | 26.1.0 | >=3.9 | py3-none-any | 35 / 233,691 |
| rpds-py | 2026.6.3 | >=3.11 | cp311-cp311-win_amd64 | 9 / 589,582 |
| typing-extensions | 4.15.0 | >=3.9 | py3-none-any | 5 / 178,133 |

The selected **139 files total 1,640,116 bytes (1.56 MiB)**. Exact cache roots,
METADATA requirements, WHEEL/RECORD hashes and every selected file hash/size are
retained in [CACHED-REFERENCE-QUALIFICATION.json](CACHED-REFERENCE-QUALIFICATION.json),
SHA-256 `401047cbf5b240867192a0d8acc1324b98ecb68837b6f4fca8f6b87dcb513ea4`.
All non-self RECORD entries were SHA-256/size verified; RECORD itself is separately
pinned by this external qualification artifact. Four duplicate cache pairs have
identical non-PYC manifests. No `.pth`, reparse point, unrecorded non-PYC file or
digest mismatch was found. PYC files are excluded from the future copy.
The historical qualification field `selected[].wheel_sha256` means the hash of
the unpacked distribution's **WHEEL metadata file**, not a downloaded `.whl`
archive. No complete reference-package wheel archive or publisher signature is
claimed. The original qualification field/report is preserved unchanged.

The declared dependency ranges close at these versions. `referencing` requires
typing-extensions >=4.4 on Python <3.13, so it is included for the selected
CPython 3.11.15 x64 host. Optional jsonschema format extras are excluded; the
current schemas contain no `format` keyword. Cached rpds-py 2026.5.1 is **excluded**
because its `cp314-cp314-win_amd64` wheel is incompatible with CPython 3.11.

The selected `rpds/rpds.cp311-win_amd64.pyd` is 560,128 bytes, SHA-256
`3fbd6d9aa1ce4669506a91c4321bb751895dfa4e78efb6ed1151cea8c51b238f`.
Its tag matches the host; actual import/ABI behavior is **unattempted**. The future
validation tool will load this Rust/Python dependency. That must be distinguished
from zero llama/native-target, vocabulary, tokenizer, model or inference calls.
RECORD agreement establishes integrity against cached metadata, not signed
publisher-origin attestation. No new download is needed for this candidate route.

## Primary implementation inspection

Cached `jsonschema/_keywords.py:231`–240 implements both length bounds with
`len(instance)`. Its SHA-256 is
`afcfc3aea01f9fa40bc109e65c4820bde89253e51a20bda9da7b8f20d7a57c57`.
The combining sequence in the discrepant case has 1,802 Python code points;
source inspection predicts rejection at maxLength 1,800. This is not an observed
reference-engine result. The pattern implementation uses `re.search` (215–220),
preserving the existing unanchored nonblank search; no schema pattern is repaired.

`jsonschema/validators.py:812`–857 maps all **14 enforcing keywords** used by both
complete variant schemas: additionalProperties, anyOf, const, enum, items,
maxItems, maxLength, minItems, minLength, pattern, properties, required, type and
uniqueItems. `$comment` is an annotation. Neither schema contains `$ref` or
`$dynamicRef`. This source has SHA-256
`97f171b995b4b0ca05530a9366a1252fb1753f99f3cb7b1068b6d9aab1096fa5`.
Its default registry can call `urlopen` (108–133); the future batch must supply an
explicit deny-retrieve `Registry` and an outer no-network audit guard. Meta-schema
checks must use that registry and the copied bundled specifications as well.

## Prospective environment assembly, not yet run

[prepare_cached_reference_environment.py](prepare_cached_reference_environment.py),
SHA-256 `8a5baeb9e3bf2c5e6b954d9a58ea1e46f52d4b98d567e165c85ccaf5419982a1`,
is prepared for owner review. Its fixed output is a new ignored directory:
`D:\Projects\drug_target_agents\data\cache\r09-jsonschema-reference-environment-20261028`.

Run only after review with the existing project CPython executable and `-I`.
It creates a standard-library venv with `with_pip=False`, no system site packages
and no symlinks; it neither invokes pip/ensurepip nor imports copied packages.
It copies only the 139 pinned files, rechecking source bytes and destination hashes,
preserves licenses/metadata, refuses existing output and retains a failure receipt.
The project `.venv`, previous wheel environments and C: caches remain untouched.
Its environment receipt pins the new launcher and configuration. Freeze that
receipt's SHA-256 externally before authorizing the batch; do not infer it from
an unanchored child response.

## Prospective once-only reference batch, not yet run

[run_cached_reference_batch.py](run_cached_reference_batch.py) is a prepared child,
SHA-256 `accaf9e906a579bf3698a5e5273645c34f25497481030539b542d0358ea61850`,
not execution authority. The owner must first pin its final helper hash and the
materialized environment receipt. Exact child argv is:

```text
D:\Projects\drug_target_agents\data\cache\r09-jsonschema-reference-environment-20261028\environment\Scripts\python.exe
-I -B
D:\Projects\drug_target_agents\planning\review-assets\recovery-step9-generation-contract-20261028\run_cached_reference_batch.py
<externally frozen ENVIRONMENT-RECEIPT.json SHA256>
```

The prospective parent must reserve a fresh attempt/capture directory, record
helper/protocol/environment hashes and exact argv/cwd, and use fixed argv with
`shell=False`, `CREATE_NO_WINDOW` and an outer **120-second** timeout. The child's
own **100-second** deadline is additional protection. Retain stdout/stderr as
exclusive files (caps: 1 MiB each), PID, exit/timeout, elapsed time and cleanup
status; on timeout/interruption kill/reap only its owned child and retain an
authoritative failure marker. Never repeat a consumed attempt automatically.
The parent capture/sealing implementation and effective configuration must be
frozen before dispatch; a direct unbounded helper launch is not this protocol.

The concrete prepared outer helper is
[run_reference_batch_once.py](run_reference_batch_once.py). It uses only the
accepted installed **0.3.10** `RunJournal`/`stable_files` primitives and pins that
accepted runtime separately from the new reference environment. Its `--prepare`
mode, run only **after** the reviewed copy step, hashes the complete installed
closure and corpus inputs and writes a fresh data-only
`REFERENCE-BATCH-EXECUTION-PROTOCOL.json`. Preparation spawns no child and imports
no reference engine. The owner reviews that new protocol/hash before separately
running `--execute <expected protocol SHA256>` in the same old installed Python.
Execution reserves the fixed fresh parent output, holds read leases across fresh
hashing and the single child, uses an owned stdin pipe closed to EOF (no NUL
exception), drains capped stdout/stderr, and persists fsynced hash-chained events,
attempt/configuration/receipt artifacts and authoritative failures. Its child
process cap is 110 seconds inside the 120-second aggregate parent budget; the
child's own deadline is 100 seconds. No existing output is reused or restarted.
Finalization checks deadlines per inventory file and after writing the receipt;
`failure.json` overrides any earlier success record or receipt.

The child reserves its fixed fresh batch output before imports. It verifies the
139 installed files, all six distribution versions and installed module location,
then validates complete schemas through Draft202012Validator with deny retrieval.
It imports no AsOf/project code and blocks network, child dispatch, target DLL
loading, E: access, benchmark payloads and writes outside its new output.

Inputs are the unchanged **109 original +58 extension** documents, their original
serialized bytes, both original full schemas and frozen authored expectations.
Read-only preflight confirmed that all 109 embedded original schema byte strings
have the same pinned base hash `a75dd967b16fd387da820e0bd90071aba511aee5363f700e9ac5849f8cc72911`;
no schema case was evaluated during that hash check.
The input anchors are:

- Original cases: `01286d35689c7005ea67fa817c4b4098cecd05c4233c3949e7ec744bc5f5d97a`.
- Frozen inputs: `1b80e365e42b28fe237c22fc35e215d1a0410729203a77255fc628309a9da414`.
- Existing future-corpus reference: `43aa4b18d3d9c7393198d0eaa93095999d1ef54f0d2757ffe6265c7d95a26e4a`.
- Existing comparison/labels: `95c2c30fa8ef69dca5122e22ce32fe3b636e812d3a8f8f05c685b366e323316a`.

Their use here grants no native authorization. Grade the **162 typed schema
expectations**; record the **five explicitly implementation-dependent parse cases**
separately, including decoder errors, duplicate keys and non-scalar strings.
Do not import the strict post-validator's parse policy as schema gold. Preserve
Python JSON's independently observed behavior without normalizing or rewriting
documents. Add the child helper's **16 separately named Unicode min/max controls**:
ASCII, astral, precomposed, combining and mixed strings at the specified bounds.
The helper bytes freeze their exact recipes and expectations before execution.

Recheck package/input pins after the batch. Preserve per-case outcomes and all
differences from authored expectations; mismatch, import failure, guard failure or
timeout closes the attempt. Even a future pass qualifies only this schema tool
and these cases. The closed PowerShell result is retained, never rerun or relabeled.
Native grammar/EOG, model performance, scientific validity and human reviews remain
separate pending gates.
