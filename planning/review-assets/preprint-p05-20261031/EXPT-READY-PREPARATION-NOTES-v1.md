P05 metadata-only execution READY preparation, version 1

**Status: DRAFT_ROOT_AUTHORIZATION_PENDING. No native execution authority.**
The helper `tools/science/prepare_source_validation_ready.py` writes only the new
explicit `EXPERIMENT-READY-DRAFT-vN.json` asset leaf. The written flags are `frozen_by: NOT_ROOT` and
`actual_execution_authorized: false`. The helper cannot write the actual READY
file, overwrite an existing draft or execute a reporting cell.

The retained original v1 draft byte SHA is
`0d532b6977dea2b7180d94a1e1777506fcb6a60515a15cefec85c277b8df5f1d`.
The current v2 draft byte SHA is
`ac1b1d1d7a9752ba61002ccc22a579eb842f12f96c3462e990a04e2b64e3a71e`.
Each binds twelve fixed native units, 180 requested fact slots, forty answerable
native measurement components, 38 scheduled outputs and ninety decisions. Those
counts come from the root's value-free native bindings and independently built
public original-only register, not from reading candidate or reference values.
No actual native output was produced.

The frozen runner remains exactly
`9a63d63eacbfb71712376862d38d77f72dd4edf616521073ad287e53eb275bf8`.
Neither that runner, its tests/design, any core module nor an earlier protocol
was changed. The preparation helper is separate from its 71 runtime code pins.
The seven additional independent analyzer/auditor/helper/test pins retain the
runner's exact `EXTRA_CODE` inventory. Explicit final auditor/test hashes are
required as input, and analyzer/test hashes are also compared to the peer's
public preparation metadata. Existing Python/Windows/PyArrow environment metadata
is copied from the frozen environment contract; no dependency is installed.

Only six named public P05 metadata files, source-input seal metadata, explicitly
supplied wholly fictional fixture/qualification metadata, code and environment
are parsed. The helper checks the input/reference audits' value-free flags,
PASS statuses, empty issues/findings and exact subject bindings. Native task,
packet and per-reference hashes/counts come solely from
`EXPERIMENT-NATIVE-BINDINGS-v1.json`; packet hashes are cross-checked against
source-input seal artifact metadata. No generation packet is opened. The public
`REGISTER-MANIFEST-v1.json` supplies ordered native cases and original-derived
counts/exposure/dependence limits; the private register is not needed.

The actual native `references.json` is opened solely as an opaque byte stream
for SHA-256 and length under a stable file lock. Its bytes are never decoded,
JSON-parsed, copied into the draft, returned to generation or exposed as source
values. The independently supplied canonical wrapper fingerprint remains
`f29444743dfa2acc9cb0a555d5f39ce866a5da04ec919280cb17afe2f82ab13a`;
it is intentionally separate from that file's byte SHA. The reference seal's byte
pin comes from public P05c acceptance metadata, without parsing the private seal
or reference facts. No original biological source values, human material,
protected clinical originals or old answers are read.

The explicit persistent invented-data inputs were:

* Fixture manifest:
  `data/cache/preprint-p05-fixtures-20261101T090035Z/manifest.json`, byte SHA
  `b6a43312e68cb26951124ab8a30507d47cb4c00e5b7f6f57be725f2fb1360040`.
* Fictional qualification ledger:
  `data/cache/preprint-p05-fictional-qualification-20261101T090042Z/ledger.json`,
  byte SHA `fadf013f8fdb2f196c191561b1bafe96ef542f95b07a8deae05dd94f781ce7f7`.
* Auditor pins used for retained v1:
  `ce7d749386b937e2210476f7720bbd23f7f79ef2595d2e61070f4249edead324`;
  auditor tests:
  `6cc92f647d6d6cddc272583c7face931455314f3b3a2a46c9c38443215966e5c`.

The fictional ledger must be PASS, qualification-only, have zero native outputs,
all native slots unexecuted, the 14-scenario reference/count map, exact frozen
runner and fixture-manifest bindings, and no lifecycle failure seal. Its real
invented-data success seal and hash-chained journal are checked. No fictional
candidate is generated or rerun by this helper; the existing qualification is
consumed as metadata.

Descriptor `expected_fields` use the precise frozen runtime schema: input audit
binds the source-input seal byte SHA and run; reference audit binds canonical
manifest fingerprint, retained reference READY and run; peer binds reviewed runner
SHA; fictional qualification binds reviewed runner, fixture manifest, zero native
outputs, qualification-only and scenario count. The nine input descriptor keys,
native case/count map, fictional reference/count map, runtime schedule and exact
71+7 code maps are preserved. `runner.schedule()` supplies the runtime arm/stratum
representation instead of copying the differently labeled design schedule.

A pure in-memory proposal uses the shape required by `validate_freeze` and is
checked only with that metadata validator. It is never written or executed. The
serialized draft then replaces all three authorization flags and is independently
checked to fail specifically at `Separate root READY required`. Pure checks also
verify deep-copy independence and the absence of a native execution entry point.
The one preparation invocation completed successfully and printed a small
metadata-only summary, with zero reference facts parsed, native packets opened
or original values read. No actual READY file or source/reference output was
created. Code-only review found no authority/data-read blocker; its two suggested
metadata cross-checks were added before preparation.

After v1 preparation, root found a metadata-shape bug in the independent auditor:
it iterated the native qualification dict as a list. No actual experiment or
audit had run. Root corrected the auditor and added a regression, changing
only two extra-code hashes. The original non-authorizing v1 draft is retained
unchanged with its then-current auditor/test pins; it is superseded for future
authorization. The helper accepts an explicit new versioned DRAFT filename,
while rejecting overwrite and any actual READY filename. Frozen runner, 71 main-code pins,
persistent fictional sources and their qualification are unchanged.

Root supplied the corrected auditor SHA
`aae8db1bf4bc2da1d14836a18cfb8d4273815f8659c7ea9064f2ea620371fe0f`
and test SHA
`001f6168f3f603940c3ec7df1c7725d1eae362b172b8f7c44e57b34d1377b2d1`.
Root reported reproduction of the old TypeError and a 25-test pass after the
strict twelve-key mapping correction; its separate correction report is
`AUDITOR-MAPPING-CORRECTION-v1.json`, byte SHA
`bbcb8b2f347d1de4d9c30b1ad483103ac7f66ac10fee66e2a7cda8ca529343f2`.
The helper then created v2 with those explicit pins. Both drafts are retained,
both have NOT_ROOT/false authorization, and neither executes a native cell.

One read-only post-handoff QA assertion that the actual READY file was absent
failed after root independently created that file in parallel. This was a
time-dependent assumption, not a helper write or an authorization-gate failure.
Root confirmed its separate reviewed actual READY byte SHA as
`49c2ce672356bfcfd572a7b6c963c56bd5c96e3d042a9972f2c36434ebb8de3f`;
no actual study had run at that confirmation. Final helper QA instead checks the
stable invariants: both drafts remain non-authorizing, v1 is unchanged, v2 differs
only in corrected two extra-code pins plus helper provenance, the RAM proposal
matches the metadata schema, and the written draft fails the root gate. Those
checks pass. Actual authorization origin is root, never this helper.

Root review, final authorization flags in a separate actual READY, an external
exact READY byte SHA and final validation/commit are separate owner-controlled
steps. At preparation time, source-inclusive native verification and all 38/90
experiment work remained future execution. This draft does not establish freshness, study independence,
biological validity, clinical truth or preprint completion. Network calls,
downloads, model calls and provider spending remain zero; platform cost remains
unmeasured.
