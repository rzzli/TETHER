# Independent reference batch: completed once

28 October 2026 UTC. The reviewed, 296-file-pinned reference batch completed
successfully with **one owned Python child**, exit zero and successful reaping.
The [sealed parent receipt](../../../data/cache/r09-jsonschema-reference-parent-20261028/receipt.json)
reports `passed_reference_batch_once`; no authoritative failure marker is present.
Helpers, original documents, expectations and the spent protocol remain unchanged.

- **162/162 typed schema expectations** matched across the unchanged 109 original
  and 58 extension documents.
- **16/16 separately frozen Unicode length controls** matched.
- The five previously declared parse-edge cases were observed separately and
  left ungraded (`matches_expected: null`). Python decoding plus jsonschema
  accepted three non-scalar surrogate strings and two duplicate-key documents.
  Duplicate keys retained their final value; no strict-parser policy was imposed
  on this independent schema result.
- The discrepant 1,802-code-point combining-sequence case was rejected at
  `maxLength: 1800`, matching its frozen typed expectation. The earlier
  PowerShell acceptance remains retained; this run does not establish its cause.

The isolated cached **jsonschema 4.26.0** tool and its qualified 139-file dependency
closure imported successfully, including the compatible rpds CPython extension.
This establishes return from these imports and metadata agreement in the tested
environment, not general ABI or platform certification. The default project
runtime dependencies remain unchanged.

The child recorded **0.265 seconds**. The parent recorded **1.954 seconds before
sealing**; root reported approximately **1.985 seconds including sealing**.
Stdout was 92 bytes, stderr empty; no timeout, capture overflow, cleanup error or
child guard attempt occurred. Peak memory was not measured.

The [summary](REFERENCE-BATCH-SUMMARY.json) retains basic raw artifact hashes,
including protocol `ded441d4a32d099d44fa240f75168cc581be1981ff73fcbd0e40acc043959aed`,
parent receipt `18764b64c8829d2905ab14d1605d6b34d16673d52e6bdb3f92c3bb79bca7fd5e`
and child result `1fa0be7bb260e95e200902311af3c0d18ae31014dd904609ba35ff7ca948e164`.

No PowerShell retry, strict-validator replay, llama target call, tokenizer,
vocabulary, model, inference or provider spending occurred. This closes the
bounded reference-tool batch only. Native grammar/EOG conformance, scientific
validation and human scientific reviews remain separate pending gates. The
complete strict post-validator remains necessary for the observed parser edges
and documented post-validation-only requirements.
