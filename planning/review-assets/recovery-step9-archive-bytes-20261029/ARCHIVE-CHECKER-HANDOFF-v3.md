# Archive checker v3 source/pure handoff

Implementation is paused at the following exact candidate, pending the independent peer record and root disposition:

- Source `captured_archive_v3.py`: `90ba49a96713b6178320f04e68affee084abfb77588551b22140330309cd7d9b`.
- Checker `check_captured_archive_v3.py`: `e6df7bd2272e56b5c7278d5b2901ad7f4d7d34f44a74ee4c28fe40e6b917e599`.
- Pure proof `CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v3.json`: `cfde0f81ae458c9d76a4cd29cb68ef8ba532e8f4be01c71d3ce96a67c552b8c9`.
- Exact byte/AST freeze `CAPTURED-ARCHIVE-CHECKER-FREEZE-v3.json`: `43041bffa8058a25ca16fe79e4bce375e29c5d1b17ea236d89ffdc25a0b3ac29`.

Thirteen methods pass, including all 32 unchanged frozen projections, fully rebound before/after cases for the two v2 findings, nullable-condition/type/range controls, callback `OverflowError` identity, and the preserved v2 callback/LF regressions. The correction admits only the documented already-closed null close result and uses noncoercing integer/finite-float predicates. There is no broad outer catch or expanded cleanup qualification.

Earlier sources, passing proofs, later failure witnesses and peer HOLD evidence remain intact. The component has no filesystem/API/native operations and no actual old archive replay. All original, directory, source, full-journal, resource/profile and owner-provenance qualification flags remain false. File-port work remains a separately reviewed design/fixture gate; no port implementation is included.
