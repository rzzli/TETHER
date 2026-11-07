# TETHER data catalog

[sources.json](sources.json) inventories 178 data products. Its collection and
parsing observations describe retained acquisitions; they do not establish
scientific validity or qualify a new engine release.

[policy-v2.json](policy-v2.json) binds the current inventory by hash. Following
the namespace migration it intentionally has **zero artifact grants and zero
permitted uses**. A renamed product ID does not authorize an old packet under a
new identity. New execution needs explicitly registered artifacts and lineage.

The original policy, its 266 artifact identities and 17 use records remain in
the [historical checkpoint](https://github.com/rzzli/TETHER/tree/tether-pre-namespace-migration-20261106/data/catalog).
Original local receipts and data have not been rewritten. Genuine temporal
field names remain unchanged.

See [policy usage](../../docs/TETHER-CATALOG-POLICY.md) and
[archive reproduction](../../docs/ARCHIVE.md).
