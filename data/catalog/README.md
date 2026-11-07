# Data catalog

[sources.json](sources.json) is a reusable requirements template for 83 providers
and 178 data products. It records access terms, release policies, required fields,
roles and dependencies. Its deployment state starts at `planned`, `not_checked`
and `not_run`; it contains no local acquisition histories or ready-to-use data.
These initial states do not rewrite the status of any historical collection.

[policy-v2.json](policy-v2.json) binds the exact inventory bytes and supports
artifact-specific grants and permitted uses. The shipped policy is inventory-only:
it contains no artifact grants or permitted uses. Registering a product name is
not permission to admit a particular file.

New artifacts need exact identities, hashes, parents, roles, releases and use
bindings. Historical originals retain their original identifiers and receipts;
relabeling them does not create new grants or preserve a semantic proof.
Record new observations in an explicitly versioned local catalog. Collection,
parsing and verification alone do not establish scientific validity.
Copy the template into an ignored deployment path before recording acquisitions;
bind a separate local policy to that catalog. Shared requirements may be updated
in the public template, but local results, artifacts and grants must remain local.

See [policy usage](../../docs/TETHER-CATALOG-POLICY.md),
[catalog maintenance](../../docs/MAINTENANCE.md#catalog-updates) and the
[data layout](../README.md). Bulk data and private root maps are excluded from the
public repository.
