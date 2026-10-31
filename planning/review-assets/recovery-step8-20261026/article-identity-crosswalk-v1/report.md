# Six-article identity crosswalk: one confirmed prior exposure

This is evaluation-only exposure metadata, not an agent-visible source, a human
assessment or scientific validation. The prospective method was frozen before
packet metadata inspection; exposure v4 and every prior artifact remain unchanged.

## Result and disposition

PMID **31019502** is already present in the prior exposed **IL23A / psoriasis**
packet. It is therefore a confirmed exposed article family for the current R08
source-only preparation (the selected BTK/psoriasis context shares this article).
The finding establishes shared article identity and previous agent-evidence packet
presence only. It does not establish an identical passage, actual prior model
consumption, or the content of any previous answer. Retain the overlap as a failed freshness/exclusion
criterion; do not replace the selected article or context, repair the old report,
or claim either selected context is fresh. This does not say its biological
content is wrong or forbid disclosed development-only source preparation.

PMIDs **40571861, 32697884, 35784333, 15059373 and 22284131** have no exact PMID
match in the inspected metadata. That negative result does not establish freshness.

The positive match is observation index1128 (zero-based) in
`data/derived/science2-fresh-20261018T170501Z/il23a-efo_0000676-inhibit-antibody/evidence.json`:

- Target ENSG00000110944; indication EFO_0000676.
- Observation `ot25:europepmc:34deafcb16a7d2da3798affc3de3d38f3e82c86b`.
- Identity pointer `/observations/1128/source_metrics/literature/0` = `31019502`.
- Declared original source `raw-6119b566a07792ecf1ea7d90`, row group0 / physical row46915.
- Original-source and receipt anchors are copied as declared metadata in
  `overlap-anchor.json`; those raw ancestors were not opened or newly verified.

## Verified scope

All **57** snapshot descriptors matched the frozen exposure-v4 hashes. Their
**58** explicitly referenced, access-approved agent-evidence packets matched the
hashes in those descriptors. No packet was unavailable, excluded or over the
64MiB bound. Identity-only projection covered **102,170 observation occurrences**;
**63,873** contained a nonempty literature field. Exactly one observation occurrence
matched a fixed PMID. Repeated snapshot occurrences are not independent studies.

The projection selects explicit article/literature, cohort/study, source record,
locator and target/indication identities. Unselected JSON string values are
lexically skipped without decoding; statements, mined source text, outcomes,
clinical fields, scores and conclusions are not extracted or inspected. A fixture
checked that excluded text containing escaped quotes/brackets is omitted. Packet
bytes are read solely for hashing and structural projection. Total execution was
45.156seconds; this is the crosswalk time, not full source-review time.

## Unresolved coverage

This inventory is bounded to the 57 descriptors already pinned by v4 and their
immediate eligible packets. It does not follow arbitrary ancestors or inspect
candidate outputs, gold answers, human reviews, benchmark labels or protected
normalized outcomes. It does not cover an unlisted snapshot, a missing literature
identity, an article represented only by an unjoined PMC/DOI alias, or an unlinked
cohort. `pmcIds` key presence was observed but its values were not decoded or joined;
there is no supplied complete PMIDâ€“PMCâ€“GEO alias crosswalk. Cohort identifiers in
the matched observation are absent. The exact published Virtual Biotech analytic
roster and complete GEO/article crosswalk remain unresolved.

All six fixed article selections and zero-match outcomes remain retained. The
positive overlap must be carried into the R08 source preparation disposition;
no freshness qualification, model generation or independent scientific acceptance
is activated. This crosswalk does not change the original twenty exposed
hypotheses/eighteen target inventory.

## Retained evidence

`method.json` fixes the six IDs, 57 descriptor pins, roles and bounds.
`crosswalk.py` implements structural identity projection. `crosswalk-report.json`
retains descriptor/packet proofs, identity match, coverage and field-key coverage.
`overlap-anchor.json` gives the exact positive-match proof chain through the
verified descriptor/packet and explicitly unverified raw-source declaration.
`manifest.json` hashes these artifacts. No network, new acquisition or model call.
