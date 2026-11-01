# Portable P05 result presentation exporter

This version ports the frozen P07 table serialization and ReportLab figure geometry. It consumes only four explicitly pinned public metadata files. It opens no private ledger/audit paths, originals, reference facts or raw outputs, and imports no old tools or project runtime package. It adds no scientific endpoint or model call.

Eleven CSV tables, eleven Markdown views and fifteen PDF/SVG/PNG/data/caption files must match all **37** reviewed historical payload commitments. The old README contained owner-specific commands and is deliberately replaced by portable instructions. The output `ARTIFACTS.json` is a new version with its own authority, code/input/output hashes and new rendering costs; it does not impersonate the historical manifest. Figure data/captions retain the historical scope and denominator warnings.

Use Python with already available ReportLab, pypdf and Pillow. Supply Poppler's `pdftoppm` explicitly or put it on `PATH`. No dependency is installed automatically. Fonts are ReportLab standard Helvetica/Helvetica-Bold; no font files are included.

Run from any directory, supplying your own paths:

```text
python build_results.py --check-inputs \
  --comparison comparison.json --comparison-sha256 1fc123d3c368d355c1f3d66a76eeaacea9ae954c6a6fad9aa3d05390d225cce0 \
  --source-policy source-policy.json --source-policy-sha256 8d88c5dca9dfbebfd7851a6e50b5d668bdedd0a6f35bd0b77aebdff01fabf6c1 \
  --historical-resources historical-resources.json --historical-resources-sha256 af588a157854752e66ff4de8393d000af727d1c15a1542fb6a01b9ba4ddb2970 \
  --expected-payloads expected-payloads.json --expected-payloads-sha256 30dfdeceabe87bf4db58ec78e5106cf4a73f3286d788962d21033f27312b48c8
```

Replace `--check-inputs` with `--build --output-root fresh-results` and optionally add `--pdftoppm /your/path/to/pdftoppm`. The backslashes above indicate shell line continuations; Windows PowerShell users can place the command on one line. Inputs are hash-checked before output reservation. The output directory must not exist; partial failures remain inspectable and cannot be resumed or silently overwritten. The default wall budget is 120 seconds (maximum 300), with cooperative phase checks, bounded Poppler subprocesses, 4 MiB per input and 16 MiB output caps. This is a bounded fixed presentation exporter, not an OS sandbox or generic report engine.

In Codex PDF-authoring workflows, run the PDF skill operation marker externally exactly once immediately before the operation's first build (three expected PDF outputs). The script neither calls that app-specific marker nor depends on it for ordinary local use. Inspect the current previews; text/page/dimension/vector checks do not replace visual review.

Historic resource values in reproduced tables are copied from explicitly bound public metadata. Shared generation is counted once per case and source verification overlaps producer total. Those figures are not new presentation-build costs; the latter are recorded separately. Exact bytes are expected only under the same Python/ReportLab/Poppler rendering environment. Cross-platform font/rendering equivalence is not claimed.

The metadata hash projection binds the original historical manifest without shipping its owner-specific environment fields. Comparison and resource files remain evaluator-only. Rendering figures does not execute actual source replay, verify the old private archive or resolve pending author/publication declarations.
