# Scientific qualification decisions — Item 1

The seven-item execution uses agent specialists as authorized. Agent provenance,
procedural separation and source-based adjudication are retained. Agent consensus
is not presented as external validation, biological efficacy or human expert review.
No human-only prerequisite prevents source-grounded development work.

`planning/protocols/science-prerequisites-v0.1.json` is the authoritative ordered
qualification register. The adjacent endpoint/reference/gate notes are retained
specialist proposals and detailed field specifications. This decision adopts their
endpoint distinctions, uncertainty handling, version crosswalk and review procedure.
`tools/science/qualification.py` implements the common executable boundary contracts;
it does not claim that every clinical field or method assumption is already populated
or scientifically validated. Downstream data builders must retain the detailed
endpoint/reference fields applicable to their products.

Canonical endpoint identifiers are `registry_next_phase_actual_start`,
`verified_experimental_dosing`, and `clinical_success`. The register explicitly maps
the endpoint proposal's names to these IDs. Registry enrollment cannot substitute
for dosing or efficacy; the original H1 endpoint remains clinical success.

The candidate occurrence window is `(2025-01-01T00:00:00Z, 2026-01-01T00:00:00Z]`.
Ascertainment through April 1, 2026 is a proposed 90-calendar-day reporting allowance,
not established completeness. Source timestamps, date intervals and publication
availability remain separately qualified. Existing endpoint archives must not be
queried for candidate outcomes before origin selection is sealed.

Binary negatives require endpoint-specific ascertainment. Unknown, censored and
competing-event cases retain null labels. Clinical failure needs explicit failure
of the qualified prespecified objective, rather than absence of advancement or a
commercial stop. Partial dates that cross a boundary remain unresolved.

Clinical numeric features initially use reproducible deterministic derivations with
complete eligible input lineage. Each contributing model must predate its feature
row's origin. September 2024 Qwen weights do not qualify a 2023-origin LLM-derived
feature. Computation performed now on eligible older information is allowed. Both
training and calibration labels must be publicly available before test origin.

The causal-genetics branch is optional. Input requirements are chosen per method;
missing per-variant N/EAF or study LD cannot be declared universally fatal to every
possible calculation. Conversely, no method may fill required unknown quantities
or reinterpret transcript regulation as a protein/drug intervention. Source trust,
numeric reproducibility, causal assumptions and historical eligibility are distinct.

No clinical activation, biological accuracy, scorer training or locked evaluation
is established by passing the Item 1 contract tests. Later stage reports must
distinguish completed operational work, explicit conditional deferrals and missing
file/access prerequisites. The earlier sealed protocols remain untouched.
