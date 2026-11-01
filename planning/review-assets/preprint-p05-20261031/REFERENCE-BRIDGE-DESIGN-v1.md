# P05 original-source reference bridge — design v1

Status: DESIGN ONLY; UNEXECUTED. Written 2026-10-31 from public code and neutral
frame/registry-plan metadata. Stage 1 has not run. No selected cases, original
biological values, audit captures, references, model outputs, or new source facts
were opened or created for this review. This does not freeze stage-2 endpoints or
technical valid/fault contrasts.

## Recommended boundary

Keep the current source-fact core and use one exact `studyLocusId` `one_to_many`
join. The task reports each physical credible-set row's own native `studyId`,
`variantId`, beta, standard error and p-value components. A locus link does not
assert equality of study/variant identities, resolve a composite identity, or
convert a study/variant statistic into a gene, intervention, drug or causal effect.

Both later branches must freshly reread the immutable originals plus the sealed
neutral selected-case plan. The generation branch must not read compiled
references or their descendants. The reference branch must not read generation
outputs. `selected-originals/*.jsonl`, normalized mapping captures, coverage,
lineage/audit reports and other stage-1 audit captures remain `evaluation_only`
and are forbidden value parents for both branches. The registry/selected-case
plan supplies routing identities only; it is not a value source.

## Existing exact public calls

The public task interface is a strict mapping, not a `SourceFactTask` dataclass:

```python
task = validate_task(task_document)
reference = compile_reference(
    task, snapshot, approved_derived_root, trusted_catalog,
    deadline=deadline,
    denied_source_ids=denied_source_ids,
    denied_dataset_ids=denied_dataset_ids,
    denied_sha256=denied_sha256,
    approved_raw_root=approved_original_root,
)
verified = verify_reference(
    retained_reference_document, independent_reference_sha256,
    task, snapshot, approved_derived_root, trusted_catalog,
    deadline=deadline,
    denied_source_ids=denied_source_ids,
    denied_dataset_ids=denied_dataset_ids,
    denied_sha256=denied_sha256,
    approved_raw_root=approved_original_root,
)
cell = score_cell(verified, retained_output_bytes, cell_id=cell_id)
```

`compile_reference` admits every node of the supplied graph before row values,
checks original/receipt bytes under stable locks, replays exact physical locators,
checks expected literal identity, and returns an immutable `VerifiedReference`.
Replay checks an independently retained reference fingerprint and recompiles from
sources. Deny-list completeness and catalog classification are trusted inputs;
the API does not discover hidden response ancestry from text.

## Task shape and minimum row requests

The following is a schema-shaped template, not a task with source values. All
angle-bracket substitutions must be filled from later eligible original reads;
dates, namespace versions and source/plan hashes cannot be invented.

```json
{
  "schema_version": 1,
  "task_id": "p05-<case-id>-native-locus-v1",
  "scope": {
    "target_id": "<selected exact targetId>",
    "indication_id": "<selected exact diseaseId>",
    "target_namespace_version": "<frozen target namespace version>",
    "indication_namespace_version": "<frozen indication namespace version>",
    "action": null,
    "modality": null,
    "tissue": null
  },
  "cutoff": "<exact frozen UTC cutoff>",
  "profile": "contemporary_assessment",
  "primary_families": ["reported_measurement"],
  "records": [
    {
      "record_key": "gwas-<physical-key>",
      "source_id": "<original GWAS source node>",
      "locator": {"format": "parquet", "row_group": 0, "row": 0},
      "identity": {
        "targetId": "<exact targetId>",
        "diseaseId": "<exact diseaseId>",
        "studyLocusId": "<exact studyLocusId>"
      }
    },
    {
      "record_key": "credible-<physical-key>",
      "source_id": "<original credible-set source node>",
      "locator": {"format": "parquet", "row_group": 0, "row": 0},
      "identity": {"studyLocusId": "<exact studyLocusId>"}
    }
  ],
  "fields": [
    {
      "record_key": "credible-<physical-key>",
      "field": "beta",
      "family": "reported_measurement",
      "group": "measurement:credible-<physical-key>",
      "unit_field": null,
      "empty_policy": "unknown"
    }
  ],
  "joins": [
    {
      "join_id": "locus:gwas-<physical-key>",
      "left_record": "gwas-<physical-key>",
      "left_field": "studyLocusId",
      "right_records": ["credible-<physical-key>"],
      "right_field": "studyLocusId",
      "cardinality": "one_to_many",
      "inventory_status": "complete"
    }
  ],
  "collection": {
    "status": "selected_records",
    "reason": "Eligible selected physical rows in the declared pinned input frame only; source-locus reporting, no biological absence claim."
  }
}
```

