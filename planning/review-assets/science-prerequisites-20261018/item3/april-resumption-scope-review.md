# April resumption: finite Science 3 acceptance

This is a read-only review of the frozen Science 3/4 contracts, origin mapping-r1,
Item 3 reports and implementation source. No database operation, endpoint-record
inspection, cohort join, adjudication or new integrity audit was performed.

**Science 3 can pass as an explicitly amended reconstructed exploratory input stage;
it cannot pass as a clinically qualified or locked cohort.** The existing origin
seal freezes 61,541 conditional arm/condition scopes across 12,941 trials. Its
historical mapping qualification covers resource inputs and exact-alias candidates.
**Qualified clinical programs remain zero.** The original protocol's phrase
“origin cohort and scope sealed” must be interpreted explicitly as this immutable
candidate universe with retained holds, rather than silently recertifying those
holds as resolved. Without that bounded interpretation, a claim that origin
clinical eligibility is fully qualified would still fail.

## Finite remaining acceptance

1. Retain a versioned closeout/amendment that binds the existing origin/mapping seal,
   reconstruction decision and integrity corrections. Preserve original protocol
   bytes, the fixed January 1, 2025 origin, January 1, 2026 occurrence horizon, and
   April 1, 2026 midnight-UTC proposed ascertainment cutoff. State the permitted
   use as evaluator input preparation and subsequent gated candidate adjudication.
   Strict origin/bulk availability, registry completeness, clinical-ready and
   clinical-locked flags remain false; qualified-program count remains zero.
2. Qualify the delivered April archive's identity, complete member CRC/hash reads,
   dump/schema/date provenance, version/cutoff precision, and evaluator-only
   structural restore/audit. Bind the original file and complete source/receipt
   ancestry and retain stopped-server acceptance, as for January. Delivery alone
   does not establish April 1 midnight coverage. Unknown timezone or later content
   requires an explicit reconstructed-cutoff policy; post-cutoff or
   boundary-straddling public versions must be excluded or held. A new bounded
   April restore contract is needed: the existing endpoint_restore wrapper permits
   only January 2026 and empty cohort SQL.
3. Complete the **input/source ascertainment coverage report**: which January/April
   versions are accessible, which source clocks and fields can establish eligible
   disclosure timing, what each named endpoint additionally requires, and the exact
   missing/partial/unknown coverage. Candidate search counts remain unmeasured/null
   until Science 4 executes searches. Keep the 90-day allowance as a frozen design
   choice with `allowance_qualified=false` unless actual supporting evidence qualifies
   it. A qualified source package does not prove universal reporting completeness,
   a complete lag distribution, or eligibility for no-record negatives.
4. Close an origin-hold disposition inventory and freeze the next-stage review/search
   policy before candidate endpoint inspection: all frozen scopes are accounted for,
   unresolved identity/regimen/population/prior-risk states remain holds, and any
   bounded origin-eligibility review queue is selected reproducibly using origin-only information.
   Outcome-dependent dropping, merging or re-selection is prohibited. A review
   supplement may resolve a hold with source evidence and preserve the parent ID;
   it must retain the original candidate and an auditable disposition history.
   Later event/no-record audit samples may use prespecified candidate-search strata;
   that sampling must not redefine origin membership.
5. Revalidate changed restoration/coverage gates and their source commitments, then
   seal an explicit pass-with-scope-and-limitations record against the four Science 3
   deliverables. January restoration, historical mapping and origin selection already
   have retained acceptance; no repeat large-cohort extraction is needed merely to
   restate these receipts. Existing evidence must still match its commitments.

These checks finish input readiness without requiring manual adjudication of all
61,541 scopes, estimating clinical performance, or pretending that unmeasured
ascertainment is complete. If April source timing cannot support even a bounded
reconstruction, its exact timing/source gap remains an unresolved input gate;
file possession does not waive that gate.

## Where scope qualification belongs

