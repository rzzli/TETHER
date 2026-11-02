# Second reviewed unpublished 0.3.12 executing archive profile

This migration is prepared for the stable serializer correction. Root application
and fresh archive/full/installed validation remain required. It is not a
release-completion record.

The first executing profile is retained byte-for-byte as
`semantic_dependencies-0.3.12-first-candidate.json` (SHA256
`27282ad12814df284cb9a81c25f935f0c47177ead845c9e831bc687c64d85e59`).
Its own predecessor and qualification remain in `../archive-profile/` unchanged.

The second migration permits only a reviewed `serde.py` module-pin change plus
profile metadata. The 22-module inventory, 21 other module pins, frozen admission
policy, archive Python implementation, and archived source/data bytes must remain
unchanged. The new `previous_resource_sha256` must identify the retained first
profile, not skip that migration.

The reviewed serializer correction has SHA256
`fa910ce74c0766240eac3a64443b4b4baf7b6b64b064a1b028cda4ace66eb79c`.
It changes only atomic JSON replacement and cleanup error reporting. On Windows,
errors 5, 32, and 33 receive at most three replacement attempts on the same staged
bytes, with 50 ms and 100 ms requested delays. Error 5 may also be permanent; the
retry is bounded and is not an assertion that any specific failure is transient.
Other errors propagate immediately. Exhaustion propagates the final original
error; a cleanup error adds a note instead of hiding the primary exception.

Serialization, canonical fingerprints, source admission, receipt semantics and
the no-clobber publisher are unchanged. There is no non-atomic fallback and no
model-call retry. The diff preserves all other serializer functions. The new
ten-test regression suite includes deterministic fictional errors and a private
native Windows file-handle case. Its retained red and green evidence is under
`../integration/windows-replace/`; the final focused validation must also pass.

Versions remain 0.5.1 / 0.3.12 because this is an unpublished candidate that has not
passed the aggregate release gate. Earlier installed qualifications describe their
own retained source/wheel hashes and are not rewritten or promoted to cover this
new source. A new installed attempt and full source bracket are required.

Validation requires the new atomic-write regressions; a fresh 52-test archive suite;
relocated fictional old-engine normal and unknown-usage runs that still verify;
and the old contradictory overquote run that still rejects. The archive dependency
guard remains strict. A complete full-suite gate, facade gate, and fresh isolated
installed qualification must also pass before aggregate completion.

No biological, clinical, benchmark, model-quality, or external-expert conclusion
is established by this engineering migration.
