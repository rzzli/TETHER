# April 2026 AACT temporal qualification: bounded peer review

Reviewed 2026-10-18. This is evaluator-side methodological review, not an outcome query or scientific-label adjudication. No endpoint records, individual trial histories, database services or biological outcomes were opened. The April archive's actual date/hash/CRC qualification belongs to the separate archive audit; this note does not assert those checks have passed.

## Recommendation

An archive requested as **April 1, 2026** may be restored and structurally verified under the existing sealed-origin, pinned-file, empty-cohort route. Its dump date, ZIP timestamps and present-day possession do **not** establish public availability at **2026-04-01T00:00:00Z**. A record version with a date-only public posting of April 1 must remain **cutoff-uncertain/held** unless separate eligible evidence establishes its public availability by that exact cutoff.

The event horizon remains **2026-01-01T00:00:00Z**. April is for observing sufficiently early publications of earlier events, not for counting new events after the horizon. Exactly 90 days separates the horizon and proposed ascertainment cutoff; that arithmetic does not establish reporting completeness, justified negatives, or clinical readiness.

## Official source semantics

NLM distinguishes update submission from public posting, and defines the latter by public accessibility of changed record information. Submission can precede public access. AACT describes a daily download and relational reorganization of registry content; this supports copied-source provenance, but supplies neither an exact refresh/publication time nor complete historical version reconstruction. These sources justify a **conditional reconstruction method**, not a verified source timezone or exact-origin completeness. [NLM posting-date explanation](https://www.nlm.nih.gov/pubs/techbull/so17/so17_clinicaltrials.html), [AACT maintainer description](https://aact.ctti-clinicaltrials.org/landing).

The modern NLM glossary and API data-structure landing pages exposed only a JavaScript glossary shell through the available text tool. Their detailed field definitions were not treated as read. No source establishing a unique timezone for these public-posting DATE fields was verified during this review.

## Fail-closed date rules proposed before labels

The frozen protocol already specifies a midnight UTC cutoff. Preserve that timestamp and explicitly amend the reconstruction rule before new endpoint-label access; do not relabel the cutoff as end-of-day or extend the event window. Keep the original UTC-calendar interpretation as a named sensitivity analysis rather than silently claiming its timezone is documented.

For a date-only public-posting value **D**, a conservative civil-offset envelope can be used provided its assumptions are stated:

1. The value is the civil calendar date of **public posting**, not submission, verification, occurrence, database computation, estimate or download.
2. Its source timezone is unspecified but assumed to use a conventional UTC offset in **[-12 hours, +14 hours]**.
3. The latest possible public-posting bound is **(D + one calendar day) at 00:00 UTC + 12 hours**. The earliest is **D at 00:00 UTC - 14 hours**. These are analytic bounds over possible offsets, not assertions about NLM's actual timezone.
4. Admit a reconstructed fact only when its complete availability upper bound is no later than the fixed cutoff. Keep strict public-timestamp qualification false because the assumptions and historical-version limitations remain.

At the April 1 midnight UTC cutoff:

| Public-posting information | Conservative disposition | Reason |
|---|---|---|
| Exact independently verified `2026-03-31T23:59:00Z` | May qualify temporally | Timestamp bound precedes cutoff; other source/scope checks still apply |
| Date-only March 30 | May qualify under declared reconstruction | Latest bound is March 31 at 12:00 UTC |
| Date-only March 31 | Hold as boundary-uncertain | Latest bound is April 1 at 12:00 UTC |
| Date-only April 1 | Hold | Date spans possible public times after cutoff under either offset-envelope or UTC-calendar interpretation |
| April 1 dump creation with unspecified timezone | Technical archive evidence only | A computation timestamp is not the record's public-availability proof |
| March 30 submission, April 1 public posting | Hold latest version | Submission cannot backdate public availability |
| February public posting of an eligible December event | Candidate earlier-event evidence | Occurrence and availability must independently qualify; no clinical-success inference from a trial start |
| Public posting before cutoff of a March 2026 event | Outside fixed event horizon | Availability cannot make a post-horizon event eligible |
| Missing, malformed, estimated or semantically unresolved posting information | Hold unless alternative evidence qualifies | No invented posting time or fallback to event/submission/download dates |

The narrower UTC-calendar sensitivity assigns a date the interval `[D00:00Z, (D+1)00:00Z)`. It would admit March 31 at this cutoff. That is a transparent assumption-dependent sensitivity, not an observed NLM timestamp. Reporting its additional admitted/held source-version counts can expose the ambiguity without selecting the rule based on outcomes. The conservative envelope must not be described as proving the actual publication time either.

## Versions, missingness and unchanged origin membership

- Apply the rule to the public clock of the **version supplying the used fact**. An early first-posted date does not date later changes. Results-specific clocks need qualification when results content is used; protocol updates are not automatically timestamps for all results versions.
- If the latest April dump version was posted too late or has a boundary-uncertain posting date, do not backdate its values using an old trial start, first registration or submission. Recover an independently eligible prior version, use separately pinned timely evidence for the particular fact, or keep that fact unresolved.
- A newer version may contain unchanged older values, but unchanged identity alone does not prove those values' earlier availability. Do not infer earlier field history from a later full record.
- Boundary holds apply to follow-up evidence, **not origin cohort membership**. Preserve all 61,541 sealed scopes. Do not remove difficult follow-up cases, change the prediction population, or transform missing updates into negatives.
- The existing origin report's December 27, 2024 posting maxima lie safely before January 1 under both interpretations. This rule does not require outcome-driven origin reselection or changing the origin timestamp.
- An old last-update date is not proof of follow-up through the cutoff; it can indicate an unchanged or stale registry record. Daily archive coverage is not evidence that all clinically relevant events were reported. No-recorded-transition remains distinct from a verified non-event, censoring or failure.

## Bounded Item 3 disposition and later activation

Retain separate fields for requested snapshot date, observed dump creation, timezone precision, technical restoration, source-version availability disposition, historical reconstruction assumptions and ascertainment coverage. Technical success may coexist with unqualified exact public availability and incomplete ascertainment. Appropriate pending claims remain `clinical_activation=false`, `clinical_locked=false`, `strict_dataset_availability_qualified=false`, `ascertainment_completeness_qualified=false` and `reporting_allowance_qualified=false`.

Item 3 can retain an explicit finite source-coverage disposition and the temporal amendment; this review does not authorize Item 4 labels, negative ascertainment, statistical fitting or any new clinical claim. Root must version the actual route/coverage decision. Future outcome adjudication must keep event dates, source-publication/availability dates and latest observation distinct.

## Review boundaries and validation

The review used the frozen scientific protocol, existing reconstructed-origin availability decision and small retained origin reports. Complete origin proof validation was previously retained; this task did not rehash multi-gigabyte ancestors. Official sources were checked on October 18, 2026. No claim is made that current documentation was itself a historical predictor.

The companion JSON records assumptions, boundary examples and unresolved qualifications. Its date arithmetic is validated independently of any clinical data. No code, original planning freeze, data archive, receipt, trial record or database state was changed.

Validation passed: the JSON parsed; all four civil-offset interval examples recomputed exactly; January 1 to April 1, 2026 is exactly 90 days; March 31 and April 1 fail the conservative upper-bound cutoff; the existing December 27 origin maximum remains before origin. Three small frozen input hashes are retained in the JSON. These checks establish arithmetic and provenance consistency only.