**Origin-only audit:** product identity/formulation; experimental versus comparator,
background or rescue roles; regimen composition; original population/subtype,
biomarker, prior therapy, route and arm phase; and already-known higher-phase/prior
qualifying events are origin eligibility questions. Retaining their source facts,
candidate identities, exclusions and unresolved holds is required now. Resolving
them is required **before that candidate receives a resolved endpoint label or
enters a clinical risk set**, using origin evidence without conditioning on its
future outcome. They cannot be reassigned wholesale to outcome-informed review.

**Science 4 candidate adjudication:** compare each frozen origin scope with proposed
follow-up scope, resolve cross-trial/arm regimen and population equivalence, establish
occurrence and first-public intervals, adjudicate endpoint-specific events and
no-record searches, and detect late-disclosed pre-origin events. A later disclosure
of an earlier event changes the candidate's at-risk disposition; it is not an
in-window advancement. Origin-risk review can be an explicitly blinded first pass
of that next-stage procedure, before its reviewer sees candidate outcomes. If it
remains unresolved, the candidate remains unresolved/ineligible for the relevant
analysis. No label may bypass the origin hold just because a future study looks
like a match. Dependence-aware qualified counts and power follow these decisions.

This allocation follows Item 1's positive-label requirement for qualified origin
risk/program scope and Item 4's separate outcome-adjudication acceptance. The
current `origin-route-decision.json` authorizes technical restore only and explicitly
forbids endpoint cohort queries; Science 4 needs its own frozen authorization/gates.

## Existing machinery and reuse limits

| Machinery | Useful capability | Required boundary before next-stage use |
|---|---|---|
| `tools/science/origin_programs.py` | Frozen origin scopes, complete eligibility/design text, source offsets/hashes, historical alias candidates, prior-phase alerts and dependence keys | Holds remain conditional; resource annotation and verbatim keys do not prove clinical equivalence |
| `tools/science/historical_inputs.py::verify_manifest`; `tools/science/endpoint_restore.py::verify_origin_closure` | Complete file/receipt/schema ancestry and exact manifest binding | Read-only source gate; neither establishes outcomes or clinical scope |
| `tools/feasibility/restore_intermediate_aact.py` and Item 3 terminal acceptance script | Archive restoration, technical schema/identifier/constraint/index audits and stopped-server evidence | Use a new April-specific wrapper/plan with empty cohort query and cutoff qualification; do not loosen the January wrapper silently |
| `tools/feasibility/registry_extract.py` | Source JSON frame/query and arm-child relational checks | Its executor is pinned to v0.4/five older snapshots; old follow-up filters and projection omit full eligibility and are not a qualified exhaustive 2025–2026 search. Version a new source/search contract |
| `tools/feasibility/registry_scope.py` | Exact ontology alias collision checks, context and prior-risk alert patterns | Its v0.5 runner consumes the old cohort/labels and its context helper reports missing eligibility. Do not run it on this new universe or treat it as a current population adjudicator |
| `tools/feasibility/program_outcomes.py` | Partial-date bounds, program/arm/source bookkeeping and scope checks | `validate_bundle` hardcodes January 2023–January 2025 and a development-only mapping contract. A new 2025 endpoint version is required; no relaxation or reuse of old labels |
| `tools/science/qualification.py::validate_outcome` | Separate endpoints, chronology, source proofs, scope, negative ascertainment and unresolved-state guards | A useful runtime subset, not full implementation of Item 1's proposed regimen/estimand/precision/adjudication field contract. Instantiate and test the additional endpoint-specific rules before labels |
| `tools/feasibility/render_outcome_review.py` | Human-readable evidence cards | Current renderer hardcodes 24 older representatives and dates; presentation reuse only after a new contract, never a new adjudication source |

Read against `planning/protocols/science-prerequisites-v0.1.json`, Item 1
`endpoint-fields.json`, Item 3 `origin-selection-notes.md`,
`origin-route-decision.json`, `origin-integrity-correction.json`,
`partial-closeout.json`, `ascertainment-access-report.md`, and mapping-r1
`origin-freeze.json`. The historical missing-April statements in those sealed
reports remain historical evidence; this review does not overwrite them or assume
the newly delivered archive's unperformed qualification has passed.
