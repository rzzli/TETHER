# Verifier adapter design: independent review

The architecture is suitable for a separately authorized **pure injected interface** stage. The [machine review](VERIFIER-ADAPTER-INDEPENDENT-DESIGN-REVIEW-v1.json) pins the original design and its [platform clarification](VERIFIER-ADAPTER-PLATFORM-CLARIFICATION-v1.md). This is a design critique, not source implementation, SDK qualification or live verification authority.

The same-owner origin/handoff is the right boundary: the entry starts its clock before helper reads/imports; the engine adopts that origin, output ownership, journal, early live leases and fresh captured bytes. No numeric restart, serialized ready flag, copied-original substitute or cross-run receipt is sufficient. Immutable captured bytes then feed every real checker. Application-level return registration, once-only cleanup and the nonfinal seal/final-clock rule preserve the earlier corrections.

The six read-stream APIs do not provide ancestry checking, finite run-root enumeration or a real output sink. The clarification now holds those as separate pending stages. It proposes attributes/search APIs with bounded rosters, an explicit end-of-directory/error distinction and search handles closed with `FindClose`. It also discloses that ctypes conversion precedes Python assignments: an unobserved native return remains unknown, and no atomicity or universal cleanup guarantee follows.

Before real platform binding, freeze the complete API/flags/layout/sentinel/closer census, including exclusive directory/file creation and write/flush/close. Derive the exact ancestor/scan/output call and event bounds; exhausted headroom is incomplete, not an excuse to omit records or increase limits. Do not supply these operations through hidden `Path`, `os.walk`, `scandir`, `rglob` or launch-SDK routes.

The finite source loader also needs an exact own-module/dependency map, relative-name rules and approved stdlib policy. Own helpers must load only from captured hash-matching bytes, with no ordinary fallback even to cached own `sys.modules` entries. Path discovery and traceback/linecache/inspect source reopening are outside the intended boundary. A real first-clock bootstrap and these loader guarantees remain implementation work.

Actual archive/universe/receipt/seal, journal/order, raw-resource/EOF/exit/cleanup and versioned profile checkers are still missing. The frozen Unicode corpus does not implement its new decoder, wire or runtime roster. Preserve the old failed189-case profile and its incomplete external verifier. Neither synthetic gates nor this design demonstrate actual300-second feasibility, full-mask/model quality or scientific validity.

No reviewed helper/test, original/source input, CPU/GGUF/pack, SDK, compiler or target operation ran during this review. The source-only design record grants no implementation or live permission; root decides the next bounded stage separately.
