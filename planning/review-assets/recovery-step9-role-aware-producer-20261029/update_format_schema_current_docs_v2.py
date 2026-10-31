"""Retain the full-project reassessment after exact format-schema review."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAME = "Project Progress Reassessment 2026-10-29 - Producer Format Schema.md"
OLD = "Project Progress Reassessment 2026-10-29 - Producer Storage Design.md"
LOG = "research-log-2026-10-29-producer-format-schema"
ACCEPTANCE = "14bc12d3b193cb1d92ea7bc6ec852efa4728eac8b8beeda95e0ea2fd895d3b1f"


def main():
    raw = (HERE / "ROLE-AWARE-PRODUCER-FORMAT-SCHEMA-ACCEPTANCE-v2.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ACCEPTANCE
    decision = json.loads(raw)
    assert decision["source_implementation_authorized"] is False
    prior = (ROOT / "planning" / OLD).read_text(encoding="utf-8")
    table = prior.split("| Item | Current status and remaining gate |", 1)[1].split("\n\nAsOf", 1)[0]
    rows = ["| R09 | Exact producer-format schema reviewed; independent literals are being prepared. Actual codec and live producer integration, complete new84 roster, entry/FFI, physical outputs, native/masking, integrated resources and scientific usefulness remain unfinished. |" if row.startswith("| R09 |") else row for row in table.splitlines()]
    table = "| Item | Current status and remaining gate |" + "\n".join(rows)
    p = "review-assets/recovery-step9-role-aware-producer-20261029/"
    assessment = f"""# Project reassessment after the producer format schema

29 October 2026 UTC. The exact machine schema is accepted for independent literal preparation. It closes the required byte layouts, typed states and interface semantics before implementation. This is progress toward the full operational producer; a codec-only pass will not complete R09. No encoder, live producer, physical route or new model experiment has been qualified. The C++ tools work without restarting.

This is a project-wide status reconciliation plus new bounded planning/metadata verification. It does not rerun the application or inspect original model/data targets. The [previous storage assessment](<{OLD}>) remains preserved.

## What is now fixed

Root [schema acceptance]({p}ROLE-AWARE-PRODUCER-FORMAT-SCHEMA-ACCEPTANCE-v2.json), SHA `{ACCEPTANCE}`, verifies twelve evidence-index pins. The [schema v2]({p}ROLE-AWARE-PRODUCER-FORMAT-CONTRACT-v2.json), `b71cd8f4...`, [delta]({p}ROLE-AWARE-PRODUCER-FORMAT-DELTA-v2.json), `9116ec34...`, and [freeze]({p}ROLE-AWARE-PRODUCER-FORMAT-FREEZE-v2.json), `6840693d...`, bind the [independent peer]({p}ROLE-AWARE-PRODUCER-FORMAT-INDEPENDENT-REVIEW-v2.json), `7828e215...`. Root independently checks contiguous layouts, record widths, all fourteen API IDs and the seven active original-file APIs. No subject implementation or subject tests were run by this gate.

The format specifies a 4096-byte header, eight section descriptors, 256-byte call and file records, 64-byte module records, 1024-byte diagnostic records and 64-byte section descriptors. All offsets, widths, byte order, reserved bytes, enum values and size/hash rules are explicit. Queries and other byte pools use record size1/count equal to byte length, including empty sections. Unknown, observed NULL, integer zero and INVALID_HANDLE remain distinct. Signed BOOL32 values, observed-but-undefined counts/errors and typed integer/float clocks retain their meaning.

Five pre-golden clarification groups are closed. They cover descriptor counts, absent expected size/input-handle tags, three-state error definition, the exact decoded/error/publication/legacy value surface, and logical-versus-boxed storage accounting. The [root choice]({p}ROLE-AWARE-PRODUCER-FORMAT-ROOT-CLARIFICATION-CHOICE-v2.json), `97c2c672...`, preserves the first schema/HOLD. Definition observedness is independent of whether a raw error value returned. `DecodedLedger.to_dict()` retains canonical input types, including tuple module edges; it does not mint owner or exception identities. Publication schema2 and scope/status names are explicit. New BOOL atoms map to legacy BOOL32 without changing signed values.

The critical first-fact decision is operationally meaningful: preallocated canonical Python slots receive the original returned object through one direct assignment before validation, packing, cache updates or clocks. Sentinel identity determines observedness. The 256-byte wire records are derived snapshots, not primary storage. A packing failure must leave raw zero/NULL/count/error facts and cleanup rights intact. Native-to-Python conversion remains an explicit unqualified boundary.

