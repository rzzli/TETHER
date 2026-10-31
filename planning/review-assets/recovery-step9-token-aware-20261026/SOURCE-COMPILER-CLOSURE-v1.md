# Source preparation compiler: concrete reuse and minimal packaging boundary

Read-only dependency audit, 2026-10-26. No runtime/test changes, data collection, source admission or model execution in this audit.

## Existing call graph

```text
tools.science.interpretation_questions.prepare_question :118
  question_template :34                        (reject unknown family before IO)
  bounded_interpretation.prepare_input :64
    run_comparison.pin :46 / check_pin :51     (legacy hash/stat helpers)
    serde.decode(Case) -> Case.validate
    chrono.load_snapshot :162
      chrono.admit_snapshot :168
        provenance.catalog_index :13
        InputGraph.__init__ :35               (DAG, roles, paths)
        eligible_artifacts / observation_exclusion
        exact packet bytes -> hash -> decode
        InputGraph.exclusion :87             (complete parent eligibility)
        InputGraph.verify :105               (raw/receipt identity and bounds)
        EvidenceStore -> query(case, category)
    select explicit observation_ids; no clinical category
    compile case/evidence/coverage/bounds/instructions
  bind_question :108
    question identity + hypothesis key + source scope
    validate_request
```

The packaged equivalent `asof.study.diagnostic_codec.bind_question` already exists at line441 and remains a structural binder, not admission. No need to port the whole old runtime, inference adapters, evaluation tools, review workflows or code_paths scanner. `bounded_interpretation` imports these broader utilities because it also executes/validates old runs; its preparation function actually needs only contracts, kernel admission, serde, a minimal immutable Prepared result, input pin checking and literals. Replace its legacy pin/check_pin with current `study.proofs.capture_file`/stable guarded reads, preserving exact output request semantics. Keep accepted old files unchanged.

## Exact 14b7 reconstruction constraints

The retained R07 preparation script `data/cache/r07-source-revalidation-20261026-v2/revalidate.py` calls prepare_question at line110 with genetic-study-report.v1, max_claims2 and one explicit observation ID. It validates original case/snapshot/catalog, full snapshot admission followed by explicit selection, complete selected ancestor closure, request identity and paired payload hashes. The key is `ot25:europepmc:91c27fcc680f479e627123e76c5b74c0adc88732`; the case is the already exposed IL6R antibody/inhibit development hypothesis. Its normalized method is2.2, source locator raw-965fc4633c8be93aa7b12569, row_group0/row130119; features are empty. This note does not independently reopen or validate the raw row.

Exact parity requires original category traversal/order, original explicit subset coverage (including observations_available), original statement duplication/source_ref/scientific_record fields, case namespace versions, bounds max_text_bytes8192/max_quotes_per_claim8, exact protocol instructions and question template. Preserve empty arrays/nulls and all metadata. Do not serialize new provenance fields into the request: keep authority manifests/proofs separately. The old compiler forces features={} at line88; initial new preparation must reject nonempty original features rather than silently modifying them. Empty features produce the same original14b7 hash. Original request bytes are retained separately; expected hash is an equality check, not the source authority.

## Important distinction: admission versus original-row replay

The retained R07 revalidate.py imports SourceAudit-related files only through dependency discovery; its complete_source_admission stage does **not call a Parquet original-row replay**. It proves normalized packets and raw ancestors match their pinned hashes and admission policy. That is substantial provenance evidence, but it does not itself prove the normalized source_metrics/statement exactly match a physically located original row. Do not inflate its source-inclusive label into a fresh complete transformation audit.

Existing original-row auditing is reusable as narrow pure logic:

