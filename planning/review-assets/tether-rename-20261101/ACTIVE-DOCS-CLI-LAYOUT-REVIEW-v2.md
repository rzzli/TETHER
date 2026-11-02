# TETHER CLI layout documentation closeout v2

PASS: 210/210 focused checks, no findings; all 124 local Markdown links in the 21 changed documents resolve. The original v1 branding inventory and 221-check validation remain unchanged.

Updated only the owned root README and 20 active guides. The canonical `tether demo/run --output OUT` layout is now explicit: an outer dossier, `tether-manifest.json`, `tether-receipt.json`, `attempt/journal.jsonl`, retained engine streams and the unmodified legacy run under `OUT/engine`. Only the first dossier header is projected to TETHER; remaining dossier bytes stay identical to the inner document.

The docs distinguish the outer receipt hash from the engine receipt hash. `tether verify/inspect-run --run-dir OUT` understand the outer attempt; outer verification includes genuine source replay and rejects `--outputs-only`. Legacy `asof verify --run-dir OUT/engine` remains supported. Failed/interrupted attempts retain `tether-failure.json` and journals for inspection without automatic retry.

Public API aliases under `tether.*` retain the legacy objects and output layouts. The separately implemented `tether._presentation` CLI layer creates the new outer presentation. Delegated `inspect-source`, `build-snapshot` and `evaluate` commands retain their engine layouts. The framework/migration receipt sections now identify their legacy-inner scope.

The CLI author confirmed filenames/layout stable. The retained v2 inventory pins the inspected `_cli.py`, `_presentation.py` and package README. AST-only checks confirm the exact filename constants; no new CLI/API execution, install, broad suite, scientific/data action or source read was performed. Data/catalog bytes and all v1 history/evidence remain unchanged by this follow-up. Runtime and package qualification are separate.

Evidence: `document_cli_layout_v2.py`, `ACTIVE-DOCS-CLI-LAYOUT-CHANGES-v2.json`, `validate_cli_layout_docs_v2.py`, and `ACTIVE-DOCS-CLI-LAYOUT-VALIDATION-v2.json`.
