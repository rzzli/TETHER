# Six-prompt offline token feasibility — current 0.3.5

Status: completed feasibility measurement only. No execution policy or runtime changed.

The six unchanged payloads reserve **14,315 input tokens**, including 32 margin units each, against the unchanged 32,000 limit. Output reservations total 6,144 against 8,000. Every input reservation plus 1,024 output tokens fits the 16,384-token context. The earlier conservative byte proxy totaled 47,753 units; those units were not measured model tokens.

| Exact stage | CLI token count | Input reservation (+32) | With 1,024 output |
|---|---:|---:|---:|
| asof_interpretation | 2,330 | 2,362 | 3,386 |
| chief_of_staff | 2,324 | 2,356 | 3,380 |
| coordinator_delegate | 2,342 | 2,374 | 3,398 |
| mapped_specialist | 2,358 | 2,390 | 3,414 |
| scientific_reviewer | 2,377 | 2,409 | 3,433 |
| coordinator_synthesize | 2,392 | 2,424 | 3,448 |

Initial pin checks, asset verification and all six quotations took 111.218 seconds within one absolute 300-second deadline. Separate read-only replay took 1.969 seconds and launched zero children. All 305 accepted source/resource pins matched before quotation, after quotation and after replay.

The experiment started exactly six approved tokenizer processes, generated no text, started no server, made no network attempt and spent 0 on providers. E: file reads were limited to the 34 approved existing model/runtime assets and acquisition receipt. Original source fields, selected IDs id03/id04, retrieval policy, complete guides, histories and budgets remained unchanged.

These are six exact full-ID hypothetical histories, not a maximum over all possible BPE histories. They establish sizing feasibility for current 0.3.5 only. Any future package must obtain fresh quotes after its own code freeze and retain full package-proof checks. No native run, scientific result, real clinical prediction or human review is authorized by this result.

The separately retained v1 attempt failed in its planning-helper audit guard before any OS child started. V2 was prospectively authorized with an exact Windows command-line representation correction and pure guard checks before E: reads. V1 failure records and its empty child record remain unchanged; no possibly completed call was repeated.

Result SHA256: 23e42fd792435435fbaee3f5a9be5481b58d3729e86f71852cde3408465c38ff
Protocol SHA256: d7b6f73b370796abda19795323236721d86c5d0e5bec34db1c445f80a41767a8

[Result and six external receipt anchors](TOKEN-QUOTE-RESULT-v2.json) · [Prospective protocol](TOKEN-QUOTE-PROTOCOL-v2.json) · [V1 failure closeout](TOKEN-QUOTE-FAILURE-CLOSEOUT-v1.json)

Ignored retained output: D:\Projects\drug_target_agents\data\cache\r09-four-arm-tokenquotes-v2-20261026T223407Z
