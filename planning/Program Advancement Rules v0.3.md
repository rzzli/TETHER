---
title: Program Advancement Rules v0.3
date: 2026-10-17
status: frozen-development-rules-applied
tags: [TETHER, clinical-evaluation, protocol, feasibility]
---

# Program advancement rules v0.3

The program-equivalence and advancement rules requested after [[Phase 3 Linkage Follow-up]] are frozen and evaluated on two authored fact records, P01 and P24. All 24 development representatives have accounting/disposition records; the other 22 did not receive a complete transition search or evaluator run. **P01 has an admissible narrowed scope link; P24 remains unresolved. No primary event, training label or new cohort member is qualified by this application.**

Planning update: [[Updated Project Plan 2026-10-17]] reconciles the subsequent Claude review. This strict development protocol remains unchanged; registry-scale label sizing now precedes further work on the same 15-case qualification queue.

This is an explicit development-protocol amendment, informed by already exposed cases. It is not preregistration, independent scientific validation or evidence that these design choices outperform alternatives. The former protocols and their zero-label outputs remain sealed.

## Endpoint decision

The primary endpoint is **first receipt of the qualifying experimental regimen by a participant in the next numerical phase**, after January 1, 2023 and supported by eligible information available by January 1, 2025. The allowed phase edges are 1→2 and 2→3.

The v0.2 phrase “first participant treated” did not resolve randomized-arm attribution. Version 0.3 conservatively requires experimental-regimen receipt. A report that the first trial participant was dosed, without identifying the regimen/arm, remains a separate descriptive trial-initiation observation. It cannot silently become the primary endpoint. This clarification can reduce event observability; it is a methodological choice rather than a newly discovered clinical fact.

Enrollment is not receipt of treatment. A registry actual-start date can support a conditional lower bound, but cannot supply an experimental-dosing upper bound. Exact dosing dates or supported intervals are permitted; the complete interval must fall after origin and by endpoint. First-public dates remain unknown unless supported. A retained page with later modifications and no historical-content assurance is conditional evidence.

## Identity and coverage rules

| Dimension | Permitted relation | Hold or separate |
| --- | --- | --- |
| Drug/product | Same product or documented source alias, including ADC payload or combination identity | Shared target alone is insufficient; changed product/payload is non-equivalent |
| Regimen | Same active composition, route and schedule | Added/removed active partner or changed route/schedule requires a separate origin-qualified unit |
| Dose | Same dose or selection from explicitly documented origin options | Outside-option dose without origin-range support remains unresolved |
| Population | Same core indication/line/genotype, or a nested stratum explicitly represented at origin | Outcome-derived subgroups, new indications/genotypes or unrepresented expansion cannot label the original unit |
| Coverage | Retain the selected dose and narrower population explicitly | Advancement does not imply every original arm or population member advanced |
| Stage | Origin arm-specific active Phase 1 or 2 | Mixed-phase labels alone, 2a→2b and skipped phases do not establish the primary edge |
| Risk set | Active experimental arm and no already-realized qualifying advancement under a documented dated search | Unknown activity/prior advancement stays unresolved; prior efficacy or completion alone is not advancement |

An external canonical drug or ontology ID is useful but is not itself a prerequisite for source-qualified clinical product identity. A retained explicit alias can support that relation. Historical target/mechanism/indication crosswalks remain separate requirements for historical agent inputs. This avoids conflating an incomplete identifier catalog with a missing clinical record.

Additional eligibility restrictions must be retained and reviewed. A nested stratum relation does not claim that the two complete eligibility sets are identical. Population or dose options cannot be invented retrospectively to make a favorable transition fit.

## Shared events and dependence

Use one canonical event identity for the next trial, relevant experimental arm/regimen and event type, linking its reports and predecessor candidates. Multiple papers or predecessor NCT IDs cannot multiply the event count. Distinct experimental arms/products within a platform require separate event identities.

Predecessors sharing an event receive a shared split-dependency component. Shared drug, regimen and evidence across other events must also be tracked before splitting or statistical analysis. Unique IDs do not establish independence. Conflicting or differing event claims are retained as variants requiring reconciliation; the evaluator withholds the unique qualified count while unresolved.

