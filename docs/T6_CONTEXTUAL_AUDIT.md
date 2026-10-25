# Contextual claim audit contract v2

This evaluator-only contract implements the representation boundary identified by
the IL6R development adjudication. It verifies exact locations and review
consistency. It does not discover scientific truth, qualify a clinical scorer or
automatically establish complete atomic extraction. V1 and native-run contracts
remain unchanged.

## Source surface and preparation

`compile_surface(binding_proof, approved_roots=...)` replays the existing native
v2 dossier binding and complete original Open Targets checks. The result binds
all seven hypothesis fields and exact dossier bytes. Every physical line has a
location; every JSON value in each provider-metrics block has an RFC6901 pointer,
exact encoded token interval, type and decoded-value fingerprint. Provider blocks
are compared to the physically verified row projection. Repeated strings retain
their distinct original occurrences. Locations are not atoms.

`build_surface(binding_proof, output, approved_roots=...)` reserves a new directory
before source work, journals stages/failures/interruption and writes `surface.json`,
`draft-inventory.json` and `report.json`. The draft contains no invented claims:
all unresolved content stays explicitly uncertain. Existing output cannot be
resumed or overwritten. Source/binding directories remain separate. Artifacts
over 64 MiB and excessive token/node counts fail without dropping content.

The default runtime remains dependency-free; original Parquet replay uses the
existing pinned ingestion extra. No network/model client or feature writer is
introduced. A structural template cannot be called a gold reference.

## Context-bearing propositions

An inventory uses schema 2, `role: evaluation_only`, an annotator identity, the
exact surface fingerprint and question, `status: draft|reviewed`, claims, ordered
line dispositions and ordered provider-value dispositions. Every line and JSON
value must receive a reasoned classification. Containers supply context, not
additional facts. Mined scientific text cannot disappear under generic source-data
classification. Uncertain extraction cannot be marked reviewed.

Each proposed claim has:

| Field | Meaning |
|---|---|
| `claim_id` | Unique occurrence identity |
| `stratum` | Annotation, scientific, operational or clinical-unassessable |
| `stance` | Source-attributed, dossier-endorsed or caution |
| `unit_kind` | Proposition or estimate bundle |
| `context` | Record, study, hypothesis or operational scope and explicit identity |
| `proposition` | Subject, predicate, object, negation, modal force, population, tissue, intervention, comparator, outcome, timing and exposure/outcome orientation |
| `focus` | One exact located fragment for the assertion under review |
| `context_fragments` | Separately located premises/context; never concatenated into a purported literal quotation |
| `entity_resolution`, `entity_reason` | Resolved or uncertain coreference with a rationale |
| `numeric_bundle` | Located estimate/interval/P/scale components, or null |
| `dependence` | Known overlap, partially known, unknown or inapplicable, explicit groups and rationale |

Canonical propositions are reviewer-authored interpretations of the text. They
are deliberately separate from literal fragments; the contract cannot prove that
the interpretation is semantically correct. Population, tissue and other absent
qualifiers remain null. Timing can distinguish discovery from replication, and
orientation distinguishes exposure from outcome. Unresolved antecedents cannot
receive definite supported/contradicted scientific or applicable-intervention
ratings.

A fragment contains `node_id`, a half-open UTF-8 byte `span`, and exact `text`.
For JSON strings, this span addresses the decoded value; the surface retains the
entire original encoded token separately. Literal nodes address actual dossier
text. Escape sequences are not confused with decoded characters. Multiple context
fragments cannot manufacture a new verbatim quotation.

Provider text and copied source quotes retain source-attributed stance. An actual
prose interpretation may be dossier-endorsed and use provider premises, subject
to reviewer assessment. A record-scoped proposition cannot import another
record's fragments. Cross-study/context relationships must be declared and remain
reviewer attestations; unknown dependence never becomes independence.

## Numerical bundles and repeated propositions

An estimate bundle keeps estimate, interval, P value and scale together with a
reason and explicit exposure/outcome orientation. Unreported components are null.
Each reported component is itself an exact fragment with coordinates, contained
within the claim's declared focus/context. A sign, exponent, inequality or
precision suffix cannot be removed by finding a convenient substring. Located
components do not establish the correct causal interpretation, scale or analysis;
those still require the scoped source reference and review.

Proposition identity binds the full hypothesis, semantic context, proposition,
stratum, stance, unit kind and reported numerical text. Repeated occurrences of
the same proposition count once in descriptive group counts. Identical words
about distinct source records can describe different propositions. Changes in
action, modality, tissue, namespace, negation, timing, orientation or reported
numbers cannot reuse an old scientific-reference scope. Identity/grouping is not
an independent experiment count.

## Independent review dimensions and references

`assess_review(inventory, surface, review, references, approved_roots=...)` checks
a supplied surface and clearly reports that this entry point did not replay the
originals. `audit_v2(binding_proof, inventory, review, references,
approved_roots=...)` reconstructs the source surface first and reports the source
replay explicitly. A saved surface alone is never an original Parquet proof.

A review binds inventory, surface and reference-list fingerprints. It covers all
proposed claims in frozen order, identifies its author and declares development
or blinded-paired review mode. The mode is an attestation here; future experiment
execution must enforce actual blinding and pre-output freezes.

Keep these axes separate: source fidelity, scientific validity, intervention
applicability, attribution and uncertainty. A faithful report of a questionable
premise can have supported fidelity and contradicted scientific validity. Clinical
assertions remain unassessable in this source-quality phase. A dubious clause does
not automatically invalidate adjacent supported clauses. Conflicting labels for
the same canonical proposition require explicit adjudication. Uncertainty is
reported using the maximum ordinal rating across its repeated occurrences.

Substantive scientific ratings require evaluator-only reference records scoped
to the exact source-run binding and question/proposition. This retains origin and
program context even when hypothesis text is identical. A different run needs
explicit reference requalification. Each reference records an attestor, basis,
limits and qualification, plus a pinned evaluator parent, JSON pointer and value
fingerprint. Parent files and roots are checked. `scope_adjudicated` is an
identified reviewer's qualification assertion, not cryptographic proof of
scientific truth, independent reasoning or public availability. A separate
reference-construction/adjudication protocol remains necessary.

## Output and remaining gates

Reports retain occurrence/group counts, separate stratum-and-stance axes,
uncertainty, declared overlap groups and unknown dependence. They produce no
pooled scientific error percentage, effective sample size, superiority claim or
clinical probability. Empty, wholly unknown or all-abstaining inventories cannot
win through a zero-error fraction. Easy metadata copies cannot dilute a scientific
error by being pooled into its denominator.

Complete byte/value disposition is a mechanical property. Atomic completeness,
correct context, necessary evidence coverage and scientific judgment remain
qualification tasks. Next: compile and independently qualify contextual atoms and
an evidence-dimension completeness reference, then enforce reference/prediction
seals and qualify bounded interpretation. A fresh paired study is still required
for the original full T6/H5 objectives; existing exposed development cases remain
development cases. Current runtime/scorer probabilities and features are unchanged.