The schema adds 13,823,488 bytes of named logical reference/value-bit allowances to the earlier 113,985,546-byte design sum, totaling **127,809,034 named logical bytes**. Eight value-bit bytes do not bound CPython boxed digit storage. Numeric objects, slot/container headers, allocation overhead, compiled modules, exception graphs and other implementation memory remain unbounded by this sum. No physical memory or timing fit follows.

## Evidence boundaries and the full operational path

The corpus/test plan permits at most forty semantic base histories, with byte-negative expansions, anchors, callbacks and API calls counted separately. Goldens and test-source expectations must freeze before encoder code. Full-cap generated layouts establish size/shape behavior; they are not evidence that real histories occurred. Pure format cases can prove exact bytes, strict decoding, rejection, immutability and cancellation. They cannot establish live raw-slot adoption, diagnostic reservation reuse, generated-store provenance or owner/exception identity.

`project_legacy` therefore requires a genuine same-owner ProducerSnapshot. A dict or DecodedLedger cannot recreate opaque tokens. The unchanged48 histories and existing regressions must eventually run against the actual new producer through the declared projection, preserving actual counters, raw facts, known late returns and identity checks. This remains producer integration work. API IDs8-14 are unqualified fragments until a physical profile exists; a complete seven-original ledger is not a complete physical-run proof.

```mermaid
flowchart LR
  A[Original inputs by declared role] --> R[Canonical first-fact slots]
  A --> I[Captured original bytes only]
  R --> E[Derived encoder and assembly]
  E --> G[Immutable generated byte store]
  I --> C[Source-bound byte consumers]
  G --> C
  G -. separate physical qualification .-> P[Owned output artifacts]
```

This is the prospective architecture. None of the arrows implies that the physical route is already qualified.

The [critical-path review]({p}ROLE-AWARE-PRODUCER-CRITICAL-PATH-AUDIT-v1.md), `2fe93b67...`, calls for actual producer integration rather than another abstract calculator. In parallel, the [composition/reservation map]({p}DISTINCT84-INTEGRATION-AND-PHYSICAL-RESERVATION-MAP-v1.md), `980ba277...`, binds existing codec/analyzer/observer interfaces, fourteen exports, fourteen artifact actors/caps and missing first-entry/physical pieces. The new84 pack remains logical/in-memory, not a physical file; new kernel, child/parent/build/protocol and full source/import/consumer graph remain unresolved.

Retained descriptor evidence adds four concrete native-core dependencies absent from the earlier sixteen-resource subset: ggml-base803840 B, ggml78848 B, libomp768000 B and llama3581952 B, totaling **5,232,640 B**. Their paths/hashes are known from historical rows23-26 and the fixed ABI context; future capture roles remain unresolved until actual PE/content consumers are selected. File extensions do not grant a role, fresh eligibility or authority.

The physical map also prevents an incorrect capacity claim. The historical original-file C is13482 at1MiB. Existing owner WriteFile design uses64KiB, with conservative W<=2921, Flush<=2251, eleven owner-written artifacts and fourteen possible readbacks. Readback Q51/R275/C359 and6*11 other identity/open/close operations give **19079 combined reservations before directories, launcher and pipes**. The original-only C16384 is not a joint physical fit. A full physical reservation and record scope must be completed before activation.

## Resource distinction affecting the real project

The vocabulary-only child remains limited to256MiB Job commit,120 seconds including cleanup and117 seconds of work. Its old61.39MiB observation does not establish inference fit. Named R07 metadata instead records context16384/parallel1/offload49-of49, startup-reported model8148.38MiB, KV3072MiB and compute137.01MiB, plus cumulative observed process PeakWorkingSet **12,325,232,640 bytes**. This is not a per-call allocation or measured VRAM peak. GPU/native peaks are null, and exact inference RAM/VRAM ceilings and KV policy are absent from the bounded records inspected. Those are existing integrated-resource declarations to resolve before generation, not a new gate or a reason to infer fit.

The0.3.9/0.3.10 transports were simulated; their parent working-set peaks and295.922/300-second result include no actual model/server startup or inference. Root must qualify actual complete-case startup/source/retrieval/masking/generation/accounting/cleanup cost under the scientific budget. A pure format pass cannot repair that evidence gap.

## Complete recovery status

{table}

AsOf0.3.11/defaultv2 retains1,774 passing full tests,327 source/resource pins and ten matching preserved-version qualifications. The application suite was not rerun for this schema/metadata gate. Earlier indexed-accounting and calculator source acceptances remain intact. Data/science still has65 missing inputs,36 unqualified endpoint labels,17/32 observable registry states and0/12 jointly source-ready clinical cases. Numerical prediction features remain empty, probabilities null and human reviews pending. Provider spending is$0; download worker and stopped periodic monitor are untouched.

