# Independent pure analyzer review

**Clear for the frozen source/pure component scope.** The reviewed analyzer is
`537a780a…`, bound to contract`05c214f4…`, vectors`150a6f05…` and freeze`125d1474…`.
The author source remains unchanged.

Eight independent methods pass. They reproduce all15 literal frozen vectors and
compare272 piece partitions of four authored scalar sequences against a brute
interval model using declared scalar widths, without the analyzer's decoder or
bisect logic. Additional probes cover all12 complete-width×pending-width cells,
zero pieces, original token ordinals, class-priority/first-selection/de-duplication,
unknown population, excluded QC failures and deep result/input immutability.

The source correctly excludes carried-in scalar completions from mixed witnesses.
It counts distinct complete widths once per boundary and preserves the earliest
witness for each width. Unknown population cases suppress complete totals and
all selectors while retaining known lower bounds. Source eligibility flags define
the population; measured outcomes do not filter it.

`required_available=True` is geometry availability, not profile acceptance. An
excluded case with unknown QC remains visible through`all_case_QC_complete=False`.
The future profile gate must retain both dimensions. The author's84-document
one-byte-piece exercise remains explicitly synthetic and was not independently
rerun for this review.

No material component blocker was found. This review establishes no model-to-piece
authenticity, tokenizer behavior, native row fit, runtime resource fit, grammar
profile qualification, full vocabulary mask or scientific result. No old profile,
CPU/GGUF/pack, SDK, target or native compiler operation occurred. The old negative
experiment and incomplete external timeout remain unchanged.
