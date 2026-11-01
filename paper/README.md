# AsOf technical paper working draft

This is a bounded source-reporting feasibility paper. It is not a clinical,
causal-genetics, independent-study or model-superiority result. External expert
responses are excluded from the study. No publication or public artifact deposit
has occurred.

Read [the manuscript](manuscript.md), [supplementary methods](supplement.md),
[the combined 17-page working PDF](asof-source-reporting-preprint.pdf),
[results and rebuild instructions](results/README.md),
[bibliographic records](references.bib) and the
[primary-source positioning audit](RELATED-WORK-SOURCE-AUDIT.md).

The study retains 38 outputs/90 policy decisions and an independent source audit.
Its twelve native units demonstrate the literal copy ceiling and preserve
missingness. Fourteen exposed controls demonstrate the exercised guard behavior.
Earlier local-model development failures remain reported separately. These
quantities and their limits must stay attached to every presentation.

The scientific text and rendered working draft are reviewable artifacts;
submission readiness additionally requires the factual
[author declarations](AUTHOR-DECLARATIONS.md), a qualified lawful release and the
final manuscript/artifact check. Unconfirmed author facts are not silently
converted into no-funding or no-conflict declarations. See the live
[project checklist](../TODO.md) for remaining P08-P10 work.

The renderer uses the already available ReportLab/pypdf runtime; the default
AsOf runtime remains dependency-free. Rendered figures use the vector files in
results/figures. The PDF build manifest records exact source/renderer/figure
hashes, rendering versions and text-preservation checks. Layout must also pass
visual inspection of every page; a successful text extraction alone does not
certify layout.

The current PDF passes all 273 ordered visible-text unit checks, all-page visual
review and a byte-identical fresh-process repeat. Three figures remain vector;
no raster images or out-of-page glyphs are present. The formatter's six negative
retention cases and two failed-publication-path cases pass. This qualifies local
presentation only; it does not qualify a public installed/relocated study release.
PDF SHA-256: `4f19060e0bb67fdd932780de9765a415f42c518cde74895302aa45b942ead588`.

The local renderer is `tools/science/build_preprint_manuscript.py`. In an existing
environment with the recorded ReportLab/pypdf/pdfplumber, fonts and Poppler,
`--check-inputs` validates parsing without writing and `--self-test` runs the
retention/failure controls. After the PDF skill marker succeeds once for the
authoring operation, `--build --marker-confirmed --repeat-check` renders both
sources, validates them and writes PDF-BUILD.json. The local paths are recorded
in code; a portable public renderer is not claimed. Source edits require a new
render and review; never reuse a previous source's successful manifest.

The exact P05 protocol, run, source-audit and analysis hashes are in Supplement S1.
Post-result manuscript/formatting edits do not modify that frozen experiment.
The separate paper-content and positioning audits live under
planning/review-assets/preprint-p08-20261101/ in this checkout. No raw datasets,
model weights or historical response archives are licensed for redistribution
by this paper directory.

The [renderer peer review](../planning/review-assets/preprint-p08-20261101/PDF-RENDERER-PEER-REVIEW-v1.md)
retains independent text inventory, vector/body geometry, local repetition and
caught-failure rollback evidence. It qualifies this trusted local rendering
operation, with no crash-atomic or hostile-filesystem guarantee.