- `tools.framework.run_pilot.SourceAudit.source` line61 checks raw file hashes with before/after metadata; `parquet_row` line76 validates row_group/row and projects columns before slicing one Arrow row and converting to Python. Its cached path/stat boundary needs current guarded stable-read handling. Its `mappings` line89 hardcodes the original PILOT set and should not be imported as generic authority.
- `tools.science.reference_packets._physical_key` line25 validates integer locators; `_source` line76 checks source URL/product/receipt authority; `_mappings` line108 replays target/disease/HGNC rows and namespace hashes; `audit_observation` line149 checks complete normalization fields against the raw projection. These are source-only validators even though housed in a reference-preparation module. Port only these pure comparisons, not reference/gold files, selection algorithms, builds, adjudications or outcome workflows.
- `audit_observation` checks projection order equals EVIDENCE_COLUMNS present in the schema, excludes clinical fields/ChEMBL, checks source_row_sha256, target/disease/provider/evidence IDs, statement/category/metrics, preserved context, empty numerical features/unknown causal direction, cohort/study/ancestry, publication/missingness and full mapping+raw parent references. It is substantially stronger than a row-hash-only assertion.
- `asof.ingest` normalization is inline at lines604â€“642, not a callable whole-row normalizer. Reuse its pinned EVIDENCE_COLUMNS/NORMALIZATION_VERSION (line28), `_json_value` line355 and `_publication` line369 where safe, with an explicit tested method2.2 adapter. Do not call build_snapshot or scan the whole release just to validate one selected row.

## Minimal new interfaces

1. `prepare_source_request(authority, roots, output, deadline)` decodes externally anchored case/snapshot/effective catalog plus explicit selection/template/bounds, performs unchanged complete kernel admission under approved roots, compiles selected records without field loss, binds the packaged question, writes request/proof report and rejects incompatible features. Return immutable request plus source/preparation receipt, not a freely mutable caller object.
2. `audit_ot25_selected_records(admitted_store, selected_ids, mapping_manifest, authority, deadline)` optionally requires the existing ingestion extra pyarrow==21.0.0, replays exactly selected evidence and mapping rows, and returns source-only technical checks. All ancestor bytes/receipts still verified; no outcome/reference imports. Initial supported source profile is OpenTargets25.09 normalization2.2 plus HGNC2026-10-10. Unknown normalization versions/products fail explicitly rather than generic claims of replay support.
3. `verify_source_preparation(path, receipt_sha256, approved_authorities)` verifies package/resource identity, complete file inventory/closure, request reconstruction and source replay evidence against the explicit authority. No tokenizer subprocess or generation happens on replay. If raw files are intentionally unavailable, only clearly labeled byte receipt verification is possible; do not silently call it source-inclusive semantic validation.

Default installed runtime remains dependency-free. `asof.ingest.arrow` line166 already requires exactly pyarrow21.0.0 and raises a clear optional-dependency error. Use this gate before Parquet access; no package install/download. CSV HGNC row replay can use the standard library. Bounded Arrow batches with selected columns, row_group and offset avoid converting an entire row group to Python; keep original physical coordinates. Reading Arrow data must occur only after product/role/root/receipt checks. A missing optional dependency yields an explicit failed or unsupported source-audit stage, not permission to mark real preparation eligible.

## Trusted source authority manifest

Require an externally anchored authority document separate from the output request: version/profile, exact case/snapshot/effective-catalog pins; logical root IDs and approved physical mappings; identifier-validation manifest pin; explicit selected observation IDs/order; question family and bounds; approved ingestion recipe/version and optional package version; complete raw+normalized+receipt inventory hashes/sizes/roles/release IDs; and package/compiler proof. Authority must derive from the already verified project snapshot/catalog/release and case approvals, not arbitrary caller JSON or a reference/gold folder. The identifier-validation manifest must itself be pinned, and its target/disease/HGNC locators must replay to approved identities and exact namespace hash strings. A case definitionâ€™s action/modality/tissue is owner-proposed scope, not inferred drug efficacy.

Prevalidate every graph node/receipt/artifact path against allowed roots before kernel construction/IO. Graph role rejection covers evaluator-only ancestors even if selected outputs look agent-safe. Keep a protected-input deny guard as defense in depth, not the sole authority. No original-root fallback, auto substitution, case replacement, source update, all-observation silent truncation, or outcome-dependent selection. Preserve current request14b7 only if all exact inputs and rows match. Otherwise fail with the precise differing field/stage; do not add a bypass for this familiar development ID.

## Concrete finite next engineering scope

After contract and peer approval: package the small preparation compiler and method2.2 selected-row audit with source-only fixtures/tests; integrate existing guarded proofs and explicit authority envelope; qualify the one exposed real request against its original inputs. Only after that authority succeeds may token-aware sizing process its aligned full-source payloads. No broad source ingestion rewrite or additional controller is needed. This prepares a reviewable real request; it does not activate native generation or complete R09 scientific evaluation.
