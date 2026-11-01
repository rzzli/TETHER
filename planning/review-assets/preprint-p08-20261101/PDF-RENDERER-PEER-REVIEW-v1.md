# Independent PDF renderer peer review

**PASS for the current trusted local rendering operation.** No unresolved renderer finding remains. This review covers code, source retention, caught-failure publication handling, layout and local reproduction; it does not reopen the paper's scientific claims or approve submission.

The final anchors are:

| Artifact | SHA-256 |
| --- | --- |
| Renderer | `0d6044702a8e6f97de605f7f92acf140c337f7a3f19b1bf6a2c0abb0b432238f` |
| PDF build manifest | `f920afd5ea4259ca8f8f4da4255dc43a0d317978cffabf7434dc8ac4ba77dcb5` |
| Combined 17-page PDF | `4f19060e0bb67fdd932780de9765a415f42c518cde74895302aa45b942ead588` |
| Main Markdown | `b01d42fccaf046ad0db52d0becd36be994eac440759f23aefaa0673bf7a9ce29` |
| Supplement Markdown | `977aba2fc3cab68513a78fde08b3cacf0a375af52c908c0fd46bbf1818337200` |

## Findings resolved

The first text check could lose repeated paragraphs, cells or words because substring membership overrode token-count deficits. The final renderer records each visible source unit in ordered marked spans and compares exact unit text after declared typography and layout normalization. Its omission, duplicate, reorder, repeated-word, table-cell and caption negative controls pass.

The first publication order could replace the PDF before preview validation or Poppler success. The final renderer validates the preview path, prepares candidate PDF and versioned previews, and publishes after QA. Invalid-preview and fictional Poppler-failure tests preserve the prior pair. Independent injections at both the first and second publication `os.replace` calls also restore the exact prior PDF and manifest.

Verified figures were initially reopened without binding the consumed bytes. The final code retains the verified bytes for sizing and overlay, and retains font bytes before use for exact hash reporting. Font metadata now says `subset_when_used`, avoiding a claim that unused loaded fonts are embedded. The used Arial regular and bold resources contain embedded subsets. These fixes required no scientific or numerical change.

## Independent evidence

Both `--self-test` and `--check-inputs` pass under the bundled Python 3.12.14 runtime. Input parsing finds 131 blocks, six tables, three figures and thirteen numbered references. The self-test has one positive retention case, six meaningful retention negatives and two publication negatives.

An independent inventory constructed directly from the two raw Markdown files, without the producer parser, matches all 273 retained visible-unit hashes in source order: 91 paragraphs including references, 31 headings, 148 table cells and three Markdown figure captions. PDF span QA observes all 273 units with zero missing, changed, duplicated or reordered units; only two repeated table-header draws are allowed. There are no out-of-page glyphs, no raster images, three vector overlays and 29 link annotations. Header/footer sequences match all seventeen pages.

The peer rerendered the final pinned code in a fresh process entirely in memory. The bytes exactly match the retained PDF hash. Current code, Markdown, PDF, figures, fonts and all seventeen preview hashes agree with their manifest bindings. This establishes local reproducibility under the recorded fonts and library versions, not cross-platform byte identity.

All sixteen initial pages were visually viewed. Seven final pages are byte-identical to those inspected previews; the ten changed final pages were separately viewed. The complete final seventeen-page document is therefore covered. Text, tables, long hashes, references, figures and captions are readable, with no clipping, missing-glyph boxes or footer collision found. The intact control table moves to the next page; the preceding whitespace is acceptable draft pagination.

An independent geometric check matches the text inside each reserved overlay rectangle to transformed original-figure glyphs. Pages 5, 6 and 7 contain exactly 738, 402 and 360 figure glyphs respectively, with no unexplained body glyph or missing figure glyph at 0.02-point tolerance. The vector overlays do not cover body text.

## Scope and limits

This is a fixed trusted local paper renderer, not a hostile-filesystem service or OS sandbox. Caught write-failure rollback is tested; two-file publication is not claimed crash-atomic. Font files are not packaged, and local reproduction does not establish redistribution clearance. The external first-create marker remains author/root caller-confirmed evidence rather than an independently authenticated peer receipt.

The renderer consumes approved Markdown and verified presentation figures/manifests. It preserves the Markdown captions; it does not promise that every separate result-bundle caption file appears verbatim. No underlying biological rows, evaluator values, historical responses or protected clinical material were read, and no model or network execution occurred. The peer edited no producer code or manuscript and wrote only review artifacts plus ephemeral fictional test files.

The PDF remains a working draft pending owner-confirmed declarations and separate release/submission checks. Scientific validation remains unestablished.
