# January 2025 origin: reconstructed-information method decision

The fixed origin remains **2025-01-01T00:00:00Z**. The January 1 AACT dump
was created at 05:22:15 in an unspecified timezone. This does not prove the bulk
artifact was public before the origin. Its original archive receipt also leaves
publisher checksum and exact public availability unverified.

There is a defensible, explicitly exploratory reconstruction route for copied
public registry fields. NLM's September 25, 2017 explanation distinguishes
submission from public posting: the Last Update Posted date describes when
the latest changed study information became publicly accessible. The AACT
maintainer describes its process as downloading the registry daily and reorganizing
the registry into connected tables. These support the inference that raw protocol
fields copied from a record whose first and last public posting intervals end
before the fixed origin are old public information, even if the database copy and
our computation occur later. This is an inference from documented field semantics
and provenance; it is not independent verification of each historical source version.

Primary sources consulted on October 18, 2026:

- [NLM, ClinicalTrials.gov: More Changes to Improve Usability (2017)](https://www.nlm.nih.gov/pubs/techbull/so17/so17_clinicaltrials.html), especially Changes to Record Date Fields.
- [AACT maintainer description](https://aact.ctti-clinicaltrials.org/landing), especially daily downloads and relational reorganization.
- [CTTI historical description (2016)](https://ctti-clinicaltrials.org/type/news/updated-aact-database-now-available-on-the-ctti-website-3/), which identifies publicly available downloadable ClinicalTrials.gov data as the input to AACT.

The extraction admits study phase/status, original start precision and type, titles,
conditions, intervention/alias and experimental-arm links, sponsors, summary,
eligibility and design records from this one snapshot. Source IDs and AACT date
representations are provenance, not additional public biological evidence.
`calculated_values`, later follow-up tables, outcomes/results tables, contemporary
drug annotations and any endpoint labels are excluded. Source `start_date` is
retained but never refines a partial `start_month_year` value. Normalized dependence
keys and verbatim prior-stage alerts are new deterministic computations on these
old strings; they do not assert target identity or clinical population equivalence.

Both first and last public-posted dates must be present and earlier than January 1.
Date-only source values represent a full UTC day interval; no exact posting time is
invented. The restored technical audit reports both maxima as **2024-12-27**, so
their conservative full-day upper bounds are strictly before the origin. Actual
start eligibility also uses the whole original day/month/year interval, never an
AACT-imputed first day. Unknown precision, mixed phases and unresolved roles are held.

This route supports **reconstructed exploratory information eligibility** after the
per-row posting checks pass. It does **not** establish strict bulk-dataset
published-before-origin eligibility, original version byte identity, registry
completeness at the exact origin, or a locked clinical evaluation set. The January 1
copy may omit pre-origin versions of records updated after the origin, and an
AACT/registry refresh lag can omit recent records. A complete historical-version
inventory or independently timestamped exact-origin source package would be needed
to remove that limitation. First/last posting dates are record-level clocks; they
cannot prove undated AACT-enriched annotations existed then. Such annotations must
remain outside the predictor route.

Decision: proceed with the immutable origin-only candidate universe and historical
mapping revision as **qualified only for this explicitly reconstructed exploratory
route**. Keep `origin_date_qualified=false`, `clinical_ready=false` and complete/locked
cohort claims false in the strict seal. Any endpoint access requires the root's
explicitly versioned route decision and the mapping revision first. No origin shift,
download-time inference, post-origin fallback or outcome-dependent re-selection is allowed.
