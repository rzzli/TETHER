# Security and trust boundaries

The current development distribution is intended for trusted local research workflows. It is not an operating-system sandbox. Treat model text, source content, journals and unanchored receipts as untrusted input. Explicit source roots grant local reading scope; serialized paths never grant themselves permission.

Byte integrity, semantic consistency, source binding and scientific validation are distinct. See the [verification threat model](docs/TETHER-VERIFICATION-SCOPE.md). Hash-chain consistency without a separately retained anchor does not establish publisher authenticity or prevent complete-tree substitution.

For a suspected vulnerability, use GitHub's **Report a vulnerability** option if enabled on [this repository](https://github.com/rzzli/TETHER/security). Otherwise open an issue describing the affected component and requesting a private reporting channel; omit exploit payloads, private data, credentials and signed URLs. No guaranteed response time or independent security certification is claimed.

Supported development scope is recorded in the [platform table](docs/MAINTENANCE.md#platform-support). Frozen study drivers and old result environments are reproduction materials, not maintained security boundaries. Preserve them separately and do not expose them as services.
