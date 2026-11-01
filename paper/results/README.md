# P05 paper results: deterministic technical source validation

These post-result presentation artifacts consume pinned analyzed metadata only.
The literal assembler reports complete verified source facts and passes 80% measurement completion in 12/12 selected native units. Always-abstain completes 0/12 and emits no fact assertions. Forty of 48 native measurement slots are answerable; eight are native nulls. These twelve units are not twelve independent studies.

Constructed invalid admissions are FULL 0/10, WITHOUT_WRAPPER 2/10 and WIRE_ONLY 7/10. All three reject 0/4 technically valid controls. The fourteen exposed generic JSON/core controls are separate from native cases and do not estimate natural corruption prevalence. Technical fidelity does not establish biological, model or clinical superiority. No new endpoint, interval, significance test, power calculation or reweighting is introduced.

FULL requires all frozen retention/provenance, P05 eligibility/inventory, base source-replay and exact-report checks. WITHOUT_WRAPPER omits only the P05 mapping/eligibility/inventory wrapper (G2), retaining the actual base guards. WIRE_ONLY requires retention/hash anchoring plus output schema/bounds and does not qualify factual source reporting. These weaker policies are diagnostic projections of retained guard outcomes, not usable clinical methods. Measurement coverage averages matched answerable-component fractions equally across groups; native nulls are excluded, so 40/48 source availability is distinct from 100% literal reporting coverage.

## Files and use

`tables/` contains CSV plus readable Markdown for all 24 native arm returns, 96 family-accounting rows, 12 source missingness rows, 42 constructed policy verdicts, seven paired comparisons/all 63 verdict cells, resource phases, complete 38-output and 90-decision accounting. CSV `unknown` means unavailable; it never substitutes zero. Undefined zero-answerable-group coverage stays unavailable. Markdown rounds only displayed floats to six significant digits; CSV retains Python round-trip numeric spelling.

`figures/` contains three native-vector PDF/SVG figures, 160 dpi PNG previews, exact machine-readable figure data and separate captions. Figures require visual review of the current previews; PDF page counts/text and PNG dimensions are checked by the builder. The artifact manifest maps every generated output to its exact sources, columns/rows and hash. The manifest itself is excluded from its recursive output hashes.

* Native tables: [arm results](tables/native_case_results.md), [fact accounting](tables/native_fact_accounting.md), [missingness](tables/native_missingness.md).
* Constructed controls: [all verdicts/stages](tables/constructed_control_verdicts.md), [policy totals](tables/constructed_policy_summary.md), [paired discordance](tables/paired_discordance.md).
* Resources: [phases](tables/resource_phases.md), [shared generation/scoring by case](tables/native_operation_resources.md).
* Complete accounting: [38 outputs](tables/output_schedule.md), [90 decisions](tables/decision_schedule.md), [all paired verdict cells](tables/paired_verdict_cells.md).
* Vector figures: [source flow](figures/figure1-flow.pdf), [native availability](figures/figure2-availability.pdf), [constructed admissions](figures/figure3-controls.pdf). Caption files sit beside the figures.

## Resource interpretation

Producer total includes all generation/guard/source-verification/retention work. The native generation row deduplicates the shared literal/abstain pair once per case; native scoring sums 24 measured calls. The 197.812 s source wrapper is a subphase within the 203.828 s producer total, not an extra cost to add to it. The independent audit is separately 7.125 s. Policy verdict projections are not independent end-to-end runtime runs. Phase-specific memory/CPU, physical I/O, partial failed hash bytes and platform costs remain unknown where unmeasured. Overall process-lifetime peak is distinct from sampled RSS and cannot be attributed to an arm.

## Rebuild

Use the already available bundled Python runtime (reportlab/pypdf/Pillow), without installing packages. Run the PDF skill marker exactly once immediately before the first PDF generation for the authoring operation; it is deliberately outside this rebuild script. Then run:

```powershell
& 'C:/Users/zzric/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' tools/science/build_p05_paper_assets.py --build --analysis data/derived/preprint-p05-analysis-20261101T092110Z/analysis.json --analysis-sha256 ee9f02ea3c3692bbd8b7d63d2d2cd545cfd769ccee9ee7454b4ed00c7ac87312 --ledger data/derived/preprint-p05-experiment-20261101T091345Z/ledger.json --ledger-sha256 b2a9727ca9ce89865b80ffe80b21a325ea6d91d8844247740ac2c2ecc9a4faa0 --audit planning/review-assets/preprint-p05-20261031/EXPERIMENT-AUDIT-v1.json --audit-sha256 f10f15959f8497821115f65268808c98ae345079c7361722390a479b15506922
```

`--check-inputs` performs metadata/hash checks without writing or generating PDFs. Source audit status and the analysis seal are checked, and the current frozen analyzer SHA must match. The original ledger retains its pre-audit `COMPLETED_PENDING_INDEPENDENT_AUDIT` status; the separately pinned PASS source-inclusive audit establishes the later verification state without rewriting the ledger.

PDF invariant mode is enabled, with ReportLab standard Helvetica/Helvetica-Bold fonts and no external font-file path. Rebuilding under the same local Python/ReportLab/Poppler/font environment is expected to repeat payload bytes; cross-platform font substitution, SVG text rendering and dependency changes can differ. For a fresh-directory repeat, add `--output-root tmp/pdfs/p05-paper-rebuild` (an empty workspace directory). Package-relative manifest paths remain the logical `paper/results/` paths. Compare all CSV/Markdown/SVG/PDF/PNG payload hashes; manual visual review remains separate.

This rendering code was written after results were available. It only formats frozen results and records its own code hash; it does not modify source inputs, READY, the experiment, analyzer, original records or evaluator facts. No models, network, new downloads, spending or monitors are used. Source/expected-reference/human/protected inputs are forbidden. Scientific validation and independent-study qualification remain not_established. Independent numeric review and author/root visual review remain separate acceptance evidence.
