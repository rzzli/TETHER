# Historical ancestor closure correction

The earlier verifier checked historical raw parents, receipts and projections, but
returned only aggregate status/counts. A caller could therefore retain a qualified
projection's pin without retaining the complete historical ancestor closure. This
was a concrete verification-interface gap; no production corruption was observed.

`tools.science.historical_inputs.verify_manifest(manifest_path, *,
audit_original_rows=False, expected_manifest_sha256=None)` now returns the existing
status/count fields plus `ancestor_pins`, `manifest_sha256`,
`manifest_final_sha256`, `available_by` and `availability_basis`. Each pin has an
absolute `path`, `sha256`, byte count and role. The complete actual closure is 1,619
files: one manifest, 805 original metadata/data files, 805 receipts, four projection
files and four schema files. Callers should check these retained pins immediately
before and after their own dependent operation. This is a bounded file-integrity
check, not an operating-system atomic snapshot.

The manifest is read once as bytes, optionally checked against the caller's expected
SHA-256, then parsed from those same UTF-8 bytes. Raw parents and receipts retain
their byte/hash checks; receipt JSON and the official release notice are parsed
from checked bytes. Projected JSONL bytes are hashed during their actual parsing.
All ancestor bytes and the manifest are rechecked before success is returned.
Availability is recomputed from the retained official notice and compared with the
manifest rather than trusting the manifest's date alone. Synthetic fixtures must
declare an explicit test-only availability source and fixture source URLs.

Thirteen focused tests pass using the standard library. They cover each ancestor
type, expected-manifest mismatch, a changed manifest after parsing, a changed raw
parent after its initial read, availability recomputation, clinical-column rejection
and complete closure pins. A test actively forbids importing pyarrow while running
the default verifier. Original-row decoding still requires pyarrow only when
`audit_original_rows=True`.

The unchanged production manifest
`e3c3b0ed80022f2f4cfb077387a6b5021b04fe51526b08a09d93e8d954303d54`
passed this full ancestor check in 2.281 seconds: 805 originals, 115,821 projected
rows and 1,619 pins. Its independently computed final SHA-256 matched its initial
SHA-256. Availability remains September 19, 2024 UTC under the retained official
release notice. The original full physical-row comparison remains the separate
previous qualification; this correction run did not decode original Parquet rows.

The new `historical-integrity-correction-validation.json` retains every actual pin
and the corrected code/test hashes. Collected data, old reports and old freeze
files remain unchanged. The prior freeze preserves the earlier code version;
this correction report records the new verifier version explicitly. No endpoint
clinical records, outcomes, provider calls, downloads or database operations were
performed for this correction.
