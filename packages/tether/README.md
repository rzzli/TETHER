# TETHER

TETHER is the canonical front door for the evidence-agent framework. This
distribution is `tether-target-agents` 0.4.1, with Python namespace `tether` and
command `tether`. It depends on the unchanged `asof-target-agents==0.3.11`
compatibility engine. The default uses no third-party runtime libraries; the
optional `ingest` extra pins PyArrow 21.0.0. Local models remain explicit opt-in.

The separate project preserves the original root project, wire IDs, dataclass
identities, code proofs and historical release bytes. Legacy names in those
artifacts identify their actual implementation; they are not silently rewritten.
An installed TETHER launcher is additional code, with its own proof.

Version 0.4.1 adds deterministic verification of category status transitions,
reviewed selections versus committed claims, and the complete engine dossier.
The `tether verify` command applies these checks to v2 engine runs as well as
new outer runs. The aliases `tether.artifacts` and `tether.semantics` continue to
expose the frozen legacy API; use the CLI or `tether._presentation.verify_engine`
for the additional boundary. Version-one receipts retain their original scope.

Archived TETHER 0.4.0 outer runs require the pinned 0.4.0 wheel/source to verify
their launcher fingerprint. The original review packet remains that historical
version; this correction does not rewrite its sources, paper or artifacts.

From this directory, development tooling resolves the engine through
`tool.uv.sources` at `../..`. Root integration instructions own environment/lock
setup. There is no implicit provider download or new scientific study.

```text
tether --help
tether --version
tether demo --output <existing-parent>/fresh-demo
tether verify --run-dir <existing-parent>/fresh-demo --receipt-sha256 <saved-hash>
tether inspect-run --run-dir <existing-parent>/fresh-demo
```

`demo` and `run` reserve a new outer directory. `engine/` contains the unchanged
legacy run, including its dossier, source bindings, journal and receipt. The
outer `dossier.md` changes only the exact first `AsOf dossier` header to `TETHER
dossier`; its remaining bytes are identical. `tether-manifest.json` binds this
projection, all engine files and the launcher code/version. The outer attempt
journal closes before `tether-receipt.json` is published. Save the printed
outer receipt hash independently; without it wholesale tree replacement is not
detectable. Receipt roles are evaluation-only, with scientific validation
explicitly unestablished.

Outer verification checks the launcher, paths, complete file inventory, journal,
exact dossier projection and genuine source-inclusive engine verification.
`--outputs-only` is rejected for an outer run. Direct v2 engine verification adds
the checks described above; other commands retain their engine semantics. TETHER metadata/journal reads are
limited to 64 MiB; dossier reads/products have a separate 256 MiB limit. These
reads reject oversized or nonregular files before opening, use bounded chunks,
reject links/reparse points and check file identity before and after reading.
Inspection parses one captured journal buffer; legacy verification/inspection
also receive journal-size preflight from the new wrapper. This per-read check is
not a promise of exclusive filesystem ownership across all later engine reads.
Help and frontend errors are branded
TETHER; legacy wire formats and core outputs retain compatibility identities.

Failures and interruptions preserve `tether-failure.json`, the outer attempt and
any inner journal. `inspect-run` reads them without retrying. Choose a new output
for any later attempt. Any exception from the supervised engine pipe attempts
bounded termination/draining, killing if necessary, and reaping. The original
error (or interrupt cause), cleanup errors and available partial bytes are kept;
failed cleanup remains explicit rather than reported as successful. This is
trusted local execution, not an OS sandbox or a
clinical/model-quality/scientific validation claim. No frozen P05/P09 package or
paper archive is modified by this distribution.
