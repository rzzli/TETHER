# TETHER artifact-specific catalog policy

TETHER 0.6.0 retains an explicit artifact-policy path for `run`. The inventory
is [sources.json](../data/catalog/sources.json), schema1, with178 products and
historical collection observations. [policy-v2.json](../data/catalog/policy-v2.json)
binds its current bytes and dependency classifications. After the namespace
migration the policy has **zero artifacts and zero permitted uses**. New identities
need newly verified registrations; old grants are not inherited by relabeling.
Direct engine API calls do not acquire schema2 authorization merely by importing
the public namespace. Passing a projection alone is insufficient authorization.

## Historical policy and qualification (archived)

The following dated import describes the original checkpoint, not current grants.
Use [its original source and policy](ARCHIVE.md) for exact reconstruction. These
counts and qualification claims have not been transferred to the new namespace.

The policy indexes all 178 products but declares only **266 artifacts**: 248 raw files actually referenced by the ten canonical T6 snapshots, 11 normalized packets, and seven AACT archive identities. Ten contemporary uses are permitted for their exact cases, snapshots, cutoff and frame. Seven AACT uses remain blocked. Other artifacts and uses are denied.

The broader October 17 inspection covered 2,206 files/9,038,960,079 bytes. The policy's 248 raw files are the actual lineage subset, with 920 source-node occurrences across cases. These counts are not interchangeable. Packet bytes and 280 small metadata/receipt files were freshly checked during import; raw payload hashes in the import are inherited from retained receipts. A separate OSMR preparation-only check freshly checked **18 raw originals/442,815,104 bytes**, one packet and 18 receipts, with zero engine dispatches. That check does not freshly verify the other 230 raw files or create a new dossier.

`input_dependencies` describe scientific/normalization requirements, while `validation_dependencies` describe fixtures used to check a method. Neither is a substitute for the actual sealed parent graph. Genetics QC cases move to validation dependencies; LD stays conditional on the applicable method. Actual evaluator ancestors remain forbidden, even when optional or hidden beneath a generated product. Planned scorer training ancestry is retained and inference remains unsupported. AACT use is tied to the original protocol: its 2023 origin and subsequent follow-up/endpoint/ascertainment snapshots do not share an unrestricted provider-level role. July 2023 retains the actual **July 2** dump date; historical public availability remains unknown.

The migration preserves all product-level collection, parsing and scientific-status fields. No missing dataset is filled, no collection status is promoted, and no biological interpretation is validated by a policy grant.

## Explicit execution and verification

The policy path requires these arguments together:

```text
tether run --case <case.json> --snapshot <snapshot.json> --output <fresh-output>
  --catalog <original-schema1-catalog.json> --catalog-policy <policy-v2.json>
  --policy-use <exact-use-id> --policy-roots <roots.json>
  --policy-frame-sha256 <independently-selected-frame-hash>
```

Join the lines using the shell's normal continuation syntax. `roots.json` has `schema_version: 1` and a `roots` object containing absolute local roots. Its `metadata` root resolves the source catalog and explicit provenance reports; each use names its raw and snapshot aliases. The local imported mapping is at `data/derived/catalog-policy-v2-20261102T084949Z/roots.json`. It is not a portable substitute for the original case/snapshot location bindings. Moving those controls requires a newly reviewed use; changing a path does not preserve an exact fingerprint.

For this frame, the independently selected frame hash is the retained build report's SHA-256: `755f3ec861e3283ea6e04bd802fdc39d1e810cdf70556ac30718f796915f4115`. The imported policy SHA-256 is `80a8bf5b61b28298081ec16ae1758a4944f0d45ac0e4ea1181e8eb6faa71cd78`. Retain the policy and resulting outer receipt anchors independently. These examples describe the interface; the migration did not rerun the ten cases.

Before child dispatch, the wrapper validates every source node, packet and parent, including unused nodes; checks role, use, release, path, size, hash and temporal context; checks original catalog/provenance bytes; and copies controls, packets and computed mappings into a fresh outer directory. It preserves nested relative paths. The child receives the copied controls and a deterministic restricted schema-1 projection. Verification derives that projection again, checks its binding to the original schema-2 policy and actual engine inputs, and rechecks source-inclusive admission.

Raw originals stay external. The wrapper archives exact receipt copies under its output and compares them with the original pinned receipts before execution/finalization/verification. The frozen child still reads those original paths. Existing content-addressed receipt copies are preserved; no transport receipt is rewritten. Equivalent Windows and POSIX separators are normalized for relative-path comparison only. IDs, URLs and path case remain exact, and traversal/device paths are denied.

The additional verification result is `artifact_policy.status: artifact_policy_consistency_verified`; schema-1 compatibility runs report `unavailable_schema1_compatibility`. Schema-2 `run` currently supports offline extractive execution only. Model/replay/scorer controls, synthetic-demo policy bypasses and policy flags on unsupported commands are rejected. Source inspection/build commands keep their legacy interfaces; new generated packets need explicit registration before a schema-2 use can admit them. Record-level publication/eligibility checks still apply after artifact authorization, so an allowed artifact can contribute zero eligible records.

## Updating policy without mutating history

The current inventory-only policy was freshly generated and validated against
the current schema1 bytes. Registering real artifacts is a separate operation;
it must verify their actual dataset identifiers, parents, paths and hashes. The
dated importer described below belongs to the historical reproduction recipe.

`tools/data/build_tether_policy.py` imports this named metadata frame into a fresh workspace `data/derived/` directory, including content-addressed metadata copies, policy, local roots and an import report. It checks the supplied original-catalog SHA before migration. Failed attempts retain `failure.json`; prior attempts are never overwritten. Run the importer and independent metadata checks before replacing a live policy. `tools/validate.py` checks policy structure and the exact schema-1 anchor without assuming local original data is present in a clean checkout.

A future downloader must write immutable observation/attempt receipts and retain every receipt already used as an anchor. The legacy downloader is unchanged. The canonical receipt reconciler checks receipt ID, dataset, release, URL, normalized path, size and source hash; the older Python acquisition helper has weaker checks and must not be treated as this new policy's promotion authority.

The guarantees are local consistency and controlled admission. They do not prove publisher authenticity, undeclared real-world ancestry, scientific validity or process isolation. The [capability table](TETHER-VERIFICATION-SCOPE.md) retains the process/host limits and matching-version archive instructions. [Q02 assessment and evidence](<../planning/Project Progress Reassessment 2026-11-02 - Artifact Catalog Policy.md>) records the tested scope and remaining programme.