The displayed zero locator indices are shape examples, not selected locators.
Expand records to **every eligible physical GWAS row for the selected triple**
and **every eligible physical credible-set row with that locus in the declared
25-file credible-set frame**. Distinct physical locators remain distinct records,
including identical duplicate projections. Retain optional native evidence `id`,
`studyId` and `variantId` in a record's identity only when present; missing/null
study or variant identity must remain reportable as unknown rather than being
required for inclusion. Never manufacture a composite identity from a locus or
variant spelling.

For each GWAS anchor use one locus join with the full eligible credible-candidate
list. Every anchor already literally contains both selected scope IDs. The core
requires all incoming joins of a linked row to resolve; with one selected locus,
these locus joins must agree. Do not quietly choose one duplicate anchor.

Expand `fields` using exactly this minimum family/group rule:

| Physical record | Literal fields | Family | Group |
| --- | --- | --- | --- |
| Each eligible GWAS row | `id`, `targetId`, `diseaseId`, `studyLocusId`, `studyId`, `variantId`, `datasourceId`, `datatypeId` | `identity_linkage` | `identity:<record_key>` |
| Each eligible credible row | `studyLocusId`, `studyId`, `variantId` | `identity_linkage` | `identity:<record_key>` |
| Each eligible credible row | `beta`, `standardError`, `pValueMantissa`, `pValueExponent` | `reported_measurement` | `measurement:<record_key>` |

Every field request has `empty_policy: unknown` and `unit_field: null` unless an
actual native unit field is declared by the frozen stage-2 projection. Optional
reported context may request `chromosome`, `position`, `sampleSize` on credible
rows and `ancestry`, `ancestryId` on GWAS rows under their existing known families;
these fields do not enter the primary measurement denominator. `ancestryId` is an
identity field; `ancestry` is context. Missing fields can be requested where the
name is in the core field-family map and produce `field_not_in_schema`.

This grouping is a candidate design, not a frozen primary endpoint. One group
contains four native components per credible row; scoring gives the matched
answerable-component fraction and equal weight to each answerable group. A
partially returned p-value pair is not checked as an atomic scientific result.
Do not compute decimal p-values, derive SE from p-values, rescale beta, infer an
odds ratio, harmonize alleles, or rank/select cases by numeric availability.

## Snapshot, roots and product lineage

Use the existing v2 `Snapshot` with `schema_version=2`,
`profile=Profile.CONTEMPORARY`, `origin=cutoff.date()`, `origin_at=cutoff`,
`allow_reconstructed=False`, `artifacts=()`, absolute `raw_root`, and the admitted
original `SourceNode` objects. Each raw node keeps its actual dataset/release,
relative original path/hash, source URL, receipt path/hash, original availability
proof, and `TemporalClass.CONTEMPORARY`; raw nodes have `parents=()` and
`computed_at=None`. Do not replace receipt availability with release-label dates
or claim historical eligibility. A later build time is separate from the frozen
information cutoff.

```python
snapshot = Snapshot(
    schema_version=2,
    snapshot_id="p05-<case-id>-originals-v1",
    profile=Profile.CONTEMPORARY,
    origin=cutoff.date(),
    allow_reconstructed=False,
    artifacts=(),
    sources=tuple(original_nodes),
    raw_root=str(approved_original_root),
    coverage={"scope": "selected_original_frame_only",
              "historical_eligibility": "not_verified"},
    origin_at=cutoff,
)
```

