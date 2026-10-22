# Publisher discovery amendment — October 21, 2026

The prospective v0.2 calibration is complete. Sponsor-poster discovery passed;
the full registry-version and co-developer controls did not. The next cohort
remains inactive. Two exact original PDFs were recovered, and the registry
inspection identified an uncollected protocol/SAP lead for an existing trial.

## What changed

The [new policy](protocols/exact-trial-retrieval-calibration-v0.2.json) was frozen,
committed and pushed at `da8d147` before network requests. It preserves the
failed v0.1 unchanged. The two newly tested document identities were an informed
consent and a sponsor-hosted trial-design poster from the previously exposed
source pool. The co-developer mirror test was explicitly response-informed;
there is no untouched holdout or discovery-sensitivity estimate.

`tools/science/source_discovery.py` separates three operations:

- An actual HTML anchor can establish an explicit publisher-to-publisher link.
  A related domain suffix or URL appearing in prose cannot establish that link.
- A frozen publisher, path boundary and report terms can identify a candidate
  for bounded retrieval, even if its search snippet omits the NCT. This does
  not establish document identity or scientific eligibility.
- Original qualification verifies the physical control and receipt, trial and
  source URLs, approved HTTPS hosts, actual body size/signature/hash and the
  expected original commitment. Different bytes require separate review and
  never automatically become a same-content mirror.

Independent adversarial tests reproduced seven forged-source failures before
the qualifier was hardened. All twelve new tests now pass. Full validation
passes **647 tests**; dependency-free validation also passes with57 expected
ingestion skips. Required probes, PowerShell parsing, wheel packaging and the
installed offline demo passed. Independent method and implementation preflight
records bind the exact frozen policy/code under
`data/benchmark/labels/source-retrieval-v02-20261021/`.

## What the fixed controls found

| Control | Observed result | Gate |
|---|---|---|
| Registry consent, NCT05997277 | Exact search result and original `ICF_001.pdf` recovered with frozen SHA. Current API instead lists `ICF_003.pdf` and `Prot_SAP_002.pdf`. | Original identity passes; complete frozen current-listing/version control fails. |
| Sponsor poster, NCT05327530 | Search returned the official EMD Serono congress PDF;4,592,512 bytes matched the frozen original. | Pass for poster discovery/byte identity. This is not a protocol/SAP or results qualification. |
| Co-developer report, NCT05967689 | Corporate request encountered a redirect outside the frozen HTTPS policy. Search returned an investor report, but the unauthenticated route was disabled and its PDF was not fetched. | Fail; no mirror comparison or publisher authentication claimed. |
| Offline wrong-report/source guards | Actual retained ESMO CNS report bytes do not match the WCLC original. Forged URLs/receipts, unbridged suffixes and background mentions are rejected. Matching consent bytes do not qualify a protocol or success rule. | Pass. The replay was offline, not a successful live request. |

Both recovered PDFs total **4,640,682 bytes**. Actual consumption was4 live GET
attempts (corporate, API, two PDFs),3 exactly frozen search queries,0 landing
opens,0 retries and **$0 provider spending**. One separate offline original-byte
replay is explicitly labeled and excluded from network counts. There were no
new-member queries, framework model calls or clinical labels.

The blocked redirect's target was not retained by the existing transport helper.
The reason for rejection is recorded, but the destination cannot be established
from the retained attempt. No hostname, acquisition date or access restriction
has been inferred to fill that gap. The request was not repeated or followed
outside the frozen policy.

## Useful lead and remaining scientific limits

The fresh API projection for NCT05997277 lists a protocol/SAP dated March22,2024,
with a reported upload time of February12,2026, and a newer consent dated
June4,2024, with a reported upload time of April15,2026. Those original files
have **not been downloaded or reviewed**. A current registry listing and its
date fields do not independently prove historical availability, version
authenticity before analysis, a prespecified success rule or clinical outcomes.
The newly listed files were not substituted into the frozen control.

The old consent date remains ambiguous in its original representation. Poster
content, patient responses, a report's primary endpoint or agreement among AI
reviewers cannot replace an authentic decision rule. The inherited population
and program-scope conflicts remain held. All old36 and later36 endpoint-label
artifacts remain byte-identical; no probabilities or numerical features were added.

## Decision and next work

The [retained gate amendment](protocols/source-readiness-retrieval-gate-v0.2.json)
keeps the original source-readiness study inactive. G3 origin closure is
unperformed and next12 membership remains null/unsealed. Successful engineering
controls alone cannot silently activate that study.

The next bounded action should address **registry version transitions and
existing-trial protocol availability**: freeze a current-reference retrieval
request for the newly listed protocol/SAP, preserve its original bytes and
receipt, and assess authenticity, analysis/version linkage and historical
availability separately. That review can test whether the scientific bottleneck
is tractable without selecting or expanding the cohort. Separately, improve
blocked-redirect provenance and prospectively authenticate any co-developer
route before fetching from it. Preserve both failed calibration versions; do
not rewrite queries, swap controls or call a newer file the missing old version.

The phase report, independent acceptance, hosted validation and final parent
hash checks are retained in `planning/review-assets/source-retrieval-v02-20261021/`.
Execution inputs/code and original query representations remain evaluator-only;
the E: backup verifies every archived entry and Git history. This completes the
amendment/calibration assessment, not clinical qualification or the broader
project. No new account, paid access or user file was required.
