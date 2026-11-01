# Proposed release rights dispositions

Status: DRAFT; official-source review completed 2026-11-01, owner/release approval separate. This is not legal certification or a claim that an archive has been published. The cards support a future explicit file allowlist; their presence does not authorize a recursive repository/data export.

| Asset class | Rights evidence | Draft package disposition | Remaining boundary |
| --- | --- | --- | --- |
| Project-authored code | Root Apache-2.0 licence | Include explicitly allowlisted source with licence/notices | Contributor facts and third-party dependencies not certified |
| OT25.09 GWAS evidence, credible sets, target and disease originals | Platform CC0 statement plus owner/upstream terms | External originals; reviewed URL/size/SHA-256 manifests | No complete release-specific upstream rights map or fresh exact-byte availability test |
| HGNC retained complete-set TSV | Official HGNC CC0 | External exact original plus manifest; later explicit CC0 payload inclusion possible | Local acquisition designation is not a provider archive release |
| Native row extracts, packets, reference facts and raw report payloads | Source-derived; not project-code licensed merely by serialization | Exclude by default; separately classify every proposed file | A hash-only descriptor must contain no row values or accidental private paths |
| Aggregated P05 results, captions and figures | Project-generated presentation, checked against retained results | Candidate allowlist after payload/attribution review | No raw-data or scientific-validity clearance inferred |
| Fictional controls | Project-authored invented data, distinct stratum | Candidate allowlist with truth/protocol labels | Does not substitute for native-source reconstruction |
| Qwen GGUF weights, model caches and runtime binaries | Repository metadata Apache-2.0; exact historical LICENSE retrieval gap | Exclude; metadata model card only | Model/runtime/training-data rights are separate |
| Final manuscript PDF | Observed Arial regular/bold subsets; embedding flags 8 | Candidate document inclusion, subject to lawful local use | No Windows font files or extracted font programs |
| Font files and installed dependency packages | Separate vendor/package rights | Exclude unless individually reviewed | Do not bundle the local environment wholesale |
| Credentials, protected clinical originals, bespoke human responses and descendants, outcome-aware archives | Outside this release's authorized scope | Exclude | Do not copy into public manifests or review fixtures |

The native input requirement is **137 complete originals, 2,866,248,239 bytes**, comprising 136 Open Targets Parquet files and one HGNC TSV. Full P05 verification depends on those exact sources and the frozen manifests. A package containing code plus fictional tests can demonstrate code behavior; it must be labelled as such and must not claim an independently reconstructed native study or a successful actual-format full-source replay.

Recommended public reconstruction metadata includes provider, product, version, exact source URL, portable logical path, format, original byte count, SHA-256, checksum origin, acquisition designation, licence/citation URLs and access/review dates. Remove machine-specific roots, credentials, human-response ancestry and source values from public metadata. A locally computed SHA-256 establishes byte identity, not publisher authentication, licence permission or biological truth.

Exact originals remain external by default even where the official licence permits reuse. This avoids turning an incomplete inventory/rights review into implicit payload distribution. If a provider no longer serves a matching object, fail closed on exact replay and report the access limitation. Do not silently replace 25.09 with a newer release, replace the HGNC snapshot with its current endpoint, or turn a 24-row extract into a claim about all original-file hashes.

Read the companion Open Targets, HGNC, model and code/font cards for the primary-source links, version limits and per-asset evidence. Review provenance, including unavailable pages, is retained in `planning/review-assets/preprint-p09-20261101/RIGHTS-SOURCE-AUDIT-v1.md`.
