# TETHER — Source-fact reporting study contract

TETHER (Target Evidence Tracking Harness for Evaluation and Reproducibility) is the current project name. The `tether-target-agents` 0.4.1 package in `packages/tether` supplies the `tether` CLI and import namespace over the frozen AsOf 0.3.11 engine. See [installation and compatibility](../README.md#installation-and-compatibility). Historical version/arm names, module commands, source paths and wire IDs below remain unchanged; the rename does not reactivate retired study or expert-review branches. Direct API aliases preserve legacy outputs; only the separate `tether._presentation` CLI layer wraps `demo`/`run` in the [TETHER run layout](../README.md#tether-cli-run-layout). Delegated source inspection, snapshot construction and evaluation keep their engine layouts.

Development version 1, initially written before P03 implementation on 31 October
2026. The initial document is retained at
`planning/review-assets/preprint-p03-20261031/TASK-CONTRACT-v1.md`; the API and
correctness clarifications here were made during implementation before any new
candidate generation. This is a separate study interface, not a replacement for v2
execution, native interpretation, existing codecs or archived verifiers.

## Task and claim

Given a frozen reporting scope, cutoff, eligible source records and requested
literal fields, report those values with their original bindings and explicit
collection-bounded unknowns. The development study concerns source eligibility,
composition, missingness, verified completion and resources. Exact projection is
the declared ceiling comparator. Successful copying is not better biomedical
interpretation. Measurement coverage/pass remains null when measurements are
unavailable; neither identifiers nor provider scores can rescue it.

Scope contains target/indication IDs and namespace versions, plus nullable action,
modality and tissue. Null intervention context stays null. Sources and all mapping
ancestors must pass existing v2 catalog/role, temporal, receipt and hash checks.
References and their descendants are evaluator-only. No bespoke expert return or
response-derived ancestor is eligible. Explicit source/dataset/hash deny lists
supplement catalog enforcement; their completeness is a trusted provenance input,
not a semantic detector of relabeled or undisclosed content.

## Frozen task representation

`source_fact_sources.validate_task` accepts exactly these keys:

- `schema_version`: integer 1; `task_id`: nonblank string.
- `scope`: exactly `target_id`, `indication_id`, `target_namespace_version`,
  `indication_namespace_version`, `action`, `modality`, `tissue`.
- `cutoff`: exact timezone-aware UTC ISO timestamp; `profile`: existing
  `contemporary_assessment`, `historical_benchmark` or `synthetic_demo`.
- `primary_families`: nonempty unique subset of `identity_linkage`,
  `reported_context`, `reported_measurement`, `provider_metric`. The eventual
  protocol names the reporting estimand; a measurement endpoint uses only the
  measurement family. The provider family is descriptive, never an effect size.
- `records`: at most 64 objects with exactly `record_key`, `source_id`, `locator`,
  `identity`. Record keys are unique. Locator is either JSON
  `{format: json, pointer: ...}` or Parquet
  `{format: parquet, row_group: integer, row: integer}`. Identity is an explicit
  nonempty mapping of original field names to exact expected values, not a fuzzy
  identifier resolver. At least one record anchors target/indication directly;
  other records must be connected by declared exact-key joins.
- `fields`: at most 512 objects with exactly `record_key`, `field`, `family`,
  `group`, `unit_field`, `empty_policy`. A field is a top-level original field;
  no expressions or code. `unit_field` is null or a literal original field name;
  no inferred/literal invented units. `empty_policy` is `unknown` or `value`.
  Field-family classification is checked against a fixed known-field map.
  Each group belongs to one record and one family, with equal group weights.
- `joins`: at most 32 objects with exactly `join_id`, `left_record`, `left_field`,
  `right_records`, `right_field`, `cardinality`, `inventory_status`. Right record
  keys explicitly enumerate the selected candidate rows. Cardinality is
  `one_to_one` or `one_to_many`; inventory status is `partial` or `complete`.
  Completeness means only this declared candidate inventory; it does not prove
  full-release enumeration. No implicit table searches or nearest-locus matching.
- `collection`: exactly `status`, `reason`; status is `selected_records`,
  `zero_matches_selected_collection`, `incomplete` or `failed_qc`. Reason is a
  nonblank scope statement. Empty inputs are allowed only for explicit bounded
  missing-input conditions, never as biological absence.

Compile and replay functions take independently retained task/source/reference
hashes and explicit approved roots. They use stable bounded original reads,
complete source ancestry and source/receipt proofs, not an expected-answer hash
alone. Derived data may be computed later using eligible old information.
Publication and annotation eligibility are checked separately from computation.
The default runtime remains dependency-free; Parquet replay requires the existing
optional Arrow 21.0.0 extra.

The only field transform is exact native typed projection (`literal_field.v1`).
Unknowns distinguish absent schema, native null, native empty, missing/incomplete
collection, failed QC and unavailable/conflicting joins. Original lists preserve
order. Integer, float, Boolean and signed zero remain distinct. JSON numeric
lexical spelling is not preserved beyond the parsed native type/value.

Answerable measurement values must be native finite integers/floats, excluding
Booleans; `pValueExponent` must be an integer. Incompatible native types fail the
task's measurement QC explicitly instead of becoming measurements or being
coerced. This does not validate units, biological interpretation or study design.
Null/absent/empty unknown dispositions remain distinct. Every compiled reference
must admit a complete exact projection under the same adapter bounds used for
all arms; overlong bindings, units or values fail explicitly, without truncation.

`compile_reference` and `verify_reference` accept `approved_raw_root` only as an
explicit trusted caller argument. A snapshot cannot grant access outside the
supplied root merely by declaring another `raw_root`. Catalog, exclusion-policy
and logical source-snapshot fingerprints are archived in the reference method.
Source proofs use logical paths so replay can relocate identical bytes through
explicit approved roots; relocation never relaxes source or receipt checks.
Exact-key joins require the same release in this version.

Exact joins preserve zero, one and multiple matches and every matched locator.
One-to-one multiplicity is unresolved, never a first-row choice; differing
requested values are conflicting. Partial-inventory zero means missing local
input; complete selected-inventory zero is only a bounded provider-linkage zero.
Linked-locus values remain locus reports, not target-perturbation/drug effects.
Linked facts are withheld as unknown when their declared join is unresolved.

## Generator-neutral output and adapters

New arms use `typed_facts_v1`: a JSON object with exactly `schema_version: 1`,
`task_id`, `task_sha256`, `status`, `facts`, `collection_status`, `reason`.
Status is `answered`, `partial`, `abstained` or `insufficient_input`.
Each emitted fact has exactly `fact_id`, `value`, `unit`, `source`,
`unknown_reason`. `source` is the complete supplied file/release/physical
locator/field binding. Fact identifiers bind the task/scope, source bytes,
release, physical record and field, preventing cross-file provider-ID collisions.
Unknown reason is null for a reported value and nonblank for an explicit null.
Answer slots and identifiers may be supplied; expected values never are.

`source_fact_adapters.adapt_output` parses only retained emitted bytes. It neither
opens sources nor receives expected reference values. It does not repair,
deduplicate, infer values, expand quotes or insert omissions. Duplicate JSON keys,
nonfinite values, wrong shapes and oversized outputs are malformed. Legacy
`interpretation_v2` prose is preserved as explicitly unscorable for typed facts;
citations and validator-expanded quotes do not become authored measurements.
It remains separate from any comparison that requires the new common wire.

## Scoring and all-cell accounting

`source_fact_evaluation.score_cell` requires a source-verified reference object
from `source_fact_sources`, not an arbitrary serialized answer file. Verification
is at compilation/replay time with stable reads, not a live rehash on every score.
Loaded references are recompiled/replayed against an independent hash anchor.
References and normalized outputs are copied and recursively frozen.

Each answerable group contributes its matched-fact fraction; average these
fractions equally within each family. Primary coverage averages all answerable
groups in the predeclared primary families equally (not an average of family
averages). Unknown-only groups have no denominator. Report component counts and
group counts as well. The same reference-derived denominator applies to all arms.
Omissions reduce coverage. Explicit correct unknowns earn no coverage and no
unsupported-assertion error. Invented values/units, wrong source or unknown reason,
duplicates and unknown fact IDs are critical errors. Preserve all conflicting
emissions; they cannot be silently deduplicated or offset by correct facts.

Readable partial outputs may earn their actual coverage; completion requires a
valid answered/partial return, correct collection disposition, zero critical
errors, and at least 80% primary group coverage. Report 60/80/100% sensitivity
flags. Report measurement completion separately; zero answerable measurement
groups gives null coverage/pass. Abstention has no coverage credit. A fully
unknown reference has no coverage pass; separately score correct bounded
insufficient-input handling. No absence-of-biology option exists.

Every scheduled cell has exactly one terminal `returned`, `malformed`, `failed`,
`timeout`, `interrupted` or `unexecuted` disposition. Failed/unreadable cells have
null coverage and completion false and stay in the planned-cell denominator.
Partial-byte analysis is secondary, never a rescued completion. Aggregate helpers
reject omitted, duplicate or unscheduled terminal cells, and task/reference
substitution within a case. Raw output hashes remain bound to each cell.

The scoring function receives retained raw bytes and calls the declared adapter
itself; callers cannot supply a forged normalized output/hash pair. Returned
malformed bytes produce normalized terminal `malformed`, while `received_terminal`
preserves the transport's `returned` event. Explicit non-return terminal events
cannot be rescued by parseable partial bytes. An all-unknown reference with the
correct collection status and `insufficient_input` response can pass the separate
missing-input handling check, never the zero-denominator coverage endpoint.

Adapter limits are 256 KiB, 512 emitted facts, 512-character IDs/units, 1,800-character
reasons, JSON value depth 16, 4,096 value nodes and 8,192-character value strings.
These are explicit failures, not truncation. A non-bytes API argument is caller
misuse; malformed byte payloads yield retained malformed dispositions.

## Acceptance and limitations

Finite fictional controls must cover source/receipt tampering, scope/date/role and
complete-ancestor rejection, response-derived mappings, cycles/missing parents,
null/empty/schema absence, duplicate IDs across sources, zero/one/many/conflicting
joins, units/types/signed zero, grouped denominators, adapter omissions and
failure accounting. Replay at least one independently checked actual-format
source without using old candidates or response-derived artifacts. These are
engineering controls and exposed development evidence, not locked study cases.

P03 completion also requires relevant legacy regressions and an installed-package
smoke for the new public functions. P04/P05 still require independently built
agent-visible source packets, actual qualified arms, exposure/cohort registers,
prospective protocols, resource measurement and adequate information. No P03
reference may itself be passed to generation. Source fidelity is not semantic
entailment, clinical truth, causality, expert alignment or model superiority.