The existing P01/P24 lead is canonically identified as **trial initiation**, because the first dosed arm is unknown. It is not relabeled as first experimental dosing. P24's shared report does not establish equivalent origin population or stage.

## Applied development results

| Item | Result |
| --- | --- |
| Frozen representatives accounted for | 24 |
| Previously excluded origin cases retained | 9 |
| Remaining cases without a qualifying next-phase lead in retained evidence | 13 |
| Cases receiving detailed transition-rule application | P01 and P24 |
| Retained candidate events classified | 17; one advancement lead, 16 separate descriptive events |
| Shared trial-initiation event groups | 1 |
| Qualified unique primary events | 0 |
| New training labels / censoring dates / cohort members | 0 / 0 / 0 |

**P01:** a documented source alias, origin second-line ES-SCLC strata and the 12 mg/kg IV-every-three-weeks option support an admissible link with narrower coverage. It fails the stricter same-population-and-dose sensitivity view. Primary qualification remains blocked by experimental-arm dosing attribution, conditional timing/content evidence, and unresolved origin arm activity/prior-advancement ascertainment. The earlier provisional study-level screen has not been promoted into an arm-level proof.

**P24:** shared drug lineage supports an alias relation, but exact origin SCLC cohort, regimen/dose and active numerical stage remain unresolved. The same Phase 3 announcement is linked as shared development evidence, with no second independent event or qualified predecessor transition.

The other 13 non-excluded cases require origin qualification and dated next-phase ascertainment. Their efficacy, safety, completion or business-discontinuation reports are not substituted for advancement. No located transition is not a failure label or a censoring date.

## Implementation and verification

Frozen package: `data/benchmark/cohorts/advancement-rules-20261017T152107Z/`.

It contains the v0.3 protocol and pre-application hash, authored source-bound facts, all 24 case applications, event classifications, shared-event accounting, readable review, decision and retained test results. Public provenance is `data/manifests/public/2026-10-17-advancement-rules.json`; the current pointer is `data/derived/active-advancement-rules.json`.

Evaluator utilities are `tools/feasibility/advancement_rules.py`, `apply_advancement_policy.py` and `verify_advancement_policy.py`. They leave the runtime contracts, numerical prediction features and canonical T6 outputs unchanged. Verification checks sealed bytes, both parent chains, the frozen protocol, source-pointer values, deterministic application and complete case accounting. Authored scope judgments remain review inputs, not automatically proven biological truth.

Ten new rule regressions include a fully supported synthetic positive, permissible narrowing, changed product/partner/population, unknown origin stage/risk, enrollment versus dosing, conditional/late evidence, date contradictions, shared-event counting and conflicting claims. Synthetic positives are explicitly fictional and do not enter the real cohort.

Completion checks passed: **36 relevant tests**, including the ten new regressions; source-inclusive replay of both parent chains and the new application; all 24 cases accounted for. The 21-file evidence manifest is `5a676737352589d0e294691aa724b5f3d938276154aa961e2145f5ac4d9d5ded`; frozen protocol SHA-256 is `ec460cc1ca298a88c2830dfb4b6fadad164ad1c2b61d7aea1eb374bda46d2490`. The full runtime suite was not rerun because runtime code was unchanged.

## Next bounded work

Resolve **origin arm activity, numerical stage and prior advancement** for the 15 non-excluded representatives under this frozen definition. Start with P01's candidate 12 mg/kg/second-line unit, then the mixed-phase/platform cases. Retain exclusions and unknowns, the P03 regimen-link conflict and the P21 dose discrepancy.

This pass should produce an origin-qualified risk register and a precise list of missing dated evidence. Seek experimental-arm dosing attribution and historical-content assurance for P01 where available. Only after the program/risk/follow-up route works should an origin-only expansion frame be frozen and enumerated; these exposed cases must remain outside an untouched-test claim.

No database restart, new download, model call or provider spending was needed for this rules step. Clinical probabilities remain null. The original endpoint window and stopped monitoring remain unchanged.
