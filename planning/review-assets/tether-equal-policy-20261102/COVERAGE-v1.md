# Equal-policy coverage ledger

Status: contract frozen before scored comparisons; implementation/corpus verification pending. This is not a passing coverage report. Reference scope is canonical v2 T1/T6 admission, source-inclusive sealed verification and inspection, with distinct catalog1/schema2 variants.

| Obligation | Required comparison surface | Implementation | Oracle coverage |
|---|---|---|---|
| EP-WIRE-01 | Native JSON, typed contracts and normalization; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-CASE-01 | Supported cases and hypothesis identity; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-PROGRAM-01 | Program context and T1 eligibility; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-TIME-01 | Information availability without invented historical dates; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-DAG-01 | Complete structural lineage and role validation; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-DAG-02 | Ancestral temporal eligibility; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-SOURCE-01 | Source bytes, transport receipts and proof completeness; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-PACKET-01 | Artifact inventory and normalized packet integrity; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-OBS-01 | Scientific record validity, lineage and publication; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-SCOPE-01 | Hypothesis/program capabilities and contextual visibility; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-FEATURE-01 | Deterministic dependency-aware feature reconstruction; verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-SCORER-01 | Scorer predispatch validity and chronology; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-SCORER-02 | Scoring applicability, contributions and abstention; verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-POLICY-01 | Schema2 policy and original catalog integrity; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-POLICY-02 | Exact use/frame/grant and all supplied inventory authorization; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-POLICY-03 | All-node raw availability and receipt consistency; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-POLICY-04 | Copied controls, immutable receipts and actual engine binding; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-EXEC-01 | Budget and effective configuration; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-EXEC-02 | Backend request, bounded retrieval and local response provenance; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-EXEC-03 | Selections, reviews and immutable source-grounded claims; verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-EXEC-04 | Journal, accounting, category state and termination; verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-VERIFY-01 | Inner receipt byte integrity and external anchor; verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-VERIFY-02 | Semantic source re-admission and final output reconstruction; verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-VERIFY-03 | Outer facade envelope, complete inventory and launcher proof; verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-IO-01 | Path, file-kind, size and stable-read boundary; prepare_run, verify_run, inspect_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-FAIL-01 | Durable failures and inspection-only recovery; inspect_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |
| EP-PROCESS-01 | Success supervision evidence and bounded execution scope; prepare_run, verify_run | Pending independent/reference adapter verification | Pending clause-level cases |

## Coverage rules

- Both positive and negative cases are needed wherever an obligation permits both. For eligibility, accepted-with-exclusion must be distinct from request rejection. For models, valid abstention must be distinct from malformed scorer rejection.
- Report operation × variant × obligation × exposure stratum. Do not aggregate away absent scorer/local-backend/policy/process coverage.
- Keep expected outcome and observed-field projection outside the descriptor. Compare complete features/contributions/accounting where declared; acceptance alone is insufficient.
- `unsupported` and `error` remain coverage failures. They cannot be silently removed from accuracy denominators, recoded as rejections, or called equal-policy completion.
- Report clauses not exercised even when a broad obligation has at least one case. A finite synthetic corpus does not prove all inputs or security under adversarial OS ownership.
- Frozen original source bytes, source receipts, outer inventories, current trusted runtime manifest and caller anchors remain common inputs. Never let one implementation use evaluator answers or stronger trust anchors.
- Preparation performs no selection/scoring. Those oracle cases require native execution bundles checked with verify_run.

## Runtime-only control ledger

| Runtime behavior | Common witness required | Current comparison status |
|---|---|---|
| Immutable admitted/query/ledger/result state | Nested mutation attempts preserve fingerprints | Pending linked witness |
| Fresh reservation/no-clobber | Concurrent owned outputs; one winner; no overwritten originals | Pending linked witness |
| Durable journal | Partial write/failure retains readable prefix and original error | Pending linked witness |
| Request/quote/select/claim ordering | Scripted backend and retained calls/reservations/reviews | Pending linked witness |
| Budget/deadline | Exact bounds and commit-time exhaustion; partial run abstains | Pending linked witness |
| Local transport and unknown/measured usage | Scripted fake opener including timeout/malformed/overquote | Pending linked witness; no live model |
| Process supervision | Exact output cap/overflow, deadline/EOF, interrupted cleanup/reaping | Pending linked Windows witness; Linux unqualified |
| Recovery | Inspect unresolved attempts; zero redispatch | Pending linked witness |
| Atomic Windows publication | Bounded errors5/32/33, same staged bytes, primary error preservation | BG01 evidence exists; link/hash before claiming BG02 reuse |

## Honest scope exclusions

Separate protocols are not dropped validator obligations: v1 receipt semantics, relocated historical archive verification, frozen study-specific experiments, ingestion/download tools and evaluator-only datasets are separate API surfaces. No canonical v2 run obligation may be reclassified as a study protocol merely because it is difficult. Optional scorer, local-backend transcript validation, full lineage, all schema2 grants, outer process records and dossier reconstruction remain in the comparison.

## Freeze gate

Before scored comparisons, retain exact hashes for POLICY-SPEC.md, policy-spec.json, COVERAGE.md, native fixture bytes, descriptors, oracle, implementation modules, trusted runtime manifest and adapter. Record construction/exposure strata and compared observable projections. Update this ledger from actual implementation checks and corpus inventory; do not mark a row complete from code inspection alone. Later amendments require a new revision and preserved earlier records.

The normative archived-replay binding case remains required even if current canonical verification accepts it. A confirmed implementation gap must be reported; it is not fixed by weakening the oracle. Legacy v1 scope controls are labeled unsupported before scoring and reported separately.
