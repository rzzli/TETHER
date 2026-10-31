# Captured native archive format map

This is a source-only proposal for a pure captured-byte checker. It does not replay or qualify an old run. No old output directory, original payload, native API or compiler was accessed for this map.

The retained recognition-v7 emitter has three publication phases. `receipt.json` hashes the files present before that receipt. `post-lease-cleanup.json` then records original lease-close outcomes and pins the immutable early receipt. `terminal-seal.json` hashes the post-cleanup files, including the early receipt and cleanup, while excluding itself. `after-seal-failure.json`, if written, pins the terminal seal and vetoes its unchanged on-disk status. The source only changes the returned in-memory status after publishing that final marker.

The early receipt needs its own membership rule. Stream and child files precede it, while cleanup, late failures and the terminal seal follow it. A publication error after the receipt can add a root `failure.json`; that later marker is absent from the receipt map but belongs in the terminal map. Requiring both maps to cover the same captured universe would reject a legitimate negative archive or encourage rewriting earlier evidence.

The terminal map can be compared exactly with the supplied run-file capture, excluding the terminal seal and after-seal marker. That is closure over supplied bytes. It cannot establish that the real directory had no other files. Missing terminal artifacts remain incomplete; failed or malformed failure markers remain vetoes.

All run locators are fixed source spellings. Absolute pin paths must match a predeclared run root and known locator before byte lookup. The checker never resolves, opens, hashes or follows a metadata path. Protocol and authority are separately supplied byte objects; protocol/effective-protocol bytes and direct declared pins can be compared without recursively opening source, build, model or pack ancestors.

The static authority excludes current parent/authority/checker/proof hashes. Those four dynamic pins appear only in the protocol roster after the static authority has been frozen. Checking that split catches declared cycles; it does not authenticate the roster's original sources. CPU, ordered model and pack entries remain descriptor-only metadata.

The proposed contract fixes the retained v7 format. A coherent negative archive can have a valid byte graph; a positive observation status can still fail other gates. Every result keeps profile qualification, original authentication, actual-directory completeness and source qualification false. Future Unicode formats and semantic/resource/source/owner checks require separate bindings.

Literal actual-shaped fixtures will be authored and frozen after root reviews this contract, before any checker implementation. They will cover both publication orders, late vetoes, finite path/DAG attacks and failure prefixes. No fixture will be an actual-run replay.
