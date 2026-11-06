# SC04 scientific figures

The renderer presents numbers from an externally anchored, accepted analysis. It does not rerun models, select cases, score predictions, fit a model, or calculate new confidence intervals. The current qualification uses two invented questions and is **not a benchmark result**.

## Retained outputs

- Figure helper: `render_analysis_figures.py` in this directory.
- Current controls: `figure-controls-attempt05/QUALIFICATION.json` (23 passed).
- Isolated environment: `data/cache/sc04-figures-env-attempt01/environment03`.
- Environment record: `figure-environment-qualification02/QUALIFICATION.json`.
- Current fictional figures: `data/cache/sc04-figure-qualification-attempt03`.
- Figure receipt SHA-256: `b19765d96e1e35a2a9e347e7251fc890c7b457cea48d10eff2c704b6a1edfb61`.
- Final visual/source qualification: `figure-qualification02/QUALIFICATION.json`.

The output contains three SVG/PNG pairs, `PLOT-DATA.json`, input and code proofs in `FRAME.json`, a hash-chained progress journal, and a receipt for the complete inventory. Visual inspection is recorded separately; the sealed renderer output retains its original `visual_inspection: pending` value.

1. All five arms: raw accuracy, substantive answer coverage, and precision among substantive answers. Failed calls remain in the scheduled denominators; no substantive answers produces undefined precision.
2. All six prespecified raw-accuracy contrasts: publication-group confidence intervals and question-level sensitivity. The one-publication fictional fixture has undefined primary intervals. No interval is fabricated. Plotted numbers are copied from the sealed analysis; no bootstrap is rerun.
3. Annotated question–DOI pair coverage at retained article, candidate pool, and selected-context layers. This is bibliographic identity coverage, **not scientific entailment**. The supplied-source arm is diagnostic.

For the O arms, passage selection uses lexical-overlap ordering; original order only breaks ties. The figure labels therefore say **Lexical passages**. Earlier plot attempts and helper bytes remain preserved, including a corrected overlapping footer and the corrected ordering labels.

## Environment provenance

The environment uses existing CPython 3.11.15 and Matplotlib **3.10.7**, released October 9, 2025. Official metadata lists Python >=3.10 including 3.11 support. The project license is PSF based. See [official release metadata](https://pypi.org/project/matplotlib/3.10.7/) and [official license](https://matplotlib.org/3.10.7/project/license.html).

Eleven exact wheels total **31,210,636 bytes (29.77 MiB)**, below the authorized 250 MiB acquisition cap. Official PyPI JSON, response receipts, wheel SHA-256 hashes, original wheels with license files, and a hash-locked requirements file are retained under `data/cache/sc04-figures-env-attempt01`. The private uv cache is `data/cache/sc04-figures-uv-cache`. Installation used only the acquired wheels and offline resolution; provider spending is $0. Existing qualified environments, experiment code, and the data downloader were not changed.

The first metadata attempt stopped before wheels because fonttools supplied both native and universal wheels. An explicit native-wheel preference resolved it in preserved `metadata02`. Sandbox restrictions blocked Windows launcher updates during the first venv and install attempts. Although `environment02` passed imports and version compatibility checks, final inspection found its six console launchers missing. It is preserved; a clean scoped offline installation created `environment03`. `INSTALLATION-COMPARISON.json` records the concrete difference. Final validation checks every installed RECORD hash and all six launchers in addition to `uv pip check`, exact versions, official wheel hashes, license-file presence, and Agg initialization. No existing qualified scientific-analysis environment was changed.

## Reproduce the fictional figures

From the repository root in PowerShell, choose a **fresh** output directory:

```powershell
$env:MPLCONFIGDIR = 'D:\Projects\drug_target_agents\data\cache\sc04-figures-env-attempt01\mplconfig03'
& 'data/cache/sc04-figures-env-attempt01/environment03/Scripts/python.exe' -I -B `
  planning/review-assets/tether-semantic-20261106/sc04/render_analysis_figures.py `
  --fictional `
  --analysis data/cache/sc04-analysis-cli-qualification-attempt04 `
  --analysis-sha256 acfd87731d44ba1b632bd8b33c4f85ecf8547e256f5dd9300f3047bc94570816 `
  --acceptance planning/review-assets/tether-semantic-20261106/sc04/analysis-root-acceptance-fictional03 `
  --acceptance-sha256 fbdc09d48dd25ea1265cab5d920f91eca792813d2679dffc437cc2b30fa5ef8c `
  --environment planning/review-assets/tether-semantic-20261106/sc04/figure-environment-qualification02/QUALIFICATION.json `
  --environment-sha256 f32e99c0d9318dfbaa6265f751a05f71aa7cc29b19b37fa23239e2bd09777ed7 `
  --output data/cache/sc04-figures-local-reproduction01
```

Run the 23 tests with the same interpreter and `test_render_analysis_figures.py --output <fresh-directory>`. Tests include altered receipts, missing arms, wrong denominators, NaN values, incorrect source nesting, undefined precision, undefined one-group uncertainty, interval endpoints outside the original estimate, output reuse, retained failure records, and explicit fictional SVG/PNG labels. Three additional peer-review controls reject correct counts exceeding substantive answers, precision inconsistent with its count ratio, and contrast points inconsistent with the four arm rates. These are direct arithmetic joins, not rescoring or bootstrap repetition. The initial test run failed only because Windows sandbox temp locations were not writable; tests now use a workspace-contained temporary directory.

## Production boundary

Production plotting requires a completed, externally anchored production analysis and its PASS root-acceptance receipt. Remove `--fictional` only for such inputs. The helper enforces all five arms, 199 scheduled questions per arm, 205 annotated question–DOI pairs, and 186 publication groups. Never relabel fictional plots or substitute partial live-run metrics. Reinspect the final production PNGs before using them in the paper.

Exact plot bytes may vary across font/rendering platforms. This record pins the local interpreter and package versions; it does not turn byte integrity into scientific truth. The accepted analysis remains responsible for original-source/native reconstruction and statistical arithmetic. The plot helper checks sealed inputs and direct plotted-value joins.
