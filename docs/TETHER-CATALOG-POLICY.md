# Artifact-specific catalog policy

[sources.json](../data/catalog/sources.json) is the schema-one product inventory.
[policy-v2.json](../data/catalog/policy-v2.json) binds its bytes and adds exact
artifact and use permissions. The shipped policy contains no artifact grants or
permitted uses. Product metadata alone does not authorize execution.

For a deployment, copy the requirements template to an ignored local catalog,
record its observations there and bind a separate local policy to its exact bytes.
Keep local grants, provenance reports and root maps out of the public tree. The
shipped policy remains bound to the blank public template; see
[catalog maintenance](MAINTENANCE.md#catalog-updates).

## Explicit execution

Supply all policy arguments together:

```text
tether run --case <case.json> --snapshot <snapshot.json> --output <fresh-output>
  --catalog <sources.json> --catalog-policy <policy-v2.json>
  --policy-use <use-id> --policy-roots <roots.json>
  --policy-frame-sha256 <independently-selected-frame-hash>
```

Join the lines with your shell's continuation syntax. The root map has
`schema_version: 1` and a `roots` object containing approved absolute local roots.
Its `metadata` root resolves catalog and provenance files. Use portable root
aliases in records; never publish credentials, signed URLs or private root maps.

Before dispatch, the wrapper checks every supplied packet and source ancestor,
including unused nodes: identity, role, use, release, path, size, hash and temporal
context must agree. It copies controls, packets and provenance into a fresh outer
run and derives the restricted schema-one view supplied to the engine.
Verification reconstructs that view and checks its original catalog binding.

Raw originals remain external. Receipt copies in the run are compared with their
pinned originals; original transport receipts are not rewritten. Relative-path
comparison normalizes equivalent separators only. IDs, URLs and path case remain
exact; traversal and device paths are rejected.

## Scope and results

The explicit policy path supports offline extractive `run` only. Model, replay and
scorer controls, demo bypasses and policy flags on unsupported commands are
rejected. New packets from ingestion need explicit registration before a use can
admit them. Publication and temporal filters still apply after authorization, so
an authorized artifact can contribute no eligible records.

A successful policy check reports
`artifact_policy.status: artifact_policy_consistency_verified`. Schema-one
compatibility execution reports `unavailable_schema1_compatibility` and has a
weaker catalog scope. Importing public module aliases does not add policy checks.

`input_dependencies` express input requirements; `validation_dependencies` identify
method-checking fixtures. Neither replaces the actual sealed ancestor graph.
Evaluator-only ancestry remains excluded even through generated or optional inputs.
Collection, parsing and scientific-validation statuses remain separate.

Use the implementations in [_catalog_policy.py](../packages/tether/src/tether/_catalog_policy.py)
and [_catalog_binding.py](../packages/tether/src/tether/_catalog_binding.py), plus
[policy tests](../packages/tether/tests/test_catalog_policy.py), for the exact
schema and admission contract. A changed catalog requires a newly bound policy;
changing labels or paths does not preserve an original proof.

These are local consistency and controlled-admission guarantees. They do not
prove scientific validity, source authenticity or process isolation. See
[verification limits](TETHER-VERIFICATION-SCOPE.md).
