# Returned-review integrity and evaluator isolation

**PASS for exact preservation, declared text projection and evaluator-role rejection only.**
The [retained report](INTAKE-INTEGRITY-AND-ROLE-REVIEW-v1.json) records 95 checks,
all passing, for three originals totaling 22,693 bytes. It publishes no answers.

- Original files and preserved copies match all three known SHA-256 hashes.
- The DOCX archive has 24 members / 112,749 expanded bytes, passes CRC checks and
  has no ZIP symlink, encrypted member or macro payload. All 122 paragraph locators/text projections
  match; comments and tracked insertions/deletions are zero. This is XML-text
  equivalence, not rendered, checkbox, drawing or OCR equivalence.
- Both strict UTF-8 line projections match exactly: 72 and 39 lines, with no
  replacement characters. Original bytes retain encoding markers/line endings.
- Source originals, copies, projections and intake manifest are Git-ignored.
- Existing catalog products `gold_evidence` and `panel_ratings` remain
  evaluation-only. Twelve direct/derived rejection controls pass, including
  forged `agent_evidence`/`reference` roles and rejection before payload hashing.
  One ordinary agent-role positive control passes. Returned answers enter none
  of these synthetic graphs or any model request.
- Six selected existing synthetic role regressions pass with zero failures,
  errors or skips. This is not a full-suite rerun or a scientific evaluation.

The first checker probe used the wrong refusal-message substring; the existing
catalog correctly denied access. The next wrapper hit default sandbox temporary
directory permissions and did not retain its detailed in-memory test counts.
Both failures are preserved. The final run uses an explicit ignored workspace
temporary directory, preserves the test log before assertions and changes no
pre-existing test method or framework source.

All human/reference acceptance flags remain false. The intake manifest leaves
reviewer identity and independence null; separate provenance/content review must
resolve human versus AI authorship, relevant expertise/conflicts, exposure and
source-first sequence, workload and exact packet binding. A filename, copied
file or completed mechanism form does not close R07, fresh HR3 or locked H5.
No adjudicated gold, clinical label, model-quality or fresh-case claim is made.
