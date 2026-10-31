# Independent Unicode wire design review

The proposed direction matches the frozen84-case profile and accepted analyzer,
but **three revisions are required before literal framing fixtures freeze**.

1. The profile reserves16actual footer rows of at most8,192bytes each. Pooling
   eight units into one65,536-byte JSONL failure row violates that frozen per-row
   constraint even though aggregate bytes fit. Keep failure JSONL at8,192bytes
   including LF; the independent failure file can retain its65,536-byte cap.
2. Setup payload schemas and exact cumulative API/state vectors remain deferred.
   Close those per-stage schemas and finite observation enums before fixtures;
   global caps and monotonic counters do not establish the required deltas.
3. Mixed EOG observations must not erase a valid piece ledger or turn known
   geometry into unknown. Preserve geometry QC/counts and separately report the
   native disagreement/null membership, which fails the profile. This preserves
   the analyzer's separation between fixed population, geometry and observation.

Two smaller clarifications belong in the revision. The measured template is
6,407bytes excluding arrays; replacing native membership null with false makes
it6,408, still below8,192. Use a strict field maximum and label it a mathematical
envelope. API-name/null enums should contain actual JSON null rather than the
literal string`"null"`.

Independent arithmetic agrees with84/78/6/68 cases, four stage instances and two
grammars. The fixed eligible-byte token budget is62,260 document tokens plus at
most6,848 selected-prefix tokens. The resulting69,108 token work,74,356 applies,
124,520 piece calls and82 samplers remain below the unchanged hard caps. Their
positive upper sum is530,477; the hard cap sum remains4,276,181. Reserved JSONL
bytes7,995,392 and all structured artifact bytes8,065,024 fit their aggregate cap;
that does not waive individual row buckets or prove runtime fit.

No additional material contradiction was found in full arrays/zero pieces,
whole-corpus first selection/de-duplication, separate expectation dimensions,
unknown handling or the source-role intent. This review read only the new design
and frozen metadata and performed data arithmetic. It built no pack or row
implementation and performed no CPU/model/old-pack, native, SDK, compiler or OS
operation. No profile, scientific or previous-timeout qualification follows.
