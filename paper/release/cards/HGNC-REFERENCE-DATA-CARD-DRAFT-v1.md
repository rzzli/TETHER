# HGNC normalization reference data card

Status: DRAFT; rights evidence and packaging recommendation, not legal certification. Official pages accessed 2026-11-01. No new reference payload was downloaded.

## Asset identity

P05 retains one tab-separated `hgnc_complete_set.txt`, 16,973,159 bytes, designated locally `snapshot_2026-10-10`. The acquisition URL recorded in neutral metadata is [HGNC's current complete-set TSV endpoint](https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt). The local designation is an acquisition date, not a provider-certified annotation release. A current response from this mutable URL must not be assumed to match the retained file.

Its P05 role is normalization/reference support. No participant-level clinical originals, protected outcome data, bespoke human responses or descendants are part of the proposed release. Identifier cross-references do not imply redistribution permission for separately linked third-party products.

## Rights and version evidence

The [official HGNC licence](https://www.genenames.org/about/license/) releases all HGNC data under CC0 and recommends attribution despite not requiring it; its resource identifier is `RRID:SCR_002827`. Attribute HGNC and follow the provider's citation guidance rather than inferring project authorship from source acknowledgements.

The [official archive help](https://www.genenames.org/download/archive/) describes monthly and quarterly complete-set TSV/JSON archives. Monthly files older than 365 days may be removed; quarterly files are currently retained. This does not establish an archived object byte-identical to the locally acquired 10 October file. No archived TSV/JSON payload was fetched or compared here, and the accessed pages did not show a licence revision date.

## Proposed disposition

Use **external original plus a reviewed hash manifest** in this draft package, matching the other actual P05 dependencies. This is an operational consistency choice, not a claim that HGNC's CC0 terms forbid redistribution. A later explicit allowlist could admit the exact HGNC file under CC0 with its source, retained byte hash/size, acquisition designation and attribution, after confirming that the intended file matches the frozen inventory and that no unrelated files are included.

A recipient reconstructing P05 must supply the exact retained TSV (or prove byte identity of a provider archive object); a newly fetched current complete set or an adjacent quarterly snapshot is a different input. If the retained file cannot be supplied lawfully or recovered exactly, mark full replay unavailable. Fictional normalization fixtures may qualify code behavior, but do not stand in for this actual input.

Evidence anchors are recorded in `planning/review-assets/preprint-p09-20261101/RIGHTS-SOURCE-AUDIT-v1.md`.