`original_nodes` includes all original dependencies actually consulted by the
case inventory and mapping/eligibility replay, not just files with emitted facts.
The wrapper's independent seal binds the full scan frame even where a file has
zero selected matches. Raw receipt availability can be represented using the
existing `Availability(..., basis="public_download_receipt",
known_public_by=receipt_completed_at, evidence_ref=receipt_sha256)` with unknown
publication/release/record/annotation dates retained as null, as stage 1 does.

HGNC may be included and verified as an original graph input without requesting a
TSV task record. Reread original HGNC TSV and Open Targets target/disease tables
to replay the exact approved mapping, uniqueness and exposure rules. Native TSV
HGNC fields are not directly representable in current source-fact locators.

The graph accepts input roles `agent_evidence`/`reference` allowed by the trusted
catalog; it rejects `evaluation_only` and does not accept `neutral_metadata`.
Consequently bind the neutral plan, READY, code, frame and catalog hashes in the
stage-2 wrapper/manifest, not as falsely relabeled raw `SourceNode`s. Per-product
lineage must name all original inputs actually used and the neutral routing plan;
no audit capture or evaluator reference is an input to generation. Reference
products themselves remain `evaluation_only`, `agent_visible=false`.

If an eligible derived input is ever necessary, the existing graph requires its
full original parent closure, a catalog-allowed role, timezone-aware
`computed_at`, and versioned method. Computation may be later than the cutoff
when all information ancestors are eligible. `computed_at` never establishes
old information availability. This bridge needs no derived value inputs.

Pass roots as explicit trusted runtime arguments. `approved_raw_root` must equal
the absolute snapshot raw root; the snapshot cannot grant itself access. Bind
logical paths in retained proofs and preserve exact bytes/receipts if relocating.

## Required stage-2 wrapper, including reference verification

1. Before source values, verify the sealed selected plan and its independent
   hashes/protocol binding; retain the actual count 1..12, original hash
   selection, known exposed exclusions and `other_exposure: UNKNOWN`. Check all
   original roles, full graph eligibility, receipts/hashes and allowed roots.
2. Under stable original/receipt locks, independently reread original mapping
   tables and all candidate files needed for selected-case discovery. Use the
   **same pinned precision-aware row-date and mapping/role eligibility logic as
   stage 1**, at the **same frozen cutoff**, before publishing generation values
   or calling the reference compiler. Extend projection only for frozen literal
   reporting fields and guard fields actually needed; no values from captures.
3. Replay eligibility per physical row. A selected unit may have eligible and
   ineligible duplicate rows. Preserve only eligible rows as task/source values;
   retain excluded locators and eligibility reasons in private technical metadata
   without disclosing excluded biological values. Never copy a future duplicate
   into a candidate inventory or let it create a conflict that blocks eligible
   evidence. Missing dates remain an explicit availability limitation.
4. Bind the entire eligible candidate inventory, exact field/group definitions,
   source and receipt hashes, original/plan/code hashes, cutoff and coverage
   disposition before deterministic output contrasts. Recheck common-wire
   representability; no silently removed rows or fields.
5. Build the agent-visible literal source packet from its own original reads.
   Publish only original eligible values, physical bindings and neutral task/slot
   information; no compiled expected-value projection, reference unknown reasons,
   evaluator join reports or reference-derived payloads.
6. Separately reread originals to compile the evaluator-only reference. The
   shared guard/scanner may be pure code; retained source values may not cross
   branches through audit captures or a compiled reference.
7. A `verify_p05_reference` wrapper must **replay steps 1–4 from originals again**,
   compare the independently retained wrapper/task/inventory hashes, and only
   then call existing `verify_reference`. Base reference replay alone does not
   verify the new normalization, exclusion inventory, READY cutoff or precision
   guard policy.

The stage-1 guard includes publication-date/year interval intersection and
independent evidence/release guards. The base compiler checks only
`publicationDate`, `evidenceDate`, `annotationDate`, and `publicationYear` with
different rules. Never assume one substitutes for the other.

## Unknowns, multiplicity and coverage

