# SciFact G1/G2 preparation checkpoint

The bounded source preparation and grouped split are implemented and qualified.
This does not qualify a trained solver, native scoring, the new TETHER task policy,
or BG03 as a whole. No candidate has been generated and no model has been fitted.

Current output: `data/benchmark/scifact/preparation-20261105-attempt03`.
Manifest SHA-256:
`cb32f1384c49b66b912a62120abd7137a8a19b303f3ad052f035f21779c131f8`.
The [qualification record](QUALIFICATION-20261105.json) pins current code, tests,
logs, the retained failures and measured counts. It passes **23 projection tests**
and **nine split tests**, with a source-inclusive reconstruction of all 12 products.
Earlier overlapping test runs are not additional independent tests.

## Actual source and partition counts

The official archive contains 5,183 corpus records, 809 training claims, 300 public
development claims and 300 unlabelled test claims. The default evaluation schedule
retains all 300 development claims. Test claims were schema-checked but are not
included in any answering or evaluation product.

Source/evidence-document and exact normalized claim-text components connect
training and development records. Quarantining connected training records removes
278 claims from fitting, tuning and calibration. The remaining 531 claims form
the deterministic source-disjoint derivative below. Assignment uses seeded group
hash order and floor boundaries at 70%/85% of groups, never splits a component,
and does not promise equal claim-size ratios.

| Partition | Claims | SUPPORT pairs | CONTRADICT pairs | NEI pairs |
|---|---:|---:|---:|---:|
| Fit | 380 | 169 | 82 | 176 |
| Tune | 82 | 44 | 14 | 41 |
| Calibration | 69 | 28 | 15 | 31 |

Every required pair class is available; no declared class-feasibility issue was
found. NEI pairs are restricted to a claim's cited documents with no annotated
evidence, as described in pinned SciFact `doc/data.md`. They are benchmark-relative
negatives. Unannotated arbitrary corpus documents remain unlabeled.

## Product and consumer boundary

`views/corpus.jsonl` contains exactly `doc_id`, `title`, and ordered `abstract`.
`views/queries_{fit,tune,calibration,dev}.jsonl` contains exactly `id` and `claim`.
Reference products, fit pairs, grouping records and detailed source locators remain
under `restricted/`, with explicit consumer-purpose grants. The original mixed
tarball remains a preparation container; extraction does not fabricate a new
download receipt or make held-out answers generally admissible.

The full preparation manifest contains aggregate reference-label counts for trusted
operator feasibility review. It is **not a predictor input**. The native runner must
issue a separate sanitized consumer recipe containing only approved paths, byte
identities and configuration. Neither that recipe nor the predictor receives the
full manifest, source bindings, grouping records, reference counts or held-out
answers. This relies on qualified preparation/consumer code and audited opens;
directories alone are not an operating-system sandbox.

Public corpus and dev-query projection bytes are invariant when reference labels or
citation hints are changed in fictional tests. Corpus/claim text changes alter the
appropriate views. Original row hashes, field hashes, member identities and one-based
row locators bind projected values back to archived bytes.

## APIs and failure preservation

- `load_archive(path, expected_sha256, expected_bytes=None)` returns immutable
  corpus, native claim records, member/row proofs and explicit diagnostics.
- `prepare_release(acquisition_record, output)` reserves a fresh output, writes
  hash-chained build stages/products, and leaves a terminal failure/interruption
  record if work fails. Existing outputs are not reused.
- `verify_preparation(output, expected_manifest_sha256, acquisition_record=None)`
  reopens exact originals/receipts, verifies projector identities and reconstructs
  every product, purpose, count and repeated report field.
- `load_product(output, verified_manifest, product_id, purpose)` checks the
  retained manifest, consumer purpose, exact bytes and product fields before returning
  immutable records. This is a trusted authorization/preparation interface, not a
  reason to pass the full manifest to the predictor.

The first fictional test attempt encountered an inaccessible sandbox TEMP; rerunning
with a workspace TEMP passed. Actual preparation attempt01 exposed one legitimate
repeated citation ID in development claim 1245. The original parser rejected it
too strictly; the correction preserves the original reference array and records a
diagnostic while group edges and pair identities use sets. No claim was excluded.
Attempt02 completed and remains unchanged. A subsequent adversarial test found five
duplicated report fields were insufficiently reconciled by verification; failing
tests are retained, the checker was corrected, and fresh attempt03 uses the updated
source pin. All 12 projected product bytes are identical between attempts02 and03.

Attempt03 preparation took 0.630 seconds; source reconstruction took 0.876 seconds.
The retained output occupies 12,015,507 bytes. Peak process memory was not instrumented
in these preparation attempts and remains null; no retrospective estimate replaces it.
Runtime sources and frozen BG02 artifacts were not edited by this task.