The consumed189-case profile remains FAILED, and its independent whole-verification remains INCOMPLETE_TIMEOUT. No original target was statted/opened/hashed, no old experiment replayed and no native/SDK/compiler/model/download/physical operation occurred here.

## Critical next step

1. **Finish independent fixtures, then implement one real slice.** Freeze the bounded byte corpus, semantic expectations and test source. Implement the concrete codec together with role-aware producer/ports/controller integration, or with a clear immediate integration boundary. Do not claim live provenance from decoded structures or end the task at a stand-alone roundtrip. Preserve primary raw slots before all packing and retain exact input/output immutability and cancellation behavior.
2. **Qualify genuine producer behavior at meaningful scale.** Reuse old identity/failure regressions and add actual role/capture/generated-byte tests, full-profile metadata and generated-stream capacity controls. Keep N4 as initial invariants. The1MiB profile, complete evidence, bounded streaming and source-issued contexts must be implemented. Retain every failed first attempt and original expectation; no dropped calls, fake byte evidence or healed caches.
3. **Close the prospective roster and physical route in parallel.** Pin the real source/import/consumer graph, physical pack/new child/build/parent and live first-clock/typed binding. Recompute joint original+owned-write/readback/directory/launcher reservations; do not call16384 a full-run capacity. Qualify new-format archive/journal/resource composition against actual bytes under the original deadline.
4. **Qualify distinct native and integrated execution.** Only a concrete separate decision may authorize the new84 observation. Preserve all84 cases,78 byte-eligible/six harness exclusions/68 coverage population and deterministic full-corpus selection. Full-vocabulary masks and generation are separate gates. Declare and measure inference resources explicitly; retain negative outcomes rather than repeating the consumed profile or silently amending limits.
5. **Finish the scientific sequence.** Complete qualified R08 inputs and HR1-HR3 before R10. Use the timed independent pilot to size/freeze H5/R11 before locked R12 and HR4. Clinical ascertainment, genetics/LD, predictors/calibration, comparisons and T2-T5/H6 remain individually conditional. Agent engineering review cannot manufacture human submissions or biological validity.

The project remains unfinished. This checkpoint authorizes literal preparation only; production source and runtime decisions remain separate.
"""
    output = ROOT / "planning" / NAME
    assert not output.exists()
    staged = {output: assessment}
    common = ["README.md", "TODO.md", "planning/Project Recovery and Evaluation Plan 2026-10-26.md", "planning/Recovery Status and Next Gates 2026-10-26.md", "planning/Project Progress Reassessments.md", "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md"]
    for relative in common:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        prefix = "planning/" if relative in ("README.md", "TODO.md") else ""
        current = f"Current checkpoint: [producer format schema](<{prefix}{NAME}>) is accepted for independent literal preparation (root `14bc12d3`, peer `7828e215`). Exact layouts, typed states, first-slot-before-packing rules and five value-surface clarifications are closed. Codec data is not live producer authority. Independent byte fixtures are next; actual codec/producer/legacy identity, complete84 roster, physical/native/resources and scientific/human gates remain open."
        text, count = re.subn(r"^Current checkpoint: .*?$", lambda _: current, text, count=1, flags=re.M)
        assert count == 1, relative
        next_step = "Next: freeze exact independent literals and tests, then implement the concrete codec plus genuine role-aware producer integration. Prepare roster/physical composition in parallel. Original-only C16384 does not cover the19079 pre-directory physical bound. Inference resources are separate from vocabulary-only256MiB. AsOf0.3.11/defaultv2 retains1,774 tests/327pins/ten preserved versions; no application or real runtime change."
        text, count = re.subn(r"^Next is the complete offset.*?$", lambda _: next_step, text, count=1, flags=re.M)
        assert count == 1, relative
        if relative == "README.md":
            text = text.replace(f"See the [current full-project reassessment](<planning/{OLD}>),", f"See the [current full-project reassessment](<planning/{NAME}>),", 1)
        if relative == "TODO.md":
            old = "- [ ] Freeze complete offset/enum/raw-fact/checker/legacy schema and independent literal corpus before role-aware encoder/producer implementation."
            assert old in text
            new = "- [x] Freeze and independently review the exact offset/enum/raw-fact/checker/legacy schema: b71cd8f4, peer7828e215, root14bc12d3 verifies12pins. Five pre-golden groups closed; original d5f28/HOLD44eee preserved. This authorizes independent literals only, not source or runtime."
            text = text.replace(old, new + f"\n- [ ] Reassess all R01-R16/HR1-HR4 after producer format schema; retain {NAME} and current-document QA.\n- [ ] Freeze independent literal corpus/test source, then implement and qualify the concrete codec and genuine role-aware producer integration (old48 identity plus new role/fault/full-profile controls).", 1)
        if relative == "planning/Project Progress Reassessments.md":
            text += f"\n| R09 exact producer-format schema reviewed | [29 October UTC format snapshot](<{NAME}>) | Root14bc12d3/peer7828e215 verifies12pins and five closed schema groups. Literal preparation only; actual producer/legacy/physical/native/science gates remain pending. Critical-path memory and joint call reservations recorded. |\n"
        staged[path] = text
    log_path = ROOT / "memory" / (LOG + ".md")
    assert not log_path.exists()
    staged[log_path] = f"""---