`one_to_many` retains all locus matches and their source bindings; distinct study
or variant identities and conflicting numeric reports stay separate physical
facts. It makes no first-match choice and does not call disagreement a resolved
composite match. Current `one_to_one` instead withholds linked facts for multiple
matches, even identical requested projections; differing requested values yield
`conflicting_values`. That behavior is available for separate frozen technical
controls but is not this locus-report design.

For an exhaustive eligible candidate inventory, an empty `right_records` list
reports only `zero_matches_selected_collection`. With a partial inventory it
reports `missing_input_in_partial_collection`; do not label it complete.
Without credible rows there are no invented measurement slots/source bindings.
GWAS identity facts may remain, while measurement coverage/pass stays null.
Keep the selected unit in the technical accounting and never replace it because
its measurement denominator is zero. `collection: incomplete` must state which
bounded collection is incomplete; it never means biological absence.

Unit `null` means no supplied native unit; it does not establish a dimensionless
or log-odds scale. The current wire has no separate unit-unknown reason. Include
an explicit neutral context statement that units/scales, effect/reference allele,
genome build and study-level ancestry are unknown unless literally supplied by
the frozen eligible projection. Report native GWAS ancestry only as that row's
reported context, without transferring it to a credible statistic. Do not infer
build/alleles from `variantId`, study identity from a locus, or effect allele from
`alleleOrigins`. The study table is absent and must not be substituted. These
limitations are metadata, not invented task facts.

## Current blockers and bounded failure policy

* A task has at most 64 records, 512 field requests, 32 joins and 1 MiB canonical
  task bytes. Output has at most 512 facts and 256 KiB. The compiler checks exact
  projection against that same output adapter. Retain a selected case as explicit
  technical failure/coverage limitation if its complete inventory exceeds a
  bound. Do not discard candidates, increase limits or add unplanned sharding.
* Fields are literal original top-level names from the fixed family map. No
  nested-field access, expressions or composite-key primitive is available.
  `approvedSymbol`, disease `name` and HGNC naming fields are not existing
  reportable fields. Their mapping validation belongs in the wrapper.
* Joins require identical `release_id`; original HGNC uses a different release
  label. Do not relabel releases to force a join. The wrapper's exact mapping
  replay and raw graph admission handle that dependency.
* The API supports JSON objects and Parquet only, with PyArrow exactly 21.0.0.
  JSON originals are bounded at 64 MiB. A Parquet locator is row-group index plus
  row-in-group index, both zero based; translate stage-1 metadata names exactly,
  never use a global physical row as the row-in-group index.
* A row may pass the new precision guard and remain unrepresentable in the old
  compiler: e.g. year/month `publicationDate`, a string `publicationYear`, or a
  timezone-offset spelling rejected by its strict UTC parser. Base replay reads
  these date fields automatically. Do not strip/coerce native dates to force a
  pass; retain the selected case with an explicit API/date-representability
  failure.
* Answerable measurements require native finite int/float excluding Boolean;
  `pValueExponent` requires native int. Invalid native numeric types/nonfinite
  values fail compilation rather than being coerced. The core does not establish
  SE positivity, valid p-value ranges, units or scientific study validity.
* Source/binding/ID/unit strings must also fit common-wire bounds; values have
  finite depth/node/string bounds. No truncation or coercion is acceptable.
* No source packet builder, qualified contrast schedule, row-inventory seal or
  P05 wrapper verifier exists merely because this design names it. Those remain
  stage-2 work after stage-1 success and a sealed selected manifest. Technical
  contrasts and their primary endpoint must be separately frozen before outputs.

## Small implementation proposal

After stage-1 sealing, add a P05-only wrapper module/script with a shared pure
original-row enumerator and eligibility replay, two separately executed product
builders, a neutral inventory/task seal, and a `verify_p05_reference` wrapper as
specified above. Reuse `validate_task`, `compile_reference`, `verify_reference`,
`adapt_output` and `score_cell` unchanged. Use deterministic exact projection only
as a technical ceiling comparator; label fault controls as constructed controls.
Do not reopen the model branch or make new LLM, biomedical, clinical, causal or
independence claims. Meaningful controls should cover future/ineligible duplicate
exclusion, all physical locus matches, zero matches, representation failures and
forbidden evaluator/audit ancestry before any actual stage-2 run.
