# Prospective corpus extension and pure comparison protocol

28 October 2026 UTC. This follows the pure generation contract and its bounded
input amendment. It authorizes no native grammar, DLL, tokenizer, vocabulary,
model, server, provider or network operation.

1. Preserve the original 109-case file byte-for-byte at
   `data/cache/r09-native-grammar-corpus-20261028/cases.json`, SHA-256
   `01286d35689c7005ea67fa817c4b4098cecd05c4233c3949e7ec744bc5f5d97a`.
   Never normalize or replace its documents. Assert current base acceptance
   schema bytes match its pinned schema before comparing any case.
2. Prepare a separate `generation-domain-extension-v1` under a new cache directory.
   Use the current v3 synthetic-context preparation and one separately tagged,
   fixed synthetic source-literal variant. Both are development fixtures. Preserve
   original serialized document bytes in individual files. Record authored schema,
   strict-validator and generation-membership expectations separately, including
   implementation-dependent schema parse cases and the explicit claim-uniqueness
   exception. Freeze inputs and code/helper/dependency pins before oracle execution.
3. Run the existing pinned PowerShell 7.6.5 `Test-Json` script in **one** batch child,
   at most 120 seconds, with exact argv, no profile or interaction. Verify the
   executable, script and four existing assembly hashes first; acquire nothing.
   Retain stdout, stderr, exit/timeout and elapsed time. No automatic retry after
   failure. A failed oracle is a retained blocker, not a reason to edit documents.
4. Independently replay original bytes through the complete v3 strict post-validator
   and the restricted pure GBNF interpreter. That interpreter recognizes only the
   emitted finite subset; it is not actual DLL/tokenizer/EOG evidence. Preserve
   observed schema acceptance, strict acceptance, and pure membership independently.
   Compare extension membership with authored expectations. Preserve differences;
   classify alternative key order/JSON spellings as outside the declared domain
   without changing their otherwise valid decoded values.
5. Retain a report, frozen artifact inventory and future native-corpus manifest
   with document/request/payload/schema/grammar hashes. The future manifest is
   reference material, **not execution authorization**. Recheck original corpus
   hash and source/helper pins. Native conformance and science remain unverified.

Boundary coverage includes joint length/nonblank at 1,800/1,801, reason 512/513,
raw/escaped BMP/astral/control/whitespace, combining marks, noncharacters, BOM and
zero-width values, less-than spellings, known-literal Unicode/separators/control
delimiters, distinct reference orders, surrogate/JSON parse failures, and the
post-only cross-claim uniqueness rule. The original 109 cases stay intact.