name: {LOG}
description: Exact producer schema, literal boundary and operational resource gaps
metadata:
  type: project
---

# Producer format checkpoint

Schema b71cd8f4 / peer7828e215 / root14bc12d3;12pins verified. Five pre-golden
groups close d5f28/HOLD44eee; widths/offsets/clocks/first-slot/diagnostic semantics
retained. Queries now byte-pool descriptor1/countbytes; absent/null/zero, three
error-definition states, canonical decoded/error/publication and BOOL32 legacy
mapping explicit. No source/test runtime or goldens existed at schema acceptance.

Primary canonical Python slots precede derived wire encoding.13,823,488 extra
logical reference/value bits give127,809,034 named logical bytes with priorF1;
ALL boxed digit/object/allocator/exception/module memory remains unknown.
Pure codec cannot recreate genuine ProducerSnapshot/owner/exception identities.
Next freeze<=40 base literal histories and honest byte-negative/anchor/callback
counts, then implement actual codec+producer integration, not another calculator.

Critical-path note2fe93b67 and map980ba277 identify parallel roster/physical work.
Missing core4 total5232640B; roles remain unresolved. Original C13482 plus writer/
flush/readback=19079 beforedirectories/launcher/pipes; C16384 is original-only.
R07 metadata context16384/parallel1/offload49of49, reportedGPU model8148.38/KV3072/
compute137.01MiB; cumulative observed processWS12325232640B is not per-call orGPU
peak. Inference RAM/VRAM/KV declarations missing.256MiB is vocabulary-only Job.

[Full reassessment](../planning/{NAME.replace(' ', '%20')}) covers20statuses/fivegates.
App0.3.11/defaultv2,1774retained tests/327pins unchanged;65missinginputs,36unqualified
labels,17of32 registry states,0of12 clinical cases; featuresempty/probabilitiesnull,
humanspending/$0. Old FAILED/INCOMPLETE_TIMEOUT preserved; monitor/downloader untouched.
"""
    path = ROOT / "memory/MEMORY.md"
    text = path.read_text(encoding="utf-8")
    staged[path] = text.replace("# Research memory index\n", f"# Research memory index\n\n- [[{LOG}]] - Schema root14bc12d3/peer7828e215 closes five pre-golden groups; independent literals then actual codec/live producer needed. Original-only versus joint19079 calls and inference versus vocab memory distinguished; full84/physical/science/human gates remain open.\n", 1)
    path = ROOT / "memory/project-goals.md"
    text = path.read_text(encoding="utf-8")
    start, end = text.index("Current source-only checkpoint:"), text.index("Raw-adoption5afb82f0")
    staged[path] = text[:start] + f"""Current source-only checkpoint: [producer format schema](../planning/{NAME.replace(' ', '%20')}).
Root14bc12d3/peer7828e215 accepts exact b71cd8 schema for independent literals only;
12pins/five groups closed, d5f28/HOLD44eee preserved. Primary Python raw-slot
assignment before packing; wire/decoded data cannot create live authority.
<=40 semantic histories planned; no goldens/encoder/producer at schema acceptance.
Next actual codec+role-aware producer integration must preserve old48 opaque
identities; decoded dicts cannot substitute. Parallel roster/physical map980ba277
records missingcore4=5232640B, joint19079 pre-directory calls beyond originalC16384.

F1 payload113985546 plus live logical bits13823488=127809034; all boxed numeric/
object/storage remains unbounded here. R07 actualmetadata context16384/offload49,
reported model/KV/compute8148.38/3072/137.01MiB and cumulativeWS12325232640B do not
provide GPU/per-call peaks or inference RAM/VRAM ceiling.256MiB is vocab-only.
See [[{LOG}]]. Full84 source/build/pack/entry/FFI/physical/masks/integrated/science/
human gates unfinished; app0.3.11/defaultv2/1774tests/327pins and prior acceptances
unchanged. Old FAILED/INCOMPLETE_TIMEOUT and all before evidence preserved.

""" + text[end:]
    for path, text in staged.items():
        path.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"documents": len(staged), "assessment": str(output), "literal_preparation_only": True}))


if __name__ == "__main__":
    main()
