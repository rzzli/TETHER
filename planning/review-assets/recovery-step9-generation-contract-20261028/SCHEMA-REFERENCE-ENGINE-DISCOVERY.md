# Offline reference-schema engine discovery

**Updated status:** the corrected uv path checked in the addendum below contains
cached JSON Schema packages. The initial missing-package conclusion and proposed
new acquisition are superseded by that discovery; qualification is still pending.

28 October 2026 UTC. **No qualified independent reference engine was found in
the bounded local locations checked.** This is discovery evidence, not a schema
validation result or an exhaustive statement about every file on the computer.
The closed [extension comparison](CORPUS-EXTENSION-RESULT.md), its original
documents, expectations and one-shot PowerShell result remain unchanged.

The discovery used installed-host `importlib.util.find_spec`, package metadata,
Node `createRequire(...).resolve(...)`, and immediate known-directory listings.
No validator package was installed, imported to validate data, or fetched. No
corpus or Unicode-control batch, PowerShell oracle rerun, native grammar call,
vocabulary/tokenizer/model load, server or inference ran. No whole-user-drive
search was performed.

## Python results

| Existing interpreter | Observed version | Package discovery |
|---|---|---|
| `D:\Projects\drug_target_agents\.venv\Scripts\python.exe` | Python 3.11.15, MSC 1944, AMD64 | `jsonschema` and `fastjsonschema`: no spec and no installed distribution metadata |
| `C:\Users\zzric\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` | Python 3.12.14, MSC 1944, AMD64 | `jsonschema`, `fastjsonschema`, `referencing` and `rpds`: no spec and no installed distribution metadata |

Direct known-directory checks also found no `jsonschema` package in the existing
0.3.10 default or ingestion wheel environments. Standard per-user Python install
and roaming package roots checked here were absent. No engine version, package
path, source hash or local string-length implementation can therefore be
reported for Python JSON Schema validation.

An additional bounded check covered the two explicitly identified uv archive
roots. `C:\Users\zzric\AppData\Local\uv\archive-v0` was absent.
`D:\Projects\drug_target_agents\data\cache\uv-preparation\archive-v0` contained
24 top-level archive directories, all checked without truncation (cap: 2,000).
Exact child `__init__.py` checks found none for `jsonschema`, `fastjsonschema`,
`referencing`, `jsonschema_specifications`, `rpds`, `attrs` or `attr`. No cached
engine or matching dependency roots were therefore available for an offline
environment assembled from these caches. No cached code was executed.

## Node results

The existing bundled executable is
`C:\Users\zzric\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe`,
reporting **v24.19.0**. Resolution returned `MODULE_NOT_FOUND` for
`ajv/package.json`, `ajv/dist/2020.js` and `jsonschema/package.json` at the
following existing or standard package roots:

- The project root and bundled Codex primary-runtime root.
- Bundled `dependencies/node`, its `@oai/artifact-tool` package and its `pnpm` package.
- `C:\Users\zzric\.codex\plugins\cache\openai-primary-runtime`.
- `C:\Users\zzric\AppData\Local\OpenAI\Codex\runtimes\cua_node`, plus its two installed revisions `1fb7137c46617d50` and `78fb63cda1a9e2b2`.
- `C:\Users\zzric\.vscode\extensions\openai.codex-audio-26.1021.22027`.
- `C:\Users\zzric\AppData\Local\Programs\Microsoft VS Code\resources\app` and its standard JSON-language-server package root.

Immediate directory filters in the bundled Node `.pnpm` store returned no names
matching `*ajv*`, `*jsonschema*` or `*json-schema*`. The standard global npm package
root was absent. `vscode-json-languageservice/package.json` also did not resolve
from either checked VS Code/Codex runtime root; no bundled language server was
executed or extracted as a substitute engine.

Consequently, an existing draft-2020 Ajv engine, dependency closure and primary
`ucs2length` implementation were **not located or qualified**. There is no Ajv
package version/path/hash to pin, and no available engine on which to base a
prospective validation-batch protocol yet. No conclusion about an unlocated
package's behavior follows from these results.

## Host executable pins

These identify the hosts used for discovery, not installed validator packages or
their complete runtime dependencies.

| Host | SHA-256 |
|---|---|
| Project Python executable | `3746b0f06795510801712b7ade197eeeea161063432a5ccec916ecd5bafe69ea` |
| Bundled app Python executable | `5640e9be2fd33d05a1a9ae1228e2354609a69ab831605995ec4e2bd6da8fff5e` |
| Bundled Node executable | `3602f2bb1a10f2cbab4c36886218a33c1ab3db87290e73b033c46c77147d0237` |

## Disposition

The observed `Test-Json` acceptance of the 1,802-code-point combining-mark case
remains a tool discrepancy. Its cause has not been established from the
PowerShell dependency's primary implementation. No grapheme-counting diagnosis,
schema relaxation, normalization or corpus rewrite is justified by this search.

The next engineering prerequisite is a **separately authorized, exact-version
reference-engine acquisition and inspection**, preferably a draft-2020 Ajv
distribution with its full offline dependency closure. That later step should
pin package and host hashes, inspect its actual length-keyword implementation,
then prospectively freeze a single bounded batch over the unchanged 167 cases
and separately labeled Unicode length controls. This note neither authorizes
acquisition nor spends a future validation attempt. The current reference-engine
gate is unavailable locally, while strict validation evidence remains retained.

## Addendum: corrected uv cache path contains candidate packages

28 October 2026 UTC, after the initial discovery. The initial C: cache hint omitted
the `cache` path segment. The recorded absence of
`C:\Users\zzric\AppData\Local\uv\archive-v0` remains accurate for that different
path; it says nothing about the corrected path.

The explicitly authorized additional check inspected only top-level archive
directories under `C:\Users\zzric\AppData\Local\uv\cache\archive-v0` and exact
known package `__init__.py` paths, plus immediate `.dist-info` directory names.
All **348 directories** were checked under the 2,000-directory cap, without
truncation. No package import, installation, validation or code execution occurred.

| Candidate distribution label | Relative archive roots beneath the corrected cache |
|---|---|
| `jsonschema-4.26.0` | `k5zMh1I94cktfILjawn79`, `KEEj4yBqmFUdAmqM2Kw3a` |
| `referencing-0.37.0` | `_otTDk1tF35GuPrzecDsg`, `EIAouAl3HnAKkclR8TYWC` |
| `jsonschema_specifications-2025.9.1` | `0v5dYOFfXmuCH_TybYlnX`, `yPekydzNH2PkvwOYdh7ju` |
| `attrs-26.1.0` | `_Skmrp7wYgOObbfQ3NkWK`, `YLb4Sz4MkXLfWQo6t17IG` |
| `rpds_py-2026.5.1` | `mDvB1JoDsxQY1Dnf9f9tP` |
| `rpds_py-2026.6.3` | `UmRZ5clbAUczk8DJ9HlAJ` |

Versions in this table are observed directory labels, not yet metadata/RECORD
qualification. The exact matching code, dependency closure, native extension
platform/interpreter compatibility, source length implementation and artifact
hashes remain unverified. No `fastjsonschema` candidate was found by the exact
path check.

**Revised next prerequisite:** inspect and pin these existing cached candidates
under a separate read-only qualification scope. If compatible and complete, a
new isolated offline validation environment could use the cache while preserving
the project's dependency-free default environment. New downloads are not currently
established as necessary. The prospective batch remains unprepared and unspent;
the original corpus, frozen expectations and PowerShell discrepancy remain intact.
