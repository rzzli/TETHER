# AsOf technical paper working draft

This is a bounded source-reporting feasibility paper. It is not a clinical,
causal-genetics, independent-study or model-superiority result. External expert
responses are excluded from the study. No publication or public artifact deposit
has occurred.

Read [the manuscript](manuscript.md), [supplementary methods](supplement.md),
[the revised 18-page working PDF](asof-source-reporting-preprint-v2.pdf),
[results and rebuild instructions](results/README.md),
[bibliographic records](references.bib) and the
[primary-source positioning audit](RELATED-WORK-SOURCE-AUDIT.md).

The study retains 38 outputs/90 policy decisions and an independent source audit.
Its twelve native units demonstrate the literal copy ceiling and preserve
missingness. Fourteen exposed controls demonstrate the exercised guard behavior.
Earlier local-model development failures remain reported separately. These
quantities and their limits must stay attached to every presentation.

A separate post-result P09 qualification covers installed, relocated Windows
source reconstruction and independent source audit. It reproduces the retained
P06 outputs and decisions; it adds no study, model result or scientific validation.
The [qualification record](release/qualification.json) and
[external release hash record](release/RELEASE-RECORD.json) specify the supported
environment, exact authorities, separate costs and missing external availability.
The inner frozen P09 bundle intentionally retains its earlier paper bytes. This
P10 source/PDF revision is a separate version. No public deposit is claimed.

The scientific text and rendered working draft are reviewable artifacts;
submission readiness additionally requires the factual
[author declarations](AUTHOR-DECLARATIONS.md) and final owner acceptance. The
local P09 artifact is qualified within its explicit Windows scope; final P10
working-packet checks are recorded separately. Unconfirmed author facts are not silently
converted into no-funding or no-conflict declarations. See the live
[project checklist](../TODO.md) for remaining P08-P10 work.

The renderer uses the already available ReportLab/pypdf runtime; the default
AsOf runtime remains dependency-free. Rendered figures use the vector files in
results/figures. The PDF build manifest records exact source/renderer/figure
hashes, rendering versions and text-preservation checks. Layout must also pass
visual inspection of every page; a successful text extraction alone does not
certify layout.

The revised PDF passes all 273 freshly checked ordered visible-text units,
all-page visual review and a byte-identical local repeat. Three figures remain vector;
no raster images or out-of-page glyphs are present. The formatter's six negative
retention cases and two failed-publication-path cases pass. This qualifies local
presentation only. P09 source reconstruction has its own separate evidence.
Current PDF SHA-256: `c9778533984d2a04451c0f535b54704397977a13de1832dc4dfe9364d25d766d`.
Its [build manifest](PDF-BUILD-v2.json) records the new source hashes:
main `79a49c7bbaba7ad65786cc5e1bbfd872ae941396990b2d17315f685e4ca3b507`;
supplement `d1a63bec471b13d44e888c4f40857d67d2cd13e504c2acef856659c3f5fabb85`.
The [prior 17-page P08 PDF](asof-source-reporting-preprint.pdf) and its build
manifest remain unchanged historical artifacts; their old checks are not proof
of this revision. Four release/status paragraphs changed; all remaining source
bytes, primary results and original protocol anchors are unchanged by exact
inverse-delta verification.

The unchanged local renderer is `tools/science/build_preprint_manuscript.py`. In an existing
environment with the recorded ReportLab/pypdf/pdfplumber, fonts and Poppler,
`--check-inputs` validates parsing without writing and `--self-test` runs the
retention/failure controls. After the PDF skill marker succeeds once for the
authoring operation, the explicit
`planning/review-assets/preprint-p10-20261101/build_working_pdf_v2.py` wrapper
with `--build --marker-confirmed --repeat-check` renders both sources, validates
them and writes only the versioned PDF/PDF-BUILD-v2.json pair. Its effective
output overrides and code hash are retained in that manifest. The local paths are recorded
in code; a portable public renderer is not claimed. Source edits require a new
render and review; never reuse a previous source's successful manifest.

The exact P05 protocol, run, source-audit and analysis hashes are in Supplement S1.
Post-result manuscript/formatting edits do not modify that frozen experiment.
The original paper-content/positioning audits live under
planning/review-assets/preprint-p08-20261101/; current revision evidence is under
planning/review-assets/preprint-p10-20261101/. The qualified P09 allowlist has one
explicit CC0 HGNC original and exact project receipt metadata; 136 Open Targets
originals remain external. Other raw datasets, model weights or historical
response archives are not licensed for redistribution by this paper directory.

The [renderer peer review](../planning/review-assets/preprint-p08-20261101/PDF-RENDERER-PEER-REVIEW-v1.md)
retains independent text inventory, vector/body geometry, local repetition and
caught-failure rollback evidence. It qualifies this trusted local rendering
operation, with no crash-atomic or hostile-filesystem guarantee.
